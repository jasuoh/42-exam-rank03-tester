# ══════════════════════════════════════════════════════════════
#  ExamShell  ·  42 Common Core  ·  Exam Rank 03 (Python)
#
#  make            show this help
#  make exam       start the exam
#  make check      validate the exercise bank (the test suite)
# ══════════════════════════════════════════════════════════════

PYTHON      ?= python3
VENV        := venv
VENV_PYTHON := $(VENV)/bin/python
SHELL       := /bin/sh

# Prefer the project venv once it exists, fall back to the system python.
# Recursively expanded on purpose: `make install run` must see the new venv.
PY = $(shell [ -x $(VENV_PYTHON) ] && echo $(VENV_PYTHON) || echo $(PYTHON))

SRC_PKG     := src
SOURCES     := $(SRC_PKG)/__main__.py $(SRC_PKG)/examshell.py \
               $(SRC_PKG)/grader.py $(SRC_PKG)/ui.py $(SRC_PKG)/exam_bank.py
RENDU       ?= rendu

# Optional flags forwarded to the tester, e.g. `make exam SEED=42 FLAGS=--strict-imports`
EX    ?=
SEED  ?=
FLAGS ?=
ARGS  := $(FLAGS) $(if $(SEED),--seed $(SEED),) $(if $(RENDU),--rendu $(RENDU),)

BOLD  := \033[1m
CYAN  := \033[96m
GREEN := \033[92m
DIM   := \033[90m
OFF   := \033[0m

.DEFAULT_GOAL := help
.PHONY: help run exam practice list stub grade check test lint format \
        install venv deps clean fclean re rendu-clean status

# ── help ──────────────────────────────────────────────────────
help:
	@printf "$(BOLD)$(CYAN)ExamShell$(OFF) — 42 Exam Rank 03 (Python)\n\n"
	@printf "$(BOLD)Play$(OFF)\n"
	@printf "  $(GREEN)make run$(OFF)          interactive menu (exam · practice · list)\n"
	@printf "  $(GREEN)make exam$(OFF)         jump straight into the 6-level exam\n"
	@printf "  $(GREEN)make practice$(OFF)     drill exercises            $(DIM)[EX=py_inter]$(OFF)\n"
	@printf "  $(GREEN)make list$(OFF)         print the exercise pool\n"
	@printf "  $(GREEN)make stub$(OFF)         create an empty solution   $(DIM)EX=py_inter$(OFF)\n"
	@printf "  $(GREEN)make grade$(OFF)        grade one solution         $(DIM)EX=py_inter$(OFF)\n\n"
	@printf "$(BOLD)Develop$(OFF)\n"
	@printf "  $(GREEN)make check$(OFF)        self-test the exercise bank (alias: test)\n"
	@printf "  $(GREEN)make lint$(OFF)         compile-check + ruff/pyflakes if installed\n"
	@printf "  $(GREEN)make format$(OFF)       run ruff format if installed\n"
	@printf "  $(GREEN)make status$(OFF)       which solutions exist in $(RENDU)/\n\n"
	@printf "$(BOLD)Environment$(OFF)\n"
	@printf "  $(GREEN)make install$(OFF)      create $(VENV)/ and install rich (nicer UI)\n"
	@printf "  $(GREEN)make clean$(OFF)        remove caches and stray artefacts\n"
	@printf "  $(GREEN)make fclean$(OFF)       clean + remove $(VENV)/\n"
	@printf "  $(GREEN)make re$(OFF)           fclean + install + check\n"
	@printf "  $(GREEN)make rendu-clean$(OFF)  delete YOUR solutions in $(RENDU)/ (asks first)\n\n"
	@printf "$(BOLD)Options$(OFF)  $(DIM)EX=<exercise>  SEED=<n>  RENDU=<dir>  FLAGS='--strict-imports'$(OFF)\n"
	@printf "$(DIM)  python: $(PY)$(OFF)\n"

# ── play ──────────────────────────────────────────────────────
run:
	@$(PY) -m $(SRC_PKG) $(ARGS)

exam:
	@$(PY) -m $(SRC_PKG) --exam $(ARGS)

practice:
	@$(PY) -m $(SRC_PKG) --practice $(EX) $(ARGS)

list:
	@$(PY) -m $(SRC_PKG) --list

stub:
	@[ -n "$(EX)" ] || { printf "usage: make stub EX=py_inter\n" >&2; exit 2; }
	@$(PY) -m $(SRC_PKG) --stub $(EX) $(ARGS)

grade:
	@[ -n "$(EX)" ] || { printf "usage: make grade EX=py_inter\n" >&2; exit 2; }
	@$(PY) -m $(SRC_PKG) --grade $(EX) $(ARGS)

# ── develop ───────────────────────────────────────────────────
check:
	@$(PY) -m $(SRC_PKG) --check $(if $(SEED),--seed $(SEED),)

test: check

# ast.parse rather than compileall: same syntax check, no __pycache__ litter.
lint:
	@$(PY) -c 'import ast,sys;[ast.parse(open(f,encoding="utf-8").read(),f) for f in sys.argv[1:]]' \
		$(SOURCES) && printf "$(GREEN)✔$(OFF) all sources parse\n"
	@if $(PY) -c "import ruff" 2>/dev/null || command -v ruff >/dev/null 2>&1; then \
		ruff check $(SOURCES); \
	elif $(PY) -m pyflakes --version >/dev/null 2>&1; then \
		$(PY) -m pyflakes $(SOURCES); \
	else \
		printf "$(DIM)  (install ruff or pyflakes for a deeper lint)$(OFF)\n"; \
	fi

format:
	@if command -v ruff >/dev/null 2>&1; then ruff format $(SOURCES); \
	else printf "ruff is not installed — pip install ruff\n" >&2; exit 1; fi

status:
	@printf "$(BOLD)Solutions in $(RENDU)/$(OFF)\n"
	@$(PY) -m $(SRC_PKG) --list --no-color | awk '/py_/ {print $$1}' | while read -r ex; do \
		if [ -f "$(RENDU)/$$ex.py" ]; then printf "  $(GREEN)●$(OFF) %s\n" "$$ex"; \
		else printf "  $(DIM)○ %s$(OFF)\n" "$$ex"; fi; \
	done

# ── environment ───────────────────────────────────────────────
install: venv deps

venv: $(VENV_PYTHON)

$(VENV_PYTHON):
	@printf "creating $(VENV)/ with $(PYTHON) …\n"
	@$(PYTHON) -m venv $(VENV)
	@$(VENV_PYTHON) -m pip install --quiet --upgrade pip

deps: $(VENV_PYTHON)
	@$(VENV_PYTHON) -m pip install --quiet -r requirements.txt
	@printf "$(GREEN)✔$(OFF) rich installed — run $(BOLD)make run$(OFF)\n"

# ── cleaning ──────────────────────────────────────────────────
clean:
	@find . -path ./$(VENV) -prune -o -name '__pycache__' -type d -print0 2>/dev/null \
		| xargs -0 rm -rf 2>/dev/null || true
	@find . -path ./$(VENV) -prune -o -name '*.py[co]' -type f -print0 2>/dev/null \
		| xargs -0 rm -f 2>/dev/null || true
	@rm -rf .ruff_cache .pytest_cache
	@rm -rf $${TMPDIR:-/tmp}/examshell-* 2>/dev/null || true
	@printf "$(GREEN)✔$(OFF) caches removed\n"

fclean: clean
	@rm -rf $(VENV)
	@printf "$(GREEN)✔$(OFF) $(VENV)/ removed\n"

# Never wired into clean/fclean: these are the student's own answers.
rendu-clean:
	@printf "This deletes every .py in $(RENDU)/. Type 'yes' to confirm: "; \
	read answer; [ "$$answer" = "yes" ] || { printf "aborted\n"; exit 1; }; \
	rm -f $(RENDU)/*.py && printf "$(GREEN)✔$(OFF) $(RENDU)/ emptied\n"

re: fclean install check
