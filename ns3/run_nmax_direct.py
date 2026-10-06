#!/usr/bin/env python3
"""Direct search for the 802.11 N_max at V >= 0.95, with a bootstrap interval (review 4.8).

Every other 802.11 capacity figure at this threshold applies ONE load ceiling (U = 2.435), measured
at N = 50 with a 288 B frame, to every configuration. This driver does not use that ceiling at all:
it simulates each configuration at its own frame size and frame rate over a grid of N, and reads
the crossing off the simulated delivery — the treatment the LoRa arm has had since F28.

Predictions and the decision rule were committed before the first run, and each later stage's
before its own runs: `docs/NMAX_DIRECT_EXPECTATIONS.md`.

Writes two files:
  results/raw/ns3_nmax_direct_runs.csv   one row per (cell, jitter, N, seed) — raw simulator output
  results/raw/ns3_nmax_direct.csv        per-(cell, jitter, N) dispersion, then one CROSSING row
                                         per (cell, jitter)

The summary is a pure function of the runs file (`summarise`), so it can be rebuilt and checked on
a machine without NS-3: `--summarise-only`, and `tests/test_nmax_direct.py`.

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
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import (  # noqa: E402
    crossing_point,
    interpolated_crossing,
    interpolated_crossing_ci,
    threshold_crossing_ci,
)
from authbc.models import bianchi, optimizer  # noqa: E402

RAW = REPO / "results" / "raw"
V_TARGET = 0.95
PER_RUN_SHARE = 0.95          # per-run criterion: this share of runs must individually meet V
BOOTSTRAP_SEED = 12345


@dataclass(frozen=True)
class Cell:
    """One configuration: what is put on air, how often, and what the single ceiling predicts."""

    label: str
    frame_bytes: int      # results/raw/design_ladder.csv, rounded to the whole byte ns-3 needs
    batch: int            # records per frame
    lam: float            # records/s per node
    model_n: int          # N_max by the load ceiling U <= 2.435 (design_ladder.csv, n_max_v95)

    @property
    def fps(self) -> float:
        return self.lam / self.batch


CELLS: dict[str, Cell] = {
    # --- adopted operating point (50 rec/s, 100 ms): the six cells registered before any run ---
    "A": Cell("first/inline-1", 174, 1, 50.0, 31),
    "B": Cell("first/batch-delta", 300, 4, 50.0, 97),
    "C": Cell("lean/inline-1", 146, 1, 50.0, 34),
    "D": Cell("lean/batch-delta", 173, 4, 50.0, 142),
    "E": Cell("first/inline-b", 565, 4, 50.0, 49),
    "F": Cell("lean/inline-b", 372, 4, 50.0, 80),
    # --- adopted point, the rungs stage 1 left out (held out: predicted before they were run) ---
    "G": Cell("first/batch-cbor", 373, 4, 50.0, 79),
    "H": Cell("lean/batch-keys", 218, 4, 50.0, 123),
    "I": Cell("first/batch-delta-published", 288, 4, 50.0, 100),
    # --- relaxed operating point (20 rec/s, 250 ms), also held out ---
    "RA": Cell("first/inline-1", 174, 1, 20.0, 88),
    "RB": Cell("first/batch-delta", 300, 4, 20.0, 208),
    "RC": Cell("lean/inline-1", 146, 1, 20.0, 101),
    "RD": Cell("lean/batch-delta", 173, 4, 20.0, 269),
    "RE": Cell("first/inline-b", 565, 4, 20.0, 140),
    "RF": Cell("lean/inline-b", 372, 4, 20.0, 185),
    "RG": Cell("first/batch-cbor", 373, 4, 20.0, 184),
    "RH": Cell("lean/batch-keys", 218, 4, 20.0, 243),
    "RI": Cell("first/batch-delta-published", 288, 4, 20.0, 213),
}


def default_grid(model_n: int) -> list[int]:
    """Six node counts spanning roughly ±20 % of the model's value."""
    step = max(1, round(model_n * 0.08))
    return [model_n + k * step for k in (-3, -2, -1, 0, 1, 2)]


def jitter_ms_of(spec: str, fps: float) -> float:
    """`--jitter` as milliseconds: a number, or ``period`` for one full sending period."""
    return 1000.0 / fps if spec == "period" else float(spec)


def _binary() -> tuple[Path, Path]:
    root = ns3_root()
    return root, root / "build" / "scratch" / "ns3.48-authbc-delay-optimized"


def run_one(frame_bytes: int, fps: float, n_nodes: int, seed: int, sim_time: float,
            *, jitter_ms: float = 0.0, via_ns3: bool = False) -> dict[str, float]:
    root, binary = _binary()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "d"
        args = [f"--nNodes={n_nodes}", f"--framesPerSec={fps}", f"--frameSize={frame_bytes}",
                f"--simTime={sim_time}", f"--seed={seed}", f"--outPrefix={prefix}"]
        if jitter_ms > 0.0:                 # absent by default: the published scenario, untouched
            args.append(f"--txJitterMs={jitter_ms!r}")
        if via_ns3:
            cmd = ["./ns3", "run", "authbc-delay " + " ".join(args)]
            env = None
        else:
            cmd = [str(binary), *args]
            env = {**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")}
        subprocess.run(cmd, cwd=root, check=True, env=env, stdout=subprocess.DEVNULL,
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


def read_runs(path: Path) -> list[dict[str, str]]:
    """The raw runs. Rows written before the jitter option existed are jitter 0 by construction."""
    if not path.exists():
        return []
    rows = list(csv.DictReader(ln for ln in path.read_text().splitlines()
                               if not ln.startswith("#")))
    for r in rows:
        r["jitter_ms"] = r.get("jitter_ms") or "0"
    return rows


def _run_key(r: dict[str, str]) -> tuple[str, float, int, int]:
    return (r["cell"], float(r["jitter_ms"]), int(r["n_nodes"]), int(r["seed"]))


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


def _per_run_crossing(per_n: dict[int, list[float]]) -> int:
    """Largest N at which PER_RUN_SHARE of the runs individually meet V, same first-failure rule."""
    share = {n: sum(x >= V_TARGET for x in v) / len(v) for n, v in per_n.items()}
    return crossing_point(share, PER_RUN_SHARE)


def summarise(runs: list[dict[str, str]], seeds: int) -> list[dict]:
    """Per-(cell, jitter, N) dispersion rows, then one CROSSING row per (cell, jitter).

    A node count enters only once all ``seeds`` runs are on file, so a half-finished sweep can be
    summarised without a short sample being compared against the threshold.
    """
    groups: dict[tuple[str, float], dict[int, list[float]]] = {}
    for r in runs:
        cell, jitter, n, _ = _run_key(r)
        groups.setdefault((cell, jitter), {}).setdefault(n, []).append(
            float(r["delivered_frac"]))
    out: list[dict] = []
    for cell, jitter in sorted(groups, key=lambda k: (list(CELLS).index(k[0]), k[1])):
        c = CELLS[cell]
        per_n = {n: v for n, v in groups[(cell, jitter)].items() if len(v) == seeds}
        if not per_n:
            continue
        head = {"cell": cell, "config": c.label, "frame_bytes": c.frame_bytes, "batch": c.batch,
                "lambda_rec_per_s": c.lam, "jitter_ms": f"{jitter:g}"}
        frame_s = bianchi.t_broadcast(c.frame_bytes)
        for n in sorted(per_n):
            v = per_n[n]
            out.append({
                **head, "n_nodes": n, "delivered_mean": round(mean(v), 5),
                "delivered_min": round(min(v), 5), "delivered_max": round(max(v), 5),
                "delivered_stdev": round(stdev(v), 5),
                "seeds_failing_v": sum(x < V_TARGET for x in v), "seeds": len(v),
                "model_util": round(
                    optimizer.channel_utilisation(n, c.lam, c.batch, c.frame_bytes), 4),
                "airtime_occupancy": round(n * c.fps * frame_s, 4),
            })
        means = {n: mean(v) for n, v in per_n.items()}
        grid = sorted(per_n)
        n_max = crossing_point(means, V_TARGET)
        ci = threshold_crossing_ci(per_n, threshold=V_TARGET, seed=BOOTSTRAP_SEED)
        interp = interpolated_crossing(means, V_TARGET)
        interp_ci = interpolated_crossing_ci(per_n, threshold=V_TARGET, seed=BOOTSTRAP_SEED)
        row = {
            **head, "n_nodes": "CROSSING", "seeds": seeds,
            # the estimate is the SAMPLE's crossing; the bootstrap supplies only the interval
            "n_max_mean": n_max, "n_max_ci_lo": ci.ci_lo, "n_max_ci_hi": ci.ci_hi,
            "n_max_per_run": _per_run_crossing(per_n), "model_n_max": c.model_n,
            "deviation_pct": round(100.0 * (n_max - c.model_n) / c.model_n, 1),
            "grid": " ".join(map(str, grid)),
            "bracketed": int(grid[0] <= n_max < grid[-1]),
        }
        if interp is not None and interp_ci is not None:
            row |= {"n_cross_interp": round(interp, 2),
                    "n_cross_interp_lo": round(interp_ci[0], 2),
                    "n_cross_interp_hi": round(interp_ci[1], 2),
                    "interp_share_bracketed": round(interp_ci[2], 4),
                    "deviation_interp_pct": round(100.0 * (interp - c.model_n) / c.model_n, 1)}
        out.append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", nargs="+", default=list("ABCDEF"), choices=list(CELLS))
    ap.add_argument("--n", type=int, nargs="+",
                    help="explicit node counts (one cell only); default: a grid round the model")
    ap.add_argument("--jitter", default="0",
                    help="per-frame send jitter in ms, or 'period' for one full period; "
                         "0 = the published strictly periodic source (default)")
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
    runs = read_runs(runs_path)
    done = {_run_key(r) for r in runs}
    todo = []
    if not args.summarise_only:
        for cell in args.cells:
            c = CELLS[cell]
            jitter = jitter_ms_of(args.jitter, c.fps)
            for n in (args.n or default_grid(c.model_n)):
                for seed in range(1, args.seeds + 1):
                    if (cell, jitter, n, seed) not in done:
                        todo.append((cell, jitter, n, seed))
    print(f"{len(done)} runs on file, {len(todo)} to do, {args.workers} at a time", flush=True)

    def job(t: tuple[str, float, int, int]) -> dict:
        cell, jitter, n, seed = t
        c = CELLS[cell]
        r = run_one(c.frame_bytes, c.fps, n, seed, args.sim_time, jitter_ms=jitter)
        return {"cell": cell, "frame_bytes": c.frame_bytes, "frames_per_s": c.fps, "n_nodes": n,
                "seed": seed, "sim_time_s": args.sim_time,
                "tx_frames": int(r["tx_frames"]), "rx_frames": int(r["rx_frames"]),
                "delivered_frac": r["delivered_frac"], "delay_mean_ms": r["delay_mean_ms"],
                "delay_p99_ms": r["delay_p99_ms"], "delay_max_ms": r["delay_max_ms"],
                "jitter_ms": f"{jitter:g}"}

    config = {"seeds": args.seeds, "t": args.sim_time,
              "cells": {k: vars(c) for k, c in CELLS.items()}}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(job, todo), 1):
            runs.append({k: str(v) for k, v in row.items()})
            if i % 30 == 0 or i == len(todo):       # checkpoint: a long sweep must survive a kill
                runs.sort(key=lambda r: (list(CELLS).index(r["cell"]), *_run_key(r)[1:]))
                _write(runs_path, runs, "ns3_nmax_direct_runs", config)
                print(f"  {i}/{len(todo)} done", flush=True)

    summary = summarise(runs, args.seeds)
    _write(RAW / "ns3_nmax_direct.csv", summary, "ns3_nmax_direct", config)
    for r in summary:
        if r["n_nodes"] == "CROSSING":
            interp = (f"  interp {r['n_cross_interp']} [{r['n_cross_interp_lo']}, "
                      f"{r['n_cross_interp_hi']}]" if "n_cross_interp" in r else "")
            print(f"  {r['cell']:<2} {r['config']:<28} jitter {r['jitter_ms']:>4} ms  "
                  f"N_max = {r['n_max_mean']} [{r['n_max_ci_lo']}, {r['n_max_ci_hi']}]{interp}  "
                  f"per-run {r['n_max_per_run']}  model {r['model_n_max']} "
                  f"({r['deviation_pct']:+.1f} %)  "
                  f"{'' if r['bracketed'] else '⚠️ NOT BRACKETED by the grid'}")


if __name__ == "__main__":
    main()
