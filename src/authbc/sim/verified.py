"""What a receiver can verify from the frames it received, under the two design rules of the
unified model (docs/revision/2026-11-17_unified_model_spec.md §4, "Design rules to test"):

* **Key record once in r frames.** A source's frames form groups of r (group g = seq // r); the
  first carries the key record. Frame j of a group verifies at a receiver only if frames 1 … j of
  that group all arrived there — the dependency the rule's formula
  (1 − p)(1 − (1 − p)^r)/(r·p) = (1/r)·Σ_j (1 − p)^j encodes.
* **A signed unit split over n frames.** Unit u = seq // n verifies only if all n of its frames
  arrived.

A reception is (receiver, source, seq), seq being the source's own frame count from 0, as the
audit twin's `--traceAllRx` writes it (`ns3/authbc-links-audit.cc`).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

Reception = tuple[int, int, int]
TimedReception = tuple[int, int, int, int]      # (receiver, source, seq, t_ns)


def _received(receptions: Iterable[Reception]) -> dict[tuple[int, int], set[int]]:
    got: dict[tuple[int, int], set[int]] = defaultdict(set)
    for rx, src, seq in receptions:
        got[(rx, src)].add(seq)
    return got


def verified_key_chain(receptions: Iterable[Reception], r: int) -> int:
    """(receiver, frame) pairs that verify with a key record once in r frames."""
    if r < 1:
        raise ValueError("r ≥ 1")
    count = 0
    for seqs in _received(receptions).values():
        for s in seqs:
            if all(q in seqs for q in range(s - s % r, s)):
                count += 1
    return count


def verified_units(receptions: Iterable[Reception], n: int,
                   sent_by_src: dict[int, int] | None = None) -> int:
    """(receiver, unit) pairs whose n frames all arrived. With `sent_by_src`, a source's last
    unit counts only if all of its n frames were sent: frames sent one by one (not in a burst)
    can end a run part-way through a unit."""
    if n < 1:
        raise ValueError("n ≥ 1")
    count = 0
    for (_rx, src), seqs in _received(receptions).items():
        limit = None if sent_by_src is None else sent_by_src[src] // n
        per_unit: dict[int, int] = defaultdict(int)
        for s in seqs:
            if limit is None or s // n < limit:
                per_unit[s // n] += 1
        count += sum(1 for k in per_unit.values() if k == n)
    return count


def units_sent(sent_by_src: dict[int, int], n: int) -> int:
    """Complete units sent, over all sources."""
    return sum(v // n for v in sent_by_src.values())


def unit_completion_ns(receptions: Iterable[TimedReception], n: int) -> list[int]:
    """For every verified (receiver, unit): its last frame's arrival minus its first frame's —
    how much longer the receiver waits to verify a unit than to receive its first frame."""
    first: dict[tuple[int, int, int], int] = {}
    last: dict[tuple[int, int, int], int] = {}
    count: dict[tuple[int, int, int], int] = defaultdict(int)
    for rx, src, seq, t in receptions:
        key = (rx, src, seq // n)
        first[key] = min(first.get(key, t), t)
        last[key] = max(last.get(key, t), t)
        count[key] += 1
    return [last[k] - first[k] for k, c in count.items() if c == n]


def read_allrx(path: str) -> list[TimedReception]:
    """The twin's `<out>_allrx.csv` (rx,src,seq,t_ns) as timed receptions."""
    out: list[TimedReception] = []
    with open(path, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            rx, src, seq, t = line.split(",")
            out.append((int(rx), int(src), int(seq), int(t)))
    return out


def untimed(receptions: Iterable[TimedReception]) -> list[Reception]:
    return [(rx, src, seq) for rx, src, seq, _t in receptions]
