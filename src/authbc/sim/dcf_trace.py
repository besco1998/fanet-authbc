"""NS-3 DCF PHY-trace analysis for the broadcast-residual study (docs/02 §6, docs/audits/p7.md).

`ns3/authbc-dcf-trace.cc` logs every PHY transmission start/end on every station. This module
turns that event stream into the quantities Bianchi's model actually predicts, so the model can be
tested against a *measurement* of its own internals rather than against end-to-end goodput:

  busy period   maximal set of transmissions that overlap in time — Bianchi's "busy virtual slot".
  multiplicity  how many stations transmitted into one busy period. The model assumes this is
                Binomial(N, τ): each station transmits independently with the same probability.
  p_s           P(multiplicity == 1 | busy) — the model's success probability, measured directly.

The discriminating test is `matched_binomial_p_success`: it takes the MEASURED mean multiplicity
and asks what P(exactly one) an independent-station model with that same mean would give. If the
measured p_s is much larger, stations are negatively correlated and the failure is in Bianchi's
decoupling assumption, not in its arithmetic.

`winner_was_participant` then tests *why* they are correlated: after a collision the colliding
stations defer only DIFS while every listener defers EIFS (ns-3 measures EIFS−DIFS = 60 µs = 6⅔
slots), so colliders get a head start. Under the model the next transmitter is a uniformly random
station; under the head-start mechanism it is disproportionately a previous collider.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# The bisection bracket for τ: τ→0 gives mean multiplicity →1, τ=1 gives →N.
_TAU_TOL: float = 1e-14
_TAU_MAX_ITER: int = 200


@dataclass(frozen=True)
class Transmission:
    """One PHY transmission: station *node* occupied the medium over [start_ns, end_ns)."""

    node: int
    start_ns: int
    end_ns: int


@dataclass(frozen=True)
class BusyPeriod:
    """A maximal run of overlapping transmissions — one *busy* virtual slot in Bianchi's sense."""

    start_ns: int
    end_ns: int
    nodes: tuple[int, ...]  # in order of transmission start

    @property
    def multiplicity(self) -> int:
        """Number of stations that transmitted into this busy period (1 ⇒ success)."""
        return len(self.nodes)

    @property
    def is_success(self) -> bool:
        """A busy period carries a frame iff exactly one station transmitted into it."""
        return len(self.nodes) == 1


class TraceError(RuntimeError):
    """Raised on a malformed or inconsistent event trace (CLAUDE.md Law 3: never paper over)."""


def parse_tx_events(lines: Iterable[str]) -> list[Transmission]:
    """Pair the ``node,event,t_ns`` B/E rows of a ``.tx.csv`` into transmissions.

    A station transmits one frame at a time, so B and E alternate per node. A trailing B with no
    E (a frame still on air when the simulation stopped) is dropped — it has no measurable end.
    Any other interleaving is a trace defect and raises.
    """
    open_start: dict[int, int] = {}
    out: list[Transmission] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("node,"):
            continue
        node_s, event, t_s = line.split(",")
        node, t_ns = int(node_s), int(t_s)
        if event == "B":
            if node in open_start:
                raise TraceError(f"node {node}: PhyTxBegin at {t_ns} while a tx was already open")
            open_start[node] = t_ns
        elif event == "E":
            start = open_start.pop(node, None)
            if start is None:
                raise TraceError(f"node {node}: PhyTxEnd at {t_ns} with no matching begin")
            out.append(Transmission(node=node, start_ns=start, end_ns=t_ns))
        else:
            raise TraceError(f"unknown tx event {event!r}")
    out.sort(key=lambda t: (t.start_ns, t.node))
    return out


def busy_periods(txs: Sequence[Transmission]) -> list[BusyPeriod]:
    """Group transmissions into maximal overlapping runs (busy periods).

    Two transmissions belong to the same busy period iff their on-air intervals overlap: the
    medium never went idle between them, so no station could have deferred between the two.
    Touching intervals (end == start) do NOT overlap — DIFS always separates consecutive periods,
    so a zero-length gap would be a distinct period.
    """
    periods: list[BusyPeriod] = []
    cur_nodes: list[int] = []
    cur_start = cur_end = 0
    for t in sorted(txs, key=lambda x: (x.start_ns, x.node)):
        if cur_nodes and t.start_ns < cur_end:
            cur_nodes.append(t.node)
            cur_end = max(cur_end, t.end_ns)
            continue
        if cur_nodes:
            periods.append(BusyPeriod(cur_start, cur_end, tuple(cur_nodes)))
        cur_nodes = [t.node]
        cur_start, cur_end = t.start_ns, t.end_ns
    if cur_nodes:
        periods.append(BusyPeriod(cur_start, cur_end, tuple(cur_nodes)))
    return periods


def within(periods: Sequence[BusyPeriod], lo_ns: int, hi_ns: int) -> list[BusyPeriod]:
    """Busy periods lying wholly inside [lo_ns, hi_ns) — the steady-state analysis window."""
    return [p for p in periods if p.start_ns >= lo_ns and p.end_ns < hi_ns]


def multiplicity_hist(periods: Sequence[BusyPeriod]) -> dict[int, int]:
    """{multiplicity: count} over the given busy periods."""
    hist: dict[int, int] = {}
    for p in periods:
        hist[p.multiplicity] = hist.get(p.multiplicity, 0) + 1
    return dict(sorted(hist.items()))


def measured_p_success(periods: Sequence[BusyPeriod]) -> float:
    """P(multiplicity == 1 | busy) — Bianchi's p_s, measured."""
    if not periods:
        raise TraceError("no busy periods in the analysis window")
    return sum(1 for p in periods if p.is_success) / len(periods)


def mean_multiplicity(periods: Sequence[BusyPeriod]) -> float:
    """E[multiplicity | busy] = transmissions per busy period."""
    if not periods:
        raise TraceError("no busy periods in the analysis window")
    return sum(p.multiplicity for p in periods) / len(periods)


def _p_tr(tau: float, n: int) -> float:
    """P(≥1 of n independent stations transmits) = 1 − (1−τ)^n, without cancellation.

    The naive form loses every significant digit for τ ≲ 1e-9 (1−(1−τ)^n subtracts two numbers
    that agree to ~15 digits), which made p_s exceed 1 for near-collision-free traces.
    """
    return -math.expm1(n * math.log1p(-tau))


def tau_matching_mean(n_stations: int, mean_mult: float) -> float:
    """τ such that INDEPENDENT stations reproduce the measured mean multiplicity.

    Solves E[k | k ≥ 1] = Nτ / (1 − (1−τ)^N) = *mean_mult* by bisection. This is how we hold the
    "how often stations transmit" question fixed while testing the "are they independent?" one.
    """
    if n_stations < 2:
        raise ValueError(f"n_stations must be ≥ 2, got {n_stations}")
    if not 1.0 <= mean_mult <= n_stations:
        raise ValueError(f"mean multiplicity must lie in [1, {n_stations}], got {mean_mult}")

    def mean_of(tau: float) -> float:
        return n_stations * tau / _p_tr(tau, n_stations)

    lo, hi = 1e-15, 1.0 - 1e-15
    for _ in range(_TAU_MAX_ITER):
        mid = 0.5 * (lo + hi)
        if mean_of(mid) < mean_mult:
            lo = mid
        else:
            hi = mid
        if hi - lo < _TAU_TOL:
            break
    return 0.5 * (lo + hi)


def matched_binomial_p_success(n_stations: int, mean_mult: float) -> float:
    """P(exactly one tx | ≥1) for independent stations with the MEASURED mean multiplicity.

    The null hypothesis for the decoupling assumption: same access rate, no correlation.
    """
    tau = tau_matching_mean(n_stations, mean_mult)
    p_tr = _p_tr(tau, n_stations)
    exactly_one = n_stations * tau * math.exp((n_stations - 1) * math.log1p(-tau))
    return exactly_one / p_tr


@dataclass(frozen=True)
class HeadStart:
    """Evidence on whether the next transmitter came from the previous busy period's colliders."""

    transitions: int          # consecutive busy-period pairs whose winner is UNAMBIGUOUS
    winner_was_participant: int  # …whose winner transmitted in the previous period
    expected_uniform: float   # Σ k_prev/N over the same pairs — the model's prediction
    successes_after_collision: int
    collisions_seen: int
    successes_after_success: int
    successes_seen: int

    @property
    def observed_fraction(self) -> float:
        return self.winner_was_participant / self.transitions if self.transitions else 0.0

    @property
    def expected_fraction(self) -> float:
        return self.expected_uniform / self.transitions if self.transitions else 0.0

    @property
    def enrichment(self) -> float:
        """Observed ÷ uniform. 1.0 means the previous busy period carried no information."""
        exp = self.expected_fraction
        return self.observed_fraction / exp if exp else 0.0

    @property
    def p_success_after_collision(self) -> float:
        if not self.collisions_seen:
            return 0.0
        return self.successes_after_collision / self.collisions_seen

    @property
    def p_success_after_success(self) -> float:
        return self.successes_after_success / self.successes_seen if self.successes_seen else 0.0


def winner_was_participant(periods: Sequence[BusyPeriod], n_stations: int) -> HeadStart:
    """Test the EIFS head-start mechanism on consecutive busy periods.

    For every adjacent pair, ask whether the station that took the medium NEXT was one of the
    stations that transmitted in the previous busy period. Bianchi's independent stations give
    k_prev/N; the post-transmission head start gives far more.

    **Only pairs whose next period is a success are counted** (audit A7). When the next period is
    itself a collision there is no single winner, and picking one — e.g. the lowest-numbered of the
    simultaneous starters — is arbitrary; at N=50 that describes 78 % of transitions and dilutes the
    statistic from 7.6× to 3.1×. The conditional success-rate counters below are unaffected and use
    every pair.
    """
    if n_stations < 2:
        raise ValueError(f"n_stations must be ≥ 2, got {n_stations}")
    transitions = hits = 0
    expected = 0.0
    succ_after_coll = colls = succ_after_succ = succs = 0
    for prev, nxt in zip(periods, periods[1:], strict=False):
        if nxt.is_success:
            transitions += 1
            if nxt.nodes[0] in set(prev.nodes):
                hits += 1
            expected += len(set(prev.nodes)) / n_stations
        if prev.is_success:
            succs += 1
            succ_after_succ += int(nxt.is_success)
        else:
            colls += 1
            succ_after_coll += int(nxt.is_success)
    return HeadStart(
        transitions=transitions,
        winner_was_participant=hits,
        expected_uniform=expected,
        successes_after_collision=succ_after_coll,
        collisions_seen=colls,
        successes_after_success=succ_after_succ,
        successes_seen=succs,
    )


def deferral_gaps(periods: Sequence[BusyPeriod]) -> list[tuple[int, bool, bool]]:
    """(gap_ns, next-starter-was-participant, previous-was-collision) for each adjacent pair.

    The gap between the end of one busy period and the start of the next is the winner's total
    deferral: DIFS + slot·backoff if it transmitted in (or heard nothing wrong during) the previous
    period, EIFS + slot·backoff if it heard a corrupted frame. The two families are separated by
    exactly EIFS − DIFS, so the gap histogram is a direct read-out of which rule applied.
    """
    out: list[tuple[int, bool, bool]] = []
    for prev, nxt in zip(periods, periods[1:], strict=False):
        out.append((nxt.start_ns - prev.end_ns,
                    nxt.nodes[0] in set(prev.nodes),
                    not prev.is_success))
    return out
