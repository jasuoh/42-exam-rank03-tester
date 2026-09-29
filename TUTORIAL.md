# Tutorial: running it, testing it, and the quality-of-life features

Step 1 and 2 cover running the tool via the Makefile and checking that the
tool itself is working correctly (`make test`). Everything from step 3 on
walks through the extras described in the README's
[shared features](docs/features.md)
section. Everything here applies to **both** testers — examples below use
`python3 -m src` (or `make …`); swap in `python3 -m c_exam` (or `make
c-…`) for the C tester and it behaves identically, since both share the
same `src/settings.py`, `src/stats.py`, `src/session_store.py`,
`src/report_export.py` and `src/hints.py`.

None of steps 3 onward is required. The exam and practice flow work
exactly as they always have if you never touch any of it.

## 1. Just running it

The Makefile is the easiest way in — no need to remember any `python3 -m`
invocation:

```bash
make install   # optional, once: creates venv/ and installs rich for the nicer TUI
make run       # interactive menu: exam · practice · list · training · stats
```

`make run` with no arguments drops you into the same menu you'd get from
`python3 -m src` directly — pick a mode with a number, or `q` to quit. Once
you know what you want, the other targets skip the menu:

```bash
make exam                    # jump straight into the exam
make practice EX=py_inter    # drill one exercise directly, no picker
make list                    # print the exercise pool and exit
make stats                   # your local practice history
```

### Picking an exam rank

The Python tester ships three exam pools: **Rank 03** (the default, 6
levels), **Rank 04** (4 levels) and **Rank 05** (3 levels). Add `RANK=` to
any target to switch, or pick **5. Switch exam rank** in the menu:

```bash
make ranks           # what each rank contains, and which one is active
make exam RANK=04    # the Rank 04 exam instead of Rank 03
make list RANK=05    # the Rank 05 pool
make stats RANK=04   # your Rank 04 history specifically
```

Each rank keeps its own history, its own saved exam and its own session
reports, so switching mid-practice never disturbs a run in progress on
another one. The training pool (step 4 below) is shared by all three — it
is never part of an exam draw anyway.

`make` with no target (or `make help`) prints the full list of targets for
both testers, with what each one does. Everything here is `make …`; swap
in `make c-…` for the C tester (`make c-run`, `make c-exam`, …) — it's the
same menu, same flow, just against `c_rendu/` and a real `cc`/`gcc`/`clang`
instead of `rendu/`.

## 2. Making sure the tool itself is correct

Two separate checks, and they check different things — run them after
*you* change something in the tool, not as part of normal practice:

```bash
make unit   # tests the tool's own logic (grading, comparison, CLI, ...)
make check  # tests the exercise banks (every reference solution must score 100%)
make test   # both, one after the other
```

`make unit` runs the `tests/` suite with stdlib `unittest` — no extra
dependency needed. It exercises things like the type-strict `deep_eq`
comparison, import detection, and exercise-name resolution, i.e. the
tester's own code, not any particular exercise.

`make check` instead runs every exercise's own reference solution back
through the real grading sandbox — the same one your `rendu/` file runs
through — and requires each one to still score 100%, and that every
fuzzer still produces valid cases, and that no level/difficulty group is
empty. This is what actually validates the exercise pool's content, and
it's what to run after touching any bank file. With no `RANK=`, it checks
**every** rank's bank plus the training bank; `make check RANK=04` narrows
it to one rank when you're iterating on that bank alone.

The C tester has the matching pair, `make c-unit` and `make c-check` (`make
c-check` additionally compiles and runs every reference solution for
real), and `make c-test` for both together.

```bash
make test    # Python: unit + check
make c-test  # C: c-unit + c-check
```

A green `make test` (and `make c-test`) is what "this tool is working
correctly" looks like — worth running after pulling changes, or before
trusting a fresh clone.

## 3. Pick a theme, save it once

Three themes exist: `dark` (the original, default), `light` (for a
white/light terminal background), and `highcontrast` (colour-blind
friendly — swaps the usual red/green pass-fail colours for a blue/orange
palette that stays distinguishable under the common forms of colour-vision
deficiency).

Try one for a single run:

```bash
python3 -m src --theme light --list
```

If you like it, save it so every future run picks it up automatically,
without retyping `--theme` every time:

```bash
python3 -m src --theme light --save-config
```

This writes `~/.examshell/config.json`:

```json
{
  "theme": "light"
}
```

and exits immediately — no exam or practice session starts. Check it any
time:

```bash
cat ~/.examshell/config.json
```

An explicit `--theme` on the command line always overrides the saved one,
so `python3 -m src --theme dark --exam` still works for a single run even
after saving `light`.

`--save-config` also remembers `--timeout`, `--fuzz`, `--show-fails`, and
`--cc` (C tester only) the same way — useful if you always run with a
longer timeout on a slow machine, for example:

```bash
python3 -m src --timeout 8 --fuzz 20 --save-config
```

`--fuzz` itself means slightly different things per tester: the Python
tool has a hand-written fuzzer for every exercise, so `--fuzz N` always
adds N extra cases everywhere. The C tool generates fuzz values generically
from an exercise's argument types instead (no per-exercise oracle to
validate against ahead of time), so it only applies to exercises whose
arguments are all plain `int`/`char`/`str`/array values with no ordering
precondition — `make c-check`/`python3 -m c_exam --check` marks which
ones with `(+fuzz)`, and grading itself announces the real case count
either way (`"… (28 tests)"`).

## 4. Practice, then check `--stats`

Every `grademe` — in an exam, in practice, in training mode — and every
`--grade EXERCISE` quietly appends one line to `~/.examshell/stats.jsonl`.
Nothing to turn on; it just happens.

```bash
make stub EX=py_inter
$EDITOR rendu/py_inter.py
make grade EX=py_inter
```

Then:

```bash
make stats
# or: python3 -m src --stats
```

```
  Your practice history

  Total attempts : 4
     Pass rate : 75%
  Exams completed : 1
  Best exam time : 00:18:42

  Commands:
    py_inter  - 3/4 passed
```

Use this to spot which exercises actually need more reps, instead of
guessing from memory. It's purely local — nothing is uploaded anywhere.

## 5. Let an exam save itself when you `quit`

Start an exam, clear a level or two, then quit early:

```bash
make exam
...
  [alice@exam · lvl2]$ quit
```

Behind the scenes this writes `~/.examshell/saved_exam_py.json` — your
login, level, passed exercises, the exercise currently drawn, attempts,
and elapsed time. Start an exam again later and you'll be asked:

```
Resume saved exam for alice — level 2? [Y/n]:
```

Answer `y` (or just hit Enter) and you're back exactly where you left
off, including the *same* exercise for the level you were on — it isn't
redrawn. Answer `n` and the save is discarded, starting fresh.

The save is also cleared automatically the moment you finish an exam
(pass or fail all the way through), so a resume prompt never lingers
after a completed run.

## 6. Filter the exercise picker with `/text`

Open practice mode with no specific exercise:

```bash
make practice
```

```
  [1] py_bracket_validator          bracket_validator()
  [2] py_capitalizer                capitalizer()
  ...
  Selection (number, /text to filter, or 'b' to go back):
```

Type `/` followed by part of a name to narrow the list:

```
Selection (number, /text to filter, or 'b' to go back): /matrix
```

```
  [1] py_mirror_matrix               mirror_matrix()
  filter /matrix — 1/40 shown  ('/' alone clears it)
  Selection (number, /text to filter, or 'b' to go back):
```

The numbers you see always match what you type — filtering renumbers the
list, so `[1]` always means "the first thing currently on screen," never
a stale global index. Type `/` alone to clear the filter and see
everything again. Training mode's picker works the same way, alongside
its existing `e`/`m`/`h` difficulty filter.

## 7. Get stuck, get a nudge

Fail the **same** exercise three times in a row in practice or training
mode (tracked via the stats history from step 2) and the next failing
report ends with one extra line:

```bash
make practice EX=py_prime_finder
# ... grademe, wrong, grademe again, still wrong, grademe a third time ...
```

```
✖  ████████░░░░░░░░  17/36 tests passed   47%
💡 Think about the edge cases first: 0, 1 and negative numbers are never
   prime — if it's only wrong for small n, that's almost always it.
```

Two sources feed this, in order: a hand-written hint on the exercise
itself when one exists (and it can vary by *how* you failed — a crash and
a Valgrind leak on the same C exercise often call for different advice),
otherwise a generic guess from the shape of the failure alone (an
off-by-one, a sign flip, an unhandled empty input, a crash, a timeout, a
leak). The generic one is deliberately hedged ("could be…") and stays
silent rather than guess wrong when nothing matches.

It never shows up during `--exam`/`make exam` — getting unstuck without a
crutch under time pressure is exactly what the real thing tests, so
practice and training are where this builds that muscle instead of
short-circuiting it. Pass the exercise (or move to a different one) and
the streak resets.

## 8. Read your session report, collect a badge

After any exam run — passed or aborted — look at the last line printed:

```
  Session report saved to /home/alice/.examshell/reports/py_20260823_121116_alice.md
```

Open it; it's plain Markdown with your score, per-level attempts and
time, and any badges you earned:

```markdown
# Exam PASSED — alice

- Date: 2026-08-23 12:11:16
- Tester: Python (Rank 03)
- Score: 100/100
- Levels cleared: 6/6
- Total time: 00:22:10
- Total attempts: 7
- Achievements: 🏅 Flawless — no retries, 🎉 First full clear!

## Levels

| Level | Exercise | Attempts | Time |
|---|---|---|---|
| 1 | py_inter | 1 | 00:03:12 |
...
```

Badges are computed only against **your own** history in
`~/.examshell/stats.jsonl`: 🏅 *Flawless* means every level was cleared on
the very first `grademe`; 🎉 *First full clear!* means it's the first time
you've ever finished this tester's exam end to end; ⏱ *New personal best
time!* means this run beat every previous completion. They're for
motivation, not part of the score.

## 9. Know where you stand: readiness, then a drill

Once you have some history, ask what the exam could still throw at you:

```bash
make readiness             # C: make c-readiness
```

Every exercise the exam can draw is listed per level — ✔ passed at least
once, ✖ tried but never passed, · never tried — followed by a per-level
score and the level with the biggest gap. Then let the tester pick your
next session for you:

```bash
make drill                 # 5 exercises; make drill N=3 for fewer
```

It walks you through your weak spots, then exercises you've never tried,
then the ones you passed longest ago — each in practice mode, so hints and
lenient warnings still apply. Press Ctrl-C at the "Press Enter" prompt to
end the drill early.

## 10. Rehearse under real conditions

`make exam` already grades like the real exam (an `import` — or in C a
compiler warning or forbidden call — fails the level, and there is no
`new`). Add the clock for a full rehearsal:

```bash
make exam FLAGS="--time-limit 180"
```

The prompt counts down (`[alice@exam · lvl2 · 02:41:07 left]$`) and the
exam ends with a *TIME'S UP* summary when it runs out. If you'd rather warm
up without the pressure, `make exam FLAGS=--relaxed` brings back the
lenient grading and `new`.

When a failing test shows up, read its **edge case** line first — "tabs",
"empty string", "no arguments" usually tells you what to fix before you
even look at the values. For C programs the failing line is a command you
can paste straight into your shell to reproduce it.

## Everything at once

```bash
make install               # once
make test                  # confirm the tool + exercise banks are sound
python3 -m src --theme highcontrast --timeout 6 --save-config
make run                   # or straight to: make exam
# ... solve a couple of levels, then `quit` ...
make exam                 # offers to resume
make practice              # try /text filtering in the picker
# ... fail the same exercise 3x in a row for a hint ...
make stats                 # see your history so far
make readiness             # what the exam could still draw that you haven't passed
make drill                 # a short session from your gaps
make exam FLAGS="--time-limit 180"   # full rehearsal with the clock running
```
