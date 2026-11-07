#!/usr/bin/env python3
"""W1b: the contention model at 802.11b, 1 Mb/s, against ns-3 — Phase 0 of the 2.4 GHz campaign.

predictions/W1b.md. The boards available beyond the two Pi 4 are 2.4 GHz radios, and a Raspberry
Pi broadcasts there at 802.11b's 1 Mb/s and nothing else (F35). Before any board is used, the model
the hardware predictions will come from is put to the test the 6 Mb/s model passed (F5): the same
access rule with 802.11b's constants (`models/phy.DSSS_1M`, read from ns-3.48), nothing fitted,
against ns-3 at the paper's two frames. With it, A12's equivalence — five stations sending fast
standing for many sending slowly — is checked at 1 Mb/s, because the hardware will rely on it.

    python analysis/dsss_campaign.py --predict
        -> results/raw/w1b_predictions.csv, experiments/dsss/plan.txt (committed BEFORE ns-3)
    python ns3/run_links.py --plan experiments/dsss/plan.txt --stem w1b
    python analysis/dsss_campaign.py --score
        -> results/raw/w1b.csv
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
import run_links  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models.phy import DSSS_1M  # noqa: E402
from authbc.sim import dcf_own_queue as oq  # noqa: E402

RAW = REPO / "results" / "raw"
PLAN = REPO / "experiments" / "dsss" / "plan.txt"
PREDICTIONS = RAW / "w1b_predictions.csv"
RUNS = RAW / "ns3_links_w1b_runs.csv"
SCORED = RAW / "w1b.csv"
SEEDS = 30
V_TARGET = 0.95
SPLIT_N = 5                         # the boards the hardware has
CELLS = {"Pb1B": "C", "Pb1D": "D"}  # ns-3 cell -> the paper's name for it
TOLERANCE = 0.03                    # F5's, crossing against ns-3
RATIO_TOLERANCE = 0.3
SPLIT_TOLERANCE = 0.02              # A12's criterion (3)
GRID_POINTS = 7
RULE = oq.OwnQueueRule("802.11b", w_post=DSSS_1M.w0, w_defer=DSSS_1M.w0, slot_s=DSSS_1M.slot_s)


def cell(name: str) -> run_links.Cell:
    return run_links.CELLS[name]


def airtime_s(frame_bytes: int) -> float:
    return DSSS_1M.t_broadcast(frame_bytes) - DSSS_1M.difs_s


def closed_form(name: str) -> float:
    c = cell(name)
    return rule_check.closed_form_crossing(c.fps, DSSS_1M.t_broadcast(c.frame_bytes),
                                           w=DSSS_1M.w0, detect_s=2 * oq.DETECT_S)


def n_equivalent(n: int, fps: float, f0: float) -> float:
    """A12's mapping: the nodes at f0 that offer the same contending load, 1 + (n − 1)·f/f0."""
    return 1.0 + (n - 1) * fps / f0


def splits() -> list[tuple[str, str]]:
    """(split cell, its reference cell): the same frame at the reference cell's rate."""
    ref = {cell(r).frame_bytes: r for r in CELLS}
    return [(k, ref[c.frame_bytes]) for k, c in run_links.CELLS.items() if k.startswith("Pb1S")]


def _job(job: tuple[str, int, int]) -> tuple[str, int, float]:
    name, n, seed = job
    c = cell(name)
    r = oq.run(n, c.fps, airtime_s(c.frame_bytes), rule=RULE, seed=seed, difs_s=DSSS_1M.difs_s)
    return name, n, r.delivered_frac


def model_means(points: list[tuple[str, int]], workers: int) -> dict[tuple[str, int], float]:
    jobs = [(name, n, s) for name, n in points for s in range(1, SEEDS + 1)]
    with Pool(workers) as pool:
        got = pool.map(_job, jobs, chunksize=20)
    by: dict[tuple[str, int], list[float]] = {}
    for name, n, d in got:
        by.setdefault((name, n), []).append(d)
    return {k: st.mean(v) for k, v in by.items()}


def grid(centre: float, step: int, cover: tuple[float, ...] = ()) -> list[int]:
    """Seven points around the crossing, widened to cover every N_eq in `cover`."""
    first = round(centre) - step * (GRID_POINTS // 2)
    last = first + step * (GRID_POINTS - 1)
    while cover and first > min(cover):
        first -= step
    while cover and last < max(cover):
        last += step
    return list(range(first, last + 1, step))


def predict(workers: int) -> list[dict]:
    scans = {name: list(range(max(2, int(0.6 * closed_form(name))),
                              int(1.4 * closed_form(name)) + 2)) for name in CELLS}
    points = [(name, n) for name, ns in scans.items() for n in ns]
    points += [(s, SPLIT_N) for s, _ref in splits()]
    means = model_means(points, workers)
    rows = []
    x: dict[str, float] = {}
    for name, label in CELLS.items():
        curve = {n: means[(name, n)] for n in scans[name]}
        cross = interpolated_crossing(curve, V_TARGET)
        if cross is None:
            raise SystemExit(f"{name}: the scan does not bracket the crossing")
        x[name] = cross
        # per-record's grid in steps of 1 and AUTHBC's in steps of 3 cover every split's N_eq
        step = 1 if cross < 20 else 3
        rows.append({"what": "crossing", "cell": name, "label": label,
                     "frame_bytes": cell(name).frame_bytes, "fps": cell(name).fps, "n": "",
                     "n_eq": "", "reference_model": "",
                     "model": round(cross, 2), "closed_form": round(closed_form(name), 2),
                     "band_lo": round((1 - TOLERANCE) * cross, 2),
                     "band_hi": round((1 + TOLERANCE) * cross, 2),
                     "ns3_grid": " ".join(map(str, grid(cross, step, cover=tuple(
                         n_equivalent(SPLIT_N, cell(sp).fps, cell(ref).fps)
                         for sp, ref in splits() if ref == name))))})
    ratio = x["Pb1D"] / x["Pb1B"]
    rows.append({"what": "ratio", "cell": "D/C", "label": "", "frame_bytes": "", "fps": "",
                 "n": "", "n_eq": "", "reference_model": "", "model": round(ratio, 3),
                 "closed_form": round(closed_form("Pb1D") / closed_form("Pb1B"), 3),
                 "band_lo": round(ratio - RATIO_TOLERANCE, 3),
                 "band_hi": round(ratio + RATIO_TOLERANCE, 3), "ns3_grid": ""})
    for split, ref in splits():
        c, r = cell(split), cell(ref)
        neq = n_equivalent(SPLIT_N, c.fps, r.fps)
        curve = {n: means[(ref, n)] for n in scans[ref]}
        ref_v = _interpolate(curve, neq)
        rows.append({"what": "split", "cell": split, "label": f"{CELLS[ref]} at N_eq",
                     "frame_bytes": c.frame_bytes, "fps": c.fps, "n": SPLIT_N,
                     "n_eq": round(neq, 3), "reference_model": round(ref_v, 5),
                     "model": round(means[(split, SPLIT_N)], 5), "closed_form": "",
                     "band_lo": round(ref_v - SPLIT_TOLERANCE, 5),
                     "band_hi": round(ref_v + SPLIT_TOLERANCE, 5), "ns3_grid": str(SPLIT_N)})
    return rows


def _interpolate(curve: dict[int, float], x: float) -> float:
    lo = max(n for n in curve if n <= x)
    hi = min(n for n in curve if n >= x)
    if lo == hi:
        return curve[lo]
    return curve[lo] + (curve[hi] - curve[lo]) * (x - lo) / (hi - lo)


def write_plan(rows: list[dict]) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# W1b, predictions/W1b.md: the paper's frames at 802.11b, 1 Mb/s, and five\n",
             "# stations sending fast in place of many sending slowly. 30 seeds.\n",
             "#   python ns3/run_links.py --plan experiments/dsss/plan.txt --stem w1b\n"]
    for r in rows:
        if r["what"] == "crossing":
            lines.append(f"{r['cell']} {r['ns3_grid']}\n")
    # the reference curve must also cover every split's N_eq
    for r in rows:
        if r["what"] == "split":
            lines.append(f"{r['cell']} {SPLIT_N}\n")
    PLAN.write_text("".join(lines))


# ------------------------------------------------------------------------------------ scoring
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def ns3_means() -> dict[tuple[str, int], float]:
    per: dict[tuple[str, int], list[float]] = {}
    for r in _rows(RUNS):
        per.setdefault((r["cell"], int(r["n_nodes"])), []).append(float(r["delivered_frac"]))
    return {k: st.mean(v) for k, v in per.items() if len(v) == SEEDS}


def score() -> list[dict]:
    reg = {(r["what"], r["cell"]): r for r in _rows(PREDICTIONS)}
    means = ns3_means()
    out, x = [], {}
    for name in CELLS:
        curve = {n: v for (c, n), v in means.items() if c == name}
        measured = interpolated_crossing(curve, V_TARGET) if len(curve) >= 2 else None
        predicted = float(reg[("crossing", name)]["model"])
        x[name] = measured
        out.append({"what": "crossing", "cell": name, "predicted": predicted,
                    "ns3": round(measured, 2) if measured is not None else "",
                    "difference": round((measured - predicted) / predicted, 4)
                    if measured is not None else "",
                    "held": abs(measured - predicted) <= TOLERANCE * predicted
                    if measured is not None else ""})
    if x["Pb1B"] and x["Pb1D"]:
        ratio = x["Pb1D"] / x["Pb1B"]
        predicted = float(reg[("ratio", "D/C")]["model"])
        out.append({"what": "ratio", "cell": "D/C", "predicted": predicted,
                    "ns3": round(ratio, 3), "difference": round(ratio - predicted, 3),
                    "held": abs(ratio - predicted) <= RATIO_TOLERANCE})
    for split, ref in splits():
        if (split, SPLIT_N) not in means:
            continue
        curve = {n: v for (c, n), v in means.items() if c == ref}
        neq = n_equivalent(SPLIT_N, cell(split).fps, cell(ref).fps)
        if not curve or neq < min(curve) or neq > max(curve):
            out.append({"what": "split", "cell": split, "predicted": "", "ns3": "",
                        "difference": "", "held": "N_eq outside the ns-3 reference grid"})
            continue
        v_ref = _interpolate(curve, neq)
        v = means[(split, SPLIT_N)]
        out.append({"what": "split", "cell": split, "predicted": round(v_ref, 5),
                    "ns3": round(v, 5), "difference": round(v - v_ref, 5),
                    "held": abs(v - v_ref) <= SPLIT_TOLERANCE})
    return out


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "v_target": V_TARGET, "split_n": SPLIT_N, "tolerance": TOLERANCE,
              "ratio_tolerance": RATIO_TOLERANCE, "split_tolerance": SPLIT_TOLERANCE,
              "phy": DSSS_1M.name, "slot_s": DSSS_1M.slot_s, "difs_s": DSSS_1M.difs_s,
              "w0": DSSS_1M.w0, "detect_s": oq.DETECT_S}
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
        _write(PREDICTIONS, rows, "w1b_predictions")
        write_plan(rows)
    else:
        rows = score()
        _write(SCORED, rows, "w1b")
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v != ""))


if __name__ == "__main__":
    main()
