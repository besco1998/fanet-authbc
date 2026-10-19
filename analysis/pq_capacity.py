#!/usr/bin/env python3
"""Revision A15 — a post-quantum signature in the frame: Falcon-512 (predictions/A15.md).

The paper concludes that post-quantum signatures do not fit, having checked only ML-DSA
(2 420 B). Falcon-512 in its padded form signs in a fixed 666 B (liboqs 0.16.0,
`OQS_SIG_falcon_padded_512_length_signature`). This script

    python analysis/pq_capacity.py --predict   # results/raw/pq_capacity_predictions.csv
    python analysis/pq_capacity.py --score     # results/raw/pq_capacity.csv

emits the lean frame with a 666 B signature (one record, and four), predicts both capacities
three ways — the paper's airtime line (Eq. 6, fitted on frames of 0.3–0.85 ms), the closed form
and the access-rule model (no fitted constant) — and scores them against ns-3 cells `PQ1`,
`PQ4` (`ns3/run_nmax_direct.py --plan experiments/pq/plan.txt --out-stem ns3_pq`).
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

import dcf_model_check as rule  # noqa: E402
import design_map as dm  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.models import bianchi  # noqa: E402

RAW = REPO / "results" / "raw"
PREDICTIONS = RAW / "pq_capacity_predictions.csv"
OUT = RAW / "pq_capacity.csv"
STEM = "ns3_pq"
FALCON_SIG = 666                       # Falcon-padded-512, liboqs 0.16.0
LINE_A, LINE_C = 0.0710, 8e-6          # Eq. (6), as fitted (docs/02 §6e)
TOLERANCE = 0.03                       # the access-rule model's registered band
LAMBDA = 50.0
CELLS = {"PQ1": 1, "PQ4": 4}


def frame_bytes(batch: int) -> float:
    return leanframes.lean_frame_sizes(batch, sig_bytes=FALCON_SIG).mean


def predict(workers: int) -> list[dict]:
    configs = {cell: (LAMBDA / b, float(round(frame_bytes(b)))) for cell, b in CELLS.items()}
    model = dm.model_crossings(list(configs.values()), workers)
    rows = []
    for cell, b in CELLS.items():
        fps, fb = configs[cell]
        t = bianchi.t_broadcast(fb)
        x = model[(fps, fb)]
        step = max(1, round(0.025 * x))
        rows.append({
            "cell": cell, "batch": b, "frame_bytes_mean": round(frame_bytes(b), 3),
            "frame_bytes": int(fb), "frames_per_s": fps, "frame_time_us": round(1e6 * t, 1),
            "line_crossing": round(0.05 / (fps * (LINE_A * t + LINE_C)), 2),
            "closed_form_crossing": round(rule.closed_form_crossing(fps, t), 2),
            "model_crossing": round(x, 2),
            "model_lo": round((1 - TOLERANCE) * x, 2), "model_hi": round((1 + TOLERANCE) * x, 2),
            "ns3_grid": " ".join(str(round(x) + k * step) for k in range(-3, 4))})
    return rows


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"sig": FALCON_SIG, "cells": CELLS, "tolerance": TOLERANCE}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def score() -> list[dict]:
    import run_nmax_direct as drv
    with PREDICTIONS.open(encoding="utf-8") as fh:
        reg = {r["cell"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}
    runs = drv.read_runs(RAW / f"{STEM}_runs.csv")
    crossing = {r["cell"]: r for r in drv.summarise(runs, 30) if r["n_nodes"] == "CROSSING"}
    out = []
    for cell, r in reg.items():
        c = crossing.get(cell)
        if c is None or c.get("grid") != r["ns3_grid"] or c.get("bracketed") != 1:
            continue
        got = float(c["n_cross_interp"])
        out.append({**r, "ns3_crossing": got, "ns3_lo": c["n_cross_interp_lo"],
                    "ns3_hi": c["n_cross_interp_hi"], "n_max": c["n_max_mean"],
                    "vs_model_pct": round(100 * (got / float(r["model_crossing"]) - 1), 2),
                    "vs_line_pct": round(100 * (got / float(r["line_crossing"]) - 1), 2),
                    "in_model_band": int(abs(got / float(r["model_crossing"]) - 1) <= TOLERANCE)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    rows = predict(args.workers) if args.predict else score()
    if not rows:
        raise SystemExit("nothing to score yet")
    _write(PREDICTIONS if args.predict else OUT, rows,
           "pq_capacity_predictions" if args.predict else "pq_capacity")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
