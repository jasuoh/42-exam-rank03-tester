#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the shared quality-of-life layer used by both testers:
settings.py, stats.py, session_store.py, report_export.py, hints.py,
achievements.py. Every test patches each module's own path constants to a
throwaway temp directory — never touches the student's real ~/.examshell/."""

import argparse
import os
import random
import tempfile
import time
import unittest
from unittest.mock import patch

from examshell import achievements, hints, report_export, session_store, settings, stats
from examshell.examshell import Session
from examshell.grader import Failure, Report


def unwritable_dir(testcase):
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
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.config_path = os.path.join(self.tmpdir.name, "config.json")
        patcher = patch.object(settings, "CONFIG_PATH", self.config_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_load_config_missing_file_is_empty(self):
        self.assertEqual(settings.load_config(), {})

    def test_load_config_corrupt_file_is_empty(self):
        with open(self.config_path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(settings.load_config(), {})

    def test_load_config_non_dict_json_is_empty(self):
        with open(self.config_path, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]")
        self.assertEqual(settings.load_config(), {})

    def test_save_and_load_round_trip(self):
        ok = settings.save_config({"theme": "light", "timeout": 5})
        self.assertTrue(ok)
        self.assertEqual(settings.load_config(), {"theme": "light", "timeout": 5})

    def test_save_config_drops_non_persistable_keys(self):
        settings.save_config({"theme": "dark", "totally_made_up": "x"})
        saved = settings.load_config()
        self.assertIn("theme", saved)
        self.assertNotIn("totally_made_up", saved)

    def test_save_config_drops_none_values(self):
        settings.save_config({"theme": "dark", "fuzz": None})
        saved = settings.load_config()
        self.assertIn("theme", saved)
        self.assertNotIn("fuzz", saved)

    def test_save_config_survives_unwritable_dir(self):
        # DATA_DIR unset/unwritable: os.makedirs should fail -> best-effort False
        bad_dir = unwritable_dir(self)
        with patch.object(settings, "DATA_DIR", bad_dir), \
             patch.object(settings, "CONFIG_PATH",
                          os.path.join(bad_dir, "config.json")):
            self.assertFalse(settings.save_config({"theme": "dark"}))

    def test_merged_prefers_explicit_cli_flag(self):
        args = argparse.Namespace(theme="highcontrast")
        config = {"theme": "light"}
        self.assertEqual(settings.merged(args, config, "theme", "dark"), "highcontrast")

    def test_merged_falls_back_to_config_file(self):
        args = argparse.Namespace(theme=None)
        config = {"theme": "light"}
        self.assertEqual(settings.merged(args, config, "theme", "dark"), "light")

    def test_merged_falls_back_to_default(self):
        args = argparse.Namespace(theme=None)
        self.assertEqual(settings.merged(args, {}, "theme", "dark"), "dark")

    def test_merged_missing_attr_on_args_falls_back(self):
        args = argparse.Namespace()
        self.assertEqual(settings.merged(args, {}, "theme", "dark"), "dark")


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.stats_path = os.path.join(self.tmpdir.name, "stats.jsonl")
        patcher = patch.object(stats, "STATS_PATH", self.stats_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        data_patcher = patch.object(stats, "DATA_DIR", self.tmpdir.name)
        data_patcher.start()
        self.addCleanup(data_patcher.stop)

    def test_load_all_on_missing_file_is_empty(self):
        self.assertEqual(stats.load_all(), [])

    def test_record_then_load_round_trips(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        events = stats.load_all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["exercise"], "py_inter")
        self.assertTrue(events[0]["ok"])

    def test_load_all_filters_by_tool(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("c", "ft_atoi", 2, False, 3, 9, "practice")
        self.assertEqual(len(stats.load_all("py")), 1)
        self.assertEqual(len(stats.load_all("c")), 1)
        self.assertEqual(len(stats.load_all()), 2)

    def test_load_all_skips_malformed_lines(self):
        with open(self.stats_path, "w", encoding="utf-8") as fh:
            fh.write('{"tool": "py", "ok": true}\n')
            fh.write("not json at all\n")
            fh.write("\n")  # blank line
            fh.write('{"tool": "py", "ok": false}\n')
        self.assertEqual(len(stats.load_all("py")), 2)

    def test_best_exam_time_none_when_no_completions(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertIsNone(stats.best_exam_time("py"))

    def test_best_exam_time_is_the_minimum(self):
        stats.record_exam_complete("py", 120.0, 6, 100)
        stats.record_exam_complete("py", 90.0, 6, 100)
        stats.record_exam_complete("py", 150.0, 8, 100)
        self.assertEqual(stats.best_exam_time("py"), 90.0)

    def test_summarize_empty(self):
        summary = stats.summarize("py")
        self.assertEqual(summary["total_attempts"], 0)
        self.assertEqual(summary["pass_rate"], 0.0)
        self.assertEqual(summary["per_exercise"], {})
        self.assertIsNone(summary["best_seconds"])

    def test_summarize_aggregates_attempts_and_passes(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_bracket_validator", 1, True, 5, 5, "practice")
        summary = stats.summarize("py")
        self.assertEqual(summary["total_attempts"], 3)
        self.assertEqual(summary["total_passes"], 2)
        self.assertAlmostEqual(summary["pass_rate"], 2 / 3)
        self.assertEqual(summary["per_exercise"]["py_inter"],
                         {"attempts": 2, "passes": 1})
        self.assertEqual(summary["per_exercise"]["py_bracket_validator"],
                         {"attempts": 1, "passes": 1})

    def test_summarize_excludes_exam_complete_from_per_exercise(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "exam")
        stats.record_exam_complete("py", 100.0, 6, 100)
        summary = stats.summarize("py")
        self.assertEqual(summary["total_attempts"], 1)  # exam-complete excluded
        self.assertEqual(summary["exam_completions"], 1)
        self.assertEqual(summary["best_seconds"], 100.0)

    def test_consecutive_fails_zero_with_no_history(self):
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 0)

    def test_consecutive_fails_counts_the_trailing_run(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_inter", 1, False, 7, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 3)

    def test_consecutive_fails_resets_on_a_pass(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 1)

    def test_consecutive_fails_ignores_exam_mode(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_inter", 1, False, 1, 10, "exam")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 2)

    def test_consecutive_fails_is_per_exercise_and_tool(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 3, 10, "practice")
        stats.record("c", "py_inter", 1, False, 3, 10, "practice")
        self.assertEqual(stats.consecutive_fails("py", "py_inter"), 1)

    def test_weakest_excludes_never_attempted(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        self.assertEqual(
            stats.weakest_exercises("py", ["py_inter", "py_never_touched"]),
            ["py_inter"])

    def test_weakest_excludes_a_spotless_record(self):
        # Nailed on the first (and only) try — nothing to gain from
        # reviewing it, so it must not pad the weak queue.
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])

    def test_weakest_ranks_by_current_fail_streak_first(self):
        # py_inter: passed once, then two fails in a row (streak 2).
        # py_hidenp: one single fail, no streak (streak 1) but never passed.
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, False, 5, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 1, 10, "practice")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter", "py_hidenp"]),
                         ["py_inter", "py_hidenp"])

    def test_weakest_ties_broken_by_lowest_pass_rate(self):
        # Neither is on an active fail streak (both last-passed) —
        # py_hidenp's lifetime pass rate (1/2) is worse than py_inter's (2/3).
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        stats.record("py", "py_hidenp", 1, False, 1, 10, "practice")
        stats.record("py", "py_hidenp", 1, True, 10, 10, "practice")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter", "py_hidenp"]),
                         ["py_hidenp", "py_inter"])

    def test_weakest_ignores_exam_mode_attempts(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "exam")
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])

    def test_weakest_empty_with_no_history(self):
        self.assertEqual(stats.weakest_exercises("py", ["py_inter"]), [])


class AchievementsTests(unittest.TestCase):
    """Every badge is a pure function of stats.jsonl — see achievements.py's
    module docstring. N_LEVELS is fixed at 6 for these tests (matches the
    real Python tester; the exact number doesn't matter to the logic)."""

    N_LEVELS = 6

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.stats_path = os.path.join(self.tmpdir.name, "stats.jsonl")
        patcher = patch.object(stats, "STATS_PATH", self.stats_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        data_patcher = patch.object(stats, "DATA_DIR", self.tmpdir.name)
        data_patcher.start()
        self.addCleanup(data_patcher.stop)

    def _ids(self):
        return {b[0] for b in achievements.unlocked("py", self.N_LEVELS)}

    def _write_raw(self, entry):
        """Append one hand-built event, bypassing stats.record() — used
        only when a test needs to control "ts" precisely (night_owl/
        early_bird), which record() always sets to the real clock."""
        import json
        os.makedirs(self.tmpdir.name, exist_ok=True)
        with open(self.stats_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def test_nothing_unlocked_with_no_history(self):
        self.assertEqual(achievements.unlocked("py", self.N_LEVELS), [])

    def test_first_blood_needs_one_pass(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        self.assertNotIn("first_blood", self._ids())
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertIn("first_blood", self._ids())

    def test_perfectionist_needs_a_first_attempt_at_100_percent(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertNotIn("perfectionist", self._ids())  # first try failed
        stats.record("py", "py_hidenp", 1, True, 6, 6, "practice")
        self.assertIn("perfectionist", self._ids())  # nailed on try 1

    def test_comeback_kid_needs_a_pass_right_after_the_threshold_streak(self):
        for _ in range(hints.STUCK_THRESHOLD - 1):
            stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertNotIn("comeback_kid", self._ids())  # streak too short
        for _ in range(hints.STUCK_THRESHOLD):
            stats.record("py", "py_hidenp", 1, False, 1, 10, "practice")
        stats.record("py", "py_hidenp", 1, True, 6, 6, "practice")
        self.assertIn("comeback_kid", self._ids())

    def test_redemption_needs_every_attempted_exercise_eventually_passed(self):
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        stats.record("py", "py_hidenp", 1, True, 6, 6, "practice")
        self.assertNotIn("redemption", self._ids())  # py_inter never passed
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        self.assertIn("redemption", self._ids())

    def test_full_coverage_needs_a_pass_on_every_level(self):
        for level in range(1, self.N_LEVELS):
            stats.record("py", "ex%d" % level, level, True, 1, 1, "practice")
        self.assertNotIn("full_coverage", self._ids())  # missing the last level
        stats.record("py", "ex%d" % self.N_LEVELS, self.N_LEVELS, True, 1, 1, "practice")
        self.assertIn("full_coverage", self._ids())

    def test_century_needs_100_total_attempts(self):
        for _ in range(achievements.CENTURY_THRESHOLD - 1):
            stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        self.assertNotIn("century", self._ids())
        stats.record("py", "py_inter", 1, False, 3, 10, "practice")
        self.assertIn("century", self._ids())

    def test_exam_cleared_needs_an_exam_complete_event(self):
        self.assertNotIn("exam_cleared", self._ids())
        stats.record_exam_complete("py", 100.0, self.N_LEVELS, 100)
        self.assertIn("exam_cleared", self._ids())

    def test_flawless_exam_needs_exactly_one_attempt_per_level(self):
        stats.record_exam_complete("py", 200.0, self.N_LEVELS + 2, 100)
        self.assertNotIn("flawless_exam", self._ids())  # 2 retries somewhere
        stats.record_exam_complete("py", 100.0, self.N_LEVELS, 100)
        self.assertIn("flawless_exam", self._ids())

    def test_night_owl_needs_a_pass_between_midnight_and_5am_local(self):
        import datetime
        three_am = datetime.datetime(2024, 1, 1, 3, 0, 0).timestamp()
        noon = datetime.datetime(2024, 1, 1, 12, 0, 0).timestamp()
        self._write_raw({"ts": noon, "tool": "py", "exercise": "py_inter",
                         "level": 1, "ok": True, "passed": 10, "total": 10,
                         "mode": "practice"})
        self.assertNotIn("night_owl", self._ids())
        self._write_raw({"ts": three_am, "tool": "py", "exercise": "py_hidenp",
                         "level": 1, "ok": True, "passed": 6, "total": 6,
                         "mode": "practice"})
        self.assertIn("night_owl", self._ids())

    def test_early_bird_needs_a_pass_between_5am_and_7am_local(self):
        import datetime
        six_am = datetime.datetime(2024, 1, 1, 6, 0, 0).timestamp()
        self._write_raw({"ts": six_am, "tool": "py", "exercise": "py_inter",
                         "level": 1, "ok": True, "passed": 10, "total": 10,
                         "mode": "practice"})
        self.assertIn("early_bird", self._ids())
        self.assertNotIn("night_owl", self._ids())  # ranges don't overlap

    def test_new_since_reports_only_the_freshly_unlocked_ones(self):
        # A first-ever pass unlocks first_blood/perfectionist/redemption
        # all at once (each is trivially true for "one pass, no history")
        # — new_since() must report exactly those three, nothing stale.
        before = achievements.unlocked("py", self.N_LEVELS)
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        after = achievements.unlocked("py", self.N_LEVELS)
        fresh = achievements.new_since(before, after)
        self.assertEqual({b[0] for b in fresh},
                         {"first_blood", "perfectionist", "redemption"})

    def test_new_since_is_empty_when_nothing_changed(self):
        stats.record("py", "py_inter", 1, True, 10, 10, "practice")
        before = achievements.unlocked("py", self.N_LEVELS)
        after = achievements.unlocked("py", self.N_LEVELS)
        self.assertEqual(achievements.new_since(before, after), [])

    def test_is_new_best_time_false_with_no_prior_runs(self):
        self.assertFalse(achievements.is_new_best_time("py", 100.0))

    def test_is_new_best_time(self):
        stats.record_exam_complete("py", 200.0, self.N_LEVELS, 100)
        self.assertTrue(achievements.is_new_best_time("py", 150.0))
        self.assertFalse(achievements.is_new_best_time("py", 250.0))

    def test_badges_are_scoped_per_tool(self):
        stats.record("c", "ft_atoi", 1, True, 10, 10, "practice")
        self.assertNotIn("first_blood", self._ids())


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        patcher = patch.object(session_store, "DATA_DIR", self.tmpdir.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _session(self):
        s = Session(login="alice")
        s.start()
        s.level = 3
        s.passed = ["py_inter", "py_bracket_validator"]
        s.attempts = 5
        s.history = [(1, "py_inter", 1, 12.5), (2, "py_bracket_validator", 2, 30.0)]
        return s

    def test_load_with_nothing_saved_is_none(self):
        self.assertIsNone(session_store.load("py"))

    def test_save_then_load_round_trips_the_shape(self):
        session = self._session()
        rng = random.Random(42)
        ok = session_store.save("py", session, rng, "py_hidenp", level_attempts=2)
        self.assertTrue(ok)
        data = session_store.load("py")
        self.assertIsNotNone(data)
        self.assertEqual(data["login"], "alice")
        self.assertEqual(data["level"], 3)
        self.assertEqual(data["current_ex"], "py_hidenp")
        self.assertEqual(data["passed"], ["py_inter", "py_bracket_validator"])
        self.assertEqual(data["attempts"], 5)
        self.assertEqual(data["level_attempts"], 2)

    def test_level_elapsed_seconds_round_trips_the_time_spent_pre_quit(self):
        # Without level_started, a resume can only restart the current
        # level's clock from the moment of resuming — silently dropping
        # whatever time was already spent on it before the earlier quit.
        session = self._session()
        rng = random.Random(42)
        level_started = time.time() - 90   # 90s already spent on this level
        session_store.save("py", session, rng, "py_hidenp",
                           level_attempts=2, level_started=level_started)
        data = session_store.load("py")
        self.assertAlmostEqual(data["level_elapsed_seconds"], 90, delta=2)

    def test_level_elapsed_seconds_defaults_to_zero_without_level_started(self):
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        data = session_store.load("py")
        self.assertEqual(data["level_elapsed_seconds"], 0)

    def test_rng_state_round_trips_identically(self):
        session = self._session()
        rng = random.Random(1234)
        rng.random()  # advance the state away from the seed-fresh state
        expected_next = [rng.random() for _ in range(5)]
        rng2 = random.Random(1234)
        rng2.random()
        session_store.save("py", session, rng2, "py_hidenp")
        data = session_store.load("py")
        restored = session_store.rng_from_saved(data)
        got_next = [restored.random() for _ in range(5)]
        self.assertEqual(got_next, expected_next)

    def test_load_rejects_a_hand_edited_incomplete_file(self):
        path = session_store._path("py")
        os.makedirs(self.tmpdir.name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"login": "alice"}')  # missing required keys
        self.assertIsNone(session_store.load("py"))

    def test_load_rejects_corrupt_json(self):
        path = session_store._path("py")
        os.makedirs(self.tmpdir.name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(session_store.load("py"))

    def test_clear_removes_the_file(self):
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        self.assertIsNotNone(session_store.load("py"))
        session_store.clear("py")
        self.assertIsNone(session_store.load("py"))

    def test_clear_on_nothing_saved_does_not_raise(self):
        session_store.clear("py")  # must not raise

    def test_py_and_c_tools_use_separate_files(self):
        session = self._session()
        session_store.save("py", session, random.Random(1), "py_hidenp")
        self.assertIsNone(session_store.load("c"))
        self.assertIsNotNone(session_store.load("py"))


class ReportExportTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.reports_dir = os.path.join(self.tmpdir.name, "reports")
        patcher = patch.object(report_export, "REPORTS_DIR", self.reports_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _session(self):
        s = Session(login="bob")
        s.start()
        s.passed = ["py_inter"]
        s.attempts = 3
        s.history = [(1, "py_inter", 3, 45.0)]
        return s

    def test_write_report_returns_a_path_that_exists(self):
        session = self._session()
        path = report_export.write_exam_report("py", session, 6, True, ["🏅 Flawless"])
        self.assertIsNotNone(path)
        self.assertTrue(os.path.isfile(path))

    def test_report_content_has_key_fields(self):
        session = self._session()
        path = report_export.write_exam_report("py", session, 6, True, ["🏅 Flawless"])
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("Exam PASSED", content)
        self.assertIn("bob", content)
        self.assertIn("Python (Rank 03)", content)
        self.assertIn("🏅 Flawless", content)
        self.assertIn("py_inter", content)

    def test_aborted_report_has_no_achievements_line(self):
        session = self._session()
        path = report_export.write_exam_report("c", session, 4, False)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("Exam aborted", content)
        self.assertIn("C (Rank 02)", content)
        self.assertNotIn("Achievements", content)

    def test_a_login_with_path_separators_cannot_escape_reports_dir(self):
        # session.login is free-form student input (see ui.ask("  Login…")
        # in both examshell.py's) — a "/" or ".." in it must never let the
        # report land outside REPORTS_DIR.
        session = self._session()
        session.login = "../../../tmp/evil"
        path = report_export.write_exam_report("py", session, 6, True)
        self.assertIsNotNone(path)
        self.assertEqual(os.path.dirname(os.path.abspath(path)),
                         os.path.abspath(self.reports_dir))
        self.assertTrue(os.path.isfile(path))

    def test_write_report_survives_unwritable_dir(self):
        with patch.object(report_export, "REPORTS_DIR", unwritable_dir(self)):
            session = self._session()
            path = report_export.write_exam_report("py", session, 6, True)
        self.assertIsNone(path)


class HintsTests(unittest.TestCase):
    """diagnose() is a heuristic, not a proof — these tests only pin down
    the specific, deliberately narrow patterns it's supposed to catch
    (see hints.py's module docstring on why it's hedged). It must work
    unmodified on both a Python Report (typed expected/got) and a C one
    (string expected/got, see c_exam/grader.py's CFailure) — every test
    below exercises both."""

    def _report(self, failures=(), fatal="", warnings=()):
        report = Report("some_exercise", "some_func")
        report.failures = list(failures)
        report.fatal = fatal
        report.warnings = list(warnings)
        return report

    def test_no_hint_when_report_is_clean(self):
        report = self._report()
        report.passed = report.total = 1
        self.assertIsNone(hints.diagnose(report))

    def test_timeout_hint(self):
        for code in ("TIMEOUT", "GLOBAL_TIMEOUT", "IMPORT_TIMEOUT"):
            self.assertIn("infinite loop", hints.diagnose(self._report(fatal=code)))

    def test_other_fatal_codes_get_no_generic_hint(self):
        self.assertIsNone(hints.diagnose(self._report(fatal="COMPILE_ERROR")))

    def test_timeout_hint_from_a_c_program_kind_per_case_timeout(self):
        # c_exam/grader.py's _grade_program records a per-case timeout as a
        # non-fatal failure with got="[TIMEOUT]" (see its "note = TIMEOUT"
        # path), not as report.fatal like every other timeout — must still
        # get the TIMEOUT hint, not the CRASH one its own bracket shape
        # would otherwise trigger.
        report = self._report([Failure([], "some output", "[TIMEOUT]")],
                              warnings=["case 2 timed out: TIMEOUT"])
        self.assertIn("infinite loop", hints.diagnose(report))

    def test_timeout_hint_from_a_python_per_case_timeout(self):
        # examshell/grader.py's RUNNER_TEMPLATE records a per-case timeout as a
        # non-fatal failure with got="[TIMEOUT > Ns]" (the per-call timeout
        # value is embedded in the message, unlike the C side's bare
        # "[TIMEOUT]") — must still get the TIMEOUT hint via the same
        # startswith() check, not silently fall through to no hint at all.
        report = self._report([Failure([1, 2], "expected", "[TIMEOUT > 3s]")])
        self.assertIn("infinite loop", hints.diagnose(report))

    def test_crash_warning_hint(self):
        report = self._report(warnings=["your program crashed: segfault"])
        self.assertIn("memory access", hints.diagnose(report))

    def test_leak_warning_hint(self):
        report = self._report(warnings=[
            "valgrind reported memory error(s) (leaks, invalid reads/"
            "writes, ...) on case 3:\n"
            "40 bytes in 1 blocks are definitely lost in loss record 1 of 1"])
        self.assertIn("leak", hints.diagnose(report))

    def test_leak_warning_hint_still_applies_under_strict_valgrind(self):
        # --strict-valgrind sets report.fatal = "VALGRIND_ERRORS" (not one
        # of the TIMEOUT codes) instead of only warning — classify() must
        # still find LEAK from the warning text, not bail out early just
        # because report.fatal is set.
        report = self._report(
            fatal="VALGRIND_ERRORS",
            warnings=["valgrind reported memory error(s) (leaks, invalid "
                      "reads/writes, ...) on case 3:\n"
                      "40 bytes in 1 blocks are definitely lost"])
        self.assertIn("leak", hints.diagnose(report))

    def test_non_leak_valgrind_finding_gets_the_crash_hint_not_leak(self):
        # The boilerplate wrapper message ALWAYS says "leak(s)" regardless
        # of the real finding (see c_exam/grader.py's run_valgrind()
        # callers) — a plain invalid read/write with zero blocks actually
        # leaked used to still trigger the LEAK hint ("trace every malloc
        # to a matching free"), which is wrong guidance for this bug.
        report = self._report(warnings=[
            "valgrind reported memory error(s) (leaks, invalid reads/"
            "writes, ...) on case 3:\n"
            "Invalid write of size 4 at 0x1091A8: ft_strcpy"])
        self.assertIn("memory access", hints.diagnose(report))

    def test_a_solution_that_legitimately_returns_the_string_none_is_not_emptyish(self):
        # An older version of this string-matched "None"/"[]"/"()"/"{}"
        # unconditionally, so a solution whose genuinely correct answer IS
        # the literal string "None" got treated as if it returned nothing.
        report = self._report([Failure([], "None", "something else")])
        self.assertIsNone(hints.diagnose(report))

    def test_crash_is_checked_before_leak(self):
        # A run can't be both, but if warnings ever carried both a crash
        # takes priority — a crash is the more actionable, more urgent
        # thing to point at first.
        report = self._report(warnings=["your program crashed: segfault",
                                        "valgrind reported memory error(s)"])
        self.assertIn("memory access", hints.diagnose(report))

    def test_crash_hint_from_a_python_exception_failure(self):
        # The Python sandbox never appends a "crashed" warning (only the C
        # tester does) — a raised exception shows up as a failing case
        # instead, e.g. "[ZeroDivisionError] division by zero" as `got`.
        report = self._report([Failure([1, 0], 1, "[ZeroDivisionError] division by zero")])
        self.assertIn("memory access", hints.diagnose(report))

    def test_off_by_one_hint_python_and_c_shaped(self):
        py_report = self._report([Failure([5], 4, 5)])
        c_report = self._report([Failure([], "4", "5")])
        for report in (py_report, c_report):
            self.assertIn("off-by-one", hints.diagnose(report))

    def test_bools_are_not_mistaken_for_off_by_one(self):
        # float(True) - float(False) == 1, which would otherwise look
        # exactly like an off-by-one on a completely unrelated bug.
        report = self._report([Failure([], True, False)])
        self.assertIsNone(hints.diagnose(report))

    def test_sign_flip_hint(self):
        report = self._report([Failure([], -3, 3)])
        self.assertIn("sign", hints.diagnose(report))

    def test_empty_expected_hint_python_and_c_shaped(self):
        py_report = self._report([Failure([], [], [1, 2])])
        c_report = self._report([Failure([], "", "1 2")])
        for report in (py_report, c_report):
            self.assertIn("empty", hints.diagnose(report))

    def test_no_hint_for_an_unrelated_mismatch(self):
        report = self._report([Failure([], "hello", "world")])
        self.assertIsNone(hints.diagnose(report))


class HintForTests(unittest.TestCase):
    """hint_for() — picking between a plain-string curated hint, a
    per-category dict one, and the diagnose() fallback (see hints.py's
    module docstring)."""

    def _report(self, failures=(), fatal="", warnings=()):
        report = Report("some_exercise", "some_func")
        report.failures = list(failures)
        report.fatal = fatal
        report.warnings = list(warnings)
        return report

    def test_plain_string_hint_is_returned_as_is(self):
        ex = {"hint": "a static hint"}
        report = self._report([Failure([], "hello", "world")])
        self.assertEqual(hints.hint_for(ex, report), "a static hint")

    def test_no_hint_field_falls_back_to_diagnose(self):
        ex = {}
        report = self._report(fatal="TIMEOUT")
        self.assertIn("infinite loop", hints.hint_for(ex, report))

    def test_dict_hint_picks_the_matching_category(self):
        ex = {"hint": {"crash": "a crash-specific hint",
                       "default": "a fallback hint"}}
        report = self._report(warnings=["your program crashed: segfault"])
        self.assertEqual(hints.hint_for(ex, report), "a crash-specific hint")

    def test_dict_hint_falls_back_to_default_key(self):
        ex = {"hint": {"crash": "a crash-specific hint",
                       "default": "a fallback hint"}}
        report = self._report([Failure([], "hello", "world")])
        self.assertEqual(hints.hint_for(ex, report), "a fallback hint")

    def test_dict_hint_with_no_matching_key_falls_back_to_diagnose(self):
        ex = {"hint": {"crash": "a crash-specific hint"}}
        report = self._report(fatal="TIMEOUT")
        self.assertIn("infinite loop", hints.hint_for(ex, report))


class VersionTests(unittest.TestCase):
    """examshell/version.py is the single source of truth; pyproject.toml and
    CHANGELOG.md must agree with it (the release workflow relies on both)."""

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, name):
        with open(os.path.join(self.ROOT, name), encoding="utf-8") as fh:
            return fh.read()

    def test_pyproject_version_matches(self):
        from examshell.version import __version__
        self.assertIn('version = "%s"' % __version__, self._read("pyproject.toml"))

    def test_changelog_has_a_section_for_this_version(self):
        from examshell.version import __version__
        headings = [line for line in self._read("CHANGELOG.md").splitlines()
                    if line.startswith("## ")]
        self.assertTrue(any(h == "## " + __version__ or h.startswith("## %s " % __version__)
                            for h in headings), headings)


class CaseLabelTests(unittest.TestCase):
    """case_labels.describe(): names the edge-case traits of a failing input."""

    class _F(object):
        def __init__(self, args, program=False):
            self.args, self.program = args, program

    def _d(self, args, program=False):
        from examshell import case_labels
        return case_labels.describe(self._F(args, program))

    def test_strings(self):
        self.assertEqual(self._d([""]), "empty string")
        self.assertEqual(self._d(["   "]), "only whitespace")
        self.assertEqual(self._d(["a\tb"]), "tabs")
        self.assertEqual(self._d([" a"]), "leading/trailing whitespace")
        self.assertEqual(self._d(["a  b"]), "repeated spaces")
        self.assertEqual(self._d(["plain"]), "")

    def test_numbers(self):
        self.assertEqual(self._d([0]), "zero")
        self.assertEqual(self._d([-4]), "negative number")
        self.assertEqual(self._d([-2 ** 31]), "INT_MIN/INT_MAX")
        self.assertEqual(self._d([True]), "")

    def test_lists(self):
        self.assertEqual(self._d([[]]), "empty list")
        self.assertEqual(self._d([[1]]), "single element")

    def test_argv(self):
        self.assertEqual(self._d([], program=True), "no arguments")
        self.assertEqual(self._d(["-3"], program=True), "negative number")
        self.assertEqual(self._d(["0"], program=True), "zero")

    def test_at_most_two_labels_without_duplicates(self):
        self.assertEqual(self._d([" \ta  b ", "", 0]), "tabs · leading/trailing whitespace")

    def test_no_inputs_known(self):
        from examshell import case_labels
        self.assertEqual(case_labels.describe(object()), "")


class ReadinessAndDrillTests(unittest.TestCase):
    """stats.exercise_status() / readiness() / drill_queue()."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
                            ("DATA_DIR", self.tmpdir.name)):
            patcher = patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.clock = 1000.0

    def _grade(self, name, ok, mode="practice"):
        self.clock += 10
        with patch.object(stats.time, "time", return_value=self.clock):
            stats.record("py", name, 1, ok, 1 if ok else 0, 1, mode)

    def test_exercise_status(self):
        self._grade("a", False)
        self._grade("a", True)
        self._grade("b", False)
        status = stats.exercise_status("py", ["a", "b", "c"])
        self.assertEqual(status["a"]["status"], "passed")
        self.assertEqual((status["a"]["passes"], status["a"]["attempts"]), (1, 2))
        self.assertEqual(status["b"]["status"], "failed")
        self.assertEqual(status["c"]["status"], "untried")

    def test_exam_passes_count_for_readiness(self):
        self._grade("a", True, mode="exam")
        levels = stats.readiness("py", {1: ["a", "b"], 2: ["c"]})
        self.assertEqual([(lv, passed, total) for lv, passed, total, _ in levels],
                         [(1, 1, 2), (2, 0, 1)])

    def test_drill_order_weak_then_untried_then_stale(self):
        self._grade("old_pass", True)
        self._grade("new_pass", True)
        self._grade("weak", False)
        queue = stats.drill_queue("py", ["new_pass", "old_pass", "weak", "fresh"], n=4)
        self.assertEqual(queue, ["weak", "fresh", "old_pass", "new_pass"])

    def test_drill_caps_weak_spots_at_half_the_session(self):
        for name in ("w1", "w2", "w3", "w4"):
            self._grade(name, False)
        queue = stats.drill_queue("py", ["w1", "w2", "w3", "w4", "u1", "u2"], n=4)
        self.assertEqual(len(queue), 4)
        self.assertEqual(sorted(queue[2:]), ["u1", "u2"])

    def test_drill_is_short_when_there_are_few_candidates(self):
        self.assertEqual(stats.drill_queue("py", ["x"], n=5), ["x"])


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        from examshell import update_check
        self.uc = update_check
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (("CACHE_PATH", os.path.join(self.tmpdir.name, "u.json")),
                            ("DATA_DIR", self.tmpdir.name)):
            patcher = patch.object(update_check, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_version_comparison(self):
        self.assertTrue(self.uc.is_newer("v0.10.0", "0.9.9"))
        self.assertFalse(self.uc.is_newer("v0.2.0", "0.2.0"))
        self.assertFalse(self.uc.is_newer("garbage", "0.2.0"))

    def test_notice_only_for_a_newer_version(self):
        self.assertIsNone(self.uc.notice_text(None))
        self.assertIsNone(self.uc.notice_text("v0.0.1"))
        self.assertIn("99.0.0", self.uc.notice_text("v99.0.0"))

    def test_result_is_cached_for_a_day_even_when_the_fetch_failed(self):
        calls = []

        def fetch():
            calls.append(1)
            return None

        self.assertIsNone(self.uc.latest_version(now=time.time(), fetch=fetch))
        self.uc.latest_version(now=time.time() + 60, fetch=fetch)
        self.assertEqual(len(calls), 1)
        self.uc.latest_version(now=time.time() + self.uc.CHECK_EVERY + 1, fetch=fetch)
        self.assertEqual(len(calls), 2)

    def test_opt_out(self):
        self.assertFalse(self.uc.enabled(opt_out_flag=True))
        with patch.dict(os.environ, {self.uc.ENV_OPT_OUT: "1"}):
            self.assertFalse(self.uc.enabled())
            self.assertEqual(self.uc.start_background_check(), {"notice": None})


class HistoryStatsTests(unittest.TestCase):
    """stats.daily_activity() / practice_streak() / exam_history()."""

    DAY = 86400

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
                            ("DATA_DIR", self.tmpdir.name)):
            patcher = patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.now = time.mktime((2026, 9, 20, 12, 0, 0, 0, 0, -1))   # local noon

    def _grade(self, days_ago, ok=True):
        with patch.object(stats.time, "time", return_value=self.now - days_ago * self.DAY):
            stats.record("py", "py_inter", 1, ok, 1, 1, "practice")

    def test_daily_activity(self):
        self._grade(0)
        self._grade(0, ok=False)
        self._grade(2)
        activity = stats.daily_activity("py", days=4, now=self.now)
        self.assertEqual(activity, [(0, 0), (1, 1), (0, 0), (2, 1)])

    def test_streak_ends_today_or_yesterday(self):
        for d in (1, 2, 3, 5):
            self._grade(d)
        self.assertEqual(stats.practice_streak("py", now=self.now), 3)
        self._grade(0)
        self.assertEqual(stats.practice_streak("py", now=self.now), 4)
        self.assertEqual(stats.practice_streak("py", now=self.now + 3 * self.DAY), 0)

    def test_exam_history_newest_first(self):
        for i, secs in enumerate((300, 200, 100)):
            with patch.object(stats.time, "time", return_value=self.now + i):
                stats.record_exam_complete("py", secs, 6, 100)
        self.assertEqual([e["seconds"] for e in stats.exam_history("py", n=2)], [100, 200])


class ReflowTests(unittest.TestCase):
    def test_joins_hard_wrapped_lines_and_keeps_paragraphs_and_lists(self):
        from examshell import ui
        prose = "one\ntwo\n\nthree\n  - item\n  - item2\n"
        self.assertEqual(ui._reflow(prose), "one two\n\nthree\n  - item\n  - item2")


if __name__ == "__main__":
    unittest.main()
