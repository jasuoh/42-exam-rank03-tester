#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""examshell/doctor.py and the 0.5.0 plumbing around it: --doctor,
the shared "s  Sync" menu row, default_config(), command names, and the
console-script entry points named in pyproject.toml."""

from __future__ import annotations

import contextlib
import importlib
import io
import os
import re
import shutil
import tempfile
import unittest
from unittest import mock

from c_exam import examshell as c_shell
from examshell import doctor, examshell as py_shell, shell_common, update_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DoctorCheckTests(unittest.TestCase):
    def test_missing_compiler_is_a_failure_only_for_the_c_tester(self) -> None:
        self.assertEqual(
            doctor.check_compiler("no-such-cc-xyz", required=True).status,
            "fail",
        )
        self.assertEqual(
            doctor.check_compiler("no-such-cc-xyz", required=False).status,
            "warn",
        )
        self.assertIn(
            "xcode-select", doctor.check_compiler("no-such-cc-xyz").fix
        )

    @unittest.skipUnless(shutil.which("cc"), "no C compiler")
    def test_working_compiler(self) -> None:
        self.assertEqual(
            doctor.check_compiler("cc", required=True).status, "ok"
        )

    def test_unwritable_data_dir_fails(self) -> None:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        blocker = os.path.join(tmp, "file")
        open(blocker, "w").close()
        check = doctor.check_data_dir(os.path.join(blocker, "sub"))
        self.assertEqual(check.status, "fail")
        self.assertIn("EXAMSHELL_HOME", check.fix)

    def test_sync_not_set_up_is_a_warning_with_the_setup_command(self) -> None:
        check = doctor.check_sync(tempfile.mkdtemp())
        self.assertEqual(check.status, "warn")
        self.assertIn("make sync-setup", check.fix)

    def test_update_check(self) -> None:
        # a cache of its own: the real ~/.examshell/update_check.json would
        # otherwise keep "v99.0.0" and announce it as an update for a day
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        cache = os.path.join(tmp, "update_check.json")
        with mock.patch.dict(
            os.environ, {update_check.ENV_OPT_OUT: ""}
        ), mock.patch.object(update_check, "DATA_DIR", tmp), mock.patch.object(
            update_check, "CACHE_PATH", cache
        ):
            newer = doctor.check_update(fetch=lambda: "v99.0.0")
        self.assertEqual(newer.status, "warn")
        self.assertIn("99.0.0", newer.detail)
        with mock.patch.dict(os.environ, {update_check.ENV_OPT_OUT: "1"}):
            self.assertIn("turned off", doctor.check_update().detail)

    def test_upgrade_command_matches_the_install(self) -> None:
        with mock.patch.object(doctor, "is_git_checkout", return_value=True):
            self.assertEqual(doctor.upgrade_command(), "make update")
        with mock.patch.object(doctor, "is_git_checkout", return_value=False):
            self.assertEqual(
                doctor.upgrade_command(), "uv tool upgrade examshell"
            )

    def test_run_doctor_exit_code(self) -> None:
        ok = [
            doctor.Check("ok", "a", "fine"),
            doctor.Check("warn", "b", "meh", "fix it"),
        ]
        broken = ok + [doctor.Check("fail", "c", "broken", "repair")]
        cfg = py_shell.default_config()
        for checks, code in ((ok, 0), (broken, 1)):
            with mock.patch.object(
                doctor, "run_checks", return_value=checks
            ), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(shell_common.run_doctor(py_shell, cfg), code)
            self.assertIn("fix it", out.getvalue())


class MenuAndConfigTests(unittest.TestCase):
    def test_sync_row_sits_right_before_quit(self) -> None:
        rows = shell_common.with_sync_row(
            [("1", "Exam", ""), ("q", "Quit", "")]
        )
        self.assertEqual([r[0] for r in rows], ["1", "s", "f", "q"])

    def test_default_config_per_tester(self) -> None:
        self.assertEqual(py_shell.default_config().rendu, "rendu")
        c_cfg = c_shell.default_config(relaxed=True)
        self.assertEqual((c_cfg.rendu, c_cfg.relaxed), ("c_rendu", True))

    def test_sync_dirs_follow_each_testers_rendu(self) -> None:
        cfg = c_shell.default_config(rendu="mine")
        self.assertEqual(
            shell_common.sync_dirs(c_shell, cfg),
            {"rendu": "rendu", "c_rendu": "mine"},
        )

    def test_command_name(self) -> None:
        with mock.patch("sys.argv", ["/home/me/.local/bin/examshell-c"]):
            self.assertEqual(
                shell_common.command_name("examshell-c", "c_exam"),
                "examshell-c",
            )
        with mock.patch("sys.argv", ["/repo/c_exam/__main__.py"]):
            self.assertEqual(
                shell_common.command_name("examshell-c", "c_exam"),
                "python3 -m c_exam",
            )


class PackagingTests(unittest.TestCase):
    def test_console_scripts_point_at_real_functions(self) -> None:
        with open(
            os.path.join(ROOT, "pyproject.toml"), encoding="utf-8"
        ) as fh:
            scripts = dict(
                re.findall(r'^([\w-]+) = "([\w.]+:\w+)"$', fh.read(), re.M)
            )
        self.assertEqual(set(scripts), {"examshell", "examshell-c"})
        for target in scripts.values():
            module, func = target.split(":")
            self.assertTrue(
                callable(getattr(importlib.import_module(module), func))
            )

    def test_old_src_shim_still_runs(self) -> None:
        import subprocess
        import sys

        out = subprocess.run(
            [sys.executable, "-m", "src", "--version"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(out.returncode, 0)
        self.assertIn("now `python3 -m examshell`", out.stderr)


if __name__ == "__main__":
    unittest.main()
