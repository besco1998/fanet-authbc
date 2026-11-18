#!/usr/bin/env python3
"""C5, setting D2 (docs/prompts/CAPTURE_PROMPT.md §8.2): the pilot. 802.11a at 6 Mb/s, the
published PHY and detection model, Nakagami m = 1 fading on every link (`--nakagamiM=1`, one
draw per frame and link), two stations and no other traffic. Every frame lost at a receiver is
counted by cause, per frame length:
* **not detected:** a drop with ns-3 reason 9, PREAMBLE_DETECT_FAILURE (length-independent);
* **bit errors:** a reception that ends in error (ERR in `--traceRx=1`), which grows with length;
* **below sensitivity:** frames that leave no trace at all: received below the PHY's −101 dBm
  RxSensitivity, they are dropped before any reception starts (deep fades; the exponential tail
  puts 0.038 % of frames there at a mean of −66.84 dBm). Counted as tx − rx − every traced loss;
* **other:** any other drop, the two stations' own collisions among them (reasons 4 and 24).

Expected from the source (F135): above the −82 dBm floor a 6 Mb/s frame has no bit errors, so
with Rayleigh fading the loss is P(faded power < −82 dBm) = 1 − exp(−P_floor / P̄), the same at
every length. That is 3.00 % at a mean of −66.84 dBm. If so, §11 of the prompt applies: stop
and ask.

    python ns3/c5_d2_probe.py   -> results/raw/c5_d2_probe.csv
"""
from __future__ import annotations

import csv
import io
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402

OUT = REPO / "results" / "raw" / "c5_d2_probe.csv"
MEANS_DBM = (-70.0, -66.84, -64.0)
SIZES = (146, 173, 281, 425)
SEEDS = (1, 2, 3)
BASE = ["--nNodes=2", "--simTime=100", "--framesPerSec=50.0", "--txJitterMs=20.0",
        "--traceRx=1", "--nakagamiM=1"]
FLOOR_DBM = -82.0


def rayleigh_below_floor(mean_dbm: float) -> float:
    """P(an exponentially distributed power with this mean lies below the detection floor)."""
    return 1 - math.exp(-(10 ** (FLOOR_DBM / 10)) / (10 ** (mean_dbm / 10)))


def run(size: int, mean_dbm: float, seed: int, td: Path) -> dict[str, object]:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    prefix = td / f"d2_{size}_m{round(-mean_dbm * 100)}_s{seed}"
    subprocess.run([str(exe), *BASE, f"--seed={seed}", f"--frameSize={size}",
                    f"--rxPowerDbm={mean_dbm}", f"--outPrefix={prefix}"], check=True, env=env,
                   capture_output=True)
    kv = dict(csv.reader(prefix.with_suffix(".csv").read_text().splitlines()[1:]))
    c: Counter[str] = Counter()
    with Path(f"{prefix}_rx.csv").open() as fh:
        next(fh)
        for line in fh:
            kind, _n, _u, _t, value = line.rstrip("\n").split(",")
            c["ERR" if kind == "ERR" else f"DROP{value.strip()}"] += 1
    collided = c["DROP4"] + c["DROP24"]
    of = int(kv["tx_frames"]) - collided
    silent = int(kv["tx_frames"]) - int(kv["rx_frames"]) - sum(c.values())
    other = {k: v for k, v in c.items() if k not in ("ERR", "DROP9", "DROP4", "DROP24")}
    return {"mean_dbm": mean_dbm, "app_bytes": size, "seed": seed, "frames": of,
            "not_detected": c["DROP9"], "below_sensitivity": silent, "bit_errors": c["ERR"],
            "other_drops": "; ".join(f"{k}: {v}" for k, v in sorted(other.items())),
            "loss": round((c["DROP9"] + silent + c["ERR"]) / of, 6),
            "rayleigh_below_floor": round(rayleigh_below_floor(mean_dbm), 6)}


def main() -> None:
    with tempfile.TemporaryDirectory() as tdir, ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(run, s, m, seed, Path(tdir))
                for m in MEANS_DBM for s in SIZES for seed in SEEDS]
        rows = [j.result() for j in jobs]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "c5_d2_probe (not registered)",
                 "config_hash": provenance.config_hash({"base": BASE, "means": MEANS_DBM,
                                                        "sizes": SIZES,
                                                        "seeds": SEEDS})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
