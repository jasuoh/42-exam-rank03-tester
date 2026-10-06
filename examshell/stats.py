#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stats.py  ·  local practice history, shared by both testers

Every grademe / --grade appends one line to ~/.examshell/stats.jsonl (JSON
Lines: one grading event per line, so a crash mid-write only ever corrupts
the last line, never the whole file). Purely local, purely additive — this
is a convenience for the student to see their own progress, never sent
anywhere, never read by grading itself.

Best-effort like settings.py: recording a stat must never be the reason a
grading run fails, so every write swallows OSError.
"""

from __future__ import annotations

import datetime
import json
import os
import time
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from ._types import Event

from .settings import DATA_DIR

STATS_PATH = os.path.join(DATA_DIR, "stats.jsonl")


def record(
    tool: str,
    exercise: str,
    level: Optional[int],
    ok: bool,
    passed: int,
    total: int,
    mode: str,
) -> None:
    """Append one grading event. `tool` is "py" or "c"; `mode` is
    "exam" / "practice" / "train" / "grade" / "exam-complete"."""
    entry = {
        "ts": time.time(),
        "tool": tool,
        "exercise": exercise,
        "level": level,
        "ok": bool(ok),
        "passed": passed,
        "total": total,
        "mode": mode,
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def load_all(tool: Optional[str] = None) -> List[Event]:
    """All recorded events, optionally filtered to one tool. Malformed
    lines (a torn write) are skipped rather than raising."""
    try:
        with open(STATS_PATH, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    events: List[Event] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        if tool is None or entry.get("tool") == tool:
            events.append(entry)
    return events


def consecutive_fails(tool: str, exercise: str) -> int:
    """How many times in a row (most recent first) `exercise` was graded
    and failed, ignoring --exam attempts — the exam is one-shot per
    exercise anyway, and this is used to decide when to nudge a stuck
    student in practice/training, never during the exam itself."""
    events = [
        e
        for e in load_all(tool)
        if e.get("exercise") == exercise and e.get("mode") != "exam"
    ]
    events.sort(key=lambda e: e.get("ts", 0))
    streak = 0
    for e in reversed(events):
        if e.get("ok"):
            break
        streak += 1
    return streak


def weakest_exercises(tool: str, candidate_names: Sequence[str]) -> List[str]:
    """`candidate_names` the student has failed at least once (in
    practice/training — --exam attempts are excluded, same reasoning as
    consecutive_fails), ranked worst-first: currently on a fail streak
    first, then lowest lifetime pass rate as a tiebreaker. Excludes both
    an exercise never attempted AND one with a spotless record — "weak"
    means "struggled with", not "haven't tried yet" (that's the plain
    exercise list) and not "nailed on the first try either" (that would
    just pad the queue with exercises there's nothing to gain from
    reviewing). Powers `--train weak` / the 'w' key in training_mode()."""
    events = [e for e in load_all(tool) if e.get("mode") != "exam"]
    per_exercise: Dict[str, Dict[str, int]] = {}
    for e in events:
        name = e.get("exercise")
        if not isinstance(name, str) or name not in candidate_names:
            continue
        row = per_exercise.setdefault(name, {"attempts": 0, "passes": 0})
        row["attempts"] += 1
        if e.get("ok"):
            row["passes"] += 1
    weak = [
        name
        for name, row in per_exercise.items()
        if row["passes"] < row["attempts"]
    ]

    def rank_key(name: str) -> Tuple[int, float]:
        row = per_exercise[name]
        streak = consecutive_fails(tool, name)
        pass_rate = row["passes"] / row["attempts"]
        return (-streak, pass_rate)

    return sorted(weak, key=rank_key)


def best_exam_time(tool: str) -> Optional[float]:
    """Fastest recorded full-exam completion (seconds), or None."""
    times = [
        e["seconds"]
        for e in load_all(tool)
        if e.get("mode") == "exam-complete" and "seconds" in e
    ]
    return min(times) if times else None


def record_exam_complete(
    tool: str, seconds: float, attempts: int, score: int
) -> None:
    entry = {
        "ts": time.time(),
        "tool": tool,
        "mode": "exam-complete",
        "seconds": seconds,
        "attempts": attempts,
        "score": score,
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def summarize(tool: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate stats for the `--stats` screen.

    Returns a dict: total attempts, overall pass rate, per-exercise
    (attempts, passes), and the best full-exam time if any.
    """
    events = [e for e in load_all(tool) if e.get("mode") != "exam-complete"]
    completions = [
        e for e in load_all(tool) if e.get("mode") == "exam-complete"
    ]

    per_exercise: Dict[str, Dict[str, int]] = {}
    for e in events:
        name = e.get("exercise")
        if not name:
            continue
        row = per_exercise.setdefault(name, {"attempts": 0, "passes": 0})
        row["attempts"] += 1
        if e.get("ok"):
            row["passes"] += 1

    total_attempts = len(events)
    total_passes = sum(1 for e in events if e.get("ok"))
    best_seconds = min((c["seconds"] for c in completions), default=None)
    return {
        "total_attempts": total_attempts,
        "total_passes": total_passes,
        "pass_rate": (total_passes / total_attempts)
        if total_attempts
        else 0.0,
        "per_exercise": per_exercise,
        "exam_completions": len(completions),
        "best_seconds": best_seconds,
    }


def exercise_status(
    tool: Optional[str], names: Iterable[str]
) -> Dict[str, Dict[str, Any]]:
    """{name: {"status", "attempts", "passes", "last_ts"}} for each of
    `names`, from every recorded grading (exam attempts included — a pass
    in the exam counts as much as one in practice). status is "passed"
    (at least once), "failed" (tried, never passed) or "untried"."""
    names = list(names)
    wanted = set(names)
    rows: Dict[str, Dict[str, Any]] = {
        name: {
            "status": "untried",
            "attempts": 0,
            "passes": 0,
            "last_ts": None,
        }
        for name in names
    }
    for e in load_all(tool):
        name = e.get("exercise")
        if name not in wanted:
            continue
        row = rows[name]
        row["attempts"] += 1
        row["passes"] += 1 if e.get("ok") else 0
        row["last_ts"] = max(row["last_ts"] or 0, e.get("ts", 0))
    for row in rows.values():
        if row["attempts"]:
            row["status"] = "passed" if row["passes"] else "failed"
    return rows


def readiness(
    tool: str, standard_levels: Mapping[int, Sequence[str]]
) -> List[Tuple[int, int, int, List[Tuple[str, Dict[str, Any]]]]]:
    """How exam-ready the student is, level by level: for each level of
    `standard_levels` ({level: [names]} — only what the exam can draw),
    (level, passed_count, total, [(name, status_row), …] sorted by name)."""
    out: List[Tuple[int, int, int, List[Tuple[str, Dict[str, Any]]]]] = []
    for level in sorted(standard_levels):
        names = sorted(standard_levels[level])
        status = exercise_status(tool, names)
        passed = sum(1 for n in names if status[n]["status"] == "passed")
        out.append(
            (level, passed, len(names), [(n, status[n]) for n in names])
        )
    return out


def drill_queue(
    tool: str, candidate_names: Sequence[str], n: int = 5
) -> List[str]:
    """Up to `n` exercises for a short daily drill, from `candidate_names`
    (in the caller's order, e.g. by level):

      1. weak spots first (weakest_exercises(): on a fail streak / low pass
         rate) — but at most half the session, so a drill is never just a
         wall of failures,
      2. then exercises never tried yet, in the given order,
      3. then passed ones, least recently practised first (a light form of
         spaced repetition — what you nailed a month ago is due again),
      4. then more weak spots if the session still isn't full.
    """
    status = exercise_status(tool, candidate_names)
    weak = weakest_exercises(tool, list(candidate_names))
    untried = [
        name for name in candidate_names if status[name]["status"] == "untried"
    ]
    stale = sorted(
        (
            name
            for name in candidate_names
            if status[name]["status"] != "untried" and name not in weak
        ),
        key=lambda name: status[name]["last_ts"] or 0,
    )
    n_first = (n + 1) // 2
    first_weak = weak[:n_first]
    queue: List[str] = []
    for name in first_weak + untried + stale + weak[n_first:]:
        if name not in queue:
            queue.append(name)
    return queue[:n]


def daily_activity(
    tool: str, days: int = 28, now: Optional[float] = None
) -> List[Tuple[int, int]]:
    """[(attempts, passes)] for each of the last `days` days, oldest first
    (today last) — the stats screen's activity chart."""
    now = time.time() if now is None else now
    today = datetime.date.fromtimestamp(now).toordinal()  # local calendar day
    counts = [[0, 0] for _ in range(days)]
    for e in load_all(tool):
        if not e.get("exercise"):
            continue
        age = today - datetime.date.fromtimestamp(e.get("ts", 0)).toordinal()
        if 0 <= age < days:
            counts[days - 1 - age][0] += 1
            counts[days - 1 - age][1] += 1 if e.get("ok") else 0
    return [(c[0], c[1]) for c in counts]


def practice_streak(tool: str, now: Optional[float] = None) -> int:
    """Consecutive days (ending today or yesterday) with at least one
    graded attempt."""
    activity = daily_activity(tool, days=366, now=now)
    days = [attempts > 0 for attempts, _ in activity]
    if not days[-1]:
        days = days[:-1]  # nothing yet today doesn't break a streak
    streak = 0
    for active in reversed(days):
        if not active:
            break
        streak += 1
    return streak


def exam_history(tool: str, n: int = 5) -> List[Event]:
    """The last `n` full-exam completions, newest first."""
    done = [e for e in load_all(tool) if e.get("mode") == "exam-complete"]
    done.sort(key=lambda e: e.get("ts", 0), reverse=True)
    return done[:n]
