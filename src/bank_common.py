#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bank_common.py  ·  helpers shared by exam_bank.py and training_bank.py

Kept tiny and dependency-free on purpose: both bank modules import it, and
neither should have to depend on the other.
"""

import textwrap


def sub(name, body):
    """Build a subject string in the standard `Assignment name: ...` shape."""
    head = (f"Assignment name  : {name}\n"
            f"Expected files   : {name}.py\n"
            f"Allowed functions: None\n"
            + "-" * 80 + "\n\n")
    return head + textwrap.dedent(body).strip("\n") + "\n"


def signature_of(subject):
    """The `def …:` line of a subject string, or None if it has none."""
    for line in subject.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and stripped.endswith(":"):
            return stripped
    return None
