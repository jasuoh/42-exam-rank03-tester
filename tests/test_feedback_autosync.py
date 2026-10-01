#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""0.6.0: --feedback (prefilled issue forms) and auto-sync."""

import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

from c_exam import examshell as c_shell
from examshell import examshell as py_shell
from examshell import feedback, settings, shell_common, sync

HAVE_GIT = shutil.which("git") is not None


def _query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


class FeedbackTests(unittest.TestCase):
    def test_exam_form_is_prefilled(self):
        url = feedback.issue_url("exam", "C · Exam Rank 02", "inter")
        self.assertTrue(url.startswith("https://github.com/jasuoh/42-exam-tester/issues/new?"))
        q = _query(url)
        self.assertEqual(q["template"], "exam_mismatch.yml")
        self.assertEqual(q["tester"], "C · Exam Rank 02")
        self.assertEqual(q["exercise"], "inter")
        self.assertTrue(q["version"].startswith("examshell "))

    def test_bug_form_carries_the_environment(self):
        q = _query(feedback.issue_url("bug"))
        self.assertEqual(q["template"], "bug_report.yml")
        self.assertIn("Python", q["env"])

    def test_form_ids_exist_in_the_issue_templates(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for kind, extra in (("exam", "inter"), ("bug", None), ("idea", None)):
            template, _ = feedback.KINDS[kind]
            with open(os.path.join(root, ".github", "ISSUE_TEMPLATE", template)) as fh:
                text = fh.read()
            for key in _query(feedback.issue_url(kind, "x", extra)):
                if key not in ("template", "title"):
                    with self.subTest(kind=kind, field=key):
                        self.assertIn("id: %s" % key, text)

    def test_tester_labels_match_the_exam_dropdown(self):
        self.assertEqual(shell_common.tester_label(c_shell), "C · Exam Rank 02")
        self.assertEqual(shell_common.tester_label(py_shell), "Python · Exam Rank 03")

    def test_no_browser_on_a_bare_linux_console(self):
        with mock.patch.object(feedback.sys, "platform", "linux"), \
             mock.patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            self.assertFalse(feedback.can_open_browser())
            self.assertFalse(feedback.open_in_browser("https://example.invalid"))

    def test_run_feedback_prints_the_link(self):
        with mock.patch.object(feedback, "open_in_browser", return_value=False), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(shell_common.run_feedback(c_shell, "exam", "inter"), 0)
        self.assertIn("exam_mismatch.yml", out.getvalue())

    def test_menu_has_sync_and_feedback_before_quit(self):
        rows = shell_common.with_sync_row([("1", "x", ""), ("q", "Quit", "")])
        self.assertEqual([r[0] for r in rows], ["1", "s", "f", "q"])


class AutoSyncSettingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for name, value in (("DATA_DIR", tmp), ("CONFIG_PATH", os.path.join(tmp, "config.json"))):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_set_auto_sync_keeps_other_settings(self):
        settings.save_config({"theme": "light", "cc": "clang"})
        with contextlib.redirect_stdout(io.StringIO()):
            shell_common.set_auto_sync(True)
        self.assertEqual(settings.load_config(),
                         {"theme": "light", "cc": "clang", "auto_sync": True})
        with contextlib.redirect_stdout(io.StringIO()):
            shell_common.set_auto_sync(False)
        self.assertFalse(shell_common.auto_sync_enabled())

    def test_off_or_not_set_up_does_nothing(self):
        cfg = c_shell.default_config()
        with mock.patch.object(sync, "sync") as run:
            self.assertIsNone(shell_common.auto_sync(c_shell, cfg, "start"))   # off
            settings.update_config("auto_sync", True)
            self.assertIsNone(shell_common.auto_sync(c_shell, cfg, "start"))   # not set up
        run.assert_not_called()


@unittest.skipUnless(HAVE_GIT, "git not installed")
class AutoSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.url = os.path.join(self.tmp, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", self.url], check=True)
        self.home = os.path.join(self.tmp, "home")
        for name, value in (("DATA_DIR", self.home),
                            ("CONFIG_PATH", os.path.join(self.home, "config.json"))):
            patcher = mock.patch.object(settings, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.cfg = c_shell.default_config(rendu=os.path.join(self.tmp, "c_rendu"))
        os.makedirs(self.cfg.rendu)
        with open(os.path.join(self.cfg.rendu, "rotone.c"), "w") as fh:
            fh.write("int main(void){return 0;}\n")
        sync.setup(self.url, self.home, shell_common.sync_dirs(c_shell, self.cfg))
        settings.update_config("auto_sync", True)

    def test_runs_and_reports(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = shell_common.auto_sync(c_shell, self.cfg, "end")
        self.assertIsNotNone(result)
        self.assertIn("pushing your progress", out.getvalue())

    def test_offline_is_only_a_warning(self):
        shutil.move(self.url, self.url + ".gone")
        with mock.patch.object(shell_common.ui, "warn") as warn, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(shell_common.auto_sync(c_shell, self.cfg, "start"))
        self.assertIn("auto-sync skipped", warn.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
