#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for `python3 -m c_exam` and the installed `examshell-c`
command."""

import sys

from examshell import ui

from .examshell import main


def run(argv=None):
    """Console-script entry point (see pyproject.toml): main() plus a quiet
    exit on Ctrl-C instead of a traceback."""
    try:
        return main(argv)
    except KeyboardInterrupt:
        print()
        ui.info("See you! 🍀")
        print()
        return 130


if __name__ == "__main__":
    sys.exit(run())
