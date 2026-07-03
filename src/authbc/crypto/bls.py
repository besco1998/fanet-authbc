"""BLS12-381 via blspy ``AugSchemeMPL`` (docs/06 §4, §5).

AugScheme prepends the signer's public key to the message, so distinct-message aggregation is
rogue-key safe without proofs of possession (docs/06 §4). blspy is the Chia min-pubkey scheme:
public key = G1 (48 B), signature = G2 (96 B) — see the ``base`` module note on the 48-vs-96 B
spec gap (flagged for T4).
"""

from __future__ import annotations

import os

from blspy import AugSchemeMPL, G1Element, G2Element, PrivateKey

_MIN_SEED = 32  # AugSchemeMPL.key_gen requires >= 32 bytes of seed


class BlsScheme:
    name = "bls"
    sig_len = 96  # G2 point (blspy AugScheme); pk (G1) is 48 B

    def keygen(self, seed: bytes | None = None) -> tuple[PrivateKey, G1Element]:
        if seed is None:
            seed = os.urandom(_MIN_SEED)
        if len(seed) < _MIN_SEED:
            raise ValueError(f"BLS seed must be >= {_MIN_SEED} bytes")
        sk = AugSchemeMPL.key_gen(seed)
        return sk, sk.get_g1()

    def sign(self, sk: PrivateKey, msg: bytes) -> bytes:
        return bytes(AugSchemeMPL.sign(sk, msg))

    def verify(self, pk: G1Element, msg: bytes, sig: bytes) -> bool:
        try:
            return AugSchemeMPL.verify(pk, msg, G2Element.from_bytes(sig))
        except (ValueError, RuntimeError):
            return False

    def aggregate(self, sigs: list[bytes]) -> bytes:
        """Aggregate raw G2 signatures into one 96 B signature."""
        return bytes(AugSchemeMPL.aggregate([G2Element.from_bytes(s) for s in sigs]))

    def aggregate_verify(self, pks: list[G1Element], msgs: list[bytes], agg_sig: bytes) -> bool:
        try:
            return AugSchemeMPL.aggregate_verify(pks, msgs, G2Element.from_bytes(agg_sig))
        except (ValueError, RuntimeError):
            return False

    @staticmethod
    def pk_from_bytes(raw: bytes) -> G1Element:
        return G1Element.from_bytes(raw)

    @staticmethod
    def pk_to_bytes(pk: G1Element) -> bytes:
        return bytes(pk)
