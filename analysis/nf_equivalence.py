#!/usr/bin/env python3
"""Revision A12 — can few radios sending fast stand in for many sending slowly?

The plan's hardware capacity test (B2) needs it: eight radios cannot be 124 nodes unless the
delivered fraction depends on the total offered frame rate N·f and not on how it is split. This
keeps N·f fixed at each crossing of the paper and varies the split (predictions/A12.md):

    design (173 B): (N, f) = (124, 12.5), (62, 25), (31, 50), (16, 97), (8, 194)    N·f ≈ 1 550
    base   (146 B): (N, f) = (70, 25), (35, 50), (18, 97.5), (9, 195), (5, 350)    N·f ≈ 1 750

    python analysis/nf_equivalence.py --predict   # results/raw/nf_equivalence_predictions.csv
    python analysis/nf_equivalence.py --score     # results/raw/nf_equivalence.csv

Prediction: the access-rule model (`authbc.sim.dcf_unsaturated`, nothing fitted), 30 seeds at
each split. Reference curve for the (N−1)/N correction: the same configuration at its paper
rate, from the published runs (design) and from this campaign's extra base cell at N = 29.
ns-3: `ns3/run_nmax_direct.py --plan experiments/nf-equivalence/plan.txt --out-stem
ns3_nf_equivalence`, the published source (send instant redrawn in each period), 30 seeds.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
PREDICTIONS = RAW / "nf_equivalence_predictions.csv"
OUT = RAW / "nf_equivalence.csv"
STEM = "ns3_nf_equivalence"
SEEDS = 30
# (ns-3 cell, frame bytes, N, frames/s per node); the reference split of each group first
SPLITS: tuple[tuple[str, int, int, float], ...] = (
    ("D", 173, 124, 12.5), ("NFD25", 173, 62, 25.0), ("NFD50", 173, 31, 50.0),
    ("NFD97", 173, 16, 97.0), ("NFD194", 173, 8, 194.0),
    ("NFB25", 146, 70, 25.0), ("C", 146, 35, 50.0), ("NFB97", 146, 18, 97.5),
    ("NFB195", 146, 9, 195.0), ("NFB350", 146, 5, 350.0),
)
REFERENCE = {173: 12.5, 146: 50.0}     # the paper's frame rate for each frame


def n_equivalent(n: int, fps: float, frame: int) -> float:
    """Nodes at the paper's rate that offer the same CONTENDING load: each of the N nodes
    contends with the other N − 1, whose load is (N − 1)·f."""
    return 1.0 + (n - 1) * fps / REFERENCE[frame]


def _one(job: tuple[int, float, int, int]) -> tuple[int, float, int, float]:
    n, fps, frame, seed = job
    return n, fps, frame, model.run(n, fps, bianchi.t_broadcast(frame) - model.DIFS_S,
                                    seed=seed).delivered_frac


def predict(workers: int) -> list[dict]:
    jobs = [(n, f, fb, s) for _, fb, n, f in SPLITS for s in range(1, SEEDS + 1)]
    got: dict[tuple[int, float, int], list[float]] = {}
    with Pool(workers) as pool:
        for n, f, fb, d in pool.imap_unordered(_one, jobs, chunksize=4):
            got.setdefault((n, f, fb), []).append(d)
    rows = []
    for cell, fb, n, f in SPLITS:
        v = st.mean(got[(n, f, fb)])
        rows.append({"ns3_cell": cell, "frame_bytes": fb, "n_nodes": n, "frames_per_s": f,
                     "offered_frames_per_s": round(n * f, 2),
                     "n_equivalent": round(n_equivalent(n, f, fb), 2),
                     "model_delivered": round(v, 5),
                     "band_lo": round(v - 0.005, 5), "band_hi": round(v + 0.005, 5)})
    return rows


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"splits": SPLITS, "seeds": SEEDS, "reference": REFERENCE}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def _means(path: Path, cell_n: set[tuple[str, int]]) -> dict[tuple[str, int], float]:
    """30-seed mean delivered fraction per (cell, N), period jitter only."""
    import run_nmax_direct as drv
    got: dict[tuple[str, int], list[float]] = {}
    for r in drv.read_runs(path):
        key = (r["cell"], int(r["n_nodes"]))
        jitter = drv.provenance.as_written(drv.one_period_ms(drv.CELLS[r["cell"]].fps))
        if key in cell_n and float(r["jitter_ms"]) == jitter:
            got.setdefault(key, []).append(float(r["delivered_frac"]))
    return {k: st.mean(v) for k, v in got.items() if len(v) == SEEDS}


def reference_curve(frame: int) -> dict[int, float]:
    """The paper's configuration at its own rate, 30 seeds: the published runs for the design,
    and for the base the published runs plus this campaign's N = 29."""
    cell = "D" if frame == 173 else "C"
    pub = RAW / "ns3_nmax_direct_runs.csv"
    import run_nmax_direct as drv
    ns = {int(r["n_nodes"]) for r in drv.read_runs(pub) if r["cell"] == cell}
    curve = {n: v for (_, n), v in _means(pub, {(cell, n) for n in ns}).items()}
    if frame == 146:
        curve |= {n: v for (_, n), v in _means(RAW / f"{STEM}_runs.csv", {("C", 29)}).items()}
    return curve


def interpolate(curve: dict[int, float], x: float) -> float | None:
    lo = max((n for n in curve if n <= x), default=None)
    hi = min((n for n in curve if n >= x), default=None)
    if lo is None or hi is None:
        return None
    return curve[lo] if hi == lo else curve[lo] + (curve[hi] - curve[lo]) * (x - lo) / (hi - lo)


def score() -> list[dict]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        reg = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    got = _means(RAW / f"{STEM}_runs.csv", {(r["ns3_cell"], int(r["n_nodes"])) for r in reg})
    rows = []
    for frame in (173, 146):
        group = [r for r in reg if int(r["frame_bytes"]) == frame]
        ref_key = (group[0]["ns3_cell"], int(group[0]["n_nodes"]))
        if ref_key not in got:
            continue
        curve = reference_curve(frame)
        for r in group:
            key = (r["ns3_cell"], int(r["n_nodes"]))
            if key not in got:
                continue
            v = got[key]
            at_eq = interpolate(curve, float(r["n_equivalent"]))
            rows.append({**r, "ns3_delivered": round(v, 5),
                         "vs_reference_split": round(v - got[ref_key], 5),
                         "vs_model": round(v - float(r["model_delivered"]), 5),
                         "in_model_band": int(abs(v - float(r["model_delivered"])) <= 0.005),
                         "reference_at_n_equivalent": "" if at_eq is None else round(at_eq, 5),
                         "vs_corrected": "" if at_eq is None else round(v - at_eq, 5)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--predict", action="store_true")
    what.add_argument("--score", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    rows = predict(args.workers) if args.predict else score()
    if not rows:
        raise SystemExit("nothing to score yet")
    _write(PREDICTIONS if args.predict else OUT, rows,
           "nf_equivalence_predictions" if args.predict else "nf_equivalence")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
