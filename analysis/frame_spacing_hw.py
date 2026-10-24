#!/usr/bin/env python3
"""How far apart one saturated sender's frames are on air, from the receiver's own clock.

docs/CONTENTION_HW_FRAMEBURST_EXPECTATIONS.md. IEEE 802.11 fixes the time from one frame of a
saturated station to its next: the frame, DIFS, and a counter drawn from 0…W−1 slots. It is the
quantity Bianchi et al. (INFOCOM 2007) measured on six commercial cards, none of which kept to
it. Here it separates two states of one chip: frame burst on (the Linux driver's setting) and
off.

⚠️ Why the receiver's clock and not the sender's rate. The sender's `achieved_fps` counts every
frame its `sendto` accepted, over the time it spent sending — including the frames still queued
in the kernel and the firmware when it stopped. The write-up of August 2026 took its reciprocal
as the time per frame and was 1.2 % low. The receiver sees frames as the air delivers them: the
sequence numbers it spans, over the time from the first frame received to the last.

    python analysis/frame_spacing_hw.py
        writes results/hw/channel/frame_spacing.csv from every one-sender session on disk
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import bianchi  # noqa: E402
from authbc.sim import dcf_unsaturated as model  # noqa: E402

HW = REPO / "results" / "hw" / "channel"
OUT = HW / "frame_spacing.csv"
UDP_PAYLOAD_BYTES = 1400
IP_UDP_BYTES = 28
SATURATED_BELOW = 0.98          # the sender achieved less than this share of what it was asked

# label, sender's directory, receiver's directory, frame burst during the session
SESSIONS = (
    ("2026-08-05", "5g_pi-a", "5g_pi-b", "on (driver's setting; not logged that day)"),
    ("2026-10-09", "one_sender_fb_on_2026-10-09_pi-a", "one_sender_fb_on_2026-10-09_pi-b",
     "on (driver's setting; not logged in this session)"),
    ("2026-10-09", "one_sender_fb_off_2026-10-09_pi-a", "one_sender_fb_off_2026-10-09_pi-b",
     "off (logged)"),
)


def ppdu_s() -> float:
    """The frame's time on air, as the channel model computes it."""
    return bianchi.t_broadcast(UDP_PAYLOAD_BYTES + IP_UDP_BYTES) - model.DIFS_S


def standard_cycle_s() -> float:
    """Frame, DIFS and the mean of a counter drawn from 0…W−1 slots: the standard's rule."""
    return ppdu_s() + model.DIFS_S + (model.W0 - 1) / 2 * model.SLOT_S


def spacing(tx: dict, rx: dict) -> dict:
    """One window. The cycle is the receiver's span over the sequence numbers it covers."""
    first = rx.get("min_seq", 0)            # files of before 2026-10-09 do not record it
    frames = rx["max_seq"] - first
    cycle = rx["span_s"] / frames
    return {
        "sent": tx["sent"], "received": rx["received_unique"],
        "sender_fps": round(tx["achieved_fps"], 2),
        "sender_ms_per_frame": round(1e3 / tx["achieved_fps"], 4),
        "first_seq_recorded": "min_seq" in rx,
        "frames_spanned": frames, "receiver_span_s": round(rx["span_s"], 4),
        "air_fps": round(1.0 / cycle, 2),
        "cycle_us": round(1e6 * cycle, 1),
        "gap_after_frame_us": round(1e6 * (cycle - ppdu_s()), 1),
    }


def saturated(tx: dict, offered_fps: int) -> bool:
    return tx["achieved_fps"] < SATURATED_BELOW * offered_fps


def session_rows(label: str, tx_dir: Path, rx_dir: Path, burst: str) -> list[dict]:
    rows = []
    for txf in sorted(tx_dir.glob("tx_*_B_*fps.json")):
        tag = txf.name[3:-5]
        offered = int(tag.split("_")[2].removesuffix("fps"))
        tx = json.loads(txf.read_text())
        rxf = rx_dir / f"rx_{tag}.json"
        if not rxf.exists() or not saturated(tx, offered):
            continue
        rows.append({"session": label, "frame_burst": burst, "window": tag,
                     "offered_fps": offered, **spacing(tx, json.loads(rxf.read_text())),
                     "ppdu_us": round(1e6 * ppdu_s(), 1),
                     "standard_cycle_us": round(1e6 * standard_cycle_s(), 1)})
    return rows


def collect() -> list[dict]:
    rows: list[dict] = []
    for label, tx_name, rx_name, burst in SESSIONS:
        if (HW / tx_name).is_dir() and (HW / rx_name).is_dir():
            rows += session_rows(label, HW / tx_name, HW / rx_name, burst)
    return rows


def main() -> None:
    rows = collect()
    if not rows:
        raise SystemExit("no saturated one-sender window found under results/hw/channel")
    buf = io.StringIO()
    config = {"udp_payload": UDP_PAYLOAD_BYTES, "saturated_below": SATURATED_BELOW,
              "slot_s": model.SLOT_S, "difs_s": model.DIFS_S, "w0": model.W0}
    for k, v in {**provenance.env_block(), "run": "frame_spacing_hw",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(f"  {r['session']}  burst {r['frame_burst'][:3]:3}  {r['window']:12} "
              f"cycle {r['cycle_us']:7.1f} µs  gap {r['gap_after_frame_us']:5.1f} µs  "
              f"on air {r['air_fps']:6.2f}/s  (sender's own rate {r['sender_fps']:.2f}/s; "
              f"standard cycle {r['standard_cycle_us']} µs)")


if __name__ == "__main__":
    main()
