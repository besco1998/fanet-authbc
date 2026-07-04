"""Placement C — cross-signer BLS aggregate (relay/attestation), docs/01 §1.

A relay forwards b records from DIFFERENT originators, each already BLS-signed by its owner;
the relay AGGREGATES the b signatures into one 96 B signature (it cannot sign for others).
``unpack`` runs ``aggregate_verify`` — which is **all-or-nothing**: a single bad inner signature
fails the whole aggregate and BLS cannot localize which signer was bad, so the entire frame's
ok_mask is False and the frame is counted as failed (docs/01 §4).
"""

from __future__ import annotations

from collections.abc import Sequence

from authbc.crypto.bls import BlsScheme
from authbc.ledger.record import Record
from authbc.placement.framer import Framer
from authbc.placement.wire import Frame, Placement, verify_C

_BLS = BlsScheme()


class RelayAggFramer(Framer):
    def pack(
        self, records: Sequence[Record], *, sigs: Sequence[bytes], pks: Sequence, b: int
    ) -> list[Frame]:
        if not (len(records) == len(sigs) == len(pks)):
            raise ValueError("records, sigs, pks must be the same length")
        frames: list[Frame] = []
        for i in range(0, len(records), b):
            rc = list(records[i : i + b])
            sc = list(sigs[i : i + b])
            pc = [_BLS.pk_to_bytes(p) for p in pks[i : i + b]]
            frames.append(Frame(t=Placement.C, src=rc[0].src, base_seq=rc[0].seq,
                                recs=tuple(rc), auth={"agg": _BLS.aggregate(sc), "signers": pc}))
        return frames

    def unpack(self, frame: Frame) -> tuple[list[Record], list[bool]]:
        ok = verify_C(frame)  # all-or-nothing
        return list(frame.recs), [ok] * frame.n
