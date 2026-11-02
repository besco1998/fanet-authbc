"""The broadcast access-rule simulator of docs/02 §6g, with the own-queue rule as a parameter.

Open item G27, registered in predictions/G27.md. On two Raspberry Pi 4 radios one saturated sender
spaces its frames closer together than the standard's rule (F74, F75), two saturated senders lose
what the rule says (F76), and below saturation the loss rises more slowly with load than the
model (F73). Which rule for a radio's own queued frames, if any, gives all three is what G27 asks.

`dcf_unsaturated` is frozen: its registration checks it byte for byte. Its event loop is copied
here, and the rule is added as an `OwnQueueRule`. With `STANDARD` this module makes the same random
draws in the same order and returns the same counts as `dcf_unsaturated.run`
(tests/test_dcf_own_queue.py), so every difference a rule makes is the rule's.

The rules, each from predictions/G27.md:

* `w_post`, `w_defer` — the window a counter is drawn from after the station's own frame, and when
  a frame finds the medium busy (Bianchi et al., INFOCOM 2007: windows of 7 and 15 where 31 is
  required).
* `q_zero` — the share of post-transmission counters that are 0 (ibid., the Prism II card).
* `q_burst` — the share of queued frames sent SIFS after the station's own frame, without
  contending (the vendor's frame-burst mode; the standard's TXOP).
* `redraw_on_defer` — a post-transmission counter interrupted by another station's frame is
  redrawn from `w_defer` (ibid. §IV-B: cards that misbehave alone behave properly after a busy
  period).
* `slot_s` — the backoff slot (no source; a timing family, disclosed as such).

Kept from the frozen model as they are, examined and small:

* a counter that does not reach zero inside the detection window is not decremented for the slot
  boundaries that pass inside it;
* an arrival during an idle period moves the slot grid to the arrival, so a running counter loses
  the part of a slot that had gone by: +0.2–0.6 µs on one saturated sender's gap at 500–2000
  arrivals/s, which is what that rule predicts (F114).

**Not kept: a defect of the frozen model (F114).** There, a frame that reaches a station inside the
detection window of that station's own frame made the station a second sender of the same group:
a station colliding with itself, two frames counted and both lost. Here the frame waits in the
station's queue. Where the frozen model forms no such group the two agree bit for bit; it forms
them in 0–1.2 % of the lost frames at the loads of F73 and 2.1 % with two saturated stations.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from authbc.sim.dcf_unsaturated import DETECT_S, DIFS_S, SLOT_S, W0

SIFS_S: float = 16e-6               # IEEE 802.11a


@dataclass(frozen=True)
class OwnQueueRule:
    name: str = "R0"
    w_post: int = W0
    w_defer: int = W0
    q_zero: float = 0.0
    q_burst: float = 0.0
    redraw_on_defer: bool = False
    slot_s: float = SLOT_S

    def __post_init__(self) -> None:
        if self.w_post < 1 or self.w_defer < 1:
            raise ValueError("windows must be at least 1")
        if not (0.0 <= self.q_zero <= 1.0 and 0.0 <= self.q_burst < 1.0):
            raise ValueError("need 0 ≤ q_zero ≤ 1 and 0 ≤ q_burst < 1")
        if self.slot_s <= 0:
            raise ValueError("slot_s must be positive")


STANDARD = OwnQueueRule()


@dataclass(frozen=True)
class Result:
    frames: int                     # frames sent (after the warm-up)
    lost: int                       # frames whose transmission overlapped another
    lost_to_ties: int               # … because two counters reached zero in the same slot
    deferred: int                   # frames that found the medium busy
    burst_frames: int = 0           # frames sent SIFS after the station's own frame
    frames_by_node: tuple[int, ...] = field(default_factory=tuple)
    first_start_s: float = 0.0      # first and last counted start, for spacings and rates
    last_start_s: float = 0.0

    @property
    def delivered_frac(self) -> float:
        return 1.0 - self.lost / self.frames

    @property
    def loss(self) -> float:
        return self.lost / self.frames


def run(n_nodes: int, frames_per_s: float, airtime_s: float, *, rule: OwnQueueRule = STANDARD,
        sim_time_s: float = 20.0, seed: int = 1, difs_s: float = DIFS_S,
        detect_s: float = DETECT_S, sifs_s: float = SIFS_S, redraw_phase: bool = True,
        warmup_s: float = 1.0, count_until_s: float | None = None,
        on_send: Callable[[list[int]], None] | None = None) -> Result:
    """One run. `airtime_s` is the frame's time on air (without DIFS).

    `count_until_s`, if given, counts only frames that start before it and stops there: a
    saturated run then measures the stations while both queues are full, not while they drain.
    """
    if n_nodes < 1 or frames_per_s <= 0 or airtime_s <= 0:
        raise ValueError("need n_nodes ≥ 1, frames_per_s > 0, airtime_s > 0")
    slot_s = rule.slot_s
    rng = random.Random(seed)
    period = 1.0 / frames_per_s
    arrivals: list[tuple[float, int]] = []
    for node in range(n_nodes):
        phase = rng.random()
        for k in range(int(sim_time_s / period)):
            arrivals.append(((k + (rng.random() if redraw_phase else phase)) * period, node))
    arrivals.sort()
    until = float("inf") if count_until_s is None else count_until_s

    counter: dict[int, int] = {}          # node -> slots left, for every node that is counting
    queued: dict[int, int] = {}           # node -> frames waiting behind its counter
    post: set[int] = set()                # nodes whose counter is a post-transmission draw
    by_node = [0] * n_nodes
    idle_from = 0.0                       # when the medium last became idle
    frames = lost = ties = deferred = bursts = 0
    first_start = last_start = -1.0
    i = 0
    inf = float("inf")

    def draw_post(node: int) -> None:
        if rule.q_zero and rng.random() < rule.q_zero:
            counter[node] = 0
        else:
            counter[node] = rng.randrange(rule.w_post)
        if rule.redraw_on_defer:
            post.add(node)

    def count(group: list[int], start: float, *, burst: bool) -> None:
        nonlocal frames, lost, bursts, first_start, last_start
        if not warmup_s <= start < until:
            return
        frames += len(group)
        bursts += len(group) if burst else 0
        for node in group:
            by_node[node] += 1
        if first_start < 0:
            first_start = start
        last_start = start
        if on_send is not None:
            on_send(group)
        if len(group) > 1:
            lost += len(group)

    def interrupted(senders: list[int]) -> None:
        # another station's frame stops a post-transmission counter: it is drawn again
        for node in [n for n in counter if n in post and n not in senders]:
            counter[node] = rng.randrange(rule.w_defer)
            post.discard(node)

    while i < len(arrivals) or queued:
        ready = idle_from + difs_s        # counters run from here, one per slot
        t_arrival = arrivals[i][0] if i < len(arrivals) else inf
        if t_arrival >= until and ready >= until:
            break
        if t_arrival < ready:             # medium busy, or idle for less than DIFS: defer
            node = arrivals[i][1]
            i += 1
            if node not in counter:       # else the frame waits for the counter already running
                counter[node] = rng.randrange(rule.w_defer)
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
            post.discard(node)
            if queued.get(node):          # a counter with no frame behind it was post-backoff
                senders.append((node, start))
        tied = len(senders)
        if not senders and zero:
            continue
        # the arrival that found the medium idle, then whoever decides to send inside the
        # detection window of the first sender: none of them has heard it yet
        first = not zero
        sending = {node for node, _ in senders}
        while i < len(arrivals) and (first or arrivals[i][0] < start + detect_s):
            first = False
            t, node = arrivals[i]
            i += 1
            queued[node] = queued.get(node, 0) + 1
            if node in counter or node in sending:   # it waits: for its counter, or its own frame
                deferred += t >= warmup_s
            else:
                senders.append((node, t))
                sending.add(node)
        if not senders:
            continue
        # a counter that runs out inside the window: its owner has not heard the sender yet.
        # With a slot of 9 µs and a window of 4 µs only a counter at 1 can; a shorter slot lets
        # more through.
        to_boundary = ready + (elapsed + 1) * slot_s - start       # in (0, slot]
        if to_boundary < detect_s:
            for node, c in list(counter.items()):
                if c >= 1 and to_boundary + (c - 1) * slot_s < detect_s and queued.get(node):
                    del counter[node]
                    post.discard(node)
                    senders.append((node, start + to_boundary + (c - 1) * slot_s))
        group = [node for node, _ in senders]
        count(group, start, burst=False)
        if len(group) > 1 and warmup_s <= start < until:
            ties += tied if tied > 1 else 0
        if rule.redraw_on_defer:
            interrupted(group)
        idle_from = max(t for _, t in senders) + airtime_s
        for node in group:
            queued[node] -= 1
            if not queued[node]:
                del queued[node]
            if not rule.q_burst:
                draw_post(node)               # post-transmission backoff
        while rule.q_burst and group:
            # a frame that reached the queue while its station was sending counts for the burst
            while i < len(arrivals) and arrivals[i][0] < idle_from:
                t, node = arrivals[i]
                i += 1
                queued[node] = queued.get(node, 0) + 1
                deferred += t >= warmup_s
                if node not in group and node not in counter:
                    counter[node] = rng.randrange(rule.w_defer)
            going = [node for node in group if queued.get(node) and rng.random() < rule.q_burst]
            for node in group:
                if node not in going:
                    draw_post(node)
            if not going:
                break
            start = idle_from + sifs_s    # nobody else may start: the medium is idle < DIFS
            count(going, start, burst=True)
            if rule.redraw_on_defer:
                interrupted(going)
            for node in going:
                queued[node] -= 1
                if not queued[node]:
                    del queued[node]
            idle_from = start + airtime_s
            group = going
    return Result(frames, lost, ties, deferred, bursts, tuple(by_node),
                  max(first_start, 0.0), max(last_start, 0.0))


def mean_gap_after_frame_s(rule: OwnQueueRule, airtime_s: float, *, seeds: int = 10,
                           sim_time_s: float = 20.0, offered_fps: float = 900.0) -> float:
    """One saturated sender: the mean time from the end of one frame to the start of the next."""
    gaps = []
    for s in range(1, seeds + 1):
        r = run(1, offered_fps, airtime_s, rule=rule, seed=s, sim_time_s=sim_time_s,
                count_until_s=sim_time_s)
        gaps.append((r.last_start_s - r.first_start_s) / (r.frames - 1) - airtime_s)
    return sum(gaps) / len(gaps)
