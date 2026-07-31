"""Placement B — self-batch, one signer (docs/01 §1).

A UAV packs b of its OWN records into one frame and signs the frame once (Ed25519 default).
Self-contained ⇒ loss-local: a received frame verifies all b records together, so ``unpack``'s
ok_mask is all-or-nothing (one signature covers the whole covered region).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from authbc.ledger.record import Record
from authbc.placement.framer import Framer, _chunks
from authbc.placement.wire import Frame, build_B, verify_B

_G_A = 64  # one Ed25519 signature


class SelfBatchFramer(Framer):
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
        del sigs, pks   # placement B signs internally (see Framer.pack)
        return [build_B(chunk, self._sk) for chunk in _chunks(records, b)]

    def unpack(self, frame: Frame, *, pk: Any = None) -> tuple[list[Record], list[bool]]:
        if pk is None:
            raise ValueError(
                "placement B (self-batch) requires the sender public key: "
                "unpack(frame, pk=pk)"
            )
        ok = verify_B(frame, pk)
        return list(frame.recs), [ok] * frame.n  # all-or-nothing
