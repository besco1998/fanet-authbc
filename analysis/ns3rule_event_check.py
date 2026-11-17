#!/usr/bin/env python3
"""What ns-3's own access rule changes in the eighteen capacities (audit of 2026-11-17, item 1;
docs/audits/2026-11-17_ns3_implementation_audit.md).

The loss expression was derived for "rule A" (an idle arrival is sent at once). ns-3.48 sends it
DIFS after its own arrival (channel-access-manager.cc:551–560; confirmed on every idle arrival of
the item-1 traces). Both rules are run here as event simulators, with the designated periodic
source, at the eighteen configurations of docs/02 §6g, and each crossing of 95 % delivery is set
against ns-3's (ns3_nmax_direct.csv, the designated source) and against the repository's own event
model (dcf_model_vs_ns3.csv). Nothing is fitted.

    python analysis/ns3rule_event_check.py     -> results/raw/ns3rule_event_check.csv
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
from authbc.sim import dcf_ns3rule  # noqa: E402

RAW = REPO / "results" / "raw"
OUT = RAW / "ns3rule_event_check.csv"
SEEDS, SIM_S, LEVEL = 30, 20.0, 0.95
CELLS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "RA", "RB", "RC", "RD",
         "SM", "ST", "SG", "SE", "SW")
ACC = uc.A80211A


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def ns3_designated() -> dict[str, tuple[int, float, float]]:
    """cell -> (frame bytes, frames/s, ns-3 crossing with a jitter of one period)."""
    out = {}
    for r in _rows(RAW / "ns3_nmax_direct.csv"):
        if r["n_nodes"] != "CROSSING" or r["cell"] not in CELLS or not r.get("n_cross_interp"):
            continue
        fps = float(r["lambda_rec_per_s"]) / int(r["batch"])
        if abs(float(r["jitter_ms"]) - 1000 / fps) < 1e-3 and float(r["skew_ppm"]) == 0:
            out[r["cell"]] = (int(r["frame_bytes"]), fps, float(r["n_cross_interp"]))
    return out


def repo_model() -> dict[str, float]:
    return {r["cell"]: float(r["model_crossing"]) for r in _rows(RAW / "dcf_model_vs_ns3.csv")
            if r.get("model_crossing")}


def _reference():
    spec = importlib.util.spec_from_file_location("closed_form_model",
                                                  REPO / "analysis" / "closed_form_model.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def grid(ns3: float) -> list[int]:
    step = max(1, round(ns3 * 0.04))
    return sorted({max(2, round(ns3) + k * step) for k in range(-4, 5)})


def delivered(job: tuple[str, str, int, int, int, float]) -> tuple[str, str, int, float]:
    cell, rule, n, seed, size, fps = job
    tf = uc.airtime_s(phy.OFDM_20MHZ_6M, size)
    if rule == "ns3-rule":
        r = dcf_ns3rule.run(n, fps, tf, slot_s=ACC.slot_s, difs_s=ACC.difs_s, w=ACC.w,
                            delta_s=ACC.delta_s, sim_time_s=SIM_S, seed=seed)
        return cell, rule, n, r.delivered_frac
    lost = _reference().simulate(n, fps, tf, W=ACC.w, delta=ACC.delta_s, slot=ACC.slot_s,
                                 difs=ACC.difs_s, dur=SIM_S, seed=seed)
    return cell, rule, n, 1.0 - lost


def main() -> None:
    cells = ns3_designated()
    missing = set(CELLS) - set(cells)
    if missing:
        raise SystemExit(f"no designated ns-3 crossing for {sorted(missing)}")
    jobs = [(c, rule, n, s, cells[c][0], cells[c][1]) for c in CELLS
            for rule in ("ns3-rule", "ruleA") for n in grid(cells[c][2])
            for s in range(1, SEEDS + 1)]
    with Pool(8) as pool:
        res = pool.map(delivered, jobs, chunksize=4)
    per: dict[tuple[str, str], dict[int, list[float]]] = {}
    for cell, rule, n, v in res:
        per.setdefault((cell, rule), {}).setdefault(n, []).append(v)
    repo = repo_model()
    rows = []
    for c in CELLS:
        size, fps, ns3 = cells[c]
        x = {}
        for rule in ("ns3-rule", "ruleA"):
            means = {n: st.mean(v) for n, v in sorted(per[(c, rule)].items())}
            x[rule] = interpolated_crossing(means, LEVEL)
        tf = uc.airtime_s(phy.OFDM_20MHZ_6M, size)
        row = {"cell": c, "frame_bytes": size, "frames_per_s": fps, "tf_us": round(tf * 1e6, 1),
               "ns3": ns3, "repo_model": repo.get(c, ""),
               "ns3_rule": round(x["ns3-rule"], 2) if x["ns3-rule"] else "",
               "rule_a": round(x["ruleA"], 2) if x["ruleA"] else "",
               "root": round(uc.n_root(fps, tf, 1 - LEVEL, ACC), 2)}
        for k in ("ns3_rule", "rule_a"):
            row[f"{k}_vs_ns3_pct"] = (round(100 * (row[k] - ns3) / ns3, 2) if row[k] != ""
                                      else "")
        row["ns3_rule_vs_rule_a_pct"] = (round(100 * (row["ns3_rule"] - row["rule_a"])
                                               / row["rule_a"], 2)
                                         if row["ns3_rule"] != "" and row["rule_a"] != "" else "")
        rows.append(row)
    buf = io.StringIO()
    config = {"seeds": SEEDS, "sim_s": SIM_S, "level": LEVEL, "cells": CELLS, "acc": str(ACC)}
    for k, v in {**provenance.env_block(), "run": "ns3rule_event_check",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
