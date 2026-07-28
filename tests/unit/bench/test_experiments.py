"""Experiment-runner unit tests (docs/02 T1-T3). Small configs so they stay fast."""

from __future__ import annotations

import pytest

from authbc.bench.experiments import load_config, run_e1, run_e2, run_e3, run_e5

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


_E2_SMALL = {
    "mtu_values": [1500],
    "placements": ["A", "B"],
    "encodings": ["cbor", "delta"],
    "g_a": 64,
    "size_seed": 1,
    "size_n": 2000,
    "lam": 20,          # T2a: needed to compute the freshness ceiling ⌊Λ·D_max⌋
    "d_max_s": 0.250,
}


def test_e2_amplification_matches_formula_at_mtu_1500() -> None:
    """T2's algebra is correct AT the MTU limit — which is what A_formula describes."""
    for x in run_e2(_E2_SMALL):
        if x["is_bmax"] and x["placement"] == "B":
            gap = abs(x["A_at_b"] - x["A_formula"]) / x["A_formula"]
            assert gap < 0.05, f"{x['encoding']}: A gap {gap:.3f} > 5% at M=1500"


def test_e2_records_that_the_mtu_limit_is_unreachable_at_1500() -> None:
    """T2a: at M=1500 freshness caps the batch first, so the REALISED amplification is 1.

    Guards the distinction the frozen data now carries: A_formula is the MTU-limit value and
    stays 1.0745; A_effective is what compression is actually worth and is 1.0.
    """
    rows = [x for x in run_e2(_E2_SMALL) if x["placement"] == "B" and x["is_bmax"]]
    assert rows
    for x in rows:
        assert x["binds"] == "freshness"
        assert x["A_effective"] == 1.0
        assert x["A_formula"] > 1.0            # the formula still says otherwise
        assert x["b_ceiling"] < x["b_max"]     # …because the MTU batch is unreachable


def test_e2_low_mtu_stays_mtu_limited_so_amplification_survives() -> None:
    """The other side of the T2a boundary: a LoRa-like MTU is capped by size, not freshness."""
    cfg = {**_E2_SMALL, "mtu_values": [256]}
    rows = [x for x in run_e2(cfg) if x["placement"] == "B" and x["is_bmax"]]
    assert rows
    for x in rows:
        assert x["binds"] == "mtu"
        assert x["A_effective"] == x["A_formula"] > 1.5
        assert x["b_ceiling"] == x["b_max"]


def test_e2_phi_decreases_with_b_for_self_batch() -> None:
    rows = sorted((x for x in run_e2(_E2_SMALL) if x["placement"] == "B"
                   and x["encoding"] == "cbor"), key=lambda r: r["b"])
    phis = [x["phi_overhead_pct"] for x in rows]
    assert all(phis[i] > phis[i + 1] for i in range(len(phis) - 1))  # batching drives φ down


def test_e2_inline_A_sig_never_amortizes() -> None:
    rows = sorted((x for x in run_e2(_E2_SMALL) if x["placement"] == "A"
                   and x["encoding"] == "cbor"), key=lambda r: r["b"])
    per = [x["bytes_per_rec"] for x in rows]
    # only the frame header H_f/b amortizes; the per-record 64 B sig does not ⇒ small change
    assert per[0] - per[-1] < 40


_E3_SMALL = {
    "encoding": "cbor",
    "g_a": 64,
    "p_values": [0.05],
    "b_values": [1, 10, 20, 30, 40],
    "seeds": [1, 2, 3, 4, 5],
    "blocks_per_seed": 400,
    "base_seed": 777,
    "size_seed": 1,
    "size_n": 2000,
}


def test_e3_VB_flat_at_1_minus_p() -> None:
    """V_B is independent of b (loss-local) and tracks 1−p."""
    b_rows = [x for x in run_e3(_E3_SMALL) if x["placement"] == "B"]
    for x in b_rows:
        assert 0.0 <= x["V_meas"] <= 1.0
        assert abs(x["V_meas"] - 0.95) < 0.02  # ~1−p regardless of b
        assert x["V_theory"] == pytest.approx(0.95)


def test_e3_VD_drops_when_block_spans_multiple_frames() -> None:
    d_rows = {x["b"]: x for x in run_e3(_E3_SMALL) if x["placement"] == "D"}
    assert d_rows[1]["n_frames"] == 1 and d_rows[1]["V_meas"] == pytest.approx(0.95, abs=0.02)
    assert d_rows[40]["n_frames"] >= 2  # block spans >1 frame
    assert d_rows[40]["V_theory"] == pytest.approx(0.95 ** d_rows[40]["n_frames"], abs=1e-6)
    assert d_rows[40]["V_meas"] < d_rows[1]["V_meas"] - 0.02  # V_D strictly lower


def test_e3_B_pareto_dominates_D_above_threshold() -> None:
    """At b where D spans >1 frame, B has higher V (D's tiny byte saving is dominated)."""
    rows = {(x["placement"], x["b"]): x for x in run_e3(_E3_SMALL)}
    b, d = rows[("B", 40)], rows[("D", 40)]
    assert b["V_meas"] > d["V_meas"]  # B dominates on verifiability above V=(1−p)^2


def test_e3_deterministic() -> None:
    assert run_e3(_E3_SMALL) == run_e3(_E3_SMALL)



def _e5():
    return run_e5(load_config("e5"))


def test_e5_success_criterion_met() -> None:
    rows = _e5()
    sc = next(r for r in rows if r["role"] == "SUCCESS_CRITERION")
    assert sc["pass"] == 1
    assert sc["auth_cut_pct"] >= 40.0
    opt = next(r for r in rows if r["role"] == "optimized")
    assert opt["V"] >= 0.95
    assert opt["bytes_per_rec"] >= opt["s"]


def test_e5_a_cbor_baseline_and_optimized_placement() -> None:
    rows = _e5()
    acbor = next(r for r in rows if r["role"] == "A+CBOR")
    assert acbor["auth_overhead_bytes"] == pytest.approx(104.0)  # g_a 64 + H_f 40, inline b=1
    assert acbor["placement"] == "A" and acbor["encoding"] == "cbor"
    opt = next(r for r in rows if r["role"] == "optimized")
    assert opt["placement"] == "B"  # self-batch amortizes the signature (T5)


def test_e5_deterministic() -> None:
    assert _e5() == _e5()
