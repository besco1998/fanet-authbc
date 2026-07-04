"""Record verification helpers (docs/01 §1 security model, docs/03 §3 ledger/).

A record's authenticity is its signature over its **canonical bytes** (the same bytes that
chain into ``prev_hash``); its ordering/non-equivocation is the hash chain. These helpers are
pure; the stateful replay/equivocation logic lives in ``store``.
"""

from __future__ import annotations

from typing import Any

from authbc.ledger.record import Record


def signature_ok(scheme: Any, pk: Any, rec: Record, sig: bytes) -> bool:
    """True iff ``sig`` verifies over the record's canonical bytes under ``pk`` (docs/01 §4)."""
    return bool(scheme.verify(pk, rec.canonical(), sig))


def link_ok(rec: Record, expected_prev_hash: bytes) -> bool:
    """True iff the record chains to ``expected_prev_hash`` (its predecessor's hash)."""
    return rec.prev_hash == expected_prev_hash
