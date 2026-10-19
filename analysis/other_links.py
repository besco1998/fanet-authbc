#!/usr/bin/env python3
"""Revision A17 — the paper's accounting applied to ADS-B, Remote ID and V2X CAM.

Analysis only (predictions/A17.md). For each broadcast system: the largest payload M one
transmission carries, its message rate Λ, and (where one applies) a deadline; then Eq. (5)
(can a frame that verifies alone fit at all?), the largest batch the payload admits, and
Eq. (2) (which batch the deadline admits). The frame is the lean design's: its one-record
frame and per-record delta as the codec EMITS them at the system's message spacing
(`leanframes.lean_frame_sizes`, generator walk at that spacing, capped at 1 s by the generator).
The record is ours, not the system's: this asks whether OUR self-verifying frame would fit
the link, which is what the paper's generality claim says.

Every M and Λ is from a source held and read (`docs/literature/README.md`):

* ADS-B 1090ES: 112-bit messages of which "only the 56 bit ME field can be used to transmit
  arbitrary data"; position "typically twice per second" (Strohmeier et al. 2015, p. 2).
* Remote ID, Bluetooth 4 legacy advertising: "25 octets of payload per frame"; Bluetooth 5 /
  Wi-Fi: a Message Pack of up to nine 25-octet messages in one frame, sent once per second
  (RFC 9575 §3.2.4.1, §6.2).
* CAM: generation interval 100–1 000 ms, i.e. 10 Hz down to 1 Hz (ETSI EN 302 637-2 V1.4.1
  §6.1.3); messages signed per ETSI TS 103 097 (held). The standard sets no end-to-end
  deadline; the deadlines below are swept, not quoted.

    python analysis/other_links.py      # results/raw/other_links.csv
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import design_map  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402

OUT = REPO / "results" / "raw" / "other_links.csv"
SIG_BYTES = 64
# (system, max payload per transmission in bytes, messages/s, source)
LINKS: tuple[tuple[str, float, float, str], ...] = (
    ("ADS-B 1090ES (ME field)", 56 / 8, 2.0, "Strohmeier et al. 2015, p. 2"),
    ("Remote ID, Bluetooth 4 legacy", 25.0, 1.0, "RFC 9575 §3.2.4.1, §6.2"),
    ("Remote ID, Bluetooth 5 / Wi-Fi (Message Pack)", 9 * 25.0, 1.0, "RFC 9575 §6.2"),
    ("V2X CAM at 10 Hz (802.11p, 1500 B MTU)", 1500.0, 10.0, "ETSI EN 302 637-2 §6.1.3"),
    ("V2X CAM at 1 Hz (802.11p, 1500 B MTU)", 1500.0, 1.0, "ETSI EN 302 637-2 §6.1.3"),
)
DEADLINES_MS: tuple[float, ...] = (100.0, 200.0, 300.0, 500.0, 1_000.0, 2_000.0, 5_000.0)


def spacing_ms(rate: float) -> int:
    """Record spacing for the generator walk: the system's message interval, at most 1 s."""
    return min(1000, round(1000.0 / rate))


def frame_bytes(rate: float, batch: int) -> float:
    return leanframes.lean_frame_sizes(batch, step_ms=spacing_ms(rate)).mean


def payload_batch(m: float, rate: float) -> int:
    """Largest batch whose emitted frame fits M; 0 if the one-record frame does not."""
    b = 0
    while b < wire_v2.MAX_RECORDS and frame_bytes(rate, b + 1) <= m:
        b += 1
    return b


def rows() -> list[dict]:
    t_ch, t_v = design_map.budget()
    out = []
    for name, m, rate, source in LINKS:
        one = frame_bytes(rate, 1)
        b_pay = payload_batch(m, rate)
        base = {"system": name, "max_payload_bytes": m, "messages_per_s": rate,
                "source": source, "one_record_frame_bytes": round(one, 3),
                "signature_fits": int(m >= SIG_BYTES), "frame_fits": int(m >= one),
                "payload_batch": b_pay}
        for d in DEADLINES_MS:
            b_fresh = design_map.b_star(rate, d, t_ch, t_v)
            b = min(b_pay, b_fresh)
            out.append({**base, "d_max_ms": d, "lam_dmax": round(rate * d / 1000, 3),
                        "fresh_batch": b_fresh, "batch": b,
                        "bytes_per_rec": round(frame_bytes(rate, b) / b, 3) if b else "",
                        "verdict": ("excluded: signature alone" if m < SIG_BYTES else
                                    "excluded: frame" if m < one else
                                    "no frame meets the deadline" if b_fresh == 0 else
                                    "one record per frame" if b == 1 else f"batch of {b}")})
    return out


def main() -> None:
    got = rows()
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "other_links",
                 "config_hash": provenance.config_hash({"links": LINKS, "d": DEADLINES_MS})
                 }.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(got[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(got)
    OUT.write_text(buf.getvalue())
    for r in got:
        print(f"{r['system']:48s} D={r['d_max_ms']:>6g}  {r['verdict']}")


if __name__ == "__main__":
    main()
