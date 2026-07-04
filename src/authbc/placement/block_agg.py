"""Placement D — block-level aggregate (one sig over b records spanning n>1 frames), docs/01 §1.

A block of b records is signed ONCE over the whole block's canonical bytes, then fragmented into
several frames that each carry the same block signature + a ``{block_id, frag_idx, frag_total}``
header. A fragment alone does NOT verify (its records are only a slice); only the REASSEMBLED
block does. All-or-nothing under loss: losing any one fragment kills the whole block (T3).

The reassembly buffer holds fragments per ``block_id`` with a **500 ms sim-time timeout**;
a block that never completes is discarded and counted (``discarded_partial``).
"""

from __future__ import annotations

from collections.abc import Sequence

from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.record import Record
from authbc.placement.framer import Framer
from authbc.placement.wire import Frame, Placement, covered_bytes, verify_D

_ED = Ed25519Scheme()
REASSEMBLY_TIMEOUT_MS = 500


class BlockAggFramer(Framer):
    def __init__(self, sk) -> None:
        self._sk = sk

    def pack(self, records: Sequence[Record], *, b: int) -> list[Frame]:
        """Sign the whole block once; split into ⌈len/b⌉ fragment frames of ≤ b records each."""
        recs = list(records)
        block_sig = _ED.sign(self._sk, covered_bytes(recs, Placement.D))  # over the WHOLE block
        block_id = recs[0].seq  # deterministic per (src, first seq)
        total = max(1, -(-len(recs) // b))
        frames: list[Frame] = []
        for idx in range(total):
            chunk = recs[idx * b : (idx + 1) * b]
            frames.append(Frame(
                t=Placement.D, src=recs[0].src, base_seq=recs[0].seq, recs=tuple(chunk),
                auth={"sig": block_sig, "block_id": block_id, "frag_idx": idx, "frag_total": total},
            ))
        return frames

    def unpack(self, frame: Frame, *, pk) -> tuple[list[Record], list[bool]]:
        """Verify a REASSEMBLED block frame (recs = the full block)."""
        ok = verify_D(frame, pk)
        return list(frame.recs), [ok] * frame.n


class BlockReassembler:
    """Collects D fragments per block_id; returns the reassembled frame once complete."""

    def __init__(self, timeout_ms: int = REASSEMBLY_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms
        self._buf: dict[int, dict] = {}
        self.discarded_partial = 0

    def offer(self, frame: Frame, now_ms: int) -> Frame | None:
        """Add a fragment; return the reassembled block frame if this completed it, else None."""
        a = frame.auth
        idx, total = a["frag_idx"], a["frag_total"]
        key = (frame.src, a["block_id"])  # block_id is unique per src, not globally
        entry = self._buf.setdefault(key, {"frags": {}, "first_ts": now_ms, "total": total})
        entry["frags"][idx] = frame
        if len(entry["frags"]) == entry["total"]:
            ordered = [entry["frags"][i] for i in range(entry["total"])]
            recs = tuple(r for f in ordered for r in f.recs)
            del self._buf[key]
            return Frame(t=Placement.D, src=ordered[0].src, base_seq=ordered[0].base_seq,
                         recs=recs, auth=ordered[0].auth)
        return None

    def sweep(self, now_ms: int) -> int:
        """Discard (and count) blocks that have not completed within the timeout."""
        expired = [k for k, e in self._buf.items() if now_ms - e["first_ts"] > self.timeout_ms]
        for k in expired:
            del self._buf[k]
            self.discarded_partial += 1
        return len(expired)
