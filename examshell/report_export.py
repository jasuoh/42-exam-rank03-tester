#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_export.py  ·  Markdown exam session report, shared by both testers

Writes a small, human-readable summary of one exam run to
~/.examshell/reports/ — something a student can keep, diff between
attempts, or paste into a study log. Auto-generated at the end of every
exam run (passed or aborted); never required reading, purely a record.

Best-effort like the rest of this package: a write failure is a missed
convenience, never a reason to fail the exam.
"""

import os
import re
import time

from .settings import DATA_DIR

REPORTS_DIR = os.path.join(DATA_DIR, "reports")

# session.login is free-form student input (see ui.ask("  Login...") in
# both examshell.py's) spliced directly into a filename below — a stray
# "/" or a ".." component in it must never let the report escape
# REPORTS_DIR.
_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")

# Which tester wrote this report, by the `tool` tag it files everything
# under (see examshell/ranks.py and c_exam/examshell.py's TOOL). An unknown tag
# is named rather than guessed at — better a bare "py09" in one line of a
# report than a report that confidently claims the wrong rank.
TOOL_LABELS = {
    "py": "Python (Rank 03)",
    "py04": "Python (Rank 04)",
    "py05": "Python (Rank 05)",
    "c": "C (Rank 02)",
}


def _safe_login(login):
    safe = _UNSAFE_FILENAME_RE.sub("_", login).strip("._")
    return safe or "student"


def write_exam_report(tool, session, n_levels, passed, achievements=()):
    """Write the report, return its path on success or None on failure."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, "%s_%s_%s.md" % (tool, stamp, _safe_login(session.login)))

    lines = []
    title = "Exam PASSED" if passed else "Exam aborted"
    lines.append("# %s — %s" % (title, session.login))
    lines.append("")
    lines.append("- Date: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("- Tester: %s" % TOOL_LABELS.get(tool, tool))
    lines.append("- Score: %d/100" % session.score())
    lines.append("- Levels cleared: %d/%d" % (len(session.passed), n_levels))
    lines.append("- Total time: %s" % session.elapsed())
    lines.append("- Total attempts: %d" % session.attempts)
    if achievements:
        lines.append("- Achievements: " + ", ".join(achievements))
    lines.append("")
    lines.append("## Levels")
    lines.append("")
    lines.append("| Level | Exercise | Attempts | Time |")
    lines.append("|---|---|---|---|")
    for level, name, attempts, seconds in session.history:
        secs = int(seconds)
        lines.append("| %d | %s | %d | %02d:%02d:%02d |"
                     % (level, name, attempts,
                        secs // 3600, (secs % 3600) // 60, secs % 60))
    lines.append("")

    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return path
    except OSError:
        return None
