#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for the pure logic in c_exam/grader.py — literal encoding,
comment/string stripping, forbidden-call detection, case-chunk parsing —
plus one real end-to-end grade() call through an actual compiler.

The end-to-end tests are skipped automatically when no C compiler is on
PATH, so the suite still runs clean on a compiler-less machine (mirrors
how tests/test_grader.py's sandbox tests don't need anything special, but
here a missing `cc` genuinely can't be worked around)."""

import os
import random
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from c_exam import grader

HAVE_CC = shutil.which(grader.DEFAULT_CC) is not None
skip_without_cc = unittest.skipUnless(HAVE_CC, "no C compiler (%r) on PATH"
                                      % grader.DEFAULT_CC)

HAVE_VALGRIND = grader.have_valgrind()
skip_without_valgrind = unittest.skipUnless(
    HAVE_VALGRIND, "valgrind is not on PATH (expected on macOS, incl. Apple "
                   "Silicon — this is a real 42 school machine / Linux feature)")


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


class ExtractFunctionSourceTests(unittest.TestCase):
    def _write(self, source):
        fd, path = tempfile.mkstemp(suffix=".c")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(source)
        self.addCleanup(os.remove, path)
        return path

    def test_extracts_the_named_function(self):
        path = self._write(
            "int other(int x)\n{\n    return 0;\n}\n\n"
            "int demo(int x)\n{\n    if (x > 0)\n    {\n        return x;\n    }\n"
            "    return 0;\n}\n")
        src = grader.extract_function_source(path, "demo")
        self.assertIn("demo(int x)", src)
        self.assertIn("return x;", src)
        self.assertNotIn("other", src)

    def test_function_not_found_returns_none(self):
        path = self._write("int other(int x)\n{\n    return 0;\n}\n")
        self.assertIsNone(grader.extract_function_source(path, "demo"))

    def test_missing_file_returns_none_not_an_exception(self):
        self.assertIsNone(grader.extract_function_source("/no/such/file.c", "demo"))

    def test_unbalanced_braces_return_none(self):
        path = self._write("int demo(int x)\n{\n    return x;\n")
        self.assertIsNone(grader.extract_function_source(path, "demo"))

    def test_brace_inside_a_string_does_not_confuse_the_counter(self):
        path = self._write(
            'int demo(int x)\n{\n    char *s = "{ not a real brace";\n'
            "    return x;\n}\n")
        src = grader.extract_function_source(path, "demo")
        self.assertIsNotNone(src)
        self.assertTrue(src.rstrip().endswith("}"))

    def test_brace_inside_a_comment_does_not_confuse_the_counter(self):
        path = self._write(
            "int demo(int x)\n{\n    // a stray { in a comment\n"
            "    return x;\n}\n")
        src = grader.extract_function_source(path, "demo")
        self.assertIsNotNone(src)
        self.assertTrue(src.rstrip().endswith("}"))

    def test_name_mentioned_in_a_comment_is_not_mistaken_for_the_signature(self):
        path = self._write(
            "// calls demo(x) internally\nint demo(int x)\n{\n    return x;\n}\n")
        src = grader.extract_function_source(path, "demo")
        self.assertIsNotNone(src)
        self.assertIn("return x;", src)

    def test_string_literals_and_comments_survive_intact(self):
        # This is shown back to the student as "your own code" — a
        # printf() whose string argument silently vanished (an earlier,
        # since-fixed version of this function extracted from a
        # comment/string-STRIPPED source) would look like the tool itself
        # is broken, not like a deliberate simplification.
        path = self._write(
            'void demo(void)\n{\n    // greet the user\n'
            '    write(1, "hello world", 11);\n}\n')
        src = grader.extract_function_source(path, "demo")
        self.assertIn('"hello world"', src)
        self.assertIn("// greet the user", src)


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


class KrFuncPtrRegexTests(unittest.TestCase):
    """int (*cmp)() compiles fine under Apple Clang's default standard but
    not under GCC's C23 default (() there now means "no parameters", not
    "unspecified" like every older C standard) — this regex is what lets
    make c-check catch that without needing a second compiler on hand."""

    def test_flags_empty_parens_function_pointer(self):
        self.assertTrue(grader._KR_FUNC_PTR_RE.search("int (*cmp)();"))

    def test_does_not_flag_a_typed_function_pointer(self):
        self.assertFalse(grader._KR_FUNC_PTR_RE.search(
            "int (*cmp)(void *, void *);"))

    def test_does_not_flag_a_void_typed_function_pointer(self):
        self.assertFalse(grader._KR_FUNC_PTR_RE.search("void (*f)(void *);"))

    def test_does_not_flag_a_plain_prototype(self):
        self.assertFalse(grader._KR_FUNC_PTR_RE.search(
            "int ft_strlen(char *str);"))


class FuzzableTests(unittest.TestCase):
    def test_all_safe_kinds_is_fuzzable(self):
        ex = {"args": ["int", "char", "str", "int_arr", "int_list", "buf", "int_ptr"]}
        self.assertTrue(grader.is_fuzzable(ex))

    def test_fixed_callback_kind_does_not_block_fuzzing(self):
        ex = {"args": ["int_list", "cmp_ascending"]}
        self.assertTrue(grader.is_fuzzable(ex))

    def test_unsafe_kind_blocks_fuzzing(self):
        for kind in ("point", "char_grid", "voidlist", "voidlist_ptr"):
            with self.subTest(kind=kind):
                self.assertFalse(grader.is_fuzzable({"args": [kind]}))

    def test_program_kind_without_an_argv_shape_is_not_fuzzable(self):
        ex = {"kind": "program", "args": ["str"]}
        self.assertFalse(grader.is_fuzzable(ex))

    def test_program_kind_with_an_argv_shape_is_fuzzable(self):
        self.assertTrue(grader.is_fuzzable({"kind": "program", "fuzz_argv": "sentence"}))
        self.assertFalse(grader.is_fuzzable({"kind": "program", "fuzz_argv": "no-such"}))


class ArgvFuzzTests(unittest.TestCase):
    """Shape-based argv fuzzing for "program"-kind exercises."""

    def test_every_shape_yields_string_argvs(self):
        rng = random.Random(5)
        for shape in grader.ARGV_SHAPES:
            with self.subTest(shape=shape):
                for _ in range(200):
                    argv = grader.fuzz_argv(shape, rng)
                    self.assertIsInstance(argv, list)
                    self.assertTrue(all(isinstance(a, str) and "\0" not in a for a in argv))

    def test_fixed_argc_shapes_mostly_have_the_right_argc(self):
        rng = random.Random(6)
        for shape, (_make, argc) in grader.ARGV_SHAPES.items():
            if argc is None:
                continue
            with self.subTest(shape=shape):
                counts = [len(grader.fuzz_argv(shape, rng)) for _ in range(300)]
                right = sum(1 for n in counts if n == argc)
                self.assertGreater(right, 200)       # ~90% right argc
                self.assertLess(right, 300)          # …but wrong argc happens

    def test_sentences_cover_whitespace_traps(self):
        rng = random.Random(7)
        texts = [grader.fuzz_argv("sentence", rng) for _ in range(300)]
        flat = [t[0] for t in texts if len(t) == 1]
        self.assertTrue(any("\t" in t for t in flat))
        self.assertTrue(any(t == "" for t in flat))
        self.assertTrue(any(t and t.strip() == "" for t in flat))
        self.assertTrue(any(t != t.strip() and t.strip() for t in flat))

    def test_division_never_by_zero(self):
        rng = random.Random(8)
        for _ in range(500):
            argv = grader.fuzz_argv("do_op", rng)
            if len(argv) == 3 and argv[1] in "/%":
                self.assertNotEqual(argv[2], "0")

    def test_every_bank_shape_exists(self):
        from c_exam.bank import EXERCISES
        for name, ex in EXERCISES.items():
            if "fuzz_argv" in ex:
                with self.subTest(name=name):
                    self.assertIn(ex["fuzz_argv"], grader.ARGV_SHAPES)


class CFailureCallTests(unittest.TestCase):
    def test_program_call_is_a_pasteable_command(self):
        f = grader.CFailure(3, "", "", args=["a b", "\tx"], program=True)
        self.assertEqual(f.call("first_word"), "./first_word 'a b' $'\\tx'")

    def test_no_arguments(self):
        f = grader.CFailure(0, "", "", args=[], program=True)
        self.assertEqual(f.call("rotone"), "./rotone")

    def test_function_call_shows_the_values(self):
        f = grader.CFailure(1, "5", "4", args=["hello"])
        self.assertEqual(f.call("ft_strlen"), "ft_strlen('hello')")

    def test_unknown_inputs_fall_back_to_the_case_index(self):
        self.assertEqual(grader.CFailure(2, "", "").call("f"), "f()  [case 2]")

    def test_no_args_is_fuzzable(self):
        self.assertTrue(grader.is_fuzzable({"args": []}))


class BuildFuzzCasesTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1234)

    def test_generates_the_requested_count(self):
        ex = {"args": ["int", "str"]}
        cases = grader.build_fuzz_cases(ex, self.rng, 10)
        self.assertEqual(len(cases), 10)

    def test_one_value_per_non_fixed_callback_arg(self):
        ex = {"args": ["int", "cmp_ascending", "str"]}
        cases = grader.build_fuzz_cases(ex, self.rng, 5)
        for case in cases:
            self.assertEqual(len(case), 2)   # cmp_ascending consumes no value

    def test_int_values_are_in_range(self):
        ex = {"args": ["int"]}
        for case in grader.build_fuzz_cases(ex, self.rng, 200):
            self.assertTrue(-1000 <= case[0] <= 1000)

    def test_char_values_are_printable_ascii(self):
        ex = {"args": ["char"]}
        for case in grader.build_fuzz_cases(ex, self.rng, 200):
            self.assertEqual(len(case[0]), 1)
            self.assertTrue(32 <= ord(case[0]) <= 126)

    def test_buf_values_stay_well_under_the_harness_buffer(self):
        ex = {"args": ["buf"]}
        for case in grader.build_fuzz_cases(ex, self.rng, 50):
            self.assertLess(len(case[0]), 128)

    def test_str_values_use_a_safe_alphabet(self):
        ex = {"args": ["str"]}
        for case in grader.build_fuzz_cases(ex, self.rng, 50):
            for ch in case[0]:
                self.assertIn(ch, grader._FUZZ_STR_ALPHABET)

    def test_int_arr_and_int_list_are_small_int_lists(self):
        ex = {"args": ["int_arr", "int_list"]}
        for case in grader.build_fuzz_cases(ex, self.rng, 50):
            for arr in case:
                self.assertIsInstance(arr, list)
                self.assertLessEqual(len(arr), 6)
                for v in arr:
                    self.assertTrue(-50 <= v <= 50)

    def test_is_deterministic_given_the_same_rng_state(self):
        ex = {"args": ["int", "str", "int_arr"]}
        cases_a = grader.build_fuzz_cases(ex, random.Random(99), 20)
        cases_b = grader.build_fuzz_cases(ex, random.Random(99), 20)
        self.assertEqual(cases_a, cases_b)


class GenerateHarnessCasesOverrideTests(unittest.TestCase):
    def test_defaults_to_ex_cases(self):
        ex = {"function": "ft_strlen", "prototype": "int ft_strlen(char *str);",
             "args": ["str"], "returns": "int", "cases": [["a"], ["bb"]]}
        harness = grader.generate_harness(ex)
        self.assertEqual(harness.count("===CASE"), 2)

    def test_override_replaces_ex_cases(self):
        ex = {"function": "ft_strlen", "prototype": "int ft_strlen(char *str);",
             "args": ["str"], "returns": "int", "cases": [["a"]]}
        harness = grader.generate_harness(ex, [["a"], ["b"], ["c"]])
        self.assertEqual(harness.count("===CASE"), 3)


class SplitCasesTests(unittest.TestCase):
    def test_splits_by_marker(self):
        out = "===CASE 0===\nfoo\n===CASE 1===\nbar\n"
        self.assertEqual(grader.split_cases(out), {0: "foo\n", 1: "bar\n"})

    def test_missing_markers_yield_no_chunks(self):
        self.assertEqual(grader.split_cases("garbage, no markers"), {})


class RunValgrindCommandTests(unittest.TestCase):
    """run_valgrind()'s command construction and exit-code interpretation,
    with subprocess.run mocked out — doesn't need valgrind on PATH, so this
    runs everywhere (including this project's own dev machine, Apple
    Silicon macOS, where valgrind isn't installable at all)."""

    def _run(self, returncode, stderr="", side_effect=None):
        with mock.patch.object(grader.subprocess, "run") as run:
            if side_effect is not None:
                run.side_effect = side_effect
            else:
                run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=returncode, stdout="", stderr=stderr)
            result = grader.run_valgrind("/tmp/some_binary", timeout=3, argv=["a", "b"])
            return result, run

    def test_clean_exit_is_reported_clean(self):
        (clean, detail), _ = self._run(returncode=0)
        self.assertTrue(clean)
        self.assertEqual(detail, "")

    def test_error_exitcode_is_reported_dirty_with_detail(self):
        (clean, detail), _ = self._run(
            returncode=grader.VALGRIND_ERROR_EXITCODE,
            stderr="==123== 40 bytes in 1 blocks are definitely lost")
        self.assertFalse(clean)
        self.assertIn("definitely lost", detail)

    def test_traced_programs_own_exit_code_colliding_with_the_sentinel_is_still_clean(self):
        # --error-exitcode only overrides the exit code when valgrind ITSELF
        # found something; a clean run passes the traced program's own exit
        # code straight through, which can coincidentally equal
        # VALGRIND_ERROR_EXITCODE. Regression test: no "==<pid>==" line in
        # stderr means valgrind found nothing, regardless of the exit code.
        (clean, detail), _ = self._run(
            returncode=grader.VALGRIND_ERROR_EXITCODE, stderr="")
        self.assertTrue(clean)
        self.assertEqual(detail, "")

    def test_timeout_is_reported_dirty_not_raised(self):
        (clean, detail), _ = self._run(
            returncode=0, side_effect=subprocess.TimeoutExpired(cmd="valgrind", timeout=3))
        self.assertFalse(clean)
        self.assertIn("timed out", detail)

    def test_command_uses_leak_check_full_and_error_exitcode(self):
        _, run = self._run(returncode=0)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[0], "valgrind")
        self.assertIn("--leak-check=full", cmd)
        self.assertIn("--errors-for-leak-kinds=all", cmd)
        self.assertIn("--error-exitcode=%d" % grader.VALGRIND_ERROR_EXITCODE, cmd)
        self.assertIn("/tmp/some_binary", cmd)
        # the exercise's own argv must be forwarded after the binary path
        self.assertEqual(cmd[-2:], ["a", "b"])

    def test_have_valgrind_reflects_path_lookup(self):
        with mock.patch.object(grader.shutil, "which", return_value=None):
            self.assertFalse(grader.have_valgrind())
        with mock.patch.object(grader.shutil, "which", return_value="/usr/bin/valgrind"):
            self.assertTrue(grader.have_valgrind())


@skip_without_valgrind
class ValgrindEndToEndTests(unittest.TestCase):
    """Real valgrind runs — skipped everywhere valgrind isn't installed
    (this project's own dev machine included), but exercised for real on
    any Linux CI runner that has it (see .github/workflows/ci.yml)."""

    CLEAN_C = "int add(int a, int b) { return a + b; }\n" \
             "int main(void) { return add(1, 2) == 3 ? 0 : 1; }\n"
    LEAKY_C = "#include <stdlib.h>\n" \
             "int main(void) { int *p = malloc(sizeof(int)); *p = 42; return 0; }\n"

    def _compile(self, tmp, name, src):
        import os
        path = os.path.join(tmp, name + ".c")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        binpath = os.path.join(tmp, name)
        ok, err = grader.compile_c([path], binpath)
        self.assertTrue(ok, err)
        return binpath

    def test_clean_binary_is_reported_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            binpath = self._compile(tmp, "clean", self.CLEAN_C)
            clean, detail = grader.run_valgrind(binpath, timeout=10)
            self.assertTrue(clean, detail)

    def test_leaky_binary_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            binpath = self._compile(tmp, "leaky", self.LEAKY_C)
            clean, detail = grader.run_valgrind(binpath, timeout=10)
            self.assertFalse(clean)
            self.assertIn("lost", detail)


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

    def test_forbidden_call_only_warns_by_default(self):
        ex = dict(self.EX, forbidden=["strlen"])
        cheat = "#include <string.h>\n" \
               "int ft_strlen(char *str)\n{\n    return strlen(str);\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, cheat)
            report = grader.grade("ft_strlen", ex, tmp)
            self.assertTrue(report.ok, report.failures)
            self.assertTrue(any("forbidden" in w for w in report.warnings))

    def test_strict_forbidden_fails_a_solution_that_uses_the_forbidden_call(self):
        # Unlike Python's --strict-imports, a forbidden C call used to only
        # ever warn — never fail grading, no matter what — so a solution
        # that just calls the libc function it's supposed to reimplement
        # still scored 100%.
        ex = dict(self.EX, forbidden=["strlen"])
        cheat = "#include <string.h>\n" \
               "int ft_strlen(char *str)\n{\n    return strlen(str);\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, cheat)
            report = grader.grade("ft_strlen", ex, tmp, strict_forbidden=True)
            self.assertEqual(report.fatal, "FORBIDDEN_CALL")
            self.assertIn("strlen", report.detail)

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

    def test_fuzz_adds_extra_cases_and_still_passes_for_the_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", self.EX, tmp,
                                  rng=random.Random(7), fuzz=5)
            self.assertTrue(report.ok, report.failures)
            self.assertEqual(report.total, len(self.EX["cases"]) + 5)

    def test_fuzz_zero_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", self.EX, tmp,
                                  rng=random.Random(7), fuzz=0)
            self.assertEqual(report.total, len(self.EX["cases"]))

    def test_fuzz_is_skipped_for_an_unfuzzable_exercise(self):
        ex = dict(self.EX, args=["point"])   # not in FUZZABLE_VALUE_KINDS
        # point-kind args need real decls this stub EX lacks — just check
        # is_fuzzable directly rather than compiling; grade() consults it
        # via the same function, see test_grade_ignores_fuzz_for_program_kind
        # below for the end-to-end confirmation on a real exercise shape.
        self.assertFalse(grader.is_fuzzable(ex))

    def test_grade_ignores_fuzz_for_program_kind(self):
        program_ex = {
            "function": "echoprog", "kind": "program",
            "oracle_c": "#include <stdio.h>\n"
                       "int main(int argc, char **argv)\n{\n"
                       "    (void)argc;\n    printf(\"%s\\n\", argv[1]);\n"
                       "    return 0;\n}\n",
            "cases": [["hi"], ["there"]],
        }
        with tempfile.TemporaryDirectory() as tmp:
            self._write_named(tmp, "echoprog.c", program_ex["oracle_c"])
            report = grader.grade("echoprog", program_ex, tmp,
                                  rng=random.Random(7), fuzz=50)
            self.assertTrue(report.ok, report.failures)
            self.assertEqual(report.total, 2)   # fuzz never applies to "program" kind

    def test_strict_forbidden_fails_a_program_kind_solution_too(self):
        program_ex = {
            "function": "echoprog", "kind": "program", "forbidden": ["puts"],
            "oracle_c": "#include <stdio.h>\n"
                       "int main(int argc, char **argv)\n{\n"
                       "    (void)argc;\n    printf(\"%s\\n\", argv[1]);\n"
                       "    return 0;\n}\n",
            "cases": [["hi"], ["there"]],
        }
        cheat = "#include <stdio.h>\n" \
               "int main(int argc, char **argv)\n{\n" \
               "    (void)argc;\n    puts(argv[1]);\n    return 0;\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write_named(tmp, "echoprog.c", cheat)
            report = grader.grade("echoprog", program_ex, tmp, strict_forbidden=True)
            self.assertEqual(report.fatal, "FORBIDDEN_CALL")
            self.assertIn("puts", report.detail)

    def _write_named(self, tmp, filename, body):
        path = tmp + "/" + filename
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def test_broken_oracle_is_a_graceful_bank_error_not_a_crash(self):
        broken_ex = dict(self.EX, oracle_c="this is not valid C at all {{{")
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", broken_ex, tmp)
            self.assertEqual(report.fatal, "BANK_ERROR")

    def test_broken_codegen_is_a_graceful_bank_error_not_a_crash(self):
        # render_call() raises ValueError on an unknown `returns` kind —
        # regression test for generate_harness() being uncaught in the
        # live grading path (only selftest() used to catch a codegen
        # crash; a fuzzed value can hit this even when curated cases
        # never do, see the module docstring).
        broken_ex = dict(self.EX, returns="no_such_return_kind")
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", broken_ex, tmp)
            self.assertEqual(report.fatal, "BANK_ERROR")

    def test_duration_includes_a_slow_valgrind_pass(self):
        # _grade_program's report.duration already included valgrind time
        # (its one assignment sits after the per-case valgrind loop);
        # _grade_function's used to be set BEFORE its own valgrind pass
        # and never updated — regression test for that inconsistency.
        # Mocked (not @skip_without_valgrind): only grade()'s own
        # bookkeeping is under test here, not a real valgrind run.
        def slow_but_clean(*args, **kwargs):
            time.sleep(0.2)
            return True, ""
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            with mock.patch.object(grader, "have_valgrind", return_value=True), \
                 mock.patch.object(grader, "run_valgrind", side_effect=slow_but_clean):
                report = grader.grade("ft_strlen", self.EX, tmp, valgrind=True)
            self.assertTrue(report.ok, report.failures)
            self.assertGreaterEqual(report.duration, 0.2)

    @skip_without_valgrind
    def test_valgrind_false_never_runs_it(self):
        # a correct-but-leaky solution must NOT be flagged when valgrind
        # wasn't requested — grade()'s default behaviour is unchanged.
        leaky = "#include <stdlib.h>\n" \
               "int ft_strlen(char *str)\n{\n" \
               "    int *leak = malloc(sizeof(int));\n    *leak = 1;\n" \
               "    int i = 0;\n    while (str[i]) i++;\n    return i;\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, leaky)
            report = grader.grade("ft_strlen", self.EX, tmp)
            self.assertTrue(report.ok, report.failures)
            self.assertEqual(report.warnings, [])

    @skip_without_valgrind
    def test_valgrind_true_warns_on_a_leaky_but_correct_solution(self):
        leaky = "#include <stdlib.h>\n" \
               "int ft_strlen(char *str)\n{\n" \
               "    int *leak = malloc(sizeof(int));\n    *leak = 1;\n" \
               "    int i = 0;\n    while (str[i]) i++;\n    return i;\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, leaky)
            report = grader.grade("ft_strlen", self.EX, tmp, valgrind=True)
            self.assertTrue(report.ok)   # output is still correct
            self.assertTrue(any("valgrind" in w for w in report.warnings))

    @skip_without_valgrind
    def test_strict_valgrind_fails_a_leaky_but_correct_solution(self):
        leaky = "#include <stdlib.h>\n" \
               "int ft_strlen(char *str)\n{\n" \
               "    int *leak = malloc(sizeof(int));\n    *leak = 1;\n" \
               "    int i = 0;\n    while (str[i]) i++;\n    return i;\n}\n"
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, leaky)
            report = grader.grade("ft_strlen", self.EX, tmp,
                                  valgrind=True, strict_valgrind=True)
            self.assertEqual(report.fatal, "VALGRIND_ERRORS")

    @skip_without_valgrind
    def test_valgrind_true_is_silent_on_a_clean_solution(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("ft_strlen", self.EX, tmp, valgrind=True)
            self.assertTrue(report.ok)
            self.assertEqual(report.warnings, [])


@skip_without_cc
@skip_without_valgrind
class ValgrindProgramKindEndToEndTests(unittest.TestCase):
    """"program"-kind exercises run valgrind once per case (a separate
    loop from "function"-kind's single pass) — its own coverage."""

    EX = {
        "function": "echoprog", "kind": "program",
        "oracle_c": "#include <stdio.h>\n"
                   "int main(int argc, char **argv)\n{\n"
                   "    (void)argc;\n    printf(\"%s\\n\", argv[1]);\n"
                   "    return 0;\n}\n",
        "cases": [["hi"], ["there"]],
    }
    LEAKY_C = "#include <stdio.h>\n#include <stdlib.h>\n" \
             "int main(int argc, char **argv)\n{\n" \
             "    int *leak = malloc(sizeof(int));\n    *leak = 1;\n" \
             "    (void)argc;\n    printf(\"%s\\n\", argv[1]);\n" \
             "    return 0;\n}\n"

    def _write(self, tmp, body):
        path = tmp + "/echoprog.c"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def test_leaky_program_is_caught_across_multiple_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.LEAKY_C)
            report = grader.grade("echoprog", self.EX, tmp, valgrind=True)
            self.assertTrue(report.ok)   # still correct output
            self.assertTrue(any("valgrind" in w for w in report.warnings))

    def test_strict_valgrind_fails_a_leaky_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.LEAKY_C)
            report = grader.grade("echoprog", self.EX, tmp,
                                  valgrind=True, strict_valgrind=True)
            self.assertEqual(report.fatal, "VALGRIND_ERRORS")

    def test_clean_program_has_no_valgrind_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, self.EX["oracle_c"])
            report = grader.grade("echoprog", self.EX, tmp, valgrind=True)
            self.assertTrue(report.ok)
            self.assertEqual(report.warnings, [])


@skip_without_cc
class ProgramTimeoutBailOutTests(unittest.TestCase):
    """A "program"-kind infinite loop stops being run after MAX_TIMEOUTS
    consecutive timeouts — the remaining cases are marked skipped instead
    of each burning the full per-case timeout."""

    EX = {
        "kind": "program", "function": "echo_arg",
        "oracle_c": "#include <unistd.h>\n#include <string.h>\n"
                    "int main(int ac, char **av)\n{\n"
                    "    if (ac == 2) write(1, av[1], strlen(av[1]));\n"
                    "    write(1, \"\\n\", 1);\n    return 0;\n}\n",
        "cases": [["a"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"], ["h"]],
    }

    def test_infinite_loop_skips_cases_after_max_timeouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(tmp + "/echo_arg.c", "w", encoding="utf-8") as fh:
                fh.write("int main(void)\n{\n    while (1)\n        ;\n}\n")
            started = time.time()
            report = grader.grade("echo_arg", self.EX, tmp, timeout=1)
            elapsed = time.time() - started
        self.assertEqual(report.passed, 0)
        self.assertEqual(len(report.failures), len(self.EX["cases"]))
        skipped = [f for f in report.failures if "skipped" in f.got]
        self.assertEqual(len(skipped), len(self.EX["cases"]) - grader.MAX_TIMEOUTS)
        # 3 real timeouts at 1s each, not 8
        self.assertLess(elapsed, len(self.EX["cases"]) - 1)


if __name__ == "__main__":
    unittest.main()
