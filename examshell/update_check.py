#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_check.py  ·  "a newer version is out" notice, shared by both testers

At most once a day, the interactive menu asks GitHub for the latest
release's tag (one small anonymous HTTPS GET — nothing about the student
is sent) in a background thread, so a slow or missing network never delays
anything. The answer is cached in ~/.examshell/update_check.json; a failed
lookup is cached too, so an offline exam machine doesn't retry every run.

Off with --no-update-check or EXAMSHELL_NO_UPDATE_CHECK=1. Never used by
the one-shot CLI modes (--grade, --check, ...) or the tests.
"""

import json
import os
import threading
import time

from .settings import DATA_DIR
from .version import REPO, __version__

LATEST_URL = "https://api.github.com/repos/%s/releases/latest" % REPO
CACHE_PATH = os.path.join(DATA_DIR, "update_check.json")
CHECK_EVERY = 24 * 3600  # seconds
HTTP_TIMEOUT = 3  # seconds — runs in the background anyway
ENV_OPT_OUT = "EXAMSHELL_NO_UPDATE_CHECK"


def parse_version(text):
    """ "v1.2.3" / "1.2.3" -> (1, 2, 3); None when it isn't one."""
    parts = str(text).strip().lstrip("vV").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def is_newer(latest, current=__version__):
    a, b = parse_version(latest), parse_version(current)
    return a is not None and b is not None and a > b


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(latest):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump({"checked": time.time(), "latest": latest}, fh)
    except OSError:
        pass


def _fetch_latest():
    """The latest release tag from GitHub, or None on any failure."""
    import urllib.request

    request = urllib.request.Request(
        LATEST_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "42-exam-tester/" + __version__,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8")).get("tag_name")
    except Exception:
        return None


def latest_version(now=None, fetch=_fetch_latest):
    """The latest known release tag — from the cache when it's fresh,
    otherwise fetched (and cached, even when the fetch failed)."""
    now = time.time() if now is None else now
    cache = _load_cache()
    if now - cache.get("checked", 0) < CHECK_EVERY:
        return cache.get("latest")
    latest = fetch()
    _save_cache(latest)
    return latest


def enabled(opt_out_flag=False):
    return not opt_out_flag and not os.environ.get(ENV_OPT_OUT)


def notice_text(latest):
    """The one-line notice for `latest`, or None when it isn't newer."""
    if not latest or not is_newer(latest):
        return None
    from .doctor import upgrade_command

    return "update available: %s (you have %s) — run `%s`" % (
        latest.lstrip("vV"),
        __version__,
        upgrade_command(),
    )


def start_background_check(opt_out_flag=False):
    """Kick off the check without blocking. Returns a dict whose "notice"
    key gets filled in when (and if) a newer version turns up."""
    result = {"notice": None}
    if not enabled(opt_out_flag):
        return result

    def run():
        result["notice"] = notice_text(latest_version())

    threading.Thread(target=run, daemon=True).start()
    return result
