"""Unsaturated broadcast DCF in one collision domain, with ns-3.48's own access rule: an event
simulator that shares nothing with ns-3 but the rule, read from its source (the audit of
2026-11-17, item 1; docs/audits/2026-11-17_ns3_implementation_audit.md).

The rule, as `ns3/ns-3.48/src/wifi/model/channel-access-manager.cc` implements it for a non-QoS
station (the scenario's ad-hoc MAC):

* `NeedBackoffUponAccess` (lines 548–567): a frame queued to an empty queue with no backoff left,
  while `IsBusy()` is false, gets zero slots and a backoff start of *its own arrival + DIFS*. It is
  sent then, if the medium stays idle. `IsBusy()` (499–509) does not count the DIFS after a busy
  period as busy, so an arrival there is treated the same way.
* If a transmission starts before that instant, the frame keeps zero slots and its backoff start;
  `GetBackoffStartFor` (789–798) then takes max(that start, busy end + DIFS): it is sent DIFS after
  the busy period.
* A frame queued while the medium is busy draws a uniform backoff in 0 … CW. Slots run from
  max(own backoff start, busy end + DIFS) and are counted in whole slots when the medium next
  turns busy (`UpdateBackoff`, 890–923), for every station, whether or not it has a frame.
* After each own transmission the station draws a new backoff (post-transmission backoff); a frame
  that arrives before it has run out waits for it.
* A start cannot be sensed for δ (the preamble-detection period): a station whose transmission
  falls within δ of another's start sends as well.
* No EIFS. EIFS follows a reception that *ends in error* (`NotifyRxEndErrorNow`, 1095–1103). With
  equal power every collision falls within δ of its first start (a later start is sensed), inside
  the first frame's preamble-detection period, where detection fails for both and no reception
  starts — so none ends in error. The ns-3 traces of the audit (item 3) check this.

Frames whose transmissions overlap are lost to every receiver (equal power, no capture). Each of N
stations sends one frame per period at a uniform instant within it (the designated source).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    frames: int
    lost: int

    @property
    def delivered_frac(self) -> float:
        return 1.0 - self.lost / self.frames if self.frames else 1.0


@dataclass
class _Station:
    queue: int = 0
    slots: int = 0
    bstart: float = -1.0            # the Txop's own backoff start


def run(n_nodes: int, frames_per_s: float, airtime_s: float, *, slot_s: float, difs_s: float,
        w: int, delta_s: float = 4e-6, sim_time_s: float = 20.0, seed: int = 1,
        arrivals: list[tuple[float, int]] | None = None,
        trace: list[tuple[float, tuple[int, ...], float]] | None = None) -> Result:
    """One run. `arrivals` replaces the periodic source by (time, station) pairs (for tests);
    `trace`, if given, receives (first start, stations, last start − first start) for every
    group of frames sent together.
    """
    if n_nodes < 2 or frames_per_s <= 0 or airtime_s <= 0 or w < 1:
        raise ValueError("need n_nodes ≥ 2, frames_per_s > 0, airtime_s > 0, w ≥ 1")
    rng = random.Random(seed)
    period = 1.0 / frames_per_s
    if arrivals is None:
        arrivals = [((k + rng.random()) * period, i) for i in range(n_nodes)
                    for k in range(int(sim_time_s / period))]
    arrivals = sorted(arrivals)
    st = [_Station() for _ in range(n_nodes)]
    idle_from = -1.0                # end of the last busy period
    frames = lost = 0
    ia, inf = 0, float("inf")

    def tx_time(s: _Station) -> float:
        return max(s.bstart, idle_from + difs_s) + s.slots * slot_s

    while True:
        pending = [(tx_time(s), i) for i, s in enumerate(st) if s.queue]
        t_tx = min(pending)[0] if pending else inf
        t_arr = arrivals[ia][0] if ia < len(arrivals) else inf
        if t_arr == inf and t_tx == inf:
            break
        if t_arr < t_tx:                                  # an arrival while the medium is idle
            s = st[arrivals[ia][1]]
            ia += 1
            if s.queue == 0 and s.slots == 0:
                s.bstart = t_arr + difs_s                 # zero slots, sent DIFS after arriving
            s.queue += 1
            continue
        senders = [i for t, i in pending if t <= t_tx + delta_s]
        starts = {i: tx_time(st[i]) for i in senders}
        sensed = t_tx + delta_s
        # arrivals before the others can sense the medium busy: still an idle medium to them
        while ia < len(arrivals) and arrivals[ia][0] < sensed:
            t, i = arrivals[ia]
            ia += 1
            s = st[i]
            if s.queue == 0 and s.slots == 0:
                s.bstart = t + difs_s
            s.queue += 1
        for i, s in enumerate(st):                        # UpdateBackoff when the medium turns busy
            if i in starts:
                continue
            start = max(s.bstart, idle_from + difs_s)
            if s.slots and sensed >= start:
                n = min(int(math.floor((sensed - start) / slot_s + 1e-9)), s.slots)
                s.slots -= n
                s.bstart = start + n * slot_s
        end = max(starts.values()) + airtime_s
        while ia < len(arrivals) and arrivals[ia][0] < end:   # arrivals to a busy medium
            t, i = arrivals[ia]
            ia += 1
            s = st[i]
            if s.queue == 0 and s.slots == 0 and i not in starts:
                s.slots, s.bstart = rng.randrange(w), t
            s.queue += 1
        frames += len(senders)
        if trace is not None:
            first = min(starts.values())
            trace.append((first, tuple(sorted(starts)), max(starts.values()) - first))
        if len(senders) > 1:
            lost += len(senders)
        for i, t in starts.items():                       # post-transmission backoff
            s = st[i]
            s.queue -= 1
            s.slots, s.bstart = rng.randrange(w), t + airtime_s
        idle_from = end
    return Result(frames, lost)
