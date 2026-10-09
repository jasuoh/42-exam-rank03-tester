#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the multi-rank support added for Exam Rank 04/05:
the rank registry, the two new banks' shape, the grader's tuple/dict-key
round-trip and its multi-function ("parts") exercises."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import random
import tempfile
import unittest
from typing import Any
from unittest import mock

from examshell import examshell, grader, ranks, settings
from examshell.grader import Report
from examshell.training_bank import TRAINING_EXERCISES


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


class RankRegistryTests(unittest.TestCase):
    def test_every_choice_resolves(self) -> None:
        for rank_id in ranks.CHOICES:
            self.assertEqual(ranks.get(rank_id).id, rank_id)

    def test_normalize_accepts_the_shapes_a_student_would_type(self) -> None:
        for value in ("4", "04", "rank04", "r4", "#4"):
            self.assertEqual(ranks.normalize(value), "04", value)
        self.assertEqual(ranks.normalize("3"), "03")
        self.assertEqual(ranks.normalize("05"), "05")

    def test_normalize_rejects_what_is_not_a_rank(self) -> None:
        for value in ("", "99", "rank99", "banana", None):
            self.assertIsNone(ranks.normalize(value))

    def test_get_falls_back_to_the_default(self) -> None:
        self.assertEqual(ranks.get(None).id, ranks.DEFAULT_RANK)
        self.assertEqual(ranks.get("nonsense").id, ranks.DEFAULT_RANK)

    def test_each_rank_files_its_history_under_its_own_tag(self) -> None:
        """A shared tag would let a Rank 03 exam be resumed as a Rank 05
        one, and would mix the two banks' stats into one history."""
        tags = [ranks.get(r).tool for r in ranks.CHOICES]
        self.assertEqual(len(set(tags)), len(tags))
        self.assertEqual(ranks.get("03").tool, "py")  # pre-existing history

    def test_rank_03_is_still_the_default(self) -> None:
        self.assertEqual(ranks.DEFAULT_RANK, "03")
        self.assertEqual(examshell.RANK.id, "03")
        self.assertEqual(examshell.TOOL, "py")


class BankShapeTests(unittest.TestCase):
    """Structural checks on all three exam banks. The heavy behavioural
    check (every oracle graded through the real sandbox) is `make check`,
    not a unit test — this only locks in the shape the tester relies on."""

    def test_every_level_has_at_least_one_standard_exercise(self) -> None:
        for rank_id in ranks.CHOICES:
            rank = ranks.get(rank_id)
            for level in range(1, rank.n_levels + 1):
                self.assertTrue(
                    rank.standard_levels[level],
                    "rank %s level %d" % (rank_id, level),
                )

    def test_every_exercise_carries_what_the_grader_needs(self) -> None:
        for rank_id in ranks.CHOICES:
            rank = ranks.get(rank_id)
            for name, ex in rank.exercises.items():
                self.assertIn("level", ex, name)
                self.assertIn("subject", ex, name)
                self.assertIn(name, ex["subject"], name)
                for part in grader.parts_of(ex):
                    for key in ("function", "oracle", "cases", "fuzz"):
                        self.assertIn(key, part, "%s / %s" % (name, key))
                    self.assertIn(
                        "def %s(" % part["function"], ex["subject"], name
                    )

    def test_new_exercises_default_to_extra_not_standard(self) -> None:
        # Same fail-closed rule the Rank 03 bank has (see
        # test_examshell.py): an exercise that forgets "standard": True
        # must never silently become eligible for a real exam draw.
        import inspect

        from examshell import exam_bank_r04, exam_bank_r05

        for module in (exam_bank_r04, exam_bank_r05):
            self.assertIn(
                '_ex.setdefault("standard", False)', inspect.getsource(module)
            )

    def test_an_exam_name_never_collides_with_a_training_name(self) -> None:
        """Both pools land in one ALL_EXERCISES namespace and one rendu/
        directory, so a shared name would mean two different subjects
        fighting over one filename (this is why Rank 05's spiral subject
        is py_spiral_generator, not py_spiral_matrix)."""
        for rank_id in ranks.CHOICES:
            clash = set(ranks.get(rank_id).exercises) & set(TRAINING_EXERCISES)
            self.assertEqual(clash, set(), "rank %s" % rank_id)

    def test_all_exercises_holds_both_pools(self) -> None:
        for rank_id in ranks.CHOICES:
            rank = ranks.get(rank_id)
            merged = rank.all_exercises()
            self.assertEqual(
                len(merged), len(rank.exercises) + len(TRAINING_EXERCISES)
            )


class UseRankTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(examshell.use_rank)  # back to the default

    def test_switching_rebinds_every_global_the_module_reads(self) -> None:
        examshell.use_rank("05")
        self.assertEqual(examshell.RANK.id, "05")
        self.assertEqual(examshell.TOOL, "py05")
        self.assertEqual(examshell.N_LEVELS, 3)
        self.assertIn("py_word_ladder", examshell.EXERCISES)
        self.assertNotIn("py_inter", examshell.EXERCISES)

    def test_session_score_follows_the_active_rank(self) -> None:
        examshell.use_rank("05")
        session = examshell.Session("tester")
        session.passed = ["a", "b", "c"]
        self.assertEqual(session.score(), 100)  # 3 levels, not 6

    def test_exercise_entries_covers_the_active_rank(self) -> None:
        examshell.use_rank("04")
        entries = examshell.exercise_entries()
        self.assertEqual(
            {name for _, _, name, _, _ in entries},
            set(ranks.get("04").exercises),
        )
        self.assertEqual(
            [idx for idx, *_ in entries], list(range(1, len(entries) + 1))
        )

    def test_switching_back_restores_rank_03(self) -> None:
        examshell.use_rank("04")
        examshell.use_rank("03")
        self.assertEqual(examshell.TOOL, "py")
        self.assertEqual(examshell.N_LEVELS, 6)

    def test_cli_rejects_an_unknown_rank(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(examshell.main(["--rank", "99", "--list"]), 2)

    def test_cli_rank_flag_selects_the_pool(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(
                examshell.main(
                    ["--rank", "04", "--list", "--no-color", "--no-rich"]
                ),
                0,
            )
        self.assertIn("py_sliding_window_maximum", out.getvalue())
        self.assertNotIn("py_inter", out.getvalue())


class LastExamTests(unittest.TestCase):
    """The exam picked last is where the next session opens."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, value in (
            ("DATA_DIR", tmp.name),
            ("CONFIG_PATH", os.path.join(tmp.name, "config.json")),
        ):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(examshell.use_rank)
        # main() creates the solution folder; keep it out of the CWD
        self.rendu = os.path.join(tmp.name, "rendu")

    def _main(self, *argv: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return examshell.main(
                list(argv) + ["--no-color", "--no-rich", "--rendu", self.rendu]
            )

    def test_remember_exam_keeps_the_python_rank_under_c(self) -> None:
        settings.update_config("timeout", 5)
        settings.remember_exam("py04")
        settings.remember_exam("c")
        self.assertEqual(
            settings.load_config(),
            {"timeout": 5, "rank": "04", "tester": "c"},
        )

    def test_without_rank_the_saved_one_is_active(self) -> None:
        settings.remember_exam("py05")
        self.assertEqual(self._main("--list"), 0)
        self.assertEqual(examshell.RANK.id, "05")

    def test_rank_flag_beats_the_saved_one(self) -> None:
        settings.remember_exam("py05")
        self.assertEqual(self._main("--rank", "04", "--list"), 0)
        self.assertEqual(examshell.RANK.id, "04")

    def test_a_bogus_saved_rank_falls_back_to_the_default(self) -> None:
        settings.update_config("rank", "99")
        self.assertEqual(self._main("--list"), 0)
        self.assertEqual(examshell.RANK.id, ranks.DEFAULT_RANK)

    def test_tui_opens_on_c_when_that_was_picked_last(self) -> None:
        from c_exam import examshell as c_shell
        from examshell import shell_common

        settings.remember_exam("c")
        with mock.patch.object(
            shell_common, "run_tui", return_value=0
        ) as run_tui:
            self.assertEqual(self._main("--tui", "--relaxed"), 0)
            self.assertIs(run_tui.call_args[0][0], c_shell)
            self.assertTrue(run_tui.call_args[0][1].relaxed)
            # an explicit --rank means Python, and is remembered
            self.assertEqual(self._main("--tui", "--rank", "04"), 0)
            self.assertIs(run_tui.call_args[0][0], examshell)
        self.assertEqual(settings.load_config()["tester"], "py")
        self.assertEqual(settings.load_config()["rank"], "04")


class ValueCodecTests(unittest.TestCase):
    """Cases reach the sandbox as JSON, which on its own loses a tuple and
    stringifies a non-string dict key — both of which the Rank 04/05 banks
    depend on."""

    ROUND_TRIPPED = [
        (1, 2),
        [(0, 30), (5, 10)],
        (2, [[(0, 30)], [(5, 10), (15, 20)]]),
        {0: [1], 1: [2]},
        {"app": ["database"]},
        [[1, 2], [3]],
        "plain",
        [],
        {},
        [{"a": (1, (2, 3))}],
    ]

    def test_round_trip_through_json_keeps_types(self) -> None:
        for value in self.ROUND_TRIPPED:
            wire = json.loads(json.dumps(grader.encode_value(value)))
            self.assertTrue(
                grader.deep_eq(grader.decode_value(wire), value), repr(value)
            )

    def test_json_stable_agrees(self) -> None:
        for value in self.ROUND_TRIPPED:
            self.assertTrue(grader.json_stable(value), repr(value))

    def test_plain_values_are_left_exactly_as_they_are(self) -> None:
        """Anything without a tuple or dict must encode to itself, so a
        bank that uses neither produces the same cases.json as before."""
        for value in ([1, 2, 3], "text", 7, True, None, [[1], [2]]):
            self.assertEqual(grader.encode_value(value), value)

    def test_a_tuple_is_not_a_list(self) -> None:
        self.assertFalse(grader.deep_eq((1, 2), [1, 2]))
        self.assertFalse(grader.deep_eq([1, 2], (1, 2)))

    def test_tuple_comparison_stays_type_strict_inside(self) -> None:
        self.assertFalse(grader.deep_eq((1, True), (1, 1)))
        self.assertTrue(grader.deep_eq((1, 2), (1, 2)))


class MultiFunctionExerciseTests(unittest.TestCase):
    """An exercise whose subject asks for two functions (see
    grader.parts_of) is graded as one verdict over both."""

    BOTH_RIGHT = (
        "def compress(s):\n"
        "    out, i = '', 0\n"
        "    while i < len(s):\n"
        "        j = i\n"
        "        while j < len(s) and s[j] == s[i]:\n"
        "            j += 1\n"
        "        out += s[i] if j - i == 1 else s[i] + str(j - i)\n"
        "        i = j\n"
        "    return out\n"
        "\n"
        "def decompress(s):\n"
        "    out, i = '', 0\n"
        "    while i < len(s):\n"
        "        ch, i = s[i], i + 1\n"
        "        n = ''\n"
        "        while i < len(s) and s[i].isdigit():\n"
        "            n += s[i]\n"
        "            i += 1\n"
        "        out += ch * (int(n) if n else 1)\n"
        "    return out\n"
    )

    def setUp(self) -> None:
        self.ex = ranks.get("05").exercises["py_compress_decompress"]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, source: str) -> str:
        path = os.path.join(self.tmp.name, "py_compress_decompress.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(source)
        return path

    def test_parts_of_a_plain_exercise_is_the_exercise_itself(self) -> None:
        plain = ranks.get("05").exercises["py_word_ladder"]
        self.assertEqual(grader.parts_of(plain), [plain])

    def test_plan_has_one_entry_per_function(self) -> None:
        plan = grader.build_plan(
            "py_compress_decompress", self.ex, random.Random(0), fuzz=2
        )
        self.assertEqual(
            [function for function, _ in plan], ["compress", "decompress"]
        )
        self.assertEqual(
            grader.plan_size(plan), sum(len(tests) for _, tests in plan)
        )

    def test_both_functions_right_passes(self) -> None:
        self._write(self.BOTH_RIGHT)
        report = grader.grade(
            "py_compress_decompress",
            self.ex,
            self.tmp.name,
            rng=random.Random(0),
            fuzz=3,
        )
        self.assertTrue(report.ok, report.fatal or report.failures[:1])

    def test_the_missing_half_is_named_in_the_verdict(self) -> None:
        self._write(self.BOTH_RIGHT.split("def decompress")[0])
        report = grader.grade(
            "py_compress_decompress",
            self.ex,
            self.tmp.name,
            rng=random.Random(0),
            fuzz=0,
        )
        self.assertEqual(report.fatal, "NO_FUNCTION")
        self.assertIn("decompress", report.detail)

    def test_a_failure_says_which_function_it_came_from(self) -> None:
        self._write(
            self.BOTH_RIGHT.replace(
                "out += ch * (int(n) if n else 1)", "out += ch"
            )
        )
        report = grader.grade(
            "py_compress_decompress",
            self.ex,
            self.tmp.name,
            rng=random.Random(0),
            fuzz=0,
        )
        self.assertFalse(report.ok)
        self.assertTrue(
            all(
                getattr(f, "function", None) == "decompress"
                for f in report.failures
            )
        )
        self.assertTrue(
            report.failures[0].call("compress").startswith("decompress(")
        )

    def test_exam_stub_is_bare_and_still_importable(self) -> None:
        cfg = examshell.exam_config(_cfg(self.tmp.name))
        examshell.use_rank("05")
        self.addCleanup(examshell.use_rank)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(examshell.make_stub("py_compress_decompress", cfg))
        with open(
            os.path.join(self.tmp.name, "py_compress_decompress.py"),
            encoding="utf-8",
        ) as fh:
            content = fh.read()
        self.assertIn("def compress(", content)
        self.assertIn("def decompress(", content)
        self.assertNotIn("__main__", content)
        self.assertNotIn("_tests", content)
        exec(
            compile(content, "py_compress_decompress.py", "exec"),
            {"__name__": "x"},
        )

    def test_stub_defines_both_functions_and_is_importable(self) -> None:
        cfg = _cfg(self.tmp.name)
        examshell.use_rank("05")
        self.addCleanup(examshell.use_rank)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(examshell.make_stub("py_compress_decompress", cfg))
        with open(
            os.path.join(self.tmp.name, "py_compress_decompress.py"),
            encoding="utf-8",
        ) as fh:
            content = fh.read()
        self.assertIn("def compress(", content)
        self.assertIn("def decompress(", content)
        namespace = {"__name__": "not_main"}
        exec(compile(content, "py_compress_decompress.py", "exec"), namespace)


class TupleAndDictExerciseTests(unittest.TestCase):
    """The Rank 05 subjects that hand tuples or int-keyed dicts across the
    sandbox boundary, graded end to end."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _grade(self, name: str, source: str, fuzz: int = 0) -> Report:
        ex = ranks.get("05").exercises[name]
        with open(
            os.path.join(self.tmp.name, name + ".py"), "w", encoding="utf-8"
        ) as fh:
            fh.write(source)
        return grader.grade(
            name, ex, self.tmp.name, rng=random.Random(0), fuzz=fuzz
        )

    def test_returning_lists_instead_of_tuples_fails(self) -> None:
        report = self._grade(
            "py_schedule_meetings",
            "def schedule_meetings(intervals):\n"
            "    rooms = []\n"
            "    for m in sorted(intervals, key=lambda x: x[0]):\n"
            "        for room in rooms:\n"
            "            if room[-1][1] <= m[0]:\n"
            "                room.append(list(m))\n"
            "                break\n"
            "        else:\n"
            "            rooms.append([list(m)])\n"
            "    return [len(rooms), rooms]\n",
        )
        self.assertFalse(report.ok)

    def test_the_same_solution_with_tuples_passes(self) -> None:
        report = self._grade(
            "py_schedule_meetings",
            "def schedule_meetings(intervals):\n"
            "    rooms = []\n"
            "    for m in sorted(intervals, key=lambda x: x[0]):\n"
            "        for room in rooms:\n"
            "            if room[-1][1] <= m[0]:\n"
            "                room.append(tuple(m))\n"
            "                break\n"
            "        else:\n"
            "            rooms.append([tuple(m)])\n"
            "    return (len(rooms), rooms)\n",
        )
        self.assertTrue(report.ok, report.fatal or report.failures[:1])

    def test_int_dict_keys_survive_the_sandbox(self) -> None:
        """A graph keyed by int must still be keyed by int inside the
        submission — plain JSON would hand it string keys, and every
        `nxt in graph` lookup would quietly miss."""
        report = self._grade(
            "py_graph_cycle_detector",
            "def graph_cycle_detector(graph):\n"
            "    for node in graph:\n"
            "        if not isinstance(node, int):\n"
            "            raise AssertionError('key is ' + repr(node))\n"
            "    state = {n: 0 for n in graph}\n"
            "    def walk(n):\n"
            "        state[n] = 1\n"
            "        for nxt in graph[n]:\n"
            "            if nxt not in graph:\n"
            "                continue\n"
            "            if state[nxt] == 1:\n"
            "                return True\n"
            "            if state[nxt] == 0 and walk(nxt):\n"
            "                return True\n"
            "        state[n] = 2\n"
            "        return False\n"
            "    return any(state[n] == 0 and walk(n) for n in graph)\n",
            fuzz=5,
        )
        self.assertTrue(report.ok, report.fatal or report.failures[:1])

    def test_tuple_arguments_arrive_as_tuples(self) -> None:
        report = self._grade(
            "py_prism_detector",
            "def prism_detector(grid, pattern):\n"
            "    if not grid or not pattern:\n"
            "        return []\n"
            "    dirs = ((1,0,'H'), (-1,0,'H-'), (0,1,'V'), (0,-1,'V-'),\n"
            "            (1,1,'D1'), (-1,-1,'D1-'), "
            "(-1,1,'D2'), (1,-1,'D2-'))\n"
            "    out = []\n"
            "    for y in range(len(grid)):\n"
            "        for x in range(len(grid[y])):\n"
            "            for dx, dy, code in dirs:\n"
            "                ok = True\n"
            "                for k in range(len(pattern)):\n"
            "                    ny, nx = y + dy * k, x + dx * k\n"
            "                    if not (0 <= ny < len(grid)) or \\\n"
            "                            not (0 <= nx < len(grid[ny])) or \\\n"
            "                            grid[ny][nx] != pattern[k]:\n"
            "                        ok = False\n"
            "                        break\n"
            "                if ok:\n"
            "                    out.append((x, y, code))\n"
            "    return out\n",
            fuzz=5,
        )
        self.assertTrue(report.ok, report.fatal or report.failures[:1])


if __name__ == "__main__":
    unittest.main()
