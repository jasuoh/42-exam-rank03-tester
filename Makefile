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
C_PKG       := c_exam
SOURCES     := $(SRC_PKG)/__main__.py $(SRC_PKG)/examshell.py \
               $(SRC_PKG)/grader.py $(SRC_PKG)/ui.py $(SRC_PKG)/bank_common.py \
               $(SRC_PKG)/exam_bank.py $(SRC_PKG)/exam_bank_r04.py \
               $(SRC_PKG)/exam_bank_r05.py $(SRC_PKG)/ranks.py \
               $(SRC_PKG)/training_bank.py \
               $(SRC_PKG)/settings.py $(SRC_PKG)/stats.py \
               $(SRC_PKG)/session_store.py $(SRC_PKG)/report_export.py \
               $(SRC_PKG)/version.py $(SRC_PKG)/case_labels.py $(SRC_PKG)/update_check.py \
               $(C_PKG)/__main__.py $(C_PKG)/examshell.py $(C_PKG)/grader.py \
               $(C_PKG)/bank.py $(C_PKG)/training_bank.py \
               $(wildcard tests/*.py)
RENDU       ?= rendu

CC          ?= cc
C_RENDU     ?= c_rendu

# Optional flags forwarded to the tester, e.g. `make exam SEED=42 FLAGS=--strict-imports`
EX    ?=
N     ?=
SEED  ?=
FLAGS ?=
# Which Python exam pool to use: 03 (default), 04 or 05. Left empty rather
# than defaulted to 03 so `make check` still means "check every rank".
RANK  ?=
RANK_ARG := $(if $(RANK),--rank $(RANK),)
ARGS  := $(FLAGS) $(RANK_ARG) $(if $(SEED),--seed $(SEED),) \
         $(if $(RENDU),--rendu $(RENDU),)
C_ARGS := $(FLAGS) $(if $(SEED),--seed $(SEED),) $(if $(C_RENDU),--rendu $(C_RENDU),) \
          $(if $(CC),--cc $(CC),)

BOLD  := \033[1m
CYAN  := \033[96m
GREEN := \033[92m
DIM   := \033[90m
OFF   := \033[0m

.DEFAULT_GOAL := help
.PHONY: help run exam practice list train list-training stub grade grade-all \
        stats ranks check unit test lint format install venv deps clean fclean re \
        rendu-clean status \
        c-run c-exam c-practice c-list c-train c-list-training c-stub \
        c-grade c-grade-all c-stats c-check c-unit c-test c-status \
        readiness drill c-readiness c-drill update

# ── help ──────────────────────────────────────────────────────
# Every "make X ..." row uses a real printf field width (%-21s) on the
# command name — NOT hand-typed spaces — so columns line up no matter how
# long a target's name is, and the alignment can never silently drift as
# targets are added.
ROWW := 21

help:
	@printf "$(CYAN)╔══════════════════════════════════════════════════════════════╗$(OFF)\n"
	@printf "$(CYAN)║$(OFF)  $(BOLD)ExamShell$(OFF)  ·  42 Common Core practice testers               $(CYAN)║$(OFF)\n"
	@printf "$(CYAN)╚══════════════════════════════════════════════════════════════╝$(OFF)\n"
	@printf "\n$(BOLD)$(CYAN)▸ PYTHON$(OFF)  $(DIM)— Exam Rank 03 (default) · 04 · 05, pick with RANK=04$(OFF)\n"
	@printf "  $(BOLD)Play$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make run" "interactive menu (exam · practice · list · training)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[RANK=04]$(OFF)\n" $(ROWW) "make exam" "jump straight into the exam"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make ranks" "list the exam ranks and their pools"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[EX=py_inter]$(OFF)\n" $(ROWW) "make practice" "drill a single exam exercise"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make list" "print the exam exercise pool"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[EX=easy|py_kth_largest]$(OFF)\n" $(ROWW) "make train" "LeetCode-style practice, by difficulty"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make list-training" "print the training pool (by difficulty)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)EX=py_inter$(OFF)\n" $(ROWW) "make stub" "create a solution stub (never overwrites)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)EX=py_inter$(OFF)\n" $(ROWW) "make grade" "grade one solution, no menu"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make grade-all" "grade every exam solution in $(RENDU)/, one overview"
	@printf "                          $(DIM)(exam pool only — a training solution grades via 'make grade')$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make stats" "your local practice history (attempts, pass rate, best time)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[RANK=04]$(OFF)\n" $(ROWW) "make readiness" "which exam exercises you've passed, level by level"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[N=5]$(OFF)\n" $(ROWW) "make drill" "short daily session from your gaps"
	@printf "  $(BOLD)Develop$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make unit" "fast unit tests for grader/ui/examshell logic"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[RANK=04]$(OFF)\n" $(ROWW) "make check" "self-test every exam bank + the training bank"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make test" "unit + check"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make lint" "compile-check + ruff/pyflakes if installed"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make format" "run ruff format if installed"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make status" "which solutions exist in $(RENDU)/"
	@printf "  $(BOLD)Environment$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make update" "pull the latest version of this tester (git pull)"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make install" "create $(VENV)/ and install rich (nicer UI, optional)"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make clean" "remove caches and stray artefacts"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make fclean" "clean + remove $(VENV)/"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make re" "fclean + install + check"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make rendu-clean" "delete YOUR solutions in $(RENDU)/ (asks first)"
	@printf "  $(DIM)Options: RANK=03|04|05  EX=<exercise>  SEED=<n>  RENDU=<dir>  FLAGS='--strict-imports'$(OFF)\n"
	@printf "  $(DIM)Try: FLAGS='--theme highcontrast --save-config' (once, remembers your theme)$(OFF)\n"
	@printf "  $(DIM)python: $(PY)$(OFF)\n"
	@printf "\n$(BOLD)$(CYAN)▸ C$(OFF)  $(DIM)— Exam Rank 02, compile-based, separate $(C_RENDU)/$(OFF)\n"
	@printf "  $(BOLD)Play$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-run" "interactive menu (exam · practice · list)"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-exam" "jump straight into the exam"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[EX=ft_atoi]$(OFF)\n" $(ROWW) "make c-practice" "drill a single exercise"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-list" "print the exercise pool"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[EX=easy|array_sum]$(OFF)\n" $(ROWW) "make c-train" "LeetCode-style practice, by difficulty"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-list-training" "print the training pool (by difficulty)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)EX=ft_atoi$(OFF)\n" $(ROWW) "make c-stub" "create a solution stub (never overwrites)"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)EX=ft_atoi$(OFF)\n" $(ROWW) "make c-grade" "grade one solution, no menu"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-grade-all" "grade every solution in $(C_RENDU)/, one overview"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-stats" "your local practice history (attempts, pass rate, best time)"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-readiness" "which exam exercises you've passed, level by level"
	@printf "    $(GREEN)%-*s$(OFF) %s $(DIM)[N=5]$(OFF)\n" $(ROWW) "make c-drill" "short daily session from your gaps"
	@printf "  $(BOLD)Develop$(OFF)\n"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-unit" "fast unit tests for the C tester's own logic"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-check" "self-test both C exercise banks (real compiles)"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-test" "c-unit + c-check"
	@printf "    $(GREEN)%-*s$(OFF) %s\n" $(ROWW) "make c-status" "which solutions exist in $(C_RENDU)/"
	@printf "  $(DIM)Options: EX=<exercise>  SEED=<n>  RENDU=<dir> (default $(C_RENDU))  CC=<compiler>$(OFF)\n"
	@printf "  $(DIM)cc: $(CC)$(OFF)\n"

# ── play ──────────────────────────────────────────────────────
run:
	@$(PY) -m $(SRC_PKG) $(ARGS)

exam:
	@$(PY) -m $(SRC_PKG) --exam $(ARGS)

practice:
	@$(PY) -m $(SRC_PKG) --practice $(EX) $(ARGS)

list:
	@$(PY) -m $(SRC_PKG) --list $(RANK_ARG)

train:
	@$(PY) -m $(SRC_PKG) --train $(EX) $(ARGS)

list-training:
	@$(PY) -m $(SRC_PKG) --list-training $(RANK_ARG)

stub:
	@[ -n "$(EX)" ] || { printf "usage: make stub EX=py_inter\n" >&2; exit 2; }
	@$(PY) -m $(SRC_PKG) --stub $(EX) $(ARGS)

grade:
	@[ -n "$(EX)" ] || { printf "usage: make grade EX=py_inter\n" >&2; exit 2; }
	@$(PY) -m $(SRC_PKG) --grade $(EX) $(ARGS)

grade-all:
	@$(PY) -m $(SRC_PKG) --grade-all $(ARGS)

stats:
	@$(PY) -m $(SRC_PKG) --stats $(RANK_ARG)

readiness:
	@$(PY) -m $(SRC_PKG) --readiness $(RANK_ARG)

drill:
	@$(PY) -m $(SRC_PKG) --drill $(N) $(ARGS)

ranks:
	@$(PY) -m $(SRC_PKG) --list-ranks

# ── play (C Rank 02) ─────────────────────────────────────────────
c-run:
	@$(PY) -m $(C_PKG) $(C_ARGS)

c-exam:
	@$(PY) -m $(C_PKG) --exam $(C_ARGS)

c-practice:
	@$(PY) -m $(C_PKG) --practice $(EX) $(C_ARGS)

c-list:
	@$(PY) -m $(C_PKG) --list

c-train:
	@$(PY) -m $(C_PKG) --train $(EX) $(C_ARGS)

c-list-training:
	@$(PY) -m $(C_PKG) --list-training

c-stub:
	@[ -n "$(EX)" ] || { printf "usage: make c-stub EX=ft_atoi\n" >&2; exit 2; }
	@$(PY) -m $(C_PKG) --stub $(EX) $(C_ARGS)

c-grade:
	@[ -n "$(EX)" ] || { printf "usage: make c-grade EX=ft_atoi\n" >&2; exit 2; }
	@$(PY) -m $(C_PKG) --grade $(EX) $(C_ARGS)

c-grade-all:
	@$(PY) -m $(C_PKG) --grade-all $(C_ARGS)

c-stats:
	@$(PY) -m $(C_PKG) --stats

c-readiness:
	@$(PY) -m $(C_PKG) --readiness

c-drill:
	@$(PY) -m $(C_PKG) --drill $(N) $(C_ARGS)

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

format:
	@if $(PY) -m ruff --version >/dev/null 2>&1; then $(PY) -m ruff format $(SOURCES); \
	elif command -v ruff >/dev/null 2>&1; then ruff format $(SOURCES); \
	else printf "ruff is not installed — pip install ruff\n" >&2; exit 1; fi

status:
	@printf "$(BOLD)Exam solutions in $(RENDU)/$(OFF)\n"
	@# $$2, not $$1: the exam listing puts a ★/○ pool marker before the
	@# name (the training listing below has none, so it stays $$1).
	@$(PY) -m $(SRC_PKG) --list $(RANK_ARG) --no-color | awk '/py_/ {print $$2}' | while read -r ex; do \
		if [ -f "$(RENDU)/$$ex.py" ]; then printf "  $(GREEN)●$(OFF) %s\n" "$$ex"; \
		else printf "  $(DIM)○ %s$(OFF)\n" "$$ex"; fi; \
	done
	@printf "$(BOLD)Training solutions in $(RENDU)/$(OFF)\n"
	@$(PY) -m $(SRC_PKG) --list-training $(RANK_ARG) --no-color | awk '/py_/ {print $$1}' | while read -r ex; do \
		if [ -f "$(RENDU)/$$ex.py" ]; then printf "  $(GREEN)●$(OFF) %s\n" "$$ex"; \
		else printf "  $(DIM)○ %s$(OFF)\n" "$$ex"; fi; \
	done

# C exercise names have no shared prefix to awk-filter on (unlike py_*),
# so list them straight from the bank modules instead of scraping --list.
c-status:
	@printf "$(BOLD)Exam solutions in $(C_RENDU)/$(OFF)\n"
	@$(PY) -c "from c_exam.bank import EXERCISES as E; [print(n) for n in sorted(E)]" \
		| while read -r ex; do \
			if [ -f "$(C_RENDU)/$$ex.c" ]; then printf "  $(GREEN)●$(OFF) %s\n" "$$ex"; \
			else printf "  $(DIM)○ %s$(OFF)\n" "$$ex"; fi; \
		done
	@printf "$(BOLD)Training solutions in $(C_RENDU)/$(OFF)\n"
	@$(PY) -c "from c_exam.training_bank import TRAINING_EXERCISES as E; [print(n) for n in sorted(E)]" \
		| while read -r ex; do \
			if [ -f "$(C_RENDU)/$$ex.c" ]; then printf "  $(GREEN)●$(OFF) %s\n" "$$ex"; \
			else printf "  $(DIM)○ %s$(OFF)\n" "$$ex"; fi; \
		done

# ── environment ───────────────────────────────────────────────
update:
	@git pull --ff-only

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
	@rm -rf $${TMPDIR:-/tmp}/examshell-* $${TMPDIR:-/tmp}/c-exam-* 2>/dev/null || true
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
