#!/usr/bin/env python3
"""C5, setting D1 (docs/prompts/CAPTURE_PROMPT.md §8.2): the received-power pilot. At 802.11a
48 Mb/s, constant received power, ns-3's published detection model, two stations and no other
traffic: the share of frames lost to noise alone, per frame length of the sweep, measured in
ns-3, beside the same share computed from ns-3's error-rate model (`ns3/authbc-per.cc`).

A frame is counted at each receiver: lost to noise if its reception ends in error (ERR in
`--traceRx=1`); the collisions between the two stations (drops with reason 4 TXING and 24
SIGNAL_DETECTION_ABORTED_BY_TX) are excluded from both numerator and denominator.

    python ns3/c5_power_pilot.py -77.2 -77.17   -> results/raw/c5_d1_power_pilot.csv
    python ns3/c5_power_pilot.py --seeds 4-23 -77.17   -> results/raw/c5_d1_power_pilot_s4-23.csv

Seeds 1–3 at every power. Within one seed the lengths share the error model's random draws, so
their deviations from the computed loss have one sign; across seeds they are independent.
"""
from __future__ import annotations

import csv
import io
import math
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

OUT = REPO / "results" / "raw" / "c5_d1_power_pilot.csv"
MODE = "OfdmRate48Mbps"
SIZES = tuple(137 + 9 * b for b in (1, 2, 4, 8, 16, 32))
BASE = ["--nNodes=2", "--simTime=100", "--framesPerSec=50.0", "--txJitterMs=20.0",
        "--traceRx=1", "--standard=80211a", f"--dataMode={MODE}"]
SEEDS = (1, 2, 3)
COLLISION_REASONS = {"4", "24"}


def _env() -> dict[str, str]:
    return {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}


def computed(dbm: float) -> dict[int, float]:
    """PER(ℓ) from ns-3's TableBasedErrorRateModel, by `authbc-per`."""
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-per-optimized"
    out = subprocess.run([str(exe), f"--mode={MODE}", f"--rxPowerDbm={dbm}",
                          "--sizes=" + ",".join(map(str, SIZES))], check=True, env=_env(),
                         capture_output=True, text=True).stdout
    return {int(r["app_bytes"]): float(r["per"]) for r in csv.DictReader(io.StringIO(out))}


def measured(size: int, dbm: float, seed: int, td: Path) -> tuple[int, int]:
    """(frames lost to noise, frames that reached a receiver without a collision)."""
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    prefix = td / f"s{size}_{seed}"
    subprocess.run([str(exe), *BASE, f"--seed={seed}", f"--frameSize={size}",
                    f"--rxPowerDbm={dbm}",
                    f"--outPrefix={prefix}"], check=True, env=_env(), capture_output=True)
    kv = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    err = coll = 0
    with Path(f"{prefix}_rx.csv").open() as fh:
        next(fh)
        for line in fh:
            kind, _node, _uid, _t, value = line.rstrip("\n").split(",")
            err += kind == "ERR"
            coll += kind == "DROP" and value.strip() in COLLISION_REASONS
    # A frame whose reception ends after the receiving application stops (1 s + simTime) is
    # neither received nor dropped: seen once in 20 seeds (seed 15, 146 B, TX end 101.0000627 s).
    # One such frame per run is excluded; more would be a loss this count does not explain.
    other = int(kv["tx_frames"]) - int(kv["rx_frames"]) - err - coll
    if other > 1:
        raise SystemExit(f"{size} B: {other} frames lost to neither noise nor a collision")
    return err, int(kv["tx_frames"]) - coll - other


def main() -> None:
    args, seeds, out = sys.argv[1:], SEEDS, OUT
    if args[0] == "--seeds":
        lo, hi = map(int, args[1].split("-"))
        seeds, out, args = tuple(range(lo, hi + 1)), OUT.with_name(f"{OUT.stem}_s{args[1]}.csv"), \
            args[2:]
    powers = [float(a) for a in args]
    rows = []
    with tempfile.TemporaryDirectory() as td, ThreadPoolExecutor(max_workers=8) as pool:
        for dbm in powers:
            per = computed(dbm)
            jobs = {(size, seed): pool.submit(measured, size, dbm, seed, Path(td))
                    for size in SIZES for seed in seeds}
            for (size, seed), job in jobs.items():
                err, of = job.result()
                p = err / of
                sd = math.sqrt(per[size] * (1 - per[size]) / of)
                rows.append({"mode": MODE, "rx_power_dbm": dbm, "app_bytes": size,
                             "seed": seed, "frames": of, "lost_to_noise": err,
                             "measured_per": round(p, 6), "computed_per": round(per[size], 6),
                             "measured_minus_computed_in_sd": round((p - per[size]) / sd, 2)})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "c5_d1_power_pilot (not registered)",
                 "config_hash": provenance.config_hash({"base": BASE, "sizes": SIZES,
                                                        "seeds": seeds,
                                                        "powers": powers})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
