# Changelog

Notable changes to this project, newest entries first. This tracks the
*tester itself* (grading logic, exercise banks, UX) — not students'
`rendu/` solutions. Loosely follows [Keep a Changelog](https://keepachangelog.com/).
Versions follow `examshell/version.py`; when a merge to `main` bumps it,
`.github/workflows/release.yml` tags it and publishes that version's section
below as a GitHub Release. Entries before 0.2.0 are grouped by date.

## 1.0.0 — 2026-10-08

**Less, calmer, and the important things work.** One way in (`make`), one
app with five menu entries, an exam that behaves like the real one, and the
terminal's own colours. Everything rarely needed still works from the
command line but no longer gets in the way.

### Added
- **`make` is all you need** — on a fresh clone it installs everything
  with uv (fetching uv into `~/.local/bin` first if the machine has none,
  no sudo) and opens the app; afterwards it just opens it, on the exam you
  picked last (C Rank 02 included).
- **Settings in the app** (`o`): exam time limit, time per test, random
  tests, C compiler, sync repo (set it up right there) and auto-sync —
  saved and applied at once.
- **A first start that asks** which exam you're practising for (C Rank 02
  or Python Rank 03 / 04 / 05) instead of assuming Rank 03.
- **`?` lists every key**, on every screen.
- **Crash log:** an unexpected error is written to
  `~/.examshell/crash.log`, and the next start offers to report it — a
  prefilled GitHub bug form, nothing sent until you submit it.
- **`e` opens your solution in your editor** — VS Code when its `code`
  command is installed, else `$VISUAL` / `$EDITOR`; a stub first if there
  is no file yet.
- **Practice tabs:** *Exam exercises* (only what the exam can draw),
  *My gaps* (the drill queue) and *Extra* (the banks' extras and the
  LeetCode-style training pool).
- **Progress** — readiness and history on one screen; `p` practises your
  gaps.
- **`make mutate`** (`tools/mutate.py`) — mutation-tests the exercise
  banks: each reference solution is changed in one small place at a time
  and graded against its own tests; a change the tests miss is reported
  with an input that exposes it. This is how the test gaps below were
  found.

### Changed
- **The exam grades like the real one:** `grademe` shows SUCCESS, or
  FAILURE with a trace of the first failing test — no hints, no other
  failures. A failed level keeps its exercise until it passes.
- **Practice results are compact:** one verdict line, the first three
  failing tests one line each (call, edge case, got ≠ expected); `d` shows
  every detail.
- **The menu has five entries** — Exam, Practice, Progress, Switch exam,
  Quit — with sync (`s`), feedback (`f`) and settings (`o`) as keys.
  Training, Daily drill, Readiness and Stats are no menu entries of their
  own any more (see Practice and Progress).
- **Practice and exam screens:** the subject on top, the results below,
  full width — made for a terminal next to your editor; the results pane
  is only as tall as it needs to be.
- **The terminal's own colours** — the app uses Textual's ANSI theme and
  one quiet border style; no logo, no emoji.
- **The Makefile has five commands:** `make` (start), `make install`,
  `make update` (now also reinstalls), `make doctor` and `make dev` (the
  developer targets: `test`, `unit`, `check`, `c-test`, `lint`, `format`,
  `mutate`, `clean`). `make tui` still works.
- **`--help` lists the main flags only**; the rest still works and is
  described in `docs/`.
- **`--save-config` merges** into `config.json` instead of replacing it.
- **Copy text out of the app** — drag over the subject, the results or the
  picker preview with the mouse, then ctrl+c. Needs Textual 2.0+.
- **The exam clock keeps running while an exam is saved** — `quit` and a
  later resume no longer pause it, so the time limit can't be stretched by
  quitting; a resume after the limit ran out ends with "TIME'S UP". Total
  and per-level times include the pause.
- **`make lint` = ruff + flake8 + `mypy --strict`**, and CI runs it as its
  own job, on `main` and `beta`.
- **Bare stub in the exam** — like the real exam, the stub is only the
  prototype/signature: no `main()`, no self-check. Practice and
  `--relaxed` keep the full helper stub.
- **Docs:** a short README around `make` and the app; `docs/` rewritten to
  match; the old step-by-step `TUTORIAL.md` is gone (the README covers a
  first session).

### Removed
- **Badges / achievements** — a passed exam still says when it was a
  personal best.
- **Markdown exam reports** (`~/.examshell/reports/`) — sync (`s`) still
  carries old ones.
- **Colour themes** (`--theme light/highcontrast`) — the terminal's colours
  are used everywhere.
- **The plain venv + pip install** and `requirements.txt` — uv only.
- **The ~50 play targets in the Makefile** (`make run`, `make exam`,
  `make grade`, `make sync`, all `c-*` play targets …) — the app covers
  them; the command line still has every mode.

### Fixed
- **Copy and paste in the full-screen app outside Ghostty & co.** (beta —
  not yet confirmed on a real Linux desktop; feedback welcome) —
  ctrl+c only sent OSC 52, which GNOME Terminal (and every VTE terminal),
  macOS Terminal and xterm ignore, so nothing was copied there; ctrl+v in
  an input field only pasted what was copied inside the app. On a local
  session both now also go through the system clipboard (`pbcopy`,
  `wl-copy`, `xclip` or `xsel`, whichever is installed); over ssh it stays
  OSC 52 only.
- **`make doctor` no longer reports an update that doesn't exist** — it
  trusted the day-long update-check cache, so a stale or bogus entry (a
  test run once left "99.0.0" there) showed up as "available". `doctor`
  now always asks GitHub afresh and rewrites the cache.
- **A new exam starts from an empty `rendu/`** (#15) — drawing an exercise
  you had already solved meant `stub` refused to create the file, and the
  old solution sat there in the middle of the exam. Starting a new exam now
  moves earlier solutions to exam exercises into
  `rendu/archive/<date-time>/`, one folder per exam; practice-only files
  stay. Resuming a saved exam keeps its files as they are.
- **A new exam draws different exercises** (#16) — with two or three
  exercises per level, independent random draws often repeated the last
  exam's. Each level is now dealt like a shuffled deck across exams
  (remembered in `~/.examshell/exam_draws_<tool>.json`): you get every
  exercise of a level once before any repeats. `--seed` exams are
  unaffected.
- Tests run against a throwaway `EXAMSHELL_HOME`, so no test can write
  into the real `~/.examshell` anymore.
- In the app's exam: pressing `n` while a grade was still running drew a new
  exercise and then showed (and could pass the level with) the old one's
  result. `n` now waits for the grade.
- **`ft_atoi_base` tests** — random cases stay within the subject (base
  2-16, no int overflow); more curated edge cases; a leading `+` or space
  is no longer tested, since the subject doesn't define it.
- **Exam `stub` for `fizzbuzz`** — the bare stub declared
  `main(int argc, char **argv)` for a program that never gets an argument,
  so a correct solution written into it failed the exam's `-Werror` on the
  unused parameters. Programs without arguments now get `main(void)`.
- **`py_capitalizer` tests** — `text.title()` passed every test although it
  also capitalises after `-`, `'` and digits (`"it's"` → `"It'S"`). New
  curated cases pin down that only a space starts a new word.
- **`--doctor` honours `--no-update-check`** — it used to ask GitHub anyway.
- **Resume prompt** — a typo at "Resume saved exam? [Y/n]" counted as
  "no" and threw the saved exam away; anything but y/n now asks again.
- **C crash report** — the case the program crashed on shows
  `[crashed: SIGSEGV]` instead of an empty result, later cases show
  `[not run — crashed on case N]`.
- **Test gaps found by mutation testing** (each bank oracle altered by
  one operator/constant, then run against its own tests):
  `py_island_matrix_counter` didn't catch a missing `0 <=` bound (Python's
  `matrix[-1]` silently wraps around and joins islands on opposite edges);
  `py_three_sum` didn't catch broken duplicate skipping or a stuck `hi`;
  `py_number_base_converter` never fed base 1 or 37 a digit that would
  still parse. New curated cases cover all three.
- **C bank: test gaps found the same way** (oracles mutated in C, each
  mutant compiled and graded, survivors re-run with 200 fuzz cases).
  The classic `c < 'z'` / `c < 'Z'` off-by-one passed `ulstr`,
  `alpha_mirror`, `repeat_alpha` and `is_palindrome_str` — no case had a
  `z` or `Z`. Also covered now: `fprime` on prime squares and powers,
  `paramsum` with 10 arguments, `rev_wstr` with a one-letter first word,
  `last_word ""`, `wdmatch` failing on the first character, `max_gap`
  with two elements, `ft_atoi` with a `0` inside the number.

## 0.6.0 — 2026-10-01

### Added
- **Feedback in one step** — `examshell --feedback [exam|bug|idea]`,
  `make feedback` / `make c-feedback`, `f · Give feedback` in both plain
  menus, `feedback` in practice, "💬 Feedback" and `f` in the full-screen
  app. Opens the matching issue form with version, exam, exercise and (for
  bugs) OS/Python prefilled; never sends anything itself, and only starts a
  browser where a graphical one can exist.
- **Edge-case fuzzing for the last three C exercises** — `flood_fill`,
  `ft_list_foreach`, `ft_list_remove_if` get whole-case generators
  (`CASE_FUZZERS`): head / tail / every / no match and the empty list for
  `remove_if`, corner / edge / island / off-grid starts for `flood_fill`.
  Every exam exercise except `fizzbuzz` is now fuzzed.
- **Auto-sync** — `examshell --auto-sync on` / `make auto-sync`: every
  session pulls when it starts and pushes when it ends; offline it's only a
  warning. Shown in `doctor`.
- README: a short "practice tool, nothing more" note; `docs/repo-about.md`
  with the description and topics for the GitHub "About" box.

### Changed
- `settings.update_config()` changes one saved preference without
  touching the others.

### Release process
- **Releases publish themselves.** A merge to `main` that changes
  `examshell/version.py` runs the tests, tags `vX.Y.Z`, and creates the
  GitHub Release with the CHANGELOG section as notes and the built
  package (wheel + sdist) attached — no manual tag any more. "Run
  workflow" on the Release action does the same by hand.

## 0.5.0 — 2026-10-01

### Added
- **Install with one command** — `uv tool install --python 3.12
  "examshell[tui] @ git+https://github.com/jasuoh/42-exam-tester"` puts
  `examshell` (Python) and `examshell-c` (C) on your PATH; run them from
  any folder (solutions go into `rendu/` / `c_rendu/` there). Update with
  `uv tool upgrade examshell`.
- **`examshell --doctor` / `make doctor` / `make c-doctor`** — checks
  Python, how it's installed and whether an update is out, rich and
  Textual, a C compiler that really compiles and runs a test program,
  valgrind, git, the data folder and the sync setup, with the fix for
  anything that's off.
- **Switch exam in the full-screen app** — "🔀 Switch exam" moves between
  Python Rank 03 / 04 / 05 and C Rank 02 without restarting; `make tui`
  covers both testers now.
- **Sync from everywhere** — `make c-sync` / `make c-sync-setup`, an
  `s · Sync progress` entry in both plain menus and "🔄 Sync" in the
  full-screen app (runs in the background).

### Changed
- **The Python tester's package is now `examshell`** (was `src`):
  `python3 -m examshell`. `python3 -m src` still works and points at the
  new name.
- **Dependencies managed with uv** — `pyproject.toml` declares them,
  `uv.lock` pins them, `make install` runs `uv sync --extra tui` when uv
  is installed and falls back to venv + pip otherwise. CI installs the
  "rich" leg exactly that way.
- `--help`, `--version` and hints name the command you actually used
  (`examshell`, `examshell-c` or `python3 -m …`); update notices say
  `make update` or `uv tool upgrade examshell` depending on the install.

## 0.4.0 — 2026-09-30

### Added
- **`make sync` — continue on another device.** Progress, the paused
  exam, exam reports and your `rendu/` + `c_rendu/` solutions travel
  through your own private git repository (`make sync-setup REPO=<url>`
  once per device). The tester combines both sides itself — history is
  unioned, the newer paused exam wins, the newer edit of a solution wins
  with the older one backed up — so there are never git conflicts.
  Settings stay per device. `src/sync.py`, docs/features.md.
- **`EXAMSHELL_HOME`** moves the data folder, e.g. into a folder
  iCloud/Dropbox already syncs.
- After pausing an exam, the summary reminds you to `make sync` when sync
  is set up (both interfaces).

### Changed
- A saved exam now records when it was saved, and finishing an exam
  leaves a small "cleared" marker instead of deleting the file — so a
  finished exam can't come back from another device.

## 0.3.0 — 2026-09-27

### Added
- **✨ Full-screen app** (`make tui` / `make c-tui` / `--tui`) — optional,
  built on Textual (Python 3.9+, `make install`). Subject and results side
  by side, grading in the background, **watch mode** (`w`: re-grade on
  every save), drill queue, exam with login/resume, level stepper,
  countdown and quit-and-save, a readiness heatmap, and stats with your
  practice streak, a 4-week activity chart and recent exams. It drives the
  same engine as the plain interface; without Textual `--tui` explains why
  and falls back. See docs/features.md.
- **`--blind`** (exam) — shows how many tests failed, not which inputs.
- `stats.daily_activity()`, `practice_streak()`, `exam_history()`.
- **Issue forms** for "exercise differs from the real exam", bugs and
  feedback.
- `tools/screenshots.py` regenerates `docs/img/`.

### Changed
- **README is now a one-page landing page**; the full documentation moved
  unchanged into `docs/` (python, c, features, development).
- Subject text is reflowed into paragraphs so it wraps to any width.
- `write_stub()` / `finish_exam()` return their result as data (the
  `make_stub()` / `exam_summary()` wrappers still print it).

### Fixed
- **C program failures hid a missing trailing newline**: expected and got
  were both shown with the newline stripped, so `'abc'` vs `'abc'` could
  fail with no visible difference. Program output is now shown raw
  (`'abc\n'` vs `'abc'`).

### Changed (engine)
- **One shared flow for both testers** (`src/shell_common.py`). The exam,
  practice, training, readiness, drill and menu logic used to exist twice
  (~900 identical lines in `src/examshell.py` and `c_exam/examshell.py`);
  each tester now only supplies what really differs — its banks, how one
  exercise is graded, stubs, its CLI. No behaviour change.
- **Engine separated from the display**, as groundwork for the full-screen
  TUI (see PLAN.md): `ExamRun` holds one exam as pure state and rules
  (levels, draws, attempts, clocks, save/resume, time limit), `grade()`
  grades and records an attempt and returns report, new badges and hint as
  data. The existing line-based UI now drives both.

## 0.2.0 — 2026-09-27

### Changed
- **The exam now grades as strictly as the real one** (both testers). In
  `--exam`, Python fails on any import and C fails on compiler warnings
  (`-Werror`) and forbidden calls; `new` (redraw an exercise) is gone.
  Practice and training keep the lenient warn-only feedback. `--relaxed`
  restores the previous lenient exam.
- C reports now show `repr()` of both expected and got output, so tabs,
  trailing spaces and newlines are visible (got used to be raw, which also
  made `--diff`'s pointer index the wrong character).

### Added
- **`--time-limit MIN`** — ends the exam with a *TIME'S UP* summary, with a
  countdown in the exam prompt.
- **Edge-case fuzzing for C "program" exercises** — every program except
  `fizzbuzz` names an argv shape (`fuzz_argv` in `c_exam/bank.py`) and
  `--fuzz N` now adds random cases built from the usual exam traps: runs of
  spaces and tabs, leading/trailing blanks, empty/blank strings,
  punctuation, wrong argc. See `ARGV_SHAPES` in `c_exam/grader.py`.
- **Reproducible failing cases** — a failing C program case shows a
  pasteable `./prog 'arg' $'\targ'` command, a failing C function case its
  call values (was just `[case N]`).
- **Edge-case labels** (`src/case_labels.py`) — every failing test names
  what kind of input it was: `empty string`, `only whitespace`, `tabs`,
  `repeated spaces`, `zero`, `negative number`, `INT_MIN/INT_MAX`,
  `empty list`, `single element`, `no arguments`.
- **`--readiness` / `make readiness`** (and `c-readiness`) — every
  exercise the exam can draw, per level, as passed / failed / never tried,
  with per-level and overall scores. Menu entry in both testers.
- **`--drill [N]` / `make drill`** (and `c-drill`) — a short session from
  your own history: weak spots (at most half), then never-tried exercises,
  then the longest-unpractised passes. Menu entry in both testers.
- **`inter`** — the missing Level 2 standard exercise of the C bank.
- **Versioning and releases** — `src/version.py` (0.2.0), `--version` on
  both testers, and `.github/workflows/release.yml`: pushing a `vX.Y.Z` tag
  publishes that version's section of this file as a GitHub Release.
- **Update notice** (`src/update_check.py`) — the interactive menu checks
  GitHub for a newer release at most once a day in the background (cached,
  silent offline). `--no-update-check` / `EXAMSHELL_NO_UPDATE_CHECK=1` turn
  it off; `make update` pulls the new version.

### Fixed
- **`--seed` exams weren't reproducible** — grading drew its fuzz cases
  from the same RNG as the exercise draw, so the exercise of every later
  level depended on how often you typed `grademe`. Grading has its own
  (still seed-deterministic) RNG now, in both testers.
- **C program infinite loops took 30–65 s to grade** — every case waited
  out the full timeout. Like the Python sandbox, grading now skips the
  remaining cases after 3 consecutive timeouts.
- `--grade range` (C) was reported as ambiguous between `ft_range` and
  `ft_rrange`; the exact `ft_`/`py_`-prefixed name now wins.
- Two unit tests failed — and created `/this/does/not/exist/...` — when run
  as root (Docker, CI containers); they now use a path that is uncreatable
  for every user.
- `pyproject.toml` / README badges pointed at the repo's old name.
- Training mode's invalid-input warning now lists every filter key.

### Added (earlier in this release)
- **Exam Rank 04 and Rank 05 (Python)** — the Python tester now carries
  three exam pools instead of one, selected with `--rank 03|04|05`
  (`RANK=04` from the Makefile) or menu entry **5 · Switch exam rank**:
  - `src/exam_bank_r04.py` — 7 subjects over 4 levels
    (`py_array_rotation_detector`, `py_constellation_mapper`,
    `py_list_intersection_finder`, `py_merge_sorted_lists`,
    `py_palindrome_partitioner`, `py_package_dependency_resolver`,
    `py_sliding_window_maximum`).
  - `src/exam_bank_r05.py` — 7 subjects over 3 levels
    (`py_compress_decompress`, `py_spiral_generator`,
    `py_graph_cycle_detector`, `py_schedule_meetings`,
    `py_island_matrix_counter`, `py_prism_detector`, `py_word_ladder`).
  - `src/ranks.py` — the registry tying each rank to its bank, its level
    count and the `tool` tag its stats/saved exam/reports are filed under
    (`py` / `py04` / `py05`). Rank 03 keeps the pre-existing `py` tag, so
    no history recorded before this change is lost, and a saved exam can
    never be resumed into a different rank. The training pool is shared by
    all three (it is never part of an exam draw).
  - Both new banks are built the same way as `exam_bank.py` — verified
    reference oracle, curated edge cases, a fuzzer and a hand-written
    stuck-student hint per exercise — and every subject is a documented
    one, so all 14 are Standard (★) and there is no Extra pool.
  - New: `--list-ranks` / `make ranks`. `--check` (`make check`) now
    validates *every* rank's bank plus the training bank in one pass;
    `--rank` narrows it to one.
- **Multi-function exercises** (`grader.parts_of()` / `build_plan()`) — a
  subject can now ask for more than one function and still be one exercise
  with one verdict. Rank 05's `py_compress_decompress` is the first: each
  function gets its own oracle, cases and fuzz, both must be defined, a
  failing call is labelled with the function it came from, and the
  generated stub defines both.
- **Tuple and non-string-dict-key fidelity in the sandbox**
  (`grader.encode_value()` / `decode_value()`) — cases travel to the
  grading subprocess as JSON, which silently flattened a tuple into a list
  and stringified an `int` dict key. Both are now tagged for the trip and
  arrive exactly as the bank wrote them, so Rank 05's `schedule_meetings`
  (a tuple of tuples), `prism_detector` (a list of tuples) and
  `graph_cycle_detector` (a dict keyed by `int`) are graded honestly —
  returning a list where a tuple was asked for now fails, as it would on
  the real exam. `deep_eq()` gained a tuple branch to match, and
  `selftest()` checks every expected value survives the round trip.
- **Achievements** (`src/achievements.py`, shared by both testers) — 10
  badges (First Blood, Perfectionist, Comeback Kid, Redemption, Full
  Coverage, Night Owl, Early Bird, Century, Exam Cleared, Flawless Exam),
  each a pure function of the student's own `stats.jsonl` history —
  nothing new is persisted. A newly-earned badge is announced the moment
  it happens (after any `--grade`/practice/train/exam call, not just at
  exam completion); `--stats` now shows the full roster, earned and
  locked, with a description of how to unlock each one. This replaces
  and generalizes the old ad-hoc "First full clear!" / "Flawless — no
  retries" logic that lived duplicated in both `examshell.py`'s and only
  ever showed at the very end of a full exam run.
- Colour-coded pass-rate bars in `--stats`'s per-exercise table (green
  solid / yellow shaky / red struggling), sorted worst-first — it
  previously showed bare "N/M passed" text despite the bar primitive
  already existing elsewhere in `ui.py`.
- A live spinner while grading is in progress (`ui.spinner()`, wraps the
  blocking `grader.grade()` call) — compiling a C exercise, running a
  big fuzz batch, or an optional valgrind pass can take a few seconds
  with zero prior feedback; now there's a visible "still working" signal
  instead of a silent wait. Plain (non-rich) terminals keep the old
  static note, since there's no live terminal control worth building for
  a single line there.
- Curated `"hint"` text for all 20 Python `TRAINING_EXERCISES` entries,
  which previously had none — each nudges toward the exercise's actual
  technique or gotcha (e.g. the two-pointer trick, which DP recurrence
  to use, why a greedy approach fails) instead of falling back to
  `hints.diagnose()`'s generic, exercise-blind guess.
- `LICENSE` (MIT) and `[project]` metadata in `pyproject.toml` (name,
  version, description, license, author, dependencies) — the repo had
  neither, which for a public GitHub repo defaults to "all rights
  reserved" regardless of visibility. README gets a license badge and a
  short License section to match.
- A one-line legend (`e=easy · m=medium · h=hard · w=weak · a=all`)
  under the training-pool table in both testers — the filter keys were
  only ever shown bare in the prompt ("e/m/h/w to filter") with no
  explanation of what they stood for.
- `--train weak` (both testers, plus a 'w' key next to e/m/h in the
  interactive training picker) — drills the training exercises you've
  actually gotten wrong at least once, worst-first (an active fail streak
  ranks above a merely-imperfect lifetime pass rate). New `stats.
  weakest_exercises()`: excludes both an exercise you've never touched
  and one with a spotless record — the queue is exactly "things worth
  reviewing," nothing more, nothing less.
- `--strict` (both testers) — shorthand for every `--strict-*` flag at
  once, i.e. the harshest grading each tester can do. On the C side this
  also turns on `--valgrind` itself (`--strict-valgrind` alone has
  nothing to check otherwise).
- `--diff` flag (both testers) — on a failing test, shows the full
  expected/got values instead of the usual 70-character clip, plus a
  pointer at the first character where they diverge (a caret line in
  the plain-text UI, a reverse-video highlight on the diverging tail in
  the rich UI). Useful once a value is long enough that eyeballing two
  side-by-side reprs stops working. New pure helper: `ui.first_diff_index()`.
- `--diff` now also shows the student's own submitted function next to a
  failing test, syntax-highlighted (a `rich.syntax.Syntax` panel, or a
  dimmed plain-text block with a `── your f() ──`-style header when rich
  isn't available) — so you can see your code and the mismatch without
  alt-tabbing to your editor. Shown once per report, not once per
  failure, and — unlike `hints.py`'s stuck-student nudges — never
  suppressed during `--exam`: it's just the student's own code, already
  open in their editor, not a crutch. New `extract_function_source()` in
  both `src/grader.py` (ast-based) and `c_exam/grader.py` (best-effort
  brace-matching over the comment/string-stripped source, reusing
  `_strip_comments_and_strings()`); both return `None` on any failure
  (syntax error, function not found, unbalanced braces) rather than
  raising, since this is a purely cosmetic display.
- `--diff` now diffs a `list`/`tuple` `Failure` element-by-element instead
  of character-by-character once it has more than one element — "index 2:
  expected 3, got 4" is far more useful than "character 47 differs" once
  a value is a 20-item list. Same idea for a multi-line value (most often
  a C `CFailure`'s multi-line stdout): a `difflib`-based line diff instead
  of the flat char pointer. Both render as a small `-`/`+` block in place
  of the usual single-line pointer, in both the rich and plain UIs; a
  short scalar (a plain string, int, float, bool, or anything single-line)
  still gets the existing char-pointer treatment, unchanged. New pure
  helpers in `src/ui.py`: `structural_diff()`, `line_diff()`.
- `find_forbidden_calls()` in `src/grader.py` — an AST-based check, the
  Python-side counterpart to `c_exam/grader.py`'s existing `find_forbidden()`.
  Lets an exercise declare a `"forbidden"` tuple of names; grading fails
  immediately (no opt-in flag, unlike C's `--strict-forbidden`) if the
  submission calls any of them, since a forbidden call here means the
  student's solution outsources the one thing the exercise is testing.
- `py_cryptic_sorter` now sets `"forbidden": ("sorted", "sort")` — using
  Python's built-in sort defeats the point of the exercise (implement a
  stable multi-key ordering yourself). Its hint was rewritten to match:
  it now points at a hand-rolled insertion sort instead of `sorted(key=...)`.
- **Curated hints for the remaining 38 exam exercises.** Only 6 of the 44
  entries in the Python exam bank had a hand-written `"hint"`; a student
  stuck on any of the other 38 fell straight through to the generic,
  pattern-matched `hints.diagnose()` fallback, which has no idea what the
  exercise is actually about and is often unhelpful. Every exercise now
  carries a short, exercise-specific nudge grounded in its own spec and
  reference implementation (e.g. the empty-list/modulo-by-zero trap in
  `py_twist_sequence`, the `set()`-collapses-duplicates trap in
  `py_anagram`, the even-length-center gap in
  `py_longest_palindromic_substring`) — pointing at what to check, never
  handing over the solution.
- Curated `"hint"` entries for all 9 `c_exam/training_bank.py` exercises
  (`array_sum`, `find_max`, `is_palindrome_num`, `count_pairs_sum`,
  `kadane_max_sum`, `count_unique`, `lis_length`, `count_inversions`,
  `max_gap`) — previously none of them had one, so a stuck student only
  ever got `hints.diagnose()`'s generic pattern-matched guess. Each hint
  targets the actual technique or edge case for that exercise (e.g.
  Kadane's classic all-negative-array bug, the strictly-increasing
  comparison in `lis_length`'s DP, sorting a copy in `max_gap`).
  `lis_length` and `max_gap` (the two that `malloc`/`free`) get a
  crash/leak/default split like `ft_split`'s; the rest are plain strings.
- Curated `"hint"` entries for the 44 C exam exercises (`c_exam/bank.py`)
  that had none — every one of the 59 exercises now nudges a stuck student
  with something specific to what it actually does, instead of falling all
  the way through to `hints.diagnose()`'s generic, pattern-matched guess.
  41 are plain strings; 2 (`rev_wstr`, `rostring`) use a `"crash"`/`"leak"`/
  `"default"` dict split, since both extract words into per-word `malloc`'d
  buffers where a sizing bug and a missing `free` are genuinely different
  mistakes worth nudging differently.

### Fixed (earlier in this release)
- **`py_bracket_validator`** carried `"level": 1` while living in the
  `exam_bank.py` level-6 section — level 1's standard pool had 3 exercises
  instead of 2, and level 6's had only 1 (`whisper_cipher`), so a level-6
  exam run never actually randomized. Corrected to `"level": 6`.
- **`ft_split` / `pgcd` / `fprime`** (`c_exam/bank.py`) each had a
  `"forbidden"` list that contradicted their own subject's
  `Allowed functions` line *and* their own `oracle_c` — e.g. `ft_split`
  forbade `malloc` while its subject said `Allowed: malloc` and its
  reference solution called `malloc` three times. Every legitimate
  solution to these three exercises was getting a bogus forbidden-call
  warning. Removed the incorrect `"forbidden"` entries.
- **`hints.classify()` never recognized a Python per-case timeout**
  (`src/hints.py`). It checked `f.got == "[TIMEOUT]"` — the exact marker
  `c_exam/grader.py`'s program-kind path uses — but the Python sandbox's
  own per-case timeout marker is `"[TIMEOUT > Ns]"` (the timeout value is
  embedded in the string). Since that never matched, a Python student
  stuck on an infinite loop on just one input (the single most common
  real timeout shape) never got the "looks like an infinite loop" hint,
  even after `STUCK_THRESHOLD` consecutive fails — silently fell through
  to no hint at all. Changed to `str(f.got).startswith("[TIMEOUT")`,
  which matches both markers. Verified live: a solution that infinite-loops
  on one specific input now gets the hint on its 3rd consecutive failing
  grade.
- **Missing `malloc` NULL-checks** in five reference solutions —
  `ft_range`, `ft_rrange`, `ft_split` (`c_exam/bank.py`), `lis_length`,
  `max_gap` (`c_exam/training_bank.py`) all dereferenced the result of
  `malloc()` without checking it first. `ft_split` additionally now frees
  every word it already duplicated (and the pointer array itself) if a
  later `malloc` fails mid-loop — matching what its own "leak" hint has
  been telling students to do all along.
- **28 "program"-kind C exercises used `printf()` while their own subject
  said `Allowed functions: write`** (`add_prime_sum`, `alpha_mirror`,
  `camel_to_snake`, `count_vowels`, `epur_str`, `expand_str`, `first_word`,
  `fizzbuzz`, `hidenp`, `is_palindrome_str`, `last_word`, `longest_word_str`,
  `paramsum`, `print_hex`, `repeat_alpha`, `rev_print`, `rev_wstr`,
  `rostring`, `rot_13`, `rotone`, `rstr_capitalizer`, `search_and_replace`,
  `snake_to_camel`, `str_capitalizer`, `tab_mult`, `ulstr`, `union`,
  `wdmatch`). The grader only diffs stdout so this never affected grading
  correctness, but the reference/"answer key" implementation should model
  the exact constraint it's teaching. Rewrote all 28 to use raw `write(2)`
  calls (plus small self-contained per-exercise integer-to-write helpers
  for the 6 that print numbers), byte-for-byte identical output, verified
  against the bank's own curated + fuzz cases and a clean
  `-Wall -Wextra -Werror` compile.

## 2026-09-02 — PR #1 bug-hunt batch

- Fixed a batch of correctness bugs across the exam flow, hints, and C
  grading; follow-up pass fixed remaining review findings (bank defaults,
  hint accuracy, `--strict-forbidden`).
- README polish (hero section, feature showcase, collapsible tables).

## 2026-08-30 – 2026-08-31

- Added stuck-student hints, shared by both the Python and C testers.
- Added optional `--valgrind` leak checking to the C tester; fixed the
  grading harness's own memory leaks in list/voidlist/str_array exercises
  uncovered while building it.
- Added a GitHub Actions CI pipeline.

---

Earlier history: `git log` — this file starts tracking from the point a
changelog was first requested.
