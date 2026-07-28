"""F13 — what each design axis actually contributes to the headline (docs/audits/model_provenance).

The 75.00 % auth-byte cut is produced by **placement × batching alone**. The encoding axis and the
scheme axis contribute exactly zero to it. That is not a defect — it is T2a seen from the other
side — but it constrains what may be claimed, so it is pinned here: if someone later writes
"co-optimizing encoding ... cuts auth bytes by 75 %", these tests are the standing rebuttal.

Expected values are hand-computed from `auth(b) = (H_f + g_a)/b` and cross-checked against the
FROZEN E2 artifact by an independent route (`bytes_per_rec − s`), never by calling the optimizer
back on itself (Law 6).
"""

from __future__ import annotations

import csv

import pytest

from authbc.bench.experiments import REPO
from authbc.models.energy import Placement
from authbc.models.optimizer import frame_auth_bytes, freshness_batch_bound

H_F, G_A = 44, 64
ENCODINGS = ("json", "cbor", "msgpack", "delta")


def _auth_overhead_per_record(placement: Placement, batch: int) -> float:
    """(H_f + auth bytes carried in the frame) / b — the headline metric, by definition."""
    return (H_F + frame_auth_bytes(placement, batch, G_A)) / batch


def _e2_rows() -> list[dict[str, str]]:
    path = REPO / "results/raw/e2_batching.csv"
    return list(csv.DictReader([ln for ln in path.read_text().splitlines()
                                if not ln.startswith("#")]))


# --- the claim: the metric does not depend on the encoding ------------------------------------
def test_auth_overhead_is_identical_across_every_encoding_in_frozen_e2() -> None:
    """Derived from the frozen artifact as bytes_per_rec − s, so this is data, not model output."""
    for placement, batch, expected in (("A", "1", 108.0), ("B", "4", 27.0)):
        seen = {r["encoding"]: float(r["bytes_per_rec"]) - float(r["s"])
                for r in _e2_rows()
                if r["placement"] == placement and r["b"] == batch and r["mtu"] == "1500"}
        assert set(seen) == set(ENCODINGS), f"E2 lost an encoding at {placement}/b={batch}"
        # The CSV stores s to 2 dp and bytes_per_rec to 3, so the difference carries up to 5 mB of
        # rounding noise. The claim is that the SPREAD across encodings is that noise and nothing
        # more — a real encoding dependence would show up orders of magnitude above it.
        assert max(seen.values()) - min(seen.values()) < 0.01, (
            f"auth overhead must not depend on the encoding; spread at {placement}/b={batch} "
            f"was {seen}. If this ever grows, F13's framing correction needs revisiting.")
        for enc, value in seen.items():
            assert value == pytest.approx(expected, abs=0.01), f"{enc} at {placement}/b={batch}"


def test_the_closed_form_carries_no_record_size_term() -> None:
    """auth(b) = (H_f + g_a)/b. Feeding wildly different record sizes cannot move it."""
    assert _auth_overhead_per_record(Placement.A, 1) == 108.0
    assert _auth_overhead_per_record(Placement.B, 4) == 27.0
    assert (108.0 - 27.0) / 108.0 == pytest.approx(0.75, abs=1e-12)   # the headline, exactly
    # B1 moved H_f 40 -> 44 and the headline did NOT move: 104/26 and 108/27 both give 75.00 %
    assert (104.0 - 26.0) / 104.0 == (108.0 - 27.0) / 108.0


def test_the_headline_is_algebraically_one_minus_one_over_b() -> None:
    """The sharpest form of F13: cut = 1 − 1/b, with EVERY other symbol cancelling.

    Baseline and optimized both carry H_f + g_a per frame; the baseline divides by 1, the optimized
    by b. So the reported percentage is invariant to header size, signature size, encoding and
    scheme — it encodes exactly one quantity, b. If this test ever fails, the metric has stopped
    being what F13 says it is and the framing correction must be revisited.
    """
    for h_f in (20, 40, 80, 200):
        for g_a in (48, 64, 96):
            for b in (2, 4, 8, 31):
                baseline = h_f + g_a
                optimized = (h_f + g_a) / b
                assert (baseline - optimized) / baseline == pytest.approx(1 - 1 / b, abs=1e-12)
    assert 1 - 1 / 4 == 0.75, "b=4 is the whole information content of the 75.00 % headline"


def test_the_batch_is_fixed_by_lambda_and_dmax_not_discovered() -> None:
    """b = 4 follows from the INPUTS Λ=20 and D_max=250 ms, not from the search.

    ⌊Λ·D_max⌋ = 5 is the fill-time-only ceiling; b=5 sits at exactly 250.0 ms of fill time, so any
    positive airtime term breaks the bound and the feasible batch is 4.
    """
    lam, d_max_s = 20.0, 0.25
    assert freshness_batch_bound(lam, d_max_s) == 5
    assert 5 / lam == d_max_s                      # b=5 exhausts the budget on fill time alone
    assert 4 / lam < d_max_s                       # b=4 leaves 50 ms of headroom
    assert (1 - 1 / 4) * 100 == 75.0


def test_the_scheme_axis_is_byte_neutral_for_the_headline() -> None:
    """Ed25519 and ECDSA-P256 are both 64 B, so the scheme cannot move the auth-byte metric.

    BLS moves it the WRONG way (96 B), which is why the scheme is decided on energy and
    verify-throughput (T4/F6) rather than on bytes.
    """
    ed = ecdsa = 64
    bls = 96
    assert ed == ecdsa
    assert (H_F + ed) / 4 == (H_F + ecdsa) / 4 == 27.0
    assert (H_F + bls) / 4 > 27.0


# --- what the encoding DOES buy, so the correction is not read as "encoding is useless" --------
def test_encoding_moves_payload_bytes_and_therefore_total_bytes() -> None:
    """A+CBOR 174.252 → delta/B/b=4 71.998 B/record: 58.68 % of TOTAL bytes, of which 20.8 % is
    attributable to the encoding and 79.2 % to placement × batching (H_f = 44 measured, B1)."""
    base_total, base_s = 174.252, 66.25
    opt_total, opt_s = 71.998, 45.0
    assert base_total - base_s == pytest.approx(108.0, abs=0.01)
    assert opt_total - opt_s == pytest.approx(27.0, abs=0.01)

    total_saving = base_total - opt_total
    auth_saving = (base_total - base_s) - (opt_total - opt_s)
    payload_saving = base_s - opt_s
    assert auth_saving + payload_saving == pytest.approx(total_saving, abs=0.01)
    assert 100 * total_saving / base_total == pytest.approx(58.68, abs=0.05)
    assert 100 * payload_saving / base_s == pytest.approx(32.1, abs=0.1)
    assert 100 * auth_saving / total_saving == pytest.approx(79.2, abs=0.1)
    assert 100 * payload_saving / total_saving == pytest.approx(20.8, abs=0.1)


def test_frozen_e2_still_shows_the_encoding_spread_it_is_credited_for() -> None:
    """The encoding axis must remain load-bearing on TOTAL bytes — 4x spread at fixed placement."""
    rows = {r["encoding"]: float(r["bytes_per_rec"]) for r in _e2_rows()
            if r["placement"] == "B" and r["b"] == "4" and r["mtu"] == "1500"}
    assert rows["json"] / rows["delta"] > 3.0, "encoding should still span >3x on total bytes"
