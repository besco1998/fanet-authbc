#!/usr/bin/env python3
"""Revision A4 — score the adaptive batching runs (predictions/A4.md).

Reads `results/raw/ns3_adaptive_runs.csv` and the per-second series in
`results/raw/ns3_adaptive_ts/`, and writes `results/raw/adaptive_batching.csv`: one row per
(scenario, policy), means over seeds with the seed-to-seed range. `--set a4b` does the same for
the second controllers (predictions/A4b.md): `ns3_adaptive_b_runs.csv`, `ns3_adaptive_b_ts/`
→ `adaptive_batching_b.csv`.

A window is one second of sending; its V is the share of the frames sent in it that reached the
neighbours they were due at; its age is the mean peak age of the receptions of those frames.
The first two windows (sources starting) are left out.
"""
from __future__ import annotations

import argparse
import csv
import io
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
SETS = {"a4": (RAW / "ns3_adaptive_runs.csv", RAW / "ns3_adaptive_ts",
               RAW / "adaptive_batching.csv"),
        "a4b": (RAW / "ns3_adaptive_b_runs.csv", RAW / "ns3_adaptive_b_ts",
                RAW / "adaptive_batching_b.csv")}
RUNS, SERIES, OUT = SETS["a4"]
V_TARGET = 0.95
SKIP = 2


def series(scenario: str, policy: str, seed: int,
           directory: Path | None = None) -> list[dict[str, float]]:
    path = (directory or SERIES) / f"{scenario}.{policy}.{seed}.csv"
    with path.open(encoding="utf-8") as fh:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(fh)]
    out = []
    for r in rows:
        if r["t"] <= SKIP or r["due"] <= 0:
            continue
        r["v"] = r["got"] / r["due"]
        r["age"] = r["age_sum_ms"] / r["age_count"] if r["age_count"] else float("nan")
        out.append(r)
    return out


def failure_n(ts: list[dict[str, float]]) -> float:
    """Active nodes at the first window where the 5-window moving mean of V is below 0.95."""
    for i in range(4, len(ts)):
        if st.mean(r["v"] for r in ts[i - 4:i + 1]) < V_TARGET:
            return ts[i]["active"]
    return float("nan")


def switch_n(ts: list[dict[str, float]], level: float) -> float:
    """Active nodes at the first window whose mean batch reaches `level`."""
    return next((r["active"] for r in ts if r["mean_b"] >= level), float("nan"))


def per_seed(scenario: str, policy: str, seed: int, summary: dict[str, str]) -> dict[str, float]:
    ts = series(scenario, policy, seed)
    minutes = len(ts) / 60.0
    out = {"frac_v95": st.mean(r["v"] >= V_TARGET for r in ts),
           "mean_v": st.mean(r["v"] for r in ts),
           "bytes_per_record": float(summary["bytes_per_record"]),
           "b_changes_per_node_min": float(summary["b_changes"])
           / max(1.0, st.mean(r["active"] for r in ts)) / minutes,
           "peak_age_mean_ms": float(summary["peak_age_mean_ms"]),
           "peak_age_p95_ms": float(summary["peak_age_p95_ms"])}
    if scenario == "ramp":
        low = [r for r in ts if r["active"] < 30]
        upto = [r for r in ts if r["active"] <= 115]
        out |= {"frac_v95_n_le_115": st.mean(r["v"] >= V_TARGET for r in upto),
                "age_n_lt_30_ms": st.mean(r["age"] for r in low),
                "failure_n": failure_n(ts),
                "first_window_v_below_n": next((r["active"] for r in ts if r["v"] < V_TARGET),
                                               float("nan")),
                **{f"b_reaches_{lv}_at_n": switch_n(ts, lv) for lv in (1.5, 2.5, 3.5)}}
    if scenario == "merge":
        merged = [r for r in ts if 62 <= r["t"] <= 121]
        out |= {"frac_v95_merged": st.mean(r["v"] >= V_TARGET for r in merged),
                "mean_b_merged": st.mean(r["mean_b"] for r in merged),
                "mean_b_apart": st.mean(r["mean_b"] for r in ts if r["t"] < 60)}
    return out


def score() -> list[dict]:
    with RUNS.open(encoding="utf-8") as fh:
        runs = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    groups: dict[tuple[str, str], list[dict[str, float]]] = {}
    for r in runs:
        groups.setdefault((r["scenario"], r["policy"]), []).append(
            per_seed(r["scenario"], r["policy"], int(r["seed"]), r))
    rows = []
    for (scen, pol), seeds in sorted(groups.items()):
        row: dict = {"scenario": scen, "policy": pol, "seeds": len(seeds)}
        for k in seeds[0]:
            vals = [s[k] for s in seeds if s[k] == s[k]]          # drop NaN
            row[k] = round(st.mean(vals), 4) if vals else ""
            row[f"{k}_min"] = round(min(vals), 4) if vals else ""
            row[f"{k}_max"] = round(max(vals), 4) if vals else ""
        rows.append(row)
    return rows


def main() -> None:
    global RUNS, SERIES, OUT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="a4", choices=list(SETS))
    RUNS, SERIES, OUT = SETS[ap.parse_args().set]
    rows = score()
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "adaptive_batching",
                 "config_hash": provenance.config_hash({"skip": SKIP, "target": V_TARGET})
                 }.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print({k: v for k, v in r.items() if not k.endswith(("_min", "_max"))})


if __name__ == "__main__":
    main()
