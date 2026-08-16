#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   EXAMSHELL  ·  42 Common Core  ·  Exam Rank 03 (Python)     ║
╚══════════════════════════════════════════════════════════════╝

A practice tester in the style of the real examshell / moulinette.

  · 6 levels, in the exact order of the real exam (1 -> 6)
  · one random exercise per level, drawn from that level's pool
  · every exercise graded against many curated cases + fuzz tests
  · you only move up at 100%
  · graded in a subprocess sandbox with a per-call timeout

    python3 -m src            # interactive menu
    python3 -m src --help     # every flag

Put your solution in `rendu/<exercise_name>.py` and define the required
function. The folder is created for you.
"""

import argparse
import os
import random
import sys
import time

from . import grader, ui
from .exam_bank import EXERCISES, LEVELS, N_LEVELS, signature_of

RENDU_DIR = "rendu"


class Config(object):
    """Everything the flags can change, in one place."""

    def __init__(self, args):
        self.rendu = args.rendu
        self.timeout = args.timeout
        self.fuzz = args.fuzz
        self.strict_imports = args.strict_imports
        self.show_fails = args.show_fails
        self.seed = args.seed


# ══════════════════════════════════════════════════════════════
#  SESSION
# ══════════════════════════════════════════════════════════════
class Session(object):
    def __init__(self, login=None):
        self.login = login or os.environ.get("USER") or "student"
        self.start_time = None
        self.level = 1
        self.current_ex = None
        self.passed = []
        self.attempts = 0
        self.history = []          # [(level, exercise, attempts, seconds)]

    def start(self):
        self.start_time = time.time()

    def elapsed(self):
        if self.start_time is None:
            return "00:00:00"
        return fmt_duration(time.time() - self.start_time)

    def score(self):
        return int(len(self.passed) / float(N_LEVELS) * 100)


def fmt_duration(seconds):
    seconds = int(seconds)
    return "%02d:%02d:%02d" % (seconds // 3600, (seconds % 3600) // 60, seconds % 60)


# ══════════════════════════════════════════════════════════════
#  GRADING FRONT-END
# ══════════════════════════════════════════════════════════════
def grade_exercise(ex_name, rng, cfg):
    """Grade one exercise, render the report, return True when it is 100%."""
    ex = EXERCISES[ex_name]
    try:
        tests = grader.build_tests(ex_name, ex, rng, cfg.fuzz)
    except grader.BankError as exc:
        ui.error("exercise bank is broken: %s" % exc)
        return False

    ui.note("Grading %s … (%d tests)" % (ex_name, len(tests)))
    report = grader.grade(ex_name, ex, cfg.rendu, timeout=cfg.timeout,
                          strict_imports=cfg.strict_imports, tests=tests)
    ui.report(report, cfg.show_fails)
    return report.ok


def exercise_entries():
    """[(index, level, name, function), …] ordered by level, then name."""
    entries, index = [], 0
    for level in range(1, N_LEVELS + 1):
        for name in sorted(LEVELS[level]):
            index += 1
            entries.append((index, level, name, EXERCISES[name]["function"]))
    return entries


def draw(rng, pool, avoid=None):
    """Pick an exercise from the pool, avoiding `avoid` when possible."""
    choices = [name for name in pool if name != avoid] or list(pool)
    return rng.choice(choices)


def show_subject(ex_name, cfg, session=None):
    ui.clear()
    ui.banner()
    if session is not None:
        ui.status_bar(session, N_LEVELS)
    ui.subject(ex_name, EXERCISES[ex_name], cfg.rendu)


# ══════════════════════════════════════════════════════════════
#  EXAM MODE
# ══════════════════════════════════════════════════════════════
EXAM_COMMANDS = [
    ("grademe", "test your solution (you advance only at 100%)"),
    ("subject", "show the assignment again"),
    ("status", "show your current progress"),
    ("new", "draw a different exercise for this level"),
    ("stub", "create an empty solution file for this exercise"),
    ("quit", "abort the exam"),
]


def exam_mode(cfg):
    rng = random.Random(cfg.seed)
    session = Session()
    ui.clear()
    ui.banner()
    print()
    try:
        login = ui.ask("  Login (Enter = %s): " % session.login)
    except ui.Abort:
        return
    if login:
        session.login = login
    session.start()
    if cfg.seed is not None:
        ui.note("seed %d — this exam is reproducible" % cfg.seed)

    while session.level <= N_LEVELS:
        session.current_ex = draw(rng, LEVELS[session.level])
        level_started, level_attempts = time.time(), 0
        show_subject(session.current_ex, cfg, session)
        ui.commands(EXAM_COMMANDS)

        while True:
            try:
                cmd = ui.ask("\n  [%s@exam · lvl%d]$ " % (session.login, session.level)).lower()
            except ui.Abort:
                cmd = "quit"

            if cmd in ("grademe", "g"):
                session.attempts += 1
                level_attempts += 1
                if grade_exercise(session.current_ex, rng, cfg):
                    session.passed.append(session.current_ex)
                    session.history.append((session.level, session.current_ex,
                                            level_attempts, time.time() - level_started))
                    ui.level_cleared(session.level)
                    session.level += 1
                    try:
                        ui.pause("  Press Enter for the next level…")
                    except ui.Abort:
                        return
                    break
                ui.info("Fix your solution and type 'grademe' again.")
            elif cmd in ("subject", "s"):
                show_subject(session.current_ex, cfg, session)
                ui.commands(EXAM_COMMANDS)
            elif cmd == "status":
                print()
                ui.status_bar(session, N_LEVELS)
            elif cmd == "new":
                session.current_ex = draw(rng, LEVELS[session.level], session.current_ex)
                show_subject(session.current_ex, cfg, session)
                ui.commands(EXAM_COMMANDS)
                ui.info("New exercise drawn for level %d." % session.level)
            elif cmd == "stub":
                make_stub(session.current_ex, cfg)
            elif cmd in ("quit", "q", "exit"):
                exam_summary(session, passed=False)
                return
            elif cmd == "":
                continue
            else:
                ui.warn("unknown command — " +
                        " · ".join(name for name, _ in EXAM_COMMANDS))

    exam_summary(session, passed=True)


def exam_summary(session, passed):
    ui.clear()
    ui.banner()
    ui.status_bar(session, N_LEVELS)
    rows = [("Total time", session.elapsed()),
            ("Attempts", session.attempts),
            ("Score", "%d/100" % session.score())]
    for level, name, attempts, seconds in session.history:
        rows.append(("Level %d" % level, "%s  (%d attempt%s, %s)"
                     % (name, attempts, "" if attempts == 1 else "s",
                        fmt_duration(seconds))))
    title = ("🎉  EXAM PASSED — all %d levels cleared!" % N_LEVELS if passed
             else "EXAM ABORTED — %d/%d levels cleared" % (len(session.passed), N_LEVELS))
    ui.summary(title, rows, passed)


# ══════════════════════════════════════════════════════════════
#  PRACTICE MODE
# ══════════════════════════════════════════════════════════════
PRACTICE_COMMANDS = [
    ("grademe", "test your solution"),
    ("subject", "show the assignment again"),
    ("stub", "create an empty solution file for this exercise"),
    ("back", "return to the menu"),
]


def practice_one(ex_name, cfg, rng):
    show_subject(ex_name, cfg)
    ui.commands(PRACTICE_COMMANDS)
    while True:
        try:
            cmd = ui.ask("\n  [practice · %s]$ " % ex_name).lower()
        except ui.Abort:
            return
        if cmd in ("grademe", "g"):
            grade_exercise(ex_name, rng, cfg)
        elif cmd in ("subject", "s"):
            show_subject(ex_name, cfg)
            ui.commands(PRACTICE_COMMANDS)
        elif cmd == "stub":
            make_stub(ex_name, cfg)
        elif cmd in ("back", "b", "quit", "q", "exit"):
            return
        elif cmd == "":
            continue
        else:
            ui.warn("unknown command — " +
                    " · ".join(name for name, _ in PRACTICE_COMMANDS))


def practice_mode(cfg, ex_name=None):
    rng = random.Random()
    if ex_name:
        practice_one(ex_name, cfg, rng)
        return
    entries = exercise_entries()
    while True:
        ui.clear()
        ui.banner()
        print()
        ui.exercise_table(entries, numbered=True)
        try:
            choice = ui.ask("\n  Selection (number, or 'b' to go back): ").lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(entries):
            ui.warn("pick a number between 1 and %d" % len(entries))
            time.sleep(0.8)
            continue
        practice_one(entries[int(choice) - 1][2], cfg, rng)


# ══════════════════════════════════════════════════════════════
#  LIST  ·  STUB
# ══════════════════════════════════════════════════════════════
def list_mode(interactive=True):
    if interactive:
        ui.clear()
        ui.banner()
        print()
    entries = exercise_entries()
    ui.exercise_table(entries)
    ui.info("%d exercises · %d levels · one exercise per level in the exam"
            % (len(entries), N_LEVELS))
    if interactive:
        try:
            ui.pause("\n  Press Enter to go back…")
        except ui.Abort:
            return


STUB_TEMPLATE = '''\
# {name} — 42 Exam Rank 03
# {assignment}

{signature}
    pass
'''


def make_stub(ex_name, cfg):
    """Create rendu/<ex>.py with the required signature. Never overwrites."""
    ex = EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".py")
    if os.path.exists(path):
        ui.warn("%s already exists — not touching it" % path)
        return False
    signature = signature_of(ex_name) or "def %s():" % ex["function"]
    try:
        os.makedirs(cfg.rendu, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(STUB_TEMPLATE.format(
                name=ex_name, assignment=ex["subject"].splitlines()[0],
                signature=signature))
    except OSError as exc:
        ui.error("cannot create %s: %s" % (path, exc))
        return False
    ui.success("created %s" % path)
    return True


# ══════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════
MENU = [
    ("1", "Start exam", "(%d levels, real exam flow)" % N_LEVELS),
    ("2", "Practice mode", "(drill a single exercise)"),
    ("3", "List all exercises", ""),
    ("q", "Quit", ""),
]


def main_menu(cfg):
    while True:
        ui.clear()
        ui.banner()
        print()
        ui.menu(MENU)
        try:
            choice = ui.ask("\n  Selection: ").lower()
        except ui.Abort:
            choice = "q"
        if choice == "1":
            exam_mode(cfg)
            try:
                ui.pause("\n  Press Enter for the main menu…")
            except ui.Abort:
                return
        elif choice == "2":
            practice_mode(cfg)
        elif choice == "3":
            list_mode()
        elif choice in ("q", "quit", "exit"):
            ui.info("Good luck on the real exam! 🍀")
            print()
            return


# ══════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════
def build_parser():
    p = argparse.ArgumentParser(
        prog="python3 -m src",
        description="42 Exam Rank 03 (Python) practice tester.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 -m src                       interactive menu\n"
               "  python3 -m src --exam --seed 42      reproducible exam\n"
               "  python3 -m src --practice py_inter   drill one exercise\n"
               "  python3 -m src --grade py_inter      grade once, no UI\n"
               "  python3 -m src --check               validate the bank\n")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--exam", action="store_true",
                      help="start the exam directly, skipping the menu")
    mode.add_argument("--practice", nargs="?", const="", metavar="EXERCISE",
                      help="practice mode, optionally on one exercise")
    mode.add_argument("--list", action="store_true",
                      help="print the exercise pool and exit")
    mode.add_argument("--grade", metavar="EXERCISE",
                      help="grade one exercise and exit (0 = OK, 1 = KO)")
    mode.add_argument("--stub", metavar="EXERCISE",
                      help="create an empty solution file and exit")
    mode.add_argument("--check", action="store_true",
                      help="self-test the exercise bank and exit")

    p.add_argument("--seed", type=int, default=None,
                   help="seed the RNG so a run is reproducible")
    p.add_argument("--rendu", default=RENDU_DIR, metavar="DIR",
                   help="where your solutions live (default: %(default)s)")
    p.add_argument("--timeout", type=int, default=grader.DEFAULT_TIMEOUT,
                   metavar="SEC",
                   help="seconds allowed per call (default: %(default)s)")
    p.add_argument("--fuzz", type=int, default=grader.DEFAULT_FUZZ, metavar="N",
                   help="random extra tests per exercise (default: %(default)s)")
    p.add_argument("--strict-imports", action="store_true",
                   help="fail grading on any import, like the real moulinette")
    p.add_argument("--show-fails", type=int, default=4, metavar="N",
                   help="failing tests to display (default: %(default)s)")
    p.add_argument("--no-color", action="store_true",
                   help="disable colours (also honours NO_COLOR)")
    p.add_argument("--no-rich", action="store_true",
                   help="force the plain ANSI UI even if rich is installed")
    return p


def resolve_exercise(name):
    """Accept the exact name, or a unique suffix like 'inter'."""
    if name in EXERCISES:
        return name
    matches = [n for n in EXERCISES if n == "py_" + name or n.endswith(name)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        ui.error("unknown exercise: %s" % name)
        ui.note("run `python3 -m src --list` to see them all")
    else:
        ui.error("ambiguous exercise %r — did you mean %s?"
                 % (name, ", ".join(sorted(matches))))
    return None


def main(argv=None):
    args = build_parser().parse_args(argv)
    ui.configure(rich=not args.no_rich, color=False if args.no_color else None)
    cfg = Config(args)

    if args.timeout < 1 or args.fuzz < 0:
        ui.error("--timeout must be >= 1 and --fuzz must be >= 0")
        return 2

    if args.check:
        rng = random.Random(args.seed if args.seed is not None else 0)
        ui.info("checking the exercise bank …")
        problems = grader.selftest(EXERCISES, LEVELS, N_LEVELS, rng,
                                   timeout=cfg.timeout, fuzz=cfg.fuzz)
        print()
        if problems:
            ui.error("%d problem(s) found in the bank" % problems)
            return 1
        ui.success("bank is consistent — %d exercises, %d levels"
                   % (len(EXERCISES), N_LEVELS))
        return 0

    if args.list:
        list_mode(interactive=False)
        return 0

    if args.stub:
        name = resolve_exercise(args.stub)
        return 0 if name and make_stub(name, cfg) else 1

    if args.grade:
        name = resolve_exercise(args.grade)
        if not name:
            return 2
        rng = random.Random(args.seed)
        return 0 if grade_exercise(name, rng, cfg) else 1

    os.makedirs(cfg.rendu, exist_ok=True)

    if args.exam:
        exam_mode(cfg)
        return 0
    if args.practice is not None:
        name = resolve_exercise(args.practice) if args.practice else None
        if args.practice and not name:
            return 2
        practice_mode(cfg, name)
        return 0

    main_menu(cfg)
    return 0
