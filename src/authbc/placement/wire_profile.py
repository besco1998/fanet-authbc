"""An integer-keyed frame profile, and what it does to the exclusion bound (M5/F44, docs/02 T6).

**Why this module exists.** `docs/01 §2a` has always said the frame skeleton is mostly CBOR *text*
key names and that "an integer-keyed profile would shrink substantially — that is a wire-format
optimisation this thesis does not claim". Separately, `docs/02` T6 claims an exclusion bound
`s_max = M − H_f − g_a` that **depends on H_f**. Those two facts were never put together, and the
consequence is not small: the header this thesis declines to optimise is the reason one of the four
excluded EU868 data rates is excluded.

**Nothing here changes the wire format.** ⚠️ D6 freezes it, `placement/wire.py` is untouched, and
every frozen artifact is bit-identical. This module *measures an alternative* so the headroom is a
reported number rather than an admission, and so T6's dependence on our own untuned framing is
visible instead of implicit.

**What the alternative changes, and what it cannot.**

* Integer keys instead of text keys: seven keys costing 29 B become seven costing 7 B.
* Per-record `src` and `seq` elided: in placement B every record in a frame shares one sender and
  carries consecutive sequence numbers, so both are derivable from the frame's `src` and
  `base_seq` + index. This is the *same* argument that justified per-frame chaining (docs/02 §9b,
  F5) applied one field further.
* ⚠️ It **cannot** touch DR0–DR2. There `M = 51 < g_a = 64`: the signature alone overflows the
  payload, so the exclusion holds at a zero-byte header and a one-byte record. That half of the
  claim is untouchable by any framing work, and it is the half worth leading with.

Implements the M5 row of `docs/OPEN_ITEMS.md §A9`. Artifact: `results/raw/wire_profile.csv`.
"""

from __future__ import annotations

from dataclasses import dataclass

import cbor2

from authbc.ledger.record import Record
from authbc.placement.wire import Frame, Placement, encode_frame

# Integer key assignments for the lean profile. Chosen 0..6 / 1..5 so every key costs one byte in
# canonical CBOR (an unsigned integer 0..23 encodes in a single byte).
F_V, F_T, F_SRC, F_BASE_SEQ, F_N, F_RECS, F_AUTH = range(7)
R_SRC, R_SEQ, R_TS, R_PH, R_PL = 1, 2, 3, 4, 5

_AUTH_BYTES = 64  # Ed25519 / ECDSA-P256, the schemes the byte results use


def _canon(obj: object) -> bytes:
    return cbor2.dumps(obj, canonical=True)


@dataclass(frozen=True)
class ProfileSizes:
    """Measured sizes for one wire profile at a given batch."""

    name: str
    frame_bytes: int
    record_bytes_total: int
    frame_header_bytes: int          # H_f, by the docs/01 §2a definition
    bytes_per_record: float

    @property
    def h_f(self) -> int:
        return self.frame_header_bytes


def _sizes(name: str, frame_len: int, rec_total: int, batch: int) -> ProfileSizes:
    return ProfileSizes(name=name, frame_bytes=frame_len, record_bytes_total=rec_total,
                        frame_header_bytes=frame_len - rec_total - _AUTH_BYTES,
                        bytes_per_record=frame_len / batch)


def current_profile(batch: int = 4, *, src: int = 40_000, base_seq: int = 180_000,
                    payload: dict | None = None) -> ProfileSizes:
    """The frozen text-keyed format actually shipped by `placement.wire` (docs/01 §4)."""
    pl = payload if payload is not None else {"a": 1}
    recs = tuple(Record(src=src, seq=base_seq + i, ts=1_000 + i,
                        prev_hash=b"\x11" * 32, pl=pl) for i in range(batch))
    frame = Frame(t=Placement.B, src=src, base_seq=base_seq, recs=recs,
                  auth=b"\x00" * _AUTH_BYTES)
    return _sizes("current", len(encode_frame(frame)),
                  sum(len(r.canonical()) for r in recs), batch)


def lean_profile(batch: int = 4, *, src: int = 40_000, base_seq: int = 180_000,
                 payload: dict | None = None, elide_redundant: bool = True) -> ProfileSizes:
    """Integer-keyed profile carrying the SAME information; optionally elides `src`/`seq`.

    `elide_redundant=False` isolates the key-naming saving alone, so the two mechanisms can be
    attributed separately rather than reported as one lump.
    """
    pl = payload if payload is not None else {"a": 1}
    recs: list[dict[int, object]] = []
    for i in range(batch):
        rec: dict[int, object] = {R_TS: 1_000 + i, R_PH: b"\x11" * 32, R_PL: pl}
        if not elide_redundant:
            rec[R_SRC] = src
            rec[R_SEQ] = base_seq + i
        recs.append(rec)
    frame = {F_V: 1, F_T: int(Placement.B), F_SRC: src, F_BASE_SEQ: base_seq,
             F_N: batch, F_RECS: recs, F_AUTH: b"\x00" * _AUTH_BYTES}
    name = "lean" if elide_redundant else "int-keys-only"
    return _sizes(name, len(_canon(frame)), sum(len(_canon(r)) for r in recs), batch)


def key_name_cost() -> tuple[int, int]:
    """(bytes spent on text key names, bytes the same count of integer keys would cost).

    The seven frame keys only — this is the quantity docs/01 §2a describes qualitatively.
    """
    text = sum(len(_canon(k)) for k in
               ("v", "t", "src", "base_seq", "n", "recs", "auth"))
    ints = sum(len(_canon(k)) for k in range(7))
    return text, ints


def smallest_record_bytes(*, elide_redundant: bool = True,
                          per_frame_chaining: bool = True) -> int:
    """s_min: the smallest record either profile can emit, for T6.

    Under per-frame chaining (docs/02 §9b, adopted on the LoRa arm) the 32 B chain link is carried
    once per frame rather than once per record, so a record is timestamp + payload — plus `src`
    and `seq` unless they are elided.
    """
    rec: dict[int, object] = {R_TS: 1_000, R_PL: {"a": 1}}
    if not per_frame_chaining:
        rec[R_PH] = b"\x11" * 32
    if not elide_redundant:
        rec[R_SRC] = 1
        rec[R_SEQ] = 0
    return len(_canon(rec))
