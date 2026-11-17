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


def verified_units(receptions: Iterable[Reception], n: int) -> int:
    """(receiver, unit) pairs whose n frames all arrived."""
    if n < 1:
        raise ValueError("n ≥ 1")
    count = 0
    for seqs in _received(receptions).values():
        per_unit: dict[int, int] = defaultdict(int)
        for s in seqs:
            per_unit[s // n] += 1
        count += sum(1 for k in per_unit.values() if k == n)
    return count


def read_allrx(path: str) -> list[Reception]:
    """The twin's `<out>_allrx.csv` (rx,src,seq,t_ns) as receptions."""
    out: list[Reception] = []
    with open(path, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            rx, src, seq, _t = line.split(",")
            out.append((int(rx), int(src), int(seq)))
    return out
