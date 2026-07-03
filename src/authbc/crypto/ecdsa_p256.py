"""ECDSA P-256 / SHA-256 via ``cryptography`` (docs/06 §4).

Signatures are byte-accounted as **fixed-width 64 B r‖s** (each of r, s is 32 B big-endian),
NOT the variable 70–72 B DER that ``cryptography`` emits/consumes — the DER form would inflate
the on-air byte counts (T1) and is not what a real deployment would put on the wire. We convert
raw↔DER at the boundary via ``decode_dss_signature``/``encode_dss_signature``.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

_CURVE = ec.SECP256R1()
_HASH = ec.ECDSA(hashes.SHA256())
_COORD_BYTES = 32  # P-256: r, s < n each fit in 32 bytes


def der_to_raw64(der: bytes) -> bytes:
    """DER (r,s) → fixed-width 64 B r‖s."""
    r, s = decode_dss_signature(der)
    return r.to_bytes(_COORD_BYTES, "big") + s.to_bytes(_COORD_BYTES, "big")


def raw64_to_der(raw: bytes) -> bytes:
    """Fixed-width 64 B r‖s → DER (r,s)."""
    if len(raw) != 64:
        raise ValueError(f"expected 64-byte r||s, got {len(raw)}")
    r = int.from_bytes(raw[:_COORD_BYTES], "big")
    s = int.from_bytes(raw[_COORD_BYTES:], "big")
    return encode_dss_signature(r, s)


class EcdsaP256Scheme:
    name = "ecdsa_p256"
    sig_len = 64

    def keygen(
        self, seed: bytes | None = None
    ) -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        # ``cryptography`` has no seeded EC keygen; seed is accepted for API uniformity but
        # unused (keygen is excluded from the measured hot path, docs/04 §1).
        sk = ec.generate_private_key(_CURVE)
        return sk, sk.public_key()

    def sign(self, sk: ec.EllipticCurvePrivateKey, msg: bytes) -> bytes:
        return der_to_raw64(sk.sign(msg, _HASH))

    def verify(self, pk: ec.EllipticCurvePublicKey, msg: bytes, sig: bytes) -> bool:
        try:
            pk.verify(raw64_to_der(sig), msg, _HASH)
            return True
        except (InvalidSignature, ValueError):
            return False

    def verify_der(self, pk: ec.EllipticCurvePublicKey, msg: bytes, der: bytes) -> bool:
        """Verify a DER-encoded signature (used by the Wycheproof SigVer KAT)."""
        try:
            pk.verify(der, msg, _HASH)
            return True
        except (InvalidSignature, ValueError):
            return False

    @staticmethod
    def pk_from_coords(x: int, y: int) -> ec.EllipticCurvePublicKey:
        return ec.EllipticCurvePublicNumbers(x, y, _CURVE).public_key()
