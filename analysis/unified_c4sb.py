#!/usr/bin/env python3
"""U-C4S (the split unit with its frames spread over the period) and U-C4B (the burst correction
on new cells), scored as predictions/UC4S.md and UC4B.md fix them.

Reads the driver's summaries and runs `results/raw/unified_c4s_n{2,3}*` and
`unified_c4b_{bb2,bb3,ab120}*`. Writes `results/raw/unified_c4sb_scored.csv`:
* **U-C4S:** the root of (G5) at ε_n, held within ±5 %; the law (outside its range) held only if
  above ns-3. Reported: the verification wait against (n − 1)/(n·f).
* **U-C4B:** the correction's capacity (`authbc.models.burst_correction`), held within ±5 % at
  802.11a, and at 802.11b by U-D's bands (±5 % from 15 stations, −9 … +5 % at 8–14, not scored
  below 8). Reported: the original root's error, every crossing of the mean curve, the wait.

    python analysis/unified_c4sb.py
"""
from __future__ import annotations

import csv
import io
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402
from authbc.models.burst_correction import unit_capacity  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "unified_c4sb_scored.csv"
EPS, F_UNIT = 0.05, 12.5
# cell: (stem, n, frame bytes, PHY, access, item)
CELLS = {
    "F2P": ("unified_c4s_n2", 2, 98, phy.OFDM_20MHZ_6M, uc.A80211A, "C4S"),
    "F3P": ("unified_c4s_n3", 3, 73, phy.OFDM_20MHZ_6M, uc.A80211A, "C4S"),
    "BB2": ("unified_c4b_bb2", 2, 98, phy.DSSS_1M, uc.A80211B, "C4B"),
    "BB3": ("unified_c4b_bb3", 3, 73, phy.DSSS_1M, uc.A80211B, "C4B"),
    "AB120": ("unified_c4b_ab120", 2, 72, phy.OFDM_20MHZ_6M, uc.A80211A, "C4B"),
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def model(cell: str) -> dict[str, float]:
    _stem, n, size, p, acc, _item = CELLS[cell]
    tf = uc.airtime_s(p, size)
    e = uc.eps_fragment(n, EPS)
    return {"tf_us": tf * 1e6, "root": uc.n_root(n * F_UNIT, tf, e, acc),
            "law": uc.n_law(n * F_UNIT, tf, e, acc),
            "correction": unit_capacity(F_UNIT, tf, n, EPS, acc)}


def band(cell: str, ns3: float) -> tuple[float, float] | None:
    """±5 % at 802.11a; at 802.11b U-D's bands by ns-3's crossing."""
    if CELLS[cell][3] is not phy.DSSS_1M or ns3 >= 15:
        return (-5.0, 5.0)
    return (-9.0, 5.0) if ns3 >= 8 else None


def err_pct(m: float, x: float) -> float:
    return 100.0 * (m - x) / x


def every_crossing(means: dict[int, float], level: float = 0.95) -> list[float]:
    ns = sorted(means)
    out = []
    for lo, hi in zip(ns, ns[1:], strict=False):
        a, b = means[lo] - level, means[hi] - level
        if a * b < 0:
            out.append(lo + a / (a - b) * (hi - lo))
    return out


def main() -> None:
    rows: list[dict[str, object]] = []
    for cell, (stem, n, _size, _p, _acc, item) in CELLS.items():
        cross = [r for r in _rows(RAW / f"{stem}.csv") if r["n_nodes"] == "CROSSING@0.95"][0]
        if cross["seeds"] != "30" or cross["delivered_stdev"] != "bracketed 1.000":
            raise ValueError(f"{stem}: not a 30-seed crossing bracketed throughout")
        x = float(cross["delivered_mean"])
        runs = _rows(RAW / f"{stem}_runs.csv")
        by: dict[int, list[float]] = {}
        for r in runs:
            by.setdefault(int(r["n_nodes"]), []).append(float(r["verified_frac"]))
        every = every_crossing({k: st.mean(v) for k, v in by.items()})
        wait = st.mean(float(r["unit_wait_mean_ms"]) for r in runs)
        p99 = st.mean(float(r["unit_wait_p99_ms"]) for r in runs)
        m = model(cell)
        if item == "C4S":
            pred, b = m["root"], (-5.0, 5.0)
        else:
            pred, b = m["correction"], band(cell, x)
        e = err_pct(pred, x)
        verdict = ("not scored (< 8 stations)" if b is None
                   else "held" if b[0] <= e <= b[1] else "failed")
        rows.append({"item": item, "cell": cell, "n": n, "tf_us": round(m["tf_us"], 3),
                     "ns3": x, "ci_lo": cross["delivered_min"], "ci_hi": cross["delivered_max"],
                     "every_crossing": " ".join(f"{c:.3f}" for c in every),
                     "scored_prediction": "root" if item == "C4S" else "burst correction",
                     "predicted": round(pred, 3), "err_pct": round(e, 2),
                     "band": "" if b is None else f"{b[0]:+g} … {b[1]:+g} %",
                     "verdict": verdict,
                     "law": round(m["law"], 3), "law_above_ns3": m["law"] > x,
                     "root": round(m["root"], 3), "root_err_pct": round(err_pct(m["root"], x), 2),
                     "wait_mean_ms": round(wait, 3), "wait_p99_ms": round(p99, 3),
                     "wait_predicted_ms": round(1000 * (n - 1) / (n * F_UNIT), 3)
                     if item == "C4S" else ""})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_c4sb",
                 "config_hash": provenance.config_hash({"eps": EPS, "f": F_UNIT,
                                                        "cells": sorted(CELLS)})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
