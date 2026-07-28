"""Unit tests for the per-record energy model (docs/02 §7).

Every expected energy is recomputed here by INDEPENDENT plain arithmetic (not by calling the
module's internal helpers) and asserted against per_record() — the Law-6 hand-check. Airtime is
recomputed here from raw 802.11a constants, quantised to whole OFDM symbols (decision D9).
"""

from __future__ import annotations

import math

import pytest

from authbc.models import bianchi
from authbc.models.energy import EnergyConfig, Measured, Placement, frame_bytes, per_record


def _air(nbytes: float) -> float:
    """Independent broadcast airtime, from raw constants: PPDU(L + 36 B) + DIFS.

    BROADCAST, never unicast (audit F2): the telemetry substrate never ACKs, so no SIFS + ACK.
    Quantised to whole 4 µs OFDM symbols (decision D9) — airtime is a step function of L, so
    there is no fixed part plus linear term to shortcut with.
    """
    symbols = math.ceil((16 + 8.0 * (nbytes + 36) + 6) / 24)
    return 20e-6 + symbols * 4e-6 + 34e-6


# A representative measured set (synthetic but order-of-magnitude realistic, docs/04 §1):
M = Measured(
    t_enc_s=50e-6,
    t_sign_s=60e-6,
    t_verify_s=100e-6,
    p_cpu_w=2.0,
    p_radio_w=0.8,
    t_agg_build_s=200e-6,
    t_agg_verify_s=1_500e-6,
)


def test_placement_B_matches_hand_calc() -> None:
    """B (self-batch): E = P_c(t_enc + t_sg/b + t_vf/b) + P_r·T_air(frame)/b."""
    cfg = EnergyConfig(Placement.B, batch=10, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    fb = 10 * 130 + 64 + 40  # 1404 B
    assert frame_bytes(cfg) == fb
    e_cpu = 2.0 * (50e-6 + 60e-6 / 10 + 100e-6 / 10)
    e_radio = 0.8 * _air(fb) / 10
    assert per_record(cfg, M) == pytest.approx(e_cpu + e_radio, rel=0, abs=1e-15)


def test_placement_A_is_unbatched() -> None:
    """A (inline): b=1, one sign + one verify per record, frame carries a single record."""
    cfg = EnergyConfig(Placement.A, batch=1, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    fb = 1 * 130 + 64 + 40  # 234 B
    e_cpu = 2.0 * (50e-6 + 60e-6 + 100e-6)
    e_radio = 0.8 * _air(fb) / 1
    assert per_record(cfg, M) == pytest.approx(e_cpu + e_radio, abs=1e-15)


def test_placement_C_uses_aggregate_terms() -> None:
    """C (relay): sign = t_sg + t_ag/b, verify = t_av/b (originators sign, receiver agg-verify)."""
    cfg = EnergyConfig(Placement.C, batch=10, record_bytes=130, auth_bytes=48, frame_hdr_bytes=40)
    fb = 10 * 130 + 48 + 40  # 1388 B
    e_cpu = 2.0 * (50e-6 + (60e-6 + 200e-6 / 10) + 1_500e-6 / 10)
    e_radio = 0.8 * _air(fb) / 10
    assert per_record(cfg, M) == pytest.approx(e_cpu + e_radio, abs=1e-15)


def test_placement_D_amortizes_like_block() -> None:
    """D (block): one signature over b records, verify once — same amortization shape as B."""
    cfg = EnergyConfig(Placement.D, batch=35, record_bytes=42, auth_bytes=64, frame_hdr_bytes=40)
    fb = 35 * 42 + 64 + 40
    e_cpu = 2.0 * (50e-6 + 60e-6 / 35 + 100e-6 / 35)
    e_radio = 0.8 * _air(fb) / 35
    assert per_record(cfg, M) == pytest.approx(e_cpu + e_radio, abs=1e-15)


def test_placement_D_multiframe_airtime_hand_calc() -> None:
    """D over n frames: radio counts n PPDUs + one header per frame (not one giant frame)."""
    cfg = EnergyConfig(
        Placement.D, batch=35, record_bytes=42, auth_bytes=64, frame_hdr_bytes=40, n_frames=3
    )
    n = 3
    air = n * _air((35 * 42 + 64 + n * 40) / n)
    e_cpu = 2.0 * (50e-6 + 60e-6 / 35 + 100e-6 / 35)
    e_radio = 0.8 * air / 35
    assert per_record(cfg, M) == pytest.approx(e_cpu + e_radio, abs=1e-15)


def test_n_frames_one_reduces_to_single_frame_form() -> None:
    """n_frames=1 must be byte-identical to the single-frame §7 broadcast airtime."""
    cfg = EnergyConfig(Placement.B, batch=10, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    from authbc.models.energy import radio_airtime_s

    assert radio_airtime_s(cfg) == pytest.approx(_air(frame_bytes(cfg)), abs=1e-18)
    assert radio_airtime_s(cfg) == pytest.approx(bianchi.t_broadcast(frame_bytes(cfg)), abs=1e-18)


def test_batching_reduces_energy_monotonically() -> None:
    """Sanity (T2 shape): larger self-batch b ⇒ lower energy/record (auth cost amortizes)."""
    energies = [
        per_record(
            EnergyConfig(Placement.B, batch=b, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40),
            M,
        )
        for b in (1, 2, 5, 10, 20)
    ]
    assert all(energies[i] > energies[i + 1] for i in range(len(energies) - 1))


def test_energy_order_of_magnitude() -> None:
    """Sanity gate: sub-millijoule per record at these µs-scale ops and sub-watt radio."""
    cfg = EnergyConfig(Placement.B, batch=10, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    e = per_record(cfg, M)
    assert 1e-6 < e < 1e-2  # between 1 µJ and 10 mJ


def test_placement_C_without_aggregate_params_raises() -> None:
    """We never fake aggregate timings (Law 2/7): C without them is an error, not a guess."""
    bare = Measured(t_enc_s=50e-6, t_sign_s=60e-6, t_verify_s=100e-6, p_cpu_w=2.0, p_radio_w=0.8)
    cfg = EnergyConfig(Placement.C, batch=10, record_bytes=130, auth_bytes=48, frame_hdr_bytes=40)
    with pytest.raises(ValueError):
        per_record(cfg, bare)


def test_placement_C_without_agg_verify_raises() -> None:
    """Aggregate BUILD present but aggregate VERIFY missing is still an error (Law 2/7)."""
    half = Measured(
        t_enc_s=50e-6, t_sign_s=60e-6, t_verify_s=100e-6, p_cpu_w=2.0, p_radio_w=0.8,
        t_agg_build_s=200e-6,  # but t_agg_verify_s left None
    )
    cfg = EnergyConfig(Placement.C, batch=10, record_bytes=130, auth_bytes=48, frame_hdr_bytes=40)
    with pytest.raises(ValueError):
        per_record(cfg, half)


def test_config_and_measured_reject_bad_inputs() -> None:
    with pytest.raises(ValueError):
        EnergyConfig(Placement.B, batch=0, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    with pytest.raises(ValueError):
        EnergyConfig(Placement.B, batch=5, record_bytes=-1, auth_bytes=64, frame_hdr_bytes=40)
    with pytest.raises(ValueError):
        EnergyConfig(Placement.D, batch=5, record_bytes=42, auth_bytes=64, frame_hdr_bytes=40,
                     n_frames=0)
    with pytest.raises(ValueError):
        Measured(t_enc_s=-1, t_sign_s=60e-6, t_verify_s=100e-6, p_cpu_w=2.0, p_radio_w=0.8)
    with pytest.raises(ValueError):
        Measured(t_enc_s=50e-6, t_sign_s=60e-6, t_verify_s=100e-6, p_cpu_w=0.0, p_radio_w=0.8)


def test_determinism() -> None:
    cfg = EnergyConfig(Placement.B, batch=8, record_bytes=130, auth_bytes=64, frame_hdr_bytes=40)
    assert per_record(cfg, M) == per_record(cfg, M)


# --- freshness / queueing (docs/02 §7, audit P3) --------------------------------------------
def test_queueing_delay_matches_the_mm1_formula_by_hand() -> None:
    """W_q = ρ·T_air/(1−ρ) with ρ = Λ·T_air/b — recomputed here from raw arithmetic."""
    from authbc.models.energy import queueing_delay_s, radio_airtime_s

    cfg = EnergyConfig(Placement.B, batch=4, record_bytes=45.0, auth_bytes=64, frame_hdr_bytes=40)
    lam = 20.0
    t_air = _air(4 * 45.0 + 64 + 40)
    assert radio_airtime_s(cfg) == pytest.approx(t_air, abs=1e-18)
    rho = lam * t_air / 4
    assert queueing_delay_s(cfg, lam) == pytest.approx(rho * t_air / (1 - rho), abs=1e-18)


def test_freshness_is_fill_plus_flight_plus_queueing() -> None:
    from authbc.models.energy import freshness_delay_s, queueing_delay_s, radio_airtime_s

    cfg = EnergyConfig(Placement.B, batch=4, record_bytes=45.0, auth_bytes=64, frame_hdr_bytes=40)
    lam = 20.0
    assert freshness_delay_s(cfg, lam) == pytest.approx(
        4 / lam + radio_airtime_s(cfg) + queueing_delay_s(cfg, lam), abs=1e-18)
    # fill time dominates utterly at telemetry rates — this is why b ≲ Λ·D_max holds
    assert (4 / lam) / freshness_delay_s(cfg, lam) > 0.99


def test_a_saturated_frame_queue_is_infinitely_stale_not_merely_slow() -> None:
    """ρ ≥ 1 means the station cannot clear its own telemetry; any bound must reject it."""
    from authbc.models.energy import freshness_delay_s, queueing_delay_s

    cfg = EnergyConfig(Placement.B, batch=1, record_bytes=1400.0, auth_bytes=64,
                       frame_hdr_bytes=40)
    assert queueing_delay_s(cfg, lam=1e6) == float("inf")
    assert freshness_delay_s(cfg, lam=1e6) == float("inf")


def test_queueing_rejects_a_nonpositive_arrival_rate() -> None:
    from authbc.models.energy import queueing_delay_s

    cfg = EnergyConfig(Placement.B, batch=4, record_bytes=45.0, auth_bytes=64, frame_hdr_bytes=40)
    with pytest.raises(ValueError, match="lam must be > 0"):
        queueing_delay_s(cfg, lam=0.0)
