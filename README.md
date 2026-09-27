<div align="center">

# ⌨️ ExamShell

### Practice testers for the 42 Common Core exams

**🐍 Python · Exam Ranks 03 · 04 · 05** &nbsp;·&nbsp; **🔧 C · Exam Rank 02**

*Real sandboxed grading. Real edge cases. Real compiler. Zero internet required.*

[![CI](https://github.com/jasuoh/42-exam-tester/actions/workflows/ci.yml/badge.svg)](https://github.com/jasuoh/42-exam-tester/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-none%20required-brightgreen)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)
![Visitors](https://komarev.com/ghpvc/?username=jasuoh&repo=42-exam-rank03-tester&label=Views&color=blueviolet&style=flat)

**[⚡ Quick start](#-quick-start)** &nbsp;·&nbsp;
**[✨ Features](#-features)** &nbsp;·&nbsp;
**[🐍 Python tester](#-python--exam-ranks-03--04--05-tester)** &nbsp;·&nbsp;
**[🔧 C tester](#-c-exam-rank-02-tester)**

</div>

<br>

Two independent practice testers, built in the style of the real `examshell` /
moulinette used at 42 — one for the **Python Common Core Exams Rank 03, 04
and 05**, one for the **C Common Core Exam Rank 02**. Same philosophy on both
sides: draw a random exercise per level, write your solution, type `grademe`,
and only advance at **100 %** — no partial credit, no shortcuts, just like the
real thing.

<br>

## ⚡ Quick start

```bash
git clone <this-repo> && cd 42-exam-tester

make install     # optional — venv + rich, for the pretty TUI
make run         # 🐍 Python · Exam Rank 03 — interactive menu
make exam RANK=04   # …or jump straight into the Rank 04 pool (03 · 04 · 05)

make c-run       # 🔧 C · Exam Rank 02 — interactive menu (needs a C compiler, that's it)
```

That's it — you're in. Both are **zero-dependency by design**: without
`rich` the Python tool falls back to clean plain-ANSI output, and the C tool
only needs whatever `cc`/`gcc`/`clang` your machine already has. Either one
runs on a bare exam machine with nothing preinstalled.

<div align="center">

| | 🐍 Python · Exam Ranks 03 · 04 · 05 | 🔧 C · Exam Rank 02 |
|---|:---:|:---:|
| **Levels** | 6 (R03) · 4 (R04) · 3 (R05) | 4 |
| **Exercises** | 44 (14 standard + 30 extra) · 7 (R04) · 7 (R05) | 59 (56 standard + 3 extra) |
| **Training pool** | 20 exercises, 3 difficulties | 9 exercises, 3 difficulties |
| **Grading engine** | in-process sandbox, type-strict `deep_eq` | compile → run → diff stdout, real `cc` |
| **Solutions live in** | `rendu/` | `c_rendu/` |
| **Extra checks** | mutation/print detection, import ban | crash/timeout, `-Wall -Wextra`, 🧪 Valgrind |
| **Pick a rank** | `RANK=04` · `--rank 04` (each keeps its own stats) | — |
| **Run it** | `make run` · `python3 -m src` | `make c-run` · `python3 -m c_exam` |

</div>

<br>

## ✨ Features

Everything below is **shared** between both testers (same theme, same local
stats, same resume/report engine) — learn it once, it just works on both.

| | |
|---|---|
| 🏖️ **True sandboxed grading** | your file is never imported/linked into the tester itself — a subprocess (Python) or a fresh compiled binary (C) does the work, so a crash or an infinite loop can never take your session down with it |
| 🎲 **Fuzzing** | curated edge cases *plus* randomised extra tests on every run — passing once by luck isn't enough |
| 🧪 **Valgrind leak checking** *(C, optional)* | `--valgrind` / `--strict-valgrind` catch leaks and invalid memory access, exactly what the real exam grades you on |
| 💡 **Stuck-student hints** | fail the same exercise 3× in a row in practice and get one hedged, non-spoiling nudge — never during `--exam` |
| 🎨 **Three colour themes** | `dark`, `light`, and a colour-blind-friendly `highcontrast` (Okabe–Ito palette) |
| ⏸️ **Resume an aborted exam** | `quit` saves your progress; next run offers to pick up exactly where you left off |
| 📄 **Session reports** | every exam run writes a Markdown summary to `~/.examshell/reports/` — a study log you can diff between attempts |
| 📊 **Local stats** | `--stats` shows attempts, pass rate, best exam time, and a per-exercise breakdown — all 100 % local, never sent anywhere |
| 🏅 **Achievements** | Flawless runs, first full clears, personal bests — bragging rights only, zero effect on scoring |
| 🔎 **Fuzzy exercise search** | `/text` in any picker narrows the list instantly |
| 🧠 **A second, separate training pool** | LeetCode-style drills by difficulty, never mixed into a real exam draw |
| 🪜 **Three Python exam ranks** | Rank 03, 04 and 05 in one tool (`RANK=04`), each with its own pool, level count and history |

<br>

## 🗺️ Table of contents

**🐍 Python · Exam Ranks 03 · 04 · 05**
[How the exam works](#-how-the-exam-works) ·
[Exercise pool](#-exercise-pool) ·
[Rank 04 & 05 pools](#-rank-04--05-pools) ·
[Training pool](#-training-pool-leetcode-style) ·
[How grading works](#-how-grading-works) ·
[Quality-of-life features](#️-quality-of-life-features-both-testers) ·
[Make targets](#️-make-targets) ·
[CLI](#️-cli) ·
[Testing](#-testing-this-project) ·
[Layout](#️-layout)

**🔧 C · Exam Rank 02**
[How it works](#-how-it-works) ·
[Exercise pool](#-exercise-pool-1) ·
[Fuzzing](#-fuzzing-partial) ·
[Valgrind](#-valgrind-optional) ·
[Training pool](#-training-pool-leetcode-style-1) ·
[Make targets](#️-make-targets-1) ·
[CLI](#️-cli-1) ·
[Layout](#️-layout-1)

---

# 🐍 Python · Exam Ranks 03 / 04 / 05 tester

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
| `new` | draw a different exercise for this level |
| `stub` | create the solution file for you |
| `quit` | abort (you still get a summary) |

Modes from the main menu: **Start exam** (the full run above — draws only
from the Standard 14, one per level), **Practice mode** (drill *any* of
the 44, Standard or Extra, no progression), **List all exercises**,
**Training mode** (LeetCode-style exercises by difficulty — see below,
never part of the exam).

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

`python3 -m src --list` prints this pool with the exact function name for
each exercise, ★/○ marking which pool each belongs to; the full signature
and subject show up once you draw or practice it.

## 🪜 Rank 04 & 05 pools

The published Rank 04 and Rank 05 Python pools are much smaller than Rank
03's, and **every exercise in them is a documented subject** — so there is
no Standard/Extra split here: all 14 are ★, and `make exam RANK=04` can
draw any of them. The flip side of a small pool is that some levels hold a
single exercise, so `new` simply re-draws it — that is the real pool, not a
bug.

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
**Training mode**, `make train`, or `python3 -m src --train`.

| Difficulty | Exercises |
|---|---|
| 🟢 Easy   | `py_fizzbuzz_list` · `py_first_unique_char` · `py_missing_number` · `py_contains_duplicate` · `py_single_number` · `py_climbing_stairs` |
| 🟡 Medium | `py_group_anagrams` · `py_product_except_self` · `py_kth_largest` · `py_three_sum` · `py_spiral_matrix` · `py_container_with_most_water` · `py_string_compression` |
| 🔴 Hard   | `py_merge_intervals` · `py_longest_increasing_subsequence` · `py_trapping_rain_water` · `py_coin_change` · `py_edit_distance` · `py_largest_rectangle_histogram` · `py_longest_common_subsequence` |

These are graded through the exact same sandbox as the exam pool (same
edge-case + fuzz testing, mutation/print detection, import checks), just
picked and listed differently. `python3 -m src --list-training` prints the
pool; `python3 -m src --train easy` opens the picker filtered to the easy
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

## 🎛️ Quality-of-life features (both testers)

Everything below lives in `src/settings.py`, `src/stats.py`,
`src/session_store.py` and `src/report_export.py` — one small shared layer
used by **both** `python3 -m src` and `python3 -m c_exam`, so it works the
same way and stores its files in the same place (`~/.examshell/`) no matter
which tester you're using. None of it is required reading: the exam and
practice flow work exactly as before if you never touch any of this.

Everything here is **best-effort**: if `~/.examshell/` can't be created or
written to (a locked-down exam machine, a read-only `$HOME`), these features
just silently do nothing — they never make grading fail.

### 🎨 Themes

Three colour themes, picked with `--theme`:

| Theme | For |
|---|---|
| `dark` (default) | the original palette — bright colours, dark terminal background |
| `light` | a white/light terminal background (darker, more saturated colours so nothing washes out) |
| `highcontrast` | colour-blind friendly — swaps the usual red/green pass-fail colours for the [Okabe–Ito](https://jfly.uni-koeln.de/color/) blue/vermillion/orange palette, which stays distinguishable under the common forms of colour-vision deficiency |

```bash
python3 -m src --theme highcontrast     # try it for one run
python3 -m src --theme light --save-config   # remember it for every future run
```

`--save-config` writes `--theme` (and `--timeout`/`--fuzz`/`--show-fails`,
`--cc` for the C tester) to `~/.examshell/config.json` and exits — no exam
or practice session starts. From then on, any run that doesn't pass the
flag explicitly picks up the saved value; an explicit flag on the command
line always wins over the saved one.

### 📊 Local stats

Every `grademe` (in an exam or in practice) and every `--grade` appends one
line to `~/.examshell/stats.jsonl` — purely local, never sent anywhere.

```bash
python3 -m src --stats      # or: make stats
python3 -m c_exam --stats   # or: make c-stats
```

Shows your overall attempts and pass rate, your best full-exam completion
time, and a per-exercise breakdown (`3/7 passed`, …) — a quick way to see
which exercises you actually need more reps on.

### 💡 Stuck? A small nudge, not a spoiler

Fail the **same** exercise three times in a row in practice/training mode
(tracked via the local stats above) and the next failing report ends with
one hedged, one-line hint — never the answer, just a push in the right
direction:

```
✖  ████████░░░░░░░░  17/36 tests passed   47%
💡 Think about the edge cases first: 0, 1 and negative numbers are never
   prime — if it's only wrong for small n, that's almost always it.
```

Two sources, in order: a hand-written hint on the exercise itself when one
exists (a growing set — not every exercise has one yet), otherwise a
generic guess from the shape of the failure alone (off-by-one, a sign
flip, an unhandled empty-input case, a crash pointing at memory rather
than logic, a leak Valgrind caught, an infinite loop). The generic one is
a heuristic, not a diagnosis — it's phrased as "could be", and stays
silent rather than guess wrong when nothing matches.

A curated hint can also react to *which kind* of failure it was, instead
of always saying the same thing: a crash and a Valgrind leak on the same
exercise usually call for different advice (e.g. `ft_split` points at a
missing NULL-terminator slot for a crash, but a missing free on an error
path for a leak), so the exercise can define one hint per failure kind
instead of a single fixed string.

**Never shown during `--exam`** —
getting unstuck without a crutch under time pressure is part of what the
exam actually tests, so practice/training is where this builds that
muscle instead of short-circuiting it.

### 📄 Session reports

Every exam run — passed or aborted — writes a small Markdown summary to
`~/.examshell/reports/` (login, score, time, per-level attempts/time, any
badges earned) and prints the path at the end. Nothing to configure; it's
just a record you can keep, diff between attempts, or paste into a study
log.

### ⏸️ Resuming an aborted exam

`quit` during an exam now saves your progress (level, passed exercises,
the exercise currently drawn, attempts, elapsed time) to
`~/.examshell/saved_exam_py.json` (`saved_exam_c.json` for the C tester).
The next time you start an exam, you're asked whether to resume:

```
Resume saved exam for alice — level 3? [Y/n]:
```

Say no (or let the exam finish normally) and the save is discarded. This
is a convenience for closed laptops and accidental `quit`s, not a way to
game the real exam's rules — the real moulinette has no resume button
either.

### 🔎 Fuzzy search in the exercise picker

Practice mode's and Training mode's exercise pickers accept `/text` as a
quick filter — type `/` followed by part of an exercise or function name
to narrow the list, `/` alone to clear it:

```
Selection (number, /text to filter, or 'b' to go back): /matrix
```

### 🏅 Achievements

Shown at the end of a **passed** exam, in the summary panel and in the
saved report: 🏅 *Flawless* (every level cleared on the first `grademe`),
🎉 *First full clear!* (your first ever 100% run for that tester), and ⏱
*New personal best time!* (faster than any previous completion) — bragging
rights only, they don't affect scoring.

**→ [TUTORIAL.md](TUTORIAL.md)** walks through all six of the above
step by step, with real command output.

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
make exam FLAGS=--strict-imports  # any import fails grading, like the moulinette
```

## ⌨️ CLI

The Makefile is a thin wrapper; everything is reachable directly:

```
python3 -m src                       # interactive menu (Rank 03)
python3 -m src --rank 04             # …the Rank 04 pool instead
python3 -m src --rank 05 --exam      # straight into the Rank 05 exam
python3 -m src --list-ranks          # which ranks exist, and what's in them
python3 -m src --exam --seed 42      # reproducible exam
python3 -m src --practice py_inter   # drill one exam exercise
python3 -m src --train               # training mode (LeetCode-style, by difficulty)
python3 -m src --train easy          # …filtered to easy exercises
python3 -m src --train py_kth_largest  # …drill one training exercise directly
python3 -m src --grade inter         # grade once (unique suffixes work)
python3 -m src --grade-all           # grade every exam solution in rendu/
python3 -m src --check               # validate every bank (add --rank for one)
python3 -m src --stats               # your local practice history
python3 -m src --theme light --save-config   # remember a theme for next time
python3 -m src --list
python3 -m src --list-training
python3 -m src --help
```

Run it from the repository root — `src/` is a package, not a standalone
script, so `python3 src/examshell.py` will not work.

Useful flags: `--rank {03,04,05}`, `--rendu DIR`, `--timeout SEC`, `--fuzz N`, `--show-fails N`,
`--strict-imports`, `--theme {dark,light,highcontrast}`, `--save-config`,
`--no-color`, `--no-rich`. See
[Quality-of-life features](#️-quality-of-life-features-both-testers) above
for what `--theme`, `--save-config` and `--stats` actually do.

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
| `src/__main__.py` | entry point for `python3 -m src` |
| `src/examshell.py` | CLI, menu, exam and practice flow |
| `src/grader.py` | test building, the sandbox, the self-test |
| `src/ui.py` | all rendering — `rich` when available, ANSI otherwise |
| `src/bank_common.py` | tiny helpers shared by both exercise banks |
| `src/exam_bank.py` | the 6-level Rank 03 exam bank ⚠ **contains the answers** |
| `src/exam_bank_r04.py` | the 4-level Rank 04 exam bank ⚠ **contains the answers** |
| `src/exam_bank_r05.py` | the 3-level Rank 05 exam bank ⚠ **contains the answers** |
| `src/ranks.py` | which ranks exist: bank, level count, history tag |
| `src/training_bank.py` | the LeetCode-style training bank, shared by every rank ⚠ **contains the answers** |
| `src/settings.py` | `~/.examshell/config.json` — theme/timeout/fuzz/show-fails, shared by both testers |
| `src/stats.py` | `~/.examshell/stats.jsonl` — local grading history, shared by both testers |
| `src/session_store.py` | exam save/resume state, shared by both testers |
| `src/report_export.py` | Markdown session reports in `~/.examshell/reports/`, shared by both testers |
| `src/hints.py` | the "stuck 3x in a row" nudge (generic + curated), shared by both testers |
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

# 🔧 C · Exam Rank 02 tester

A second, independent practice tester in the same repo, for the **42
Common Core C Exam Rank 02** — same shape (levels, `grademe`, a stub with a
quick self-check), completely different grading mechanism underneath: your
file is **compiled**, not imported.

```bash
make c-run           # interactive menu
make c-exam          # jump straight into the exam
```

Solutions live in `c_rendu/` (separate from the Python tool's `rendu/`).
Uses your system's `cc` by default — no extra dependency, works on any
machine with a C compiler.

## 🔍 How it works

Real Exam Rank 02 subjects come in two shapes, and this bank has both —
each graded differently:

* **"Write a function"** (e.g. `ft_atoi`, `ft_split`, `sort_list`) — the
  bank supplies a reference implementation (`oracle_c`) and a small type
  description (`args`/`returns`/curated `cases`). From that, the tester
  **generates a `main()`** that calls the function under test once per
  case, each call's output isolated by a marker. That generated `main()`
  is compiled once against the reference implementation and once against
  your file, both binaries run, and their output is compared call-by-call
  — the same "exactness" philosophy as the Python tool's type-strict
  comparison, just at the level of raw stdout bytes. Your submission
  **must not define `main()`** here — the tester supplies its own, and a
  leftover `main()` in your file collides with it at link time (reported
  clearly, not as a cryptic linker error).
* **"Write a program"** (e.g. `rotone`, `fizzbuzz`, `hidenp`, `pgcd`) —
  these real subjects hand you argc/argv and expect a full program, so
  there's no harness: your file **must** define `main()`. It's compiled
  standalone, then run once per case with that case's argv, and its
  stdout is compared directly against `oracle_c` (also a full program)
  run the same way.

A few exercises pass or return a singly-linked list (`t_list`, one int
`data` field and a `next` pointer) — for those, both your file and the
grader's harness `#include "list.h"`, and `make c-stub`/`make c-grade`
write that header into `c_rendu/` for you the same way the real exam
hands you one.

Beyond pass/fail, `grademe` tells you when:

* your program **crashed** (segfault, abort, …) — very common in C, and
  much more informative than "0/N passed" on its own,
* your program **timed out** (infinite loop) — per test case in "program"
  mode, per whole run in "function" mode,
* a **compiler warning** was raised (`-Wall -Wextra` always run; add
  `--strict-norm` to turn warnings into hard failures with `-Werror`,
  mirroring the Python tool's `--strict-imports`),
* you used a **forbidden libc call** for that exercise (e.g. `atoi` itself
  for `ft_atoi`) — a warning by default (matching the Python tool's
  default posture on imports), or a hard failure with `--strict-forbidden`
  (matching the real moulinette, and `--strict-imports` on the Python
  side).

`--cc` isn't just a convenience flag: every oracle in both C banks is
also verified against a second compiler (GCC, alongside the default
`cc`/Clang) before being trusted, since the two don't always agree — GCC's
C23 default reads an empty-parens function pointer declaration `int
(*cmp)()` as "takes no parameters" where every older C standard (and
Clang's current default) reads it as "unspecified parameters", so a
prototype that compiles under one can fail to compile under the other.
`make c-check` scans every prototype for that specific pattern regardless
of which `cc` you run it with.

Every generated **"function"**-kind stub also ships a `#ifdef
SELF_TEST`-guarded `main()` with a couple of worked examples, so you can
try your implementation immediately:

```bash
cc -DSELF_TEST c_rendu/ft_atoi.c -o /tmp/t && /tmp/t
```

That guard is what keeps it safe: normal grading never defines `SELF_TEST`,
so the real compile never sees two `main()`s. Unlike the Python tool's
embedded self-check, this one doesn't auto-compare against expected
values — eyeball it against the subject's Examples, or just run `grademe`
for the real, automatic check. **"Program"**-kind stubs don't need that
guard at all — you already have your own `main()`, so just compile and run
the file directly: `cc c_rendu/rotone.c -o /tmp/t && /tmp/t abc`.

## 📚 Exercise pool

**59 exercises, across 4 levels**, split the same way as the Python
bank — Standard vs Extra:

* **Standard (56)** — the complete pool of a real Exam Rank 02 practice
  repository, its own per-level folder structure used directly (not
  blended across sources with different level splits). Names, prototypes,
  behaviour and level placement are all real. Exact level placement still
  varies by campus and changes over time, same caveat as the Python side.
  Marked in **bold** below and with ★ in `--list`; the only pool a real
  `make c-exam` run can draw from.
* **Extra (3)** — this project's own invented additions for more
  text-manipulation practice, one per level 1–3, not verified against any
  real exam sheet, **never drawn into a real exam run** — reach them
  through **Practice mode** instead (marked with ○ in `--list`).

<details>
<summary><b>📖 Show the full C exercise pool (59 exercises)</b></summary>
<br>

| Level | Standard (drawn by `make c-exam`) | Extra (practice mode only) |
|------:|----------|-------|
| 1 (12) | **`first_word`** 🖥️ · **`fizzbuzz`** 🖥️ · **`ft_putstr`** · **`ft_strcpy`** · **`ft_strlen`** · **`ft_swap`** · **`repeat_alpha`** 🖥️ · **`rev_print`** 🖥️ · **`rot_13`** 🖥️ · **`rotone`** 🖥️ · **`search_and_replace`** 🖥️ · **`ulstr`** 🖥️ | `count_vowels` 🖥️ |
| 2 (19) | **`alpha_mirror`** 🖥️ · **`camel_to_snake`** 🖥️ · **`do_op`** 🖥️ · **`ft_atoi`** · **`ft_strcmp`** · **`ft_strcspn`** · **`ft_strdup`** · **`ft_strpbrk`** · **`ft_strrev`** · **`ft_strspn`** · **`is_power_of_2`** · **`last_word`** 🖥️ · **`max`** · **`print_bits`** · **`reverse_bits`** · **`snake_to_camel`** 🖥️ · **`swap_bits`** · **`union`** 🖥️ · **`wdmatch`** 🖥️ | `is_palindrome_str` 🖥️ |
| 3 (15) | **`add_prime_sum`** 🖥️ · **`epur_str`** 🖥️ · **`expand_str`** 🖥️ · **`ft_atoi_base`** · **`ft_list_size`** 🔗 · **`ft_range`** · **`ft_rrange`** · **`hidenp`** 🖥️ · **`lcm`** · **`paramsum`** 🖥️ · **`pgcd`** 🖥️ · **`print_hex`** 🖥️ · **`rstr_capitalizer`** 🖥️ · **`str_capitalizer`** 🖥️ · **`tab_mult`** 🖥️ | `longest_word_str` 🖥️ |
| 4 (10) | **`flood_fill`** 🧩 · **`fprime`** 🖥️ · **`ft_itoa`** · **`ft_list_foreach`** 🔗 · **`ft_list_remove_if`** 🔗 · **`ft_split`** · **`rev_wstr`** 🖥️ · **`rostring`** 🖥️ · **`sort_int_tab`** · **`sort_list`** 🔗 | — |

🖥️ = "program" kind (your own `main()`, argv-driven) · 🔗 = uses a shared
linked-list header (`list.h` for the simple `int`-data `t_list` used by
`sort_list`/`ft_list_size`, `ft_list.h` for the `void *data` generic one
used by `ft_list_foreach`/`ft_list_remove_if` — two different real headers
for two different real subjects, same as the actual exam) · 🧩 =
`flood_fill.h` (`t_point` + a 2D char grid).

The three Extra exercises mirror text exercises the Python side already
has (`py_vowel_counter`, `py_echo_validator`, `py_longest_word`) so you
can practice the same logic in both languages.

`ft_list_foreach`/`ft_list_remove_if` are graded against a fixed test
callback the harness supplies (an accumulator, and an int-equality
comparator respectively) rather than a callback of the student's own
choosing — that's what lets a generic harness test a function-pointer
argument at all, at the cost of not exercising arbitrary callback logic.

</details>

### 🎲 Fuzzing (partial)

`--fuzz N` (default 8, like the Python tool's) adds N random extra cases
to every **"function"-kind exercise whose args are all "safe" to
randomise** — plain `int`/`char`/`str`/`int_arr`/`int_list`/`buf`
arguments with no exercise-specific precondition. Unlike the Python
tool, there is no per-exercise custom fuzzer: C has no oracle-only
in-process check, so a fuzzed value can only be validated by actually
compiling and running it, and a value the oracle doesn't expect could
trigger undefined behaviour identically on both sides (a false failure
that's nobody's fault). So exercises using a linked list, `t_point`,
a char grid, or a fixed callback keep their curated cases only —
`make c-check` marks which exercises got fuzzed with `(+fuzz)`.
**"Program"-kind exercises are never fuzzed** — their argv shapes vary
too much (a bare string vs. multiple flags vs. numeric parsing) to
randomise generically without mostly generating meaningless input.

```bash
python3 -m c_exam --grade ft_atoi --fuzz 20
python3 -m c_exam --check --fuzz 20       # also fuzzes the self-test
```

### 🧪 Valgrind (optional)

`--valgrind` runs your compiled solution through valgrind's leak checker
(`--leak-check=full --show-leak-kinds=all --errors-for-leak-kinds=all`, so a
leak counts as an error the same as an invalid read/write) in addition to
the normal output comparison — a leak/memory error is reported as a
**warning**, output correctness still decides pass/fail. `--strict-valgrind`
raises the stakes: a leak/memory error **fails** grading outright (implies
`--valgrind`). For "function"-kind exercises this is one valgrind pass over
the whole harness run; for "program"-kind exercises it's one pass per case.

Not available at all on Apple Silicon macOS — valgrind simply doesn't
install there — but works on the real 42 school machines' Linux. Both flags
are a no-op with a clear warning when the `valgrind` binary isn't on PATH,
same best-effort posture as `--cc` pointing at a missing compiler.

```bash
python3 -m c_exam --grade ft_split --valgrind
python3 -m c_exam --grade ft_split --strict-valgrind
python3 -m c_exam --check --valgrind          # also leak-checks the self-test
```

## 🧠 Training pool (LeetCode-style)

A second, independent bank for open-ended practice — the C counterpart to
the Python tool's own training pool above, same shape: grouped by
**difficulty** instead of exam level, never drawn into `make c-exam` or
shown in `--list`. Reach it through the main menu's **Training mode**,
`make c-train`, or `python3 -m c_exam --train`.

| Difficulty | Exercises |
|---|---|
| 🟢 Easy   | `array_sum` · `find_max` · `is_palindrome_num` |
| 🟡 Medium | `count_pairs_sum` · `kadane_max_sum` · `count_unique` |
| 🔴 Hard   | `lis_length` · `count_inversions` · `max_gap` |

Deliberately smaller than the Python tool's 20 — every exercise here uses
only plain `int`/`int *` arguments and an `int` return with no precondition
on how the array is ordered, so `--fuzz` (see above) already covers all
nine automatically; `make c-check`/`python3 -m c_exam --check` validates
this bank the same real-compiler way as the exam pool.
`python3 -m c_exam --list-training` prints the pool; `python3 -m c_exam
--train easy` opens the picker filtered to the easy exercises, `--train
array_sum` drills that one exercise directly.

## 🛠️ Make targets

| Target | What it does |
|---|---|
| `make c-run` | interactive menu (exam · practice · list · training) |
| `make c-exam` | start the exam directly |
| `make c-practice` | drill exercises — `make c-practice EX=ft_atoi` for one |
| `make c-list` | print the exercise pool |
| `make c-train` | Training mode — `make c-train EX=easy` or `EX=array_sum` |
| `make c-list-training` | print the training pool (by difficulty) |
| `make c-stub EX=…` | create a solution stub (never overwrites) |
| `make c-grade EX=…` | grade one solution, no menu |
| `make c-grade-all` | grade every solution in `c_rendu/` at once, one overview |
| `make c-stats` | your local practice history — attempts, pass rate, best exam time |
| `make c-unit` | fast unit tests for the C tester's own logic |
| `make c-check` | self-test both C exercise banks (every oracle, through the real sandbox) |
| `make c-test` | `c-unit` + `c-check` |

Options: `EX=<exercise>`, `SEED=<n>`, `RENDU=<dir>` (that's `c_rendu` by
default here), `CC=<compiler>` (default `cc`).

## ⌨️ CLI

```
python3 -m c_exam                       # interactive menu
python3 -m c_exam --exam --seed 42      # reproducible exam
python3 -m c_exam --practice ft_atoi    # drill one exercise
python3 -m c_exam --train               # training mode (LeetCode-style, by difficulty)
python3 -m c_exam --train easy          # …filtered to easy exercises
python3 -m c_exam --grade atoi          # grade once (unique suffixes work)
python3 -m c_exam --grade-all           # grade every solution in c_rendu/
python3 -m c_exam --check               # validate both banks
python3 -m c_exam --stats               # your local practice history
python3 -m c_exam --list
python3 -m c_exam --list-training
python3 -m c_exam --help
```

Useful flags: `--rendu DIR`, `--cc COMPILER`, `--timeout SEC`, `--strict-norm`,
`--strict-forbidden`, `--fuzz N`, `--valgrind`, `--strict-valgrind`, `--show-fails N`,
`--theme {dark,light,highcontrast}`, `--save-config`, `--no-color`,
`--no-rich`. Same shared theme/config/stats/resume/report layer as the
Python tester — see
[Quality-of-life features](#️-quality-of-life-features-both-testers) up top,
[Fuzzing (partial)](#-fuzzing-partial) for what `--fuzz` covers here, and
[Valgrind (optional)](#-valgrind-optional) for the leak checker.

## 🗂️ Layout

| File | |
|---|---|
| `c_exam/__main__.py` | entry point for `python3 -m c_exam` |
| `c_exam/examshell.py` | CLI, menu, exam and practice flow |
| `c_exam/grader.py` | harness codegen, the compile/run/diff sandbox, fuzzing, the self-test |
| `c_exam/bank.py` | the exam exercise bank ⚠ **contains the answers** |
| `c_exam/training_bank.py` | the LeetCode-style training bank ⚠ **contains the answers** |
| `c_rendu/` | your solutions (git-ignored) |

Rendering is **shared** with the Python tool — `c_exam/examshell.py` uses
`src/ui.py` directly, unchanged in behavior, including `exercise_table`/
`training_table`. `src/grader.py`'s `Report` is reused too; only the
grading mechanism itself (`c_exam/grader.py`) is new. Themes, saved
config, local stats, exam save/resume, session reports and stuck-student
hints (`src/settings.py`, `src/stats.py`, `src/session_store.py`,
`src/report_export.py`, `src/hints.py`) are shared the same way — see
[Quality-of-life features](#️-quality-of-life-features-both-testers).

<br>

---

## 📄 License

[MIT](LICENSE) — do whatever you want with it, just keep the copyright notice.

---

<div align="center">

### 🍀 Good luck on the real exam

*Solve it, don't memorise it.*

</div>
