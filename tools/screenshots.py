#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate the full-screen UI screenshots in docs/img/ (SVG, straight from
Textual). Needs Textual and a C compiler:

    venv/bin/python tools/screenshots.py

Everything runs against a throwaway HOME with a small, made-up practice
history, so your own ~/.examshell is never read or touched.
"""

import argparse
import asyncio
import os
import random
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "img")
SIZE = (118, 34)

os.environ["HOME"] = tempfile.mkdtemp(prefix="examshell-shots-")
os.environ["EXAMSHELL_NO_UPDATE_CHECK"] = "1"
sys.path.insert(0, ROOT)

from c_exam import examshell as c_shell          # noqa: E402
from examshell import stats                            # noqa: E402
from examshell.tui.app import ExamShellApp             # noqa: E402

# A first_word that forgets tabs — passes the curated cases, fails the fuzz.
BUGGY_FIRST_WORD = r"""#include <unistd.h>

int	main(int argc, char **argv)
{
	int	i;

	i = 0;
	if (argc == 2)
	{
		while (argv[1][i] == ' ')
			i++;
		while (argv[1][i] && argv[1][i] != ' ')
			write(1, &argv[1][i++], 1);
	}
	write(1, "\n", 1);
	return (0);
}
"""


def fake_history():
    """A few weeks of plausible practice so readiness/stats have content."""
    rng = random.Random(42)
    now = time.time()
    standard = [(lvl, n) for lvl, names in sorted(c_shell.STANDARD_LEVELS.items())
                for n in sorted(names)]
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
    def __init__(self, ts):
        self.ts = ts

    def __enter__(self):
        self._orig = stats.time.time
        stats.time.time = lambda: self.ts

    def __exit__(self, *exc):
        stats.time.time = self._orig


def config(rendu, **overrides):
    values = dict(rendu=rendu, timeout=5, cc="cc", strict_norm=False, show_fails=3, diff=False,
                  seed=4, fuzz=8, valgrind=False, strict_valgrind=False, strict_forbidden=False,
                  strict=False, relaxed=False, time_limit=180, no_update_check=True, blind=False)
    values.update(overrides)
    return c_shell.Config(argparse.Namespace(**values))


async def shoot():
    os.makedirs(OUT, exist_ok=True)
    rendu = tempfile.mkdtemp()
    with open(os.path.join(rendu, "first_word.c"), "w") as fh:
        fh.write(BUGGY_FIRST_WORD)
    fake_history()

    app = ExamShellApp(c_shell, config(rendu))
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-menu.svg"))

        app.push_screen(_screen("ReadinessScreen"))
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-readiness.svg"))
        await pilot.press("escape")

        app.push_screen(_screen("StatsScreen"))
        await pilot.pause()
        app.save_screenshot(os.path.join(OUT, "tui-stats.svg"))
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
        exam.run.session.start_time -= 38 * 60 + 12          # 38 minutes in
        await pilot.press("t")                               # a stub: compiles, prints nothing
        await pilot.pause()
        await pilot.press("g")
        await app.workers.wait_for_complete()
        await pilot.pause(1.1)
        app.save_screenshot(os.path.join(OUT, "tui-exam.svg"))
    shutil.rmtree(rendu, ignore_errors=True)
    print("screenshots written to", OUT)


def _screen(name, *args):
    from examshell.tui import app as tui_app
    return getattr(tui_app, name)(*args)


if __name__ == "__main__":
    asyncio.run(shoot())
