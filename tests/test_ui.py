#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for src/ui.py — the parsing/escaping helpers that do not need
an actual terminal. Rendering itself is checked by hand (see the README)."""

import unittest

from src import ui


class ColorTests(unittest.TestCase):
    def tearDown(self):
        ui.configure()   # restore auto-detected defaults for later tests

    def test_no_styling_when_color_is_off(self):
        ui.configure(color=False)
        self.assertEqual(ui.c("text", "RED", "BOLD"), "text")

    def test_styling_when_color_is_on(self):
        ui.configure(rich=False, color=True)
        styled = ui.c("text", "RED")
        self.assertNotEqual(styled, "text")
        self.assertIn("text", styled)
        self.assertTrue(styled.startswith(ui.C.RED))
        self.assertTrue(styled.endswith(ui.C.RESET))

    def test_no_styles_requested_is_a_no_op(self):
        ui.configure(rich=False, color=True)
        self.assertEqual(ui.c("text"), "text")


class EscapeTests(unittest.TestCase):
    def test_brackets_are_neutralised_for_rich_markup(self):
        if not ui.HAVE_RICH:
            self.skipTest("rich is not installed in this environment")
        escaped = ui._esc("[q]")
        self.assertNotEqual(escaped, "[q]")
        self.assertIn("q", escaped)

    def test_escaping_is_idempotent_on_plain_text(self):
        self.assertIn("hello", ui._esc("hello"))


class SplitSubjectTests(unittest.TestCase):
    def setUp(self):
        self.subject = (
            "Assignment name  : py_demo\n"
            "Expected files   : py_demo.py\n"
            "Allowed functions: None\n"
            + "-" * 20 + "\n\n"
            "Some prose explaining the exercise.\n\n"
            "    def demo(x: int) -> int:\n\n"
            "Examples:\n"
            "    demo(1) -> 2\n"
            "    demo(2) -> 4\n"
        )

    def test_header_lines_are_extracted(self):
        header, _, _, _ = ui._split_subject(self.subject)
        joined = "\n".join(header)
        self.assertIn("Assignment name  : py_demo", joined)
        self.assertIn("Allowed functions: None", joined)

    def test_signature_is_found(self):
        _, _, signature, _ = ui._split_subject(self.subject)
        self.assertEqual(signature, "def demo(x: int) -> int:")

    def test_prose_excludes_header_and_examples(self):
        _, prose, _, _ = ui._split_subject(self.subject)
        self.assertIn("Some prose explaining the exercise.", prose)
        self.assertNotIn("Assignment name", prose)
        self.assertNotIn("demo(1)", prose)

    def test_examples_are_captured(self):
        _, _, _, examples = ui._split_subject(self.subject)
        self.assertIn("demo(1) -> 2", examples)
        self.assertIn("demo(2) -> 4", examples)


if __name__ == "__main__":
    unittest.main()
