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
which one applies per exercise. `Report` is reused as-is from
`examshell/grader.py` (plain bookkeeping, no Python-specific logic). A bank/
codegen bug (the reference itself fails to compile or crashes) is
reported as a "BANK_ERROR" fatal Report rather than raised — a raw
exception would crash a student's interactive session, and fuzzing
(below) makes that path reachable even for exercises whose curated
cases always compiled cleanly.
`CFailure` here plays the role `Failure` plays there, keyed by case index
instead of call arguments.
"""

import os
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
import time

from examshell.grader import MAX_TIMEOUTS, Report

DEFAULT_TIMEOUT = 5        # seconds per case (program mode) / per whole run (function mode)
DEFAULT_CC = "cc"
COMPILE_TIMEOUT = 20       # seconds for a single compiler invocation
DEFAULT_FUZZ = 8           # random extra cases per exercise (function-kind, safe args only)

# valgrind isn't available at all on Apple Silicon macOS — this is squarely
# a "real 42 school machine" (Linux) feature. Off by default, opt-in via
# --valgrind, and a no-op with a clear note when the binary isn't on PATH
# (same best-effort posture as --cc pointing at a missing compiler).
VALGRIND_TIMEOUT_MULT = 5     # valgrind runs much slower than the bare binary
VALGRIND_ERROR_EXITCODE = 99

# Every line valgrind itself writes (an error, a leak record, ...) is
# prefixed "==<pid>==" — see run_valgrind()'s use of this to tell a real
# finding apart from the traced program's own exit code coincidentally
# matching VALGRIND_ERROR_EXITCODE.
_VALGRIND_REPORT_RE = re.compile(r"(?m)^==\d+==")

CASE_DELIM = "===CASE "
_CASE_RE = re.compile(r"===CASE (\d+)===\n")

# `int (*cmp)()` compiles under Apple Clang's default standard, but not
# under GCC's C23 default: () there now means "takes no parameters" (same
# as (void)), not "unspecified parameters" like every older C standard —
# so a real call with real arguments fails to compile. selftest() below
# scans every bank prototype for this so a second compiler isn't needed
# to catch it (see also c_exam/grader.py's DEFAULT_CC / --cc).
_KR_FUNC_PTR_RE = re.compile(r"\(\*\w+\)\(\s*\)")

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


def shell_arg(arg):
    """`arg` quoted so the whole command can be pasted into bash as-is —
    $'...' when it holds a tab/newline (they'd be invisible otherwise)."""
    if any(ch in arg for ch in "\t\n\r"):
        escaped = (arg.replace("\\", "\\\\").replace("'", "\\'")
                   .replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r"))
        return "$'" + escaped + "'"
    return shlex.quote(arg)


class CFailure(object):
    __slots__ = ("index", "expected", "got", "args", "program")

    def __init__(self, index, expected, got, args=None, program=False):
        self.index, self.expected, self.got = index, expected, got
        # The case's own inputs — call values for a "function"-kind
        # exercise, argv for a "program"-kind one — so the report shows
        # exactly what to rerun (and examshell/case_labels.py can name its edge
        # case). None only for callers that don't know them.
        self.args, self.program = args, program

    def call(self, function):
        if self.args is None:
            return "%s()  [case %d]" % (function, self.index)
        if self.program:
            return " ".join(["./" + function] + [shell_arg(a) for a in self.args])
        return "%s(%s)" % (function, ", ".join(repr(a) for a in self.args))


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

# Split by what actually calls each one (see needed_helpers_c) — an
# exercise that only ever takes an int_list ARG (e.g. ft_list_size) never
# calls print_list, and one that only ever RETURNS an int_list would never
# call build_list; bundling all three unconditionally would leave one
# `static` unused and that's a compiler warning of the harness's own
# making, shown to the student as if it were their fault.
LIST_BUILD_HELPER = """
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
"""

LIST_PRINT_HELPER = """
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

LIST_FREE_HELPER = """
static void free_list(t_list *list)
{
    t_list *next;

    while (list)
    {
        next = list->next;
        free(list);
        list = next;
    }
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

static void free_str_array(char **arr)
{
    int i;

    i = 0;
    while (arr && arr[i])
        free(arr[i++]);
    free(arr);
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
# Split the same way as LIST_*_HELPER above (see the comment there) —
# print_voidlist in particular is only ever called for ft_list_remove_if
# (the one voidlist_ptr exercise with a print_after_args entry);
# ft_list_foreach never prints its list at all, so bundling it
# unconditionally would leave it unused there.
VOIDLIST_BUILD_HELPER = """
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
"""

VOIDLIST_PRINT_HELPER = """
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

VOIDLIST_FREE_HELPER = """
static void free_voidlist(t_list *list)
{
    t_list *next;

    while (list)
    {
        next = list->next;
        free(list->data);
        free(list);
        list = next;
    }
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


# ══════════════════════════════════════════════════════════════
#  FUZZING  ·  "function"-kind exercises with only "safe" arg kinds
# ══════════════════════════════════════════════════════════════
# Deliberately conservative compared to the Python tool's fuzzers (one
# hand-written generator per exercise there, free to respect that
# exercise's own preconditions). C has no oracle-only in-process check —
# a bad fuzzed value can only be caught by actually compiling and
# running it, and a value the oracle doesn't expect can trigger real
# undefined behaviour identically in both the oracle and a correct
# student solution (a false failure neither side can be "blamed" for).
# So only arg kinds with no exercise-specific precondition get random
# values; an exercise using any other kind (voidlist, point, char_grid,
# a fixed callback with its own contract, ...) is graded on its curated
# cases only, same as before this existed. "program"-kind exercises get
# their own shape-based argv fuzzing instead (see ARGV_SHAPES below).
FUZZABLE_VALUE_KINDS = {"int", "int_ptr", "char", "str", "int_arr", "int_list", "buf"}

_FUZZ_STR_ALPHABET = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                      "0123456789 _-.")


def _fuzz_str(rng, max_len):
    return "".join(rng.choice(_FUZZ_STR_ALPHABET) for _ in range(rng.randint(0, max_len)))


def _fuzz_value(kind, rng):
    """One random value for a single "safe" arg kind (see FUZZABLE_VALUE_KINDS)."""
    if kind in ("int", "int_ptr"):
        return rng.randint(-1000, 1000)
    if kind == "char":
        return chr(rng.randint(32, 126))
    if kind == "str":
        return _fuzz_str(rng, 16)
    if kind in ("int_arr", "int_list"):
        return [rng.randint(-50, 50) for _ in range(rng.randint(0, 6))]
    if kind == "buf":
        # the harness declares a fixed `char name[128];` for this kind —
        # stay well under it so a correct solution never legitimately
        # overflows the very buffer the harness itself provides.
        return _fuzz_str(rng, 40)
    raise ValueError("kind %r has no fuzz generator" % (kind,))  # pragma: no cover


# ── argv fuzzing  ·  "program"-kind exercises ─────────────────────────
# A program's argv can't be randomised generically (the module docstring
# above), but most of them fall into a handful of SHAPES — "one sentence",
# "two strings", "a positive number", ... A bank entry opts in with
# `"fuzz_argv": "<shape>"`; the generators below produce exactly the
# inputs people fail real exams on: runs of spaces AND tabs, leading and
# trailing whitespace, empty strings, punctuation, and the wrong argc.
# Every generator stays inside the subject's own preconditions (a positive
# number where the subject promises one, ...) — the reference program
# defines the expected output for everything else it's handed.
_WORD_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_PUNCT = ".,;:!?'-_()"
_BLANKS = (" ", "  ", "\t", " \t ", "   ")


def _fuzz_word(rng, max_len=8, punct=True):
    chars = _WORD_CHARS + (_PUNCT if punct else "")
    return "".join(rng.choice(chars) for _ in range(rng.randint(1, max_len)))


def _fuzz_sentence(rng):
    """Words separated by random runs of spaces/tabs, sometimes with
    leading/trailing blanks, sometimes empty or blank-only."""
    roll = rng.random()
    if roll < 0.07:
        return ""
    if roll < 0.14:
        return "".join(rng.choice(_BLANKS) for _ in range(rng.randint(1, 3)))
    words = [_fuzz_word(rng) for _ in range(rng.randint(1, 6))]
    text = "".join(w + rng.choice(_BLANKS) for w in words[:-1]) + words[-1]
    if rng.random() < 0.4:
        text = rng.choice(_BLANKS) + text
    if rng.random() < 0.4:
        text += rng.choice(_BLANKS)
    return text


def _fuzz_small_alphabet(rng, max_len=12):
    """A string over a tiny alphabet, so two of them actually overlap
    (union/inter) and repeat characters (the 'no doubles' traps)."""
    return "".join(rng.choice("abcdeAB12 ") for _ in range(rng.randint(0, max_len)))


def _fuzz_subsequence_pair(rng):
    """(s1, s2) where s1 is hidden in s2 in order about half the time."""
    s1 = _fuzz_word(rng, 5, punct=False)
    noise = [_fuzz_word(rng, 3, punct=False) for _ in range(len(s1) + 1)]
    if rng.random() < 0.5:
        s2 = "".join(n + c for n, c in zip(noise, s1)) + noise[-1]
    else:
        s2 = "".join(noise)
    return [s1, s2]


def _fuzz_camel(rng):
    words = ["".join(rng.choice("abcdefghijklmnopqrstuvwxyz")
                     for _ in range(rng.randint(1, 5))) for _ in range(rng.randint(1, 4))]
    return words[0] + "".join(w.capitalize() for w in words[1:])


def _fuzz_snake(rng):
    return "_".join("".join(rng.choice("abcdefghijklmnopqrstuvwxyz")
                            for _ in range(rng.randint(1, 5)))
                    for _ in range(rng.randint(1, 4)))


def _fuzz_do_op(rng):
    op = rng.choice("+-*/%")
    left = rng.randint(-1000, 1000)
    right = rng.randint(-1000, 1000)
    if op in "/%" and right == 0:
        right = rng.choice((-7, 3, 5))     # the subject never divides by 0
    return [str(left), op, str(right)]


def _fuzz_search_and_replace(rng):
    text = _fuzz_sentence(rng)
    pool = [c for c in text if c not in " \t"] or ["a"]
    search = rng.choice(pool) if rng.random() < 0.8 else rng.choice(_WORD_CHARS)
    replace = rng.choice(_WORD_CHARS + _PUNCT)
    if rng.random() < 0.15:                # not a single character -> "\n"
        replace += rng.choice(_WORD_CHARS)
    return [text, search, replace]


# shape -> (generator for the RIGHT argv, how many args that is)
ARGV_SHAPES = {
    "sentence": (lambda rng: [_fuzz_sentence(rng)], 1),
    "sentences": (lambda rng: [_fuzz_sentence(rng) for _ in range(rng.randint(1, 3))], None),
    "two_strings": (lambda rng: [_fuzz_small_alphabet(rng), _fuzz_small_alphabet(rng)], 2),
    "subsequence": (_fuzz_subsequence_pair, 2),
    "camel": (lambda rng: [_fuzz_camel(rng)], 1),
    "snake": (lambda rng: [_fuzz_snake(rng)], 1),
    "positive_int": (lambda rng: [str(rng.randint(1, 100000))], 1),
    "non_negative_int": (lambda rng: [str(rng.randint(0, 1 << 20))], 1),
    "small_positive_int": (lambda rng: [str(rng.randint(1, 3000))], 1),
    "two_positive_ints": (lambda rng: [str(rng.randint(1, 10000)),
                                       str(rng.randint(1, 10000))], 2),
    "do_op": (_fuzz_do_op, 3),
    "search_and_replace": (_fuzz_search_and_replace, 3),
    "any_args": (lambda rng: [_fuzz_word(rng) for _ in range(rng.randint(0, 12))], None),
}


def fuzz_argv(shape, rng):
    """One random argv for `shape` — about 1 in 10 has the wrong argc
    (none at all, or one too many), the case every subject specifies and
    many solutions forget."""
    make, argc = ARGV_SHAPES[shape]
    argv = make(rng)
    if argc is not None and rng.random() < 0.1:
        argv = [] if rng.random() < 0.5 else argv + [_fuzz_word(rng)]
    return argv


# ── whole-case fuzzing · "function"-kind exercises with structured args ─
# Linked lists of boxed ints, a char grid plus two points, … can't be
# randomised one arg at a time (the args depend on each other: the start
# point must lie on the grid, data_ref should usually match some element).
# These exercises opt in with `"fuzz_cases": "<name>"` and get a generator
# for WHOLE cases, aimed at the classic bugs of that exercise.
def _fuzz_foreach_case(rng):
    """ft_list_foreach: empty, single, long, negative, zeros."""
    roll = rng.random()
    if roll < 0.15:
        return [[]]
    if roll < 0.3:
        return [[rng.randint(-50, 50)]]
    return [[rng.randint(-50, 50) for _ in range(rng.randint(2, 9))]]


def _fuzz_remove_if_case(rng):
    """ft_list_remove_if: matches at the head (the head pointer must move),
    at the tail, back to back, everywhere, nowhere — and the empty list."""
    pool = [1, 2, 3]
    values = [rng.choice(pool) for _ in range(rng.randint(0, 8))]
    roll = rng.random()
    if roll < 0.15 or not values:
        ref = rng.choice(pool + [9])
    elif roll < 0.35:
        ref = values[0]                                     # head matches
    elif roll < 0.5:
        ref = values[-1]                                    # tail matches
    elif roll < 0.65:
        ref = values[0]
        values = [ref] * len(values)                        # every node goes
    elif roll < 0.8:
        ref = 9                                             # nothing matches
    else:
        ref = rng.choice(values)
    return [values, ref]


def _fuzz_flood_fill_case(rng):
    """flood_fill: random 1-6 x 1-6 grids of 2-3 symbols, starting in a
    corner, on an edge or anywhere — sometimes on a 1-cell island, rarely
    off the grid (curated cases already pin that down)."""
    width, height = rng.randint(1, 6), rng.randint(1, 6)
    symbols = rng.choice(("01", "012", "0"))
    grid = ["".join(rng.choice(symbols) for _ in range(width)) for _ in range(height)]
    roll = rng.random()
    if roll < 0.3:
        begin = (rng.choice((0, width - 1)), rng.choice((0, height - 1)))   # corner
    elif roll < 0.5:
        begin = (rng.randint(0, width - 1), rng.choice((0, height - 1)))    # edge
    elif roll < 0.95:
        begin = (rng.randint(0, width - 1), rng.randint(0, height - 1))
    else:
        begin = (width + rng.randint(0, 2), height + rng.randint(0, 2))     # off the grid
    return [grid, (width, height), begin]


def _fuzz_atoi_base_case(rng):
    """ft_atoi_base: a base the subject allows (2-16) and a number that fits
    in an int, written in that base in mixed case — sometimes negative,
    sometimes cut short by a digit too big for the base, a stray '-'/'+' or
    a space. Never a LEADING '+' or space: the subject doesn't say, and a
    student reusing their ft_atoi rightly skips them. (The generic fuzzer would pass bases like 558 or -17 and
    overflow the result: behaviour the subject never defines.)"""
    base = rng.randint(2, 16)
    value = rng.choice((rng.randint(0, base ** 3), rng.randint(0, 2 ** 31 - 1)))
    digits = ""
    while True:
        digits = "0123456789abcdef"[value % base] + digits
        value //= base
        if not value:
            break
    digits = "".join(c.upper() if rng.random() < 0.5 else c for c in digits)
    if rng.random() < 0.4:
        digits = "-" + digits
    roll = rng.random()
    if roll < 0.3:
        cut = rng.randint(1, len(digits))
        bad = rng.choice(["-", "+", " ", "g", "z"] + (["0123456789abcdef"[base]] if base < 16 else []))
        digits = digits[:cut] + bad + digits[cut:]
    elif roll < 0.35:
        digits = rng.choice(("", "-", "--1"))
    return [digits, base]


CASE_FUZZERS = {
    "atoi_base": _fuzz_atoi_base_case,
    "list_foreach": _fuzz_foreach_case,
    "list_remove_if": _fuzz_remove_if_case,
    "flood_fill": _fuzz_flood_fill_case,
}


def is_fuzzable(ex):
    """True when this exercise can get random extra cases: every arg of a
    "function"-kind exercise is safe to randomise, it names a whole-case
    generator (see CASE_FUZZERS), or a "program"-kind one names its argv
    shape (see ARGV_SHAPES)."""
    if ex.get("kind") == "program":
        return ex.get("fuzz_argv") in ARGV_SHAPES
    if ex.get("fuzz_cases") in CASE_FUZZERS:
        return True
    return all(k in FUZZABLE_VALUE_KINDS or k in FIXED_CALLBACK_KINDS
               for k in ex.get("args", ()))


def build_fuzz_cases(ex, rng, n):
    """`n` extra random case tuples, shaped exactly like a hand-curated
    entry in ex["cases"] (one value per arg, fixed-callback args skipped —
    they consume no case value, see FIXED_CALLBACK_KINDS)."""
    if ex.get("fuzz_cases") in CASE_FUZZERS:
        make = CASE_FUZZERS[ex["fuzz_cases"]]
        return [make(rng) for _ in range(n)]
    kinds = [k for k in ex["args"] if k not in FIXED_CALLBACK_KINDS]
    return [[_fuzz_value(k, rng) for k in kinds] for _ in range(n)]


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
            refs[i] = ("int_list", name)
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
        lines.append("free_str_array(ret);")
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
        lines.append("free_list(ret);")
    else:
        raise ValueError("unknown return kind %r" % (returns,))
    # The harness builds test fixtures (a linked list, a void*-boxed list)
    # for int_list/voidlist(_ptr) args itself, so it must free them itself
    # too — otherwise every grading run leaks by construction, regardless
    # of the student's own code (see the valgrind leak-check CI job). An
    # int_list ARG is skipped when the return is also "int_list": every
    # bank exercise shaped that way (sort_list) sorts in place and hands
    # back the same nodes, so free_list(ret) above already released them
    # — freeing the arg's own local variable too would double-free.
    for ref in refs.values():
        kind, name = ref[0], ref[1]
        if kind == "int_list" and returns != "int_list":
            lines.append("free_list(%s);" % name)
        elif kind in ("voidlist", "voidlist_ptr"):
            lines.append("free_voidlist(%s);" % name)
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
    if "int_list" in ex.get("args", ()):
        helpers += LIST_BUILD_HELPER
    if ex.get("returns") == "int_list":
        helpers += LIST_PRINT_HELPER
    if needs_list_h(ex):
        helpers += LIST_FREE_HELPER
    if ex.get("returns") == "str_array":
        helpers += PRINT_STR_ARRAY_HELPER
    if "cmp_ascending" in ex["args"]:
        helpers += CMP_ASCENDING_HELPER
    if needs_ft_list_h(ex):
        helpers += VOIDLIST_BUILD_HELPER + VOIDLIST_FREE_HELPER
    print_after = ex.get("print_after_args", ())
    if any(ex["args"][i] in ("voidlist", "voidlist_ptr") for i in print_after):
        helpers += VOIDLIST_PRINT_HELPER
    if ex.get("returns") == "foreach_sum":
        helpers += ACCUMULATE_HELPER
    if "cmp_eq_ints" in ex["args"]:
        helpers += EQ_INTS_HELPER
    if "char_grid" in ex["args"]:
        helpers += CHAR_GRID_HELPERS
    return helpers


def generate_harness(ex, cases=None):
    """The full harness.c source: preamble + one main() looping every case.

    `cases` defaults to ex["cases"]; grade() passes curated + fuzz cases
    combined so the harness that gets compiled matches what was announced.
    """
    if cases is None:
        cases = ex["cases"]
    blocks = "\n".join(render_call(ex, args, index=i)
                       for i, args in enumerate(cases))
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


def _is_undeclared_null(compile_error):
    """True when the student used NULL without including a header that
    defines it — their file is its own translation unit, so the harness's
    #includes don't reach it. clang: "undeclared identifier 'NULL'", gcc:
    "'NULL' undeclared"."""
    return bool(re.search(r"undeclared identifier '?NULL'?|'NULL' undeclared",
                          compile_error))


NULL_HINT = ("NULL isn't defined in your file — add #include <stddef.h> "
             "(or <stdlib.h> / <unistd.h>), or return (0) instead. Your file "
             "is compiled on its own, like in the real exam.\n\n")


def _compile_error_detail(compile_error):
    """The COMPILE_ERROR detail: the compiler's output (truncated), with a
    plain-language hint in front for the common mistakes."""
    hint = NULL_HINT if _is_undeclared_null(compile_error) else ""
    return hint + compile_error[:800]


def find_forbidden(stripped_src, forbidden_names):
    found = []
    for name in forbidden_names:
        if re.search(r"\b" + re.escape(name) + r"\s*\(", stripped_src):
            found.append(name)
    return found


# ══════════════════════════════════════════════════════════════
#  STATIC CHECK  ·  source display (--diff's inline code panel)
# ══════════════════════════════════════════════════════════════
_SIG_START_RE_TEMPLATE = r"(?m)^[^\n{}]*\b%s\s*\("


def _real_chars(src):
    """Yield (original_index, char) for every character of `src` that is
    NOT inside a comment or a string/char literal — same skip rules as
    _strip_comments_and_strings(), but yielding ORIGINAL offsets instead
    of building a stripped copy, so a caller can locate a token safely
    (ignoring a stray '{'/'(' inside a string or comment) and then slice
    the UNTOUCHED original text once it knows where that token really is."""
    i, n = 0, len(src)
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
            yield i, src[i]
            i += 1


def extract_function_source(filepath, function_name):
    """Best-effort brace-matching extraction of one function's definition
    from the student's C file, for --diff's inline code panel — with the
    student's ORIGINAL formatting, comments and string literals intact
    (via _real_chars() above), not a stripped approximation: this is
    shown back to the student as "your own code", and a printf() whose
    string argument silently vanished would look like the tool is
    broken, not like a deliberate simplification.

    There's no C parser available here (see _strip_comments_and_strings()'s
    own docstring for the same trade-off this project already accepts
    elsewhere), so this scans a comment/string-free VIEW of the source for
    '<something> function_name(' at the start of a line, then counts
    braces the same comment/string-safe way — but every position used to
    slice the final result maps back to the real, original source.

    Returns None on any failure (file unreadable, function not found,
    unbalanced braces) — must never be able to crash grading.
    """
    try:
        with open(filepath, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return None
    real = list(_real_chars(src))
    filtered = "".join(ch for _, ch in real)
    sig_re = re.compile(_SIG_START_RE_TEMPLATE % re.escape(function_name))
    m = sig_re.search(filtered)
    if not m:
        return None
    sig_start = real[m.start()][0]
    # Resume the same real-char scan right after the signature match to
    # find the function's opening brace, then count depth from there —
    # both steps skip string/comment content via _real_chars(), and both
    # report positions in the ORIGINAL source.
    tail = [(i, ch) for i, ch in real if i >= real[m.end() - 1][0]]
    depth = 0
    body_start = None
    for i, ch in tail:
        if ch == "{":
            if body_start is None:
                body_start = i
            depth += 1
        elif ch == "}" and body_start is not None:
            depth -= 1
            if depth == 0:
                return src[sig_start:i + 1].strip()
    return None


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


def have_valgrind():
    return shutil.which("valgrind") is not None


def run_valgrind(path, timeout=DEFAULT_TIMEOUT, argv=None):
    """Run `path` under valgrind's full leak checker.

    Returns (clean, detail): clean is True when valgrind reported zero
    errors (leaks included — --errors-for-leak-kinds=all makes a leak
    count as an "error" the same as an invalid read/write would), detail
    is a truncated excerpt of valgrind's own report ("" when clean).
    Never raises — a valgrind-side problem (timeout) is reported through
    `detail` like any other finding, not as an exception.
    """
    cmd = ["valgrind", "--leak-check=full", "--show-leak-kinds=all",
           "--errors-for-leak-kinds=all",
           "--error-exitcode=%d" % VALGRIND_ERROR_EXITCODE, "-q",
           path] + list(argv or ())
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout * VALGRIND_TIMEOUT_MULT,
                              text=True, errors="replace")
    except subprocess.TimeoutExpired:
        return False, "valgrind timed out — the program may just be slow " \
                      "under instrumentation, not necessarily an infinite loop"
    # --error-exitcode only overrides the exit code when valgrind ITSELF
    # found an error; a clean run passes the TRACED PROGRAM's own exit
    # code straight through, which can coincidentally equal
    # VALGRIND_ERROR_EXITCODE (e.g. a program-kind exercise whose correct
    # solution legitimately exits(99)) and would otherwise misreport a
    # clean run as leaky. Valgrind always prefixes every one of its own
    # findings with "==<pid>==", even under -q (which only silences its
    # startup/summary banners, never an actual finding) — checking for
    # that is what actually tells "valgrind found something" apart from
    # "the program's own exit code happened to match".
    if proc.returncode == VALGRIND_ERROR_EXITCODE and _VALGRIND_REPORT_RE.search(proc.stderr):
        return False, proc.stderr[:800]
    return True, ""


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
          strict_norm=False, filepath=None, rng=None, fuzz=0,
          valgrind=False, strict_valgrind=False, strict_forbidden=False):
    """Grade one exercise. `rng`/`fuzz` only ever apply to "function"-kind
    exercises whose args are all "safe" to randomise (see is_fuzzable) —
    every other exercise is graded on its curated cases alone, same as
    before fuzzing existed. `valgrind` is silently skipped (not an error)
    when the valgrind binary isn't on PATH — see have_valgrind(). A
    forbidden call (see find_forbidden()) only warns unless
    `strict_forbidden` — the real exam's own moulinette does fail on one,
    same as Python's --strict-imports; this project's own default stays
    lenient so a beginner's warning-only feedback loop isn't lost."""
    if ex.get("kind") == "program":
        return _grade_program(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath,
                              valgrind, strict_valgrind, strict_forbidden, rng, fuzz)
    return _grade_function(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath,
                           rng, fuzz, valgrind, strict_valgrind, strict_forbidden)


def _grade_function(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath,
                    rng=None, fuzz=0, valgrind=False, strict_valgrind=False,
                    strict_forbidden=False):
    report = Report(ex_name, ex["function"])
    path = filepath or os.path.join(rendu_dir, ex_name + ".c")
    started = time.time()

    if not os.path.isfile(path):
        return report.fail("FILE_MISSING", "expected your solution at %s" % path)

    cases = list(ex["cases"])
    if fuzz and rng is not None and is_fuzzable(ex):
        cases += build_fuzz_cases(ex, rng, fuzz)

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
        if strict_forbidden:
            return report.fail("FORBIDDEN_CALL", ", ".join(forbidden))

    workdir = tempfile.mkdtemp(prefix="c-exam-")
    try:
        include_dirs = []
        header = header_filename(ex)
        if header:
            with open(os.path.join(workdir, header), "w", encoding="utf-8") as fh:
                fh.write(header_content(header))
            include_dirs.append(workdir)

        # Codegen itself (render_call(), a return_len callable, ...) can
        # raise on a value it doesn't expect — reachable even for an
        # exercise whose curated cases always codegen cleanly, since fuzz
        # cases exercise it with values the bank author never tried. Same
        # BANK_ERROR treatment as a reference that fails to compile below:
        # a bank/codegen bug is never the student's fault, and must never
        # surface as a raw traceback mid-exam (see the module docstring).
        try:
            harness_src = generate_harness(ex, cases)
        except Exception as exc:
            return report.fail("BANK_ERROR",
                               "%s: harness codegen crashed (%s: %s)"
                               % (ex_name, type(exc).__name__, exc))
        harness_path = os.path.join(workdir, "harness.c")
        with open(harness_path, "w", encoding="utf-8") as fh:
            fh.write(harness_src)

        oracle_path = os.path.join(workdir, "oracle.c")
        with open(oracle_path, "w", encoding="utf-8") as fh:
            fh.write(ex["oracle_c"])

        ref_bin = os.path.join(workdir, "ref")
        ok, err = compile_c([oracle_path, harness_path], ref_bin, cc,
                            include_dirs=include_dirs)
        if not ok:
            # A real bank/codegen bug, not the student's fault — never let it
            # surface as a raw traceback mid-exam (fuzz cases make this path
            # reachable even for exercises whose curated cases always compiled).
            return report.fail("BANK_ERROR",
                               "%s: reference implementation fails to compile:\n%s"
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
            return report.fail("COMPILE_ERROR", _compile_error_detail(err))
        if err.strip():
            report.warnings.append(
                "compiler warning (fix it — the real exam compiles with "
                "-Wall -Wextra too; --strict-norm makes this fatal):\n" + err[:500])

        ref_out, ref_crash = run_bin(ref_bin, timeout)
        if ref_crash:
            return report.fail("BANK_ERROR", "%s: reference binary %s"
                               % (ex_name, ref_crash))

        stu_out, stu_crash = run_bin(student_bin, timeout)
        report.duration = time.time() - started

        if stu_crash == "TIMEOUT":
            return report.fail("TIMEOUT", "no result after %ds — infinite loop?" % timeout)
        if stu_crash:
            report.warnings.append("your program crashed: " + stu_crash.split(":", 1)[1])

        if valgrind and have_valgrind():
            # one valgrind pass covers every case: the harness's own main()
            # already loops through curated + fuzz cases inside this single
            # binary/process.
            vg_clean, vg_detail = run_valgrind(student_bin, timeout)
            if not vg_clean:
                # Appended before the strict_valgrind fail-out below too —
                # ui.report() prints warnings even on a fatal Report, and
                # hints.classify() detects LEAK by scanning report.warnings
                # for the word (see examshell/hints.py), which needs it present
                # here regardless of strict/non-strict.
                report.warnings.append(
                    "valgrind reported memory error(s) (leaks, invalid "
                    "reads/writes, ...) — fix them before the real exam, "
                    "leaked/invalid memory is graded there too:\n" + vg_detail)
                if strict_valgrind:
                    return report.fail("VALGRIND_ERRORS", vg_detail)

        n = len(cases)
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
                    CFailure(i, expected.rstrip("\n"), got.rstrip("\n"), args=cases[i]))
        # Updated (not just set once above) so a valgrind pass — much
        # slower than the bare binary, see VALGRIND_TIMEOUT_MULT — is
        # counted too, the same way _grade_program's single end-of-loop
        # assignment already does; only the early TIMEOUT/VALGRIND_ERRORS
        # fatal returns above keep the earlier, valgrind-time-free value.
        report.duration = time.time() - started
        return report
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _grade_program(ex_name, ex, rendu_dir, cc, timeout, strict_norm, filepath,
                   valgrind=False, strict_valgrind=False, strict_forbidden=False,
                   rng=None, fuzz=0):
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
        if strict_forbidden:
            return report.fail("FORBIDDEN_CALL", ", ".join(forbidden))

    workdir = tempfile.mkdtemp(prefix="c-exam-")
    try:
        oracle_path = os.path.join(workdir, "oracle.c")
        with open(oracle_path, "w", encoding="utf-8") as fh:
            fh.write(ex["oracle_c"])

        ref_bin = os.path.join(workdir, "ref")
        ok, err = compile_c([oracle_path], ref_bin, cc)
        if not ok:
            return report.fail("BANK_ERROR",
                               "%s: reference program fails to compile:\n%s"
                               % (ex_name, err[:800]))

        student_bin = os.path.join(workdir, "student")
        extra = ["-Werror"] if strict_norm else []
        ok, err = compile_c([path], student_bin, cc, extra_flags=extra)
        if not ok:
            return report.fail("COMPILE_ERROR", _compile_error_detail(err))
        if err.strip():
            report.warnings.append(
                "compiler warning (fix it — the real exam compiles with "
                "-Wall -Wextra too; --strict-norm makes this fatal):\n" + err[:500])

        run_valgrind_ok = valgrind and have_valgrind()
        vg_issues = []
        cases = list(ex["cases"])
        if fuzz and rng is not None and is_fuzzable(ex):
            cases += [fuzz_argv(ex["fuzz_argv"], rng) for _ in range(fuzz)]
        report.total = len(cases)
        streak = 0
        for i, argv in enumerate(cases):
            ref_out, ref_crash = run_bin(ref_bin, timeout, argv=argv)
            if ref_crash:
                return report.fail("BANK_ERROR", "%s: reference program %s on case %d"
                                   % (ex_name, ref_crash, i))
            # Same bail-out as the Python sandbox (examshell/grader.py's
            # MAX_TIMEOUTS): an infinite loop would otherwise cost the full
            # timeout on EVERY remaining case — 30s+ of staring at a spinner.
            if streak >= MAX_TIMEOUTS:
                report.failures.append(CFailure(i, ref_out,
                                                "[skipped after %d timeouts]" % streak,
                                                args=argv, program=True))
                continue
            stu_out, stu_crash = run_bin(student_bin, timeout, argv=argv)
            streak = streak + 1 if stu_crash == "TIMEOUT" else 0
            if stu_crash:
                note = stu_crash.split(":", 1)[-1]
                report.warnings.append("case %d %s: %s"
                                       % (i, "timed out" if stu_crash == "TIMEOUT"
                                          else "crashed", note))
                report.failures.append(CFailure(i, ref_out,
                                                "[%s]" % note, args=argv, program=True))
                continue
            if stu_out == ref_out:
                report.passed += 1
            else:
                # Raw, NOT rstrip()'d like the function-kind chunks above:
                # there the trailing newline is the harness's own, here it
                # is the student's — and a missing (or extra) "\n" is one
                # of the most common real exam failures. Stripped, the two
                # sides could look identical while the case still fails.
                report.failures.append(
                    CFailure(i, ref_out, stu_out, args=argv, program=True))
            if run_valgrind_ok:
                vg_clean, vg_detail = run_valgrind(student_bin, timeout, argv=argv)
                if not vg_clean:
                    vg_issues.append((i, vg_detail))
                    if strict_valgrind:
                        break

        if vg_issues:
            # Appended before the strict_valgrind fail-out below too — see
            # the matching comment in _grade_function.
            more = (" (+%d more case%s)" % (len(vg_issues) - 1,
                    "" if len(vg_issues) == 2 else "s") if len(vg_issues) > 1 else "")
            report.warnings.append(
                "valgrind reported memory error(s) (leaks, invalid reads/writes, "
                "...) on case %d%s — fix them before the real exam, leaked/invalid "
                "memory is graded there too:\n%s"
                % (vg_issues[0][0], more, vg_issues[0][1]))
            if strict_valgrind:
                return report.fail("VALGRIND_ERRORS", "case %d: %s"
                                   % (vg_issues[0][0], vg_issues[0][1]))

        report.duration = time.time() - started
        return report
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
#  BANK SELF-TEST  (make c-check)
# ══════════════════════════════════════════════════════════════
def selftest(exercises, groups, cc=DEFAULT_CC, timeout=DEFAULT_TIMEOUT,
             rng=None, fuzz=0, valgrind=False, log=print):
    """Validate the whole C bank. Returns the number of problems found.

    `rng`/`fuzz` run every fuzzable exercise's oracle (as "student") against
    fuzzed cases too, the same way grade() would for a real submission —
    this is what actually proves the fuzz generators never hand the oracle
    a value it cannot handle. `valgrind` (only useful where the binary is
    actually on PATH — see have_valgrind()) runs every oracle through it
    too, always in strict mode: a leak in the bank's OWN reference
    implementation is a bank bug, not a warning to shrug off."""
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
            prototype = ex.get("prototype", "")
            if _KR_FUNC_PTR_RE.search(prototype):
                bad("%s: prototype declares a K&R-style empty-parens function "
                    "pointer (%s) — GCC's C23 default reads () as \"takes no "
                    "arguments\", not \"unspecified\", so a real call to it fails "
                    "to compile; write out the parameter types instead"
                    % (name, _KR_FUNC_PTR_RE.search(prototype).group()))
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

            report = grade(name, ex, workdir, cc=cc, timeout=timeout, filepath=path,
                           rng=rng, fuzz=fuzz, valgrind=valgrind, strict_valgrind=valgrind)
            if report.fatal:
                bad("%s: %s (%s)" % (name, report.fatal, report.detail))
                continue
            if not report.ok:
                bad("%s: oracle fails its own %s, e.g. case %d"
                    % (name, "harness" if kind == "function" else "run",
                       report.failures[0].index))
                continue
            fuzzed = " (+fuzz)" if fuzz and is_fuzzable(ex) else ""
            vg_tag = " (+valgrind)" if valgrind and have_valgrind() else ""
            log("  ok    %-32s %3d tests%s%s" % (name, report.total, fuzzed, vg_tag))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return problems
