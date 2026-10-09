#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   EXAMSHELL  ·  42 Common Core  ·  Python Exam Ranks 03-05   ║
╚══════════════════════════════════════════════════════════════╝

A practice tester in the style of the real examshell / moulinette.

  · every level in the exact order of the real exam (1 -> N)
  · one random exercise per level, drawn from that level's pool
  · every exercise graded against many curated cases + fuzz tests
  · you only move up at 100%
  · graded in a subprocess sandbox with a per-call timeout

    python3 -m examshell                 # interactive menu (Rank 03)
    python3 -m examshell --rank 04       # the Rank 04 pool instead
    python3 -m examshell --help          # every flag

Put your solution in `rendu/<exercise_name>.py` and define the required
function. The folder is created for you.

Which rank is active decides the exercise bank, the number of levels and
the tag this student's stats/saved exam/reports are filed under — see
ranks.py and use_rank() below. Everything else is rank-agnostic.
"""

from __future__ import annotations

import argparse
import copy
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import grader, ranks, settings, shell_common, ui
from ._types import Exercise

# Used by the shared flow (examshell/shell_common.py), not here — kept
# reachable as examshell.<name> for callers and tests that patch them through
# it.
from . import (  # noqa: F401
    hints,
    session_store,
    stats,
)
from .bank_common import signature_for as _signature_for
from .bank_common import signature_of as _signature_of
from .shell_common import (  # noqa: F401
    DRILL_SIZE,
    countdown,
    draw,
    fmt_duration,
    time_left,
)
from .training_bank import (
    DIFFICULTIES,
    TRAINING_BY_DIFFICULTY,
    TRAINING_EXERCISES,
)
from .shell_common import (
    ExerciseEntry,
    GradingJob,
    Session as _Session,
    TrainingEntry,
)
from .version import __version__

RENDU_DIR = "rendu"
STUB_SAMPLE_CASES = 3  # curated cases embedded as a quick self-check in a stub


# The active rank's pools, rebound by use_rank() below. They start out on
# the default rank — exactly what use_rank() with no argument sets.
RANK: ranks.Rank = ranks.get()
TOOL: str = RANK.tool
EXERCISES: Dict[str, Exercise] = RANK.exercises
LEVELS: Dict[int, List[str]] = RANK.levels
N_LEVELS: int = RANK.n_levels
STANDARD_LEVELS: Dict[int, List[str]] = RANK.standard_levels
ALL_EXERCISES: Dict[str, Exercise] = RANK.all_exercises()


def use_rank(value: object = None) -> ranks.Rank:
    """Point this module at one exam rank, and return it.

    The names it rebinds are the ones the rest of the module reads as
    plain globals — a rank switch is therefore one assignment each, and
    nothing below has to thread a rank argument through. Called once at
    startup (see main()) and again whenever the student switches rank from
    the menu.

    ALL_EXERCISES is every exercise from both pools, keyed by name — used
    wherever the code only needs "the exercise dict for this name" and
    doesn't care which pool it came from (resolving, grading, showing the
    subject, creating a stub). Exam-only concerns (level draws, the level
    progression) keep using EXERCISES/LEVELS directly, so the training
    pool can never be drawn into an exam run.
    """
    global \
        RANK, \
        TOOL, \
        EXERCISES, \
        LEVELS, \
        N_LEVELS, \
        STANDARD_LEVELS, \
        ALL_EXERCISES
    RANK = ranks.get(value)
    TOOL = RANK.tool  # tags saved config/stats/reports — vs c_exam's "c"
    EXERCISES = RANK.exercises
    LEVELS = RANK.levels
    N_LEVELS = RANK.n_levels
    STANDARD_LEVELS = RANK.standard_levels
    ALL_EXERCISES = RANK.all_exercises()
    return RANK


def banner() -> None:
    """ui.banner(), told which rank the student is in."""
    ui.banner(subtitle="%s  ·  Common Core" % RANK.label)


class Config(object):
    """Everything the flags can change, in one place."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.rendu: str = args.rendu
        self.timeout: int = args.timeout
        self.fuzz: int = args.fuzz
        self.strict_imports: bool = args.strict_imports or args.strict
        self.show_fails: int = args.show_fails
        self.diff: bool = args.diff
        self.seed: Optional[int] = args.seed
        # Exam-only realism, see exam_config() / exam_commands().
        self.relaxed: bool = getattr(args, "relaxed", False)
        self.time_limit: Optional[int] = getattr(args, "time_limit", None)
        self.blind: bool = getattr(args, "blind", False)
        # forced on in the exam
        self.bare_stub: bool = getattr(args, "bare_stub", False)
        self.no_update_check: bool = getattr(args, "no_update_check", False)


# ══════════════════════════════════════════════════════════════
#  TESTER HOOKS  ·  what examshell/shell_common.py needs from this tester
# ══════════════════════════════════════════════════════════════
_SH = sys.modules[__name__]

PROG = shell_common.command_name("examshell", "examshell")
# which folder of the sync repo this tester's --rendu maps to
# (examshell/sync.py)
SYNC_SLOT = "rendu"
SOURCE_EXT = ".py"
EXAM_PROMPT = "exam"
PRACTICE_PROMPT = "practice"
# Config flags the exam forces on unless --relaxed: the real moulinette
# allows no import at all.
STRICT_EXAM_FLAGS = (
    "strict_imports",
    "bare_stub",
)  # bare_stub: see write_stub()

EXAM_COMMANDS = [
    ("grademe", "test your solution (you advance only at 100%)"),
    ("subject", "show the assignment again"),
    ("status", "show your current progress"),
    ("new", "draw a different exercise for this level"),
    ("stub", "create an empty solution file for this exercise"),
    ("quit", "abort the exam"),
]

PRACTICE_COMMANDS = [
    ("grademe", "test your solution"),
    ("subject", "show the assignment again"),
    ("stub", "create an empty solution file for this exercise"),
    ("feedback", "this exercise differs from your real exam? tell us"),
    ("back", "return to the menu"),
]


def Session(login: Optional[str] = None) -> _Session:
    """A fresh exam session, scored against the active rank's level count."""
    return shell_common.Session(login, N_LEVELS)


def prepare_grading(
    ex_name: str, rng: random.Random, cfg: Config
) -> GradingJob:
    """Build this exercise's test plan (curated + fuzz, expected values from
    the oracle) — raises grader.BankError if the bank itself is broken."""
    ex = ALL_EXERCISES[ex_name]
    plan = grader.build_plan(ex_name, ex, rng, cfg.fuzz)
    return shell_common.GradingJob(
        grader.plan_size(plan),
        lambda: grader.grade(
            ex_name,
            ex,
            cfg.rendu,
            timeout=cfg.timeout,
            strict_imports=cfg.strict_imports,
            plan=plan,
        ),
    )


def grading_notes(cfg: Config) -> List[str]:
    """Warnings to show before grading — none for the Python tester."""
    return []


# ══════════════════════════════════════════════════════════════
#  THE SHARED FLOW  ·  see examshell/shell_common.py
# ══════════════════════════════════════════════════════════════
def grade_exercise(
    ex_name: str, rng: random.Random, cfg: Config, mode: str = "practice"
) -> bool:
    """Grade one exercise, render the report, return True when it is 100%."""
    return shell_common.grade_exercise(_SH, ex_name, rng, cfg, mode)


def grade_all(cfg: Config) -> bool:
    return shell_common.grade_all(_SH, cfg)


def exercise_entries() -> List[ExerciseEntry]:
    return shell_common.exercise_entries(_SH)


def training_entries() -> List[TrainingEntry]:
    return shell_common.training_entries(_SH)


def show_subject(
    ex_name: str, cfg: Config, session: Optional[_Session] = None
) -> None:
    shell_common.show_subject(_SH, ex_name, cfg, session)


def exam_config(cfg: Config) -> Config:
    return shell_common.exam_config(_SH, cfg)


def exam_commands(cfg: Config) -> List[Tuple[str, str]]:
    return shell_common.exam_commands(_SH, cfg)


def exam_mode(cfg: Config) -> None:
    shell_common.exam_mode(_SH, cfg)


def exam_summary(
    session: _Session, passed: bool, timed_out: bool = False
) -> None:
    shell_common.exam_summary(_SH, session, passed, timed_out)


def practice_one(
    ex_name: str, cfg: Config, rng: random.Random, mode: str = "practice"
) -> None:
    shell_common.practice_one(_SH, ex_name, cfg, rng, mode)


def practice_mode(cfg: Config, ex_name: Optional[str] = None) -> None:
    shell_common.practice_mode(_SH, cfg, ex_name)


def training_mode(
    cfg: Config,
    ex_name: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> None:
    shell_common.training_mode(_SH, cfg, ex_name, difficulty)


def list_mode(interactive: bool = True) -> None:
    shell_common.list_mode(_SH, interactive)


def training_list_mode(interactive: bool = True) -> None:
    shell_common.training_list_mode(_SH, interactive)


def show_stats() -> None:
    shell_common.show_stats(_SH)


def readiness_mode(interactive: bool = True) -> None:
    shell_common.readiness_mode(_SH, interactive)


def drill_mode(cfg: Config, n: int = DRILL_SIZE) -> None:
    shell_common.drill_mode(_SH, cfg, n)


def main_menu(cfg: Config) -> None:
    shell_common.main_menu(_SH, cfg)


def resolve_exercise(name: str) -> Optional[str]:
    """Accept the exact name, or a unique suffix like 'inter'. Searches both
    the exam pool and the training pool."""
    return shell_common.resolve_exercise(_SH, name, "py_")


# ══════════════════════════════════════════════════════════════
#  STUB
# ══════════════════════════════════════════════════════════════
STUB_TEMPLATE = """\
# {name} — 42 Exam {rank}
# {assignment}

{signature}
    pass


if __name__ == "__main__":
    # Quick self-check — run this file directly for instant feedback.
    # NOT the real grader: grademe (g in the app) also covers
    # dozens of edge cases and randomised inputs these examples don't.
    _tests = [
{cases_block}
    ]
    _ok = 0
    for _args, _expected in _tests:
        try:
            _got = {function}(*_args)
        except Exception as exc:
            print("FAIL", _args, "-> raised", type(exc).__name__ + ":", exc)
            continue
        if _got == _expected:
            _ok += 1
            print("ok  ", _args, "->", _got)
        else:
            print("FAIL", _args, "-> got", _got, "expected", _expected)
    print("%d/%d quick checks passed" % (_ok, len(_tests)))
"""


# The same stub for a subject that asks for more than one function (see
# grader.parts_of()). Kept as its own template rather than generalising
# the one above: every row of the self-check has to say which function it
# calls, and paying that cost on the single-function stub — which is the
# overwhelming majority — would make the common case harder to read for
# no gain.
STUB_MULTI_TEMPLATE = """\
# {name} — 42 Exam {rank}
# {assignment}

{defs_block}

if __name__ == "__main__":
    # Quick self-check — run this file directly for instant feedback.
    # NOT the real grader: grademe (g in the app) also covers
    # dozens of edge cases and randomised inputs these examples don't.
    # Both functions are graded together: neither one alone passes.
    _tests = [
{cases_block}
    ]
    _ok = 0
    for _name, _args, _expected in _tests:
        try:
            _got = globals()[_name](*_args)
        except Exception as exc:
            print("FAIL", _name, _args, "-> raised",
                  type(exc).__name__ + ":", exc)
            continue
        if _got == _expected:
            _ok += 1
            print("ok  ", _name, _args, "->", _got)
        else:
            print("FAIL", _name, _args, "-> got", _got, "expected", _expected)
    print("%d/%d quick checks passed" % (_ok, len(_tests)))
"""


def _sample_cases(
    part: Exercise, n: int = STUB_SAMPLE_CASES
) -> List[Tuple[Any, Any]]:
    """Up to `n` curated (args, expected) pairs, expected from the oracle.
    `part` is an exercise or one of its parts — both carry "cases" and
    "oracle" (see grader.parts_of()).

    deepcopy matters: some oracles receive mutable lists/matrices, and this
    runs in the same process as later grading — an oracle that mutated its
    input in place would otherwise corrupt the bank's own `cases` data.
    """
    samples: List[Tuple[Any, Any]] = []
    for args in part["cases"][:n]:
        try:
            samples.append((args, part["oracle"](*copy.deepcopy(args))))
        except Exception:
            continue
    return samples


def write_stub(ex_name: str, cfg: Config) -> Tuple[bool, str, str]:
    """Create rendu/<ex>.py with the required signature(s). Never overwrites.
    Returns (ok, kind, message) — kind names the ui function to report it
    with ("success" / "warn" / "error"); nothing is printed here."""
    ex = ALL_EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".py")
    if os.path.exists(path):
        return False, "warn", "%s already exists — not touching it" % path
    parts = grader.parts_of(ex)
    shared = {
        "name": ex_name,
        "assignment": ex["subject"].splitlines()[0],
        "rank": RANK.label.replace("Exam ", ""),
        "short": ex_name[3:] if ex_name.startswith("py_") else ex_name,
    }
    if getattr(cfg, "bare_stub", False):
        # The exam (unless --relaxed): like the real one, just the
        # signature(s) — no self-check, no example cases.
        samples: Sequence[Tuple[Any, ...]] = []
        body = "# %s — 42 Exam %s\n\n%s" % (
            ex_name,
            shared["rank"],
            "\n\n".join(
                "%s\n    pass\n"
                % (
                    (
                        _signature_for(ex["subject"], part["function"])
                        if len(parts) > 1
                        else _signature_of(ex["subject"])
                    )
                    or "def %s():" % part["function"]
                )
                for part in parts
            ),
        )
    elif len(parts) == 1:
        samples = _sample_cases(ex)
        body = STUB_TEMPLATE.format(
            signature=_signature_of(ex["subject"])
            or "def %s():" % ex["function"],
            function=ex["function"],
            cases_block="\n".join("        (%r, %r)," % row for row in samples)
            or "        # (no sample cases available)",
            **shared,
        )
    else:
        defs: List[str] = []
        rows: List[Tuple[Any, ...]] = []
        for part in parts:
            function = part["function"]
            defs.append(
                "%s\n    pass\n"
                % (
                    _signature_for(ex["subject"], function)
                    or "def %s():" % function
                )
            )
            rows.extend((function,) + row for row in _sample_cases(part))
        samples = rows
        body = STUB_MULTI_TEMPLATE.format(
            defs_block="\n\n".join(defs),
            cases_block="\n".join(
                "        (%r, %r, %r)," % row for row in rows
            )
            or "        # (no sample cases available)",
            **shared,
        )
    try:
        os.makedirs(cfg.rendu, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    except OSError as exc:
        return False, "error", "cannot create %s: %s" % (path, exc)
    if getattr(cfg, "bare_stub", False):
        return (
            True,
            "success",
            (
                "created %s  (bare, like the real exam — "
                "--relaxed for the self-check stub)" % path
            ),
        )
    return (
        True,
        "success",
        (
            "created %s  (%d quick self-check case%s included)"
            % (path, len(samples), "" if len(samples) == 1 else "s")
        ),
    )


def make_stub(ex_name: str, cfg: Config) -> bool:
    """write_stub(), reported through the line-based UI. True on success."""
    ok, kind, message = write_stub(ex_name, cfg)
    getattr(ui, kind)(message)
    return ok


# ══════════════════════════════════════════════════════════════
#  MAIN MENU  ·  the Python-only entries (1-4 and q are shared)
# ══════════════════════════════════════════════════════════════


def menu_rows() -> List[Tuple[str, str, str]]:
    """The main menu. A function, not a constant: the exam's level count
    and the active rank both change under a rank switch."""
    return [
        ("1", "Start exam", "(%d levels, real exam flow)" % N_LEVELS),
        ("2", "Practice mode", "(drill a single exam exercise)"),
        ("3", "List all exercises", ""),
        (
            "4",
            "Training mode",
            "(LeetCode-style, by difficulty — not exam material)",
        ),
        ("5", "Switch exam rank", "(currently %s)" % RANK.label),
        ("6", "Exam readiness", "(what you've passed, level by level)"),
        ("7", "Daily drill", "(%d exercises from your gaps)" % DRILL_SIZE),
        ("q", "Quit", ""),
    ]


def extra_menu_action(choice: str, cfg: Config) -> bool:
    """Menu entries beyond the shared 1-4 (see shell_common.main_menu())."""
    if choice == "5":
        rank_menu()
    elif choice == "6":
        readiness_mode()
    elif choice == "7":
        drill_mode(cfg)
    else:
        return False
    return True


def rank_menu() -> None:
    """Pick another exam rank. Each rank keeps its own history and its own
    saved exam (see ranks.py), so switching never disturbs a run in
    progress on another one."""
    rows = [
        (rank_id, label, "%d exercises · %d levels" % (count, levels))
        for rank_id, label, count, levels in ranks.summary()
    ]
    while True:
        ui.clear()
        banner()
        print()
        ui.menu(rows + [("b", "Back", "")])
        try:
            choice = ui.ask("\n  Selection: ").lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        picked = ranks.normalize(choice)
        if picked is None:
            ui.warn("pick one of: %s" % ", ".join(ranks.CHOICES))
            time.sleep(0.8)
            continue
        use_rank(picked)
        settings.remember_exam("py" + picked)
        ui.success("switched to %s" % RANK.label)
        time.sleep(0.6)
        return


# ══════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=PROG,
        description="42 Exam Rank 03/04/05 (Python) practice tester.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="usually you just run `make`: the full-screen app does the "
        "rest\n(exam, practice, progress, settings).\n\n"
        "examples:\n"
        "  python3 -m examshell --exam            the exam, no menu\n"
        "  python3 -m examshell --grade py_inter  grade one solution\n\n"
        "more options (timeouts, strict mode, sync, ...): docs/python.md",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--exam",
        action="store_true",
        help="start the exam directly, skipping the menu",
    )
    mode.add_argument(
        "--practice",
        nargs="?",
        const="",
        metavar="EXERCISE",
        help="practice mode, optionally on one exercise",
    )
    mode.add_argument(
        "--list", action="store_true", help="print the exercise pool and exit"
    )
    mode.add_argument(
        "--train",
        nargs="?",
        const="",
        metavar="EXERCISE_OR_DIFFICULTY",
        help="training mode (LeetCode-style, by difficulty, "
        "or 'weak' for your worst-performing exercises "
        "so far — see --stats; never part of the exam)",
    )
    mode.add_argument(
        "--list-training",
        action="store_true",
        help="print the training pool (by difficulty) and exit",
    )
    mode.add_argument(
        "--grade",
        metavar="EXERCISE",
        help="grade one exercise and exit (0 = OK, 1 = KO)",
    )
    mode.add_argument(
        "--grade-all",
        action="store_true",
        help="grade every solution found in rendu/ and exit",
    )
    mode.add_argument(
        "--stub",
        metavar="EXERCISE",
        help="create an empty solution file and exit",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="self-test the exercise bank and exit",
    )
    mode.add_argument(
        "--stats",
        action="store_true",
        help="show your local practice history and exit",
    )
    mode.add_argument(
        "--feedback",
        nargs="?",
        const="idea",
        choices=("exam", "bug", "idea"),
        metavar="exam|bug|idea",
        help="open a prefilled GitHub issue form: an exercise that "
        "differs from your real exam, a bug, or an idea",
    )
    mode.add_argument(
        "--auto-sync",
        choices=("on", "off"),
        help="remember: sync automatically at the start and end of "
        "every session (needs --sync-setup)",
    )
    mode.add_argument(
        "--doctor",
        action="store_true",
        help="check this machine: Python, extras, C compiler, "
        "valgrind, git, data folder, sync, updates",
    )
    mode.add_argument(
        "--sync",
        action="store_true",
        help="carry your progress and solutions to/from your own "
        "private git repo (see --sync-setup)",
    )
    mode.add_argument(
        "--sync-setup",
        metavar="REPO_URL",
        help="connect this device to your private git repo for "
        "--sync (once per device), then sync",
    )
    mode.add_argument(
        "--readiness",
        action="store_true",
        help="show, level by level, which exercises the exam "
        "can draw you've passed, failed or never tried",
    )
    mode.add_argument(
        "--drill",
        nargs="?",
        type=int,
        const=DRILL_SIZE,
        metavar="N",
        help="a short daily session (default %d exercises): weak "
        "spots, never-tried ones, then the longest-unpractised" % DRILL_SIZE,
    )
    mode.add_argument(
        "--list-ranks",
        action="store_true",
        help="print the exam ranks this tester knows and exit",
    )

    p.add_argument(
        "--rank",
        default=None,
        metavar="RANK",
        help="which exam pool to use: %s (default: %s). Each "
        "rank keeps its own stats and saved exam."
        % (" / ".join(ranks.CHOICES), ranks.DEFAULT_RANK),
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed the RNG so a run is reproducible",
    )
    p.add_argument(
        "--rendu",
        default=RENDU_DIR,
        metavar="DIR",
        help="where your solutions live (default: %(default)s)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SEC",
        help="seconds allowed per call (default: %d, or your "
        "saved --save-config value)" % grader.DEFAULT_TIMEOUT,
    )
    p.add_argument(
        "--fuzz",
        type=int,
        default=None,
        metavar="N",
        help="random extra tests per exercise (default: %d, or "
        "your saved --save-config value)" % grader.DEFAULT_FUZZ,
    )
    p.add_argument(
        "--strict-imports",
        action="store_true",
        help="fail grading on any import, like the real moulinette",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="shorthand for every --strict-* flag at once — the "
        "harshest grading this tester can do (currently "
        "just --strict-imports; add more --strict-* flags "
        "here as they show up)",
    )
    p.add_argument(
        "--show-fails",
        type=int,
        default=None,
        metavar="N",
        help="failing tests to display (default: 4, or your "
        "saved --save-config value)",
    )
    p.add_argument(
        "--diff",
        action="store_true",
        help="on a failing test, show the full expected/got "
        "values with a pointer at the first character "
        "where they differ, instead of a 70-char clip",
    )
    p.add_argument(
        "--save-config",
        action="store_true",
        help="remember --timeout/--fuzz/--show-fails for next time, then exit",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="disable colours (also honours NO_COLOR)",
    )
    p.add_argument(
        "--relaxed",
        action="store_true",
        help="exam mode only: grade leniently (imports only warn) "
        "and allow 'new' to redraw an exercise — by default "
        "the exam is as strict as the real one",
    )
    p.add_argument(
        "--blind",
        action="store_true",
        help="exam mode only: like the real exam, show how many "
        "tests failed but not which inputs",
    )
    p.add_argument(
        "--tui",
        action="store_true",
        help="the app (needs Python 3.9+ and Textual, which make "
        "installs; falls back to the plain menu)",
    )
    p.add_argument(
        "--time-limit",
        type=int,
        default=None,
        metavar="MIN",
        help="exam mode only: end the exam after MIN minutes, "
        "with a countdown in the prompt (default: no limit)",
    )
    p.add_argument(
        "--no-update-check",
        action="store_true",
        help="don't check GitHub (at most once a day, in the "
        "background) for a newer version of this tester",
    )
    p.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    p.add_argument(
        "--no-rich",
        action="store_true",
        help="force the plain ANSI UI even if rich is installed",
    )
    shell_common.hide_advanced_flags(p)
    return p


def list_ranks() -> None:
    """The exam ranks this tester knows about, and which one is active."""
    ui.clear()
    banner()
    print()
    rows = [
        (
            rank_id,
            label,
            "%d exercises · %d levels%s"
            % (count, levels, "   ← active" if rank_id == RANK.id else ""),
        )
        for rank_id, label, count, levels in ranks.summary()
    ]
    ui.menu(rows)
    ui.info(
        "pick one with --rank, e.g. `python3 -m examshell --rank 04 --exam`"
    )


def run_tui_on_last_exam(
    args: argparse.Namespace, cfg: Config
) -> Optional[int]:
    """`make` opens on the C exam when that's the one the full-screen
    app was switched to last — unless --rank (or a Python exercise to
    practice) says Python."""
    if (
        args.rank
        or args.practice
        or settings.load_config().get("tester") != "c"
    ):
        return shell_common.run_tui(_SH, cfg, args)
    from c_exam import examshell as c_shell

    keep = {
        k: getattr(cfg, k, None)
        for k in ("relaxed", "time_limit", "blind", "no_update_check")
    }
    # --rendu is Python's folder: kept for a later switch back to Python
    return shell_common.run_tui(
        c_shell,
        c_shell.default_config(**keep),
        args,
        rendus={SYNC_SLOT: cfg.rendu},
    )


def check_banks(
    cfg: Config, seed: Optional[int], rank_ids: Sequence[str]
) -> int:
    """`--check`: grade every bank's own oracles through the real sandbox.

    The training bank is shared by every rank, so it is checked exactly
    once regardless of how many exam banks are being checked alongside it.
    Returns a process exit code.
    """
    rng = random.Random(seed if seed is not None else 0)
    problems = 0
    counts: List[str] = []
    for rank_id in rank_ids:
        rank = ranks.get(rank_id)
        ui.info("checking the %s exam bank …" % rank.label)
        problems += grader.selftest(
            rank.exercises,
            rank.levels,
            rng,
            timeout=cfg.timeout,
            fuzz=cfg.fuzz,
        )
        print()
        counts.append(
            "%s: %d exercises (%d levels)"
            % (rank.label, len(rank.exercises), rank.n_levels)
        )
    ui.info("checking the training bank …")
    problems += grader.selftest(
        TRAINING_EXERCISES,
        TRAINING_BY_DIFFICULTY,
        rng,
        timeout=cfg.timeout,
        fuzz=cfg.fuzz,
    )
    print()
    if problems:
        ui.error("%d problem(s) found in the bank(s)" % problems)
        return 1
    ui.success(
        "banks are consistent — %s, training: %d exercises "
        "(%d difficulties)"
        % (" · ".join(counts), len(TRAINING_EXERCISES), len(DIFFICULTIES))
    )
    return 0


def apply_saved_settings(args: argparse.Namespace) -> argparse.Namespace:
    """Fill every flag the student didn't pass from ~/.examshell/config.json,
    then the built-in default (see settings.merged())."""
    file_config = settings.load_config()
    args.timeout = settings.merged(
        args, file_config, "timeout", grader.DEFAULT_TIMEOUT
    )
    args.fuzz = settings.merged(args, file_config, "fuzz", grader.DEFAULT_FUZZ)
    args.show_fails = settings.merged(args, file_config, "show_fails", 4)
    args.time_limit = settings.merged(args, file_config, "time_limit", None)
    return args


def default_config(**overrides: Any) -> Config:
    """A Config as if started with no flags (saved settings applied), with
    `overrides` on top — what the full-screen app uses when it switches to
    this tester."""
    args = apply_saved_settings(build_parser().parse_args([]))
    for key, value in overrides.items():
        setattr(args, key, value)
    return Config(args)


def main(argv: Optional[List[str]] = None) -> int:
    args = apply_saved_settings(build_parser().parse_args(argv))
    ui.configure(
        rich=not args.no_rich,
        color=False if args.no_color else None,
    )
    cfg = Config(args)

    if args.rank is not None and ranks.normalize(args.rank) is None:
        ui.error(
            "unknown rank: %s — pick one of %s"
            % (args.rank, ", ".join(ranks.CHOICES))
        )
        return 2
    # Everything below reads the rank through this module's globals, so
    # this one call is what makes --rank take effect (see use_rank()).
    # Without --rank, the rank picked last (rank_menu(), the full-screen
    # app) — except for --check, where no --rank means every rank.
    use_rank(args.rank or (None if args.check else saved_rank()))

    if args.save_config:
        ok = settings.save_config(
            dict(
                settings.load_config(),
                **{
                    "timeout": args.timeout,
                    "fuzz": args.fuzz,
                    "show_fails": args.show_fails,
                },
            )
        )
        if ok:
            ui.success(
                "saved to %s — timeout=%d fuzz=%d show_fails=%d"
                % (
                    settings.CONFIG_PATH,
                    args.timeout,
                    args.fuzz,
                    args.show_fails,
                )
            )
        else:
            ui.error("could not write %s" % settings.CONFIG_PATH)
        return 0 if ok else 1

    if args.time_limit is not None and args.time_limit < 1:
        ui.error("--time-limit must be >= 1 (minutes)")
        return 2

    if args.timeout < 1 or args.fuzz < 0:
        ui.error("--timeout must be >= 1 and --fuzz must be >= 0")
        return 2

    if args.stats:
        show_stats()
        return 0

    if args.readiness:
        readiness_mode(interactive=False)
        return 0

    if args.feedback:
        return shell_common.run_feedback(_SH, args.feedback)

    if args.auto_sync:
        return shell_common.set_auto_sync(args.auto_sync == "on")

    if args.doctor:
        return shell_common.run_doctor(_SH, cfg)

    if args.sync or args.sync_setup:
        return shell_common.run_sync(_SH, cfg, args.sync_setup)

    if args.list_ranks:
        list_ranks()
        return 0

    if args.check:
        return check_banks(
            cfg,
            args.seed,
            # No --rank means "every rank": `make check` is
            # the one place that wants all of them at once,
            # and the training bank is only ever walked once
            # no matter how many exam banks come with it.
            [args.rank] if args.rank else list(ranks.CHOICES),
        )

    if args.list:
        list_mode(interactive=False)
        return 0

    if args.list_training:
        training_list_mode(interactive=False)
        return 0

    if args.stub:
        name = resolve_exercise(args.stub)
        return 0 if name and make_stub(name, cfg) else 1

    if args.grade:
        name = resolve_exercise(args.grade)
        if not name:
            return 2
        rng = random.Random(args.seed)
        return 0 if grade_exercise(name, rng, cfg, mode="grade") else 1

    if args.grade_all:
        return 0 if grade_all(cfg) else 1

    os.makedirs(cfg.rendu, exist_ok=True)
    # An interactive session: with auto-sync on (--auto-sync on), pull the
    # other device's progress first and push this one's when it ends.
    shell_common.auto_sync(_SH, cfg, "start")
    try:
        return run_interactive(args, cfg)
    finally:
        shell_common.auto_sync(_SH, cfg, "end")


def saved_rank() -> Optional[str]:
    """The Python rank picked last (settings.remember_exam()), or None."""
    return ranks.normalize(settings.load_config().get("rank"))


def run_interactive(args: argparse.Namespace, cfg: Config) -> int:
    """The modes that keep the student in a session: full-screen app, exam,
    practice, training, drill, or the menu."""
    if args.rank:
        # an explicit `--rank 04` is the exam picked last, too
        settings.remember_exam("py" + RANK.id)
    if args.tui:
        code = run_tui_on_last_exam(args, cfg)
        if code is not None:
            return code

    if args.exam:
        exam_mode(cfg)
        return 0
    if args.practice is not None:
        name = resolve_exercise(args.practice) if args.practice else None
        if args.practice and not name:
            return 2
        practice_mode(cfg, name)
        return 0
    if args.drill is not None:
        if args.drill < 1:
            ui.error("--drill needs at least 1 exercise")
            return 2
        drill_mode(cfg, args.drill)
        return 0
    if args.train is not None:
        value = args.train.lower()
        if value in DIFFICULTIES or value == "weak":
            training_mode(cfg, difficulty=value)
        elif value:
            name = resolve_exercise(value)
            if not name:
                return 2
            training_mode(cfg, ex_name=name)
        else:
            training_mode(cfg)
        return 0

    main_menu(cfg)
    return 0
