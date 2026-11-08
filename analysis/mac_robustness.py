#!/usr/bin/env python3
"""W1(a): does AUTHBC's capacity ratio survive a radio that does not keep the standard's rule?

predictions/W1a.md. Every capacity in the paper is that of a radio keeping the 802.11 access rule,
and no measured card does (Bianchi et al., INFOCOM 2007; F74 for ours). The deviation found most
often is a smaller contention window: CWmin 7 or 15 where 31 is required, which in 802.11a terms
is a window of 4 or 8 slots where the standard gives 16. This script predicts the crossings of
V = 0.95 for cell C (per-record signing) and cell D (AUTHBC) at those windows, by the closed form
of docs/02 §6g and by the event model, and scores ns-3 against them. It also predicts, in the
model only, the crossings under the rules calibrated on our own chip in G27.

    python analysis/mac_robustness.py --predict
        -> results/raw/w1a_predictions.csv and experiments/mac-robustness/plan_cw{3,7}.txt,
           committed BEFORE any ns-3 run
    python ns3/run_nmax_direct.py --plan experiments/mac-robustness/plan_cw7.txt --cw-min 7 \
        --out-stem ns3_w1a_cw7 --no-summary        (and cw3 with --cw-min 3)
    python analysis/mac_robustness.py --score
        -> results/raw/w1a.csv
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
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "ns3"))

import dcf_model_check as rule_check  # noqa: E402
import own_queue_rules as g27  # noqa: E402
import run_nmax_direct as drv  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402

RAW = REPO / "results" / "raw"
PLANS = REPO / "experiments" / "mac-robustness"
PREDICTIONS = RAW / "w1a_predictions.csv"
SCORED = RAW / "w1a.csv"
SEEDS = 30
V_TARGET = 0.95
CELLS = ("C", "D")
WINDOWS = (4, 8, 16)                # W = CWmin + 1; 16 is the standard and the control
NS3_WINDOWS = (4, 8)                # run in ns-3 (16 is the published campaign)
TOLERANCE = 0.03                    # F5's: the model's crossing against ns-3's
RATIO_BAND = (3.3, 3.8)             # S01's band for the ratio
GRID_POINTS = 7
GRID_STEP = {"C": 1, "D": 3}


def airtime_s(cell: str) -> float:
    return bianchi.t_broadcast(drv.CELLS[cell].frame_bytes) - oq.DIFS_S


def closed_form(cell: str, w: int) -> float:
    c = drv.CELLS[cell]
    return rule_check.closed_form_crossing(c.fps, bianchi.t_broadcast(c.frame_bytes), w=w)


def window_rule(w: int) -> oq.OwnQueueRule:
    return oq.OwnQueueRule(f"W{w}", w_post=w, w_defer=w)


def rule_sets() -> list[tuple[str, str, oq.OwnQueueRule]]:
    """(set, label, rule): the windows, then G27's rules as calibrated on our chip."""
    sets = [("window", f"W={w}", window_rule(w)) for w in WINDOWS]
    gaps = g27.measured_gaps_s()
    for state in ("on", "off"):
        for r in g27.candidates(gaps[state]["mean"]):
            sets.append((f"G27 {state}", f"{r.name} {g27.parameter(r)}", r))
    return sets


def scan(cell: str, centre: float, *, wide: bool = False) -> list[int]:
    """Node counts the model is run at. A window's crossing is near its closed form; a G27 rule
    can move it far from the standard's, so its scan runs from 0.3 to 1.2 times the standard's."""
    if wide:
        step = max(1, round(0.03 * centre))
        return list(range(max(2, int(0.3 * centre)), int(1.2 * centre) + step, step))
    step = GRID_STEP[cell]
    lo, hi = int(0.8 * centre), int(1.2 * centre) + 1
    return list(range(max(2, lo), hi + step, step))


def _model_job(job: tuple[str, int, oq.OwnQueueRule, int]) -> tuple[str, int, str, float]:
    cell, n, rule, seed = job
    c = drv.CELLS[cell]
    r = oq.run(n, c.fps, airtime_s(cell), rule=rule, seed=seed)
    return cell, n, repr(rule), r.delivered_frac


def model_crossings(sets: list[tuple[str, str, oq.OwnQueueRule]], workers: int
                    ) -> dict[tuple[str, str], tuple[float | None, dict[int, float]]]:
    """(label, cell) -> the event model's crossing of V_TARGET and its means over the scan."""
    jobs = []
    for name, _label, rule in sets:
        window = name == "window"
        for cell in CELLS:
            centre = closed_form(cell, rule.w_post if window else oq.W0)
            jobs += [(cell, n, rule, seed) for n in scan(cell, centre, wide=not window)
                     for seed in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_model_job, jobs, chunksize=20)
    by: dict[tuple[str, str, int], list[float]] = {}
    for cell, n, rep, d in got:
        by.setdefault((rep, cell, n), []).append(d)
    out = {}
    for _s, label, rule in sets:
        for cell in CELLS:
            means = {n: st.mean(v) for (rep, c, n), v in by.items()
                     if rep == repr(rule) and c == cell}
            out[(label, cell)] = (interpolated_crossing(means, V_TARGET), means)
    return out


def ns3_grid(cell: str, centre: float) -> list[int]:
    step = GRID_STEP[cell]
    first = round(centre) - step * (GRID_POINTS // 2)
    return [first + k * step for k in range(GRID_POINTS)]


def predict(workers: int) -> list[dict]:
    sets = rule_sets()
    got = model_crossings(sets, workers)
    rows = []
    for name, label, rule in sets:
        x = {cell: got[(label, cell)][0] for cell in CELLS}
        if any(v is None for v in x.values()):
            raise SystemExit(f"{label}: the scan does not bracket the crossing")
        w = rule.w_post if name == "window" else ""
        cf = {cell: closed_form(cell, int(w)) for cell in CELLS} if w else {}
        for cell in CELLS:
            row = {"set": name, "rule": label, "cell": cell,
                   "frame_bytes": drv.CELLS[cell].frame_bytes, "frames_per_s": drv.CELLS[cell].fps,
                   "model_crossing": round(x[cell], 2),
                   "closed_form_crossing": round(cf[cell], 2) if cf else "",
                   "band_lo": "", "band_hi": "", "ns3_grid": ""}
            if name == "window" and w in NS3_WINDOWS:
                row["band_lo"] = round((1 - TOLERANCE) * x[cell], 2)
                row["band_hi"] = round((1 + TOLERANCE) * x[cell], 2)
                row["ns3_grid"] = " ".join(map(str, ns3_grid(cell, x[cell])))
            rows.append(row)
        rows.append({"set": name, "rule": label, "cell": "D/C", "frame_bytes": "",
                     "frames_per_s": "", "model_crossing": round(x["D"] / x["C"], 3),
                     "closed_form_crossing": round(cf["D"] / cf["C"], 3) if cf else "",
                     "band_lo": RATIO_BAND[0] if w in NS3_WINDOWS else "",
                     "band_hi": RATIO_BAND[1] if w in NS3_WINDOWS else "", "ns3_grid": ""})
    return rows


def write_plans(rows: list[dict]) -> None:
    PLANS.mkdir(parents=True, exist_ok=True)
    for w in NS3_WINDOWS:
        lines = [f"# W1(a), predictions/W1a.md: window {w} slots (--cw-min {w - 1}), designated "
                 "source.\n",
                 f"#   python ns3/run_nmax_direct.py --plan <this file> --cw-min {w - 1} "
                 f"--out-stem ns3_w1a_cw{w - 1} --no-summary\n"]
        for r in rows:
            if r["set"] == "window" and r["rule"] == f"W={w}" and r["ns3_grid"]:
                lines.append(f"{r['cell']} period {r['ns3_grid']}\n")
        (PLANS / f"plan_cw{w - 1}.txt").write_text("".join(lines))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def ns3_crossing(w: int, cell: str) -> tuple[float | None, dict[int, float], dict[int, float]]:
    """ns-3's crossing, its means and per-seed spread; only node counts with all SEEDS runs."""
    path = RAW / f"ns3_w1a_cw{w - 1}_runs.csv"
    if not path.exists():
        return None, {}, {}
    per_n: dict[int, list[float]] = {}
    for r in _rows(path):
        if r["cell"] == cell:
            per_n.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
    full = {n: v for n, v in sorted(per_n.items()) if len(v) == SEEDS}
    means = {n: st.mean(v) for n, v in full.items()}
    sds = {n: st.stdev(v) for n, v in full.items()}
    return (interpolated_crossing(means, V_TARGET) if len(means) >= 2 else None), means, sds


def score() -> list[dict]:
    reg = {(r["rule"], r["cell"]): r for r in _rows(PREDICTIONS) if r["set"] == "window"}
    out = []
    for w in NS3_WINDOWS:
        x = {}
        for cell in CELLS:
            measured, means, _sds = ns3_crossing(w, cell)
            predicted = float(reg[(f"W={w}", cell)]["model_crossing"])
            x[cell] = measured
            out.append({"window": w, "cell": cell, "predicted": predicted,
                        "ns3": round(measured, 2) if measured is not None else "",
                        "error_pct": round(100 * (measured - predicted) / predicted, 2)
                        if measured is not None else "",
                        "within_band": abs(measured - predicted) <= TOLERANCE * predicted
                        if measured is not None else "", "points": len(means)})
        if x["C"] is not None and x["D"] is not None:
            ratio = x["D"] / x["C"]
            out.append({"window": w, "cell": "D/C",
                        "predicted": float(reg[(f"W={w}", "D/C")]["model_crossing"]),
                        "ns3": round(ratio, 3), "error_pct": "",
                        "within_band": RATIO_BAND[0] <= ratio <= RATIO_BAND[1], "points": ""})
    return out


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "v_target": V_TARGET, "windows": WINDOWS, "tolerance": TOLERANCE,
              "ratio_band": RATIO_BAND, "grid_points": GRID_POINTS, "grid_step": GRID_STEP,
              "slot_s": oq.SLOT_S, "difs_s": oq.DIFS_S, "detect_s": oq.DETECT_S}
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
        _write(PREDICTIONS, rows, "w1a_predictions")
        write_plans(rows)
    else:
        rows = score()
        _write(SCORED, rows, "w1a")
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
