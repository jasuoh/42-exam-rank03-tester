#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
version.py  ·  the one place the tester's version number lives

Shared by both testers (`--version`, the update check) and mirrored in
pyproject.toml — tests/test_shared.py keeps the two in sync, and the
release workflow refuses to publish a tag that doesn't match it.
"""

__version__ = "0.3.0"

REPO = "jasuoh/42-exam-tester"
REPO_URL = "https://github.com/" + REPO
