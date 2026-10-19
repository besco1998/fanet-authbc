#!/usr/bin/env python3
"""Revision A1 — capacity of a swarm that is spread out, faded, moving (predictions/A1.md).

Reads the runs of `ns3/run_spatial.py` and writes what the registration scores:

    python analysis/spatial_capacity.py --dref           # results/raw/spatial_dref.csv
    python analysis/spatial_capacity.py --score STEM...  # results/raw/spatial_capacity.csv

* **d_ref.** The largest distance of the pair sweep at which the 30-seed mean delivery of an
  isolated link is at least 0.99 for every frame of A1, and at every shorter distance.
* **Crossings.** Per (scenario, configuration): where the 30-seed mean of the per-receiver V
  (the share of its neighbours' frames a receiver got, averaged over receivers) crosses 0.95,
  by linear interpolation between grid points, with a bootstrap interval over seeds (the
  method of every capacity in the paper, `authbc.bench.stats`). Also: the first-failure grid
  crossing, the mean neighbour count and the node density at the crossing.
* **Hidden-station share.** For a receiver r, a neighbour s and any other node i: i spoils s's
  frame at r if its power there is within the 4 dB capture margin of s's,
  c = P(P_s G_s < 10^0.4 P_i G_i); and i is hidden from s if it misses s's preamble,
  h = P(P_si G < −82 dBm). G is the Nakagami-3 power gain, Gamma(3, 1/3), so the ratio of two
  is F(6, 6). The share is Σ c·h / Σ c over i, averaged over neighbour pairs: the fraction of
  the nodes that can spoil a frame that cannot hear it coming. Mean powers are the scenario's:
  20 dBm, 46.7 dB at 1 m, exponent 2. Computed from the placements the runs used.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats as sps

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import (  # noqa: E402
    crossing_point,
    interpolated_crossing,
    interpolated_crossing_ci,
)

RAW = REPO / "results" / "raw"
V_TARGET = 0.95
LINK_TARGET = 0.99
SEEDS = 30
BOOTSTRAP_SEED = 20261019
TX_DBM, REF_LOSS_DB, EXPONENT = 20.0, 46.7, 2.0
PREAMBLE_DBM, CAPTURE_DB, NAKAGAMI_M = -82.0, 4.0, 3.0
RADIUS_OF = {"s1-r100": 100.0, "s1-r300": 300.0, "s1-r600": 600.0, "s1-r1000": 1000.0}


def read_runs(stem: str) -> list[dict[str, str]]:
    path = RAW / f"ns3_spatial_{stem}_runs.csv"
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def d_ref(rows: list[dict[str, str]]) -> tuple[float, dict[tuple[int, str], float]]:
    """(d_ref, mean delivery per (distance, config)) from the pair sweep."""
    got: dict[tuple[int, str], list[float]] = defaultdict(list)
    for r in rows:
        got[(int(r["scenario"].removeprefix("pair-")), r["config"])].append(
            float(r["v_pooled"]))
    means = {k: st.mean(v) for k, v in got.items() if len(v) == SEEDS}
    configs = {c for _, c in means}
    best = 0.0
    for d in sorted({d for d, _ in means}):
        if all(means[(d, c)] >= LINK_TARGET for c in configs):
            best = float(d)
        else:
            break
    return best, means


def per_n(rows: list[dict[str, str]], scenario: str, config: str, metric: str
          ) -> dict[int, list[float]]:
    """{N: the metric over seeds}, only for node counts that hold every seed."""
    out: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        if r["scenario"] == scenario and r["config"] == config:
            out[int(r["n_nodes"])].append(float(r[metric]))
    return {n: v for n, v in out.items() if len(v) == SEEDS}


def mean_dbm(d: np.ndarray) -> np.ndarray:
    return TX_DBM - REF_LOSS_DB - 10 * EXPONENT * np.log10(np.maximum(d, 1.0))


def hidden_share(xyz: np.ndarray, ref_m: float) -> tuple[float, float]:
    """(mean hidden-station share, mean number of nodes able to spoil a frame) over the
    neighbour pairs of one placement. See the module docstring for the definition."""
    dist = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    p_mw = 10 ** (mean_dbm(dist) / 10)
    np.fill_diagonal(p_mw, np.nan)
    theta = 10 ** (CAPTURE_DB / 10)
    miss = sps.gamma.cdf(10 ** (PREAMBLE_DBM / 10) / p_mw, a=NAKAGAMI_M, scale=1 / NAKAGAMI_M)
    n = len(xyz)
    shares, spoilers = [], []
    for s in range(n):
        for r in np.flatnonzero((dist[s] <= ref_m) & (np.arange(n) != s)):
            others = np.ones(n, dtype=bool)
            others[s] = others[r] = False
            c = sps.f.cdf(theta * p_mw[others, r] / p_mw[s, r], 2 * NAKAGAMI_M, 2 * NAKAGAMI_M)
            total = c.sum()
            spoilers.append(total)
            shares.append(float((c * miss[s, others]).sum() / total) if total > 0 else 0.0)
    return (st.mean(shares), st.mean(spoilers)) if shares else (math.nan, math.nan)


def positions(stem: str, scenario: str, n: int, seed: int) -> np.ndarray | None:
    path = RAW / f"ns3_spatial_{stem}_positions" / f"{scenario}.{n}.{seed}.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return np.array([[float(r["x"]), float(r["y"]), float(r["z"])]
                         for r in csv.DictReader(fh)])


def crossing_row(rows: list[dict[str, str]], scenario: str, config: str) -> dict | None:
    v = per_n(rows, scenario, config, "v_mean_receiver")
    if len(v) < 2:
        return None
    means = {n: st.mean(x) for n, x in v.items()}
    x = interpolated_crossing(means, V_TARGET)
    ci = interpolated_crossing_ci(v, threshold=V_TARGET, seed=BOOTSTRAP_SEED)
    nb = {n: st.mean(x) for n, x in per_n(rows, scenario, config, "mean_neighbours").items()}
    out: dict = {"scenario": scenario, "config": config, "grid": " ".join(map(str, sorted(v))),
                 "n_max": crossing_point(means, V_TARGET),
                 "n_cross": "" if x is None else round(x, 2),
                 "n_cross_lo": "" if ci is None else round(ci[0], 2),
                 "n_cross_hi": "" if ci is None else round(ci[1], 2),
                 "bracketed": int(x is not None)}
    if x is not None:
        lo = max(n for n in means if n <= x)
        hi = min(n for n in means if n > x)
        nb_x = nb[lo] + (nb[hi] - nb[lo]) * (x - lo) / (hi - lo)
        out["neighbours_at_cross"] = round(nb_x, 2)
        if scenario in RADIUS_OF:
            out["density_per_km2"] = round(x / (math.pi * (RADIUS_OF[scenario] / 1000) ** 2), 1)
        out["v_at_grid"] = " ".join(f"{n}:{means[n]:.4f}" for n in sorted(means))
    return out


def _write(path: Path, rows: list[dict], run: str, config: dict) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def score(stems: list[str], ref_m: float) -> list[dict]:
    out = []
    for stem in stems:
        rows = read_runs(stem)
        pairs = sorted({(r["scenario"], r["config"]) for r in rows})
        found = {}
        for scen, cfg in pairs:
            row = crossing_row(rows, scen, cfg)
            if row is None:
                continue
            row["stem"] = stem
            found[(scen, cfg)] = row
            out.append(row)
        for (scen, cfg), row in found.items():
            base = found.get((scen, "base"))
            if cfg != "base" and base and row["n_cross"] != "" and base["n_cross"] != "":
                row["ratio_to_base"] = round(row["n_cross"] / base["n_cross"], 3)
                if row["n_cross_lo"] != "" and base["n_cross_hi"] != "":
                    row["ratio_lo"] = round(row["n_cross_lo"] / base["n_cross_hi"], 3)
                    row["ratio_hi"] = round(row["n_cross_hi"] / base["n_cross_lo"], 3)
            if row["n_cross"] != "" and (RAW / f"ns3_spatial_{stem}_positions").exists():
                n_at = max(int(n) for n in row["grid"].split() if int(n) <= row["n_cross"])
                got = [positions(stem, scen, n_at, s) for s in range(1, SEEDS + 1)]
                shares = [hidden_share(p, ref_m) for p in got if p is not None]
                if shares:
                    row["hidden_share"] = round(st.mean(h for h, _ in shares), 4)
                    row["spoilers"] = round(st.mean(c for _, c in shares), 2)
                    row["hidden_at_n"] = n_at
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--dref", action="store_true")
    what.add_argument("--score", nargs="+", metavar="STEM")
    ap.add_argument("--d-ref", type=float, default=0.0)
    args = ap.parse_args()
    if args.dref:
        best, means = d_ref(read_runs("dref"))
        rows = [{"distance_m": d, "config": c, "delivered_mean": round(v, 5),
                 "meets_link_target": int(v >= LINK_TARGET), "d_ref_m": best}
                for (d, c), v in sorted(means.items())]
        _write(RAW / "spatial_dref.csv", rows, "spatial_dref",
               {"target": LINK_TARGET, "seeds": SEEDS})
        print(f"d_ref = {best:g} m")
        for c in sorted({c for _, c in means}):
            last = max((d for (d, cc), v in means.items() if cc == c and v >= LINK_TARGET),
                       default=0)
            print(f"  {c}: last distance at >= 0.99: {last} m")
        return
    if args.d_ref <= 0:
        raise SystemExit("--score needs the measured --d-ref")
    rows = score(args.score, args.d_ref)
    _write(RAW / "spatial_capacity.csv", rows, "spatial_capacity",
           {"stems": args.score, "d_ref": args.d_ref, "seeds": SEEDS, "level": V_TARGET})
    for r in rows:
        print({k: r.get(k, "") for k in ("scenario", "config", "n_cross", "n_cross_lo",
                                          "n_cross_hi", "neighbours_at_cross", "ratio_to_base",
                                          "hidden_share")})


if __name__ == "__main__":
    main()
