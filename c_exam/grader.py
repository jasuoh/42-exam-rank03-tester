#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grader.py  ·  sandboxed grading engine for the C Exam Rank 02 tester

Real Exam Rank 02 subjects come in two shapes, and this bank has both:

  "function"  the student writes ONE function, the tester supplies main().
              A small C test harness is GENERATED from the exercise's
              `args`/`returns`/`cases` metadata — one call per curated
              case, each wrapped so its output is isolated between
              "===CASE N===" markers. The harness is compiled once
              against the bank's reference implementation (`oracle_c`)
              and once against the student's file; both binaries run,
              their stdout is diffed chunk by chunk.

  "program"   the student writes a full program, argv and all (e.g.
              `rotone`, `fizzbuzz`, `hidenp`) — there is no harness here,
              because there's nothing to call: the student's own main()
              *is* the thing under test. Both the student's file and
              `oracle_c` (also a full program) are compiled standalone,
              then run once per case with that case's argv, and their
              stdout is diffed directly.

Both paths share compiling, running, and diffing — `grade()` just picks
which one applies per exercise. `Report` and `BankError` are reused as-is
from `src/grader.py` (plain bookkeeping, no Python-specific logic).
`CFailure` here plays the role `Failure` plays there, keyed by case index
instead of call arguments.
"""

import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

from src.grader import BankError, Report

DEFAULT_TIMEOUT = 5        # seconds per case (program mode) / per whole run (function mode)
DEFAULT_CC = "cc"
COMPILE_TIMEOUT = 20       # seconds for a single compiler invocation

CASE_DELIM = "===CASE "
_CASE_RE = re.compile(r"===CASE (\d+)===\n")

# Shared with any exercise using a linked list ("int_list" arg/return) —
# written into the sandbox's temp workdir at grade time, and alongside a
# generated stub, so the student's own file can #include "list.h" too, the
# same way the real exam hands you a header for exercises that need one.
LIST_H_CONTENT = """#ifndef LIST_H
# define LIST_H

typedef struct s_list
{
    int             data;
    struct s_list   *next;
}   t_list;

#endif
"""

# For ft_list_foreach / ft_list_remove_if: the real subject's t_list is a
# `void *data` generic node — a different shape than LIST_H_CONTENT's
# int-only one, so it gets its own header (mirrors the real exam: those
# two exercises really do hand you a *different* list.h than sort_list's).
FT_LIST_H_CONTENT = """#ifndef FT_LIST_H
# define FT_LIST_H

typedef struct s_list
{
    struct s_list   *next;
    void            *data;
}   t_list;

#endif
"""

# For flood_fill: a 2D char grid + the t_point the real subject uses.
FLOOD_FILL_H_CONTENT = """#ifndef FLOOD_FILL_H
# define FLOOD_FILL_H

typedef struct s_point
{
    int x;
    int y;
}   t_point;

#endif
"""


class CFailure(object):
    __slots__ = ("index", "expected", "got")

    def __init__(self, index, expected, got):
        self.index, self.expected, self.got = index, expected, got

    def call(self, function):
        return "%s()  [case %d]" % (function, self.index)


# ══════════════════════════════════════════════════════════════
#  C LITERAL ENCODING
# ══════════════════════════════════════════════════════════════
def c_char_literal(ch):
    escapes = {"\\": "\\\\", "'": "\\'", "\n": "\\n", "\t": "\\t",
               "\r": "\\r", "\0": "\\0"}
    if ch in escapes:
        body = escapes[ch]
    elif 32 <= ord(ch) < 127:
        body = ch
    else:
        body = "\\x%02x" % ord(ch)
    return "'" + body + "'"


def c_string_literal(s):
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r"}
    out = ['"']
    for ch in s:
        if ch in escapes:
            out.append(escapes[ch])
        elif 32 <= ord(ch) < 127:
            out.append(ch)
        else:
            out.append("\\x%02x" % ord(ch))
    out.append('"')
    return "".join(out)


# ══════════════════════════════════════════════════════════════
#  HARNESS CODEGEN  ·  "function"-kind exercises only
# ══════════════════════════════════════════════════════════════
HARNESS_PREAMBLE = """#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
{header_include}
{helpers}
{prototype}
"""

# Spliced in only for the exercises that actually use each helper — an
# unused `static` helper is itself a compiler warning, and every OTHER
# exercise's grading run would otherwise show that as if it were the
# student's fault.
PRINT_INT_ARRAY_HELPER = """
static void print_int_array(int *a, int n)
{
    int i;

    for (i = 0; i < n; i++)
    {
        if (i)
            printf(" ");
        printf("%d", a[i]);
    }
    printf("\\n");
}
"""

LIST_HELPERS = """
static t_list *build_list(int *vals, int n)
{
    t_list *head;
    t_list *tail;
    t_list *node;
    int i;

    head = NULL;
    tail = NULL;
    i = 0;
    while (i < n)
    {
        node = malloc(sizeof(t_list));
        node->data = vals[i];
        node->next = NULL;
        if (!head)
            head = node;
        else
            tail->next = node;
        tail = node;
        i++;
    }
    return head;
}

static void print_list(t_list *list)
{
    while (list)
    {
        printf("%d ", list->data);
        list = list->next;
    }
    printf("\\n");
}
"""

PRINT_STR_ARRAY_HELPER = """
static void print_str_array(char **arr)
{
    int i;

    i = 0;
    while (arr && arr[i])
    {
        printf("%s|", arr[i]);
        i++;
    }
    printf("\\n");
}
"""

CMP_ASCENDING_HELPER = """
static int ascending(int a, int b)
{
    return (a <= b);
}
"""

# For ft_list_foreach / ft_list_remove_if — a "void *data" list boxing
# plain ints (each data is a malloc'd int*), plus the fixed callbacks the
# harness always tests with: `accumulate` sums every element's data (so a
# correct foreach visits each node exactly once, in order), `eq_ints`
# treats two ints as "equal" (matching the real subject's "cmp returns 0
# when the two are equal" contract).
VOIDLIST_HELPERS = """
static t_list *build_voidlist(int *vals, int n)
{
    t_list *head;
    t_list *tail;
    t_list *node;
    int *box;
    int i;

    head = NULL;
    tail = NULL;
    i = 0;
    while (i < n)
    {
        box = malloc(sizeof(int));
        *box = vals[i];
        node = malloc(sizeof(t_list));
        node->data = box;
        node->next = NULL;
        if (!head)
            head = node;
        else
            tail->next = node;
        tail = node;
        i++;
    }
    return head;
}

static void print_voidlist(t_list *list)
{
    while (list)
    {
        printf("%d ", *(int *)list->data);
        list = list->next;
    }
    printf("\\n");
}
"""

ACCUMULATE_HELPER = """
static int g_foreach_sum;

static void accumulate(void *data)
{
    g_foreach_sum += *(int *)data;
}
"""

EQ_INTS_HELPER = """
static int eq_ints(void *a, void *b)
{
    return (*(int *)a != *(int *)b);
}
"""

# For flood_fill — every row is its own mutable char[] (NOT a pointer to a
# string literal: those live in read-only memory and flood_fill has to
# write into them), collected into a char* array.
CHAR_GRID_HELPERS = """
static void print_char_grid(char **grid, int rows)
{
    int i;

    i = 0;
    while (i < rows)
    {
        printf("%s\\n", grid[i]);
        i++;
    }
}
"""


# Arg kinds that pass a fixed, hardcoded C identifier (a function pointer
# the harness itself defines) and consume no case value at all — so e.g. a
# case tuple for `["int_list", "cmp_ascending"]` only ever supplies one
# value. Kept as one set so both the codegen below and selftest's case/arg
# count check agree on which kinds don't consume a value.
FIXED_CALLBACK_KINDS = {
    "cmp_ascending": "ascending",
    "cmp_eq_ints": "eq_ints",
    "cb_accumulate": "accumulate",
}


def _emit_args(ex, args):
    """Build (decl lines, call-argument expressions, {arg_index: (kind, var)})."""
    decls, call_args, refs = [], [], {}
    ai = 0
    for i, kind in enumerate(ex["args"]):
        name = "arg%d" % i
        if kind in FIXED_CALLBACK_KINDS:
            call_args.append(FIXED_CALLBACK_KINDS[kind])
            continue
        value = args[ai]
        ai += 1
        if kind == "int":
            decls.append("int %s = %s;" % (name, int(value)))
            call_args.append(name)
        elif kind == "int_ptr":
            decls.append("int %s = %s;" % (name, int(value)))
            call_args.append("&" + name)
            refs[i] = ("int_ptr", name)
        elif kind == "char":
            decls.append("char %s = %s;" % (name, c_char_literal(value)))
            call_args.append(name)
        elif kind == "str":
            decls.append("char *%s = %s;" % (name, c_string_literal(value)))
            call_args.append(name)
        elif kind == "int_arr":
            cap = max(1, len(value))
            items = ", ".join(str(int(v)) for v in value) or "0"
            size_name = name + "_size"
            decls.append("int %s[%d] = {%s};" % (name, cap, items))
            decls.append("int %s = %d;" % (size_name, len(value)))
            call_args.append(name)
            call_args.append(size_name)
            refs[i] = ("int_arr", name)
        elif kind == "int_list":
            cap = max(1, len(value))
            items = ", ".join(str(int(v)) for v in value) or "0"
            vals_name = name + "_vals"
            decls.append("int %s[%d] = {%s};" % (vals_name, cap, items))
            decls.append("t_list *%s = build_list(%s, %d);"
                         % (name, vals_name, len(value)))
            call_args.append(name)
        elif kind == "buf":
            decls.append("char %s[128];" % name)
            decls.append("strcpy(%s, %s);" % (name, c_string_literal(value)))
            call_args.append(name)
        elif kind == "voidlist" or kind == "voidlist_ptr":
            cap = max(1, len(value))
            items = ", ".join(str(int(v)) for v in value) or "0"
            vals_name = name + "_vals"
            decls.append("int %s[%d] = {%s};" % (vals_name, cap, items))
            decls.append("t_list *%s = build_voidlist(%s, %d);"
                         % (name, vals_name, len(value)))
            call_args.append(("&" if kind == "voidlist_ptr" else "") + name)
            refs[i] = (kind, name)
        elif kind == "point":
            x, y = int(value[0]), int(value[1])
            decls.append("t_point %s = {%d, %d};" % (name, x, y))
            call_args.append(name)
        elif kind == "char_grid":
            row_names = []
            for r, row in enumerate(value):
                row_name = "%s_row%d" % (name, r)
                decls.append("char %s[] = %s;" % (row_name, c_string_literal(row)))
                row_names.append(row_name)
            decls.append("char *%s[] = {%s};" % (name, ", ".join(row_names)))
            call_args.append(name)
            refs[i] = ("char_grid", name, len(value))
        else:
            raise ValueError("unknown arg kind %r" % (kind,))
    return decls, call_args, refs


def render_call(ex, args, index=None):
    """One example call as a C block. Used both for the harness (with an
    index, so its output is delimited) and the stub's SELF_TEST snippet
    (without one — see examshell.make_stub). Only for "function"-kind
    exercises; "program"-kind ones have no call to render."""
    decls, call_args, refs = _emit_args(ex, args)
    lines = []
    if index is not None:
        lines.append('printf("' + CASE_DELIM + str(index) + '===\\n");')
    lines.extend(decls)
    call_expr = ex["function"] + "(" + ", ".join(call_args) + ")"
    returns = ex.get("returns", "void")
    if returns == "foreach_sum":
        lines.append("g_foreach_sum = 0;")
        lines.append(call_expr + ";")
        lines.append('printf("%d\\n", g_foreach_sum);')
    elif returns == "void":
        lines.append(call_expr + ";")
        for i in ex.get("print_after_args", ()):
            kind, name = refs[i][0], refs[i][1]
            if kind == "int_arr":
                lines.append("print_int_array(" + name + ", " + name + "_size);")
            elif kind == "int_ptr":
                lines.append('printf("%d\\n", ' + name + ");")
            elif kind == "voidlist_ptr":
                lines.append("print_voidlist(" + name + ");")
            elif kind == "char_grid":
                rows = refs[i][2]
                lines.append("print_char_grid(" + name + ", " + str(rows) + ");")
    elif returns == "int":
        lines.append("int ret = " + call_expr + ";")
        lines.append('printf("%d\\n", ret);')
    elif returns == "strcmp_sign":
        lines.append("int ret = " + call_expr + ";")
        lines.append('printf("%d\\n", (ret > 0) - (ret < 0));')
    elif returns == "str":
        lines.append("char *ret = " + call_expr + ";")
        lines.append('printf("%s\\n", ret ? ret : "(null)");')
    elif returns == "str_owned":
        lines.append("char *ret = " + call_expr + ";")
        lines.append('printf("%s\\n", ret ? ret : "(null)");')
        lines.append("free(ret);")
    elif returns == "str_array":
        lines.append("char **ret = " + call_expr + ";")
        lines.append("print_str_array(ret);")
    elif returns == "int_arr":
        # the length of a malloc'd returned array isn't observable from C
        # alone — the exercise supplies a `return_len(case_args)` callable
        # that computes it the same way the oracle itself does, so the
        # literal count can be baked into the generated call site.
        length = ex["return_len"](args)
        lines.append("int *ret = " + call_expr + ";")
        lines.append("print_int_array(ret, " + str(length) + ");")
        lines.append("free(ret);")
    elif returns == "int_list":
        lines.append("t_list *ret = " + call_expr + ";")
        lines.append("print_list(ret);")
    else:
        raise ValueError("unknown return kind %r" % (returns,))
    indented = "\n        ".join(lines)
    return "    {\n        " + indented + "\n    }"


def needs_list_h(ex):
    return "int_list" in ex.get("args", ()) or ex.get("returns") == "int_list"


def needs_ft_list_h(ex):
    return "voidlist" in ex.get("args", ()) or "voidlist_ptr" in ex.get("args", ())


def needs_flood_fill_h(ex):
    return "point" in ex.get("args", ()) or "char_grid" in ex.get("args", ())


def header_filename(ex):
    """Which shared header (if any) this exercise's args/return need."""
    if needs_list_h(ex):
        return "list.h"
    if needs_ft_list_h(ex):
        return "ft_list.h"
    if needs_flood_fill_h(ex):
        return "flood_fill.h"
    return None


def header_content(filename):
    return {"list.h": LIST_H_CONTENT, "ft_list.h": FT_LIST_H_CONTENT,
           "flood_fill.h": FLOOD_FILL_H_CONTENT}[filename]


def needed_helpers_c(ex):
    """The C source of every codegen helper (print_int_array, the t_list
    build/print pair, print_str_array, ascending, ...) this exercise's
    calls actually use — shared by generate_harness() (the grading
    harness) and examshell.make_stub()'s SELF_TEST block, so a stub that
    calls e.g. build_list() always has it defined, not just the real
    harness."""
    helpers = ""
    needs_array_printer = (("int_arr" in ex["args"] and ex.get("print_after_args"))
                           or ex.get("returns") == "int_arr")
    if needs_array_printer:
        helpers += PRINT_INT_ARRAY_HELPER
    if needs_list_h(ex):
        helpers += LIST_HELPERS
    if ex.get("returns") == "str_array":
        helpers += PRINT_STR_ARRAY_HELPER
    if "cmp_ascending" in ex["args"]:
        helpers += CMP_ASCENDING_HELPER
    if needs_ft_list_h(ex):
        helpers += VOIDLIST_HELPERS
    if ex.get("returns") == "foreach_sum":
        helpers += ACCUMULATE_HELPER
    if "cmp_eq_ints" in ex["args"]:
        helpers += EQ_INTS_HELPER
    if "char_grid" in ex["args"]:
        helpers += CHAR_GRID_HELPERS
    return helpers


def generate_harness(ex):
    """The full harness.c source: preamble + one main() looping every case."""
    blocks = "\n".join(render_call(ex, args, index=i)
                       for i, args in enumerate(ex["cases"]))
    header = header_filename(ex)
    header_include = '#include "%s"\n' % header if header else ""
    preamble = HARNESS_PREAMBLE.format(prototype=ex["prototype"],
                                       header_include=header_include,
                                       helpers=needed_helpers_c(ex))
    # stdout is a pipe when graded (never a TTY), so libc fully-buffers it —
    # printf()'s bytes would only flush at exit, landing *after* every raw
    # write() the student's own function makes and scrambling case order.
    # Unbuffering keeps printf and write interleaved in true call order.
    setup = "    setvbuf(stdout, NULL, _IONBF, 0);\n"
    return preamble + "\nint main(void)\n{\n" + setup + blocks + "\n    return 0;\n}\n"


# ══════════════════════════════════════════════════════════════
#  STATIC CHECKS  ·  forbidden calls (both kinds)
# ══════════════════════════════════════════════════════════════
def _strip_comments_and_strings(src):
    """Best-effort scrub of comments and string/char literal contents, so a
    banned word inside a comment or a string doesn't false-positive. Not a
    real C parser — good enough for a lint-style scan, same spirit as the
    Python tool's ast-based `find_imports` but C has no stdlib parser."""
    out, i, n = [], 0, len(src)
    while i < n:
        two = src[i:i + 2]
        if two == "/*":
            end = src.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif two == "//":
            end = src.find("\n", i)
            i = n if end == -1 else end
        elif src[i] in "\"'":
            quote = src[i]
            j = i + 1
            while j < n and src[j] != quote:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def _is_duplicate_main(link_error):
    """True for the linker error a student's own (unguarded) main() causes
    when it collides with the harness's — covers both ld64 ("duplicate
    symbol '_main'") and GNU ld ("multiple definition of `main'"). Only
    relevant to "function"-kind grading — "program"-kind exercises expect
    (and require) the student to define main()."""
    low = link_error.lower()
    return "main" in low and ("duplicate symbol" in low or "multiple definition" in low)


def find_forbidden(stripped_src, forbidden_names):
    found = []
    for name in forbidden_names:
        if re.search(r"\b" + re.escape(name) + r"\s*\(", stripped_src):
            found.append(name)
    return found


# ══════════════════════════════════════════════════════════════
#  COMPILE  ·  RUN
# ══════════════════════════════════════════════════════════════
def compile_c(sources, output, cc=DEFAULT_CC, extra_flags=(), include_dirs=()):
    cmd = [cc, "-Wall", "-Wextra"]
    for d in include_dirs:
        cmd += ["-I", d]
    cmd += list(extra_flags) + list(sources) + ["-o", output]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=COMPILE_TIMEOUT, text=True)
    except subprocess.TimeoutExpired:
        return False, "compiler timed out after %ds" % COMPILE_TIMEOUT
    return proc.returncode == 0, proc.stderr


def run_bin(path, timeout=DEFAULT_TIMEOUT, argv=None):
    """Returns (stdout, crash_note). crash_note is None on a clean exit."""
    cmd = [path] + list(argv or ())
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, text=True, errors="replace")
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    if proc.returncode < 0:
        try:
            name = signal.Signals(-proc.returncode).name
        except ValueError:
            name = "signal %d" % (-proc.returncode)
        return proc.stdout, "CRASHED:" + name
    return proc.stdout, None


def split_cases(output):
    """{case_index: chunk_text} parsed from a harness run's stdout."""
    matches = list(_CASE_RE.finditer(output))
    chunks = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        chunks[int(m.group(1))] = output[start:end]
    return chunks


# ══════════════════════════════════════════════════════════════
#  GRADE
# ══════════════════════════════════════════════════════════════
def grade(ex_name, ex, rendu_dir, cc=DEFAULT_CC, timeout=DEFAULT_TIMEOUT,
          strict_norm=False, filepath=None):
    if ex.get("kind") == "program":
        return _grade_program(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath)
    return _grade_function(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath)


def _grade_function(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath):
    report = Report(ex_name, ex["function"])
    path = filepath or os.path.join(rendu_dir, ex_name + ".c")
    started = time.time()

    if not os.path.isfile(path):
        return report.fail("FILE_MISSING", "expected your solution at %s" % path)

    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    stripped = _strip_comments_and_strings(raw)

    # No static "does this file contain main(" pre-check: the stub ships an
    # example main() guarded by `#ifdef SELF_TEST`, which a text scan can't
    # tell apart from a real, unguarded one — the preprocessor can. Instead,
    # a genuine unguarded main() is left to the real compiler: it collides
    # with the harness's own main() at link time (see the duplicate-symbol
    # detection below), which is both correct and simpler.
    forbidden = find_forbidden(stripped, ex.get("forbidden", ()))
    if forbidden:
        report.warnings.append(
            "forbidden call found for this exercise: %s" % ", ".join(forbidden))

    workdir = tempfile.mkdtemp(prefix="c-exam-")
    try:
        include_dirs = []
        header = header_filename(ex)
        if header:
            with open(os.path.join(workdir, header), "w", encoding="utf-8") as fh:
                fh.write(header_content(header))
            include_dirs.append(workdir)

        harness_path = os.path.join(workdir, "harness.c")
        with open(harness_path, "w", encoding="utf-8") as fh:
            fh.write(generate_harness(ex))

        oracle_path = os.path.join(workdir, "oracle.c")
        with open(oracle_path, "w", encoding="utf-8") as fh:
            fh.write(ex["oracle_c"])

        ref_bin = os.path.join(workdir, "ref")
        ok, err = compile_c([oracle_path, harness_path], ref_bin, cc,
                            include_dirs=include_dirs)
        if not ok:
            raise BankError("%s: reference implementation fails to compile:\n%s"
                            % (ex_name, err[:800]))

        student_bin = os.path.join(workdir, "student")
        extra = ["-Werror"] if strict_norm else []
        ok, err = compile_c([path, harness_path], student_bin, cc,
                            extra_flags=extra, include_dirs=include_dirs)
        if not ok:
            if _is_duplicate_main(err):
                return report.fail(
                    "FORBIDDEN_MAIN",
                    "define only %s() — the tester supplies its own main()"
                    % ex["function"])
            return report.fail("COMPILE_ERROR", err[:800])
        if err.strip():
            report.warnings.append(
                "compiler warning (fix it — the real exam compiles with "
                "-Wall -Wextra too; --strict-norm makes this fatal):\n" + err[:500])

        ref_out, ref_crash = run_bin(ref_bin, timeout)
        if ref_crash:
            raise BankError("%s: reference binary %s" % (ex_name, ref_crash))

        stu_out, stu_crash = run_bin(student_bin, timeout)
        report.duration = time.time() - started

        if stu_crash == "TIMEOUT":
            return report.fail("TIMEOUT", "no result after %ds — infinite loop?" % timeout)
        if stu_crash:
            report.warnings.append("your program crashed: " + stu_crash.split(":", 1)[1])

        n = len(ex["cases"])
        ref_chunks = split_cases(ref_out)
        stu_chunks = split_cases(stu_out)
        report.total = n
        for i in range(n):
            expected = ref_chunks.get(i, "")
            got = stu_chunks.get(i, "[no output — crashed or exited early?]")
            if got == expected:
                report.passed += 1
            else:
                # comparison above is on the raw chunks (exactness matters
                # for void-printing exercises); only the *display* strips
                # the harness's own trailing newline, so ui.py's failure
                # list doesn't grow a stray blank line per entry.
                report.failures.append(
                    CFailure(i, expected.rstrip("\n"), got.rstrip("\n")))
        return report
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _grade_program(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath):
    """"program"-kind exercises: the student's file compiles ALONE (it IS
    the main()), and is run once per case with that case's argv."""
    report = Report(ex_name, ex["function"])
    path = filepath or os.path.join(rendu_dir, ex_name + ".c")
    started = time.time()

    if not os.path.isfile(path):
        return report.fail("FILE_MISSING", "expected your solution at %s" % path)

    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    stripped = _strip_comments_and_strings(raw)
    forbidden = find_forbidden(stripped, ex.get("forbidden", ()))
    if forbidden:
        report.warnings.append(
            "forbidden call found for this exercise: %s" % ", ".join(forbidden))

    workdir = tempfile.mkdtemp(prefix="c-exam-")
    try:
        oracle_path = os.path.join(workdir, "oracle.c")
        with open(oracle_path, "w", encoding="utf-8") as fh:
            fh.write(ex["oracle_c"])

        ref_bin = os.path.join(workdir, "ref")
        ok, err = compile_c([oracle_path], ref_bin, cc)
        if not ok:
            raise BankError("%s: reference program fails to compile:\n%s"
                            % (ex_name, err[:800]))

        student_bin = os.path.join(workdir, "student")
        extra = ["-Werror"] if strict_norm else []
        ok, err = compile_c([path], student_bin, cc, extra_flags=extra)
        if not ok:
            return report.fail("COMPILE_ERROR", err[:800])
        if err.strip():
            report.warnings.append(
                "compiler warning (fix it — the real exam compiles with "
                "-Wall -Wextra too; --strict-norm makes this fatal):\n" + err[:500])

        cases = ex["cases"]
        report.total = len(cases)
        for i, argv in enumerate(cases):
            ref_out, ref_crash = run_bin(ref_bin, timeout, argv=argv)
            if ref_crash:
                raise BankError("%s: reference program %s on case %d"
                                % (ex_name, ref_crash, i))
            stu_out, stu_crash = run_bin(student_bin, timeout, argv=argv)
            if stu_crash:
                note = stu_crash.split(":", 1)[-1]
                report.warnings.append("case %d %s: %s"
                                       % (i, "timed out" if stu_crash == "TIMEOUT"
                                          else "crashed", note))
                report.failures.append(CFailure(i, ref_out.rstrip("\n"),
                                                "[%s]" % note))
                continue
            if stu_out == ref_out:
                report.passed += 1
            else:
                report.failures.append(
                    CFailure(i, ref_out.rstrip("\n"), stu_out.rstrip("\n")))
        report.duration = time.time() - started
        return report
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
#  BANK SELF-TEST  (make c-check)
# ══════════════════════════════════════════════════════════════
def selftest(exercises, groups, cc=DEFAULT_CC, timeout=DEFAULT_TIMEOUT, log=print):
    """Validate the whole C bank. Returns the number of problems found."""
    problems = 0

    def bad(msg):
        nonlocal problems
        problems += 1
        log("  FAIL  " + msg)

    for group, pool in groups.items():
        if not pool:
            bad("group %r has no exercise" % (group,))

    workdir = tempfile.mkdtemp(prefix="c-exam-check-")
    try:
        for name in sorted(exercises):
            ex = exercises[name]
            kind = ex.get("kind", "function")

            if name not in ex["subject"]:
                bad("%s: subject does not mention the exercise name" % name)
            if kind == "function":
                for args in ex["cases"]:
                    want = sum(1 for k in ex["args"] if k not in FIXED_CALLBACK_KINDS)
                    if len(args) != want:
                        bad("%s: a case has %d value(s), expected %d "
                            "(matching 'args')" % (name, len(args), want))
                        break
                try:
                    generate_harness(ex)   # must not crash — grade() regenerates it
                except Exception as exc:
                    bad("%s: harness codegen crashed (%s: %s)"
                        % (name, type(exc).__name__, exc))
                    continue

            path = os.path.join(workdir, name + ".c")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(ex["oracle_c"])

            report = grade(name, ex, workdir, cc=cc, timeout=timeout, filepath=path)
            if report.fatal:
                bad("%s: %s (%s)" % (name, report.fatal, report.detail))
                continue
            if not report.ok:
                bad("%s: oracle fails its own %s, e.g. case %d"
                    % (name, "harness" if kind == "function" else "run",
                       report.failures[0].index))
                continue
            log("  ok    %-32s %3d tests" % (name, report.total))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return problems
