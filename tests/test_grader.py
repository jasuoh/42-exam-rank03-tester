#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in src/grader.py.

These do not touch the exercise bank's content — that is `make check`'s
job. They exercise the grader's own building blocks in isolation: type
comparison, import detection, test-set building, report shape.
"""

import os
import random
import tempfile
import unittest

from src import grader

_SOME_MODULE_GLOBAL = 42  # used by a fixture function below


def _uses_a_module_global(x):
    return x + _SOME_MODULE_GLOBAL


def _fully_self_contained(x):
    return x * 2


def _ref_demo(x):
    return x + 1


class DeepEqTests(unittest.TestCase):
    def test_bool_is_not_int(self):
        self.assertFalse(grader.deep_eq(True, 1))
        self.assertFalse(grader.deep_eq(False, 0))
        self.assertTrue(grader.deep_eq(True, True))

    def test_list_is_not_tuple(self):
        self.assertFalse(grader.deep_eq([1], (1,)))

    def test_int_and_float_compare_numerically(self):
        self.assertTrue(grader.deep_eq(1, 1.0))
        self.assertFalse(grader.deep_eq(1, 1.5))

    def test_nested_lists(self):
        self.assertTrue(grader.deep_eq([[1, 2], [3]], [[1, 2], [3]]))
        self.assertFalse(grader.deep_eq([[1, 2], [3]], [[1, 2], [3, 4]]))

    def test_dicts_are_order_independent_but_type_strict(self):
        self.assertTrue(grader.deep_eq({"a": 1, "b": 2}, {"b": 2, "a": 1}))
        self.assertFalse(grader.deep_eq({"a": 1}, {"a": True}))
        self.assertFalse(grader.deep_eq({"a": 1}, {"a": 1, "b": 2}))

    def test_recursive_helper_is_self_contained(self):
        # deep_eq calls itself; that must be its only "free" global.
        extra = grader._free_globals(grader.deep_eq, allow=("deep_eq",))
        self.assertEqual(extra, [])


class ShortReprTests(unittest.TestCase):
    def test_short_value_is_untouched(self):
        self.assertEqual(grader.short_repr([1, 2, 3]), "[1, 2, 3]")

    def test_long_value_is_truncated(self):
        text = grader.short_repr("x" * 500, limit=20)
        self.assertEqual(len(text), 21)          # 20 chars + the ellipsis
        self.assertTrue(text.endswith("…"))

    def test_unrepresentable_object_does_not_raise(self):
        class Cursed(object):
            def __repr__(self):
                raise RuntimeError("nope")

        self.assertEqual(grader.short_repr(Cursed()), "<unrepresentable object>")


class FreeGlobalsTests(unittest.TestCase):
    def test_pure_function_has_no_free_globals(self):
        self.assertEqual(grader._free_globals(_fully_self_contained), [])

    def test_module_global_is_detected(self):
        self.assertIn("_SOME_MODULE_GLOBAL",
                      grader._free_globals(_uses_a_module_global))


class BuildTestsTests(unittest.TestCase):
    def test_curated_cases_are_deduplicated(self):
        ex = {"oracle": lambda x: x * 2,
              "cases": [[1], [1], [2]],
              "fuzz": lambda rng: [rng.randint(0, 1000)]}
        tests = grader.build_tests("fake", ex, random.Random(0), fuzz=0)
        self.assertEqual(len(tests), 2)
        self.assertIn(([1], 2), [(a, e) for a, e in tests])
        self.assertIn(([2], 4), [(a, e) for a, e in tests])

    def test_curated_oracle_crash_is_a_bank_error(self):
        ex = {"oracle": lambda x: 1 / x, "cases": [[0]], "fuzz": lambda rng: [1]}
        with self.assertRaises(grader.BankError):
            grader.build_tests("fake", ex, random.Random(0), fuzz=0)

    def test_broken_fuzzer_is_a_bank_error(self):
        ex = {"oracle": lambda x: x, "cases": [], "fuzz": lambda rng: 1 / 0}
        with self.assertRaises(grader.BankError):
            grader.build_tests("fake", ex, random.Random(0), fuzz=1)

    def test_fuzz_case_that_crashes_the_oracle_is_skipped_not_fatal(self):
        # unlike a curated case, a bad *fuzz* draw is just discarded
        ex = {"oracle": lambda x: 1 / x, "cases": [],
              "fuzz": lambda rng: [rng.choice([0, 1, 2])]}
        tests = grader.build_tests("fake", ex, random.Random(1), fuzz=20)
        self.assertTrue(all(args != [0] for args, _ in tests))


class FindImportsTests(unittest.TestCase):
    def _write(self, source):
        fd, path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(source)
        self.addCleanup(os.remove, path)
        return path

    def test_real_import_is_found(self):
        path = self._write("import os\nfrom sys import argv\n")
        found = grader.find_imports(path)
        self.assertEqual(len(found), 2)

    def test_import_mentioned_in_a_string_is_not_flagged(self):
        path = self._write('text = "please import os"\n')
        self.assertEqual(grader.find_imports(path), [])

    def test_import_mentioned_in_a_comment_is_not_flagged(self):
        path = self._write("# import os\nx = 1\n")
        self.assertEqual(grader.find_imports(path), [])

    def test_missing_file_returns_empty_not_an_exception(self):
        self.assertEqual(grader.find_imports("/no/such/file.py"), [])

    def test_syntax_error_returns_empty_not_an_exception(self):
        path = self._write("def broken(:\n")
        self.assertEqual(grader.find_imports(path), [])


class OracleSourceTests(unittest.TestCase):
    def test_function_is_renamed_and_stays_valid_python(self):
        ex = {"oracle": _ref_demo, "function": "demo"}
        src = grader.oracle_source(ex)
        self.assertIn("def demo(", src)
        namespace = {}
        exec(compile(src, "<test>", "exec"), namespace)
        self.assertEqual(namespace["demo"](1), 2)


class ReportTests(unittest.TestCase):
    def test_ok_requires_total_greater_than_zero(self):
        report = grader.Report("ex", "fn")
        self.assertFalse(report.ok)          # 0/0 is not a pass
        report.total, report.passed = 5, 5
        self.assertTrue(report.ok)
        report.passed = 4
        self.assertFalse(report.ok)

    def test_fatal_short_circuits_ok(self):
        report = grader.Report("ex", "fn")
        report.total = report.passed = 5
        report.fail("FILE_MISSING")
        self.assertFalse(report.ok)

    def test_fatal_title_falls_back_to_the_raw_code(self):
        report = grader.Report("ex", "fn").fail("SOMETHING_NEW")
        self.assertEqual(report.fatal_title, "SOMETHING_NEW")
        known = grader.Report("ex", "fn").fail("FILE_MISSING")
        self.assertEqual(known.fatal_title, grader.FATAL_TITLES["FILE_MISSING"])

    def test_failure_call_formatting(self):
        failure = grader.Failure(["ab", 3], "expected", "got")
        self.assertEqual(failure.call("f"), "f('ab', 3)")


class GradeTests(unittest.TestCase):
    """Cheap paths through grade() that do not need the sandbox."""

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            ex = {"oracle": lambda x: x, "cases": [[1]],
                  "fuzz": lambda rng: [1], "function": "demo"}
            report = grader.grade("demo", ex, tmp, random.Random(0))
            self.assertEqual(report.fatal, "FILE_MISSING")

    def test_strict_imports_rejects_before_running_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "demo.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("import os\ndef demo(x):\n    return x\n")
            ex = {"oracle": lambda x: x, "cases": [[1]],
                  "fuzz": lambda rng: [1], "function": "demo"}
            report = grader.grade("demo", ex, tmp, random.Random(0),
                                  strict_imports=True)
            self.assertEqual(report.fatal, "FORBIDDEN")

    def test_correct_solution_passes_through_the_real_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "demo.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("def demo(x):\n    return x * 2\n")
            ex = {"oracle": lambda x: x * 2, "cases": [[1], [2], [3]],
                  "fuzz": lambda rng: [rng.randint(-5, 5)], "function": "demo"}
            report = grader.grade("demo", ex, tmp, random.Random(0), fuzz=3)
            self.assertTrue(report.ok, report.failures)
            self.assertEqual(report.passed, report.total)


if __name__ == "__main__":
    unittest.main()
