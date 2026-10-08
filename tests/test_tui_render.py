#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""examshell/tui/render.py — the full-screen UI's rich renderables. Needs only
rich (not Textual), so these run wherever rich is installed."""

from __future__ import annotations

import io
import unittest
from typing import Any, cast

try:
    from rich.console import Console
    from examshell.tui import render

    HAVE_RICH = True
except ImportError:  # pragma: no cover
    HAVE_RICH = False

from examshell.grader import Failure, Report
from examshell.shell_common import Session


def text_of(renderable: Any, width: int = 100) -> str:
    console = Console(
        width=width, record=True, color_system=None, file=io.StringIO()
    )
    console.print(renderable)
    return console.export_text()


@unittest.skipUnless(HAVE_RICH, "rich not installed")
class ReportViewTests(unittest.TestCase):
    def _failing(self) -> Report:
        report = Report("py_inter", "inter")
        report.total, report.passed = 3, 1
        report.failures = [
            Failure(["", "abc"], "", "'x'"),
            Failure(["a\tb", "b"], "b", "'a'"),
        ]
        return report

    def test_failures_show_call_edge_case_and_values(self) -> None:
        out = text_of(render.report_view(self._failing(), "inter"))
        self.assertIn("FAILED", out)
        self.assertIn("1/3 tests", out)
        self.assertIn("inter('', 'abc')", out)
        self.assertIn("edge case: empty string", out)
        self.assertIn("edge case: tabs", out)

    def test_blind_hides_inputs(self) -> None:
        out = text_of(render.report_view(self._failing(), "inter", blind=True))
        self.assertIn("2 failing tests, inputs hidden", out)
        self.assertNotIn("inter('', 'abc')", out)

    def test_fatal(self) -> None:
        report = Report("x", "f").fail(
            "FILE_MISSING", "expected your solution at r/x.py"
        )
        out = text_of(render.report_view(report, "f"))
        self.assertIn("File not found", out)
        self.assertIn("expected your solution at r/x.py", out)

    def test_passed(self) -> None:
        report = Report("x", "f")
        report.total = report.passed = 5
        self.assertIn("PASSED", text_of(render.report_view(report, "f")))

    def test_compact_is_one_line_per_failure(self) -> None:
        report = self._failing()
        report.failures *= 3  # 6 failures
        out = text_of(render.compact_report_view(report, "inter", hint="h"))
        lines = out.strip().splitlines()
        self.assertTrue(lines[0].startswith("✖ FAILED  1/3"))
        self.assertIn("inter('', 'abc')  (empty string)  got 'x' ≠ ''", out)
        self.assertEqual(sum("✖ inter(" in line for line in lines), 3)
        self.assertIn("… 3 more · d for details", out)
        self.assertEqual(lines[-1], "hint: h")

    def test_exam_trace_shows_only_the_first_failure(self) -> None:
        out = text_of(render.exam_trace_view(self._failing(), "inter"))
        self.assertTrue(out.startswith("FAILURE"))
        self.assertIn("inter('', 'abc')", out)
        self.assertNotIn("inter('a\\tb', 'b')", out)
        self.assertNotIn("edge case", out)  # no hints in the exam
        blind = text_of(
            render.exam_trace_view(self._failing(), "inter", blind=True)
        )
        self.assertEqual(blind.strip(), "FAILURE")
        report = Report("x", "f")
        report.total = report.passed = 5
        self.assertEqual(
            text_of(render.exam_trace_view(report, "f")).strip(), "SUCCESS"
        )


@unittest.skipUnless(HAVE_RICH, "rich not installed")
class ChartTests(unittest.TestCase):
    def test_sparkline_scales_to_the_maximum(self) -> None:
        self.assertEqual(render.sparkline([0, 4, 8]).plain, "▁▅█")
        self.assertEqual(render.sparkline([0, 0]).plain, "▁▁")

    def test_bar_width(self) -> None:
        self.assertEqual(len(render.bar(1, 4, 20).plain), 20)
        self.assertEqual(len(render.bar(0, 0, 8).plain), 8)

    def test_readiness_view_lists_every_exercise(self) -> None:
        levels = [
            (
                1,
                1,
                2,
                [("a", {"status": "passed"}), ("b", {"status": "untried"})],
            ),
            (2, 0, 1, [("c", {"status": "failed"})]),
        ]
        out = text_of(render.readiness_view(levels))
        for piece in (
            "Overall",
            "1/3",
            "Level 1",
            "Level 2",
            "a",
            "b",
            "c",
            "tried, never passed",
        ):
            self.assertIn(piece, out)

    def test_attempt_summary_counts_this_exercise_only(self) -> None:
        bad, ok, other = Report("a", "a"), Report("a", "a"), Report("b", "b")
        bad.total, bad.passed = 2, 1
        ok.total = ok.passed = 2
        self.assertEqual(render.attempt_summary([], "a"), "")
        entries = [
            ("10:00:00", "a", bad),
            ("10:01:00", "b", other),
        ]
        self.assertEqual(
            render.attempt_summary(entries, "a"),
            "graded 1× · last 10:00:00 ✖ 1/2",
        )
        entries.append(("10:02:00", "a", ok))
        self.assertEqual(
            render.attempt_summary(entries, "a"), "graded 2× · last 10:02:00 ✔"
        )

    def test_per_exercise_worst_first(self) -> None:
        summary = {
            "per_exercise": {
                "good": {"passes": 2, "attempts": 2},
                "bad": {"passes": 0, "attempts": 3},
            }
        }
        out = text_of(render.per_exercise_view(summary))
        self.assertLess(out.index("bad"), out.index("good"))
        empty = render.per_exercise_view({"per_exercise": {}})
        self.assertIn("no grading history", text_of(empty))

    def test_stepper(self) -> None:
        class S(object):
            level = 2

        session = cast(Session, S())  # stepper() only reads .level
        self.assertEqual(render.stepper(session, 4).plain, "● ◉ ○ ○ ")
