"""Unit tests for the Bianchi DCF solver (docs/02 §6; guards docs/03 §3 models/).

Validation strategy (Law 4 TDD, Law 6 result-validation):
  * THREE frozen spot values the solver must reproduce, obtained by an INDEPENDENT route:
      - N=1: closed form τ = 2/(W+1), p_c = 0 (a single station never collides);
      - N=5, N=50: scipy `brentq` on the single combined equation
        f(τ) = τ_of_pc(pc_of_tau(τ, N)) − τ, bracketed on τ ∈ (0, 2/(W+1)].
    The brentq route is a genuinely different algorithm (bracketed bisection on the composed
    map) from the production damped substitution, so agreement pins the solver to ground truth.
  * Convergence must hold at N ∈ {5, 50, 100} (the undamped map oscillates at high N — the
    damping is what makes N=100 converge).
  * Invariants: τ, p_c, P_tr, P_s ∈ [0, 1]; throughput below the 6 Mb/s PHY ceiling.
  * S-vs-N shape: monotone non-increasing (gentle) — a dip-then-rise would mean a solver bug.
"""

from __future__ import annotations

import pytest
from scipy.optimize import brentq

from authbc.models import bianchi as b

L_TEST = 1000  # payload bytes used throughout (arbitrary; below MTU)


# --- independent reference solver (bracketed brentq on τ) ---------------------------------
def _brentq_reference(n: int) -> tuple[float, float]:
    """Independent fixed-point solve — different algorithm from production (Law 6 cross-check)."""
    if n == 1:
        return 2.0 / (b.W + 1), 0.0
    tau = brentq(
        lambda t: b.tau_of_pc(b.pc_of_tau(t, n)) - t,
        1e-15,
        2.0 / (b.W + 1),
        xtol=1e-16,
        rtol=8.9e-16,
    )
    return tau, b.pc_of_tau(tau, n)


# --- (b) THREE frozen hand/independent spot values ----------------------------------------
# Frozen literals produced by the independent brentq route above (and N=1 closed form).
SPOT_VALUES = {
    1: (0.117647058824, 0.000000000000),   # = 2/17 exactly, p_c=0
    5: (0.076148902235, 0.271536297612),
    50: (0.018290394373, 0.595266660858),
}


@pytest.mark.parametrize("n,tau_ref,pc_ref", [(n, *v) for n, v in SPOT_VALUES.items()])
def test_matches_frozen_spot_values(n: int, tau_ref: float, pc_ref: float) -> None:
    res = b.solve(n, L_TEST)
    assert res.tau == pytest.approx(tau_ref, abs=1e-9)
    assert res.p_c == pytest.approx(pc_ref, abs=1e-9)


def test_n1_is_exact_closed_form() -> None:
    """Single station: τ = 2/(W+1) and p_c = 0 EXACTLY (no floating slack)."""
    res = b.solve(1, L_TEST)
    assert res.tau == 2.0 / (b.W + 1)
    assert res.p_c == 0.0
    assert res.iterations == 1  # converges on the first step


def test_n2_tau_equals_pc_identity() -> None:
    """At N=2, p_c = 1−(1−τ)^1 = τ exactly by construction — a self-consistency anchor."""
    res = b.solve(2, L_TEST)
    assert res.p_c == pytest.approx(res.tau, abs=1e-9)


@pytest.mark.parametrize("n", [2, 5, 10, 50, 100])
def test_matches_independent_brentq(n: int) -> None:
    """Production damped solver == independent brentq route (Law 6 cross-check)."""
    tau_ref, pc_ref = _brentq_reference(n)
    res = b.solve(n, L_TEST)
    assert res.tau == pytest.approx(tau_ref, abs=1e-9)
    assert res.p_c == pytest.approx(pc_ref, abs=1e-9)


# --- (a) convergence at the required N (damping is load-bearing here) ----------------------
@pytest.mark.parametrize("n", [5, 50, 100])
def test_converges_at_required_n(n: int) -> None:
    res = b.solve(n, L_TEST)                      # must not raise ConvergenceError
    assert 1 <= res.iterations < 100_000
    assert b.fixed_point_residual(res) < 1e-9    # both DCF equations satisfied


# --- (c) invariants / sanity gates --------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 5, 10, 50, 100])
def test_probabilities_in_unit_interval(n: int) -> None:
    res = b.solve(n, L_TEST)
    for p in (res.tau, res.p_c, res.p_tr, res.p_s):
        assert 0.0 <= p <= 1.0


@pytest.mark.parametrize("n", [1, 2, 5, 10, 50, 100])
def test_throughput_below_phy_ceiling(n: int) -> None:
    res = b.solve(n, L_TEST)
    assert 0.0 < res.throughput_bps < b.R_BPS    # strictly below the 6 Mb/s PHY rate


def test_s_vs_n_shape_is_monotone_non_increasing() -> None:
    """S declines gently with contention; NO dip-then-rise (that would signal a solver bug)."""
    s = [b.solve(n, L_TEST).throughput_bps for n in range(2, 101)]
    diffs = [s[i + 1] - s[i] for i in range(len(s) - 1)]
    assert all(d <= 1e-3 for d in diffs)         # non-increasing (μbps tolerance)
    assert s[0] > s[-1]                           # and it does decline overall


# --- determinism & error paths ------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 5, 50])
def test_determinism(n: int) -> None:
    r1, r2 = b.solve(n, L_TEST), b.solve(n, L_TEST)
    assert (r1.tau, r1.p_c, r1.throughput_bps) == (r2.tau, r2.p_c, r2.throughput_bps)


def test_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        b.solve(0, L_TEST)
    with pytest.raises(ValueError):
        b.solve(-3, L_TEST)
    with pytest.raises(ValueError):
        b.solve(5, 0)


def test_non_convergence_raises_not_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """A starved iteration budget must RAISE, never return a half-solved point (Law 3)."""
    monkeypatch.setattr(b, "_MAX_ITER", 1)
    with pytest.raises(b.ConvergenceError):
        b.solve(50, L_TEST)


# --- airtime / T_fx reconciliation (docs/02 §6 "T_fx ≈ 123 µs") ---------------------------
def test_tfx_reconciles_with_doc_anchor() -> None:
    assert b.T_FX == pytest.approx(122e-6, abs=1e-9)     # exact term breakdown
    assert b.T_FX == pytest.approx(123e-6, abs=1.5e-6)   # within rounding of the doc anchor
    assert b.T_FX == pytest.approx(b.t_success(0) - b.DIFS)  # = successful exchange − DIFS idle


def test_t_air_is_affine_in_payload() -> None:
    for length in (0, 100, 1000):
        assert b.t_air(length) == pytest.approx(b.T_FX + 8.0 * length / b.R_BPS)


# --- exact 802.11a OFDM airtime (audit A1/A10) ---------------------------------------------
def test_ofdm_ppdu_matches_measured_ns3_durations() -> None:
    """Pinned to NS-3 3.41 measurements, not to a formula restated from the same source.

    Measured directly from PhyTxBegin/PhyTxEnd at 6 Mb/s: every 1400 B data frame occupied
    exactly 1 940 000 ns and every ACK exactly 44 000 ns.
    """
    assert b.ofdm_ppdu(b.mpdu_bytes(1400)) == pytest.approx(1940e-6, abs=1e-12)
    assert b.T_ACK_EXACT == pytest.approx(44e-6, abs=1e-12)
    assert b.mpdu_bytes(1400) == 1436  # 1400 payload + 8 LLC/SNAP + 24 MAC hdr + 4 FCS


def test_ofdm_quantisation_is_what_the_continuous_model_misses() -> None:
    """Records the size of the approximation the docs/02 §6 constants carry."""
    exact_data = b.ofdm_ppdu(b.mpdu_bytes(1400))
    cont_data = b.T_PHY + 8 * (1400 + b.MAC_OVH_BYTES) / b.R_BPS
    assert cont_data < exact_data
    assert (exact_data - cont_data) / exact_data == pytest.approx(0.0041, abs=5e-4)  # 0.41 %
    # The ACK is the bad one: 14 B needs 6 whole symbols, so continuous 8N/R is 12 % short.
    assert (b.T_ACK_EXACT - b.T_ACK) / b.T_ACK_EXACT == pytest.approx(
        0.121, abs=5e-3)


def test_exact_slot_times_match_measured_ns3_deferral_floors() -> None:
    """NS-3 gap floors: 94 µs after a success (SIFS+ACK+DIFS) and 43 µs = DIFS+slot after a
    collision, both measured from the busy-period trace at N=50 unicast."""
    data = b.ofdm_ppdu(b.mpdu_bytes(1400))
    assert b.t_success_exact(1400) - data == pytest.approx(94e-6, abs=1e-12)
    assert b.t_collision_exact(1400) - data == pytest.approx(b.DIFS, abs=1e-12)
    assert b.t_broadcast_exact(1400) == pytest.approx(1974e-6, abs=1e-12)


def test_solve_airtime_overrides_leave_the_default_model_untouched() -> None:
    """The override exists for the NS-3 comparison; omitting it must reproduce docs/02 §6."""
    base = b.solve(20, 1400.0)
    same = b.solve(20, 1400.0,
                         t_s=b.t_success(1400.0), t_c=b.t_collision(1400.0))
    assert same.throughput_bps == pytest.approx(base.throughput_bps, rel=1e-15)
    exact = b.solve(20, 1400.0,
                          t_s=b.t_success_exact(1400.0), t_c=b.t_collision_exact(1400.0))
    # Longer real slots ⇒ strictly lower predicted throughput, and τ/p_c are unaffected.
    assert exact.throughput_bps < base.throughput_bps
    assert exact.tau == pytest.approx(base.tau, rel=1e-15)
