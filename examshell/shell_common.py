#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell_common.py  ·  the exam/practice/training flow, shared by both testers

`examshell/examshell.py` (Python) and `c_exam/examshell.py` (C) used to carry a
full copy each of everything below. Now each of them is a thin "tester
module" that supplies only what really differs — its banks, how one
exercise is graded, how a stub is written, its CLI — and hands itself to
these functions as `sh`.

Two layers:

  * the ENGINE — `ExamRun` (one exam as pure state: level, exercise,
    attempts, clocks, RNGs, save/resume, time limit) and `grade()` (grade,
    record stats, work out a hint) — no input, no output.
    Anything that wants to drive an exam (the line-based UI below, a
    full-screen TUI) builds on these.
  * the line-based UI — exam_mode(), practice_mode(), … — which drives the
    engine through examshell/ui.py.

Every collaborator is looked up on `sh` at call time (sh.grade_exercise,
sh.show_subject, sh.N_LEVELS, …), never imported or bound early: the
Python tester rebinds its bank globals on a rank switch, and the tests
patch these names on the tester module.

What a tester module must define
--------------------------------
  constants  TOOL, N_LEVELS, EXERCISES, LEVELS, STANDARD_LEVELS,
             ALL_EXERCISES, DIFFICULTIES, TRAINING_BY_DIFFICULTY,
             TRAINING_EXERCISES, SOURCE_EXT (".py"/".c"), EXAM_PROMPT,
             PRACTICE_PROMPT, EXAM_COMMANDS, PRACTICE_COMMANDS,
             STRICT_EXAM_FLAGS (Config attributes the exam forces on)
  hooks      banner(), Session(login=None), prepare_grading(name, rng, cfg)
             -> GradingJob, grading_notes(cfg) -> [str], make_stub(name,
             cfg), menu_rows(), extra_menu_action(choice, cfg) -> bool
  wrappers   the public flow functions below, re-exported as
             `def exam_mode(cfg): return shell_common.exam_mode(_SH, cfg)`
             and so on — so sh.grade_exercise, sh.show_subject,
             sh.exam_summary, sh.practice_one, … resolve to them.
"""

from __future__ import annotations

import argparse
import copy
import os
import random
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from . import (
    hints,
    session_store,
    stats,
    ui,
    update_check,
)
from ._types import Event, Tester, TesterConfig
from .grader import BankError, Report

if TYPE_CHECKING:
    from .sync import SyncResult

# (index, level, name, function, standard) — see exercise_entries()
ExerciseEntry = Tuple[int, int, str, str, bool]
# (index, difficulty, name, function) — see training_entries()
TrainingEntry = Tuple[int, str, str, str]
# (level, exercise, attempts, seconds) — one cleared level of an exam
HistoryRow = Tuple[int, str, int, float]
_Entry = TypeVar("_Entry", bound=Tuple[Any, ...])
_Config = TypeVar("_Config", bound=TesterConfig)

DRILL_SIZE = 5


# ══════════════════════════════════════════════════════════════
#  SMALL PURE HELPERS
# ══════════════════════════════════════════════════════════════
def command_name(installed: str, module: str) -> str:
    """How the student invoked this tester — the installed console script
    (`examshell`, `examshell-c`) or `python3 -m <module>` — so --help,
    --version and every "run `…`" hint name the command they actually use."""
    import sys

    if os.path.basename(sys.argv[0] or "") == installed:
        return installed
    return "python3 -m " + module


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    return "%02d:%02d:%02d" % (
        seconds // 3600,
        (seconds % 3600) // 60,
        seconds % 60,
    )


def draw(
    rng: random.Random, pool: Sequence[str], avoid: Optional[str] = None
) -> str:
    """Pick an exercise from the pool, avoiding `avoid` when possible."""
    choices = [name for name in pool if name != avoid] or list(pool)
    return rng.choice(choices)


def renumber(entries: Sequence[_Entry]) -> List[_Entry]:
    """Replace each entry's leading index with a fresh 1..N. Filtering
    (by difficulty, by a /query) shrinks the list on screen, so the
    numbers shown must shrink to match — otherwise a number the student
    can see gets rejected as out of range."""
    return [cast(_Entry, (i + 1,) + e[1:]) for i, e in enumerate(entries)]


def filter_entries(
    entries: List[_Entry], query: str, name_col: int, func_col: int
) -> List[_Entry]:
    """Case-insensitive substring match against name and function."""
    if not query:
        return entries
    q = query.lower()
    return [
        e
        for e in entries
        if q in e[name_col].lower() or q in e[func_col].lower()
    ]


def percent(part: float, whole: float) -> int:
    return int(round(100.0 * part / whole)) if whole else 0


def time_left(session: Session, cfg: TesterConfig) -> Optional[float]:
    """Seconds left under --time-limit (negative once it ran out), or None
    when the exam has no limit."""
    if not cfg.time_limit or session.start_time is None:
        return None
    return cfg.time_limit * 60 - (time.time() - session.start_time)


def countdown(session: Session, cfg: TesterConfig) -> str:
    """' · 1:23:45 left' for the exam prompt, or '' without a time limit."""
    left = time_left(session, cfg)
    if left is None:
        return ""
    return " · %s left" % fmt_duration(max(0, left))


# ══════════════════════════════════════════════════════════════
#  SESSION
# ══════════════════════════════════════════════════════════════
class Session(object):
    """One exam's bookkeeping — what session_store saves and
    finish_exam() sums up."""

    def __init__(self, login: Optional[str] = None, n_levels: int = 1) -> None:
        self.login = login or os.environ.get("USER") or "student"
        self.n_levels = n_levels
        self.start_time: Optional[float] = None
        self.level = 1
        self.current_ex: Optional[str] = None
        self.passed: List[str] = []
        self.attempts = 0
        self.history: List[HistoryRow] = []

    def start(self) -> None:
        self.start_time = time.time()

    def elapsed(self) -> str:
        if self.start_time is None:
            return "00:00:00"
        return fmt_duration(time.time() - self.start_time)

    def score(self) -> int:
        return int(len(self.passed) / float(self.n_levels) * 100)


# ══════════════════════════════════════════════════════════════
#  ENGINE  ·  grading
# ══════════════════════════════════════════════════════════════
class GradingJob(object):
    """What a tester's prepare_grading() hands back: how many tests will
    run (for the "Grading … (N tests)" line), a verb for that line, and
    `run()`, which does the grading and returns a grader Report."""

    def __init__(
        self, size: int, run: Callable[[], Report], verb: str = "Grading"
    ) -> None:
        self.size, self.run, self.verb = size, run, verb


class GradeOutcome(object):
    """The result of grade(): the Report plus, for a stuck student, a
    hint."""

    def __init__(
        self, report: Report, filepath: str, hint: Optional[str] = None
    ) -> None:
        self.report, self.filepath, self.hint = report, filepath, hint

    @property
    def ok(self) -> bool:
        return self.report.ok


# What `--help` lists. Everything else still works (scripts, docs/), it
# just isn't in the way: the app and its Settings cover it.
CORE_FLAGS = frozenset(
    (
        "--help",
        "--tui",
        "--exam",
        "--practice",
        "--grade",
        "--stub",
        "--list",
        "--rank",
        "--rendu",
        "--doctor",
        "--version",
    )
)


def hide_advanced_flags(parser: argparse.ArgumentParser) -> None:
    """Keep `--help` to CORE_FLAGS; the rest is described in docs/."""
    for action in parser._actions:
        if action.option_strings and not CORE_FLAGS & set(
            action.option_strings
        ):
            action.help = argparse.SUPPRESS


def solution_path(sh: Tester, ex_name: str, cfg: TesterConfig) -> str:
    return os.path.join(cfg.rendu, ex_name + sh.SOURCE_EXT)


def record(
    sh: Tester, ex_name: str, report: Report, cfg: TesterConfig, mode: str
) -> GradeOutcome:
    """Persist one graded attempt: returns a GradeOutcome. A hint is only
    offered outside the exam, once the student has failed this exercise
    STUCK_THRESHOLD times in a row."""
    ex = sh.ALL_EXERCISES[ex_name]
    stats.record(
        sh.TOOL,
        ex_name,
        ex.get("level"),
        report.ok,
        report.passed,
        report.total,
        mode,
    )
    hint = None
    if not report.ok and mode != "exam":
        if stats.consecutive_fails(sh.TOOL, ex_name) >= hints.STUCK_THRESHOLD:
            hint = hints.hint_for(ex, report)
    return GradeOutcome(report, solution_path(sh, ex_name, cfg), hint)


def grade(
    sh: Tester,
    ex_name: str,
    rng: random.Random,
    cfg: TesterConfig,
    mode: str = "practice",
) -> GradeOutcome:
    """Grade one exercise with no output at all: returns a GradeOutcome.
    Raises BankError when the exercise bank itself is broken."""
    job: GradingJob = sh.prepare_grading(ex_name, rng, cfg)
    return record(sh, ex_name, job.run(), cfg, mode)


# ══════════════════════════════════════════════════════════════
#  ENGINE  ·  one exam
# ══════════════════════════════════════════════════════════════
def exam_config(sh: Tester, cfg: _Config) -> _Config:
    """The config the exam actually grades with. Unless --relaxed, it is as
    strict as the real exam (the tester's STRICT_EXAM_FLAGS all on).
    Practice and training keep the lenient warn-only feedback — that is
    where mistakes are supposed to be cheap. Always a copy: an option
    changed while the exam runs (the app's ctrl+p) can't reach it."""
    strict = copy.copy(cfg)
    if cfg.relaxed:
        return strict
    for flag in sh.STRICT_EXAM_FLAGS:
        setattr(strict, flag, True)
    return strict


def archive_exam_solutions(sh: Tester, cfg: TesterConfig) -> Optional[str]:
    """Move every solution to an exam exercise out of cfg.rendu into
    <rendu>/archive/<now>/ — a new folder each time, so every exam's work
    stays together. Practice-only files are left alone. Returns the folder,
    or None if there was nothing to move. The archive is a subdirectory, so
    grading and sync (both top-level only) skip it."""
    exam_exercises = {n for pool in sh.STANDARD_LEVELS.values() for n in pool}
    paths = [
        path
        for path in (solution_path(sh, n, cfg) for n in sorted(exam_exercises))
        if os.path.isfile(path)
    ]
    if not paths:
        return None
    base = os.path.join(
        cfg.rendu,
        "archive",
        time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time())),
    )
    folder, n = base, 1
    while os.path.exists(folder):
        n += 1
        folder = "%s-%d" % (base, n)
    os.makedirs(folder)
    for path in paths:
        os.replace(path, os.path.join(folder, os.path.basename(path)))
    return folder


class ExamRun(object):
    """One exam as pure state and rules — no input, no output.

    Levels are cleared in order, one exercise drawn per level from the
    Standard pool; you advance only by passing it. The exercise draw and
    the grading use separate RNGs, so `--seed N` reproduces the same
    exercises however often the student grades — and every grademe of a
    level draws the same random tests (see grade_rng). Each level keeps
    its own attempt count and clock (restarted by redraw()), which is what
    ends up in the session history / report.
    """

    def __init__(self, sh: Tester, cfg: TesterConfig) -> None:
        self.sh = sh
        self.cfg = exam_config(sh, cfg)
        self.rng = random.Random(cfg.seed)
        self.session: Session = sh.Session()
        self.level_attempts = 0
        self.level_started: Optional[float] = None
        self.resumed = False

    # ── lifecycle ─────────────────────────────────────────────────────
    def start(self, login: Optional[str] = None) -> Optional[str]:
        """Begin a fresh exam, from an empty rendu/ like the real one:
        solutions to exam exercises left from earlier runs (issue #15) are
        moved to an archive folder of their own. Returns that folder, or
        None if there was nothing to move. A resumed exam keeps its files —
        see resume()."""
        if login:
            self.session.login = login
        self.session.start()
        return archive_exam_solutions(self.sh, self.cfg)

    def resume(self, saved: Event) -> None:
        """Continue a run saved by save() (see session_store).

        The clocks kept running while the exam was saved, like in the real
        exam: both are anchored at the moment of the save (`saved_at`), so
        the pause counts too and --time-limit can't be stretched by
        quitting. A save from before `saved_at` existed resumes its clocks
        where they stopped, as it always did."""
        now = time.time()
        # never in the future: a save synced from a device whose clock is
        # ahead must not hand out extra time
        anchor = min(saved.get("saved_at") or now, now)
        s = self.session
        s.login = saved["login"]
        s.level = saved["level"]
        s.passed = saved["passed"]
        s.attempts = saved["attempts"]
        s.history = [cast(HistoryRow, tuple(row)) for row in saved["history"]]
        s.start_time = anchor - saved["elapsed_seconds"]
        s.current_ex = saved["current_ex"]
        self.rng = session_store.rng_from_saved(saved)
        self.level_attempts = saved.get("level_attempts", 0)
        # Restore how much of this level's clock had already run before the
        # earlier quit — otherwise a resume would restart it from zero and
        # drop that time from session.history / the report.
        self.level_started = anchor - saved.get("level_elapsed_seconds", 0)
        self.resumed = True

    @property
    def n_levels(self) -> int:
        n: int = self.sh.N_LEVELS
        return n

    @property
    def level(self) -> int:
        return self.session.level

    @property
    def current_ex(self) -> Optional[str]:
        return self.session.current_ex

    @property
    def finished(self) -> bool:
        return self.session.level > self.n_levels

    def _new_exercise(self, avoid: Optional[str] = None) -> None:
        pool = self.sh.STANDARD_LEVELS[self.session.level]
        if self.cfg.seed is not None:
            # --seed reproduces the exam: no memory of earlier ones
            self.session.current_ex = draw(self.rng, pool, avoid)
        else:
            self.session.current_ex = session_store.draw_fresh(
                self.sh.TOOL, self.session.level, self.rng, pool, avoid
            )
        self.level_started, self.level_attempts = time.time(), 0

    @property
    def grade_rng(self) -> random.Random:
        """A fresh grading RNG for the current level, the same on every
        grademe: re-grading unchanged code must not draw new random tests
        and flip FAILURE into SUCCESS. It is derived from the draw RNG's
        state without advancing it — that state is what session_store
        saves, so a resumed exam grades with the same tests too (and
        --seed N reproduces them)."""
        peek = random.Random()
        peek.setstate(self.rng.getstate())
        return random.Random(
            "grade-%d-%d-%s"
            % (peek.getrandbits(64), self.session.level, self.current_ex)
        )

    def ensure_exercise(self) -> str:
        """The exercise for the current level, drawn if there isn't one yet
        (a resumed run keeps the one it was saved with)."""
        if self.session.current_ex is None:
            self._new_exercise()
        return cast(str, self.session.current_ex)

    # ── actions ───────────────────────────────────────────────────────
    @property
    def can_redraw(self) -> bool:
        """The real exam never lets you swap an exercise — only --relaxed."""
        return bool(self.cfg.relaxed)

    def redraw(self) -> bool:
        """Draw a different exercise for this level, with a fresh clock and
        attempt count (a solve right after it must not inherit the
        abandoned exercise's). False when redraws aren't allowed."""
        if not self.can_redraw:
            return False
        self._new_exercise(avoid=self.session.current_ex)
        return True

    def begin_attempt(self) -> None:
        self.session.attempts += 1
        self.level_attempts += 1

    def pass_level(self) -> bool:
        """Record the current exercise as passed and move up a level.
        Returns True when that was the last level."""
        s = self.session
        current = cast(str, s.current_ex)  # graded, so one was drawn
        s.passed.append(current)
        s.history.append(
            (
                s.level,
                current,
                self.level_attempts,
                time.time() - cast(float, self.level_started),
            )
        )
        s.level += 1
        s.current_ex = None
        return self.finished

    # ── clock ─────────────────────────────────────────────────────────
    def time_left(self) -> Optional[float]:
        return time_left(self.session, self.cfg)

    def countdown(self) -> str:
        return countdown(self.session, self.cfg)

    def times_up(self) -> bool:
        left = self.time_left()
        return left is not None and left <= 0

    # ── persistence ───────────────────────────────────────────────────
    def save(self) -> None:
        """Save mid-level, so a resume lands on the same exercise and clock."""
        session_store.save(
            self.sh.TOOL,
            self.session,
            self.rng,
            self.session.current_ex,
            self.level_attempts,
            self.level_started,
        )

    def save_between_levels(self) -> None:
        """Save right after a level was cleared — the next one isn't drawn
        yet."""
        session_store.save(self.sh.TOOL, self.session, self.rng, None, 0)

    def discard_save(self) -> None:
        session_store.clear(self.sh.TOOL)


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  grading
# ══════════════════════════════════════════════════════════════
def grade_exercise(
    sh: Tester,
    ex_name: str,
    rng: random.Random,
    cfg: TesterConfig,
    mode: str = "practice",
) -> bool:
    """Grade one exercise, render the report, return True when it is 100%."""
    for note in sh.grading_notes(cfg):
        ui.warn(note)
    try:
        job: GradingJob = sh.prepare_grading(ex_name, rng, cfg)
    except BankError as exc:
        ui.error("exercise bank is broken: %s" % exc)
        return False
    with ui.spinner("%s %s … (%d tests)" % (job.verb, ex_name, job.size)):
        report = job.run()
    # --blind: in the exam, like the real one, you learn THAT you failed,
    # not on which input — testing your own edge cases is part of the exam.
    blind = mode == "exam" and getattr(cfg, "blind", False)
    if mode == "exam":
        # The real grademe shows the first failing test, nothing more —
        # all failures, edge-case labels and the score are Practice.
        ui.exam_trace(report, blind)
    else:
        ui.report(
            report, cfg.show_fails, cfg.diff, solution_path(sh, ex_name, cfg)
        )
    outcome = record(sh, ex_name, report, cfg, mode)
    if outcome.hint:
        ui.hint(outcome.hint)
    return report.ok


def grade_all(sh: Tester, cfg: TesterConfig) -> bool:
    """Grade every exam exercise that has a solution in cfg.rendu.

    Each exercise is graded with a fresh `random.Random(cfg.seed)`, so this
    matches `--grade EXERCISE --seed N` run one at a time. Returns True iff
    every solution that was found passed all of its tests.
    """
    for note in sh.grading_notes(cfg):
        ui.warn(note)
    rows: List[Tuple[int, str, str, str]] = []
    found, all_ok = 0, True
    for _, level, name, _func, _standard in sh.exercise_entries():
        if not os.path.isfile(solution_path(sh, name, cfg)):
            rows.append((level, name, "missing", "—"))
            continue
        found += 1
        try:
            job: GradingJob = sh.prepare_grading(
                name, random.Random(cfg.seed), cfg
            )
        except BankError as exc:
            ui.error("exercise bank is broken: %s" % exc)
            all_ok = False
            rows.append((level, name, "ko", "bank error"))
            continue
        with ui.spinner("%s %s … (%d tests)" % (job.verb, name, job.size)):
            report = job.run()
        all_ok = all_ok and report.ok
        label = (
            "%d/%d" % (report.passed, report.total)
            if not report.fatal
            else report.fatal_title
        )
        rows.append((level, name, "ok" if report.ok else "ko", label))

    ui.overview_table(rows)
    if found == 0:
        ui.note("no solutions found in %s/ — nothing to grade" % cfg.rendu)
    else:
        ui.info(
            "%d/%d solutions found — run --grade EXERCISE for details"
            % (found, len(rows))
        )
    return all_ok


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  listings
# ══════════════════════════════════════════════════════════════
def exercise_entries(sh: Tester) -> List[ExerciseEntry]:
    """[(index, level, name, function, standard), …] ordered by level, then
    name. `standard` marks the exercises the exam actually draws from —
    the rest ("Extra") only ever show up in practice mode."""
    entries: List[ExerciseEntry] = []
    index = 0
    for level in range(1, sh.N_LEVELS + 1):
        for name in sorted(sh.LEVELS[level]):
            index += 1
            entries.append(
                (
                    index,
                    level,
                    name,
                    sh.EXERCISES[name]["function"],
                    sh.EXERCISES[name]["standard"],
                )
            )
    return entries


def training_entries(sh: Tester) -> List[TrainingEntry]:
    """[(index, difficulty, name, function), …] ordered by difficulty, then
    name. A separate listing from exercise_entries() on purpose: the
    training pool is never part of an exam draw, so it never shares a
    table with it."""
    entries: List[TrainingEntry] = []
    index = 0
    for difficulty in sh.DIFFICULTIES:
        for name in sorted(sh.TRAINING_BY_DIFFICULTY[difficulty]):
            index += 1
            entries.append(
                (
                    index,
                    difficulty,
                    name,
                    sh.TRAINING_EXERCISES[name]["function"],
                )
            )
    return entries


def show_subject(
    sh: Tester,
    ex_name: str,
    cfg: TesterConfig,
    session: Optional[Session] = None,
) -> None:
    ui.clear()
    sh.banner()
    if session is not None:
        ui.status_bar(session, sh.N_LEVELS)
    ui.subject(ex_name, sh.ALL_EXERCISES[ex_name], cfg.rendu)


def _screen(sh: Tester) -> None:
    ui.clear()
    sh.banner()
    print()


def list_mode(sh: Tester, interactive: bool = True) -> None:
    if interactive:
        _screen(sh)
    entries = sh.exercise_entries()
    ui.exercise_table(entries)
    ui.info(
        "%d exercises · %d levels · one exercise per level in the exam"
        % (len(entries), sh.N_LEVELS)
    )
    if interactive:
        _pause_back()


def training_list_mode(sh: Tester, interactive: bool = True) -> None:
    if interactive:
        _screen(sh)
    entries = sh.training_entries()
    ui.training_table(entries)
    ui.info(
        "%d training exercises · %d difficulties · practice only, "
        "never drawn into the exam" % (len(entries), len(sh.DIFFICULTIES))
    )
    if interactive:
        _pause_back()


def _pause_back() -> None:
    try:
        ui.pause("\n  Press Enter to go back…")
    except ui.Abort:
        pass


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  exam
# ══════════════════════════════════════════════════════════════
def exam_commands(sh: Tester, cfg: TesterConfig) -> List[Tuple[str, str]]:
    """EXAM_COMMANDS minus `new` unless --relaxed: the real exam never lets
    you redraw an exercise you don't like."""
    return [row for row in sh.EXAM_COMMANDS if cfg.relaxed or row[0] != "new"]


def _times_up(sh: Tester, run: ExamRun) -> bool:
    """End the exam when --time-limit ran out. True when it did."""
    if not run.times_up():
        return False
    run.discard_save()
    sh.exam_summary(run.session, passed=False, timed_out=True)
    return True


def exam_mode(sh: Tester, cfg: TesterConfig) -> None:
    run = ExamRun(sh, cfg)
    cfg = run.cfg
    session = run.session
    _screen(sh)

    saved = session_store.load(sh.TOOL)
    if saved:
        try:
            resume = ui.confirm(
                "  Resume saved exam for %s — level %d?"
                % (saved["login"], saved["level"])
            )
        except ui.Abort:
            return
        if resume:
            run.resume(saved)
            if _times_up(sh, run):  # the limit ran out during the pause
                return
            ui.note("Resumed at level %d." % session.level)
        else:
            run.discard_save()

    if not run.resumed:
        try:
            login = ui.ask("  Login (Enter = %s): " % session.login)
        except ui.Abort:
            return
        archived = run.start(login)
        if archived:
            ui.note("earlier exam solutions moved to %s" % archived)
        if cfg.seed is not None:
            ui.note("seed %d — this exam is reproducible" % cfg.seed)
    if not cfg.relaxed:
        ui.note(
            "realistic mode — graded as strictly as the real exam, no "
            "'new' (start with --relaxed for lenient grading)"
        )
    if cfg.time_limit:
        ui.note("time limit: %d minutes" % cfg.time_limit)
    if getattr(cfg, "blind", False):
        ui.note("blind grading — you'll see THAT a test failed, not which")

    commands = exam_commands(sh, cfg)
    while not run.finished:
        run.ensure_exercise()
        sh.show_subject(run.current_ex, cfg, session)
        ui.commands(commands)

        while True:
            try:
                cmd = ui.ask(
                    "\n  [%s@%s · lvl%d%s]$ "
                    % (
                        session.login,
                        sh.EXAM_PROMPT,
                        session.level,
                        run.countdown(),
                    )
                ).lower()
            except ui.Abort:
                cmd = "quit"
            if _times_up(sh, run):
                return

            if cmd in ("grademe", "g"):
                run.begin_attempt()
                if sh.grade_exercise(
                    run.current_ex, run.grade_rng, cfg, mode="exam"
                ):
                    cleared = session.level
                    last = run.pass_level()
                    ui.level_cleared(cleared)
                    if last:
                        try:
                            ui.pause("  Press Enter to see your summary…")
                        except ui.Abort:
                            pass
                        run.discard_save()
                        sh.exam_summary(session, passed=True)
                        return
                    try:
                        ui.pause("  Press Enter for the next level…")
                    except ui.Abort:
                        run.save_between_levels()
                        sh.exam_summary(session, passed=False)
                        return
                    break
                ui.info("Fix your solution and type 'grademe' again.")
            elif cmd in ("subject", "s"):
                sh.show_subject(run.current_ex, cfg, session)
                ui.commands(commands)
            elif cmd == "status":
                print()
                ui.status_bar(session, sh.N_LEVELS)
            elif cmd == "new" and not run.can_redraw:
                ui.warn(
                    "the real exam has no 'new' — solve this one "
                    "(or start with --relaxed to allow redraws)"
                )
            elif cmd == "new":
                run.redraw()
                sh.show_subject(run.current_ex, cfg, session)
                ui.commands(commands)
                ui.info("New exercise drawn for level %d." % session.level)
            elif cmd == "stub":
                sh.make_stub(run.current_ex, cfg)
            elif cmd in ("quit", "q", "exit"):
                run.save()
                sh.exam_summary(session, passed=False)
                return
            elif cmd == "":
                continue
            else:
                ui.warn(
                    "unknown command — "
                    + " · ".join(name for name, _ in commands)
                )

    run.discard_save()
    sh.exam_summary(session, passed=True)


class ExamResult(object):
    """What finish_exam() produces: the summary panel's title and rows,
    and whether the exam was passed."""

    def __init__(
        self, title: str, rows: List[Tuple[str, object]], passed: bool
    ) -> None:
        self.title, self.rows, self.passed = title, rows, passed


def finish_exam(
    sh: Tester, session: Session, passed: bool, timed_out: bool = False
) -> ExamResult:
    """Close an exam: record a completion (and whether it's a personal
    best) and return an ExamResult to show. No output."""
    rows: List[Tuple[str, object]] = [
        ("Total time", session.elapsed()),
        ("Attempts", session.attempts),
        ("Score", "%d/100" % session.score()),
    ]
    for level, name, attempts, seconds in session.history:
        rows.append(
            (
                "Level %d" % level,
                "%s  (%d attempt%s, %s)"
                % (
                    name,
                    attempts,
                    "" if attempts == 1 else "s",
                    fmt_duration(seconds),
                ),
            )
        )

    if passed:
        seconds = time.time() - session.start_time if session.start_time else 0
        # looked up BEFORE this run is recorded, so it's the best so far
        best = stats.best_exam_time(sh.TOOL)
        stats.record_exam_complete(
            sh.TOOL, seconds, session.attempts, session.score()
        )
        if best is not None and seconds < best:
            rows.append(("Personal best", "yes — %s" % fmt_duration(seconds)))

    title = (
        "EXAM PASSED — all %d levels cleared" % sh.N_LEVELS
        if passed
        else "%s — %d/%d levels cleared"
        % (
            "TIME'S UP" if timed_out else "EXAM ABORTED",
            len(session.passed),
            sh.N_LEVELS,
        )
    )
    return ExamResult(title, rows, passed)


def exam_summary(
    sh: Tester, session: Session, passed: bool, timed_out: bool = False
) -> None:
    ui.clear()
    sh.banner()
    ui.status_bar(session, sh.N_LEVELS)
    result = finish_exam(sh, session, passed, timed_out)
    ui.summary(result.title, result.rows, result.passed)
    hint = sync_hint() if not passed and not timed_out else None
    if hint:
        ui.note(hint)


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  practice · training
# ══════════════════════════════════════════════════════════════
def practice_one(
    sh: Tester,
    ex_name: str,
    cfg: TesterConfig,
    rng: random.Random,
    mode: str = "practice",
) -> None:
    sh.show_subject(ex_name, cfg)
    ui.commands(sh.PRACTICE_COMMANDS)
    while True:
        try:
            cmd = ui.ask(
                "\n  [%s · %s]$ " % (sh.PRACTICE_PROMPT, ex_name)
            ).lower()
        except ui.Abort:
            return
        if cmd in ("grademe", "g"):
            sh.grade_exercise(ex_name, rng, cfg, mode=mode)
        elif cmd in ("subject", "s"):
            sh.show_subject(ex_name, cfg)
            ui.commands(sh.PRACTICE_COMMANDS)
        elif cmd == "stub":
            sh.make_stub(ex_name, cfg)
        elif cmd == "feedback":
            run_feedback(sh, "exam", ex_name)
        elif cmd in ("back", "b", "quit", "q", "exit"):
            return
        elif cmd == "":
            continue
        else:
            ui.warn(
                "unknown command — "
                + " · ".join(name for name, _ in sh.PRACTICE_COMMANDS)
            )


def _pick(choice: str, shown: Sequence[Tuple[Any, ...]]) -> Optional[str]:
    """The exercise name for a typed list number, or None."""
    if not choice.isdigit() or not 1 <= int(choice) <= len(shown):
        return None
    name: str = shown[int(choice) - 1][2]
    return name


def practice_mode(
    sh: Tester, cfg: TesterConfig, ex_name: Optional[str] = None
) -> None:
    rng = random.Random()
    if ex_name:
        sh.practice_one(ex_name, cfg, rng)
        return
    all_entries: List[ExerciseEntry] = sh.exercise_entries()
    query = ""
    while True:
        _screen(sh)
        shown = renumber(filter_entries(all_entries, query, 2, 3))
        ui.exercise_table(shown, numbered=True)
        if query:
            ui.note(
                "filter /%s — %d/%d shown  ('/' alone clears it)"
                % (query, len(shown), len(all_entries))
            )
            if not shown:
                ui.warn("no exercise matches %r" % query)
        try:
            choice = ui.ask(
                "\n  Selection (number, /text to filter, or 'b' to go back): "
            ).lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        if choice.startswith("/"):
            query = choice[1:].strip()
            continue
        picked = _pick(choice, shown)
        if picked is None:
            ui.warn(
                "pick a number between 1 and %d, or /text to filter"
                % len(shown)
            )
            time.sleep(0.8)
            continue
        sh.practice_one(picked, cfg, rng)


DIFFICULTY_KEYS: Dict[str, Optional[str]] = {
    "e": "easy",
    "m": "medium",
    "h": "hard",
    "a": None,
    "w": "weak",
}


def weak_entries(sh: Tester) -> List[TrainingEntry]:
    """Training entries the student has struggled with, worst-first — see
    stats.weakest_exercises(). Recomputed fresh every call (not cached)
    so a grade recorded a moment ago is reflected immediately."""
    training: List[TrainingEntry] = sh.training_entries()
    by_name = {e[2]: e for e in training}
    return [
        by_name[n] for n in stats.weakest_exercises(sh.TOOL, list(by_name))
    ]


def training_mode(
    sh: Tester,
    cfg: TesterConfig,
    ex_name: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> None:
    """Drill the training pool. Reuses practice_one() — grading, `stub` and
    `subject` don't care which pool an exercise came from. `difficulty`
    is either a real difficulty name, None ("all"), or the "weak" sentinel
    (see weak_entries()) — not a difficulty, but reuses the exact same
    filter/pick loop."""
    rng = random.Random()
    if ex_name:
        sh.practice_one(ex_name, cfg, rng, mode="train")
        return
    query = ""
    while True:
        if difficulty == "weak":
            entries = weak_entries(sh)
        else:
            entries = cast(List[TrainingEntry], sh.training_entries())
            if difficulty:
                entries = [e for e in entries if e[1] == difficulty]
        shown = renumber(filter_entries(entries, query, 2, 3))
        _screen(sh)
        ui.training_table(shown, numbered=True)
        ui.note(
            "keys: e=easy · m=medium · h=hard · "
            "w=weak (needs practice) · a=all"
        )
        label = "all" if not difficulty else difficulty
        if difficulty == "weak" and not entries:
            ui.note(
                "no weak spots yet — nothing attempted in training/practice "
                "yet, or everything you've tried you've eventually passed"
            )
        if query:
            ui.note(
                "filter /%s — %d/%d shown  ('/' alone clears it)"
                % (query, len(shown), len(entries))
            )
            if not shown:
                ui.warn("no exercise matches %r" % query)
        try:
            choice = ui.ask(
                "\n  [%s] Selection (number · e/m/h/w to filter · "
                "/text to search · b to go back): " % label
            ).lower()
        except ui.Abort:
            return
        if choice in ("b", "back", "q", "quit", ""):
            return
        if choice.startswith("/"):
            query = choice[1:].strip()
            continue
        if choice in DIFFICULTY_KEYS:
            difficulty = DIFFICULTY_KEYS[choice]
            continue
        picked = _pick(choice, shown)
        if picked is None:
            ui.warn(
                "pick a number, e/m/h/w/a to filter, /text to search, "
                "or b to go back"
            )
            time.sleep(0.8)
            continue
        sh.practice_one(picked, cfg, rng, mode="train")


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  stats · readiness · drill
# ══════════════════════════════════════════════════════════════
def show_stats(sh: Tester) -> None:
    summary = stats.summarize(sh.TOOL)
    _screen(sh)
    rows: List[Tuple[str, object]] = [
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
            (
                (name, row["passes"], row["attempts"])
                for name, row in summary["per_exercise"].items()
            ),
            key=lambda r: r[1] / r[2],
        )
        ui.stats_table(per_ex_rows)
    else:
        ui.note("no grading history yet — practice or grade something first")


_READY_GLYPH = {"passed": "ok", "failed": "ko", "untried": "missing"}


def readiness_mode(sh: Tester, interactive: bool = True) -> None:
    """How ready you are for the real exam: every exercise the exam can
    draw, level by level — passed at least once, tried but never passed,
    or never tried (see stats.readiness())."""
    if interactive:
        _screen(sh)
    levels = stats.readiness(sh.TOOL, sh.STANDARD_LEVELS)
    rows: List[Tuple[int, str, str, str]] = []
    for level, _passed, _total, entries in levels:
        for name, row in entries:
            label = (
                "%d/%d passed" % (row["passes"], row["attempts"])
                if row["attempts"]
                else "never tried"
            )
            rows.append((level, name, _READY_GLYPH[row["status"]], label))
    ui.overview_table(
        rows, title="Exam readiness — every exercise the exam can draw"
    )
    done = sum(passed for _, passed, _, _ in levels)
    total = sum(count for _, _, count, _ in levels)
    summary_rows: List[Tuple[str, object]] = [
        (
            "Level %d" % level,
            "%d/%d passed  (%d%%)" % (passed, count, percent(passed, count)),
        )
        for level, passed, count, _ in levels
    ]
    summary_rows.append(
        ("Overall", "%d/%d  (%d%%)" % (done, total, percent(done, total)))
    )
    ui.summary("Exam readiness", summary_rows, passed=done == total)
    if done < total:
        weakest = min(levels, key=lambda lv: percent(lv[1], lv[2]))
        ui.info(
            "level %d is your biggest gap — a daily drill (--drill, "
            "My gaps in the app) works through your gaps" % weakest[0]
        )
    if interactive:
        _pause_back()


def drill_mode(sh: Tester, cfg: TesterConfig, n: int = DRILL_SIZE) -> None:
    """A short daily session: weak spots, then never-tried exercises, then
    the ones practised longest ago (see stats.drill_queue()) — only
    exercises the real exam can draw."""
    names = [
        name for _, _, name, _, standard in sh.exercise_entries() if standard
    ]
    queue = stats.drill_queue(sh.TOOL, names, n)
    rng = random.Random()
    for i, name in enumerate(queue, 1):
        _screen(sh)
        ui.info(
            "Drill %d/%d — %s (level %d)"
            % (i, len(queue), name, sh.ALL_EXERCISES[name]["level"])
        )
        try:
            ui.pause("  Press Enter to start, Ctrl-C to end the drill…")
        except ui.Abort:
            return
        sh.practice_one(name, cfg, rng, mode="drill")
    ui.success(
        "drill done — %d exercise%s. `--readiness` shows where you stand."
        % (len(queue), "" if len(queue) == 1 else "s")
    )


# ══════════════════════════════════════════════════════════════
#  LINE-BASED UI  ·  main menu
# ══════════════════════════════════════════════════════════════
def with_sync_row(
    rows: Sequence[Tuple[str, str, str]],
) -> List[Tuple[str, str, str]]:
    """The tester's menu rows plus the shared "s  Sync" and "f  Feedback"
    entries, right before Quit."""
    from . import settings, sync

    hint = (
        "(with %s)" % sync.remote_url(settings.DATA_DIR)
        if sync.is_configured(settings.DATA_DIR)
        else "(not set up — see docs/sync.md)"
    )
    sync_row = ("s", "Sync progress", hint)
    feedback_row = (
        "f",
        "Give feedback",
        "(opens a GitHub form — nothing is sent automatically)",
    )
    quit_rows = [r for r in rows if r[0] == "q"]
    return (
        [r for r in rows if r[0] != "q"] + [sync_row, feedback_row] + quit_rows
    )


def main_menu(sh: Tester, cfg: TesterConfig) -> None:
    """Entries 1-4 and q are the same in both testers; anything else goes
    to the tester's own extra_menu_action() (rank switch, readiness, …)."""
    update = update_check.start_background_check(cfg.no_update_check)
    while True:
        ui.clear()
        sh.banner()
        if update["notice"]:
            ui.note(update["notice"])
        print()
        ui.menu(with_sync_row(sh.menu_rows()))
        try:
            choice = ui.ask("\n  Selection: ").lower()
        except ui.Abort:
            choice = "q"
        if choice == "1":
            sh.exam_mode(cfg)
            try:
                ui.pause("\n  Press Enter for the main menu…")
            except ui.Abort:
                return
        elif choice == "2":
            sh.practice_mode(cfg)
        elif choice == "3":
            sh.list_mode()
        elif choice == "4":
            sh.training_mode(cfg)
        elif choice in ("q", "quit", "exit"):
            ui.info("Good luck on the real exam!")
            print()
            return
        elif choice in ("s", "f"):
            print()
            if choice == "s":
                run_sync(sh, cfg)
            else:
                run_feedback(sh)
            try:
                ui.pause("\n  Press Enter for the main menu…")
            except ui.Abort:
                return
        else:
            sh.extra_menu_action(choice, cfg)


def resolve_exercise(sh: Tester, name: str, prefix: str) -> Optional[str]:
    """Accept the exact name, or a unique suffix like 'inter'. Searches both
    the exam pool and the training pool. "<prefix><name>" is an exact match
    in all but spelling — it wins over a mere suffix match (e.g. "range" is
    ft_range, not also ft_rrange)."""
    if name in sh.ALL_EXERCISES:
        return name
    if prefix + name in sh.ALL_EXERCISES:
        return prefix + name
    matches: List[str] = [n for n in sh.ALL_EXERCISES if n.endswith(name)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        ui.error("unknown exercise: %s" % name)
        ui.note("run `%s --list` to see them all" % sh.PROG)
    else:
        ui.error(
            "ambiguous exercise %r — did you mean %s?"
            % (name, ", ".join(sorted(matches)))
        )
    return None


def run_tui(
    sh: Tester,
    cfg: TesterConfig,
    args: argparse.Namespace,
    rendus: Optional[Dict[str, str]] = None,
) -> Optional[int]:
    """--tui: hand over to the full-screen app (examshell/tui/) when it can run
    here, starting where the other flags point (--exam, --practice X).
    `rendus`: the other testers' solution folders, by SYNC_SLOT. Returns
    an exit code, or None — after saying why — to fall back to the
    line-based UI."""
    from . import tui

    if not tui.available():
        ui.warn(tui.why_unavailable() + " — using the normal interface")
        return None
    start: Union[None, str, Tuple[str, str]] = None
    if args.exam:
        start = "exam"
    elif getattr(args, "practice", None) is not None:
        if args.practice:
            name: Optional[str] = sh.resolve_exercise(args.practice)
            if not name:
                return 2
            start = ("practice", name)
        else:
            start = "practice"
    return tui.run(sh, cfg, start, rendus)


def sync_dirs(sh: Tester, cfg: TesterConfig) -> Dict[str, str]:
    """{slot: local dir} for examshell/sync.py — this tester's own --rendu, the
    other tester's default folder, so one sync carries both."""
    dirs = {"rendu": "rendu", "c_rendu": "c_rendu"}
    dirs[sh.SYNC_SLOT] = cfg.rendu
    return dirs


def run_sync(
    sh: Tester, cfg: TesterConfig, setup_url: Optional[str] = None
) -> int:
    """--sync / --sync-setup URL. Returns a process exit code."""
    from . import settings, sync

    # No spinner: git may need to ask for a password / key passphrase.
    ui.info(
        "syncing with %s …"
        % (setup_url or sync.remote_url(settings.DATA_DIR) or "your repo")
    )
    try:
        if setup_url:
            result = sync.setup(
                setup_url, settings.DATA_DIR, sync_dirs(sh, cfg)
            )
        else:
            result = sync.sync(settings.DATA_DIR, sync_dirs(sh, cfg))
    except sync.SyncError as exc:
        ui.error(str(exc))
        return 1
    if setup_url:
        ui.success("this device is connected to %s" % setup_url)
        ui.note(
            "make sure that repository is PRIVATE — it holds your solutions"
        )
    ui.success(result.summary())
    for backup in result.backups:
        ui.note(
            "a newer version came from the repo — your older one is kept at %s"
            % backup
        )
    return 0


def sync_hint() -> Optional[str]:
    """The line to show after an exam is paused, when sync is set up."""
    from . import settings, sync

    if sync.is_configured(settings.DATA_DIR):
        return (
            "continue on another device: sync (s in the app) here, "
            "then on the other device"
        )
    return None


_DOCTOR_GLYPH = {
    "ok": ("✔", "GREEN"),
    "warn": ("⚠", "YELLOW"),
    "fail": ("✖", "RED"),
}


def run_doctor(sh: Tester, cfg: TesterConfig) -> int:
    """--doctor: check this machine, print one line per check plus the fix
    for anything that's off. Exit code 1 only when something is broken."""
    from . import doctor

    sh.banner()
    print()
    checks = doctor.run_checks(
        cc=getattr(cfg, "cc", "cc"),
        c_required=sh.SYNC_SLOT == "c_rendu",
        no_update_check=cfg.no_update_check,
    )
    width = max(len(c.name) for c in checks)
    for check in checks:
        glyph, colour = _DOCTOR_GLYPH[check.status]
        print(
            ui.IND0
            + ui.c(glyph, colour)
            + "  "
            + ui.c(check.name.ljust(width), "BOLD")
            + "  "
            + check.detail
        )
        if check.fix:
            print(ui.IND0 + " " * (width + 5) + ui.c("→ " + check.fix, "GRAY"))
    print()
    failed = [c for c in checks if c.status == "fail"]
    warned = [c for c in checks if c.status == "warn"]
    if failed:
        ui.error(
            "%d problem%s to fix before this tester works fully"
            % (len(failed), "" if len(failed) == 1 else "s")
        )
        return 1
    if warned:
        ui.success(
            "ready — %d optional thing%s not set up (see → above)"
            % (len(warned), "" if len(warned) == 1 else "s")
        )
    else:
        ui.success("everything is ready")
    return 0


def tester_label(sh: Tester) -> str:
    """'Python · Exam Rank 03' / 'C · Exam Rank 02' — matches the issue
    forms' exam dropdown."""
    if hasattr(sh, "RANK"):
        return "Python · %s" % sh.RANK.label
    return "C · Exam Rank 02"


def run_feedback(
    sh: Tester, kind: Optional[str] = None, exercise: Optional[str] = None
) -> int:
    """--feedback / the menu's "f" / practice's `feedback`: open (or print)
    the prefilled issue form. Asks which kind when `kind` is None."""
    from . import feedback

    if kind is None:
        rows = [
            (str(i), label, "")
            for i, (_k, label) in enumerate(feedback.KIND_LABELS, 1)
        ]
        ui.menu(rows)
        try:
            choice = ui.ask("\n  What kind of feedback? ").strip()
        except ui.Abort:
            return 0
        if not choice.isdigit() or not 1 <= int(choice) <= len(rows):
            return 0
        kind = feedback.KIND_LABELS[int(choice) - 1][0]
    url = feedback.issue_url(kind, tester_label(sh), exercise)
    if feedback.open_in_browser(url):
        ui.success(
            "opened the form in your browser — "
            "nothing is sent until you submit it"
        )
    else:
        ui.info(
            "open this link to give feedback "
            "(nothing is sent until you submit it):"
        )
    print("  " + url)
    return 0


def auto_sync_enabled() -> bool:
    from . import settings

    return bool(settings.load_config().get("auto_sync"))


def set_auto_sync(on: bool) -> int:
    """--auto-sync on|off. Returns a process exit code."""
    from . import settings, sync

    if not settings.update_config("auto_sync", bool(on)):
        ui.error("could not write %s" % settings.CONFIG_PATH)
        return 1
    if on:
        ui.success(
            "auto-sync on — every session pulls first and pushes when it ends"
        )
        if not sync.is_configured(settings.DATA_DIR):
            ui.note(
                "sync isn't set up on this device yet: add your private "
                "repo in the app's Settings (o), or --sync-setup URL — "
                "see docs/sync.md"
            )
    else:
        ui.success("auto-sync off — sync yourself with s in the app")
    return 0


def auto_sync(
    sh: Tester, cfg: TesterConfig, when: str
) -> Optional[SyncResult]:
    """Called around every interactive session (`when` = "start" / "end").
    Does nothing unless auto-sync is on and sync is set up; a failure
    (offline, …) is only ever a one-line warning — never a reason not to
    practise."""
    from . import settings, sync

    if not auto_sync_enabled() or not sync.is_configured(settings.DATA_DIR):
        return None
    ui.info(
        "auto-sync (%s) …"
        % (
            "pulling your progress"
            if when == "start"
            else "pushing your progress"
        )
    )
    try:
        result = sync.sync(settings.DATA_DIR, sync_dirs(sh, cfg))
    except (sync.SyncError, OSError) as exc:
        ui.warn(
            "auto-sync skipped — %s "
            "(your progress stays here; sync later with s in the app)" % exc
        )
        return None
    ui.note(result.summary())
    for backup in result.backups:
        ui.note(
            "a newer version came from the repo — your older one is kept at %s"
            % backup
        )
    return result
