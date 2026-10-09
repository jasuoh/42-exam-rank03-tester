<div align="center">

# ⌨️ ExamShell

### Practice for the 42 Common Core exams

**C · Exam Rank 02** &nbsp;·&nbsp; **Python · Exam Ranks 03 · 04 · 05**

[![CI](https://github.com/jasuoh/42-exam-tester/actions/workflows/ci.yml/badge.svg)](https://github.com/jasuoh/42-exam-tester/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)
![Visitors](https://komarev.com/ghpvc/?username=jasuoh&repo=42-exam-rank03-tester&label=Views&color=blueviolet&style=flat)

</div>

A random exercise per level, your editor next to it, `grademe` — and you
only move on at **100 %**, graded as strictly as the real exam and on far
more edge cases than you'd think to test yourself.

> **A practice tool, nothing more.** None of this exists in the real exam.
> It helps you train; it doesn't replace learning to solve the exercises.

<p align="center">
  <img src="docs/img/tui-practice.svg" alt="ExamShell next to your editor: the subject on top, a failing first_word below — one line per failing test, with the edge case it covers" width="760">
</p>

## Start

```bash
git clone https://github.com/jasuoh/42-exam-tester && cd 42-exam-tester
make
```

You need git, make and, for the C exam, a C compiler — `make doctor` checks.
The first `make` installs everything else with
[uv](https://docs.astral.sh/uv/) (and uv itself into `~/.local/bin` if it
isn't there yet — no sudo), then opens the app and asks which exam you're
practising for. From then on `make` starts it, on the exam you picked last.

Keep the terminal next to your editor: you write in `rendu/` (Python) or
`c_rendu/` (C), the app grades.

| | |
|---|---|
| `make update` | get the newest version |
| `make doctor` | is this machine ready? (Python, compiler, sync …) |

## In the app

**Exam** — the real thing: levels in order, one random exercise each, 100 %
to move on, no redraws. `grademe` answers **SUCCESS** or **FAILURE** with a
trace of the first failing test, like the real exam. Failed? Same exercise
until it passes. Quit any time — the next start offers to resume.

<p align="center">
  <img src="docs/img/tui-exam.svg" alt="The exam: level 1 of 4, a FAILURE with the first failing test as a trace" width="760">
</p>

**Practice** — any exercise, full feedback. Three tabs: the exercises the
exam can draw, **My gaps** (what you failed, never tried or passed longest
ago) and **Extra** (LeetCode-style training, never in the exam). The first
three failing tests show up one line each; `d` shows everything. After a few
fails in a row you get a hint.

**Progress** — every exercise the exam can draw, level by level: passed,
failed, never tried. `p` practises your gaps.

**Switch exam** — C Rank 02 or Python Rank 03 / 04 / 05. Remembered for
next time.

| Key | Where | |
|---|---|---|
| `g` | exam · practice | grademe |
| `e` | exam · practice | open your solution in VS Code (or `$EDITOR`) — a stub first if there's none |
| `t` | exam · practice | write a stub |
| `d` | practice | all the details of the last grade |
| `f` | menu · practice | report an exercise that differs from your real exam |
| `o` | menu | settings: exam time limit, time per test, C compiler, sync |
| `s` | menu | sync with your other device |
| `esc` | exam | quit & save (elsewhere: back) |
| `?` | everywhere | all the keys |

## Continue on another device

Progress, a paused exam and your solutions can travel through your own
**private** git repo — school in the morning, laptop at night. Add the repo
once in **Settings** (`o`), then `s` syncs. Step by step:
[🇬🇧 docs/sync.md](docs/sync.md) · [🇩🇪 docs/sync.de.md](docs/sync.de.md)

## More

| | |
|---|---|
| [C tester](docs/c.md) · [Python tester](docs/python.md) | the exercise pools, how grading works, the command line |
| [Features](docs/features.md) | everything the app does, in detail |
| [Development](docs/development.md) | tests, code layout, releases — `make dev` lists the commands |
| [Changelog](CHANGELOG.md) · [Roadmap](PLAN.md) | what changed, what's next |

## Does it match your exam?

Exercise pools differ between campuses and change over time. If something
differs from your real exam, press `f` in the app (or
[open an issue](https://github.com/jasuoh/42-exam-tester/issues/new/choose)) —
the form is filled in for you, nothing is sent until you submit it.

## License

[MIT](LICENSE)

<div align="center">

*Solve it, don't memorise it. Good luck on the real exam.*

</div>
