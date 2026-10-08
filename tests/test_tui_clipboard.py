#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for examshell/tui/clipboard.py — which tool copies/pastes
where. Runs without Textual; no real clipboard tool is ever started."""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from typing import Dict, List, Optional, Sequence
from unittest import mock

from examshell.tui import clipboard


def _tools(
    env: Dict[str, str], platform: str = "linux", have: str = ""
) -> Optional[Sequence[List[str]]]:
    """clipboard._tools() with this environment and these tools installed
    (space-separated names)."""
    installed = set(have.split())
    with mock.patch.dict("os.environ", env, clear=True), mock.patch.object(
        sys, "platform", platform
    ), mock.patch.object(
        shutil,
        "which",
        side_effect=lambda name: (
            "/usr/bin/" + name if name in installed else None
        ),
    ):
        return clipboard._tools()


class ToolChoiceTests(unittest.TestCase):
    def test_macos_uses_pbcopy(self) -> None:
        tools = _tools({}, "darwin", "pbcopy")
        self.assertEqual(tools and tools[0], ["pbcopy"])

    def test_wayland_prefers_wl_copy(self) -> None:
        env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
        tools = _tools(env, have="wl-copy xclip")
        self.assertEqual(tools and tools[0], ["wl-copy"])

    def test_x11_falls_back_to_xclip_then_xsel(self) -> None:
        env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}
        tools = _tools(env, have="xclip")
        self.assertEqual(tools and tools[0][0], "xclip")
        tools = _tools({"DISPLAY": ":0"}, have="xsel")
        self.assertEqual(tools and tools[0][0], "xsel")

    def test_nothing_without_a_display_a_tool_or_over_ssh(self) -> None:
        self.assertIsNone(_tools({}, have="xclip wl-copy"))
        self.assertIsNone(_tools({"DISPLAY": ":0"}))
        self.assertIsNone(
            _tools(
                {"DISPLAY": ":0", "SSH_CONNECTION": "1 2 3 4"}, have="xclip"
            )
        )


class CopyPasteTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(
            clipboard, "_tools", return_value=(["cp-tool"], ["paste-tool"])
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_copy_feeds_the_text_to_the_tool(self) -> None:
        with mock.patch.object(subprocess, "run") as run:
            self.assertTrue(clipboard.copy("héllo"))
        self.assertEqual(run.call_args[0][0], ["cp-tool"])
        self.assertEqual(run.call_args[1]["input"], "héllo".encode("utf-8"))
        # never a pipe on stdout: wl-copy/xclip keep it open in background
        self.assertIs(run.call_args[1]["stdout"], subprocess.DEVNULL)

    def test_paste_returns_the_tools_output(self) -> None:
        done = subprocess.CompletedProcess(["paste-tool"], 0, b"from os\n")
        with mock.patch.object(subprocess, "run", return_value=done):
            self.assertEqual(clipboard.paste(), "from os\n")

    def test_a_failing_tool_is_not_an_error(self) -> None:
        for error in (
            OSError("gone"),
            subprocess.TimeoutExpired("x", 2),
            subprocess.CalledProcessError(1, "x"),
        ):
            with mock.patch.object(subprocess, "run", side_effect=error):
                self.assertFalse(clipboard.copy("x"))
                self.assertIsNone(clipboard.paste())


if __name__ == "__main__":
    unittest.main()
