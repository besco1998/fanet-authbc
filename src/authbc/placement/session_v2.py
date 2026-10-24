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

And a fifth, which the paper answered before the code did (audit F80):

* **What can a receiver show to someone else?** One signature covers a frame, so a record is
  evidence only together with its frame. The receiver keeps every accepted frame, and both
  frames of an equivocation. `verified_records` and `proves_equivocation` are what a third
  party runs on them: they take the sender's public key and no receiver state.
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


@dataclass(frozen=True)
class Equivocation:
    """Two frames one sender signed that give one sequence number two different records."""

    src: int
    seq: int
    held: bytes       # the frame accepted earlier, as it arrived
    offered: bytes    # the frame that contradicts it, as it arrived


def verified_records(data: bytes, pk: Any) -> tuple[Record, ...] | None:
    """The records of a frame that decodes and verifies with nothing but the sender's key.

    None for a frame that is malformed, that fails its signature, or that is coded against a
    record it does not carry: such a frame is evidence only with the frames before it, back to
    one that starts with a keyframe. The design sends a keyframe in every frame.
    """
    try:
        frame = decode_frame_v2(data)
    except (DesyncError, WireDecodeError):
        return None
    return frame.recs if verify_v2(frame, pk) else None


def proves_equivocation(held: bytes, offered: bytes, pk: Any) -> bool:
    """True iff the two frames, each checked alone under ``pk``, give one sequence number of
    one sender two different records. No receiver state enters: a third party can run it."""
    first, second = verified_records(held, pk), verified_records(offered, pk)
    if first is None or second is None:
        return False
    signed = {(r.src, r.seq): r.canonical() for r in first}
    return any(signed.get((r.src, r.seq), r.canonical()) != r.canonical() for r in second)


class LeanReceiver:
    """Decodes, verifies and stores lean frames from any number of senders."""

    def __init__(self, public_keys: Mapping[int, Any]) -> None:
        self._pks = dict(public_keys)
        self._last: dict[int, Record] = {}
        self._frames: dict[tuple[int, int], bytes] = {}   # (src, seq) -> the frame it came in
        self.evidence: list[Equivocation] = []
        self.store = Store()
        self.counters: dict[str, int] = {r.value: 0 for r in Receipt}

    def frame_of(self, src: int, seq: int) -> bytes | None:
        """The accepted frame that carried this record: what makes the record checkable."""
        return self._frames.get((src, seq))

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
        # Looked for in every record before any is offered to the store: a frame whose first
        # record repeats one that is held would otherwise be refused as a replay, and a
        # different record signed for a later sequence number would never be seen.
        contradicted = next((r for r in frame.recs if self.store.contradicts(r)), None)
        if contradicted is not None:
            self.store.ingest(contradicted)       # the store counts it and keeps the two records
            self.evidence.append(Equivocation(src, contradicted.seq,
                                              self._frames[(src, contradicted.seq)], data))
            return Received(Receipt.EQUIVOCATION)
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
        for rec in frame.recs:
            self._frames[(src, rec.seq)] = data
        return Received(Receipt.ACCEPTED, frame.recs)
