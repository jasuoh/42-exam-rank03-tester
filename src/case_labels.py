#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
case_labels.py  ·  "which edge case was this?" — shared by both testers

A failing test is much easier to fix when the report says WHAT kind of
input broke it ("empty string", "tabs", "negative number") instead of just
showing the raw value. describe() looks at a failure's own inputs — a
Python Failure's call arguments, a C CFailure's case values or argv — and
names the edge-case traits it can see. Purely descriptive: it knows nothing
about the exercise, so it only ever names properties of the input itself,
never guesses at the bug.
"""

INT_MAX = 2 ** 31 - 1
INT_MIN = -2 ** 31
MAX_LABELS = 2


def _string_traits(s):
    if s == "":
        return ["empty string"]
    if s.strip() == "":
        return ["only whitespace"]
    traits = []
    if "\t" in s:
        traits.append("tabs")
    if s != s.strip():
        traits.append("leading/trailing whitespace")
    if "  " in s:
        traits.append("repeated spaces")
    return traits


def _number_traits(n):
    if n == 0:
        return ["zero"]
    if n in (INT_MAX, INT_MIN) or abs(n) > INT_MAX:
        return ["INT_MIN/INT_MAX"]
    if n < 0:
        return ["negative number"]
    return []


def _argv_number(s):
    """int(s) for an argv string that is a plain integer, else None."""
    body = s[1:] if s[:1] in "+-" else s
    return int(s) if body.isdigit() else None


def _value_traits(value, argv=False):
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return _number_traits(value)
    if isinstance(value, str):
        number = _argv_number(value) if argv else None
        return _number_traits(number) if number is not None else _string_traits(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return ["empty list"]
        if len(value) == 1:
            return ["single element"]
    return []


def describe(failure):
    """A short ' · '-joined label for a failure's input, or "" when none
    of its inputs has a notable trait. Works on both testers' failure
    objects: `args` holds the call arguments (Python Failure, C function-
    kind CFailure) or the argv (C program-kind CFailure, `program` set)."""
    args = getattr(failure, "args", None)
    if args is None:
        return ""
    argv = bool(getattr(failure, "program", False))
    if argv and not args:
        return "no arguments"
    labels = []
    for value in args:
        for trait in _value_traits(value, argv):
            if trait not in labels:
                labels.append(trait)
    return " · ".join(labels[:MAX_LABELS])
