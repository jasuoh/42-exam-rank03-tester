#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The full-screen app (examshell/tui/app.py), driven headless through
Textual's test pilot. Skipped where Textual isn't installed (it's optional)."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import unittest
from typing import Any, Optional, TYPE_CHECKING
from unittest import mock

from examshell import examshell as py_shell
from examshell import (
    session_store,
    settings,
    shell_common,
    stats,
    tui,
    ui,
)
from examshell.grader import Report
from examshell.tui import clipboard

HAVE_TEXTUAL = tui.available()
if HAVE_TEXTUAL:
    from textual.app import App
    from textual.coordinate import Coordinate
    from textual.widgets import DataTable, OptionList

    from examshell.tui import app as tui_app

GOOD_INTER = (
    "def inter(s1, s2):\n    out = ''\n    for c in s1:\n"
    "        if c in s2 and c not in out:\n"
    "            out += c\n    return out\n"
)


def _cfg(rendu: str, **overrides: Any) -> py_shell.Config:
    values = dict(
        rendu=rendu,
        timeout=3,
        fuzz=5,
        strict_imports=False,
        strict=False,
        show_fails=4,
        diff=False,
        seed=1,
        relaxed=False,
        time_limit=None,
        no_update_check=True,
        blind=False,
    )
    values.update(overrides)
    return py_shell.Config(argparse.Namespace(**values))


# A mixin for TestCase subclasses: the type checker sees TestCase's
# addCleanup() through it, at runtime it stays a plain object.
if TYPE_CHECKING:
    _Base = unittest.TestCase
else:
    _Base = object


class _Isolated(_Base):
    """Every file the app writes goes to a throwaway directory."""

    def isolate(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.rendu = os.path.join(tmp.name, "rendu")
        os.makedirs(self.rendu)
        for module, name, value in (
            (stats, "STATS_PATH", os.path.join(tmp.name, "stats.jsonl")),
            (stats, "DATA_DIR", tmp.name),
            (session_store, "DATA_DIR", tmp.name),
            (settings, "DATA_DIR", tmp.name),
            (settings, "CONFIG_PATH", os.path.join(tmp.name, "config.json")),
        ):
            patcher = mock.patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # and nothing reaches the real system clipboard
        no_clipboard = mock.patch.object(
            clipboard, "_tools", return_value=None
        )
        no_clipboard.start()
        self.addCleanup(no_clipboard.stop)


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiAppTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.isolate()

    async def test_menu_to_practice_and_grade(self) -> None:
        with open(os.path.join(self.rendu, "py_inter.py"), "w") as fh:
            fh.write(GOOD_INTER)
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)) as pilot:
            self.assertIsInstance(app.screen, tui_app.MenuScreen)
            await pilot.press("down", "enter")  # Practice
            self.assertIsInstance(app.screen, tui_app.PickerScreen)
            await pilot.press("slash", *"py_inter", "enter", "enter")
            screen = app.screen
            assert isinstance(screen, tui_app.PracticeScreen)
            self.assertEqual(screen.ex_name, "py_inter")
            await pilot.press("g")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(
                app.screen.query_one("#results-pane").border_title, "grademe"
            )
            self.assertIn(
                "✔ PASSED",
                str(
                    app.screen.query_one("#results", tui_app.Copyable).render()
                ),
            )
            self.assertEqual(len(screen.log_entries), 1)
            self.assertIn(
                "graded 1×",
                str(app.screen.query_one("#results-pane").border_subtitle),
            )
        self.assertEqual(
            stats.exercise_status("py", ["py_inter"])["py_inter"]["status"],
            "passed",
        )

    async def test_side_panels_hide_on_narrow_terminals(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(140, 36)) as pilot:
            self.assertTrue(app.screen.query_one("#menu-right").display)
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            self.assertFalse(app.screen.query_one("#menu-right").display)

    async def test_watch_mode_regrades_on_save(self) -> None:
        path = os.path.join(self.rendu, "py_inter.py")
        with open(path, "w") as fh:
            fh.write("def inter(s1, s2):\n    return ''\n")
        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu), start=("practice", "py_inter")
        )
        with mock.patch.object(tui_app, "WATCH_INTERVAL", 0.1):
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("w")
                with open(path, "w") as fh:
                    fh.write(GOOD_INTER)
                os.utime(path, (time.time() + 5, time.time() + 5))
                screen = app.screen
                assert isinstance(screen, tui_app.PracticeScreen)
                for _ in range(40):
                    await pilot.pause(0.1)
                    await app.workers.wait_for_complete()
                    if screen.outcome and screen.outcome.report.ok:
                        break
                assert screen.outcome is not None
                self.assertTrue(screen.outcome.report.ok)

    async def test_exam_login_refused_new_and_quit_to_summary(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.PromptModal)
            await pilot.press(*"alice", "enter")
            exam = app.screen
            assert isinstance(exam, tui_app.ExamScreen)
            first = exam.run.current_ex
            await pilot.press("n")  # not in realistic mode
            self.assertEqual(exam.run.current_ex, first)
            await pilot.press("g")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(exam.run.session.attempts, 1)
            await pilot.press("escape", "y")
            await pilot.pause()
            summary = app.screen
            assert isinstance(summary, tui_app.SummaryScreen)
            self.assertFalse(summary.result.passed)
        saved = session_store.load("py")
        assert saved is not None
        self.assertEqual(
            (saved["login"], saved["current_ex"]), ("alice", first)
        )

    async def test_esc_on_resume_and_login_goes_back_to_the_menu(
        self,
    ) -> None:
        run = shell_common.ExamRun(py_shell, _cfg(self.rendu))
        run.start("alice")
        run.ensure_exercise()
        run.save()
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.ConfirmModal)
            await pilot.press("escape")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.MenuScreen)
        self.assertIsNotNone(session_store.load("py"))  # kept

        session_store.clear("py")
        solution = os.path.join(self.rendu, "py_inter.py")
        with open(solution, "w") as fh:
            fh.write(GOOD_INTER)
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.PromptModal)
            await pilot.press("escape")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.MenuScreen)
        self.assertTrue(os.path.isfile(solution))  # nothing archived
        self.assertIsNone(session_store.load("py"))  # nothing started

    async def test_passing_every_level_ends_on_a_passed_summary(self) -> None:
        report = Report("x", "f")
        report.total = report.passed = 3

        def always_pass(
            sh: object,
            ex_name: str,
            rng: object,
            cfg: object,
            mode: str = "practice",
        ) -> shell_common.GradeOutcome:
            return shell_common.GradeOutcome(report, "unused")

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        with mock.patch.object(shell_common, "grade", side_effect=always_pass):
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("enter")  # default login
                for _ in range(py_shell.N_LEVELS):
                    await pilot.press("g")
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                summary = app.screen
                assert isinstance(summary, tui_app.SummaryScreen)
                self.assertTrue(summary.result.passed)
        self.assertIsNone(session_store.load("py"))
        self.assertEqual(len(stats.exam_history("py")), 1)

    async def test_redraw_is_ignored_while_grading(self) -> None:
        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu, relaxed=True), start="exam"
        )
        async with app.run_test(size=(140, 36)) as pilot:
            await pilot.press(*"bob", "enter")
            exam = app.screen
            assert isinstance(exam, tui_app.ExamScreen)
            first = exam.run.current_ex
            exam.grading = True  # a grade still running in its worker
            await pilot.press("n")
            self.assertEqual(exam.run.current_ex, first)

    async def test_picker_preview_follows_the_cursor(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(140, 36)) as pilot:
            await pilot.press("down", "enter")  # Practice
            picker = app.screen
            await pilot.press("down", "down")
            await pilot.pause()
            table: DataTable[str] = picker.query_one("#table", DataTable)
            name = table.coordinate_to_cell_key(Coordinate(2, 0)).row_key.value
            self.assertEqual(
                picker.query_one("#preview-pane").border_title, name
            )
            await pilot.press("enter")  # open it, come back
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(table.cursor_row, 2)
            await pilot.press("slash", *"zzqqxx")  # no match clears it
            await pilot.pause()
            self.assertIsNone(picker.query_one("#preview-pane").border_title)

    async def test_d_toggles_the_full_details(self) -> None:
        from examshell.grader import Failure

        report = Report("py_inter", "inter")
        report.total, report.passed = 9, 0
        report.failures = [
            Failure(["a%d" % i, "b"], "", "'x'") for i in range(9)
        ]
        outcome = shell_common.GradeOutcome(report, "unused")
        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu), start=("practice", "py_inter")
        )
        with mock.patch.object(shell_common, "grade", return_value=outcome):
            async with app.run_test(size=(100, 40)) as pilot:
                await pilot.pause()
                await pilot.press("g")
                await app.workers.wait_for_complete()
                await pilot.pause()
                results = app.screen.query_one("#results", tui_app.Copyable)
                self.assertIn("6 more", str(results.render()))
                await pilot.press("d")
                await pilot.pause()
                full = str(results.render())
                self.assertIn("expected", full)
                self.assertIn("inter('a8', 'b')", full)
                await pilot.press("d")
                await pilot.pause()
                self.assertIn("6 more", str(results.render()))

    async def test_e_opens_the_solution_in_vs_code(self) -> None:
        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu), start=("practice", "py_inter")
        )
        path = os.path.join(self.rendu, "py_inter.py")
        with mock.patch(
            "shutil.which", return_value="/usr/bin/code"
        ), mock.patch("subprocess.Popen") as popen:
            async with app.run_test(size=(100, 36)) as pilot:
                await pilot.pause()
                await pilot.press("e")
                await pilot.pause()
        self.assertTrue(os.path.isfile(path))  # a stub first
        self.assertEqual(popen.call_args[0][0], ["code", path])

    def test_editor_falls_back_to_editor_env(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(
                os.environ, {"VISUAL": "", "EDITOR": "vim -p"}
            ):
                self.assertEqual(
                    tui_app.editor_command("x.py"), ["vim", "-p", "x.py"]
                )
            with mock.patch.dict(os.environ, {"VISUAL": "", "EDITOR": ""}):
                self.assertIsNone(tui_app.editor_command("x.py"))

    async def test_drill_keeps_its_session_log_across_exercises(self) -> None:
        report = Report("x", "f")
        report.total = report.passed = 1
        outcome = shell_common.GradeOutcome(report, "unused")
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with mock.patch.object(shell_common, "grade", return_value=outcome):
            async with app.run_test(size=(140, 36)) as pilot:
                app.push_screen(
                    tui_app.PracticeScreen(
                        "py_inter",
                        mode="drill",
                        queue=["py_inter", "py_inter"],
                    )
                )
                await pilot.pause()
                await pilot.press("g")
                await app.workers.wait_for_complete()
                await pilot.pause()
                await pilot.press("n")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, tui_app.PracticeScreen)
                self.assertEqual(screen.position, 1)
                self.assertEqual(len(screen.log_entries), 1)

    async def test_subject_and_results_can_be_copied(self) -> None:
        with open(os.path.join(self.rendu, "py_inter.py"), "w") as fh:
            fh.write(GOOD_INTER)
        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu), start=("practice", "py_inter")
        )
        async with app.run_test(size=(140, 36)) as pilot:
            await pilot.pause()
            for wid, piece in (
                ("#subject", "Assignment name"),
                ("#results", "press g to grade"),
            ):
                app.screen.query_one(wid).text_select_all()
                await pilot.pause()
                copied = app.screen.get_selected_text() or ""
                self.assertIn(piece, copied)
                self.assertFalse(
                    any(line != line.rstrip() for line in copied.split("\n"))
                )
                app.screen.clear_selection()

    async def test_menu_has_the_five_entries(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)):
            menu = app.screen.query_one("#menu", OptionList)
            self.assertEqual(
                [
                    menu.get_option_at_index(i).id
                    for i in range(menu.option_count)
                ],
                ["exam", "practice", "progress", "switch", "quit"],
            )

    async def test_progress_screen_leads_to_the_gaps(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)) as pilot:
            app.push_screen(tui_app.ProgressScreen())
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.ProgressScreen)
            await pilot.press("p")
            await pilot.pause()
            picker = app.screen
            assert isinstance(picker, tui_app.PickerScreen)
            self.assertEqual(picker.pool, "gaps")
            # nothing tried yet: the gaps are the first exam exercises,
            # and picking one starts a drill through all of them
            await pilot.press("enter")
            await pilot.pause()
            drill = app.screen
            assert isinstance(drill, tui_app.PracticeScreen)
            self.assertEqual(drill.mode, "drill")
            self.assertEqual(len(drill.queue or []), shell_common.DRILL_SIZE)

    async def test_picker_tabs_switch_the_pool(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)) as pilot:
            app.push_screen(tui_app.PickerScreen())
            await pilot.pause()
            picker = app.screen
            assert isinstance(picker, tui_app.PickerScreen)
            exam_names = {e[2] for e in picker.entries}
            # only what the exam can draw
            self.assertEqual(
                exam_names,
                {
                    n
                    for pool in py_shell.STANDARD_LEVELS.values()
                    for n in pool
                },
            )
            await pilot.press("tab", "tab")  # exam → gaps → extra
            await pilot.pause()
            self.assertEqual(picker.pool, "extra")
            extra_names = {e[2] for e in picker.entries}
            self.assertTrue(extra_names)
            self.assertFalse(exam_names & extra_names)
            table: DataTable[str] = picker.query_one("#table", DataTable)
            table.move_cursor(row=table.row_count - 1)  # a training one
            await pilot.press("enter")
            await pilot.pause()
            practice = app.screen
            assert isinstance(practice, tui_app.PracticeScreen)
            self.assertEqual(practice.mode, "train")


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiSwitchAndSyncTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.isolate()

    async def _open_menu_item(
        self, app: tui_app.ExamShellApp, pilot: Any, item_id: str
    ) -> None:
        menu = app.screen.query_one("#menu", OptionList)
        index = [
            menu.get_option_at_index(i).id for i in range(menu.option_count)
        ].index(item_id)
        menu.highlighted = index
        await pilot.press("enter")
        await pilot.pause()

    async def test_switch_from_python_to_c_and_to_rank_05(self) -> None:
        from c_exam import examshell as c_shell

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu, relaxed=True))
        async with app.run_test(size=(120, 36)) as pilot:
            await self._open_menu_item(app, pilot, "switch")
            self.assertIsInstance(app.screen, tui_app.ChoiceModal)
            app.screen.dismiss("c")
            await pilot.pause()
            self.assertIs(app.sh, c_shell)
            self.assertEqual(app.cfg.rendu, "c_rendu")
            self.assertTrue(app.cfg.relaxed)  # carried over
            self.assertIn("C · Exam Rank 02", app.label())
            self.assertEqual(settings.load_config()["tester"], "c")
            app.switch_exam("py05")
            self.assertIs(app.sh, py_shell)
            self.assertEqual(py_shell.RANK.id, "05")
            # remembered for the next `make`
            self.assertEqual(
                settings.load_config(), {"tester": "py", "rank": "05"}
            )
        py_shell.use_rank("03")

    async def test_feedback_from_practice_prefills_the_exercise(self) -> None:
        from examshell import feedback

        app = tui_app.ExamShellApp(
            py_shell, _cfg(self.rendu), start=("practice", "py_inter")
        )
        with mock.patch.object(
            feedback, "open_in_browser", return_value=False
        ) as opened:
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("f")
                await pilot.pause()
        self.assertIn("exercise=py_inter", opened.call_args[0][0])

    async def test_sync_without_setup_warns_instead_of_failing(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with mock.patch.object(App, "notify") as notify:
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("s")
                await pilot.pause()
        self.assertTrue(
            any("Settings (o)" in str(c) for c in notify.call_args_list)
        )


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiSettingsTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.isolate()
        config = mock.patch.object(
            settings, "CONFIG_PATH", os.path.join(self.rendu, "config.json")
        )
        config.start()
        self.addCleanup(config.stop)

    async def _change(
        self, app: Any, pilot: Any, key: str, text: Optional[str]
    ) -> None:
        menu = app.screen.query_one("#settings", OptionList)
        ids = [
            menu.get_option_at_index(i).id for i in range(menu.option_count)
        ]
        menu.highlighted = ids.index(key)
        await pilot.press("enter")
        await pilot.pause()
        if text is not None:
            await pilot.press(*text, "enter")
            await pilot.pause()

    async def test_settings_are_saved_and_applied(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(100, 36)) as pilot:
            await pilot.press("o")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.SettingsScreen)
            await self._change(app, pilot, "time_limit", "90")
            await self._change(app, pilot, "timeout", "7")
            await self._change(app, pilot, "fuzz", "x")  # not a number
            await self._change(app, pilot, "auto_sync", None)  # a toggle
            self.assertEqual(app.cfg.time_limit, 90)
            self.assertEqual(app.cfg.timeout, 7)
            self.assertEqual(app.cfg.fuzz, 5)  # unchanged
            await self._change(app, pilot, "time_limit", "0")
            self.assertIsNone(app.cfg.time_limit)
        saved = settings.load_config()
        self.assertEqual(saved["timeout"], 7)
        self.assertTrue(saved["auto_sync"])
        self.assertNotIn("time_limit", saved)  # None isn't stored
        self.assertNotIn("fuzz", saved)
        # and a new session starts with them
        self.assertEqual(py_shell.default_config().timeout, 7)

    async def test_a_compiler_not_on_path_is_refused(self) -> None:
        from c_exam import examshell as c_shell

        cfg = c_shell.default_config(no_update_check=True)
        app = tui_app.ExamShellApp(c_shell, cfg)
        async with app.run_test(size=(100, 36)) as pilot:
            await pilot.press("o")
            await pilot.pause()
            await self._change(app, pilot, "cc", "clnag-not-there")
            self.assertEqual(cfg.cc, "cc")
        self.assertNotIn("cc", settings.load_config())


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiFirstImpressionTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    """The welcome question, `?` and the crash log."""

    def setUp(self) -> None:
        self.isolate()
        config = mock.patch.object(
            settings, "CONFIG_PATH", os.path.join(self.rendu, "config.json")
        )
        config.start()
        self.addCleanup(config.stop)
        self.addCleanup(py_shell.use_rank)

    async def test_the_first_start_asks_which_exam(self) -> None:
        from c_exam import examshell as c_shell

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), ask_exam=True)
        async with app.run_test(size=(100, 36)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.ChoiceModal)
            app.screen.dismiss("c")
            await pilot.pause()
            self.assertIs(app.sh, c_shell)
        self.assertEqual(settings.load_config()["tester"], "c")

    async def test_esc_at_the_welcome_keeps_the_default(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), ask_exam=True)
        async with app.run_test(size=(100, 36)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.MenuScreen)
        self.assertEqual(
            settings.load_config(), {"tester": "py", "rank": "03"}
        )

    async def test_question_mark_lists_the_keys(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.press("question_mark")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.HelpModal)
            await pilot.press("escape")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.MenuScreen)

    async def test_an_unexpected_error_lands_in_crash_log(self) -> None:
        from examshell.tui import crashlog

        def boom() -> None:
            raise ZeroDivisionError("on purpose")

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with self.assertRaises(ZeroDivisionError):
            async with app.run_test(size=(100, 36)) as pilot:
                app.call_later(boom)
                await pilot.pause()
        log = crashlog.pending()
        assert log is not None
        self.assertIn("ZeroDivisionError: on purpose", log)

    async def test_a_worker_crash_logs_where_it_broke(self) -> None:
        from examshell.tui import crashlog

        def boom() -> None:
            raise RuntimeError("boom in a worker")

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with self.assertRaises(Exception):
            async with app.run_test(size=(100, 36)) as pilot:
                app.run_worker(boom, thread=True)
                await pilot.pause(0.2)
        log = crashlog.pending()
        assert log is not None
        self.assertIn("RuntimeError: boom in a worker", log)
        self.assertIn("in boom", log)  # the frame, not just the summary

    async def test_a_crash_is_logged_and_offered_as_a_bug_report(
        self,
    ) -> None:
        from examshell import feedback
        from examshell.tui import crashlog

        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            crashlog.record(exc, "PracticeScreen")
        log = crashlog.pending()
        assert log is not None
        self.assertIn("RuntimeError: boom", log)
        self.assertIn("where: PracticeScreen", log)
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with mock.patch.object(
            feedback, "open_in_browser", return_value=True
        ) as opened:
            async with app.run_test(size=(100, 36)) as pilot:
                await pilot.pause()
                self.assertIsInstance(app.screen, tui_app.ConfirmModal)
                await pilot.press("y")
                await pilot.pause()
        self.assertIn("RuntimeError", opened.call_args[0][0])
        self.assertIsNone(crashlog.pending())  # answered: not asked again


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiClipboardTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.isolate()

    async def test_copy_and_paste_use_the_system_clipboard(self) -> None:
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with mock.patch.object(
            clipboard, "copy", return_value=True
        ) as copy, mock.patch.object(clipboard, "paste", return_value="sys"):
            app.copy_to_clipboard("hello")
            copy.assert_called_once_with("hello")
            self.assertEqual(app.clipboard, "sys")
        # no system clipboard here: what was copied inside the app
        self.assertEqual(app.clipboard, "hello")


class TuiFallbackTests(unittest.TestCase):
    def test_falls_back_with_a_reason_when_unavailable(self) -> None:
        args = argparse.Namespace(exam=False, practice=None)
        with mock.patch.object(
            tui, "available", return_value=False
        ), mock.patch.object(ui, "warn") as warn:
            self.assertIsNone(shell_common.run_tui(py_shell, _cfg("r"), args))
        self.assertIn("normal interface", warn.call_args[0][0])

    def test_reason_names_the_python_version_or_textual(self) -> None:
        reason = tui.why_unavailable()
        self.assertTrue("Python 3.9" in reason or "textual" in reason.lower())
        if sys.version_info < (3, 9):
            self.assertFalse(tui.available())


if __name__ == "__main__":
    unittest.main()
