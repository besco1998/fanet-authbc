"""Canonical CBOR wire format for placements A–D (docs/01 §1 placements, §4 wire format).

Frame := {v:1, t:PLACEMENT_ID, src:u16, base_seq:u32, n:u8, recs:[Record×n], auth:AuthBlock}
serialized with ``canonical_bytes`` (no indefinite-length items, deterministic key order).

**Signature input = ``covered_bytes`` ONLY** — the one boundary an attacker probes:
  A inline per-record   → each record's canonical bytes (a sig per record)
  B self-batch (1 signer)→ canonical bytes of the whole ``recs`` array (one sig)
  C cross-signer (BLS)   → each originator's record canonical bytes (aggregate over them)
  D block-level          → canonical bytes of the whole block's records (one sig, fragmented)

NOTE (e-axis, deferred to P3): ``recs`` here are canonical CBOR record maps — the hashing/
signing substrate. Carrying records in a different encoding e (JSON/msgpack/delta) is a P3
framer concern; the ledger's authenticated form is always this canonical map.
NOTE (BLS size): C's ``agg_sig`` is 96 B (blspy min-pubkey; Mohamed's P1 decision), not 48 B.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import cbor2

from authbc.crypto.bls import BlsScheme
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record, canonical_bytes

WIRE_VERSION = 1
_ED = Ed25519Scheme()
_BLS = BlsScheme()


class WireDecodeError(ValueError):
    """Any malformed frame — the single exception decode raises (subclasses ValueError)."""


class Placement(IntEnum):
    A = 0  # inline per-record
    B = 1  # self-batch, one signer
    C = 2  # cross-signer aggregate (BLS)
    D = 3  # block-level aggregate


@dataclass(frozen=True)
class Frame:
    t: Placement
    src: int
    base_seq: int
    recs: tuple[Record, ...]
    auth: Any  # per-placement AuthBlock (see module docstring)
    v: int = WIRE_VERSION

    @property
    def n(self) -> int:
        return len(self.recs)


# --------------------------------------------------------------------------- covered bytes
def covered_bytes(recs: tuple[Record, ...] | list[Record], placement: Placement):
    """The exact bytes a placement signs over (the #1 audit boundary).

    A/C → list of per-record canonical bytes; B/D → canonical bytes of the ``recs`` array.
    """
    if placement in (Placement.A, Placement.C):
        return [r.canonical() for r in recs]
    return canonical_bytes([r.to_map() for r in recs])


# --------------------------------------------------------------------------- encode / decode
def encode_frame(frame: Frame) -> bytes:
    if frame.n != len(frame.recs):  # invariant guard
        raise ValueError("frame.n must equal len(recs)")
    if not (0 <= frame.n <= 255):
        raise ValueError("n must fit u8")
    obj = {
        "v": frame.v,
        "t": int(frame.t),
        "src": frame.src,
        "base_seq": frame.base_seq,
        "n": frame.n,
        "recs": [r.to_map() for r in frame.recs],
        "auth": frame.auth,
    }
    return canonical_bytes(obj)


def _validate_auth_shape(t: Placement, auth: Any, n: int) -> None:
    """Reject structurally wrong AuthBlocks so verifiers never crash on fuzzed input."""
    b = (bytes, bytearray)
    if t is Placement.A:
        if not isinstance(auth, list) or len(auth) != n or not all(isinstance(s, b) for s in auth):
            raise ValueError("A auth must be a list of n byte strings")
    elif t is Placement.B:
        if not isinstance(auth, b):
            raise ValueError("B auth must be a byte string")
    elif t is Placement.C:
        if (not isinstance(auth, dict) or not isinstance(auth.get("agg"), b)
                or not isinstance(auth.get("signers"), list)
                or not all(isinstance(s, b) for s in auth["signers"])):
            raise ValueError("C auth must be {agg:bytes, signers:[bytes]}")
    else:  # D
        if (not isinstance(auth, dict) or not isinstance(auth.get("sig"), b)
                or not all(isinstance(auth.get(k), int) and not isinstance(auth.get(k), bool)
                           for k in ("block_id", "frag_idx", "frag_total"))):
            raise ValueError("D auth must be {sig:bytes, block_id/frag_idx/frag_total:int}")


def decode_frame(data: bytes) -> Frame:
    """Decode + structurally validate a frame. Any malformed input ⇒ ``WireDecodeError``."""
    try:
        obj = cbor2.loads(data)
        if not isinstance(obj, dict):
            raise ValueError("frame must be a CBOR map")
        if obj.get("v") != WIRE_VERSION:
            raise ValueError(f"unsupported wire version {obj.get('v')}")
        t = Placement(obj["t"])
        recs = tuple(Record.from_map(m) for m in obj["recs"])
        if obj["n"] != len(recs):
            raise ValueError("frame n does not match number of records")
        _validate_auth_shape(t, obj["auth"], len(recs))
        return Frame(t=t, src=obj["src"], base_seq=obj["base_seq"],
                     recs=recs, auth=obj["auth"], v=obj["v"])
    except WireDecodeError:
        raise
    except (cbor2.CBORDecodeError, KeyError, IndexError, TypeError, ValueError, OverflowError,
            AttributeError) as e:
        raise WireDecodeError(f"malformed frame: {e}") from e


# --------------------------------------------------------------------------- builders
def build_A(recs: list[Record], sk) -> Frame:
    """Inline per-record: the frame owner signs each of its own records (Ed25519)."""
    auth = [_ED.sign(sk, r.canonical()) for r in recs]
    return Frame(t=Placement.A, src=recs[0].src, base_seq=recs[0].seq, recs=tuple(recs), auth=auth)


def build_B(recs: list[Record], sk) -> Frame:
    """Self-batch: one signer, one Ed25519 signature over the canonical recs array."""
    auth = _ED.sign(sk, covered_bytes(recs, Placement.B))
    return Frame(t=Placement.B, src=recs[0].src, base_seq=recs[0].seq, recs=tuple(recs), auth=auth)


def build_C(recs: list[Record], signer_sks: list) -> Frame:
    """Cross-signer: each originator BLS-signs its own record; aggregate to one 96 B sig."""
    sigs = [_BLS.sign(sk, r.canonical()) for sk, r in zip(signer_sks, recs, strict=True)]
    pks = [_BLS.pk_to_bytes(sk.get_g1()) for sk in signer_sks]
    auth = {"agg": _BLS.aggregate(sigs), "signers": pks}
    return Frame(t=Placement.C, src=recs[0].src, base_seq=recs[0].seq, recs=tuple(recs), auth=auth)


def build_D(recs: list[Record], sk, *, block_id: int, frag_idx: int, frag_total: int) -> Frame:
    """Block-level: one Ed25519 sig over the whole block's records; this frame is a fragment."""
    auth = {
        "sig": _ED.sign(sk, covered_bytes(recs, Placement.D)),
        "block_id": block_id,
        "frag_idx": frag_idx,
        "frag_total": frag_total,
    }
    return Frame(t=Placement.D, src=recs[0].src, base_seq=recs[0].seq, recs=tuple(recs), auth=auth)


# --------------------------------------------------------------------------- verifiers
def verify_A(frame: Frame, pks: list) -> bool:
    if len(frame.auth) != frame.n:
        return False
    return all(
        _ED.verify(pk, r.canonical(), sig)
        for pk, r, sig in zip(pks, frame.recs, frame.auth, strict=True)
    )


def verify_B(frame: Frame, pk) -> bool:
    return _ED.verify(pk, covered_bytes(frame.recs, Placement.B), frame.auth)


def verify_C(frame: Frame) -> bool:
    try:
        pks = [_BLS.pk_from_bytes(b) for b in frame.auth["signers"]]
    except (ValueError, RuntimeError):  # malformed G1 pubkey bytes (e.g. fuzzed)
        return False
    if len(pks) != frame.n:
        return False
    msgs = covered_bytes(frame.recs, Placement.C)
    return _BLS.aggregate_verify(pks, msgs, frame.auth["agg"])


def verify_D(frame: Frame, pk) -> bool:
    """Verify a single reassembled block frame: sig over the block's records."""
    return _ED.verify(pk, covered_bytes(frame.recs, Placement.D), frame.auth["sig"])
