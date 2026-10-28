"""After the mission: merge every UAV's ledger and audit it (revision A16; predictions/A16.md).

The paper calls the receiver's store a "blockchain-style ledger", but nothing ever checked one
ledger against another. This is that step. After a mission each UAV uploads

* its own frames — what it signed, in order (`Upload.own`), and
* the neighbours' frames it accepted and kept (`LeanReceiver._frames`, exposed as
  `Upload.held`), with any equivocation evidence it caught (`Upload.evidence`).

`audit` then, with nothing but the public keys:

1. checks each sender's own chain — every frame verifies alone (`verified_records`), sequence
   numbers are contiguous, and each record's link is the hash of the one before it;
2. checks every frame a neighbour held against the sender's own chain — a receiver that lost
   a frame stored the next one without being able to check its link; here it is checked;
3. collects every pair of valid frames of one sender that give one sequence number two records
   (`proves_equivocation`), and every held frame that does not verify under its sender's key
   (a forgery a receiver could not have accepted — evidence the holder altered its upload);
4. publishes a report whose Merkle root covers every audited frame, signed by the auditor.

The audit is deterministic: the same uploads give the same report and root.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from authbc.ledger.record import GENESIS_PH, Record
from authbc.placement.session_v2 import proves_equivocation, verified_records
from authbc.placement.wire_v2 import frame_src


@dataclass(frozen=True)
class Upload:
    """What one UAV hands in after a mission."""

    uav: int
    own: tuple[bytes, ...]                       # its own frames, in the order it sent them
    held: tuple[bytes, ...] = ()                 # neighbours' frames it accepted and kept
    evidence: tuple[tuple[bytes, bytes], ...] = ()   # equivocation pairs it caught


@dataclass
class Report:
    gaps: list[tuple[int, int, int]] = field(default_factory=list)        # (src, after, next)
    broken_links: list[tuple[int, int]] = field(default_factory=list)     # (src, seq)
    bad_own_frames: list[tuple[int, int]] = field(default_factory=list)   # (uav, index)
    mismatches: list[tuple[int, int, int]] = field(default_factory=list)  # (holder, src, seq)
    forgeries: list[tuple[int, int]] = field(default_factory=list)        # (holder, index)
    equivocations: list[tuple[int, int]] = field(default_factory=list)    # (src, seq)
    frames_audited: int = 0
    merkle_root: bytes = b""
    signature: bytes = b""

    def clean(self) -> bool:
        return not (self.gaps or self.broken_links or self.bad_own_frames or self.mismatches
                    or self.forgeries or self.equivocations)


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    """SHA-256 Merkle root; a leaf is hashed with a 0x00 prefix, a node with 0x01 (RFC 6962
    domain separation), and an odd node is carried up unchanged."""
    level = [hashlib.sha256(b"\x00" + leaf).digest() for leaf in leaves]
    if not level:
        return hashlib.sha256(b"").digest()
    while len(level) > 1:
        nxt = [hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest()
               for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def _chain(src: int, frames: Sequence[bytes], pk: Any, report: Report, uav: int
           ) -> dict[int, tuple[Record, bytes]]:
    """A sender's own chain, checked; returns each record, with its frame, by sequence number."""
    records: dict[int, tuple[Record, bytes]] = {}
    last: Record | None = None
    for index, data in enumerate(frames):
        recs = verified_records(data, pk)
        if recs is None:
            report.bad_own_frames.append((uav, index))
            continue
        for rec in recs:
            if last is not None:
                if rec.seq != last.seq + 1:
                    report.gaps.append((src, last.seq, rec.seq))
                elif rec.prev_hash != last.record_hash():
                    report.broken_links.append((src, rec.seq))
            elif rec.seq == 0 and rec.prev_hash != GENESIS_PH:
                report.broken_links.append((src, rec.seq))
            records[rec.seq] = (rec, data)
            last = rec
    return records


def audit(uploads: Sequence[Upload], keys: Mapping[int, Any], auditor: Any = None) -> Report:
    """Merge and check every upload. `auditor`, if given, is (scheme, secret key)."""
    report = Report()
    chains = {u.uav: _chain(u.uav, u.own, keys[u.uav], report, u.uav) for u in uploads}
    leaves: list[bytes] = [f for u in uploads for f in u.own]
    seen_pairs: set[tuple[int, int]] = set()
    for u in uploads:
        for index, data in enumerate(u.held):
            src = frame_src(data)
            recs = verified_records(data, keys[src]) if src in keys else None
            if recs is None:
                report.forgeries.append((u.uav, index))
                continue
            leaves.append(data)
            mine = chains.get(src, {})
            for rec in recs:
                signed = mine.get(rec.seq)
                if signed is not None and signed[0].canonical() != rec.canonical():
                    report.mismatches.append((u.uav, src, rec.seq))
                    if ((src, rec.seq) not in seen_pairs
                            and proves_equivocation(signed[1], data, keys[src])):
                        seen_pairs.add((src, rec.seq))
                        report.equivocations.append((src, rec.seq))
        for held, offered in u.evidence:
            src = frame_src(held)
            if proves_equivocation(held, offered, keys[src]):
                for rec in verified_records(offered, keys[src]) or ():
                    if (src, rec.seq) not in seen_pairs:
                        seen_pairs.add((src, rec.seq))
                        report.equivocations.append((src, rec.seq))
    report.frames_audited = len(leaves)
    report.merkle_root = merkle_root(sorted(leaves))
    if auditor is not None:
        scheme, sk = auditor
        report.signature = scheme.sign(sk, report.merkle_root + _summary(report))
    return report


def _summary(report: Report) -> bytes:
    """The findings, in a fixed byte form, so that the auditor's signature covers them too."""
    parts = (report.gaps, report.broken_links, report.bad_own_frames, report.mismatches,
             report.forgeries, report.equivocations)
    return repr(tuple(sorted(p) for p in parts)).encode()
