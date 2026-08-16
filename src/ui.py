#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui.py  ·  presentation layer for ExamShell (42 · Exam Rank 03 · Python)

Every byte the student sees goes through this module, so the rest of the
code never has to branch on which backend is active:

    rich   -> panels, tables, syntax highlighting     (pip install rich)
    ANSI   -> plain coloured text, runs anywhere      (exam machines)

Colour is turned off automatically when stdout is not a TTY, when TERM is
"dumb", or when NO_COLOR is set (https://no-color.org).
"""

import os
import shutil
import sys

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
except ImportError:                                        # pragma: no cover
    HAVE_RICH = False

    def _rich_escape(text):
        return text


class Abort(Exception):
    """Raised by ask() when the student hits Ctrl-C / Ctrl-D."""


# ══════════════════════════════════════════════════════════════
#  BACKEND STATE
# ══════════════════════════════════════════════════════════════
_rich = False
_color = True
_console = None


def _auto_color():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return sys.stdout.isatty()


def configure(rich=None, color=None):
    """(Re)configure the backend. None means 'auto-detect'."""
    global _rich, _color, _console
    _color = _auto_color() if color is None else bool(color)
    want_rich = HAVE_RICH if rich is None else (bool(rich) and HAVE_RICH)
    _rich = want_rich and _color
    _console = Console(highlight=False) if _rich else None


def using_rich():
    return _rich


def width():
    return min(shutil.get_terminal_size((80, 24)).columns, 78)


class C:
    """ANSI escapes; every attribute is "" when colour is disabled."""
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; MAGENTA = "\033[95m"; CYAN = "\033[96m"
    WHITE = "\033[97m"; GRAY = "\033[90m"
    BG_RED = "\033[41m"; BG_GREEN = "\033[42m"


def c(text, *styles):
    """Wrap `text` in ANSI styles (no-op when colour is off)."""
    if not _color or not styles:
        return text
    return "".join(getattr(C, s) for s in styles) + text + C.RESET


# ══════════════════════════════════════════════════════════════
#  PRIMITIVES
# ══════════════════════════════════════════════════════════════
def clear():
    if not sys.stdout.isatty():
        return
    os.system("cls" if os.name == "nt" else "clear")


def ask(label):
    """Prompt for a line of input. Ctrl-C / Ctrl-D raise Abort."""
    try:
        if _rich:
            return _console.input("[bold cyan]%s[/bold cyan]" % _esc(label)).strip()
        return input(c(label, "BOLD", "CYAN")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Abort()


def pause(label="  Press Enter to continue…"):
    try:
        if _rich:
            _console.input("[dim]%s[/dim]" % _esc(label))
        else:
            input(c(label, "GRAY"))
    except (EOFError, KeyboardInterrupt):
        print()
        raise Abort()


def info(msg):
    _line(msg, "cyan", "CYAN")


def note(msg):
    _line(msg, "dim", "GRAY")


def warn(msg):
    _line("⚠  " + msg, "yellow", "YELLOW")


def error(msg):
    _line("✖  " + msg, "bold red", "RED", "BOLD")


def success(msg):
    _line("✔  " + msg, "bold green", "GREEN", "BOLD")


def _line(msg, rich_style, *ansi):
    if _rich:
        _console.print("  [%s]%s[/%s]" % (rich_style, _esc(msg), rich_style))
    else:
        print("  " + c(msg, *ansi))


def _esc(text):
    """Escape rich markup.

    Anything that is not a hand-written style tag must go through this:
    prompts like "[user@exam · lvl1]$", menu keys like "[q]" and student
    output like "[1, 2]" are all valid rich markup otherwise, and rich
    silently swallows them.
    """
    return _rich_escape(str(text))


def box_message(title, detail="", style="red"):
    """A framed one-liner, used for grading errors."""
    if _rich:
        body = Text(title, style="bold %s" % style)
        if detail:
            body.append("\n" + detail, style="dim")
        _console.print(Panel(body, border_style=style, box=box.ROUNDED,
                             padding=(0, 2)))
    else:
        colour = {"red": "RED", "green": "GREEN", "yellow": "YELLOW"}.get(style, "CYAN")
        print("  " + c("[KO] " + title, colour, "BOLD"))
        if detail:
            print("       " + c(detail, "GRAY"))


# ══════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════
def banner():
    if _rich:
        title = Text()
        title.append("EXAMSHELL", style="bold white")
        title.append("  ·  Exam Rank 03  ·  Common Core", style="cyan")
        sub = Text("42 School  ·  Python Edition", style="dim")
        _console.print(Panel(Align.center(Text.assemble(title, "\n", sub)),
                             box=box.DOUBLE, border_style="cyan", padding=(0, 2)))
        return
    w = width()
    inner = w - 2
    print(c("╔" + "═" * inner + "╗", "CYAN"))
    for text, styles in (("EXAMSHELL · Exam Rank 03 · Common Core", ("BOLD", "WHITE")),
                         ("42 School · Python Edition", ("GRAY",))):
        pad = inner - len(text)
        left = pad // 2
        print(c("║", "CYAN") + " " * left + c(text, *styles)
              + " " * (pad - left) + c("║", "CYAN"))
    print(c("╚" + "═" * inner + "╝", "CYAN"))


def status_bar(s, n_levels):
    """s is a Session (login / level / elapsed() / score() / passed)."""
    level = min(s.level, n_levels)
    if _rich:
        grid = Table.grid(expand=True, padding=(0, 2))
        for _ in range(4):
            grid.add_column(justify="left")
        grid.add_row(
            Text.assemble(("LOGIN ", "cyan"), (s.login, "bold white")),
            Text.assemble(("LEVEL ", "cyan"), ("%d/%d" % (level, n_levels), "bold yellow")),
            Text.assemble(("TIME ", "cyan"), (s.elapsed(), "white")),
            Text.assemble(("SCORE ", "cyan"), ("%d/100" % s.score(), "bold green")),
        )
        dots = Text()
        for lvl in range(1, n_levels + 1):
            if lvl < s.level:
                dots.append("● ", style="green")
            elif lvl == s.level:
                dots.append("◆ ", style="bold yellow")
            else:
                dots.append("○ ", style="dim")
        _console.print(Panel(Group(grid, dots), border_style="cyan",
                             box=box.SQUARE, padding=(0, 1)))
        return
    bar = "═" * width()
    print(c(bar, "CYAN"))
    print("  " + c("LOGIN: ", "CYAN") + c(s.login.ljust(12), "BOLD", "WHITE")
          + c("LEVEL: ", "CYAN") + c(("%d/%d" % (level, n_levels)).ljust(6), "YELLOW")
          + c("TIME: ", "CYAN") + c(s.elapsed(), "WHITE"))
    print("  " + c("SCORE: ", "CYAN") + c(("%d/100" % s.score()).ljust(12), "BOLD", "GREEN")
          + c("PASSED: ", "CYAN") + c("%d/%d" % (len(s.passed), n_levels), "GREEN"))
    dots = " ".join("●" if l < s.level else "◆" if l == s.level else "○"
                    for l in range(1, n_levels + 1))
    print("  " + c(dots, "YELLOW"))
    print(c(bar, "CYAN"))


def _split_subject(subject):
    """Split a subject into (header rows, prose, signature, examples)."""
    header, prose, examples, signature = [], [], [], None
    in_examples = False
    for line in subject.splitlines():
        if line.startswith(("Assignment", "Expected", "Allowed")):
            header.append(line)
        elif line and set(line) == {"-"}:
            continue
        elif line.strip().startswith("def "):
            signature = line.strip()
        elif line.strip().lower().startswith("example"):
            in_examples = True
        elif in_examples or "->" in line:
            examples.append(line)
        else:
            prose.append(line)
    return header, "\n".join(prose).strip("\n"), signature, \
        "\n".join(examples).strip("\n")


def subject(ex_name, ex, rendu_dir):
    header, prose, signature, examples = _split_subject(ex["subject"])
    if _rich:
        meta = Table.grid(padding=(0, 1))
        meta.add_column(style="cyan", justify="right")
        meta.add_column(style="white")
        for row in header:
            key, _, value = row.partition(":")
            meta.add_row(key.strip(), value.strip())
        blocks = [meta, Rule(style="grey37")]
        prose = "\n".join(l for l in prose.splitlines() if l.strip())
        if prose:
            blocks.append(Text(prose, style="white"))
        if signature:
            blocks.append(Syntax(signature, "python", theme="monokai",
                                 background_color="default"))
        if examples.strip():
            blocks.append(Syntax(examples, "python", theme="monokai",
                                 background_color="default", word_wrap=True))
        _console.print(Panel(
            Group(*blocks),
            title="[bold yellow]📄 %s[/bold yellow]" % _esc(ex_name),
            subtitle="[dim]Level %d  ·  file: %s[/dim]" % (
                ex["level"], _esc(os.path.join(rendu_dir, ex_name + ".py"))),
            border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
        print()
        return

    print()
    print("  " + c("📄 " + ex_name, "BOLD", "YELLOW")
          + c("   (Level %d)" % ex["level"], "GRAY"))
    print("  " + c("─" * (width() - 2), "GRAY"))
    for line in ex["subject"].splitlines():
        if line.startswith(("Assignment", "Expected", "Allowed")):
            print("  " + c(line, "CYAN"))
        elif line and set(line) == {"-"}:
            print("  " + c("─" * (width() - 4), "GRAY"))
        elif "->" in line:
            head, _, tail = line.partition("->")
            print("  " + c(head, "WHITE") + c("->", "GREEN") + c(tail, "YELLOW"))
        elif line.strip().startswith("def "):
            print("  " + c(line, "MAGENTA"))
        else:
            print("  " + line)
    print("  " + c("─" * (width() - 2), "GRAY"))
    print("  " + c("Create file:  %s/%s.py" % (rendu_dir, ex_name), "GRAY"))
    print()


def commands(rows):
    """rows: [(command, description), …]"""
    if _rich:
        t = Table(box=box.MINIMAL, show_header=False, pad_edge=False)
        t.add_column(style="bold cyan", no_wrap=True)
        t.add_column(style="dim")
        for cmd, desc in rows:
            t.add_row(_esc(cmd), _esc(desc))
        _console.print(t)
        return
    print("  " + c("Commands:", "CYAN"))
    for cmd, desc in rows:
        print("    " + c(cmd.ljust(9), "BOLD", "CYAN") + c("- " + desc, "GRAY"))


def menu(rows):
    """rows: [(key, label, hint), …]"""
    if _rich:
        t = Table(box=box.MINIMAL, show_header=False, pad_edge=False)
        t.add_column(style="bold white", no_wrap=True)
        t.add_column()
        for key, label, hint in rows:
            t.add_row(_esc("[%s]" % key),
                      "%s  [dim]%s[/dim]" % (_esc(label), _esc(hint)))
        _console.print(t)
        return
    for key, label, hint in rows:
        print("  " + c("[%s] " % key, "WHITE", "BOLD") + label.ljust(20)
              + c(hint, "GRAY"))


def exercise_table(entries, numbered=False):
    """entries: [(index, level, name, function), …]"""
    if _rich:
        t = Table(title="[bold]Exercise pool[/bold]  (one per level in the exam)",
                  box=box.SIMPLE_HEAVY, header_style="bold cyan")
        t.add_column("#", justify="right", style="dim")
        t.add_column("Level", justify="center", style="yellow")
        t.add_column("Exercise", style="white")
        t.add_column("Function", style="green")
        for idx, lvl, name, func in entries:
            t.add_row(str(idx) if numbered else "", str(lvl),
                      _esc(name), _esc(func + "()"))
        _console.print(t)
        return
    last = None
    for idx, lvl, name, func in entries:
        if lvl != last:
            print("  " + c("Level %d:" % lvl, "YELLOW"))
            last = lvl
        prefix = ("[%d] " % idx) if numbered else ""
        print("    " + c(prefix, "GRAY") + c(name.ljust(32), "WHITE")
              + c(func + "()", "GRAY"))


# ══════════════════════════════════════════════════════════════
#  GRADING OUTPUT
# ══════════════════════════════════════════════════════════════
def report(rep, show_fails=4):
    """Render a grader.Report."""
    for msg in rep.warnings:
        warn(msg)
    if rep.fatal:
        box_message(rep.fatal_title, rep.detail, style="red")
        return
    if rep.failures:
        _failures(rep, show_fails)
    _verdict(rep)


def _failures(rep, show_fails):
    shown = rep.failures[:show_fails]
    if _rich:
        t = Table(box=box.SIMPLE_HEAVY, show_edge=False, pad_edge=False,
                  header_style="bold red")
        t.add_column("failing call", style="white", max_width=46, overflow="fold")
        t.add_column("expected", style="green", max_width=26, overflow="fold")
        t.add_column("got", style="red", max_width=26, overflow="fold")
        for f in shown:
            t.add_row(_esc(f.call(rep.function)), _esc(repr(f.expected)), _esc(f.got))
        _console.print(t)
    else:
        for f in shown:
            print("    " + c("[KO] " + f.call(rep.function)[:90], "RED"))
            print("          " + c("expected : " + repr(f.expected)[:70], "GRAY"))
            print("          " + c("got      : " + str(f.got)[:70], "GRAY"))
    rest = len(rep.failures) - len(shown)
    if rest > 0:
        note("… and %d more failing test%s" % (rest, "s" if rest > 1 else ""))


def _verdict(rep):
    ratio = "%d/%d" % (rep.passed, rep.total)
    ok = rep.ok
    label = "OK   %s tests passed" % ratio if ok else "KO   %s tests passed" % ratio
    if _rich:
        _console.print(Panel(Align.center(Text(label, style="bold white")),
                             style="on green" if ok else "on red",
                             box=box.HEAVY, padding=(0, 2)))
        return
    print()
    print(c("  %s  %s tests passed  " % ("OK" if ok else "KO", ratio),
            "BG_GREEN" if ok else "BG_RED", "WHITE", "BOLD"))


def level_cleared(level):
    if _rich:
        _console.print(Panel(Align.center(
            Text("✔  Level %d cleared!" % level, style="bold green")),
            border_style="green", box=box.ROUNDED))
    else:
        print()
        print("  " + c("✔ Level %d cleared!" % level, "GREEN", "BOLD"))


def summary(title, rows, passed=True):
    """rows: [(label, value), …]"""
    style = "green" if passed else "yellow"
    if _rich:
        t = Table.grid(padding=(0, 2))
        t.add_column(style="cyan", justify="right")
        t.add_column(style="bold white")
        for label, value in rows:
            t.add_row(label, str(value))
        _console.print(Panel(
            Group(Align.center(Text(title, style="bold white")),
                  Rule(style=style), t),
            border_style=style, box=box.DOUBLE, padding=(1, 3)))
        return
    print()
    print(c("  " + title + "  ", "BG_GREEN" if passed else "BG_RED", "WHITE", "BOLD"))
    print()
    for label, value in rows:
        print("  " + c(label.rjust(12) + " : ", "CYAN") + str(value))
    print()


configure()
