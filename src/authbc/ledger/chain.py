"""Per-UAV append-only hash chain (docs/01 §1 "Ledger"; owned-object model).

Only the owner appends to its own chain. ``append`` fills ``seq`` (monotonic from 0), the
timestamp, and ``prev_hash`` (genesis zero-hash at seq 0, else SHA-256 of the previous
record's canonical bytes). ``verify`` re-walks the chain independently of append.
"""

from __future__ import annotations

from authbc.ledger.record import GENESIS_PH, Record


class Chain:
    def __init__(self, src: int) -> None:
        self.src = src
        self._records: list[Record] = []

    @property
    def head(self) -> Record | None:
        return self._records[-1] if self._records else None

    def __len__(self) -> int:
        return len(self._records)

    def append(self, pl: dict[str, int], ts: int) -> Record:
        prev_hash = GENESIS_PH if self.head is None else self.head.record_hash()
        rec = Record(src=self.src, seq=len(self._records), ts=ts, prev_hash=prev_hash, pl=pl)
        self._records.append(rec)
        return rec

    def records(self) -> list[Record]:
        return list(self._records)

    def verify(self) -> bool:
        """True iff seq is 0..n-1, every src matches, and every prev_hash chains correctly."""
        prev = GENESIS_PH
        for i, rec in enumerate(self._records):
            if rec.seq != i or rec.src != self.src or rec.prev_hash != prev:
                return False
            prev = rec.record_hash()
        return True
