#!/usr/bin/env python3
"""Runs of the adaptive-batching scenario (revision A4; `ns3/authbc-adaptive.cc`,
`predictions/A4.md`).

    python ns3/run_adaptive.py --workers 6            # every registered run not yet on file

Each run is (scenario, policy, seed); its summary goes to `results/raw/ns3_adaptive_runs.csv`
(one row per run, checkpointed as runs finish) and its per-second series to
`results/raw/ns3_adaptive_ts/<scenario>.<policy>.<seed>.csv`.
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
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

RAW = REPO / "results" / "raw"
RUNS = RAW / "ns3_adaptive_runs.csv"
SERIES = RAW / "ns3_adaptive_ts"
SEEDS = tuple(range(1, 11))
POLICIES: dict[str, tuple[str, ...]] = {
    "adaptive": ("--policy=adaptive",), "fixed1": ("--policy=fixed", "--fixedB=1"),
    "fixed4": ("--policy=fixed", "--fixedB=4"), "oracle": ("--policy=oracle",)}
SCENARIOS: dict[str, tuple[str, ...]] = {
    # the plan's slope (1.5 nodes/s), stopped at 140 nodes: b <= 4 holds no policy above ~125
    "ramp": ("--scenario=ramp", "--rampStart=20", "--rampEnd=140", "--rampSeconds=80",
             "--simTime=90"),
    "merge": ("--scenario=merge", "--nNodes=120", "--simTime=180"),
    "mobile": ("--scenario=mobile", "--nNodes=100", "--speedMps=15", "--simTime=60"),
}


def run_one(scenario: str, policy: str, seed: int) -> tuple[dict[str, str], str]:
    root = ns3_root()
    exe = root / "build" / "scratch" / "ns3.48-authbc-adaptive-optimized"
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "a"
        subprocess.run([str(exe), *SCENARIOS[scenario], *POLICIES[policy], f"--seed={seed}",
                        f"--outPrefix={prefix}"], cwd=root, check=True,
                       env={**os.environ, "LD_LIBRARY_PATH": str(root / "build" / "lib")},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        summary = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
        series = Path(f"{prefix}_ts.csv").read_text()
    return summary, series


def read_runs() -> list[dict[str, str]]:
    if not RUNS.exists():
        return []
    with RUNS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def write_runs(rows: list[dict]) -> None:
    buf = io.StringIO()
    config = {"seeds": SEEDS, "policies": POLICIES, "scenarios": SCENARIOS}
    for k, v in {**provenance.env_block(), "run": "ns3_adaptive_runs",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(dict.fromkeys(k for r in rows for k in r)),
                       restval="", lineterminator="\n")
    w.writeheader()
    w.writerows(sorted(rows, key=lambda r: (r["scenario"], r["policy"], int(r["seed"]))))
    RUNS.write_text(buf.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS), choices=list(SCENARIOS))
    args = ap.parse_args()
    rows = read_runs()
    done = {(r["scenario"], r["policy"], int(r["seed"])) for r in rows}
    todo = [(s, p, seed) for s in args.scenarios for p in POLICIES for seed in SEEDS
            if (s, p, seed) not in done]
    # the costliest first: fixed b = 1 sends four times the frames
    todo.sort(key=lambda t: (t[1] != "fixed1", t[0] != "merge"))
    print(f"{len(rows)} runs on file, {len(todo)} to do", flush=True)
    SERIES.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, *t): t for t in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            scen, pol, seed = futures[fut]
            summary, series = fut.result()
            (SERIES / f"{scen}.{pol}.{seed}.csv").write_text(series)
            rows.append({"scenario": scen, "policy": pol, "seed": str(seed), **summary})
            write_runs(rows)
            print(f"  {i}/{len(todo)} {scen} {pol} {seed}", flush=True)


if __name__ == "__main__":
    main()
