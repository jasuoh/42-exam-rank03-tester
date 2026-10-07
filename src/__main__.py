"""`python3 -m src` → `python3 -m examshell` (the package was renamed in
0.5.0)."""

from __future__ import annotations

import sys

from examshell.__main__ import run

if __name__ == "__main__":
    sys.stderr.write(
        "note: `python3 -m src` is now `python3 -m examshell` "
        "(or just `examshell` once installed)\n"
    )
    sys.exit(run())
