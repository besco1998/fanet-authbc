"""Unit tests for the Ed25519↔BLS crossover math (docs/02 T4).

All expected values are recomputed by hand from the P1 measured medians (ns) pasted below, so a
regression in the crossover changes a number a human checked. The headline: κ* (break-even
P_r/P_c) sits far above the physically plausible band ⇒ Ed25519 wins on 802.11 for all ρ, b.
"""

from __future__ import annotations

import math

import pytest

from authbc.models import crossover as x

# --- P1 measured medians (results/raw/p1_crypto.csv), nanoseconds -------------------------
NS = 1e-9
T_VF_ED = 94_972.4 * NS
T_VF_BLS = 1_016_469.0 * NS
T_AV = {  # bls agg_verify median per batch b (ns → s)
    2: 1_469_257.0 * NS,
    4: 1_931_029.0 * NS,
    8: 3_445_443.0 * NS,
    16: 5_912_399.0 * NS,
    32: 11_392_958.5 * NS,
}


def test_delta_bytes_hand_values() -> None:
    assert x.delta_relay_bytes(32) == pytest.approx(64 - 48 / 32)   # 62.5
    assert x.delta_relay_bytes(2) == pytest.approx(40.0)
    assert x.delta_own_bytes(32) == pytest.approx(16 / 32)          # 0.5
    # H_a>0 only shrinks BLS's saving (helps Ed25519):
    assert x.delta_relay_bytes(16, h_a=16) < x.delta_relay_bytes(16, h_a=0)


def test_radio_saving_hand_value() -> None:
    assert x.radio_saving_s(62.5) == pytest.approx(8 * 62.5 / 6e6)  # 83.333 µs


def test_extra_cpu_relay_hand_value() -> None:
    dt = x.extra_cpu_relay_s(T_AV[32], 32, T_VF_ED)
    assert dt == pytest.approx((11_392_958.5 / 32 - 94_972.4) * NS)  # 261.06 µs


def test_kappa_star_relay_b32_matches_prestated_expectation() -> None:
    """The most BLS-favourable point (ρ=1, b=32): κ*≈3.13 — still ≫ plausible 0.5."""
    dt = x.extra_cpu_relay_s(T_AV[32], 32, T_VF_ED)
    dr = x.radio_saving_s(x.delta_relay_bytes(32))
    kstar = x.kappa_star(dt, dr)
    assert kstar == pytest.approx(3.133, abs=0.01)
    assert x.winner_for_plausible_powers(kstar) == "ed25519"


def test_kappa_star_own_is_independent_of_b() -> None:
    """Own-record κ* has b cancel out (≈43.2 for every b) — Ed25519 dominates self-batch."""
    vals = []
    for b in (2, 8, 32):
        dt = x.extra_cpu_own_s(T_VF_BLS, T_VF_ED, b)
        dr = x.radio_saving_s(x.delta_own_bytes(b))
        vals.append(x.kappa_star(dt, dr))
    assert vals[0] == pytest.approx(vals[1]) == pytest.approx(vals[2])
    assert vals[0] == pytest.approx(43.2, abs=0.1)


@pytest.mark.parametrize("b", [2, 4, 8, 16, 32])
def test_relay_crossover_always_favours_ed25519_on_80211(b: int) -> None:
    dt = x.extra_cpu_relay_s(T_AV[b], b, T_VF_ED)
    dr = x.radio_saving_s(x.delta_relay_bytes(b))
    assert x.kappa_star(dt, dr) > x.PLAUSIBLE_KAPPA_MAX     # break-even needs implausible P_r/P_c


def test_mix_interpolates_and_validates() -> None:
    assert x.mix(0.0, 10.0, 2.0) == 10.0
    assert x.mix(1.0, 10.0, 2.0) == 2.0
    assert x.mix(0.25, 10.0, 2.0) == pytest.approx(8.0)
    with pytest.raises(ValueError):
        x.mix(1.5, 1.0, 2.0)


def test_kappa_star_degenerate_cases() -> None:
    assert x.kappa_star(1e-4, 0.0) == math.inf        # BLS saves no bytes, costs CPU → never wins
    assert x.kappa_star(-1e-4, 0.0) == -math.inf      # (BLS cheaper CPU AND no radio diff)
    assert x.kappa_star(-1e-4, 1e-5) == 0.0           # BLS cheaper on both → wins for all powers
    assert x.winner_for_plausible_powers(0.0) == "bls"
    assert x.winner_for_plausible_powers(0.3) == "regime-dependent"
    assert x.winner_for_plausible_powers(3.13) == "ed25519"


def test_verify_throughput_wall_at_high_lambda() -> None:
    """At Λ=2000, BLS agg-verify is throughput-infeasible at b=2 but feasible from b=4."""
    assert not x.verify_throughput_ok(T_AV[2] / 2, 2000)   # 734.6µs·2000 = 1.47 > 1
    assert x.verify_throughput_ok(T_AV[4] / 4, 2000)       # 482.8µs·2000 = 0.97 ≤ 1
    assert x.verify_throughput_ok(T_VF_ED, 2000)           # Ed25519 always keeps up
