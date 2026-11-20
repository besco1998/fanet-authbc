#!/usr/bin/env python3
"""U-C7B (predictions/UC7B.md): the new 10 % cell, and every U-C7 cell again with per-node counts.

* **The new cell** `D10C8L120SF8`: N = 2 … 7, seeds 1–30.
* **Every U-C7 cell:** its stored 30-seed grid (the node counts with seeds 1–30 in
  `results/raw/uc7_<cell>_runs.csv`), run again with `--per-node`.
* **The identity check:** each rerun's totals must equal the stored row, run by run, or this
  exits non-zero (a stop).

    python ns3/run_uc7b.py [workers]
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "src"))

from uc7 import CELLS, CELLS_B  # noqa: E402

RAW = REPO / "results" / "raw"


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.open() if not ln.startswith("#")))


def grid(cell: str) -> list[int]:
    by: dict[int, set[int]] = {}
    for r in _rows(RAW / f"uc7_{cell.lower()}_runs.csv"):
        by.setdefault(int(r["n_devices"]), set()).add(int(r["seed"]))
    return sorted(n for n, seeds in by.items() if seeds >= set(range(1, 31)))


def run(cell: str, ns: list[int], workers: str) -> None:
    subprocess.run([sys.executable, str(REPO / "ns3" / "run_c7.py"), "--cell", cell, "--n",
                    *map(str, ns), "--seeds", "30", "--per-node", "--workers", workers],
                   check=True)


def identical(cell: str) -> tuple[int, int]:
    """(rows compared, rows differing) between the stored run and its per-node rerun."""
    stored = {(r["n_devices"], r["seed"]): r for r in _rows(RAW / f"uc7_{cell.lower()}_runs.csv")}
    again = _rows(RAW / f"uc7_{cell.lower()}_pn_runs.csv")
    bad = sum(stored[(r["n_devices"], r["seed"])][k] != r[k]
              for r in again for k in ("sent", "received"))
    return len(again), bad


def main() -> int:
    workers = sys.argv[1] if len(sys.argv) > 1 else "8"
    run(CELLS_B[0].name, list(range(2, 8)), workers)
    failed = []
    for c in CELLS:
        run(c.name, grid(c.name), workers)
        n, bad = identical(c.name)
        print(f"{c.name}: {n} reruns, {bad} totals differ", flush=True)
        if bad:
            failed.append(c.name)
    if failed:
        print(f"STOP: per-node reruns differ from the stored runs at {failed}", flush=True)
        return 1
    print("all per-node reruns reproduce their stored totals", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
