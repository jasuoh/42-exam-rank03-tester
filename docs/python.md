# 🐍 Python tester · Exam Ranks 03 / 04 / 05

Everything about the Python tester. Day to day you use it through the app
(`make`, then **Switch exam** → Python Rank 03 / 04 / 05); the command line
is at the end.

[← back to the README](../README.md)

---

Levels in order, one random exercise per level, each graded against dozens
of tests, and you only move up at **100 %** — same rules as the real thing.

**Three exam pools, one tool.** Pick the rank with **Switch exam** in the
app (or `--rank 04` on the command line); the next start opens on it again.

| Rank | Levels | Exercises | Tag its history lives under |
|---|:---:|:---:|---|
| **03** *(default)* | 6 | 44 (14 standard + 30 extra) | `py` |
| **04** | 4 | 7 (all standard) | `py04` |
| **05** | 3 | 7 (all standard) | `py05` |

Each rank keeps its **own** stats and saved exam, so a
half-finished Rank 04 run can never be resumed into a Rank 03 one, and a
Rank 03 best time is never beaten by a shorter Rank 05 one. The training
pool is shared by all three — it is never part of any exam draw anyway.

Your solutions go into `rendu/<exercise>.py`; `e` in the app opens the
file in your editor (a stub with the right signature first), `g` grades it.


## 🎯 How the exam works

1. **Every level, in order** 1 → N — six of them on Rank 03, four on Rank
   04, three on Rank 05.
2. One **random exercise per level**, drawn from that level's pool (two or
   three per level on Rank 03 — see below), dealt like a shuffled deck
   across exams so the same ones don't keep coming back.
3. Write your solution in `rendu/<exercise_name>.py` and define the required
   function. `rendu/` is created for you.
4. `grademe` (`g` in the app). **You only advance at 100 %** — a failed
   level keeps its exercise.

In the plain line-based menu (the fallback without Textual) you type the
commands, like in the real exam:

| Command | |
|---|---|
| `grademe` | test your solution |
| `subject` | show the assignment again |
| `status` | show your progress |
| `new` | draw a different exercise for this level (**only with `--relaxed`**) |
| `stub` | create the solution file for you — in the exam just the bare signature, like the real one (`--relaxed`: with a quick self-check) |
| `quit` | save and leave — the next start offers to resume |

**The exam is as strict as the real one by default.** Practice and training
only *warn* about an `import` (or, in C, a compiler warning or a forbidden
call) so mistakes stay cheap while you learn — but the exam fails you on
them, exactly like the real moulinette, and there is no `new` to redraw an
exercise you don't like. Passing here therefore means something. One flag
changes that:

```bash
python3 -m examshell --exam --relaxed   # lenient exam: warnings only, `new` allowed
```

The time limit is a setting (**Settings** → *Exam time limit*, or
`--time-limit 180`).

With `--seed N` the whole exam is reproducible: the same exercises are
drawn no matter how many times you type `grademe` along the way.

In the app: **Exam** (the run above — draws only from the Standard 14),
**Practice** (any exercise; the *Extra* tab holds the Extra 30 and the
training pool) and **Progress** — see [features.md](features.md).

Outside the exam, every generated stub also embeds a small
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
important — **the exam only ever draws from the Standard 14**:

* **Standard (14)** — the original pool, based on the publicly documented
  Rank-03 exercises. These are the ones that can plausibly show up on the
  *real* 42 exam, and the only ones the exam can draw. Marked in **bold**
  below and with ★ in `--list`.
* **Extra (30)** — added for broader practice: more variety, a wider
  difficulty range, a couple of deliberately easy warm-ups in levels 1–2.
  Good drilling, but not verified against any real exam sheet, and
  **never drawn into an exam** — they're in Practice → *Extra* (○ in
  `--list`).

<details>
<summary><b>📖 Show the full Python exercise pool (44 exercises)</b></summary>
<br>

| Level | Drawn by the exam | Extra (practice only) |
|------:|----------|-------|
| 1 | **`py_cryptic_sorter`** · **`py_inter`** | `py_capitalizer` · `py_char_counter` · `py_char_frequency` · `py_leet_speak` · `py_string_reverser` · `py_vowel_counter` |
| 2 | **`py_echo_validator`** · **`py_mirror_matrix`** | `py_camel_to_snake_converter` · `py_case_counter` · `py_digit_extractor` · `py_even_odd_counter` · `py_longest_common_prefix` · `py_run_length_encoder` · `py_second_largest` · `py_sum_of_squares` |
| 3 | **`py_hidenp`** · **`py_number_base_converter`** · **`py_pattern_tracker`** | `py_binary_gap` · `py_run_length_decoder` · `py_string_rotation_checker` · `py_word_reverser` |
| 4 | **`py_anagram`** · **`py_shadow_merge`** · **`py_string_permutation_checker`** | `py_max_subarray_sum` · `py_pangram_checker` · `py_roman_numeral` · `py_unique_elements` |
| 5 | **`py_string_sculptor`** · **`py_twist_sequence`** | `py_longest_word` · `py_matrix_transposer` · `py_pascals_triangle_row` · `py_zigzag_flatten` |
| 6 | **`py_bracket_validator`** · **`py_whisper_cipher`** | `py_longest_palindromic_substring` · `py_matrix_rotator` · `py_prime_finder` · `py_two_sum_indices` |

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
no Standard/Extra split here: all 14 are ★, and each rank's exam can draw
any of its 7. The flip side of a small pool is that some levels hold a
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
an exam or shown in `--list`. It's in Practice → *Extra*, or
`python3 -m examshell --train`.

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
* you used an **import**, which the real exam forbids (a warning in
  practice, a failure in the exam — and with `--strict-imports` outside it).

## ⌨️ Command line

For scripts and the plain menu — the app needs none of this.
`python3 -m examshell --help` lists the main flags; the useful ones:

```
python3 -m examshell                        # the plain menu (--tui: the app)
python3 -m examshell --rank 04 --exam       # straight into the Rank 04 exam
python3 -m examshell --practice py_inter    # practise one exercise
python3 -m examshell --train easy           # the training pool, by difficulty
python3 -m examshell --stub py_inter        # write rendu/py_inter.py (never overwrites)
python3 -m examshell --grade inter          # grade once (unique suffixes work; exit 0 = OK)
python3 -m examshell --grade-all            # grade every exam solution in rendu/
python3 -m examshell --list                 # the pool (--list-training, --list-ranks)
python3 -m examshell --stats                # your history (--readiness, --drill 5)
python3 -m examshell --sync                 # sync (--sync-setup URL, --auto-sync on|off)
python3 -m examshell --feedback exam        # report an exercise (exam|bug|idea)
python3 -m examshell --check                # self-test the banks
python3 -m examshell --doctor
```

| Flag | |
|---|---|
| `--rank 03\|04\|05` | the exam pool |
| `--rendu DIR` | where your solutions are (default `rendu`) |
| `--seed N` | a reproducible exam: the same draw every time |
| `--relaxed` | lenient exam: imports only warn, `new` allowed |
| `--time-limit MIN` | end the exam after MIN minutes |
| `--blind` | exam grademe says SUCCESS or FAILURE, without the failing test |
| `--timeout SEC` · `--fuzz N` · `--show-fails N` | time per test, random tests, failures shown |
| `--strict-imports` · `--strict` · `--diff` | strict grading outside the exam, side-by-side values |
| `--save-config` | remember `--timeout` / `--fuzz` / `--show-fails` |
| `--no-color` · `--no-rich` · `--no-update-check` | plain output, no update check |

Run it from the repository root — or install the commands `examshell` and
`examshell-c` anywhere with
`uv tool install "examshell[tui] @ git+https://github.com/jasuoh/42-exam-tester"`.

Developing the tester: `make dev` lists the commands (`make test`,
`make check RANK=04` …).
