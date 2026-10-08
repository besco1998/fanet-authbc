"""Sender and receiver state for the lean frame — what happens when a frame is lost (docs/01 §4b).

`wire_v2` is the format; this module is the protocol around it, and it exists to answer four
questions the paper could not answer while the design was only a byte model (audit F45):

* **Which frames decode alone?** The sender emits a self-contained frame every `ref_interval`
  frames and dependent ones in between (`ref_interval = 1` means every frame decodes alone).
* **What does a lost frame cost?** A dependent frame cannot be rebuilt without its predecessor, so
  the receiver reports `DESYNC` for it and for every later dependent frame, until the next
  self-contained one. That propagation is what docs/02 T3' counts.
* **What stops a replay?** The signature is checked first; then the ledger store rejects any
  record whose `(src, seq)` is not newer than the last one accepted from that sender.
* **Can a replay or a forgery desynchronise a receiver?** No: the state a dependent frame is
  decoded against advances only when a frame has been verified AND stored.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from authbc.ledger.record import Record
from authbc.ledger.store import Outcome, Store
from authbc.placement.wire import WireDecodeError
from authbc.placement.wire_v2 import (
    DesyncError,
    build_B_v2,
    decode_frame_v2,
    encode_frame_v2,
    frame_src,
    verify_v2,
)


class Receipt(StrEnum):
    """What a receiver did with one frame."""

    ACCEPTED = "accepted"            # decoded, verified, every record stored
    DESYNC = "desync"                # well formed, but coded against a record not held
    MALFORMED = "malformed"
    UNKNOWN_SENDER = "unknown_sender"
    BAD_SIGNATURE = "bad_signature"
    REPLAY = "replay"
    EQUIVOCATION = "equivocation"
    TAMPERED = "tampered"            # verified, but its chain link contradicts the store


_FROM_STORE: dict[Outcome, Receipt] = {
    Outcome.REPLAY: Receipt.REPLAY,
    Outcome.EQUIVOCATION: Receipt.EQUIVOCATION,
    Outcome.TAMPERED: Receipt.TAMPERED,
}


class LeanSender:
    """Frames one UAV's own consecutive records, one self-contained frame per `ref_interval`."""

    def __init__(self, sk: Any, *, ref_interval: int = 1) -> None:
        if ref_interval < 1:
            raise ValueError(f"ref_interval must be ≥ 1 frame, got {ref_interval}")
        self._sk = sk
        self._ref = ref_interval
        self._frames = 0
        self._last: Record | None = None

    def frame(self, recs: Sequence[Record]) -> bytes:
        """Encode the next frame. `recs` must directly follow the previous call's records."""
        dependent = self._frames % self._ref != 0
        prev = self._last if dependent else None
        data = encode_frame_v2(build_B_v2(recs, self._sk, prev=prev), prev=prev)
        self._frames += 1
        self._last = recs[-1]
        return data


@dataclass(frozen=True)
class Received:
    receipt: Receipt
    records: tuple[Record, ...] = ()


class LeanReceiver:
    """Decodes, verifies and stores lean frames from any number of senders."""

    def __init__(self, public_keys: Mapping[int, Any]) -> None:
        self._pks = dict(public_keys)
        self._last: dict[int, Record] = {}
        self.store = Store()
        self.counters: dict[str, int] = {r.value: 0 for r in Receipt}

    def receive(self, data: bytes) -> Received:
        out = self._receive(data)
        self.counters[out.receipt.value] += 1
        return out

    def _receive(self, data: bytes) -> Received:
        try:
            src = frame_src(data)
            frame = decode_frame_v2(data, prev=self._last.get(src))
        except DesyncError:
            return Received(Receipt.DESYNC)
        except WireDecodeError:
            return Received(Receipt.MALFORMED)
        pk = self._pks.get(src)
        if pk is None:
            return Received(Receipt.UNKNOWN_SENDER)
        if not verify_v2(frame, pk):
            return Received(Receipt.BAD_SIGNATURE)
        # A frame is signed as a unit, so its records are accepted or refused together: the first
        # record the store declines decides the frame.
        for rec in frame.recs:
            outcome = self.store.ingest(rec)
            if outcome is not Outcome.STORED:
                return Received(_FROM_STORE[outcome])
        # Only now may later dependent frames be decoded against this one. Advancing on a frame
        # that merely DECODED would let a replayed self-contained frame rewind the state and
        # desynchronise an honest sender's stream.
        self._last[src] = frame.recs[-1]
        return Received(Receipt.ACCEPTED, frame.recs)
