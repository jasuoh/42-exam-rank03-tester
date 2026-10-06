#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
achievements.py  ·  badges earned from a student's own practice history,
shared by both testers.

Every badge is a pure function of stats.jsonl (see stats.py) — nothing new
is ever persisted, so a badge collection is always just "everything you've
ever graded, looked at a certain way", recomputed fresh every time it's
shown. That statelessness is also what makes "did I just unlock something"
work: call unlocked() once before recording this run's event and once
after, and diff the two sets (see new_since()) — no separate "already
notified about this badge" bookkeeping needed.

Compares a student only against their own history. There is no
leaderboard here, no comparison between students, nothing sent anywhere.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Sequence, Tuple

from . import stats
from ._types import Event
from .hints import STUCK_THRESHOLD

CENTURY_THRESHOLD = 100
NIGHT_OWL_HOURS = range(0, 5)  # 00:00–04:59 local time
EARLY_BIRD_HOURS = range(5, 7)  # 05:00–06:59 local time


def _grading_events(tool: str) -> List[Event]:
    """Real grading events only (has an "exercise"), sorted oldest-first —
    excludes exam-complete pseudo-events (see stats.record_exam_complete),
    which carry no "exercise" field and are handled separately below."""
    events = [e for e in stats.load_all(tool) if e.get("exercise")]
    events.sort(key=lambda e: e.get("ts", 0))
    return events


def _exam_completions(tool: str) -> List[Event]:
    return [
        e for e in stats.load_all(tool) if e.get("mode") == "exam-complete"
    ]


def _first_blood(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    return any(e.get("ok") for e in events)


def _perfectionist(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    """100% on the very first recorded attempt at some exercise."""
    seen: set[str] = set()
    for e in events:
        name = e["exercise"]
        if name in seen:
            continue
        seen.add(name)
        if e.get("ok"):
            return True
    return False


def _comeback_kid(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    """Passed an exercise right after a fail-streak of STUCK_THRESHOLD or
    more on that same exercise — the exact moment a stuck-student hint
    would have been showing (see hints.py), turned around."""
    streaks: Dict[str, int] = {}
    for e in events:
        name = e["exercise"]
        if e.get("ok"):
            if streaks.get(name, 0) >= STUCK_THRESHOLD:
                return True
            streaks[name] = 0
        else:
            streaks[name] = streaks.get(name, 0) + 1
    return False


def _full_coverage(
    events: List[Event], _completions: List[Event], n_levels: int
) -> bool:
    """Passed at least one exercise from every level in the pool."""
    passed_levels = {
        e["level"]
        for e in events
        if e.get("ok") and e.get("level") is not None
    }
    return n_levels > 0 and len(passed_levels) >= n_levels


def _redemption(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    """Every exercise ever attempted has eventually been passed at least
    once — no exercise permanently stuck at 0 passes — and at least one of
    them was failed before its first pass: there has to be something to
    redeem, a clean first-try pass is Perfectionist's business."""
    ever_passed: Dict[str, bool] = {}
    redeemed = False
    for e in events:
        name = e["exercise"]
        failed_before = name in ever_passed and not ever_passed[name]
        ever_passed.setdefault(name, False)
        if e.get("ok"):
            redeemed = redeemed or failed_before
            ever_passed[name] = True
    return redeemed and all(ever_passed.values())


def _century(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    return len(events) >= CENTURY_THRESHOLD


def _exam_cleared(
    _events: List[Event], completions: List[Event], _n_levels: int
) -> bool:
    return len(completions) > 0


def _flawless_exam(
    _events: List[Event], completions: List[Event], n_levels: int
) -> bool:
    """A full exam cleared with exactly one attempt per level — no retry
    on any level. session.attempts (stored as "attempts") counts one
    grademe call per attempt, pass or fail, across the whole exam."""
    return any(c.get("attempts") == n_levels for c in completions)


def _night_owl(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    return any(
        e.get("ok") and time.localtime(e["ts"]).tm_hour in NIGHT_OWL_HOURS
        for e in events
    )


def _early_bird(
    events: List[Event], _completions: List[Event], _n_levels: int
) -> bool:
    return any(
        e.get("ok") and time.localtime(e["ts"]).tm_hour in EARLY_BIRD_HOURS
        for e in events
    )


# (id, emoji, label, description, check) — order is display order, roughly
# easiest-to-earn first. `check(events, completions, n_levels)` -> bool.
BadgeCheck = Callable[[List[Event], List[Event], int], bool]
Badge = Tuple[str, str, str, str]  # (id, emoji, label, description)
BADGES: Tuple[Tuple[str, str, str, str, BadgeCheck], ...] = (
    (
        "first_blood",
        "🩸",
        "First Blood",
        "Pass your first graded attempt.",
        _first_blood,
    ),
    (
        "perfectionist",
        "💯",
        "Perfectionist",
        "100% on an exercise's very first attempt.",
        _perfectionist,
    ),
    (
        "comeback_kid",
        "🔥",
        "Comeback Kid",
        "Pass an exercise right after %d+ fails in a row on it."
        % STUCK_THRESHOLD,
        _comeback_kid,
    ),
    (
        "redemption",
        "🎯",
        "Redemption",
        "Fail an exercise, then pass it — with every exercise you've "
        "ever attempted passed eventually.",
        _redemption,
    ),
    (
        "full_coverage",
        "🧭",
        "Full Coverage",
        "Pass at least one exercise from every level.",
        _full_coverage,
    ),
    (
        "night_owl",
        "🦉",
        "Night Owl",
        "Pass something between midnight and 5am.",
        _night_owl,
    ),
    (
        "early_bird",
        "🐦",
        "Early Bird",
        "Pass something between 5am and 7am.",
        _early_bird,
    ),
    (
        "century",
        "🏃",
        "Century",
        "%d total graded attempts." % CENTURY_THRESHOLD,
        _century,
    ),
    (
        "exam_cleared",
        "🏆",
        "Exam Cleared",
        "Clear a full exam, all levels.",
        _exam_cleared,
    ),
    (
        "flawless_exam",
        "🏅",
        "Flawless Exam",
        "Clear a full exam with no retries on any level.",
        _flawless_exam,
    ),
)


def unlocked(tool: str, n_levels: int) -> List[Badge]:
    """Which badges are unlocked right now, as
    [(id, emoji, label, description), …] in BADGES order. Recomputed
    fresh from stats.jsonl every call — safe to call often, and calling
    it twice (before/after recording one new event) is how new_since()
    detects a badge earned just now."""
    events = _grading_events(tool)
    completions = _exam_completions(tool)
    return [
        (bid, emoji, label, desc)
        for bid, emoji, label, desc, check in BADGES
        if check(events, completions, n_levels)
    ]


def new_since(before: Sequence[Badge], after: Sequence[Badge]) -> List[Badge]:
    """Badges present in `after` but not `before` (both as returned by
    unlocked()) — what to announce as "just unlocked", in BADGES order."""
    seen = {b[0] for b in before}
    return [b for b in after if b[0] not in seen]


def is_new_best_time(tool: str, seconds: float) -> bool:
    """True when `seconds` beats every prior recorded full-exam time —
    call BEFORE stats.record_exam_complete() persists this run's time,
    same "before" convention as unlocked()/new_since(). Deliberately not
    part of the BADGES/unlocked() collection: it describes THIS run
    ("you just beat your record"), not a standing trait to collect."""
    prior_best = stats.best_exam_time(tool)
    return prior_best is not None and seconds < prior_best
