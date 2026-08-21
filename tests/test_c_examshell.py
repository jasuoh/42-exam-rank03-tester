#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in c_exam/examshell.py — exercise
resolution, listing, stub creation. Mirrors tests/test_examshell.py's
style. None of these need a C compiler (only file I/O) — compiling is
covered by tests/test_c_grader.py's end-to-end tests instead."""

import argparse
import contextlib
import io
import tempfile
import unittest
from unittest import mock

from c_exam import examshell
from c_exam.bank import EXERCISES, N_LEVELS


def _cfg(rendu, **overrides):
    args = argparse.Namespace(rendu=rendu, timeout=5, cc="cc",
                              strict_norm=False, show_fails=4, seed=None)
    for key, value in overrides.items():
        setattr(args, key, value)
    return examshell.Config(args)


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

    def test_unknown_returns_none(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(examshell.resolve_exercise("not_a_real_exercise"))

    def test_ambiguous_suffix_returns_none(self):
        fake = {"ft_alpha_demo": {}, "ft_beta_demo": {}}
        with mock.patch.object(examshell, "EXERCISES", fake), \
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

    def test_all_entries_are_standard(self):
        entries = examshell.exercise_entries()
        self.assertTrue(all(standard for *_, standard in entries))

    def test_indexes_are_sequential_from_one(self):
        entries = examshell.exercise_entries()
        self.assertEqual([idx for idx, *_ in entries], list(range(1, len(entries) + 1)))


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


if __name__ == "__main__":
    unittest.main()
