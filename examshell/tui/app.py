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

import os
import random

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from .. import session_store, shell_common, stats, ui, update_check
from ..grader import BankError
from ..version import __version__
from . import render

THEMES = {
    "dark": "textual-dark",
    "light": "textual-light",
    "highcontrast": "textual-dark",
}
WATCH_INTERVAL = 1.0  # seconds between solution-file checks


# ══════════════════════════════════════════════════════════════
#  SMALL MODALS
# ══════════════════════════════════════════════════════════════
class ConfirmModal(ModalScreen):
    """Yes/no question → dismisses with True/False."""

    BINDINGS = [
        Binding("y", "answer(True)", "yes"),
        Binding("n", "answer(False)", "no"),
        Binding("escape", "answer(False)", "no"),
    ]

    def __init__(self, question):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.question, classes="modal-question")
            yield Static(
                "[b]y[/b] yes   ·   [b]n[/b] no", classes="modal-hint"
            )

    def action_answer(self, value):
        self.dismiss(value)


class PromptModal(ModalScreen):
    """One line of text → dismisses with the string (Esc → default)."""

    BINDINGS = [Binding("escape", "cancel", "use default")]

    def __init__(self, question, default=""):
        super().__init__()
        self.question, self.default = question, default

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.question, classes="modal-question")
            yield Input(placeholder=self.default, id="prompt")

    def on_input_submitted(self, event):
        self.dismiss(event.value.strip() or self.default)

    def action_cancel(self):
        self.dismiss(self.default)


class ChoiceModal(ModalScreen):
    """Pick one of [(id, label)] → dismisses with the id (or None)."""

    BINDINGS = [Binding("escape", "cancel", "back")]

    def __init__(self, title, choices):
        super().__init__()
        self.title_text, self.choices = title, choices

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal"):
            yield Static(self.title_text, classes="modal-question")
            yield OptionList(
                *[Option(label, id=cid) for cid, label in self.choices]
            )

    def on_option_list_option_selected(self, event):
        self.dismiss(event.option.id)

    def action_cancel(self):
        self.dismiss(None)


# ══════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════
class MenuScreen(Screen):
    BINDINGS = [Binding("q", "app.quit", "quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="menu-body"):
            with Vertical(id="menu-left"):
                yield Static(id="logo")
                yield OptionList(id="menu")
            yield VerticalScroll(Static(id="glance"), id="menu-right")
        yield Footer()

    def on_mount(self):
        self.refresh_menu()
        self.query_one("#menu", OptionList).focus()

    def on_screen_resume(self):
        self.refresh_menu()

    def refresh_menu(self):
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

    def glance(self):
        sh = self.app.sh
        levels = stats.readiness(sh.TOOL, sh.STANDARD_LEVELS)
        parts = [render.Text("Exam readiness", style="bold"), render.Text("")]
        for level, passed, count, _ in levels:
            line = render.Text("Level %d  " % level, style="yellow")
            line.append_text(render.bar(passed, count, 14))
            line.append("  %d/%d" % (passed, count), style="dim")
            parts.append(line)
        streak = stats.practice_streak(sh.TOOL)
        parts += [
            render.Text(""),
            render.Text(
                "🔥 %d-day practice streak" % streak
                if streak
                else "no practice today yet",
                style="bold" if streak else "dim",
            ),
        ]
        if self.app.update_notice.get("notice"):
            parts += [
                render.Text(""),
                render.Text(
                    "🔔 " + self.app.update_notice["notice"],
                    style="bold magenta",
                ),
            ]
        parts += [
            render.Text(""),
            render.Text("v%s" % __version__, style="dim"),
        ]
        return render.Group(*parts)

    def on_option_list_option_selected(self, event):
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
class PickerScreen(Screen):
    """Filterable table of the exam pool or the training pool."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("slash", "focus_filter", "filter"),
    ]

    def __init__(self, pool):
        super().__init__()
        self.pool = pool

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="type to filter by name or function …", id="filter"
        )
        yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self):
        sh = self.app.sh
        self.entries = (
            sh.exercise_entries()
            if self.pool == "exam"
            else sh.training_entries()
        )
        self.status = stats.exercise_status(
            sh.TOOL, [e[2] for e in self.entries]
        )
        table = self.query_one(DataTable)
        table.add_columns(
            "",
            "level" if self.pool == "exam" else "difficulty",
            "",
            "exercise",
            "function",
        )
        self.fill("")
        table.focus()

    def on_screen_resume(self):
        sh = self.app.sh
        self.status = stats.exercise_status(
            sh.TOOL, [e[2] for e in self.entries]
        )
        self.fill(self.query_one("#filter", Input).value)

    def fill(self, query):
        table = self.query_one(DataTable)
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

    def on_input_changed(self, event):
        self.fill(event.value)

    def on_input_submitted(self, _event):
        self.query_one(DataTable).focus()

    def action_focus_filter(self):
        self.query_one("#filter", Input).focus()

    def on_data_table_row_selected(self, event):
        mode = "practice" if self.pool == "exam" else "train"
        self.app.push_screen(PracticeScreen(event.row_key.value, mode=mode))


# ══════════════════════════════════════════════════════════════
#  THE SPLIT VIEW  ·  subject | results  (practice and exam)
# ══════════════════════════════════════════════════════════════
class SplitScreen(Screen):
    """Subject on the left, grading results on the right. Subclasses decide
    what grading means (practice vs exam)."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status")
        with Horizontal(id="split"):
            yield VerticalScroll(Static(id="subject"), id="subject-pane")
            yield VerticalScroll(Static(id="results"), id="results-pane")
        yield Footer()

    def show_exercise(self, ex_name):
        sh = self.app.sh
        self.ex_name = ex_name
        ex = sh.ALL_EXERCISES[ex_name]
        pane = self.query_one("#subject-pane")
        pane.border_title = "📄 %s" % ex_name
        pane.border_subtitle = shell_common.solution_path(
            sh, ex_name, self.app.cfg
        )
        self.query_one("#subject", Static).update(
            ui.subject_blocks(ex, code_background=None)
        )  # the theme's own code background
        self.set_results(
            render.waiting_view(
                "Write your solution in %s, then press g to grade."
                % shell_common.solution_path(sh, ex_name, self.app.cfg)
            )
        )

    def set_results(self, renderable, title="results"):
        self.query_one("#results", Static).update(renderable)
        self.query_one("#results-pane").border_title = title

    def action_stub(self):
        run = getattr(self, "run", None)  # ExamScreen: the exam's own config
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

    def __init__(self, ex_name, mode="practice", queue=None, position=0):
        super().__init__()
        self.start_ex, self.mode = ex_name, mode
        self.queue, self.position = queue, position
        self.rng = random.Random()
        self.grading = False
        self.watch_timer = None
        self.watch_mtime = None

    def on_mount(self):
        self.show_exercise(self.start_ex)
        self.update_status()

    def update_status(self):
        text = render.Text()
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
    def action_grade(self):
        if self.grading:
            return
        self.grading = True
        self.set_results(
            render.waiting_view("⏳ grading %s …" % self.ex_name), "grading …"
        )
        self.grade_worker(self.ex_name)

    @work(thread=True, exclusive=True)
    def grade_worker(self, ex_name):
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

    def show_error(self, message):
        self.grading = False
        self.set_results(render.Text(message, style="bold red"), "error")

    def show_outcome(self, outcome):
        self.grading = False
        report = outcome.report
        view = render.report_view(
            report, report.function, self.app.cfg.show_fails or 6
        )
        if outcome.hint:
            view = render.Group(
                view, render.Text(""), render.hint_view(outcome.hint)
            )
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
    def _mtime(self):
        try:
            return os.path.getmtime(
                shell_common.solution_path(
                    self.app.sh, self.ex_name, self.app.cfg
                )
            )
        except OSError:
            return None

    def action_toggle_watch(self):
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

    def check_watch(self):
        mtime = self._mtime()
        if mtime is not None and mtime != self.watch_mtime:
            self.watch_mtime = mtime
            self.action_grade()

    def action_feedback(self):
        self.app.open_feedback("exam", self.ex_name)

    def action_next(self):
        if self.queue and self.position + 1 < len(self.queue):
            nxt = self.position + 1
            self.app.switch_screen(
                PracticeScreen(
                    self.queue[nxt],
                    mode="drill",
                    queue=self.queue,
                    position=nxt,
                )
            )


class ExamScreen(SplitScreen):
    """The exam, driving one shell_common.ExamRun."""

    BINDINGS = [
        Binding("g", "grade", "grademe"),
        Binding("t", "stub", "stub"),
        Binding("n", "redraw", "new", show=False),
        Binding("escape", "quit_exam", "quit & save"),
    ]

    def __init__(self):
        super().__init__()
        self.run = None
        self.grading = False
        self.over = False

    def on_mount(self):
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

    def after_resume_question(self, yes, saved):
        if yes:
            self.run.resume(saved)
            self.notify("Resumed at level %d." % self.run.level)
            self.begin()
        else:
            self.run.discard_save()
            self.ask_login()

    def ask_login(self):
        default = self.run.session.login
        self.app.push_screen(PromptModal("Login", default), self.after_login)

    def after_login(self, login):
        self.run.start(login)
        cfg = self.run.cfg
        notes = []
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

    def begin(self):
        self.load_level()
        self.set_interval(1.0, self.tick)

    def load_level(self):
        self.show_exercise(self.run.ensure_exercise())
        self.update_status()

    def update_status(self):
        run = self.run
        self.query_one("#status", Static).update(
            render.exam_status(
                run.session, run.n_levels, run.countdown(), run.level_attempts
            )
        )

    def tick(self):
        if self.over or self.run.session.start_time is None:
            return
        self.update_status()
        if self.run.times_up():
            self.run.discard_save()
            self.finish(passed=False, timed_out=True)

    # ── actions ───────────────────────────────────────────────────────
    def action_grade(self):
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
    def grade_worker(self, ex_name):
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

    def show_error(self, message):
        self.grading = False
        self.set_results(render.Text(message, style="bold red"), "error")

    def show_outcome(self, outcome):
        self.grading = False
        if self.over:
            return
        report = outcome.report
        blind = getattr(self.run.cfg, "blind", False)
        self.set_results(
            render.report_view(
                report,
                report.function,
                self.app.cfg.show_fails or 6,
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

    def action_redraw(self):
        if self.over:
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

    def action_quit_exam(self):
        if self.over:
            self.app.pop_screen()
            return
        self.app.push_screen(
            ConfirmModal(
                "Quit the exam? Your progress is saved and can be resumed."
            ),
            self.after_quit_question,
        )

    def after_quit_question(self, yes):
        if yes and not self.over:
            if self.run.session.start_time is not None:
                self.run.save()
            self.finish(passed=False)

    def finish(self, passed, timed_out=False):
        self.over = True
        result = shell_common.finish_exam(
            self.app.sh, self.run.session, passed, timed_out
        )
        self.app.switch_screen(SummaryScreen(result))


class SummaryScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "menu"),
        Binding("enter", "app.pop_screen", "menu", show=False),
    ]

    def __init__(self, result):
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static(render.exam_result_view(self.result), id="summary"),
            id="summary-pane",
        )
        yield Footer()

    def on_mount(self):
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
class ReadinessScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("d", "drill", "drill my gaps"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(id="readiness"), id="readiness-pane")
        yield Footer()

    def on_mount(self):
        self.refresh_view()

    def on_screen_resume(self):
        self.refresh_view()

    def refresh_view(self):
        sh = self.app.sh
        self.query_one(
            "#readiness-pane"
        ).border_title = "exam readiness — every exercise the exam can draw"
        self.query_one("#readiness", Static).update(
            render.readiness_view(stats.readiness(sh.TOOL, sh.STANDARD_LEVELS))
        )

    def action_drill(self):
        self.app.start_drill()


class StatsScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(id="stats"), id="stats-pane")
        yield Footer()

    def on_mount(self):
        tool = self.app.sh.TOOL
        self.query_one("#stats-pane").border_title = "your history"
        self.query_one("#stats", Static).update(
            render.stats_view(
                stats.summarize(tool),
                stats.daily_activity(tool),
                stats.practice_streak(tool),
                stats.exam_history(tool),
                shell_common.fmt_duration,
            )
        )


# ══════════════════════════════════════════════════════════════
#  THE APP
# ══════════════════════════════════════════════════════════════
class ExamShellApp(App):
    TITLE = "ExamShell"
    CSS = """
    Screen { background: $surface; }
    #menu-body { height: 1fr; }
    #menu-left { width: 3fr; padding: 1 2; }
    #logo { height: 4; content-align: center middle; }
    #menu { height: 1fr; border: round $accent; padding: 0 1; }
    #menu-right {
        width: 2fr; border: round $secondary; padding: 1 2; margin: 1 2 1 0;
    }
    #status { height: 1; padding: 0 1; background: $panel; }
    #split { height: 1fr; }
    #subject-pane { width: 1fr; border: round $warning; padding: 0 1; }
    #results-pane { width: 1fr; border: round $accent; padding: 0 1; }
    #summary-pane, #readiness-pane, #stats-pane {
        border: round $accent; padding: 1 2; margin: 1 2;
    }
    #summary-pane.passed { border: heavy $success; }
    #filter { margin: 0 1; }
    #table { height: 1fr; margin: 0 1; }
    .modal {
        width: 64; height: auto; padding: 1 2; border: thick $accent;
        background: $panel;
    }
    ModalScreen { align: center middle; }
    .modal-question { margin-bottom: 1; }
    .modal-hint { color: $text-muted; }
    """

    def __init__(self, sh, cfg, start=None):
        super().__init__()
        self.sh, self.cfg, self.start = sh, cfg, start
        self.update_notice = {"notice": None}

    def label(self):
        if hasattr(self.sh, "RANK"):
            return "🐍 Python · %s" % self.sh.RANK.label
        return "🔧 C · Exam Rank 02"

    def on_mount(self):
        self.theme = THEMES.get(ui.current_theme(), "textual-dark")
        self.update_notice = update_check.start_background_check(
            getattr(self.cfg, "no_update_check", False)
        )
        self.push_screen(MenuScreen())
        if self.start == "exam":
            self.push_screen(ExamScreen())
        elif isinstance(self.start, tuple) and self.start[0] == "practice":
            self.push_screen(PracticeScreen(self.start[1]))

    def start_drill(self):
        names = [e[2] for e in self.sh.exercise_entries() if e[4]]
        queue = stats.drill_queue(self.sh.TOOL, names, shell_common.DRILL_SIZE)
        if queue:
            self.push_screen(
                PracticeScreen(queue[0], mode="drill", queue=queue, position=0)
            )

    # ── switching between the Python ranks and the C exam ─────────────
    def exam_choices(self):
        from .. import ranks
        from c_exam import examshell as c_shell

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
                % (len(c_shell.EXERCISES), c_shell.N_LEVELS),
            )
        )
        return choices

    def switch_exam(self, choice):
        """Point the whole app at another tester (and rank). Exam-wide
        choices made on the command line (--relaxed, --time-limit, --blind)
        carry over; everything else comes from that tester's own defaults
        and your saved settings."""
        if not choice:
            return
        if choice == "c":
            from c_exam import examshell as new_sh
        else:
            from .. import examshell as new_sh

            new_sh.use_rank(choice[2:])
        keep = {
            k: getattr(self.cfg, k, None)
            for k in ("relaxed", "time_limit", "blind", "no_update_check")
        }
        self.cfg = new_sh.default_config(**keep)
        self.sh = new_sh
        self.notify("Switched to %s" % self.label())
        self.screen.refresh_menu()

    # ── feedback ──────────────────────────────────────────────────────
    def open_feedback(self, kind, exercise=None):
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
    def sync_hint(self):
        from .. import settings, sync

        if sync.is_configured(settings.DATA_DIR):
            return "progress + solutions with %s" % sync.remote_url(
                settings.DATA_DIR
            )
        return "not set up — make sync-setup REPO=… (docs/sync.md)"

    def start_sync(self):
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
    def sync_worker(self):
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

    def sync_done(self, result):
        self.notify(result.summary(), title="✔ Synced", timeout=8)
        for backup in result.backups:
            self.notify("older version kept at %s" % backup, timeout=10)
        if isinstance(self.screen, MenuScreen):
            self.screen.refresh_menu()
