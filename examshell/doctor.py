#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor.py  ·  `examshell --doctor` / `make doctor`: is this machine ready?

One screen that answers "why doesn't X work here?" — Python version, how
the tester is installed and whether it's up to date, the optional extras,
a C compiler that really compiles and runs, valgrind, git, the data folder,
and the sync setup. Every check returns a status and, when something is
off, the one command that fixes it.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, List, Optional

from . import settings, sync, update_check
from .version import __version__

OK, WARN, FAIL = "ok", "warn", "fail"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELLO_C = (
    '#include <unistd.h>\nint main(void){ write(1, "ok\\n", 3); return 0; }\n'
)


class Check(object):
    def __init__(
        self, status: str, name: str, detail: str, fix: str = ""
    ) -> None:
        self.status, self.name, self.detail, self.fix = (
            status,
            name,
            detail,
            fix,
        )


def is_git_checkout() -> bool:
    """Running from a cloned repo (vs. installed with uv tool / pip)?"""
    return os.path.isdir(os.path.join(ROOT, ".git")) and os.path.isfile(
        os.path.join(ROOT, "Makefile")
    )


TOOL_INSTALL = (
    "uv tool install --force --python 3.12 "
    '"examshell[tui] @ git+https://github.com/jasuoh/42-exam-tester"'
)


def upgrade_command() -> str:
    return "make update" if is_git_checkout() else "uv tool upgrade examshell"


def extras_command() -> str:
    """How to get rich + Textual for THIS kind of install."""
    return "make install" if is_git_checkout() else TOOL_INSTALL


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def check_python() -> Check:
    v = sys.version_info
    text = "%d.%d.%d" % v[:3]
    if v >= (3, 9):
        return Check(OK, "Python", text)
    if v >= (3, 8):
        return Check(
            WARN,
            "Python",
            text + " — everything works except the full-screen app",
            "for --tui: " + extras_command(),
        )
    return Check(
        FAIL, "Python", text + " — too old", "install Python 3.8 or newer"
    )


def check_install() -> Check:
    if is_git_checkout():
        return Check(
            OK, "ExamShell", "%s · git checkout at %s" % (__version__, ROOT)
        )
    return Check(OK, "ExamShell", "%s · installed package" % __version__)


def check_update(
    fetch: Optional[Callable[[], Optional[str]]] = None,
    opt_out: bool = False,
) -> Check:
    if opt_out:
        return Check(OK, "Updates", "check turned off (--no-update-check)")
    if not update_check.enabled():
        return Check(
            OK, "Updates", "check turned off (%s)" % update_check.ENV_OPT_OUT
        )
    try:
        latest = (
            update_check.latest_version(fetch=fetch)
            if fetch
            else update_check.latest_version()
        )
    except Exception:  # never let doctor crash
        latest = None
    if latest is None:
        return Check(
            OK, "Updates", "couldn't check (offline, or no release yet)"
        )
    if update_check.is_newer(latest):
        return Check(
            WARN,
            "Updates",
            "%s is available (you have %s)"
            % (latest.lstrip("vV"), __version__),
            upgrade_command(),
        )
    return Check(OK, "Updates", "up to date")


def check_extras() -> List[Check]:
    checks = []
    if _has("rich"):
        checks.append(Check(OK, "rich", "installed — colours and tables"))
    else:
        checks.append(
            Check(
                WARN, "rich", "not installed — plain output", extras_command()
            )
        )
    if _has("textual") and sys.version_info >= (3, 9):
        checks.append(
            Check(
                OK, "Textual", "installed — `--tui` full-screen app available"
            )
        )
    else:
        checks.append(
            Check(
                WARN,
                "Textual",
                "not available — no full-screen app",
                extras_command(),
            )
        )
    return checks


def check_compiler(cc: str = "cc", required: bool = False) -> Check:
    """Compile and RUN a tiny program — a compiler that exists but can't
    link (missing Xcode command line tools, …) is the classic trap."""
    if not shutil.which(cc):
        return Check(
            FAIL if required else WARN,
            "C compiler",
            "`%s` not found — the C tester can't grade" % cc,
            "macOS: xcode-select --install · Linux: sudo apt install gcc",
        )
    workdir = tempfile.mkdtemp(prefix="examshell-doctor-")
    try:
        src, binary = os.path.join(workdir, "t.c"), os.path.join(workdir, "t")
        with open(src, "w") as fh:
            fh.write(HELLO_C)
        built = subprocess.run(
            [cc, "-Wall", "-Wextra", "-Werror", src, "-o", binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30,
        )
        if built.returncode != 0:
            return Check(
                FAIL if required else WARN,
                "C compiler",
                "`%s` can't compile a test program: %s"
                % (cc, built.stderr.strip()[:160]),
                "macOS: xcode-select --install",
            )
        ran = subprocess.run(
            [binary],
            stdout=subprocess.PIPE,
            timeout=10,
            universal_newlines=True,
        )
        if ran.stdout != "ok\n":
            return Check(
                FAIL if required else WARN,
                "C compiler",
                "a compiled test program didn't run correctly",
            )
        version = subprocess.run(
            [cc, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=10,
        ).stdout.splitlines()
        return Check(
            OK,
            "C compiler",
            "`%s` compiles and runs · %s"
            % (cc, version[0].strip() if version else "?"),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check(
            FAIL if required else WARN, "C compiler", "test failed: %s" % exc
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def check_valgrind() -> Check:
    if shutil.which("valgrind"):
        return Check(
            OK, "valgrind", "installed — `--valgrind` leak checks work"
        )
    return Check(
        WARN,
        "valgrind",
        "not installed — optional leak checks unavailable",
        "Linux: sudo apt install valgrind (not available on macOS)",
    )


def check_git() -> Check:
    if shutil.which("git"):
        return Check(OK, "git", "installed")
    return Check(
        WARN,
        "git",
        "not installed — `make sync` needs it",
        "macOS: xcode-select --install · Linux: sudo apt install git",
    )


def check_data_dir(data_dir: Optional[str] = None) -> Check:
    data_dir = data_dir or settings.DATA_DIR
    try:
        os.makedirs(data_dir, exist_ok=True)
        probe = os.path.join(data_dir, ".doctor-probe")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
    except OSError as exc:
        return Check(
            FAIL,
            "Data folder",
            "%s isn't writable (%s) — no stats, saves or reports"
            % (data_dir, exc),
            "set EXAMSHELL_HOME to a writable folder",
        )
    moved = " (EXAMSHELL_HOME)" if os.environ.get("EXAMSHELL_HOME") else ""
    return Check(OK, "Data folder", data_dir + moved)


def check_sync(data_dir: Optional[str] = None) -> Check:
    data_dir = data_dir or settings.DATA_DIR
    if not sync.is_configured(data_dir):
        return Check(
            WARN,
            "Sync",
            "not set up — progress stays on this device",
            "make sync-setup REPO=<your private repo> (see docs/sync.md)",
        )
    auto = (
        " · auto-sync on"
        if settings.load_config().get("auto_sync")
        else " · auto-sync off (`--auto-sync on`)"
    )
    return Check(
        OK,
        "Sync",
        "connected to %s%s" % (sync.remote_url(data_dir) or "?", auto),
    )


def run_checks(
    cc: str = "cc",
    c_required: bool = False,
    fetch: Optional[Callable[[], Optional[str]]] = None,
    no_update_check: bool = False,
) -> List[Check]:
    """Every check, in display order. `no_update_check` (the CLI flag)
    skips the GitHub lookup, like EXAMSHELL_NO_UPDATE_CHECK does."""
    checks = [
        check_python(),
        check_install(),
        check_update(fetch, opt_out=no_update_check),
    ]
    checks += check_extras()
    checks += [
        check_compiler(cc, required=c_required),
        check_valgrind(),
        check_git(),
        check_data_dir(),
        check_sync(),
    ]
    return checks
