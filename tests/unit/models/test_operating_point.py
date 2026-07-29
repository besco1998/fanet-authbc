"""The operating point against its citations (items A4/B2/B3/B4, docs/01 §1, docs/02 §7a).

Every constant that defines where this thesis operates — Λ, D_max, N_local, p — was an uncited
assumption until 2026-07-29. These tests pin what the citations actually say and, more importantly,
pin the *relationships* that make the operating point defensible:

  * batching depends only on the PRODUCT Λ·D_max, so the relaxed-latency operating point and the
    3GPP-compliant one give identical byte results;
  * N_local is reported as a curve (N_max per configuration), not defended as a constant;
  * T6 needs only ε ≤ p, so its exclusions survive the whole loss grid.

Sources: 3GPP TS 22.125 V17.6.0 §5.2.2 (direct UAV-to-UAV local broadcast); PX4 `mavlink_main.cpp`;
ArduPilot `GCS_MAVLink_Parameters.cpp`.
"""

from __future__ import annotations

import csv

import pytest

from authbc.bench.experiments import REPO
from authbc.models.energy import EnergyConfig, Placement, freshness_delay_s
from authbc.models.optimizer import freshness_batch_bound, max_fragments

H_F, G_A, S_DELTA = 44, 64, 45.0

# --- 3GPP TS 22.125 V17.6.0, direct UAV-to-UAV local broadcast (§5.2.2) ---------------------
TS22125_MIN_MSG_RATE_HZ = 10        # R-5.2.2-010: "at least 10 messages per second"
TS22125_MAX_LATENCY_S = 0.100       # R-5.2.2-011: "end-to-end latency of at most 100ms"
TS22125_PAYLOAD_RANGE_B = (50, 1500)  # R-5.2.2-008, "not including security-related component(s)"

# --- autopilot stream rates, read from source 2026-07-29 (item A4) --------------------------
PX4_GLOBAL_POSITION_INT_HZ = {"NORMAL": 5, "OSD": 10, "CONFIG": 10, "ONBOARD": 50,
                              "LOW_BANDWIDTH": 2}
ARDUPILOT_POSITION_DEFAULT_HZ = {"Plane": 1, "Rover": 1, "Sub": 3, "Copter": 0}


def _admissible_batch(lam: float, d_max_s: float, s: float = S_DELTA) -> int:
    """The batch E5 would accept: largest b whose full D(b) fits the budget."""
    b = max(1, freshness_batch_bound(lam, d_max_s))
    while b > 1:
        cfg = EnergyConfig(placement=Placement.B, batch=b, record_bytes=s,
                           auth_bytes=G_A, frame_hdr_bytes=H_F, n_frames=1)
        if freshness_delay_s(cfg, lam) <= d_max_s:
            break
        b -= 1
    return b


def _envelope_rows() -> dict[str, str]:
    path = REPO / "results/raw/capacity_envelope.csv"
    rows = csv.DictReader([ln for ln in path.read_text().splitlines() if not ln.startswith("#")])
    return {r["binds"]: r["verdict"] for r in rows if r["n_local"] == "ENVELOPE"}


# --- A4: the rate sits between the standard's floor and the autopilot's ceiling -------------
def test_lambda_is_bracketed_by_the_standard_and_the_autopilot() -> None:
    lam = 20
    assert lam >= TS22125_MIN_MSG_RATE_HZ, "below the 3GPP minimum message rate"
    assert lam <= PX4_GLOBAL_POSITION_INT_HZ["ONBOARD"], "above PX4's companion-link rate"
    assert PX4_GLOBAL_POSITION_INT_HZ["OSD"] < lam < PX4_GLOBAL_POSITION_INT_HZ["ONBOARD"]


def test_ardupilot_multirotor_default_forbids_batching_entirely() -> None:
    """The correction behind item A4: Copter's default POSITION rate is 0 Hz, not 1 Hz.

    Batching needs Λ ≥ 1/D_max. At an on-demand (0 Hz) or 1 Hz stream there is nothing to batch,
    and this thesis's mechanism simply does not apply — which the docs must say rather than imply
    a universal "1 Hz ArduPilot default".
    """
    assert ARDUPILOT_POSITION_DEFAULT_HZ["Copter"] == 0
    assert ARDUPILOT_POSITION_DEFAULT_HZ["Plane"] == 1
    assert _admissible_batch(1.0, 0.250) == 1, "a 1 Hz link cannot batch at a 250 ms bound"


# --- B3: only the product Λ·D_max matters ---------------------------------------------------
def test_the_relaxed_and_the_compliant_operating_points_are_equivalent() -> None:
    """(Λ=20, D=250 ms) and (Λ=50, D=100 ms) both give Λ·D = 5 ⇒ b = 4 ⇒ the same bytes.

    This is what makes the 250 ms deviation from TS 22.125 R-5.2.2-011 recoverable: the co-design
    result is reproduced verbatim at PX4's ONBOARD rate under the standard's latency bound.
    """
    relaxed = _admissible_batch(20.0, 0.250)
    compliant = _admissible_batch(50.0, TS22125_MAX_LATENCY_S)
    assert relaxed == compliant == 4
    assert 20 * 0.250 == 50 * TS22125_MAX_LATENCY_S == 5.0
    auth = (H_F + G_A) / 4
    assert auth == 27.0
    assert (1 - 1 / relaxed) == (1 - 1 / compliant) == 0.75


def test_the_standard_latency_at_our_rate_forbids_batching() -> None:
    """At Λ=20 the 100 ms bound admits only b=1 — the auth-byte result vanishes (0 %).

    b=2 needs exactly 100.0 ms of fill time, so any positive airtime breaks the bound. This is the
    honest cost of the deviation and is reported, not hidden.
    """
    assert _admissible_batch(20.0, TS22125_MAX_LATENCY_S) == 1
    assert 2 / 20.0 == TS22125_MAX_LATENCY_S      # exactly exhausts the budget on fill alone


def test_the_standards_minimum_rate_also_forbids_batching() -> None:
    assert _admissible_batch(float(TS22125_MIN_MSG_RATE_HZ), TS22125_MAX_LATENCY_S) == 1


# --- B2: N_local is a curve, and N=50 sits between the baselines and the co-design ----------
def test_n_max_envelope_separates_the_baselines_from_the_co_design() -> None:
    """The capability claim: the co-design carries 3.2x the swarm the Pillar-1 baseline can."""
    env = _envelope_rows()
    assert env["optimized delta/B @250ms"] == "N_max=103"
    assert env["A+CBOR Pillar-1 @250ms"] == "N_max=32"
    assert env["A+JSON naive @250ms"] == "N_max=25"
    assert 103 / 32 > 3.0, "co-design should roughly triple the supportable swarm"


def test_n_equals_50_lies_between_the_baseline_and_the_co_design_limits() -> None:
    """Which is precisely why N=50 is quoted — it is not an arbitrary constant."""
    assert 32 < 50 < 103


def test_the_compliant_operating_point_costs_swarm_size() -> None:
    """(Λ=50, D=100 ms) gives the same bytes but 3x the channel load, so N_max falls 103 -> 35."""
    env = _envelope_rows()
    assert env["optimized delta/B @3GPP100ms/50Hz"] == "N_max=35"
    assert env["optimized delta/B @3GPP100ms/10Hz"] == "N_max=78"


# --- B4: T6 depends on ε ≤ p, not on p = 0.05 ------------------------------------------------
@pytest.mark.parametrize("p", [0.02, 0.05, 0.10])
def test_t6_no_fragmentation_holds_across_the_whole_loss_grid(p: float) -> None:
    """Whenever the verifiability target is no looser than the loss rate, n_max = 1."""
    assert max_fragments(epsilon=p, p_loss=p) == 1


def test_our_loss_grid_is_more_pessimistic_than_the_standards_c2_reliability() -> None:
    """TS 22.125 Table 7.2-1 asks 99.9 % (p=1e-3) for MANAGED C2 links with retransmission.

    802.11 broadcast has no ACK and no retransmission, so a receiver sees the raw channel error
    rate. Our grid is 20-100x more pessimistic, which is conservative for every dependent claim.
    """
    ts22125_c2_p = 1e-3
    for p in (0.02, 0.05, 0.10):
        assert p > ts22125_c2_p * 10


# --- B3 as an optimization: the region, not a chosen constant (docs/02 §7a) -------------------
def _region() -> list[dict[str, str]]:
    path = REPO / "results/raw/operating_region.csv"
    return list(csv.DictReader([ln for ln in path.read_text().splitlines()
                                if not ln.startswith("#")]))


def test_compliant_and_runnable_set_is_exactly_four_points() -> None:
    """The headline result of B3 is a BOUND, not a choice.

    Under TS 22.125 (>=10 msg/s, <=100 ms) AND U<1 at N=50, only four operating points exist and
    the best achievable auth-byte cut is 50 %, not the 75 % the declared reference point reports.
    """
    ok = [r for r in _region()
          if r["ts22125_compliant"] == "1" and r["runnable_at_n_ref"] == "1"]
    assert len(ok) == 4
    best = max(float(r["auth_cut_pct"]) for r in ok)
    assert best == pytest.approx(50.0, abs=0.01), (
        "under full compliance at N=50 the achievable cut is 50 %; if this changes, docs/02 §7a "
        "and the paper's compliance paragraph must change with it")
    batching = sorted(int(r["lambda_rec_per_s"]) for r in ok if int(r["b"]) >= 2)
    assert batching == [21, 22], "only 21-22 Hz both meets the deadline and clears the medium"


def test_the_declared_reference_point_is_non_compliant_and_says_so() -> None:
    """Λ=20, D=250 ms is DECLARED, not optimal. The deviation must stay visible in the data."""
    ref = next(r for r in _region()
               if r["lambda_rec_per_s"] == "20" and r["d_max_ms"] == "250")
    assert ref["ts22125_compliant"] == "0", "the reference point violates R-5.2.2-011 by design"
    assert ref["runnable_at_n_ref"] == "1" and int(ref["b"]) == 4
    assert float(ref["auth_cut_pct"]) == pytest.approx(75.0)
    assert int(ref["n_max"]) == 103


def test_equal_lambda_times_dmax_gives_identical_bytes() -> None:
    """The governing relation: bytes depend only on the product, capacity does not."""
    a = next(r for r in _region() if r["lambda_rec_per_s"] == "20" and r["d_max_ms"] == "250")
    b = next(r for r in _region() if r["lambda_rec_per_s"] == "50" and r["d_max_ms"] == "100")
    assert a["lambda_x_dmax"] == b["lambda_x_dmax"] == "5.0"
    assert a["b"] == b["b"] == "4"
    assert a["auth_bytes_per_rec"] == b["auth_bytes_per_rec"]
    assert a["total_cut_pct"] == b["total_cut_pct"]
    # identical bytes, and that is exactly where they differ:
    assert float(a["channel_util_at_n_ref"]) < 1.0 < float(b["channel_util_at_n_ref"])
    assert int(a["n_max"]) > int(b["n_max"])
