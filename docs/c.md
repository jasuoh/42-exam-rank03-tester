# 🔧 C tester · Exam Rank 02

Everything about the C tester (`python3 -m c_exam`, `make c-…`).

[← back to the README](../README.md)

---


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
* a **compiler warning** was raised (`-Wall -Wextra` always run) — a
  warning in practice, a **hard failure in the exam** (`-Werror`, like the
  real one; `--strict-norm` does the same outside the exam, `--relaxed`
  turns it off in the exam),
* you used a **forbidden libc call** for that exercise (e.g. `atoi` itself
  for `ft_atoi`) — again a warning in practice and a **failure in the
  exam** (`--strict-forbidden` / `--relaxed` as above).

An infinite loop in a "program" stops being run after 3 timeouts in a row
— the remaining cases are marked skipped instead of each waiting out the
full timeout.

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

**60 exercises, across 4 levels**, split the same way as the Python
bank — Standard vs Extra:

* **Standard (57)** — the complete pool of a real Exam Rank 02 practice
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
<summary><b>📖 Show the full C exercise pool (60 exercises)</b></summary>
<br>

| Level | Standard (drawn by `make c-exam`) | Extra (practice mode only) |
|------:|----------|-------|
| 1 (12) | **`first_word`** 🖥️ · **`fizzbuzz`** 🖥️ · **`ft_putstr`** · **`ft_strcpy`** · **`ft_strlen`** · **`ft_swap`** · **`repeat_alpha`** 🖥️ · **`rev_print`** 🖥️ · **`rot_13`** 🖥️ · **`rotone`** 🖥️ · **`search_and_replace`** 🖥️ · **`ulstr`** 🖥️ | `count_vowels` 🖥️ |
| 2 (20) | **`alpha_mirror`** 🖥️ · **`camel_to_snake`** 🖥️ · **`do_op`** 🖥️ · **`ft_atoi`** · **`ft_strcmp`** · **`ft_strcspn`** · **`ft_strdup`** · **`ft_strpbrk`** · **`ft_strrev`** · **`ft_strspn`** · **`inter`** 🖥️ · **`is_power_of_2`** · **`last_word`** 🖥️ · **`max`** · **`print_bits`** · **`reverse_bits`** · **`snake_to_camel`** 🖥️ · **`swap_bits`** · **`union`** 🖥️ · **`wdmatch`** 🖥️ | `is_palindrome_str` 🖥️ |
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

### 🎲 Fuzzing

`--fuzz N` (default 8) adds N random extra cases to every **"program"-kind
exercise** (except `fizzbuzz`, which takes no input) and every
**"function"-kind exercise whose args are all "safe" to randomise**.

**Programs** are fuzzed by argv *shape* — each one names its shape in the
bank (`sentence`, `two_strings`, `subsequence`, `camel`, `snake`,
`positive_int`, `do_op`, `search_and_replace`, `any_args`, …), and the
generators aim at exactly what people fail real exams on: runs of spaces
**and tabs**, leading/trailing blanks, empty and blank-only strings,
punctuation, and — in about 1 case in 10 — the wrong number of arguments.
Every generator stays inside the subject's own promises (a positive number
where the subject guarantees one, no division by zero for `do_op`).

**Functions** are fuzzed when their args are — plain `int`/`char`/`str`/`int_arr`/`int_list`/`buf`
arguments with no exercise-specific precondition. Unlike the Python
tool, there is no per-exercise custom fuzzer: C has no oracle-only
in-process check, so a fuzzed value can only be validated by actually
compiling and running it, and a value the oracle doesn't expect could
trigger undefined behaviour identically on both sides (a false failure
that's nobody's fault). So exercises using a linked list, `t_point`,
a char grid, or a fixed callback keep their curated cases only —
`make c-check` marks which exercises got fuzzed with `(+fuzz)`.

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
| `make c-readiness` | which exam exercises you've passed / failed / never tried, level by level |
| `make c-drill` | a short daily session from your gaps (`N=3` for 3 exercises) |
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
python3 -m c_exam --readiness           # passed/failed/untried, level by level
python3 -m c_exam --drill               # a short session from your gaps
python3 -m c_exam --exam --relaxed      # lenient exam: warnings only, `new` allowed
python3 -m c_exam --list
python3 -m c_exam --list-training
python3 -m c_exam --help
```

Useful flags: `--rendu DIR`, `--cc COMPILER`, `--timeout SEC`, `--strict-norm`,
`--strict-forbidden`, `--fuzz N`, `--valgrind`, `--strict-valgrind`, `--show-fails N`,
`--relaxed`, `--time-limit MIN`, `--theme {dark,light,highcontrast}`, `--save-config`,
`--no-color`, `--no-rich`, `--no-update-check`. Same shared theme/config/stats/resume/report layer as the
Python tester — see
[shared features](features.md),
[Fuzzing](#-fuzzing) for what `--fuzz` covers here, and
[Valgrind (optional)](#-valgrind-optional) for the leak checker.

## 🗂️ Layout

| File | |
|---|---|
| `c_exam/__main__.py` | entry point for `python3 -m c_exam` |
| `c_exam/examshell.py` | the C tester: its CLI, stubs, and the hooks the shared flow needs (see `examshell/shell_common.py`) |
| `c_exam/grader.py` | harness codegen, the compile/run/diff sandbox, fuzzing, the self-test |
| `c_exam/bank.py` | the exam exercise bank ⚠ **contains the answers** |
| `c_exam/training_bank.py` | the LeetCode-style training bank ⚠ **contains the answers** |
| `c_rendu/` | your solutions (git-ignored) |

The whole exam/practice/training flow is **shared** with the Python tool
(`examshell/shell_common.py`) — `c_exam/examshell.py` only supplies what is
C-specific. Rendering is shared too — `c_exam/examshell.py` uses
`examshell/ui.py` directly, unchanged in behavior, including `exercise_table`/
`training_table`. `examshell/grader.py`'s `Report` is reused too; only the
grading mechanism itself (`c_exam/grader.py`) is new. Themes, saved
config, local stats, exam save/resume, session reports and stuck-student
hints (`examshell/settings.py`, `examshell/stats.py`, `examshell/session_store.py`,
`examshell/report_export.py`, `examshell/hints.py`) are shared the same way — see
[shared features](features.md).

<br>

---
