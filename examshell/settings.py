#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
settings.py  ·  persistent CLI preferences, shared by both testers

A tiny JSON file at ~/.examshell/config.json holds a handful of "sticky"
preferences (theme, timeout, fuzz, show-fails, C compiler) so students
don't have to retype the same flags every run. Precedence is always

    explicit CLI flag  >  saved config file  >  built-in default

File I/O here is best-effort on purpose: a locked-down exam machine may
have a read-only or missing $HOME, and a convenience feature must never
be the reason grading breaks. Every read/write swallows OSError.
"""

import json
import os

# EXAMSHELL_HOME moves everything (stats, saved exams, reports, config) —
# e.g. into a folder iCloud/Dropbox already syncs, the zero-setup
# alternative to `make sync` (examshell/sync.py).
DATA_DIR = os.environ.get("EXAMSHELL_HOME") or os.path.join(
    os.path.expanduser("~"), ".examshell"
)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# Keys this module will persist. Kept deliberately small: boolean flags
# like --no-color/--no-rich are left out because a plain store_true has
# no way to represent "explicitly turn back on" from the CLI, which would
# make a saved "off" sticky forever — everything below is instead a
# value flag (or has an unambiguous None-means-unset CLI default).
PERSISTABLE_KEYS = (
    "theme",
    "timeout",
    "fuzz",
    "show_fails",
    "cc",
    "auto_sync",
)


def load_config():
    """Return the saved preferences dict, or {} if none / unreadable."""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(values):
    """Persist `values` (only PERSISTABLE_KEYS, non-None). Best-effort."""
    data = {
        k: v
        for k, v in values.items()
        if k in PERSISTABLE_KEYS and v is not None
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
        return True
    except OSError:
        return False


def update_config(key, value):
    """Change ONE saved preference, keeping every other one (save_config()
    replaces the whole file). Best-effort, like the rest."""
    data = load_config()
    data[key] = value
    return save_config(data)


def merged(args, config, key, default):
    """CLI flag (if the user actually passed it) > config file > default."""
    value = getattr(args, key, None)
    if value is not None:
        return value
    return config.get(key, default)
