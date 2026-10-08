# ══════════════════════════════════════════════════════════════
#  ExamShell  ·  42 exam practice — Python Rank 03/04/05 · C Rank 02
#
#  make            start ExamShell (the full-screen app)
#  make help       the few other commands
#  make dev        commands for working on the tester itself
# ══════════════════════════════════════════════════════════════

PYTHON      ?= python3
SHELL       := /bin/sh
# Everything is installed with uv (https://docs.astral.sh/uv/): locked
# versions from uv.lock into .venv/, and a Python of its own if this machine
# has none that fits. No uv yet? `make install` fetches it into ~/.local/bin
# with the official installer — no sudo, nothing else on the machine touched.
UV_HOME     := $(HOME)/.local/bin
UV           = $(or $(shell command -v uv 2>/dev/null),$(wildcard $(UV_HOME)/uv))
VENV_PYTHON := .venv/bin/python

# The project venv once it exists, the system python before that (the
# developer targets run on a bare python3 too — that's what CI checks).
# Recursively expanded on purpose: `make install start` must see the venv.
PY = $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(PYTHON))

SRC_PKG     := examshell
C_PKG       := c_exam
# Every Python file of the project (lint, format). A wildcard, not a list:
# a hand-kept list silently left new modules unlinted.
SOURCES     := $(wildcard $(SRC_PKG)/*.py $(SRC_PKG)/tui/*.py $(C_PKG)/*.py \
                          src/*.py tools/*.py tests/*.py)
RENDU       ?= rendu
CC          ?= cc

# Developer knobs: `make check RANK=04`, `make check SEED=42`
SEED  ?=
RANK  ?=
RANK_ARG := $(if $(RANK),--rank $(RANK),)

BOLD  := \033[1m
GREEN := \033[92m
RED   := \033[91m
DIM   := \033[90m
OFF   := \033[0m

.DEFAULT_GOAL := start
.PHONY: start tui help dev install uv update doctor \
        unit check test c-unit c-check c-test lint mutate format \
        clean fclean re

ROWW := 14

# ── use ───────────────────────────────────────────────────────
# Everything else — exam, practice, progress, switching between Python
# 03/04/05 and C 02, sync, settings — is done inside the app. It opens on
# the exam you picked last; without Textual it falls back to the menu.
start:
	@[ -x $(VENV_PYTHON) ] || $(MAKE) --no-print-directory install
	@$(VENV_PYTHON) -m $(SRC_PKG) --tui --rendu $(RENDU)

# the old name, kept so muscle memory still works
tui: start

help:
	@printf "$(BOLD)ExamShell$(OFF)  $(DIM)· 42 exam practice · Python Rank 03/04/05 · C Rank 02$(OFF)\n\n"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make" "start ExamShell"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make install" "set it up (make does it the first time)"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make update" "get the newest version"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make doctor" "is this machine ready?"
	@printf "\n  $(DIM)%-*s %s$(OFF)\n" $(ROWW) "make dev" "tests & lint, for working on the tester"

dev:
	@printf "$(BOLD)Working on the tester$(OFF)\n\n"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make test" "unit tests + every exercise bank checked against its tests"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make unit" "unit tests only (fast)"
	@printf "  $(GREEN)%-*s$(OFF) %s  $(DIM)%s$(OFF)\n" $(ROWW) "make check" "self-test the Python banks" "[RANK=04 SEED=1]"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-test" "C unit tests + C banks (real compiles)"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make lint" "ruff, flake8, mypy --strict"
	@printf "  $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make format" "ruff format"
	@printf "  $(GREEN)%-*s$(OFF) %s  $(DIM)%s$(OFF)\n" $(ROWW) "make mutate" "what the banks fail to test" "[MUT=py|c ONLY=a,b]"
	@printf "  $(GREEN)%-*s$(OFF) %s  $(DIM)%s$(OFF)\n" $(ROWW) "make clean" "remove caches" "(fclean: also .venv/)"
	@printf "\n  $(DIM)The command line has more (python3 -m examshell --help), see docs/.$(OFF)\n"

update:
	@git pull --ff-only || { printf "$(RED)✖$(OFF) couldn't update — local changes, or not on a branch? (see git's message above)\n"; exit 1; }
	@$(MAKE) --no-print-directory install

doctor:
	@$(PY) -m $(SRC_PKG) --doctor

# ── develop ───────────────────────────────────────────────────
unit:
	@$(PY) -m unittest discover -s tests -t .

check:
	@$(PY) -m $(SRC_PKG) --check $(RANK_ARG) $(if $(SEED),--seed $(SEED),)

test: unit check

c-unit:
	@$(PY) -m unittest discover -s tests -p "test_c_*.py" -t .

c-check:
	@$(PY) -m $(C_PKG) --check $(if $(SEED),--seed $(SEED),) --cc $(CC)

c-test: c-unit c-check

# ast.parse rather than compileall: same syntax check, no __pycache__ litter.
lint:
	@$(PY) -c 'import ast,sys;[ast.parse(open(f,encoding="utf-8").read(),f) for f in sys.argv[1:]]' \
		$(SOURCES) && printf "$(GREEN)✔$(OFF) all sources parse\n"
	@if $(PY) -m ruff --version >/dev/null 2>&1; then \
		$(PY) -m ruff check $(SOURCES); \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check $(SOURCES); \
	elif $(PY) -m pyflakes --version >/dev/null 2>&1; then \
		$(PY) -m pyflakes $(SOURCES); \
	else \
		printf "$(DIM)  (install ruff or pyflakes for a deeper lint)$(OFF)\n"; \
	fi
	@# flake8 (pycodestyle + pyflakes, default 79 columns) and mypy --strict
	@# (config in pyproject.toml). Both are in uv's dev group — `make install`
	@# brings them. Missing tools are skipped with a note, unless
	@# LINT_STRICT=1 (what CI sets): then a missing tool fails the lint.
	@for tool in flake8 mypy; do \
		if ! $(PY) -m $$tool --version >/dev/null 2>&1; then \
			if [ -n "$(LINT_STRICT)" ]; then \
				printf "$(RED)✖$(OFF) $$tool is not installed (make install)\n"; exit 1; \
			fi; \
			printf "$(DIM)  ($$tool not installed — make install for the full lint)$(OFF)\n"; \
		elif [ $$tool = flake8 ]; then \
			$(PY) -m flake8 $(SOURCES) && printf "$(GREEN)✔$(OFF) flake8\n" || exit 1; \
		else \
			$(PY) -m mypy --strict && printf "$(GREEN)✔$(OFF) mypy --strict\n" || exit 1; \
		fi; \
	done

# Mutation-test the banks (tools/mutate.py): exit 1 when a bank lets a
# plausible bug through. MUT=py|c narrows the language, ONLY=a,b the
# exercises.
mutate:
	@$(PY) tools/mutate.py --lang $(or $(MUT),all) $(if $(ONLY),--only $(ONLY),)

format:
	@if $(PY) -m ruff --version >/dev/null 2>&1; then $(PY) -m ruff format $(SOURCES); \
	elif command -v ruff >/dev/null 2>&1; then ruff format $(SOURCES); \
	else printf "ruff is not installed — make install\n" >&2; exit 1; fi

# ── install ───────────────────────────────────────────────────
install: uv
	@uv="$$(command -v uv || echo $(UV_HOME)/uv)"; "$$uv" sync --quiet --extra tui
	@printf "$(GREEN)✔$(OFF) installed with uv into .venv/\n"

# uv itself, if this machine doesn't have it yet
uv:
	@if [ -z "$(UV)" ]; then \
		printf "installing uv (https://docs.astral.sh/uv/) into $(UV_HOME) …\n"; \
		if command -v curl >/dev/null 2>&1; then \
			curl -LsSf https://astral.sh/uv/install.sh \
				| env UV_INSTALL_DIR="$(UV_HOME)" UV_NO_MODIFY_PATH=1 sh >/dev/null || exit 1; \
		elif command -v wget >/dev/null 2>&1; then \
			wget -qO- https://astral.sh/uv/install.sh \
				| env UV_INSTALL_DIR="$(UV_HOME)" UV_NO_MODIFY_PATH=1 sh >/dev/null || exit 1; \
		else \
			printf "$(RED)✖$(OFF) needs curl or wget to fetch uv — or install it: https://docs.astral.sh/uv/\n"; exit 1; \
		fi; \
	fi

# ── cleaning ──────────────────────────────────────────────────
clean:
	@find . -path ./.venv -prune -o -name '__pycache__' -type d -print0 2>/dev/null \
		| xargs -0 rm -rf 2>/dev/null || true
	@find . -path ./.venv -prune -o -name '*.py[co]' -type f -print0 2>/dev/null \
		| xargs -0 rm -f 2>/dev/null || true
	@rm -rf .ruff_cache .pytest_cache
	@rm -rf $${TMPDIR:-/tmp}/examshell-* $${TMPDIR:-/tmp}/c-exam-* 2>/dev/null || true
	@printf "$(GREEN)✔$(OFF) caches removed\n"

fclean: clean
	@rm -rf .venv
	@printf "$(GREEN)✔$(OFF) .venv/ removed\n"

re: fclean install check
