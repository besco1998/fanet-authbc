# fanet-authbc

Co-optimizing **encoding × authentication placement × signature scheme × batching** for
blockchain-grade UAV telemetry ledgers over 802.11 FANET links (LoRa arm later). This repo
is the reproducible testbed for the AUTHBC thesis (owner: Mohamed A. Farouk).

Full specification lives in [`docs/`](docs/) (charter `docs/00`, system model `docs/01`,
math `docs/02`, implementation guide `docs/03`, evaluation `docs/04`, agent KB `docs/06`,
parallel plan `docs/07`). Agent standing policy: [`CLAUDE.md`](CLAUDE.md). Phase prompts:
[`docs/prompts/`](docs/prompts/).

## Quickstart

```bash
make setup     # create .venv (Python 3.12) and install pinned deps + pre-commit
make test      # unit / property / integration tests
make lint      # ruff
make all       # lint + test
```

`make setup` requires Python **3.12+** (`PYTHON` overridable, e.g. `make setup PYTHON=python`).
Benchmarks (`bench-*`), experiments (`exp-e1..e5`), NS-3 (`sim-ns3`), and figures run
locally in later phases and commit their CSVs; CI runs setup + lint + tests only.

## Status

Phase **P0** (bootstrap). See [`docs/status/lane1.md`](docs/status/lane1.md) for the latest
handoff and [`docs/audits/`](docs/audits/) for phase audits.
