#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examshell/tui  ·  the full-screen terminal interface (optional)

Built on Textual (Python 3.9+), which `make` installs. The
testers never import anything below this package's __init__ unless the
student asked for `--tui` AND it is available — the zero-dependency,
Python 3.8 line-based UI stays the default and the fallback.
"""

from __future__ import annotations

import importlib.util
import sys
from typing import Dict, Optional, Tuple, Union

from .._types import Tester, TesterConfig

MIN_PYTHON = (3, 9)


def available() -> bool:
    """True when the full-screen UI can run here."""
    return (
        sys.version_info >= MIN_PYTHON
        and importlib.util.find_spec("textual") is not None
    )


def why_unavailable() -> str:
    if sys.version_info < MIN_PYTHON:
        return (
            "the full-screen UI needs Python 3.9+ (this is %d.%d)"
            % sys.version_info[:2]
        )
    from ..doctor import extras_command

    return "the full-screen UI needs Textual — `%s`" % extras_command()


def run(
    sh: Tester,
    cfg: TesterConfig,
    start: Union[None, str, Tuple[str, str]] = None,
    rendus: Optional[Dict[str, str]] = None,
) -> int:
    """Run the app for tester module `sh`. `start` is None (main menu),
    "exam", or ("practice", exercise_name); `rendus` the other testers'
    solution folders by SYNC_SLOT. Returns a process exit code."""
    from .. import settings
    from .app import ExamShellApp

    # never picked an exam (switch_exam / --rank remember it): ask once
    ask_exam = start is None and not settings.load_config().get("tester")
    ExamShellApp(
        sh, cfg, start=start, ask_exam=ask_exam, rendus=rendus
    ).run()
    return 0
