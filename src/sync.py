#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync.py  ·  carry your progress and solutions between devices via git

`make sync-setup REPO=<url>` once per device, then `make sync` before and
after practising. The remote is the student's OWN (private) repository —
there is no server of ours involved, and nothing leaves the machine except
towards that repo.

What travels, and how two devices' versions are combined:

  stats.jsonl            union of every graded attempt, ordered by time
  saved_exam_<tool>.json the newer one wins (a finished exam leaves a
                         tombstone — see session_store.clear() — so it
                         doesn't come back from the other device)
  reports/*.md           union
  rendu/, c_rendu/       per file, the newer edit wins; the older version
                         is kept in <data dir>/sync-backup/ — code is
                         never thrown away
  config.json            NOT synced — settings like the compiler are
                         per device

No `git merge` ever runs: sync() fetches the remote state, combines it with
the local one by the rules above, writes the result to both sides, commits
and pushes. So there are never git conflicts for the student to resolve.
A solution file's edit time can't live in git (a checkout resets it), so
the repo keeps a small manifest.json of them.
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time

REPO_DIRNAME = "sync-repo"
BACKUP_DIRNAME = "sync-backup"
BRANCH = "main"
MANIFEST = "manifest.json"
SOLUTION_EXTS = (".py", ".c", ".h")
GIT_TIMEOUT = 180            # seconds per git call (a password prompt may be waiting)

REPO_README = """# ExamShell progress

Synced by `make sync` from
[42-exam-tester](https://github.com/jasuoh/42-exam-tester). Don't edit by
hand — run `make sync` on each device instead.

**Keep this repository PRIVATE.** It contains your exam solutions, and
sharing solutions can count as cheating at 42.

- `data/` — practice history, saved exams, exam reports
- `solutions/` — your `rendu/` and `c_rendu/` files
"""


class SyncError(Exception):
    """Sync can't proceed — the message says what to do about it."""


class SyncResult(object):
    """What one sync moved, for the one-line summary."""

    def __init__(self):
        self.pulled = {"attempts": 0, "solutions": 0, "reports": 0, "exams": 0}
        self.pushed = {"attempts": 0, "solutions": 0, "reports": 0, "exams": 0}
        self.backups = []            # local files replaced by a newer remote version
        self.committed = False

    def summary(self):
        def part(counts):
            bits = ["%d %s" % (n, what if n != 1 else what.rstrip("s"))
                    for what, n in counts.items() if n]
            return ", ".join(bits) or "nothing new"
        return "↓ from the repo: %s  ·  ↑ to the repo: %s" % (part(self.pulled),
                                                               part(self.pushed))


# ══════════════════════════════════════════════════════════════
#  GIT
# ══════════════════════════════════════════════════════════════
def repo_dir(data_dir):
    return os.path.join(data_dir, REPO_DIRNAME)


def is_configured(data_dir):
    return os.path.isdir(os.path.join(repo_dir(data_dir), ".git"))


def _git(repo, *args, check=True):
    try:
        proc = subprocess.run(["git", "-C", repo] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=GIT_TIMEOUT)
    except FileNotFoundError:
        raise SyncError("git isn't installed")
    except subprocess.TimeoutExpired:
        raise SyncError("git %s timed out after %ds" % (args[0], GIT_TIMEOUT))
    if check and proc.returncode != 0:
        raise SyncError("git %s failed: %s" % (args[0], (proc.stderr or proc.stdout).strip()[-600:]))
    return proc


def remote_url(data_dir):
    if not is_configured(data_dir):
        return None
    proc = _git(repo_dir(data_dir), "remote", "get-url", "origin", check=False)
    return proc.stdout.strip() or None


def setup(url, data_dir, solution_dirs, device=None):
    """Connect this device to `url` (clone it, or re-point an existing
    setup), then run a first sync. Returns that sync's SyncResult."""
    repo = repo_dir(data_dir)
    if is_configured(data_dir):
        _git(repo, "remote", "set-url", "origin", url)
    else:
        if os.path.exists(repo):
            raise SyncError("%s exists but isn't a git repository — move it away first" % repo)
        os.makedirs(data_dir, exist_ok=True)
        _git(data_dir, "clone", "-q", url, REPO_DIRNAME)
    return sync(data_dir, solution_dirs, device)


def sync(data_dir, solution_dirs, device=None):
    """Pull, combine, push. `solution_dirs` maps a slot name ("rendu",
    "c_rendu") to that local directory. Returns a SyncResult."""
    if not is_configured(data_dir):
        raise SyncError("sync isn't set up on this device — run "
                        "`make sync-setup REPO=<your private repo url>` first")
    repo = repo_dir(data_dir)
    device = device or socket.gethostname() or "a device"

    _git(repo, "fetch", "-q", "origin")
    if _git(repo, "rev-parse", "--verify", "-q", "origin/" + BRANCH, check=False).returncode == 0:
        # Our working copy is only ever written by sync() itself and every
        # local fact is re-read from data_dir below, so the remote state is
        # always the right base — no merge needed.
        _git(repo, "checkout", "-q", "-B", BRANCH, "origin/" + BRANCH)
        _git(repo, "reset", "-q", "--hard", "origin/" + BRANCH)
    else:
        _git(repo, "checkout", "-q", "-B", BRANCH)          # empty remote: first push

    result = SyncResult()
    data = os.path.join(repo, "data")
    os.makedirs(data, exist_ok=True)
    _merge_stats(os.path.join(data_dir, "stats.jsonl"), os.path.join(data, "stats.jsonl"), result)
    _merge_saved_exams(data_dir, data, result)
    _merge_reports(os.path.join(data_dir, "reports"), os.path.join(data, "reports"), result)
    _merge_solutions(repo, solution_dirs, os.path.join(data_dir, BACKUP_DIRNAME), result)
    with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(REPO_README)

    _git(repo, "add", "-A")
    if _git(repo, "diff", "--cached", "--quiet", check=False).returncode != 0:
        identity = []
        if not _git(repo, "config", "user.email", check=False).stdout.strip():
            identity = ["-c", "user.name=ExamShell sync", "-c", "user.email=examshell@localhost"]
        # never ask for a GPG passphrase just to save practice progress
        _git(repo, *(identity + ["-c", "commit.gpgsign=false",
                                 "commit", "-q", "-m", "sync from %s" % device]))
        result.committed = True
    if result.committed or _git(repo, "rev-parse", "--verify", "-q", "origin/" + BRANCH,
                                check=False).returncode != 0:
        if _git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0:
            _git(repo, "push", "-q", "-u", "origin", BRANCH)
    return result


# ══════════════════════════════════════════════════════════════
#  MERGE RULES
# ══════════════════════════════════════════════════════════════
def _read_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip()]
    except OSError:
        return []


def _canonical(line):
    """(ts, canonical json) for a stats line, or None when it's torn."""
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    if not isinstance(entry, dict):
        return None
    return entry.get("ts", 0), json.dumps(entry, sort_keys=True)


def _merge_stats(local_path, remote_path, result):
    local = {c for c in map(_canonical, _read_lines(local_path)) if c}
    remote = {c for c in map(_canonical, _read_lines(remote_path)) if c}
    merged = sorted(local | remote)
    result.pulled["attempts"] += len(remote - local)
    result.pushed["attempts"] += len(local - remote)
    text = "".join(line + "\n" for _ts, line in merged)
    for path, side in ((local_path, local), (remote_path, remote)):
        if side != set(merged):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)


def _exam_stamp(path):
    """When a saved-exam file was last written: its saved_at / cleared_at,
    or (a save from before sync existed) the file's own mtime."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return -1
    if isinstance(data, dict):
        stamp = data.get("saved_at") or data.get("cleared_at")
        if stamp:
            return stamp
    return os.path.getmtime(path)


def _merge_saved_exams(local_dir, remote_dir, result):
    names = set()
    for folder in (local_dir, remote_dir):
        if os.path.isdir(folder):
            names.update(n for n in os.listdir(folder)
                         if n.startswith("saved_exam_") and n.endswith(".json"))
    for name in sorted(names):
        local, remote = os.path.join(local_dir, name), os.path.join(remote_dir, name)
        l_stamp = _exam_stamp(local) if os.path.exists(local) else -1
        r_stamp = _exam_stamp(remote) if os.path.exists(remote) else -1
        if r_stamp > l_stamp:
            os.makedirs(local_dir, exist_ok=True)
            shutil.copyfile(remote, local)
            result.pulled["exams"] += 1
        elif l_stamp > r_stamp:
            shutil.copyfile(local, remote)
            result.pushed["exams"] += 1


def _merge_reports(local_dir, remote_dir, result):
    def listing(folder):
        return set(os.listdir(folder)) if os.path.isdir(folder) else set()
    local, remote = listing(local_dir), listing(remote_dir)
    for name in sorted(remote - local):
        os.makedirs(local_dir, exist_ok=True)
        shutil.copyfile(os.path.join(remote_dir, name), os.path.join(local_dir, name))
        result.pulled["reports"] += 1
    for name in sorted(local - remote):
        os.makedirs(remote_dir, exist_ok=True)
        shutil.copyfile(os.path.join(local_dir, name), os.path.join(remote_dir, name))
        result.pushed["reports"] += 1


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _solution_files(folder):
    if not os.path.isdir(folder):
        return set()
    return {n for n in os.listdir(folder)
            if n.endswith(SOLUTION_EXTS) and not n.startswith(".")
            and os.path.isfile(os.path.join(folder, n))}


def _merge_solutions(repo, solution_dirs, backup_root, result):
    manifest_path = os.path.join(repo, MANIFEST)
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        manifest = {}
    mtimes = manifest.setdefault("solutions", {})
    stamp = time.strftime("%Y%m%d_%H%M%S")

    for slot, local_dir in sorted(solution_dirs.items()):
        remote_dir = os.path.join(repo, "solutions", slot)
        for name in sorted(_solution_files(local_dir) | _solution_files(remote_dir)):
            key = "%s/%s" % (slot, name)
            local, remote = os.path.join(local_dir, name), os.path.join(remote_dir, name)
            has_local, has_remote = os.path.isfile(local), os.path.isfile(remote)
            remote_mtime = mtimes.get(key, 0)

            if has_local and has_remote and _sha(local) == _sha(remote):
                continue
            local_mtime = os.path.getmtime(local) if has_local else -1
            if has_remote and (not has_local or remote_mtime > local_mtime):
                if has_local:                         # keep the older version, never lose code
                    backup = os.path.join(backup_root, stamp, slot, name)
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(local, backup)
                    result.backups.append(backup)
                os.makedirs(local_dir, exist_ok=True)
                shutil.copyfile(remote, local)
                if remote_mtime:
                    os.utime(local, (remote_mtime, remote_mtime))
                result.pulled["solutions"] += 1
            else:
                os.makedirs(remote_dir, exist_ok=True)
                shutil.copyfile(local, remote)
                mtimes[key] = local_mtime
                result.pushed["solutions"] += 1

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
