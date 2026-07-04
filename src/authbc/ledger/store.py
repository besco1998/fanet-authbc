"""Ledger store — ingest overheard records with replay/equivocation/tamper handling.

Owned-object model (docs/01 §1): a node stores verified records overheard from others. Per src
we keep every accepted record's hash keyed by ``(src, seq)`` (for duplicate + equivocation
detection) and the highest accepted ``seq`` (for replay rejection). Outcomes are counted; the
equivocation evidence pair is retained (docs/03 §3).

**seq u32 wraparound policy**: ``seq`` is required strictly monotonic-increasing per src, so a
wrap back through 0 (seq ≤ last accepted) is rejected as a replay. u32 gives ~4.3e9 records/UAV
(~6.8 yr at 20 rec/s) — beyond this arm's scope; the wrap is rejected, never silently accepted.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from authbc.ledger.record import GENESIS_PH, Record
from authbc.ledger.verify import signature_ok


class Outcome(StrEnum):
    STORED = "stored"
    REPLAY = "replay"
    EQUIVOCATION = "equivocation"
    TAMPERED = "tampered"


class Store:
    def __init__(self) -> None:
        self._accepted: dict[tuple[int, int], bytes] = {}  # (src,seq) -> record_hash
        self._last_seq: dict[int, int] = {}
        self._records: dict[tuple[int, int], Record] = {}
        self.equivocations: list[tuple[Record, Record]] = []  # retained evidence pairs
        self.counters: dict[str, int] = {o.value: 0 for o in Outcome}

    def ingest(
        self, rec: Record, *, scheme: Any = None, pk: Any = None, sig: bytes | None = None
    ) -> Outcome:
        # 1. authenticity — a bad signature is tampering (any field flip breaks the sig)
        if scheme is not None and sig is not None and not signature_ok(scheme, pk, rec, sig):
            return self._count(Outcome.TAMPERED)

        key = (rec.src, rec.seq)
        rh = rec.record_hash()

        # 2. same (src,seq) seen before → duplicate (replay) or equivocation
        if key in self._accepted:
            if self._accepted[key] != rh:
                self.equivocations.append((self._records[key], rec))
                return self._count(Outcome.EQUIVOCATION)
            return self._count(Outcome.REPLAY)

        # 3. stale seq for a slot we never accepted → replay (covers u32 wraparound)
        if rec.seq <= self._last_seq.get(rec.src, -1):
            return self._count(Outcome.REPLAY)

        # 4. chain-link integrity where the predecessor is known (contiguous); gaps are allowed
        #    (availability under loss is a robustness metric, docs/01 — not a security failure)
        expected_prev = GENESIS_PH if rec.seq == 0 else self._accepted.get((rec.src, rec.seq - 1))
        if expected_prev is not None and rec.prev_hash != expected_prev:
            return self._count(Outcome.TAMPERED)

        # accept
        self._accepted[key] = rh
        self._records[key] = rec
        self._last_seq[rec.src] = rec.seq
        return self._count(Outcome.STORED)

    def _count(self, outcome: Outcome) -> Outcome:
        self.counters[outcome.value] += 1
        return outcome

    def records(self) -> list[Record]:
        return list(self._records.values())
