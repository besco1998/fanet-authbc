"""D7 — the chain-hash term in the energy model (docs/audits/model_provenance.md F14).

`models.energy.per_record` had no hashing term until 2026-07-29, yet every record is SHA-256'd to
form `prev_hash` — that IS the ledger. The omission was half of F14's measured ~32 % energy gap.

These tests pin the term, its magnitude, and the two properties that make it different from every
other cost in the model: it is charged TWICE per record (sender extends the chain, receiver
verifies it) and it does NOT amortize over the batch.
"""

from __future__ import annotations

import pytest

from authbc.models.energy import EnergyConfig, Measured, Placement, per_record

# MEASURED on authbc-pi4a with the P1 harness (scheme=sha256, op=chain_link), 45 B input =
# prev_hash 32 B + delta body 13 B. Median 2745.5 ns, CI [2745.1, 2745.5].
T_HASH_ARM_S = 2745.5e-9
P_CPU_W = 0.634


def _measured(t_hash_s: float) -> Measured:
    return Measured(t_enc_s=47.759e-6, t_sign_s=88.120e-6, t_verify_s=259.499e-6,
                    p_cpu_w=P_CPU_W, p_radio_w=0.218, t_hash_s=t_hash_s)


def _cfg(batch: int) -> EnergyConfig:
    return EnergyConfig(placement=Placement.B, batch=batch, record_bytes=45.0,
                        auth_bytes=64, frame_hdr_bytes=44, n_frames=1)


def test_the_hash_term_is_charged_twice_per_record() -> None:
    """Sender hashes to extend the chain; receiver re-hashes to verify it."""
    with_hash = per_record(_cfg(4), _measured(T_HASH_ARM_S))
    without = per_record(_cfg(4), _measured(0.0))
    assert with_hash - without == pytest.approx(2.0 * T_HASH_ARM_S * P_CPU_W, rel=1e-9)
    assert (with_hash - without) * 1e6 == pytest.approx(3.481, abs=0.001)   # µJ/record


def test_the_hash_term_does_not_amortize_over_the_batch() -> None:
    """Unlike the signature, the chain is per-record by construction.

    This is why the omission hurt batched configurations proportionally more in *time* — the
    property that produced the (later retracted) inference about the direction of F14's bias.
    """
    deltas = []
    for b in (1, 2, 4, 8, 31):
        deltas.append(per_record(_cfg(b), _measured(T_HASH_ARM_S))
                      - per_record(_cfg(b), _measured(0.0)))
    assert all(d == pytest.approx(deltas[0], rel=1e-9) for d in deltas), (
        "the chain-hash cost per record must be independent of b")


def test_zero_default_reproduces_the_f14_omission() -> None:
    """`t_hash_s` defaults to 0.0 for backward compatibility — which silently restores the bug.

    Pinned so the danger stays visible: anything that computes energy must set it from a measured
    per-platform figure, not accept the default.
    """
    assert Measured(t_enc_s=1e-6, t_sign_s=1e-6, t_verify_s=1e-6,
                    p_cpu_w=1.0, p_radio_w=1.0).t_hash_s == 0.0


def test_negative_hash_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="t_hash_s"):
        _measured(-1e-9)


def test_e5_energy_moved_by_exactly_the_hash_term() -> None:
    """E5's optimized row went 112.0818 → 115.5631 µJ/record when D7 landed.

    Bytes are untouched: the hash is payload the chain requires, not authentication overhead.
    """
    assert 112.0818 + 2.0 * T_HASH_ARM_S * P_CPU_W * 1e6 == pytest.approx(115.5631, abs=0.001)
