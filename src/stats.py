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

import json
import os
import time

from .settings import DATA_DIR

STATS_PATH = os.path.join(DATA_DIR, "stats.jsonl")


def record(tool, exercise, level, ok, passed, total, mode):
    """Append one grading event. `tool` is "py" or "c"; `mode` is
    "exam" / "practice" / "train" / "grade" / "exam-complete"."""
    entry = {
        "ts": time.time(), "tool": tool, "exercise": exercise,
        "level": level, "ok": bool(ok), "passed": passed, "total": total,
        "mode": mode,
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def load_all(tool=None):
    """All recorded events, optionally filtered to one tool. Malformed
    lines (a torn write) are skipped rather than raising."""
    try:
        with open(STATS_PATH, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if tool is None or entry.get("tool") == tool:
            events.append(entry)
    return events


def consecutive_fails(tool, exercise):
    """How many times in a row (most recent first) `exercise` was graded
    and failed, ignoring --exam attempts — the exam is one-shot per
    exercise anyway, and this is used to decide when to nudge a stuck
    student in practice/training, never during the exam itself."""
    events = [e for e in load_all(tool)
             if e.get("exercise") == exercise and e.get("mode") != "exam"]
    events.sort(key=lambda e: e.get("ts", 0))
    streak = 0
    for e in reversed(events):
        if e.get("ok"):
            break
        streak += 1
    return streak


def weakest_exercises(tool, candidate_names):
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
    per_exercise = {}
    for e in events:
        name = e.get("exercise")
        if name not in candidate_names:
            continue
        row = per_exercise.setdefault(name, {"attempts": 0, "passes": 0})
        row["attempts"] += 1
        if e.get("ok"):
            row["passes"] += 1
    weak = [name for name, row in per_exercise.items() if row["passes"] < row["attempts"]]

    def rank_key(name):
        row = per_exercise[name]
        streak = consecutive_fails(tool, name)
        pass_rate = row["passes"] / row["attempts"]
        return (-streak, pass_rate)

    return sorted(weak, key=rank_key)


def best_exam_time(tool):
    """Fastest recorded full-exam completion (seconds), or None."""
    times = [e["seconds"] for e in load_all(tool)
             if e.get("mode") == "exam-complete" and "seconds" in e]
    return min(times) if times else None


def record_exam_complete(tool, seconds, attempts, score):
    entry = {
        "ts": time.time(), "tool": tool, "mode": "exam-complete",
        "seconds": seconds, "attempts": attempts, "score": score,
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def summarize(tool=None):
    """Aggregate stats for the `--stats` screen.

    Returns a dict: total attempts, overall pass rate, per-exercise
    (attempts, passes), and the best full-exam time if any.
    """
    events = [e for e in load_all(tool) if e.get("mode") != "exam-complete"]
    completions = [e for e in load_all(tool) if e.get("mode") == "exam-complete"]

    per_exercise = {}
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
        "pass_rate": (total_passes / total_attempts) if total_attempts else 0.0,
        "per_exercise": per_exercise,
        "exam_completions": len(completions),
        "best_seconds": best_seconds,
    }


def exercise_status(tool, names):
    """{name: {"status", "attempts", "passes", "last_ts"}} for each of
    `names`, from every recorded grading (exam attempts included — a pass
    in the exam counts as much as one in practice). status is "passed"
    (at least once), "failed" (tried, never passed) or "untried"."""
    wanted = set(names)
    rows = {name: {"status": "untried", "attempts": 0, "passes": 0, "last_ts": None}
            for name in names}
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


def readiness(tool, standard_levels):
    """How exam-ready the student is, level by level: for each level of
    `standard_levels` ({level: [names]} — only what the exam can draw),
    (level, passed_count, total, [(name, status_row), …] sorted by name)."""
    out = []
    for level in sorted(standard_levels):
        names = sorted(standard_levels[level])
        status = exercise_status(tool, names)
        passed = sum(1 for n in names if status[n]["status"] == "passed")
        out.append((level, passed, len(names), [(n, status[n]) for n in names]))
    return out


def drill_queue(tool, candidate_names, n=5):
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
    untried = [name for name in candidate_names if status[name]["status"] == "untried"]
    stale = sorted((name for name in candidate_names
                    if status[name]["status"] != "untried" and name not in weak),
                   key=lambda name: status[name]["last_ts"] or 0)
    first_weak = weak[:(n + 1) // 2]
    queue = []
    for name in first_weak + untried + stale + weak[len(first_weak):]:
        if name not in queue:
            queue.append(name)
    return queue[:n]
