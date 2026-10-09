#!/usr/bin/env python3
"""The batch size as a dimension of the capacity (docs/NMAX_DIRECT_EXPECTATIONS.md, follow-up F6).

Every capacity simulated before this one is of a frame of one record or of four, because both
operating points have Λ·D_max = 5 (audit F80, open item G31). The airtime line and the
access-rule model were therefore checked across frame size and frame rate, never across the
batch itself. This script registers, and later scores, the lean design with two, three and
eight records to a frame at 50 records/s — what deadlines of 60, 80 and 180 ms would admit:

    python analysis/batch_capacity.py --predict   # results/raw/batch_capacity_predictions.csv
    python analysis/batch_capacity.py --score     # results/raw/batch_capacity.csv

Two predictions per cell, both made with what was fixed before any of these runs:

* the airtime line, with the slope calibrated on cells A–F and nothing re-fitted
  (`analysis/nmax_airtime_line.py`), within its registered ±6 %;
* the access-rule model, which has no fitted constant (`authbc.sim.dcf_unsaturated`), within
  its registered ±3 %.

The predictions file is committed before the runs it predicts. The ns-3 runs go to a file of
their own, `results/raw/ns3_batch_runs.csv`, so no reported sample is touched.
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
import nmax_airtime_line as airtime  # noqa: E402
import run_nmax_direct as drv  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402

RAW = REPO / "results" / "raw"
STEM = "ns3_batch"
PREDICTIONS = RAW / "batch_capacity_predictions.csv"
OUT = RAW / "batch_capacity.csv"
V_TARGET = 0.95
SEEDS = 30
LINE_TOLERANCE = airtime.TOLERANCE      # 0.06, as registered for F2 and F3
MODEL_TOLERANCE = rule.TOLERANCE        # 0.03, as registered for F5
# cell -> (node counts the model is scanned at, node counts registered for ns-3)
GRIDS: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {
    "B2": (tuple(range(58, 76, 2)), (60, 62, 64, 66, 68, 70, 72)),
    "B3": (tuple(range(84, 111, 3)), (87, 90, 93, 96, 99, 102, 105)),
    "B8": (tuple(range(198, 255, 7)), (205, 212, 219, 226, 233, 240, 247)),
}


def deadline_ms(cell: str) -> float:
    """The smallest freshness bound that admits this batch: (b + 1) record periods."""
    c = drv.CELLS[cell]
    return 1000.0 * (c.batch + 1) / c.lam


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "level": V_TARGET, "line_tolerance": LINE_TOLERANCE,
              "model_tolerance": MODEL_TOLERANCE, "grids": {k: v[1] for k, v in GRIDS.items()}}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def predict(workers: int) -> list[dict]:
    """Both predictions for each cell, from nothing that these runs can change."""
    slope, _ = airtime.calibrate(airtime.crossings("period"))
    line = airtime.predictions(slope, tuple(GRIDS))
    got = rule.model_means([(cell, n, rule.model.W0) for cell, (scan, _) in GRIDS.items()
                            for n in scan], workers)
    rows = []
    for cell, (scan, grid) in GRIDS.items():
        c = drv.CELLS[cell]
        means = {n: got[(cell, n, rule.model.W0)]["delivered"] for n in scan}
        model_x = interpolated_crossing(means, V_TARGET)
        if model_x is None:
            raise SystemExit(f"{cell}: the model's scan does not bracket the crossing")
        rows.append({
            "cell": cell, "batch": c.batch, "deadline_ms": f"{deadline_ms(cell):g}",
            "frame_bytes": c.frame_bytes, "frames_per_s": round(c.fps, 4),
            "frame_time_us": round(1e6 * bianchi.t_broadcast(c.frame_bytes), 1),
            "line_slope": round(slope, 4), "line_crossing": round(line[cell], 2),
            "line_lo": round((1 - LINE_TOLERANCE) * line[cell], 2),
            "line_hi": round((1 + LINE_TOLERANCE) * line[cell], 2),
            "model_crossing": round(model_x, 2),
            "model_lo": round((1 - MODEL_TOLERANCE) * model_x, 2),
            "model_hi": round((1 + MODEL_TOLERANCE) * model_x, 2),
            "single_ceiling": c.model_n, "ns3_grid": " ".join(map(str, grid)),
            "ns3_stem": STEM})
    return rows


def registered() -> dict[str, dict[str, str]]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        return {r["cell"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def ns3_crossings() -> dict[str, dict]:
    """The CROSSING row of each cell from its own runs file; empty until the runs exist.

    `run_nmax_direct.summarise` admits a node count only once all thirty seeds are on file, so
    an unfinished campaign cannot be scored against the threshold on a short sample.
    """
    path = RAW / f"{STEM}_runs.csv"
    if not path.exists():
        return {}
    return {r["cell"]: r for r in drv.summarise(drv.read_runs(path), SEEDS)
            if r["n_nodes"] == "CROSSING" and r["cell"] in GRIDS}


def score() -> list[dict]:
    """Each registered prediction against ns-3. A cell whose crossing its grid does not bracket
    is left out, so an incomplete or mis-placed campaign cannot pass."""
    out = []
    for cell, r in ns3_crossings().items():
        if r.get("bracketed") != 1 or r.get("n_cross_interp") in (None, ""):
            continue
        reg = registered()[cell]
        measured = float(r["n_cross_interp"])
        line, model = float(reg["line_crossing"]), float(reg["model_crossing"])
        out.append({
            "cell": cell, "batch": reg["batch"], "frame_bytes": reg["frame_bytes"],
            "frames_per_s": reg["frames_per_s"], "ns3_crossing": measured,
            "ns3_lo": r["n_cross_interp_lo"], "ns3_hi": r["n_cross_interp_hi"],
            "n_max": r["n_max_mean"], "n_max_ci_lo": r["n_max_ci_lo"],
            "n_max_ci_hi": r["n_max_ci_hi"], "n_max_per_run": r["n_max_per_run"],
            "line_crossing": line,
            "vs_line_pct": round(100.0 * (measured - line) / line, 2),
            "line_within_band": int(abs(measured - line) <= LINE_TOLERANCE * line),
            "model_crossing": model,
            "vs_model_pct": round(100.0 * (measured - model) / model, 2),
            "model_within_band": int(abs(measured - model) <= MODEL_TOLERANCE * model),
            "single_ceiling": reg["single_ceiling"],
            "vs_ceiling_pct": round(100.0 * (measured - float(reg["single_ceiling"]))
                                    / float(reg["single_ceiling"]), 2),
            "grid": r["grid"]})
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
        _write(PREDICTIONS, rows, "batch_capacity_predictions")
        for r in rows:
            print(f"{r['cell']}: b = {r['batch']}, {r['frame_bytes']} B at "
                  f"{r['frames_per_s']} /s — "
                  f"line {r['line_crossing']} [{r['line_lo']}, {r['line_hi']}], "
                  f"model {r['model_crossing']} [{r['model_lo']}, {r['model_hi']}], "
                  f"single ceiling {r['single_ceiling']}")
        return
    rows = score()
    if not rows:
        raise SystemExit("no cell has a bracketed crossing on file yet")
    _write(OUT, rows, "batch_capacity")
    for r in rows:
        print(f"{r['cell']}: ns-3 {r['ns3_crossing']} [{r['ns3_lo']}, {r['ns3_hi']}], N_max "
              f"{r['n_max']} — line {r['line_crossing']} ({r['vs_line_pct']:+.2f} %, "
              f"{'in' if r['line_within_band'] else 'OUT OF'} band), model {r['model_crossing']} "
              f"({r['vs_model_pct']:+.2f} %, {'in' if r['model_within_band'] else 'OUT OF'} band)")


if __name__ == "__main__":
    main()
