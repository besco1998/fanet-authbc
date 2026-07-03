"""Uniform signature-scheme interface (docs/03 §3 crypto/, docs/06 §4).

Every scheme exposes ``keygen``/``sign``/``verify`` over raw ``bytes`` messages and raw
``bytes`` signatures so the benchmark harness (P1b) and placements (P3) treat schemes
uniformly; BLS additionally exposes ``aggregate``/``aggregate_verify``. ``sig_len`` is the
raw signature width used for byte accounting: Ed25519 64, ECDSA-P256 64 (fixed-width r‖s,
NOT the 70–72 B DER — docs/06 §4), BLS 96 (blspy AugScheme signature is a G2 point).

Spec gap (flagged for P1b / T4): docs/01 §1 & docs/02 assume a 48 B **min-signature** BLS
variant; blspy ships only the **min-pubkey** Chia scheme (pk 48 B in G1, sig 96 B in G2).
Aggregation semantics are identical; only the byte split differs. Recorded here so T2/T4
byte accounting uses the real 96 B rather than silently absorbing the difference.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SignatureScheme(Protocol):
    """Common surface for ECDSA-P256, Ed25519, and BLS12-381 (AugScheme)."""

    name: str
    sig_len: int

    def keygen(self, seed: bytes | None = None) -> tuple[Any, Any]:
        """Return ``(secret_key, public_key)`` objects (keygen is off the hot path)."""
        ...

    def sign(self, sk: Any, msg: bytes) -> bytes:
        """Sign ``msg`` → raw signature bytes (``sig_len`` wide)."""
        ...

    def verify(self, pk: Any, msg: bytes, sig: bytes) -> bool:
        """Return True iff ``sig`` is a valid signature of ``msg`` under ``pk``."""
        ...
