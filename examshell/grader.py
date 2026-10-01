#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grader.py  ·  sandboxed grading engine for ExamShell

The student's file is never imported into this process. It is executed by a
throw-away runner script in a subprocess that

  * has its own clean sys.path (it cannot import exam_bank and peek),
  * gets /dev/null on stdin (input() raises instead of hanging forever),
  * arms SIGALRM around every single call (infinite-loop proof),
  * bails out early after repeated timeouts instead of grinding through
    40 cases at `timeout` seconds each,
  * writes its verdict to a result FILE, so anything the submission prints
    can never corrupt the protocol,
  * compares type-strictly (True != 1, tuple != list), recursively.

Cases travel to that subprocess as JSON, which on its own flattens a tuple
into a list and stringifies a non-string dict key — both fatal for a
type-strict comparison, and both needed by the Rank 04/05 banks (tuples of
coordinates, adjacency dicts keyed by int). encode_value()/decode_value()
below wrap those two shapes in a tagged form so they survive the trip
unchanged; everything else passes through as plain JSON.
"""

import copy
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

DEFAULT_TIMEOUT = 3        # seconds per test case
DEFAULT_FUZZ = 30          # random extra tests per exercise
MAX_TIMEOUTS = 3           # consecutive timeouts before we give up


class BankError(Exception):
    """The exercise bank itself is inconsistent (an oracle blew up)."""


def _free_globals(func, allow=()):
    """Module-level names `func` depends on, other than the names in `allow`.

    A function with free globals cannot be lifted out of this module and
    spliced into the standalone sandbox runner (or an oracle-only file) — it
    would silently break the moment it runs somewhere without that global.
    """
    try:
        names = set(inspect.getclosurevars(func).globals)
    except (TypeError, ValueError):                        # pragma: no cover
        return []
    return sorted(names - set(allow))


# ══════════════════════════════════════════════════════════════
#  SANDBOX RUNNER HELPERS  (real functions here, unit-testable — the exact
#  same source text is spliced into the subprocess runner below, so there
#  is only ever one implementation of the comparison logic.)
# ══════════════════════════════════════════════════════════════
def deep_eq(a, b):
    """Type-strict, recursive equality: True is not 1, (1,) is not [1]."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(deep_eq(x, y) for x, y in zip(a, b))
    # Tuples need their own branch for the same reason lists do: the
    # fallback below would fall through to `a == b`, and Python's tuple
    # equality is not type-strict about what's inside ((1,) == (True,)).
    # A tuple/list mismatch still lands on the type check below.
    if isinstance(a, tuple) and isinstance(b, tuple):
        return len(a) == len(b) and all(deep_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(deep_eq(a[k], b[k]) for k in a)
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b
    if type(a) is not type(b):
        return False
    return a == b


def short_repr(value, limit=150):
    """A repr() capped at `limit` characters. Never raises."""
    try:
        text = repr(value)
    except Exception:
        text = "<unrepresentable object>"
    return text if len(text) <= limit else text[:limit] + "…"


def decode_value(value):
    """Rebuild what encode_value() below packed for the JSON trip.

    The "__examshell__" tag is spelled out rather than pulled from a
    module constant on purpose: this function is spliced verbatim into the
    sandbox runner, where no such constant exists.
    """
    if isinstance(value, list):
        return [decode_value(item) for item in value]
    if isinstance(value, dict):
        kind = value.get("__examshell__")
        if kind == "tuple":
            return tuple(decode_value(item) for item in value["items"])
        if kind == "dict":
            return {decode_value(k): decode_value(v) for k, v in value["items"]}
        return {k: decode_value(v) for k, v in value.items()}
    return value


for _helper in (deep_eq, short_repr, decode_value):
    _extra = _free_globals(_helper, allow=(_helper.__name__,))
    if _extra:                                             # pragma: no cover
        raise AssertionError("grader.%s must be self-contained, found: %s"
                             % (_helper.__name__, _extra))
_RUNNER_HELPERS_SRC = "\n\n".join(
    inspect.getsource(h) for h in (deep_eq, short_repr, decode_value))
del _helper, _extra


def encode_value(value):
    """`value` in a form json can round-trip without losing its types.

    Plain JSON silently turns a tuple into a list and a non-string dict key
    into a string — invisible until deep_eq() rejects a correct answer for
    the wrong reason. Tuples and dicts are therefore tagged; everything
    else (numbers, strings, bools, None, lists) is left exactly as it is,
    so a bank that uses none of them produces byte-identical cases.json to
    before this existed. Parent-process only — the sandbox just decodes.
    """
    if isinstance(value, tuple):
        return {"__examshell__": "tuple",
                "items": [encode_value(item) for item in value]}
    if isinstance(value, list):
        return [encode_value(item) for item in value]
    if isinstance(value, dict):
        return {"__examshell__": "dict",
                "items": [[encode_value(k), encode_value(v)]
                          for k, v in value.items()]}
    return value


def json_stable(value):
    """True when `value` survives the trip to the sandbox unchanged — what
    selftest() checks so a bank can never ship an expected value the
    grader could not compare faithfully."""
    try:
        round_tripped = decode_value(json.loads(json.dumps(encode_value(value))))
    except (TypeError, ValueError):
        return False
    return deep_eq(round_tripped, value)


# ══════════════════════════════════════════════════════════════
#  RESULT TYPES
# ══════════════════════════════════════════════════════════════
FATAL_TITLES = {
    "FILE_MISSING":    "File not found",
    "FORBIDDEN":       "Forbidden import (Allowed functions: None)",
    "IMPORT_ERROR":    "Your file cannot be imported (syntax error?)",
    "IMPORT_TIMEOUT":  "Importing your file timed out (loop at module level?)",
    "NO_FUNCTION":     "Required function not found",
    "NOT_CALLABLE":    "That name exists but is not a function",
    "BAD_SIGNATURE":   "Wrong function signature",
    "GLOBAL_TIMEOUT":  "Global timeout (infinite loop?)",
    "NO_RESULT":       "The sandbox produced no result",
    "BAD_RESULT":      "The sandbox result was unreadable",
    # shared with c_exam/grader.py — its Report/fatal codes reuse this dict
    "COMPILE_ERROR":   "Your file does not compile",
    "FORBIDDEN_MAIN":  "You defined main() — only the required function is allowed",
    "TIMEOUT":         "Timed out (infinite loop?)",
    "BANK_ERROR":      "Internal error in the exercise bank (not your fault — please report this)",
    "VALGRIND_ERRORS": "valgrind found memory error(s) (--strict-valgrind)",
    "FORBIDDEN_CALL":  "Forbidden call found for this exercise",
}


class Failure(object):
    __slots__ = ("args", "expected", "got", "function")

    def __init__(self, args, expected, got, function=None):
        self.args, self.expected, self.got = args, expected, got
        # Which function this call was made against. None for the single-
        # function exercises that are the norm; set on a multi-function
        # one (see parts_of()) so the report says which half failed.
        self.function = function

    def call(self, function):
        return "%s(%s)" % (self.function or function,
                           ", ".join(repr(a) for a in self.args))


class Report(object):
    def __init__(self, exercise, function):
        self.exercise = exercise
        self.function = function
        self.passed = 0
        self.total = 0
        self.failures = []
        self.fatal = ""
        self.detail = ""
        self.warnings = []
        self.duration = 0.0

    @property
    def ok(self):
        return not self.fatal and self.total > 0 and self.passed == self.total

    @property
    def fatal_title(self):
        return FATAL_TITLES.get(self.fatal, self.fatal)

    def fail(self, code, detail=""):
        self.fatal, self.detail = code, detail
        return self


# ══════════════════════════════════════════════════════════════
#  TEST BUILDING
# ══════════════════════════════════════════════════════════════
def parts_of(ex):
    """The gradeable parts of an exercise, each a dict carrying its own
    "function"/"oracle"/"cases"/"fuzz".

    Almost every exercise asks for exactly one function and is its own
    single part. A few subjects ask for two (Rank 05's compress/decompress)
    — those list a "parts" key, and the exercise's own top-level keys
    mirror the first part so everything that only needs "the function this
    exercise is about" (the stub signature, the subject header, --diff's
    code panel) keeps working untouched.
    """
    return ex.get("parts") or [ex]


def build_plan(ex_name, ex, rng, fuzz=DEFAULT_FUZZ):
    """[(function, tests), …] — build_tests() once per part."""
    return [(part["function"], build_tests(ex_name, part, rng, fuzz))
            for part in parts_of(ex)]


def plan_size(plan):
    """How many test cases a plan runs in total."""
    return sum(len(tests) for _, tests in plan)


def build_tests(ex_name, ex, rng, fuzz=DEFAULT_FUZZ):
    """Curated cases + fuzz, with the expected values taken from the oracle."""
    oracle = ex["oracle"]
    tests, seen = [], set()

    def add(args, curated):
        key = repr(args)
        if key in seen:
            return
        try:
            expected = oracle(*copy.deepcopy(args))
        except Exception as exc:
            if curated:
                raise BankError("%s: oracle crashed on %r (%s: %s)"
                                % (ex_name, args, type(exc).__name__, exc)) from exc
            return
        seen.add(key)
        tests.append((list(args), expected))

    for args in ex["cases"]:
        add(args, True)
    for _ in range(fuzz):
        try:
            args = ex["fuzz"](rng)
        except Exception as exc:
            raise BankError("%s: fuzzer crashed (%s: %s)"
                            % (ex_name, type(exc).__name__, exc)) from exc
        add(args, False)
    return tests


# ══════════════════════════════════════════════════════════════
#  STATIC CHECK  ·  imports
# ══════════════════════════════════════════════════════════════
def find_imports(path):
    """Real import statements only — strings and comments do not count."""
    import ast
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError, ValueError):
        return []                      # the sandbox reports this properly
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.append((node.lineno, "import " + ", ".join(a.name for a in node.names)))
        elif isinstance(node, ast.ImportFrom):
            found.append((node.lineno, "from %s import …" % (node.module or ".")))
    return sorted(found)


# ══════════════════════════════════════════════════════════════
#  STATIC CHECK  ·  forbidden calls
# ══════════════════════════════════════════════════════════════
def find_forbidden_calls(path, forbidden_names):
    """Calls to a banned name, as either a bare identifier (`sorted(x)`) or
    an attribute (`x.sort()`) — same spirit as c_exam's find_forbidden(),
    ast-based since Python has a real parser for it. A syntax error yields
    no findings; the sandbox reports that properly."""
    if not forbidden_names:
        return []
    import ast
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, SyntaxError, ValueError):
        return []
    names = set(forbidden_names)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in names:
            found.add(func.id)
        elif isinstance(func, ast.Attribute) and func.attr in names:
            found.add(func.attr)
    return sorted(found)


# ══════════════════════════════════════════════════════════════
#  STATIC CHECK  ·  source display (--diff's inline code panel)
# ══════════════════════════════════════════════════════════════
def extract_function_source(filepath, function_name):
    """The student's own source text for one function (its `def` line
    through its full body), for --diff's inline code panel — read via
    `ast`, the same way find_imports()/find_forbidden_calls() above
    already parse the submission. When `function_name` is defined more
    than once, the LAST definition wins (matching Python's own redefinition
    semantics — that's the one that actually runs).

    Returns None on ANY failure (unreadable file, syntax error, function
    not found) rather than raising — this is a nice-to-have display, never
    something that's allowed to crash grading.
    """
    import ast
    try:
        with open(filepath, encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=filepath)
    except (OSError, SyntaxError, ValueError, UnicodeDecodeError):
        return None
    match = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == function_name:
            match = node
    if match is None:
        return None
    try:
        return ast.get_source_segment(source, match)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  SANDBOX RUNNER  (executed in the subprocess)
# ══════════════════════════════════════════════════════════════
RUNNER_TEMPLATE = r'''
import contextlib, copy, importlib.util, inspect, io, json, signal, sys, time

sub_path, func_name, cases_path, out_path = sys.argv[1:5]
timeout, max_timeouts, deadline = (int(a) for a in sys.argv[5:8])
started = time.monotonic()


class Timeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise Timeout()


try:
    signal.signal(signal.SIGALRM, _on_alarm)
    HAVE_ALARM = True
except (AttributeError, ValueError):        # Windows, or not the main thread
    HAVE_ALARM = False


def alarm(seconds):
    if HAVE_ALARM:
        signal.alarm(seconds)


def finish(payload):
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    sys.exit(0)


{{HELPERS}}


# ── import the submission (the import itself is timed too) ────────────
spec = importlib.util.spec_from_file_location("submission", sub_path)
if spec is None or spec.loader is None:
    finish({"fatal": "IMPORT_ERROR", "detail": "cannot load " + sub_path})
module = importlib.util.module_from_spec(spec)
noise = io.StringIO()
try:
    alarm(timeout)
    with contextlib.redirect_stdout(noise), contextlib.redirect_stderr(noise):
        spec.loader.exec_module(module)
    alarm(0)
except Timeout:
    finish({"fatal": "IMPORT_TIMEOUT", "detail": "no result after %ds" % timeout})
except BaseException as exc:
    alarm(0)
    finish({"fatal": "IMPORT_ERROR",
            "detail": type(exc).__name__ + ": " + str(exc)[:200]})

func = getattr(module, func_name, None)
if func is None:
    names = [n for n in vars(module) if callable(getattr(module, n, None))
             and not n.startswith("_")]
    hint = ("defined instead: " + ", ".join(sorted(names)[:5])) if names else ""
    finish({"fatal": "NO_FUNCTION", "detail": func_name + "()  " + hint})
if not callable(func):
    finish({"fatal": "NOT_CALLABLE", "detail": func_name})

with open(cases_path) as fh:
    cases = [[decode_value(args), decode_value(expected)]
             for args, expected in json.load(fh)]

try:
    signature = inspect.signature(func)
except (TypeError, ValueError):
    signature = None
if signature is not None and cases:
    try:
        signature.bind(*cases[0][0])
    except TypeError:
        finish({"fatal": "BAD_SIGNATURE",
                "detail": "%s%s cannot be called with %d argument(s)"
                          % (func_name, signature, len(cases[0][0]))})

# ── run every case ───────────────────────────────────────────────────
results, printed, mutated, streak = [], 0, False, 0
for args, expected in cases:
    if streak >= max_timeouts:
        results.append({"ok": False, "got": "[skipped after %d timeouts]" % streak})
        continue
    if time.monotonic() - started > deadline:
        results.append({"ok": False, "got": "[skipped: time budget exceeded]"})
        continue
    sent = copy.deepcopy(args)
    noise = io.StringIO()
    try:
        alarm(timeout)
        with contextlib.redirect_stdout(noise):
            got = func(*sent)
        alarm(0)
        streak = 0
    except Timeout:
        streak += 1
        results.append({"ok": False, "got": "[TIMEOUT > %ds]" % timeout})
        continue
    except BaseException as exc:
        alarm(0)
        streak = 0
        results.append({"ok": False,
                        "got": "[%s] %s" % (type(exc).__name__, str(exc)[:100])})
        continue
    printed += len(noise.getvalue())
    if sent != args:
        mutated = True
    ok = deep_eq(got, expected)
    if not ok and got is None and noise.getvalue().strip():
        results.append({"ok": False, "got": "None  (printed %s instead)"
                                            % short_repr(noise.getvalue().strip(), 40)})
        continue
    results.append({"ok": ok, "got": short_repr(got)})

finish({"results": results, "printed": printed, "mutated": mutated})
'''

RUNNER_SRC = RUNNER_TEMPLATE.replace("{{HELPERS}}", _RUNNER_HELPERS_SRC)


# ══════════════════════════════════════════════════════════════
#  SANDBOX DRIVER
# ══════════════════════════════════════════════════════════════
def run_sandbox(filepath, function, tests, timeout=DEFAULT_TIMEOUT):
    """Run `tests` against `filepath` in a subprocess; return the raw payload."""
    workdir = tempfile.mkdtemp(prefix="examshell-")
    runner = os.path.join(workdir, "runner.py")
    cases = os.path.join(workdir, "cases.json")
    result = os.path.join(workdir, "result.json")
    try:
        with open(runner, "w", encoding="utf-8") as fh:
            fh.write(RUNNER_SRC)
        with open(cases, "w", encoding="utf-8") as fh:
            json.dump([[encode_value(list(args)), encode_value(expected)]
                       for args, expected in tests], fh)

        # the runner stops grading after `deadline`; the subprocess timeout is
        # only the backstop for a runner that cannot be interrupted at all.
        deadline = timeout * (MAX_TIMEOUTS + 2) + 10
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"   # no __pycache__ in rendu/
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            subprocess.run(
                [sys.executable, runner, os.path.abspath(filepath), function,
                 cases, result, str(timeout), str(MAX_TIMEOUTS), str(deadline)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=workdir, env=env, timeout=deadline + 10,
            )
        except subprocess.TimeoutExpired:
            return {"fatal": "GLOBAL_TIMEOUT",
                    "detail": "no result after %ds" % (deadline + 10)}

        if not os.path.exists(result):
            return {"fatal": "NO_RESULT", "detail": "the sandbox died unexpectedly"}
        try:
            with open(result, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError) as exc:
            return {"fatal": "BAD_RESULT", "detail": str(exc)[:200]}
    finally:
        _rmtree(workdir)


def _rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
#  GRADE
# ══════════════════════════════════════════════════════════════
def grade(ex_name, ex, rendu_dir, rng=None, timeout=DEFAULT_TIMEOUT,
          fuzz=DEFAULT_FUZZ, strict_imports=False, filepath=None, tests=None,
          plan=None):
    """Grade one exercise and return a Report.

    Pass `plan` (from build_plan()) when you already built it, so the count
    you announced is the count you actually run; `tests` is the same thing
    for the single-function case. Otherwise a plan is built from `rng`.

    Unlike a plain `import` (only forbidden under --strict-imports, since
    it's usually still an honest attempt), a call listed in an exercise's
    own `forbidden` — e.g. `sorted`/`sort` on py_cryptic_sorter — trivialises
    exactly the thing the exercise is testing, so it always fails grading,
    no flag needed.
    """
    report = Report(ex_name, ex["function"])
    path = filepath or os.path.join(rendu_dir, ex_name + ".py")
    started = time.time()

    if not os.path.isfile(path):
        return report.fail("FILE_MISSING", "expected your solution at %s" % path)

    imports = find_imports(path)
    if imports:
        listed = ", ".join(text for _, text in imports[:3])
        if strict_imports:
            return report.fail("FORBIDDEN", listed)
        report.warnings.append("import found — forbidden in the real exam: %s" % listed)

    forbidden = find_forbidden_calls(path, ex.get("forbidden", ()))
    if forbidden:
        return report.fail("FORBIDDEN_CALL", ", ".join(forbidden))

    if plan is None:
        plan = ([(ex["function"], tests)] if tests is not None
                else build_plan(ex_name, ex, rng, fuzz))

    multi = len(plan) > 1
    mutated, printed = False, 0
    for function, tests in plan:
        payload = run_sandbox(path, function, tests, timeout)
        if "fatal" in payload:
            report.duration = time.time() - started
            detail = payload.get("detail", "")
            # With two functions to find, "Required function not found"
            # alone doesn't say which one is missing.
            if multi and detail:
                detail = "%s  (while grading %s)" % (detail, function)
            return report.fail(payload["fatal"], detail)

        results = payload.get("results", [])
        if len(results) != len(tests):
            report.duration = time.time() - started
            return report.fail("BAD_RESULT", "expected %d results, got %d"
                               % (len(tests), len(results)))

        report.total += len(tests)
        for (args, expected), outcome in zip(tests, results):
            if outcome.get("ok"):
                report.passed += 1
            else:
                report.failures.append(
                    Failure(args, expected, outcome.get("got", "?"),
                            function if multi else None))
        mutated = mutated or bool(payload.get("mutated"))
        printed += payload.get("printed", 0)

    report.duration = time.time() - started
    if mutated:
        report.warnings.append(
            "your function modified its input arguments — return a NEW value instead")
    if printed:
        report.warnings.append(
            "your function printed %d character(s) while being graded — "
            "the exam grades what you RETURN" % printed)
    return report


# ══════════════════════════════════════════════════════════════
#  BANK SELF-TEST  (make check)
# ══════════════════════════════════════════════════════════════
def oracle_source(ex):
    """Every one of the exercise's oracles, each renamed to the function
    the student must write — a standalone module that is, by definition,
    a perfect submission. One `def` for the usual single-function
    exercise, one per part for a multi-function one (see parts_of())."""
    chunks = []
    for part in parts_of(ex):
        src = inspect.getsource(part["oracle"])
        chunks.append(src.replace("def " + part["oracle"].__name__,
                                  "def " + part["function"], 1))
    return "\n\n".join(chunks)


def oracle_free_globals(ex):
    """Module-level names an oracle depends on — it must depend on none, or
    it cannot be extracted into a standalone file for the self-test."""
    names = set()
    for part in parts_of(ex):
        names.update(_free_globals(part["oracle"]))
    return sorted(names)


def selftest(exercises, groups, rng, timeout=DEFAULT_TIMEOUT,
             fuzz=DEFAULT_FUZZ, log=print):
    """Validate a whole bank (exercises grouped by level or difficulty).

    `groups` maps each group key (a level number, a difficulty name, …) to
    the list of exercise names in it — bank modules build and validate this
    at import time, so an out-of-range or empty group already raised there;
    this only re-checks it defensively. Returns the number of problems found.
    """
    problems = 0

    def bad(msg):
        nonlocal problems
        problems += 1
        log("  FAIL  " + msg)

    for group, pool in groups.items():
        if not pool:
            bad("group %r has no exercise" % (group,))

    workdir = tempfile.mkdtemp(prefix="examshell-check-")
    try:
        for name in sorted(exercises):
            ex = exercises[name]

            free = oracle_free_globals(ex)
            if free:
                bad("%s: oracle is not self-contained, it needs %s"
                    % (name, ", ".join(free)))
            for part in parts_of(ex):
                if ("def %s(" % part["function"]) not in ex["subject"]:
                    bad("%s: subject does not show `def %s(`"
                        % (name, part["function"]))
            if name not in ex["subject"]:
                bad("%s: subject does not mention the assignment name" % name)

            try:
                plan = build_plan(name, ex, rng, fuzz)
            except BankError as exc:
                bad(str(exc))
                continue

            # One standalone module holding every oracle this exercise
            # needs — a submission that must, by construction, score 100%.
            path = os.path.join(workdir, name + ".py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(oracle_source(ex))

            broken = False
            for part, (function, tests) in zip(parts_of(ex), plan):
                if len(tests) < len(part["cases"]):
                    bad("%s: duplicate curated cases for %s" % (name, function))

                # every expected value must survive the trip to the sandbox
                for args, expected in tests:
                    if not json_stable(expected):
                        bad("%s: expected value %r does not survive the "
                            "sandbox round-trip" % (name, expected))
                        break

                # the oracle must be deterministic
                for args, expected in tests[:len(part["cases"])]:
                    if not deep_eq(part["oracle"](*copy.deepcopy(args)), expected):
                        bad("%s: oracle is not deterministic on %r" % (name, args))
                        break

                # …and it must score 100% through the real sandbox
                payload = run_sandbox(path, function, tests, timeout)
                if "fatal" in payload:
                    bad("%s: sandbox says %s (%s)"
                        % (name, payload["fatal"], payload.get("detail", "")))
                    broken = True
                    break
                failed = [i for i, r in enumerate(payload["results"]) if not r["ok"]]
                if failed:
                    bad("%s: oracle fails its own tests, e.g. %s%r"
                        % (name, function, tuple(tests[failed[0]][0])))
                    broken = True
                    break
                if payload.get("mutated"):
                    bad("%s: oracle mutates its input arguments" % name)
            if broken:
                continue
            log("  ok    %-32s %3d tests" % (name, plan_size(plan)))
    finally:
        _rmtree(workdir)
    return problems
