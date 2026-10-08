#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.py  ·  presentation layer for ExamShell (42 · Exam Rank 03 · Python)

Every byte the student sees goes through this module, so the rest of the
code never has to branch on which backend is active:

    rich   -> panels, tables, syntax highlighting     (make install)
    ANSI   -> plain coloured text, runs anywhere      (exam machines)

Colour is turned off automatically when stdout is not a TTY, when TERM is
"dumb", or when NO_COLOR is set (https://no-color.org).
"""

from __future__ import annotations

import contextlib
import difflib
import os
import shutil
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

if TYPE_CHECKING:
    from .grader import FailureLike, Report
    from .shell_common import Session

from ._types import Exercise

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console, Group
    from rich.markup import escape as _rich_escape
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text

    HAVE_RICH = True
except ImportError:  # pragma: no cover
    HAVE_RICH = False


class Abort(Exception):
    """Raised by ask() when the student hits Ctrl-C / Ctrl-D."""


# Indentation scheme used throughout the ANSI fallback: IND0 for lines that
# sit directly under a banner/heading (menus, commands, status, verdicts),
# IND1 for a line nested one level under an IND0 line (table rows under a
# level/difficulty header, …).
IND0 = "  "
IND1 = "    "

# rich style name -> ANSI attribute name, keyed by exercise difficulty.
DIFFICULTY_STYLE = {"easy": "green", "medium": "yellow", "hard": "red"}


# ══════════════════════════════════════════════════════════════
#  BACKEND STATE
# ══════════════════════════════════════════════════════════════
_rich = False
_color = True
_console: Optional[Console] = None


def _out() -> Console:
    """The rich console. Only called on the rich path: _rich is True
    exactly when configure() created one."""
    assert _console is not None
    return _console


def _auto_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return sys.stdout.isatty()


def configure(
    rich: Optional[bool] = None, color: Optional[bool] = None
) -> None:
    """(Re)configure the backend. None means 'auto-detect'. Colours are
    the terminal's own ANSI ones, so the output matches its theme."""
    global _rich, _color, _console
    _color = _auto_color() if color is None else bool(color)
    want_rich = HAVE_RICH if rich is None else (bool(rich) and HAVE_RICH)
    _rich = want_rich and _color
    _console = Console(highlight=False) if _rich else None


def using_rich() -> bool:
    return _rich


def width() -> int:
    return min(shutil.get_terminal_size((80, 24)).columns, 78)


class C:
    """ANSI escapes; every attribute is "" when colour is disabled."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


def c(text: str, *styles: str) -> str:
    """Wrap `text` in ANSI styles (no-op when colour is off)."""
    if not _color or not styles:
        return text
    codes = [getattr(C, s) for s in styles]
    return "".join(codes) + text + C.RESET


def _bar(done: float, total: float, width: int = 16) -> str:
    """A compact block-character progress bar: '██████░░░░░░░░░░'.

    Pure block characters (single terminal cell each), so it's safe to use
    in both the rich and the ANSI path without any display-width pitfalls
    (unlike e.g. emoji, whose rendered width doesn't match len()).
    """
    filled = int(round(width * done / total)) if total > 0 else 0
    return "█" * filled + "░" * (width - filled)


# ══════════════════════════════════════════════════════════════
#  PRIMITIVES
# ══════════════════════════════════════════════════════════════
def clear() -> None:
    if not sys.stdout.isatty():
        return
    os.system("cls" if os.name == "nt" else "clear")


def ask(label: str) -> str:
    """Prompt for a line of input. Ctrl-C / Ctrl-D raise Abort."""
    try:
        if _rich:
            return (
                _out().input("[bold cyan]%s[/bold cyan]" % _esc(label)).strip()
            )
        return input(c(label, "BOLD", "CYAN")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Abort() from None


def confirm(question: str, default: bool = True) -> bool:
    """A yes/no prompt (Enter = `default`). Anything that isn't a clear
    yes or no asks again instead of guessing — a typo must never answer
    for the student (e.g. throw away a saved exam). Ctrl-C raises Abort."""
    label = "%s %s: " % (question, "[Y/n]" if default else "[y/N]")
    while True:
        answer = ask(label).lower()
        if answer == "":
            return default
        if answer in ("y", "yes", "j", "ja"):
            return True
        if answer in ("n", "no", "nein"):
            return False
        warn("please answer y or n")


def pause(label: str = "  Press Enter to continue…") -> None:
    try:
        if _rich:
            _out().input("[dim]%s[/dim]" % _esc(label))
        else:
            input(c(label, "GRAY"))
    except (EOFError, KeyboardInterrupt):
        print()
        raise Abort() from None


def info(msg: str) -> None:
    _line(msg, "cyan", "CYAN")


def note(msg: str) -> None:
    _line(msg, "dim", "GRAY")


@contextlib.contextmanager
def spinner(msg: str) -> Iterator[None]:
    """A live animated status line for a blocking call that can take a
    few seconds with no other feedback (grading — compiling a C
    exercise, running a big fuzz batch, an optional valgrind pass — all
    happen inside one synchronous call with nothing printed until it
    returns). Rich has a real spinner primitive for this; the plain ANSI
    path has no live terminal control worth building for a single line,
    so it falls back to the same static note() line this replaced."""
    if _rich:
        with _out().status("[dim]%s[/dim]" % _esc(msg), spinner="dots"):
            yield
    else:
        note(msg)
        yield


def warn(msg: str) -> None:
    _line("⚠  " + msg, "yellow", "YELLOW")


def error(msg: str) -> None:
    _line("✖  " + msg, "bold red", "RED", "BOLD")


def success(msg: str) -> None:
    _line("✔  " + msg, "bold green", "GREEN", "BOLD")


def hint(msg: str) -> None:
    """A stuck-student nudge (see hints.py) — deliberately calmer than
    warn()/error(): this isn't a problem with the run, just a suggestion."""
    _line("💡 " + msg, "cyan", "CYAN")


def _line(msg: str, rich_style: str, *ansi: str) -> None:
    if _rich:
        _out().print(
            IND0 + "[%s]%s[/%s]" % (rich_style, _esc(msg), rich_style)
        )
    else:
        print(IND0 + c(msg, *ansi))


def _esc(text: object) -> str:
    """Escape rich markup.

    Anything that is not a hand-written style tag must go through this:
    prompts like "[user@exam · lvl1]$", menu keys like "[q]" and student
    output like "[1, 2]" are all valid rich markup otherwise, and rich
    silently swallows them.
    """
    if not HAVE_RICH:
        return str(text)
    return _rich_escape(str(text))


def box_message(title: str, detail: str = "", style: str = "red") -> None:
    """A framed one-liner, used for grading errors."""
    if _rich:
        body = Text(title, style="bold %s" % style)
        if detail:
            body.append("\n" + detail, style="dim")
        _out().print(
            Panel(body, border_style=style, box=box.ROUNDED, padding=(0, 2))
        )
    else:
        colour = {"red": "RED", "green": "GREEN", "yellow": "YELLOW"}.get(
            style, "CYAN"
        )
        print(IND0 + c("[KO] " + title, colour, "BOLD"))
        if detail:
            print(IND0 + " " * len("[KO] ") + c(detail, "GRAY"))


# ══════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════
def banner(
    subtitle: str = "Exam Rank 03  ·  Common Core",
    edition: str = "42 School  ·  Python Edition",
) -> None:
    if _rich:
        title = Text()
        title.append("EXAMSHELL", style="bold white")
        title.append("  ·  " + subtitle, style="cyan")
        sub = Text(edition, style="dim")
        _out().print(
            Panel(
                Align.center(Text.assemble(title, "\n", sub)),
                box=box.DOUBLE,
                border_style="cyan",
                padding=(0, 2),
            )
        )
        return
    w = width()
    inner = w - 2
    print(c("╔" + "═" * inner + "╗", "CYAN"))
    rows: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("EXAMSHELL · " + subtitle, ("BOLD", "WHITE")),
        (edition, ("GRAY",)),
    )
    for text, styles in rows:
        pad = inner - len(text)
        left = pad // 2
        print(
            c("║", "CYAN")
            + " " * left
            + c(text, *styles)
            + " " * (pad - left)
            + c("║", "CYAN")
        )
    print(c("╚" + "═" * inner + "╝", "CYAN"))


def status_bar(s: Session, n_levels: int) -> None:
    """s is a Session (login / level / elapsed() / score() / passed)."""
    level = min(s.level, n_levels)
    if _rich:
        grid = Table.grid(expand=True, padding=(0, 2))
        for _ in range(4):
            grid.add_column(justify="left")
        grid.add_row(
            Text.assemble(("LOGIN ", "cyan"), (s.login, "bold white")),
            Text.assemble(
                ("LEVEL ", "cyan"),
                ("%d/%d" % (level, n_levels), "bold yellow"),
            ),
            Text.assemble(("TIME ", "cyan"), (s.elapsed(), "white")),
            Text.assemble(
                ("SCORE ", "cyan"),
                ("%d/100 " % s.score(), "bold green"),
                (_bar(s.score(), 100, 10), "green"),
            ),
        )
        dots = Text()
        for lvl in range(1, n_levels + 1):
            if lvl < s.level:
                dots.append("● ", style="green")
            elif lvl == s.level:
                dots.append("◆ ", style="bold yellow")
            else:
                dots.append("○ ", style="dim")
        _out().print(
            Panel(
                Group(grid, dots),
                border_style="cyan",
                box=box.SQUARE,
                padding=(0, 1),
            )
        )
        return
    bar = "═" * width()
    print(c(bar, "CYAN"))
    print(
        IND0
        + c("LOGIN: ", "CYAN")
        + c(s.login.ljust(12), "BOLD", "WHITE")
        + c("LEVEL: ", "CYAN")
        + c(("%d/%d" % (level, n_levels)).ljust(6), "YELLOW")
        + c("TIME: ", "CYAN")
        + c(s.elapsed(), "WHITE")
    )
    print(
        IND0
        + c("SCORE: ", "CYAN")
        + c(("%d/100" % s.score()).ljust(12), "BOLD", "GREEN")
        + c("PASSED: ", "CYAN")
        + c("%d/%d  " % (len(s.passed), n_levels), "GREEN")
        + c(_bar(s.score(), 100, 10), "GREEN")
    )
    dot_line = " ".join(
        "●" if lvl < s.level else "◆" if lvl == s.level else "○"
        for lvl in range(1, n_levels + 1)
    )
    print(IND0 + c(dot_line, "YELLOW"))
    print(c(bar, "CYAN"))


def _looks_like_c_prototype(line: str) -> bool:
    """A C exercise's `<type> name(...);` line — the C bank's equivalent of
    a Python `def ...:` signature. Comment lines never end in `;`, and a
    prose sentence ending in a raw `);` doesn't happen in this project's
    subject style, so this is safe without a real C parser."""
    return (
        line.endswith(";")
        and "(" in line
        and ")" in line
        and not line.startswith(("//", "/*", "*"))
    )


def _split_subject(subject: str) -> Tuple[List[str], str, str, str]:
    """Split a subject into (header rows, prose, signature, examples).

    A subject asking for more than one function (Rank 05's
    compress/decompress) shows every `def` line it carries, in order —
    hence a list gathered here rather than a single line kept. A C
    prototype is still taken only once: unlike a `def …:`, that shape is
    guessed at (see _looks_like_c_prototype) and the C banks never ask for
    two functions in one subject.
    """
    header: List[str] = []
    prose: List[str] = []
    examples: List[str] = []
    signatures: List[str] = []
    in_examples = False
    for line in subject.splitlines():
        if line.startswith(("Assignment", "Expected", "Allowed")):
            header.append(line)
        elif line and set(line) == {"-"}:
            continue
        elif line.strip().startswith("def "):
            signatures.append(line.strip())
        elif not signatures and _looks_like_c_prototype(line.strip()):
            signatures.append(line.strip())
        elif line.strip().lower().startswith("example"):
            in_examples = True
        elif in_examples or "->" in line:
            examples.append(line)
        else:
            prose.append(line)
    return (
        header,
        "\n".join(prose).strip("\n"),
        "\n".join(signatures),
        "\n".join(examples).strip("\n"),
    )


def _group_label(ex: Exercise) -> str:
    """'Level N' for an exam exercise, 'Easy'/'Medium'/'Hard' for a training
    one — the two banks tag exercises differently, this renders either."""
    if "level" in ex:
        return "Level %d" % ex["level"]
    return str(ex["difficulty"]).title()


def _file_ext(ex: Exercise) -> str:
    """.c for the C bank's exercises (they carry an 'oracle_c'), .py otherwise.

    Not 'prototype': "program"-kind C exercises (their own main(), no
    harness) have no prototype at all, only "function"-kind ones do.
    """
    return ".c" if "oracle_c" in ex else ".py"


def _reflow(prose: str) -> str:
    """Join the subject's hard-wrapped lines back into paragraphs so the
    text wraps to whatever width it is shown at. Blank lines separate
    paragraphs; an indented or bulleted line keeps its own line."""
    paragraphs: List[List[str]] = []
    current: List[str] = []
    for line in prose.splitlines():
        if not line.strip():
            if current:
                paragraphs.append(current)
                current = []
            continue
        starts_block = line[:1].isspace() or line.lstrip()[:2] in ("- ", "* ")
        if current and not starts_block:
            current[-1] += " " + line.strip()
        else:
            current.append(line.rstrip())
    if current:
        paragraphs.append(current)
    return "\n\n".join("\n".join(p) for p in paragraphs)


def subject_blocks(
    ex: Exercise,
    lexer_theme: str = "ansi_dark",
    code_background: Optional[str] = "default",
) -> Group:
    """The subject as a rich Group (metadata table, prose, signature,
    examples) — needs rich. Shared by subject() below and the full-screen
    TUI (examshell/tui/), which frames it itself."""
    header, prose, signature, examples = _split_subject(ex["subject"])
    lexer = "c" if _file_ext(ex) == ".c" else "python"
    meta = Table.grid(padding=(0, 1))
    meta.add_column(style="cyan", justify="right")
    meta.add_column(style="white")
    for row in header:
        key, _, value = row.partition(":")
        key, value = key.strip(), value.strip()
        if key == "Allowed functions" and value == "None":
            meta.add_row(key, Text(value, style="bold yellow"))
        else:
            meta.add_row(key, value)
    blocks: List[Any] = [meta, Rule(style="grey37")]
    prose = _reflow(prose)
    if prose:
        blocks.append(Text(prose))
    if signature:
        blocks.append(
            Syntax(
                signature,
                lexer,
                theme=lexer_theme,
                background_color=code_background,
            )
        )
    if examples.strip():
        blocks.append(
            Syntax(
                examples,
                "text",
                theme=lexer_theme,
                background_color=code_background,
                word_wrap=True,
            )
        )
    return Group(*blocks)


def subject(ex_name: str, ex: Exercise, rendu_dir: str) -> None:
    group = _group_label(ex)
    ext = _file_ext(ex)
    if _rich:
        _out().print(
            Panel(
                subject_blocks(ex),
                title="[bold yellow]📄 %s[/bold yellow]" % _esc(ex_name),
                subtitle="[dim]%s  ·  file: %s[/dim]"
                % (group, _esc(os.path.join(rendu_dir, ex_name + ext))),
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        print()
        return

    print()
    print(
        IND0
        + c("📄 " + ex_name, "BOLD", "YELLOW")
        + c("   (%s)" % group, "GRAY")
    )
    print(IND0 + c("─" * (width() - 2), "GRAY"))
    for line in ex["subject"].splitlines():
        if line.startswith("Allowed") and line.rstrip().endswith("None"):
            print(IND0 + c(line, "YELLOW", "BOLD"))
        elif line.startswith(("Assignment", "Expected", "Allowed")):
            print(IND0 + c(line, "CYAN"))
        elif line and set(line) == {"-"}:
            print(IND0 + c("─" * (width() - 4), "GRAY"))
        elif "->" in line:
            head, _, tail = line.partition("->")
            print(
                IND0 + c(head, "WHITE") + c("->", "GREEN") + c(tail, "YELLOW")
            )
        elif line.strip().startswith("def ") or _looks_like_c_prototype(
            line.strip()
        ):
            print(IND0 + c(line, "MAGENTA"))
        else:
            print(IND0 + line)
    print(IND0 + c("─" * (width() - 2), "GRAY"))
    print(
        IND0 + c("Create file:  %s/%s%s" % (rendu_dir, ex_name, ext), "GRAY")
    )
    print()


def commands(rows: Sequence[Tuple[str, str]]) -> None:
    """rows: [(command, description), …]"""
    if _rich:
        t = Table(box=None, show_header=False, pad_edge=False)
        t.add_column(style="bold cyan", no_wrap=True)
        t.add_column(style="dim")
        for cmd, desc in rows:
            t.add_row(_esc(cmd), _esc(desc))
        _out().print(
            Panel(
                t,
                title="[dim]commands[/dim]",
                title_align="left",
                border_style="grey37",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        return
    print(IND0 + c("Commands:", "CYAN"))
    for cmd, desc in rows:
        print(IND1 + c(cmd.ljust(9), "BOLD", "CYAN") + c("- " + desc, "GRAY"))


def _pass_rate_tier(rate: float) -> str:
    """Colour tier for a pass rate: solid / shaky / struggling — used so a
    weak spot jumps out of a stats table without reading every number."""
    if rate >= 0.8:
        return "green"
    if rate >= 0.5:
        return "yellow"
    return "red"


def stats_table(rows: Sequence[Tuple[str, int, int]]) -> None:
    """rows: [(name, passes, attempts), …] — per-exercise practice
    history, with a colour-coded pass-rate bar (green solid, yellow
    shaky, red struggling) so weak spots are visible at a glance instead
    of having to read every "N/M passed" number."""
    if _rich:
        t = Table(box=None, show_header=False, pad_edge=False)
        t.add_column(style="bold white", no_wrap=True)
        t.add_column(no_wrap=True)
        t.add_column(justify="right", style="dim")
        for name, passes, attempts in rows:
            rate = (passes / attempts) if attempts else 0.0
            style = _pass_rate_tier(rate)
            bar = _bar(passes, attempts, 12)
            t.add_row(
                _esc(name),
                "[%s]%s[/%s]" % (style, bar, style),
                "%d/%d" % (passes, attempts),
            )
        _out().print(
            Panel(
                t,
                title="[dim]per-exercise[/dim]",
                title_align="left",
                border_style="grey37",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        return
    name_width = max((len(name) for name, _, _ in rows), default=0) + 2
    for name, passes, attempts in rows:
        rate = (passes / attempts) if attempts else 0.0
        style = _pass_rate_tier(rate).upper()
        bar = _bar(passes, attempts, 12)
        print(
            IND0
            + c(name.ljust(name_width), "WHITE")
            + c(bar, style)
            + "  "
            + c("%d/%d" % (passes, attempts), "GRAY")
        )


def menu(rows: Sequence[Tuple[str, str, str]]) -> None:
    """rows: [(key, label, hint), …]"""
    if _rich:
        t = Table(box=None, show_header=False, pad_edge=False)
        t.add_column(style="bold white", no_wrap=True)
        t.add_column()
        for key, label, hint in rows:
            t.add_row(
                _esc("[%s]" % key),
                "%s  [dim]%s[/dim]" % (_esc(label), _esc(hint)),
            )
        _out().print(
            Panel(t, border_style="grey37", box=box.ROUNDED, padding=(0, 1))
        )
        return
    for key, label, hint in rows:
        print(
            IND0
            + c("[%s] " % key, "WHITE", "BOLD")
            + label.ljust(20)
            + c(hint, "GRAY")
        )


def exercise_table(
    entries: Sequence[Tuple[int, int, str, str, bool]], numbered: bool = False
) -> None:
    """entries: [(index, level, name, function, standard), …]. `standard`
    marks the exercises a real exam run can actually draw — everything
    else is practice-only, shown with a dim ○ instead of ★. Shared by both
    testers (examshell/exam_bank.py's Standard/Extra split and
    c_exam/bank.py's)."""
    if _rich:
        t = Table(
            title="[bold]Exercise pool[/bold]  "
            "(★ = can appear in a real exam run)",
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
            row_styles=["", "dim"],
        )
        t.add_column("#", justify="right", style="dim")
        t.add_column("", justify="center", width=1)
        t.add_column("Level", justify="center", style="yellow")
        t.add_column("Exercise", style="white")
        t.add_column("Function", style="green")
        for idx, lvl, name, func, standard in entries:
            mark = (
                "[bold yellow]★[/bold yellow]" if standard else "[dim]○[/dim]"
            )
            t.add_row(
                str(idx) if numbered else "",
                mark,
                str(lvl),
                _esc(name),
                _esc(func + "()"),
            )
        _out().print(t)
        return
    width = max((len(name) for _, _, name, _, _ in entries), default=0) + 2
    last: Optional[int] = None
    for idx, lvl, name, func, standard in entries:
        if lvl != last:
            print(IND0 + c("Level %d:" % lvl, "YELLOW"))
            last = lvl
        prefix = ("[%d] " % idx) if numbered else ""
        mark = c("★", "YELLOW", "BOLD") if standard else c("○", "GRAY")
        print(
            IND1
            + c(prefix, "GRAY")
            + mark
            + " "
            + c(name.ljust(width), "WHITE")
            + c(func + "()", "GRAY")
        )


def training_table(
    entries: Sequence[Tuple[int, str, str, str]], numbered: bool = False
) -> None:
    """entries: [(index, difficulty, name, function), …]"""
    if _rich:
        t = Table(
            title="[bold]Training pool[/bold]  "
            "(LeetCode-style · practice only, not exam material)",
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
            row_styles=["", "dim"],
        )
        t.add_column("#", justify="right", style="dim")
        t.add_column("Difficulty", justify="center")
        t.add_column("Exercise", style="white")
        t.add_column("Function", style="green")
        for idx, diff, name, func in entries:
            style = DIFFICULTY_STYLE.get(diff, "white")
            t.add_row(
                str(idx) if numbered else "",
                "[%s]%s[/%s]" % (style, diff.title(), style),
                _esc(name),
                _esc(func + "()"),
            )
        _out().print(t)
        return
    width = max((len(name) for _, _, name, _ in entries), default=0) + 2
    last: Optional[str] = None
    for idx, diff, name, func in entries:
        if diff != last:
            style = DIFFICULTY_STYLE.get(diff, "white").upper()
            print(IND0 + c(diff.title() + ":", style))
            last = diff
        prefix = ("[%d] " % idx) if numbered else ""
        print(
            IND1
            + c(prefix, "GRAY")
            + c(name.ljust(width), "WHITE")
            + c(func + "()", "GRAY")
        )


def overview_table(
    rows: Sequence[Tuple[Any, str, str, str]], title: str = "Grading overview"
) -> None:
    """rows: [(level, name, status, tests_label), …]

    status is "ok" / "ko" / "missing".
    """
    glyph = {"ok": ("✔", "green"), "ko": ("✖", "red"), "missing": ("·", "dim")}
    if _rich:
        t = Table(
            title="[bold]%s[/bold]" % _esc(title),
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
            row_styles=["", "dim"],
        )
        t.add_column("Level", justify="center", style="yellow")
        t.add_column("Exercise", style="white")
        t.add_column("", justify="center")
        t.add_column("Tests", justify="right", style="dim")
        for lvl, name, status, tests_label in rows:
            mark, style = glyph[status]
            t.add_row(
                str(lvl),
                _esc(name),
                "[%s]%s[/%s]" % (style, mark, style),
                _esc(tests_label),
            )
        _out().print(t)
        return
    print(IND0 + c(title, "BOLD"))
    width = max((len(name) for _, name, _, _ in rows), default=0) + 2
    for lvl, name, status, tests_label in rows:
        mark, style = glyph[status]
        print(
            IND0
            + c(str(lvl), "YELLOW")
            + "  "
            + c(mark, style.upper())
            + "  "
            + c(name.ljust(width), "WHITE")
            + c(tests_label, "GRAY")
        )


# ══════════════════════════════════════════════════════════════
#  GRADING OUTPUT
# ══════════════════════════════════════════════════════════════
def first_diff_index(expected_text: str, got_text: str) -> Optional[int]:
    """Index of the first character where two DISPLAYED strings diverge,
    or None when they're identical. Pure string comparison over exactly
    what's shown on screen (repr(f.expected) vs str(f.got)) — not the
    underlying values — so a --diff pointer lines up with what the
    student actually sees, whether that's a Python repr() or a C
    tester's raw stdout chunk. Used to point at exactly where two long,
    similar-looking values part ways, since side-by-side reprs alone
    hide that past the first dozen characters."""
    n = min(len(expected_text), len(got_text))
    for i in range(n):
        if expected_text[i] != got_text[i]:
            return i
    return n if len(expected_text) != len(got_text) else None


# ── structural diff  (--diff, list/tuple and multi-line values) ───────
# first_diff_index() above is a flat character-by-character compare — great
# for a scalar, useless for "which element of this 20-item list is wrong"
# or "which line of this program's output is wrong". The two helpers below
# cover those: they return None (fall back to the char pointer) when there
# isn't more than one element/line to line up, and otherwise return a pair
# of same-length, line-aligned (expected_lines, got_lines) — one diff line
# per element/source-line, prefixed "- "/"+ " where the two sides disagree
# and "  " where they agree — ready to drop straight into the "expected"/
# "got" columns/blocks _failures() already renders.
def _split_top_level(text: str) -> List[str]:
    """Split a repr()-like string on top-level commas — respecting nested
    brackets/parens/braces and quoted strings, so an inner list's own
    commas (or a comma inside a string) never fragment one logical element
    into two. Not a parser, just a lint-style scan — same "good enough,
    not exact" spirit as c_exam/grader.py's _strip_comments_and_strings()."""
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    quote: Optional[str] = None
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if quote:
            current.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                current.append(text[i])
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            current.append(ch)
        elif ch in "([{":
            depth += 1
            current.append(ch)
        elif ch in ")]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _strip_outer_brackets(text: str) -> str:
    if len(text) >= 2 and text[0] in "([" and text[-1] in ")]":
        return text[1:-1]
    return text


def _diff_columns(
    exp_items: Sequence[str], got_items: Sequence[str]
) -> Tuple[List[str], List[str]]:
    """difflib.ndiff() over two same-kind sequences (list elements or text
    lines), reshaped into a pair of line-aligned display lists — one line
    per ndiff entry, "  "-prefixed where both sides agree, "- " only on
    the expected side, "+ " only on the got side. "? " hint lines (ndiff's
    own caret/marker lines) are dropped — useful in a unified terminal
    diff, redundant once expected/got are already shown as separate
    columns/blocks."""
    lines = [
        ln
        for ln in difflib.ndiff(exp_items, got_items)
        if not ln.startswith("? ")
    ]
    exp_out: List[str] = []
    got_out: List[str] = []
    for ln in lines:
        tag, content = ln[:2], ln[2:]
        if tag == "  ":
            exp_out.append("  " + content)
            got_out.append("  " + content)
        elif tag == "- ":
            exp_out.append("- " + content)
        elif tag == "+ ":
            got_out.append("+ " + content)
    return exp_out, got_out


def structural_diff(
    expected: object, exp_text: str, got_text: str
) -> Optional[Tuple[List[str], List[str]]]:
    """Element-by-element diff for a --diff structural block, used when
    `expected` is a list/tuple (a Failure only — a CFailure's expected/got
    are always plain strings, see line_diff() below) whose repr splits
    into more than one top-level element. `exp_text`/`got_text` are the
    same displayed strings first_diff_index() compares (repr(expected),
    str(got)) — got is already text by the time it reaches here (it went
    through the sandbox's own repr(), see grader.short_repr()), so this
    diffs the two TEXTS' top-level-comma-split pieces rather than round-
    tripping got_text back into a native value (which would need an
    eval() and can't work anyway once short_repr() has truncated it).

    Returns (expected_lines, got_lines) — see _diff_columns() — or None
    when `expected` isn't a list/tuple, or splits into 0-1 elements (as
    short as the char-pointer already handles fine)."""
    if not isinstance(expected, (list, tuple)):
        return None
    exp_items = _split_top_level(_strip_outer_brackets(exp_text))
    got_items = _split_top_level(_strip_outer_brackets(got_text))
    if len(exp_items) <= 1:
        return None
    return _diff_columns(exp_items, got_items)


def line_diff(
    exp_text: str, got_text: str
) -> Optional[Tuple[List[str], List[str]]]:
    """Line-by-line diff for a multi-line --diff value — a C failure's
    multi-line stdout chunk, most often, but works for any multi-line
    string. Returns (expected_lines, got_lines) — see _diff_columns() —
    or None when neither side has more than one line (a single-line value
    is exactly what the char-pointer already handles well)."""
    if "\n" not in exp_text and "\n" not in got_text:
        return None
    return _diff_columns(exp_text.splitlines(), got_text.splitlines())


def _diff_block(
    f: FailureLike, exp_text: str, got_text: str
) -> Optional[Tuple[List[str], List[str]]]:
    """The one entry point _failures() needs: structural_diff() first (more
    specific — an element, not just a line, is what actually differs in a
    list/tuple), then line_diff(), or None to fall back to the plain
    char-pointer.

    line_diff() needs REAL newlines to split on, and exp_text/got_text
    aren't a matched pair for that: exp_text is always repr(f.expected) —
    matching what structural_diff() and the scalar char-pointer view need
    — which escapes any real newline in a Python Failure's expected value
    into the two characters "\\" + "n". A CFailure's expected/got, though,
    are already plain, un-repr()'d strings (see c_exam/grader.py's
    CFailure docstring) — got_text (str(f.got)) is already raw there, so
    feeding it repr(f.expected) instead of the equally-raw f.expected
    would compare an escaped string against a real multi-line one and
    never line up. Detected via `.index` (CFailure-only, see its
    __slots__) rather than an isinstance check, so this module doesn't
    need to import c_exam.grader just to tell the two failure types apart.
    """
    block = structural_diff(f.expected, exp_text, got_text)
    if block:
        return block
    if hasattr(f, "index"):  # CFailure: its own strings are already raw
        return line_diff(str(f.expected), str(f.got))
    return line_diff(exp_text, got_text)


# Diff blocks are capped the same way _DIFF_CLIP caps a plain value below —
# a legitimate multi-hundred-line C program's stdout, or a huge fuzzed
# list, must never be able to flood the terminal.
_DIFF_BLOCK_MAX_LINES = 30


def _clip_block(lines: List[str]) -> Tuple[List[str], int]:
    if len(lines) <= _DIFF_BLOCK_MAX_LINES:
        return lines, 0
    return lines[:_DIFF_BLOCK_MAX_LINES], len(lines) - _DIFF_BLOCK_MAX_LINES


def report(
    rep: Report,
    show_fails: int = 4,
    diff: bool = False,
    filepath: Optional[str] = None,
) -> None:
    """Render a grader.Report. `filepath` is the exact file that was
    graded (see both examshell.py's grade_exercise()) — used only when
    `diff` is set, to show the student's own submitted function next to
    its failures (see _code_panel())."""
    for msg in rep.warnings:
        warn(msg)
    if rep.fatal:
        box_message(rep.fatal_title, rep.detail, style="red")
        return
    if rep.failures:
        _failures(rep, show_fails, diff, filepath)
    _verdict(rep)


# --diff shows the full value (instead of the usual 70/26-char clip) plus
# a pointer at the first differing character — clipped only at this much
# higher cap, so an absurdly long value still can't flood the terminal.
_DIFF_CLIP = 400


def _failure_texts(f: FailureLike) -> Tuple[str, str]:
    """(expected, got) as shown in a report. A Python Failure's got is
    already the sandbox's repr text. A CFailure's values are both RAW
    stdout, so repr() both sides — an invisible tab or trailing space then
    shows up, and --diff's pointer indexes the same text on both lines.
    The grader's own bracketed markers ("[TIMEOUT]", "[no output …]")
    stay as they are."""
    exp_text, got_text = repr(f.expected), str(f.got)
    if hasattr(f, "index") and not (
        got_text.startswith("[") and got_text.endswith("]")
    ):
        got_text = repr(got_text)
    return exp_text, got_text


def _call_text(f: FailureLike, function: str) -> Tuple[str, str]:
    """The failing call, plus the edge case its input represents (see
    examshell/case_labels.py) when there is one worth naming."""
    from . import case_labels

    label = case_labels.describe(f)
    return f.call(function), label


def _failures(
    rep: Report,
    show_fails: int,
    diff: bool = False,
    filepath: Optional[str] = None,
) -> None:
    shown = rep.failures[:show_fails]
    if diff and shown and filepath:
        source = _extract_source(filepath, rep.function)
        if source:
            _code_panel(source, rep.function, filepath)
    if _rich:
        t = Table(
            box=box.SIMPLE_HEAVY,
            show_edge=False,
            pad_edge=False,
            header_style="bold red",
        )
        t.add_column(
            "failing call", style="white", max_width=46, overflow="fold"
        )
        t.add_column("expected", style="green", max_width=26, overflow="fold")
        t.add_column("got", style="red", max_width=26, overflow="fold")
        for f in shown:
            exp_text, got_text = _failure_texts(f)
            call, label = _call_text(f, rep.function)
            call_cell = _esc(call) + (
                "\n[yellow]⟨%s⟩[/yellow]" % _esc(label) if label else ""
            )
            if diff:
                block = _diff_block(f, exp_text, got_text)
                if block:
                    exp_lines, got_lines = block
                    exp_lines, exp_more = _clip_block(exp_lines)
                    got_lines, got_more = _clip_block(got_lines)
                    exp_shown = "\n".join(exp_lines) + (
                        "\n… +%d more" % exp_more if exp_more else ""
                    )
                    got_shown = "\n".join(got_lines) + (
                        "\n… +%d more" % got_more if got_more else ""
                    )
                    t.add_row(call_cell, _esc(exp_shown), _esc(got_shown))
                else:
                    idx = first_diff_index(exp_text, got_text)
                    t.add_row(
                        call_cell,
                        _diff_markup(exp_text, idx),
                        _diff_markup(got_text, idx),
                    )
            else:
                t.add_row(call_cell, _esc(exp_text), _esc(got_text))
        _out().print(t)
    else:
        hang = IND0 + " " * len(
            "[KO] "
        )  # aligns under the text, like box_message
        for f in shown:
            call, label = _call_text(f, rep.function)
            print(IND0 + c("[KO] " + call[:90], "RED"))
            if label:
                print(hang + c("edge case: " + label, "YELLOW"))
            exp_text, got_text = _failure_texts(f)
            if diff:
                block = _diff_block(f, exp_text, got_text)
                if block:
                    exp_lines, got_lines = block
                    exp_lines, exp_more = _clip_block(exp_lines)
                    got_lines, got_more = _clip_block(got_lines)
                    print(hang + c("expected :", "GRAY"))
                    for line in exp_lines:
                        print(hang + "  " + c(line, "GRAY"))
                    if exp_more:
                        print(hang + "  " + c("… +%d more" % exp_more, "GRAY"))
                    print(hang + c("got      :", "GRAY"))
                    for line in got_lines:
                        print(hang + "  " + c(line, "GRAY"))
                    if got_more:
                        print(hang + "  " + c("… +%d more" % got_more, "GRAY"))
                else:
                    idx = first_diff_index(exp_text, got_text)
                    print(
                        hang + c("expected : " + exp_text[:_DIFF_CLIP], "GRAY")
                    )
                    print(
                        hang + c("got      : " + got_text[:_DIFF_CLIP], "GRAY")
                    )
                    if idx is not None and idx < _DIFF_CLIP:
                        print(
                            hang
                            + " " * (len("got      : ") + idx)
                            + c("^", "RED")
                        )
            else:
                print(hang + c("expected : " + exp_text[:70], "GRAY"))
                print(hang + c("got      : " + got_text[:70], "GRAY"))
    rest = len(rep.failures) - len(shown)
    if rest > 0:
        note("… and %d more failing test%s" % (rest, "s" if rest > 1 else ""))


def _extract_source(filepath: str, function_name: str) -> Optional[str]:
    """Best-effort source lookup for --diff's inline code panel — Python
    files use examshell.grader's ast-based extractor, C files use
    c_exam.grader's brace-matching one. Imported lazily (not at module
    load) so this presentation module doesn't hard-depend on either grading
    backend at import time. Never raises — both extractors already return
    None on any failure of their own, and an unexpected import error here is
    caught too, since this is purely cosmetic and must never crash
    grading."""
    try:
        if filepath.endswith(".c"):
            from c_exam import grader as _c_grader

            return _c_grader.extract_function_source(filepath, function_name)
        from . import grader as _py_grader

        return _py_grader.extract_function_source(filepath, function_name)
    except Exception:
        return None


def _code_panel(source: str, function_name: str, filepath: str) -> None:
    """--diff's inline code panel: the student's own submitted function,
    syntax-highlighted, shown once per report (not once per failure, see
    _failures() above) so they can see it next to the mismatch without
    alt-tabbing to their editor. This is not a hint or a crutch (contrast
    hints.py's stuck-student nudges, deliberately suppressed during --exam
    — see that module's docstring): it's just the student's own code, which
    they already have open in their editor, so this runs during --exam
    too."""
    lexer = "c" if filepath.endswith(".c") else "python"
    title = "your %s()" % function_name
    if _rich:
        syntax = Syntax(
            source,
            lexer,
            theme="ansi_dark",
            line_numbers=True,
            background_color="default",
            word_wrap=True,
        )
        _out().print(
            Panel(
                syntax,
                title="[dim]%s[/dim]" % _esc(title),
                title_align="left",
                border_style="grey37",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        return
    header = "── " + title + " "
    print(
        IND0
        + c(header + "─" * max(0, width() - len(header) - len(IND0)), "GRAY")
    )
    for line in source.splitlines():
        print(IND1 + c(line, "GRAY"))
    print(IND0 + c("─" * width(), "GRAY"))


def _diff_markup(text: str, idx: Optional[int]) -> str:
    """`text`, rich-escaped, with everything from `idx` onward reverse-
    styled — the rich-table equivalent of the plain path's "^" pointer
    line (a caret can't be reliably column-aligned inside a wrapping,
    padded table cell, so highlighting the diverging tail is the more
    robust choice for that renderer)."""
    text = text[:_DIFF_CLIP]
    if idx is None or idx >= len(text):
        return _esc(text)
    return _esc(text[:idx]) + "[reverse]" + _esc(text[idx:]) + "[/reverse]"


def _verdict(rep: Report) -> None:
    ratio = "%d/%d" % (rep.passed, rep.total)
    pct = int(rep.passed / rep.total * 100) if rep.total else 0
    bar = _bar(rep.passed, rep.total)
    ok = rep.ok
    mark = "✔" if ok else "✖"
    label = "%s  %s  %s tests passed  %3d%%" % (mark, bar, ratio, pct)
    if _rich:
        _out().print(
            Panel(
                Align.center(Text(label, style="bold white")),
                style="on green" if ok else "on red",
                box=box.HEAVY,
                padding=(0, 2),
            )
        )
        return
    print()
    print(c("  %s  " % label, "BG_GREEN" if ok else "BG_RED", "WHITE", "BOLD"))


def level_cleared(level: int) -> None:
    if _rich:
        _out().print(
            Panel(
                Align.center(
                    Text("✔  Level %d cleared!" % level, style="bold green")
                ),
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        print()
        print(IND0 + c("✔ Level %d cleared!" % level, "GREEN", "BOLD"))


def summary(
    title: str, rows: Sequence[Tuple[str, object]], passed: bool = True
) -> None:
    """rows: [(label, value), …]"""
    style = "green" if passed else "yellow"
    if _rich:
        t = Table.grid(padding=(0, 2))
        t.add_column(style="cyan", justify="right")
        t.add_column(style="bold white")
        for label, value in rows:
            t.add_row(label, str(value))
        _out().print(
            Panel(
                Group(
                    Align.center(Text(title, style="bold white")),
                    Rule(style=style),
                    t,
                ),
                border_style=style,
                box=box.DOUBLE,
                padding=(1, 3),
            )
        )
        return
    print()
    print(
        c(
            "  " + title + "  ",
            "BG_GREEN" if passed else "BG_RED",
            "WHITE",
            "BOLD",
        )
    )
    print()
    for label, value in rows:
        print(IND0 + c(label.rjust(12) + " : ", "CYAN") + str(value))
    print()


configure()
