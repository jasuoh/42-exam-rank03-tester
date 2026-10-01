#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examshell/tui  ·  the full-screen terminal interface (optional)

Built on Textual, which needs Python 3.9+ and `pip install textual`. The
testers never import anything below this package's __init__ unless the
student asked for `--tui` AND it is available — the zero-dependency,
Python 3.8 line-based UI stays the default and the fallback.
"""

import importlib.util
import sys

MIN_PYTHON = (3, 9)


def available():
    """True when the full-screen UI can run here."""
    return (sys.version_info >= MIN_PYTHON
            and importlib.util.find_spec("textual") is not None)


def why_unavailable():
    if sys.version_info < MIN_PYTHON:
        return "the full-screen UI needs Python 3.9+ (this is %d.%d)" % sys.version_info[:2]
    return "the full-screen UI needs Textual — `pip install textual` (or `make install`)"


def run(sh, cfg, start=None):
    """Run the app for tester module `sh`. `start` is None (main menu),
    "exam", or ("practice", exercise_name). Returns a process exit code."""
    from .app import ExamShellApp
    ExamShellApp(sh, cfg, start=start).run()
    return 0
