"""Framer ABC + MTU/batch helpers (docs/01 §1 placements, docs/02 §6-7).

A ``Framer`` packs records into wire frames (reusing the frozen P2 ``wire`` builders) and
unpacks a received frame back to ``(records, ok_mask)`` where ``ok_mask[i]`` says whether
record i verified. Placement B/C/D are all-or-nothing per frame (one auth object); A is
per-record. ``b_max`` is the byte-budget batch limit (docs/02 T2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence

from authbc.ledger.record import Record
from authbc.placement.wire import Frame

M_MTU = 1500  # application MTU budget (docs/01 §1, docs/02 §6)
H_F = 44      # ledger frame header bytes — MEASURED from wire.py (B1, docs/01 §2a)


def b_max(s: int, g_a: int, *, mtu: int = M_MTU, h_f: int = H_F) -> int:
    """Max single-auth records per frame: ⌊(M − H_f − g_a)/s⌋ (docs/02 T2 §, B/C/D)."""
    if s <= 0:
        raise ValueError("record size s must be positive")
    return (mtu - h_f - g_a) // s


def b_max_inline(s: int, g_record: int = 64, *, mtu: int = M_MTU, h_f: int = H_F) -> int:
    """Max per-record-signed (placement A) records: ⌊(M − H_f)/(s + g_record)⌋."""
    if s <= 0:
        raise ValueError("record size s must be positive")
    return (mtu - h_f) // (s + g_record)


def _chunks(records: Sequence[Record], b: int) -> Iterator[list[Record]]:
    if b < 1:
        raise ValueError("batch size b must be >= 1")
    for i in range(0, len(records), b):
        yield list(records[i : i + b])


class Framer(ABC):
    """Pack records into frames / unpack a frame to (records, ok_mask)."""

    @abstractmethod
    def pack(self, records: Sequence[Record], *, b: int) -> list[Frame]:
        ...

    @abstractmethod
    def unpack(self, frame: Frame, **verifier) -> tuple[list[Record], list[bool]]:
        ...
