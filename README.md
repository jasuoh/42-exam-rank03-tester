# ExamShell — 42 Python Exam Rank 03

A practice tester in the style of the real `examshell` / moulinette for the
**42 Python Exam Rank 03** (Common Core).

## Files
- `examshell.py`  – the tester (menu, exam flow, sandbox grader, UI)
- `exam_bank.py`  – the exercise bank (subjects, reference oracles, tests)

## Run

```bash
python3 examshell.py
```

Optional prettier UI (panels, tables, syntax highlighting):

```bash
pip install rich
```

If `rich` is not installed the tester automatically falls back to plain
coloured output, so it still runs anywhere (e.g. on exam machines).

A `rendu/` folder is created automatically. Put your solution there as
`<exercise_name>.py`, defining the required function.

## Exam flow (like the real exam)

- **6 levels**, in order 1 → 6.
- One **random exercise per level**, drawn from that level's pool.
- Test with `grademe`. **You advance only at 100%.**
- If a solution fails you can fix and `grademe` again, or draw a fresh
  exercise for the level with `new`.

### Commands during the exam
`grademe` · `subject` · `status` · `new` · `quit`

## Modes (main menu)
1. **Start exam** – full 6-level run with login, timer, score, progress dots.
2. **Practice mode** – drill any single exercise (no progression).
3. **List all exercises**.

## Exercise pool (14 exercises, 1 per level in the exam)

| Level | Exercises |
|------:|-----------|
| 1 | `py_cryptic_sorter`, `py_inter` |
| 2 | `py_echo_validator`, `py_mirror_matrix` |
| 3 | `py_number_base_converter`, `py_pattern_tracker`, `py_hidenp` |
| 4 | `py_anagram`, `py_shadow_merge`, `py_string_permutation_checker` |
| 5 | `py_string_sculptor`, `py_twist_sequence` |
| 6 | `py_bracket_validator`, `py_whisper_cipher` |

## Testing

Each exercise is graded against **~38–44 tests**: many curated edge cases
(empty inputs, case handling, boundaries, special characters, …) **plus**
randomized fuzz tests. Expected outputs are computed from verified reference
solutions, so they are guaranteed correct.

Grading runs in a **sandbox (subprocess)** with a per-test timeout, so syntax
errors, runtime errors and infinite loops are handled cleanly.

## Options (top of `examshell.py`)
- `FUZZ_PER_EX` – number of random extra tests per exercise (default 30).
- `PER_TEST_TIMEOUT` – seconds per test case (default 3).
- `STRICT_IMPORTS` – set `True` so any `import` in the rendu fails grading
  (like the real moulinette). Default: warning only.

---

> Note: the exact exercise set can depend on your campus and may change.
> This pool is based on the publicly documented Rank-03 Python exercises at
> the time of writing. Don't rote-learn the solutions — understand the logic.