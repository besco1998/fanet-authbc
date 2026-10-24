#!/usr/bin/env python3
"""Do the two traffic sources deliver the same on average? (docs/NMAX_DIRECT_EXPECTATIONS.md, F4)

Fourteen (configuration, N) points were simulated with strictly periodic senders and with a send
time redrawn in every period. Over seeds 1–30 the redrawn source delivered 0.0031 more on
average — about two standard errors. Follow-up F4 repeats the comparison on seeds that had never
been used. This script is its arithmetic:

    d_i  = mean(redrawn at point i) − mean(strictly periodic at point i)
    D    = mean of the d_i
    SE   = sqrt( Σ_i ( s²_redrawn,i / n_redrawn,i + s²_periodic,i / n_periodic,i ) ) / k

    python analysis/source_difference.py

`SE` is propagated from the spread between runs at each point. It does not assume the true
difference is the same at every point, and it is dominated by the strictly periodic runs, whose
spread is ten to twenty times the other's.
"""
from __future__ import annotations

import csv
import math
import statistics as st
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench.provenance import as_written  # noqa: E402

RAW = REPO / "results" / "raw"
FIRST = RAW / "ns3_nmax_direct_runs.csv"          # the reported sample: seeds 1–30
FRESH = RAW / "ns3_source_fresh_runs.csv"         # follow-up F4: seeds 31 and up
Point = tuple[str, int]


@dataclass(frozen=True)
class Difference:
    points: int
    d: float                       # mean over points of (redrawn − strictly periodic)
    se: float                      # propagated from the spread between runs
    per_point: dict[Point, float]

    @property
    def z(self) -> float:
        return self.d / self.se


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def by_source(runs: list[dict[str, str]]) -> dict[Point, dict[str, dict[int, float]]]:
    """(cell, N) -> source -> seed -> delivered fraction, for the two sources being compared.

    `periodic` is a send jitter of zero; `redrawn` is a jitter of one sending period. Runs with
    a rate offset, or any other jitter, belong to neither.
    """
    out: dict[Point, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for r in runs:
        if float(r.get("skew_ppm") or 0) != 0.0:
            continue
        jitter = float(r.get("jitter_ms") or 0)
        one_period = as_written(1000.0 / float(r["frames_per_s"]))
        source = "periodic" if jitter == 0.0 else "redrawn" if jitter == one_period else None
        if source is not None:
            out[(r["cell"], int(r["n_nodes"]))][source][int(r["seed"])] = float(
                r["delivered_frac"])
    return out


def difference(samples: dict[Point, dict[str, dict[int, float]]],
               seeds: dict[str, range]) -> Difference:
    """D and its standard error over the points that hold every seed of `seeds` for both sources.

    A point missing any required seed of either source is left out whole, so a half-finished
    campaign cannot be scored on a short sample.
    """
    per_point: dict[Point, float] = {}
    variance = 0.0
    for point, sources in sorted(samples.items()):
        values = {}
        for source, wanted in seeds.items():
            have = sources.get(source, {})
            if any(seed not in have for seed in wanted):
                break
            values[source] = [have[seed] for seed in wanted]
        else:
            per_point[point] = st.mean(values["redrawn"]) - st.mean(values["periodic"])
            variance += sum(st.variance(v) / len(v) for v in values.values())
    if not per_point:
        raise ValueError("no point holds every requested seed under both sources")
    k = len(per_point)
    return Difference(k, st.mean(per_point.values()), math.sqrt(variance) / k, per_point)


def combine(a: Difference, b: Difference) -> tuple[float, float]:
    """Inverse-variance weighted mean of two independent estimates of D, and its standard error."""
    wa, wb = 1.0 / a.se ** 2, 1.0 / b.se ** 2
    return (wa * a.d + wb * b.d) / (wa + wb), math.sqrt(1.0 / (wa + wb))


FIRST_SEEDS = {"periodic": range(1, 31), "redrawn": range(1, 31)}
# F4 as registered: sixty fresh seeds for the noisy source, thirty for the quiet one
FRESH_SEEDS = {"periodic": range(31, 91), "redrawn": range(31, 61)}


def main() -> None:
    first = difference(by_source(read(FIRST)), FIRST_SEEDS)
    print(f"seeds 1-30   : {first.points} points  D = {first.d:+.5f}  SE = {first.se:.5f}  "
          f"z = {first.z:+.2f}")
    if not FRESH.exists():
        print("fresh seeds  : not run yet")
        return
    fresh = difference(by_source(read(FRESH)), FRESH_SEEDS)
    print(f"fresh seeds  : {fresh.points} points  D = {fresh.d:+.5f}  SE = {fresh.se:.5f}  "
          f"z = {fresh.z:+.2f}")
    for point, d in fresh.per_point.items():
        print(f"    {point[0]:<2} N = {point[1]:<4} d = {d:+.5f}   (seeds 1-30: "
              f"{first.per_point.get(point, float('nan')):+.5f})")
    both, se = combine(first, fresh)
    print(f"combined     : D = {both:+.5f}  SE = {se:.5f}  z = {both / se:+.2f}")


if __name__ == "__main__":
    main()
