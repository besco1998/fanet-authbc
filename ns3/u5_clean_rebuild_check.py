#!/usr/bin/env python3
"""U5, the N ≥ 20 reproduction drift (Mohamed, 2026-11-21): one rebuild from a clean tree, then
record and close (`docs/revision/2026-11-20_u5_frozen_lora.md`).

**What was found on 2026-11-20.** Today's build reproduced every stored LoRa mean at N ≤ 15
exactly, and differed at N ≥ 20 by at most 6 × 10⁻⁵, from one or two runs per node count.

**The rebuild.** A fresh copy of `ns3/ns-3.48` (sources, the lorawan module with its patch, the
scratch programs; no `build/`, no `cmake-cache/`), configured as the original (optimized profile,
examples on, tests off, native optimisations on) and compiled with ccache disabled, so every
object is new. It is pointed to by AUTHBC_NS3 (`ns3_paths.ns3_root`).

**The check.** The frozen scenario `authbc-lora-capacity`, from the clean tree, at every published
configuration and node count N ≥ 20, seeds 1–30, with run_lora_capacity's arguments:
* each run's sent and received counts against U5's `base` runs from the main tree
  (`results/raw/u5_lora_runs.csv`; the twin, which equals the original there);
* each node count's 30-seed mean against the stored file, at the five decimals it holds.

    AUTHBC_NS3=<clean tree> python ns3/u5_clean_rebuild_check.py [workers]
        -> results/raw/u5_clean_rebuild_check.csv
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

import run_u5_lora as u5  # noqa: E402
from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = u5.RAW / "u5_clean_rebuild_check.csv"


def run_original(config: str, n: int, seed: int) -> dict[str, str]:
    _f, gw, inter, chan, radius = u5.CONFIGS[config]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-lora-capacity-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "c"
        args = [str(exe), f"--nDevices={n}", f"--dataRate={u5.DR}",
                f"--payloadBytes={u5.PAYLOAD}", f"--appPeriod={u5.PUBLISHED_PERIOD_S}",
                f"--simulationTime={u5.SIM_S}", f"--seed={seed}", f"--outPrefix={prefix}",
                f"--gwRegion={gw}", f"--channelModel={chan}", f"--radius={radius}",
                f"--interferenceMatrix={inter}", f"--txJitter={u5.JITTER_S}"]
        proc = subprocess.run(args, cwd=td, env=env, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"exit {proc.returncode}: {' '.join(args)}")
        got = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    return {"config": config, "n": str(n), "seed": str(seed), "sent": got["sent"],
            "received": got["received"]}


def main() -> int:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    if ns3_root() == (REPO / "ns3" / "ns-3.48"):
        raise SystemExit("set AUTHBC_NS3 to the clean tree: this check is against the main one")
    stored_runs = u5._rows(u5.RAW / "u5_lora_runs.csv")
    base = {(r["config"], r["n_devices"], r["seed"]): r for r in stored_runs
            if r["variant"] == "base"}
    jobs = sorted({(c, int(n)) for c, n, _s in base if int(n) >= 20})
    runs = []
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(run_original, c, n, s) for c, n in jobs for s in range(1, u5.SEEDS + 1)]
        runs = [f.result() for f in futs]
    rows = []
    for c, n in jobs:
        mine = [r for r in runs if (r["config"], r["n"]) == (c, str(n))]
        same = sum((r["sent"], r["received"]) == (base[(c, str(n), r["seed"])]["sent"],
                                                  base[(c, str(n), r["seed"])]["received"])
                   for r in mine)
        mean = sum(int(r["received"]) / int(r["sent"]) for r in mine) / len(mine)
        stored = {int(r["n_devices"]): r for r in u5._rows(u5.RAW / u5.CONFIGS[c][0])}[n]
        rows.append({"config": c, "n_devices": n, "runs": len(mine),
                     "runs_identical_to_main_build": same,
                     "clean_mean": round(mean, 5), "stored_mean": stored["delivered_frac"],
                     "clean_equals_stored": round(mean, 5) == float(stored["delivered_frac"])})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "u5_clean_rebuild_check",
                 "ns3_tree": str(ns3_root())}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    print(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
