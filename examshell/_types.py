#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_types.py  ·  type aliases shared across both testers (for mypy only)

Nothing here changes behaviour. The bank entries, stats events and saved
state are plain JSON-shaped dicts on purpose (they are written to and read
from disk), so they stay `Dict[str, Any]` — these names just say which
kind of dict a function expects.
"""

from __future__ import annotations

import random
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Protocol

# One exercise of a bank (exam_bank.py, c_exam/bank.py, …).
Exercise = Dict[str, Any]
# One line of stats.jsonl, or one saved exam (session_store.py).
Event = Dict[str, Any]
# A tester module (examshell.examshell or c_exam.examshell) handed to the
# shared flow as `sh`: every hook is looked up on it at call time, so it
# is duck-typed on purpose (see shell_common's module docstring).
Tester = ModuleType
# A bank's random-input generator: rng -> one call's argument list.
Fuzzer = Callable[[random.Random], List[Any]]


class TesterConfig(Protocol):
    """What the shared flow reads from either tester's Config."""

    rendu: str
    timeout: int
    fuzz: int
    show_fails: int
    diff: bool
    seed: Optional[int]
    relaxed: bool
    time_limit: Optional[int]
    blind: bool
    bare_stub: bool
    no_update_check: bool
