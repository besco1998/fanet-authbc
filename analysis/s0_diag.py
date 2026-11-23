#!/usr/bin/env python3
"""The diagnostics after the gate S0's completeness failure (2026-11-23; disclosed, not scored;
predictions/S0.md, Outcome): for every single-sender window, the share of the sender's frames the
sniffer recorded, beside the share each Pi receiver recorded, and the sniffer's mean signal. D1a
repeats S0's positions and adds 40 B and 1 000 B frames; D1b swaps pi-A and pi-B in place. If the
sniffer's misses follow the board, they are the board's; if they stay with the place, the place's.
P1 (predictions/P1.md) uses the same rows per sniffer placement, with its registered rule.

    python analysis/s0_diag.py SESSION [SESSION ...]
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import dsss_three as w1d  # noqa: E402
import s0  # noqa: E402


def rows(session: Path) -> list[dict[str, object]]:
    frames = s0.sniffer_frames(session)
    spans = s0.window_spans(session)
    files = w1d._files(session)
    out = []
    for tag in sorted(spans, key=lambda x: int(x.split("_")[0])):
        lo, hi, senders = spans[tag]
        if len(senders) != 1:
            continue
        n = senders[0]
        sent = files[tag]["tx"][n]["sent"]
        size = files[tag]["tx"][n]["bytes"]
        got = s0.in_window(frames, spans[tag], n)
        receivers = {r: d["by_source"].get(f"10.0.0.{n}", {}).get("received_unique", 0) / sent
                     for r, d in files[tag]["rx"].items() if r != n}
        out.append({"session": session.name, "window": tag, "sender": n, "bytes": size,
                    "sent": sent, "sniffer": round(s0.completeness(got, sent), 4),
                    **{f"node{r}": round(v, 4) for r, v in sorted(receivers.items())},
                    "signal_dbm": round(st.mean(f.signal_dbm for f in got
                                                if f.signal_dbm is not None), 2)})
    return out


PLACEMENT_MIN = 0.99          # P1's registered rule: every sender at or above, or no re-gate there


def bad_checksum_frames(session: Path) -> int:
    """Frames flagged with a bad FCS anywhere in the capture (the driver as built drops them)."""
    return sum(f.bad_fcs for f in s0.sniffer_frames(session))


def placement_verdict(session_rows: list[dict[str, object]]) -> bool:
    """P1: a placement qualifies for a re-gate only if every sender's share is >= 0.99."""
    return all(float(str(r["sniffer"])) >= PLACEMENT_MIN for r in session_rows)


def main() -> None:
    for arg in sys.argv[1:]:
        found = rows(Path(arg))
        for r in found:
            print(" | ".join(f"{k} {v}" for k, v in r.items()))
        print(f"{Path(arg).name}: bad-checksum frames {bad_checksum_frames(Path(arg))}; "
              f"every sender >= {PLACEMENT_MIN}: {placement_verdict(found)}")


if __name__ == "__main__":
    main()
