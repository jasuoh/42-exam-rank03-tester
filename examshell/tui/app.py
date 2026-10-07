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
from rich.syntax import Syntax
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
)
from textual.visual import VisualType
from textual.widgets.option_list import Option

from .. import session_store, shell_common, stats, ui, update_check
from .._types import Event, Tester, TesterConfig
from ..grader import BankError, Report
from ..shell_common import ExamResult, ExamRun, GradeOutcome
from ..sync import SyncResult
from ..version import __version__
from . import render

THEMES = {
    "dark": "textual-dark",
    "light": "textual-light",
    "highcontrast": "textual-dark",
}
WATCH_INTERVAL = 1.0  # seconds between solution-file checks
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
class ConfirmModal(ModalScreen[bool]):
    """Yes/no question → dismisses with True/False."""

    BINDINGS = [
        Binding("y", "answer(True)", "yes"),
        Binding("n", "answer(False)", "no"),
        Binding("escape", "answer(False)", "no"),
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


class PromptModal(ModalScreen[str]):
    """One line of text → dismisses with the string (Esc → default)."""

    BINDINGS = [Binding("escape", "cancel", "use default")]

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
        self.dismiss(self.default)


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
    BINDINGS = [Binding("q", "app.quit", "quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="menu-body"):
            with Vertical(id="menu-left"):
                yield Static(id="logo")
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
        self.query_one("#logo", Static).update(render.logo(self.app.label()))
        items = [
            (
                "exam",
                "🎯  Start exam",
                "%d levels, as strict as the real one" % sh.N_LEVELS,
            ),
            (
                "practice",
                "📚  Practice",
                "any exam exercise, lenient feedback",
            ),
            ("training", "🧠  Training", "LeetCode-style, by difficulty"),
            (
                "drill",
                "🔁  Daily drill",
                "%d exercises from your gaps" % shell_common.DRILL_SIZE,
            ),
            (
                "readiness",
                "📈  Exam readiness",
                "what you've passed, level by level",
            ),
            ("stats", "📊  Stats", "history, streak, pass rates"),
        ]
        items.append(
            (
                "switch",
                "🔀  Switch exam",
                "Python 03 · 04 · 05 or C 02 — now: %s" % self.app.label(),
            )
        )
        items.append(("sync", "🔄  Sync", self.app.sync_hint()))
        items.append(
            (
                "feedback",
                "💬  Feedback",
                "differs from your real exam? a bug? an idea?",
            )
        )
        items.append(("quit", "🚪  Quit", ""))
        menu = self.query_one("#menu", OptionList)
        highlighted = menu.highlighted
        menu.clear_options()
        for oid, label, hint in items:
            prompt = "%s\n    [dim]%s[/dim]" % (label, hint) if hint else label
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
            parts += [Text(""), Text("🔔 " + notice, style="bold magenta")]
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
            app.push_screen(PickerScreen("exam"))
        elif choice == "training":
            app.push_screen(PickerScreen("training"))
        elif choice == "drill":
            app.start_drill()
        elif choice == "readiness":
            app.push_screen(ReadinessScreen())
        elif choice == "stats":
            app.push_screen(StatsScreen())
        elif choice == "switch":
            app.push_screen(
                ChoiceModal("Switch exam", app.exam_choices()), app.switch_exam
            )
        elif choice == "sync":
            app.start_sync()
        elif choice == "feedback":
            from .. import feedback

            app.push_screen(
                ChoiceModal(
                    "Give feedback — opens a GitHub form, nothing is "
                    "sent until you submit it",
                    list(feedback.KIND_LABELS),
                ),
                app.open_feedback,
            )
        elif choice == "quit":
            app.exit()


# ══════════════════════════════════════════════════════════════
#  EXERCISE PICKER
# ══════════════════════════════════════════════════════════════
class PickerScreen(AppScreen[None]):
    """Filterable table of the exam pool or the training pool."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("slash", "focus_filter", "filter"),
    ]

    entries: List[Tuple[Any, ...]]
    status: Dict[str, Dict[str, Any]]

    def __init__(self, pool: str) -> None:
        super().__init__()
        self.pool = pool

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="picker-body"):
            with Vertical(id="picker-left"):
                yield Input(
                    placeholder="type to filter by name or function …",
                    id="filter",
                )
                yield DataTable(
                    id="table", cursor_type="row", zebra_stripes=True
                )
            yield VerticalScroll(Copyable(id="preview"), id="preview-pane")
        yield Footer()

    def on_mount(self) -> None:
        sh = self.app.sh
        self.entries = (
            sh.exercise_entries()
            if self.pool == "exam"
            else sh.training_entries()
        )
        self.status = stats.exercise_status(
            sh.TOOL, [e[2] for e in self.entries]
        )
        table: DataTable[str] = self.query_one(DataTable)
        table.add_columns(
            "",
            "level" if self.pool == "exam" else "difficulty",
            "",
            "exercise",
            "function",
        )
        self.fill("")
        table.focus()

    def on_screen_resume(self) -> None:
        sh = self.app.sh
        self.status = stats.exercise_status(
            sh.TOOL, [e[2] for e in self.entries]
        )
        table: DataTable[str] = self.query_one(DataTable)
        row = table.cursor_row
        self.fill(self.query_one("#filter", Input).value)
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
            pool_mark = ""
            if self.pool == "exam":
                pool_mark = (
                    "[yellow]★[/yellow]" if entry[4] else "[dim]○[/dim]"
                )
            table.add_row(
                mark[self.status[name]["status"]],
                str(entry[1]),
                pool_mark,
                name,
                entry[3],
                key=name,
            )
        if not table.row_count:
            pane = self.query_one("#preview-pane")
            pane.border_title = pane.border_subtitle = None
            self.query_one("#preview", Copyable).update(
                render.waiting_view("no exercise matches")
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
        pane.border_title = "📄 %s" % name
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
        mode = "practice" if self.pool == "exam" else "train"
        name = cast(str, event.row_key.value)  # rows are keyed by name
        self.app.push_screen(PracticeScreen(name, mode=mode))


# ══════════════════════════════════════════════════════════════
#  THE SPLIT VIEW  ·  subject | results  (practice and exam)
# ══════════════════════════════════════════════════════════════
class SplitScreen(AppScreen[None]):
    """Subject on the left, grading results on the right. Subclasses decide
    what grading means (practice vs exam)."""

    def __init__(self) -> None:
        super().__init__()
        self.ex_name = ""  # empty while the exam still asks for the login
        self.code_mtime: Optional[float] = None
        self.log_entries: List[LogEntry] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status")
        with Horizontal(id="split"):
            with Vertical(id="split-left"):
                yield VerticalScroll(Copyable(id="subject"), id="subject-pane")
                yield VerticalScroll(Copyable(id="code"), id="code-pane")
            with Vertical(id="split-right"):
                yield VerticalScroll(Copyable(id="results"), id="results-pane")
                yield VerticalScroll(
                    Static(render.attempt_log([]), id="log"), id="log-pane"
                )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_code)
        self.query_one("#log-pane").border_title = "this session"
        self.query_one("#log", Static).update(
            render.attempt_log(self.log_entries)
        )

    def show_exercise(self, ex_name: str) -> None:
        sh = self.app.sh
        self.ex_name = ex_name
        ex = sh.ALL_EXERCISES[ex_name]
        pane = self.query_one("#subject-pane")
        pane.border_title = "📄 %s" % ex_name
        pane.border_subtitle = shell_common.solution_path(
            sh, ex_name, self.app.cfg
        )
        self.query_one("#subject", Copyable).update(
            ui.subject_blocks(ex, code_background=None)
        )  # the theme's own code background
        self.set_results(
            render.waiting_view(
                "Write your solution in %s, then press g to grade."
                % shell_common.solution_path(sh, ex_name, self.app.cfg)
            )
        )
        self.refresh_code(force=True)

    def refresh_code(self, force: bool = False) -> None:
        """Your solution file under the subject — re-read whenever it's
        saved."""
        if not self.ex_name:
            return
        path = shell_common.solution_path(
            self.app.sh, self.ex_name, self.app.cfg
        )
        try:
            mtime: Optional[float] = os.path.getmtime(path)
        except OSError:
            mtime = None
        if not force and mtime == self.code_mtime:
            return
        self.code_mtime = mtime
        pane = self.query_one("#code-pane")
        code = self.query_one("#code", Copyable)
        if mtime is None:
            pane.border_title = "your code"
            code.update(
                render.waiting_view(
                    "no %s yet — write it in your editor, or press t for a "
                    "stub" % os.path.basename(path)
                )
            )
            return
        with open(path, errors="replace") as fh:
            source = fh.read()
        pane.border_title = "your code · saved %s" % time.strftime(
            "%H:%M:%S", time.localtime(mtime)
        )
        code.update(
            Syntax(
                source,
                "c" if path.endswith(".c") else "python",
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
        )

    def log_report(self, report: Report) -> None:
        self.log_entries.append(
            (time.strftime("%H:%M:%S"), report.exercise, report)
        )
        self.query_one("#log", Static).update(
            render.attempt_log(self.log_entries)
        )

    def fails_that_fit(
        self, report: Report, hint: Optional[str] = None
    ) -> int:
        """At least --show-fails, more when the results pane has room (one
        failing test takes ~4 lines) — but never pushing the warnings or
        the hint below the fold."""
        reserve = 6 + 2 * len(report.warnings)
        if hint:
            reserve += len(hint) // 40 + 4
        height = self.query_one("#results-pane").size.height
        return max(self.app.cfg.show_fails or 6, (height - reserve) // 4)

    def set_results(
        self, renderable: RenderableType, title: str = "results"
    ) -> None:
        self.query_one("#results", Copyable).update(renderable)
        self.query_one("#results-pane").border_title = title

    def action_stub(self) -> None:
        # ExamScreen: the exam's own config
        run: Optional[ExamRun] = getattr(self, "run", None)
        cfg = run.cfg if run is not None else self.app.cfg
        ok, kind, message = self.app.sh.write_stub(self.ex_name, cfg)
        self.notify(
            message,
            severity="information"
            if ok
            else ("warning" if kind == "warn" else "error"),
        )


class PracticeScreen(SplitScreen):
    """Practice/training/drill: grade as often as you like, optional watch
    mode (re-grade on every save), hints after repeated fails."""

    BINDINGS = [
        Binding("g", "grade", "grademe"),
        Binding("w", "toggle_watch", "watch"),
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
        self.queue, self.position = queue, position
        self.rng = random.Random()
        self.grading = False
        self.watch_timer: Optional[Timer] = None
        self.watch_mtime: Optional[float] = None

    def on_mount(self) -> None:
        super().on_mount()
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
        view = render.report_view(
            report, report.function, self.fails_that_fit(report, outcome.hint)
        )
        if outcome.hint:
            view = Group(view, Text(""), render.hint_view(outcome.hint))
        self.set_results(view, "✔ passed" if report.ok else "✖ failed")
        for emoji, label in outcome.badges:
            self.notify(
                "%s %s" % (emoji, label), title="New badge!", timeout=6
            )
        if report.ok and self.queue and self.position + 1 < len(self.queue):
            self.notify(
                "Passed! Press n for the next drill exercise.", timeout=5
            )

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
        super().on_mount()
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
                lambda yes: self.after_resume_question(bool(yes), saved),
            )
        else:
            self.ask_login()

    def after_resume_question(self, yes: bool, saved: Event) -> None:
        if yes:
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
        self.run.start(login)
        cfg = self.run.cfg
        notes: List[str] = []
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
            render.report_view(
                report,
                report.function,
                self.fails_that_fit(report),
                blind=blind,
            ),
            "✔ passed" if report.ok else "✖ failed",
        )
        if not report.ok:
            return
        cleared = self.run.level
        if self.run.pass_level():
            self.run.discard_save()
            self.finish(passed=True)
            return
        self.notify(
            "Level %d cleared! 🎉  On to level %d."
            % (cleared, self.run.level),
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
        )
        yield Footer()

    def on_mount(self) -> None:
        pane = self.query_one("#summary-pane")
        pane.border_title = "exam summary"
        if self.result.passed:
            pane.add_class("passed")
        for badge in self.result.badges:
            self.notify(badge, title="🏅", timeout=8)
        hint = None if self.result.passed else shell_common.sync_hint()
        if hint:
            self.notify(hint, timeout=10)


# ══════════════════════════════════════════════════════════════
#  READINESS · STATS
# ══════════════════════════════════════════════════════════════
class ReadinessScreen(AppScreen[None]):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("d", "drill", "drill my gaps"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(id="readiness"), id="readiness-pane")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def on_screen_resume(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        sh = self.app.sh
        self.query_one(
            "#readiness-pane"
        ).border_title = "exam readiness — every exercise the exam can draw"
        self.query_one("#readiness", Static).update(
            render.readiness_view(stats.readiness(sh.TOOL, sh.STANDARD_LEVELS))
        )

    def action_drill(self) -> None:
        self.app.start_drill()


class StatsScreen(AppScreen[None]):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="stats-body"):
            yield VerticalScroll(Static(id="stats"), id="stats-pane")
            yield VerticalScroll(
                Static(id="per-exercise"), id="per-exercise-pane"
            )
        yield Footer()

    def on_mount(self) -> None:
        tool = self.app.sh.TOOL
        summary = stats.summarize(tool)
        self.query_one("#stats-pane").border_title = "your history"
        self.query_one(
            "#per-exercise-pane"
        ).border_title = "per exercise (worst first)"
        self.query_one("#stats", Static).update(
            render.stats_overview(
                summary,
                stats.daily_activity(tool),
                stats.practice_streak(tool),
                stats.exam_history(tool),
                shell_common.fmt_duration,
            )
        )
        self.query_one("#per-exercise", Static).update(
            render.per_exercise_view(summary)
        )


# ══════════════════════════════════════════════════════════════
#  THE APP
# ══════════════════════════════════════════════════════════════
class ExamShellApp(App[None]):
    TITLE = "ExamShell"
    CSS = """
    Screen { background: $surface; }
    #menu-body { height: 1fr; }
    #menu-left { width: 56; padding: 1 1 1 2; }
    #logo { height: 4; content-align: center middle; }
    #menu {
        height: auto; max-height: 1fr; border: round $accent; padding: 0 1;
    }
    #menu-right {
        width: 1fr; border: round $secondary; padding: 1 2; margin: 1 2 1 1;
    }
    #status { height: 1; padding: 0 1; background: $panel; }
    #split, #picker-body, #stats-body { height: 1fr; }
    #split-left { width: 3fr; }
    #subject-pane {
        height: auto; max-height: 60%; border: round $warning; padding: 0 1;
    }
    #code-pane {
        height: 1fr; min-height: 5; border: round $secondary; padding: 0 1;
    }
    #split-right { width: 2fr; }
    #results-pane { height: 1fr; border: round $accent; padding: 0 1; }
    #log-pane {
        height: auto; max-height: 10; border: round $secondary; padding: 0 1;
    }
    #summary-pane, #readiness-pane {
        border: round $accent; padding: 1 2; margin: 1 2;
    }
    #stats-pane {
        width: 1fr; border: round $accent; padding: 1 2; margin: 1 1 1 2;
    }
    #per-exercise-pane {
        width: 1fr; border: round $secondary; padding: 0 1; margin: 1 2 1 1;
    }
    #summary-pane.passed { border: heavy $success; }
    #picker-left { width: 2fr; max-width: 72; }
    #preview-pane {
        width: 3fr; border: round $warning; padding: 0 1; margin: 0 1 0 0;
    }
    #filter { margin: 0 1; }
    #table { height: 1fr; margin: 0 1; }
    .-narrow #menu-right, .-narrow #preview-pane { display: none; }
    .-narrow #menu-left { width: 1fr; }
    .-narrow #picker-left { max-width: 100%; }
    .-narrow #stats-body { layout: vertical; }
    .-narrow #stats-pane { width: 1fr; height: auto; margin: 1 2 0 2; }
    .-narrow #per-exercise-pane { width: 1fr; margin: 0 2 1 2; }
    .modal {
        width: 64; height: auto; padding: 1 2; border: thick $accent;
        background: $panel;
    }
    ModalScreen { align: center middle; }
    .modal-question { margin-bottom: 1; }
    .modal-hint { color: $text-muted; }
    """

    def __init__(
        self,
        sh: Tester,
        cfg: TesterConfig,
        start: Union[None, str, Tuple[str, str]] = None,
    ) -> None:
        super().__init__()
        self.sh, self.cfg, self.start = sh, cfg, start
        self.update_notice: Dict[str, Optional[str]] = {"notice": None}

    def label(self) -> str:
        if hasattr(self.sh, "RANK"):
            return "🐍 Python · %s" % self.sh.RANK.label
        return "🔧 C · Exam Rank 02"

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < NARROW, "-narrow")

    def on_mount(self) -> None:
        self.set_class(self.size.width < NARROW, "-narrow")
        self.theme = THEMES.get(ui.current_theme(), "textual-dark")
        self.update_notice = update_check.start_background_check(
            getattr(self.cfg, "no_update_check", False)
        )
        self.push_screen(MenuScreen())
        if self.start == "exam":
            self.push_screen(ExamScreen())
        elif isinstance(self.start, tuple) and self.start[0] == "practice":
            self.push_screen(PracticeScreen(self.start[1]))

    def start_drill(self) -> None:
        names = [e[2] for e in self.sh.exercise_entries() if e[4]]
        queue = stats.drill_queue(self.sh.TOOL, names, shell_common.DRILL_SIZE)
        if queue:
            self.push_screen(
                PracticeScreen(queue[0], mode="drill", queue=queue, position=0)
            )

    # ── switching between the Python ranks and the C exam ─────────────
    def exam_choices(self) -> List[Tuple[str, str]]:
        from .. import ranks
        from c_exam import bank as c_bank

        choices = [
            (
                "py" + rid,
                "🐍 Python · %s  ·  %d exercises · %d levels"
                % (label, count, levels),
            )
            for rid, label, count, levels in ranks.summary()
        ]
        choices.append(
            (
                "c",
                "🔧 C · Exam Rank 02  ·  %d exercises · %d levels"
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
        keep = {
            k: getattr(self.cfg, k, None)
            for k in ("relaxed", "time_limit", "blind", "no_update_check")
        }
        self.cfg = new_sh.default_config(**keep)
        self.sh = new_sh
        self.notify("Switched to %s" % self.label())
        if isinstance(self.screen, MenuScreen):
            self.screen.refresh_menu()

    # ── feedback ──────────────────────────────────────────────────────
    def open_feedback(
        self, kind: Optional[str], exercise: Optional[str] = None
    ) -> None:
        """Open the prefilled issue form in a browser where one exists; the
        link always goes to the clipboard too (OSC 52, works over ssh)."""
        if not kind:
            return
        from .. import feedback

        url = feedback.issue_url(
            kind, shell_common.tester_label(self.sh), exercise
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
    def sync_hint(self) -> str:
        from .. import settings, sync

        if sync.is_configured(settings.DATA_DIR):
            return "progress + solutions with %s" % sync.remote_url(
                settings.DATA_DIR
            )
        return "not set up — make sync-setup REPO=… (docs/sync.md)"

    def start_sync(self) -> None:
        from .. import settings, sync

        if not sync.is_configured(settings.DATA_DIR):
            self.notify(
                "Sync isn't set up on this device yet — run "
                "`make sync-setup REPO=<your private repo>` "
                "(see docs/sync.md).",
                severity="warning",
                timeout=8,
            )
            return
        self.notify("Syncing with your repo …")
        self.sync_worker()

    @work(thread=True, exclusive=True, group="sync")
    def sync_worker(self) -> None:
        from .. import settings, sync

        try:
            result = sync.sync(
                settings.DATA_DIR, shell_common.sync_dirs(self.sh, self.cfg)
            )
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
