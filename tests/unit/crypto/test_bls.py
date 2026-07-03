"""BLS12-381 AugScheme KATs (docs/06 §4,§5).

Vectors are Chia bls-signatures known-answer tests (vendored src/test.cpp, see tests/vectors
README): the "Augmented, aggregate of aggregates" vector (exact aggregate-sig hex) exercises
sign+aggregate+aggregate_verify; the IETF/Pyecc BasicScheme vector is an independent sign KAT.
Signatures are 96 B (G2); public keys 48 B (G1) — see crypto/base note on the 48-vs-96 B gap.
"""

from __future__ import annotations

from blspy import BasicSchemeMPL, PrivateKey

from authbc.crypto.bls import BlsScheme

SCHEME = BlsScheme()

# --- Chia test vector 2: Augmented, aggregate of aggregates (src/test.cpp ~L470-517) -------
_M1 = bytes([1, 2, 3, 40])
_M2 = bytes([5, 6, 70, 201])
_M3 = bytes([9, 10, 11, 12, 13])
_M4 = bytes([15, 63, 244, 92, 0, 1])
_SEED1 = bytes([2]) * 32
_SEED2 = bytes([3]) * 32
_EXPECTED_AGG = (
    "a1d5360dcb418d33b29b90b912b4accde535cf0e52caf467a005dc632d9f7af44b"
    "6c4e9acd4"
    "6eac218b28cdb07a3e3bc087df1cd1e3213aa4e11322a3ff3847bbba0b2fd19ddc"
    "25ca964871"
    "997b9bceeab37a4c2565876da19382ea32a962200"
)

# --- IETF/Pyecc BasicScheme sign vector (src/test.cpp ~L362-380) ----------------------------
_BASIC_SK = bytes([1]) * 32
_BASIC_MSG = bytes([3, 1, 4, 1, 5, 9])
_BASIC_SIG = (
    "96ba34fac33c7f129d602a0bc8a3d43f9abc014eceaab7359146b4b150e57b808"
    "645738f35671e9e10e0d862a30cab70074eb5831d13e6a5b162d01eebe687d016"
    "4adbd0a864370a7c222a2768d7704da254f1bf1823665bc2361f9dd8c00e99"
)


def test_aug_aggregate_kat_via_wrapper() -> None:
    """The full AugScheme aggregate KAT, driven through the BlsScheme wrapper."""
    sk1, pk1 = SCHEME.keygen(seed=_SEED1)
    sk2, pk2 = SCHEME.keygen(seed=_SEED2)
    sigs = [
        SCHEME.sign(sk1, _M1),
        SCHEME.sign(sk2, _M2),
        SCHEME.sign(sk2, _M1),
        SCHEME.sign(sk1, _M3),
        SCHEME.sign(sk1, _M1),
        SCHEME.sign(sk1, _M4),
    ]
    agg = SCHEME.aggregate(sigs)
    assert len(agg) == SCHEME.sig_len == 96
    assert agg.hex() == _EXPECTED_AGG  # known-answer aggregate signature
    pks = [pk1, pk2, pk2, pk1, pk1, pk1]
    msgs = [_M1, _M2, _M1, _M3, _M1, _M4]
    assert SCHEME.aggregate_verify(pks, msgs, agg) is True
    # tamper one message → aggregate_verify must fail
    assert SCHEME.aggregate_verify(pks, [_M2, _M2, _M1, _M3, _M1, _M4], agg) is False


def test_basic_scheme_sign_kat() -> None:
    """Independent sign KAT against BasicSchemeMPL (validates the blspy build)."""
    sig = BasicSchemeMPL.sign(PrivateKey.from_bytes(_BASIC_SK), _BASIC_MSG)
    assert bytes(sig).hex() == _BASIC_SIG


def test_sign_verify_roundtrip_and_reject() -> None:
    sk, pk = SCHEME.keygen(seed=bytes(range(32)))
    sig = SCHEME.sign(sk, b"authbc-p1")
    assert len(sig) == 96
    assert SCHEME.verify(pk, b"authbc-p1", sig) is True
    assert SCHEME.verify(pk, b"tampered", sig) is False


def test_single_signer_aggregate_verifies() -> None:
    sk, pk = SCHEME.keygen(seed=bytes([7]) * 32)
    s = SCHEME.sign(sk, b"solo")
    agg = SCHEME.aggregate([s])
    assert SCHEME.aggregate_verify([pk], [b"solo"], agg) is True
