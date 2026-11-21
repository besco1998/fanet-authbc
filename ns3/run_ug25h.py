#!/usr/bin/env python3
"""U-G25H runs (predictions/UG25H.md): per cell, a pilot of 5 seeds on seven node counts at ±5 %
steps around the (G25) root, then 30 seeds (1–30) on seven node counts by U-C2's rule around the
pilot's crossing of 1 − ε (centre rounded, step max(1, round(2 % of the centre))).

    python ns3/run_ug25h.py [workers]
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import ug25h  # noqa: E402

from authbc.bench.stats import interpolated_crossing  # noqa: E402

RAW = REPO / "results" / "raw"


def drive(cell: str, stem: str, workers: str, level: float, *args: str) -> None:
    subprocess.run([sys.executable, str(REPO / "ns3" / "run_unified.py"), "--cells", cell,
                    "--stem", stem, "--levels", repr(level), "--workers", workers, *args],
                   check=True)


def pilot_crossing(stem: str, level: float) -> float | None:
    by: dict[int, list[float]] = {}
    for r in csv.DictReader(ln for ln in (RAW / f"{stem}_runs.csv").open()
                            if not ln.startswith("#")):
        by.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
    return interpolated_crossing({n: sum(v) / len(v) for n, v in by.items() if len(v) >= 5},
                                 level)


def main() -> int:
    workers = sys.argv[1] if len(sys.argv) > 1 else "10"
    pred = {r["cell"]: r for r in ug25h.predictions()}
    for name, (_c, eps) in ug25h.CELLS.items():
        level = round(1 - eps, 6)
        root = float(pred[name]["g25_root"])                    # type: ignore[arg-type]
        drive(name, f"ug25h_pilot_{name.lower()}", workers, level, "--pilot", "--center",
              repr(root))
        x = pilot_crossing(f"ug25h_pilot_{name.lower()}", level)
        c = round(x if x is not None else root)
        step = max(1, round(0.02 * c))
        ns = [c + k * step for k in range(-3, 4)]
        print(f"{name}: pilot crossing {x} -> N {ns}", flush=True)
        drive(name, f"ug25h_{name.lower()}", workers, level, "--n", *map(str, ns), "--seeds",
              "30")
    print("all U-G25H runs done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
