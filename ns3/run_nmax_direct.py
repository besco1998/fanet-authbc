#!/usr/bin/env python3
"""Direct search for the 802.11 N_max at V >= 0.95, with a bootstrap interval (review 4.8).

Every other 802.11 capacity figure at this threshold applies ONE load ceiling (U = 2.435), measured
at N = 50 with a 288 B frame, to every configuration. This driver does not use that ceiling at all:
it simulates each configuration at its own frame size and frame rate over a grid of N, and reads
the crossing off the simulated delivery — the treatment the LoRa arm has had since F28.

Predictions and the decision rule were committed before the first run:
`docs/NMAX_DIRECT_EXPECTATIONS.md`.

Writes two files:
  results/raw/ns3_nmax_direct_runs.csv   one row per (cell, N, seed) — the raw simulator output
  results/raw/ns3_nmax_direct.csv        per-(cell, N) dispersion, then one CROSSING row per cell

Runs are launched as the built scenario binary, several at a time. `--verify` first checks that
launching the binary directly returns exactly what the documented `./ns3 run` entry returns.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean, stdev

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
from ns3_paths import ns3_root  # noqa: E402

NS3 = ns3_root()
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import threshold_crossing_ci  # noqa: E402
from authbc.models import optimizer  # noqa: E402

BINARY = NS3 / "build" / "scratch" / "ns3.48-authbc-delay-optimized"
RAW = REPO / "results" / "raw"
V_TARGET = 0.95
PER_RUN_SHARE = 0.95          # per-run criterion: this share of runs must individually meet V
LAMBDA = 50.0                 # adopted operating point, records/s per node

# cell -> (label, frame bytes, records per frame, signatures per frame is irrelevant on air,
#          model N_max at U <= 2.435). Frame sizes: results/raw/design_ladder.csv, whole bytes.
CELLS: dict[str, tuple[str, int, int, int]] = {
    "A": ("first/inline-1", 174, 1, 31),
    "B": ("first/batch-delta", 300, 4, 97),
    "C": ("lean/inline-1", 146, 1, 34),
    "D": ("lean/batch-delta", 173, 4, 142),
    "E": ("first/inline-b", 565, 4, 49),
    "F": ("lean/inline-b", 372, 4, 80),
}


def default_grid(model_n: int) -> list[int]:
    """Six node counts spanning roughly ±20 % of the model's value."""
    step = max(1, round(model_n * 0.08))
    return [model_n + k * step for k in (-3, -2, -1, 0, 1, 2)]


def run_one(frame_bytes: int, fps: float, n_nodes: int, seed: int, sim_time: float,
            *, via_ns3: bool = False) -> dict[str, float]:
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "d"
        args = [f"--nNodes={n_nodes}", f"--framesPerSec={fps}", f"--frameSize={frame_bytes}",
                f"--simTime={sim_time}", f"--seed={seed}", f"--outPrefix={prefix}"]
        if via_ns3:
            cmd = ["./ns3", "run", "authbc-delay " + " ".join(args)]
            env = None
        else:
            cmd = [str(BINARY), *args]
            env = {**os.environ, "LD_LIBRARY_PATH": str(NS3 / "build" / "lib")}
        subprocess.run(cmd, cwd=NS3, check=True, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    return {k: float(v) for k, v in rows.items()}


def verify(sim_time: float) -> None:
    """The directly-launched binary must return exactly what `./ns3 run` returns."""
    a = run_one(288, 12.5, 20, 1, sim_time, via_ns3=True)
    b = run_one(288, 12.5, 20, 1, sim_time, via_ns3=False)
    if a != b:
        raise SystemExit(f"VERIFY FAILED: ./ns3 run and the binary disagree\n  {a}\n  {b}")
    c = run_one(288, 12.5, 20, 1, sim_time, via_ns3=False)
    if b != c:
        raise SystemExit("VERIFY FAILED: the same seed gave two different results")
    print(f"verify: ./ns3 run == direct binary == repeat (delivered {b['delivered_frac']})")


def _read_runs(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))


def _write(path: Path, rows: list[dict], run: str, config: dict) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def summarise(runs: list[dict[str, str]], seeds: int) -> list[dict]:
    """Per-(cell, N) dispersion rows, then one CROSSING row per cell."""
    out: list[dict] = []
    for cell, (label, frame, batch, model_n) in CELLS.items():
        per_n: dict[int, list[float]] = {}
        for r in runs:
            if r["cell"] == cell:
                per_n.setdefault(int(r["n_nodes"]), []).append(float(r["delivered_frac"]))
        per_n = {n: v for n, v in per_n.items() if len(v) == seeds}
        if not per_n:
            continue
        for n in sorted(per_n):
            v = per_n[n]
            out.append({
                "cell": cell, "config": label, "frame_bytes": frame, "batch": batch,
                "n_nodes": n, "delivered_mean": round(mean(v), 5),
                "delivered_min": round(min(v), 5), "delivered_max": round(max(v), 5),
                "delivered_stdev": round(stdev(v), 5),
                "seeds_failing_v": sum(x < V_TARGET for x in v), "seeds": len(v),
                "model_util": round(optimizer.channel_utilisation(n, LAMBDA, batch, frame), 4),
            })
        ci = threshold_crossing_ci(per_n, threshold=V_TARGET, seed=12345)
        # per-run criterion, same first-failure rule as the mean criterion
        strict = 0
        for n in sorted(per_n):
            if sum(x >= V_TARGET for x in per_n[n]) / len(per_n[n]) < PER_RUN_SHARE:
                break
            strict = n
        grid = sorted(per_n)
        out.append({
            "cell": cell, "config": label, "frame_bytes": frame, "batch": batch,
            "n_nodes": "CROSSING", "n_max_mean": ci.point, "n_max_ci_lo": ci.ci_lo,
            "n_max_ci_hi": ci.ci_hi, "n_max_per_run": strict, "model_n_max": model_n,
            "deviation_pct": round(100.0 * (ci.point - model_n) / model_n, 1),
            "grid": " ".join(map(str, grid)),
            "bracketed": int(grid[0] <= ci.point < grid[-1]),
            "seeds": seeds,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", nargs="+", default=sorted(CELLS), choices=sorted(CELLS))
    ap.add_argument("--n", type=int, nargs="+",
                    help="explicit node counts (one cell only); default: a grid round the model")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--sim-time", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--verify", action="store_true", help="check binary == ./ns3 run, then exit")
    ap.add_argument("--summarise-only", action="store_true")
    args = ap.parse_args()
    if args.verify:
        verify(args.sim_time)
        return
    if args.n and len(args.cells) != 1:
        raise SystemExit("--n applies to exactly one cell")

    runs_path = RAW / "ns3_nmax_direct_runs.csv"
    runs = _read_runs(runs_path)
    done = {(r["cell"], int(r["n_nodes"]), int(r["seed"])) for r in runs}
    todo = []
    if not args.summarise_only:
        for cell in args.cells:
            _, frame, batch, model_n = CELLS[cell]
            for n in (args.n or default_grid(model_n)):
                for seed in range(1, args.seeds + 1):
                    if (cell, n, seed) not in done:
                        todo.append((cell, frame, LAMBDA / batch, n, seed))
    print(f"{len(done)} runs on file, {len(todo)} to do, {args.workers} at a time")

    def job(t: tuple) -> dict:
        cell, frame, fps, n, seed = t
        r = run_one(frame, fps, n, seed, args.sim_time)
        return {"cell": cell, "frame_bytes": frame, "frames_per_s": fps, "n_nodes": n,
                "seed": seed, "sim_time_s": args.sim_time,
                "tx_frames": int(r["tx_frames"]), "rx_frames": int(r["rx_frames"]),
                "delivered_frac": r["delivered_frac"], "delay_mean_ms": r["delay_mean_ms"],
                "delay_p99_ms": r["delay_p99_ms"], "delay_max_ms": r["delay_max_ms"]}

    config = {"seeds": args.seeds, "t": args.sim_time, "lambda": LAMBDA, "cells": CELLS}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(job, todo), 1):
            runs.append({k: str(v) for k, v in row.items()})
            if i % 30 == 0 or i == len(todo):       # checkpoint: a long sweep must survive a kill
                runs.sort(key=lambda r: (r["cell"], int(r["n_nodes"]), int(r["seed"])))
                _write(runs_path, runs, "ns3_nmax_direct_runs", config)
                print(f"  {i}/{len(todo)} done", flush=True)

    summary = summarise(runs, args.seeds)
    _write(RAW / "ns3_nmax_direct.csv", summary, "ns3_nmax_direct", config)
    for r in summary:
        if r["n_nodes"] == "CROSSING":
            print(f"  {r['cell']} {r['config']:<20} N_max = {r['n_max_mean']} "
                  f"[{r['n_max_ci_lo']}, {r['n_max_ci_hi']}]  per-run {r['n_max_per_run']}  "
                  f"model {r['model_n_max']} ({r['deviation_pct']:+.1f} %)  "
                  f"{'' if r['bracketed'] else '⚠️ NOT BRACKETED by the grid'}")


if __name__ == "__main__":
    main()
