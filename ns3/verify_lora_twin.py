#!/usr/bin/env python3
"""Gate for the LoRa twin (work package E of docs/prompts/NEXT_PHASE_PROMPT.md, C7).

`authbc-lora-dc.cc` at its defaults (`--channels=0`) must write the same output as
`authbc-lora-capacity.cc`, byte for byte, for the same arguments. The original produced frozen
results and is never edited. Two presets × two node counts × two seeds, each with the one-sided
jitter the stored LoRa runs use.

    python ns3/verify_lora_twin.py   -> results/raw/lora_twin_identity.csv; exit 1 on any difference
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = REPO / "results" / "raw" / "lora_twin_identity.csv"
CASES = [(region, n, seed) for region in ("aloha", "eu") for n in (5, 20) for seed in (1, 2)]
ARGS = "--dataRate=5 --payloadBytes=218 --appPeriod=38.4 --simulationTime=1200 --txJitter=1.0"


def run(program: str, region: str, n: int, seed: int, prefix: Path) -> str:
    """One run of a built program; its working directory is the temporary one (durations.txt)."""
    exe = ns3_root() / "build" / "scratch" / f"ns3.48-{program}-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    args = [str(exe), f"--nDevices={n}", f"--seed={seed}", f"--gwRegion={region}",
            *ARGS.split(), f"--outPrefix={prefix}"]
    subprocess.run(args, cwd=prefix.parent, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return prefix.with_suffix(".csv").read_text()


def main() -> int:
    rows, bad = [], 0
    with tempfile.TemporaryDirectory() as td:
        for region, n, seed in CASES:
            a = run("authbc-lora-capacity", region, n, seed, Path(td) / f"o{region}{n}{seed}")
            b = run("authbc-lora-dc", region, n, seed, Path(td) / f"t{region}{n}{seed}")
            same = a == b
            bad += not same
            got = dict(csv.reader(a.splitlines()[1:]))
            rows.append({"gw_region": region, "n_devices": n, "seed": seed,
                         "sent": got["sent"], "received": got["received"],
                         "identical": int(same)})
    buf = io.StringIO()
    chash = provenance.config_hash({"cases": str(CASES), "args": ARGS})
    for k, v in {**provenance.env_block(), "run": "lora_twin_identity",
                 "config_hash": chash}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    print(f"{len(rows) - bad} of {len(rows)} identical -> {OUT.relative_to(REPO)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
