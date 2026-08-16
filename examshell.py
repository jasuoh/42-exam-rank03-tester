#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║   EXAMSHELL  ·  42 Common Core  ·  Exam Rank 03 (Python)      ║
╚══════════════════════════════════════════════════════════════╝

A practice tester in the style of the real examshell / moulinette for the
42 Python Exam Rank 03.

  - 6 levels, in the exact order of the real exam (1 -> 6)
  - one random exercise per level, drawn from that level's pool
  - each exercise is graded against MANY tests + edge cases
  - you only move up when every test is green
  - graded in a sandbox (subprocess) with a per-test timeout (loop-proof)

Run:
    python3 examshell.py

The `rendu/` folder is created automatically. Put your solution there as
`<exercise_name>.py`, defining the required function.

UI: uses `rich` if installed (nicer panels / tables / syntax highlighting),
otherwise falls back to plain ANSI so it runs anywhere (e.g. exam machines).
    pip install rich          # optional, for the pretty UI
"""

import os
import sys
import time
import json
import random
import tempfile
import subprocess
from copy import deepcopy

from exam_bank import EXERCISES, LEVELS, N_LEVELS

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
RENDU_DIR        = "rendu"     # working directory (like the real exam)
FUZZ_PER_EX      = 30          # random extra tests per exercise
PER_TEST_TIMEOUT = 3           # seconds per test case (infinite-loop guard)
STRICT_IMPORTS   = False       # True => any `import` in the rendu fails grading

# ══════════════════════════════════════════════════════════════
#  RICH (optional) + PLAIN FALLBACK
# ══════════════════════════════════════════════════════════════
try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.align import Align
    from rich.rule import Rule
    from rich import box
    RICH = True
    console = Console()
except Exception:                                  # pragma: no cover
    RICH = False
    console = None


class Ansi:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; MAGENTA = "\033[95m"; CYAN = "\033[96m"
    WHITE = "\033[97m"; GRAY = "\033[90m"
    BG_RED = "\033[41m"; BG_GREEN = "\033[42m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ══════════════════════════════════════════════════════════════
#  BUILD TESTS  (curated cases + fuzz, expected from the oracle)
# ══════════════════════════════════════════════════════════════
def build_tests(ex_name, rng):
    ex = EXERCISES[ex_name]
    oracle = ex["oracle"]
    tests, seen = [], set()

    def add(args):
        key = repr(args)
        if key in seen:
            return
        seen.add(key)
        tests.append((args, oracle(*deepcopy(args))))

    for args in ex["cases"]:
        add(args)
    for _ in range(FUZZ_PER_EX):
        try:
            add(ex["fuzz"](rng))
        except Exception:
            pass
    return tests


# ══════════════════════════════════════════════════════════════
#  SANDBOX RUNNER (subprocess, per-test SIGALRM timeout)
# ══════════════════════════════════════════════════════════════
_RUNNER = r'''
import sys, json, importlib.util, signal

path, func_name, cases_file = sys.argv[1], sys.argv[2], sys.argv[3]

class _TO(Exception): pass
def _alarm(s, f): raise _TO()
try:
    signal.signal(signal.SIGALRM, _alarm)
    HAVE_ALARM = True
except Exception:
    HAVE_ALARM = False

spec = importlib.util.spec_from_file_location("submission", path)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception as e:
    print(json.dumps({"fatal": "IMPORT_ERROR", "msg": type(e).__name__ + ": " + str(e)}))
    sys.exit(0)

if not hasattr(mod, func_name):
    print(json.dumps({"fatal": "NO_FUNCTION", "msg": func_name}))
    sys.exit(0)
func = getattr(mod, func_name)

with open(cases_file) as fh:
    cases = json.load(fh)

results = []
for args, expected in cases:
    if HAVE_ALARM:
        signal.alarm({TIMEOUT})
    try:
        got = func(*args)
        if HAVE_ALARM:
            signal.alarm(0)
        ok = (got == expected) and (isinstance(got, bool) == isinstance(expected, bool))
        results.append({"ok": bool(ok), "got": repr(got)[:140]})
    except _TO:
        results.append({"ok": False, "got": "[TIMEOUT >%ds]" % {TIMEOUT}})
    except Exception as e:
        if HAVE_ALARM:
            signal.alarm(0)
        results.append({"ok": False, "got": "[ERROR] " + type(e).__name__ + ": " + str(e)[:90]})

print(json.dumps({"results": results}))
'''


def run_submission(filepath, func_name, tests):
    runner_src = _RUNNER.replace("{TIMEOUT}", str(PER_TEST_TIMEOUT))
    payload = [[list(args), expected] for args, expected in tests]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as cf:
        json.dump(payload, cf)
        cases_file = cf.name
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as rf:
        rf.write(runner_src)
        runner_file = rf.name
    try:
        proc = subprocess.run(
            [sys.executable, runner_file, filepath, func_name, cases_file],
            capture_output=True, text=True,
            timeout=PER_TEST_TIMEOUT * len(tests) + 10,
        )
    except subprocess.TimeoutExpired:
        return {"fatal": "GLOBAL_TIMEOUT", "msg": "Global timeout (infinite loop?)"}
    finally:
        for path in (cases_file, runner_file):
            try:
                os.remove(path)
            except OSError:
                pass

    out = proc.stdout.strip().splitlines()
    if not out:
        return {"fatal": "NO_OUTPUT", "msg": proc.stderr.strip()[:200] or "no output"}
    try:
        return json.loads(out[-1])
    except json.JSONDecodeError:
        return {"fatal": "BAD_OUTPUT", "msg": proc.stderr.strip()[:200] or out[-1][:200]}


def check_imports(filepath):
    try:
        src = open(filepath, encoding="utf-8").read()
    except OSError:
        return []
    bad = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            bad.append((i, s))
    return bad


_FATAL_MSG = {
    "IMPORT_ERROR": "File cannot be imported (syntax error?)",
    "NO_FUNCTION": "required function not found",
    "GLOBAL_TIMEOUT": "global timeout (likely an infinite loop)",
    "NO_OUTPUT": "runner produced no output",
    "BAD_OUTPUT": "runner output unreadable",
}


# ══════════════════════════════════════════════════════════════
#  GRADER
# ══════════════════════════════════════════════════════════════
def grade(ex_name, rng, show_fails=4):
    ex = EXERCISES[ex_name]
    filepath = os.path.join(RENDU_DIR, ex_name + ".py")

    if not os.path.isfile(filepath):
        _grade_error("File not found",
                     f"Create your solution at {RENDU_DIR}/{ex_name}.py")
        return False

    imports = check_imports(filepath)
    if imports:
        msg = ", ".join(s for _, s in imports[:3])
        if STRICT_IMPORTS:
            _grade_error("Forbidden import (Allowed functions: None)", msg)
            return False
        _warn(f"import found (forbidden in the real exam): {msg}")

    tests = build_tests(ex_name, rng)
    res = _run_with_status(ex_name, filepath, ex["function"], tests)

    if "fatal" in res:
        _grade_error(_FATAL_MSG.get(res["fatal"], res["fatal"]), res.get("msg", ""))
        return False

    results = res["results"]
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    fails = [(args, exp, r["got"])
             for (args, exp), r in zip(tests, results) if not r["ok"]]
    _render_grade(ex, passed, total, fails, show_fails)
    return passed == total


def _run_with_status(ex_name, filepath, func_name, tests):
    if RICH:
        with console.status(
            f"[cyan]Grading [bold]{ex_name}[/bold] "
            f"([yellow]{len(tests)}[/yellow] tests)…", spinner="dots"):
            return run_submission(filepath, func_name, tests)
    print(Ansi.CYAN + f"  Grading {ex_name} ... ({len(tests)} tests)" + Ansi.RESET)
    return run_submission(filepath, func_name, tests)


def _render_grade(ex, passed, total, fails, show_fails):
    fn = ex["function"]
    if RICH:
        if fails:
            t = Table(box=box.SIMPLE_HEAVY, show_edge=False, pad_edge=False,
                      header_style="bold red")
            t.add_column("failing call", style="white", max_width=48)
            t.add_column("expected", style="green")
            t.add_column("got", style="red")
            for args, exp, got in fails[:show_fails]:
                call = f"{fn}({', '.join(repr(a) for a in args)})"
                t.add_row(call[:48], repr(exp)[:36], str(got)[:36])
            console.print(t)
            if len(fails) > show_fails:
                console.print(f"[dim]   … and {len(fails) - show_fails} more "
                              f"failing tests[/dim]")
        ratio = f"{passed}/{total}"
        if passed == total:
            console.print(Panel(Align.center(
                Text(f"OK   {ratio} tests passed", style="bold white")),
                style="on green", box=box.HEAVY, padding=(0, 2)))
        else:
            console.print(Panel(Align.center(
                Text(f"KO   {ratio} tests passed", style="bold white")),
                style="on red", box=box.HEAVY, padding=(0, 2)))
        return

    # plain fallback
    for args, exp, got in fails[:show_fails]:
        call = f"{fn}({', '.join(repr(a) for a in args)})"
        print(Ansi.RED + f"    [KO] {call[:90]}" + Ansi.RESET)
        print(Ansi.GRAY + f"          expected : {exp!r}" + Ansi.RESET)
        print(Ansi.GRAY + f"          got      : {got}" + Ansi.RESET)
    if len(fails) > show_fails:
        print(Ansi.GRAY + f"       ... and {len(fails) - show_fails} more" + Ansi.RESET)
    print()
    banner_txt = f"  {'OK' if passed == total else 'KO'}  {passed}/{total} tests passed  "
    bg = Ansi.BG_GREEN if passed == total else Ansi.BG_RED
    print(bg + Ansi.WHITE + Ansi.BOLD + banner_txt + Ansi.RESET)


def _grade_error(title, detail=""):
    if RICH:
        body = Text(title, style="bold red")
        if detail:
            body.append("\n" + detail, style="dim")
        console.print(Panel(body, title="[red]KO", border_style="red",
                            box=box.ROUNDED, padding=(0, 2)))
    else:
        print(Ansi.RED + f"  [KO] {title}" + Ansi.RESET)
        if detail:
            print(Ansi.GRAY + f"       {detail}" + Ansi.RESET)


def _warn(msg):
    if RICH:
        console.print(f"[yellow]  ⚠  {msg}[/yellow]")
    else:
        print(Ansi.YELLOW + f"  [!] {msg}" + Ansi.RESET)


# ══════════════════════════════════════════════════════════════
#  SESSION
# ══════════════════════════════════════════════════════════════
class Session:
    def __init__(self):
        self.login = os.environ.get("USER", "student")
        self.start_time = None
        self.level = 1
        self.current_ex = None
        self.passed = []
        self.attempts = 0
        os.makedirs(RENDU_DIR, exist_ok=True)

    def elapsed(self):
        if self.start_time is None:
            return "00:00:00"
        s = int(time.time() - self.start_time)
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

    def score(self):
        return int(len(self.passed) / N_LEVELS * 100)


# ══════════════════════════════════════════════════════════════
#  UI  ·  banner / status / subject
# ══════════════════════════════════════════════════════════════
def banner():
    if RICH:
        title = Text()
        title.append("EXAMSHELL", style="bold white")
        title.append("  ·  Exam Rank 03  ·  Common Core", style="cyan")
        sub = Text("42 School  ·  Python Edition", style="dim")
        console.print(Panel(Align.center(Text.assemble(title, "\n", sub)),
                            box=box.DOUBLE, border_style="cyan", padding=(0, 2)))
    else:
        print(Ansi.CYAN + "╔" + "═" * 60 + "╗" + Ansi.RESET)
        print(Ansi.CYAN + "║" + Ansi.RESET + Ansi.BOLD + Ansi.WHITE +
              "      EXAMSHELL  ·  Exam Rank 03  ·  Common Core           " +
              Ansi.RESET + Ansi.CYAN + " ║" + Ansi.RESET)
        print(Ansi.CYAN + "║" + Ansi.RESET + Ansi.GRAY +
              "                 42 School  ·  Python Edition               " +
              Ansi.RESET + Ansi.CYAN + "║" + Ansi.RESET)
        print(Ansi.CYAN + "╚" + "═" * 60 + "╝" + Ansi.RESET)


def status_bar(s):
    if RICH:
        grid = Table.grid(expand=True, padding=(0, 2))
        for _ in range(4):
            grid.add_column(justify="left")
        grid.add_row(
            Text.assemble(("LOGIN ", "cyan"), (s.login, "bold white")),
            Text.assemble(("LEVEL ", "cyan"),
                          (f"{min(s.level, N_LEVELS)}/{N_LEVELS}", "bold yellow")),
            Text.assemble(("TIME ", "cyan"), (s.elapsed(), "white")),
            Text.assemble(("SCORE ", "cyan"), (f"{s.score()}/100", "bold green")),
        )
        dots = Text()
        for lvl in range(1, N_LEVELS + 1):
            if lvl < s.level:
                dots.append("● ", style="green")
            elif lvl == s.level:
                dots.append("◆ ", style="bold yellow")
            else:
                dots.append("○ ", style="dim")
        console.print(Panel(Group(grid, dots), border_style="cyan", box=box.SQUARE,
                            padding=(0, 1)))
    else:
        print(Ansi.CYAN + "═" * 62 + Ansi.RESET)
        print(Ansi.CYAN + "  LOGIN: " + Ansi.WHITE + Ansi.BOLD + s.login.ljust(12) +
              Ansi.RESET + Ansi.CYAN + "LEVEL: " + Ansi.YELLOW +
              f"{min(s.level, N_LEVELS)}/{N_LEVELS}".ljust(6) + Ansi.RESET +
              Ansi.CYAN + "TIME: " +
              Ansi.WHITE + s.elapsed() + Ansi.RESET)
        print(Ansi.CYAN + "  SCORE: " + Ansi.GREEN + Ansi.BOLD +
              f"{s.score()}/100".ljust(10) + Ansi.RESET + Ansi.CYAN + "PASSED: " +
              Ansi.GREEN + f"{len(s.passed)}/{N_LEVELS}" + Ansi.RESET)
        print(Ansi.CYAN + "═" * 62 + Ansi.RESET)


def _split_subject(ex_name):
    lines = EXERCISES[ex_name]["subject"].splitlines()
    header, body, signature = [], [], None
    for line in lines:
        if line.startswith(("Assignment", "Expected", "Allowed")):
            header.append(line)
        elif set(line) == {"-"}:
            continue
        elif line.strip().startswith("def "):
            signature = line.strip()
            body.append(line)
        else:
            body.append(line)
    return header, "\n".join(body).strip("\n"), signature


def show_subject(ex_name, s=None, header_bar=True):
    ex = EXERCISES[ex_name]
    clear()
    banner()
    if s and header_bar:
        status_bar(s)
    if RICH:
        header, body, signature = _split_subject(ex_name)
        meta = Table.grid(padding=(0, 1))
        meta.add_column(style="cyan", justify="right")
        meta.add_column(style="white")
        for h in header:
            k, _, v = h.partition(":")
            meta.add_row(k.strip(), v.strip())

        prose_lines, example_lines, in_examples = [], [], False
        for line in body.splitlines():
            if line.strip().lower().startswith("example"):
                in_examples = True
            if in_examples or "->" in line or line.strip().startswith("def "):
                example_lines.append(line)
            else:
                prose_lines.append(line)

        blocks = [meta, Rule(style="grey37")]
        prose = "\n".join(l for l in prose_lines if l.strip())
        if prose:
            blocks.append(Text(prose, style="white"))
        if signature:
            blocks.append(Syntax(signature, "python", theme="monokai",
                                 background_color="default"))
        ex_txt = "\n".join(l for l in example_lines
                           if not l.strip().startswith("def "))
        if ex_txt.strip():
            blocks.append(Syntax(ex_txt, "python", theme="monokai",
                                 background_color="default", word_wrap=True))
        console.print(Panel(
            Group(*blocks),
            title=f"[bold yellow]📄 {ex_name}[/bold yellow]",
            subtitle=f"[dim]Level {ex['level']}  ·  file: "
                     f"{RENDU_DIR}/{ex_name}.py[/dim]",
            border_style="yellow", box=box.ROUNDED, padding=(1, 2)))
    else:
        print()
        print(Ansi.BOLD + Ansi.YELLOW + f"  📄 {ex_name}" + Ansi.RESET +
              Ansi.GRAY + f"   (Level {ex['level']})" + Ansi.RESET)
        print(Ansi.GRAY + "  " + "─" * 58 + Ansi.RESET)
        for line in ex["subject"].splitlines():
            if line.startswith(("Assignment", "Expected", "Allowed")):
                print(Ansi.CYAN + "  " + line + Ansi.RESET)
            elif set(line) == {"-"}:
                print(Ansi.GRAY + "  " + line[:58] + Ansi.RESET)
            elif "->" in line:
                i = line.index("->")
                print("  " + Ansi.WHITE + line[:i] + Ansi.GREEN + "->" +
                      Ansi.YELLOW + line[i + 2:] + Ansi.RESET)
            elif line.strip().startswith("def "):
                print("  " + Ansi.MAGENTA + line + Ansi.RESET)
            else:
                print("  " + line)
        print(Ansi.GRAY + "  " + "─" * 58 + Ansi.RESET)
        print(Ansi.GRAY + f"  Create file:  {RENDU_DIR}/{ex_name}.py" + Ansi.RESET)
    print()


def help_commands(practice=False):
    rows = [
        ("grademe", "test your solution (advance only at 100%)"),
        ("subject", "show the assignment again"),
    ]
    if not practice:
        rows += [("status", "show current progress"),
                 ("new", "draw a new exercise for this level")]
    rows.append(("back" if practice else "quit",
                 "return to menu" if practice else "abort the exam"))
    if RICH:
        t = Table(box=box.MINIMAL, show_header=False, pad_edge=False)
        t.add_column(style="bold cyan", no_wrap=True)
        t.add_column(style="dim")
        for c, d in rows:
            t.add_row(c, d)
        console.print(t)
    else:
        print(Ansi.CYAN + "  Commands:" + Ansi.RESET)
        for c, d in rows:
            print(Ansi.GRAY + f"    {c:<8}- {d}" + Ansi.RESET)


def prompt(label):
    if RICH:
        return console.input(f"[bold cyan]{label}[/bold cyan]").strip()
    return input(Ansi.BOLD + Ansi.CYAN + label + Ansi.RESET).strip()


# ══════════════════════════════════════════════════════════════
#  EXAM MODE
# ══════════════════════════════════════════════════════════════
def exam_mode(seed=None):
    rng = random.Random(seed)
    s = Session()
    clear(); banner(); print()
    login = prompt("  Login (Enter = default): ")
    if login:
        s.login = login
    s.start_time = time.time()

    while s.level <= N_LEVELS:
        pool = LEVELS[s.level]
        s.current_ex = rng.choice(pool)
        show_subject(s.current_ex, s)
        help_commands()

        solved = False
        while not solved:
            try:
                cmd = prompt(f"\n  [{s.login}@exam · lvl{s.level}]$ ").lower()
            except (EOFError, KeyboardInterrupt):
                print(); cmd = "quit"

            if cmd in ("grademe", "g"):
                s.attempts += 1
                if grade(s.current_ex, rng):
                    s.passed.append(s.current_ex)
                    _level_cleared(s)
                    s.level += 1
                    solved = True
                else:
                    _info("Fix your solution and type 'grademe' again.")
            elif cmd in ("subject", "s"):
                show_subject(s.current_ex, s); help_commands()
            elif cmd == "status":
                print(); status_bar(s)
            elif cmd == "new":
                s.current_ex = rng.choice(pool)
                _info("New exercise drawn.")
                show_subject(s.current_ex, s); help_commands()
            elif cmd in ("quit", "q", "exit"):
                _info("Exam aborted.", style="red"); return
            elif cmd == "":
                continue
            else:
                _info("Unknown command: grademe · subject · status · new · quit")

    _exam_complete(s)


def _level_cleared(s):
    if RICH:
        console.print(Panel(Align.center(
            Text(f"✔  Level {s.level} cleared!", style="bold green")),
            border_style="green", box=box.ROUNDED))
        console.input("[dim]  Press Enter for the next level…[/dim]")
    else:
        print(Ansi.GREEN + Ansi.BOLD + f"\n  ✔ Level {s.level} cleared!  " +
              Ansi.RESET + Ansi.GRAY + "Press Enter for next level…" + Ansi.RESET)
        input()


def _exam_complete(s):
    clear(); banner(); status_bar(s); print()
    if RICH:
        t = Table.grid(padding=(0, 2))
        t.add_column(style="cyan", justify="right")
        t.add_column(style="bold white")
        t.add_row("Total time", s.elapsed())
        t.add_row("Attempts", str(s.attempts))
        t.add_row("Score", f"{s.score()}/100")
        console.print(Panel(
            Group(Align.center(Text("🎉  EXAM PASSED — all 6 levels cleared!",
                                    style="bold white")),
                  Rule(style="green"), t),
            border_style="green", box=box.DOUBLE, padding=(1, 3)))
    else:
        print(Ansi.BG_GREEN + Ansi.WHITE + Ansi.BOLD +
              "   🎉  EXAM PASSED  —  all 6 levels cleared!   " + Ansi.RESET)
        print()
        print(Ansi.CYAN + f"  Total time : {s.elapsed()}" + Ansi.RESET)
        print(Ansi.CYAN + f"  Attempts   : {s.attempts}" + Ansi.RESET)
        print(Ansi.CYAN + f"  Score      : {s.score()}/100" + Ansi.RESET)
    print()


def _info(msg, style="yellow"):
    if RICH:
        console.print(f"[{style}]  {msg}[/{style}]")
    else:
        color = {"yellow": Ansi.YELLOW, "red": Ansi.RED}.get(style, Ansi.GRAY)
        print(color + f"  {msg}" + Ansi.RESET)


# ══════════════════════════════════════════════════════════════
#  PRACTICE MODE
# ══════════════════════════════════════════════════════════════
def practice_mode():
    rng = random.Random()
    while True:
        clear(); banner(); print()
        names = _list_exercises(numbered=True)
        choice = prompt("\n  Selection (number, or 'b' to go back): ").lower()
        if choice in ("b", "q", ""):
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(names)):
            continue
        ex_name = names[int(choice) - 1]
        show_subject(ex_name)
        help_commands(practice=True)
        while True:
            cmd = prompt(f"\n  [practice · {ex_name}]$ ").lower()
            if cmd in ("grademe", "g"):
                grade(ex_name, rng)
            elif cmd in ("subject", "s"):
                show_subject(ex_name); help_commands(practice=True)
            elif cmd in ("b", "back", "q"):
                break


def _list_exercises(numbered=False):
    names = []
    if RICH:
        t = Table(title="[bold]Exercise pool[/bold]  (1 per level in the exam)",
                  box=box.SIMPLE_HEAVY, header_style="bold cyan")
        t.add_column("#", justify="right", style="dim")
        t.add_column("Level", justify="center", style="yellow")
        t.add_column("Exercise", style="white")
        t.add_column("Function", style="green")
        for lvl in range(1, N_LEVELS + 1):
            for n in sorted(LEVELS[lvl]):
                names.append(n)
                t.add_row(str(len(names)) if numbered else "",
                          str(lvl), n, f"{EXERCISES[n]['function']}()")
        console.print(t)
    else:
        for lvl in range(1, N_LEVELS + 1):
            print(Ansi.YELLOW + f"  Level {lvl}:" + Ansi.RESET)
            for n in sorted(LEVELS[lvl]):
                names.append(n)
                idx = f"[{len(names)}] " if numbered else ""
                print(Ansi.GRAY + f"    {idx}" + Ansi.RESET + Ansi.WHITE + n +
                      Ansi.RESET + Ansi.GRAY +
                      f"   {EXERCISES[n]['function']}()" + Ansi.RESET)
    return names


def list_mode():
    clear(); banner(); print()
    _list_exercises()
    total = sum(len(v) for v in LEVELS.values())
    msg = f"  {total} exercises total · 1 per level in the exam · {N_LEVELS} levels"
    if RICH:
        console.print(f"[cyan]{msg}[/cyan]")
        console.input("[dim]\n  Press Enter to go back…[/dim]")
    else:
        print(Ansi.CYAN + msg + Ansi.RESET)
        input(Ansi.GRAY + "\n  Press Enter to go back…" + Ansi.RESET)


# ══════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════
def main_menu():
    while True:
        clear(); banner(); print()
        if RICH:
            t = Table(box=box.MINIMAL, show_header=False, pad_edge=False)
            t.add_column(style="bold white", no_wrap=True)
            t.add_column()
            t.add_row("[1]", "Start exam        [dim](6 levels, real exam flow)[/dim]")
            t.add_row("[2]", "Practice mode     [dim](drill a single exercise)[/dim]")
            t.add_row("[3]", "List all exercises")
            t.add_row("[q]", "Quit")
            console.print(t)
        else:
            print(Ansi.WHITE + "  [1] " + Ansi.RESET + "Start exam " +
                  Ansi.GRAY + "(6 levels, real exam flow)" + Ansi.RESET)
            print(Ansi.WHITE + "  [2] " + Ansi.RESET + "Practice mode " +
                  Ansi.GRAY + "(drill a single exercise)" + Ansi.RESET)
            print(Ansi.WHITE + "  [3] " + Ansi.RESET + "List all exercises")
            print(Ansi.WHITE + "  [q] " + Ansi.RESET + "Quit")
        choice = prompt("\n  Selection: ").lower()
        if choice == "1":
            exam_mode()
            _pause_to_menu()
        elif choice == "2":
            practice_mode()
        elif choice == "3":
            list_mode()
        elif choice in ("q", "quit", "exit"):
            if RICH:
                console.print("\n[cyan]  Good luck on the real exam! 🍀[/cyan]\n")
            else:
                print(Ansi.CYAN + "\n  Good luck on the real exam! 🍀\n" + Ansi.RESET)
            return


def _pause_to_menu():
    if RICH:
        console.input("[dim]\n  Press Enter for the main menu…[/dim]")
    else:
        input(Ansi.GRAY + "\n  Press Enter for the main menu…" + Ansi.RESET)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        if RICH:
            console.print("\n\n[cyan]  See you! 🍀[/cyan]\n")
        else:
            print(Ansi.CYAN + "\n\n  See you! 🍀\n" + Ansi.RESET)