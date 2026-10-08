#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examshell/tui/crashlog.py  ·  what the app leaves behind when it crashes

When the app dies on an unexpected error, the terminal comes back and the
traceback scrolls away. So the app writes it to ~/.examshell/crash.log
first, and the next start asks whether to report it (a prefilled GitHub
bug form — nothing is sent automatically). Answered either way, the log is
renamed to crash.log.seen and kept for whoever wants to look.

Best-effort like everything under ~/.examshell: a failing write never
hides the original error.
"""

from __future__ import annotations

import os
import platform
import sys
import time
import traceback
from typing import Optional

from .. import settings
from ..version import __version__

MAX_REPORT_LINES = 25  # what goes into the issue form (URLs have a limit)


def _path() -> str:
    return os.path.join(settings.DATA_DIR, "crash.log")


def record(error: BaseException, where: str = "") -> None:
    """Write `error` with its traceback and the environment to crash.log."""
    lines = [
        "ExamShell %s crashed at %s" % (__version__, time.strftime("%c")),
        "where: %s" % (where or "?"),
        "Python %s on %s" % (sys.version.split()[0], platform.platform()),
        "",
    ] + traceback.format_exception(type(error), error, error.__traceback__)
    try:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as fh:
            fh.write("\n".join(line.rstrip("\n") for line in lines) + "\n")
    except OSError:
        pass


def pending() -> Optional[str]:
    """The crash log of the last session, if it hasn't been answered yet."""
    try:
        with open(_path(), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def report_text(log: str) -> str:
    """The log, cut to what fits into the issue form: its head (version,
    environment) and the end of the traceback (where it broke)."""
    lines = log.rstrip("\n").splitlines()
    if len(lines) <= MAX_REPORT_LINES:
        return "\n".join(lines)
    keep = MAX_REPORT_LINES - 5
    head, tail = lines[:4], lines[-keep:]
    return "\n".join(head + ["…"] + tail)


def mark_seen() -> None:
    try:
        os.replace(_path(), _path() + ".seen")
    except OSError:
        pass
