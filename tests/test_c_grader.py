#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in c_exam/grader.py — literal encoding,
comment/string stripping, forbidden-call detection, case-chunk parsing —
plus one real end-to-end grade() call through an actual compiler.

The end-to-end tests are skipped automatically when no C compiler is on
PATH, so the suite still runs clean on a compiler-less machine (mirrors
how tests/test_grader.py's sandbox tests don't need anything special, but
here a missing `cc` genuinely can't be worked around)."""

import shutil
import tempfile
import unittest

from c_exam import grader

HAVE_CC = shutil.which(grader.DEFAULT_CC) is not None
skip_without_cc = unittest.skipUnless(HAVE_CC, "no C compiler (%r) on PATH"
                                      % grader.DEFAULT_CC)


class CLiteralTests(unittest.TestCase):
    def test_char_literal_escapes_special_chars(self):
        self.assertEqual(grader.c_char_literal("a"), "'a'")
        self.assertEqual(grader.c_char_literal("\n"), "'\\n'")
        self.assertEqual(grader.c_char_literal("'"), "'\\''")
        self.assertEqual(grader.c_char_literal("\\"), "'\\\\'")

    def test_string_literal_escapes_special_chars(self):
        self.assertEqual(grader.c_string_literal("hello"), '"hello"')
        self.assertEqual(grader.c_string_literal('a"b'), '"a\\"b"')
        self.assertEqual(grader.c_string_literal("a\nb"), '"a\\nb"')
        self.assertEqual(grader.c_string_literal(""), '""')

    def test_string_literal_escapes_non_ascii(self):
        self.assertIn("\\x", grader.c_string_literal("\x01"))


class StripCommentsAndStringsTests(unittest.TestCase):
    def test_line_comment_is_removed(self):
        stripped = grader._strip_comments_and_strings("int main(void) // hi\n{ return 0; }")
        self.assertNotIn("hi", stripped)
        self.assertIn("int main(void)", stripped)

    def test_block_comment_is_removed(self):
        stripped = grader._strip_comments_and_strings("/* main( */ int x;")
        self.assertNotIn("main(", stripped)

    def test_string_contents_are_removed(self):
        stripped = grader._strip_comments_and_strings('char *s = "call strlen(x) here";')
        self.assertNotIn("strlen(", stripped)

    def test_real_code_is_untouched(self):
        src = "int ft_strlen(char *str)\n{\n    return 0;\n}\n"
        self.assertEqual(grader._strip_comments_and_strings(src), src)


class ForbiddenCallTests(unittest.TestCase):
    def test_finds_a_real_call(self):
        stripped = grader._strip_comments_and_strings("int x = strlen(str);")
        self.assertEqual(grader.find_forbidden(stripped, ["strlen"]), ["strlen"])

    def test_ignores_a_call_inside_a_comment(self):
        stripped = grader._strip_comments_and_strings("// strlen(str) is banned\nint y;")
        self.assertEqual(grader.find_forbidden(stripped, ["strlen"]), [])

    def test_does_not_false_positive_on_a_prefix(self):
        # "ft_strlen(" contains "strlen(" as a substring but not as its own
        # word — \b must not match inside another identifier.
        stripped = grader._strip_comments_and_strings("int x = ft_strlen(str);")
        self.assertEqual(grader.find_forbidden(stripped, ["strlen"]), [])


class DuplicateMainTests(unittest.TestCase):
    def test_detects_ld64_wording(self):
        self.assertTrue(grader._is_duplicate_main(
            "duplicate symbol '_main' in:\n  a.o\n  b.o\nld: 1 duplicate symbols"))

    def test_detects_gnu_ld_wording(self):
        self.assertTrue(grader._is_duplicate_main(
            "b.o: in function `main':\nb.c:1: multiple definition of `main'"))

    def test_unrelated_error_is_not_flagged(self):
        self.assertFalse(grader._is_duplicate_main(
            "error: expected ';' before '}' token"))


class SplitCasesTests(unittest.TestCase):
    def test_splits_by_marker(self):
        out = "===CASE 0===\nfoo\n===CASE 1===\nbar\n"
        self.assertEqual(grader.split_cases(out), {0: "foo\n", 1: "bar\n"})

    def test_missing_markers_yield_no_chunks(self):
        self.assertEqual(grader.split_cases("garbage, no markers"), {})


@skip_without_cc
class GradeEndToEndTests(unittest.TestCase):
    EX = {
        "function": "ft_strlen", "prototype": "int ft_strlen(char *str);",
        "args": ["str"], "returns": "int",
        "oracle_c": "int ft_strlen(char *str)\n{\n"
                   "    int i = 0;\n    while (str[i]) i++;\n    return i;\n}\n",
        "cases": [["hello"], [""], ["ab"]],
    }

    def _write(self, tmp, body):
        path = tmp + "/ft_strlen.c"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def test_correct_solution_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertTrue(report.ok, report.failures)
            self.assertEqual(report.passed, report.total)

    def test_wrong_solution_fails_with_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "int ft_strlen(char *str)\n{\n"
                             "    (void)str;\n    return 42;\n}\n")
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertFalse(report.ok)
            self.assertEqual(report.passed, 0)
            self.assertEqual(report.failures[0].got, "42")

    def test_unguarded_main_is_reported_as_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"] + "\nint main(void) { return 0; }\n")
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertEqual(report.fatal, "FORBIDDEN_MAIN")

    def test_selftest_guarded_main_does_not_trip_the_check(self):
        # the exact shape c_exam/examshell.py's stub ships — must grade fine
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"] +
                       "\n#ifdef SELF_TEST\nint main(void) { return 0; }\n#endif\n")
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertTrue(report.ok, report.failures)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertEqual(report.fatal, "FILE_MISSING")


if __name__ == "__main__":
    unittest.main()
