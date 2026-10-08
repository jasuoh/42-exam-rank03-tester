#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   C EXAM SHELL  ·  42 Common Core  ·  Exam Rank 02 (C)        ║
╚══════════════════════════════════════════════════════════════╝

A practice tester for 42's C Exam Rank 02, in the style of the Python
Exam Rank 03 tester this repo already has (`examshell/`). Same shape, different
grading mechanism: your file is compiled — together with a generated
main() — and run, and its output is compared against the same harness
compiled with a reference implementation. See c_exam/grader.py.

    python3 -m c_exam            # interactive menu
    python3 -m c_exam --help     # every flag

Put your solution in `c_rendu/<exercise_name>.c` and define the required
function (and ONLY that function — no main()). The folder is created for
you.
"""

from __future__ import annotations

import argparse
import os
import random
import shlex
import sys
from typing import Any, Dict, List, Optional, Tuple

from examshell import settings, shell_common, ui
from examshell._types import Exercise

# Used by the shared flow (examshell/shell_common.py), not here — kept
# reachable as examshell.<name> for callers and tests that patch them through
# it.
from examshell import (  # noqa: F401
    hints,
    session_store,
    stats,
)
from examshell.shell_common import (  # noqa: F401
    DRILL_SIZE,
    countdown,
    draw,
    fmt_duration,
    time_left,
)
from examshell.shell_common import (
    ExerciseEntry,
    GradingJob,
    TrainingEntry,
)
from examshell.shell_common import Session as _Session
from examshell.version import __version__

from . import grader

# hooks, see shell_common
from .bank import (  # noqa: F401
    EXERCISES,
    LEVELS,
    N_LEVELS,
    STANDARD_LEVELS,
)
from .training_bank import (
    DIFFICULTIES,
    TRAINING_BY_DIFFICULTY,
    TRAINING_EXERCISES,
)

RENDU_DIR = "c_rendu"
TOOL = "c"  # tags saved config/stats/reports — "c" vs examshell's "py"

# Every exercise from both pools, keyed by name — used wherever the code only
# needs "the exercise dict for this name" and doesn't care which pool it is
# from (resolving, grading, showing the subject, creating a stub). Exam-only
# concerns (level draws, the 4-level progression) keep using EXERCISES/LEVELS
# directly so the training pool can never be drawn into an exam run.
ALL_EXERCISES: Dict[str, Exercise] = dict(EXERCISES)
ALL_EXERCISES.update(TRAINING_EXERCISES)


def banner() -> None:
    """ui.banner() with this tool's own title — it defaults to the Python
    tool's "Exam Rank 03 · Python Edition" otherwise."""
    ui.banner(
        subtitle="Exam Rank 02  ·  Common Core",
        edition="42 School  ·  C Edition",
    )


class Config(object):
    def __init__(self, args: argparse.Namespace) -> None:
        self.rendu: str = args.rendu
        self.timeout: int = args.timeout
        self.cc: str = args.cc
        self.strict_norm: bool = args.strict_norm or args.strict
        self.show_fails: int = args.show_fails
        self.diff: bool = args.diff
        self.seed: Optional[int] = args.seed
        self.fuzz: int = args.fuzz
        # --strict implies --valgrind too, not just --strict-valgrind: the
        # latter only fails on what valgrind finds, so without turning
        # valgrind on itself "the harshest grading this tester can do"
        # would silently skip the leak/UB check entirely.
        self.valgrind: bool = args.valgrind or args.strict
        self.strict_valgrind: bool = args.strict_valgrind or args.strict
        self.strict_forbidden: bool = args.strict_forbidden or args.strict
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

PROG = shell_common.command_name("examshell-c", "c_exam")
# which folder of the sync repo this tester's --rendu maps to
# (examshell/sync.py)
SYNC_SLOT = "c_rendu"
SOURCE_EXT = ".c"
EXAM_PROMPT = "c-exam"
PRACTICE_PROMPT = "c-practice"
# Config flags the exam forces on unless --relaxed: the real exam compiles
# with -Wall -Wextra -Werror, a forbidden call fails it, and `stub` gives
# you a bare file — no main(), no self-test, no examples.
STRICT_EXAM_FLAGS = ("strict_norm", "strict_forbidden", "bare_stub")

EXAM_COMMANDS = [
    ("grademe", "compile & test your solution (you advance only at 100%)"),
    ("subject", "show the assignment again"),
    ("status", "show your current progress"),
    ("new", "draw a different exercise for this level"),
    ("stub", "create an empty solution file for this exercise"),
    ("quit", "abort the exam"),
]

PRACTICE_COMMANDS = [
    ("grademe", "compile & test your solution"),
    ("subject", "show the assignment again"),
    ("stub", "create an empty solution file for this exercise"),
    ("feedback", "this exercise differs from your real exam? tell us"),
    ("back", "return to the menu"),
]


def Session(login: Optional[str] = None) -> _Session:
    """A fresh exam session, scored against the 4 levels."""
    return shell_common.Session(login, N_LEVELS)


def grading_notes(cfg: Config) -> List[str]:
    """Warnings to show before grading."""
    if cfg.valgrind and not grader.have_valgrind():
        return [
            "--valgrind requested but the valgrind binary isn't on PATH — "
            "skipping the leak/UB check (not available on Apple Silicon "
            "macOS; works on the real 42 school machines' Linux)"
        ]
    return []


def prepare_grading(
    ex_name: str, rng: random.Random, cfg: Config
) -> GradingJob:
    """Compile-and-run grading for one exercise (curated + fuzz cases)."""
    ex = ALL_EXERCISES[ex_name]
    size = len(ex["cases"]) + (cfg.fuzz if grader.is_fuzzable(ex) else 0)
    return shell_common.GradingJob(
        size,
        lambda: grader.grade(
            ex_name,
            ex,
            cfg.rendu,
            cc=cfg.cc,
            timeout=cfg.timeout,
            strict_norm=cfg.strict_norm,
            rng=rng,
            fuzz=cfg.fuzz,
            valgrind=cfg.valgrind,
            strict_valgrind=cfg.strict_valgrind,
            strict_forbidden=cfg.strict_forbidden,
        ),
        verb="Compiling & grading",
    )


# ══════════════════════════════════════════════════════════════
#  THE SHARED FLOW  ·  see examshell/shell_common.py
# ══════════════════════════════════════════════════════════════
def grade_exercise(
    ex_name: str, rng: random.Random, cfg: Config, mode: str = "practice"
) -> bool:
    """Compile, grade and report one exercise; True when it is 100%."""
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
    """Accept the exact name, or a unique suffix like 'strlen'. Searches
    both the exam pool and the training pool."""
    return shell_common.resolve_exercise(_SH, name, "ft_")


# ══════════════════════════════════════════════════════════════
#  STUB
# ══════════════════════════════════════════════════════════════


FUNCTION_STUB_TEMPLATE = """\
/* {name} — 42 Exam Rank 02 */
/* {assignment} */
{includes}
{definition}
{{
    /* your code here */
}}

#ifdef SELF_TEST
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

{helpers}
int main(void)
{{
    /* try it yourself:
         cc -DSELF_TEST {path} -o /tmp/t && /tmp/t
       then compare the printed output against the Examples above by eye —
       this does NOT check pass/fail like the Python tool's stub does.
       The real check is grademe (g in the app). */
{examples}
    return 0;
}}
#endif
"""


PROGRAM_STUB_TEMPLATE = """\
/* {name} — 42 Exam Rank 02 */
/* {assignment} */
/* this is a PROGRAM — write your own main(), argc/argv and all. */

#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv)
{{
    /* your code here — try it yourself:
         cc {path} -o /tmp/t && /tmp/t{example_args}
       then compare the output against the Examples above by eye.
       The real check is grademe (g in the app). */
    (void)argc;
    (void)argv;
    return (0);
}}
"""


# The exam's stub (cfg.bare_stub): like the real exam, you start from an
# empty file — just the prototype, no main(), no self-test, no examples.
BARE_FUNCTION_STUB_TEMPLATE = """\
/* {name} — 42 Exam Rank 02 */
{includes}
{definition}
{{
}}
"""

BARE_PROGRAM_STUB_TEMPLATE = """\
/* {name} — 42 Exam Rank 02 */

{main}
{{
}}
"""


def _bare_main(ex: Exercise) -> str:
    """The bare stub's main() line. A program that never gets an argument
    (fizzbuzz) gets `main(void)`: with unused argc/argv, a correct solution
    would fail the exam's -Wall -Wextra -Werror on unused parameters."""
    takes_args = ex.get("fuzz_argv") or any(ex["cases"])
    return (
        "int main(int argc, char **argv)" if takes_args else "int main(void)"
    )


def _definition_header(prototype: str) -> str:
    """'void ft_putstr(char *str);' -> 'void ft_putstr(char *str)' (no ';')."""
    return prototype.rstrip(";").rstrip()


def write_stub(ex_name: str, cfg: Config) -> Tuple[bool, str, str]:
    """Create c_rendu/<ex>.c (and list.h, if the exercise needs one). Never
    overwrites an existing file. Returns (ok, kind, message) — kind names
    the ui function to report it with; nothing is printed here."""
    ex = ALL_EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".c")
    if os.path.exists(path):
        return False, "warn", "%s already exists — not touching it" % path
    bare = getattr(cfg, "bare_stub", False)
    try:
        os.makedirs(cfg.rendu, exist_ok=True)
        if ex.get("kind") == "program" and bare:
            content = BARE_PROGRAM_STUB_TEMPLATE.format(
                name=ex_name, main=_bare_main(ex)
            )
        elif ex.get("kind") == "program":
            first_case: List[str] = next((c for c in ex["cases"] if c), [])
            example_args = "".join(" " + shlex.quote(a) for a in first_case)
            content = PROGRAM_STUB_TEMPLATE.format(
                name=ex_name,
                assignment=ex["subject"].splitlines()[0],
                path=path,
                short=ex_name,
                example_args=example_args,
            )
        elif bare:
            header = grader.header_filename(ex)
            content = BARE_FUNCTION_STUB_TEMPLATE.format(
                name=ex_name,
                includes='\n#include "%s"\n' % header if header else "",
                definition=_definition_header(ex["prototype"]),
            )
        else:
            header = grader.header_filename(ex)
            includes = '\n#include "%s"\n' % header if header else ""
            examples = "\n".join(
                grader.render_call(ex, args) for args in ex["cases"][:2]
            )
            content = FUNCTION_STUB_TEMPLATE.format(
                name=ex_name,
                assignment=ex["subject"].splitlines()[0],
                includes=includes,
                definition=_definition_header(ex["prototype"]),
                path=path,
                short=ex_name,
                helpers=grader.needed_helpers_c(ex),
                examples=examples,
            )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        header = grader.header_filename(ex)
        if header:
            header_path = os.path.join(cfg.rendu, header)
            if not os.path.exists(header_path):
                with open(header_path, "w", encoding="utf-8") as fh:
                    fh.write(grader.header_content(header))
    except OSError as exc:
        return False, "error", "cannot create %s: %s" % (path, exc)
    return (
        True,
        "success",
        "created %s%s"
        % (
            path,
            "  (bare, like the real exam — --relaxed for the full stub)"
            if bare
            else "",
        ),
    )


def make_stub(ex_name: str, cfg: Config) -> bool:
    """write_stub(), reported through the line-based UI. True on success."""
    ok, kind, message = write_stub(ex_name, cfg)
    getattr(ui, kind)(message)
    return ok


# ══════════════════════════════════════════════════════════════
#  MAIN MENU  ·  the C-only entries (1-4 and q are shared)
# ══════════════════════════════════════════════════════════════
MENU = [
    ("1", "Start exam", "(%d levels, real exam flow)" % N_LEVELS),
    ("2", "Practice mode", "(drill a single exercise)"),
    ("3", "List all exercises", ""),
    (
        "4",
        "Training mode",
        "(LeetCode-style, by difficulty — not exam material)",
    ),
    ("5", "Exam readiness", "(what you've passed, level by level)"),
    ("6", "Daily drill", "(%d exercises from your gaps)" % DRILL_SIZE),
    ("q", "Quit", ""),
]


def menu_rows() -> List[Tuple[str, str, str]]:
    return MENU


def extra_menu_action(choice: str, cfg: Config) -> bool:
    """Menu entries beyond the shared 1-4 (see shell_common.main_menu())."""
    if choice == "5":
        readiness_mode()
    elif choice == "6":
        drill_mode(cfg)
    else:
        return False
    return True


# ══════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=PROG,
        description="42 Exam Rank 02 (C) practice tester.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="usually you just run `make`: the full-screen app does the "
        "rest\n(exam, practice, progress, settings).\n\n"
        "examples:\n"
        "  python3 -m c_exam --exam            the exam, no menu\n"
        "  python3 -m c_exam --grade ft_atoi   grade one solution\n\n"
        "more options (timeouts, strict mode, sync, ...): docs/c.md",
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
        help="grade every solution found in c_rendu/ and exit",
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
        "--cc",
        default=None,
        metavar="COMPILER",
        help="C compiler to use (default: %s, or your saved "
        "--save-config value)" % grader.DEFAULT_CC,
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SEC",
        help="seconds allowed per harness run (default: %d, or "
        "your saved --save-config value)" % grader.DEFAULT_TIMEOUT,
    )
    p.add_argument(
        "--strict-norm",
        action="store_true",
        help="fail grading on any compiler warning (-Werror)",
    )
    p.add_argument(
        "--strict-forbidden",
        action="store_true",
        help="fail grading on a forbidden call, like the real "
        "moulinette (default: warning only, like malloc "
        "in an ft_strdup-style exercise's forbidden list)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="shorthand for --strict-norm + --strict-forbidden + "
        "--strict-valgrind, and turns on --valgrind itself "
        "too (otherwise --strict-valgrind has nothing to "
        "check) — the harshest grading this tester can do",
    )
    p.add_argument(
        "--fuzz",
        type=int,
        default=None,
        metavar="N",
        help="random extra cases per fuzzable exercise (default: %d, or "
        'your saved --save-config value) — only "function"-kind '
        "exercises whose args are all safe to randomise are "
        "affected; everything else still grades on curated cases "
        "alone" % grader.DEFAULT_FUZZ,
    )
    p.add_argument(
        "--valgrind",
        action="store_true",
        help="run your compiled solution through valgrind's leak "
        "checker too (warning only; needs valgrind on PATH — "
        "not available on Apple Silicon macOS, but is on the "
        "real 42 school machines' Linux)",
    )
    p.add_argument(
        "--strict-valgrind",
        action="store_true",
        help="like --valgrind, but a leak/memory error fails grading "
        "instead of only warning",
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
        help="remember --timeout/--fuzz/--show-fails/--cc for "
        "next time, then exit",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="disable colours (also honours NO_COLOR)",
    )
    p.add_argument(
        "--relaxed",
        action="store_true",
        help="exam mode only: grade leniently (compiler warnings and "
        "forbidden calls only warn) "
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
        help="full-screen interface (needs Python 3.9+ and "
        "`pip install textual`; falls back to the normal one)",
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
    args.cc = settings.merged(args, file_config, "cc", grader.DEFAULT_CC)
    if args.strict_valgrind:
        args.valgrind = True
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

    if args.save_config:
        ok = settings.save_config(
            dict(
                settings.load_config(),
                **{
                    "timeout": args.timeout,
                    "fuzz": args.fuzz,
                    "show_fails": args.show_fails,
                    "cc": args.cc,
                },
            )
        )
        if ok:
            ui.success(
                "saved to %s — timeout=%d fuzz=%d show_fails=%d cc=%s"
                % (
                    settings.CONFIG_PATH,
                    args.timeout,
                    args.fuzz,
                    args.show_fails,
                    args.cc,
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

    if args.check:
        rng = random.Random(args.seed if args.seed is not None else 0)
        if cfg.valgrind and not grader.have_valgrind():
            ui.warn(
                "--valgrind requested but the valgrind binary isn't on "
                "PATH — skipping the leak/UB check for both banks"
            )
        ui.info("checking the C exercise bank …")
        problems = grader.selftest(
            EXERCISES,
            LEVELS,
            cc=cfg.cc,
            timeout=cfg.timeout,
            rng=rng,
            fuzz=cfg.fuzz,
            valgrind=cfg.valgrind,
        )
        print()
        ui.info("checking the C training bank …")
        problems += grader.selftest(
            TRAINING_EXERCISES,
            TRAINING_BY_DIFFICULTY,
            cc=cfg.cc,
            timeout=cfg.timeout,
            rng=rng,
            fuzz=cfg.fuzz,
            valgrind=cfg.valgrind,
        )
        print()
        if problems:
            ui.error("%d problem(s) found in the bank(s)" % problems)
            return 1
        ui.success(
            "banks are consistent — %d exam exercises (%d levels), "
            "%d training exercises (%d difficulties)"
            % (
                len(EXERCISES),
                N_LEVELS,
                len(TRAINING_EXERCISES),
                len(DIFFICULTIES),
            )
        )
        return 0

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


def run_interactive(args: argparse.Namespace, cfg: Config) -> int:
    """The modes that keep the student in a session: full-screen app, exam,
    practice, training, drill, or the menu."""
    if args.tui:
        code = shell_common.run_tui(_SH, cfg, args)
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
