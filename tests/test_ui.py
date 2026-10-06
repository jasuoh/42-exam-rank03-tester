#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for examshell/ui.py — the parsing/escaping helpers that do not
need an actual terminal. Rendering itself is checked by hand (see the
README)."""

from __future__ import annotations

import unittest
from typing import Any, List

from examshell import ui


class ColorTests(unittest.TestCase):
    def tearDown(self) -> None:
        ui.configure()  # restore auto-detected defaults for later tests

    def test_no_styling_when_color_is_off(self) -> None:
        ui.configure(color=False)
        self.assertEqual(ui.c("text", "RED", "BOLD"), "text")

    def test_styling_when_color_is_on(self) -> None:
        ui.configure(rich=False, color=True)
        styled = ui.c("text", "RED")
        self.assertNotEqual(styled, "text")
        self.assertIn("text", styled)
        self.assertTrue(styled.startswith(ui.C.RED))
        self.assertTrue(styled.endswith(ui.C.RESET))

    def test_no_styles_requested_is_a_no_op(self) -> None:
        ui.configure(rich=False, color=True)
        self.assertEqual(ui.c("text"), "text")


class EscapeTests(unittest.TestCase):
    def test_brackets_are_neutralised_for_rich_markup(self) -> None:
        if not ui.HAVE_RICH:
            self.skipTest("rich is not installed in this environment")
        escaped = ui._esc("[q]")
        self.assertNotEqual(escaped, "[q]")
        self.assertIn("q", escaped)

    def test_escaping_is_idempotent_on_plain_text(self) -> None:
        self.assertIn("hello", ui._esc("hello"))


class FileExtTests(unittest.TestCase):
    def test_python_exercise_gets_py(self) -> None:
        self.assertEqual(ui._file_ext({"oracle": lambda: None}), ".py")

    def test_c_function_kind_gets_c(self) -> None:
        self.assertEqual(
            ui._file_ext(
                {"oracle_c": "int f(void);", "prototype": "int f(void);"}
            ),
            ".c",
        )

    def test_c_program_kind_gets_c(self) -> None:
        # "program"-kind C exercises (own main(), no harness) carry no
        # "prototype" — only "oracle_c" is common to every C exercise.
        self.assertEqual(
            ui._file_ext({"oracle_c": "int main(void){}", "kind": "program"}),
            ".c",
        )


class FirstDiffIndexTests(unittest.TestCase):
    def test_identical_strings_return_none(self) -> None:
        self.assertIsNone(ui.first_diff_index("abc", "abc"))

    def test_divergence_points_at_the_first_differing_character(self) -> None:
        self.assertEqual(ui.first_diff_index("hello", "hallo"), 1)

    def test_one_string_a_prefix_of_the_other_points_past_the_shorter_one(
        self,
    ) -> None:
        self.assertEqual(ui.first_diff_index("abc", "abcdef"), 3)
        self.assertEqual(ui.first_diff_index("abcdef", "abc"), 3)

    def test_empty_strings_are_identical(self) -> None:
        self.assertIsNone(ui.first_diff_index("", ""))

    def test_completely_different_strings_diverge_at_zero(self) -> None:
        self.assertEqual(ui.first_diff_index("abc", "xyz"), 0)


class PassRateTierTests(unittest.TestCase):
    def test_solid_at_and_above_80_percent(self) -> None:
        self.assertEqual(ui._pass_rate_tier(0.8), "green")
        self.assertEqual(ui._pass_rate_tier(1.0), "green")

    def test_shaky_between_50_and_80_percent(self) -> None:
        self.assertEqual(ui._pass_rate_tier(0.5), "yellow")
        self.assertEqual(ui._pass_rate_tier(0.79), "yellow")

    def test_struggling_below_50_percent(self) -> None:
        self.assertEqual(ui._pass_rate_tier(0.0), "red")
        self.assertEqual(ui._pass_rate_tier(0.49), "red")


class SplitTopLevelTests(unittest.TestCase):
    def test_simple_comma_separated_values(self) -> None:
        self.assertEqual(ui._split_top_level("1, 2, 3"), ["1", "2", "3"])

    def test_nested_brackets_are_not_split(self) -> None:
        self.assertEqual(
            ui._split_top_level("1, [2, 3], 4"), ["1", "[2, 3]", "4"]
        )

    def test_comma_inside_a_string_is_not_split(self) -> None:
        self.assertEqual(
            ui._split_top_level("1, 'a,b', 3"), ["1", "'a,b'", "3"]
        )

    def test_nested_dict_braces_are_not_split(self) -> None:
        self.assertEqual(
            ui._split_top_level("{'a': 1, 'b': 2}, 3"),
            ["{'a': 1, 'b': 2}", "3"],
        )

    def test_empty_text_is_no_elements(self) -> None:
        self.assertEqual(ui._split_top_level(""), [])

    def test_single_element_has_no_comma(self) -> None:
        self.assertEqual(ui._split_top_level("42"), ["42"])


class StructuralDiffTests(unittest.TestCase):
    def test_non_list_or_tuple_expected_returns_none(self) -> None:
        self.assertIsNone(ui.structural_diff(5, "5", "6"))
        self.assertIsNone(ui.structural_diff("ab", "'ab'", "'ac'"))

    def test_single_element_list_falls_back_to_none(self) -> None:
        self.assertIsNone(ui.structural_diff([5], "[5]", "[6]"))

    def test_empty_list_falls_back_to_none(self) -> None:
        self.assertIsNone(ui.structural_diff([], "[]", "[1]"))

    def test_one_differing_element_is_isolated(self) -> None:
        block = ui.structural_diff([1, 2, 3], "[1, 2, 3]", "[1, 2, 4]")
        assert block is not None
        exp_lines, got_lines = block
        self.assertIn("  1", exp_lines)
        self.assertIn("  2", exp_lines)
        self.assertIn("- 3", exp_lines)
        self.assertIn("+ 4", got_lines)
        self.assertNotIn("+ 4", exp_lines)
        self.assertNotIn("- 3", got_lines)

    def test_extra_trailing_elements_are_flagged_as_additions(self) -> None:
        block = ui.structural_diff([1, 2, 3], "[1, 2, 3]", "[1, 2, 3, 4]")
        assert block is not None
        exp_lines, got_lines = block
        self.assertEqual(exp_lines, ["  1", "  2", "  3"])
        self.assertEqual(got_lines, ["  1", "  2", "  3", "+ 4"])

    def test_missing_trailing_elements_are_flagged_as_removals(self) -> None:
        block = ui.structural_diff([1, 2, 3], "[1, 2, 3]", "[1, 2]")
        assert block is not None
        exp_lines, got_lines = block
        self.assertEqual(exp_lines, ["  1", "  2", "- 3"])
        self.assertEqual(got_lines, ["  1", "  2"])

    def test_tuple_parens_are_stripped_the_same_way_as_list_brackets(
        self,
    ) -> None:
        block = ui.structural_diff((1, 2, 3), "(1, 2, 3)", "(1, 2, 4)")
        assert block is not None
        exp_lines, got_lines = block
        self.assertIn("- 3", exp_lines)
        self.assertIn("+ 4", got_lines)


class LineDiffTests(unittest.TestCase):
    def test_single_line_values_return_none(self) -> None:
        self.assertIsNone(ui.line_diff("abc", "abd"))

    def test_multi_line_mismatch_is_isolated_per_line(self) -> None:
        block = ui.line_diff("line1\nline2\nline3", "line1\nlineX\nline3")
        assert block is not None
        exp_lines, got_lines = block
        self.assertIn("  line1", exp_lines)
        self.assertIn("  line3", exp_lines)
        self.assertIn("- line2", exp_lines)
        self.assertIn("+ lineX", got_lines)

    def test_only_got_side_is_multi_line(self) -> None:
        # e.g. expected a one-line result but got multi-line stdout instead
        self.assertIsNotNone(ui.line_diff("ok", "ok\nextra line"))


class _FakeCFailure(object):
    """Mimics c_exam.grader.CFailure's attribute shape (.index/.expected/
    .got, both strings always un-repr()'d) without importing that module —
    _diff_block() tells the two failure kinds apart structurally (see its
    own docstring), so a fake with the right attributes is enough."""

    def __init__(self, expected: object, got: object) -> None:
        self.index, self.expected, self.got = 0, expected, got
        self.args: Any = None

    def call(self, function: str) -> str:
        return function


class _FakeFailure(object):
    """Mimics examshell.grader.Failure's attribute shape
    (.args/.expected/.got)."""

    def __init__(self, expected: object, got: object) -> None:
        self.args: List[Any] = []
        self.expected, self.got = expected, got

    def call(self, function: str) -> str:
        return function


class DiffBlockTests(unittest.TestCase):
    """Regression coverage for a real bug found while smoke-testing --diff
    on a multi-line C stdout mismatch: exp_text/got_text as computed in
    _failures() are repr(f.expected)/str(f.got) — fine for a Python
    Failure (got is already the sandbox's short_repr() text, so neither
    side ever has a REAL embedded newline), but for a CFailure that
    mismatches exp_text's escaped "\\n" against got_text's real one,
    so line_diff() saw ~0 lines on one side and every line as a pure
    addition on the other. _diff_block() must use the CFailure's own
    (already raw) strings instead."""

    def test_c_failure_uses_its_own_raw_strings_for_line_diff(self) -> None:
        f = _FakeCFailure("a\nb\nc", "a\nX\nc")
        exp_text, got_text = repr(f.expected), str(f.got)
        block = ui._diff_block(f, exp_text, got_text)
        assert block is not None
        exp_lines, got_lines = block
        self.assertEqual(exp_lines, ["  a", "- b", "  c"])
        self.assertEqual(got_lines, ["  a", "+ X", "  c"])

    def test_python_failure_never_gets_a_misaligned_line_diff(self) -> None:
        # A Failure's got is already short_repr()'d (no real newlines even
        # for a multi-line return value), and so is exp_text — so
        # line_diff() correctly never fires here; falls back to None
        # (the plain char-pointer takes over in _failures()).
        f = _FakeFailure("a\nb", "'a\\nX'")
        exp_text, got_text = repr(f.expected), str(f.got)
        self.assertIsNone(ui._diff_block(f, exp_text, got_text))


class SplitSubjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = (
            "Assignment name  : py_demo\n"
            "Expected files   : py_demo.py\n"
            "Allowed functions: None\n" + "-" * 20 + "\n\n"
            "Some prose explaining the exercise.\n\n"
            "    def demo(x: int) -> int:\n\n"
            "Examples:\n"
            "    demo(1) -> 2\n"
            "    demo(2) -> 4\n"
        )

    def test_header_lines_are_extracted(self) -> None:
        header, _, _, _ = ui._split_subject(self.subject)
        joined = "\n".join(header)
        self.assertIn("Assignment name  : py_demo", joined)
        self.assertIn("Allowed functions: None", joined)

    def test_signature_is_found(self) -> None:
        _, _, signature, _ = ui._split_subject(self.subject)
        self.assertEqual(signature, "def demo(x: int) -> int:")

    def test_prose_excludes_header_and_examples(self) -> None:
        _, prose, _, _ = ui._split_subject(self.subject)
        self.assertIn("Some prose explaining the exercise.", prose)
        self.assertNotIn("Assignment name", prose)
        self.assertNotIn("demo(1)", prose)

    def test_examples_are_captured(self) -> None:
        _, _, _, examples = ui._split_subject(self.subject)
        self.assertIn("demo(1) -> 2", examples)
        self.assertIn("demo(2) -> 4", examples)


class FailureTextsTests(unittest.TestCase):
    """A CFailure's raw stdout is repr()'d on BOTH sides so invisible
    characters show and --diff's pointer lines up; grader markers stay."""

    def test_c_failure_reprs_both_sides(self) -> None:
        f = _FakeCFailure("ab", "a\tb")
        self.assertEqual(ui._failure_texts(f), ("'ab'", "'a\\tb'"))

    def test_c_failure_marker_is_left_alone(self) -> None:
        f = _FakeCFailure("ab", "[TIMEOUT]")
        self.assertEqual(ui._failure_texts(f)[1], "[TIMEOUT]")

    def test_python_failure_got_is_unchanged(self) -> None:
        f = _FakeFailure("x", "'y'")
        self.assertEqual(ui._failure_texts(f), ("'x'", "'y'"))


if __name__ == "__main__":
    unittest.main()
