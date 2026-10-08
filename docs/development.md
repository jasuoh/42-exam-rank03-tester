# 🛠️ Developing ExamShell

Testing the tool itself, the code layout, and how releases are made.

[← back to the README](../README.md)

---

## 📦 Dependencies (uv)

Everything is installed with [uv](https://docs.astral.sh/uv/): `rich`
(colours) and `textual` (the app, Python 3.9+), declared in
`pyproject.toml` and pinned in `uv.lock`. `make install` (and the first
`make`) runs `uv sync`, and fetches uv itself into `~/.local/bin` first if
the machine has none:

```bash
uv sync --extra tui          # what `make install` runs: .venv/ with rich, textual, ruff, flake8, mypy
uv run examshell --doctor    # run anything inside that environment
uv lock --upgrade            # bump the pinned versions (commit uv.lock)
uv tool install "examshell[tui] @ git+https://github.com/jasuoh/42-exam-tester"
                             # examshell / examshell-c on the PATH, no clone
uv add --optional tui <pkg>  # a new optional dependency
```

The developer targets (`make dev` lists them) use `.venv/` once it exists
and a bare `python3` before that. CI installs one leg exactly like a
student (`make install`) and runs the other with no dependencies at all —
the testers still work there, in the plain line-based menu.

The package is `examshell/` (the Python tester and everything shared) plus
`c_exam/` (the C tester); `pyproject.toml` installs them with the
`examshell` and `examshell-c` commands. `src/` is only a `python3 -m src`
shim for old habits and is never installed.

## ✅ Testing this project

Two independent safety nets, run separately because they check different
things:

* **`make check`** validates every exercise *bank* (`exam_bank.py`,
  `exam_bank_r04.py`, `exam_bank_r05.py` and `training_bank.py`): every
  reference solution is run back through the real sandbox and must score
  100 %, every subject must match its function(s), every expected value
  must survive the trip to the sandbox unchanged, every fuzzer must work,
  no level/difficulty group may be empty. Run it after touching any bank
  file; `make check RANK=04` narrows it to one rank plus the training
  bank.
* **`make unit`** validates the *tool's own code* (stdlib `unittest`, no
  extra dependency): comparison logic (`deep_eq`), import detection,
  exercise resolution, `--grade-all`'s bookkeeping, subject parsing, and so
  on. Run it after touching `grader.py`, `ui.py` or `examshell.py`.
  `deep_eq` is defined once in `grader.py` — the exact same source is
  spliced into the sandboxed runner, so unit-testing it here also covers
  what actually grades your code.

`make test` runs both.

**`make mutate`** checks the *banks' tests* themselves (`tools/mutate.py`):
every reference solution is changed in one small place at a time — `<`
becomes `<=`, a constant moves by one, `and` becomes `or` — and graded
against its own exercise's tests like a submission. A change the tests
don't catch is a plausible student bug that would pass; when the bank's
own fuzzer then finds an input where it gives a different answer, it's
reported as a **GAP** with that input — add it (or a simpler one) to the
exercise's `cases`. Run it after adding or changing an exercise
(`make mutate ONLY=py_my_exercise`; `MUT=py` / `MUT=c` for one tester;
`python3 tools/mutate.py --show-unproven` also lists survivors without
such an input). It exits 1 on a gap.

**`make lint`** checks the code itself: every file parses, `ruff check`,
`flake8` (default settings, 79 columns — `make format` runs `ruff format`
at that width) and `mypy --strict` over the package, `tests/` and
`tools/` (config in `pyproject.toml`). CI runs it as its own job with
`LINT_STRICT=1`, which fails when a tool is missing instead of skipping
it. The code stays Python 3.8 compatible: every module starts with
`from __future__ import annotations`, and type aliases evaluated at
runtime use `typing.List`/`Dict`/`Optional`, not `list[...]`/`X | None`.

## 🗂️ Layout

| File | |
|---|---|
| `examshell/__main__.py` | entry point for `python3 -m examshell` |
| `examshell/examshell.py` | the Python tester: its CLI, rank switching, stubs, and the hooks the shared flow needs |
| `examshell/shell_common.py` | the exam / practice / training / readiness / drill flow **both** testers run — an I/O-free engine (`ExamRun`, `grade()`) plus the line-based UI on top of it |
| `examshell/tui/app.py` | the app (Textual): menu, practice, exam, progress, settings |
| `examshell/tui/render.py` | the app's rich renderables — pure functions, unit-tested without Textual |
| `examshell/tui/crashlog.py` | writes `crash.log` on an unexpected error; the next start offers to report it |
| `examshell/tui/clipboard.py` | copy/paste through the system clipboard where OSC 52 isn't enough |
| `examshell/grader.py` | test building, the sandbox, the self-test |
| `examshell/ui.py` | all rendering — `rich` when available, ANSI otherwise |
| `examshell/bank_common.py` | tiny helpers shared by both exercise banks |
| `examshell/exam_bank.py` | the 6-level Rank 03 exam bank ⚠ **contains the answers** |
| `examshell/exam_bank_r04.py` | the 4-level Rank 04 exam bank ⚠ **contains the answers** |
| `examshell/exam_bank_r05.py` | the 3-level Rank 05 exam bank ⚠ **contains the answers** |
| `examshell/ranks.py` | which ranks exist: bank, level count, history tag |
| `examshell/training_bank.py` | the LeetCode-style training bank, shared by every rank ⚠ **contains the answers** |
| `examshell/settings.py` | `~/.examshell/config.json` — the app's settings and the exam picked last, shared by both testers |
| `examshell/stats.py` | `~/.examshell/stats.jsonl` — local grading history, shared by both testers |
| `examshell/session_store.py` | exam save/resume state, shared by both testers |
| `examshell/case_labels.py` | names the edge case of a failing input, shared by both testers |
| `examshell/update_check.py` | the once-a-day "new version available" notice |
| `examshell/version.py` | the version number (`--version`, releases, the update check) |
| `examshell/sync.py` | sync through the student's private git repo |
| `examshell/doctor.py` · `feedback.py` | `--doctor`, `--feedback` |
| `examshell/_types.py` | the shared type protocols (`Tester`, `TesterConfig` …) |
| `examshell/hints.py` | the "stuck 3x in a row" nudge (generic + curated), shared by both testers |
| `tests/` | unit tests for the tool itself |
| `rendu/` | your solutions (git-ignored) |

---

## 🖼️ Screenshots

`docs/img/*.svg` are real Textual screenshots, regenerated with

```bash
.venv/bin/python tools/screenshots.py
```

It runs the app headless against a throwaway `HOME` with a made-up practice
history, so your own `~/.examshell/` is never touched.

## 🚀 Releasing

1. In the PR: bump `examshell/version.py` **and** `pyproject.toml` (a unit
   test keeps them equal), run `uv lock`, and add a `## X.Y.Z — date`
   section at the top of `CHANGELOG.md`.
2. Merge it. `.github/workflows/release.yml` sees the new version on
   `main`, runs the tests, tags `vX.Y.Z` and publishes the GitHub Release
   (notes = that CHANGELOG section, package files attached).

Nothing else to do — no manual tag. If the run failed (e.g. a missing
CHANGELOG section), fix it on `main` and use **Actions → Release → Run
workflow**. A version that's already tagged is skipped.
