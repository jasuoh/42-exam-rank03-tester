#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in c_exam/examshell.py — exercise
resolution, listing, stub creation. Mirrors tests/test_examshell.py's
style. None of these need a C compiler (only file I/O) — compiling is
covered by tests/test_c_grader.py's end-to-end tests instead."""

import argparse
import contextlib
import inspect
import io
import os
import random
import shutil
import tempfile
import unittest
from unittest import mock

from examshell import shell_common

from c_exam import examshell
from c_exam.bank import EXERCISES, N_LEVELS
from c_exam.training_bank import DIFFICULTIES, TRAINING_EXERCISES
from examshell import stats

HAVE_CC = shutil.which("cc") is not None
skip_without_cc = unittest.skipUnless(HAVE_CC, "no C compiler on PATH")


def _cfg(rendu, **overrides):
    args = argparse.Namespace(rendu=rendu, timeout=5, cc="cc",
                              strict_norm=False, show_fails=4, diff=False,
                              seed=None, fuzz=0,
                              valgrind=False, strict_valgrind=False,
                              strict_forbidden=False, strict=False)
    for key, value in overrides.items():
        setattr(args, key, value)
    return examshell.Config(args)


class ConfigStrictTests(unittest.TestCase):
    """--strict is shorthand for --strict-norm + --strict-forbidden +
    --strict-valgrind, and turns on --valgrind itself too."""

    def test_plain_flags_still_work_alone(self):
        cfg = _cfg("x", strict_norm=True, strict_forbidden=True)
        self.assertTrue(cfg.strict_norm)
        self.assertTrue(cfg.strict_forbidden)
        self.assertFalse(cfg.valgrind)

    def test_strict_implies_every_strict_flag_and_valgrind_itself(self):
        cfg = _cfg("x", strict=True)
        self.assertTrue(cfg.strict_norm)
        self.assertTrue(cfg.strict_forbidden)
        self.assertTrue(cfg.strict_valgrind)
        self.assertTrue(cfg.valgrind)

    def test_neither_flag_is_lenient(self):
        cfg = _cfg("x")
        self.assertFalse(cfg.strict_norm)
        self.assertFalse(cfg.strict_forbidden)
        self.assertFalse(cfg.strict_valgrind)
        self.assertFalse(cfg.valgrind)


class FmtDurationTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(examshell.fmt_duration(0), "00:00:00")

    def test_minutes_and_seconds(self):
        self.assertEqual(examshell.fmt_duration(61), "00:01:01")


class ResolveExerciseTests(unittest.TestCase):
    def test_exact_name(self):
        self.assertEqual(examshell.resolve_exercise("ft_atoi"), "ft_atoi")

    def test_unique_suffix(self):
        self.assertEqual(examshell.resolve_exercise("atoi"), "ft_atoi")
        self.assertEqual(examshell.resolve_exercise("putstr"), "ft_putstr")

    def test_prefixed_name_wins_over_other_suffix_matches(self):
        # "range" is a suffix of both ft_range and ft_rrange — the one
        # that is literally "ft_" + "range" must win, not be "ambiguous".
        self.assertEqual(examshell.resolve_exercise("range"), "ft_range")

    def test_unknown_returns_none(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(examshell.resolve_exercise("not_a_real_exercise"))

    def test_ambiguous_suffix_returns_none(self):
        # resolve_exercise searches ALL_EXERCISES (exam + training pool
        # merged at import time) — patch that, not EXERCISES, which it no
        # longer reads.
        fake = {"ft_alpha_demo": {}, "ft_beta_demo": {}}
        with mock.patch.object(examshell, "ALL_EXERCISES", fake), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(examshell.resolve_exercise("demo"))


class ExerciseEntriesTests(unittest.TestCase):
    def test_covers_every_exercise_exactly_once(self):
        entries = examshell.exercise_entries()
        self.assertEqual(len(entries), len(EXERCISES))
        self.assertEqual({name for _, _, name, _, _ in entries}, set(EXERCISES))

    def test_ordered_by_level_then_name(self):
        entries = examshell.exercise_entries()
        levels = [lvl for _, lvl, _, _, _ in entries]
        self.assertEqual(levels, sorted(levels))
        for level in range(1, N_LEVELS + 1):
            names = [name for _, lvl, name, _, _ in entries if lvl == level]
            self.assertEqual(names, sorted(names))

    def test_standard_flag_matches_the_bank(self):
        entries = examshell.exercise_entries()
        flagged = {name for _, _, name, _, standard in entries if standard}
        self.assertEqual(flagged, {n for n in EXERCISES if EXERCISES[n]["standard"]})
        self.assertEqual(len(flagged), 57)

    def test_new_exercises_default_to_extra_not_standard(self):
        # Same opt-IN convention as examshell/exam_bank.py's own bank — every
        # exercise must mark "standard": True explicitly, and an entry
        # that forgets to must fail CLOSED (Extra) rather than silently
        # becoming eligible for a real `make c-exam` draw. Source-level
        # check (not a live-dict one: EXERCISES already has the key on
        # every entry, whether from the source or from this fallback, so
        # only the source pins down which one actually happened).
        import c_exam.bank as bank_module
        src = inspect.getsource(bank_module)
        self.assertIn('_ex.setdefault("standard", False)', src)

    def test_indexes_are_sequential_from_one(self):
        entries = examshell.exercise_entries()
        self.assertEqual([idx for idx, *_ in entries], list(range(1, len(entries) + 1)))


class TrainingEntriesTests(unittest.TestCase):
    def test_covers_every_training_exercise_exactly_once(self):
        entries = examshell.training_entries()
        self.assertEqual(len(entries), len(TRAINING_EXERCISES))
        self.assertEqual({name for _, _, name, _ in entries}, set(TRAINING_EXERCISES))

    def test_ordered_by_difficulty_then_name(self):
        entries = examshell.training_entries()
        order = {d: i for i, d in enumerate(DIFFICULTIES)}
        difficulties = [order[d] for _, d, _, _ in entries]
        self.assertEqual(difficulties, sorted(difficulties))

    def test_never_shares_names_with_the_exam_pool(self):
        # the training pool is a completely separate bank — same spirit
        # as the Python tool's, see training_bank.py's module docstring
        self.assertEqual(set(TRAINING_EXERCISES) & set(EXERCISES), set())


class ResolveExerciseFindsTrainingPoolTests(unittest.TestCase):
    def test_exact_training_name_resolves(self):
        self.assertEqual(examshell.resolve_exercise("array_sum"), "array_sum")

    def test_training_exercise_is_gradeable_through_all_exercises(self):
        self.assertIn("array_sum", examshell.ALL_EXERCISES)
        self.assertEqual(examshell.ALL_EXERCISES["array_sum"]["function"], "array_sum")


class DrawTests(unittest.TestCase):
    def test_avoids_the_given_exercise_when_possible(self):
        import random
        rng = random.Random(0)
        pool = ["a", "b", "c"]
        for _ in range(20):
            self.assertNotEqual(examshell.draw(rng, pool, avoid="a"), "a")


class MakeStubTests(unittest.TestCase):
    def test_creates_file_with_the_right_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("ft_atoi", cfg))
            with open(tmp + "/ft_atoi.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("int ft_atoi(const char *str)", content)

    def test_embeds_a_guarded_self_test_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("ft_atoi", cfg))
            with open(tmp + "/ft_atoi.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("#ifdef SELF_TEST", content)
            self.assertIn("#endif", content)
            # the guard must come AFTER the real function, and its own
            # main() must be inside the guard, not accidentally outside it
            guard_pos = content.index("#ifdef SELF_TEST")
            main_pos = content.index("int main(void)")
            self.assertLess(guard_pos, main_pos)

    def test_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            path = tmp + "/ft_atoi.c"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("/* my own work */\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(examshell.make_stub("ft_atoi", cfg))
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "/* my own work */\n")

    def test_program_kind_stub_has_its_own_main_no_self_test_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("rotone", cfg))
            with open(tmp + "/rotone.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("int main(int argc, char **argv)", content)
            self.assertNotIn("SELF_TEST", content)

    def test_training_exercise_stub_gets_a_c_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("array_sum", cfg))
            with open(tmp + "/array_sum.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("int array_sum(int *arr, unsigned int size)", content)

    def test_exam_stub_is_bare_like_the_real_exam(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = shell_common.exam_config(examshell._SH, _cfg(tmp))
            self.assertTrue(cfg.bare_stub)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("ft_atoi_base", cfg))
                self.assertTrue(examshell.make_stub("rotone", cfg))
                self.assertTrue(examshell.make_stub("ft_list_size", cfg))
            with open(tmp + "/ft_atoi_base.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("int ft_atoi_base(const char *str, int str_base)", content)
            for helper in ("main", "SELF_TEST", "printf", "#include"):
                self.assertNotIn(helper, content)
            with open(tmp + "/rotone.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("int main(int argc, char **argv)", content)
            self.assertNotIn("/tmp/t", content)
            with open(tmp + "/ft_list_size.c", encoding="utf-8") as fh:
                self.assertIn('#include "list.h"', fh.read())

    def test_relaxed_exam_keeps_the_full_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = _cfg(tmp)
            base.relaxed = True
            cfg = shell_common.exam_config(examshell._SH, base)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("ft_atoi_base", cfg))
            with open(tmp + "/ft_atoi_base.c", encoding="utf-8") as fh:
                self.assertIn("SELF_TEST", fh.read())

    def test_list_needing_exercise_also_writes_list_h(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("ft_list_size", cfg))
            with open(tmp + "/ft_list_size.c", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn('#include "list.h"', content)
            with open(tmp + "/list.h", encoding="utf-8") as fh:
                self.assertIn("t_list", fh.read())


class GradeAllValgrindWarningTests(unittest.TestCase):
    """grade_exercise() already warns once when --valgrind is requested but
    the binary isn't on PATH — grade_all() used to silently skip the same
    check, so a whole `--grade-all --valgrind` run gave no indication that
    every one of its (also silently skipped) leak checks had no effect."""

    def test_warns_once_when_valgrind_is_requested_but_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(examshell.grader, "have_valgrind", return_value=False), \
             mock.patch.object(examshell.ui, "warn") as warn, \
             mock.patch.object(examshell.ui, "overview_table"), \
             mock.patch.object(examshell.ui, "note"), \
             mock.patch.object(examshell.ui, "info"):
            cfg = _cfg(tmp, valgrind=True)
            examshell.grade_all(cfg)
        self.assertTrue(any("valgrind" in call.args[0] for call in warn.call_args_list))


@skip_without_cc
class GradeExerciseHintTests(unittest.TestCase):
    """Mirrors tests/test_examshell.py's GradeExerciseHintTests — same
    grade_exercise() wiring (STUCK_THRESHOLD, never during --exam), shared
    verbatim between both testers (see examshell/hints.py)."""

    WRONG_SOLUTION = "int ft_strlen(char *str)\n{\n    (void)str;\n    return -1;\n}\n"

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        stats_patcher = mock.patch.object(
            stats, "STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl"))
        stats_patcher.start()
        self.addCleanup(stats_patcher.stop)
        data_patcher = mock.patch.object(stats, "DATA_DIR", self.tmpdir.name)
        data_patcher.start()
        self.addCleanup(data_patcher.stop)

    def _rendu_with_wrong_solution(self):
        rendu = tempfile.TemporaryDirectory()
        self.addCleanup(rendu.cleanup)
        with open(os.path.join(rendu.name, "ft_strlen.c"), "w", encoding="utf-8") as fh:
            fh.write(self.WRONG_SOLUTION)
        return rendu.name

    def test_no_hint_before_the_threshold(self):
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.object(examshell.hints, "diagnose", return_value="a hint"), \
             mock.patch.object(examshell.ui, "hint") as hint, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(examshell.hints.STUCK_THRESHOLD - 1):
                examshell.grade_exercise("ft_strlen", rng, cfg, mode="practice")
        hint.assert_not_called()

    def test_hint_appears_once_the_threshold_is_reached(self):
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        # ft_strlen now has its own curated hint (see c_exam/bank.py) —
        # blank it out for this test so hint_for() falls through to the
        # generic diagnose() path this test is actually exercising.
        with mock.patch.dict(EXERCISES["ft_strlen"], {"hint": None}), \
             mock.patch.object(examshell.hints, "diagnose", return_value="a hint"), \
             mock.patch.object(examshell.ui, "hint") as hint, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(examshell.hints.STUCK_THRESHOLD):
                examshell.grade_exercise("ft_strlen", rng, cfg, mode="practice")
        hint.assert_called_once_with("a hint")

    def test_never_hints_during_exam_mode(self):
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.object(examshell.hints, "diagnose", return_value="a hint"), \
             mock.patch.object(examshell.ui, "hint") as hint, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(examshell.hints.STUCK_THRESHOLD + 2):
                examshell.grade_exercise("ft_strlen", rng, cfg, mode="exam")
        hint.assert_not_called()

    def test_curated_bank_hint_is_preferred_over_the_generic_one(self):
        rendu = tempfile.TemporaryDirectory()
        self.addCleanup(rendu.cleanup)
        with open(os.path.join(rendu.name, "ft_split.c"), "w", encoding="utf-8") as fh:
            fh.write("#include <stdlib.h>\n"
                    "char **ft_split(char *str)\n{\n    (void)str;\n"
                    "    return calloc(1, sizeof(char *));\n}\n")
        cfg = _cfg(rendu.name, fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.object(examshell.hints, "diagnose", return_value="generic"), \
             mock.patch.object(examshell.ui, "hint") as hint, \
             contextlib.redirect_stdout(io.StringIO()):
            for _ in range(examshell.hints.STUCK_THRESHOLD):
                examshell.grade_exercise("ft_split", rng, cfg, mode="practice")
        hint.assert_called_once_with(EXERCISES["ft_split"]["hint"]["default"])


class TrainCliCaseTests(unittest.TestCase):
    """Mirrors tests/test_examshell.py's class of the same name — same
    fix, same regression, both examshell.py's own --train handling."""

    def test_train_resolves_an_uppercase_exercise_name(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(examshell, "training_mode") as training_mode, \
             contextlib.redirect_stdout(io.StringIO()):
            rc = examshell.main(["--train", "ARRAY_SUM", "--rendu", tmp])
        self.assertEqual(rc, 0)
        training_mode.assert_called_once_with(mock.ANY, ex_name="array_sum")


class NewCommandResetsLevelTimingTests(unittest.TestCase):
    """Mirrors tests/test_examshell.py's class of the same name — same
    fix, same regression, both examshell.py's exam_mode()."""

    def test_attempts_after_new_do_not_include_the_abandoned_exercise(self):
        cfg = _cfg("unused-rendu", fuzz=0, seed=None, relaxed=True)
        ask_calls = ["  ", "grademe", "new", "grademe"]
        captured = {}

        def fake_summary(session, passed):
            captured["session"] = session

        with mock.patch.object(examshell, "grade_exercise", side_effect=[False, True]), \
             mock.patch.object(examshell, "exam_summary", side_effect=fake_summary), \
             mock.patch.object(examshell.session_store, "load", return_value=None), \
             mock.patch.object(examshell.session_store, "save"), \
             mock.patch.object(examshell.session_store, "clear"), \
             mock.patch.object(examshell.ui, "ask", side_effect=ask_calls), \
             mock.patch.object(examshell.ui, "pause", side_effect=examshell.ui.Abort()), \
             mock.patch.object(examshell.ui, "clear"), \
             mock.patch.object(examshell.ui, "banner"), \
             mock.patch.object(examshell.ui, "status_bar"), \
             mock.patch.object(examshell.ui, "subject"), \
             mock.patch.object(examshell.ui, "commands"), \
             mock.patch.object(examshell.ui, "level_cleared"), \
             mock.patch.object(examshell.ui, "info"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.exam_mode(cfg)

        self.assertEqual(captured["session"].history[0][2], 1)


class ExamModeAbortAtLevelPauseTests(unittest.TestCase):
    """Mirrors tests/test_examshell.py's class of the same name — same fix,
    same regression, both examshell.py's (see examshell/examshell.py's exam_mode
    and c_exam/examshell.py's own copy)."""

    def _run(self, pause_side_effect, n_asks):
        cfg = _cfg("unused-rendu", fuzz=0, seed=None)
        ask_calls = ["  "] + ["grademe"] * n_asks
        with mock.patch.object(examshell, "grade_exercise", return_value=True), \
             mock.patch.object(examshell.session_store, "load", return_value=None), \
             mock.patch.object(examshell.session_store, "save") as save, \
             mock.patch.object(examshell.session_store, "clear") as clear, \
             mock.patch.object(examshell.report_export, "write_exam_report", return_value=None), \
             mock.patch.object(examshell.stats, "best_exam_time", return_value=None), \
             mock.patch.object(examshell.stats, "record_exam_complete"), \
             mock.patch.object(examshell.ui, "ask", side_effect=ask_calls), \
             mock.patch.object(examshell.ui, "pause", side_effect=pause_side_effect), \
             mock.patch.object(examshell.ui, "summary") as summary, \
             mock.patch.object(examshell.ui, "clear"), \
             mock.patch.object(examshell.ui, "banner"), \
             mock.patch.object(examshell.ui, "status_bar"), \
             mock.patch.object(examshell.ui, "subject"), \
             mock.patch.object(examshell.ui, "commands"), \
             mock.patch.object(examshell.ui, "level_cleared"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.exam_mode(cfg)
        return save, clear, summary

    def test_abort_on_the_final_level_pause_still_shows_a_passed_summary(self):
        pause_effects = [None] * (N_LEVELS - 1) + [examshell.ui.Abort()]
        save, clear, summary = self._run(pause_effects, n_asks=N_LEVELS)
        save.assert_not_called()
        clear.assert_called_once_with(examshell.TOOL)
        summary.assert_called_once()
        self.assertIn("PASSED", summary.call_args[0][0])

    def test_abort_on_a_mid_exam_level_pause_still_shows_an_aborted_summary(self):
        save, clear, summary = self._run([examshell.ui.Abort()], n_asks=1)
        save.assert_called_once()
        clear.assert_not_called()
        summary.assert_called_once()
        self.assertIn("ABORTED", summary.call_args[0][0])


class SeededExamIsReproducibleTests(unittest.TestCase):
    """--seed N must reproduce the same exam no matter how often the
    student types `grademe`: grading (fuzz cases) draws from its own RNG,
    never from the one that picks each level's exercise."""

    def _drawn(self, fails_per_level):
        cfg = _cfg("unused-rendu", fuzz=0, seed=1234)
        drawn = []
        outcomes = ([False] * fails_per_level + [True]) * N_LEVELS

        def fake_grade(ex_name, rng, cfg, mode="practice"):
            for _ in range(50):            # what a fuzzed grading run does
                rng.random()
            return outcomes.pop(0)

        def fake_subject(ex_name, cfg, session=None):
            if not drawn or drawn[-1] != ex_name:
                drawn.append(ex_name)

        asks = ["  "] + ["grademe"] * len(outcomes)
        with mock.patch.object(examshell, "grade_exercise", side_effect=fake_grade), \
             mock.patch.object(examshell, "show_subject", side_effect=fake_subject), \
             mock.patch.object(examshell, "exam_summary"), \
             mock.patch.object(examshell.session_store, "load", return_value=None), \
             mock.patch.object(examshell.session_store, "save"), \
             mock.patch.object(examshell.session_store, "clear"), \
             mock.patch.object(examshell.ui, "ask", side_effect=asks), \
             mock.patch.object(examshell.ui, "pause"), \
             mock.patch.object(examshell.ui, "clear"), \
             mock.patch.object(examshell.ui, "banner"), \
             mock.patch.object(examshell.ui, "commands"), \
             mock.patch.object(examshell.ui, "level_cleared"), \
             mock.patch.object(examshell.ui, "info"), \
             mock.patch.object(examshell.ui, "note"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.exam_mode(cfg)
        return drawn

    def test_retries_do_not_change_later_draws(self):
        first_try = self._drawn(fails_per_level=0)
        with_retries = self._drawn(fails_per_level=3)
        self.assertEqual(len(first_try), N_LEVELS)
        self.assertEqual(first_try, with_retries)



STRICT_FLAGS = ("strict_norm", "strict_forbidden")
class RealisticExamModeTests(unittest.TestCase):
    """By default the exam grades as strictly as the real one and has no
    `new`; --relaxed restores the lenient behaviour. --time-limit ends it."""

    def test_exam_config_is_strict_by_default(self):
        cfg = examshell.exam_config(_cfg("x"))
        for flag in STRICT_FLAGS:
            self.assertTrue(getattr(cfg, flag), flag)

    def test_exam_config_leaves_the_original_config_alone(self):
        base = _cfg("x")
        examshell.exam_config(base)
        for flag in STRICT_FLAGS:
            self.assertFalse(getattr(base, flag), flag)

    def test_relaxed_keeps_lenient_grading(self):
        cfg = examshell.exam_config(_cfg("x", relaxed=True))
        for flag in STRICT_FLAGS:
            self.assertFalse(getattr(cfg, flag), flag)

    def test_new_is_hidden_unless_relaxed(self):
        names = [n for n, _ in examshell.exam_commands(_cfg("x"))]
        self.assertNotIn("new", names)
        names = [n for n, _ in examshell.exam_commands(_cfg("x", relaxed=True))]
        self.assertIn("new", names)

    def _run(self, cfg, asks, **patches):
        captured = {}

        def fake_summary(session, passed, timed_out=False):
            captured.update(session=session, passed=passed, timed_out=timed_out)

        with mock.patch.object(examshell, "grade_exercise", return_value=False), \
             mock.patch.object(examshell, "exam_summary", side_effect=fake_summary), \
             mock.patch.object(examshell.session_store, "load", return_value=None), \
             mock.patch.object(examshell.session_store, "save"), \
             mock.patch.object(examshell.session_store, "clear"), \
             mock.patch.object(examshell.ui, "ask", side_effect=asks), \
             mock.patch.object(examshell.ui, "warn") as warn, \
             mock.patch.object(examshell.ui, "clear"), \
             mock.patch.object(examshell.ui, "banner"), \
             mock.patch.object(examshell.ui, "status_bar"), \
             mock.patch.object(examshell.ui, "subject"), \
             mock.patch.object(examshell.ui, "commands"), \
             mock.patch.object(examshell.ui, "info"), \
             mock.patch.object(examshell.ui, "note"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.exam_mode(cfg)
        return captured, warn

    def test_new_is_refused_in_realistic_mode(self):
        cfg = _cfg("unused-rendu")
        captured, warn = self._run(cfg, ["  ", "new", "quit"])
        self.assertTrue(any("--relaxed" in c.args[0] for c in warn.call_args_list))
        self.assertFalse(captured["timed_out"])

    def test_time_limit_ends_the_exam(self):
        cfg = _cfg("unused-rendu", time_limit=1)
        with mock.patch.object(shell_common.time, "time",
                               side_effect=[1000.0] + [1000.0 + 61] * 50):
            captured, _warn = self._run(cfg, ["  ", "grademe"])
        self.assertTrue(captured["timed_out"])
        self.assertFalse(captured["passed"])

    def test_countdown_only_with_a_time_limit(self):
        session = examshell.Session()
        session.start_time = shell_common.time.time()
        self.assertEqual(examshell.countdown(session, _cfg("x")), "")
        self.assertIn("left", examshell.countdown(session, _cfg("x", time_limit=90)))


class ReadinessAndDrillModeTests(unittest.TestCase):
    """--readiness / --drill wiring (the ranking itself is tested in
    tests/test_shared.py)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
                            ("DATA_DIR", self.tmpdir.name)):
            patcher = mock.patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_readiness_lists_every_standard_exercise(self):
        with mock.patch.object(examshell.ui, "overview_table") as table, \
             mock.patch.object(examshell.ui, "summary"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.readiness_mode(interactive=False)
        rows = table.call_args[0][0]
        standard = {n for n in examshell.EXERCISES if examshell.EXERCISES[n]["standard"]}
        self.assertEqual({row[1] for row in rows}, standard)
        self.assertTrue(all(row[2] == "missing" for row in rows))

    def test_drill_practises_n_standard_exercises(self):
        with mock.patch.object(examshell, "practice_one") as practice, \
             mock.patch.object(examshell.ui, "pause"), \
             mock.patch.object(examshell.ui, "clear"), \
             contextlib.redirect_stdout(io.StringIO()):
            examshell.drill_mode(_cfg("x"), n=3)
        self.assertEqual(practice.call_count, 3)
        for call in practice.call_args_list:
            self.assertTrue(examshell.EXERCISES[call[0][0]]["standard"])
            self.assertEqual(call[1]["mode"], "drill")


if __name__ == "__main__":
    unittest.main()
