#!/usr/bin/env python3
"""Where the unified model's error comes from, by event simulation alone (task of 2026-11-17, work
package A3; the model: docs/revision/2026-11-17_unified_model_spec.md).

The loss expression assumes Poisson starts and the access "rule A". ns-3's sources are periodic,
each frame at a uniform instant of its period (the designated source), and ns-3 follows its own
access rule (docs/audits, item 1). Each assumption is changed alone in an event simulator that
shares nothing with ns-3, at the same cells, and the crossing of 95 % delivery is read off:

* `ruleA-poisson`  — Mohamed's simulator (`analysis/closed_form_model.simulate`), Poisson starts:
  what the loss expression approximates;
* `ruleA-periodic` — the same with the designated periodic source: the Poisson assumption's share;
* `ruleA-gapbackoff` — periodic, and a frame arriving in the DIFS after a busy period draws a
  backoff instead of sending at its end;
* `repo-model`     — `src/authbc/sim/dcf_unsaturated.py`, periodic: its own rule (a gap arrival
  draws a counter; post-transmission backoff).

EIFS is in none of them; ns-3 has it. What remains between the closest simulator and ns-3 is left
to the ns-3 audit (items 1 and 3), not assigned here.

    python analysis/unified_gap_event.py      -> results/raw/unified_gap_event.csv
"""
from __future__ import annotations

import csv
import importlib.util
import io
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402
from authbc.sim import dcf_unsaturated as repo_model  # noqa: E402

OUT = REPO / "results" / "raw" / "unified_gap_event.csv"
SEEDS, SIM_S, LEVEL = 30, 20.0, 0.95

# cell: (access constants, payload bytes, frames/s, ns-3 crossing with the designated source)
CELLS = {
    "Pb1B": (uc.A80211B, phy.DSSS_1M, 146, 50.0, 9.72),
    "Pb1D": (uc.A80211B, phy.DSSS_1M, 173, 12.5, 31.05),
    "C": (uc.A80211A, phy.OFDM_20MHZ_6M, 146, 50.0, 35.26),
    "D": (uc.A80211A, phy.OFDM_20MHZ_6M, 173, 12.5, 124.55),
}
VARIANTS = ("ruleA-poisson", "ruleA-periodic", "ruleA-gapbackoff", "repo-model")


def _reference():
    spec = importlib.util.spec_from_file_location("closed_form_model",
                                                  REPO / "analysis" / "closed_form_model.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def grid(cell: str) -> list[int]:
    """Node counts around the model's root: ±25 %, about nine points."""
    acc, p, payload, fps, _ = CELLS[cell]
    root = uc.n_root(fps, uc.airtime_s(p, payload), 1 - LEVEL, acc)
    step = max(1, round(root * 0.06))
    return sorted({max(2, round(root) + k * step) for k in range(-4, 6)})


def delivered(job: tuple[str, str, int, int]) -> tuple[str, str, int, int, float]:
    cell, variant, n, seed = job
    acc, p, payload, fps, _ = CELLS[cell]
    tf = uc.airtime_s(p, payload)
    if variant == "repo-model":
        r = repo_model.run(n, fps, tf, sim_time_s=SIM_S, seed=seed, w0=acc.w, slot_s=acc.slot_s,
                           difs_s=acc.difs_s, detect_s=acc.delta_s)
        return cell, variant, n, seed, r.delivered_frac
    ref = _reference()
    lost = ref.simulate(n, fps, tf, W=acc.w, delta=acc.delta_s, slot=acc.slot_s,
                        difs=acc.difs_s, dur=SIM_S, seed=seed,
                        poisson=variant == "ruleA-poisson",
                        gap_backoff=variant == "ruleA-gapbackoff")
    return cell, variant, n, seed, 1.0 - lost


def main() -> None:
    jobs = [(c, v, n, s) for c in CELLS for v in VARIANTS for n in grid(c)
            for s in range(1, SEEDS + 1)]
    with Pool(8) as pool:
        results = pool.map(delivered, jobs, chunksize=8)
    per: dict[tuple[str, str], dict[int, list[float]]] = {}
    for cell, variant, n, _seed, v in results:
        per.setdefault((cell, variant), {}).setdefault(n, []).append(v)
    rows = []
    for (cell, variant), by_n in sorted(per.items()):
        acc, p, payload, fps, ns3 = CELLS[cell]
        tf = uc.airtime_s(p, payload)
        means = {n: st.mean(v) for n, v in sorted(by_n.items())}
        x = interpolated_crossing(means, LEVEL)
        root = uc.n_root(fps, tf, 1 - LEVEL, acc)
        rows.append({"cell": cell, "variant": variant, "frame_bytes": payload, "frames_per_s": fps,
                     "tf_us": round(tf * 1e6, 1), "window": acc.w, "seeds": SEEDS,
                     "grid": " ".join(map(str, means)),
                     "crossing": round(x, 2) if x is not None else "",
                     "ns3": ns3, "root": round(root, 2),
                     "vs_ns3_pct": round(100 * (x - ns3) / ns3, 2) if x is not None else "",
                     "root_vs_this_pct": round(100 * (root - x) / x, 2) if x is not None else ""})
    buf = io.StringIO()
    config = {"seeds": SEEDS, "sim_s": SIM_S, "level": LEVEL, "cells": str(CELLS)}
    for k, v in {**provenance.env_block(), "run": "unified_gap_event",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(f"{r['cell']:5s} {r['variant']:17s} crossing {r['crossing']!s:>7} "
              f"ns3 {r['ns3']:7.2f} ({r['vs_ns3_pct']!s:>6}%)  root {r['root']:7.2f} "
              f"(root vs this {r['root_vs_this_pct']}%)")


if __name__ == "__main__":
    main()
