#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in examshell/examshell.py — CLI plumbing,
exercise resolution, formatting — not the interactive flow itself."""

from __future__ import annotations

import argparse
import contextlib
import inspect
import io
import os
import random
import tempfile
import time
import unittest
from typing import Any, Dict, List, Tuple
from unittest import mock

from examshell import hints
from examshell import session_store
from examshell import shell_common
from examshell import ui

from examshell import examshell, stats
from examshell.exam_bank import EXERCISES, N_LEVELS
from examshell.training_bank import DIFFICULTIES, TRAINING_EXERCISES


def _cfg(rendu: str, **overrides: Any) -> examshell.Config:
    args = argparse.Namespace(
        rendu=rendu,
        timeout=3,
        fuzz=0,
        strict_imports=False,
        strict=False,
        show_fails=4,
        diff=False,
        seed=None,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    return examshell.Config(args)


class ConfigStrictTests(unittest.TestCase):
    """--strict is shorthand for every --strict-* flag at once."""

    def test_plain_strict_imports_still_works_alone(self) -> None:
        cfg = _cfg("x", strict_imports=True)
        self.assertTrue(cfg.strict_imports)

    def test_strict_implies_strict_imports(self) -> None:
        cfg = _cfg("x", strict=True)
        self.assertTrue(cfg.strict_imports)

    def test_neither_flag_is_lenient(self) -> None:
        cfg = _cfg("x")
        self.assertFalse(cfg.strict_imports)


class FmtDurationTests(unittest.TestCase):
    def test_zero(self) -> None:
        self.assertEqual(shell_common.fmt_duration(0), "00:00:00")

    def test_minutes_and_seconds(self) -> None:
        self.assertEqual(shell_common.fmt_duration(61), "00:01:01")

    def test_hours(self) -> None:
        self.assertEqual(shell_common.fmt_duration(3661), "01:01:01")


class ResolveExerciseTests(unittest.TestCase):
    def test_exact_name(self) -> None:
        self.assertEqual(examshell.resolve_exercise("py_inter"), "py_inter")

    def test_unique_suffix(self) -> None:
        self.assertEqual(examshell.resolve_exercise("inter"), "py_inter")
        self.assertEqual(
            examshell.resolve_exercise("cipher"), "py_whisper_cipher"
        )

    def test_finds_a_training_exercise_too(self) -> None:
        self.assertEqual(
            examshell.resolve_exercise("fizzbuzz_list"), "py_fizzbuzz_list"
        )
        self.assertEqual(
            examshell.resolve_exercise("py_kth_largest"), "py_kth_largest"
        )

    def test_prefixed_name_wins_over_other_suffix_matches(self) -> None:
        fake: Dict[str, Dict[str, Any]] = {
            "py_inter": {},
            "py_union_inter": {},
        }
        with mock.patch.object(examshell, "ALL_EXERCISES", fake):
            self.assertEqual(examshell.resolve_exercise("inter"), "py_inter")

    def test_unknown_returns_none(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(
                examshell.resolve_exercise("not_a_real_exercise")
            )

    def test_ambiguous_suffix_returns_none(self) -> None:
        fake: Dict[str, Dict[str, Any]] = {
            "py_alpha_demo": {},
            "py_beta_demo": {},
        }
        with mock.patch.object(
            examshell, "ALL_EXERCISES", fake
        ), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(examshell.resolve_exercise("demo"))


class ExerciseEntriesTests(unittest.TestCase):
    def test_covers_every_exercise_exactly_once(self) -> None:
        entries = examshell.exercise_entries()
        self.assertEqual(len(entries), len(EXERCISES))
        self.assertEqual(
            {name for _, _, name, _, _ in entries}, set(EXERCISES)
        )

    def test_ordered_by_level_then_name(self) -> None:
        entries = examshell.exercise_entries()
        levels = [lvl for _, lvl, _, _, _ in entries]
        self.assertEqual(levels, sorted(levels))
        for level in range(1, N_LEVELS + 1):
            names = [name for _, lvl, name, _, _ in entries if lvl == level]
            self.assertEqual(names, sorted(names))

    def test_standard_flag_matches_the_bank(self) -> None:
        entries = examshell.exercise_entries()
        flagged = {name for _, _, name, _, standard in entries if standard}
        self.assertEqual(
            flagged, {n for n in EXERCISES if EXERCISES[n]["standard"]}
        )
        self.assertEqual(len(flagged), 14)

    def test_new_exercises_default_to_extra_not_standard(self) -> None:
        # Fail-CLOSED by design: an exercise that forgets to mark itself
        # "standard": True must never silently become eligible for a real
        # `make exam` draw (see c_exam/bank.py's own copy of this test —
        # it used to default the opposite way there).
        import examshell.exam_bank as bank_module

        src = inspect.getsource(bank_module)
        self.assertIn('_ex.setdefault("standard", False)', src)

    def test_indexes_are_sequential_from_one(self) -> None:
        entries = examshell.exercise_entries()
        self.assertEqual(
            [idx for idx, *_ in entries], list(range(1, len(entries) + 1))
        )


class TrainingEntriesTests(unittest.TestCase):
    def test_covers_every_training_exercise_exactly_once(self) -> None:
        entries = examshell.training_entries()
        self.assertEqual(len(entries), len(TRAINING_EXERCISES))
        self.assertEqual(
            {name for _, _, name, _ in entries}, set(TRAINING_EXERCISES)
        )

    def test_ordered_by_difficulty_then_name(self) -> None:
        entries = examshell.training_entries()
        order = {d: i for i, d in enumerate(DIFFICULTIES)}
        ranks = [order[d] for _, d, _, _ in entries]
        self.assertEqual(ranks, sorted(ranks))
        for difficulty in DIFFICULTIES:
            names = [name for _, d, name, _ in entries if d == difficulty]
            self.assertEqual(names, sorted(names))

    def test_indexes_are_sequential_from_one(self) -> None:
        entries = examshell.training_entries()
        self.assertEqual(
            [idx for idx, *_ in entries], list(range(1, len(entries) + 1))
        )

    def test_never_overlaps_the_exam_pool(self) -> None:
        self.assertEqual(set(TRAINING_EXERCISES) & set(EXERCISES), set())


class DrawTests(unittest.TestCase):
    def test_avoids_the_given_exercise_when_possible(self) -> None:
        rng = random.Random(0)
        pool = ["a", "b", "c"]
        for _ in range(20):
            self.assertNotEqual(shell_common.draw(rng, pool, avoid="a"), "a")

    def test_falls_back_when_the_pool_has_only_one_exercise(self) -> None:
        rng = random.Random(0)
        self.assertEqual(
            shell_common.draw(rng, ["only"], avoid="only"), "only"
        )

    def test_no_avoid_can_return_anything_in_the_pool(self) -> None:
        rng = random.Random(0)
        self.assertIn(shell_common.draw(rng, ["a", "b"]), ("a", "b"))


class MakeStubTests(unittest.TestCase):
    def test_creates_file_with_the_right_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("py_inter", cfg))
            with open(tmp + "/py_inter.py", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("def inter(", content)

    def test_embeds_a_runnable_self_check_from_the_oracle(self) -> None:
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

    def test_works_for_a_training_exercise_too(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.make_stub("py_fizzbuzz_list", cfg))
            with open(tmp + "/py_fizzbuzz_list.py", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("def fizzbuzz_list(", content)
            self.assertIn('if __name__ == "__main__"', content)

    def test_never_overwrites_an_existing_file(self) -> None:
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
    def test_reports_missing_ok_and_ko_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp, fuzz=0, seed=0)

            with open(tmp + "/py_inter.py", "w", encoding="utf-8") as fh:
                fh.write(
                    "def inter(s1, s2):\n    return ''\n"
                )  # wrong on purpose

            with mock.patch.object(
                ui, "overview_table"
            ) as captured, contextlib.redirect_stdout(io.StringIO()):
                ok = examshell.grade_all(cfg)

            self.assertFalse(ok)
            rows = {
                name: status for _, name, status, _ in captured.call_args[0][0]
            }
            self.assertEqual(rows["py_inter"], "ko")
            self.assertEqual(rows["py_cryptic_sorter"], "missing")
            self.assertEqual(len(rows), len(EXERCISES))

    def test_true_when_nothing_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _cfg(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(examshell.grade_all(cfg))


class GradeExerciseHintTests(unittest.TestCase):
    """grade_exercise()'s stuck-student nudge (see examshell/hints.py) — a
    generic diagnose() hint only appears after STUCK_THRESHOLD consecutive
    fails on the same exercise, and never during --exam."""

    WRONG_SOLUTION = "def inter(s1, s2):\n    return ''\n"  # always fails

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        stats_patcher = mock.patch.object(
            stats, "STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")
        )
        stats_patcher.start()
        self.addCleanup(stats_patcher.stop)
        data_patcher = mock.patch.object(stats, "DATA_DIR", self.tmpdir.name)
        data_patcher.start()
        self.addCleanup(data_patcher.stop)

    def _rendu_with_wrong_solution(self) -> str:
        rendu = tempfile.TemporaryDirectory()
        self.addCleanup(rendu.cleanup)
        with open(
            os.path.join(rendu.name, "py_inter.py"), "w", encoding="utf-8"
        ) as fh:
            fh.write(self.WRONG_SOLUTION)
        return rendu.name

    # These patch hints.diagnose() to a canned string so they test only
    # grade_exercise()'s wiring (streak threshold, exam exclusion) — the
    # heuristic's own accuracy is HintsTests' job in test_shared.py, and
    # coupling both here would make this test flaky against unrelated
    # changes to diagnose()'s pattern matching. py_inter now carries its
    # own curated hint (see exam_bank.py), which would otherwise short-
    # circuit hints.diagnose() entirely (see hints.hint_for()) — these
    # tests stub it back to None so the diagnose() mock stays the one
    # and only hint source, same as before py_inter had a curated hint.

    def test_no_hint_before_the_threshold(self) -> None:
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.dict(
            EXERCISES["py_inter"], {"hint": None}
        ), mock.patch.object(
            hints, "diagnose", return_value="a hint"
        ), mock.patch.object(ui, "hint") as hint, contextlib.redirect_stdout(
            io.StringIO()
        ):
            for _ in range(hints.STUCK_THRESHOLD - 1):
                examshell.grade_exercise("py_inter", rng, cfg, mode="practice")
        hint.assert_not_called()

    def test_hint_appears_once_the_threshold_is_reached(self) -> None:
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.dict(
            EXERCISES["py_inter"], {"hint": None}
        ), mock.patch.object(
            hints, "diagnose", return_value="a hint"
        ), mock.patch.object(ui, "hint") as hint, contextlib.redirect_stdout(
            io.StringIO()
        ):
            for _ in range(hints.STUCK_THRESHOLD):
                examshell.grade_exercise("py_inter", rng, cfg, mode="practice")
        hint.assert_called_once_with("a hint")

    def test_never_hints_during_exam_mode(self) -> None:
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.dict(
            EXERCISES["py_inter"], {"hint": None}
        ), mock.patch.object(
            hints, "diagnose", return_value="a hint"
        ), mock.patch.object(ui, "hint") as hint, contextlib.redirect_stdout(
            io.StringIO()
        ):
            for _ in range(hints.STUCK_THRESHOLD + 2):
                examshell.grade_exercise("py_inter", rng, cfg, mode="exam")
        hint.assert_not_called()

    def test_no_hint_when_diagnose_finds_no_pattern(self) -> None:
        cfg = _cfg(self._rendu_with_wrong_solution(), fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.dict(
            EXERCISES["py_inter"], {"hint": None}
        ), mock.patch.object(
            hints, "diagnose", return_value=None
        ), mock.patch.object(ui, "hint") as hint, contextlib.redirect_stdout(
            io.StringIO()
        ):
            for _ in range(hints.STUCK_THRESHOLD):
                examshell.grade_exercise("py_inter", rng, cfg, mode="practice")
        hint.assert_not_called()

    def test_curated_bank_hint_is_preferred_over_the_generic_one(self) -> None:
        rendu = tempfile.TemporaryDirectory()
        self.addCleanup(rendu.cleanup)
        with open(
            os.path.join(rendu.name, "py_prime_finder.py"),
            "w",
            encoding="utf-8",
        ) as fh:
            fh.write("def prime_finder(n):\n    return True\n")  # always fails
        cfg = _cfg(rendu.name, fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.object(
            hints, "diagnose", return_value="generic"
        ), mock.patch.object(ui, "hint") as hint, contextlib.redirect_stdout(
            io.StringIO()
        ):
            for _ in range(hints.STUCK_THRESHOLD):
                examshell.grade_exercise(
                    "py_prime_finder", rng, cfg, mode="practice"
                )
        hint.assert_called_once_with(EXERCISES["py_prime_finder"]["hint"])

    def test_no_hint_once_the_solution_is_fixed(self) -> None:
        rendu = self._rendu_with_wrong_solution()
        cfg = _cfg(rendu, fuzz=0, seed=0)
        rng = random.Random(0)
        with mock.patch.dict(
            EXERCISES["py_inter"], {"hint": None}
        ), contextlib.redirect_stdout(io.StringIO()):
            for _ in range(hints.STUCK_THRESHOLD - 1):
                examshell.grade_exercise("py_inter", rng, cfg, mode="practice")
            with open(
                os.path.join(rendu, "py_inter.py"), "w", encoding="utf-8"
            ) as fh:
                fh.write(
                    "def inter(s1, s2):\n"
                    "    return sorted(set(s1) & set(s2))\n"
                )
            with mock.patch.object(ui, "hint") as hint:
                examshell.grade_exercise("py_inter", rng, cfg, mode="practice")
        hint.assert_not_called()


class TrainCliCaseTests(unittest.TestCase):
    """--train's exercise-name branch used to resolve against the ORIGINAL
    (mixed-case) argv value even though a lowercased `value` was already
    computed right above it for the difficulty check — regression test for
    that inconsistency (c_exam/examshell.py's main() has the identical
    bug/fix)."""

    def test_train_resolves_an_uppercase_exercise_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            examshell, "training_mode"
        ) as training_mode, contextlib.redirect_stdout(io.StringIO()):
            rc = examshell.main(
                ["--train", "PY_FIZZBUZZ_LIST", "--rendu", tmp]
            )
        self.assertEqual(rc, 0)
        training_mode.assert_called_once_with(
            mock.ANY, ex_name="py_fizzbuzz_list"
        )


class NewCommandResetsLevelTimingTests(unittest.TestCase):
    """'new' (draw a different exercise for this level) used to leave
    level_attempts/level_started tied to the exercise just abandoned — a
    later solve on the freshly drawn one would misattribute the abandoned
    exercise's own failed attempt (and the time spent on it) to the new
    one in session.history / the exported report."""

    def test_attempts_after_new_do_not_include_the_abandoned_exercise(
        self,
    ) -> None:
        cfg = _cfg("unused-rendu", fuzz=0, seed=None, relaxed=True)
        ask_calls = ["  ", "grademe", "new", "grademe"]
        captured: Dict[str, Any] = {}

        def fake_summary(session: object, passed: bool) -> None:
            captured["session"] = session

        with mock.patch.object(
            examshell, "grade_exercise", side_effect=[False, True]
        ), mock.patch.object(
            examshell, "exam_summary", side_effect=fake_summary
        ), mock.patch.object(
            session_store, "load", return_value=None
        ), mock.patch.object(session_store, "save"), mock.patch.object(
            session_store, "clear"
        ), mock.patch.object(
            ui, "ask", side_effect=ask_calls
        ), mock.patch.object(
            ui, "pause", side_effect=ui.Abort()
        ), mock.patch.object(ui, "clear"), mock.patch.object(
            ui, "banner"
        ), mock.patch.object(ui, "status_bar"), mock.patch.object(
            ui, "subject"
        ), mock.patch.object(ui, "commands"), mock.patch.object(
            ui, "level_cleared"
        ), mock.patch.object(ui, "info"), contextlib.redirect_stdout(
            io.StringIO()
        ):
            examshell.exam_mode(cfg)

        self.assertEqual(captured["session"].history[0][2], 1)


class ExamModeAbortAtLevelPauseTests(unittest.TestCase):
    """Ctrl-C / Ctrl-D exactly at the "Press Enter for the next level…"
    pause used to exit exam_mode silently, with no summary at all — every
    other exit point in the loop (the "quit" command, an abort while
    typing a command) shows one. Regression test for that inconsistency,
    plus the specific case of aborting the pause right after the FINAL
    level: the saved state used to end up with level = N_LEVELS + 1, an
    out-of-range value the outer `while` loop can never satisfy again."""

    def _run(
        self, pause_side_effect: Any, n_asks: int
    ) -> Tuple[Any, Any, Any]:
        cfg = _cfg("unused-rendu", fuzz=0, seed=None)
        ask_calls = ["  "] + [
            "grademe"
        ] * n_asks  # login (default), then one "grademe" per level
        with mock.patch.object(
            examshell, "grade_exercise", return_value=True
        ), mock.patch.object(
            session_store, "load", return_value=None
        ), mock.patch.object(session_store, "save") as save, mock.patch.object(
            session_store, "clear"
        ) as clear, mock.patch.object(
            stats, "best_exam_time", return_value=None
        ), mock.patch.object(stats, "record_exam_complete"), mock.patch.object(
            ui, "ask", side_effect=ask_calls
        ), mock.patch.object(
            ui, "pause", side_effect=pause_side_effect
        ), mock.patch.object(ui, "summary") as summary, mock.patch.object(
            ui, "clear"
        ), mock.patch.object(ui, "banner"), mock.patch.object(
            ui, "status_bar"
        ), mock.patch.object(ui, "subject"), mock.patch.object(
            ui, "commands"
        ), mock.patch.object(ui, "level_cleared"), contextlib.redirect_stdout(
            io.StringIO()
        ):
            examshell.exam_mode(cfg)
        return save, clear, summary

    def test_abort_on_the_final_level_pause_still_shows_a_passed_summary(
        self,
    ) -> None:
        pause_effects = [None] * (N_LEVELS - 1) + [ui.Abort()]
        save, clear, summary = self._run(pause_effects, n_asks=N_LEVELS)
        save.assert_not_called()
        clear.assert_called_once_with(examshell.TOOL)
        summary.assert_called_once()
        self.assertIn("PASSED", summary.call_args[0][0])

    def test_abort_on_a_mid_exam_level_pause_still_shows_an_aborted_summary(
        self,
    ) -> None:
        save, clear, summary = self._run([ui.Abort()], n_asks=1)
        save.assert_called_once()
        clear.assert_not_called()
        summary.assert_called_once()
        self.assertIn("ABORTED", summary.call_args[0][0])


class SeededExamIsReproducibleTests(unittest.TestCase):
    """--seed N must reproduce the same exam no matter how often the
    student types `grademe`: grading (fuzz cases) draws from its own RNG,
    never from the one that picks each level's exercise."""

    def _drawn(self, fails_per_level: int) -> List[str]:
        cfg = _cfg("unused-rendu", fuzz=0, seed=1234)
        drawn: List[str] = []
        outcomes = ([False] * fails_per_level + [True]) * N_LEVELS

        def fake_grade(
            ex_name: str,
            rng: random.Random,
            cfg: object,
            mode: str = "practice",
        ) -> bool:
            for _ in range(50):  # what a fuzzed grading run does
                rng.random()
            return outcomes.pop(0)

        def fake_subject(
            ex_name: str, cfg: object, session: object = None
        ) -> None:
            if not drawn or drawn[-1] != ex_name:
                drawn.append(ex_name)

        asks = ["  "] + ["grademe"] * len(outcomes)
        with mock.patch.object(
            examshell, "grade_exercise", side_effect=fake_grade
        ), mock.patch.object(
            examshell, "show_subject", side_effect=fake_subject
        ), mock.patch.object(examshell, "exam_summary"), mock.patch.object(
            session_store, "load", return_value=None
        ), mock.patch.object(session_store, "save"), mock.patch.object(
            session_store, "clear"
        ), mock.patch.object(ui, "ask", side_effect=asks), mock.patch.object(
            ui, "pause"
        ), mock.patch.object(ui, "clear"), mock.patch.object(
            ui, "banner"
        ), mock.patch.object(ui, "commands"), mock.patch.object(
            ui, "level_cleared"
        ), mock.patch.object(ui, "info"), mock.patch.object(
            ui, "note"
        ), contextlib.redirect_stdout(io.StringIO()):
            examshell.exam_mode(cfg)
        return drawn

    def test_retries_do_not_change_later_draws(self) -> None:
        first_try = self._drawn(fails_per_level=0)
        with_retries = self._drawn(fails_per_level=3)
        self.assertEqual(len(first_try), N_LEVELS)
        self.assertEqual(first_try, with_retries)


STRICT_FLAGS = ("strict_imports",)


class RealisticExamModeTests(unittest.TestCase):
    """By default the exam grades as strictly as the real one and has no
    `new`; --relaxed restores the lenient behaviour. --time-limit ends it."""

    def test_exam_config_is_strict_by_default(self) -> None:
        cfg = examshell.exam_config(_cfg("x"))
        for flag in STRICT_FLAGS:
            self.assertTrue(getattr(cfg, flag), flag)

    def test_exam_config_leaves_the_original_config_alone(self) -> None:
        base = _cfg("x")
        examshell.exam_config(base)
        for flag in STRICT_FLAGS:
            self.assertFalse(getattr(base, flag), flag)

    def test_relaxed_keeps_lenient_grading(self) -> None:
        cfg = examshell.exam_config(_cfg("x", relaxed=True))
        for flag in STRICT_FLAGS:
            self.assertFalse(getattr(cfg, flag), flag)

    def test_new_is_hidden_unless_relaxed(self) -> None:
        names = [n for n, _ in examshell.exam_commands(_cfg("x"))]
        self.assertNotIn("new", names)
        names = [
            n for n, _ in examshell.exam_commands(_cfg("x", relaxed=True))
        ]
        self.assertIn("new", names)

    def _run(
        self, cfg: examshell.Config, asks: List[str], **patches: Any
    ) -> Tuple[Dict[str, Any], Any]:
        captured: Dict[str, Any] = {}

        def fake_summary(
            session: object, passed: bool, timed_out: bool = False
        ) -> None:
            captured.update(
                session=session, passed=passed, timed_out=timed_out
            )

        with mock.patch.object(
            examshell, "grade_exercise", return_value=False
        ), mock.patch.object(
            examshell, "exam_summary", side_effect=fake_summary
        ), mock.patch.object(
            session_store, "load", return_value=None
        ), mock.patch.object(session_store, "save"), mock.patch.object(
            session_store, "clear"
        ), mock.patch.object(ui, "ask", side_effect=asks), mock.patch.object(
            ui, "warn"
        ) as warn, mock.patch.object(ui, "clear"), mock.patch.object(
            ui, "banner"
        ), mock.patch.object(ui, "status_bar"), mock.patch.object(
            ui, "subject"
        ), mock.patch.object(ui, "commands"), mock.patch.object(
            ui, "info"
        ), mock.patch.object(ui, "note"), contextlib.redirect_stdout(
            io.StringIO()
        ):
            examshell.exam_mode(cfg)
        return captured, warn

    def test_new_is_refused_in_realistic_mode(self) -> None:
        cfg = _cfg("unused-rendu")
        captured, warn = self._run(cfg, ["  ", "new", "quit"])
        self.assertTrue(
            any("--relaxed" in c.args[0] for c in warn.call_args_list)
        )
        self.assertFalse(captured["timed_out"])

    def test_time_limit_ends_the_exam(self) -> None:
        cfg = _cfg("unused-rendu", time_limit=1)
        with mock.patch.object(
            time,
            "time",
            side_effect=[1000.0] + [1000.0 + 61] * 50,
        ):
            captured, _warn = self._run(cfg, ["  ", "grademe"])
        self.assertTrue(captured["timed_out"])
        self.assertFalse(captured["passed"])

    def test_countdown_only_with_a_time_limit(self) -> None:
        session = examshell.Session()
        session.start_time = time.time()
        self.assertEqual(shell_common.countdown(session, _cfg("x")), "")
        self.assertIn(
            "left", shell_common.countdown(session, _cfg("x", time_limit=90))
        )


class ReadinessAndDrillModeTests(unittest.TestCase):
    """--readiness / --drill wiring (the ranking itself is tested in
    tests/test_shared.py)."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        for name, value in (
            ("STATS_PATH", os.path.join(self.tmpdir.name, "stats.jsonl")),
            ("DATA_DIR", self.tmpdir.name),
        ):
            patcher = mock.patch.object(stats, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_readiness_lists_every_standard_exercise(self) -> None:
        with mock.patch.object(
            ui, "overview_table"
        ) as table, mock.patch.object(
            ui, "summary"
        ), contextlib.redirect_stdout(io.StringIO()):
            examshell.readiness_mode(interactive=False)
        rows = table.call_args[0][0]
        standard = {
            n
            for n in examshell.EXERCISES
            if examshell.EXERCISES[n]["standard"]
        }
        self.assertEqual({row[1] for row in rows}, standard)
        self.assertTrue(all(row[2] == "missing" for row in rows))

    def test_drill_practises_n_standard_exercises(self) -> None:
        with mock.patch.object(
            examshell, "practice_one"
        ) as practice, mock.patch.object(ui, "pause"), mock.patch.object(
            ui, "clear"
        ), contextlib.redirect_stdout(io.StringIO()):
            examshell.drill_mode(_cfg("x"), n=3)
        self.assertEqual(practice.call_count, 3)
        for call in practice.call_args_list:
            self.assertTrue(examshell.EXERCISES[call[0][0]]["standard"])
            self.assertEqual(call[1]["mode"], "drill")


if __name__ == "__main__":
    unittest.main()
