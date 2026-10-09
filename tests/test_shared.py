#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the shared quality-of-life layer used by both testers:
settings.py, stats.py, session_store.py, hints.py. Every test patches
each module's own path constants to a throwaway temp directory — never
touches the student's real ~/.examshell/."""

from __future__ import annotations

import argparse
import os
import random
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional, Sequence, TypeVar
from unittest.mock import patch

from examshell import (
    hints,
    session_store,
    settings,
    stats,
)
from examshell.examshell import Session
from examshell.shell_common import Session as SessionState
from examshell.grader import Failure, Report


_T = TypeVar("_T")


def _some(value: Optional[_T]) -> _T:
    """`value`, failing the test right here when it is None."""
    assert value is not None
    return value


def unwritable_dir(testcase: unittest.TestCase) -> str:
    """A directory path that os.makedirs() can never create, even as root:
    it sits *under a regular file*, so every attempt fails with
    NotADirectoryError. A made-up absolute path like /this/does/not/exist
    would simply get created when the tests run as root (Docker, CI
    containers) — failing the test and littering the filesystem."""
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    blocker = os.path.join(tmp.name, "a-file")
    with open(blocker, "w", encoding="utf-8"):
        pass
    return os.path.join(blocker, "sub")


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.config_path = os.path.join(self.tmpdir.name, "config.json")
        patcher = patch.object(settings, "CONFIG_PATH", self.config_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_config_missing_file_is_empty(self) -> None:
        self.assertEqual(settings.load_config(), {})

    def test_load_config_corrupt_file_is_empty(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(settings.load_config(), {})

    def test_load_config_non_dict_json_is_empty(self) -> None:
        with open(self.config_path, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]")
        self.assertEqual(settings.load_config(), {})

    def test_save_and_load_round_trip(self) -> None:
        ok = settings.save_config({"fuzz": 7, "timeout": 5})
        self.assertTrue(ok)
        self.assertEqual(settings.load_config(), {"fuzz": 7, "timeout": 5})

    def test_save_config_drops_non_persistable_keys(self) -> None:
        settings.save_config({"timeout": 3, "totally_made_up": "x"})
        saved = settings.load_config()
        self.assertIn("timeout", saved)
        self.assertNotIn("totally_made_up", saved)

    def test_save_config_drops_none_values(self) -> None:
        settings.save_config({"timeout": 3, "fuzz": None})
        saved = settings.load_config()
        self.assertIn("timeout", saved)
        self.assertNotIn("fuzz", saved)

    def test_save_config_survives_unwritable_dir(self) -> None:
        # DATA_DIR unset/unwritable: os.makedirs should fail -> best-effort
        # False
        bad_dir = unwritable_dir(self)
        with patch.object(settings, "DATA_DIR", bad_dir), patch.object(
            settings, "CONFIG_PATH", os.path.join(bad_dir, "config.json")
        ):
            self.assertFalse(settings.save_config({"timeout": 3}))

    def test_interrupted_save_keeps_the_old_config(self) -> None:
        # The run dies after writing the new data, before it is swapped in:
        # config.json must still be the complete old file.
        settings.save_config({"timeout": 3})
        with patch("examshell.settings.os.replace", side_effect=OSError):
            self.assertFalse(settings.save_config({"timeout": 9}))
        self.assertEqual(settings.load_config(), {"timeout": 3})

    def test_merged_prefers_explicit_cli_flag(self) -> None:
        args = argparse.Namespace(theme="highcontrast")
        config = {"theme": "light"}
        self.assertEqual(
            settings.merged(args, config, "theme", "dark"), "highcontrast"
        )

    def test_merged_falls_back_to_config_file(self) -> None:
        args = argparse.Namespace(theme=None)
        config = {"theme": "light"}
        self.assertEqual(
            settings.merged(args, config, "theme", "dark"), "light"
        )

    def test_merged_falls_back_to_default(self) -> None:
        args = argparse.Namespace(theme=None)
        self.assertEqual(settings.merged(args, {}, "theme", "dark"), "dark")

    def test_merged_missing_attr_on_args_falls_back(self) -> None:
        args = argparse.Namespace()
        self.assertEqual(settings.merged(args, {}, "theme", "dark"), "dark")


class StatsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.stats_path = os.path.join(self.tmpdir.name, "stats.jsonl")
        patcher = patch.object(stats, "STATS_PATH", self.stats_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        data_patcher = patch.object(stats, "DATA_DIR", self.tmpdir.name)
        data_patcher.start()
        self.addCleanup(data_patcher.stop)

    def test_load_all_on_missing_file_is_empty(self) -> None:
        self.assertEqual(stats.load_all(), [])

    def test_record_then_load_round_trips(self) -> None:
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        events = stats.load_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["exercise"], "py_inter")
        self.assertTrue(events[0]["ok"])

    def test_load_all_filters_by_tool(self) -> None:
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("c", "ft_atoi", 2, False, 3, 9, "practice")
        self.assertEqual(len(stats.load_all("py")), 1)
        self.assertEqual(len(stats.load_all("c")), 1)
        self.assertEqual(len(stats.load_all()), 2)

    def test_load_all_skips_malformed_lines(self) -> None:
        with open(self.stats_path, "w", encoding="utf-8") as fh:
            fh.write('{"tool": "py", "ok": true}\n')
            fh.write("not json at all\n")
            fh.write("\n")  # blank line
            fh.write('{"tool": "py", "ok": false}\n')
        self.assertEqual(len(stats.load_all("py")), 2)

    def test_best_exam_time_none_when_no_completions(self) -> None:
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertIsNone(stats.best_exam_time("py"))

    def test_best_exam_time_is_the_minimum(self) -> None:
        stats.record_exam_complete("py", 120.0, 6, 100)
        stats.record_exam_complete("py", 90.0, 6, 100)
        stats.record_exam_complete("py", 150.0, 8, 100)
        self.assertEqual(stats.best_exam_time("py"), 90.0)

    def test_summarize_empty(self) -> None:
        summary = stats.summarize("py")
        self.assertEqual(summary["total_attempts"], 0)
        self.assertEqual(summary["pass_rate"], 0.0)
        self.assertEqual(summary["per_exercise"], {})
        self.assertIsNone(summary["best_seconds"])

    def test_summarize_aggregates_attempts_and_passes(self) -> None:
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_bracket_validator", 1, True, 5, 5, "practice")
        summary = stats.summarize("py")
        self.assertEqual(summary["total_attempts"], 3)
        self.assertEqual(summary["total_passes"], 2)
        self.assertAlmostEqual(summary["pass_rate"], 2 / 3)
        self.assertEqual(
            summary["per_exercise"]["py_inter"], {"attempts": 2, "passes": 1}
        )
        self.assertEqual(
            summary["per_exercise"]["py_bracket_validator"],
            {"attempts": 1, "passes": 1},
        )

    def test_summarize_excludes_exam_complete_from_per_exercise(self) -> None:
        stats.record("py", "py_inter", 1, True, 10, 10, "exam")
        stats.record_exam_complete("py", 100.0, 6, 100)
        summary = stats.summarize("py")
        self.assertEqual(
            summary["total_attempts"], 1
        )  # exam-complete excluded
        self.assertEqual(summary["exam_completions"], 1)
        self.assertEqual(summary["best_seconds"], 100.0)

    def test_consecutive_fails_zero_with_no_history(self) -> None:
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 0)

    def test_consecutive_fails_counts_the_trailing_run(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_inter", 1, False, 7, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 3)

    def test_consecutive_fails_resets_on_a_pass(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 1)

    def test_consecutive_fails_ignores_exam_mode(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_inter", 1, False, 1, 10, "exam")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 2)

    def test_consecutive_fails_is_per_exercise_and_tool(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 3, 10, "practice")
        stats.record("c", "py_inter", 1, False, 3, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 1)

    def test_weakest_excludes_never_attempted(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        self.assertEqual(
            stats.weakest_exercises("py", ["py_inter", "py_never_touched"]),
            ["py_inter"],
        )

    def test_weakest_excludes_a_spotless_record(self) -> None:
        # Nailed on the first (and only) try — nothing to gain from
        # reviewing it, so it must not pad the weak queue.
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])

    def test_weakest_ranks_by_current_fail_streak_first(self) -> None:
        # py_inter: passed once, then two fails in a row (streak 2).
        # py_hidenp: one single fail, no streak (streak 1) but never passed.
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 1, 10, "practice")
        self.assertEqual(
            stats.weakest_exercises("py", ["py_inter", "py_hidenp"]),
            ["py_inter", "py_hidenp"],
        )

    def test_weakest_ties_broken_by_lowest_pass_rate(self) -> None:
        # Neither is on an active fail streak (both last-passed) —
        # py_hidenp's lifetime pass rate (1/2) is worse than py_inter's (2/3).
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 1, 10, "practice")
        stats.record("py", "py_hidenp", 1, True, 10, 10, "practice")
        self.assertEqual(
            stats.weakest_exercises("py", ["py_inter", "py_hidenp"]),
            ["py_hidenp", "py_inter"],
        )

    def test_weakest_ignores_exam_mode_attempts(self) -> None:
        stats.record("py", "py_inter", 1, False, 3, 10, "exam")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])

    def test_weakest_empty_with_no_history(self) -> None:
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])


class SessionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        patcher = patch.object(session_store, "DATA_DIR", self.tmpdir.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _session(self) -> SessionState:
        s = Session(login="alice")
        s.start()
        s.level = 3
        s.passed = ["py_inter", "py_bracket_validator"]
        s.attempts = 5
        s.history = [
            (1, "py_inter", 1, 12.5),
            (2, "py_bracket_validator", 2, 30.0),
        ]
        return s

    def test_load_with_nothing_saved_is_none(self) -> None:
        self.assertIsNone(session_store.load("py"))

    def test_save_then_load_round_trips_the_shape(self) -> None:
        session = self._session()
        rng = random.Random(42)
        ok = session_store.save(
            "py", session, rng, "py_hidenp", level_attempts=2
        )
        self.assertTrue(ok)
        data = session_store.load("py")
        assert data is not None
        self.assertIsNotNone(data)
        self.assertEqual(data["login"], "alice")
        self.assertEqual(data["level"], 3)
        self.assertEqual(data["current_ex"], "py_hidenp")
        self.assertEqual(data["passed"], ["py_inter", "py_bracket_validator"])
        self.assertEqual(data["attempts"], 5)
        self.assertEqual(data["level_attempts"], 2)

    def test_level_elapsed_seconds_round_trips_the_time_spent_pre_quit(
        self,
    ) -> None:
        # Without level_started, a resume can only restart the current
        # level's clock from the moment of resuming — silently dropping
        # whatever time was already spent on it before the earlier quit.
        session = self._session()
        rng = random.Random(42)
        level_started = time.time() - 90  # 90s already spent on this level
        session_store.save(
            "py",
            session,
            rng,
            "py_hidenp",
            level_attempts=2,
            level_started=level_started,
        )
        data = session_store.load("py")
        assert data is not None
        self.assertAlmostEqual(data["level_elapsed_seconds"], 90, delta=2)

    def test_level_elapsed_seconds_defaults_to_zero_without_level_started(
        self,
    ) -> None:
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        data = session_store.load("py")
        assert data is not None
        self.assertEqual(data["level_elapsed_seconds"], 0)

    def test_rng_state_round_trips_identically(self) -> None:
        session = self._session()
        rng = random.Random(1234)
        rng.random()  # advance the state away from the seed-fresh state
        expected_next = [rng.random() for _ in range(5)]
        rng2 = random.Random(1234)
        rng2.random()
        session_store.save("py", session, rng2, "py_hidenp")
        data = session_store.load("py")
        assert data is not None
        restored = session_store.rng_from_saved(data)
        got_next = [restored.random() for _ in range(5)]
        self.assertEqual(got_next, expected_next)

    def test_load_rejects_a_hand_edited_incomplete_file(self) -> None:
        path = session_store._path("py")
        os.makedirs(self.tmpdir.name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"login": "alice"}')  # missing required keys
        self.assertIsNone(session_store.load("py"))

    def test_load_rejects_corrupt_json(self) -> None:
        path = session_store._path("py")
        os.makedirs(self.tmpdir.name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(session_store.load("py"))

    def test_clear_removes_the_file(self) -> None:
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        self.assertIsNotNone(session_store.load("py"))
        session_store.clear("py")
        self.assertIsNone(session_store.load("py"))

    def test_clear_on_nothing_saved_does_not_raise(self) -> None:
        session_store.clear("py")  # must not raise

    def test_py_and_c_tools_use_separate_files(self) -> None:
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        self.assertIsNone(session_store.load("c"))
        self.assertIsNotNone(session_store.load("py"))


class HintsTests(unittest.TestCase):
    """diagnose() is a heuristic, not a proof — these tests only pin down
    the specific, deliberately narrow patterns it's supposed to catch
    (see hints.py's module docstring on why it's hedged). It must work
    unmodified on both a Python Report (typed expected/got) and a C one
    (string expected/got, see c_exam/grader.py's CFailure) — every test
    below exercises both."""

    def _report(
        self,
        failures: Sequence[Any] = (),
        fatal: str = "",
        warnings: Sequence[str] = (),
    ) -> Report:
        report = Report("some_exercise", "some_func")
        report.failures = list(failures)
        report.fatal = fatal
        report.warnings = list(warnings)
        return report

    def test_no_hint_when_report_is_clean(self) -> None:
        report = self._report()
        report.passed = report.total = 1
        self.assertIsNone(hints.diagnose(report))

    def test_timeout_hint(self) -> None:
        for code in ("TIMEOUT", "GLOBAL_TIMEOUT", "IMPORT_TIMEOUT"):
            self.assertIn(
                "infinite loop",
                _some(hints.diagnose(self._report(fatal=code))),
            )

    def test_other_fatal_codes_get_no_generic_hint(self) -> None:
        self.assertIsNone(hints.diagnose(self._report(fatal="COMPILE_ERROR")))

    def test_timeout_hint_from_a_c_program_kind_per_case_timeout(self) -> None:
        # c_exam/grader.py's _grade_program records a per-case timeout as a
        # non-fatal failure with got="[TIMEOUT]" (see its "note = TIMEOUT"
        # path), not as report.fatal like every other timeout — must still
        # get the TIMEOUT hint, not the CRASH one its own bracket shape
        # would otherwise trigger.
        report = self._report(
            [Failure([], "some output", "[TIMEOUT]")],
            warnings=["case 2 timed out: TIMEOUT"],
        )
        self.assertIn("infinite loop", _some(hints.diagnose(report)))

    def test_timeout_hint_from_a_python_per_case_timeout(self) -> None:
        # examshell/grader.py's RUNNER_TEMPLATE records a per-case timeout as a
        # non-fatal failure with got="[TIMEOUT > Ns]" (the per-call timeout
        # value is embedded in the message, unlike the C side's bare
        # "[TIMEOUT]") — must still get the TIMEOUT hint via the same
        # startswith() check, not silently fall through to no hint at all.
        report = self._report([Failure([1, 2], "expected", "[TIMEOUT > 3s]")])
        self.assertIn("infinite loop", _some(hints.diagnose(report)))

    def test_crash_warning_hint(self) -> None:
        report = self._report(warnings=["your program crashed: segfault"])
        self.assertIn("memory access", _some(hints.diagnose(report)))

    def test_leak_warning_hint(self) -> None:
        report = self._report(
            warnings=[
                "valgrind reported memory error(s) (leaks, invalid reads/"
                "writes, ...) on case 3:\n"
                "40 bytes in 1 blocks are definitely lost "
                "in loss record 1 of 1"
            ]
        )
        self.assertIn("leak", _some(hints.diagnose(report)))

    def test_leak_warning_hint_still_applies_under_strict_valgrind(
        self,
    ) -> None:
        # --strict-valgrind sets report.fatal = "VALGRIND_ERRORS" (not one
        # of the TIMEOUT codes) instead of only warning — classify() must
        # still find LEAK from the warning text, not bail out early just
        # because report.fatal is set.
        report = self._report(
            fatal="VALGRIND_ERRORS",
            warnings=[
                "valgrind reported memory error(s) (leaks, invalid "
                "reads/writes, ...) on case 3:\n"
                "40 bytes in 1 blocks are definitely lost"
            ],
        )
        self.assertIn("leak", _some(hints.diagnose(report)))

    def test_non_leak_valgrind_finding_gets_the_crash_hint_not_leak(
        self,
    ) -> None:
        # The boilerplate wrapper message ALWAYS says "leak(s)" regardless
        # of the real finding (see c_exam/grader.py's run_valgrind()
        # callers) — a plain invalid read/write with zero blocks actually
        # leaked used to still trigger the LEAK hint ("trace every malloc
        # to a matching free"), which is wrong guidance for this bug.
        report = self._report(
            warnings=[
                "valgrind reported memory error(s) (leaks, invalid reads/"
                "writes, ...) on case 3:\n"
                "Invalid write of size 4 at 0x1091A8: ft_strcpy"
            ]
        )
        self.assertIn("memory access", _some(hints.diagnose(report)))

    def test_returning_the_string_none_is_not_emptyish(
        self,
    ) -> None:
        # An older version of this string-matched "None"/"[]"/"()"/"{}"
        # unconditionally, so a solution whose genuinely correct answer IS
        # the literal string "None" got treated as if it returned nothing.
        report = self._report([Failure([], "None", "something else")])
        self.assertIsNone(hints.diagnose(report))

    def test_crash_is_checked_before_leak(self) -> None:
        # A run can't be both, but if warnings ever carried both a crash
        # takes priority — a crash is the more actionable, more urgent
        # thing to point at first.
        report = self._report(
            warnings=[
                "your program crashed: segfault",
                "valgrind reported memory error(s)",
            ]
        )
        self.assertIn("memory access", _some(hints.diagnose(report)))

    def test_crash_hint_from_a_python_exception_failure(self) -> None:
        # The Python sandbox never appends a "crashed" warning (only the C
        # tester does) — a raised exception shows up as a failing case
        # instead, e.g. "[ZeroDivisionError] division by zero" as `got`.
        report = self._report(
            [Failure([1, 0], 1, "[ZeroDivisionError] division by zero")]
        )
        self.assertIn("memory access", _some(hints.diagnose(report)))

    def test_off_by_one_hint_python_and_c_shaped(self) -> None:
        py_report = self._report([Failure([5], 4, 5)])
        c_report = self._report([Failure([], "4", "5")])
        for report in (py_report, c_report):
            self.assertIn("off-by-one", _some(hints.diagnose(report)))

    def test_bools_are_not_mistaken_for_off_by_one(self) -> None:
        # float(True) - float(False) == 1, which would otherwise look
        # exactly like an off-by-one on a completely unrelated bug.
        report = self._report([Failure([], True, False)])
        self.assertIsNone(hints.diagnose(report))

    def test_sign_flip_hint(self) -> None:
        report = self._report([Failure([], -3, 3)])
        self.assertIn("sign", _some(hints.diagnose(report)))

    def test_empty_expected_hint_python_and_c_shaped(self) -> None:
        py_report = self._report([Failure([], [], [1, 2])])
        c_report = self._report([Failure([], "", "1 2")])
        for report in (py_report, c_report):
            self.assertIn("empty", _some(hints.diagnose(report)))

    def test_no_hint_for_an_unrelated_mismatch(self) -> None:
        report = self._report([Failure([], "hello", "world")])
        self.assertIsNone(hints.diagnose(report))


class HintForTests(unittest.TestCase):
    """hint_for() — picking between a plain-string curated hint, a
    per-category dict one, and the diagnose() fallback (see hints.py's
    module docstring)."""

    def _report(
        self,
        failures: Sequence[Any] = (),
        fatal: str = "",
        warnings: Sequence[str] = (),
    ) -> Report:
        report = Report("some_exercise", "some_func")
        report.failures = list(failures)
        report.fatal = fatal
        report.warnings = list(warnings)
        return report

    def test_plain_string_hint_is_returned_as_is(self) -> None:
        ex = {"hint": "a static hint"}
        report = self._report([Failure([], "hello", "world")])
        self.assertEqual(hints.hint_for(ex, report), "a static hint")

    def test_no_hint_field_falls_back_to_diagnose(self) -> None:
        ex: Dict[str, Any] = {}
        report = self._report(fatal="TIMEOUT")
        self.assertIn("infinite loop", _some(hints.hint_for(ex, report)))

    def test_dict_hint_picks_the_matching_category(self) -> None:
        ex = {
            "hint": {
                "crash": "a crash-specific hint",
                "default": "a fallback hint",
            }
        }
        report = self._report(warnings=["your program crashed: segfault"])
        self.assertEqual(hints.hint_for(ex, report), "a crash-specific hint")

    def test_dict_hint_falls_back_to_default_key(self) -> None:
        ex = {
            "hint": {
                "crash": "a crash-specific hint",
                "default": "a fallback hint",
            }
        }
        report = self._report([Failure([], "hello", "world")])
        self.assertEqual(hints.hint_for(ex, report), "a fallback hint")

    def test_dict_hint_with_no_matching_key_falls_back_to_diagnose(
        self,
    ) -> None:
        ex = {"hint": {"crash": "a crash-specific hint"}}
        report = self._report(fatal="TIMEOUT")
        self.assertIn("infinite loop", _some(hints.hint_for(ex, report)))


class VersionTests(unittest.TestCase):
    """examshell/version.py is the single source of truth; pyproject.toml and
    CHANGELOG.md must agree with it (the release workflow relies on both)."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, name: str) -> str:
        with open(os.path.join(self.ROOT, name), encoding="utf-8") as fh:
            return fh.read()

    def test_pyproject_version_matches(self) -> None:
        from examshell.version import __version__

        self.assertIn(
            'version = "%s"' % __version__, self._read("pyproject.toml")
        )

    def test_changelog_has_a_section_for_this_version(self) -> None:
        from examshell.version import __version__

        headings = [
            line
            for line in self._read("CHANGELOG.md").splitlines()
            if line.startswith("## ")
        ]
        self.assertTrue(
            any(
                h == "## " + __version__
                or h.startswith("## %s " % __version__)
                for h in headings
            ),
            headings,
        )


class CaseLabelTests(unittest.TestCase):
    """case_labels.describe(): names the edge-case traits of a failing
    input."""

    class _F(object):
        def __init__(
            self, args: Optional[List[Any]], program: bool = False
        ) -> None:
            self.args, self.program = args, program

    def _d(self, args: Optional[List[Any]], program: bool = False) -> str:
        from examshell import case_labels

        return case_labels.describe(self._F(args, program))

    def test_strings(self) -> None:
        self.assertEqual(self._d([""]), "empty string")
        self.assertEqual(self._d(["   "]), "only whitespace")
        self.assertEqual(self._d(["a\tb"]), "tabs")
        self.assertEqual(self._d([" a"]), "leading/trailing whitespace")
        self.assertEqual(self._d(["a  b"]), "repeated spaces")
        self.assertEqual(self._d(["plain"]), "")

    def test_numbers(self) -> None:
        self.assertEqual(self._d([0]), "zero")
        self.assertEqual(self._d([-4]), "negative number")
        self.assertEqual(self._d([-(2**31)]), "INT_MIN/INT_MAX")
        self.assertEqual(self._d([True]), "")

    def test_lists(self) -> None:
        self.assertEqual(self._d([[]]), "empty list")
        self.assertEqual(self._d([[1]]), "single element")

    def test_argv(self) -> None:
        self.assertEqual(self._d([], program=True), "no arguments")
        self.assertEqual(self._d(["-3"], program=True), "negative number")
        self.assertEqual(self._d(["0"], program=True), "zero")

    def test_at_most_two_labels_without_duplicates(self) -> None:
        self.assertEqual(
            self._d([" \ta  b ", "", 0]), "tabs · leading/trailing whitespace"
        )

    def test_no_inputs_known(self) -> None:
        from examshell import case_labels

        self.assertEqual(case_labels.describe(object()), "")


class ReadinessAndDrillTests(unittest.TestCase):
    """stats.exercise_status() / readiness() / drill_queue()."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (
            ("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
            ("DATA_DIR", self.tmpdir.name),
        ):
            patcher = patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.clock = 1000.0

    def _grade(self, name: str, ok: bool, mode: str = "practice") -> None:
        self.clock += 10
        with patch.object(time, "time", return_value=self.clock):
            stats.record("py", name, 1, ok, 1 if ok else 0, 1, mode)

    def test_exercise_status(self) -> None:
        self._grade("a", False)
        self._grade("a", True)
        self._grade("b", False)
        status = stats.exercise_status("py", ["a", "b", "c"])
        self.assertEqual(status["a"]["status"], "passed")
        self.assertEqual(
            (status["a"]["passes"], status["a"]["attempts"]), (1, 2)
        )
        self.assertEqual(status["b"]["status"], "failed")
        self.assertEqual(status["c"]["status"], "untried")

    def test_exam_passes_count_for_readiness(self) -> None:
        self._grade("a", True, mode="exam")
        levels = stats.readiness("py", {1: ["a", "b"], 2: ["c"]})
        self.assertEqual(
            [(lv, passed, total) for lv, passed, total, _ in levels],
            [(1, 1, 2), (2, 0, 1)],
        )

    def test_drill_order_weak_then_untried_then_stale(self) -> None:
        self._grade("old_pass", True)
        self._grade("new_pass", True)
        self._grade("weak", False)
        queue = stats.drill_queue(
            "py", ["new_pass", "old_pass", "weak", "fresh"], n=4
        )
        self.assertEqual(queue, ["weak", "fresh", "old_pass", "new_pass"])

    def test_drill_caps_weak_spots_at_half_the_session(self) -> None:
        for name in ("w1", "w2", "w3", "w4"):
            self._grade(name, False)
        queue = stats.drill_queue(
            "py", ["w1", "w2", "w3", "w4", "u1", "u2"], n=4
        )
        self.assertEqual(len(queue), 4)
        self.assertEqual(sorted(queue[2:]), ["u1", "u2"])

    def test_drill_is_short_when_there_are_few_candidates(self) -> None:
        self.assertEqual(stats.drill_queue("py", ["x"], n=5), ["x"])


class UpdateCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        from examshell import update_check

        self.uc = update_check
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (
            ("CACHE_PATH", os.path.join(self.tmpdir.name, "u.json")),
            ("DATA_DIR", self.tmpdir.name),
        ):
            patcher = patch.object(update_check, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_version_comparison(self) -> None:
        self.assertTrue(self.uc.is_newer("v0.10.0", "0.9.9"))
        self.assertFalse(self.uc.is_newer("v0.2.0", "0.2.0"))
        self.assertFalse(self.uc.is_newer("garbage", "0.2.0"))

    def test_notice_only_for_a_newer_version(self) -> None:
        self.assertIsNone(self.uc.notice_text(None))
        self.assertIsNone(self.uc.notice_text("v0.0.1"))
        self.assertIn("99.0.0", _some(self.uc.notice_text("v99.0.0")))

    def test_result_is_cached_for_a_day_even_when_the_fetch_failed(
        self,
    ) -> None:
        calls = []

        def fetch() -> None:
            calls.append(1)
            return None

        self.assertIsNone(self.uc.latest_version(now=time.time(), fetch=fetch))
        self.uc.latest_version(now=time.time() + 60, fetch=fetch)
        self.assertEqual(len(calls), 1)
        self.uc.latest_version(
            now=time.time() + self.uc.CHECK_EVERY + 1, fetch=fetch
        )
        self.assertEqual(len(calls), 2)

    def test_opt_out(self) -> None:
        self.assertFalse(self.uc.enabled(opt_out_flag=True))
        with patch.dict(os.environ, {self.uc.ENV_OPT_OUT: "1"}):
            self.assertFalse(self.uc.enabled())
            self.assertEqual(
                self.uc.start_background_check(), {"notice": None}
            )


class HistoryStatsTests(unittest.TestCase):
    """stats.daily_activity() / practice_streak() / exam_history()."""

    DAY = 86400

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (
            ("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
            ("DATA_DIR", self.tmpdir.name),
        ):
            patcher = patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.now = time.mktime((2026, 9, 20, 12, 0, 0, 0, 0, -1))  # local noon

    def _grade(self, days_ago: int, ok: bool = True) -> None:
        with patch.object(
            time, "time", return_value=self.now - days_ago * self.DAY
        ):
            stats.record("py", "py_inter", 1, ok, 1, 1, "practice")

    def test_daily_activity(self) -> None:
        self._grade(0)
        self._grade(0, ok=False)
        self._grade(2)
        activity = stats.daily_activity("py", days=4, now=self.now)
        self.assertEqual(activity, [(0, 0), (1, 1), (0, 0), (2, 1)])

    def test_streak_ends_today_or_yesterday(self) -> None:
        for d in (1, 2, 3, 5):
            self._grade(d)
        self.assertEqual(stats.practice_streak("py", now=self.now), 3)
        self._grade(0)
        self.assertEqual(stats.practice_streak("py", now=self.now), 4)
        self.assertEqual(
            stats.practice_streak("py", now=self.now + 3 * self.DAY), 0
        )

    def test_exam_history_newest_first(self) -> None:
        for i, secs in enumerate((300, 200, 100)):
            with patch.object(time, "time", return_value=self.now + i):
                stats.record_exam_complete("py", secs, 6, 100)
        self.assertEqual(
            [e["seconds"] for e in stats.exam_history("py", n=2)], [100, 200]
        )


class ReflowTests(unittest.TestCase):
    def test_joins_hard_wrapped_lines_and_keeps_paragraphs_and_lists(
        self,
    ) -> None:
        from examshell import ui

        prose = "one\ntwo\n\nthree\n  - item\n  - item2\n"
        self.assertEqual(
            ui._reflow(prose), "one two\n\nthree\n  - item\n  - item2"
        )


if __name__ == "__main__":
    unittest.main()
