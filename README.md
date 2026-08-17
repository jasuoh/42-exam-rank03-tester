# ExamShell — 42 Python Exam Rank 03

A practice tester built in the style of the real `examshell` / moulinette for
the **42 Common Core Python Exam Rank 03**.

Six levels in order, one random exercise per level out of a pool of 40, each
graded against dozens of tests, and you only move up at **100 %** — same
rules as the real thing.

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
make grade-all               # grade everything you've written so far
```

Inside the exam you type `grademe`, exactly like the real one.

## How the exam works

1. **Six levels**, in order 1 → 6.
2. One **random exercise per level**, drawn from that level's pool (levels 1
   and 2 have eight to draw from, levels 3–6 have six).
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

Modes from the main menu: **Start exam** (the full run above), **Practice
mode** (drill any single exercise, no progression), **List all exercises**.

## Exercise pool

40 exercises, one drawn at random per level per run — **all 40 are in play
during a real run of `make exam`**, but they are not all the same kind of
exercise:

* **Standard (14)** — the original pool, based on the publicly documented
  Rank-03 exercises. These are the ones that can plausibly show up on the
  *real* 42 exam. Marked in **bold** below.
* **Extra (26)** — added later for broader practice: more variety, a wider
  difficulty range, a couple of deliberately easy warm-ups in levels 1–2.
  Good drilling, but not verified against any real exam sheet — don't treat
  them as "this is what 42 asks."

| Level | Standard | Extra |
|------:|----------|-------|
| 1 | **`py_cryptic_sorter`** · **`py_inter`** | `py_vowel_counter` · `py_capitalizer` · `py_leet_speak` · `py_char_frequency` · `py_string_reverser` · `py_char_counter` |
| 2 | **`py_echo_validator`** · **`py_mirror_matrix`** | `py_digit_extractor` · `py_case_counter` · `py_run_length_encoder` · `py_second_largest` · `py_even_odd_counter` · `py_sum_of_squares` |
| 3 | **`py_number_base_converter`** · **`py_pattern_tracker`** · **`py_hidenp`** | `py_word_reverser` · `py_run_length_decoder` · `py_binary_gap` |
| 4 | **`py_anagram`** · **`py_shadow_merge`** · **`py_string_permutation_checker`** | `py_unique_elements` · `py_pangram_checker` · `py_max_subarray_sum` |
| 5 | **`py_string_sculptor`** · **`py_twist_sequence`** | `py_matrix_transposer` · `py_longest_word` · `py_zigzag_flatten` · `py_pascals_triangle_row` |
| 6 | **`py_bracket_validator`** · **`py_whisper_cipher`** | `py_matrix_rotator` · `py_prime_finder` · `py_longest_palindromic_substring` · `py_two_sum_indices` |

Within the extra pool, `py_string_reverser` and `py_char_counter` (level 1),
plus `py_even_odd_counter` and `py_sum_of_squares` (level 2), are the
deliberately easy ones — a good place to start if you're new to the exam
format.

There is currently no flag to restrict a run to only the standard 14 —
`make exam` always draws from the full pool for a given level.

`python3 -m src --list` prints this pool with the exact function name for
each exercise; the full signature and subject show up once you draw or
practice it.

## How grading works

Most exercises run against **~30–60 tests**: every curated edge case in the
bank (empty inputs, case handling, boundaries, punctuation, negative
numbers, ties…) plus randomised fuzz tests — fewer for the handful of
exercises with a naturally small input domain (e.g. a Pascal's-triangle row
index only takes so many interesting values). Expected values come from a
reference implementation, never from a hand-written answer key, so they
cannot drift out of sync with the subject.

Your file is **never imported into the tester**. It runs in a subprocess that:

* has a clean `sys.path` — it cannot import the bank and read the answers,
* gets `/dev/null` on stdin, so a stray `input()` fails instead of hanging,
* arms an alarm around **every single call**, so an infinite loop costs you
  three seconds and not your session,
* gives up early after repeated timeouts instead of grinding through 40
  cases at the full timeout each,
* reports through a result file, so anything your code prints cannot
  corrupt the verdict.

Comparison is **type-strict and recursive**: `True` is not `1`, and a tuple
is not a list — the same pickiness the moulinette has.

Beyond pass/fail, the grader tells you when:

* your function **printed** the answer instead of returning it (the single
  most common way to fail an exam you had actually solved),
* your function **mutated its input** when the subject asked for a new
  value,
* your **signature is wrong** — one clear message instead of forty
  identical `TypeError`s,
* you used an **import**, which the real exam forbids (a warning by
  default, a failure with `--strict-imports`).

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
| `make grade-all` | grade every solution in `rendu/` at once, one overview |
| `make unit` | fast unit tests for the tool's own logic |
| `make check` | self-test the exercise bank's content |
| `make test` | `unit` + `check` |
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

## CLI

The Makefile is a thin wrapper; everything is reachable directly:

```
python3 -m src                       # interactive menu
python3 -m src --exam --seed 42      # reproducible exam
python3 -m src --practice py_inter   # drill one exercise
python3 -m src --grade inter         # grade once (unique suffixes work)
python3 -m src --grade-all           # grade every solution in rendu/
python3 -m src --check               # validate the exercise bank
python3 -m src --list
python3 -m src --help
```

Run it from the repository root — `src/` is a package, not a standalone
script, so `python3 src/examshell.py` will not work.

Useful flags: `--rendu DIR`, `--timeout SEC`, `--fuzz N`, `--show-fails N`,
`--strict-imports`, `--no-color`, `--no-rich`.

## Testing this project

Two independent safety nets, run separately because they check different
things:

* **`make check`** validates the exercise *bank*: every reference solution
  is run back through the real sandbox and must score 100 %, every subject
  must match its function, every fuzzer must work, no level may be empty.
  Run it after touching `exam_bank.py`.
* **`make unit`** validates the *tool's own code* (stdlib `unittest`, no
  extra dependency): comparison logic (`deep_eq`), import detection,
  exercise resolution, `--grade-all`'s bookkeeping, subject parsing, and so
  on. Run it after touching `grader.py`, `ui.py` or `examshell.py`.
  `deep_eq` is defined once in `grader.py` — the exact same source is
  spliced into the sandboxed runner, so unit-testing it here also covers
  what actually grades your code.

`make test` runs both.

## Layout

| File | |
|---|---|
| `src/__main__.py` | entry point for `python3 -m src` |
| `src/examshell.py` | CLI, menu, exam and practice flow |
| `src/grader.py` | test building, the sandbox, the self-test |
| `src/ui.py` | all rendering — `rich` when available, ANSI otherwise |
| `src/exam_bank.py` | the exercise bank ⚠ **contains the answers** |
| `tests/` | unit tests for the tool itself |
| `rendu/` | your solutions (git-ignored) |

---

> The exact exercise set depends on your campus and changes over time. The
> **standard** pool above is based on the publicly documented Rank-03 Python
> exercises; the **extra** pool is this project's own addition for more
> practice. Don't rote-learn the solutions — understand the logic.
