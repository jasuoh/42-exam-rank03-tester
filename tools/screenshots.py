#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate the full-screen UI screenshots in docs/img/ (SVG, straight from
Textual). Needs Textual and a C compiler:

    venv/bin/python tools/screenshots.py

Everything runs against a throwaway HOME with a small, made-up practice
history, so your own ~/.examshell is never read or touched.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import shutil
import sys
import tempfile
import time
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "img")
SIZE = (140, 38)

os.environ["HOME"] = tempfile.mkdtemp(prefix="examshell-shots-")
os.environ["EXAMSHELL_NO_UPDATE_CHECK"] = "1"
sys.path.insert(0, ROOT)

from c_exam import bank as c_bank  # noqa: E402
from c_exam import examshell as c_shell  # noqa: E402
from examshell import stats  # noqa: E402
from examshell.tui.app import ExamScreen, ExamShellApp  # noqa: E402
from textual.screen import Screen  # noqa: E402

# A first_word that forgets tabs — passes the curated cases, fails the fuzz.
BUGGY_FIRST_WORD = """#include <unistd.h>

int\tmain(int argc, char **argv)
{
\tint\ti;

\ti = 0;
\tif (argc == 2)
\t{
\t\twhile (argv[1][i] == ' ')
\t\t\ti++;
\t\twhile (argv[1][i] && argv[1][i] != ' ')
\t\t\twrite(1, &argv[1][i++], 1);
\t}
\twrite(1, "\\n", 1);
\treturn (0);
}
"""


def fake_history() -> None:
    """A few weeks of plausible practice so readiness/stats have content."""
    rng = random.Random(42)
    now = time.time()
    standard = [
        (lvl, n)
        for lvl, names in sorted(c_bank.STANDARD_LEVELS.items())
        for n in sorted(names)
    ]
    for i, (lvl, name) in enumerate(standard):
        if rng.random() < 0.55 - 0.1 * lvl:
            continue
        for _ in range(rng.randint(1, 4)):
            ts = now - rng.randint(0, 24) * 86400 - rng.randint(0, 5000)
            ok = rng.random() < 0.75 - 0.12 * lvl
            with _clock(ts):
                stats.record("c", name, lvl, ok, 1 if ok else 0, 1, "practice")
    for days in (0, 1, 2, 3):
        with _clock(now - days * 86400 - 60):
            stats.record("c", "rotone", 1, True, 6, 6, "practice")
    with _clock(now - 3 * 86400):
        stats.record_exam_complete("c", 2 * 3600 + 17 * 60, 7, 100)


class _clock(object):
    def __init__(self, ts: float) -> None:
        self.ts = ts

    def __enter__(self) -> None:
        self._orig = time.time
        time.time = lambda: self.ts

    def __exit__(self, *exc: object) -> None:
        time.time = self._orig


def config(rendu: str, **overrides: Any) -> c_shell.Config:
    values = dict(
        rendu=rendu,
        timeout=5,
        cc="cc",
        strict_norm=False,
        show_fails=3,
        diff=False,
        seed=4,
        fuzz=8,
        valgrind=False,
        strict_valgrind=False,
        strict_forbidden=False,
        strict=False,
        relaxed=False,
        time_limit=180,
        no_update_check=True,
        blind=False,
    )
    values.update(overrides)
    return c_shell.Config(argparse.Namespace(**values))


async def shoot() -> None:
    os.makedirs(OUT, exist_ok=True)
    # a relative c_rendu/, as in real use: the subject pane shows its path
    workdir = tempfile.mkdtemp()
    os.chdir(workdir)
    rendu = "c_rendu"
    os.makedirs(rendu)
    with open(os.path.join(rendu, "first_word.c"), "w") as fh:
        fh.write(BUGGY_FIRST_WORD)
    fake_history()

    app = ExamShellApp(c_shell, config(rendu))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-menu.svg"))

        app.push_screen(_screen("ProgressScreen"))
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-progress.svg"))
        await pilot.press("escape")

        app.push_screen(_screen("PracticeScreen", "first_word"))
        await pilot.pause()
        await pilot.press("g")
        await app.workers.wait_for_complete()
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-practice.svg"))

    app = ExamShellApp(c_shell, config(rendu, seed=11), start="exam")
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        await pilot.press(*"alice", "enter")
        await pilot.pause()
        exam = app.screen
        assert isinstance(exam, ExamScreen)
        session = exam.run.session
        assert session.start_time is not None
        session.start_time -= 38 * 60 + 12  # 38 minutes in
        # the full helper stub (the exam's own `t` writes a bare one that
        # doesn't compile yet): compiles, prints nothing
        c_shell.write_stub(exam.ex_name, config(rendu, relaxed=True))
        await pilot.pause()
        await pilot.press("g")
        await app.workers.wait_for_complete()
        await pilot.pause(1.1)
        app.save_screenshot(os.path.join(OUT, "tui-exam.svg"))
    os.chdir(ROOT)
    shutil.rmtree(workdir, ignore_errors=True)
    print("screenshots written to", OUT)


def _screen(name: str, *args: Any) -> Screen[Any]:
    from examshell.tui import app as tui_app

    screen: Screen[Any] = getattr(tui_app, name)(*args)
    return screen


if __name__ == "__main__":
    asyncio.run(shoot())
