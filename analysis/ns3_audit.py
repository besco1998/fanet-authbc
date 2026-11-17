#!/usr/bin/env python3
"""The ns-3 implementation audit's targeted runs and their reduction (task of 2026-11-17, work
package B; findings in docs/audits/2026-11-17_ns3_implementation_audit.md).

Every run uses the audit twin `ns3/authbc-links-audit.cc`, which is `authbc-links.cc` plus traces
that are off by default (gate: `ns3/verify_audit_twin.py`). Raw traces are large and regenerable
from the seeds below, so they go to a directory of the caller's choice; only the reductions are
kept, in results/raw/ns3_audit_*.csv.

    python analysis/ns3_audit.py --run DIR       # the runs below, into DIR
    python analysis/ns3_audit.py --reduce DIR    # results/raw/ns3_audit_{items,access_hist}.csv

What each reduction measures:
* item 1 — the access rule: for every frame, enqueue → transmit start, classified by what the
  medium was doing at enqueue (idle ≥ DIFS / idle < DIFS after a busy period / busy). Rule A sends
  an idle arrival at once; ns-3's `NeedBackoffUponAccess` (channel-access-manager.cc:551–560)
  sends it DIFS after its own arrival. The histogram decides.
* item 2 — CCA during collisions: a third station's PHY state over every overlap of others' frames.
* item 3 — EIFS: receptions that end in error (each starts an EIFS at that station), per frame.
* item 4 — frames that arrive while their station's post-transmission backoff may still run.
* item 5 — the mode and preamble of every received frame, per cell.
* item 6 — the PHY duration of every frame (TX end − begin = CalculateTxDuration) against the
  model's airtime, per cell.
* item 7 — the live constants of 802.11a, 802.11p and 802.11b.
* item 8 — received power over every pair, and receptions that survived an overlap (capture).
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import subprocess
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "ns3"))

from ns3_paths import ns3_root  # noqa: E402

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi, phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
DETECT_NS = 4_000
# name: (standard, mode, nodes, frames/s, bytes, sim s, extra options)
RUNS: dict[str, tuple[str, str, int, float, int, float, str]] = {
    # items 1-4 at the designated cells' crossings, 802.11a and 802.11b
    "C_cross": ("80211a", "OfdmRate6Mbps", 35, 50.0, 146, 20.0,
                "--traceMac=1 --traceRx=1 --traceStateNode=0 --constants=1"),
    "D_cross": ("80211a", "OfdmRate6Mbps", 124, 12.5, 173, 20.0,
                "--traceMac=1 --traceRx=1 --traceStateNode=0 --constants=1"),
    "Pb1D_cross": ("80211b", "DsssRate1Mbps", 31, 12.5, 173, 20.0,
                   "--traceMac=1 --traceRx=1 --traceStateNode=0 --constants=1"),
    "Pb1B_cross": ("80211b", "DsssRate1Mbps", 10, 50.0, 146, 20.0,
                   "--traceMac=1 --traceRx=1 --traceStateNode=0 --constants=1"),
    # items 5-7: every standard and rate on file, both frames, short
    **{f"phy_{std}_{mode}_{size}": (std, mode, 3, 50.0, size, 1.0,
                                    "--traceMac=1 --traceRx=2 --constants=1")
       for std, mode in (("80211a", "OfdmRate6Mbps"), ("80211a", "OfdmRate12Mbps"),
                         ("80211a", "OfdmRate24Mbps"), ("80211p", "OfdmRate3MbpsBW10MHz"),
                         ("80211p", "OfdmRate6MbpsBW10MHz"), ("80211p", "OfdmRate12MbpsBW10MHz"),
                         ("80211b", "DsssRate1Mbps"))
       for size in (146, 173)},
    # item 8: equal power and capture at N = 2 and at the largest N on file (MD10-500)
    "pwr_n2": ("80211a", "OfdmRate6Mbps", 2, 50.0, 173, 2.0, "--traceMac=1 --traceRx=2"),
    "pwr_n609": ("80211a", "OfdmRate6Mbps", 609, 2.5, 176, 2.0, "--traceMac=1 --traceRx=2"),
}
SEED = 1


def _phy_of(std: str, mode: str) -> phy.OfdmPhy | phy.DsssPhy:
    if std == "80211b":
        return phy.DSSS_1M
    rate = float(mode.replace("OfdmRate", "").split("Mbps")[0])
    return phy.ofdm_10mhz(rate) if std == "80211p" else phy.ofdm_20mhz(rate)


def _access(std: str) -> uc.Access:
    return {"80211a": uc.A80211A, "80211p": uc.A80211P, "80211b": uc.A80211B}[std]


# ------------------------------------------------------------------------------------------ runs
def run_one(name: str, out: Path) -> str:
    std, mode, n, fps, size, sim, extra = RUNS[name]
    exe = ns3_root() / "build" / "scratch" / "ns3.48-authbc-links-audit-optimized"
    jitter = 1000.0 / fps
    while jitter * 1e-3 > 1.0 / fps:
        jitter = math.nextafter(jitter, 0.0)
    args = [str(exe), f"--nNodes={n}", f"--framesPerSec={fps!r}", f"--frameSize={size}",
            f"--txJitterMs={jitter!r}", f"--simTime={sim}", f"--seed={SEED}",
            f"--outPrefix={out / name}", *extra.split()]
    if std != "80211a" or mode != "OfdmRate6Mbps":
        args += [f"--standard={std}", f"--dataMode={mode}"]
    env = {**os.environ, "LD_LIBRARY_PATH": str(ns3_root() / "build" / "lib")}
    subprocess.run(args, check=True, env=env, capture_output=True)
    return name


def run_all(out: Path, workers: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name in pool.map(lambda n: run_one(n, out), RUNS):
            print("done", name, flush=True)


# ------------------------------------------------------------------------------------- reading
def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


Tx = tuple[int, int, int, int]                      # (begin ns, end ns, node, uid)


def frames(mac: Path) -> tuple[dict[tuple[int, int], dict[str, int]], list[Tx]]:
    """{(node, uid): {E, B, F}} and every transmission (begin, end, node, uid), by begin."""
    fr: dict[tuple[int, int], dict[str, int]] = defaultdict(dict)
    with mac.open(encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            kind, node, uid, t, _ = line.rstrip("\n").split(",")
            if kind in ("E", "B", "F"):
                fr[(int(node), int(uid))][kind] = int(t)
    tx = sorted((v["B"], v["F"], k[0], k[1]) for k, v in fr.items() if "B" in v and "F" in v)
    return fr, tx


def busy_union(tx: list[Tx], detect_ns: int) -> list[tuple[int, int, int]]:
    """Busy periods as a station other than the senders sees them: each frame is sensed only
    from begin + detect; overlapping frames merge. (start, end, frames in the period)."""
    out: list[list[int]] = []
    for b, f, _n, _u in tx:
        s = b + detect_ns
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], f)
            out[-1][2] += 1
        else:
            out.append([s, f, 1])
    return [tuple(x) for x in out]  # type: ignore[misc]


# ------------------------------------------------------------------------------------ item 1
def item1(name: str, d: Path) -> tuple[dict, list[dict]]:
    std = RUNS[name][0]
    difs_ns = round(_access(std).difs_s * 1e9)
    fr, tx = frames(d / f"{name}_mac.csv")
    busy = busy_union(tx, DETECT_NS)
    starts = [b[0] for b in busy]
    classes: Counter[str] = Counter()
    hist: Counter[tuple[str, int]] = Counter()
    exact_difs = {"idle": 0, "gap": 0}
    at_once = {"idle": 0, "gap": 0}
    for (_node, _uid), v in fr.items():
        if "E" not in v or "B" not in v:
            continue
        te, tb = v["E"], v["B"]
        i = bisect_right(starts, te) - 1
        if i >= 0 and busy[i][0] <= te < busy[i][1]:
            cls = "busy"
        else:
            last_end = busy[i][1] if i >= 0 else -10**12
            cls = "gap" if te - last_end < difs_ns else "idle"
        classes[cls] += 1
        wait_us = (tb - te) / 1000
        hist[(cls, min(int(wait_us), 400))] += 1
        if cls in ("idle", "gap"):
            exact_difs[cls] += abs((tb - te) - difs_ns) < 500
            at_once[cls] += tb - te < 500
    summary = {"run": name, "item": 1, "frames": sum(classes.values()),
               **{f"arrived_{c}": classes[c] for c in ("idle", "gap", "busy")},
               "idle_sent_at_difs_after_arrival": exact_difs["idle"],
               "idle_sent_at_once": at_once["idle"],
               "gap_sent_at_difs_after_arrival": exact_difs["gap"],
               "gap_sent_at_once": at_once["gap"], "difs_us": difs_ns / 1000}
    rows = [{"run": name, "class": c, "wait_us_floor": w, "frames": k}
            for (c, w), k in sorted(hist.items())]
    return summary, rows


# ------------------------------------------------------------------------------------ item 2
def item2(name: str, d: Path) -> dict:
    """Node 0's PHY state over every period in which two or more OTHER stations' frames overlap."""
    _fr, tx = frames(d / f"{name}_mac.csv")
    state = [(int(r["start_ns"]), int(r["start_ns"]) + int(r["duration_ns"]), int(r["state"]))
             for r in _csv(d / f"{name}_state.csv")]
    idle_states = {0}                               # WifiPhyState IDLE (wifi-phy-state.h)
    others = [(b, f) for b, f, n, _u in tx if n != 0]
    groups: list[list[int]] = []
    for b, f in others:
        if groups and b < groups[-1][1]:
            groups[-1][1] = max(groups[-1][1], f)
            groups[-1][2] += 1
        else:
            groups.append([b, f, 1])
    collided = [(b + DETECT_NS, f) for b, f, k in groups if k > 1]
    own = [(b, f) for b, f, n, _u in tx if n == 0]
    idle_ns = total_ns = 0
    starts = [s for s, _e, _st in state]
    for s, e in collided:
        if any(ob < e and of > s for ob, of in own):
            continue                                # node 0 itself was sending
        total_ns += e - s
        i = max(0, bisect_right(starts, s) - 1)
        while i < len(state) and state[i][0] < e:
            a, b, code = state[i]
            if code in idle_states:
                idle_ns += max(0, min(b, e) - max(a, s))
            i += 1
    return {"run": name, "item": 2, "collided_periods": len(collided),
            "collided_ns_observed": total_ns, "idle_ns_during_collisions": idle_ns}


# ------------------------------------------------------------------------------------ item 3
def item3(name: str, d: Path) -> dict:
    rx = _csv(d / f"{name}_rx.csv")
    errs = sum(r["kind"] == "ERR" for r in rx)
    drops = Counter(r["value"] for r in rx if r["kind"] == "DROP")
    fr, tx = frames(d / f"{name}_mac.csv")
    n = RUNS[name][2]
    return {"run": name, "item": 3, "frames": len(tx), "rx_error_ends": errs,
            "rx_error_per_frame_per_receiver": round(errs / (len(tx) * (n - 1)), 6),
            "drops_by_reason": " ".join(f"{k}:{v}" for k, v in sorted(drops.items()))}


# ------------------------------------------------------------------------------------ item 4
def item4(name: str, d: Path) -> dict:
    """Frames enqueued within (DIFS + (W−1)·σ + own airtime) after their station's previous frame
    ended: the only ones a post-transmission backoff can still be holding (an upper bound)."""
    std = RUNS[name][0]
    acc = _access(std)
    fr, _tx = frames(d / f"{name}_mac.csv")
    by_node: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for (node, _uid), v in fr.items():
        if {"E", "B", "F"} <= v.keys():
            by_node[node].append((v["E"], v["B"], v["F"]))
    window = round((acc.difs_s + (acc.w - 1) * acc.slot_s) * 1e9)
    exposed = total = 0
    for seq in by_node.values():
        seq.sort()
        for (_e0, _b0, f0), (e1, _b1, _f1) in zip(seq, seq[1:], strict=False):
            total += 1
            exposed += 0 <= e1 - f0 < window
    return {"run": name, "item": 4, "frames": total, "enqueued_within_post_backoff_bound": exposed,
            "bound_us": window / 1000}


# ------------------------------------------------------------------------------- items 9, 11
def item9(name: str, d: Path) -> dict:
    """Frames enqueued while their own station's previous frame was still waiting (queued behind
    another), and frames enqueued but never sent before the run ended."""
    fr, _tx = frames(d / f"{name}_mac.csv")
    by_node: dict[int, list[tuple[int, int | None]]] = defaultdict(list)
    for (node, _uid), v in fr.items():
        if "E" in v:
            by_node[node].append((v["E"], v.get("B")))
    behind = unsent = total = 0
    for seq in by_node.values():
        seq.sort()
        prev_b: int | None = -1
        for e, b in seq:
            total += 1
            unsent += b is None
            behind += prev_b is None or (prev_b is not None and e < prev_b)
            prev_b = b
    return {"run": name, "item": 9, "frames_enqueued": total, "queued_behind_own": behind,
            "never_sent": unsent}


def item11(name: str, d: Path) -> dict:
    """Start-time spread inside every group of overlapping frames: 0 = the same instant (a tie in
    the same slot), else the other start fell inside the detection window δ."""
    _fr, tx = frames(d / f"{name}_mac.csv")
    groups: list[list[int]] = []
    reach = -1
    for b, f, _n, _u in tx:
        if groups and b < reach:
            groups[-1].append(b)
        else:
            groups.append([b])
        reach = max(reach, f) if groups[-1] != [b] else f
    spreads = [max(g) - min(g) for g in groups if len(g) > 1]
    hist = Counter(min(sp // 1000, 9) for sp in spreads)
    return {"run": name, "item": 11, "collisions": len(spreads),
            "same_instant": sum(sp == 0 for sp in spreads),
            "max_spread_ns": max(spreads) if spreads else "",
            "spread_us_hist": " ".join(f"{k}:{v}" for k, v in sorted(hist.items()))}


# ------------------------------------------------------------------------------- items 5, 6, 8
def items568(name: str, d: Path) -> dict:
    """Mode, preamble and power of every received frame; TX durations; OK receptions of frames
    whose transmission overlapped another's (capture). The receive trace is streamed: at 609
    stations it holds millions of rows."""
    std, mode, n, _fps, size, _sim, _x = RUNS[name]
    _fr, tx = frames(d / f"{name}_mac.csv")
    collided: set[int] = set()
    reach = -1                                      # latest end among the frames before this one
    for j, (b, f, _n, uid) in enumerate(tx):
        if reach > b or (j + 1 < len(tx) and tx[j + 1][0] < f):
            collided.add(uid)
        reach = max(reach, f)
    modes: Counter[str] = Counter()
    preambles: Counter[str] = Counter()
    lo, hi, captured = math.inf, -math.inf, 0
    with (d / f"{name}_rx.csv").open(encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            kind, _node, uid, _t, value = line.rstrip("\n").split(",", 4)
            if kind == "PWR":
                sig, _noise, m, pre = value.split(";")
                modes[m] += 1
                preambles[pre] += 1
                lo, hi = min(lo, float(sig)), max(hi, float(sig))
            elif kind == "OK" and int(uid) in collided:
                captured += 1
    durs = Counter(f - b for b, f, _n, _u in tx)
    model_ns = round(uc.airtime_s(_phy_of(std, mode), size) * 1e9)
    bianchi_ns = (round((bianchi.t_broadcast(size) - bianchi.DIFS) * 1e9)
                  if (std, mode) == ("80211a", "OfdmRate6Mbps") else "")
    return {"run": name, "item": "5/6/8", "standard": std, "mode": mode, "nodes": n,
            "frame_bytes": size, "frames": len(tx),
            "rx_modes": " ".join(f"{k}:{v}" for k, v in modes.items()),
            "rx_preamble_types": " ".join(f"{k}:{v}" for k, v in preambles.items()),
            "tx_duration_ns": " ".join(f"{k}:{v}" for k, v in sorted(durs.items())),
            "model_airtime_ns": model_ns, "bianchi_minus_difs_ns": bianchi_ns,
            "signal_dbm_min": lo if modes else "", "signal_dbm_max": hi if modes else "",
            "collided_frames": len(collided), "ok_receptions_of_collided": captured}


def constants(d: Path) -> list[dict]:
    rows = []
    for f in sorted(d.glob("phy_*_146_constants.csv")):
        kv = {r["key"]: r["value"] for r in _csv(f)}
        rows.append({"run": f.name.replace("_constants.csv", ""), "item": 7, **kv})
    return rows


def _write(path: Path, rows: list[dict], run: str) -> None:
    fields: list[str] = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": run, "ns3": "3.48",
                 "config_hash": provenance.config_hash({"runs": str(RUNS), "seed": SEED})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue())


def reduce_all(d: Path) -> None:
    items: list[dict] = []
    hist: list[dict] = []
    for name in ("C_cross", "D_cross", "Pb1D_cross", "Pb1B_cross"):
        s, h = item1(name, d)
        items.append(s)
        hist += h
        items += [item2(name, d), item3(name, d), item4(name, d), item9(name, d),
                  item11(name, d)]
    items += [items568(name, d) for name in RUNS if name.startswith(("phy_", "pwr_"))]
    items += constants(d)
    _write(RAW / "ns3_audit_items.csv", items, "ns3_audit_items")
    _write(RAW / "ns3_audit_access_hist.csv", hist, "ns3_audit_access_hist")
    for r in items:
        print(r)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--run", type=Path, metavar="DIR")
    what.add_argument("--reduce", type=Path, metavar="DIR")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    if args.run:
        run_all(args.run, args.workers)
    else:
        reduce_all(args.reduce)


if __name__ == "__main__":
    main()
