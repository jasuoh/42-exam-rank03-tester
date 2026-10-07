#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ranks.py  ·  the Python exam ranks this tester knows about

One tester, three exam pools. A rank is just "which bank, how many levels,
and under which tag do this student's stats/saved exam/reports live" —
everything else (grading, the UI, the training pool, hints, badges) is
shared, because none of it cares which rank an exercise came from.

The `tool` tag is what keeps a rank's history its own: stats.jsonl rows,
~/.examshell/saved_exam_<tool>.json and the exported reports are all keyed
by it, so a half-finished Rank 04 exam can never be resumed into a Rank 03
one, and a Rank 03 best time is not beaten by a shorter Rank 05 run. "py"
is Rank 03's tag rather than "py03" so that every history recorded before
this module existed still counts.

The training POOL is deliberately shared by all three: it is LeetCode-style
drilling that belongs to no particular exam, and there is no reason a Rank
05 student should be shown a smaller set of drills than a Rank 03 one.
What a student did in it is still recorded under whichever rank was active
at the time, like everything else — one rule for every grading event
rather than a special case for one pool.
"""

from __future__ import annotations

from types import ModuleType
from typing import Dict, List, Optional, Tuple

from . import exam_bank, exam_bank_r04, exam_bank_r05, training_bank
from ._types import Exercise


class Rank(object):
    __slots__ = ("id", "label", "tool", "bank", "training")

    def __init__(
        self,
        rank_id: str,
        label: str,
        tool: str,
        bank: ModuleType,
        training: ModuleType = training_bank,
    ) -> None:
        self.id = rank_id
        self.label = label  # "Exam Rank 03"
        self.tool = tool  # stats / saved-exam / report tag
        self.bank = bank
        self.training = training

    @property
    def n_levels(self) -> int:
        n: int = self.bank.N_LEVELS
        return n

    @property
    def exercises(self) -> Dict[str, Exercise]:
        exercises: Dict[str, Exercise] = self.bank.EXERCISES
        return exercises

    @property
    def levels(self) -> Dict[int, List[str]]:
        levels: Dict[int, List[str]] = self.bank.LEVELS
        return levels

    @property
    def standard_levels(self) -> Dict[int, List[str]]:
        levels: Dict[int, List[str]] = self.bank.STANDARD_LEVELS
        return levels

    def all_exercises(self) -> Dict[str, Exercise]:
        """Exam pool + training pool, keyed by name — what a name can be
        resolved against. The exam pool wins a name collision: a rank's own
        subject is the one its student came here for."""
        merged: Dict[str, Exercise] = dict(self.training.TRAINING_EXERCISES)
        merged.update(self.exercises)
        return merged


RANKS = {
    "03": Rank("03", "Exam Rank 03", "py", exam_bank),
    "04": Rank("04", "Exam Rank 04", "py04", exam_bank_r04),
    "05": Rank("05", "Exam Rank 05", "py05", exam_bank_r05),
}

DEFAULT_RANK = "03"
CHOICES = ("03", "04", "05")


def normalize(value: object) -> Optional[str]:
    """Accept "3", "03", "rank04", "r5" … and return a key of RANKS, or
    None when it names no rank we have."""
    if value is None:
        return None
    text = str(value).strip().lower()
    for prefix in ("rank", "r", "#"):
        if text.startswith(prefix):
            cut = len(prefix)
            text = text[cut:]
    text = text.lstrip("0") or "0"
    key = "%02d" % int(text) if text.isdigit() else text
    return key if key in RANKS else None


def get(value: object = None) -> Rank:
    """The Rank for `value`, falling back to the default."""
    return RANKS[normalize(value) or DEFAULT_RANK]


def summary() -> List[Tuple[str, str, int, int]]:
    """[(id, label, exercises, levels), …] in rank order — for the
    rank-picker screen and --list-ranks."""
    return [
        (r.id, r.label, len(r.exercises), r.n_levels)
        for r in (RANKS[key] for key in CHOICES)
    ]
