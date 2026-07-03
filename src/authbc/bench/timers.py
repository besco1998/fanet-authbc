"""Microbenchmark timing harness (docs/06 §3, docs/02 §8).

Rules enforced: ``time.perf_counter_ns`` (monotonic — survives host sleep for the *clock*,
though suspended runs are still discarded elsewhere); ``gc.disable()`` around the timed
region; ≥1000 warmup iterations; a checksum accumulated over outputs to defeat dead-code
elimination; and enough work that total ≥ 200 ms OR ≥10 000 ops (whichever larger). Per-op
samples are batched (``batch`` calls per timing bracket) so ``perf_counter_ns`` overhead does
not inflate fast ops; the batch-mean is one sample and many samples feed the bootstrap CI.
"""

from __future__ import annotations

import gc
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Any

MIN_OPS = 10_000
MIN_TOTAL_NS = 200_000_000  # 200 ms


@dataclass(frozen=True)
class BenchResult:
    """Per-op timing samples (ns) plus provenance for the run."""

    name: str
    samples_ns: list[float]  # one entry per batch = mean ns/op over that batch
    n_ops: int  # total operations actually timed (reps * batch)
    batch: int
    warmup: int
    checksum: int  # accumulated over outputs — must be used, guards against DCE


def _default_checksum(value: Any) -> int:
    if isinstance(value, (bytes, bytearray)):
        return len(value) ^ (value[0] if value else 0)
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    return hash(value) & 0xFFFFFFFF


def time_op(
    fn: Callable[[], Any],
    *,
    warmup: int = 1000,
    reps: int = 200,
    batch: int = 50,
    checksum: Callable[[Any], int] | None = None,
    min_ops: int = MIN_OPS,
    min_total_ns: int = MIN_TOTAL_NS,
) -> BenchResult:
    """Time ``fn()`` and return per-op samples (ns). ``reps`` batches of ``batch`` calls each.

    Auto-grows ``reps`` until both floors (``min_ops`` ops and ``min_total_ns`` wall time) are
    met, so callers can pass conservative defaults and still satisfy docs/06 §3. The floors are
    overridable (the harness unit test lowers them to stay fast).
    """
    if warmup < 1000:
        raise ValueError("warmup must be >= 1000 (docs/06 §3)")
    if batch < 1 or reps < 1:
        raise ValueError("batch and reps must be >= 1")
    csum_fn = checksum or _default_checksum

    for _ in range(warmup):  # warmup (not timed)
        fn()

    samples: list[float] = []
    acc = 0
    total_ns = 0
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        rep = 0
        while rep < reps or len(samples) * batch < min_ops or total_ns < min_total_ns:
            t0 = perf_counter_ns()
            for _ in range(batch):
                out = fn()
            t1 = perf_counter_ns()
            dt = t1 - t0
            total_ns += dt
            samples.append(dt / batch)
            # Rolling combine (NOT xor): xor of identical outputs cancels to 0 over an even
            # number of batches, which would silently defeat the dead-code guard. This mixes
            # the output in an order-dependent, non-cancelling way.
            acc = (acc * 1_000_003 + csum_fn(out)) & 0xFFFF_FFFF_FFFF_FFFF
            rep += 1
            if rep > 10_000_000:  # safety valve — should never trigger
                break
    finally:
        if gc_was_enabled:
            gc.enable()

    return BenchResult(
        name=getattr(fn, "__name__", "op"),
        samples_ns=samples,
        n_ops=len(samples) * batch,
        batch=batch,
        warmup=warmup,
        checksum=acc,
    )
