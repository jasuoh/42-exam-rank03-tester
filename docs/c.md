# 🔧 C tester · Exam Rank 02

Everything about the C tester. Day to day you use it through the app
(`make`, then **Switch exam** → C Rank 02); the command line is at the end.

[← back to the README](../README.md)

---


A second, independent practice tester in the same repo, for the **42
Common Core C Exam Rank 02** — same shape (levels, `grademe`, outside the
exam a stub with a quick self-check), completely different grading
mechanism underneath: your
file is **compiled**, not imported.

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
grader's harness `#include "list.h"`, and the stub (`t` / `e`) and grading
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
The bank self-test (`make c-test`) scans every prototype for that specific pattern regardless
of which `cc` you run it with.

Outside the exam, every generated **"function"**-kind stub also ships a `#ifdef
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
  Marked in **bold** below and with ★ in `--list`; the only pool the exam
  draws from.
* **Extra (3)** — this project's own invented additions for more
  text-manipulation practice, one per level 1–3, not verified against any
  real exam sheet, **never drawn into an exam** — they're in Practice →
  *Extra* (○ in `--list`).

<details>
<summary><b>📖 Show the full C exercise pool (60 exercises)</b></summary>
<br>

| Level | Standard (drawn by the exam) | Extra (practice only) |
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
that's nobody's fault).

**Structured exercises** — `flood_fill`, `ft_list_foreach` and
`ft_list_remove_if` — get a hand-written generator for *whole* cases
instead (`CASE_FUZZERS` in `c_exam/grader.py`), aimed at their classic
bugs: for `remove_if` a match at the head (the head pointer must move), at
the tail, on every node, on none, and the empty list; for `flood_fill`
random grids with the start in a corner, on an edge, on a 1-cell island
and occasionally off the grid. Every generated case is checked against the
reference solution under valgrind in CI. Only `fizzbuzz` (no input at all)
isn't fuzzed — the bank self-test (`make c-test`) marks fuzzed exercises
with `(+fuzz)`.

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
**difficulty** instead of exam level, never drawn into an exam or shown in
`--list`. It's in Practice → *Extra*, or `python3 -m c_exam --train`.

| Difficulty | Exercises |
|---|---|
| 🟢 Easy   | `array_sum` · `find_max` · `is_palindrome_num` |
| 🟡 Medium | `count_pairs_sum` · `kadane_max_sum` · `count_unique` |
| 🔴 Hard   | `lis_length` · `count_inversions` · `max_gap` |

Deliberately smaller than the Python tool's 20 — every exercise here uses
only plain `int`/`int *` arguments and an `int` return with no precondition
on how the array is ordered, so `--fuzz` (see above) already covers all
nine automatically; `python3 -m c_exam --check` validates
this bank the same real-compiler way as the exam pool.
`python3 -m c_exam --list-training` prints the pool; `python3 -m c_exam
--train easy` opens the picker filtered to the easy exercises, `--train
array_sum` drills that one exercise directly.

## ⌨️ Command line

For scripts and the plain menu — the app needs none of this.
`python3 -m c_exam --help` lists the main flags; the useful ones:

```
python3 -m c_exam                       # the plain menu (--tui: the app)
python3 -m c_exam --exam                # straight into the exam
python3 -m c_exam --practice ft_atoi    # practise one exercise
python3 -m c_exam --train easy          # the training pool, by difficulty
python3 -m c_exam --stub ft_atoi        # write c_rendu/ft_atoi.c (never overwrites)
python3 -m c_exam --grade atoi          # grade once (unique suffixes work; exit 0 = OK)
python3 -m c_exam --grade-all           # grade every solution in c_rendu/
python3 -m c_exam --check               # validate both banks (real compiles)
python3 -m c_exam --list                # the pool (--list-training)
python3 -m c_exam --sync                # sync (--sync-setup URL, --auto-sync on|off)
python3 -m c_exam --feedback exam       # report an exercise (exam|bug|idea)
python3 -m c_exam --stats               # your history (--readiness, --drill 5)
python3 -m c_exam --doctor
```

| Flag | |
|---|---|
| `--rendu DIR` | where your solutions are (default `c_rendu`) |
| `--cc COMPILER` | the compiler (also a setting in the app) |
| `--seed N` | a reproducible exam |
| `--relaxed` | lenient exam: warnings only, `new` allowed, full stub |
| `--time-limit MIN` · `--blind` | exam clock · grademe without the failing test |
| `--valgrind` · `--strict-valgrind` | leak checks (warn · fail) |
| `--strict-norm` · `--strict-forbidden` · `--strict` | fail on warnings / forbidden calls outside the exam too (`--strict`: both) |
| `--diff` | point at the first differing character |
| `--timeout SEC` · `--fuzz N` · `--show-fails N` · `--save-config` | time per test, random tests, failures shown; remember them |
| `--no-color` · `--no-rich` · `--no-update-check` | plain output, no update check |

See also [Fuzzing](#-fuzzing), [Valgrind (optional)](#-valgrind-optional)
and the [features](features.md) both testers share.

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
grading mechanism itself (`c_exam/grader.py`) is new. Settings, local
stats, exam save/resume and stuck-student hints (`examshell/settings.py`,
`examshell/stats.py`, `examshell/session_store.py`, `examshell/hints.py`)
are shared the same way — see
[shared features](features.md).

<br>

---
