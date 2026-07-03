"""Ed25519 (RFC 8032) via ``cryptography`` (docs/06 §4).

Deterministic signatures (64 B). Batch verification is NOT exposed by ``cryptography``/PyNaCl,
so the project scope is **sequential** verify (docs/06 §4); true batch verify is ⚠️ D3.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class Ed25519Scheme:
    name = "ed25519"
    sig_len = 64

    def keygen(self, seed: bytes | None = None) -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        sk = (
            Ed25519PrivateKey.from_private_bytes(seed)
            if seed is not None
            else Ed25519PrivateKey.generate()
        )
        return sk, sk.public_key()

    def sign(self, sk: Ed25519PrivateKey, msg: bytes) -> bytes:
        return sk.sign(msg)

    def verify(self, pk: Ed25519PublicKey, msg: bytes, sig: bytes) -> bool:
        try:
            pk.verify(sig, msg)
            return True
        except (InvalidSignature, ValueError):  # ValueError: malformed / wrong-length sig
            return False

    # --- helpers for KATs / serialization -------------------------------------------------
    @staticmethod
    def sk_from_bytes(raw: bytes) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(raw)

    @staticmethod
    def pk_from_bytes(raw: bytes) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(raw)

    @staticmethod
    def pk_to_bytes(pk: Ed25519PublicKey) -> bytes:
        return pk.public_bytes_raw()
