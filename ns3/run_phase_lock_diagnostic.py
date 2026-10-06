#!/usr/bin/env python3
"""WHICH nodes lose frames when sender phases are frozen (follow-up F1, direct N_max search).

The 30-seed sweeps of `authbc-delay` are heavily left-skewed: a few seeds deliver far less than
the rest. `docs/NMAX_DIRECT_EXPECTATIONS.md` attributes that to strictly periodic sources whose
relative phases never move, so that an unlucky pair of nodes collides in every period. If that is
right, the loss in a bad seed is not spread over the network: it sits on a few nodes.

This driver reruns chosen (cell, N, seed) points with the scenario's `--perNode` output under each
traffic source and writes one row per node: `results/raw/ns3_phase_lock_diagnostic.csv`.

    python ns3/run_phase_lock_diagnostic.py --cell A --n 29 --seeds 1 2 3

`--perNode` only attaches a second observer to the send trace; the aggregate delivery of each run
is checked here against the stored run of the same point wherever one exists.
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402
from run_nmax_direct import CELLS, RAW, read_runs, source_of  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = RAW / "ns3_phase_lock_diagnostic.csv"


def run(cell: str, n: int, seed: int, source: str, sim_time: float) -> tuple[dict, list[dict]]:
    """(aggregate row, per-node rows) of one run with per-node output switched on."""
    c = CELLS[cell]
    jitter, skew = source_of(source, c.fps)
    root = ns3_root()
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "d"
        args = [f"--nNodes={n}", f"--framesPerSec={c.fps}", f"--frameSize={c.frame_bytes}",
                f"--simTime={sim_time}", f"--seed={seed}", f"--outPrefix={prefix}", "--perNode=1"]
        if jitter > 0.0:
            args.append(f"--txJitterMs={jitter!r}")
        if skew > 0.0:
            args.append(f"--txSkewPpm={skew!r}")
        subprocess.run([str(root / "build" / "scratch" / "ns3.48-authbc-delay-optimized"), *args],
                       cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       env={**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")})
        agg = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        nodes = list(csv.DictReader(Path(f"{prefix}_nodes.csv").read_text().splitlines()))
    return agg, nodes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", required=True, choices=list(CELLS))
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--sources", nargs="+", default=["0", "0.1", "1", "period", "0.1/5000"])
    ap.add_argument("--sim-time", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    stored = {(r["cell"], float(r["jitter_ms"]), float(r["skew_ppm"]), int(r["n_nodes"]),
               int(r["seed"])): float(r["delivered_frac"])
              for r in read_runs(RAW / "ns3_nmax_direct_runs.csv")}
    jobs = [(seed, src) for seed in args.seeds for src in args.sources]
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda j: run(args.cell, args.n, j[0], j[1], args.sim_time), jobs)
        for (seed, src), (agg, nodes) in zip(jobs, results, strict=True):
            jitter, skew = source_of(src, CELLS[args.cell].fps)
            total = float(agg["delivered_frac"])
            before = stored.get((args.cell, jitter, skew, args.n, seed))
            if before is not None and before != total:
                raise SystemExit(f"--perNode changed a result: {args.cell} N={args.n} seed={seed} "
                                 f"source={src}: stored {before}, now {total}")
            fracs = sorted(float(x["delivered_frac"]) for x in nodes)
            print(f"  seed {seed:>2} source {src:<9} delivered {total:.4f}"
                  f"{'  (= stored run)' if before is not None else ''}   "
                  f"worst three nodes {fracs[0]:.3f} {fracs[1]:.3f} {fracs[2]:.3f}   "
                  f"median node {fracs[len(fracs) // 2]:.3f}", flush=True)
            for x in nodes:
                rows.append({"cell": args.cell, "n_nodes": args.n, "seed": seed,
                             "jitter_ms": f"{jitter:g}", "skew_ppm": f"{skew:g}",
                             "run_delivered_frac": total, "node": int(x["node"]),
                             "tx_frames": int(x["tx_frames"]), "rx_copies": int(x["rx_copies"]),
                             "node_delivered_frac": float(x["delivered_frac"])})

    buf = io.StringIO()
    meta = {**provenance.env_block(), "run": "ns3_phase_lock_diagnostic",
            "config_hash": provenance.config_hash(
                {"cell": args.cell, "n": args.n, "seeds": args.seeds, "sources": args.sources,
                 "t": args.sim_time})}
    for k, v in meta.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
