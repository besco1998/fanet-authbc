#!/usr/bin/env python3
"""How often do the paper's 95 % intervals contain the truth? (decision H2, finding F86)

F86 measured the percentile bootstrap of a MEAN over 30 seeds at 92–94 % coverage. Mohamed's
decision (H2, option 1): switch the V intervals to Student-t, and test the CROSSING intervals the
same way before deciding for them. This does that test: synthetic per-seed delivery curves with a
known crossing, shaped like the paper's cells, run through the repository's own interval code.

    shape    mean V(N) = 0.95 - slope (N - x_true), per-seed values normal with sd `sd`,
             30 seeds per N, every N drawn independently (seeds are independent runs).
             cell D: slope 0.00106 per node, sd 0.0019, x_true 124.55 (A2, A12).
    grids    step 3 (115 ... 133, as A2) and step 1 (120 ... 127, as the published D grid).
    methods  V at one N: percentile bootstrap of the mean, t interval (`stats.t_interval`).
             interpolated crossing: percentile bootstrap (`stats.interpolated_crossing_ci`),
             and two candidates: the delta-method t interval of the interpolated crossing,
             and the expanded percentile bootstrap (the same code at a widened level).
             grid crossing N_max: percentile bootstrap (`stats.threshold_crossing_ci`).

    python analysis/interval_coverage.py      # results/raw/interval_coverage.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import (  # noqa: E402
    bootstrap_ci,
    expanded_level,
    interpolated_crossing,
    interpolated_crossing_ci,
    t_interval,
    threshold_crossing_ci,
)

OUT = REPO / "results" / "raw" / "interval_coverage.csv"
THRESHOLD = 0.95
SEEDS = 30
X_TRUE = 124.55
SLOPE = 0.00106
SD = 0.0019
GRIDS = {"step3": tuple(range(115, 134, 3)), "step1": tuple(range(120, 128))}
RESAMPLES = 2000
BASE_SEED = 20261021


def true_mean(n: float) -> float:
    return THRESHOLD - SLOPE * (n - X_TRUE)


def true_n_max(grid: tuple[int, ...]) -> int:
    """The grid crossing of the true curve: the largest N with every N up to it passing."""
    last = 0
    for n in grid:
        if true_mean(n) < THRESHOLD:
            break
        last = n
    return last


def delta_t_crossing(per_n: dict[int, list[float]], ci: float = 0.95
                     ) -> tuple[float, float] | None:
    """t interval of the interpolated crossing from the two bracketing means (delta method).

    x = a + h (V_a - c) / (V_a - V_b); its variance from the two means' standard errors, the
    t quantile at the seeds' degrees of freedom."""
    means = {n: float(np.mean(v)) for n, v in per_n.items()}
    x = interpolated_crossing(means, THRESHOLD)
    if x is None:
        return None
    ns = sorted(means)
    a = max(n for n in ns if n <= x)
    b = ns[ns.index(a) + 1]
    va, vb, h = means[a], means[b], b - a
    d = va - vb
    dx_dva = h * (THRESHOLD - vb) / d ** 2       # d/dVa of h (Va - c)/(Va - Vb)
    dx_dvb = h * (va - THRESHOLD) / d ** 2
    se2 = {n: float(np.var(per_n[n], ddof=1)) / len(per_n[n]) for n in (a, b)}
    se = float(np.sqrt(dx_dva ** 2 * se2[a] + dx_dvb ** 2 * se2[b]))
    q = float(sps.t.ppf((1 + ci) / 2, SEEDS - 1))
    return x - q * se, x + q * se


def trial(rng: np.random.Generator, grid: tuple[int, ...], k: int) -> dict[str, int]:
    per_n = {n: list(rng.normal(true_mean(n), SD, SEEDS)) for n in grid}
    hit: dict[str, int] = {}
    at = grid[len(grid) // 2]                     # V at one node count, the middle of the grid
    lo, hi = bootstrap_ci(per_n[at], seed=k, statistic=np.mean, resamples=RESAMPLES)
    hit["v_mean_bootstrap"] = int(lo <= true_mean(at) <= hi)
    lo, hi = t_interval(per_n[at])
    hit["v_mean_t"] = int(lo <= true_mean(at) <= hi)
    ci = interpolated_crossing_ci(per_n, threshold=THRESHOLD, seed=k, resamples=RESAMPLES)
    hit["crossing_bootstrap"] = int(ci is not None and ci[0] <= X_TRUE <= ci[1])
    ci = interpolated_crossing_ci(per_n, threshold=THRESHOLD, seed=k, resamples=RESAMPLES,
                                  ci=expanded_level(SEEDS))
    hit["crossing_expanded_bootstrap"] = int(ci is not None and ci[0] <= X_TRUE <= ci[1])
    lo, hi = bootstrap_ci(per_n[at], seed=k, statistic=np.mean, resamples=RESAMPLES,
                          ci=expanded_level(SEEDS))
    hit["v_mean_expanded_bootstrap"] = int(lo <= true_mean(at) <= hi)
    dt = delta_t_crossing(per_n)
    hit["crossing_delta_t"] = int(dt is not None and dt[0] <= X_TRUE <= dt[1])
    tc = threshold_crossing_ci(per_n, threshold=THRESHOLD, seed=k, resamples=RESAMPLES)
    hit["n_max_bootstrap"] = int(tc.ci_lo <= true_n_max(grid) <= tc.ci_hi)
    return hit


def run(trials: int) -> list[dict]:
    rows = []
    for g, (name, grid) in enumerate(GRIDS.items()):
        rng = np.random.default_rng([BASE_SEED, g])
        hits = [trial(rng, grid, k) for k in range(trials)]
        for method in hits[0]:
            c = sum(h[method] for h in hits)
            lo, hi = sps.binomtest(c, trials).proportion_ci(confidence_level=0.95)
            rows.append({"grid": name, "method": method, "trials": trials,
                         "coverage": round(c / trials, 4), "coverage_lo": round(lo, 4),
                         "coverage_hi": round(hi, 4)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=1000)
    rows = run(ap.parse_args().trials)
    buf = io.StringIO()
    config = {"seeds": SEEDS, "x": X_TRUE, "slope": SLOPE, "sd": SD, "grids": GRIDS,
              "resamples": RESAMPLES, "base": BASE_SEED}
    for k, v in {**provenance.env_block(), "run": "interval_coverage",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(f"{r['grid']:6s} {r['method']:20s} {r['coverage']:.3f} "
              f"[{r['coverage_lo']:.3f}, {r['coverage_hi']:.3f}]")


if __name__ == "__main__":
    main()
