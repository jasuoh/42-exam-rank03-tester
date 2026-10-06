#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for examshell/shell_common.py's engine layer — ExamRun and
grade(), the I/O-free core both testers' line-based UI (and a future
full-screen one) drive. Run against both tester modules, since each
supplies its own hooks."""

import argparse
import os
import random
import tempfile
import unittest
from unittest import mock

from c_exam import examshell as c_shell
from examshell import examshell as py_shell
from examshell import session_store, shell_common, stats
from examshell.grader import Report


def _cfg(sh, **overrides):
    values = dict(
        rendu="unused-rendu",
        timeout=3,
        fuzz=0,
        strict_imports=False,
        strict=False,
        show_fails=4,
        diff=False,
        seed=7,
        relaxed=False,
        blind=False,
        time_limit=None,
        cc="cc",
        strict_norm=False,
        valgrind=False,
        strict_valgrind=False,
        strict_forbidden=False,
    )
    values.update(overrides)
    return sh.Config(argparse.Namespace(**values))


class _TempDataDir(unittest.TestCase):
    """Point every file the engine writes at a throwaway directory."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for module, name, value in (
            (stats, "STATS_PATH", os.path.join(tmp.name, "stats.jsonl")),
            (stats, "DATA_DIR", tmp.name),
            (session_store, "DATA_DIR", tmp.name),
        ):
            patcher = mock.patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)


class ExamRunTests(_TempDataDir):
    SHELLS = (py_shell, c_shell)

    def test_levels_advance_only_by_passing(self):
        for sh in self.SHELLS:
            with self.subTest(tester=sh.TOOL):
                run = shell_common.ExamRun(sh, _cfg(sh))
                run.start("alice")
                first = run.ensure_exercise()
                self.assertIn(first, sh.STANDARD_LEVELS[1])
                self.assertEqual(
                    run.ensure_exercise(), first
                )  # stable until passed
                run.begin_attempt()
                run.begin_attempt()
                self.assertFalse(run.pass_level())
                self.assertEqual(run.level, 2)
                self.assertEqual(run.session.history[0][:3], (1, first, 2))
                self.assertIn(run.ensure_exercise(), sh.STANDARD_LEVELS[2])

    def test_last_level_finishes_the_run(self):
        sh = c_shell
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start()
        for _ in range(sh.N_LEVELS):
            run.ensure_exercise()
            run.begin_attempt()
            last = run.pass_level()
        self.assertTrue(last)
        self.assertTrue(run.finished)
        self.assertEqual(run.session.score(), 100)

    def test_same_seed_same_exam(self):
        def exercises(sh):
            run = shell_common.ExamRun(sh, _cfg(sh, seed=99))
            run.start()
            drawn = []
            while not run.finished:
                drawn.append(run.ensure_exercise())
                run.grade_rng.random()  # grading must not shift draws
                run.pass_level()
            return drawn

        for sh in self.SHELLS:
            with self.subTest(tester=sh.TOOL):
                self.assertEqual(exercises(sh), exercises(sh))

    def test_redraw_only_when_relaxed(self):
        sh = py_shell
        strict = shell_common.ExamRun(sh, _cfg(sh))
        strict.start()
        strict.ensure_exercise()
        self.assertFalse(strict.can_redraw)
        self.assertFalse(strict.redraw())

        relaxed = shell_common.ExamRun(sh, _cfg(sh, relaxed=True))
        relaxed.start()
        before = relaxed.ensure_exercise()
        relaxed.begin_attempt()
        self.assertTrue(relaxed.redraw())
        self.assertEqual(relaxed.level_attempts, 0)
        if len(sh.STANDARD_LEVELS[1]) > 1:
            self.assertNotEqual(relaxed.current_ex, before)

    def test_exam_config_forces_the_testers_strict_flags(self):
        self.assertTrue(
            shell_common.ExamRun(py_shell, _cfg(py_shell)).cfg.strict_imports
        )
        c_cfg = shell_common.ExamRun(c_shell, _cfg(c_shell)).cfg
        self.assertTrue(c_cfg.strict_norm and c_cfg.strict_forbidden)

    def test_save_and_resume_round_trip(self):
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start("bob")
        run.ensure_exercise()
        run.pass_level()
        current = run.ensure_exercise()
        run.begin_attempt()
        run.save()

        resumed = shell_common.ExamRun(sh, _cfg(sh))
        resumed.resume(session_store.load(sh.TOOL))
        self.assertTrue(resumed.resumed)
        self.assertEqual((resumed.session.login, resumed.level), ("bob", 2))
        self.assertEqual(resumed.ensure_exercise(), current)
        self.assertEqual(resumed.level_attempts, 1)
        # the draw RNG continues where it left off
        self.assertEqual(resumed.rng.random(), run.rng.random())

    def test_time_limit(self):
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh, time_limit=1))
        with mock.patch.object(shell_common.time, "time", return_value=1000.0):
            run.start()
        with mock.patch.object(shell_common.time, "time", return_value=1030.0):
            self.assertFalse(run.times_up())
            self.assertIn("00:00:30 left", run.countdown())
        with mock.patch.object(shell_common.time, "time", return_value=1060.0):
            self.assertTrue(run.times_up())


class GradeTests(_TempDataDir):
    """grade(): no output at all — Report, stats, badges and hint as data."""

    def _job(self, ok):
        report = Report("x", "f")
        report.total, report.passed = 3, 3 if ok else 1
        return shell_common.GradingJob(3, lambda: report)

    def test_records_and_returns_an_outcome(self):
        sh = py_shell
        with mock.patch.object(
            sh, "prepare_grading", return_value=self._job(True)
        ), mock.patch.object(shell_common.ui, "report") as rendered:
            outcome = shell_common.grade(
                sh, "py_inter", random.Random(0), _cfg(sh)
            )
        rendered.assert_not_called()
        self.assertTrue(outcome.ok)
        self.assertTrue(
            outcome.filepath.endswith(
                os.path.join("unused-rendu", "py_inter.py")
            )
        )
        self.assertEqual(len(stats.load_all(sh.TOOL)), 1)
        self.assertIn(
            "First Blood", [label for _emoji, label in outcome.badges]
        )

    def test_hint_after_repeated_fails_but_never_in_the_exam(self):
        sh = py_shell
        with mock.patch.object(
            sh, "prepare_grading", side_effect=lambda *a: self._job(False)
        ), mock.patch.dict(
            sh.ALL_EXERCISES["py_inter"], {"hint": "look again"}
        ):
            outcomes = [
                shell_common.grade(sh, "py_inter", random.Random(0), _cfg(sh))
                for _ in range(shell_common.hints.STUCK_THRESHOLD)
            ]
            in_exam = shell_common.grade(
                sh, "py_inter", random.Random(0), _cfg(sh), mode="exam"
            )
        self.assertIsNone(outcomes[0].hint)
        self.assertEqual(outcomes[-1].hint, "look again")
        self.assertIsNone(in_exam.hint)


class FinishAndBlindTests(_TempDataDir):
    def test_finish_exam_returns_the_summary_as_data(self):
        sh = py_shell
        tmp = tempfile.mkdtemp()
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start("carol")
        run.ensure_exercise()
        run.begin_attempt()
        with mock.patch.object(
            shell_common.report_export, "REPORTS_DIR", tmp
        ), mock.patch.object(shell_common.ui, "summary") as rendered:
            result = shell_common.finish_exam(
                sh, run.session, passed=False, timed_out=True
            )
        rendered.assert_not_called()
        self.assertIn("TIME'S UP", result.title)
        self.assertEqual(dict(result.rows)["Attempts"], 1)
        self.assertTrue(os.path.isfile(result.report_path))

    def test_blind_exam_report_hides_failing_cases(self):
        sh = py_shell
        report = Report("py_inter", "inter")
        report.total, report.passed = 3, 1
        job = shell_common.GradingJob(3, lambda: report)
        with mock.patch.object(
            sh, "prepare_grading", return_value=job
        ), mock.patch.object(
            shell_common.ui, "report"
        ) as rendered, mock.patch.object(shell_common.ui, "spinner"):
            shell_common.grade_exercise(
                sh,
                "py_inter",
                random.Random(0),
                _cfg(sh, blind=True),
                mode="exam",
            )
            self.assertEqual(rendered.call_args[0][1], 0)
            shell_common.grade_exercise(
                sh,
                "py_inter",
                random.Random(0),
                _cfg(sh, blind=True),
                mode="practice",
            )
            self.assertEqual(rendered.call_args[0][1], 4)


if __name__ == "__main__":
    unittest.main()
