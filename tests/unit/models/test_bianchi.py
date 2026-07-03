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
