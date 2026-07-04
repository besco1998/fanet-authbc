"""Ledger record + the ONE canonical-bytes definition (docs/01 §1 "Ledger", §4 wire format).

``Record`` := ``{src:u16, seq:u32, ts:u32(ms), ph:bytes32, pl:map}`` where ``pl`` is the
integer-only telemetry map (docs/06 §5 — floats break canonical CBOR). Records chain by
``prev_hash = SHA-256(canonical_bytes(previous record))``; genesis prev_hash = 32 zero bytes.

``canonical_bytes`` is defined **once** here and used everywhere a record or frame region is
hashed or signed, so the byte boundary is unambiguous (docs/01 §4).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import cbor2

GENESIS_PH: bytes = b"\x00" * 32
PREV_HASH_LEN: int = 32
_U16 = (0, 2**16 - 1)
_U32 = (0, 2**32 - 1)

# Canonical record map key order (docs/01 §4). cbor2 canonical=True sorts keys deterministically,
# so this order is documentation; the on-wire order is always the canonical (sorted) one.
RECORD_KEYS: tuple[str, ...] = ("src", "seq", "ts", "ph", "pl")


def canonical_bytes(obj: Any) -> bytes:
    """Canonical CBOR (RFC 8949 §4.2 core deterministic) — docs/01 §4.

    Deterministic map-key order + shortest int/length forms; ``canonical=True`` never emits
    indefinite-length items. THE single definition used for all hashing and signing.
    """
    return cbor2.dumps(obj, canonical=True)


@dataclass(frozen=True)
class Record:
    src: int
    seq: int
    ts: int
    prev_hash: bytes
    pl: dict[str, int]

    def __post_init__(self) -> None:
        if not (_U16[0] <= self.src <= _U16[1]):
            raise ValueError(f"src out of u16 range: {self.src}")
        for name, val in (("seq", self.seq), ("ts", self.ts)):
            if not (_U32[0] <= val <= _U32[1]):
                raise ValueError(f"{name} out of u32 range: {val}")
        if not isinstance(self.prev_hash, bytes) or len(self.prev_hash) != PREV_HASH_LEN:
            raise ValueError(f"prev_hash must be {PREV_HASH_LEN} bytes")
        for k, v in self.pl.items():
            if isinstance(v, bool) or not isinstance(v, int):
                raise TypeError(f"pl[{k}] must be a non-bool int (canonical stability), got {v!r}")
        # freeze the payload so a Record is effectively immutable
        object.__setattr__(self, "pl", MappingProxyType(dict(self.pl)))

    def to_map(self) -> dict:
        """Canonical record map per docs/01 §4 (keys src,seq,ts,ph,pl)."""
        return {"src": self.src, "seq": self.seq, "ts": self.ts, "ph": self.prev_hash,
                "pl": dict(self.pl)}

    @classmethod
    def from_map(cls, m: dict) -> Record:
        """Reconstruct a Record from its canonical map (inverse of ``to_map``)."""
        return cls(src=m["src"], seq=m["seq"], ts=m["ts"], prev_hash=m["ph"], pl=dict(m["pl"]))

    def canonical(self) -> bytes:
        return canonical_bytes(self.to_map())

    def record_hash(self) -> bytes:
        """SHA-256 over this record's canonical bytes — the value the NEXT record chains to."""
        return hashlib.sha256(self.canonical()).digest()
