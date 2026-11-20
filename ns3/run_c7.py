#!/usr/bin/env python3
"""Runs for U-C7 (predictions/UC7.md): duty-cycled ALOHA over C channels, through the LoRa twin
`authbc-lora-dc.cc --channels=C` (gate: `ns3/verify_lora_twin.py`).

Each cell is `analysis/uc7.py`'s:
* the period is ToA/d;
* the one-sided jitter is 2·ToA;
* the run lasts 60 mean intervals per node;
* SF7, the `aloha` collision matrix (no capture), the ideal channel, one gateway.

    python ns3/run_c7.py --cell D1C3L20 --n 6 7 8 9 10 --seeds 30
    python ns3/run_c7.py --cell D1C3L20 --pilot          # 5 seeds, 7 N at ±5 % steps around N*
    python ns3/run_c7.py --cell D1C3L20 --n ... --per-node   # per-device counts, separate files

Raw rows go to results/raw/uc7_<cell>_runs.csv (appended, resumable), with provenance headers.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "analysis"))

from ns3_paths import ns3_root  # noqa: E402
from uc7 import CELLS, CELLS_B  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
ALL_CELLS = [*CELLS, *CELLS_B]
NODE_FIELDS = ["cell", "n_devices", "seed", "node", "sent", "received"]
FIELDS = ["cell", "n_devices", "seed", "sent", "received", "delivered_frac", "gateway_tx",
          "sim_time_s", "app_period_s", "tx_jitter_s"]


def run_one(cell_name: str, n: int, seed: int,
            per_node: bool = False) -> tuple[dict[str, str], list[dict[str, str]]]:
    c = next(x for x in ALL_CELLS if x.name == cell_name)
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-lora-dc-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "c"
        args = [str(exe), f"--nDevices={n}", f"--dataRate={c.dr}", f"--payloadBytes={c.payload}",
                f"--appPeriod={c.period_s!r}", f"--simulationTime={c.sim_s!r}",
                f"--seed={seed}", f"--txJitter={c.jitter_s!r}", f"--channels={c.channels}",
                "--interferenceMatrix=aloha", "--gwRegion=aloha", "--channelModel=ideal",
                f"--outPrefix={prefix}", *(["--perNode=1"] if per_node else [])]
        proc = subprocess.run(args, cwd=td, env=env, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"exit {proc.returncode}: {' '.join(args)}\n"
                               f"{proc.stderr.decode(errors='replace')[-1500:]}")
        got = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        freq = dict(ln.split(",") for ln in (Path(td) / "c_freq.csv").read_text().splitlines()[1:])
        nodes = []
        if per_node:
            with (Path(td) / "c_nodes.csv").open() as fh:
                nodes = [{"cell": cell_name, "n_devices": str(n), "seed": str(seed), **r}
                         for r in csv.DictReader(fh)]
    return {"cell": cell_name, "n_devices": str(n), "seed": str(seed), "sent": got["sent"],
            "received": got["received"], "delivered_frac": got["delivered_frac"],
            "gateway_tx": freq["gateway_tx"], "sim_time_s": got["sim_time_s"],
            "app_period_s": got["app_period_s"], "tx_jitter_s": got["tx_jitter_s"]}, nodes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", required=True, choices=[c.name for c in ALL_CELLS])
    ap.add_argument("--n", type=int, nargs="+")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--per-node", action="store_true",
                    help="also per-device counts; rows go to uc7_<cell>_pn_{runs,nodes}.csv")
    a = ap.parse_args()
    cell = next(c for c in ALL_CELLS if c.name == a.cell)
    if a.pilot:
        step = max(1, round(cell.n_star() * 0.05))
        a.n = [max(2, round(cell.n_star()) + k * step) for k in range(-3, 4)]
        a.seeds = 5
    if not a.n:
        raise SystemExit("give --n, or --pilot")
    stem = f"uc7_{a.cell.lower()}{'_pn' if a.per_node else ''}"
    path, node_path = RAW / f"{stem}_runs.csv", RAW / f"{stem}_nodes.csv"
    done = set()
    if path.exists():
        done = {(int(r["n_devices"]), int(r["seed"])) for r in csv.DictReader(
            ln for ln in path.open() if not ln.startswith("#"))}
    todo = [(n, s) for n in sorted(set(a.n)) for s in range(1, a.seeds + 1) if (n, s) not in done]
    print(f"{a.cell}: {len(done)} on file, {len(todo)} to do", flush=True)
    if not path.exists():
        buf = io.StringIO()
        for k, v in {**provenance.env_block(), "run": f"uc7_{a.cell.lower()}",
                     "config_hash": provenance.config_hash({"cell": str(cell)})}.items():
            buf.write(f"# {k}={v}\n")
        csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n").writeheader()
        path.write_text(buf.getvalue())
        if a.per_node:
            node_buf = io.StringIO()
            node_buf.write(buf.getvalue().rsplit("\n", 2)[0] + "\n")     # the provenance lines
            csv.DictWriter(node_buf, fieldnames=NODE_FIELDS, lineterminator="\n").writeheader()
            node_path.write_text(node_buf.getvalue())
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(run_one, a.cell, n, s, a.per_node) for n, s in todo]
        for f in as_completed(futures):
            row, nodes = f.result()
            with path.open("a", newline="") as fh:
                csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n").writerow(row)
            if nodes:
                with node_path.open("a", newline="") as fh:
                    csv.DictWriter(fh, fieldnames=NODE_FIELDS, lineterminator="\n").writerows(nodes)
    print(f"{a.cell}: done", flush=True)


if __name__ == "__main__":
    main()
