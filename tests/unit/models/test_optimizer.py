"""Unit tests for the co-design optimizer (docs/03 §3, docs/02 T2/T3/T5).

Two layers:
  * A 5-point TOY with hand-picked (bytes, energy, V) proving the Pareto front is EXACT — this
    pins the domination logic independently of any physical model (Law 6 "provably correct").
  * Integration on a small (e,σ,placement,b) grid proving the constraints actually filter and
    the returned front is internally non-dominated and a subset of the feasible pool.
"""

from __future__ import annotations

import pytest

from authbc.models.energy import Placement
from authbc.models.optimizer import (
    Candidate,
    Constraints,
    EncodingSpec,
    OptimizeResult,
    Platform,
    SchemeSpec,
    bytes_per_record,
    frame_auth_bytes,
    n_frames,
    pareto_front,
    solve,
    verifiability,
)


# --- 5-point hand-checkable Pareto toy ----------------------------------------------------
def _toy(bytes_pr: float, energy: float, v: float, tag: str) -> Candidate:
    """A Candidate carrying only the three objectives that matter for domination."""
    return Candidate(
        encoding=tag, scheme="σ", placement=Placement.B, batch=1, n_frames=1,
        bytes_per_record=bytes_pr, energy_j=energy, verifiability=v,
        verify_time_s=0.0, latency_s=0.0, meets_latency=True,
    )


def test_pareto_front_toy_is_exact() -> None:
    """Objectives: min bytes, min energy, max V. Hand-derived front = {P1, P2, P3}."""
    p1 = _toy(100, 5.0, 0.95, "P1")   # non-dominated
    p2 = _toy(120, 4.0, 0.95, "P2")   # non-dominated (cheapest energy)
    p3 = _toy(110, 4.5, 0.99, "P3")   # non-dominated (highest V)
    p4 = _toy(150, 6.0, 0.90, "P4")   # dominated by P1 (worse on all three)
    p5 = _toy(100, 5.0, 0.90, "P5")   # dominated by P1 (equal bytes+energy, lower V)

    front = pareto_front([p1, p2, p3, p4, p5])
    tags = {c.encoding for c in front}
    assert tags == {"P1", "P2", "P3"}
    assert "P4" not in tags and "P5" not in tags
    assert len(front) == 3


def test_pareto_front_order_preserved_and_singleton() -> None:
    assert pareto_front([]) == []
    solo = _toy(10, 1.0, 0.99, "solo")
    assert pareto_front([solo]) == [solo]


def test_equal_metric_points_both_kept() -> None:
    """Two candidates with identical objectives dominate neither — both stay (no silent merge)."""
    a = _toy(100, 5.0, 0.95, "A")
    b = _toy(100, 5.0, 0.95, "B")
    assert len(pareto_front([a, b])) == 2


# --- model-helper unit checks -------------------------------------------------------------
def test_n_frames_and_verifiability() -> None:
    # b·s+g_a+H_f = 10·130+64+40 = 1404 ≤ 1500 ⇒ 1 frame; 20·130+64+40 = 2704 ⇒ 2 frames.
    assert n_frames(10, 130, 64, 40, 1500) == 1
    assert n_frames(20, 130, 64, 40, 1500) == 2
    assert verifiability(Placement.B, 1, 0.02) == pytest.approx(0.98)
    assert verifiability(Placement.D, 3, 0.02) == pytest.approx(0.98**3)


def test_bytes_model_A_does_not_amortize_signature() -> None:
    # A carries b·g_a (naive baseline); B amortizes one g_a over b.
    assert frame_auth_bytes(Placement.A, 10, 64) == 640
    assert frame_auth_bytes(Placement.B, 10, 64) == 64
    a = bytes_per_record(Placement.A, 10, 130, 64, 40, 1)   # s + g_a + H_f/b
    b = bytes_per_record(Placement.B, 10, 130, 64, 40, 1)   # s + (g_a+H_f)/b
    assert a == pytest.approx(130 + 64 + 40 / 10)
    assert b == pytest.approx(130 + (64 + 40) / 10)
    assert a > b   # batching (B) beats inline (A) on bytes — the thesis motivation (T2)


# --- integration on a small grid ----------------------------------------------------------
ENCODINGS = [
    EncodingSpec("cbor", record_bytes=130, t_enc_s=50e-6),
    EncodingSpec("delta", record_bytes=42, t_enc_s=70e-6),
]
SCHEMES = [
    SchemeSpec("ed25519", auth_bytes=64, t_sign_s=60e-6, t_verify_s=100e-6),
    SchemeSpec("bls", auth_bytes=48, t_sign_s=70e-6, t_verify_s=1_500e-6,
               t_agg_build_s=200e-6, t_agg_verify_s=1_600e-6),
]
PLACEMENTS = [Placement.A, Placement.B, Placement.C, Placement.D]
BATCHES = [1, 5, 10, 20]
PLATFORM = Platform(p_cpu_w=2.0, p_radio_w=0.8, frame_hdr_bytes=40, mtu_bytes=1500)
CON = Constraints(epsilon=0.05, p_loss=0.02, lam=200, d_max_s=0.250)


def test_solve_returns_valid_pareto_set() -> None:
    res = solve(ENCODINGS, SCHEMES, PLACEMENTS, BATCHES, PLATFORM, CON)
    assert isinstance(res, OptimizeResult)
    assert len(res.pareto) >= 1
    # every feasible candidate obeys the HARD constraints
    for c in res.feasible:
        assert c.verifiability >= 1.0 - CON.epsilon
        assert c.verify_time_s * CON.lam <= 1.0
    # the Pareto set is a subset of the feasible pool and is internally non-dominated
    feas_ids = {id(c) for c in res.feasible}
    assert all(id(c) in feas_ids for c in res.pareto)
    assert pareto_front(res.pareto) == res.pareto
    # C with the non-aggregate ed25519 scheme is skipped, not counted feasible/infeasible
    assert res.skipped == len(ENCODINGS) * len(BATCHES)  # ed25519 × C over all e,b


def test_solve_is_deterministic() -> None:
    a = solve(ENCODINGS, SCHEMES, PLACEMENTS, BATCHES, PLATFORM, CON)
    b = solve(ENCODINGS, SCHEMES, PLACEMENTS, BATCHES, PLATFORM, CON)

    def key(r: OptimizeResult) -> list[tuple[str, str, str, int]]:
        return sorted((c.encoding, c.scheme, c.placement.value, c.batch) for c in r.pareto)

    assert key(a) == key(b)


def test_mtu_constraint_filters_oversize_single_frame() -> None:
    """A single frame that exceeds the MTU is infeasible (T2 feasibility b ≤ b_max)."""
    big = [EncodingSpec("json", record_bytes=358, t_enc_s=80e-6)]
    res = solve(big, [SCHEMES[0]], [Placement.B], [20], PLATFORM, CON)  # 20·358+64+40=7264 > 1500
    assert res.feasible == []
    assert res.infeasible == 1


def test_verify_throughput_constraint_filters_high_rate() -> None:
    """At Λ=60000 rec/s, ed25519 B needs b≥10 to keep up (t_vf/b·Λ ≤ 1); b=5 is filtered."""
    fast = Constraints(epsilon=0.05, p_loss=0.02, lam=60_000, d_max_s=0.250)
    res = solve([ENCODINGS[0]], [SCHEMES[0]], [Placement.B], [5, 10], PLATFORM, fast)
    kept = {c.batch for c in res.feasible}
    assert 5 not in kept       # 100µs/5 · 60000 = 1.2 > 1  → infeasible
    assert 10 in kept          # 100µs/10 · 60000 = 0.6 ≤ 1 → feasible


def test_verifiability_constraint_filters_over_aggregated_D() -> None:
    """With ε<p-margin, a block D spanning ≥3 frames drops below V≥1−ε (T3 forces frame-level)."""
    # cbor s=130: b=35 ⇒ 35·130+64+40=4654 ⇒ n=⌈4654/1500⌉=4 frames ⇒ V=0.98^4≈0.922 < 0.95.
    res = solve([ENCODINGS[0]], [SCHEMES[0]], [Placement.D], [35], PLATFORM, CON)
    assert res.feasible == []
    assert res.infeasible == 1


def test_grid_guard_rejects_oversize_and_empty() -> None:
    many_batches = list(range(1, 4000))
    with pytest.raises(ValueError):
        solve(ENCODINGS, SCHEMES, PLACEMENTS, many_batches, PLATFORM, CON)
    with pytest.raises(ValueError):
        solve([], SCHEMES, PLACEMENTS, BATCHES, PLATFORM, CON)


# --- freshness is a real constraint and a real objective (audit F10) ------------------------
def _fresh_setup():
    """A grid whose byte-optimal batch is far outside the freshness bound."""
    encs = [EncodingSpec(name="delta", record_bytes=45.0, t_enc_s=48e-6)]
    schemes = [SchemeSpec(name="ed25519", auth_bytes=64, t_sign_s=88e-6, t_verify_s=260e-6)]
    plat = Platform(p_cpu_w=0.634, p_radio_w=0.218, frame_hdr_bytes=40, mtu_bytes=1500)
    return encs, schemes, plat


def test_freshness_is_enforced_not_merely_annotated() -> None:
    """docs/02 §7: "enforce D ≤ D_max in the optimizer". A stale config is INADMISSIBLE.

    Regression guard for F10: the byte-optimal batch b=31 sits at 1552 ms, 6.2× over the 250 ms
    bound, and was previously returned as the optimum with the violation computed and discarded.
    """
    encs, schemes, plat = _fresh_setup()
    batches = [1, 2, 4, 5, 10, 31]
    con = Constraints(epsilon=0.05, p_loss=0.05, lam=20, d_max_s=0.250)
    res = solve(encs, schemes, [Placement.B], batches, plat, con)

    assert res.feasible, "some batch must remain feasible"
    assert all(c.latency_s <= con.d_max_s for c in res.feasible)
    assert all(c.meets_latency for c in res.feasible)
    assert max(c.batch for c in res.feasible) == 4, "b≤Λ·D_max ⇒ 4 at Λ=20, D_max=250 ms"
    assert 31 not in {c.batch for c in res.feasible}


def test_relaxing_d_max_readmits_the_large_batches() -> None:
    """The constraint must bind on D_max itself, not on some unrelated limit."""
    encs, schemes, plat = _fresh_setup()
    batches = [1, 4, 31]
    loose = solve(encs, schemes, [Placement.B], batches, plat,
                  Constraints(epsilon=0.05, p_loss=0.05, lam=20, d_max_s=10.0))
    assert 31 in {c.batch for c in loose.feasible}


def test_freshness_is_a_pareto_objective_so_small_batches_survive() -> None:
    """With freshness as a 4th objective, a fresher-but-bytier config is NOT dominated.

    Under the old 3-objective set (bytes, energy, V) the largest feasible batch dominated every
    smaller one outright, hiding the bytes↔freshness trade-off that co-design is about.
    """
    encs, schemes, plat = _fresh_setup()
    con = Constraints(epsilon=0.05, p_loss=0.05, lam=20, d_max_s=10.0)
    res = solve(encs, schemes, [Placement.B], [1, 2, 4, 8, 16, 31], plat, con)
    pareto_batches = sorted(c.batch for c in res.pareto)
    assert len(pareto_batches) > 1, "the frontier must expose the trade-off, not collapse to one"
    assert 1 in pareto_batches, "b=1 is the freshest point and cannot be dominated"
    assert 31 in pareto_batches, "b=31 is the byte-optimal point and cannot be dominated"
    # and freshness must be monotone in batch, which is what makes the trade-off real
    by_b = {c.batch: c.latency_s for c in res.feasible}
    assert [by_b[b] for b in sorted(by_b)] == sorted(by_b[b] for b in sorted(by_b))
