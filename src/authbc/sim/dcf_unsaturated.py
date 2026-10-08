"""Unsaturated broadcast DCF in one collision domain: an event simulator of the access rule alone.

Implements docs/02 §6g. It exists to answer one question — *why* does loss reach 5 % where the
direct ns-3 search finds it (docs/NMAX_DIRECT_EXPECTATIONS.md) — with a second implementation
that shares nothing with ns-3: no PHY, no propagation, no packets; only arrival times, the
carrier-sense rule and backoff counters. Everything in it is a constant of IEEE 802.11a or of
the scenario; nothing is fitted.

The rule, as the standard states it and as the scenario configures it (broadcast: no
acknowledgement, no retransmission, the contention window never doubles):

* Each of N stations sends one frame per period, at an instant drawn uniformly within the period.
* A frame that arrives when the medium has been idle for DIFS is sent at once.
* Otherwise the station draws a counter uniformly from {0 … W−1}. Counters fall by one per idle
  slot once the medium has been idle for DIFS, freeze while it is busy, and the station sends
  when its counter reaches zero.
* A station cannot sense a transmission during its first ``detect_s`` (the preamble-detection
  time), so one that decides to send within that window sends as well.
* After sending, a station draws a post-transmission counter the same way; a frame that arrives
  before it has run out waits for it.
* Frames whose transmissions overlap are lost to every receiver (equal power, no capture).

Two things can therefore destroy a frame, and the simulator counts them separately: a **tie** —
two counters reaching zero in the same slot — and the **detection window**.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

SLOT_S: float = 9e-6                # IEEE 802.11a
DIFS_S: float = 34e-6               # SIFS + 2 slots
W0: int = 16                        # CWmin + 1
DETECT_S: float = 4e-6              # preamble detection (ns-3's default; half of line's 8 µs)


@dataclass(frozen=True)
class Result:
    frames: int                     # frames sent (after the warm-up)
    lost: int                       # frames whose transmission overlapped another
    lost_to_ties: int               # … because two counters reached zero in the same slot
    deferred: int                   # frames that had to draw a counter

    @property
    def delivered_frac(self) -> float:
        return 1.0 - self.lost / self.frames

    @property
    def deferred_frac(self) -> float:
        return self.deferred / self.frames


def run(n_nodes: int, frames_per_s: float, airtime_s: float, *, sim_time_s: float = 20.0,
        seed: int = 1, w0: int = W0, slot_s: float = SLOT_S, difs_s: float = DIFS_S,
        detect_s: float = DETECT_S, redraw_phase: bool = True,
        warmup_s: float = 1.0) -> Result:
    """One run. `airtime_s` is the frame's time on air (without DIFS)."""
    if n_nodes < 2 or frames_per_s <= 0 or airtime_s <= 0 or w0 < 1:
        raise ValueError("need n_nodes ≥ 2, frames_per_s > 0, airtime_s > 0, w0 ≥ 1")
    rng = random.Random(seed)
    period = 1.0 / frames_per_s
    arrivals: list[tuple[float, int]] = []
    for node in range(n_nodes):
        phase = rng.random()
        for k in range(int(sim_time_s / period)):
            arrivals.append(((k + (rng.random() if redraw_phase else phase)) * period, node))
    arrivals.sort()

    counter: dict[int, int] = {}          # node -> slots left, for every node that is counting
    queued: dict[int, int] = {}           # node -> frames waiting behind its counter
    idle_from = 0.0                       # when the medium last became idle
    frames = lost = ties = deferred = 0
    i = 0
    inf = float("inf")
    while i < len(arrivals) or queued:
        ready = idle_from + difs_s        # counters run from here, one per slot
        t_arrival = arrivals[i][0] if i < len(arrivals) else inf
        if t_arrival < ready:             # medium busy, or idle for less than DIFS: defer
            node = arrivals[i][1]
            i += 1
            if node not in counter:       # else the frame waits for the counter already running
                counter[node] = rng.randrange(w0)
            queued[node] = queued.get(node, 0) + 1
            deferred += t_arrival >= warmup_s
            continue
        lowest = min(counter.values(), default=None)
        if lowest is not None and ready + lowest * slot_s <= t_arrival:
            # the lowest counters reach zero first
            start, elapsed = ready + lowest * slot_s, lowest
            zero = [node for node, c in counter.items() if c == lowest]
        elif t_arrival < inf:             # an arrival finds the medium idle for DIFS or more
            start, zero = t_arrival, []
            elapsed = int((start - ready) / slot_s + 1e-9)
        else:
            break
        for node in counter:              # whole idle slots that have gone by
            counter[node] -= elapsed
        idle_from = start - difs_s        # time has moved on with the medium still idle
        senders: list[tuple[int, float]] = []
        for node in zero:
            del counter[node]
            if queued.get(node):          # a counter with no frame behind it was post-backoff
                senders.append((node, start))
        tied = len(senders)
        if not senders and zero:
            continue
        # the arrival that found the medium idle, then whoever decides to send inside the
        # detection window of the first sender: none of them has heard it yet
        first = not zero
        while i < len(arrivals) and (first or arrivals[i][0] < start + detect_s):
            first = False
            t, node = arrivals[i]
            i += 1
            if node in counter:           # post-transmission counter still running: it waits
                queued[node] = queued.get(node, 0) + 1
                deferred += t >= warmup_s
            else:
                queued[node] = queued.get(node, 0) + 1
                senders.append((node, t))
        if not senders:
            continue
        # a counter that runs out inside the window: its owner has not heard the sender yet
        to_boundary = ready + (elapsed + 1) * slot_s - start       # in (0, slot]
        if to_boundary < detect_s:
            for node, c in list(counter.items()):
                if c == 1 and queued.get(node):
                    del counter[node]
                    senders.append((node, start + to_boundary))
        if start >= warmup_s:
            frames += len(senders)
            if len(senders) > 1:
                lost += len(senders)
                ties += tied if tied > 1 else 0
        idle_from = max(t for _, t in senders) + airtime_s
        for node, _ in senders:
            queued[node] -= 1
            if not queued[node]:
                del queued[node]
            counter[node] = rng.randrange(w0)        # post-transmission backoff
    return Result(frames, lost, ties, deferred)


def mean_delivered(n_nodes: int, frames_per_s: float, airtime_s: float, *, seeds: int = 30,
                   sim_time_s: float = 20.0, w0: int = W0) -> float:
    """Mean delivered fraction over `seeds` runs numbered from 1."""
    return sum(run(n_nodes, frames_per_s, airtime_s, seed=s, sim_time_s=sim_time_s,
                   w0=w0).delivered_frac for s in range(1, seeds + 1)) / seeds
