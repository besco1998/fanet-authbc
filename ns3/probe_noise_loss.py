#!/usr/bin/env python3
"""Feasibility probe for C5 (task of 2026-11-17, work package C): can a fixed, equal received
power make the 173 B frame lose 1–3 % to noise alone at 802.11a, 6 Mb/s, in the published
configuration (ThresholdPreambleDetectionModel 4 dB / −82 dBm, TableBasedErrorRateModel)?

Two stations, 50 frames/s each, 20 simulated seconds, through the audit twin with
`--rxPowerDbm` and `--traceRx=1`. Every frame lost at a receiver is counted by cause: a decode
error after a detected preamble (ERR), or a drop with its ns-3 reason (DROP).
Not a registered run: it decides whether C5 can be run as the task states it.

    python ns3/probe_noise_loss.py   -> results/raw/c5_noise_probe.csv (6 Mb/s)
                                     -> results/raw/c5_noise_probe_rates.csv (24–54 Mb/s)
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = REPO / "results" / "raw" / "c5_noise_probe.csv"
OUT_RATES = REPO / "results" / "raw" / "c5_noise_probe_rates.csv"
# the higher 802.11a rates, to find where decode errors appear above the detection floor
RATES = ("OfdmRate24Mbps", "OfdmRate36Mbps", "OfdmRate48Mbps", "OfdmRate54Mbps")
RATE_POWERS = tuple(float(d) for d in range(-82, -63))
POWERS = (-70.0, -78.0, -80.0, -81.0, -81.5, -81.9, -82.0, -82.1, -82.5, -84.0)
SIZES = (173, 425)
BASE = ["--nNodes=2", "--simTime=20", "--seed=1", "--framesPerSec=50.0", "--txJitterMs=20.0",
        "--traceRx=1"]


def probe(size: int, dbm: float, td: Path, mode: str = "") -> dict[str, object]:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    prefix = td / f"p{mode}{size}_m{round(-dbm * 10)}"   # no dot: with_suffix would cut "-70.0"
    rate = ["--standard=80211a", f"--dataMode={mode}"] if mode else []
    subprocess.run([str(exe), *BASE, *rate, f"--frameSize={size}", f"--rxPowerDbm={dbm}",
                    f"--outPrefix={prefix}"], check=True, env=env, capture_output=True)
    kv = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    causes: Counter[str] = Counter()
    with Path(f"{prefix}_rx.csv").open() as fh:
        next(fh)
        for line in fh:
            kind, _node, _uid, _t, value = line.rstrip("\n").split(",")
            causes["ERR" if kind == "ERR" else f"DROP reason {value}"] += 1
    return {"mode": mode or "OfdmRate6Mbps", "frame_bytes": size, "rx_power_dbm": dbm,
            "tx_frames": kv["tx_frames"],
            "delivered_frac": kv["delivered_frac"],
            "decode_errors": causes.get("ERR", 0),
            "drops": "; ".join(f"{k}: {v}" for k, v in sorted(causes.items()) if k != "ERR")}


def _write(path: Path, rows: list[dict[str, object]], config: dict[str, object]) -> None:
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": f"{path.stem} (not registered)",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


def main() -> None:
    with tempfile.TemporaryDirectory() as tdir:
        rows = [probe(s, p, Path(tdir)) for s in SIZES for p in POWERS]
        _write(OUT, rows, {"base": BASE, "powers": POWERS, "sizes": SIZES})
        rows = [probe(s, p, Path(tdir), m) for m in RATES for p in RATE_POWERS for s in SIZES]
        _write(OUT_RATES, rows, {"base": BASE, "powers": RATE_POWERS, "sizes": SIZES,
                                 "rates": RATES})


if __name__ == "__main__":
    main()
