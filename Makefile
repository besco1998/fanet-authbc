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
.PHONY: help setup lint test verify-frozen all hw-capture hw-reduce \
        bench-micro bench-macro exp-e1 exp-e2 exp-e3 exp-e4 exp-e5 exp-capacity exp-lora exp-lora-codesign \
        sim-ns3 sim-ns3-matrix sim-ns3-dcf sim-ns3-sensitivity export-framesizes figures

help:  ## list the supported targets
	@echo "fanet-authbc — supported targets:"
	@echo "  setup             create .venv (Python >=3.12) + install pinned deps + pre-commit"
	@echo "  lint              ruff check src tests"
	@echo "  test              pytest (unit/property/integration)"
	@echo "  all               lint + test"
	@echo "  bench-micro/-macro [P1]  exp-e1..e3 [P4]  exp-e4 [P5]  exp-e5/sim-ns3 [P6]"
	@echo "  export-framesizes [P3]   figures [P4]   sim-ns3-matrix/-dcf [P6b/P7]"

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

test:  ## run the fast test suite (excludes the slow frozen-reproduction gate)
	$(BIN)/pytest -m "not frozen"

verify-frozen:  ## re-derive every deterministic frozen artifact; fail on staleness (docs/DECISIONS.md)
	$(BIN)/pytest -m frozen -p no:cov -o addopts="-q"

all: lint test verify-frozen  ## lint + fast tests + frozen-reproduction gate

# --------------------------------------------------------------------------- guarded stubs
bench-micro:  ## P1 microbenchmarks -> results/raw/p1_{sizes,crypto}.csv
	$(BIN)/python -m authbc.bench.micro --seed 1 --n 10000
bench-macro:
	@echo "ERROR: 'bench-macro' is implemented in P1 (docs/prompts/P1_MICROBENCH.md)."; exit 1
exp-e1:  ## E1 overhead dominance -> results/raw/e1_dominance.csv
	$(BIN)/python -m authbc.bench.experiments --exp e1
exp-e2:  ## E2 batching cure -> results/raw/e2_batching.csv
	$(BIN)/python -m authbc.bench.experiments --exp e2
exp-e3:  ## E3 loss frontier -> results/raw/e3_loss.csv
	$(BIN)/python -m authbc.bench.experiments --exp e3
exp-e4:  ## P5b E4: Ed25519<->BLS crossover from measured P1 timings -> results/raw/e4_*.csv + figure
	$(BIN)/python experiments/e4/run_e4.py
	$(BIN)/python analysis/figures_e4.py
exp-e5:  ## E5 co-design: optimizer vs baselines -> results/raw/e5_codesign.csv
	$(BIN)/python -m authbc.bench.experiments --exp e5
exp-capacity:  ## (N, Lambda) channel capacity envelope (docs/02 §6b) -> results/raw/capacity_envelope.csv
	$(BIN)/python -m authbc.bench.experiments --exp capacity
exp-lora:  ## LoRa arm feasibility + duty budget (docs/02 §9) -> results/raw/lora_eu868.csv
	$(BIN)/python -m authbc.bench.experiments --exp lora
exp-lora-codesign:  ## LoRa arm as a joint optimization -> results/raw/lora_codesign.csv
	$(BIN)/python -m authbc.bench.experiments --exp lora-codesign
sim-ns3:  ## [P6] build authbc-sat + 2-node both-modes smoke -> results/raw/ns3_smoke.csv
	PY=$(BIN)/python bash ns3/sim_ns3.sh
sim-ns3-matrix:  ## [P6b] N x mode x seed saturation matrix -> results/raw/ns3_matrix.csv
	$(BIN)/python ns3/run_matrix.py --seeds 10
sim-ns3-dcf:  ## [P7 F9] measure NS-3's DCF slot statistics -> results/raw/ns3_dcf_residual.csv
	$(BIN)/python ns3/dcf_residual.py --seeds 5
sim-ns3-sensitivity:  ## [P7] deployment-geometry sensitivity -> results/raw/ns3_sensitivity.csv
	$(BIN)/python ns3/sensitivity.py --seeds 3
export-framesizes:  ## P3 SYNC-3: placement×encoding×b frame sizes -> results/raw/framesizes.csv
	$(BIN)/python -m authbc.bench.framesizes
hw-capture:  ## P7b (this host): capture the Arduino INA219 stream -> results/hw/energy/samples-*.csv
	$(BIN)/python hw/ina219_capture.py --port $${PORT:-/dev/ttyACM0}

hw-reduce:  ## P7b (this host): reduce MANIFEST=… SAMPLES=… -> energy/op + CI
	$(BIN)/python hw/ina219_capture.py --reduce "$(MANIFEST)" "$(SAMPLES)"

figures:  ## regenerate E1-E3 figures from frozen results/raw -> results/figures/
	$(BIN)/python analysis/figures_e123.py
