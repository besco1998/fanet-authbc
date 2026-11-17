#!/usr/bin/env python3
"""Runs for the unified-model validation (task of 2026-11-17, work packages C and D): every new
ns-3 run of the task goes through the audit twin `authbc-links-audit.cc`, which is
`authbc-links.cc` at its defaults (gate: `ns3/verify_audit_twin.py`). Registrations come first
(`predictions/U*.md`, tag `prereg-U*`); this driver only runs what they name.

    python ns3/run_unified.py --cells UB16 --pilot              # 5 seeds, coarse grid
    python ns3/run_unified.py --cells UB16 --n 350 355 ... --seeds 30   # the measurement
    python ns3/run_unified.py --cells C --n 14 --seeds 10 --trace DIR    # keep the traces

Raw runs go to results/raw/<stem>_runs.csv (one row per cell, N and seed, appended, resumable);
the summary to results/raw/<stem>.csv: per node count the mean, spread and seeds, then one
CROSSING row per cell — the straight-line crossing of the mean delivered fraction and its
bootstrap interval over seeds, as the frozen campaign computes them (`authbc.bench.stats`).
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import statistics as st
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import interpolated_crossing, interpolated_crossing_ci  # noqa: E402

RAW = REPO / "results" / "raw"
SIM_TIME = 20.0
BOOTSTRAP_SEED = 0


@dataclass(frozen=True)
class Cell:
    frame_bytes: int
    fps: float
    standard: str = "80211a"
    mode: str = "OfdmRate6Mbps"
    extra: tuple[str, ...] = ()           # further audit-twin options

    def args(self) -> list[str]:
        a = [f"--frameSize={self.frame_bytes}", f"--framesPerSec={self.fps!r}",
             f"--txJitterMs={one_period_ms(self.fps)!r}", *self.extra]
        if (self.standard, self.mode) != ("80211a", "OfdmRate6Mbps"):
            a += [f"--standard={self.standard}", f"--dataMode={self.mode}"]
        return a


def one_period_ms(fps: float) -> float:
    """One sending period in ms that the scenario's guard accepts (as `run_nmax_direct`)."""
    period = 1000.0 / fps
    while period * 1e-3 > 1.0 / fps:
        period = math.nextafter(period, 0.0)
    return period


# lean format: 137 B fixed + 9 B per record, 50 records/s, 802.11a 6 Mb/s (U-C1, U-C2)
CELLS: dict[str, Cell] = {
    "C": Cell(146, 50.0),
    "D": Cell(173, 12.5),
    "UB16": Cell(137 + 9 * 16, 50.0 / 16),
    "UB32": Cell(137 + 9 * 32, 50.0 / 32),
    "UB64": Cell(137 + 9 * 64, 50.0 / 64),
}


def run_one(cell: str, n: int, seed: int, trace_dir: Path | None,
            trace_opts: tuple[str, ...]) -> dict[str, str]:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        out = trace_dir if trace_dir is not None else Path(td)
        prefix = out / f"{cell}_n{n}_s{seed}"
        args = [str(exe), f"--nNodes={n}", f"--simTime={SIM_TIME}", f"--seed={seed}",
                f"--outPrefix={prefix}", *CELLS[cell].args()]
        if trace_dir is not None:
            args += list(trace_opts)
        subprocess.run(args, check=True, env=env, capture_output=True)
        kv = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    c = CELLS[cell]
    return {"cell": cell, "frame_bytes": str(c.frame_bytes), "frames_per_s": repr(c.fps),
            "standard": c.standard, "mode": c.mode, "extra": " ".join(c.extra),
            "n_nodes": str(n), "seed": str(seed), "sim_time_s": repr(SIM_TIME),
            "tx_frames": kv["tx_frames"], "rx_frames": kv["rx_frames"],
            "delivered_frac": kv["delivered_frac"], "delay_mean_ms": kv["delay_mean_ms"],
            "delay_p99_ms": kv["delay_p99_ms"]}


FIELDS = ["cell", "frame_bytes", "frames_per_s", "standard", "mode", "extra", "n_nodes", "seed",
          "sim_time_s", "tx_frames", "rx_frames", "delivered_frac", "delay_mean_ms",
          "delay_p99_ms"]


def read_runs(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def _header(run: str, config: dict) -> str:
    return "".join(f"# {k}={v}\n" for k, v in {**provenance.env_block(), "run": run,
                                                 "ns3": "3.48 (authbc-links-audit)",
                                                 "config_hash": provenance.config_hash(config)
                                                 }.items())


def append_runs(path: Path, rows: list[dict[str, str]], stem: str) -> None:
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        if new:
            fh.write(_header(f"{stem}_runs", {"cells": {k: str(v) for k, v in CELLS.items()},
                                              "sim_time": SIM_TIME}))
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def summarise(runs: list[dict[str, str]], seeds: int, levels: tuple[float, ...]) -> list[dict]:
    """Per (cell, N) dispersion over exactly `seeds` runs, then a CROSSING row per level."""
    by: dict[str, dict[int, list[float]]] = {}
    for r in runs:
        by.setdefault(r["cell"], {}).setdefault(int(r["n_nodes"]), []).append(
            float(r["delivered_frac"]))
    out: list[dict] = []
    for cell, per_n in sorted(by.items()):
        full = {n: v for n, v in sorted(per_n.items()) if len(v) == seeds}
        for n, v in full.items():
            out.append({"cell": cell, "n_nodes": n, "seeds": len(v),
                        "delivered_mean": round(st.mean(v), 6),
                        "delivered_min": round(min(v), 6), "delivered_max": round(max(v), 6),
                        "delivered_stdev": round(st.stdev(v), 6) if len(v) > 1 else ""})
        means = {n: st.mean(v) for n, v in full.items()}
        for level in levels:
            x = interpolated_crossing(means, level)
            ci = interpolated_crossing_ci(full, threshold=level, seed=BOOTSTRAP_SEED)
            out.append({"cell": cell, "n_nodes": f"CROSSING@{level:g}", "seeds": seeds,
                        "delivered_mean": round(x, 3) if x is not None else "",
                        "delivered_min": round(ci[0], 3) if ci else "",
                        "delivered_max": round(ci[1], 3) if ci else "",
                        "delivered_stdev": f"bracketed {ci[2]:.3f}" if ci else ""})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", nargs="+", required=True, choices=list(CELLS))
    ap.add_argument("--n", type=int, nargs="+", help="node counts (default: the pilot grid)")
    ap.add_argument("--pilot", action="store_true", help="5 seeds on a coarse grid")
    ap.add_argument("--center", type=float, help="pilot grid centre (the registered root)")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--first-seed", type=int, default=1)
    ap.add_argument("--stem", required=True, help="results/raw/<stem>_runs.csv and <stem>.csv")
    ap.add_argument("--levels", type=float, nargs="+", default=[0.95])
    ap.add_argument("--trace", type=Path, help="keep traces in this directory")
    ap.add_argument("--trace-opts", nargs="*", default=["--traceMac=1"])
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if args.pilot:
        if args.center is None or len(args.cells) != 1:
            raise SystemExit("--pilot needs one cell and --center")
        step = max(1, round(args.center * 0.05))
        args.n = [max(2, round(args.center) + k * step) for k in range(-3, 4)]
        args.seeds = 5
    if not args.n:
        raise SystemExit("give --n, or --pilot with --center")
    path = RAW / f"{args.stem}_runs.csv"
    done = {(r["cell"], int(r["n_nodes"]), int(r["seed"])) for r in read_runs(path)}
    todo = [(c, n, s) for c in args.cells for n in args.n
            for s in range(args.first_seed, args.first_seed + args.seeds) if (c, n, s) not in done]
    if args.trace:
        args.trace.mkdir(parents=True, exist_ok=True)
    print(f"{len(done)} runs on file, {len(todo)} to do, {args.workers} at a time", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, c, n, s, args.trace, tuple(args.trace_opts))
                   for c, n, s in todo]
        for k, f in enumerate(as_completed(futures), 1):
            append_runs(path, [f.result()], args.stem)
            if k % 10 == 0 or k == len(futures):
                print(f"  {k}/{len(futures)} done", flush=True)
    runs = read_runs(path)
    summary = summarise(runs, args.seeds, tuple(args.levels))
    buf = io.StringIO(_header(args.stem, {"seeds": args.seeds, "levels": args.levels}))
    w = csv.DictWriter(buf, fieldnames=list(summary[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(summary)
    (RAW / f"{args.stem}.csv").write_text(buf.getvalue())
    for r in summary:
        if str(r["n_nodes"]).startswith("CROSSING"):
            print(r)


if __name__ == "__main__":
    main()
