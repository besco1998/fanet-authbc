#!/usr/bin/env python3
"""A1 stage 1: place the grids of stage 2 (predictions/A1.md, "Procedure").

Exploratory and never reported as a capacity. Each (scenario, configuration) walks its own grid
on seeds 1–5, one node count at a time, and stops when two consecutive 5-seed means of the
per-receiver V are below 0.93, or past N = 800 (censored). Runs go to
`results/raw/ns3_spatial_stage1_runs.csv` through the same writer as `run_spatial.py`.

    python ns3/stage1_spatial.py --d-ref 215 --workers 4
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))

import run_spatial as rs  # noqa: E402

SEEDS = 5
STOP_BELOW = 0.93
N_LIMIT = 800
STEM = "stage1"


def start_and_step(scenario: str, config: str) -> tuple[int, int]:
    """First node count and step: the registered grids."""
    if scenario == "s2":
        return (30, 30) if config == "base" else (60, 60)
    return (20, 20) if config == "base" else (40, 40)


def walks() -> list[tuple[str, str]]:
    scen = ["s1-r100", "s1-r300", "s1-r600", "s1-r1000", "s2", "s3-v0"]
    return [(s, c) for s in scen for c in ("base", "inline4", "design")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--d-ref", type=float, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--sim-time", type=float, default=20.0)
    args = ap.parse_args()
    known = rs.scenarios(args.d_ref)
    path = rs.RAW / f"ns3_spatial_{STEM}_runs.csv"
    pos_dir = rs.RAW / f"ns3_spatial_{STEM}_positions"
    runs = rs.read_runs(path)
    lock = threading.Lock()
    config = {"seeds": SEEDS, "t": args.sim_time, "d_ref": args.d_ref, "stage": 1,
              "stop_below": STOP_BELOW, "n_limit": N_LIMIT,
              "configs": {k: asdict(v) for k, v in rs.CONFIGS.items()},
              "scenarios": {s: asdict(known[s]) for s, _ in walks()}}

    def on_file(scen: str, cfg: str, n: int) -> list[float]:
        return [float(r["v_mean_receiver"]) for r in runs
                if (r["scenario"], r["config"], int(r["n_nodes"])) == (scen, cfg, n)]

    def one(scen: str, cfg: str, n: int, seed: int) -> None:
        got, _, positions, _ = rs.run_one(known[scen], rs.CONFIGS[cfg], n, seed, args.sim_time)
        if known[scen].layout in ("disc", "clusters"):
            pos_dir.mkdir(exist_ok=True)
            where = pos_dir / f"{scen}.{n}.{seed}.csv"
            if not where.exists():
                where.write_text("".join(",".join(ln.split(",")[:4]) + "\n"
                                         for ln in positions.splitlines()))
        row = {"scenario": scen, "config": cfg, "frame_bytes": rs.CONFIGS[cfg].frame_bytes,
               "frames_per_s": rs.CONFIGS[cfg].frames_per_s, "n_nodes": n, "seed": seed,
               **{k: (int(v) if v.is_integer() else v) for k, v in got.items()
                  if k not in ("nNodes", "frameSize", "framesPerSec", "seed")}}
        with lock:
            runs.append({k: str(v) for k, v in row.items()})
            runs.sort(key=rs._key)
            rs.write(path, runs, f"ns3_spatial_{STEM}_runs", config)

    state = {w: start_and_step(*w)[0] for w in walks()}       # next node count to run
    below = dict.fromkeys(walks(), 0)
    active = set(walks())
    pending: dict[Future, tuple[str, str, int]] = {}
    outstanding: dict[tuple[str, str, int], int] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        def launch(w: tuple[str, str]) -> None:
            scen, cfg = w
            n = state[w]
            filed = {rs._key(r) for r in runs}          # a restart resumes where it stopped
            todo = [s for s in range(1, SEEDS + 1) if (scen, cfg, n, s) not in filed]
            outstanding[(scen, cfg, n)] = len(todo)
            if not todo:
                finish(w, n)
                return
            for s in todo:
                pending[pool.submit(one, scen, cfg, n, s)] = (scen, cfg, n)

        def finish(w: tuple[str, str], n: int) -> None:
            v = st.mean(on_file(*w, n))
            below[w] = below[w] + 1 if v < STOP_BELOW else 0
            print(f"{w[0]:9s} {w[1]:8s} N={n:4d}  V={v:.4f}", flush=True)
            step = start_and_step(*w)[1]
            if below[w] >= 2 or n + step > N_LIMIT:
                active.discard(w)
                print(f"{w[0]:9s} {w[1]:8s} stops after N={n}", flush=True)
                return
            state[w] = n + step
            launch(w)

        for w in walks():
            launch(w)
        while pending:
            done_now, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for fut in done_now:
                scen, cfg, n = pending.pop(fut)
                fut.result()
                outstanding[(scen, cfg, n)] -= 1
                if outstanding[(scen, cfg, n)] == 0:
                    finish((scen, cfg), n)


if __name__ == "__main__":
    main()
