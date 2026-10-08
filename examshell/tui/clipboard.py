#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examshell/tui/clipboard.py  ·  the system clipboard, where OSC 52 isn't enough

Textual copies with the OSC 52 escape sequence only: the terminal has to
put the text on the clipboard itself. Ghostty, kitty, iTerm2 or WezTerm
do; GNOME Terminal (and every other VTE terminal), macOS Terminal and
plain xterm silently ignore it, so ctrl+c in the full-screen app copied
nothing there. And ctrl+v in an input field only pasted what had been
copied *inside* the app, never the system clipboard.

So, on a local session, copying also goes through the platform's own
tool (pbcopy, wl-copy, xclip or xsel) and pasting reads from it. Over
ssh those would reach the remote machine's clipboard, not the student's,
so there only OSC 52 is used. Best-effort: no tool, or a failing one,
just means OSC 52 alone, like before.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence

TIMEOUT = 2  # seconds — a stuck clipboard tool must not freeze the app

# (copy command, paste command) per clipboard system, in order of preference
_DARWIN = (["pbcopy"], ["pbpaste"])
_WAYLAND = (["wl-copy"], ["wl-paste", "--no-newline"])
_X11 = (
    (
        ["xclip", "-selection", "clipboard"],
        ["xclip", "-selection", "clipboard", "-o"],
    ),
    (["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"]),
)


def _candidates() -> List[Sequence[List[str]]]:
    env = os.environ
    if env.get("SSH_CONNECTION") or env.get("SSH_TTY"):
        return []
    if sys.platform == "darwin":
        return [_DARWIN]
    found: List[Sequence[List[str]]] = []
    if env.get("WAYLAND_DISPLAY"):
        found.append(_WAYLAND)
    if env.get("DISPLAY"):  # also XWayland, when wl-copy isn't installed
        found.extend(_X11)
    return found


def _tools() -> Optional[Sequence[List[str]]]:
    """(copy, paste) commands of the first installed tool, or None."""
    for tools in _candidates():
        if shutil.which(tools[0][0]):
            return tools
    return None


def copy(text: str) -> bool:
    """Put `text` on the system clipboard. False when that wasn't
    possible here (OSC 52 is then all there is)."""
    tools = _tools()
    if tools is None:
        return False
    try:
        # no pipes besides stdin: wl-copy and xclip stay in the background
        # to serve the clipboard, and would hold an open stdout forever
        subprocess.run(
            tools[0],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def paste() -> Optional[str]:
    """The system clipboard's text, or None when it can't be read here."""
    tools = _tools()
    if tools is None:
        return None
    try:
        done = subprocess.run(
            tools[1],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode("utf-8", errors="replace")
