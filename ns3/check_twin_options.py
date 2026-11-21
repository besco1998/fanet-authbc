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

Added for work package F of `docs/prompts/NEXT_PHASE_PROMPT.md` (2026-11-20):
* `--placementOnly`: writes the positions and no result. They equal those a full run of the same
  seed and radius writes (`--perPair`), and all lie in the disc;
* `--outlierM=7` on a 2 m disc: node 0 at (7, 0), every other node where it was without the
  option;
* `--perPair`: per source, the receptions summed over receivers equal `--perNode`'s copies, and
  the frames sent agree;
* `--txPowerDbm=10`: every frame received 6.0206 dB below the published −30.6571 dBm (ns-3's
  default power is 16.0206 dBm);
* `--captureMarginDb=5`: the live PHY holds a SimpleFrameCaptureModel, and none without it.

Added for work package H (2026-11-20):
* `--slotUs=9` at 802.11b: the live slot is 9 µs and DIFS 28 µs (SIFS 10 + 2 × 9), read back;
  and in the timing of two saturated senders, every gap after a frame on DIFS + k·slot
  (the standard's 20 µs as the control): the read-back is taken before the run starts;
* `--cwMinList=3,63`: node 0's backoff draws stay within 0 … 3, and node 1's go above 3.

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


def _positions(path: Path) -> dict[int, tuple[float, float]]:
    with path.open() as fh:
        next(fh)
        return {int(n): (float(x), float(y)) for n, x, y in (ln.strip().split(",") for ln in fh)}


def check_placement(td: Path) -> list[dict[str, object]]:
    disc = ["--radiusM=10", "--pathLossExp=2"]
    _run(td / "po", *disc, "--placementOnly=1")
    _run(td / "pp", *disc, "--perPair=1", "--perNode=1")
    only, full = _positions(td / "po_positions.csv"), _positions(td / "pp_positions.csv")
    inside = all(x * x + y * y <= 100.0 for x, y in only.values())
    _run(td / "ol", "--radiusM=2", "--pathLossExp=2", "--outlierM=7", "--placementOnly=1")
    _run(td / "nl", "--radiusM=2", "--pathLossExp=2", "--placementOnly=1")
    ol, nl = _positions(td / "ol_positions.csv"), _positions(td / "nl_positions.csv")
    return [{"check": "placementOnly == the run's placement", "frames": "",
             "expected": "same positions, all in the disc, no result file",
             "passed": only == full and inside and not (td / "po.csv").exists()},
            {"check": "outlierM 7 on a 2 m disc", "frames": "",
             "expected": "node 0 at (7, 0); the others unmoved",
             "passed": ol[0] == (7.0, 0.0) and all(ol[i] == nl[i] for i in nl if i != 0)}]


def check_positions_file(td: Path) -> list[dict[str, object]]:
    """--positionsFile (UF2): a run reading back its own placement equals the run without the
    option, so no random stream moves; a placement from elsewhere is used exactly."""
    disc = ["--radiusM=10", "--pathLossExp=2"]
    # td / "pp" was run by check_placement: the same disc, --perPair and --perNode, no file
    _run(td / "pf0", *disc, "--placementOnly=1")
    _run(td / "pf1", *disc, "--perPair=1", "--perNode=1",
         f"--positionsFile={td / 'pf0_positions.csv'}")
    same = all((td / f"pf1_{s}.csv").read_bytes() == (td / f"pp_{s}.csv").read_bytes()
               for s in ("nodes", "pairs", "positions"))
    _run(td / "pf5", "--radiusM=5", "--pathLossExp=2", "--placementOnly=1")
    _run(td / "pf2", *disc, "--perPair=1", f"--positionsFile={td / 'pf5_positions.csv'}")
    moved = _positions(td / "pf2_positions.csv")
    return [{"check": "positionsFile with the run's own placement", "frames": "",
             "expected": "nodes, pairs and positions files byte-identical to the run without it",
             "passed": same},
            {"check": "positionsFile from another placement", "frames": "",
             "expected": "the file's positions exactly, not the seed's",
             "passed": moved == _positions(td / "pf5_positions.csv")
             and moved != _positions(td / "pp_positions.csv")}]


def check_per_pair(td: Path) -> dict[str, object]:
    # td / "pp" was run by check_placement with --perPair and --perNode together
    with (td / "pp_nodes.csv").open() as fh:
        nodes = {int(r["node"]): r for r in csv.DictReader(fh)}
    rx_by_src: dict[int, int] = defaultdict(int)
    tx_by_src: dict[int, set[int]] = defaultdict(set)
    with (td / "pp_pairs.csv").open() as fh:
        for r in csv.DictReader(fh):
            rx_by_src[int(r["src"])] += int(r["rx_frames"])
            tx_by_src[int(r["src"])].add(int(r["tx_frames"]))
    ok = all(rx_by_src[i] == int(nodes[i]["rx_copies"])
             and tx_by_src[i] == {int(nodes[i]["tx_frames"])} for i in nodes)
    return {"check": "perPair sums to perNode", "frames": sum(rx_by_src.values()),
            "expected": "per source: receptions and frames sent agree", "passed": ok}


def check_tx_power(td: Path) -> dict[str, object]:
    _run(td / "tx10", "--frameSize=173", "--txPowerDbm=10", "--traceRx=2")
    got = _powers(td / "tx10_rx.csv")
    return {"check": "txPowerDbm 10", "frames": "", "expected": "every PWR at -36.6777 dBm",
            "passed": got == {-36.6777}}


def _capture_model(path: Path) -> str:
    with path.open() as fh:
        return next(ln.strip().split(",", 1)[1] for ln in fh
                    if ln.startswith("frame_capture_model,"))


def check_capture_model(td: Path) -> dict[str, object]:
    _run(td / "cm5", "--captureMarginDb=5", "--constants=1")
    _run(td / "cm0", "--constants=1")
    on, off = _capture_model(td / "cm5_constants.csv"), _capture_model(td / "cm0_constants.csv")
    return {"check": "captureMarginDb 5", "frames": "",
            "expected": f"live model SimpleFrameCaptureModel ({on}); none without ({off})",
            "passed": "SimpleFrameCaptureModel" in on and "SimpleFrameCaptureModel" not in off}


def _constant(path: Path, key: str) -> str:
    with path.open() as fh:
        return next(ln.strip().split(",", 1)[1] for ln in fh if ln.startswith(key + ","))


def check_slot(td: Path) -> dict[str, object]:
    _run(td / "sl", "--standard=80211b", "--dataMode=DsssRate1Mbps", "--slotUs=9",
         "--constants=1")
    slot, difs = _constant(td / "sl_constants.csv", "slot_ns"), _constant(td / "sl_constants.csv",
                                                                         "difs_ns")
    return {"check": "slotUs 9 at 802.11b", "frames": "",
            "expected": f"slot 9000 ns, DIFS 28000 ns (got {slot}, {difs})",
            "passed": (slot, difs) == ("9000", "28000")}


def _gaps_ns(path: Path) -> list[int]:
    """Every gap from a frame's TX end to the next TX begin of any node, from the MAC trace."""
    ev = []
    with path.open() as fh:
        next(fh)
        for line in fh:
            kind, _node, _uid, t, _v = line.rstrip("\n").split(",")
            if kind in ("B", "F"):
                ev.append((int(t), kind))
    ev.sort()
    return [b[0] - a[0] for a, b in zip(ev, ev[1:], strict=False) if a[1] == "F" and b[1] == "B"]


def check_slot_timing(td: Path, slot_us: int) -> dict[str, object]:
    """The constants file is written before the simulation starts, so a slot reset at
    initialisation would not show there. Two saturated senders show it in their timing: every gap
    after a frame (not after a collision, which uses EIFS) is DIFS + k·slot."""
    difs_ns, slot_ns = (10 + 2 * slot_us) * 1000, slot_us * 1000
    _run(td / f"st{slot_us}", "--nNodes=2", "--framesPerSec=2000", "--txJitterMs=0.4",
         "--frameSize=173", "--standard=80211b", "--dataMode=DsssRate1Mbps", "--traceMac=1",
         *((f"--slotUs={slot_us}",) if slot_us != 20 else ()))
    gaps = _gaps_ns(td / f"st{slot_us}_mac.csv")
    on = [g for g in gaps if g >= difs_ns and (g - difs_ns) % slot_ns == 0]
    return {"check": f"slot {slot_us} us in the timing (802.11b, 2 saturated)",
            "frames": len(gaps),
            "expected": f"min gap {difs_ns} ns (got {min(gaps)}); >= 95 % on DIFS + k*{slot_ns} "
                        f"(got {100 * len(on) / len(gaps):.1f} %)",
            "passed": min(gaps) == difs_ns and len(on) >= 0.95 * len(gaps)}


def check_cw_list(td: Path) -> dict[str, object]:
    _run(td / "cw", "--frameSize=173", "--cwMinList=3,63", "--traceMac=1")
    draws: dict[int, list[int]] = defaultdict(list)
    with (td / "cw_mac.csv").open() as fh:
        next(fh)
        for line in fh:
            kind, node, _uid, _t, value = line.rstrip("\n").split(",")
            if kind == "K":
                draws[int(node)].append(int(value))
    ok = bool(draws[0]) and max(draws[0]) <= 3 and max(draws[1], default=0) > 3
    return {"check": "cwMinList 3,63", "frames": sum(map(len, draws.values())),
            "expected": f"node 0 draws <= 3 (max {max(draws[0], default=-1)}), node 1 above 3 "
                        f"(max {max(draws[1], default=-1)})", "passed": ok}


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
                check_nakagami(td), *check_verification(), *check_placement(td),
                check_per_pair(td), *check_positions_file(td), check_tx_power(td),
                check_capture_model(td),
                check_slot(td), check_slot_timing(td, 20), check_slot_timing(td, 9),
                check_cw_list(td)]
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
