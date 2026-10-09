"""Unequal received power and capture, on top of the access-rule model (docs/02 §6h).

`dcf_unsaturated` loses every frame whose transmission overlaps another: all stations at one
point, equal power, no capture. That is the scenario every capacity of this work was simulated
in, and the first thing a reader doubts. This module keeps the same access rule — it calls the
same simulator and changes nothing in it — and places the stations in a disc. For each group of
frames that start together it then asks, receiver by receiver, the question the packet
simulator's physical layer asks (ns-3.48, `PhyEntity::EndPreambleDetectionPeriod` and
`ThresholdPreambleDetectionModel`): of the preambles that arrive together, is the strongest one
at least `threshold_db` above the sum of the others? If so that frame is received there; the
others are not.

What it assumes, and so what it cannot show:

* every station still senses every other one, exactly as before. That holds while every pair
  is within energy-detection range. At a larger radius a station that cannot lock onto either
  of two colliding frames may take the medium for idle; this model does not have that.
* noise is negligible beside the weakest signal (true at the radii registered);
* the frames of a group start together, which the access rule guarantees to within the
  detection time: a station that could hear a transmission defers to it.

Nothing is fitted: the threshold is the simulator's default (4 dB), the path-loss exponent is
free space (2), and distances below the reference distance of the simulator's log-distance
model (1 m) are treated as that model treats them.
"""

from __future__ import annotations

import math
import random

from authbc.sim import dcf_unsaturated as access

THRESHOLD_DB: float = 4.0           # ns-3 ThresholdPreambleDetectionModel::Threshold
EXPONENT: float = 2.0               # free space
REFERENCE_M: float = 1.0            # ns-3 LogDistancePropagationLossModel::ReferenceDistance


def positions(n_nodes: int, radius_m: float, seed: int) -> list[tuple[float, float]]:
    """`n_nodes` points uniform in a disc of radius `radius_m`."""
    rng = random.Random(f"positions:{seed}")
    points = []
    for _ in range(n_nodes):
        r, a = radius_m * math.sqrt(rng.random()), 2.0 * math.pi * rng.random()
        points.append((r * math.cos(a), r * math.sin(a)))
    return points


def gains(points: list[tuple[float, float]], exponent: float = EXPONENT) -> list[list[float]]:
    """gains[i][r]: power received at r from i, relative to the power at the reference distance."""
    out = []
    for xi, yi in points:
        out.append([max(math.hypot(xi - xr, yi - yr), REFERENCE_M) ** -exponent
                    for xr, yr in points])
    return out


def received(senders: list[int], gain: list[list[float]], ratio: float) -> int:
    """Receptions of one group of frames that start together, summed over receivers.

    A lone frame reaches every other station. Of several, each station that is not itself
    sending receives the strongest if it exceeds the sum of the rest by `ratio`, else none.
    """
    n = len(gain)
    if len(senders) == 1:
        return n - 1
    sending = set(senders)
    count = 0
    for r in range(n):
        if r in sending:
            continue
        powers = [gain[s][r] for s in senders]
        best = max(powers)
        count += best >= ratio * (sum(powers) - best)
    return count


def run(n_nodes: int, frames_per_s: float, airtime_s: float, *, radius_m: float,
        seed: int = 1, exponent: float = EXPONENT, threshold_db: float = THRESHOLD_DB,
        sim_time_s: float = 20.0, w0: int = access.W0) -> float:
    """Delivered fraction of one run: receptions over frames sent times the other stations."""
    gain = gains(positions(n_nodes, radius_m, seed), exponent)
    ratio = 10.0 ** (threshold_db / 10.0)
    got = 0

    def on_send(senders: list[int]) -> None:
        nonlocal got
        got += received(senders, gain, ratio)

    result = access.run(n_nodes, frames_per_s, airtime_s, seed=seed, sim_time_s=sim_time_s,
                        w0=w0, on_send=on_send)
    return got / (result.frames * (n_nodes - 1))


def mean_delivered(n_nodes: int, frames_per_s: float, airtime_s: float, *, radius_m: float,
                   seeds: int = 30, threshold_db: float = THRESHOLD_DB) -> float:
    """Mean delivered fraction over `seeds` runs numbered from 1, each with its own placement."""
    return sum(run(n_nodes, frames_per_s, airtime_s, radius_m=radius_m, seed=s,
                   threshold_db=threshold_db) for s in range(1, seeds + 1)) / seeds
