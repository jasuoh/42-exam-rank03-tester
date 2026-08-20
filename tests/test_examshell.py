#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in src/examshell.py — CLI plumbing,
exercise resolution, formatting — not the interactive flow itself."""

import argparse
import contextlib
import io
import random
import tempfile
import unittest
from unittest import mock

from src import examshell
from src.exam_bank import EXERCISES, N_LEVELS
from src.training_bank import DIFFICULTIES, TRAINING_EXERCISES


def _cfg(rendu, **overrides):
    args = argparse.Namespace(rendu=rendu, timeout=3, fuzz=0,
                              strict_imports=False, show_fails=4, seed=None)
    for key, value in overrides.items():
        setattr(args, key, value)
    return examshell.Config(args)


class FmtDurationTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(examshell.fmt_duration(0), "00:00:00")

    def test_minutes_and_seconds(self):
        self.assertEqual(examshell.fmt_duration(61), "00:01:01")

    def test_hours(self):
        self.assertEqual(examshell.fmt_duration(3661), "01:01:01")


class ResolveExerciseTests(unittest.TestCase):
    def test_exact_name(self):
        self.assertEqual(examshell.resolve_exercise("py_inter"), "py_inter")

    def test_unique_suffix(self):
        self.assertEqual(examshell.resolve_exercise("inter"), "py_inter")
        self.assertEqual(examshell.resolve_exercise("cipher"), "py_whisper_cipher")

    def test_finds_a_training_exercise_too(self):
        self.assertEqual(examshell.resolve_exercise("fizzbuzz_list"),
                         "py_fizzbuzz_list")
        self.assertEqual(examshell.resolve_exercise("py_kth_largest"),
                         "py_kth_largest")

    def test_unknown_returns_none(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(examshell.resolve_exercise("not_a_real_exercise"))

    def test_ambiguous_suffix_returns_none(self):
        fake = {"py_alpha_demo": {}, "py_beta_demo": {}}
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
        self.assertEqual(len(flagged), 14)

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
        ranks = [order[d] for _, d, _, _ in entries]
        self.assertEqual(ranks, sorted(ranks))
        for difficulty in DIFFICULTIES:
            names = [name for _, d, name, _ in entries if d == difficulty]
            self.assertEqual(names, sorted(names))

    def test_indexes_are_sequential_from_one(self):
        entries = examshell.training_entries()
        self.assertEqual([idx for idx, *_ in entries], list(range(1, len(entries) + 1)))

    def test_never_overlaps_the_exam_pool(self):
        self.assertEqual(set(TRAINING_EXERCISES) & set(EXERCISES), set())


class DrawTests(unittest.TestCase):
    def test_avoids_the_given_exercise_when_possible(self):
        rng = random.Random(0)
        pool = ["a", "b", "c"]
        for _ in range(20):
            self.assertNotEqual(examshell.draw(rng, pool, avoid="a"), "a")

    def test_falls_back_when_the_pool_has_only_one_exercise(self):
        rng = random.Random(0)
        self.assertEqual(examshell.draw(rng, ["only"], avoid="only"), "only")

    def test_no_avoid_can_return_anything_in_the_pool(self):
        rng = random.Random(0)
        self.assertIn(examshell.draw(rng, ["a", "b"]), ("a", "b"))


class MakeStubTests(unittest.TestCase):
    def test_creates_file_with_the_right_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("py_inter", cfg))
            with open(tmp + "/py_inter.py", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("def inter(", content)

    def test_embeds_a_runnable_self_check_from_the_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("py_inter", cfg))
            with open(tmp + "/py_inter.py", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn('if __name__ == "__main__"', content)
            # py_inter's first curated case is ["hello", "world"] -> "lo";
            # this locks in that the sample comes from the oracle, not a guess.
            self.assertIn("(['hello', 'world'], 'lo')", content)
            # must be valid, importable Python (the __main__ guard keeps the
            # self-check from running here, same as during real grading)
            namespace = {"__name__": "not_main"}
            exec(compile(content, "py_inter.py", "exec"), namespace)

    def test_works_for_a_training_exercise_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("py_fizzbuzz_list", cfg))
            with open(tmp + "/py_fizzbuzz_list.py", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("def fizzbuzz_list(", content)
            self.assertIn('if __name__ == "__main__"', content)

    def test_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            path = tmp + "/py_inter.py"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("# my own work\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(examshell.make_stub("py_inter", cfg))
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "# my own work\n")


class GradeAllTests(unittest.TestCase):
    def test_reports_missing_ok_and_ko_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp, fuzz=0, seed=0)

            with open(tmp + "/py_inter.py", "w", encoding="utf-8") as fh:
                fh.write("def inter(s1, s2):\n    return ''\n")   # wrong on purpose

            with mock.patch.object(examshell.ui, "overview_table") as captured, \
                 contextlib.redirect_stdout(io.StringIO()):
                ok = examshell.grade_all(cfg)

            self.assertFalse(ok)
            rows = {name: status for _, name, status, _ in captured.call_args[0][0]}
            self.assertEqual(rows["py_inter"], "ko")
            self.assertEqual(rows["py_cryptic_sorter"], "missing")
            self.assertEqual(len(rows), len(EXERCISES))

    def test_true_when_nothing_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.grade_all(cfg))


if __name__ == "__main__":
    unittest.main()
