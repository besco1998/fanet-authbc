#!/usr/bin/env python3
"""Does the crossing rule read low on a noisy curve? (docs/NMAX_DIRECT_EXPECTATIONS.md, F4)

Under strictly periodic senders the six crossings of seeds 1–30 all read lower than under the
redrawn source, by 1–9 %. The registration of F4 offered an explanation — that the rule (the
largest N that passes with every smaller N passing) reads low when the means are noisy — and
said it would be checked on the runs already on file. This is that check.

For each cell: take one mean per node count that both sources are supposed to share, from the
access-rule model (`authbc.sim.dcf_unsaturated`, which matches the redrawn source within
0.002); add the strictly periodic source's own run-to-run residuals, resampled with
replacement; read the interpolated crossing as the summary does; repeat.

    python analysis/crossing_rule_check.py        # writes results/raw/crossing_rule_check.csv

If the rule read low, the median of the resampled crossings would sit below the crossing of the
common mean. It does not.
"""
from __future__ import annotations

import csv
import io
import random
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
CELLS = tuple("ABCDEF")
SEEDS = 30
RESAMPLES = 2000
RNG_SEED = 7
V_TARGET = 0.95


def _driver():
    import run_nmax_direct as drv
    return drv


def periodic_runs() -> dict[str, dict[int, list[float]]]:
    """Strictly periodic runs of seeds 1–30, by cell and node count (complete points only)."""
    out: dict[str, dict[int, list[float]]] = {}
    with (RAW / "ns3_nmax_direct_runs.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if (r["cell"] in CELLS and float(r["jitter_ms"] or 0) == 0.0
                    and float(r["skew_ppm"] or 0) == 0.0):
                out.setdefault(r["cell"], {}).setdefault(int(r["n_nodes"]), []).append(
                    float(r["delivered_frac"]))
    return {c: {n: v for n, v in sorted(per_n.items()) if len(v) == SEEDS}
            for c, per_n in out.items()}


def observed_crossings() -> dict[str, dict[str, float]]:
    """cell -> {'periodic': …, 'redrawn': …}: the interpolated crossings of the summary."""
    drv = _driver()
    out: dict[str, dict[str, float]] = {}
    with (RAW / "ns3_nmax_direct.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["n_nodes"] != "CROSSING" or r["cell"] not in CELLS or r["skew_ppm"] != "0":
                continue
            jitter = float(r["jitter_ms"])
            one_period = provenance.as_written(1000.0 / drv.CELLS[r["cell"]].fps)
            source = "periodic" if jitter == 0.0 else "redrawn" if jitter == one_period else None
            if source and r["n_cross_interp"]:
                out.setdefault(r["cell"], {})[source] = float(r["n_cross_interp"])
    return out


def _model_mean(job: tuple[str, int]) -> tuple[str, int, float]:
    cell, n = job
    c = _driver().CELLS[cell]
    airtime = bianchi.t_broadcast(c.frame_bytes) - model.DIFS_S
    return cell, n, model.mean_delivered(n, c.fps, airtime, seeds=SEEDS)


def resampled_crossings(mean: dict[int, float], runs: dict[int, list[float]],
                        rng: random.Random, resamples: int = RESAMPLES) -> list[float]:
    """Crossings of `mean` plus the runs' own scatter, resampled; unbracketed draws are left out."""
    residual = {n: [x - st.mean(v) for x in v] for n, v in runs.items()}
    out = []
    for _ in range(resamples):
        noisy = {n: mean[n] + st.mean(rng.choices(residual[n], k=len(residual[n]))) for n in runs}
        x = interpolated_crossing(noisy, V_TARGET)
        if x is not None:
            out.append(x)
    return sorted(out)


def check(workers: int = 4) -> list[dict]:
    runs, observed = periodic_runs(), observed_crossings()
    with Pool(workers) as pool:
        means: dict[str, dict[int, float]] = {}
        for cell, n, m in pool.imap_unordered(_model_mean,
                                              [(c, n) for c in CELLS for n in runs[c]]):
            means.setdefault(cell, {})[n] = m
    rng = random.Random(RNG_SEED)
    rows = []
    for cell in CELLS:
        mean = dict(sorted(means[cell].items()))
        xs = resampled_crossings(mean, runs[cell], rng)
        true = interpolated_crossing(mean, V_TARGET)
        seen = observed[cell]["periodic"]
        rows.append({
            "cell": cell, "node_counts": " ".join(map(str, mean)),
            "crossing_of_common_mean": round(true, 2),
            "resampled_median": round(st.median(xs), 2),
            "resampled_p2_5": round(xs[int(0.025 * len(xs))], 2),
            "resampled_p97_5": round(xs[int(0.975 * len(xs))], 2),
            "bracketed_pct": round(100.0 * len(xs) / RESAMPLES, 1),
            "observed_periodic": seen, "observed_redrawn": observed[cell]["redrawn"],
            "observed_shift_pct": round(100.0 * (seen / observed[cell]["redrawn"] - 1.0), 1),
            "p_at_or_below_observed": round(sum(x <= seen for x in xs) / len(xs), 3),
        })
    return rows


def main() -> None:
    rows = check()
    buf = io.StringIO()
    config = {"cells": CELLS, "seeds": SEEDS, "resamples": RESAMPLES, "rng_seed": RNG_SEED}
    for k, v in {**provenance.env_block(), "run": "crossing_rule_check",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    (RAW / "crossing_rule_check.csv").write_text(buf.getvalue())
    for r in rows:
        print(f"  {r['cell']}  common mean crosses at {r['crossing_of_common_mean']:>7}  resampled "
              f"median {r['resampled_median']:>7} [{r['resampled_p2_5']}, {r['resampled_p97_5']}]"
              f"  observed {r['observed_periodic']:>7}  P = {r['p_at_or_below_observed']}")


if __name__ == "__main__":
    main()
