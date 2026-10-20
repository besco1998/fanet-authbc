#!/usr/bin/env python3
"""Runs of the links scenario (`ns3/authbc-links.cc`): revision A10 (traces of the stream-signing
schemes' frames) and A11 (other PHYs and rates).

A plan file names the runs, one line each: `cell N1 N2 ...`; every (cell, N) runs `--seeds`
seeds numbered from 1, with the published source (send instant redrawn in each period). Rows go
to `results/raw/ns3_links_<stem>_runs.csv`, checkpointed as runs finish. With `--trace MODULE`,
each run also writes per-link traces, which are handed to `analysis/MODULE.per_run(text, cell)`
at once; only what it returns is kept (the traces are rebuilt from the seed if ever needed).

    python ns3/run_links.py --plan experiments/stream-deadline/plan.txt --stem stream_deadline \
        --trace stream_deadline --workers 6
"""
from __future__ import annotations

import argparse
import csv
import importlib
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

from ns3_paths import ns3_root  # noqa: E402
from run_nmax_direct import one_period_ms  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
TRACE_LINKS = 20


@dataclass(frozen=True)
class Cell:
    label: str
    frame_bytes: int
    fps: float
    standard: str = "80211a"
    data_mode: str = "OfdmRate6Mbps"


CELLS: dict[str, Cell] = {
    # A10: Table 5's frames (models/stream_auth.py), and the variants the plan adds
    "LSM": Cell("stream/mavlink2", 94, 50.0),
    "LST": Cell("stream/tesla", 106, 50.0),
    "LSG": Cell("stream/gennaro-rohatgi", 114, 50.0),
    "LSE": Cell("stream/emss-k100", 146, 50.5),
    "LSW": Cell("stream/wong-lam-4", 211, 50.0),
    "LTB": Cell("stream/tesla-batch4", 133, 12.5),
    # EMSS with a signature packet (210 B) after every k data packets (146 B): simulated as one
    # frame of their mean size at their joint rate
    "LE4": Cell("stream/emss-k4", 159, 62.5),
    "LE8": Cell("stream/emss-k8", 153, 56.25),
    "LE16": Cell("stream/emss-k16", 150, 53.125),
    # A11: the paper's two frames at other PHYs and rates (analysis/phy_links.py)
    "Pa6B": Cell("phy/80211a-6-base", 146, 50.0, "80211a", "OfdmRate6Mbps"),
    "Pa6D": Cell("phy/80211a-6-design", 173, 12.5, "80211a", "OfdmRate6Mbps"),
    "Pa12B": Cell("phy/80211a-12-base", 146, 50.0, "80211a", "OfdmRate12Mbps"),
    "Pa12D": Cell("phy/80211a-12-design", 173, 12.5, "80211a", "OfdmRate12Mbps"),
    "Pa24B": Cell("phy/80211a-24-base", 146, 50.0, "80211a", "OfdmRate24Mbps"),
    "Pa24D": Cell("phy/80211a-24-design", 173, 12.5, "80211a", "OfdmRate24Mbps"),
    "Pp3B": Cell("phy/80211p-3-base", 146, 50.0, "80211p", "OfdmRate3MbpsBW10MHz"),
    "Pp3D": Cell("phy/80211p-3-design", 173, 12.5, "80211p", "OfdmRate3MbpsBW10MHz"),
    "Pp6B": Cell("phy/80211p-6-base", 146, 50.0, "80211p", "OfdmRate6MbpsBW10MHz"),
    "Pp6D": Cell("phy/80211p-6-design", 173, 12.5, "80211p", "OfdmRate6MbpsBW10MHz"),
    "Pp12B": Cell("phy/80211p-12-base", 146, 50.0, "80211p", "OfdmRate12MbpsBW10MHz"),
    "Pp12D": Cell("phy/80211p-12-design", 173, 12.5, "80211p", "OfdmRate12MbpsBW10MHz"),
}


def run_one(cell: Cell, n: int, seed: int, trace: bool) -> tuple[dict[str, float], str]:
    root = ns3_root()
    exe = root / "build" / "scratch" / "ns3.48-authbc-links-optimized"
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "l"
        args = [f"--nNodes={n}", f"--framesPerSec={cell.fps!r}", f"--frameSize={cell.frame_bytes}",
                "--simTime=20.0", f"--seed={seed}", f"--outPrefix={prefix}",
                f"--txJitterMs={one_period_ms(cell.fps)!r}"]
        if cell.standard != "80211a":
            args.append(f"--standard={cell.standard}")
        if cell.data_mode != "OfdmRate6Mbps":
            args.append(f"--dataMode={cell.data_mode}")
        if trace:
            args.append(f"--traceLinks={TRACE_LINKS}")
        subprocess.run([str(exe), *args], cwd=root, check=True,
                       env={**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        text = Path(f"{prefix}_trace.csv").read_text() if trace else ""
    return {k: float(v) for k, v in rows.items()}, text


def read_plan(path: Path) -> list[tuple[str, list[int]]]:
    plan = []
    for line in path.read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        cell, *ns = fields
        if cell not in CELLS or not ns:
            raise SystemExit(f"bad plan line: {line!r}")
        plan.append((cell, [int(x) for x in ns]))
    return plan


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--stem", required=True)
    ap.add_argument("--trace", help="analysis module whose per_run(text, cell) reduces traces")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    reducer = importlib.import_module(args.trace) if args.trace else None
    path = RAW / f"ns3_links_{args.stem}_runs.csv"
    runs: list[dict[str, str]] = []
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            runs = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    done = {(r["cell"], int(r["n_nodes"]), int(r["seed"])) for r in runs}
    todo = [(c, n, s) for c, ns in read_plan(args.plan) for n in ns
            for s in range(1, args.seeds + 1) if (c, n, s) not in done]
    print(f"{len(runs)} runs on file, {len(todo)} to do", flush=True)
    config = {"seeds": args.seeds, "cells": {k: asdict(v) for k, v in CELLS.items()},
              "trace": args.trace, "trace_links": TRACE_LINKS}

    def job(t: tuple[str, int, int]) -> dict:
        cell, n, seed = t
        got, text = run_one(CELLS[cell], n, seed, reducer is not None)
        row = {"cell": cell, "frame_bytes": CELLS[cell].frame_bytes, "fps": CELLS[cell].fps,
               "n_nodes": n, "seed": seed, "tx_frames": int(got["tx_frames"]),
               "rx_frames": int(got["rx_frames"]), "delivered_frac": got["delivered_frac"],
               "delay_mean_ms": got["delay_mean_ms"], "delay_max_ms": got["delay_max_ms"]}
        if reducer is not None:
            row |= reducer.per_run(text, cell)
        return row

    def write() -> None:
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"ns3_links_{args.stem}_runs",
                     "config_hash": provenance.config_hash(config)}.items():
            buf.write(f"# {k}={v}\n")
        w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in runs for k in r)),
                           restval="", lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(runs, key=lambda r: (r["cell"], int(r["n_nodes"]), int(r["seed"]))))
        path.write_text(buf.getvalue())

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(job, t) for t in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            runs.append({k: str(v) for k, v in fut.result().items()})
            if i % 10 == 0 or i == len(todo):
                write()
                print(f"  {i}/{len(todo)} done", flush=True)


if __name__ == "__main__":
    main()
