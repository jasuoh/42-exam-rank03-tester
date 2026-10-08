# AGENTS.md

How to work on ExamShell — for AI agents and people alike. Read this before
changing anything.

## What this is

Practice testers for the 42 Common Core exams: **C Exam Rank 02**
(`c_exam/`) and **Python Exam Ranks 03 / 04 / 05** (`examshell/`). Students
run `make`, which opens a Textual app next to their editor: an exam that
behaves like the real one, practice with full feedback, progress, settings.

## Product rules (decided with the maintainer)

- **The exam simulates the real exam.** Levels in order, 100 % to advance,
  a failed level **keeps its exercise**, no redraw (only `--relaxed`),
  `grademe` shows **SUCCESS** or **FAILURE + a trace of the first failing
  test** — no hints, no other failures. Don't add comfort to the exam.
- **Comfort belongs in Practice** (hints, all failures with `d`, extra
  exercises, gaps).
- **Keep it small.** Five menu entries (Exam · Practice · Progress ·
  Switch exam · Quit), keys for the rest (`o` settings, `s` sync, `f`
  feedback). Settings live in the app, not in the Makefile. Before adding
  a feature, menu entry, flag or make target, ask the maintainer.
- **The Makefile is for installing and starting:** `make`, `install`,
  `update`, `doctor`, `dev` (+ the developer targets it lists). Install is
  **uv only** — no manual venv/pip path.
- The app uses the terminal's colours (Textual `ansi-dark`), one quiet
  border style, no emoji.

## Layout

| Path | |
|---|---|
| `examshell/shell_common.py` | the shared engine (`ExamRun`, `grade()`, `finish_exam()`) + the line-based UI |
| `examshell/tui/app.py` | the Textual app — screens, keys, settings |
| `examshell/tui/render.py` | rich renderables for the app (pure, unit-tested) |
| `examshell/examshell.py` · `c_exam/examshell.py` | each tester's CLI and hooks |
| `examshell/exam_bank*.py` · `c_exam/bank.py` · `*training_bank.py` | exercises **with reference solutions** |
| `examshell/grader.py` · `c_exam/grader.py` | sandboxed grading (Python subprocess · C compile + run) |
| `examshell/settings.py` · `stats.py` · `session_store.py` · `sync.py` | `~/.examshell/` data, shared by both testers |
| `tests/` | `unittest` suite · `tools/` screenshots, mutation tests |
| `PLAN.md` | roadmap and the decisions behind it (German) |

## Commands

```bash
make install        # uv sync --extra tui (fetches uv if missing)
make unit           # unit tests (~500, ~25 s)
make test           # unit + every Python bank checked against its tests
make c-test         # C unit tests + C banks (real compiles)
make lint           # ruff, flake8 (79 cols), mypy --strict — must pass
make format         # ruff format
.venv/bin/python tools/screenshots.py   # regenerate docs/img/*.svg
```

If `make unit` suddenly skips ~34 tests, `.venv` is missing — run
`make install`.

## Code conventions

- Python **3.8 compatible**: `from __future__ import annotations` in every
  module; runtime type aliases use `typing.List` / `Optional`, not
  `list[...]` / `X | None`. The app (Textual) needs 3.9+.
- 79 columns, `mypy --strict` clean, typed tests too.
- Match the surrounding code: comments explain *why*, docstrings are
  short and concrete. No new dependencies without asking.
- User-facing text is English; `PLAN.md` and `docs/sync.de.md` are German.

## Tests must never touch the real `~/.examshell`

`tests/__init__.py` points `EXAMSHELL_HOME` at a temp dir, but modules
compute their paths at import — **patch** them in tests that write data:
`stats.DATA_DIR` / `STATS_PATH`, `session_store.DATA_DIR`,
`settings.DATA_DIR` / `CONFIG_PATH`, `update_check.DATA_DIR` /
`CACHE_PATH`. TUI tests also stub `examshell.tui.clipboard._tools` so they
never overwrite the real clipboard. A leaked fake "v99.0.0" in the real
update cache is how we learned this.

## Manual testing

Unit tests don't replace using the app. To test like a student without
touching anyone's data:

- `EXAMSHELL_HOME=$(mktemp -d)` for the data folder.
- `make RENDU=/tmp/x/rendu` for Python solutions. The **C tester always
  uses `c_rendu/` in the current folder** — run it from a scratch copy
  (`git worktree add`) or clean up after.
- Drive the real `make` in a pseudo-terminal (Python `pty`) and send keys,
  or use Textual's `App.run_test()` pilot (see `tests/test_tui_app.py`).
- Never run `make install`/`uv` against someone's real `$HOME` just to
  test; use a temp `HOME` and a worktree.

## Git workflow

- `main` is **stable** — what students get; a version bump merged into
  `main` publishes a release (`.github/workflows/release.yml`).
- `beta` collects work for the next release. Branch from `beta`, open the
  PR **into `beta`**. Never merge yourself; the maintainer reviews and
  merges.
- One topic per commit, a message that says what and why. Add a
  `CHANGELOG.md` entry under the upcoming version.
- Don't push or open a PR unless asked.
