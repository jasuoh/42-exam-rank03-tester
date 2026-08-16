#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for `python3 -m src`."""

import sys

from . import ui
from .examshell import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        ui.info("See you! 🍀")
        print()
        sys.exit(130)
