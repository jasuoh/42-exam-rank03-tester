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

    python3 -m src                 # interactive menu (Rank 03)
    python3 -m src --rank 04       # the Rank 04 pool instead
    python3 -m src --help          # every flag

Put your solution in `rendu/<exercise_name>.py` and define the required
function. The folder is created for you.

Which rank is active decides the exercise bank, the number of levels and
the tag this student's stats/saved exam/reports are filed under — see
ranks.py and use_rank() below. Everything else is rank-agnostic.
"""

import argparse
import copy
import os
import random
import time

from . import (achievements, grader, hints, ranks, report_export,
               session_store, settings, stats, ui)
from .bank_common import signature_for as _signature_for
from .bank_common import signature_of as _signature_of
from .training_bank import DIFFICULTIES, TRAINING_BY_DIFFICULTY, TRAINING_EXERCISES
from .version import __version__

RENDU_DIR = "rendu"
STUB_SAMPLE_CASES = 3    # curated cases embedded as a quick self-check in a stub


def use_rank(value=None):
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
    global RANK, TOOL, EXERCISES, LEVELS, N_LEVELS, STANDARD_LEVELS, ALL_EXERCISES
    RANK = ranks.get(value)
    TOOL = RANK.tool          # tags saved config/stats/reports — vs c_exam's "c"
    EXERCISES = RANK.exercises
    LEVELS = RANK.levels
    N_LEVELS = RANK.n_levels
    STANDARD_LEVELS = RANK.standard_levels
    ALL_EXERCISES = RANK.all_exercises()
    return RANK


use_rank()


def banner():
    """ui.banner(), told which rank the student is in."""
    ui.banner(subtitle="%s  ·  Common Core" % RANK.label)


class Config(object):
    """Everything the flags can change, in one place."""

    def __init__(self, args):
        self.rendu = args.rendu
        self.timeout = args.timeout
        self.fuzz = args.fuzz
        self.strict_imports = args.strict_imports or args.strict
        self.show_fails = args.show_fails
        self.diff = args.diff
        self.seed = args.seed
        # Exam-only realism, see exam_config() / exam_commands().
        self.relaxed = getattr(args, "relaxed", False)
        self.time_limit = getattr(args, "time_limit", None)   # minutes


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
def grade_exercise(ex_name, rng, cfg, mode="practice"):
    """Grade one exercise, render the report, return True when it is 100%."""
    ex = ALL_EXERCISES[ex_name]
    try:
        plan = grader.build_plan(ex_name, ex, rng, cfg.fuzz)
    except grader.BankError as exc:
        ui.error("exercise bank is broken: %s" % exc)
        return False

    with ui.spinner("Grading %s … (%d tests)" % (ex_name, grader.plan_size(plan))):
        report = grader.grade(ex_name, ex, cfg.rendu, timeout=cfg.timeout,
                              strict_imports=cfg.strict_imports, plan=plan)
    filepath = os.path.join(cfg.rendu, ex_name + ".py")
    ui.report(report, cfg.show_fails, cfg.diff, filepath)
    before_badges = achievements.unlocked(TOOL, N_LEVELS)
    stats.record(TOOL, ex_name, ex.get("level"), report.ok,
                report.passed, report.total, mode)
    for _bid, emoji, label, _desc in achievements.new_since(
            before_badges, achievements.unlocked(TOOL, N_LEVELS)):
        ui.badge_unlocked(emoji, label)
    if not report.ok and mode != "exam":
        if stats.consecutive_fails(TOOL, ex_name) >= hints.STUCK_THRESHOLD:
            text = hints.hint_for(ex, report)
            if text:
                ui.hint(text)
    return report.ok


def grade_all(cfg):
    """Grade every exercise that has a solution in cfg.rendu.

    Each exercise is graded with a fresh `random.Random(cfg.seed)`, so this
    matches `--grade EXERCISE --seed N` run one at a time. Returns True iff
    every solution that was found passed all of its tests.
    """
    rows, found, all_ok = [], 0, True
    for _, level, name, _func, _standard in exercise_entries():
        path = os.path.join(cfg.rendu, name + ".py")
        if not os.path.isfile(path):
            rows.append((level, name, "missing", "—"))
            continue
        found += 1
        ex = EXERCISES[name]
        rng = random.Random(cfg.seed)
        try:
            plan = grader.build_plan(name, ex, rng, cfg.fuzz)
        except grader.BankError as exc:
            ui.error("exercise bank is broken: %s" % exc)
            all_ok = False
            rows.append((level, name, "ko", "bank error"))
            continue
        with ui.spinner("Grading %s … (%d tests)" % (name, grader.plan_size(plan))):
            report = grader.grade(name, ex, cfg.rendu, timeout=cfg.timeout,
                                  strict_imports=cfg.strict_imports, plan=plan)
        all_ok = all_ok and report.ok
        label = ("%d/%d" % (report.passed, report.total) if not report.fatal
                 else report.fatal_title)
        rows.append((level, name, "ok" if report.ok else "ko", label))

    ui.overview_table(rows)
    if found == 0:
        ui.note("no solutions found in %s/ — nothing to grade" % cfg.rendu)
    else:
        ui.info("%d/%d solutions found — run --grade EXERCISE for details"
                % (found, len(rows)))
    return all_ok


def exercise_entries():
    """[(index, level, name, function, standard), …] ordered by level, then
    name. `standard` marks the 14 exercises `make exam` actually draws
    from — the rest ("Extra") only ever show up in practice mode."""
    entries, index = [], 0
    for level in range(1, N_LEVELS + 1):
        for name in sorted(LEVELS[level]):
            index += 1
            entries.append((index, level, name, EXERCISES[name]["function"],
                            EXERCISES[name]["standard"]))
    return entries


def training_entries():
    """[(index, difficulty, name, function), …] ordered by difficulty, then name.

    A separate listing from exercise_entries() on purpose: the training pool
    is never part of an exam draw, so it never shares a table with it.
    """
    entries, index = [], 0
    for difficulty in DIFFICULTIES:
        for name in sorted(TRAINING_BY_DIFFICULTY[difficulty]):
            index += 1
            entries.append((index, difficulty, name,
                            TRAINING_EXERCISES[name]["function"]))
    return entries


def draw(rng, pool, avoid=None):
    """Pick an exercise from the pool, avoiding `avoid` when possible."""
    choices = [name for name in pool if name != avoid] or list(pool)
    return rng.choice(choices)


def show_subject(ex_name, cfg, session=None):
    ui.clear()
    banner()
    if session is not None:
        ui.status_bar(session, N_LEVELS)
    ui.subject(ex_name, ALL_EXERCISES[ex_name], cfg.rendu)


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


def exam_config(cfg):
    """The config the exam actually grades with. Unless --relaxed, it is as
    strict as the real exam: any import fails grading (the real moulinette allows none). Practice and training keep the lenient
    warn-only feedback — that is where mistakes are supposed to be cheap."""
    if cfg.relaxed:
        return cfg
    strict = copy.copy(cfg)
    strict.strict_imports = True
    return strict


def exam_commands(cfg):
    """EXAM_COMMANDS minus `new` unless --relaxed: the real exam never lets
    you redraw an exercise you don't like."""
    return [row for row in EXAM_COMMANDS if cfg.relaxed or row[0] != "new"]


def time_left(session, cfg):
    """Seconds left under --time-limit (negative once it ran out), or None
    when the exam has no limit."""
    if not cfg.time_limit or session.start_time is None:
        return None
    return cfg.time_limit * 60 - (time.time() - session.start_time)


def exam_grade_rng(seed):
    """The exam's grading RNG — independent of the exercise-draw RNG, but
    still deterministic under --seed (string seeds are hashed stably)."""
    return random.Random(None if seed is None else "grade-%d" % seed)


def exam_mode(cfg):
    rng = random.Random(cfg.seed)
    # Grading draws its fuzz cases from its OWN generator: sharing `rng`
    # would make every later exercise draw depend on how many times the
    # student typed `grademe`, so `--seed N` would not reproduce the exam.
    grade_rng = exam_grade_rng(cfg.seed)
    cfg = exam_config(cfg)
    session = Session()
    ui.clear()
    banner()
    print()

    resumed = False
    saved = session_store.load(TOOL)
    if saved:
        try:
            ans = ui.ask("  Resume saved exam for %s — level %d? [Y/n]: "
                         % (saved["login"], saved["level"])).lower()
        except ui.Abort:
            return
        if ans in ("", "y", "yes"):
            session.login = saved["login"]
            session.level = saved["level"]
            session.passed = saved["passed"]
            session.attempts = saved["attempts"]
            session.history = [tuple(row) for row in saved["history"]]
            session.start_time = time.time() - saved["elapsed_seconds"]
            session.current_ex = saved["current_ex"]
            rng = session_store.rng_from_saved(saved)
            resumed = True
            ui.note("Resumed at level %d." % session.level)
        else:
            session_store.clear(TOOL)

    if not resumed:
        try:
            login = ui.ask("  Login (Enter = %s): " % session.login)
        except ui.Abort:
            return
        if login:
            session.login = login
        session.start()
        if cfg.seed is not None:
            ui.note("seed %d — this exam is reproducible" % cfg.seed)
    if not cfg.relaxed:
        ui.note("realistic mode — graded as strictly as the real exam, no "
                "'new' (start with --relaxed for lenient grading)")
    if cfg.time_limit:
        ui.note("time limit: %d minutes" % cfg.time_limit)

    if resumed:
        level_attempts = saved.get("level_attempts", 0)
        # Restore how much of this level's clock had already run before
        # the earlier quit — otherwise a resume always restarts it from
        # zero, silently dropping the time spent on it pre-quit from
        # session.history / the exported report (see session_store.save()).
        level_started = time.time() - saved.get("level_elapsed_seconds", 0)
    else:
        level_attempts = 0
        level_started = time.time()

    while session.level <= N_LEVELS:
        if not resumed or session.current_ex is None:
            session.current_ex = draw(rng, STANDARD_LEVELS[session.level])
            level_started, level_attempts = time.time(), 0
        resumed = False
        show_subject(session.current_ex, cfg, session)
        ui.commands(exam_commands(cfg))

        while True:
            try:
                cmd = ui.ask("\n  [%s@exam · lvl%d%s]$ "
                             % (session.login, session.level,
                                countdown(session, cfg))).lower()
            except ui.Abort:
                cmd = "quit"
            if _times_up(session, cfg):
                return

            if cmd in ("grademe", "g"):
                session.attempts += 1
                level_attempts += 1
                if grade_exercise(session.current_ex, grade_rng, cfg, mode="exam"):
                    session.passed.append(session.current_ex)
                    session.history.append((session.level, session.current_ex,
                                            level_attempts, time.time() - level_started))
                    ui.level_cleared(session.level)
                    session.level += 1
                    if session.level > N_LEVELS:
                        try:
                            ui.pause("  Press Enter to see your summary…")
                        except ui.Abort:
                            pass
                        session_store.clear(TOOL)
                        exam_summary(session, passed=True)
                        return
                    try:
                        ui.pause("  Press Enter for the next level…")
                    except ui.Abort:
                        session_store.save(TOOL, session, rng, None, 0)
                        exam_summary(session, passed=False)
                        return
                    break
                ui.info("Fix your solution and type 'grademe' again.")
            elif cmd in ("subject", "s"):
                show_subject(session.current_ex, cfg, session)
                ui.commands(exam_commands(cfg))
            elif cmd == "status":
                print()
                ui.status_bar(session, N_LEVELS)
            elif cmd == "new" and not cfg.relaxed:
                ui.warn("the real exam has no 'new' — solve this one "
                        "(or start with --relaxed to allow redraws)")
            elif cmd == "new":
                session.current_ex = draw(rng, STANDARD_LEVELS[session.level],
                                          session.current_ex)
                # A fresh exercise for this level starts its own clock and
                # attempt count — otherwise both keep accruing from the
                # exercise just abandoned, so a solve right after 'new'
                # would misreport the abandoned exercise's time/attempts.
                level_started, level_attempts = time.time(), 0
                show_subject(session.current_ex, cfg, session)
                ui.commands(exam_commands(cfg))
                ui.info("New exercise drawn for level %d." % session.level)
            elif cmd == "stub":
                make_stub(session.current_ex, cfg)
            elif cmd in ("quit", "q", "exit"):
                session_store.save(TOOL, session, rng, session.current_ex,
                                   level_attempts, level_started)
                exam_summary(session, passed=False)
                return
            elif cmd == "":
                continue
            else:
                ui.warn("unknown command — " +
                        " · ".join(name for name, _ in exam_commands(cfg)))

    session_store.clear(TOOL)
    exam_summary(session, passed=True)


def countdown(session, cfg):
    """' · 1:23:45 left' for the exam prompt, or '' without a time limit."""
    left = time_left(session, cfg)
    if left is None:
        return ""
    return " · %s left" % fmt_duration(max(0, left))


def _times_up(session, cfg):
    """End the exam when --time-limit ran out. True when it did."""
    left = time_left(session, cfg)
    if left is None or left > 0:
        return False
    session_store.clear(TOOL)
    exam_summary(session, passed=False, timed_out=True)
    return True


def exam_summary(session, passed, timed_out=False):
    ui.clear()
    banner()
    ui.status_bar(session, N_LEVELS)
    rows = [("Total time", session.elapsed()),
            ("Attempts", session.attempts),
            ("Score", "%d/100" % session.score())]
    for level, name, attempts, seconds in session.history:
        rows.append(("Level %d" % level, "%s  (%d attempt%s, %s)"
                     % (name, attempts, "" if attempts == 1 else "s",
                        fmt_duration(seconds))))

    badge_lines = []
    if passed:
        seconds = time.time() - session.start_time if session.start_time else 0
        # Both computed BEFORE this run is persisted, so they reflect
        # history up to (not including) this exam — see
        # achievements.unlocked()'s before/after convention.
        before = achievements.unlocked(TOOL, N_LEVELS)
        new_best = achievements.is_new_best_time(TOOL, seconds)
        stats.record_exam_complete(TOOL, seconds, session.attempts, session.score())
        after = achievements.unlocked(TOOL, N_LEVELS)
        badge_lines = ["%s %s!" % (emoji, label)
                       for _bid, emoji, label, _desc in achievements.new_since(before, after)]
        if new_best:
            badge_lines.append("⏱ New personal best time!")
        rows.append(("Badges", ", ".join(badge_lines) if badge_lines else "—"))

    title = ("🎉  EXAM PASSED — all %d levels cleared!" % N_LEVELS if passed
             else "%s — %d/%d levels cleared"
             % ("⏰ TIME'S UP" if timed_out else "EXAM ABORTED",
                len(session.passed), N_LEVELS))
    ui.summary(title, rows, passed)

    report_path = report_export.write_exam_report(TOOL, session, N_LEVELS, passed, badge_lines)
    if report_path:
        ui.note("Session report saved to %s" % report_path)


# ══════════════════════════════════════════════════════════════
#  PRACTICE MODE
# ══════════════════════════════════════════════════════════════
PRACTICE_COMMANDS = [
    ("grademe", "test your solution"),
    ("subject", "show the assignment again"),
    ("stub", "create an empty solution file for this exercise"),
    ("back", "return to the menu"),
]


def practice_one(ex_name, cfg, rng, mode="practice"):
    show_subject(ex_name, cfg)
    ui.commands(PRACTICE_COMMANDS)
    while True:
        try:
            cmd = ui.ask("\n  [practice · %s]$ " % ex_name).lower()
        except ui.Abort:
            return
        if cmd in ("grademe", "g"):
            grade_exercise(ex_name, rng, cfg, mode=mode)
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


def _renumber(entries):
    """Replace each entry's leading index with a fresh 1..N. Filtering
    (by difficulty, by a /query) shrinks the list on screen, so the
    numbers shown must shrink to match — otherwise a number the student
    can see gets rejected as out of range."""
    return [(i + 1,) + e[1:] for i, e in enumerate(entries)]


def _filter_entries(entries, query, name_col, func_col):
    """Case-insensitive substring match against name and function."""
    if not query:
        return entries
    q = query.lower()
    return [e for e in entries if q in e[name_col].lower() or q in e[func_col].lower()]


def practice_mode(cfg, ex_name=None):
    rng = random.Random()
    if ex_name:
        practice_one(ex_name, cfg, rng)
        return
    all_entries = exercise_entries()
    query = ""
    while True:
        ui.clear()
        banner()
        print()
        shown = _renumber(_filter_entries(all_entries, query, 2, 3))
        ui.exercise_table(shown, numbered=True)
        if query:
            ui.note("filter /%s — %d/%d shown  ('/' alone clears it)"
                    % (query, len(shown), len(all_entries)))
            if not shown:
                ui.warn("no exercise matches %r" % query)
        try:
            choice = ui.ask("\n  Selection (number, /text to filter, "
                            "or 'b' to go back): ").lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        if choice.startswith("/"):
            query = choice[1:].strip()
            continue
        if not choice.isdigit() or not 1 <= int(choice) <= len(shown):
            ui.warn("pick a number between 1 and %d, or /text to filter" % len(shown))
            time.sleep(0.8)
            continue
        practice_one(shown[int(choice) - 1][2], cfg, rng)


# ══════════════════════════════════════════════════════════════
#  TRAINING MODE  ·  LeetCode-style, by difficulty — never in the exam
# ══════════════════════════════════════════════════════════════
_DIFFICULTY_KEYS = {"e": "easy", "m": "medium", "h": "hard", "a": None, "w": "weak"}


def _weak_entries():
    """Training entries the student has struggled with, worst-first — see
    stats.weakest_exercises(). Recomputed fresh every call (not cached)
    so a grade recorded a moment ago is reflected immediately."""
    all_entries = training_entries()
    by_name = {e[2]: e for e in all_entries}
    names = stats.weakest_exercises(TOOL, list(by_name))
    return [by_name[n] for n in names]


def training_mode(cfg, ex_name=None, difficulty=None):
    """Drill the training pool. Reuses practice_one() — grading, `stub` and
    `subject` don't care which pool an exercise came from. `difficulty`
    is either a real difficulty name, None ("all"), or the "weak" sentinel
    (see _weak_entries()) — not a difficulty, but reuses the exact same
    filter/pick loop."""
    rng = random.Random()
    if ex_name:
        practice_one(ex_name, cfg, rng, mode="train")
        return
    query = ""
    while True:
        if difficulty == "weak":
            entries = _weak_entries()
        else:
            entries = training_entries()
            if difficulty:
                entries = [e for e in entries if e[1] == difficulty]
        shown = _renumber(_filter_entries(entries, query, 2, 3))
        ui.clear()
        banner()
        print()
        ui.training_table(shown, numbered=True)
        ui.note("keys: e=easy · m=medium · h=hard · w=weak (needs practice) · a=all")
        label = ("all" if not difficulty else difficulty)
        if difficulty == "weak" and not entries:
            ui.note("no weak spots yet — nothing attempted in training/practice "
                    "yet, or everything you've tried you've eventually passed")
        if query:
            ui.note("filter /%s — %d/%d shown  ('/' alone clears it)"
                    % (query, len(shown), len(entries)))
            if not shown:
                ui.warn("no exercise matches %r" % query)
        try:
            choice = ui.ask("\n  [%s] Selection (number · e/m/h/w to filter · "
                            "/text to search · b to go back): " % label).lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        if choice.startswith("/"):
            query = choice[1:].strip()
            continue
        if choice in _DIFFICULTY_KEYS:
            difficulty = _DIFFICULTY_KEYS[choice]
            continue
        if not choice.isdigit() or not 1 <= int(choice) <= len(shown):
            ui.warn("pick a number, e/m/h/w/a to filter, /text to search, "
                    "or b to go back")
            time.sleep(0.8)
            continue
        practice_one(shown[int(choice) - 1][2], cfg, rng, mode="train")


# ══════════════════════════════════════════════════════════════
#  LIST  ·  STUB
# ══════════════════════════════════════════════════════════════
def list_mode(interactive=True):
    if interactive:
        ui.clear()
        banner()
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


def training_list_mode(interactive=True):
    if interactive:
        ui.clear()
        banner()
        print()
    entries = training_entries()
    ui.training_table(entries)
    ui.info("%d training exercises · %d difficulties · practice only, "
            "never drawn into the exam" % (len(entries), len(DIFFICULTIES)))
    if interactive:
        try:
            ui.pause("\n  Press Enter to go back…")
        except ui.Abort:
            return


STUB_TEMPLATE = '''\
# {name} — 42 Exam {rank}
# {assignment}

{signature}
    pass


if __name__ == "__main__":
    # Quick self-check — run this file directly for instant feedback.
    # NOT the real grader: `grademe` / `make grade EX={short}` also cover
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
'''

# The same stub for a subject that asks for more than one function (see
# grader.parts_of()). Kept as its own template rather than generalising
# the one above: every row of the self-check has to say which function it
# calls, and paying that cost on the single-function stub — which is the
# overwhelming majority — would make the common case harder to read for
# no gain.
STUB_MULTI_TEMPLATE = '''\
# {name} — 42 Exam {rank}
# {assignment}

{defs_block}

if __name__ == "__main__":
    # Quick self-check — run this file directly for instant feedback.
    # NOT the real grader: `grademe` / `make grade EX={short}` also cover
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
            print("FAIL", _name, _args, "-> raised", type(exc).__name__ + ":", exc)
            continue
        if _got == _expected:
            _ok += 1
            print("ok  ", _name, _args, "->", _got)
        else:
            print("FAIL", _name, _args, "-> got", _got, "expected", _expected)
    print("%d/%d quick checks passed" % (_ok, len(_tests)))
'''


def _sample_cases(part, n=STUB_SAMPLE_CASES):
    """Up to `n` curated (args, expected) pairs, expected from the oracle.
    `part` is an exercise or one of its parts — both carry "cases" and
    "oracle" (see grader.parts_of()).

    deepcopy matters: some oracles receive mutable lists/matrices, and this
    runs in the same process as later grading — an oracle that mutated its
    input in place would otherwise corrupt the bank's own `cases` data.
    """
    samples = []
    for args in part["cases"][:n]:
        try:
            samples.append((args, part["oracle"](*copy.deepcopy(args))))
        except Exception:
            continue
    return samples


def make_stub(ex_name, cfg):
    """Create rendu/<ex>.py with the required signature(s). Never overwrites."""
    ex = ALL_EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".py")
    if os.path.exists(path):
        ui.warn("%s already exists — not touching it" % path)
        return False
    parts = grader.parts_of(ex)
    shared = {
        "name": ex_name,
        "assignment": ex["subject"].splitlines()[0],
        "rank": RANK.label.replace("Exam ", ""),
        "short": ex_name[3:] if ex_name.startswith("py_") else ex_name,
    }
    if len(parts) == 1:
        samples = _sample_cases(ex)
        body = STUB_TEMPLATE.format(
            signature=_signature_of(ex["subject"]) or "def %s():" % ex["function"],
            function=ex["function"],
            cases_block="\n".join("        (%r, %r)," % row for row in samples)
                        or "        # (no sample cases available)",
            **shared)
    else:
        defs, rows = [], []
        for part in parts:
            function = part["function"]
            defs.append("%s\n    pass\n"
                        % (_signature_for(ex["subject"], function)
                           or "def %s():" % function))
            rows.extend((function,) + row for row in _sample_cases(part))
        samples = rows
        body = STUB_MULTI_TEMPLATE.format(
            defs_block="\n\n".join(defs),
            cases_block="\n".join("        (%r, %r, %r)," % row for row in rows)
                        or "        # (no sample cases available)",
            **shared)
    try:
        os.makedirs(cfg.rendu, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    except OSError as exc:
        ui.error("cannot create %s: %s" % (path, exc))
        return False
    ui.success("created %s  (%d quick self-check case%s included)"
              % (path, len(samples), "" if len(samples) == 1 else "s"))
    return True


def show_stats():
    summary = stats.summarize(TOOL)
    ui.clear()
    banner()
    print()
    rows = [
        ("Total attempts", summary["total_attempts"]),
        ("Pass rate", "%d%%" % round(summary["pass_rate"] * 100)),
        ("Exams completed", summary["exam_completions"]),
    ]
    if summary["best_seconds"] is not None:
        rows.append(("Best exam time", fmt_duration(summary["best_seconds"])))
    ui.summary("Your practice history", rows, passed=True)
    if summary["per_exercise"]:
        # Worst-first: the whole point of the colour-coded bar is to make a
        # weak spot jump out, so put it where it's seen first, same spirit
        # as stats.weakest_exercises() / --train weak.
        per_ex_rows = sorted(
            ((name, row["passes"], row["attempts"])
             for name, row in summary["per_exercise"].items()),
            key=lambda r: r[1] / r[2])
        ui.stats_table(per_ex_rows)
    else:
        ui.note("no grading history yet — practice or grade something first")
    print()
    earned = {b[0] for b in achievements.unlocked(TOOL, N_LEVELS)}
    badge_rows = [(emoji, label, desc, bid in earned)
                  for bid, emoji, label, desc, _check in achievements.BADGES]
    ui.badges_table(badge_rows)


# ══════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════
def menu_rows():
    """The main menu. A function, not a constant: the exam's level count
    and the active rank both change under a rank switch."""
    return [
        ("1", "Start exam", "(%d levels, real exam flow)" % N_LEVELS),
        ("2", "Practice mode", "(drill a single exam exercise)"),
        ("3", "List all exercises", ""),
        ("4", "Training mode", "(LeetCode-style, by difficulty — not exam material)"),
        ("5", "Switch exam rank", "(currently %s)" % RANK.label),
        ("q", "Quit", ""),
    ]


def rank_menu():
    """Pick another exam rank. Each rank keeps its own history and its own
    saved exam (see ranks.py), so switching never disturbs a run in
    progress on another one."""
    rows = [(rank_id, label, "%d exercises · %d levels" % (count, levels))
            for rank_id, label, count, levels in ranks.summary()]
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
        ui.success("switched to %s" % RANK.label)
        time.sleep(0.6)
        return


def main_menu(cfg):
    while True:
        ui.clear()
        banner()
        print()
        ui.menu(menu_rows())
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
        elif choice == "4":
            training_mode(cfg)
        elif choice == "5":
            rank_menu()
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
        description="42 Exam Rank 03/04/05 (Python) practice tester.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 -m src                       interactive menu (Rank 03)\n"
               "  python3 -m src --rank 04             the Rank 04 pool instead\n"
               "  python3 -m src --exam --seed 42      reproducible exam\n"
               "  python3 -m src --practice py_inter   drill one exercise\n"
               "  python3 -m src --train easy          drill an easy training exercise\n"
               "  python3 -m src --grade py_inter      grade once, no UI\n"
               "  python3 -m src --grade-all           grade every rendu/ solution\n"
               "  python3 -m src --check               validate the banks\n")
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
                      help="grade every solution found in rendu/ and exit")
    mode.add_argument("--stub", metavar="EXERCISE",
                      help="create an empty solution file and exit")
    mode.add_argument("--check", action="store_true",
                      help="self-test the exercise bank and exit")
    mode.add_argument("--stats", action="store_true",
                      help="show your local practice history and exit")
    mode.add_argument("--list-ranks", action="store_true",
                      help="print the exam ranks this tester knows and exit")

    p.add_argument("--rank", default=None, metavar="RANK",
                   help="which exam pool to use: %s (default: %s). Each "
                        "rank keeps its own stats, saved exam and reports."
                        % (" / ".join(ranks.CHOICES), ranks.DEFAULT_RANK))
    p.add_argument("--seed", type=int, default=None,
                   help="seed the RNG so a run is reproducible")
    p.add_argument("--rendu", default=RENDU_DIR, metavar="DIR",
                   help="where your solutions live (default: %(default)s)")
    p.add_argument("--timeout", type=int, default=None, metavar="SEC",
                   help="seconds allowed per call (default: %d, or your "
                        "saved --save-config value)" % grader.DEFAULT_TIMEOUT)
    p.add_argument("--fuzz", type=int, default=None, metavar="N",
                   help="random extra tests per exercise (default: %d, or "
                        "your saved --save-config value)" % grader.DEFAULT_FUZZ)
    p.add_argument("--strict-imports", action="store_true",
                   help="fail grading on any import, like the real moulinette")
    p.add_argument("--strict", action="store_true",
                   help="shorthand for every --strict-* flag at once — the "
                        "harshest grading this tester can do (currently "
                        "just --strict-imports; add more --strict-* flags "
                        "here as they show up)")
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
                   help="remember --theme/--timeout/--fuzz/--show-fails "
                        "for next time, then exit")
    p.add_argument("--no-color", action="store_true",
                   help="disable colours (also honours NO_COLOR)")
    p.add_argument("--relaxed", action="store_true",
                   help="exam mode only: grade leniently (imports only warn) "
                        "and allow 'new' to redraw an exercise — by default "
                        "the exam is as strict as the real one")
    p.add_argument("--time-limit", type=int, default=None, metavar="MIN",
                   help="exam mode only: end the exam after MIN minutes, "
                        "with a countdown in the prompt (default: no limit)")
    p.add_argument("--version", action="version",
                   version="%(prog)s " + __version__)
    p.add_argument("--no-rich", action="store_true",
                   help="force the plain ANSI UI even if rich is installed")
    return p


def list_ranks():
    """The exam ranks this tester knows about, and which one is active."""
    ui.clear()
    banner()
    print()
    rows = [(rank_id, label, "%d exercises · %d levels%s"
             % (count, levels, "   ← active" if rank_id == RANK.id else ""))
            for rank_id, label, count, levels in ranks.summary()]
    ui.menu(rows)
    ui.info("pick one with --rank, e.g. `python3 -m src --rank 04 --exam`")


def check_banks(cfg, seed, rank_ids):
    """`--check`: grade every bank's own oracles through the real sandbox.

    The training bank is shared by every rank, so it is checked exactly
    once regardless of how many exam banks are being checked alongside it.
    Returns a process exit code.
    """
    rng = random.Random(seed if seed is not None else 0)
    problems, counts = 0, []
    for rank_id in rank_ids:
        rank = ranks.get(rank_id)
        ui.info("checking the %s exam bank …" % rank.label)
        problems += grader.selftest(rank.exercises, rank.levels, rng,
                                    timeout=cfg.timeout, fuzz=cfg.fuzz)
        print()
        counts.append("%s: %d exercises (%d levels)"
                      % (rank.label, len(rank.exercises), rank.n_levels))
    ui.info("checking the training bank …")
    problems += grader.selftest(TRAINING_EXERCISES, TRAINING_BY_DIFFICULTY, rng,
                                timeout=cfg.timeout, fuzz=cfg.fuzz)
    print()
    if problems:
        ui.error("%d problem(s) found in the bank(s)" % problems)
        return 1
    ui.success("banks are consistent — %s, training: %d exercises "
               "(%d difficulties)"
               % (" · ".join(counts), len(TRAINING_EXERCISES), len(DIFFICULTIES)))
    return 0


def resolve_exercise(name):
    """Accept the exact name, or a unique suffix like 'inter'. Searches both
    the exam pool and the training pool."""
    if name in ALL_EXERCISES:
        return name
    # "<prefix><name>" is an exact match in all but spelling — it wins over
    # a mere suffix match (e.g. "range" is ft_range, not also ft_rrange).
    if "py_" + name in ALL_EXERCISES:
        return "py_" + name
    matches = [n for n in ALL_EXERCISES if n.endswith(name)]
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
    file_config = settings.load_config()
    args.theme = settings.merged(args, file_config, "theme", "dark")
    args.timeout = settings.merged(args, file_config, "timeout", grader.DEFAULT_TIMEOUT)
    args.fuzz = settings.merged(args, file_config, "fuzz", grader.DEFAULT_FUZZ)
    args.show_fails = settings.merged(args, file_config, "show_fails", 4)
    ui.configure(rich=not args.no_rich, color=False if args.no_color else None,
                theme=args.theme)
    cfg = Config(args)

    if args.rank is not None and ranks.normalize(args.rank) is None:
        ui.error("unknown rank: %s — pick one of %s"
                 % (args.rank, ", ".join(ranks.CHOICES)))
        return 2
    # Everything below reads the rank through this module's globals, so
    # this one call is what makes --rank take effect (see use_rank()).
    use_rank(args.rank)

    if args.save_config:
        ok = settings.save_config({"theme": args.theme, "timeout": args.timeout,
                                    "fuzz": args.fuzz, "show_fails": args.show_fails})
        if ok:
            ui.success("saved to %s — theme=%s timeout=%d fuzz=%d show_fails=%d"
                      % (settings.CONFIG_PATH, args.theme, args.timeout,
                         args.fuzz, args.show_fails))
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

    if args.list_ranks:
        list_ranks()
        return 0

    if args.check:
        return check_banks(cfg, args.seed,
                           # No --rank means "every rank": `make check` is
                           # the one place that wants all of them at once,
                           # and the training bank is only ever walked once
                           # no matter how many exam banks come with it.
                           [args.rank] if args.rank else list(ranks.CHOICES))

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

    if args.exam:
        exam_mode(cfg)
        return 0
    if args.practice is not None:
        name = resolve_exercise(args.practice) if args.practice else None
        if args.practice and not name:
            return 2
        practice_mode(cfg, name)
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
