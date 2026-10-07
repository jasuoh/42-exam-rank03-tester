#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mutation-test the exercise banks: does every bank actually test its own
subject?

Each reference solution (oracle) is changed in one small place at a time —
a comparison flipped (`<` -> `<=`), a small constant moved by one, `and`
swapped for `or`, a `not` dropped — and the mutant is graded against the
bank's own tests, exactly like a submission. A mutant the tests don't
reject behaves like a plausible student bug that would pass:

    make mutate                    # both testers
    make mutate MUT=py ONLY=py_three_sum,py_inter
    python3 tools/mutate.py --lang c --show-unproven

A surviving mutant is only reported as a GAP when the bank's own fuzzer,
drawn many more times, finds an input where it disagrees with the oracle —
so every gap comes with an input that is inside the subject. Survivors
without such an input are either equivalent (no input can tell them
apart) or belong to an exercise without a fuzzer; --show-unproven lists
them for a look by hand.

Exit code 1 when a gap was found. Needs a C compiler for the C banks.
"""

from __future__ import annotations

import argparse
import ast
import copy
import os
import random
import re
import shutil
import signal
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from c_exam import bank as c_bank  # noqa: E402
from c_exam import grader as c_grader  # noqa: E402
from c_exam import training_bank as c_training  # noqa: E402
from examshell import grader as py_grader  # noqa: E402
from examshell import ranks  # noqa: E402
from examshell._types import Exercise  # noqa: E402

CALL_TIMEOUT = 0.5  # seconds per in-process Python call
PY_HEAVY_FUZZ = 3000  # extra fuzz draws to prove a Python survivor
C_HEAVY_FUZZ = 200  # extra fuzz cases to prove a C survivor


class Mutant(object):
    """One changed copy of an oracle's source."""

    def __init__(self, line: int, change: str, source: str) -> None:
        self.line, self.change, self.source = line, change, source

    def line_text(self) -> str:
        lines = self.source.splitlines()
        return lines[self.line - 1].strip() if self.line <= len(lines) else ""


class Result(object):
    """What happened to one surviving mutant."""

    def __init__(self, exercise: str, mutant: Mutant) -> None:
        self.exercise, self.mutant = exercise, mutant
        self.proof: Optional[str] = None  # the input that tells it apart


# ══════════════════════════════════════════════════════════════
#  PYTHON  ·  AST mutations, graded in-process
# ══════════════════════════════════════════════════════════════
_CMP_SWAP: Dict[type, Callable[[], ast.cmpop]] = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}


class _Mutator(ast.NodeTransformer):
    """Counts mutation sites in visiting order; changes site `target`."""

    def __init__(self, target: int) -> None:
        self.target, self.seen = target, 0
        self.change, self.line = "", 0

    def _hit(self, node: ast.AST, change: str) -> bool:
        hit = self.seen == self.target
        self.seen += 1
        if hit:
            self.change, self.line = change, getattr(node, "lineno", 0)
        return hit

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            swap = _CMP_SWAP.get(type(op))
            if swap is not None and self._hit(node, "comparison"):
                node.ops[i] = swap()
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if type(value) is int and abs(value) <= 10:
            for delta in (1, -1):
                if self._hit(node, "%d -> %d" % (value, value + delta)):
                    return ast.copy_location(ast.Constant(value + delta), node)
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        if self._hit(node, "and <-> or"):
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Not) and self._hit(node, "drop `not`"):
            return node.operand
        return node


def python_mutants(source: str) -> Iterator[Mutant]:
    counter = _Mutator(-1)
    counter.visit(ast.parse(source))
    for target in range(counter.seen):
        mutator = _Mutator(target)
        tree = ast.fix_missing_locations(mutator.visit(ast.parse(source)))
        yield Mutant(mutator.line, mutator.change, ast.unparse(tree))


class _Timeout(Exception):
    pass


def _on_alarm(signum: int, frame: object) -> None:
    raise _Timeout()


def _call(func: Callable[..., Any], args: List[Any]) -> Tuple[str, Any]:
    """("ok", value) / ("timeout", None) / ("raise", exception name)."""
    signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT)
    try:
        return "ok", func(*copy.deepcopy(args))
    except _Timeout:
        return "timeout", None
    except Exception as exc:
        return "raise", type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _python_survives(
    funcs: Dict[str, Callable[..., Any]],
    plan: List[Tuple[str, List[py_grader.Test]]],
) -> bool:
    for function, tests in plan:
        for args, expected in tests:
            status, got = _call(funcs[function], args)
            if status != "ok" or not py_grader.deep_eq(got, expected):
                return False
    return True


def _python_proof(
    ex: Exercise,
    funcs: Dict[str, Callable[..., Any]],
    oracles: Dict[str, Callable[..., Any]],
) -> Optional[str]:
    rng = random.Random(1)
    for part in py_grader.parts_of(ex):
        function = part["function"]
        for _ in range(PY_HEAVY_FUZZ):
            args = part["fuzz"](rng)
            status, expected = _call(oracles[function], args)
            if status != "ok":
                continue  # outside what the oracle handles: not a proof
            got = _call(funcs[function], args)
            if got[0] != "ok" or not py_grader.deep_eq(got[1], expected):
                shown = got[1] if got[0] == "ok" else "[%s]" % got[0]
                return "%s(%s) -> expected %r, mutant %r" % (
                    function,
                    ", ".join(repr(a) for a in args),
                    expected,
                    shown,
                )
    return None


def _load(source: str) -> Dict[str, Any]:
    namespace: Dict[str, Any] = {}
    exec(compile(source, "<mutant>", "exec"), namespace)
    return namespace


def run_python(names: Optional[List[str]]) -> Tuple[int, List[Result]]:
    signal.signal(signal.SIGALRM, _on_alarm)
    pool: Dict[str, Exercise] = {}
    for rank_id in ranks.CHOICES:
        pool.update(ranks.get(rank_id).all_exercises())
    total, survivors = 0, []
    for name in sorted(pool):
        if names and name not in names:
            continue
        ex = pool[name]
        source = py_grader.oracle_source(ex)
        oracles = _load(source)
        plan = py_grader.build_plan(
            name, ex, random.Random(0), py_grader.DEFAULT_FUZZ
        )
        for mutant in python_mutants(source):
            total += 1
            try:
                funcs = _load(mutant.source)
            except Exception:
                continue  # a mutant that doesn't even load is caught
            if not _python_survives(funcs, plan):
                continue
            result = Result(name, mutant)
            result.proof = _python_proof(ex, funcs, oracles)
            survivors.append(result)
    return total, survivors


# ══════════════════════════════════════════════════════════════
#  C  ·  source mutations, graded through c_exam's real grader
# ══════════════════════════════════════════════════════════════
_C_OPS = (
    (r"<=", "<"),
    (r"(?<![<-])<(?![<=])", "<="),
    (r">=", ">"),
    (r"(?<![->])>(?![>=])", ">="),
    (r"==", "!="),
    (r"!=", "=="),
    (r"&&", "||"),
    (r"\|\|", "&&"),
)
_C_LITERAL_RE = re.compile(r"\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'")
_C_DIGIT_RE = re.compile(r"(?<![\w.])(\d)(?![\w.])")


def c_mutants(source: str) -> Iterator[Mutant]:
    lines = source.split("\n")
    for index, line in enumerate(lines):
        if line.strip().startswith("#"):
            continue  # preprocessor: #include <x.h> is no comparison
        # mask string/char literals so their contents are never mutated
        code = _C_LITERAL_RE.sub(lambda m: "\0" * len(m.group()), line)
        changes: List[Tuple[int, int, str, str]] = []
        for pattern, replacement in _C_OPS:
            for m in re.finditer(pattern, code):
                changes.append((m.start(), m.end(), replacement, m.group()))
        for m in _C_DIGIT_RE.finditer(code):
            value = int(m.group(1))
            for new in (value + 1, value - 1):
                if new >= 0:
                    changes.append((m.start(), m.end(), str(new), m.group()))
        for start, end, replacement, original in changes:
            mutated = line[:start] + replacement + line[end:]
            after = index + 1
            yield Mutant(
                after,
                "%s -> %s" % (original, replacement),
                "\n".join(lines[:index] + [mutated] + lines[after:]),
            )


def _c_grade(
    name: str, ex: Exercise, source: str, fuzz: int, seed: int
) -> py_grader.Report:
    workdir = tempfile.mkdtemp(prefix="examshell-mutate-")
    try:
        path = os.path.join(workdir, name + ".c")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(source)
        header = c_grader.header_filename(ex)
        if header:
            with open(
                os.path.join(workdir, header), "w", encoding="utf-8"
            ) as fh:
                fh.write(c_grader.header_content(header))
        return c_grader.grade(
            name,
            ex,
            workdir,
            filepath=path,
            rng=random.Random(seed),
            fuzz=fuzz,
            timeout=2,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _c_exercise(item: Tuple[str, Exercise]) -> Tuple[int, List[Result]]:
    name, ex = item
    total, survivors = 0, []
    for mutant in c_mutants(ex["oracle_c"]):
        total += 1
        report = _c_grade(name, ex, mutant.source, c_grader.DEFAULT_FUZZ, 0)
        if not report.ok:
            continue
        result = Result(name, mutant)
        if c_grader.is_fuzzable(ex):
            heavy = _c_grade(name, ex, mutant.source, C_HEAVY_FUZZ, 1)
            if not heavy.ok and not heavy.fatal:
                failure = heavy.failures[0]
                result.proof = "%s -> expected %r, mutant %r" % (
                    failure.call(ex["function"]),
                    failure.expected,
                    failure.got,
                )
        survivors.append(result)
    return total, survivors


def run_c(names: Optional[List[str]], jobs: int) -> Tuple[int, List[Result]]:
    pool: Dict[str, Exercise] = dict(c_training.TRAINING_EXERCISES)
    pool.update(c_bank.EXERCISES)
    items = sorted(
        (name, ex) for name, ex in pool.items() if not names or name in names
    )
    total, survivors = 0, []
    with ThreadPoolExecutor(jobs) as executor:
        for count, found in executor.map(_c_exercise, items):
            total += count
            survivors += found
    return total, survivors


# ══════════════════════════════════════════════════════════════
#  REPORT
# ══════════════════════════════════════════════════════════════
def report(
    label: str, total: int, survivors: List[Result], show_unproven: bool
) -> int:
    gaps = [r for r in survivors if r.proof]
    unproven = [r for r in survivors if not r.proof]
    print(
        "%s: %d mutants · %d survived the bank's tests · %d proven gap%s"
        % (
            label,
            total,
            len(survivors),
            len(gaps),
            "" if len(gaps) == 1 else "s",
        )
    )
    for r in gaps:
        print(
            "  GAP  %-28s line %-3d %-14s %s"
            % (
                r.exercise,
                r.mutant.line,
                r.mutant.change,
                r.mutant.line_text()[:60],
            )
        )
        print("       %s" % (r.proof or "")[:300])
    if show_unproven and unproven:
        print("  unproven (equivalent, or no fuzzer — check by hand):")
        for r in unproven:
            print(
                "       %-28s line %-3d %-14s %s"
                % (
                    r.exercise,
                    r.mutant.line,
                    r.mutant.change,
                    r.mutant.line_text()[:60],
                )
            )
    return len(gaps)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools/mutate.py",
        description="Find what the exercise banks fail to test.",
    )
    parser.add_argument("--lang", choices=("py", "c", "all"), default="all")
    parser.add_argument(
        "--only", help="comma-separated exercise names (default: all)"
    )
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 4, help="C workers"
    )
    parser.add_argument(
        "--show-unproven",
        action="store_true",
        help="also list survivors without a proving input",
    )
    args = parser.parse_args(argv)
    names = args.only.split(",") if args.only else None
    gaps = 0
    if args.lang in ("py", "all"):
        total, survivors = run_python(names)
        gaps += report("Python", total, survivors, args.show_unproven)
    if args.lang in ("c", "all"):
        if not shutil.which("cc"):
            print("C: skipped — no `cc` on PATH")
        else:
            total, survivors = run_c(names, max(1, args.jobs))
            gaps += report("C", total, survivors, args.show_unproven)
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
