#!/usr/bin/env python3
"""Revision A2, second part — age of information at a receiver when frames are lost.

Eq. (2) of the paper bounds the PEAK age of information at a receiver that loses no frame
(the paper says so, citing Yates et al. 2021). This script measures what a lost frame does to
it, with the codec in the loop: real lean frames from `LeanSender`, an independent loss
process, and `LeanReceiver`; an update counts only if the receiver decoded, verified and
stored it. Registration: `predictions/A2.md`.

Two quantities, because the plan's "peak age for every verified record" reads two ways:

* **delay to verification** of each verified record — its verification time minus its own
  timestamp. Loss cannot move it: a record in a lost frame is never verified at all.
* **age of information** of one sender at one receiver — time since the newest verified
  record was taken. Its peak (just before an update lands) and its time average both grow
  with loss, because a lost frame stretches the interval between updates.

Timing is the paper's worst case, as in Eq. (2): a frame leaves when its last record is
taken, reaches the receiver after the worst channel delay simulated at the design's crossing,
and is verified one Ed25519 verification later (`results/raw/freshness_budget.csv`). Record
timestamps are the generator's, 20 ms apart with its ±3 ms jitter.

    python analysis/aoi_under_loss.py      # results/raw/aoi_under_loss.csv
"""
from __future__ import annotations

import csv
import io
import statistics as st
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import design_map  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.bench.stats import bootstrap_ci  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt  # noqa: E402

OUT = REPO / "results" / "raw" / "aoi_under_loss.csv"
LAMBDA = 50
D_MAX_MS = 100.0
BATCHES: tuple[int, ...] = (4, 1)           # the design, then the baseline for comparison
P_VALUES: tuple[float, ...] = (0.0, 0.01, 0.05, 0.10)
SEEDS: tuple[int, ...] = tuple(range(1, 31))
FRAMES_PER_SEED = 240                       # 7 200 frames per cell, as the loss table of E10
BASE_SEED = 5151
CI_SEED = 20261019


def percentile(xs: list[float], q: float) -> float:
    """Linear-interpolation percentile, the convention of the ns-3 delay scenario."""
    return float(np.percentile(np.asarray(xs), 100 * q))


def one_stream(batch: int, p: float, seed: int, t_after_ms: float) -> dict[str, list[float]]:
    """Ages of one sender at one receiver over FRAMES_PER_SEED frames."""
    sk, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    recs = leanframes.chained_records(seed, FRAMES_PER_SEED * batch,
                                      step_ms=design_map.step_ms(LAMBDA))
    sender = LeanSender(sk)
    frames = [sender.frame(recs[i:i + batch]) for i in range(0, len(recs), batch)]
    rng = np.random.default_rng([BASE_SEED, batch, int(round(p * 1e6)), seed])
    lost = rng.random(len(frames)) < p
    rx = LeanReceiver({leanframes.CONVENTION_SRC: pk})
    delays, peaks, area, span = [], [], 0.0, 0.0
    newest: float | None = None
    t_prev: float | None = None
    for k, (data, gone) in enumerate(zip(frames, lost, strict=True)):
        if gone:
            continue
        got = rx.receive(data)
        if got.receipt is not Receipt.ACCEPTED:
            raise RuntimeError(f"a frame on a loss-only link was {got.receipt}")
        t_verified = recs[k * batch + batch - 1].ts + t_after_ms
        delays.extend(t_verified - r.ts for r in got.records)
        if newest is not None and t_prev is not None:
            peak = t_verified - newest
            peaks.append(peak)
            low = t_prev - newest              # the age just after the previous update
            area += (peak * peak - low * low) / 2
            span += t_verified - t_prev
        newest, t_prev = float(max(r.ts for r in got.records)), t_verified
    return {"delays": delays, "peaks": peaks, "avg": [area / span]}


def cell(batch: int, p: float, t_after_ms: float) -> dict:
    per_seed = [one_stream(batch, p, s, t_after_ms) for s in SEEDS]
    peaks = [x for s in per_seed for x in s["peaks"]]
    delays = [x for s in per_seed for x in s["delays"]]
    mean_peaks = [st.mean(s["peaks"]) for s in per_seed]
    lo, hi = bootstrap_ci(mean_peaks, seed=CI_SEED, statistic=np.mean)
    over = sum(x > D_MAX_MS for x in peaks)
    period = 1000.0 * batch / LAMBDA
    return {
        "lambda_rec_per_s": LAMBDA, "batch": batch, "p": p, "d_max_ms": D_MAX_MS,
        "t_after_ms": round(t_after_ms, 4), "updates": len(peaks),
        "peak_mean_ms": round(st.mean(peaks), 3), "peak_mean_ci_lo": round(lo, 3),
        "peak_mean_ci_hi": round(hi, 3),
        "peak_p50_ms": round(percentile(peaks, 0.50), 3),
        "peak_p95_ms": round(percentile(peaks, 0.95), 3),
        "peak_p99_ms": round(percentile(peaks, 0.99), 3),
        "peak_max_ms": round(max(peaks), 3),
        "share_peak_over_dmax": round(over / len(peaks), 5),
        "avg_age_ms": round(st.mean(x for s in per_seed for x in s["avg"]), 3),
        "delay_mean_ms": round(st.mean(delays), 3),
        "delay_max_ms": round(max(delays), 3),
        "records_verified": len(delays),
        "theory_peak_mean_ms": round(period / (1 - p) + t_after_ms, 3),
        "theory_extra_ms": round(period * p / (1 - p), 3),
        # updates arrive a geometric number m of frame periods apart: E[m²]/(2E[m])
        "theory_avg_age_ms": round(t_after_ms + period * (1 + p) / (2 * (1 - p)), 3),
    }


def main() -> None:
    t_ch, t_v = design_map.budget()
    rows = [cell(b, p, t_ch + t_v) for b in BATCHES for p in P_VALUES]
    buf = io.StringIO()
    config = {"lambda": LAMBDA, "batches": BATCHES, "p": P_VALUES, "seeds": SEEDS,
              "frames": FRAMES_PER_SEED, "base_seed": BASE_SEED, "t_after_ms": t_ch + t_v}
    for k, v in {**provenance.env_block(), "run": "aoi_under_loss",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(f"b={r['batch']} p={r['p']}: peak mean {r['peak_mean_ms']} "
              f"(theory {r['theory_peak_mean_ms']}), p95 {r['peak_p95_ms']}, "
              f"p99 {r['peak_p99_ms']}, share > D_max {r['share_peak_over_dmax']}, "
              f"avg age {r['avg_age_ms']}, delay max {r['delay_max_ms']}")


if __name__ == "__main__":
    main()
