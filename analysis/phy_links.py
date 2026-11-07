#!/usr/bin/env python3
"""Revision A11 — the design on other 802.11 PHYs and rates (predictions/A11.md).

Every capacity of the paper is at 802.11a, 6 Mb/s. Here the baseline (146 B, 50 frames/s) and
the design (173 B, 12.5 /s) are simulated at 802.11a 6, 12, 24 Mb/s and 802.11p (10 MHz) 3, 6,
12 Mb/s (`ns3/authbc-links.cc`, the published scenario with `--standard`/`--dataMode`; the
broadcast rate is set with NonUnicastMode, which ns-3 otherwise leaves at the first basic rate).
802.11p runs under the same ad-hoc, non-QoS DCF as the baseline: OCB's EDCA categories are not
modelled (ns-3.48 has no OCB MAC; stated substitution).

Prediction: the access-rule model (`authbc.sim.dcf_unsaturated`, nothing fitted) with each PHY's
own slot, DIFS and frame airtime (`authbc.models.phy`), 30 seeds per point.

    python analysis/phy_links.py --predict   # results/raw/phy_links_predictions.csv
    python analysis/phy_links.py --score     # results/raw/phy_links.csv
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
sys.path.insert(0, str(REPO / "analysis"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing, interpolated_crossing_ci  # noqa: E402
from authbc.models import bianchi, phy  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
PREDICTIONS = RAW / "phy_links_predictions.csv"
OUT = RAW / "phy_links.csv"
STEM = "phy"
SEEDS = 30
TOLERANCE = 0.03
FRAMES = {"base": (146, 50.0), "design": (173, 12.5)}
# cell -> (standard, ns-3 mode, rate in Mb/s, role)
CELLS = {
    f"P{s[-1]}{r}{role[0].upper()}": (s, mode, r, role)
    for s, rates in (("80211a", {6: "OfdmRate6Mbps", 12: "OfdmRate12Mbps", 24: "OfdmRate24Mbps"}),
                     ("80211p", {3: "OfdmRate3MbpsBW10MHz", 6: "OfdmRate6MbpsBW10MHz",
                                 12: "OfdmRate12MbpsBW10MHz"}))
    for r, mode in rates.items() for role in ("base", "design")}


def phy_of(standard: str, rate: float) -> phy.OfdmPhy:
    return phy.ofdm_20mhz(rate) if standard == "80211a" else phy.ofdm_10mhz(rate)


def _one(job: tuple[str, int, int]) -> tuple[str, int, float]:
    cell, n, seed = job
    standard, _, rate, role = CELLS[cell]
    p = phy_of(standard, rate)
    fb, fps = FRAMES[role]
    airtime = p.ppdu_s(bianchi.mpdu_bytes(fb))
    r = model.run(n, fps, airtime, seed=seed, slot_s=p.slot_s, difs_s=p.difs_s)
    return cell, n, r.delivered_frac


def model_crossing(cell: str, workers: int) -> float:
    standard, _, rate, role = CELLS[cell]
    p = phy_of(standard, rate)
    fb, fps = FRAMES[role]
    guess = 0.05 / (fps * (0.0710 * p.t_broadcast(fb) + 8e-6))     # Eq. (6), only to start
    scan = sorted({max(2, round(guess * (0.6 + 0.08 * k))) for k in range(12)})
    while True:
        with Pool(workers) as pool:
            got = pool.map(_one, [(cell, n, s) for n in scan for s in range(1, SEEDS + 1)])
        means = {n: st.mean(d for c, m, d in got if m == n) for n in scan}
        x = interpolated_crossing(means, 0.95)
        if x is not None:
            return x
        scan = sorted({max(2, round(n * (1.5 if means[scan[-1]] >= 0.95 else 0.6)))
                       for n in scan})


def predict(workers: int) -> list[dict]:
    rows = []
    for cell, (standard, mode, rate, role) in CELLS.items():
        x = model_crossing(cell, workers)
        step = max(1, round(0.025 * x))
        fb, fps = FRAMES[role]
        rows.append({"cell": cell, "standard": standard, "mode": mode, "rate_mbps": rate,
                     "role": role, "frame_bytes": fb, "frames_per_s": fps,
                     "frame_time_us": round(1e6 * phy_of(standard, rate).t_broadcast(fb), 1),
                     "model_crossing": round(x, 2), "model_lo": round((1 - TOLERANCE) * x, 2),
                     "model_hi": round((1 + TOLERANCE) * x, 2),
                     "ns3_grid": " ".join(str(round(x) + k * step) for k in range(-3, 4))})
    by = {(r["standard"], r["rate_mbps"]): {} for r in rows}
    for r in rows:
        by[(r["standard"], r["rate_mbps"])][r["role"]] = r["model_crossing"]
    for r in rows:
        pair = by[(r["standard"], r["rate_mbps"])]
        r["model_ratio"] = round(pair["design"] / pair["base"], 3)
    return rows


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash({"cells": CELLS, "seeds": SEEDS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def score() -> list[dict]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        reg = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    with (RAW / f"ns3_links_{STEM}_runs.csv").open(encoding="utf-8") as fh:
        runs = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    out = []
    for r in reg:
        per_n: dict[int, list[float]] = {}
        for x in runs:
            if x["cell"] == r["cell"]:
                per_n.setdefault(int(x["n_nodes"]), []).append(float(x["delivered_frac"]))
        per_n = {n: v for n, v in per_n.items() if len(v) == SEEDS}
        if sorted(per_n) != [int(n) for n in r["ns3_grid"].split()]:
            continue
        x = interpolated_crossing({n: st.mean(v) for n, v in per_n.items()}, 0.95)
        ci = interpolated_crossing_ci(per_n, threshold=0.95, seed=20261020)
        if x is None:
            continue
        out.append({**r, "ns3_crossing": round(x, 2),
                    "ns3_lo": round(ci[0], 2) if ci else "",
                    "ns3_hi": round(ci[1], 2) if ci else "",
                    "vs_model_pct": round(100 * (x / float(r["model_crossing"]) - 1), 2),
                    "in_band": int(abs(x / float(r["model_crossing"]) - 1) <= TOLERANCE)})
    pairs: dict[tuple[str, str], dict[str, float]] = {}
    for r in out:
        pairs.setdefault((r["standard"], r["rate_mbps"]), {})[r["role"]] = r["ns3_crossing"]
    for r in out:
        p = pairs[(r["standard"], r["rate_mbps"])]
        r["ns3_ratio"] = round(p["design"] / p["base"], 3) if len(p) == 2 else ""
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
           "phy_links_predictions" if args.predict else "phy_links")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
