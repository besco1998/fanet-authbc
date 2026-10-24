#!/usr/bin/env python3
"""Revision A5 — does a time window catch frames an adversary holds back? (predictions/A5.md)

The codec in the loop: real lean frames (b = 4, 50 records/s, a keyframe in every frame) go to
`TimedReceiver` (`authbc.placement.freshness_rule`) or, for comparison, to `LeanReceiver` alone,
which refuses replays by sequence number only.

* **Clocks.** The receiver compares its own clock with the frame's newest timestamp. Each
  timestamp and each local reading carries an independent Gaussian error of σ ∈ {1, 10, 50} ms
  (so their difference has σ√2). In a GNSS outage of t seconds both clocks drift by up to
  20 ppm; the worst case is in opposite directions: 2·20e-6·t apart.
* **Honest timing.** A frame leaves when its last record is taken and is verified
  T = T_ch + t_v = 3.7502 ms later (worst channel delay and one verification, as Eq. 2).
* **The adversary** is a delay line: from a frame chosen uniformly in the first half of the
  stream to the end, every frame arrives δ late, δ ∈ {10, 50, 100, 250, 1000, 10 000} ms. A
  single frame delayed alone is already refused by sequence number once a later one has
  arrived; a delay line is the attack sequence numbers cannot see.
* **Policies.** `seq-only` (the receiver as published); `fixed150` (Δ_acc = 150 ms, the
  plan's number); `formula` (Δ_acc = b/Λ + T_ch + t_v + 2σ + g, g = 10 ms).

    python analysis/replay_window.py      # results/raw/replay_window.csv
"""
from __future__ import annotations

import csv
import io
import sys
from functools import cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "analysis"))

import design_map  # noqa: E402

from authbc.bench import leanframes, provenance  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.placement.freshness_rule import TimedReceiver, TimeWindow, accepted  # noqa: E402
from authbc.placement.session_v2 import LeanReceiver, LeanSender, Receipt  # noqa: E402

OUT = REPO / "results" / "raw" / "replay_window.csv"
LAMBDA, BATCH = 50.0, 4
SIGMAS_MS: tuple[float, ...] = (1.0, 10.0, 50.0)
DELAYS_MS: tuple[float, ...] = (10.0, 50.0, 100.0, 250.0, 1_000.0, 10_000.0)
OUTAGES_MIN: tuple[float, ...] = tuple(float(m) for m in range(0, 241, 15))
FIXED_WINDOWS_MS: tuple[float, ...] = (150.0, 250.0)
GUARD_MS = 10.0
DRIFT_PPM = 20.0
SEEDS: tuple[int, ...] = tuple(range(1, 31))
FRAMES_PER_SEED = 2_400
BASE_SEED = 5555


@cache
def frames_of(seed: int) -> tuple[list[bytes], list[int]]:
    """A seed's frames and each frame's newest timestamp (built once per worker process)."""
    sk, _ = Ed25519Scheme().keygen(seed=bytes(range(32)))
    recs = leanframes.chained_records(seed, FRAMES_PER_SEED * BATCH,
                                      step_ms=design_map.step_ms(LAMBDA))
    sender = LeanSender(sk)
    frames = [sender.frame(recs[i:i + BATCH]) for i in range(0, len(recs), BATCH)]
    return frames, [recs[i + BATCH - 1].ts for i in range(0, len(recs), BATCH)]


def window(sigma: float, guard: float) -> TimeWindow:
    t_ch, t_v = design_map.budget()
    return TimeWindow(batch=BATCH, lam=LAMBDA, t_ch_ms=t_ch, t_v_ms=t_v, sigma_clk_ms=sigma,
                      guard_ms=guard, drift_ppm=DRIFT_PPM)


def policy_window(policy: str, sigma: float) -> TimeWindow | None:
    """The window of a policy; None for sequence numbers alone."""
    if policy == "seq-only":
        return None
    if policy.startswith("fixed"):
        w = window(sigma, 0.0)
        return window(sigma, float(policy.removeprefix("fixed")) - w.accept_ms)
    return window(sigma, GUARD_MS)


def run_stream(policy: str, sigma: float, delay: float, drift_ms: float, seed: int,
               known_outage_s: float) -> tuple[int, int, int, int]:
    """(honest frames, honest refused, delayed frames, delayed refused) for one seed.

    `drift_ms` is the true clock separation; `known_outage_s` is the outage the receiver knows
    of and widens its window for (0 for a fixed window).
    """
    frames, newest = frames_of(seed)
    _, pk = Ed25519Scheme().keygen(seed=bytes(range(32)))
    t_after = sum(design_map.budget())
    rng = np.random.default_rng([BASE_SEED, int(sigma * 10), int(delay), int(drift_ms * 10),
                                 seed])
    onset = int(rng.integers(0, len(frames) // 2)) if delay > 0 else len(frames)
    err = rng.normal(0.0, sigma, size=(len(frames), 2))      # stamping and local reading
    inner = LeanReceiver({leanframes.CONVENTION_SRC: pk})
    w = policy_window(policy, sigma)
    rx = None if w is None else TimedReceiver(inner, w, max_window_ms=1e12)
    honest = honest_refused = late = late_refused = 0
    for k, (data, ts) in enumerate(zip(frames, newest, strict=True)):
        held = delay if k >= onset else 0.0
        t_local = ts + t_after + held + drift_ms + err[k, 1] - err[k, 0]
        if rx is None:
            ok = inner.receive(data).receipt is Receipt.ACCEPTED
        else:
            ok = accepted(rx.receive(data, t_local, outage_s=known_outage_s))
        if held:
            late += 1
            late_refused += not ok
        else:
            honest += 1
            honest_refused += not ok
    return honest, honest_refused, late, late_refused


def _job(job: tuple[str, str, float, float, float, float]) -> dict:
    study, policy, sigma, delay, outage_min, known_min = job
    drift_ms = 2.0 * DRIFT_PPM * 1e-6 * outage_min * 60.0 * 1000.0      # worst case, apart
    totals = np.zeros(4, dtype=int)
    for seed in SEEDS:
        totals += run_stream(policy, sigma, delay, drift_ms, seed, known_min * 60.0)
    w = policy_window(policy, sigma)
    return {"study": study, "policy": policy, "sigma_ms": sigma, "delay_ms": delay,
            "outage_min": outage_min, "clock_apart_ms": round(drift_ms, 3),
            "window_ms": "" if w is None else round(w.widened(known_min * 60.0), 3),
            "honest_frames": int(totals[0]), "honest_refused": int(totals[1]),
            "false_rejection": round(totals[1] / totals[0], 7) if totals[0] else "",
            "delayed_frames": int(totals[2]), "delayed_refused": int(totals[3]),
            "detection": round(totals[3] / totals[2], 6) if totals[2] else ""}


def jobs() -> list[tuple[str, str, float, float, float, float]]:
    out: list[tuple[str, str, float, float, float, float]] = []
    for policy in ("seq-only", "fixed150", "formula"):
        for sigma in SIGMAS_MS:
            out.append(("honest", policy, sigma, 0.0, 0.0, 0.0))
            out += [("delay", policy, sigma, d, 0.0, 0.0) for d in DELAYS_MS]
    for fixed in FIXED_WINDOWS_MS:                    # a window that does not widen
        out += [("outage", f"fixed{fixed:g}", 10.0, 0.0, m, 0.0) for m in OUTAGES_MIN]
    out += [("outage", "formula", 10.0, 0.0, m, m) for m in OUTAGES_MIN]   # one that does
    return out


def main() -> None:
    with Pool(3) as pool:
        rows = pool.map(_job, jobs())
    buf = io.StringIO()
    config = {"sigmas": SIGMAS_MS, "delays": DELAYS_MS, "outages": OUTAGES_MIN,
              "fixed": FIXED_WINDOWS_MS, "guard": GUARD_MS, "drift": DRIFT_PPM, "seeds": SEEDS,
              "frames": FRAMES_PER_SEED, "base": BASE_SEED}
    for k, v in {**provenance.env_block(), "run": "replay_window",
                 "config_hash": provenance.config_hash(config)}.items():
        buf.write(f"# {k}={v}\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    OUT.write_text(buf.getvalue())
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
