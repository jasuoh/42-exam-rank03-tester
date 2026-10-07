# 🐍 Python tester · Exam Ranks 03 / 04 / 05

Everything about the Python tester (`python3 -m examshell`, `make …`).

[← back to the README](../README.md)

---

Levels in order, one random exercise per level, each graded against dozens
of tests, and you only move up at **100 %** — same rules as the real thing.

**Three exam pools, one tool.** Rank 03 is the default; `RANK=04` /
`RANK=05` (or `--rank 04`) switches to the Rank 04 or Rank 05 pool, and
menu entry **5** switches ranks without leaving the tool.

| Rank | Levels | Exercises | Tag its history lives under |
|---|:---:|:---:|---|
| **03** *(default)* | 6 | 44 (14 standard + 30 extra) | `py` |
| **04** | 4 | 7 (all standard) | `py04` |
| **05** | 3 | 7 (all standard) | `py05` |

Each rank keeps its **own** stats, saved exam and session reports, so a
half-finished Rank 04 run can never be resumed into a Rank 03 one, and a
Rank 03 best time is never beaten by a shorter Rank 05 one. The training
pool is shared by all three — it is never part of any exam draw anyway.

```bash
make exam                    # jump straight into the 6-level Rank 03 exam
make exam RANK=05            # …or the 3-level Rank 05 one
make ranks                   # what each rank contains, and which is active
make stub EX=py_inter        # create rendu/py_inter.py with the signature
$EDITOR rendu/py_inter.py    # solve it
make grade EX=py_inter       # grade it (exit code 0 = OK, 1 = KO)
make grade-all               # grade everything you've written so far
```

Inside the exam you type `grademe`, exactly like the real one.

## 🎯 How the exam works

1. **Every level, in order** 1 → N — six of them on Rank 03, four on Rank
   04, three on Rank 05.
2. One **random exercise per level**, drawn from that level's pool (on Rank
   03, levels 1 and 2 have eight to draw from and levels 3–6 have six; the
   Rank 04/05 pools are much smaller — see below).
3. Write your solution in `rendu/<exercise_name>.py` and define the required
   function. `rendu/` is created for you.
4. Type `grademe`. **You only advance at 100 %.**

Commands during the exam:

| Command | |
|---|---|
| `grademe` | test your solution |
| `subject` | show the assignment again |
| `status` | show your progress |
| `new` | draw a different exercise for this level (**only with `--relaxed`**) |
| `stub` | create the solution file for you — in the exam just the bare signature, like the real one (`--relaxed`: with a quick self-check) |
| `quit` | abort (you still get a summary) |

**The exam is as strict as the real one by default.** Practice and training
only *warn* about an `import` (or, in C, a compiler warning or a forbidden
call) so mistakes stay cheap while you learn — but the exam fails you on
them, exactly like the real moulinette, and there is no `new` to redraw an
exercise you don't like. Passing here therefore means something. Two flags
change that:

```bash
make exam FLAGS=--relaxed            # the old lenient exam: warnings only, `new` allowed
make exam FLAGS="--time-limit 180"   # end the exam after 180 minutes, countdown in the prompt
```

With `--seed N` the whole exam is reproducible: the same exercises are
drawn no matter how many times you type `grademe` along the way.

Modes from the main menu: **Start exam** (the full run above — draws only
from the Standard 14, one per level), **Practice mode** (drill *any* of
the 44, Standard or Extra, no progression), **List all exercises**,
**Training mode** (LeetCode-style exercises by difficulty — see below,
never part of the exam), **Exam readiness** and **Daily drill** (see
[Readiness & drill](features.md#-exam-readiness--daily-drill)).

Every generated stub (`stub` / `make stub`) also embeds a small
**self-check block**: a handful of the exercise's own curated cases with
their expected output, computed from the reference solution, so
`python3 rendu/<exercise>.py` gives instant `ok` / `FAIL` feedback while
you're still writing the function — no need to go through the full sandboxed
`grademe` for a quick sanity check. It's inert during real grading (the
block only runs when the file is executed directly, never when it's
imported), and it only covers a few examples — `grademe` still checks dozens
of edge cases and fuzz inputs these don't.

## 📚 Exercise pool

44 exercises, but they are not all the same kind of exercise, and —
important — **`make exam` only ever draws from the Standard 14**:

* **Standard (14)** — the original pool, based on the publicly documented
  Rank-03 exercises. These are the ones that can plausibly show up on the
  *real* 42 exam, and the only ones a real `make exam` run can draw.
  Marked in **bold** below and with ★ in `--list`.
* **Extra (30)** — added for broader practice: more variety, a wider
  difficulty range, a couple of deliberately easy warm-ups in levels 1–2.
  Good drilling, but not verified against any real exam sheet, and
  **never drawn into a real exam run** — reach them through **Practice
  mode** instead (marked with ○ in `--list`).

<details>
<summary><b>📖 Show the full Python exercise pool (44 exercises)</b></summary>
<br>

| Level | Standard (drawn by `make exam`) | Extra (practice mode only) |
|------:|----------|-------|
| 1 | **`py_cryptic_sorter`** · **`py_inter`** · **`py_bracket_validator`** | `py_vowel_counter` · `py_capitalizer` · `py_leet_speak` · `py_char_frequency` · `py_string_reverser` · `py_char_counter` |
| 2 | **`py_echo_validator`** · **`py_mirror_matrix`** | `py_digit_extractor` · `py_case_counter` · `py_run_length_encoder` · `py_second_largest` · `py_even_odd_counter` · `py_sum_of_squares` · `py_longest_common_prefix` · `py_camel_to_snake_converter` |
| 3 | **`py_number_base_converter`** · **`py_pattern_tracker`** · **`py_hidenp`** | `py_word_reverser` · `py_run_length_decoder` · `py_binary_gap` · `py_string_rotation_checker` |
| 4 | **`py_anagram`** · **`py_shadow_merge`** · **`py_string_permutation_checker`** | `py_unique_elements` · `py_pangram_checker` · `py_max_subarray_sum` · `py_roman_numeral` |
| 5 | **`py_string_sculptor`** · **`py_twist_sequence`** | `py_matrix_transposer` · `py_longest_word` · `py_zigzag_flatten` · `py_pascals_triangle_row` |
| 6 | **`py_whisper_cipher`** | `py_matrix_rotator` · `py_prime_finder` · `py_longest_palindromic_substring` · `py_two_sum_indices` |

Within the extra pool, `py_string_reverser` and `py_char_counter` (level 1),
plus `py_even_odd_counter` and `py_sum_of_squares` (level 2), are the
deliberately easy ones — a good place to start if you're new to the exam
format.

</details>

`python3 -m examshell --list` prints this pool with the exact function name for
each exercise, ★/○ marking which pool each belongs to; the full signature
and subject show up once you draw or practice it.

## 🪜 Rank 04 & 05 pools

The published Rank 04 and Rank 05 Python pools are much smaller than Rank
03's, and **every exercise in them is a documented subject** — so there is
no Standard/Extra split here: all 14 are ★, and `make exam RANK=04` can
draw any of them. The flip side of a small pool is that some levels hold a
single exercise, so `new` (with `--relaxed`) simply re-draws it — that is
the real pool, not a bug.

<details>
<summary><b>📖 Show the Rank 04 pool (7 exercises, 4 levels)</b></summary>
<br>

| Level | Exercise | Function | What it is |
|------:|---|---|---|
| 1 | `py_array_rotation_detector` | `array_rotation_detector()` | is one list a cyclic rotation of another |
| 1 | `py_constellation_mapper` | `constellation_mapper()` | plot `(row, col)` stars onto a `'.'`/`'*'` grid |
| 1 | `py_list_intersection_finder` | `list_intersection_finder()` | elements common to every list, unique + sorted |
| 2 | `py_merge_sorted_lists` | `merge_sorted_lists()` | k-way merge — `sorted()`/`.sort()` are **forbidden** |
| 3 | `py_palindrome_partitioner` | `palindrome_partitioner()` | minimum cuts so every piece is a palindrome |
| 3 | `py_package_dependency_resolver` | `package_dependency_resolver()` | topological sort, `[]` on a cycle |
| 4 | `py_sliding_window_maximum` | `sliding_window_maximum()` | maximum of every window of size k |

</details>

<details>
<summary><b>📖 Show the Rank 05 pool (7 exercises, 3 levels)</b></summary>
<br>

| Level | Exercise | Function | What it is |
|------:|---|---|---|
| 1 | `py_compress_decompress` | `compress()` + `decompress()` | run-length coding **both ways** — two functions, one verdict |
| 1 | `py_spiral_generator` | `generate_spiral()` | build an n×n matrix filled 1..n² in a clockwise spiral |
| 2 | `py_graph_cycle_detector` | `graph_cycle_detector()` | does a directed graph contain a cycle |
| 2 | `py_schedule_meetings` | `schedule_meetings()` | minimum meeting rooms + who goes where |
| 2 | `py_island_matrix_counter` | `island_matrix_counter()` | count connected `"1"` regions (no diagonals) |
| 3 | `py_prism_detector` | `prism_detector()` | find a word in a grid in all 8 directions |
| 3 | `py_word_ladder` | `word_ladder()` | shortest one-letter-at-a-time transformation |

Two Rank 05 subjects are shaped unlike anything in Rank 03, and the tester
grew to fit them rather than the other way round:

* **`py_compress_decompress` asks for two functions.** Both are graded in
  one run and the verdict covers both — a perfect `compress()` with a
  missing `decompress()` fails, and the report names which half broke. The
  generated stub defines both.
* **Tuples and int-keyed dicts are graded faithfully.** `schedule_meetings`
  returns a tuple of tuples, `prism_detector` a list of tuples, and
  `graph_cycle_detector` takes a dict keyed by `int`. Returning a list
  where a tuple was asked for **fails**, exactly as it would on the real
  exam.

> ℹ️ Rank 05's spiral subject is filed as **`py_spiral_generator`** rather
> than the published `py_spiral_matrix`: the training pool already has a
> `py_spiral_matrix` (spiral *traversal* of an existing matrix — a
> different exercise), and two subjects fighting over one `rendu/` filename
> is a trap. The function name, `generate_spiral()`, is unchanged.

</details>

## 🧠 Training pool (LeetCode-style)

A second, completely separate pool of exercises for open-ended practice —
grouped by **difficulty** instead of exam level, and **never** drawn into
`make exam` or shown in `--list`. Reach it through the main menu's
**Training mode**, `make train`, or `python3 -m examshell --train`.

| Difficulty | Exercises |
|---|---|
| 🟢 Easy   | `py_fizzbuzz_list` · `py_first_unique_char` · `py_missing_number` · `py_contains_duplicate` · `py_single_number` · `py_climbing_stairs` |
| 🟡 Medium | `py_group_anagrams` · `py_product_except_self` · `py_kth_largest` · `py_three_sum` · `py_spiral_matrix` · `py_container_with_most_water` · `py_string_compression` |
| 🔴 Hard   | `py_merge_intervals` · `py_longest_increasing_subsequence` · `py_trapping_rain_water` · `py_coin_change` · `py_edit_distance` · `py_largest_rectangle_histogram` · `py_longest_common_subsequence` |

These are graded through the exact same sandbox as the exam pool (same
edge-case + fuzz testing, mutation/print detection, import checks), just
picked and listed differently. `python3 -m examshell --list-training` prints the
pool; `python3 -m examshell --train easy` opens the picker filtered to the easy
exercises, `--train py_kth_largest` drills that one exercise directly.

## 🧪 How grading works

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
is not a list — the same pickiness the moulinette has. Cases cross into the
sandbox as JSON, which would flatten a tuple into a list and stringify an
`int` dict key; both are wrapped so they arrive exactly as the bank wrote
them (`grader.encode_value()`), which is what lets the Rank 05 subjects
grade tuples and int-keyed graphs honestly.

A subject that asks for **more than one function** (Rank 05's
`compress`/`decompress`) is graded as one exercise with one verdict: each
function gets its own cases and fuzz, both must be defined, and a failing
call is labelled with the function it came from.

Beyond pass/fail, the grader tells you when:

* your function **printed** the answer instead of returning it (the single
  most common way to fail an exam you had actually solved),
* your function **mutated its input** when the subject asked for a new
  value,
* your **signature is wrong** — one clear message instead of forty
  identical `TypeError`s,
* you used an **import**, which the real exam forbids (a warning by
  default, a failure with `--strict-imports`).

## 🛠️ Make targets

| Target | What it does |
|---|---|
| `make` | show the help |
| `make run` | interactive menu (exam · practice · list) |
| `make exam` | start the exam directly |
| `make practice` | drill exercises — `make practice EX=py_inter` for one |
| `make list` | print the exercise pool |
| `make train` | Training mode — `make train EX=easy` or `EX=py_kth_largest` |
| `make list-training` | print the training pool (by difficulty) |
| `make stub EX=…` | create an empty solution file (never overwrites) |
| `make grade EX=…` | grade one solution, no menu |
| `make grade-all` | grade every **exam** solution in `rendu/` at once, one overview (training solutions: `make grade EX=…`) |
| `make stats` | your local practice history — attempts, pass rate, best exam time (per rank) |
| `make readiness` | which exam exercises you've passed / failed / never tried, level by level |
| `make drill` | a short daily session from your gaps (`N=3` for 3 exercises) |
| `make update` | pull the latest version of this tester |
| `make ranks` | list the exam ranks, their pools, and which one is active |
| `make unit` | fast unit tests for the tool's own logic |
| `make check` | self-test every exam bank + the training bank (`RANK=04` narrows it to one) |
| `make test` | `unit` + `check` |
| `make lint` | parse-check the sources, plus ruff/pyflakes if installed |
| `make status` | show which solutions you have written so far |
| `make install` | create `venv/` and install `rich` |
| `make clean` | remove caches and stray artefacts |
| `make fclean` | `clean` + remove `venv/` |
| `make re` | `fclean` + `install` + `check` |
| `make rendu-clean` | delete your solutions (asks for confirmation first) |

Options: `RANK=03|04|05`, `EX=<exercise>`, `SEED=<n>`, `RENDU=<dir>`,
`FLAGS='--strict-imports'`, `PYTHON=python3.11`.

```bash
make exam SEED=42                 # reproducible exam, same draw every time
make exam RANK=04                 # the Rank 04 pool instead of Rank 03
make list RANK=05                 # what Rank 05 contains
make exam FLAGS=--relaxed         # lenient exam: imports only warn, `new` allowed
make exam FLAGS="--time-limit 180"  # end the exam after 3 hours
make grade EX=py_inter FLAGS=--strict-imports  # strict grading outside the exam too
```

## ⌨️ CLI

The Makefile is a thin wrapper; everything is reachable directly:

```
python3 -m examshell                       # interactive menu (Rank 03)
python3 -m examshell --rank 04             # …the Rank 04 pool instead
python3 -m examshell --rank 05 --exam      # straight into the Rank 05 exam
python3 -m examshell --list-ranks          # which ranks exist, and what's in them
python3 -m examshell --exam --seed 42      # reproducible exam
python3 -m examshell --practice py_inter   # drill one exam exercise
python3 -m examshell --train               # training mode (LeetCode-style, by difficulty)
python3 -m examshell --train easy          # …filtered to easy exercises
python3 -m examshell --train py_kth_largest  # …drill one training exercise directly
python3 -m examshell --grade inter         # grade once (unique suffixes work)
python3 -m examshell --grade-all           # grade every exam solution in rendu/
python3 -m examshell --check               # validate every bank (add --rank for one)
python3 -m examshell --stats               # your local practice history
python3 -m examshell --readiness           # passed/failed/untried, level by level
python3 -m examshell --drill 5             # a short session from your gaps
python3 -m examshell --exam --time-limit 180   # exam with a 3-hour countdown
python3 -m examshell --version
python3 -m examshell --theme light --save-config   # remember a theme for next time
python3 -m examshell --list
python3 -m examshell --list-training
python3 -m examshell --help
```

Run it from the repository root — `examshell/` is a package, not a standalone
script, so `python3 examshell/examshell.py` will not work.

Useful flags: `--rank {03,04,05}`, `--rendu DIR`, `--timeout SEC`, `--fuzz N`, `--show-fails N`,
`--strict-imports`, `--relaxed`, `--time-limit MIN`, `--theme {dark,light,highcontrast}`,
`--save-config`, `--no-color`, `--no-rich`, `--no-update-check`. See
[shared features](features.md)
for what `--theme`, `--save-config` and `--stats` actually do.
