# ExamShell — 42 Python Exam Rank 03

A practice tester built in the style of the real `examshell` / moulinette for
the **42 Common Core Python Exam Rank 03**.

Six levels in order, one random exercise per level, dozens of tests per
exercise, and you only move up at **100 %** — same rules as the real thing.

```bash
make install     # optional: venv + rich for the pretty UI
make run         # interactive menu
```

No dependencies are required. Without `rich` the tester falls back to plain
ANSI output, so it runs on any exam machine with nothing but Python 3.8+.

---

## Quick start

```bash
make exam                    # jump straight into the 6-level exam
make stub EX=py_inter        # create rendu/py_inter.py with the signature
$EDITOR rendu/py_inter.py    # solve it
make grade EX=py_inter       # grade it (exit code 0 = OK, 1 = KO)
```

Inside the exam you type `grademe`, exactly like the real one.

## Make targets

| Target | What it does |
|---|---|
| `make` | show the help |
| `make run` | interactive menu (exam · practice · list) |
| `make exam` | start the exam directly |
| `make practice` | drill exercises — `make practice EX=py_inter` for one |
| `make list` | print the exercise pool |
| `make stub EX=…` | create an empty solution file (never overwrites) |
| `make grade EX=…` | grade one solution, no menu |
| `make check` | self-test the exercise bank (aliased as `make test`) |
| `make lint` | parse-check the sources, plus ruff/pyflakes if installed |
| `make status` | show which solutions you have written so far |
| `make install` | create `venv/` and install `rich` |
| `make clean` | remove caches and stray artefacts |
| `make fclean` | `clean` + remove `venv/` |
| `make re` | `fclean` + `install` + `check` |
| `make rendu-clean` | delete your solutions (asks for confirmation first) |

Options: `EX=<exercise>`, `SEED=<n>`, `RENDU=<dir>`,
`FLAGS='--strict-imports'`, `PYTHON=python3.11`.

```bash
make exam SEED=42                 # reproducible exam, same draw every time
make exam FLAGS=--strict-imports  # any import fails grading, like the moulinette
```

## How the exam works

1. **Six levels**, in order 1 → 6.
2. One **random exercise per level**, drawn from that level's pool.
3. Write your solution in `rendu/<exercise_name>.py` and define the required
   function. `rendu/` is created for you.
4. Type `grademe`. **You only advance at 100 %.**

Commands during the exam:

| Command | |
|---|---|
| `grademe` | test your solution |
| `subject` | show the assignment again |
| `status` | show your progress |
| `new` | draw a different exercise for this level |
| `stub` | create the solution file for you |
| `quit` | abort (you still get a summary) |

## Exercise pool

14 exercises, one per level per run:

| Level | Exercises |
|------:|-----------|
| 1 | `py_cryptic_sorter`, `py_inter` |
| 2 | `py_echo_validator`, `py_mirror_matrix` |
| 3 | `py_number_base_converter`, `py_pattern_tracker`, `py_hidenp` |
| 4 | `py_anagram`, `py_shadow_merge`, `py_string_permutation_checker` |
| 5 | `py_string_sculptor`, `py_twist_sequence` |
| 6 | `py_bracket_validator`, `py_whisper_cipher` |

## How grading works

Each exercise runs against **~40–60 tests**: every curated edge case in the
bank (empty inputs, case handling, boundaries, punctuation, negative numbers…)
plus randomised fuzz tests. Expected values come from a reference
implementation, never from a hand-written answer key, so they cannot drift out
of sync with the subject.

Your file is **never imported into the tester**. It runs in a subprocess that:

* has a clean `sys.path` — it cannot import the bank and read the answers,
* gets `/dev/null` on stdin, so a stray `input()` fails instead of hanging,
* arms an alarm around **every single call**, so an infinite loop costs you
  three seconds and not your session,
* gives up early after repeated timeouts instead of grinding through 40 cases,
* reports through a result file, so anything your code prints cannot corrupt
  the verdict.

Comparison is **type-strict and recursive**: `True` is not `1`, and a tuple is
not a list — the same pickiness the moulinette has.

Beyond pass/fail, the grader tells you when:

* your function **printed** the answer instead of returning it (the single most
  common way to fail an exam you had actually solved),
* your function **mutated its input** when the subject asked for a new value,
* your **signature is wrong** — one clear message instead of forty identical
  `TypeError`s,
* you used an **import**, which the real exam forbids (a warning by default,
  a failure with `--strict-imports`).

## CLI

The Makefile is a thin wrapper; everything is reachable directly:

```
python3 -m src                       # interactive menu
python3 -m src --exam --seed 42      # reproducible exam
python3 -m src --practice py_inter   # drill one exercise
python3 -m src --grade inter         # grade once (suffixes work)
python3 -m src --check               # validate the exercise bank
python3 -m src --list
python3 -m src --help
```

Run it from the repository root — `src/` is a package, not a standalone
script, so `python3 src/examshell.py` will not work.

Useful flags: `--rendu DIR`, `--timeout SEC`, `--fuzz N`, `--show-fails N`,
`--strict-imports`, `--no-color`, `--no-rich`.

## Layout

| File | |
|---|---|
| `src/__main__.py` | entry point for `python3 -m src` |
| `src/examshell.py` | CLI, menu, exam and practice flow |
| `src/grader.py` | test building, the sandbox, the self-test |
| `src/ui.py` | all rendering — `rich` when available, ANSI otherwise |
| `src/exam_bank.py` | the exercise bank ⚠ **contains the answers** |
| `rendu/` | your solutions (git-ignored) |

`make check` runs every reference solution back through the real sandbox and
verifies that each subject matches its function, that every fuzzer works, and
that no level is empty. Run it after touching `exam_bank.py`.

---

> The exact exercise set depends on your campus and changes over time. This
> pool is based on the publicly documented Rank-03 Python exercises. Don't
> rote-learn the solutions — understand the logic.
