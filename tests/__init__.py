"""Every test runs against a throwaway data folder: settings.DATA_DIR is
read from EXAMSHELL_HOME at import time, so setting it here (the package
is imported before any test module) keeps stats, saved exams, exam draws
and the update-check cache out of the real ~/.examshell even when a test
forgets to patch DATA_DIR itself."""

import atexit
import os
import shutil
import tempfile

_home = tempfile.mkdtemp(prefix="examshell-tests-")
os.environ["EXAMSHELL_HOME"] = _home
atexit.register(shutil.rmtree, _home, True)
