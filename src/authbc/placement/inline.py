"""Placement A — inline per-record signatures (docs/01 §1, the baseline).

Every record carries its own Ed25519 signature; loss of a frame loses only the records in it,
and each record verifies independently, so ``unpack`` returns a per-record ``ok_mask``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.placement.framer import Framer, _chunks
from authbc.placement.wire import Frame, build_A

_ED = Ed25519Scheme()


class InlineFramer(Framer):
    """Frame owner signs each of its own records individually (Ed25519)."""

    def __init__(self, sk) -> None:
        self._sk = sk

    def pack(
        self,
        records: Sequence[Record],
        *,
        b: int,
        sigs: Sequence[bytes] | None = None,
        pks: Sequence[Any] | None = None,
    ) -> list[Frame]:
        del sigs, pks   # placement A signs internally (see Framer.pack)
        return [build_A(chunk, self._sk) for chunk in _chunks(records, b)]

    def unpack(self, frame: Frame, *, pk: Any = None) -> tuple[list[Record], list[bool]]:
        if pk is None:
            raise ValueError(
                "placement A (inline) requires the sender public key: "
                "unpack(frame, pk=pk)"
            )
        ok = [_ED.verify(pk, r.canonical(), sig)
              for r, sig in zip(frame.recs, frame.auth, strict=True)]
        return list(frame.recs), ok
