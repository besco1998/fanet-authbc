# Makefile — the ONLY supported entry points (docs/03 §5, CLAUDE.md).
# Real at P0: setup lint test all.  Everything else is a guarded stub that fails loudly
# with the phase that implements it (so `make exp-e1` can never silently "pass").
#
# Interpreter: PYTHON defaults to python3 (env switched to system 3.12 at P0). Override for
# a specific interpreter, e.g.  make setup PYTHON=/usr/bin/python3.12   or  PYTHON=python (CI).

PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin

.DEFAULT_GOAL := help
.PHONY: help setup lint test all \
        bench-micro bench-macro exp-e1 exp-e2 exp-e3 exp-e4 exp-e5 \
        sim-ns3 export-framesizes figures

help:  ## list the supported targets
	@echo "fanet-authbc — supported targets:"
	@echo "  setup             create .venv (Python >=3.12) + install pinned deps + pre-commit"
	@echo "  lint              ruff check src tests"
	@echo "  test              pytest (unit/property/integration)"
	@echo "  all               lint + test"
	@echo "  bench-micro/-macro [P1]  exp-e1..e3 [P4]  exp-e4 [P5]  exp-e5/sim-ns3 [P6]"
	@echo "  export-framesizes [P3]   figures [P4]"

# ---------------------------------------------------------------------------- real targets
setup:  ## create venv (Python >=3.12) and install pinned deps + pre-commit hooks
	@fstype=$$(df -T . | awk 'NR==2{print $$2}'); \
	  case "$$fstype" in \
	    drvfs|9p|cifs|v9fs|fuseblk) echo "ERROR: repo is on '$$fstype' (Windows/network FS). Move it to the Linux FS under ~/ — /mnt/c breaks NS-3 and is 10-50x slower (docs/06 §1)."; exit 1;; \
	    *) echo "fs check: '$$fstype' OK (Linux FS)";; \
	  esac
	@$(PYTHON) -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,12) else 1)' \
	  || { echo "ERROR: $(PYTHON) = $$($(PYTHON) -V 2>&1); need Python >=3.12."; \
	       echo "       Retry with:  make setup PYTHON=/usr/bin/python3.12"; exit 1; }
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e '.[dev]'
	$(BIN)/pre-commit install
	@echo "setup complete: $$($(BIN)/python -V) in $(VENV)"

lint:  ## ruff check
	$(BIN)/ruff check src tests

test:  ## run the test suite
	$(BIN)/pytest

all: lint test  ## lint + test

# --------------------------------------------------------------------------- guarded stubs
bench-micro:  ## P1 microbenchmarks -> results/raw/p1_{sizes,crypto}.csv
	$(BIN)/python -m authbc.bench.micro --seed 1 --n 10000
bench-macro:
	@echo "ERROR: 'bench-macro' is implemented in P1 (docs/prompts/P1_MICROBENCH.md)."; exit 1
exp-e1:  ## E1 overhead dominance -> results/raw/e1_dominance.csv
	$(BIN)/python -m authbc.bench.experiments --exp e1
exp-e2:  ## E2 batching cure -> results/raw/e2_batching.csv
	$(BIN)/python -m authbc.bench.experiments --exp e2
exp-e3:
	@echo "ERROR: 'exp-e3' is implemented in P4 (docs/prompts/P4_EXPERIMENTS_E123.md)."; exit 1
exp-e4:
	@echo "ERROR: 'exp-e4' is implemented in P5 (docs/prompts/P5_MODELS_OPTIMIZER.md)."; exit 1
exp-e5:
	@echo "ERROR: 'exp-e5' is implemented in P6 (docs/prompts/P6_NS3_VALIDATION.md)."; exit 1
sim-ns3:
	@echo "ERROR: 'sim-ns3' is implemented in P6 (docs/prompts/P6_NS3_VALIDATION.md)."; exit 1
export-framesizes:  ## P3 SYNC-3: placement×encoding×b frame sizes -> results/raw/framesizes.csv
	$(BIN)/python -m authbc.bench.framesizes
figures:
	@echo "ERROR: 'figures' is implemented from P4 onward (docs/prompts/P4_EXPERIMENTS_E123.md)."; exit 1
