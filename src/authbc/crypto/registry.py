"""Signature-scheme registry (docs/03 §3 crypto/)."""

from __future__ import annotations

from authbc.crypto.base import SignatureScheme
from authbc.crypto.bls import BlsScheme
from authbc.crypto.ecdsa_p256 import EcdsaP256Scheme
from authbc.crypto.ed25519 import Ed25519Scheme

SCHEME_CLASSES: dict[str, type] = {
    "ecdsa_p256": EcdsaP256Scheme,
    "ed25519": Ed25519Scheme,
    "bls": BlsScheme,
}


def get_scheme(name: str) -> SignatureScheme:
    return SCHEME_CLASSES[name]()


def all_schemes() -> list[SignatureScheme]:
    return [cls() for cls in SCHEME_CLASSES.values()]
