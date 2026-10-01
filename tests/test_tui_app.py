#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The full-screen app (examshell/tui/app.py), driven headless through Textual's
test pilot. Skipped where Textual isn't installed (it's optional)."""

import argparse
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

from examshell import examshell as py_shell
from examshell import report_export, session_store, settings, shell_common, stats, tui
from examshell.grader import Report

HAVE_TEXTUAL = tui.available()
if HAVE_TEXTUAL:
    from examshell.tui import app as tui_app

GOOD_INTER = ("def inter(s1, s2):\n    out = ''\n    for c in s1:\n"
              "        if c in s2 and c not in out:\n            out += c\n    return out\n")


def _cfg(rendu, **overrides):
    values = dict(rendu=rendu, timeout=3, fuzz=5, strict_imports=False, strict=False,
                  show_fails=4, diff=False, seed=1, relaxed=False, time_limit=None,
                  no_update_check=True, blind=False)
    values.update(overrides)
    return py_shell.Config(argparse.Namespace(**values))


class _Isolated(object):
    """Every file the app writes goes to a throwaway directory."""

    def isolate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.rendu = os.path.join(tmp.name, "rendu")
        os.makedirs(self.rendu)
        for module, name, value in (
                (stats, "STATS_PATH", os.path.join(tmp.name, "stats.jsonl")),
                (stats, "DATA_DIR", tmp.name),
                (session_store, "DATA_DIR", tmp.name),
                (report_export, "REPORTS_DIR", os.path.join(tmp.name, "reports")),
                (settings, "DATA_DIR", tmp.name)):
            patcher = mock.patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiAppTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.isolate()

    async def test_menu_to_practice_and_grade(self):
        with open(os.path.join(self.rendu, "py_inter.py"), "w") as fh:
            fh.write(GOOD_INTER)
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)) as pilot:
            self.assertIsInstance(app.screen, tui_app.MenuScreen)
            await pilot.press("down", "enter")                  # Practice
            self.assertIsInstance(app.screen, tui_app.PickerScreen)
            await pilot.press("slash", *"py_inter", "enter", "enter")
            self.assertIsInstance(app.screen, tui_app.PracticeScreen)
            self.assertEqual(app.screen.ex_name, "py_inter")
            await pilot.press("g")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(app.screen.query_one("#results-pane").border_title, "✔ passed")
        self.assertEqual(stats.exercise_status("py", ["py_inter"])["py_inter"]["status"],
                         "passed")

    async def test_watch_mode_regrades_on_save(self):
        path = os.path.join(self.rendu, "py_inter.py")
        with open(path, "w") as fh:
            fh.write("def inter(s1, s2):\n    return ''\n")
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start=("practice", "py_inter"))
        with mock.patch.object(tui_app, "WATCH_INTERVAL", 0.1):
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("w")
                with open(path, "w") as fh:
                    fh.write(GOOD_INTER)
                os.utime(path, (time.time() + 5, time.time() + 5))
                for _ in range(40):
                    await pilot.pause(0.1)
                    await app.workers.wait_for_complete()
                    if app.screen.query_one("#results-pane").border_title == "✔ passed":
                        break
                self.assertEqual(app.screen.query_one("#results-pane").border_title,
                                 "✔ passed")

    async def test_exam_login_refused_new_and_quit_to_summary(self):
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.PromptModal)
            await pilot.press(*"alice", "enter")
            exam = app.screen
            self.assertIsInstance(exam, tui_app.ExamScreen)
            first = exam.run.current_ex
            await pilot.press("n")                                  # not in realistic mode
            self.assertEqual(exam.run.current_ex, first)
            await pilot.press("g")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(exam.run.session.attempts, 1)
            await pilot.press("escape", "y")
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.SummaryScreen)
            self.assertFalse(app.screen.result.passed)
        saved = session_store.load("py")
        self.assertEqual((saved["login"], saved["current_ex"]), ("alice", first))

    async def test_passing_every_level_ends_on_a_passed_summary(self):
        report = Report("x", "f")
        report.total = report.passed = 3

        def always_pass(sh, ex_name, rng, cfg, mode="practice"):
            return shell_common.GradeOutcome(report, "unused")

        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start="exam")
        with mock.patch.object(tui_app.shell_common, "grade", side_effect=always_pass):
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("enter")                          # default login
                for _ in range(py_shell.N_LEVELS):
                    await pilot.press("g")
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                self.assertIsInstance(app.screen, tui_app.SummaryScreen)
                self.assertTrue(app.screen.result.passed)
        self.assertIsNone(session_store.load("py"))
        self.assertEqual(len(stats.exam_history("py")), 1)

    async def test_readiness_and_stats_screens_open(self):
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        async with app.run_test(size=(120, 36)) as pilot:
            app.push_screen(tui_app.ReadinessScreen())
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.ReadinessScreen)
            await pilot.press("escape")
            app.push_screen(tui_app.StatsScreen())
            await pilot.pause()
            self.assertIsInstance(app.screen, tui_app.StatsScreen)


@unittest.skipUnless(HAVE_TEXTUAL, "Textual not installed (optional)")
class TuiSwitchAndSyncTests(_Isolated, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.isolate()

    async def _open_menu_item(self, app, pilot, item_id):
        menu = app.screen.query_one("#menu")
        index = [menu.get_option_at_index(i).id for i in range(menu.option_count)].index(item_id)
        menu.highlighted = index
        await pilot.press("enter")
        await pilot.pause()

    async def test_switch_from_python_to_c_and_to_rank_05(self):
        from c_exam import examshell as c_shell
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu, relaxed=True))
        async with app.run_test(size=(120, 36)) as pilot:
            await self._open_menu_item(app, pilot, "switch")
            self.assertIsInstance(app.screen, tui_app.ChoiceModal)
            app.screen.dismiss("c")
            await pilot.pause()
            self.assertIs(app.sh, c_shell)
            self.assertEqual(app.cfg.rendu, "c_rendu")
            self.assertTrue(app.cfg.relaxed)                # carried over
            self.assertIn("C · Exam Rank 02", app.label())
            app.switch_exam("py05")
            self.assertIs(app.sh, py_shell)
            self.assertEqual(py_shell.RANK.id, "05")
        py_shell.use_rank("03")

    async def test_feedback_from_practice_prefills_the_exercise(self):
        from examshell import feedback
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu), start=("practice", "py_inter"))
        with mock.patch.object(feedback, "open_in_browser", return_value=False) as opened:
            async with app.run_test(size=(120, 36)) as pilot:
                await pilot.press("f")
                await pilot.pause()
        self.assertIn("exercise=py_inter", opened.call_args[0][0])

    async def test_sync_without_setup_warns_instead_of_failing(self):
        app = tui_app.ExamShellApp(py_shell, _cfg(self.rendu))
        with mock.patch.object(tui_app.App, "notify") as notify:
            async with app.run_test(size=(120, 36)) as pilot:
                await self._open_menu_item(app, pilot, "sync")
        self.assertTrue(any("sync-setup" in str(c) for c in notify.call_args_list))


class TuiFallbackTests(unittest.TestCase):
    def test_falls_back_with_a_reason_when_unavailable(self):
        args = argparse.Namespace(exam=False, practice=None)
        with mock.patch.object(tui, "available", return_value=False), \
             mock.patch.object(shell_common.ui, "warn") as warn:
            self.assertIsNone(shell_common.run_tui(py_shell, _cfg("r"), args))
        self.assertIn("normal interface", warn.call_args[0][0])

    def test_reason_names_the_python_version_or_textual(self):
        reason = tui.why_unavailable()
        self.assertTrue("Python 3.9" in reason or "textual" in reason.lower())
        if sys.version_info < (3, 9):
            self.assertFalse(tui.available())


if __name__ == "__main__":
    unittest.main()
