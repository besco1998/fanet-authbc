#!/usr/bin/env python3
"""Check, before any run that uses them, that the audit twin's options for C3–C5 do what
`ns3/authbc-links-audit.cc` says (task of 2026-11-17, work package C), on short real runs:

* `--sizePattern=173,158`: each node's k-th frame (in enqueue order, which is its send order)
  has the airtime of pattern[k mod 2] — 304 µs and 284 µs at 802.11a, 6 Mb/s;
* `--burst=3` with 73 B frames: each node's frames are enqueued three at one instant, all
  172 µs on air;
* `--rxPowerDbm=-80`: every frame the PHY delivers is received at −80 dBm; without the option at
  the published −30.6571 dBm (audit item 8);
* `--nakagamiM=1` at a mean of −60 dBm: received powers vary frame by frame, and their linear
  mean is within 10 % of 1 nW. Only 0.6 % of draws fall below the −82 dBm detection floor and go
  unseen, so they bias the mean by less than 1 %;
* the driver's verification (`authbc.sim.verified`, `ns3/run_unified.py`): with r = 1 and n = 1
  the verified fraction equals the delivered fraction, on a real run of cell D.

    python ns3/check_twin_options.py   -> results/raw/twin_options_check.csv
"""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

import run_unified  # noqa: E402
from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

OUT = REPO / "results" / "raw" / "twin_options_check.csv"
BASE = ["--nNodes=3", "--simTime=2", "--seed=1", "--framesPerSec=12.5", "--txJitterMs=80.0"]


def _run(prefix: Path, *opts: str) -> None:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    subprocess.run([str(exe), *BASE, f"--outPrefix={prefix}", *opts], check=True, env=env,
                   capture_output=True)


def _frames(mac: Path) -> dict[int, list[tuple[int, int]]]:
    """Per node, (enqueue ns, airtime ns) of each frame, in enqueue order."""
    ev: dict[tuple[int, int], dict[str, int]] = defaultdict(dict)
    with mac.open() as fh:
        next(fh)
        for line in fh:
            kind, node, uid, t, _v = line.rstrip("\n").split(",")
            if kind in "EBF":
                ev[(int(node), int(uid))][kind] = int(t)
    out: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for (node, _uid), e in ev.items():
        if {"E", "B", "F"} <= e.keys():
            out[node].append((e["E"], e["F"] - e["B"]))
    return {k: sorted(v) for k, v in out.items()}


def _us(size: int) -> int:
    return round(uc.airtime_s(phy.OFDM_20MHZ_6M, size) * 1e9)


def check_size_pattern(td: Path) -> dict[str, object]:
    _run(td / "sp", "--frameSize=173", "--sizePattern=173,158", "--traceMac=1")
    want = (_us(173), _us(158))
    fr = _frames(td / "sp_mac.csv")
    ok = all(air == want[k % 2] for v in fr.values() for k, (_e, air) in enumerate(v))
    return {"check": "sizePattern 173,158", "frames": sum(map(len, fr.values())),
            "expected": f"airtime {want[0]} / {want[1]} ns alternating", "passed": ok}


def check_burst(td: Path) -> dict[str, object]:
    _run(td / "bu", "--frameSize=73", "--burst=3", "--traceMac=1")
    fr = _frames(td / "bu_mac.csv")
    ok = all(len(v) % 3 == 0 and all(air == _us(73) for _e, air in v)
             and all(v[i][0] == v[i + 1][0] == v[i + 2][0] for i in range(0, len(v), 3))
             for v in fr.values())
    return {"check": "burst 3 x 73 B", "frames": sum(map(len, fr.values())),
            "expected": f"enqueued in threes at one instant, {_us(73)} ns each", "passed": ok}


def _powers(rx: Path) -> set[float]:
    with rx.open() as fh:
        return {round(float(ln.split(",")[4].split(";")[0]), 4) for ln in fh
                if ln.startswith("PWR,")}


def check_rx_power(td: Path) -> list[dict[str, object]]:
    _run(td / "p80", "--frameSize=173", "--rxPowerDbm=-80", "--traceRx=2")
    _run(td / "p0", "--frameSize=173", "--traceRx=2")
    got80, got0 = _powers(td / "p80_rx.csv"), _powers(td / "p0_rx.csv")
    return [{"check": "rxPowerDbm -80", "frames": "", "expected": "every PWR at -80 dBm",
             "passed": got80 == {-80.0}},
            {"check": "rxPowerDbm off", "frames": "", "expected": "every PWR at -30.6571 dBm",
             "passed": got0 == {-30.6571}}]


def check_nakagami(td: Path) -> dict[str, object]:
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    subprocess.run([str(exe), *[a for a in BASE if not a.startswith("--simTime")], "--simTime=20",
                    f"--outPrefix={td / 'nk'}", "--frameSize=173", "--rxPowerDbm=-60",
                    "--nakagamiM=1", "--traceRx=2"], check=True, env=env, capture_output=True)
    with (td / "nk_rx.csv").open() as fh:
        dbm = [float(ln.split(",")[4].split(";")[0]) for ln in fh if ln.startswith("PWR,")]
    mean_nw = sum(10 ** (d / 10) for d in dbm) / len(dbm) * 1e6
    return {"check": "nakagamiM 1 at -60 dBm", "frames": len(dbm),
            "expected": f"varying; linear mean {mean_nw:.3f} nW within 10 % of 1 nW",
            "passed": len(set(dbm)) > len(dbm) // 2 and abs(mean_nw - 1.0) <= 0.10}


def check_verification() -> list[dict[str, object]]:
    rows = []
    for cell in ("DK1", "DU1"):
        r = run_unified.run_one(cell, 40, 1, None, ())
        rows.append({"check": f"verified == delivered ({cell}, N = 40)", "frames": r["tx_frames"],
                     "expected": f"delivered {r['delivered_frac']}",
                     "passed": r["verified_frac"] == r["delivered_frac"]})
    return rows


def main() -> None:
    with tempfile.TemporaryDirectory() as tdir:
        td = Path(tdir)
        rows = [check_size_pattern(td), check_burst(td), *check_rx_power(td),
                check_nakagami(td), *check_verification()]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "twin_options_check",
                 "config_hash": provenance.config_hash({"base": BASE})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())
    if not all(r["passed"] for r in rows):
        raise SystemExit("a twin option does not do what it says")


if __name__ == "__main__":
    main()
