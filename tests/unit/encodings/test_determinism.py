"""Cross-subprocess determinism gate (docs/06 §5, docs/03 §3).

Encode the SAME 1000-record stream in two independent Python subprocesses and compare the
SHA-256 of the concatenation. A mismatch means the encoding is not reproducible across
processes (e.g. hash-seed-dependent dict order, float creep) — a STOP condition, Law 3.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from authbc.encodings.registry import ENCODER_CLASSES, stream_digest

ENCODER_NAMES = list(ENCODER_CLASSES)

_SNIPPET = (
    "from authbc.encodings.registry import stream_digest;"
    "print(stream_digest({name!r}, {seed}, {n}))"
)


def _subprocess_digest(name: str, seed: int, n: int) -> str:
    # PYTHONHASHSEED randomized per process by default; if any encoder leaked dict-hash
    # ordering, the two processes would disagree.
    proc = subprocess.run(
        [sys.executable, "-c", _SNIPPET.format(name=name, seed=seed, n=n)],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.mark.parametrize("name", ENCODER_NAMES)
def test_determinism_across_two_subprocesses(name: str) -> None:
    seed, n = 123, 1000
    d1 = _subprocess_digest(name, seed, n)
    d2 = _subprocess_digest(name, seed, n)
    assert d1 == d2, f"{name}: cross-process digest mismatch ({d1} != {d2})"
    # in-process must agree with the subprocesses too
    assert stream_digest(name, seed, n) == d1
