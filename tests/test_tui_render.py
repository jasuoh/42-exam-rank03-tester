#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""examshell/tui/render.py — the full-screen UI's rich renderables. Needs only
rich (not Textual), so these run wherever rich is installed."""

import io
import unittest

try:
    from rich.console import Console
    from examshell.tui import render

    HAVE_RICH = True
except ImportError:  # pragma: no cover
    HAVE_RICH = False

from examshell.grader import Failure, Report


def text_of(renderable, width=100):
    console = Console(
        width=width, record=True, color_system=None, file=io.StringIO()
    )
    console.print(renderable)
    return console.export_text()


@unittest.skipUnless(HAVE_RICH, "rich not installed")
class ReportViewTests(unittest.TestCase):
    def _failing(self):
        report = Report("py_inter", "inter")
        report.total, report.passed = 3, 1
        report.failures = [
            Failure(["", "abc"], "", "'x'"),
            Failure(["a\tb", "b"], "b", "'a'"),
        ]
        return report

    def test_failures_show_call_edge_case_and_values(self):
        out = text_of(render.report_view(self._failing(), "inter"))
        self.assertIn("FAILED", out)
        self.assertIn("1/3 tests", out)
        self.assertIn("inter('', 'abc')", out)
        self.assertIn("edge case: empty string", out)
        self.assertIn("edge case: tabs", out)

    def test_blind_hides_inputs(self):
        out = text_of(render.report_view(self._failing(), "inter", blind=True))
        self.assertIn("2 failing tests, inputs hidden", out)
        self.assertNotIn("inter('', 'abc')", out)

    def test_fatal(self):
        report = Report("x", "f").fail(
            "FILE_MISSING", "expected your solution at r/x.py"
        )
        out = text_of(render.report_view(report, "f"))
        self.assertIn("File not found", out)
        self.assertIn("expected your solution at r/x.py", out)

    def test_passed(self):
        report = Report("x", "f")
        report.total = report.passed = 5
        self.assertIn("PASSED", text_of(render.report_view(report, "f")))


@unittest.skipUnless(HAVE_RICH, "rich not installed")
class ChartTests(unittest.TestCase):
    def test_sparkline_scales_to_the_maximum(self):
        self.assertEqual(render.sparkline([0, 4, 8]).plain, "▁▅█")
        self.assertEqual(render.sparkline([0, 0]).plain, "▁▁")

    def test_bar_width(self):
        self.assertEqual(len(render.bar(1, 4, 20).plain), 20)
        self.assertEqual(len(render.bar(0, 0, 8).plain), 8)

    def test_readiness_view_lists_every_exercise(self):
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

    def test_stepper(self):
        class S(object):
            level = 2

        self.assertEqual(render.stepper(S(), 4).plain, "● ◉ ○ ○ ")
