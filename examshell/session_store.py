#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
session_store.py  ·  exam progress save/resume, shared by both testers

An in-progress exam (login, level, passed exercises, the exercise
currently drawn, elapsed time, RNG state) can be saved to
~/.examshell/saved_exam_<tool>.json when the student quits early, and
restored the next time they start an exam — so a closed laptop or a
`quit` by mistake doesn't cost the whole run.

It also remembers which exercises recent exams drew per level
(~/.examshell/exam_draws_<tool>.json), so a new exam doesn't hand out the
same ones again (issue #16) — see draw_fresh().

Best-effort like the rest of this package: a save/load failure is a
missed convenience, never a reason to crash the exam.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from ._types import Event

from .settings import DATA_DIR, write_atomic

if TYPE_CHECKING:
    from .shell_common import Session


def _path(tool: str) -> str:
    return os.path.join(DATA_DIR, "saved_exam_%s.json" % tool)


def _rng_to_json(rng: random.Random) -> List[Any]:
    version, internal, gauss_next = rng.getstate()
    return [version, list(internal), gauss_next]


def _rng_from_json(
    data: List[Any],
) -> Tuple[Any, ...]:
    version, internal, gauss_next = data
    return (version, tuple(internal), gauss_next)


def save(
    tool: str,
    session: Session,
    rng: random.Random,
    current_ex: Optional[str],
    level_attempts: int = 0,
    level_started: Optional[float] = None,
) -> bool:
    """Persist enough state to resume exactly where the student left off.

    `level_started` is the wall-clock time.time() the CURRENT level began —
    without it, a resume can only restart that level's clock from the
    moment of resuming, silently dropping whatever time was already spent
    on it before quitting (see load()'s counterpart, level_elapsed_seconds).
    """
    data = {
        "login": session.login,
        "level": session.level,
        "current_ex": current_ex,
        "passed": session.passed,
        "attempts": session.attempts,
        "history": session.history,
        "level_attempts": level_attempts,
        "level_elapsed_seconds": (time.time() - level_started)
        if level_started
        else 0,
        "elapsed_seconds": time.time() - session.start_time
        if session.start_time
        else 0,
        "rng_state": _rng_to_json(rng),
        # what examshell/sync.py compares when two devices both have a save
        "saved_at": time.time(),
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        write_atomic(_path(tool), json.dumps(data))
        return True
    except OSError:
        return False


def load(tool: str) -> Optional[Event]:
    """The saved dict, or None if there is nothing (or nothing usable)
    to resume."""
    try:
        with open(_path(tool), encoding="utf-8") as fh:
            data = json.load(fh)
        # sanity-check the shape before handing it back — a hand-edited
        # or half-written file should just look like "nothing saved".
        required = (
            "login",
            "level",
            "current_ex",
            "passed",
            "attempts",
            "history",
            "elapsed_seconds",
            "rng_state",
        )
        if not isinstance(data, dict) or not all(k in data for k in required):
            return None
        return data
    except (OSError, ValueError):
        return None


def clear(tool: str) -> None:
    """Forget the saved exam. Leaves a small tombstone instead of just
    deleting the file: with sync, a plain delete would look like
    "this device never had one" and the other device's stale save would
    come right back. load() ignores the tombstone (no required keys)."""
    path = _path(tool)
    if not os.path.exists(path):
        return
    try:
        write_atomic(path, json.dumps({"cleared_at": time.time()}))
    except OSError:
        pass


def rng_from_saved(data: Event) -> random.Random:
    rng = random.Random()
    rng.setstate(_rng_from_json(data["rng_state"]))
    return rng


# ── exam draws ───────────────────────────────────────────────────────
def _draws_path(tool: str) -> str:
    return os.path.join(DATA_DIR, "exam_draws_%s.json" % tool)


def _load_draws(tool: str) -> Dict[str, List[str]]:
    try:
        with open(_draws_path(tool), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): [n for n in v if isinstance(n, str)]
        for k, v in data.items()
        if isinstance(v, list)
    }


def draw_fresh(
    tool: str,
    level: int,
    rng: random.Random,
    pool: Sequence[str],
    avoid: Optional[str] = None,
) -> str:
    """Draw this level's exercise like a shuffled deck: what earlier exams
    drew at this level is skipped until every exercise of it came up once,
    and a new round never starts with the one that ended the last — with
    two or three exercises per level, plain random draws kept repeating
    them (issue #16). `avoid` (a redraw) is skipped whenever possible."""
    draws = _load_draws(tool)
    key = str(level)
    seen = [n for n in draws.get(key, []) if n in pool]
    choices = [n for n in pool if n not in seen and n != avoid]
    if not choices:  # a full round: start the next one
        last = seen[-1] if seen else None
        seen = []
        choices = [n for n in pool if n not in (last, avoid)]
    name = rng.choice(choices or list(pool))
    draws[key] = seen + [name]
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        write_atomic(_draws_path(tool), json.dumps(draws))
    except OSError:
        pass
    return name
