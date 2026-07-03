"""Uniform scheme API contract across ECDSA-P256, Ed25519, BLS (docs/03 §3 crypto/)."""

from __future__ import annotations

import pytest

from authbc.crypto.registry import SCHEME_CLASSES, all_schemes, get_scheme

_MSG = b"authbc uniform api"


@pytest.mark.parametrize("name", list(SCHEME_CLASSES))
def test_uniform_sign_verify(name: str) -> None:
    scheme = get_scheme(name)
    sk, pk = scheme.keygen(seed=bytes(range(32)))
    sig = scheme.sign(sk, _MSG)
    assert len(sig) == scheme.sig_len
    assert scheme.verify(pk, _MSG, sig) is True
    assert scheme.verify(pk, _MSG + b"!", sig) is False


def test_registry_complete() -> None:
    schemes = all_schemes()
    assert {s.name for s in schemes} == {"ecdsa_p256", "ed25519", "bls"}
    assert {s.sig_len for s in schemes} == {64, 96}  # ed/ecdsa 64, bls 96
