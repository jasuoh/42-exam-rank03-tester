#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py  ·  rich renderables for the full-screen UI

Pure functions from engine data (Reports, sessions, stats) to rich
objects — no Textual in here, so all of it is unit-testable with rich
alone. The app (app.py) only decides where each one goes on screen.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Sequence,
    Tuple,
)

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import case_labels, ui
from .._types import Event

if TYPE_CHECKING:
    from ..grader import Report
    from ..shell_common import ExamResult, Session

OK, KO, TODO = "green", "red", "grey50"
SPARKS = "▁▂▃▄▅▆▇█"


def bar(done: float, total: float, width: int = 20, style: str = OK) -> Text:
    """A thin progress bar as Text — coloured part done, dim part to go."""
    filled = int(round(width * done / float(total))) if total else 0
    text = Text("━" * filled, style=style)
    text.append("━" * (width - filled), style="grey30")
    return text


def percent(done: float, total: float) -> int:
    return int(round(100.0 * done / total)) if total else 0


# ── grading ──────────────────────────────────────────────────────────
def report_view(
    report: Report, function: str, show_fails: int = 6, blind: bool = False
) -> Group:
    """A graded Report: verdict bar first (what you look at), then fatal
    error / failing cases / warnings."""
    blocks: List[RenderableType] = []
    ok = report.ok
    verdict = Text()
    verdict.append(
        " ✔ PASSED " if ok else " ✖ FAILED ",
        style="bold black on green" if ok else "bold white on red",
    )
    verdict.append("  ")
    if report.fatal:
        verdict.append(report.fatal_title, style="bold red")
    else:
        verdict.append_text(
            bar(report.passed, report.total, 24, OK if ok else KO)
        )
        verdict.append(
            "  %d/%d tests  %d%%"
            % (
                report.passed,
                report.total,
                percent(report.passed, report.total),
            ),
            style="bold",
        )
    blocks.append(verdict)

    if report.fatal and report.detail:
        blocks.append(
            Panel(Text(report.detail), border_style="red", box=box.ROUNDED)
        )

    failures = report.failures
    if failures and blind:
        blocks.append(
            Text(
                "\nblind grading — %d failing test%s, inputs hidden "
                "(like the real exam)"
                % (len(failures), "" if len(failures) == 1 else "s"),
                style="italic yellow",
            )
        )
    elif failures:
        blocks.append(Text(""))
        for f in failures[:show_fails]:
            exp_text, got_text = ui._failure_texts(f)
            label = case_labels.describe(f)
            call = Text("✖ ", style="bold red")
            call.append(f.call(function), style="bold")
            blocks.append(call)
            if label:
                blocks.append(Text("   edge case: " + label, style="yellow"))
            grid = Table.grid(padding=(0, 1))
            grid.add_column(style="dim", no_wrap=True)
            grid.add_column(overflow="fold")
            grid.add_row("   expected", Text(exp_text[:400], style="green"))
            grid.add_row("   got", Text(got_text[:400], style="red"))
            blocks.append(grid)
        rest = len(failures) - show_fails
        if rest > 0:
            blocks.append(
                Text(
                    "… and %d more failing test%s"
                    % (rest, "s" if rest > 1 else ""),
                    style="dim",
                )
            )
    for warning in report.warnings:
        blocks.append(Text("\n⚠ " + warning, style="yellow"))
    if report.duration:
        blocks.append(Text("\ngraded in %.1fs" % report.duration, style="dim"))
    return Group(*blocks)


def compact_report_view(
    report: Report, function: str, show: int = 3, hint: str = ""
) -> Group:
    """Practice: what you need at a glance — one verdict line, the first
    `show` failing tests one line each (input, got ≠ expected), warnings
    and the hint. report_view() has the full details (`d`)."""
    ok = report.ok
    lines: List[RenderableType] = []
    verdict = Text(
        "✔ PASSED" if ok else "✖ FAILED", style="bold " + (OK if ok else KO)
    )
    if report.fatal:
        verdict.append("  " + report.fatal_title, style="bold")
    elif report.total:
        verdict.append("  %d/%d" % (report.passed, report.total), style="bold")
    if report.duration:
        verdict.append("  ·  %.1fs" % report.duration, style="dim")
    lines.append(verdict)
    if report.fatal and report.detail:
        detail = report.detail.strip().splitlines()
        lines.append(Text("\n".join(detail[:6]), style=KO))
        if len(detail) > 6:
            lines.append(Text("… d for the full error", style="dim"))
    for f in report.failures[:show]:
        exp_text, got_text = ui._failure_texts(f)
        row = Text(no_wrap=True, overflow="ellipsis")
        row.append("✖ ", style=KO)
        row.append(f.call(function), style="bold")
        label = case_labels.describe(f)
        if label:
            row.append("  (%s)" % label, style="yellow")
        row.append("  got ", style="dim")
        row.append(got_text[:120], style=KO)
        row.append(" ≠ ", style="dim")
        row.append(exp_text[:120], style=OK)
        lines.append(row)
    rest = len(report.failures) - show
    if rest > 0:
        lines.append(Text("… %d more · d for details" % rest, style="dim"))
    for warning in report.warnings:
        lines.append(Text("⚠ " + warning, style="yellow"))
    if hint:
        lines.append(Text("hint: " + hint, style="yellow"))
    return Group(*lines)


def exam_trace_view(
    report: Report, function: str, blind: bool = False
) -> Group:
    """The exam's grademe, like the real one: SUCCESS or FAILURE, and on a
    FAILURE a trace of the first failing test — nothing more."""
    if report.ok:
        return Group(Text("SUCCESS", style="bold " + OK))
    lines: List[RenderableType] = [Text("FAILURE", style="bold " + KO)]
    if blind:
        return Group(*lines)
    lines.append(Text(""))
    if report.fatal:
        lines.append(Text(report.fatal_title, style="bold"))
        if report.detail:
            detail = report.detail.strip().splitlines()
            lines.append(Text("\n".join(detail[:12]), style=KO))
        return Group(*lines)
    if report.failures:
        f = report.failures[0]
        exp_text, got_text = ui._failure_texts(f)
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="dim", no_wrap=True)
        grid.add_column(overflow="fold")
        grid.add_row("test", Text(f.call(function), style="bold"))
        grid.add_row("expected", Text(exp_text[:400], style=OK))
        grid.add_row("got", Text(got_text[:400], style=KO))
        lines.append(grid)
    return Group(*lines)


def hint_view(hint: str) -> Panel:
    return Panel(
        Text(hint), title="💡 hint", border_style="yellow", box=box.ROUNDED
    )


def waiting_view(message: str) -> Text:
    return Text(message, style="dim italic")


# ── exam ─────────────────────────────────────────────────────────────
def stepper(session: Session, n_levels: int) -> Text:
    """● cleared · ◉ current · ○ ahead."""
    text = Text()
    for level in range(1, n_levels + 1):
        if level < session.level:
            text.append("● ", style=OK)
        elif level == session.level:
            text.append("◉ ", style="bold yellow")
        else:
            text.append("○ ", style=TODO)
    return text


def exam_status(
    session: Session, n_levels: int, countdown: str = "", attempts: int = 0
) -> Text:
    text = Text()
    text.append(" %s " % session.login, style="bold reverse")
    text.append(
        "  Level %d/%d  " % (min(session.level, n_levels), n_levels),
        style="bold",
    )
    text.append_text(stepper(session, n_levels))
    text.append("  attempts on this level: %d" % attempts, style="dim")
    if countdown:
        text.append(
            "   ⏱%s" % countdown.replace(" · ", " "), style="bold magenta"
        )
    return text


def exam_result_view(result: ExamResult) -> Group:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", justify="right")
    table.add_column()
    for key, value in result.rows:
        table.add_row(str(key), str(value))
    blocks: List[RenderableType] = [
        Text(
            result.title, style="bold green" if result.passed else "bold red"
        ),
        Text(""),
        table,
    ]
    if result.report_path:
        blocks += [
            Text(""),
            Text("report saved to %s" % result.report_path, style="dim"),
        ]
    return Group(*blocks)


# ── readiness · stats ────────────────────────────────────────────────
def readiness_view(
    levels: Sequence[Tuple[int, int, int, List[Tuple[str, Dict[str, Any]]]]],
) -> Group:
    """levels as returned by stats.readiness(): one row of chips per level
    — green passed, red tried-but-never-passed, grey never tried."""
    blocks: List[RenderableType] = []
    done = sum(p for _, p, _, _ in levels)
    total = sum(t for _, _, t, _ in levels)
    head = Text("Overall  ", style="bold")
    head.append_text(bar(done, total, 30))
    head.append(
        "  %d/%d  %d%%" % (done, total, percent(done, total)), style="bold"
    )
    blocks += [head, Text("")]
    for level, passed, count, entries in levels:
        line = Text("Level %d  " % level, style="bold yellow")
        line.append_text(bar(passed, count, 12))
        line.append("  %d/%d\n" % (passed, count), style="dim")
        for name, row in entries:
            line.append_text(chip(name, row["status"]))
            line.append(" ")
        blocks += [line, Text("")]
    legend = Text()
    for status, label in (
        ("passed", "passed"),
        ("failed", "tried, never passed"),
        ("untried", "never tried"),
    ):
        legend.append_text(chip(label, status))
        legend.append("  ")
    blocks.append(legend)
    return Group(*blocks)


CHIP_COLOURS = {
    "passed": ("green", "bold black"),
    "failed": ("red", "bold white"),
    "untried": ("grey23", "white"),
}


def chip(label: str, status: str) -> Text:
    """A pill-shaped label — half-blocks instead of padding spaces, so a
    line of chips only ever wraps BETWEEN chips, never inside one."""
    colour, fg = CHIP_COLOURS[status]
    text = Text("▐", style=colour)
    text.append(label, style="%s on %s" % (fg, colour))
    text.append("▌", style=colour)
    return text


def sparkline(values: Sequence[float]) -> Text:
    """One block character per value, scaled to the largest."""
    top = max(values) if values else 0
    if not top:
        return Text(SPARKS[0] * len(values), style=TODO)
    text = Text()
    for v in values:
        idx = int(round((len(SPARKS) - 1) * v / float(top)))
        text.append(SPARKS[idx], style=OK if v else TODO)
    return text


def stats_overview(
    summary: Dict[str, Any],
    activity: Sequence[Tuple[int, int]],
    streak: int,
    history: Sequence[Event],
    fmt_duration: Callable[[float], str],
) -> Group:
    """Headline numbers, a 4-week activity chart and the recent exams."""
    head = Table.grid(padding=(0, 3))
    for _ in range(4):
        head.add_column(justify="center")

    def tile(value: object, label: str) -> Text:
        t = Text(str(value), style="bold cyan", justify="center")
        t.append("\n" + label, style="dim")
        return t

    head.add_row(
        tile(summary["total_attempts"], "graded attempts"),
        tile("%d%%" % round(summary["pass_rate"] * 100), "pass rate"),
        tile(
            "%d day%s" % (streak, "" if streak == 1 else "s"),
            "practice streak",
        ),
        tile(
            fmt_duration(summary["best_seconds"])
            if summary["best_seconds"] is not None
            else "—",
            "best exam time",
        ),
    )
    blocks: List[RenderableType] = [head, Text("")]

    chart = Text("last 4 weeks  ", style="bold")
    chart.append_text(sparkline([a for a, _ in activity]))
    chart.append("  %d attempts" % sum(a for a, _ in activity), style="dim")
    blocks.append(chart)

    if history:
        exams = Table(
            title="recent exams",
            box=box.SIMPLE,
            title_style="bold",
            header_style="dim",
            title_justify="left",
        )
        exams.add_column("time")
        exams.add_column("attempts", justify="right")
        exams.add_column("score", justify="right")
        for e in history:
            exams.add_row(
                fmt_duration(e.get("seconds", 0)),
                str(e.get("attempts", "")),
                "%s/100" % e.get("score", ""),
            )
        blocks += [Text(""), exams]
    return Group(*blocks)


def per_exercise_view(summary: Dict[str, Any]) -> RenderableType:
    """Every exercise you've graded, by pass rate (worst first)."""
    if not summary["per_exercise"]:
        return Text(
            "no grading history yet — practice something first",
            style="dim italic",
        )
    per = Table(box=box.SIMPLE, header_style="dim", expand=True)
    per.add_column("exercise")
    per.add_column("pass rate", ratio=1)
    per.add_column("", justify="right")
    rows = sorted(
        summary["per_exercise"].items(),
        key=lambda kv: kv[1]["passes"] / float(kv[1]["attempts"]),
    )
    for name, row in rows:
        rate = row["passes"] / float(row["attempts"])
        style = OK if rate >= 0.8 else "yellow" if rate >= 0.4 else KO
        per.add_row(
            name,
            bar(row["passes"], row["attempts"], 16, style),
            "%d/%d" % (row["passes"], row["attempts"]),
        )
    return per


def attempt_summary(
    entries: Sequence[Tuple[str, str, Report]], exercise: str
) -> str:
    """One line on this session's gradings of `exercise` — how many, and
    how the last one went: "graded 3× · last 14:02:11 ✖ 1/2"."""
    mine = [
        (clock, report) for clock, name, report in entries if name == exercise
    ]
    if not mine:
        return ""
    clock, report = mine[-1]
    if report.ok:
        last = "✔"
    elif report.fatal:
        last = "✖ " + report.fatal_title
    else:
        last = "✖ %d/%d" % (report.passed, report.total)
    return "graded %d× · last %s %s" % (len(mine), clock, last)


def to_text(renderable: RenderableType, width: int, console: Console) -> Text:
    """Flatten any rich renderable into styled Text laid out at `width` —
    same look, but plain text underneath, so it can be selected and
    copied."""
    text = Text(no_wrap=True)
    lines = console.render_lines(
        renderable, console.options.update_width(width), pad=False
    )
    for i, line in enumerate(lines):
        if i:
            text.append("\n")
        for segment in line:
            if not segment.control:
                text.append(segment.text, segment.style)
    return text


def logo(subtitle: str) -> Text:
    """The menu's title block."""
    text = Text(justify="center")
    word = "E X A M S H E L L"
    colours = [
        "#5fd7ff",
        "#5fafff",
        "#8787ff",
        "#af87ff",
        "#d787ff",
        "#ff87d7",
    ]
    for i, ch in enumerate(word):
        text.append(ch, style="bold %s" % colours[(i // 3) % len(colours)])
    text.append("\n" + subtitle, style="dim")
    return text
