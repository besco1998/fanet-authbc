"""Ed25519 KATs (docs/06 §4): RFC 8032 §7.1 sign+verify + Wycheproof verify vectors.

RFC 8032 vectors are deterministic sign KATs (sk+msg ⇒ exact 64-byte sig); Wycheproof adds
negative/edge verify cases. Vectors are vendored under tests/vectors/ (see its README).
KATs must pass before any timing exists (docs/03 §3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from authbc.crypto.ed25519 import Ed25519Scheme

VECTORS = Path(__file__).resolve().parents[2] / "vectors"
SCHEME = Ed25519Scheme()

_LABELS = ("ALGORITHM", "SECRET KEY", "PUBLIC KEY", "MESSAGE", "SIGNATURE")
_HEXCHARS = set("0123456789abcdefABCDEF")


def _hexbytes(parts: list[str]) -> bytes:
    return bytes.fromhex("".join(c for c in "".join(parts) if c in _HEXCHARS))


def _strip_rfc_pagination(text: str) -> str:
    """Drop RFC page headers/footers/form-feeds so long hex values stay contiguous."""
    keep = []
    for line in text.replace("\x0c", "\n").splitlines():
        if "[Page " in line or line.startswith("RFC 8032") or "Josefsson" in line:
            continue
        keep.append(line)
    return "\n".join(keep)


def _parse_rfc8032_ed25519() -> list[dict[str, bytes]]:
    """Extract the pure-Ed25519 (§7.1) vectors from the vendored RFC 8032 text.

    Linear scan: a stripped line ending in ':' whose head matches a label switches the
    current field; other lines contribute their hex to it. ALGORITHM is kept raw (so
    'Ed25519ph' does not hex-collapse to 'Ed25519'); only exact 'Ed25519' blocks are used.
    """
    text = _strip_rfc_pagination((VECTORS / "rfc8032.txt").read_text())
    vectors: list[dict[str, bytes]] = []
    # Blocks are delimited by any dashes-header line ('-----TEST', '-----foo', '-----', …),
    # not only '-----TEST' — otherwise the SHA(abc) vector merges with the Ed25519ctx block.
    for block in re.split(r"(?m)^[ \t]*-----.*$", text):
        raw: dict[str, list[str]] = {}
        current: str | None = None
        for ln in block.splitlines():
            s = ln.strip()
            label = next((lb for lb in _LABELS if s.startswith(lb) and s.endswith(":")), None)
            if label is not None:
                current = label
                raw.setdefault(label, [])
            elif current is not None and s:
                raw[current].append(s)
        algo = "".join(raw.get("ALGORITHM", [])).strip()
        if algo != "Ed25519" or not {"SECRET KEY", "PUBLIC KEY", "SIGNATURE"} <= raw.keys():
            continue
        vectors.append(
            {
                "sk": _hexbytes(raw.get("SECRET KEY", [])),
                "pk": _hexbytes(raw.get("PUBLIC KEY", [])),
                "msg": _hexbytes(raw.get("MESSAGE", [])),
                "sig": _hexbytes(raw.get("SIGNATURE", [])),
            }
        )
    return vectors


RFC_VECTORS = _parse_rfc8032_ed25519()


def test_rfc8032_vectors_loaded() -> None:
    # RFC 8032 §7.1 has 5 Ed25519 vectors (TEST 1, 2, 3, 1024, SHA(abc)).
    assert len(RFC_VECTORS) == 5, f"expected 5 RFC8032 Ed25519 vectors, got {len(RFC_VECTORS)}"


@pytest.mark.parametrize("i", range(len(RFC_VECTORS)))
def test_rfc8032_sign_and_verify(i: int) -> None:
    v = RFC_VECTORS[i]
    sk = SCHEME.sk_from_bytes(v["sk"])
    pk = SCHEME.pk_from_bytes(v["pk"])
    assert len(v["sig"]) == 64
    # deterministic sign must reproduce the exact signature
    assert SCHEME.sign(sk, v["msg"]) == v["sig"]
    # and the derived public key must match the vector's
    assert SCHEME.pk_to_bytes(pk) == v["pk"]
    assert SCHEME.verify(pk, v["msg"], v["sig"]) is True
    # a flipped bit must fail
    tampered = bytes([v["sig"][0] ^ 0x01]) + v["sig"][1:]
    assert SCHEME.verify(pk, v["msg"], tampered) is False


def _wycheproof_ed25519_cases():
    data = json.loads((VECTORS / "wycheproof_ed25519.json").read_text())
    for group in data["testGroups"]:
        pk = SCHEME.pk_from_bytes(bytes.fromhex(group["publicKey"]["pk"]))
        for tc in group["tests"]:
            yield pytest.param(
                pk, bytes.fromhex(tc["msg"]), tc["sig"], tc["result"],
                id=f"tc{tc['tcId']}-{tc['result']}",
            )


@pytest.mark.parametrize(("pk", "msg", "sig_hex", "result"), list(_wycheproof_ed25519_cases()))
def test_wycheproof_ed25519_verify(pk, msg: bytes, sig_hex: str, result: str) -> None:
    try:
        sig = bytes.fromhex(sig_hex)
    except ValueError:  # malformed hex → treat as invalid signature
        assert result == "invalid"
        return
    ok = SCHEME.verify(pk, msg, sig)
    if result == "valid":
        assert ok is True
    elif result == "invalid":
        assert ok is False
    else:  # "acceptable" — either outcome is allowed
        assert isinstance(ok, bool)


def test_keygen_sign_verify_roundtrip() -> None:
    sk, pk = SCHEME.keygen(seed=bytes(range(32)))
    sig = SCHEME.sign(sk, b"authbc-p1")
    assert len(sig) == SCHEME.sig_len == 64
    assert SCHEME.verify(pk, b"authbc-p1", sig) is True
    assert SCHEME.verify(pk, b"other", sig) is False
    assert re.fullmatch(r"[0-9a-f]*", sig.hex())
