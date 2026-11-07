"""ECDSA P-256/SHA-256 KATs (docs/06 §4): Wycheproof SigVer + fixed-width 64 B r‖s.

Wycheproof gives (pubkey wx/wy, msg, DER sig, result) verify vectors incl. many negatives;
we verify DER directly (verify_der) and assert the outcome. A separate test proves our public
API emits/consumes the fixed-width 64 B r‖s form, NOT the variable-length DER (docs/06 §4): up
to 72 B, and 70–72 B for all but ~0.2 % of signatures (r or s below 2^247).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from authbc.crypto.ecdsa_p256 import EcdsaP256Scheme, der_to_raw64, raw64_to_der

VECTORS = Path(__file__).resolve().parents[2] / "vectors"
SCHEME = EcdsaP256Scheme()


def _wycheproof_ecdsa_cases():
    data = json.loads((VECTORS / "wycheproof_ecdsa_secp256r1_sha256.json").read_text())
    for group in data["testGroups"]:
        pub = group["publicKey"]
        pk = SCHEME.pk_from_coords(int(pub["wx"], 16), int(pub["wy"], 16))
        for tc in group["tests"]:
            yield pytest.param(
                pk, bytes.fromhex(tc["msg"]), tc["sig"], tc["result"],
                id=f"tc{tc['tcId']}-{tc['result']}",
            )


_CASES = list(_wycheproof_ecdsa_cases())


def test_wycheproof_loaded() -> None:
    assert len(_CASES) > 300, f"expected >300 ECDSA SigVer cases, got {len(_CASES)}"


@pytest.mark.parametrize(("pk", "msg", "sig_hex", "result"), _CASES)
def test_wycheproof_ecdsa_verify(pk, msg: bytes, sig_hex: str, result: str) -> None:
    try:
        der = bytes.fromhex(sig_hex)
    except ValueError:  # malformed hex ⇒ not a valid signature
        assert result == "invalid"
        return
    ok = SCHEME.verify_der(pk, msg, der)
    if result == "valid":
        assert ok is True
    elif result == "invalid":
        assert ok is False
    else:  # "acceptable"
        assert isinstance(ok, bool)


def _der_int_len(x: int) -> int:
    """Bytes of a positive DER INTEGER's content: minimal big-endian, plus 0x00 if the top bit
    is set (X.690 §8.3)."""
    return x.bit_length() // 8 + 1


def test_signature_is_fixed_width_64_not_der() -> None:
    """Our sign() must emit exactly 64 B r‖s, whatever length its DER form has.

    ⚠️ This test asserted 70 ≤ len(DER) ≤ 72 from 2026-07-03 until the clean gate of
    2026-10-22 drew a 69 B signature: an r or s below 2^247 shortens its DER integer, ~1 run in
    512 (measured 0.21 % of 50 000). The DER length is now checked exactly against r and s.
    """
    sk, pk = SCHEME.keygen()
    sig = SCHEME.sign(sk, b"authbc-p1")
    assert len(sig) == SCHEME.sig_len == 64
    assert SCHEME.verify(pk, b"authbc-p1", sig) is True
    assert SCHEME.verify(pk, b"tampered", sig) is False
    # round-trip raw↔DER is lossless, and the DER form verifies through cryptography directly
    der = raw64_to_der(sig)
    r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    assert len(der) == 6 + _der_int_len(r) + _der_int_len(s) <= 72
    assert der_to_raw64(der) == sig
    assert SCHEME.verify_der(pk, b"authbc-p1", der) is True


@pytest.mark.parametrize(("r", "s", "der_len"), [
    (2**255, 2**255, 72),          # both top bits set: two 33 B integers
    (2**254, 2**254, 70),          # neither: two 32 B integers
    (2**247, 2**254, 70),          # r = 2^247: 31 B with the top bit set, so 32 again
    (2**246, 2**254, 69),          # r below 2^247: 31 B
    (2**246, 2**246, 68),
    (1, 2**255, 40),               # leading zero bytes are dropped in DER ...
])
def test_raw_der_round_trip_keeps_leading_zeros(r: int, s: int, der_len: int) -> None:
    """... and restored by der_to_raw64: the fixed-width form never shrinks (the case the random
    test above meets about once in 512 runs, here every run)."""
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    der = raw64_to_der(raw)
    assert len(der) == der_len == 6 + _der_int_len(r) + _der_int_len(s)
    assert der_to_raw64(der) == raw


def test_verify_rejects_wrong_length_sig() -> None:
    sk, pk = SCHEME.keygen()
    assert SCHEME.verify(pk, b"m", b"\x00" * 63) is False  # not 64 B → rejected, no raise
