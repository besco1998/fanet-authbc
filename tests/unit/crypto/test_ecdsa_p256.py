"""ECDSA P-256/SHA-256 KATs (docs/06 §4): Wycheproof SigVer + fixed-width 64 B r‖s.

Wycheproof gives (pubkey wx/wy, msg, DER sig, result) verify vectors incl. many negatives;
we verify DER directly (verify_der) and assert the outcome. A separate test proves our public
API emits/consumes the fixed-width 64 B r‖s form, NOT the 70–72 B DER (docs/06 §4).
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


def test_signature_is_fixed_width_64_not_der() -> None:
    """Our sign() must emit exactly 64 B r‖s (a DER sig would be 70–72 B)."""
    sk, pk = SCHEME.keygen()
    sig = SCHEME.sign(sk, b"authbc-p1")
    assert len(sig) == SCHEME.sig_len == 64
    assert SCHEME.verify(pk, b"authbc-p1", sig) is True
    assert SCHEME.verify(pk, b"tampered", sig) is False
    # round-trip raw↔DER is lossless, and the DER form verifies through cryptography directly
    der = raw64_to_der(sig)
    assert 70 <= len(der) <= 72
    assert der_to_raw64(der) == sig
    assert SCHEME.verify_der(pk, b"authbc-p1", der) is True


def test_verify_rejects_wrong_length_sig() -> None:
    sk, pk = SCHEME.keygen()
    assert SCHEME.verify(pk, b"m", b"\x00" * 63) is False  # not 64 B → rejected, no raise
