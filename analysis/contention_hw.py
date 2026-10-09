#!/usr/bin/env python3
"""Contention on real radios: what the access-rule model predicts, and what the boards measured.

docs/CONTENTION_HW_EXPECTATIONS.md. Every 802.11 capacity in the paper is simulated. The model
of docs/02 §6g says why the simulated capacities are what they are; this is the first test of
it that does not run inside a simulator. Each of N boards in one ad-hoc cell sends one 1400 B
broadcast frame per period at an instant drawn within the period, and counts what it receives
from each of the others (`hw/channel/run_adhoc_contention.sh`).

    python analysis/contention_hw.py --predict
        writes results/raw/contention_hw_predictions.csv — committed BEFORE any measurement
    python analysis/contention_hw.py --ns3-check
        the same twelve points in ns-3 (needs the built simulator) -> contention_hw_ns3_check.csv
    python analysis/contention_hw.py --commands 3 --hosts pi@a pi@b pi@c
        prints the commands that start a three-board session
    python analysis/contention_hw.py --reduce 3 results/hw/channel/contention_3/node*
        writes results/hw/channel/contention_3nodes.csv and scores it against the predictions

A delivered fraction is frames received over frames sent, summed over every ordered pair of
boards — the definition the ns-3 scenario uses.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

RAW = REPO / "results" / "raw"
HW = REPO / "results" / "hw" / "channel"
PREDICTIONS = RAW / "contention_hw_predictions.csv"

UDP_PAYLOAD_BYTES = 1400            # what bcast_tx.py sends; the frame of the airtime measurement
IP_UDP_BYTES = 28                   # carried on air in addition; the model adds MAC, LLC and FCS
NODES = (2, 3, 4, 5)
OCCUPANCY = (0.50, 0.70, 0.85)      # N · f · T, the share of time the cell's frames take
SEEDS = 30
LINK_LOSS = 2.3e-4                  # measured on the two-board link with one transmitter
# The registered bands, as multiples of the model's loss (docs/CONTENTION_HW_EXPECTATIONS.md).
BAND_TWO_BOARDS = (0.6, 1.4)        # the receiver is the other transmitter: no capture
BAND_MORE_BOARDS = (0.3, 1.4)       # a third board may capture one of two colliding frames


def airtime_s() -> float:
    """Time the frame is on air (its PPDU), as the channel model computes it."""
    return bianchi.t_broadcast(UDP_PAYLOAD_BYTES + IP_UDP_BYTES) - model.DIFS_S


def rate_fps(n_nodes: int, occupancy: float) -> int:
    """Frames per second per board that fill `occupancy` of the medium among `n_nodes`."""
    return round(occupancy / (n_nodes * (airtime_s() + model.DIFS_S)))


def grid() -> list[tuple[int, float, int]]:
    return [(n, u, rate_fps(n, u)) for n in NODES for u in OCCUPANCY]


def _one(job: tuple[int, int, int]) -> tuple[int, int, float, int, int]:
    n, fps, seed = job
    r = model.run(n, fps, airtime_s(), seed=seed)
    return n, fps, r.delivered_frac, r.lost, r.lost_to_ties


def predict(workers: int = 4) -> list[dict]:
    jobs = [(n, fps, seed) for n, _u, fps in grid() for seed in range(1, SEEDS + 1)]
    runs: dict[tuple[int, int], list[tuple[float, int, int]]] = {}
    with Pool(workers) as pool:
        for n, fps, d, lost, ties in pool.imap_unordered(_one, jobs, chunksize=10):
            runs.setdefault((n, fps), []).append((d, lost, ties))
    rows = []
    for n, u, fps in grid():
        got = runs[(n, fps)]
        loss = 1.0 - st.mean(d for d, _l, _t in got)
        lo, hi = BAND_TWO_BOARDS if n == 2 else BAND_MORE_BOARDS
        rows.append({
            "nodes": n, "occupancy_target": u, "rate_fps_per_node": fps,
            "occupancy": round(n * fps * (airtime_s() + model.DIFS_S), 4),
            "model_loss": round(loss, 5),
            "model_loss_sd_between_seeds": round(st.pstdev(1.0 - d for d, _l, _t in got), 5),
            "model_tie_share": round(sum(t for _d, _l, t in got)
                                     / max(1, sum(lost for _d, lost, _t in got)), 3),
            "link_loss_added": LINK_LOSS,
            "predicted_loss": round(loss + LINK_LOSS, 5),
            "band_lo": round(lo * loss + LINK_LOSS, 5), "band_hi": round(hi * loss + LINK_LOSS, 5),
        })
    return rows


def _ns3_one(job: tuple[int, int, int]) -> tuple[int, int, float]:
    sys.path.insert(0, str(REPO / "ns3"))
    import run_nmax_direct as drv

    n, fps, seed = job
    r = drv.run_one(UDP_PAYLOAD_BYTES + IP_UDP_BYTES, fps, n, seed, 20.0,
                    jitter_ms=drv.one_period_ms(fps))
    return n, fps, r["delivered_frac"]


def ns3_check(workers: int = 3) -> list[dict]:
    """The registered points in ns-3, beside the model: is the model sound at two to five nodes?

    The model had been compared with ns-3 at 28 nodes and more. These are simulations of the
    same access rule, not measurements; they say whether the prediction is one simulator's or two.
    """
    reg = registered()
    jobs = [(n, fps, seed) for n, fps in reg for seed in range(1, SEEDS + 1)]
    runs: dict[tuple[int, int], list[float]] = {}
    with Pool(workers) as pool:
        for n, fps, d in pool.imap_unordered(_ns3_one, jobs):
            runs.setdefault((n, fps), []).append(1.0 - d)
    rows = []
    for (n, fps), r in sorted(reg.items()):
        loss, m = runs[(n, fps)], float(r["model_loss"])
        rows.append({"nodes": n, "rate_fps_per_node": fps, "model_loss": m,
                     "ns3_loss": round(st.mean(loss), 5),
                     "ns3_loss_se": round(st.stdev(loss) / len(loss) ** 0.5, 5),
                     "ns3_over_model": round(st.mean(loss) / m, 3), "seeds": len(loss)})
    return rows


def _write(path: Path, rows: list[dict], run: str) -> None:
    buf = io.StringIO()
    config = {"udp_payload": UDP_PAYLOAD_BYTES, "nodes": NODES, "occupancy": OCCUPANCY,
              "seeds": SEEDS, "slot_s": model.SLOT_S, "difs_s": model.DIFS_S, "w0": model.W0,
              "detect_s": model.DETECT_S}
    for k, v in {**provenance.env_block(), "run": run,
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue())


def registered() -> dict[tuple[int, int], dict[str, str]]:
    with PREDICTIONS.open(encoding="utf-8") as fh:
        return {(int(r["nodes"]), int(r["rate_fps_per_node"])): r
                for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))}


# --------------------------------------------------------------------------- the boards' output
def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def windows(node_dirs: list[Path], n_nodes: int) -> list[dict]:
    """One row per window: what every board sent, and what every other board received of it."""
    by_tag: dict[str, dict[str, dict[int, dict]]] = {}
    for d in node_dirs:
        for path in sorted(d.glob("*_node*_*.json")):
            m = re.fullmatch(r"(tx|rx|ctr)_node(\d+)_(.+)\.json", path.name)
            if m:
                by_tag.setdefault(m.group(3), {}).setdefault(m.group(1), {})[int(m.group(2))] = \
                    _load(path)
    rows = []
    for tag, parts in sorted(by_tag.items()):
        tx, rx, ctr = parts.get("tx", {}), parts.get("rx", {}), parts.get("ctr", {})
        nodes = list(range(1, n_nodes + 1))
        if sorted(tx) != nodes or sorted(rx) != nodes:
            raise SystemExit(f"window {tag}: expected tx and rx files from nodes {nodes}, "
                             f"found tx {sorted(tx)} rx {sorted(rx)}")
        sent = {k: tx[k]["sent"] for k in nodes}
        received = sum(rx[r]["by_source"].get(f"10.0.0.{s}", {}).get("received_unique", 0)
                       for s in nodes for r in nodes if r != s)
        rate = float(tx[1]["rate"])
        rows.append({
            "window": tag, "nodes": n_nodes, "rate_fps_per_node": round(rate),
            "sent": sum(sent.values()), "received": received,
            "delivered_frac": round(received / (sum(sent.values()) * (n_nodes - 1)), 6),
            "achieved_fps_min": round(min(tx[k]["achieved_fps"] for k in nodes), 2),
            "late_frames": sum(tx[k].get("late", 0) for k in nodes),
            "tx_dropped": sum(ctr[k]["tx_dropped"] for k in ctr),
            "duplicates": sum(rx[k]["duplicates"] for k in nodes),
        })
    return rows


def usable(row: dict) -> bool:
    """A window measures the channel only if the senders did what they were asked to do."""
    return (row["tx_dropped"] == 0
            and row["achieved_fps_min"] >= 0.98 * row["rate_fps_per_node"]
            and row["late_frames"] <= 0.01 * row["sent"])


def score(rows: list[dict]) -> list[dict]:
    """Mean loss per rate over the usable windows, against the registered prediction."""
    reg = registered()
    out = []
    for rate in sorted({r["rate_fps_per_node"] for r in rows}):
        mine = [r for r in rows if r["rate_fps_per_node"] == rate]
        good = [r for r in mine if usable(r)]
        key = (mine[0]["nodes"], rate)
        if key not in reg:
            raise SystemExit(f"no registered prediction for {key[0]} boards at {rate} frames/s")
        p = reg[key]
        loss = [1.0 - r["delivered_frac"] for r in good]
        measured = st.mean(loss) if loss else float("nan")
        out.append({
            "nodes": key[0], "rate_fps_per_node": rate, "windows": len(mine),
            "usable_windows": len(good),
            "measured_loss": round(measured, 5) if loss else "",
            "measured_loss_min": round(min(loss), 5) if loss else "",
            "measured_loss_max": round(max(loss), 5) if loss else "",
            "predicted_loss": float(p["predicted_loss"]),
            "band_lo": float(p["band_lo"]), "band_hi": float(p["band_hi"]),
            "inside_band": (float(p["band_lo"]) <= measured <= float(p["band_hi"]))
                           if loss else "",
        })
    return out


def commands(n_nodes: int, hosts: list[str], mode: str) -> list[str]:
    if len(hosts) != n_nodes:
        raise SystemExit(f"{n_nodes} boards need {n_nodes} hosts, got {len(hosts)}")
    rates = ",".join(str(rate_fps(n_nodes, u)) for u in OCCUPANCY)
    lines = ["START=$(( $(date +%s) + 60 ))"]
    for k, host in enumerate(hosts, start=1):
        # No `cd … &&` in front: a backgrounded `a && b` is a subshell that keeps the ssh
        # channel open, and the launching terminal then waits for the whole session.
        lines.append(f'ssh {host} "nohup setsid /home/pi/authbc_channel/'
                     f'run_adhoc_contention.sh {k} {n_nodes} $START {rates} 5180 {mode} '
                     f'>/dev/null 2>&1 </dev/null &"')
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--predict", action="store_true")
    what.add_argument("--ns3-check", action="store_true")
    what.add_argument("--commands", type=int, metavar="NODES")
    what.add_argument("--reduce", type=int, metavar="NODES")
    ap.add_argument("dirs", nargs="*", type=Path, help="one directory per board (--reduce)")
    ap.add_argument("--hosts", nargs="*", default=[], help="ssh targets, node 1 first")
    ap.add_argument("--mode", default="full", choices=("full", "probe"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.predict:
        rows = predict(args.workers)
        _write(PREDICTIONS, rows, "contention_hw_predictions")
        for r in rows:
            print(f"  {r['nodes']} boards  {r['rate_fps_per_node']:>4} frames/s  occupancy "
                  f"{r['occupancy']:.2f}  loss {100 * r['predicted_loss']:.2f} %  "
                  f"band {100 * r['band_lo']:.2f}–{100 * r['band_hi']:.2f} %")
    elif args.ns3_check:
        rows = ns3_check()
        _write(RAW / "contention_hw_ns3_check.csv", rows, "contention_hw_ns3_check")
        for r in rows:
            print(f"  {r['nodes']} boards  {r['rate_fps_per_node']:>4} frames/s  model "
                  f"{100 * r['model_loss']:.3f} %  ns-3 {100 * r['ns3_loss']:.3f} "
                  f"± {100 * r['ns3_loss_se']:.3f} %  ratio {r['ns3_over_model']}")
    elif args.commands:
        print("\n".join(commands(args.commands, args.hosts, args.mode)))
    else:
        rows = windows(args.dirs, args.reduce)
        _write(HW / f"contention_{args.reduce}nodes_windows.csv", rows, "contention_hw_windows")
        scored = score(rows)
        _write(HW / f"contention_{args.reduce}nodes.csv", scored, "contention_hw")
        for r in scored:
            verdict = {True: "inside", False: "OUTSIDE", "": "no usable window"}[r["inside_band"]]
            print(f"  {r['rate_fps_per_node']:>4} frames/s  measured {r['measured_loss']}  "
                  f"predicted {r['predicted_loss']}  [{r['band_lo']}, {r['band_hi']}]  {verdict} "
                  f"({r['usable_windows']} of {r['windows']} windows usable)")


if __name__ == "__main__":
    main()
