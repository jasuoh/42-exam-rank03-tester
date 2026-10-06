#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feedback.py  ·  `examshell --feedback [exam|bug|idea]`

Opens the right GitHub issue form with what we already know filled in —
tester version, which exam, the OS, the exercise you were on — so giving
feedback takes seconds. Nothing is ever sent from here: it only builds a
link; the student reads the form and submits it (or doesn't) themselves.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Dict, Optional
from urllib.parse import urlencode

from .version import REPO_URL, __version__

ISSUES_URL = REPO_URL + "/issues/new"

# kind -> (issue form file, title prefix) — see .github/ISSUE_TEMPLATE/
KINDS = {
    "exam": ("exam_mismatch.yml", "[exam] "),
    "bug": ("bug_report.yml", "[bug] "),
    "idea": ("feedback.yml", "[feedback] "),
}
KIND_LABELS = (
    ("exam", "An exercise differs from my real exam"),
    ("bug", "The tester itself misbehaves"),
    ("idea", "Feedback / an idea"),
)


def environment() -> str:
    """'Linux 6.8 · Python 3.12.3 · cc' — the bug form's env field."""
    return "%s %s · Python %s" % (
        platform.system(),
        platform.release(),
        platform.python_version(),
    )


def issue_url(
    kind: str, tester_label: str = "", exercise: Optional[str] = None
) -> str:
    """The prefilled issue-form link. GitHub fills a form field from a query
    parameter named after that field's `id`."""
    template, prefix = KINDS[kind]
    params: Dict[str, str] = {
        "template": template,
        "title": prefix + (exercise or ""),
    }
    version = "examshell %s" % __version__
    if kind == "exam":
        params.update(tester=tester_label, version=version)
        if exercise:
            params["exercise"] = exercise
    elif kind == "bug":
        params.update(version=version, env=environment())
    return ISSUES_URL + "?" + urlencode(params)


def can_open_browser() -> bool:
    """Only hand the link to a browser where a graphical one can exist — on
    a bare Linux console `webbrowser` would start a text browser (lynx, w3m)
    right inside the terminal session."""
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def open_in_browser(url: str) -> bool:
    """True when a browser was asked to open `url`."""
    if not can_open_browser():
        return False
    import webbrowser

    try:
        return bool(webbrowser.open(url))
    except webbrowser.Error:
        return False
