#!/usr/bin/env python3
"""Reduce a hardware ad-hoc broadcast sweep to one CSV with provenance (docs/06 §7, Law 7).

Pairs each transmitter window with the matching receiver window and emits per-window delivery.
Nothing is averaged here: the per-window rows ARE the artifact, because a single delivery figure
compared against a threshold is the failure mode that moved four headline numbers in this project.

⚠️ Two columns exist to keep an earlier mistake from recurring. `sent_app` is what `sendto`
accepted; `tx_frames_nic` is what the interface counter says actually left. On the 2.4 GHz run
these diverged sharply above the saturation knee, and treating `sent_app` as transmitted turned
local queue overflow into apparent channel loss. Delivery is reported against BOTH, and the
honest denominator is `tx_frames_nic` whenever the two disagree.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics as st
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def _load(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def _git_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def collect(tx_dir: Path, rx_dir: Path) -> list[dict]:
    rows = []
    for txf in sorted(tx_dir.glob("tx_*.json")):
        tag = txf.name[3:-5]
        tx, rx = _load(txf), _load(rx_dir / f"rx_{tag}.json")
        if not rx:
            continue
        ctx = _load(tx_dir / f"ctr_tx_{tag}.json")
        crx = _load(rx_dir / f"ctr_rx_{tag}.json")
        sent_app = tx.get("sent", 0)
        nic = ctx.get("tx_packets", 0)
        got = rx.get("received_unique", 0)
        idx, phase, rate = tag.split("_")
        rows.append({
            "window": idx,
            "phase": phase,
            "offered_fps": int(rate.removesuffix("fps")),
            "achieved_fps": round(tx.get("achieved_fps", 0.0), 2),
            "offered_mbps": round(tx.get("achieved_fps", 0.0) * tx.get("bytes", 0) * 8 / 1e6, 4),
            "sent_app": sent_app,
            "tx_frames_nic": nic,
            "tx_dropped_nic": ctx.get("tx_dropped", 0),
            "rx_frames_nic": crx.get("rx_packets", 0),
            "received_unique": got,
            "duplicates": rx.get("duplicates", 0),
            "delivered_vs_app": round(got / sent_app, 6) if sent_app else 0.0,
            # nic tx_packets counts ALL egress, not just our broadcast, so this is a lower bound
            # on delivery rather than an exact figure; it is reported to bound the app number.
            "delivered_vs_nic": round(got / nic, 6) if nic else 0.0,
            "rcvbuf_bytes": rx.get("rcvbuf_bytes", 0),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tx-dir", required=True, type=Path)
    ap.add_argument("--rx-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--band", required=True, help="e.g. '5GHz ch36 (802.11a)'")
    ap.add_argument("--frame-bytes", type=int, default=1400)
    a = ap.parse_args()

    rows = collect(a.tx_dir, a.rx_dir)
    if not rows:
        raise SystemExit(f"no paired windows found in {a.tx_dir} / {a.rx_dir}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as fh:
        fh.write("# AUTHBC hardware 802.11 ad-hoc broadcast sweep\n")
        fh.write(f"# generated_utc={datetime.now(UTC).isoformat()}\n")
        fh.write(f"# git_rev={_git_rev()}  host={platform.node()}"
                 f"  python={platform.python_version()}\n")
        fh.write(f"# band={a.band}  frame_bytes={a.frame_bytes}\n")
        fh.write("# tx=pi-a(authbc-pi4a) rx=pi-b(authbc-pi4b), 2 nodes, one transmitter\n")
        fh.write("# ⚠️ ONE transmitter: this measures LINK loss, NOT contention. It cannot\n")
        fh.write("#    validate Ma & Chen, which is a model of N contending stations.\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    phase_a = [r["delivered_vs_app"] for r in rows if r["phase"] == "A"]
    print(f"wrote {a.out}  ({len(rows)} windows)")
    if len(phase_a) > 1:
        print(f"phase A n={len(phase_a)} mean={st.mean(phase_a)*100:.3f}% "
              f"min={min(phase_a)*100:.3f}% max={max(phase_a)*100:.3f}% "
              f"stdev={st.stdev(phase_a)*100:.3f} pp")


if __name__ == "__main__":
    main()
