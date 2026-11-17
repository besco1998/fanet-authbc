#!/usr/bin/env python3
"""U-C1: the loss expression's three terms measured one by one in ns-3 (predictions/UC1.md; the
model: docs/revision/2026-11-17_unified_model_spec.md).

Every frame of every traced run (`ns3/run_unified.py --trace DIR`, `--traceMac`) is classified as
the registration fixes:
* a *group* is a set of transmissions whose air intervals overlap; with equal power all are lost;
* **detection window** — the group's starts are not all at one instant;
* **same-slot tie** — all at one instant, and every frame drew a backoff (a draw by its station
  between its enqueue and its start);
* **zero-backoff start after a busy period** — all at one instant, at least one frame drew none.

Also measured: **a**, the share of frames that arrive to a busy medium (busy from a start + 4 µs to
its end), and **K**, for each such frame, the number of other stations holding a frame when that
busy period ends. Shares are per seed; the mean and a bootstrap 95 % interval over seeds are
reported, and each prediction scored as held (within ±10 % of the mean, or inside the interval).

    python analysis/unified_c1.py DIR      -> results/raw/unified_c1_scored.csv
    python analysis/unified_c1.py DIR OUT  -> OUT (U-D's D3: the same rules at 802.11b)
"""
from __future__ import annotations

import csv
import io
import re
import statistics as st
import sys
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import bootstrap_ci  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

OUT = REPO / "results" / "raw" / "unified_c1_scored.csv"   # unified_c1.csv is the driver's summary
DETECT_NS = 4_000
CELLS = {"C": (146, 50.0), "D": (173, 12.5),          # U-C1, 802.11a at 6 Mb/s
         "Pb1B": (146, 50.0), "Pb1D": (173, 12.5)}    # U-D's D3, 802.11b at 1 Mb/s
STANDARD = {"C": "80211a", "D": "80211a", "Pb1B": "80211b", "Pb1D": "80211b"}
PHY_ACCESS = {"80211a": (phy.OFDM_20MHZ_6M, uc.A80211A), "80211b": (phy.DSSS_1M, uc.A80211B)}
TOL = 0.10
QUANTITIES = ("tie", "zero_backoff_after_busy", "detection_window", "p", "a", "K")


def read_trace(path: Path) -> tuple[dict[tuple[int, int], dict[str, int]],
                                    dict[int, list[int]]]:
    """{(node, uid): {E, B, F}} and each node's backoff-draw times."""
    fr: dict[tuple[int, int], dict[str, int]] = defaultdict(dict)
    draws: dict[int, list[int]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            kind, node, uid, t, _v = line.rstrip("\n").split(",")
            if kind == "K":
                draws[int(node)].append(int(t))
            else:
                fr[(int(node), int(uid))][kind] = int(t)
    for v in draws.values():
        v.sort()
    return fr, draws


def classify(fr: dict[tuple[int, int], dict[str, int]],
             draws: dict[int, list[int]]) -> dict[str, float]:
    """One run: each class's lost frames over frames sent, and a and K."""
    tx = sorted((v["B"], v["F"], node, v.get("E", v["B"]))
                for (node, _u), v in fr.items() if "B" in v and "F" in v)

    def drew(node: int, e: int, b: int) -> bool:
        times = draws.get(node, [])
        i = bisect_right(times, b)
        return i > 0 and times[i - 1] >= e

    groups: list[list[tuple[int, int, int, int]]] = []
    reach = -1
    for t in tx:
        if groups and t[0] < reach:
            groups[-1].append(t)
            reach = max(reach, t[1])
        else:
            groups.append([t])
            reach = t[1]
    lost = {"tie": 0, "zero_backoff_after_busy": 0, "detection_window": 0}
    for g in groups:
        if len(g) < 2:
            continue
        if len({b for b, _f, _n, _e in g}) > 1:
            lost["detection_window"] += len(g)
        elif all(drew(n, e, b) for b, _f, n, e in g):
            lost["tie"] += len(g)
        else:
            lost["zero_backoff_after_busy"] += len(g)
    # busy periods as a non-sender senses them, for a and K
    busy: list[list[int]] = []
    for b, f, _n, _e in tx:
        s = b + DETECT_NS
        if busy and s <= busy[-1][1]:
            busy[-1][1] = max(busy[-1][1], f)
        else:
            busy.append([s, f])
    starts = [p[0] for p in busy]
    # every frame is enqueued before it starts, so the frames held at time t are those enqueued
    # by t less those started by t
    enq = sorted(e for _b, _f, _n, e in tx)
    began = sorted(b for b, _f, _n, _e in tx)
    arrived_busy, k_counts = 0, []
    for _b, _f, _n, e in tx:
        i = bisect_right(starts, e) - 1
        if i >= 0 and busy[i][0] <= e < busy[i][1]:
            arrived_busy += 1
            end = busy[i][1]
            held = bisect_right(enq, end) - bisect_right(began, end)
            k_counts.append(held - 1)                     # the others, not the frame itself
    n = len(tx)
    return {**{k: v / n for k, v in lost.items()}, "p": sum(lost.values()) / n,
            "a": arrived_busy / n, "K": st.mean(k_counts) if k_counts else 0.0}


def diagnose(fr: dict[tuple[int, int], dict[str, int]],
             draws: dict[int, list[int]]) -> dict[str, float]:
    """Not scored (added after the U-C1 scoring): each collision split by start spread (one
    instant or not) and by how many of its frames drew a backoff. In ns-3 a station counts slots
    from its own backoff start, so two counters that expire in the same slot can start a few µs
    apart; such a group is "spread > 0, all drew"."""
    tx = sorted((v["B"], v["F"], node, v.get("E", v["B"]))
                for (node, _u), v in fr.items() if "B" in v and "F" in v)

    def drew(node: int, e: int, b: int) -> bool:
        times = draws.get(node, [])
        i = bisect_right(times, b)
        return i > 0 and times[i - 1] >= e

    groups: list[list[tuple[int, int, int, int]]] = []
    reach = -1
    for t in tx:
        if groups and t[0] < reach:
            groups[-1].append(t)
            reach = max(reach, t[1])
        else:
            groups.append([t])
            reach = t[1]
    out = {f"{sp}_{who}": 0.0 for sp in ("instant", "spread") for who in ("all", "mixed", "none")}
    for g in groups:
        if len(g) < 2:
            continue
        sp = "instant" if len({b for b, _f, _n, _e in g}) == 1 else "spread"
        k = sum(drew(n, e, b) for b, _f, n, e in g)
        who = "all" if k == len(g) else "none" if k == 0 else "mixed"
        out[f"{sp}_{who}"] += len(g) / len(tx)
    return out


def predictions(cell: str, n: int) -> dict[str, float]:
    size, f = CELLS[cell]
    p_hy, acc = PHY_ACCESS[STANDARD[cell]]
    tf = uc.airtime_s(p_hy, size)
    nu = (n - 1) * f
    p = uc.loss(nu, tf, acc)
    a = nu * (tf - acc.delta_s) * (1 - p / 2)
    gam, eta = nu * acc.difs_s, nu * acc.slot_s * (acc.w - 1) / 2
    return {**uc.loss_terms(nu, tf, acc), "p": p, "a": a,
            "K": a * (1 + gam + 2 * eta) / (1 - gam - a)}


def main_diagnose(d: Path, out: Path = OUT.parent / "unified_c1_diagnostic.csv") -> None:
    per: dict[tuple[str, int], list[dict[str, float]]] = defaultdict(list)
    for path in sorted(d.glob("*_mac.csv")):
        m = re.fullmatch(r"(\w+?)_n(\d+)_s(\d+)_mac\.csv", path.name)
        if m and m.group(1) in CELLS:
            per[(m.group(1), int(m.group(2)))].append(diagnose(*read_trace(path)))
    rows = []
    for (cell, n), runs in sorted(per.items()):
        mean = {k: st.mean(r[k] for r in runs) for k in runs[0]}
        pred = predictions(cell, n)
        rows.append({"cell": cell, "n_nodes": n, "seeds": len(runs),
                     **{k: round(v, 6) for k, v in mean.items()},
                     "ties_any_spread": round(mean["instant_all"] + mean["spread_all"], 6),
                     "model_tie": round(pred["tie"], 6)})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_c1_diagnostic (not scored)",
                 "config_hash": provenance.config_hash({"cells": CELLS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    for r in rows:
        print(r)


def main() -> None:
    # unified_c1.py [--diagnose] DIR [OUT]: OUT defaults to U-C1's files; U-D's D3 names its own.
    if sys.argv[1] == "--diagnose":
        main_diagnose(*(Path(a) for a in sys.argv[2:4]))
        return
    d = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    per: dict[tuple[str, int], list[dict[str, float]]] = defaultdict(list)
    for path in sorted(d.glob("*_mac.csv")):
        m = re.fullmatch(r"(\w+?)_n(\d+)_s(\d+)_mac\.csv", path.name)
        if not m or m.group(1) not in CELLS:
            continue
        per[(m.group(1), int(m.group(2)))].append(classify(*read_trace(path)))
    rows = []
    for (cell, n), runs in sorted(per.items()):
        pred = predictions(cell, n)
        for q in QUANTITIES:
            vals = [r[q] for r in runs]
            mean = st.mean(vals)
            lo, hi = bootstrap_ci(vals, seed=1, statistic=np.mean) if len(vals) > 1 else (mean,
                                                                                          mean)
            held = abs(pred[q] - mean) <= TOL * mean or lo <= pred[q] <= hi
            rows.append({"cell": cell, "n_nodes": n, "seeds": len(runs), "quantity": q,
                         "predicted": round(pred[q], 6), "measured": round(mean, 6),
                         "ci_lo": round(lo, 6), "ci_hi": round(hi, 6),
                         "pred_vs_meas_pct": round(100 * (pred[q] - mean) / mean, 1)
                         if mean else "", "held": held})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "unified_c1",
                 "config_hash": provenance.config_hash({"tol": TOL, "detect_ns": DETECT_NS,
                                                        "cells": CELLS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
