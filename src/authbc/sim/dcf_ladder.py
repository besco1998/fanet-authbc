"""Slot-exact DCF backoff reference simulator — the third implementation (docs/02 §6).

Bianchi's model and NS-3 disagree by 14× on 802.11 BROADCAST saturation throughput while agreeing
to ±5 % on unicast (docs/audits/p7.md). This module isolates the single assumption responsible, by
simulating the backoff *slot process* alone: no PHY, no channel, no packets — just counters. It is
therefore independent of both NS-3 (which it must reproduce) and of `models.bianchi` (whose
assumption it tests).

The process, exactly as IEEE 802.11-2020 §10.3.4.3 specifies it and as the NS-3 traces measure it.
After a busy period ends, a station transmits at ``DIFS + index·slot`` where *index* is

  * a **fresh** draw from {0 … W−1} if the station transmitted in that busy period, or
  * its **residual** counter, which is necessarily ≥ 1 for a station that deferred — a counter of 0
    would already have fired.

So a station that has just transmitted, and only such a station, can hold index 0 and take the
medium one slot ahead of the entire field. `head_start=False` removes exactly that asymmetry (the
fresh draw becomes 1 + U{0…W−1}) and nothing else, which is the assumption Bianchi's virtual-slot
abstraction makes when it decrements every station once per busy period.

With broadcast there is no ACK, hence no retry and no CW doubling, so W is *frozen* — which is why
the asymmetry dominates here and is negligible for unicast, where colliding stations back off into
an exponentially wider window.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LadderResult:
    """Outcome of one slot-process run."""

    n: int
    busy_periods: int
    idle_slots: int
    transmissions: int
    successes: int
    multiplicity_hist: dict[int, int] = field(compare=False)
    elapsed_s: float = 0.0
    throughput_bps: float = 0.0
    successes_after_collision: int = 0
    collisions_followed: int = 0
    successes_after_success: int = 0
    successes_followed: int = 0

    @property
    def p_success(self) -> float:
        """P(exactly one transmitter | busy) — Bianchi's p_s."""
        return self.successes / self.busy_periods if self.busy_periods else 0.0

    @property
    def p_success_after_collision(self) -> float:
        """P(success | the previous busy period collided) — the head-start channel.

        Under Bianchi's independence assumption this equals `p_success`; under the head start it
        is far larger, because a collision leaves several stations redrawing into the one slot
        that every deferring station is barred from.
        """
        return (self.successes_after_collision / self.collisions_followed
                if self.collisions_followed else 0.0)

    @property
    def p_success_after_success(self) -> float:
        """P(success | the previous busy period succeeded) — only one station redraws."""
        return (self.successes_after_success / self.successes_followed
                if self.successes_followed else 0.0)

    @property
    def idle_slots_per_busy_period(self) -> float:
        """Backoff slots elapsed between consecutive busy periods.

        Bianchi's virtual-slot abstraction predicts (1−p_tr)/p_tr ≈ 0.002 at N=50; the real slot
        process gives ≈0.74, because a busy period is followed by DIFS and, unless a station that
        just transmitted redrew 0, at least one countdown slot.
        """
        return self.idle_slots / self.busy_periods if self.busy_periods else 0.0

    @property
    def mean_multiplicity(self) -> float:
        return self.transmissions / self.busy_periods if self.busy_periods else 0.0

    @property
    def tau(self) -> float:
        """Per-station transmissions per virtual slot (busy periods + idle slots).

        NOT directly comparable to Bianchi's τ = 2/(W+1): the model and the real slot process
        disagree about how many idle slots there are (see `idle_slots_per_busy_period`), so they
        divide by different denominators. `mean_multiplicity`/n is the comparable quantity when
        the medium is nearly always busy.
        """
        slots = self.busy_periods + self.idle_slots
        return self.transmissions / (self.n * slots) if slots else 0.0


def run(
    n: int,
    *,
    w: int = 16,
    busy_periods: int = 200_000,
    head_start: bool = True,
    t_busy_s: float = 0.0,
    slot_s: float = 9e-6,
    payload_bytes: float = 0.0,
    seed: int = 1,
    initial: Sequence[int] | None = None,
) -> LadderResult:
    """Simulate *busy_periods* virtual slots of the saturated no-ACK backoff process.

    Each round: the stations holding the minimum index transmit together (multiplicity ≥ 2 is a
    collision); the intervening ``min`` idle slots elapse for everybody; the transmitters redraw.

    *t_busy_s* is the channel time of one busy period (frame airtime + DIFS); with *payload_bytes*
    it turns the slot statistics into a throughput directly comparable to NS-3 and to
    `models.bianchi`. Leave both at 0 for a pure slot-statistics run.

    *initial* overrides the starting backoff counters; it exists so the transient can be probed
    from a deliberately pathological state (e.g. all-zero = perfectly synchronised stations).
    """
    if n < 2:
        raise ValueError(f"n must be ≥ 2 stations, got {n}")
    if w < 2:
        raise ValueError(f"w (CW_min size) must be ≥ 2, got {w}")
    if busy_periods < 1:
        raise ValueError(f"busy_periods must be ≥ 1, got {busy_periods}")

    rng = random.Random(seed)
    offset = 0 if head_start else 1
    # Default start is independent uniform draws; any transient is amortised over the run length
    # (`test_result_is_insensitive_to_the_initial_state` checks this from the all-zero state).
    if initial is None:
        index = [rng.randrange(w) for _ in range(n)]
    elif len(initial) != n:
        raise ValueError(f"initial has {len(initial)} counters, expected {n}")
    else:
        index = list(initial)

    hist: dict[int, int] = {}
    idle_slots = 0
    transmissions = 0
    successes = 0
    succ_after_coll = colls_followed = succ_after_succ = succs_followed = 0
    prev_k = 0

    for _ in range(busy_periods):
        m = min(index)
        idle_slots += m
        winners = [i for i, c in enumerate(index) if c == m]
        k = len(winners)
        transmissions += k
        successes += k == 1
        hist[k] = hist.get(k, 0) + 1
        if prev_k > 1:
            colls_followed += 1
            succ_after_coll += k == 1
        elif prev_k == 1:
            succs_followed += 1
            succ_after_succ += k == 1
        prev_k = k
        if m:
            index = [c - m for c in index]
        for i in winners:
            index[i] = rng.randrange(w) + offset

    elapsed = busy_periods * t_busy_s + idle_slots * slot_s
    throughput = (successes * 8.0 * payload_bytes / elapsed) if elapsed > 0 else 0.0
    return LadderResult(
        n=n,
        busy_periods=busy_periods,
        idle_slots=idle_slots,
        transmissions=transmissions,
        successes=successes,
        multiplicity_hist=dict(sorted(hist.items())),
        elapsed_s=elapsed,
        throughput_bps=throughput,
        successes_after_collision=succ_after_coll,
        collisions_followed=colls_followed,
        successes_after_success=succ_after_succ,
        successes_followed=succs_followed,
    )
