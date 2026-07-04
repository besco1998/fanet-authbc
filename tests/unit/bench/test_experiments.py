"""Experiment-runner unit tests (docs/02 T1-T3). Small configs so they stay fast."""

from __future__ import annotations

import pytest

from authbc.bench.experiments import run_e1

_E1_SMALL = {
    "g": 64,
    "records_per_seed": 100,
    "seeds": [1, 2, 3],
    "encodings": ["json", "cbor", "msgpack", "delta"],
    "baselines": ["json", "cbor"],
}


def test_e1_phi_equals_formula_and_in_range() -> None:
    rows = run_e1(_E1_SMALL)
    assert len(rows) == 4
    for r in rows:
        assert r["phi_pct"] == pytest.approx(100 * r["g"] / (r["mean_bytes"] + r["g"]), abs=0.01)
        assert 0.0 < r["phi_pct"] < 100.0
        assert r["ci_lo"] <= r["mean_bytes"] <= r["ci_hi"]
        assert r["n_records"] == 300  # 3 seeds × 100


def test_e1_size_ordering_and_baselines() -> None:
    by = {r["encoding"]: r for r in run_e1(_E1_SMALL)}
    assert by["json"]["mean_bytes"] > by["cbor"]["mean_bytes"] > by["delta"]["mean_bytes"]
    assert by["json"]["baseline"] == 1 and by["cbor"]["baseline"] == 1
    assert by["delta"]["baseline"] == 0


def test_e1_deterministic() -> None:
    assert run_e1(_E1_SMALL) == run_e1(_E1_SMALL)
