#!/usr/bin/env python3
"""Capacity with the nodes spread out and capture at work (docs/NMAX_DIRECT_EXPECTATIONS.md, F7).

Every capacity of this work was simulated with all nodes at one point: equal received power,
so a frame that overlaps another is lost everywhere. A review of the paper named that scenario
as its weakest point (audit F80). This script registers, and later scores, the same two
configurations — the lean baseline (cell C) and the design (cell D) — with the nodes placed
uniformly in a disc and received power falling with distance as in free space:

    python analysis/spread_capacity.py --predict   # results/raw/spread_capacity_predictions.csv
    python analysis/spread_capacity.py --score     # results/raw/spread_capacity.csv

Two radii, and a different kind of prediction for each:

* **15 m.** Every pair is within energy-detection range, so every station senses every other
  exactly as in the published scenario and only the received powers differ. Prediction: the
  crossing of `authbc.sim.dcf_capture` (the access-rule model with the simulator's capture
  rule, nothing fitted), within ±5 %.
* **100 m.** A swarm's scale. Most pairs are below the energy-detection threshold, and a
  station that cannot lock onto either of two colliding frames may take the medium for idle;
  the model does not have that. Prediction: a bracket — no lower than the published
  equal-power crossing, no higher than the capture model's band.

The predictions file is committed before the runs it predicts. The ns-3 runs go to files of
their own, one per radius.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

import nmax_airtime_line as airtime  # noqa: E402
import run_nmax_direct as drv  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_capture as capture  # noqa: E402
from authbc.sim import dcf_unsaturated as access  # noqa: E402

RAW = REPO / "results" / "raw"
PREDICTIONS = RAW / "spread_capacity_predictions.csv"
OUT = RAW / "spread_capacity.csv"
V_TARGET = 0.95
SEEDS = 30
TOLERANCE = 0.05                    # the capture model's crossing against ns-3's, registered
PATH_LOSS_EXP = capture.EXPONENT


@dataclass(frozen=True)
class Case:
    """One configuration at one radius: what is predicted and where ns-3 is run."""
    name: str
    cell: str
    radius_m: float
    kind: str                       # "point": inside the model's band; "bracket": see module text
    scan: tuple[int, ...]           # node counts the model is run at
    ns3_grid: tuple[int, ...]       # node counts registered for ns-3

    @property
    def stem(self) -> str:
        return f"ns3_spread_r{self.radius_m:g}"


CASES: tuple[Case, ...] = (
    Case("C, 15 m", "C", 15.0, "point", tuple(range(34, 47, 2)), (37, 38, 39, 40, 41, 42, 43)),
    Case("D, 15 m", "D", 15.0, "point", tuple(range(120, 165, 8)),
         (128, 132, 136, 140, 144, 148, 152)),
    Case("C, 100 m", "C", 100.0, "bracket", tuple(range(34, 47, 2)),
         (33, 35, 37, 39, 41, 43, 45)),
    Case("D, 100 m", "D", 100.0, "bracket", tuple(range(120, 165, 8)),
         (116, 122, 128, 134, 140, 146, 152)),
)


def _one(job: tuple[str, float, int, int]) -> tuple[str, float, int, float]:
    cell, radius_m, n, seed = job
    c = drv.CELLS[cell]
    air = bianchi.t_broadcast(c.frame_bytes) - access.DIFS_S
    return cell, radius_m, n, capture.run(n, c.fps, air, radius_m=radius_m, seed=seed)


def model_crossings(workers: int) -> dict[str, float]:
    """The capture model's crossing of 0.95 for each case: thirty seeds per node count."""
    jobs = [(c.cell, c.radius_m, n, s) for c in CASES for n in c.scan
            for s in range(1, SEEDS + 1)]
    runs: dict[tuple[str, float, int], list[float]] = {}
    with Pool(workers) as pool:
        for cell, radius_m, n, d in pool.imap_unordered(_one, jobs, chunksize=10):
            runs.setdefault((cell, radius_m, n), []).append(d)
    out = {}
    for c in CASES:
        means = {n: st.mean(runs[(c.cell, c.radius_m, n)]) for n in c.scan}
        x = interpolated_crossing(means, V_TARGET)
        if x is None:
            raise SystemExit(f"{c.name}: the model's scan does not bracket the crossing")
        out[c.name] = x
    return out


def equal_power_crossings() -> dict[str, float]:
    """ns-3's crossing in the published scenario, per cell (results/raw/ns3_nmax_direct.csv)."""
    rows = airtime.crossings("period")
    return {cell: float(rows[cell]["n_cross_interp"]) for cell in {c.cell for c in CASES}}


def predict(workers: int) -> list[dict]:
    model, published = model_crossings(workers), equal_power_crossings()
    rows = []
    for c in CASES:
        x, base = model[c.name], published[c.cell]
        hi = (1 + TOLERANCE) * x
        lo = (1 - TOLERANCE) * x if c.kind == "point" else base
        cell = drv.CELLS[c.cell]
        rows.append({"case": c.name, "cell": c.cell, "radius_m": f"{c.radius_m:g}",
                     "path_loss_exp": f"{PATH_LOSS_EXP:g}", "kind": c.kind,
                     "frame_bytes": cell.frame_bytes, "frames_per_s": cell.fps,
                     "threshold_db": f"{capture.THRESHOLD_DB:g}",
                     "equal_power_crossing": base, "model_crossing": round(x, 2),
                     "predicted_lo": round(lo, 2), "predicted_hi": round(hi, 2),
                     "model_gain_pct": round(100.0 * (x / base - 1.0), 1),
                     "ns3_grid": " ".join(map(str, c.ns3_grid)), "ns3_stem": c.stem})
    return rows


def registered() -> dict[str, dict[str, str]]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        return {r["case"]: r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


def ns3_crossing(case: Case) -> dict | None:
    """The CROSSING row of a case from its radius's runs file; None until the file exists."""
    path = RAW / f"{case.stem}_runs.csv"
    if not path.exists():
        return None
    rows = [r for r in drv.summarise(drv.read_runs(path), SEEDS)
            if r["n_nodes"] == "CROSSING" and r["cell"] == case.cell]
    return rows[0] if rows else None


def score() -> list[dict]:
    """Each registered prediction against ns-3. A case is scored only when every registered
    node count holds thirty seeds and its crossing is bracketed by them."""
    out = []
    reg = registered()
    for c in CASES:
        r = ns3_crossing(c)
        if r is None or r.get("grid") != reg[c.name]["ns3_grid"]:
            continue
        if r.get("bracketed") != 1 or r.get("n_cross_interp") in (None, ""):
            continue
        measured = float(r["n_cross_interp"])
        lo, hi = float(reg[c.name]["predicted_lo"]), float(reg[c.name]["predicted_hi"])
        model, base = float(reg[c.name]["model_crossing"]), \
            float(reg[c.name]["equal_power_crossing"])
        out.append({"case": c.name, "cell": c.cell, "radius_m": reg[c.name]["radius_m"],
                    "kind": c.kind, "ns3_crossing": measured,
                    "ns3_lo": r["n_cross_interp_lo"], "ns3_hi": r["n_cross_interp_hi"],
                    "n_max": r["n_max_mean"], "n_max_per_run": r["n_max_per_run"],
                    "predicted_lo": lo, "predicted_hi": hi,
                    "within_prediction": int(lo <= measured <= hi),
                    "model_crossing": model,
                    "vs_model_pct": round(100.0 * (measured - model) / model, 2),
                    "equal_power_crossing": base,
                    "vs_equal_power_pct": round(100.0 * (measured - base) / base, 2),
                    "grid": r["grid"]})
    return out


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "level": V_TARGET, "tolerance": TOLERANCE,
              "threshold_db": capture.THRESHOLD_DB, "exponent": PATH_LOSS_EXP,
              "cases": {c.name: (c.cell, c.radius_m, c.kind, c.ns3_grid) for c in CASES}}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


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
        _write(PREDICTIONS, rows, "spread_capacity_predictions")
        for r in rows:
            print(f"{r['case']:9} ({r['kind']:7}): equal power {r['equal_power_crossing']}, "
                  f"capture model {r['model_crossing']} (+{r['model_gain_pct']} %), "
                  f"predicted [{r['predicted_lo']}, {r['predicted_hi']}]")
        return
    rows = score()
    if not rows:
        raise SystemExit("no case has a complete, bracketed grid on file yet")
    _write(OUT, rows, "spread_capacity")
    for r in rows:
        print(f"{r['case']:9}: ns-3 {r['ns3_crossing']} [{r['ns3_lo']}, {r['ns3_hi']}] — "
              f"predicted [{r['predicted_lo']}, {r['predicted_hi']}]: "
              f"{'inside' if r['within_prediction'] else 'OUTSIDE'}; "
              f"{r['vs_model_pct']:+.2f} % from the model, "
              f"{r['vs_equal_power_pct']:+.2f} % from equal power")


if __name__ == "__main__":
    main()
