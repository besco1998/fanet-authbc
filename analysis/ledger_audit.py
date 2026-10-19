#!/usr/bin/env python3
"""Revision A16 — audit a one-hour mission's ledgers, with two faults planted (predictions/A16.md).

Three UAVs fly one hour at 50 records/s, four records to a frame (45 000 frames each), each
hearing the other two over an independent loss of 5 %. Everything is the real code: frames
from `LeanSender`, receivers `LeanReceiver` (which keep every frame they accept), the audit
`authbc.ledger.audit`. Two faults are planted:

* **equivocation** — UAV 2 signs a second version of its frame 10 000 and shows it to UAV 3,
  the original to UAV 1; its own upload holds the original;
* **a forged gap-fill** — UAV 3 adds to its upload a frame in UAV 1's name at a sequence number
  it lost, signed with UAV 3's own key.

Measured: the audit's wall time for the mission (one flight hour, so no scaling), the frames
audited, and the storage each UAV holds — as kept frames (what the receiver keeps) and as
decoded records, per sender-hour.

    python analysis/ledger_audit.py      # results/raw/ledger_audit.csv
"""
from __future__ import annotations

import csv
import io
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.ledger.audit import Upload, audit  # noqa: E402
from authbc.ledger.record import Record  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender  # noqa: E402

OUT = REPO / "results" / "raw" / "ledger_audit.csv"
UAVS = (1, 2, 3)
MISSION_S = 3600
LAMBDA, BATCH = 50, 4
LOSS = 0.05
SEED = 1616
FORK_FRAME = 10_000
_ED = Ed25519Scheme()


def keys() -> dict[int, tuple]:
    return {u: _ED.keygen(seed=bytes([u]) * 32) for u in UAVS}


def mission_records(uav: int) -> list[Record]:
    return leanframes.chained_records(uav, MISSION_S * LAMBDA, src=uav, base_seq=0,
                                      step_ms=1000 // LAMBDA)


def forked(recs: list[Record], sk) -> bytes:
    """A second, different version of a frame: the first record's time moved by 1 ms and the
    rest re-chained, signed by the same key."""
    alt: list[Record] = []
    for r in recs:
        link = alt[-1].record_hash() if alt else r.prev_hash
        alt.append(Record(src=r.src, seq=r.seq, ts=r.ts + (1 if not alt else 0),
                          prev_hash=link, pl=r.pl))
    return wire_v2.encode_frame_v2(wire_v2.build_B_v2(alt, sk))


def main() -> None:
    k = keys()
    pks = {u: pk for u, (_, pk) in k.items()}
    frames: dict[int, list[bytes]] = {}
    for u in UAVS:
        recs = mission_records(u)
        sender = LeanSender(k[u][0])
        frames[u] = [sender.frame(recs[i:i + BATCH]) for i in range(0, len(recs), BATCH)]
    fork = forked(mission_records(2)[FORK_FRAME * BATCH:(FORK_FRAME + 1) * BATCH], k[2][0])
    rng = np.random.default_rng(SEED)
    receivers = {u: LeanReceiver(pks) for u in UAVS}
    lost_by_3_from_1: list[int] = []
    t0 = time.perf_counter()
    for rx_id, rx in receivers.items():
        for src in UAVS:
            if src == rx_id:
                continue
            lost = rng.random(len(frames[src])) < LOSS
            for i, (data, gone) in enumerate(zip(frames[src], lost, strict=True)):
                if gone:
                    if (src, rx_id) == (1, 3):
                        lost_by_3_from_1.append(i)
                    continue
                if (src, rx_id, i) == (2, 3, FORK_FRAME):
                    data = fork
                rx.receive(data)
    receive_s = time.perf_counter() - t0
    gap = lost_by_3_from_1[len(lost_by_3_from_1) // 2]
    planted = wire_v2.encode_frame_v2(wire_v2.build_B_v2(
        mission_records(1)[gap * BATCH:(gap + 1) * BATCH], k[3][0]))
    uploads = []
    for u in UAVS:
        held = tuple(dict.fromkeys(receivers[u]._frames.values()))
        if u == 3:
            held += (planted,)
        uploads.append(Upload(u, tuple(frames[u]), held))
    t1 = time.perf_counter()
    report = audit(uploads, pks)
    audit_s = time.perf_counter() - t1
    fork_seq = FORK_FRAME * BATCH
    frame_bytes = sum(len(f) for f in frames[1])
    record_bytes = sum(len(r.canonical()) for r in mission_records(1))
    row = {
        "uavs": len(UAVS), "mission_s": MISSION_S, "lambda": LAMBDA, "batch": BATCH,
        "loss": LOSS, "frames_per_uav": len(frames[1]),
        "frames_held": sum(len(u.held) for u in uploads),
        "frames_audited": report.frames_audited,
        "receive_s": round(receive_s, 1), "audit_s": round(audit_s, 1),
        "audit_frames_per_s": round(report.frames_audited / audit_s, 1),
        "kept_bytes_per_sender_hour": frame_bytes * 3600 // MISSION_S,
        "kept_bytes_per_record": round(frame_bytes / (MISSION_S * LAMBDA), 3),
        "decoded_bytes_per_sender_hour": record_bytes * 3600 // MISSION_S,
        "decoded_bytes_per_record": round(record_bytes / (MISSION_S * LAMBDA), 3),
        "equivocation_detected": int(any(s == 2 and fork_seq <= q < fork_seq + BATCH
                                         for s, q in report.equivocations)),
        "forgery_detected": int((3, len(uploads[2].held) - 1) in report.forgeries),
        "false_findings": len(report.gaps) + len(report.broken_links)
        + len(report.bad_own_frames)
        + len([m for m in report.mismatches if not (m[1] == 2 and fork_seq <= m[2] < fork_seq + 4)])
        + len([f for f in report.forgeries if f != (3, len(uploads[2].held) - 1)])
        + len([e for e in report.equivocations
               if not (e[0] == 2 and fork_seq <= e[1] < fork_seq + BATCH)]),
        "merkle_root": report.merkle_root.hex(),
    }
    buf = io.StringIO()
    config = {"uavs": UAVS, "mission": MISSION_S, "loss": LOSS, "seed": SEED, "fork": FORK_FRAME}
    for key, v in {**provenance.env_block(), "run": "ledger_audit",
                   "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {key}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(row), lineterminator="\n")
    w.writeheader()
    w.writerow(row)
    OUT.write_text(buf.getvalue())
    print(row)


if __name__ == "__main__":
    main()
