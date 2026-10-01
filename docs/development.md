# 🛠️ Developing ExamShell

Testing the tool itself, the code layout, and how releases are made.

[← back to the README](../README.md)

---

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

## 🗂️ Layout

| File | |
|---|---|
| `examshell/__main__.py` | entry point for `python3 -m examshell` |
| `examshell/examshell.py` | the Python tester: its CLI, rank switching, stubs, and the hooks the shared flow needs |
| `examshell/shell_common.py` | the exam / practice / training / readiness / drill flow **both** testers run — an I/O-free engine (`ExamRun`, `grade()`) plus the line-based UI on top of it |
| `examshell/grader.py` | test building, the sandbox, the self-test |
| `examshell/ui.py` | all rendering — `rich` when available, ANSI otherwise |
| `examshell/bank_common.py` | tiny helpers shared by both exercise banks |
| `examshell/exam_bank.py` | the 6-level Rank 03 exam bank ⚠ **contains the answers** |
| `examshell/exam_bank_r04.py` | the 4-level Rank 04 exam bank ⚠ **contains the answers** |
| `examshell/exam_bank_r05.py` | the 3-level Rank 05 exam bank ⚠ **contains the answers** |
| `examshell/ranks.py` | which ranks exist: bank, level count, history tag |
| `examshell/training_bank.py` | the LeetCode-style training bank, shared by every rank ⚠ **contains the answers** |
| `examshell/settings.py` | `~/.examshell/config.json` — theme/timeout/fuzz/show-fails, shared by both testers |
| `examshell/stats.py` | `~/.examshell/stats.jsonl` — local grading history, shared by both testers |
| `examshell/session_store.py` | exam save/resume state, shared by both testers |
| `examshell/report_export.py` | Markdown session reports in `~/.examshell/reports/`, shared by both testers |
| `examshell/case_labels.py` | names the edge case of a failing input, shared by both testers |
| `examshell/update_check.py` | the once-a-day "new version available" notice |
| `examshell/version.py` | the version number (`--version`, releases, the update check) |
| `examshell/hints.py` | the "stuck 3x in a row" nudge (generic + curated), shared by both testers |
| `tests/` | unit tests for the tool itself |
| `rendu/` | your solutions (git-ignored) |

---

> 💬 The exact exercise set depends on your campus and changes over time. The
> **standard** pools above are based on the publicly documented Rank 03, 04
> and 05 Python exercises; Rank 03's **extra** pool is this project's own
> addition for more practice. Function names and signatures in particular
> vary between campuses — read the real subject on the day. Don't
> rote-learn the solutions — understand the logic.

---

## 🖼️ Screenshots

`docs/img/*.svg` are real Textual screenshots, regenerated with

```bash
venv/bin/python tools/screenshots.py
```

It runs the app headless against a throwaway `HOME` with a made-up practice
history, so your own `~/.examshell/` is never touched.
