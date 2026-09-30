#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   C EXAM SHELL  ·  42 Common Core  ·  Exam Rank 02 (C)        ║
╚══════════════════════════════════════════════════════════════╝

A practice tester for 42's C Exam Rank 02, in the style of the Python
Exam Rank 03 tester this repo already has (`src/`). Same shape, different
grading mechanism: your file is compiled — together with a generated
main() — and run, and its output is compared against the same harness
compiled with a reference implementation. See c_exam/grader.py.

    python3 -m c_exam            # interactive menu
    python3 -m c_exam --help     # every flag

Put your solution in `c_rendu/<exercise_name>.c` and define the required
function (and ONLY that function — no main()). The folder is created for
you.
"""

import argparse
import os
import random
import shlex
import sys

from src import settings, shell_common, ui
# Used by the shared flow (src/shell_common.py), not here — kept reachable
# as examshell.<name> for callers and tests that patch them through it.
from src import achievements, hints, report_export, session_store, stats  # noqa: F401
from src.shell_common import DRILL_SIZE, countdown, draw, fmt_duration, time_left  # noqa: F401
from src.version import __version__

from . import grader
from .bank import EXERCISES, LEVELS, N_LEVELS, STANDARD_LEVELS  # noqa: F401 (hooks, see shell_common)
from .training_bank import DIFFICULTIES, TRAINING_BY_DIFFICULTY, TRAINING_EXERCISES

RENDU_DIR = "c_rendu"
TOOL = "c"               # tags saved config/stats/reports — "c" vs src's "py"

# Every exercise from both pools, keyed by name — used wherever the code only
# needs "the exercise dict for this name" and doesn't care which pool it is
# from (resolving, grading, showing the subject, creating a stub). Exam-only
# concerns (level draws, the 4-level progression) keep using EXERCISES/LEVELS
# directly so the training pool can never be drawn into an exam run.
ALL_EXERCISES = dict(EXERCISES)
ALL_EXERCISES.update(TRAINING_EXERCISES)


def banner():
    """ui.banner() with this tool's own title — it defaults to the Python
    tool's "Exam Rank 03 · Python Edition" otherwise."""
    ui.banner(subtitle="Exam Rank 02  ·  Common Core",
             edition="42 School  ·  C Edition")


class Config(object):
    def __init__(self, args):
        self.rendu = args.rendu
        self.timeout = args.timeout
        self.cc = args.cc
        self.strict_norm = args.strict_norm or args.strict
        self.show_fails = args.show_fails
        self.diff = args.diff
        self.seed = args.seed
        self.fuzz = args.fuzz
        # --strict implies --valgrind too, not just --strict-valgrind: the
        # latter only fails on what valgrind finds, so without turning
        # valgrind on itself "the harshest grading this tester can do"
        # would silently skip the leak/UB check entirely.
        self.valgrind = args.valgrind or args.strict
        self.strict_valgrind = args.strict_valgrind or args.strict
        self.strict_forbidden = args.strict_forbidden or args.strict
        # Exam-only realism, see exam_config() / exam_commands().
        self.relaxed = getattr(args, "relaxed", False)
        self.time_limit = getattr(args, "time_limit", None)   # minutes
        self.blind = getattr(args, "blind", False)
        self.no_update_check = getattr(args, "no_update_check", False)

# ══════════════════════════════════════════════════════════════
#  TESTER HOOKS  ·  what src/shell_common.py needs from this tester
# ══════════════════════════════════════════════════════════════
_SH = sys.modules[__name__]

PROG = "python3 -m c_exam"
# which folder of the sync repo this tester's --rendu maps to (src/sync.py)
SYNC_SLOT = "c_rendu"
SOURCE_EXT = ".c"
EXAM_PROMPT = "c-exam"
PRACTICE_PROMPT = "c-practice"
# Config flags the exam forces on unless --relaxed: the real exam compiles
# with -Wall -Wextra -Werror, and a forbidden call fails it.
STRICT_EXAM_FLAGS = ("strict_norm", "strict_forbidden")

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
    ("back", "return to the menu"),
]


def Session(login=None):
    """A fresh exam session, scored against the 4 levels."""
    return shell_common.Session(login, N_LEVELS)


def grading_notes(cfg):
    """Warnings to show before grading."""
    if cfg.valgrind and not grader.have_valgrind():
        return ["--valgrind requested but the valgrind binary isn't on PATH — "
                "skipping the leak/UB check (not available on Apple Silicon "
                "macOS; works on the real 42 school machines' Linux)"]
    return []


def prepare_grading(ex_name, rng, cfg):
    """Compile-and-run grading for one exercise (curated + fuzz cases)."""
    ex = ALL_EXERCISES[ex_name]
    size = len(ex["cases"]) + (cfg.fuzz if grader.is_fuzzable(ex) else 0)
    return shell_common.GradingJob(
        size,
        lambda: grader.grade(ex_name, ex, cfg.rendu, cc=cfg.cc, timeout=cfg.timeout,
                             strict_norm=cfg.strict_norm, rng=rng, fuzz=cfg.fuzz,
                             valgrind=cfg.valgrind, strict_valgrind=cfg.strict_valgrind,
                             strict_forbidden=cfg.strict_forbidden),
        verb="Compiling & grading")


# ══════════════════════════════════════════════════════════════
#  THE SHARED FLOW  ·  see src/shell_common.py
# ══════════════════════════════════════════════════════════════
def grade_exercise(ex_name, rng, cfg, mode="practice"):
    """Compile, grade and report one exercise; True when it is 100%."""
    return shell_common.grade_exercise(_SH, ex_name, rng, cfg, mode)


def grade_all(cfg):
    return shell_common.grade_all(_SH, cfg)


def exercise_entries():
    return shell_common.exercise_entries(_SH)


def training_entries():
    return shell_common.training_entries(_SH)


def show_subject(ex_name, cfg, session=None):
    shell_common.show_subject(_SH, ex_name, cfg, session)


def exam_config(cfg):
    return shell_common.exam_config(_SH, cfg)


def exam_commands(cfg):
    return shell_common.exam_commands(_SH, cfg)


def exam_mode(cfg):
    shell_common.exam_mode(_SH, cfg)


def exam_summary(session, passed, timed_out=False):
    shell_common.exam_summary(_SH, session, passed, timed_out)


def practice_one(ex_name, cfg, rng, mode="practice"):
    shell_common.practice_one(_SH, ex_name, cfg, rng, mode)


def practice_mode(cfg, ex_name=None):
    shell_common.practice_mode(_SH, cfg, ex_name)


def training_mode(cfg, ex_name=None, difficulty=None):
    shell_common.training_mode(_SH, cfg, ex_name, difficulty)


def list_mode(interactive=True):
    shell_common.list_mode(_SH, interactive)


def training_list_mode(interactive=True):
    shell_common.training_list_mode(_SH, interactive)


def show_stats():
    shell_common.show_stats(_SH)


def readiness_mode(interactive=True):
    shell_common.readiness_mode(_SH, interactive)


def drill_mode(cfg, n=DRILL_SIZE):
    shell_common.drill_mode(_SH, cfg, n)


def main_menu(cfg):
    shell_common.main_menu(_SH, cfg)


def resolve_exercise(name):
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
       The real check is `grademe` / `make c-grade EX={short}`. */
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
       The real check is `grademe` / `make c-grade EX={short}`. */
    (void)argc;
    (void)argv;
    return (0);
}}
"""


def _definition_header(prototype):
    """'void ft_putstr(char *str);' -> 'void ft_putstr(char *str)' (no ';')."""
    return prototype.rstrip(";").rstrip()


def write_stub(ex_name, cfg):
    """Create c_rendu/<ex>.c (and list.h, if the exercise needs one). Never
    overwrites an existing file. Returns (ok, kind, message) — kind names
    the ui function to report it with; nothing is printed here."""
    ex = ALL_EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".c")
    if os.path.exists(path):
        return False, "warn", "%s already exists — not touching it" % path
    try:
        os.makedirs(cfg.rendu, exist_ok=True)
        if ex.get("kind") == "program":
            first_case = next((c for c in ex["cases"] if c), [])
            example_args = "".join(" " + shlex.quote(a) for a in first_case)
            content = PROGRAM_STUB_TEMPLATE.format(
                name=ex_name, assignment=ex["subject"].splitlines()[0],
                path=path, short=ex_name, example_args=example_args)
        else:
            header = grader.header_filename(ex)
            includes = "\n#include \"%s\"\n" % header if header else ""
            examples = "\n".join(grader.render_call(ex, args)
                                 for args in ex["cases"][:2])
            content = FUNCTION_STUB_TEMPLATE.format(
                name=ex_name, assignment=ex["subject"].splitlines()[0],
                includes=includes, definition=_definition_header(ex["prototype"]),
                path=path, short=ex_name, helpers=grader.needed_helpers_c(ex),
                examples=examples)
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
    return True, "success", "created %s" % path


def make_stub(ex_name, cfg):
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
    ("4", "Training mode", "(LeetCode-style, by difficulty — not exam material)"),
    ("5", "Exam readiness", "(what you've passed, level by level)"),
    ("6", "Daily drill", "(%d exercises from your gaps)" % DRILL_SIZE),
    ("q", "Quit", ""),
]


def menu_rows():
    return MENU


def extra_menu_action(choice, cfg):
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


def build_parser():
    p = argparse.ArgumentParser(
        prog="python3 -m c_exam",
        description="42 Exam Rank 02 (C) practice tester.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 -m c_exam                       interactive menu\n"
               "  python3 -m c_exam --exam --seed 42      reproducible exam\n"
               "  python3 -m c_exam --practice ft_atoi    drill one exercise\n"
               "  python3 -m c_exam --train easy          drill an easy training exercise\n"
               "  python3 -m c_exam --grade ft_atoi       grade once, no UI\n"
               "  python3 -m c_exam --grade-all           grade every c_rendu/ solution\n"
               "  python3 -m c_exam --check                validate the banks\n")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--exam", action="store_true",
                      help="start the exam directly, skipping the menu")
    mode.add_argument("--practice", nargs="?", const="", metavar="EXERCISE",
                      help="practice mode, optionally on one exercise")
    mode.add_argument("--list", action="store_true",
                      help="print the exercise pool and exit")
    mode.add_argument("--train", nargs="?", const="", metavar="EXERCISE_OR_DIFFICULTY",
                      help="training mode (LeetCode-style, by difficulty, "
                           "or 'weak' for your worst-performing exercises "
                           "so far — see --stats; never part of the exam)")
    mode.add_argument("--list-training", action="store_true",
                      help="print the training pool (by difficulty) and exit")
    mode.add_argument("--grade", metavar="EXERCISE",
                      help="grade one exercise and exit (0 = OK, 1 = KO)")
    mode.add_argument("--grade-all", action="store_true",
                      help="grade every solution found in c_rendu/ and exit")
    mode.add_argument("--stub", metavar="EXERCISE",
                      help="create an empty solution file and exit")
    mode.add_argument("--check", action="store_true",
                      help="self-test the exercise bank and exit")
    mode.add_argument("--stats", action="store_true",
                      help="show your local practice history and exit")
    mode.add_argument("--sync", action="store_true",
                      help="carry your progress and solutions to/from your own "
                           "private git repo (see --sync-setup)")
    mode.add_argument("--sync-setup", metavar="REPO_URL",
                      help="connect this device to your private git repo for "
                           "--sync (once per device), then sync")
    mode.add_argument("--readiness", action="store_true",
                      help="show, level by level, which exercises the exam "
                           "can draw you've passed, failed or never tried")
    mode.add_argument("--drill", nargs="?", type=int, const=DRILL_SIZE, metavar="N",
                      help="a short daily session (default %d exercises): weak "
                           "spots, never-tried ones, then the longest-unpractised"
                           % DRILL_SIZE)

    p.add_argument("--seed", type=int, default=None,
                   help="seed the RNG so a run is reproducible")
    p.add_argument("--rendu", default=RENDU_DIR, metavar="DIR",
                   help="where your solutions live (default: %(default)s)")
    p.add_argument("--cc", default=None, metavar="COMPILER",
                   help="C compiler to use (default: %s, or your saved "
                        "--save-config value)" % grader.DEFAULT_CC)
    p.add_argument("--timeout", type=int, default=None, metavar="SEC",
                   help="seconds allowed per harness run (default: %d, or "
                        "your saved --save-config value)" % grader.DEFAULT_TIMEOUT)
    p.add_argument("--strict-norm", action="store_true",
                   help="fail grading on any compiler warning (-Werror)")
    p.add_argument("--strict-forbidden", action="store_true",
                   help="fail grading on a forbidden call, like the real "
                        "moulinette (default: warning only, like malloc "
                        "in an ft_strdup-style exercise's forbidden list)")
    p.add_argument("--strict", action="store_true",
                   help="shorthand for --strict-norm + --strict-forbidden + "
                        "--strict-valgrind, and turns on --valgrind itself "
                        "too (otherwise --strict-valgrind has nothing to "
                        "check) — the harshest grading this tester can do")
    p.add_argument("--fuzz", type=int, default=None, metavar="N",
                   help="random extra cases per fuzzable exercise (default: %d, or "
                        "your saved --save-config value) — only \"function\"-kind "
                        "exercises whose args are all safe to randomise are "
                        "affected; everything else still grades on curated cases "
                        "alone" % grader.DEFAULT_FUZZ)
    p.add_argument("--valgrind", action="store_true",
                   help="run your compiled solution through valgrind's leak "
                        "checker too (warning only; needs valgrind on PATH — "
                        "not available on Apple Silicon macOS, but is on the "
                        "real 42 school machines' Linux)")
    p.add_argument("--strict-valgrind", action="store_true",
                   help="like --valgrind, but a leak/memory error fails grading "
                        "instead of only warning")
    p.add_argument("--show-fails", type=int, default=None, metavar="N",
                   help="failing tests to display (default: 4, or your "
                        "saved --save-config value)")
    p.add_argument("--diff", action="store_true",
                   help="on a failing test, show the full expected/got "
                        "values with a pointer at the first character "
                        "where they differ, instead of a 70-char clip")
    p.add_argument("--theme", choices=ui.THEME_NAMES, default=None,
                   help="colour theme: dark (default), light, or highcontrast "
                        "(colour-blind friendly)")
    p.add_argument("--save-config", action="store_true",
                   help="remember --theme/--timeout/--fuzz/--show-fails/--cc for "
                        "next time, then exit")
    p.add_argument("--no-color", action="store_true",
                   help="disable colours (also honours NO_COLOR)")
    p.add_argument("--relaxed", action="store_true",
                   help="exam mode only: grade leniently (compiler warnings and forbidden calls only warn) "
                        "and allow 'new' to redraw an exercise — by default "
                        "the exam is as strict as the real one")
    p.add_argument("--blind", action="store_true",
                   help="exam mode only: like the real exam, show how many "
                        "tests failed but not which inputs")
    p.add_argument("--tui", action="store_true",
                   help="full-screen interface (needs Python 3.9+ and "
                        "`pip install textual`; falls back to the normal one)")
    p.add_argument("--time-limit", type=int, default=None, metavar="MIN",
                   help="exam mode only: end the exam after MIN minutes, "
                        "with a countdown in the prompt (default: no limit)")
    p.add_argument("--no-update-check", action="store_true",
                   help="don't check GitHub (at most once a day, in the "
                        "background) for a newer version of this tester")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + __version__)
    p.add_argument("--no-rich", action="store_true",
                   help="force the plain ANSI UI even if rich is installed")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    file_config = settings.load_config()
    args.theme = settings.merged(args, file_config, "theme", "dark")
    args.timeout = settings.merged(args, file_config, "timeout", grader.DEFAULT_TIMEOUT)
    args.fuzz = settings.merged(args, file_config, "fuzz", grader.DEFAULT_FUZZ)
    args.show_fails = settings.merged(args, file_config, "show_fails", 4)
    args.cc = settings.merged(args, file_config, "cc", grader.DEFAULT_CC)
    if args.strict_valgrind:
        args.valgrind = True
    ui.configure(rich=not args.no_rich, color=False if args.no_color else None,
                theme=args.theme)
    cfg = Config(args)

    if args.save_config:
        ok = settings.save_config({"theme": args.theme, "timeout": args.timeout,
                                    "fuzz": args.fuzz, "show_fails": args.show_fails,
                                    "cc": args.cc})
        if ok:
            ui.success("saved to %s — theme=%s timeout=%d fuzz=%d show_fails=%d cc=%s"
                      % (settings.CONFIG_PATH, args.theme, args.timeout,
                         args.fuzz, args.show_fails, args.cc))
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

    if args.sync or args.sync_setup:
        return shell_common.run_sync(_SH, cfg, args.sync_setup)

    if args.check:
        rng = random.Random(args.seed if args.seed is not None else 0)
        if cfg.valgrind and not grader.have_valgrind():
            ui.warn("--valgrind requested but the valgrind binary isn't on "
                    "PATH — skipping the leak/UB check for both banks")
        ui.info("checking the C exercise bank …")
        problems = grader.selftest(EXERCISES, LEVELS, cc=cfg.cc, timeout=cfg.timeout,
                                   rng=rng, fuzz=cfg.fuzz, valgrind=cfg.valgrind)
        print()
        ui.info("checking the C training bank …")
        problems += grader.selftest(TRAINING_EXERCISES, TRAINING_BY_DIFFICULTY,
                                    cc=cfg.cc, timeout=cfg.timeout, rng=rng, fuzz=cfg.fuzz,
                                    valgrind=cfg.valgrind)
        print()
        if problems:
            ui.error("%d problem(s) found in the bank(s)" % problems)
            return 1
        ui.success("banks are consistent — %d exam exercises (%d levels), "
                   "%d training exercises (%d difficulties)"
                   % (len(EXERCISES), N_LEVELS, len(TRAINING_EXERCISES),
                      len(DIFFICULTIES)))
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
