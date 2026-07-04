"""Golden end-to-end ledger scenario — the regression anchor for P3+ (P2 step 5, Law 6).

3 UAVs, direct handoff (no channel yet), fixed seeds. The EXPECTED final counters are stated
in advance and asserted EXACTLY; determinism is asserted by re-running. If a count ever
changes, that is a real behaviour change to investigate — never edit the expectation to match.

EXPECTED (by construction below):
  stored = 30  (3 UAVs × 10 valid signed records)
  replay = 5   (re-ingest of UAV 1's first 5 records)
  equivocation = 1  (a second (src=2, seq=0) with a different payload)
  tampered = 1  (a fresh UAV-3 record ingested under the wrong public key)
"""

from __future__ import annotations

from authbc.bench import telemgen
from authbc.crypto.ed25519 import Ed25519Scheme
from authbc.ledger.chain import Chain
from authbc.ledger.store import Store

_TELEMETRY = ("lat", "lon", "alt", "vel_x", "vel_y", "vel_z", "battery", "mode")
_ED = Ed25519Scheme()
SRCS = (1, 2, 3)
PER_UAV = 10


def _pl(seed: int, i: int) -> dict[str, int]:
    r = telemgen.samples(seed=seed, n=i + 1)[i]
    return {k: getattr(r, k) for k in _TELEMETRY}


def run_scenario() -> Store:
    keys = {src: _ED.keygen(seed=bytes([src]) * 32) for src in SRCS}
    chains = {src: Chain(src=src) for src in SRCS}
    store = Store()

    # 30 valid signed records
    for src in SRCS:
        sk, pk = keys[src]
        for i in range(PER_UAV):
            rec = chains[src].append(_pl(src, i), ts=100 + i)
            store.ingest(rec, scheme=_ED, pk=pk, sig=_ED.sign(sk, rec.canonical()))

    # 5 replays: re-ingest UAV 1's first five records
    sk1, pk1 = keys[1]
    for rec in chains[1].records()[:5]:
        store.ingest(rec, scheme=_ED, pk=pk1, sig=_ED.sign(sk1, rec.canonical()))

    # 1 equivocation: a second (src=2, seq=0) with a different payload
    sk2, pk2 = keys[2]
    evil = Chain(src=2).append(_pl(999, 0), ts=777)  # same (2,0), different hash
    store.ingest(evil, scheme=_ED, pk=pk2, sig=_ED.sign(sk2, evil.canonical()))

    # 1 tampered: a fresh UAV-3 record ingested under the WRONG key
    sk3, _ = keys[3]
    _, wrong_pk = _ED.keygen(seed=b"\xaa" * 32)
    rec = chains[3].append(_pl(3, PER_UAV), ts=200)
    store.ingest(rec, scheme=_ED, pk=wrong_pk, sig=_ED.sign(sk3, rec.canonical()))

    return store


def test_golden_exact_counters() -> None:
    store = run_scenario()
    assert store.counters == {"stored": 30, "replay": 5, "equivocation": 1, "tampered": 1}
    assert len(store.equivocations) == 1
    assert len(store.records()) == 30


def test_golden_is_deterministic() -> None:
    assert run_scenario().counters == run_scenario().counters
