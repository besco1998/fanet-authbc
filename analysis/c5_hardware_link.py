#!/usr/bin/env python3
"""C5's hardware link (docs/prompts/CAPTURE_PROMPT.md §8.4; Mohamed, 2026-11-18: "from the W3a
measured loss against frame length, not from ns-3"). A prediction for a future hardware session,
not scheduled.

For each W3a link (three receivers × three transmit powers, 802.11b 1 Mb/s through three walls,
`results/raw/w3a_w3a_2026-11-06.csv`), the loss to noise measured at three frame sizes gives the
best batch the unified model predicts:
* frame size by batch, on the IP layer as W3a measured it: the straight line through its one-record
  frame (S, 147 B) and its four-record frame (A, 173 B), ℓ(b) = 147 + 26·(b − 1)/3 B;
* the loss to noise PER(ℓ): straight lines between the three measured sizes (147, 173, 1 028 B),
  each from its counts (lost / frames). Nothing is fitted; b runs from 1 to 101, so ℓ stays inside
  the measured range;
* the collision budget ε_c(b) = 1 − (1 − ε)/(1 − PER(ℓ(b))), and the capacity, the root of
  p_c(ν) = ε_c(b) with 802.11b's constants (σ = 20 µs, DIFS = 50 µs, W = 32), T_f = 192 µs +
  8(ℓ + 36)/(1 Mb/s), at Λ = 10 records/s (U-D's rate). None where ε_c ≤ 0.

    python analysis/c5_hardware_link.py   -> results/raw/c5_hardware_bestbatch.csv
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from authbc.bench import provenance  # noqa: E402
from authbc.models import phy  # noqa: E402
from authbc.models import unified_capacity as uc  # noqa: E402

RAW = REPO / "results" / "raw"
W3A = RAW / "w3a_w3a_2026-11-06.csv"
OUT = RAW / "c5_hardware_bestbatch.csv"
EPS, LAMBDA = 0.05, 10.0
SIZE_BYTES = {"S": 147, "A": 173, "L": 1028}          # on the IP layer (w3a_loss.FRAME_BYTES)
RECEIVERS = {"2": "pi-B", "3": "Pi 3", "4": "TP-Link"}
B_MAX = 101
SWEEP = (1, 2, 4, 8, 16, 32, 64)


def frame_bytes(b: int) -> float:
    return SIZE_BYTES["S"] + (SIZE_BYTES["A"] - SIZE_BYTES["S"]) * (b - 1) / 3


def interpolate(points: dict[int, float], x: float) -> float:
    """Straight lines between measured (size, loss) points; x must lie inside them."""
    xs = sorted(points)
    if not xs[0] <= x <= xs[-1]:
        raise ValueError(f"{x} B lies outside the measured sizes {xs}")
    for lo, hi in zip(xs, xs[1:], strict=False):
        if x <= hi:
            return points[lo] + (points[hi] - points[lo]) * (x - lo) / (hi - lo)
    return points[xs[-1]]


def capacity(b: int, per: float) -> float | None:
    e = 1.0 - (1.0 - EPS) / (1.0 - per)
    if e <= 0:
        return None
    tf = phy.DSSS_1M.plcp_s + 8 * (frame_bytes(b) + 36) / phy.DSSS_1M.rate_bps
    return uc.n_root(LAMBDA / b, tf, e, uc.A80211B)


def links() -> dict[tuple[str, str], dict[int, float]]:
    """{(receiver, mBm): {size: loss}} from W3a's per-trace counts."""
    with W3A.open() as fh:
        rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                if r["what"] == "trace"]
    out: dict[tuple[str, str], dict[int, float]] = {}
    for r in rows:
        out.setdefault((r["receiver"], r["mbm"]), {})[SIZE_BYTES[r["size"]]] = (
            int(r["lost"]) / int(r["frames"]))
    return out


def ranges(bs: list[int]) -> str:
    """Contiguous runs, e.g. [1, 2, 3, 7, 8] -> "1-3, 7-8"."""
    out, start = [], None
    for i, b in enumerate(bs):
        if start is None:
            start = b
        if i + 1 == len(bs) or bs[i + 1] != b + 1:
            out.append(f"{start}-{b}" if start != b else f"{b}")
            start = None
    return ", ".join(out)


def main() -> None:
    rows: list[dict[str, object]] = []
    for (rx, mbm), per in sorted(links().items(), key=lambda kv: (kv[0][0], -int(kv[0][1]))):
        caps = {b: capacity(b, interpolate(per, frame_bytes(b))) for b in range(1, B_MAX + 1)}
        ok = {b: c for b, c in caps.items() if c is not None}
        best = max(ok, key=lambda b: ok[b]) if ok else None
        sweep_ok = [b for b in SWEEP if caps.get(b) is not None]
        best_sweep = max(sweep_ok, key=lambda b: caps[b] or 0) if sweep_ok else None
        rows.append({"receiver": RECEIVERS[rx], "tx_dbm": int(mbm) / 100,
                     "loss_147B": round(per[147], 5), "loss_173B": round(per[173], 5),
                     "loss_1028B": round(per[1028], 5),
                     "best_batch": ("none: the one-record frame alone misses 95 %" if best is None
                                    else f">= {B_MAX} (the measured range's edge, still rising)"
                                    if best == B_MAX else best),
                     "capacity_at_best": round(ok[best], 2) if best else "",
                     "best_in_sweep": best_sweep if best_sweep else "",
                     "capacity_b1": round(caps[1], 2) if caps[1] else "",
                     "capacity_b4": round(caps[4], 2) if caps[4] else "",
                     "feasible_b": ranges(sorted(ok))})
    buf = io.StringIO()
    for k, v in {**provenance.env_block(), "run": "c5_hardware_bestbatch",
                 "config_hash": provenance.config_hash({"eps": EPS, "lambda": LAMBDA,
                                                        "sizes": SIZE_BYTES,
                                                        "b_max": B_MAX})}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
