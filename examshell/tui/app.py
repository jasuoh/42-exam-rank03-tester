#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py  ·  ExamShell as a full-screen Textual app

Every screen drives the same engine the line-based UI uses —
examshell/shell_common.py's ExamRun / grade() / finish_exam() and the tester
module's hooks (`sh`) — so rules, grading, stats and saves are identical
whichever interface the student picks. This module only lays things out
and turns keys into engine calls; examshell/tui/render.py builds the visuals.

Grading runs in a worker thread (it compiles, runs subprocesses, can take
seconds) and hands its result back to the UI thread.
"""

from __future__ import annotations

import os
import random
import shlex
import shutil
import subprocess
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.selection import Selection
from textual.timer import Timer
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    OptionList,
    Static,
    Tab,
    Tabs,
)
from textual.visual import VisualType
from textual.widgets.option_list import Option
from textual.worker import WorkerFailed

from .. import session_store, settings, shell_common, stats, ui, update_check
from .._types import Event, Tester, TesterConfig
from ..grader import BankError, Report
from ..shell_common import ExamResult, ExamRun, GradeOutcome
from ..sync import SyncResult
from ..version import __version__
from . import clipboard as system_clipboard
from . import crashlog
from . import render

# the terminal's own colours: the app looks like the rest of your terminal
# (your Ghostty / VS Code theme) instead of bringing its own
THEME = "ansi-dark"
SUBJECT_SYNTAX = "ansi_dark"
WATCH_INTERVAL = 1.0  # seconds between solution-file checks


def editor_command(path: str) -> Optional[List[str]]:
    """How to open `path`: VS Code when its `code` command is installed
    (the editor next to the terminal), else $VISUAL / $EDITOR, else None."""
    if shutil.which("code"):
        return ["code", path]
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return shlex.split(editor) + [path]
    return None


# below this many columns, side panels (dashboard, preview) hide
NARROW = 120

# one line of the "this session" log: (clock, exercise, report)
LogEntry = Tuple[str, str, Report]

_ResultT = TypeVar("_ResultT")


class AppScreen(Screen[_ResultT]):
    """A Screen whose `app` is typed as ExamShellApp (Textual types it as
    a plain App) — only narrows the type, the object is the same."""

    @property
    def app(self) -> ExamShellApp:  # type: ignore[override]
        return cast("ExamShellApp", super().app)


class Copyable(Static):
    """A Static whose content can be selected with the mouse and copied
    (ctrl+c). Textual only selects plain text, so tables/panels/syntax
    are flattened to Text at the widget's width, again on every resize."""

    def __init__(self, content: VisualType = "", **kwargs: Any) -> None:
        super().__init__(content, **kwargs)
        self.source: VisualType = content

    def update(self, content: VisualType = "", *, layout: bool = True) -> None:
        self.source = content
        self.refit()

    def on_resize(self) -> None:
        self.refit()

    def get_selection(self, selection: Selection) -> Optional[Tuple[str, str]]:
        """Copied text without the padding that fills code backgrounds."""
        result = super().get_selection(selection)
        if result is None:
            return None
        text, end = result
        return "\n".join(line.rstrip() for line in text.split("\n")), end

    def refit(self) -> None:
        width = self.size.width
        if width and not isinstance(self.source, (str, Text)):
            # only rich renderables are ever put in here
            flat = render.to_text(
                cast(RenderableType, self.source), width, self.app.console
            )
            Static.update(self, flat)
        else:
            Static.update(self, self.source)


# ══════════════════════════════════════════════════════════════
#  SMALL MODALS
# ══════════════════════════════════════════════════════════════
class ConfirmModal(ModalScreen[Optional[bool]]):
    """Yes/no question → dismisses with True/False (Esc → None, so a
    caller can tell "back" from "no")."""

    BINDINGS = [
        Binding("y", "answer(True)", "yes"),
        Binding("n", "answer(False)", "no"),
        Binding("escape", "cancel", "back"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.question, classes="modal-question")
            yield Static(
                "[b]y[/b] yes   ·   [b]n[/b] no", classes="modal-hint"
            )

    def action_answer(self, value: bool) -> None:
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class PromptModal(ModalScreen[Optional[str]]):
    """One line of text → dismisses with the string (Enter on an empty
    line → default, Esc → None)."""

    BINDINGS = [Binding("escape", "cancel", "back")]

    def __init__(self, question: str, default: str = "") -> None:
        super().__init__()
        self.question, self.default = question, default

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.question, classes="modal-question")
            yield Input(placeholder=self.default, id="prompt")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or self.default)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpModal(ModalScreen[None]):
    """`?` — every key, in one place."""

    BINDINGS = [
        Binding("escape", "dismiss", "close"),
        Binding("question_mark", "dismiss", "close", show=False),
        Binding("q", "dismiss", "close", show=False),
    ]

    KEYS = (
        ("Menu", ""),
        ("enter", "open the highlighted entry"),
        ("o", "settings"),
        ("s", "sync with your other device"),
        ("f", "feedback — an exercise that differs from your exam"),
        ("q", "quit"),
        ("Exam and practice", ""),
        ("g", "grademe"),
        ("e", "open your solution in your editor"),
        ("t", "write a stub"),
        ("esc", "back — in the exam: quit and save"),
        ("Practice only", ""),
        ("d", "all the details of the last grade"),
        ("w", "grade every time you save"),
        ("n", "next exercise of My gaps"),
        ("f", "feedback on this exercise"),
        ("Exercise list", ""),
        ("tab", "next tab: Exam exercises · My gaps · Extra"),
        ("/", "filter by name"),
        ("Progress", ""),
        ("p", "practise your gaps"),
    )

    def compose(self) -> ComposeResult:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", no_wrap=True)
        table.add_column()
        for key, text in self.KEYS:
            if text:
                table.add_row(key, text)
            else:
                table.add_row("", "")
                table.add_row(Text(key, style="dim"), "")
        with Vertical(classes="modal"):
            yield Static(table)
            yield Static("esc to close", classes="modal-hint")


class ChoiceModal(ModalScreen[Optional[str]]):
    """Pick one of [(id, label)] → dismisses with the id (or None)."""

    BINDINGS = [Binding("escape", "cancel", "back")]

    def __init__(self, title: str, choices: Sequence[Tuple[str, str]]) -> None:
        super().__init__()
        self.title_text, self.choices = title, choices

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.title_text, classes="modal-question")
            yield OptionList(
                *[Option(label, id=cid) for cid, label in self.choices]
            )

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ══════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════
class MenuScreen(AppScreen[None]):
    BINDINGS = [
        Binding("o", "settings", "settings"),
        Binding("s", "app.sync", "sync"),
        Binding("f", "feedback", "feedback"),
        Binding("q", "app.quit", "quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="menu-body"):
            with Vertical(id="menu-left"):
                yield OptionList(id="menu")
            yield VerticalScroll(Static(id="glance"), id="menu-right")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_menu()
        self.query_one("#menu", OptionList).focus()

    def on_screen_resume(self) -> None:
        self.refresh_menu()

    def refresh_menu(self) -> None:
        sh = self.app.sh
        self.app.sub_title = self.app.label()
        items = [
            ("exam", "Exam", "%d levels, real exam rules" % sh.N_LEVELS),
            ("practice", "Practice", "any exercise, full feedback"),
            (
                "progress",
                "Progress",
                "what you've passed, where your gaps are",
            ),
            ("switch", "Switch exam", "now: %s" % self.app.label()),
            ("quit", "Quit", ""),
        ]
        menu = self.query_one("#menu", OptionList)
        highlighted = menu.highlighted
        menu.clear_options()
        for oid, label, hint in items:
            prompt = "%s\n  [dim]%s[/dim]" % (label, hint) if hint else label
            menu.add_option(Option(prompt, id=oid))
        menu.highlighted = highlighted if highlighted is not None else 0
        self.query_one("#glance", Static).update(self.glance())

    def glance(self) -> RenderableType:
        sh = self.app.sh
        tool = sh.TOOL
        parts: List[RenderableType] = [
            render.stats_overview(
                stats.summarize(tool),
                stats.daily_activity(tool),
                stats.practice_streak(tool),
                [],
                shell_common.fmt_duration,
            ),
            Text(""),
            Text(""),
            render.readiness_view(stats.readiness(tool, sh.STANDARD_LEVELS)),
        ]
        notice = self.app.update_notice.get("notice")
        if notice:
            parts += [Text(""), Text(notice, style="bold yellow")]
        parts += [Text(""), Text("v%s" % __version__, style="dim")]
        return Group(*parts)

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        choice = event.option.id
        app = self.app
        if choice == "exam":
            app.push_screen(ExamScreen())
        elif choice == "practice":
            app.push_screen(PickerScreen())
        elif choice == "progress":
            app.push_screen(ProgressScreen())
        elif choice == "switch":
            app.push_screen(
                ChoiceModal("Switch exam", app.exam_choices()), app.switch_exam
            )
        elif choice == "quit":
            app.exit()

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_feedback(self) -> None:
        from .. import feedback

        self.app.push_screen(
            ChoiceModal(
                "Give feedback — opens a GitHub form, nothing is "
                "sent until you submit it",
                list(feedback.KIND_LABELS),
            ),
            self.app.open_feedback,
        )


# ══════════════════════════════════════════════════════════════
#  EXERCISE PICKER
# ══════════════════════════════════════════════════════════════
class PickerScreen(AppScreen[None]):
    """Practice: one filterable table, three tabs — the exam pool, your gaps
    (a short queue from stats.drill_queue(), weak spots first) and the extra
    LeetCode-style pool, which the exam never draws from."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("slash", "focus_filter", "filter"),
        Binding("tab", "next_tab", "next tab"),
    ]

    POOLS = (
        ("exam", "Exam exercises"),
        ("gaps", "My gaps"),
        ("extra", "Extra"),
    )

    entries: List[Tuple[Any, ...]]
    status: Dict[str, Dict[str, Any]]

    def __init__(self, pool: str = "exam") -> None:
        super().__init__()
        self.pool = pool

    def compose(self) -> ComposeResult:
        yield Header()
        yield Tabs(
            *[Tab(label, id=pool) for pool, label in self.POOLS],
            active=self.pool,
            id="pools",
        )
        with Horizontal(id="picker-body"):
            with Vertical(id="picker-left"):
                yield Input(
                    placeholder="type to filter by name or function …",
                    id="filter",
                )
                yield DataTable(
                    id="table", cursor_type="row", zebra_stripes=True
                )
            yield VerticalScroll(
                Copyable(id="preview"), id="preview-pane", classes="pane"
            )
        yield Footer()

    def on_mount(self) -> None:
        self.load_pool(self.pool)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        pool = event.tab.id
        if pool and pool != self.pool:
            self.load_pool(pool)

    def action_next_tab(self) -> None:
        self.query_one(Tabs).action_next_tab()

    def load_pool(self, pool: str) -> None:
        sh = self.app.sh
        self.pool = pool
        exam = list(sh.exercise_entries())  # e[4]: the exam can draw it
        if pool == "exam":
            self.entries = [e for e in exam if e[4]]
        elif pool == "gaps":
            by_name = {e[2]: e for e in exam if e[4]}
            queue = stats.drill_queue(
                sh.TOOL, list(by_name), shell_common.DRILL_SIZE
            )
            self.entries = [by_name[name] for name in queue]
        else:  # what the exam never draws: the bank's extras + training
            self.entries = [
                (e[0], "level %s" % e[1], e[2], e[3]) for e in exam if not e[4]
            ] + list(sh.training_entries())
        self.status = stats.exercise_status(
            sh.TOOL, [e[2] for e in self.entries]
        )
        table: DataTable[str] = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns(
            "", "kind" if pool == "extra" else "level", "exercise"
        )
        self.fill(self.query_one("#filter", Input).value)
        table.focus()

    def on_screen_resume(self) -> None:
        table: DataTable[str] = self.query_one(DataTable)
        row = table.cursor_row
        self.load_pool(self.pool)
        table.move_cursor(row=row)

    def fill(self, query: str) -> None:
        table: DataTable[str] = self.query_one(DataTable)
        table.clear()
        mark = {
            "passed": "[green]✔[/green]",
            "failed": "[red]✖[/red]",
            "untried": "[dim]·[/dim]",
        }
        for entry in shell_common.filter_entries(self.entries, query, 2, 3):
            name = entry[2]
            table.add_row(
                mark[self.status[name]["status"]],
                str(entry[1]),
                name,
                key=name,
            )
        if not table.row_count:
            pane = self.query_one("#preview-pane")
            pane.border_title = pane.border_subtitle = None
            self.query_one("#preview", Copyable).update(
                render.waiting_view(
                    "no gaps right now — everything passed recently"
                    if self.pool == "gaps" and not query
                    else "no exercise matches"
                )
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self.fill(event.value)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        self.query_one(DataTable).focus()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.row_key is None:
            return
        name = cast(str, event.row_key.value)  # rows are keyed by name
        row = self.status[name]
        pane = self.query_one("#preview-pane")
        pane.border_title = name
        pane.border_subtitle = (
            "%d/%d passed" % (row["passes"], row["attempts"])
            if row["attempts"]
            else "never tried"
        )
        self.query_one("#preview", Copyable).update(
            ui.subject_blocks(
                self.app.sh.ALL_EXERCISES[name], code_background=None
            )
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        name = cast(str, event.row_key.value)  # rows are keyed by name
        if self.pool == "gaps":
            # the rest of the gaps follow with `n`
            queue = [e[2] for e in self.entries]
            self.app.push_screen(
                PracticeScreen(
                    name, mode="drill", queue=queue, position=queue.index(name)
                )
            )
            return
        training = name in self.app.sh.TRAINING_EXERCISES
        self.app.push_screen(
            PracticeScreen(name, mode="train" if training else "practice")
        )


# ══════════════════════════════════════════════════════════════
#  THE SPLIT VIEW  ·  subject over results  (practice and exam)
# ══════════════════════════════════════════════════════════════
class SplitScreen(AppScreen[None]):
    """The subject on top, the grading results below — your code stays in
    your editor. Subclasses decide what grading means (practice vs exam)."""

    def __init__(self) -> None:
        super().__init__()
        self.ex_name = ""  # empty while the exam still asks for the login
        self.log_entries: List[LogEntry] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status")
        with Vertical(id="split"):
            yield VerticalScroll(
                Copyable(id="subject"), id="subject-pane", classes="pane"
            )
            yield VerticalScroll(
                Copyable(id="results"), id="results-pane", classes="pane"
            )
        yield Footer()

    def show_exercise(self, ex_name: str) -> None:
        sh = self.app.sh
        self.ex_name = ex_name
        ex = sh.ALL_EXERCISES[ex_name]
        pane = self.query_one("#subject-pane")
        pane.border_title = ex_name
        pane.border_subtitle = shell_common.solution_path(
            sh, ex_name, self.app.cfg
        )
        self.query_one("#subject", Copyable).update(
            ui.subject_blocks(
                ex, lexer_theme=SUBJECT_SYNTAX, code_background=None
            )
        )  # the theme's own code background
        self.set_results(
            render.waiting_view(
                "Write your solution in %s, then press g to grade."
                % shell_common.solution_path(sh, ex_name, self.app.cfg)
            )
        )
        self.show_attempts()

    def log_report(self, report: Report) -> None:
        self.log_entries.append(
            (time.strftime("%H:%M:%S"), report.exercise, report)
        )
        self.show_attempts()

    def show_attempts(self) -> None:
        """This session's gradings of the current exercise, in one line
        under the results."""
        self.query_one(
            "#results-pane"
        ).border_subtitle = render.attempt_summary(
            self.log_entries, self.ex_name
        )

    def set_results(
        self, renderable: RenderableType, title: str = "results"
    ) -> None:
        self.query_one("#results", Copyable).update(renderable)
        self.query_one("#results-pane").border_title = title

    def _cfg(self) -> TesterConfig:
        # ExamScreen: the exam's own config
        run: Optional[ExamRun] = getattr(self, "run", None)
        return run.cfg if run is not None else self.app.cfg

    def action_stub(self) -> None:
        ok, kind, message = self.app.sh.write_stub(self.ex_name, self._cfg())
        self.notify(
            message,
            severity="information"
            if ok
            else ("warning" if kind == "warn" else "error"),
        )

    def action_edit(self) -> None:
        """Open your solution in your editor (a stub first if there's no
        file yet): VS Code when `code` is there, else $VISUAL / $EDITOR
        right here in the terminal."""
        if not self.ex_name:
            return
        cfg = self._cfg()
        path = shell_common.solution_path(self.app.sh, self.ex_name, cfg)
        if not os.path.exists(path):
            self.app.sh.write_stub(self.ex_name, cfg)
        command = editor_command(path)
        if command is None:
            self.notify(
                "No editor found (no `code`, no $EDITOR) — open %s" % path,
                severity="warning",
            )
        elif command[0] == "code":
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.notify("Opened %s in VS Code" % path)
        else:
            with self.app.suspend():
                subprocess.call(command)


class PracticeScreen(SplitScreen):
    """Practice/training/drill: grade as often as you like, optional watch
    mode (re-grade on every save), hints after repeated fails."""

    BINDINGS = [
        Binding("g", "grade", "grademe"),
        Binding("d", "details", "details"),
        Binding("w", "toggle_watch", "watch"),
        Binding("e", "edit", "edit"),
        Binding("t", "stub", "stub"),
        Binding("f", "feedback", "differs from exam?"),
        Binding("n", "next", "next", show=False),
        Binding("escape", "app.pop_screen", "back"),
    ]

    def __init__(
        self,
        ex_name: str,
        mode: str = "practice",
        queue: Optional[List[str]] = None,
        position: int = 0,
    ) -> None:
        super().__init__()
        self.start_ex, self.mode = ex_name, mode
        self.outcome: Optional[GradeOutcome] = None
        self.details = False
        self.queue, self.position = queue, position
        self.rng = random.Random()
        self.grading = False
        self.watch_timer: Optional[Timer] = None
        self.watch_mtime: Optional[float] = None

    def on_mount(self) -> None:
        self.show_exercise(self.start_ex)
        self.update_status()

    def update_status(self) -> None:
        text = Text()
        text.append(" %s " % self.mode.upper(), style="bold reverse")
        if self.queue:
            text.append(
                "  drill %d/%d" % (self.position + 1, len(self.queue)),
                style="bold",
            )
            if self.position + 1 < len(self.queue):
                text.append("  ·  n = next exercise", style="dim")
        text.append("   watch: ", style="dim")
        text.append(
            "ON — grading on every save" if self.watch_timer else "off (w)",
            style="bold green" if self.watch_timer else "dim",
        )
        self.query_one("#status", Static).update(text)

    # ── grading ───────────────────────────────────────────────────────
    def action_grade(self) -> None:
        if self.grading:
            return
        self.grading = True
        self.set_results(
            render.waiting_view("⏳ grading %s …" % self.ex_name), "grading …"
        )
        self.grade_worker(self.ex_name)

    @work(thread=True, exclusive=True)
    def grade_worker(self, ex_name: str) -> None:
        app = self.app
        try:
            outcome = shell_common.grade(
                app.sh, ex_name, self.rng, app.cfg, mode=self.mode
            )
            app.call_from_thread(self.show_outcome, outcome)
        except BankError as exc:
            app.call_from_thread(
                self.show_error, "exercise bank is broken: %s" % exc
            )

    def show_error(self, message: str) -> None:
        self.grading = False
        self.set_results(Text(message, style="bold red"), "error")

    def show_outcome(self, outcome: GradeOutcome) -> None:
        self.grading = False
        report = outcome.report
        self.log_report(report)
        self.outcome, self.details = outcome, False
        self.show_report()
        if report.ok and self.queue and self.position + 1 < len(self.queue):
            self.notify(
                "Passed! Press n for the next drill exercise.", timeout=5
            )

    def show_report(self) -> None:
        """The last grade: compact, or every detail after `d`."""
        outcome = self.outcome
        if outcome is None:
            return
        report = outcome.report
        if self.details:
            view: RenderableType = render.report_view(
                report, report.function, len(report.failures)
            )
            if outcome.hint:
                view = Group(view, Text(""), render.hint_view(outcome.hint))
        else:
            view = render.compact_report_view(
                report, report.function, hint=outcome.hint or ""
            )
        self.set_results(view, "grademe")

    def action_details(self) -> None:
        if self.outcome is not None and not self.outcome.report.ok:
            self.details = not self.details
            self.show_report()

    # ── watch mode ────────────────────────────────────────────────────
    def _mtime(self) -> Optional[float]:
        try:
            return os.path.getmtime(
                shell_common.solution_path(
                    self.app.sh, self.ex_name, self.app.cfg
                )
            )
        except OSError:
            return None

    def action_toggle_watch(self) -> None:
        if self.watch_timer:
            self.watch_timer.stop()
            self.watch_timer = None
        else:
            self.watch_mtime = self._mtime()
            self.watch_timer = self.set_interval(
                WATCH_INTERVAL, self.check_watch
            )
            self.notify("Watching your file — every save re-grades it.")
        self.update_status()

    def check_watch(self) -> None:
        mtime = self._mtime()
        if mtime is not None and mtime != self.watch_mtime:
            self.watch_mtime = mtime
            self.action_grade()

    def action_feedback(self) -> None:
        self.app.open_feedback("exam", self.ex_name)

    def action_next(self) -> None:
        if self.queue and self.position + 1 < len(self.queue):
            nxt = self.position + 1
            screen = PracticeScreen(
                self.queue[nxt], mode="drill", queue=self.queue, position=nxt
            )
            screen.log_entries = self.log_entries
            self.app.switch_screen(screen)


class ExamScreen(SplitScreen):
    """The exam, driving one shell_common.ExamRun."""

    BINDINGS = [
        Binding("g", "grade", "grademe"),
        Binding("e", "edit", "edit"),
        Binding("t", "stub", "stub"),
        Binding("n", "redraw", "new", show=False),
        Binding("escape", "quit_exam", "quit & save"),
    ]

    run: ExamRun  # created in on_mount()

    def __init__(self) -> None:
        super().__init__()
        self.grading = False
        self.over = False

    def on_mount(self) -> None:
        app = self.app
        self.run = shell_common.ExamRun(app.sh, app.cfg)
        self.set_results(render.waiting_view("Starting the exam …"))
        saved = session_store.load(app.sh.TOOL)
        if saved:
            question = "Resume your saved exam for [b]%s[/b] — level %d?" % (
                saved["login"],
                saved["level"],
            )
            app.push_screen(
                ConfirmModal(question),
                lambda yes: self.after_resume_question(yes, saved),
            )
        else:
            self.ask_login()

    def after_resume_question(
        self, yes: Optional[bool], saved: Event
    ) -> None:
        if yes is None:  # esc: back to the menu, the save stays
            self.app.pop_screen()
        elif yes:
            self.run.resume(saved)
            self.notify("Resumed at level %d." % self.run.level)
            self.begin()
            self.tick()  # the limit may have run out during the pause
        else:
            self.run.discard_save()
            self.ask_login()

    def ask_login(self) -> None:
        default = self.run.session.login
        self.app.push_screen(PromptModal("Login", default), self.after_login)

    def after_login(self, login: Optional[str]) -> None:
        if login is None:  # esc: nothing started, nothing archived
            self.app.pop_screen()
            return
        archived = self.run.start(login)
        cfg = self.run.cfg
        notes: List[str] = []
        if archived:
            notes.append("earlier exam solutions moved to %s" % archived)
        if not cfg.relaxed:
            notes.append(
                "realistic mode: as strict as the real exam, no 'new'"
            )
        if getattr(cfg, "blind", False):
            notes.append("blind grading: failing inputs are hidden")
        if cfg.time_limit:
            notes.append("time limit: %d minutes" % cfg.time_limit)
        if notes:
            self.notify(" · ".join(notes), timeout=6)
        self.begin()

    def begin(self) -> None:
        self.load_level()
        self.set_interval(1.0, self.tick)

    def load_level(self) -> None:
        self.show_exercise(self.run.ensure_exercise())
        self.update_status()

    def update_status(self) -> None:
        run = self.run
        self.query_one("#status", Static).update(
            render.exam_status(
                run.session, run.n_levels, run.countdown(), run.level_attempts
            )
        )

    def tick(self) -> None:
        if self.over or self.run.session.start_time is None:
            return
        self.update_status()
        if self.run.times_up():
            self.run.discard_save()
            self.finish(passed=False, timed_out=True)

    # ── actions ───────────────────────────────────────────────────────
    def action_grade(self) -> None:
        if self.grading or self.over or self.run.current_ex is None:
            return
        self.grading = True
        self.run.begin_attempt()
        self.update_status()
        self.set_results(
            render.waiting_view("⏳ grading %s …" % self.ex_name), "grading …"
        )
        self.grade_worker(self.run.current_ex)

    @work(thread=True, exclusive=True)
    def grade_worker(self, ex_name: str) -> None:
        app = self.app
        try:
            outcome = shell_common.grade(
                app.sh, ex_name, self.run.grade_rng, self.run.cfg, mode="exam"
            )
            app.call_from_thread(self.show_outcome, outcome)
        except BankError as exc:
            app.call_from_thread(
                self.show_error, "exercise bank is broken: %s" % exc
            )

    def show_error(self, message: str) -> None:
        self.grading = False
        self.set_results(Text(message, style="bold red"), "error")

    def show_outcome(self, outcome: GradeOutcome) -> None:
        self.grading = False
        if self.over:
            return
        report = outcome.report
        self.log_report(report)
        blind = getattr(self.run.cfg, "blind", False)
        self.set_results(
            render.exam_trace_view(report, report.function, blind=blind),
            "grademe",
        )
        if not report.ok:
            return
        cleared = self.run.level
        if self.run.pass_level():
            self.run.discard_save()
            self.finish(passed=True)
            return
        self.notify(
            "Level %d cleared — on to level %d." % (cleared, self.run.level),
            title="✔ PASSED",
            timeout=5,
        )
        self.load_level()

    def action_redraw(self) -> None:
        if self.over or self.grading:
            return
        if not self.run.redraw():
            self.notify(
                "The real exam has no 'new' — "
                "start with --relaxed to allow redraws.",
                severity="warning",
            )
            return
        self.load_level()
        self.notify("New exercise drawn for level %d." % self.run.level)

    def action_quit_exam(self) -> None:
        if self.over:
            self.app.pop_screen()
            return
        self.app.push_screen(
            ConfirmModal(
                "Quit the exam? Your progress is saved and can be resumed."
            ),
            self.after_quit_question,
        )

    def after_quit_question(self, yes: Optional[bool]) -> None:
        if yes and not self.over:
            if self.run.session.start_time is not None:
                self.run.save()
            self.finish(passed=False)

    def finish(self, passed: bool, timed_out: bool = False) -> None:
        self.over = True
        result = shell_common.finish_exam(
            self.app.sh, self.run.session, passed, timed_out
        )
        self.app.switch_screen(SummaryScreen(result))


class SummaryScreen(AppScreen[None]):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "menu"),
        Binding("enter", "app.pop_screen", "menu", show=False),
    ]

    def __init__(self, result: ExamResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Copyable(render.exam_result_view(self.result), id="summary"),
            id="summary-pane",
            classes="pane",
        )
        yield Footer()

    def on_mount(self) -> None:
        pane = self.query_one("#summary-pane")
        pane.border_title = "exam summary"
        if self.result.passed:
            pane.add_class("passed")
        hint = None if self.result.passed else shell_common.sync_hint()
        if hint:
            self.notify(hint, timeout=10)


# ══════════════════════════════════════════════════════════════
#  PROGRESS  ·  readiness + stats on one screen
# ══════════════════════════════════════════════════════════════
class ProgressScreen(AppScreen[None]):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("p", "practice_gaps", "practice my gaps"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="stats-body"):
            yield VerticalScroll(
                Static(id="readiness"), id="stats-pane", classes="pane"
            )
            yield VerticalScroll(
                Static(id="per-exercise"),
                id="per-exercise-pane",
                classes="pane",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def on_screen_resume(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        sh = self.app.sh
        tool = sh.TOOL
        summary = stats.summarize(tool)
        self.query_one("#stats-pane").border_title = "readiness"
        self.query_one("#per-exercise-pane").border_title = "per exercise"
        self.query_one("#readiness", Static).update(
            Group(
                render.readiness_view(
                    stats.readiness(tool, sh.STANDARD_LEVELS)
                ),
                Text(""),
                render.stats_overview(
                    summary,
                    stats.daily_activity(tool),
                    stats.practice_streak(tool),
                    stats.exam_history(tool),
                    shell_common.fmt_duration,
                ),
            )
        )
        self.query_one("#per-exercise", Static).update(
            render.per_exercise_view(summary)
        )

    def action_practice_gaps(self) -> None:
        self.app.push_screen(PickerScreen("gaps"))


# ══════════════════════════════════════════════════════════════
#  SETTINGS  ·  what used to be flags and --save-config
# ══════════════════════════════════════════════════════════════
class SettingsScreen(AppScreen[None]):
    """The few things worth changing, saved to ~/.examshell/config.json
    (settings.py) and applied right away. Esc in a prompt keeps the value."""

    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="settings-body"):
            yield OptionList(id="settings")
            yield Static(
                "enter to change · saved for every session",
                classes="modal-hint",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one("#settings", OptionList).focus()

    def rows(self) -> List[Tuple[str, str, str]]:
        from .. import sync

        cfg = self.app.cfg
        limit = getattr(cfg, "time_limit", None)
        repo = sync.remote_url(settings.DATA_DIR)
        rows = [
            (
                "time_limit",
                "Exam time limit",
                "%d min" % limit if limit else "off",
            ),
            ("timeout", "Time per test", "%d s" % cfg.timeout),
            ("fuzz", "Random tests per exercise", str(cfg.fuzz)),
        ]
        if hasattr(cfg, "cc"):
            rows.append(("cc", "C compiler", str(getattr(cfg, "cc"))))
        rows += [
            ("sync_repo", "Sync repo", repo or "not set up"),
            (
                "auto_sync",
                "Auto-sync",
                "on" if shell_common.auto_sync_enabled() else "off",
            ),
        ]
        return rows

    def refresh_list(self) -> None:
        menu = self.query_one("#settings", OptionList)
        highlighted = menu.highlighted
        menu.clear_options()
        for key, label, value in self.rows():
            menu.add_option(Option("%-28s [b]%s[/b]" % (label, value), id=key))
        menu.highlighted = highlighted if highlighted is not None else 0

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        key = event.option.id or ""
        cfg = self.app.cfg
        if key == "auto_sync":
            on = not shell_common.auto_sync_enabled()
            self.save("auto_sync", on)
            if on:
                self.app.notify(
                    "Auto-sync on: every session pulls first and pushes "
                    "when it ends (once a sync repo is set up)."
                )
            return
        if key == "sync_repo":
            self.app.push_screen(
                PromptModal(
                    "URL of your PRIVATE git repo for sync "
                    "(see docs/sync.md) — Esc to cancel",
                ),
                self.app.setup_sync,
            )
            return
        prompts = {
            "time_limit": "Exam time limit in minutes (0 = off):",
            "timeout": "Seconds each test may run:",
            "fuzz": "Random tests per exercise, on top of the fixed ones:",
            "cc": "C compiler to use (cc, gcc, clang …):",
        }
        current = getattr(cfg, key, None)
        default = str(current or 0) if key == "time_limit" else str(current)
        self.app.push_screen(
            PromptModal(prompts[key], default),
            lambda value: self.apply(key, value),
        )

    def apply(self, key: str, value: Optional[str]) -> None:
        if value is None:
            return
        if key == "cc":
            if value and shutil.which(value) is None:
                self.app.notify("%r is not on PATH" % value, severity="error")
            elif value:
                self.save("cc", value)
            return
        try:
            number = int(value)
        except ValueError:
            self.app.notify("%r is not a number" % value, severity="error")
            return
        if key == "time_limit":
            self.save("time_limit", number if number > 0 else None)
        elif number < (1 if key == "timeout" else 0):
            self.app.notify("that's too small", severity="error")
        else:
            self.save(key, number)

    def save(self, key: str, value: Any) -> None:
        if not settings.update_config(key, value):
            self.app.notify(
                "could not write %s" % settings.CONFIG_PATH, severity="error"
            )
            return
        if key != "auto_sync":
            setattr(self.app.cfg, key, value)
        self.refresh_list()


# ══════════════════════════════════════════════════════════════
#  THE APP
# ══════════════════════════════════════════════════════════════
class ExamShellApp(App[None]):
    TITLE = "ExamShell"
    CSS = """
    Screen { background: $background; }
    #menu-body { height: 1fr; }
    #menu-left { width: 56; padding: 1 1 1 2; }
    #menu { height: auto; max-height: 1fr; border: round $border-blurred; }
    #menu:focus { border: round $primary; }
    #menu-right { width: 1fr; padding: 1 2; margin: 1 2 1 1; }
    #status { height: 1; padding: 0 1; }
    #split, #picker-body, #stats-body { height: 1fr; }
    .pane { border: round $border-blurred; padding: 0 1; }
    #subject-pane { height: 1fr; min-height: 6; }
    #results-pane { height: auto; max-height: 70%; }
    #pools { margin: 0 1; }
    #settings-body { padding: 1 2; }
    #settings { height: auto; border: round $border-blurred; }
    #summary-pane { padding: 1 2; margin: 1 2; }
    #summary-pane.passed { border: round $success; }
    #stats-pane { width: 1fr; padding: 1 2; margin: 1 1 1 2; }
    #per-exercise-pane { width: 1fr; margin: 1 2 1 1; }
    #picker-left { width: 2fr; max-width: 72; }
    #preview-pane { width: 3fr; margin: 0 1 0 0; }
    #filter { margin: 0 1 1 1; border: none; height: 1; padding: 0 1; }
    DataTable > .datatable--header {
        background: $background; color: $text-muted; text-style: bold;
    }
    #table { height: 1fr; margin: 0 1; }
    .-narrow #menu-right, .-narrow #preview-pane { display: none; }
    .-narrow #menu-left { width: 1fr; }
    .-narrow #picker-left { max-width: 100%; }
    .-narrow #stats-body { layout: vertical; }
    .-narrow #stats-pane { width: 1fr; height: auto; margin: 1 2 0 2; }
    .-narrow #per-exercise-pane { width: 1fr; margin: 0 2 1 2; }
    .modal {
        width: 64; height: auto; padding: 1 2; border: round $primary;
    }
    ModalScreen { align: center middle; }
    .modal-question { margin-bottom: 1; }
    .modal-hint { color: $text-muted; }
    """

    BINDINGS = [Binding("question_mark", "help", "keys")]

    def __init__(
        self,
        sh: Tester,
        cfg: TesterConfig,
        start: Union[None, str, Tuple[str, str]] = None,
        ask_exam: bool = False,
    ) -> None:
        super().__init__()
        self.sh, self.cfg, self.start = sh, cfg, start
        # the very first start: ask which exam, instead of assuming Rank 03
        self.ask_exam = ask_exam
        self.update_notice: Dict[str, Optional[str]] = {"notice": None}

    def action_help(self) -> None:
        if not isinstance(self.screen, HelpModal):
            self.push_screen(HelpModal())

    def _handle_exception(self, error: Exception) -> None:
        """An unexpected error ends the app (Textual's own handling) — but
        first it goes to crash.log, so the next start can offer to report
        it instead of the traceback just scrolling away."""
        # A worker's WorkerFailed is raised fresh, without frames: log the
        # error it wraps, whose traceback says where it actually broke.
        cause = error.error if isinstance(error, WorkerFailed) else error
        crashlog.record(cause, type(self.screen).__name__)
        super()._handle_exception(error)

    # ── clipboard: OSC 52 plus the system's own tool ─────────────────
    def copy_to_clipboard(self, text: str) -> None:
        """OSC 52 (what Textual does) for the terminals that support it,
        and the system clipboard for the ones that don't (GNOME Terminal,
        macOS Terminal, ...) — see clipboard.py."""
        super().copy_to_clipboard(text)
        system_clipboard.copy(text)

    @property
    def clipboard(self) -> str:
        """What ctrl+v in an input field pastes: the system clipboard where
        it can be read, else what was last copied inside the app."""
        text = system_clipboard.paste()
        return self._clipboard if text is None else text

    def label(self) -> str:
        if hasattr(self.sh, "RANK"):
            return "Python · %s" % self.sh.RANK.label
        return "C · Exam Rank 02"

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < NARROW, "-narrow")

    def on_mount(self) -> None:
        self.set_class(self.size.width < NARROW, "-narrow")
        self.theme = THEME
        self.update_notice = update_check.start_background_check(
            getattr(self.cfg, "no_update_check", False)
        )
        self.push_screen(MenuScreen())
        if self.start == "exam":
            self.push_screen(ExamScreen())
        elif isinstance(self.start, tuple) and self.start[0] == "practice":
            self.push_screen(PracticeScreen(self.start[1]))
        if self.ask_exam:
            self.push_screen(
                ChoiceModal(
                    "Welcome! Which exam are you practising for?",
                    self.exam_choices(),
                ),
                self.first_pick,
            )
        log = crashlog.pending()
        if log is not None:  # asked first: it's on top of the welcome
            self.push_screen(
                ConfirmModal(
                    "ExamShell crashed last time. Report it? It opens a "
                    "GitHub form with the error filled in — nothing is "
                    "sent until you submit it."
                ),
                lambda yes: self.report_crash(log, yes),
            )

    def first_pick(self, choice: Optional[str]) -> None:
        """The welcome question's answer (Esc keeps the default — and
        doesn't ask again)."""
        if choice:
            self.switch_exam(choice)
        else:
            settings.remember_exam(self.choice_id())

    def choice_id(self) -> str:
        """This tester as an exam_choices() id: "py03" … or "c"."""
        rank = getattr(self.sh, "RANK", None)
        return "py" + rank.id if rank is not None else "c"

    def report_crash(self, log: str, yes: Optional[bool]) -> None:
        crashlog.mark_seen()
        if yes:
            self.open_feedback("bug", details=crashlog.report_text(log))

    # ── switching between the Python ranks and the C exam ─────────────
    def exam_choices(self) -> List[Tuple[str, str]]:
        from .. import ranks
        from c_exam import bank as c_bank

        choices = [
            (
                "py" + rid,
                "Python · %s  ·  %d exercises · %d levels"
                % (label, count, levels),
            )
            for rid, label, count, levels in ranks.summary()
        ]
        choices.append(
            (
                "c",
                "C · Exam Rank 02  ·  %d exercises · %d levels"
                % (len(c_bank.EXERCISES), c_bank.N_LEVELS),
            )
        )
        return choices

    def switch_exam(self, choice: Optional[str]) -> None:
        """Point the whole app at another tester (and rank). Exam-wide
        choices made on the command line (--relaxed, --time-limit, --blind)
        carry over; everything else comes from that tester's own defaults
        and your saved settings."""
        if not choice:
            return
        new_sh: Tester
        if choice == "c":
            from c_exam import examshell as c_shell

            new_sh = c_shell
        else:
            from .. import examshell as py_shell

            py_shell.use_rank(choice[2:])
            new_sh = py_shell
        settings.remember_exam(choice)
        keep = {
            k: getattr(self.cfg, k, None)
            for k in ("relaxed", "time_limit", "blind", "no_update_check")
        }
        self.cfg = new_sh.default_config(**keep)
        self.sh = new_sh
        self.notify("Switched to %s" % self.label())
        if isinstance(self.screen, MenuScreen):
            self.screen.refresh_menu()
        elif isinstance(self.screen, SettingsScreen):
            self.screen.refresh_list()

    # ── feedback ──────────────────────────────────────────────────────
    def open_feedback(
        self,
        kind: Optional[str],
        exercise: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Open the prefilled issue form in a browser where one exists; the
        link always goes to the clipboard too (OSC 52 works over ssh)."""
        if not kind:
            return
        from .. import feedback

        url = feedback.issue_url(
            kind, shell_common.tester_label(self.sh), exercise, details
        )
        try:
            self.copy_to_clipboard(url)
        except Exception:
            pass
        if feedback.open_in_browser(url):
            self.notify(
                "Opened the form in your browser (link also copied).",
                timeout=6,
            )
        else:
            self.notify(
                "Link copied — paste it into a browser:\n" + url, timeout=15
            )

    # ── sync ──────────────────────────────────────────────────────────
    def action_sync(self) -> None:
        self.start_sync()

    def start_sync(self) -> None:
        from .. import settings, sync

        if not sync.is_configured(settings.DATA_DIR):
            self.notify(
                "Sync isn't set up on this device yet — add your private "
                "repo in Settings (o). See docs/sync.md.",
                severity="warning",
                timeout=8,
            )
            return
        self.notify("Syncing with your repo …")
        self.sync_worker()

    def setup_sync(self, url: Optional[str]) -> None:
        if url:
            self.notify("Connecting to %s …" % url)
            self.sync_worker(url)

    @work(thread=True, exclusive=True, group="sync")
    def sync_worker(self, setup_url: Optional[str] = None) -> None:
        from .. import settings, sync

        dirs = shell_common.sync_dirs(self.sh, self.cfg)
        try:
            if setup_url:
                result = sync.setup(setup_url, settings.DATA_DIR, dirs)
            else:
                result = sync.sync(settings.DATA_DIR, dirs)
        except sync.SyncError as exc:
            self.call_from_thread(
                self.notify,
                str(exc),
                title="Sync failed",
                severity="error",
                timeout=10,
            )
            return
        self.call_from_thread(self.sync_done, result)

    def sync_done(self, result: SyncResult) -> None:
        self.notify(result.summary(), title="✔ Synced", timeout=8)
        for backup in result.backups:
            self.notify("older version kept at %s" % backup, timeout=10)
        if isinstance(self.screen, MenuScreen):
            self.screen.refresh_menu()
