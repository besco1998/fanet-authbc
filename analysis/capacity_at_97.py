#!/usr/bin/env python3
"""Capacity at 97 % delivery, the loss the paper's own margin rule requires (review 2026-10-27,
item S-01; predictions/S01.md).

The headline capacities are crossings of 95 % delivery, the zero-margin point of the
verifiability target (Sec. Loss: epsilon >= p + 0.02, so p <= 0.03 at epsilon = 0.05). This adds
the crossing of 97 % for per-record signing (cell C) and AUTHBC (cell D), predicted first by the
contention model of `dcf_model_check.py` and then simulated in ns-3 on the registered grid.

    python analysis/capacity_at_97.py --predict   # results/raw/capacity_97_predictions.csv
    python analysis/capacity_at_97.py --score     # results/raw/capacity_97.csv, once ns-3 has run
        ns-3: python ns3/run_nmax_direct.py --plan experiments/nmax-direct/plan_level97.txt \
              --out-stem ns3_level97 --no-summary
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import dcf_model_check as mc  # noqa: E402

RAW = REPO / "results" / "raw"
LEVEL = 0.97
CASES: tuple[mc.Case, ...] = (
    mc.Case("C, 3 % loss", "C", 16, LEVEL, tuple(range(20, 34)), (25, 26, 27, 28, 29, 30, 31),
            "ns3_level97"),
    mc.Case("D, 3 % loss", "D", 16, LEVEL, tuple(range(80, 116, 3)), (86, 89, 92, 95, 98, 101,
                                                                    104), "ns3_level97"),
)


def predict(workers: int) -> list[dict]:
    drv = mc._driver()
    got = mc.model_means([(c.cell, n, c.w0) for c in CASES for n in c.scan], workers)
    rows = []
    for c in CASES:
        cell = drv.CELLS[c.cell]
        x = mc.interpolated_crossing({n: got[(c.cell, n, c.w0)]["delivered"] for n in c.scan},
                                     c.level)
        if x is None:
            raise SystemExit(f"{c.name}: the scan does not bracket the {c.level} crossing")
        rows.append({"case": c.name, "cell": c.cell, "frame_bytes": cell.frame_bytes,
                     "frames_per_s": cell.fps, "window_slots": c.w0, "delivered_level": c.level,
                     "model_crossing": round(x, 2),
                     "band_lo": round((1 - mc.TOLERANCE) * x, 2),
                     "band_hi": round((1 + mc.TOLERANCE) * x, 2),
                     "ns3_grid": " ".join(map(str, c.ns3_grid)), "ns3_stem": c.stem})
    return rows


def score() -> list[dict]:
    with (RAW / "capacity_97_predictions.csv").open(encoding="utf-8") as fh:
        registered = {r["case"]: r for r in csv.DictReader(ln for ln in fh
                                                           if not ln.startswith("#"))}
    out = []
    for c in CASES:
        measured, means = mc.ns3_crossing(c)
        if measured is None:
            raise SystemExit(f"{c.name}: ns-3 has not bracketed the crossing yet")
        predicted = float(registered[c.name]["model_crossing"])
        out.append({"case": c.name, "cell": c.cell, "delivered_level": c.level,
                    "predicted": predicted, "ns3_crossing": round(measured, 2),
                    "error_pct": round(100.0 * (measured - predicted) / predicted, 2),
                    "within_band": int(abs(measured - predicted) <= mc.TOLERANCE * predicted),
                    "points": len(means)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.predict:
        rows = predict(args.workers)
        mc._write(RAW / "capacity_97_predictions.csv", rows, "capacity_97_predictions")
    else:
        rows = score()
        mc._write(RAW / "capacity_97.csv", rows, "capacity_97")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
