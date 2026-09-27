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
import time

from src import achievements, hints, report_export, session_store, settings, stats, ui
from src.version import __version__

from . import grader
from .bank import EXERCISES, LEVELS, N_LEVELS, STANDARD_LEVELS
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
        self.history = []

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
    ex = ALL_EXERCISES[ex_name]
    fuzzed = cfg.fuzz if grader.is_fuzzable(ex) else 0
    n = len(ex["cases"]) + fuzzed
    if cfg.valgrind and not grader.have_valgrind():
        ui.warn("--valgrind requested but the valgrind binary isn't on PATH — "
                "skipping the leak/UB check (not available on Apple Silicon "
                "macOS; works on the real 42 school machines' Linux)")
    with ui.spinner("Compiling & grading %s … (%d tests)" % (ex_name, n)):
        report = grader.grade(ex_name, ex, cfg.rendu, cc=cfg.cc, timeout=cfg.timeout,
                              strict_norm=cfg.strict_norm, rng=rng, fuzz=cfg.fuzz,
                              valgrind=cfg.valgrind, strict_valgrind=cfg.strict_valgrind,
                              strict_forbidden=cfg.strict_forbidden)
    filepath = os.path.join(cfg.rendu, ex_name + ".c")
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
    if cfg.valgrind and not grader.have_valgrind():
        ui.warn("--valgrind requested but the valgrind binary isn't on PATH — "
                "skipping the leak/UB check for every exercise below (not "
                "available on Apple Silicon macOS; works on the real 42 "
                "school machines' Linux)")
    rows, found, all_ok = [], 0, True
    for _, level, name, _func, _standard in exercise_entries():
        path = os.path.join(cfg.rendu, name + ".c")
        if not os.path.isfile(path):
            rows.append((level, name, "missing", "—"))
            continue
        found += 1
        rng = random.Random(cfg.seed)
        with ui.spinner("Compiling & grading %s …" % name):
            report = grader.grade(name, EXERCISES[name], cfg.rendu, cc=cfg.cc,
                                  timeout=cfg.timeout, strict_norm=cfg.strict_norm,
                                  rng=rng, fuzz=cfg.fuzz,
                                  valgrind=cfg.valgrind, strict_valgrind=cfg.strict_valgrind,
                                  strict_forbidden=cfg.strict_forbidden)
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
    name. `standard` marks the real, documented exercises `make c-exam`
    actually draws from — the invented "Extra" ones only ever show up in
    practice mode (same Standard/Extra split as the Python bank)."""
    entries, index = [], 0
    for level in range(1, N_LEVELS + 1):
        for name in sorted(LEVELS[level]):
            index += 1
            entries.append((index, level, name, EXERCISES[name]["function"],
                            EXERCISES[name]["standard"]))
    return entries


def training_entries():
    """[(index, difficulty, name, function), …] ordered by difficulty, then
    name. A separate listing from exercise_entries() on purpose: the
    training pool is never part of an exam draw, so it never shares a
    table with it."""
    entries, index = [], 0
    for difficulty in DIFFICULTIES:
        for name in sorted(TRAINING_BY_DIFFICULTY[difficulty]):
            index += 1
            entries.append((index, difficulty, name,
                            TRAINING_EXERCISES[name]["function"]))
    return entries


def draw(rng, pool, avoid=None):
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
    ("grademe", "compile & test your solution (you advance only at 100%)"),
    ("subject", "show the assignment again"),
    ("status", "show your current progress"),
    ("new", "draw a different exercise for this level"),
    ("stub", "create an empty solution file for this exercise"),
    ("quit", "abort the exam"),
]


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
        ui.commands(EXAM_COMMANDS)

        while True:
            try:
                cmd = ui.ask("\n  [%s@c-exam · lvl%d]$ "
                            % (session.login, session.level)).lower()
            except ui.Abort:
                cmd = "quit"

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
                ui.commands(EXAM_COMMANDS)
            elif cmd == "status":
                print()
                ui.status_bar(session, N_LEVELS)
            elif cmd == "new":
                session.current_ex = draw(rng, STANDARD_LEVELS[session.level],
                                          session.current_ex)
                # A fresh exercise for this level starts its own clock and
                # attempt count — otherwise both keep accruing from the
                # exercise just abandoned, so a solve right after 'new'
                # would misreport the abandoned exercise's time/attempts.
                level_started, level_attempts = time.time(), 0
                show_subject(session.current_ex, cfg, session)
                ui.commands(EXAM_COMMANDS)
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
                        " · ".join(name for name, _ in EXAM_COMMANDS))

    session_store.clear(TOOL)
    exam_summary(session, passed=True)


def exam_summary(session, passed):
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
             else "EXAM ABORTED — %d/%d levels cleared" % (len(session.passed), N_LEVELS))
    ui.summary(title, rows, passed)

    report_path = report_export.write_exam_report(TOOL, session, N_LEVELS, passed, badge_lines)
    if report_path:
        ui.note("Session report saved to %s" % report_path)


# ══════════════════════════════════════════════════════════════
#  PRACTICE MODE
# ══════════════════════════════════════════════════════════════
PRACTICE_COMMANDS = [
    ("grademe", "compile & test your solution"),
    ("subject", "show the assignment again"),
    ("stub", "create an empty solution file for this exercise"),
    ("back", "return to the menu"),
]


def practice_one(ex_name, cfg, rng, mode="practice"):
    show_subject(ex_name, cfg)
    ui.commands(PRACTICE_COMMANDS)
    while True:
        try:
            cmd = ui.ask("\n  [c-practice · %s]$ " % ex_name).lower()
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
    """Replace each entry's leading index with a fresh 1..N so a filtered
    (shorter) list on screen always matches what you type."""
    return [(i + 1,) + e[1:] for i, e in enumerate(entries)]


def _filter_entries(entries, query, name_col, func_col):
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


def make_stub(ex_name, cfg):
    """Create c_rendu/<ex>.c (and list.h, if the exercise needs one). Never
    overwrites an existing file."""
    ex = ALL_EXERCISES[ex_name]
    path = os.path.join(cfg.rendu, ex_name + ".c")
    if os.path.exists(path):
        ui.warn("%s already exists — not touching it" % path)
        return False
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
        ui.error("cannot create %s: %s" % (path, exc))
        return False
    ui.success("created %s" % path)
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
MENU = [
    ("1", "Start exam", "(%d levels, real exam flow)" % N_LEVELS),
    ("2", "Practice mode", "(drill a single exercise)"),
    ("3", "List all exercises", ""),
    ("4", "Training mode", "(LeetCode-style, by difficulty — not exam material)"),
    ("q", "Quit", ""),
]


def main_menu(cfg):
    while True:
        ui.clear()
        banner()
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
        elif choice == "4":
            training_mode(cfg)
        elif choice in ("q", "quit", "exit"):
            ui.info("Good luck on the real exam! 🍀")
            print()
            return


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
    p.add_argument("--version", action="version",
                   version="%(prog)s " + __version__)
    p.add_argument("--no-rich", action="store_true",
                   help="force the plain ANSI UI even if rich is installed")
    return p


def resolve_exercise(name):
    """Accept the exact name, or a unique suffix like 'strlen'. Searches
    both the exam pool and the training pool."""
    if name in ALL_EXERCISES:
        return name
    # "<prefix><name>" is an exact match in all but spelling — it wins over
    # a mere suffix match (e.g. "range" is ft_range, not also ft_rrange).
    if "ft_" + name in ALL_EXERCISES:
        return "ft_" + name
    matches = [n for n in ALL_EXERCISES if n.endswith(name)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        ui.error("unknown exercise: %s" % name)
        ui.note("run `python3 -m c_exam --list` to see them all")
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

    if args.timeout < 1 or args.fuzz < 0:
        ui.error("--timeout must be >= 1 and --fuzz must be >= 0")
        return 2

    if args.stats:
        show_stats()
        return 0

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
