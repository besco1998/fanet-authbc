#!/usr/bin/env python3
"""U5 (Mohamed, 2026-11-20): how much two module behaviours move each published LoRa number.

The published LoRa capacities come from the frozen scenario `authbc-lora-capacity.cc`, through
`ns3/run_lora_capacity.py`:
* the headline (`lora_capacity.csv`);
* the EU-gateway preset (`_eu`), the Goursaud capture matrix (`_goursaud`), and correlated
  shadowing at 500 m and 1 000 m (`_shadow500`, `_shadow1000`).

Each is rerun through the twin `authbc-lora-dc.cc` (default path identical to the original,
`ns3/verify_lora_twin.py`), with the same node counts, seeds 1–30, 3 600 s and a 1 s one-sided
jitter, in three variants:
* `base`: as published. **It must reproduce the stored delivered fractions exactly,** else stop;
* `noserver` (a): no network server, so no ADRACKReq downlinks during which the gateway is deaf;
* `nomic` (b): the period from the frame's time on air *in the module*, 358.656 ms for 218 B at
  SF7, instead of the repo's 363.78 ms, which counts a 4 B MIC the module never sends. So a true
  1 % duty.

For each variant, as `run_lora_capacity.py` computes them:
* N_max by the first-failure rule on the 30-seed mean (V ≥ 0.95);
* its 95 % bootstrap interval (`threshold_crossing_ci`, 10 000 resamples, seed 0);
* the strict reading (95 % of runs each meeting V).

The analytic payload-exclusion results (`lora_budget.csv`) take no part: neither behaviour
touches them.

    python ns3/run_u5_lora.py [workers]   -> results/raw/u5_lora_runs.csv, results/raw/u5_lora.csv
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

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.bench.stats import threshold_crossing_ci  # noqa: E402

RAW = REPO / "results" / "raw"
PAYLOAD, DR, SIM_S, JITTER_S, SEEDS, EPS = 218, 5, 3600.0, 1.0, 30, 0.05
PUBLISHED_PERIOD_S = 36.378            # the stored files' app_period_s: ToA 363.78 ms at 1 %
MODULE_TOA_S = 0.358656                # the twin's durations.txt for 218 B at SF7
CONFIGS = {   # name: (stored file, gwRegion, interferenceMatrix, channelModel, radius)
    "headline": ("lora_capacity.csv", "aloha", "aloha", "ideal", 1000.0),
    "eu": ("lora_capacity_eu.csv", "eu", "aloha", "ideal", 1000.0),
    "goursaud": ("lora_capacity_goursaud.csv", "aloha", "goursaud", "ideal", 1000.0),
    "shadow500": ("lora_capacity_shadow500.csv", "aloha", "aloha", "shadowing", 500.0),
    "shadow1000": ("lora_capacity_shadow1000.csv", "aloha", "aloha", "shadowing", 1000.0),
}
VARIANTS = {"base": ([], PUBLISHED_PERIOD_S), "noserver": (["--noServer=1"], PUBLISHED_PERIOD_S),
            "nomic": ([], MODULE_TOA_S / 0.01)}


def _rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in path.open() if not ln.startswith("#")))


def run_one(config: str, variant: str, n: int, seed: int) -> dict[str, str]:
    _f, gw, inter, chan, radius = CONFIGS[config]
    extra, period = VARIANTS[variant]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-lora-dc-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    with tempfile.TemporaryDirectory() as td:
        prefix = Path(td) / "c"
        # the same arguments, in the same order of meaning, as run_lora_capacity.run_one
        args = [str(exe), f"--nDevices={n}", f"--dataRate={DR}", f"--payloadBytes={PAYLOAD}",
                f"--appPeriod={period}", f"--simulationTime={SIM_S}", f"--seed={seed}",
                f"--outPrefix={prefix}", f"--gwRegion={gw}", f"--channelModel={chan}",
                f"--radius={radius}", f"--interferenceMatrix={inter}", f"--txJitter={JITTER_S}",
                *extra]
        proc = subprocess.run(args, cwd=td, env=env, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(f"exit {proc.returncode}: {' '.join(args)}")
        got = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    return {"config": config, "variant": variant, "n_devices": str(n), "seed": str(seed),
            "sent": got["sent"], "received": got["received"],
            "delivered_frac": got["delivered_frac"], "app_period_s": repr(period)}


def summarise(runs: list[dict[str, str]]) -> list[dict[str, object]]:
    out = []
    for config, (fname, *_r) in CONFIGS.items():
        stored = {int(r["n_devices"]): r for r in _rows(RAW / fname)}
        for variant in VARIANTS:
            per: dict[int, list[float]] = {}
            for r in runs:
                if (r["config"], r["variant"]) == (config, variant):
                    per.setdefault(int(r["n_devices"]), []).append(float(r["delivered_frac"]))
            n_max = n_strict = 0
            failed = strict_failed = False
            for n in sorted(per):
                vals = per[n]
                ok = sum(vals) / len(vals) >= 1 - EPS
                ok_strict = sum(v >= 1 - EPS for v in vals) / len(vals) >= 0.95
                if ok and not failed:
                    n_max = n
                elif not ok:
                    failed = True
                if ok_strict and not strict_failed:
                    n_strict = n
                elif not ok_strict:
                    strict_failed = True
            ci = threshold_crossing_ci(per, threshold=1 - EPS, resamples=10_000, seed=0)
            mismatch = sum(round(sum(v) / len(v), 5) != float(stored[n]["delivered_frac"])
                           for n, v in per.items()) if variant == "base" else ""
            out.append({"config": config, "variant": variant, "n_max": n_max,
                        "n_max_ci95": f"[{ci.ci_lo},{ci.ci_hi}]", "n_max_strict": n_strict,
                        **{f"delivered_n{n}": round(sum(v) / len(v), 5)
                           for n, v in sorted(per.items()) if n <= 10},
                        "base_rows_differing_from_stored": mismatch})
    return out


def main() -> int:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    todo = [(c, v, int(r["n_devices"]), s) for c, (fname, *_r) in CONFIGS.items()
            for r in _rows(RAW / fname) for v in VARIANTS for s in range(1, SEEDS + 1)]
    print(f"{len(todo)} runs", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        runs = list(pool.map(lambda t: run_one(*t), todo))
    head = "".join(f"# {k}={v}\n" for k, v in {**provenance.env_block(), "run": "u5_lora",
                                                "config_hash": provenance.config_hash(
                                                    {"configs": str(CONFIGS),
                                                     "variants": str(VARIANTS)})}.items())
    for path, data in ((RAW / "u5_lora_runs.csv", runs), (RAW / "u5_lora.csv", summarise(runs))):
        buf = io.StringIO(head)
        buf.seek(0, io.SEEK_END)
        fields = list(dict.fromkeys(k for row in data for k in row))
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(data)
        path.write_text(buf.getvalue())
    summary = _rows(RAW / "u5_lora.csv")
    bad = [r for r in summary if r["variant"] == "base" and r["base_rows_differing_from_stored"]
           not in ("0", "")]
    for r in summary:
        print(f"{r['config']:10s} {r['variant']:9s} N_max {r['n_max']} CI {r['n_max_ci95']} "
              f"strict {r['n_max_strict']}  base-vs-stored differing rows "
              f"{r['base_rows_differing_from_stored']}", flush=True)
    if bad:
        print("STOP: the base variant does not reproduce the stored results", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
