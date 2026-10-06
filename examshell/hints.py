#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hints.py  ·  gentle nudges for a student who's stuck, shared by both testers

Two sources, checked in order (see hint_for() and grade_exercise() in both
examshell.py's):

  1. A curated hint on the exercise itself (bank entry's optional "hint"
     key) — hand-written, exercise-specific, added incrementally over
     time. Preferred when present. It's either:
       - a plain string, shown for every failure on that exercise, or
       - a dict keyed by the same category names classify() returns
         (plus an optional "default"), so one exercise can nudge a crash,
         a leak and a plain wrong answer differently — e.g. ft_split can
         say "you're missing the NULL terminator slot" for a crash but
         "your word count doesn't match your extraction logic" otherwise.
  2. diagnose() below — a generic, pattern-matched guess from the shape of
     the failure alone (works for every exercise immediately, curated or
     not). It only ever *suggests* ("could be", "often means") — it has
     no idea what the student's code actually does, so it's wrong often
     enough that a confident tone would be actively misleading.

Both are surfaced only after STUCK_THRESHOLD *consecutive* fails on the
same exercise (see stats.consecutive_fails) — not on every red result.
A student who fails once just made a mistake; a student who fails three
times in a row on the same thing is stuck, and that's the moment a small
push helps instead of feeling like nagging. Never shown during --exam
(see both examshell.py's grade_exercise) — confronting a stuck moment
without a crutch is part of what the exam is actually testing, and the
practice/training modes are where this tool is supposed to build that
muscle instead of short-circuiting it.
"""

import re

STUCK_THRESHOLD = 3

_EMPTYISH_OBJECTS = (None, [], (), {})

# The Python sandbox never appends a "crashed" warning like the C tester
# does (see grade_exercise() below) — a raised exception is just a failing
# case, recorded as "[ExceptionType] message" in that Failure's `got` (see
# examshell/grader.py's RUNNER_TEMPLATE). Recognising that shape here is what
# lets a Python crash reach the same CRASH category as a C one.
_CRASH_MARKER_RE = re.compile(r"^\[[A-Za-z_]\w*\]")

TIMEOUT = "timeout"
CRASH = "crash"
LEAK = "leak"
OFF_BY_ONE = "off_by_one"
SIGN_FLIP = "sign_flip"
EMPTY_EXPECTED = "empty_expected"

_GENERIC_HINTS = {
    TIMEOUT: (
        "Looks like an infinite loop — check your stopping "
        "condition, especially for the smallest possible input "
        "(empty, 0, a single element)."
    ),
    CRASH: (
        "A crash almost always points at memory access, not wrong "
        "logic — a null pointer, an out-of-bounds access, or an "
        "off-by-one in a loop bound are the usual suspects."
    ),
    LEAK: (
        "Valgrind found a leak — some malloc'd block is never freed "
        "on at least one path (an early return, an error case, only "
        "freeing part of a list or array). Trace every malloc to a "
        "matching free on every path, including the ones you don't "
        "expect to hit."
    ),
    OFF_BY_ONE: (
        "Your result is off by exactly 1 — a classic "
        "off-by-one, often a < vs. <= or a stray +1/-1 "
        "somewhere in a loop bound."
    ),
    SIGN_FLIP: (
        "The sign is wrong — maybe a condition that's being "
        "evaluated backwards?"
    ),
    EMPTY_EXPECTED: (
        "The expected value here is 'empty' — did you "
        "handle the empty-input (or 0-element) case "
        "separately?"
    ),
}


def _as_number(value):
    """float(value), or None when it isn't numeric — including bools,
    which parse as 0.0/1.0 but would make a bool-logic bug look like an
    off-by-one, actively misleading rather than helpful."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_emptyish(value):
    """True when `value` represents "nothing" — the real empty Python
    object (None, [], (), {}, "") when it's still typed (a Python
    Report's f.expected is — see examshell/grader.py's Failure), a bare "" when
    it's already a string (a C tester's raw stdout diff always is, and so
    is a Python Report's f.got — see RUNNER_TEMPLATE's short_repr()).
    Deliberately NOT string-matching "None"/"[]"/"()"/"{}" the way an
    older version of this did: a solution whose genuinely correct answer
    is the literal string "None" (or "[]", ...) would otherwise be
    treated as if it returned nothing at all."""
    if isinstance(value, str):
        return value.strip() == ""
    return value in _EMPTYISH_OBJECTS


def classify(report):
    """Which generic failure pattern `report` matches, as one of the
    category constants above, or None when nothing applies. `report` is
    a graded Report — Python's and the C tester's share the same shape
    (see examshell/grader.py's Report, reused by c_exam/grader.py), so this
    works unmodified for both. Shared by diagnose() (the generic hint)
    and hint_for() (picking the right branch of a per-category curated
    hint)."""
    if report.fatal in ("TIMEOUT", "GLOBAL_TIMEOUT", "IMPORT_TIMEOUT"):
        return TIMEOUT
    if any("crashed" in w for w in report.warnings):
        return CRASH
    # Valgrind's own leak-summary phrasing ("N bytes in M blocks are
    # definitely/indirectly/possibly lost") is the only reliable signal
    # that a valgrind finding was actually a LEAK — the boilerplate
    # wrapper message around it (see c_exam/grader.py's run_valgrind()
    # callers) always says "leak" regardless of the real finding, so
    # grepping for that word used to show the LEAK hint even for e.g. a
    # plain invalid read/write with zero blocks actually leaked. Any
    # other valgrind finding is routed to CRASH instead — genuinely the
    # closer category (memory access, not "wrong logic").
    if any("lost" in w.lower() for w in report.warnings):
        return LEAK
    if any("valgrind reported" in w.lower() for w in report.warnings):
        return CRASH
    if report.fatal or not report.failures:
        return None
    f = report.failures[0]
    # A per-case timeout (one case's alarm fires, the run keeps going) is
    # recorded as a plain failure rather than a fatal Report, on both
    # sides — c_exam/grader.py's _grade_program uses got="[TIMEOUT]",
    # examshell/grader.py's RUNNER_TEMPLATE uses got="[TIMEOUT > Ns]" (the
    # per-call timeout is embedded in the message there). startswith()
    # catches both — special-cased ahead of the CRASH marker below, which
    # would otherwise also match "[TIMEOUT]" and misreport an infinite
    # loop as a memory-access crash.
    if str(f.got).startswith("[TIMEOUT"):
        return TIMEOUT
    if _CRASH_MARKER_RE.match(str(f.got)):
        return CRASH
    exp_n, got_n = _as_number(f.expected), _as_number(f.got)
    if exp_n is not None and got_n is not None and exp_n != got_n:
        if abs(got_n - exp_n) == 1:
            return OFF_BY_ONE
        if exp_n != 0 and got_n != 0 and (exp_n < 0) != (got_n < 0):
            return SIGN_FLIP
    if _is_emptyish(f.expected) and not _is_emptyish(f.got):
        return EMPTY_EXPECTED
    return None


def diagnose(report):
    """One short, hedged hint string, or None when nothing generic
    applies."""
    category = classify(report)
    return _GENERIC_HINTS.get(category) if category else None


def hint_for(ex, report):
    """The hint text to show for a failing `report` on bank entry `ex`,
    or None. `ex.get("hint")` is either a plain string (used as-is) or a
    dict keyed by classify()'s categories plus an optional "default";
    falls back to diagnose()'s generic guess when there's no curated
    hint, or the dict has neither a matching category nor a "default"."""
    raw = ex.get("hint")
    if isinstance(raw, dict):
        category = classify(report)
        return raw.get(category) or raw.get("default") or diagnose(report)
    return raw or diagnose(report)
