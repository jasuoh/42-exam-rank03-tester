#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for examshell/shell_common.py's engine layer — ExamRun and
grade(), the I/O-free core both testers' line-based UI (and a future
full-screen one) drive. Run against both tester modules, since each
supplies its own hooks."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import random
import tempfile
import time
import unittest
from typing import Any, List, cast
from unittest import mock

from c_exam import bank as c_bank
from c_exam import examshell as c_shell
from examshell import examshell as py_shell
from examshell import hints
from examshell._types import Tester, TesterConfig
from examshell import ui
from examshell import session_store, shell_common, stats
from examshell.grader import Failure, Report


def _cfg(sh: Tester, **overrides: Any) -> TesterConfig:
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
    cfg: TesterConfig = sh.Config(argparse.Namespace(**values))
    return cfg


class _TempDataDir(unittest.TestCase):
    """Point every file the engine writes at a throwaway directory."""

    def setUp(self) -> None:
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

    def test_levels_advance_only_by_passing(self) -> None:
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

    def test_last_level_finishes_the_run(self) -> None:
        sh = c_shell
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start()
        for _ in range(c_bank.N_LEVELS):
            run.ensure_exercise()
            run.begin_attempt()
            last = run.pass_level()
        self.assertTrue(last)
        self.assertTrue(run.finished)
        self.assertEqual(run.session.score(), 100)

    def test_same_seed_same_exam(self) -> None:
        def exercises(sh: Tester) -> List[str]:
            run = shell_common.ExamRun(sh, _cfg(sh, seed=99))
            run.start()
            drawn: List[str] = []
            while not run.finished:
                drawn.append(run.ensure_exercise())
                run.grade_rng.random()  # grading must not shift draws
                run.pass_level()
            return drawn

        for sh in self.SHELLS:
            with self.subTest(tester=sh.TOOL):
                self.assertEqual(exercises(sh), exercises(sh))

    def test_new_exams_go_through_every_exercise_of_a_level(self) -> None:
        # issue #16: with 2-3 exercises per level, plain random draws kept
        # handing out the same ones exam after exam
        sh = py_shell

        def first_exercise() -> str:
            run = shell_common.ExamRun(sh, _cfg(sh, seed=None))
            run.start()
            return run.ensure_exercise()

        pool = sh.STANDARD_LEVELS[1]
        for _ in range(3):
            exams = [first_exercise() for _ in pool]
            self.assertEqual(sorted(exams), sorted(pool))
        # nor does a new round start with the one that ended the last
        last = exams[-1]
        self.assertNotEqual(first_exercise(), last)

    def test_a_failed_level_keeps_its_exercise(self) -> None:
        # like the real exam: after FAILURE you work on the same exercise
        # until it passes — across fails, a redraw attempt and a resume
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh, seed=None))
        run.start("erin")
        first = run.ensure_exercise()
        for _ in range(5):
            run.begin_attempt()  # graded, failed: no pass_level()
            self.assertEqual(run.ensure_exercise(), first)
        self.assertFalse(run.redraw())
        self.assertEqual(run.current_ex, first)
        run.save()
        resumed = shell_common.ExamRun(sh, _cfg(sh, seed=None))
        saved = session_store.load(sh.TOOL)
        assert saved is not None
        resumed.resume(saved)
        self.assertEqual(resumed.ensure_exercise(), first)
        self.assertEqual(resumed.level_attempts, 5)

    def test_redraw_only_when_relaxed(self) -> None:
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

    def test_exam_config_forces_the_testers_strict_flags(self) -> None:
        py_cfg = shell_common.ExamRun(py_shell, _cfg(py_shell)).cfg
        self.assertTrue(cast(py_shell.Config, py_cfg).strict_imports)
        c_cfg = cast(
            c_shell.Config, shell_common.ExamRun(c_shell, _cfg(c_shell)).cfg
        )
        self.assertTrue(c_cfg.strict_norm and c_cfg.strict_forbidden)

    def test_save_and_resume_round_trip(self) -> None:
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start("bob")
        run.ensure_exercise()
        run.pass_level()
        current = run.ensure_exercise()
        run.begin_attempt()
        run.save()

        resumed = shell_common.ExamRun(sh, _cfg(sh))
        saved = session_store.load(sh.TOOL)
        assert saved is not None
        resumed.resume(saved)
        self.assertTrue(resumed.resumed)
        self.assertEqual((resumed.session.login, resumed.level), ("bob", 2))
        self.assertEqual(resumed.ensure_exercise(), current)
        self.assertEqual(resumed.level_attempts, 1)
        # the draw RNG continues where it left off
        self.assertEqual(resumed.rng.random(), run.rng.random())

    def test_the_clock_keeps_running_while_saved(self) -> None:
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh, time_limit=1))
        with mock.patch.object(time, "time", return_value=1000.0):
            run.start()
            run.ensure_exercise()
        with mock.patch.object(time, "time", return_value=1020.0):
            run.save()  # 20s in
        saved = session_store.load(sh.TOOL)
        assert saved is not None
        resumed = shell_common.ExamRun(sh, _cfg(sh, time_limit=1))
        with mock.patch.object(time, "time", return_value=1050.0):
            resumed.resume(saved)  # 30s later: the pause counts too
            self.assertIn("00:00:10 left", resumed.countdown())
        with mock.patch.object(time, "time", return_value=1060.0):
            self.assertTrue(resumed.times_up())

    # issue #15: a new exam starts from an empty rendu/ — solutions to exam
    # exercises from earlier runs go to rendu/archive/<when>/; a resumed
    # exam keeps its files where they are.
    TRAINING = {".py": "py_fizzbuzz_list", ".c": "array_sum"}

    def _write(self, rendu: str, sh: Tester, name: str, text: str) -> str:
        path = os.path.join(rendu, name + sh.SOURCE_EXT)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_new_exam_archives_earlier_exam_solutions(self) -> None:
        for sh in self.SHELLS:
            with self.subTest(
                tester=sh.TOOL
            ), tempfile.TemporaryDirectory() as rendu:
                exam_ex = sorted(sh.STANDARD_LEVELS[1])[0]
                training_ex = self.TRAINING[sh.SOURCE_EXT]
                self._write(rendu, sh, exam_ex, "old solution\n")
                self._write(rendu, sh, training_ex, "practice\n")
                run = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))

                archive = run.start()

                assert archive is not None
                self.assertEqual(
                    os.path.dirname(archive), os.path.join(rendu, "archive")
                )
                self.assertEqual(
                    os.listdir(archive), [exam_ex + sh.SOURCE_EXT]
                )
                with open(
                    os.path.join(archive, exam_ex + sh.SOURCE_EXT),
                    encoding="utf-8",
                ) as fh:
                    self.assertEqual(fh.read(), "old solution\n")
                # the exercise is gone from rendu/, so a stub starts fresh
                self.assertFalse(
                    os.path.exists(
                        shell_common.solution_path(sh, exam_ex, run.cfg)
                    )
                )
                ok, _, _ = sh.write_stub(exam_ex, run.cfg)
                self.assertTrue(ok)
                # anything that isn't an exam exercise stays
                self.assertTrue(
                    os.path.isfile(
                        shell_common.solution_path(sh, training_ex, run.cfg)
                    )
                )

    def test_each_new_exam_gets_its_own_archive(self) -> None:
        sh = py_shell
        with tempfile.TemporaryDirectory() as rendu:
            exam_ex = sorted(sh.STANDARD_LEVELS[1])[0]
            archives = []
            for text in ("first\n", "second\n"):
                self._write(rendu, sh, exam_ex, text)
                with mock.patch.object(time, "time", return_value=1000.0):
                    run = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))
                    archives.append(run.start())
            self.assertEqual(len(set(archives)), 2)
            self.assertEqual(
                len(os.listdir(os.path.join(rendu, "archive"))), 2
            )

    def test_new_exam_with_nothing_to_archive(self) -> None:
        sh = py_shell
        with tempfile.TemporaryDirectory() as rendu:
            run = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))
            self.assertIsNone(run.start())
            self.assertFalse(os.path.exists(os.path.join(rendu, "archive")))
        # a rendu/ that doesn't exist yet is fine too
        run = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))
        self.assertIsNone(run.start())

    def test_resume_keeps_the_exams_files(self) -> None:
        sh = py_shell
        with tempfile.TemporaryDirectory() as rendu:
            run = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))
            run.start()
            ex = run.ensure_exercise()
            path = self._write(rendu, sh, ex, "work in progress\n")
            run.save()

            resumed = shell_common.ExamRun(sh, _cfg(sh, rendu=rendu))
            saved = session_store.load(sh.TOOL)
            assert saved is not None
            resumed.resume(saved)

            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "work in progress\n")
            self.assertFalse(os.path.exists(os.path.join(rendu, "archive")))

    def test_time_limit(self) -> None:
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh, time_limit=1))
        with mock.patch.object(time, "time", return_value=1000.0):
            run.start()
        with mock.patch.object(time, "time", return_value=1030.0):
            self.assertFalse(run.times_up())
            self.assertIn("00:00:30 left", run.countdown())
        with mock.patch.object(time, "time", return_value=1060.0):
            self.assertTrue(run.times_up())


class GradeTests(_TempDataDir):
    """grade(): no output at all — Report, stats, badges and hint as data."""

    def _job(self, ok: bool) -> shell_common.GradingJob:
        report = Report("x", "f")
        report.total, report.passed = 3, 3 if ok else 1
        return shell_common.GradingJob(3, lambda: report)

    def test_records_and_returns_an_outcome(self) -> None:
        sh = py_shell
        with mock.patch.object(
            sh, "prepare_grading", return_value=self._job(True)
        ), mock.patch.object(ui, "report") as rendered:
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

    def test_hint_after_repeated_fails_but_never_in_the_exam(self) -> None:
        sh = py_shell
        with mock.patch.object(
            sh, "prepare_grading", side_effect=lambda *a: self._job(False)
        ), mock.patch.dict(
            sh.ALL_EXERCISES["py_inter"], {"hint": "look again"}
        ):
            outcomes = [
                shell_common.grade(sh, "py_inter", random.Random(0), _cfg(sh))
                for _ in range(hints.STUCK_THRESHOLD)
            ]
            in_exam = shell_common.grade(
                sh, "py_inter", random.Random(0), _cfg(sh), mode="exam"
            )
        self.assertIsNone(outcomes[0].hint)
        self.assertEqual(outcomes[-1].hint, "look again")
        self.assertIsNone(in_exam.hint)


class FinishAndBlindTests(_TempDataDir):
    def test_finish_exam_returns_the_summary_as_data(self) -> None:
        sh = py_shell
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start("carol")
        run.ensure_exercise()
        run.begin_attempt()
        with mock.patch.object(ui, "summary") as rendered:
            result = shell_common.finish_exam(
                sh, run.session, passed=False, timed_out=True
            )
        rendered.assert_not_called()
        self.assertIn("TIME'S UP", result.title)
        self.assertEqual(dict(result.rows)["Attempts"], 1)

    def test_a_faster_passed_exam_is_a_personal_best(self) -> None:
        sh = py_shell
        stats.record_exam_complete(sh.TOOL, 3600, 6, 100)
        run = shell_common.ExamRun(sh, _cfg(sh))
        run.start("dave")
        assert run.session.start_time is not None
        run.session.start_time -= 1800
        result = shell_common.finish_exam(sh, run.session, passed=True)
        self.assertIn("Personal best", dict(result.rows))
        slower = shell_common.ExamRun(sh, _cfg(sh))
        slower.start("dave")
        assert slower.session.start_time is not None
        slower.session.start_time -= 7200
        result = shell_common.finish_exam(sh, slower.session, passed=True)
        self.assertNotIn("Personal best", dict(result.rows))

    def test_blind_exam_report_hides_failing_cases(self) -> None:
        sh = py_shell
        report = Report("py_inter", "inter")
        report.total, report.passed = 3, 1
        report.failures = [Failure(("ab", "b"), "b", "'x'")]
        job = shell_common.GradingJob(3, lambda: report)
        out = io.StringIO()
        with mock.patch.object(
            sh, "prepare_grading", return_value=job
        ), mock.patch.object(ui, "report") as rendered, mock.patch.object(
            ui, "spinner"
        ), mock.patch.object(ui, "_rich", False), mock.patch.object(
            ui, "_color", False
        ), contextlib.redirect_stdout(
            out
        ):
            shell_common.grade_exercise(
                sh,
                "py_inter",
                random.Random(0),
                _cfg(sh, blind=True),
                mode="exam",
            )
            rendered.assert_not_called()
            self.assertIn("FAILURE", out.getvalue())
            self.assertNotIn("inter(", out.getvalue())
            shell_common.grade_exercise(
                sh,
                "py_inter",
                random.Random(0),
                _cfg(sh, blind=True),
                mode="practice",
            )
            self.assertEqual(rendered.call_args[0][1], 4)

    def test_exam_grademe_shows_only_the_first_failure(self) -> None:
        # The line exam must match the real grademe: FAILURE and one trace,
        # no other failures, edge-case labels or score.
        sh = py_shell
        report = Report("py_inter", "inter")
        report.total, report.passed = 3, 1
        report.failures = [
            Failure(("ab", "b"), "b", "'x'"),
            Failure(("", ""), "", "'y'"),
        ]
        job = shell_common.GradingJob(3, lambda: report)
        out = io.StringIO()
        with mock.patch.object(
            sh, "prepare_grading", return_value=job
        ), mock.patch.object(ui, "_rich", False), mock.patch.object(
            ui, "_color", False
        ), contextlib.redirect_stdout(
            out
        ):
            shell_common.grade_exercise(
                sh, "py_inter", random.Random(0), _cfg(sh), mode="exam"
            )
        text = out.getvalue()
        self.assertIn("FAILURE", text)
        self.assertIn("inter('ab', 'b')", text)
        self.assertNotIn("'y'", text)
        self.assertNotIn("[KO]", text)
        self.assertNotIn("tests passed", text)


if __name__ == "__main__":
    unittest.main()
