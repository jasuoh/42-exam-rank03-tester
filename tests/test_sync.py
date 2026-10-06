#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""examshell/sync.py — two "devices" (separate data dirs and solution folders)
syncing through a local bare git repository. Needs git."""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from examshell import session_store, sync

HAVE_GIT = shutil.which("git") is not None


class Device(object):
    def __init__(self, root, name):
        self.name = name
        self.data = os.path.join(root, name, "home")
        self.dirs = {
            "rendu": os.path.join(root, name, "rendu"),
            "c_rendu": os.path.join(root, name, "c_rendu"),
        }
        os.makedirs(self.data)

    def setup(self, url):
        return sync.setup(url, self.data, self.dirs, device=self.name)

    def sync(self):
        return sync.sync(self.data, self.dirs, device=self.name)

    def write(self, slot, name, text, mtime):
        os.makedirs(self.dirs[slot], exist_ok=True)
        path = os.path.join(self.dirs[slot], name)
        with open(path, "w") as fh:
            fh.write(text)
        os.utime(path, (mtime, mtime))
        return path

    def read(self, slot, name):
        with open(os.path.join(self.dirs[slot], name)) as fh:
            return fh.read()

    def stats(self, *events):
        with open(os.path.join(self.data, "stats.jsonl"), "a") as fh:
            for ts, exercise in events:
                fh.write(
                    json.dumps(
                        {
                            "ts": ts,
                            "tool": "py",
                            "exercise": exercise,
                            "ok": True,
                            "mode": "practice",
                        }
                    )
                    + "\n"
                )

    def stat_lines(self):
        with open(os.path.join(self.data, "stats.jsonl")) as fh:
            return [json.loads(line)["ts"] for line in fh if line.strip()]

    def save_exam(self, level, when):
        class S(object):
            login, passed, attempts, history, start_time = (
                "alice",
                [],
                1,
                [],
                when - 60,
            )

        S.level = level
        with mock.patch.object(
            session_store, "DATA_DIR", self.data
        ), mock.patch.object(session_store.time, "time", return_value=when):
            session_store.save("py", S(), random.Random(1), "py_inter")

    def clear_exam(self, when):
        with mock.patch.object(
            session_store, "DATA_DIR", self.data
        ), mock.patch.object(session_store.time, "time", return_value=when):
            session_store.clear("py")

    def saved_exam(self):
        with mock.patch.object(session_store, "DATA_DIR", self.data):
            return session_store.load("py")


@unittest.skipUnless(HAVE_GIT, "git not installed")
class SyncTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.url = os.path.join(tmp.name, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", self.url], check=True)
        self.a = Device(tmp.name, "laptop")
        self.b = Device(tmp.name, "campus")

    def test_not_set_up(self):
        with self.assertRaises(sync.SyncError) as ctx:
            self.a.sync()
        self.assertIn("sync-setup", str(ctx.exception))
        self.assertFalse(sync.is_configured(self.a.data))

    def test_solutions_and_history_travel_between_devices(self):
        self.a.write("rendu", "py_inter.py", "A", 1000)
        self.a.write("c_rendu", "rotone.c", "int main(){}", 1000)
        self.a.stats((1, "py_inter"), (2, "py_inter"))
        pushed = self.a.setup(self.url)
        self.assertEqual(pushed.pushed["solutions"], 2)
        self.assertEqual(sync.remote_url(self.a.data), self.url)

        self.b.stats((3, "py_hidenp"))
        pulled = self.b.setup(self.url)
        self.assertEqual(pulled.pulled["solutions"], 2)
        self.assertEqual(self.b.read("rendu", "py_inter.py"), "A")
        self.assertEqual(self.b.read("c_rendu", "rotone.c"), "int main(){}")
        self.assertEqual(self.b.stat_lines(), [1, 2, 3])

        self.a.sync()  # A gets B's attempt too
        self.assertEqual(self.a.stat_lines(), [1, 2, 3])
        again = self.a.sync()  # nothing left to move
        self.assertFalse(again.committed)
        self.assertEqual(
            sum(again.pulled.values()) + sum(again.pushed.values()), 0
        )

    def test_newer_edit_wins_and_the_older_one_is_backed_up(self):
        self.a.write("rendu", "py_inter.py", "old", 1000)
        self.a.setup(self.url)
        self.b.setup(self.url)
        self.b.write("rendu", "py_inter.py", "new on campus", 2000)
        self.b.sync()
        self.a.write("rendu", "py_inter.py", "older edit on laptop", 1500)
        result = self.a.sync()
        self.assertEqual(self.a.read("rendu", "py_inter.py"), "new on campus")
        self.assertEqual(len(result.backups), 1)
        with open(result.backups[0]) as fh:
            self.assertEqual(fh.read(), "older edit on laptop")

    def test_a_local_edit_newer_than_the_repo_is_pushed(self):
        self.a.write("rendu", "py_inter.py", "v1", 1000)
        self.a.setup(self.url)
        self.b.setup(self.url)
        self.a.write("rendu", "py_inter.py", "v2", 3000)
        self.a.sync()
        self.b.sync()
        self.assertEqual(self.b.read("rendu", "py_inter.py"), "v2")

    def test_paused_exam_resumes_on_the_other_device_and_stays_finished(self):
        self.a.save_exam(level=3, when=5000)
        self.a.setup(self.url)
        self.b.setup(self.url)
        self.assertEqual(self.b.saved_exam()["level"], 3)

        self.b.clear_exam(when=6000)  # finished it on campus
        self.b.sync()
        self.a.sync()
        self.assertIsNone(
            self.a.saved_exam()
        )  # not resurrected from the laptop

        self.a.save_exam(level=1, when=7000)  # a new exam later wins again
        self.a.sync()
        self.b.sync()
        self.assertEqual(self.b.saved_exam()["level"], 1)

    def test_reports_are_merged(self):
        for device, name in ((self.a, "py_1.md"), (self.b, "c_2.md")):
            os.makedirs(os.path.join(device.data, "reports"))
            with open(os.path.join(device.data, "reports", name), "w") as fh:
                fh.write("# report")
        self.a.setup(self.url)
        self.b.setup(self.url)
        self.a.sync()
        for device in (self.a, self.b):
            self.assertEqual(
                sorted(os.listdir(os.path.join(device.data, "reports"))),
                ["c_2.md", "py_1.md"],
            )

    def test_config_stays_per_device(self):
        with open(os.path.join(self.a.data, "config.json"), "w") as fh:
            fh.write('{"cc": "clang"}')
        self.a.setup(self.url)
        self.b.setup(self.url)
        self.assertFalse(
            os.path.exists(os.path.join(self.b.data, "config.json"))
        )

    def test_bad_remote_is_a_clear_error(self):
        with self.assertRaises(sync.SyncError):
            self.a.setup(
                os.path.join(os.path.dirname(self.url), "does-not-exist.git")
            )


class DataDirTests(unittest.TestCase):
    def test_examshell_home_moves_the_data_dir(self):
        target = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, target)
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                "from examshell import settings, stats; "
                "print(settings.DATA_DIR); print(stats.STATS_PATH)",
            ],
            env=dict(os.environ, EXAMSHELL_HOME=target),
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ).stdout.split()
        self.assertEqual(out, [target, os.path.join(target, "stats.jsonl")])


class ClearTombstoneTests(unittest.TestCase):
    def test_clear_leaves_a_tombstone_that_load_ignores(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        device = Device(tmp, "x")
        device.save_exam(level=2, when=time.time())
        device.clear_exam(when=time.time())
        self.assertIsNone(device.saved_exam())
        with open(os.path.join(device.data, "saved_exam_py.json")) as fh:
            self.assertIn("cleared_at", json.load(fh))


if __name__ == "__main__":
    unittest.main()
