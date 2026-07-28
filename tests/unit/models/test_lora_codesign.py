"""Unit tests for the LoRa co-design optimizer (guards src/authbc/models/lora_codesign.py).

The contract this pins (Law 4/6):
  1. it is an OPTIMIZATION, not a selection — the full Pareto set is returned, never one point;
  2. the design space includes the DATA RATE, and the range objective is what keeps that axis
     alive (without it the fastest rate trivially dominates and the axis collapses);
  3. Λ and freshness are DERIVED from the duty cycle, never configured;
  4. designs that cannot fit the regional payload limit are *skipped*, not "infeasible".
"""

from __future__ import annotations

import pytest

from authbc.models import lora
from authbc.models.energy import Placement
from authbc.models.lora_codesign import LoRaConstraints, pareto_front, solve
from authbc.models.optimizer import EncodingSpec, SchemeSpec

_ENCS = [EncodingSpec("delta", 45.0, 48e-6), EncodingSpec("cbor", 66.25, 50e-6)]
_SCHEMES = [SchemeSpec("ed25519", 64, 88e-6, 260e-6)]
_BATCHES = [1, 2, 3, 4, 5, 6, 8]
_DRS = [0, 1, 2, 3, 4, 5, 6]


def _solve(**kw):
    return solve(_ENCS, _SCHEMES, [Placement.A, Placement.B, Placement.D], _BATCHES, _DRS,
                 LoRaConstraints(), **kw)


def test_long_range_data_rates_cannot_carry_an_authenticated_frame_at_all() -> None:
    """The LoRa arm's hardest finding: DR0–DR3 are skipped, not merely dominated.

    Per-frame overhead is 40 B header + 64 B signature = 104 B, against a regional limit of 51 B
    at DR0–DR2 and 115 B at DR3 (RP002-1.0.3 Table 13). No batching or chain optimisation helps —
    the overhead alone exceeds the budget before a single record is added.
    """
    res = _solve(chain_modes=("per_record", "per_frame"))
    assert {c.dr for c in res.feasible} == {4, 5, 6}
    assert res.skipped > res.evaluated, "most of the LoRa design space does not physically exist"
    for dr in (0, 1, 2, 3):
        limit = lora.EU868_DATA_RATES[dr].max_app_payload
        assert limit < 40 + 64 + 45, f"DR{dr} must be unable to hold header+sig+one record"


def test_lambda_and_freshness_are_derived_from_the_duty_cycle() -> None:
    """Λ = b·duty/T and D = T/duty — neither is an input, and D does not depend on b directly."""
    res = _solve()
    for c in res.feasible:
        interval = lora.duty_cycle_interval_s(c.toa_s, LoRaConstraints().duty_cycle)
        assert c.freshness_s == pytest.approx(interval)
        assert c.lambda_max == pytest.approx(c.batch / interval)


def test_range_objective_keeps_the_data_rate_axis_alive() -> None:
    """Without range, the fastest DR dominates on both Λ and D and the axis collapses to one.

    This is the formulation check: the frontier must span several data rates, because trading
    airtime for link budget is exactly the choice the LoRa arm exists to make.
    """
    res = _solve(chain_modes=("per_record", "per_frame"))
    drs = {c.dr for c in res.pareto}
    assert len(drs) > 1, "a single-DR frontier means the range objective is not doing its job"
    assert drs == {4, 5, 6}
    # and range must be monotone in spreading factor
    by_dr = {c.dr: c.relative_range for c in res.pareto}
    assert by_dr[4] > by_dr[5] > by_dr[6] == pytest.approx(1.0)


def test_the_result_is_a_frontier_not_a_winner() -> None:
    """No point on the front dominates another; every one is a defensible operating choice."""
    res = _solve(chain_modes=("per_record", "per_frame"))
    assert len(res.pareto) > 10
    assert pareto_front(res.pareto) == res.pareto     # already non-dominated
    assert set(res.pareto) <= set(res.feasible)


def test_batching_trades_bytes_against_freshness_within_a_data_rate() -> None:
    """The LoRa co-design tension: a bigger batch lowers bytes/record and raises Λ, but the
    longer frame lengthens the duty-cycle interval and therefore worsens freshness."""
    res = _solve(chain_modes=("per_frame",))
    dr5 = sorted((c for c in res.feasible if c.dr == 5 and c.placement is Placement.B
                  and c.encoding == "delta"), key=lambda c: c.batch)
    assert [c.batch for c in dr5] == sorted(c.batch for c in dr5)
    assert dr5[0].bytes_per_record > dr5[-1].bytes_per_record   # bytes improve with b
    assert dr5[0].lambda_max < dr5[-1].lambda_max               # Λ improves with b
    assert dr5[0].freshness_s < dr5[-1].freshness_s             # …and freshness gets WORSE


def test_chain_per_frame_dominates_per_record_above_a_single_record() -> None:
    """Audit F5 on the payload-starved link: fewer bytes per record ⇒ more records per frame."""
    res = _solve(chain_modes=("per_record", "per_frame"))
    best = {}
    for c in res.feasible:
        if c.encoding == "delta" and c.dr == 5 and c.placement is Placement.B:
            best[c.chain_mode] = max(best.get(c.chain_mode, c), c, key=lambda x: x.lambda_max)
    assert best["per_frame"].batch > best["per_record"].batch
    assert best["per_frame"].lambda_max > 2.5 * best["per_record"].lambda_max


def test_empty_or_oversized_design_space_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty design space"):
        solve([], _SCHEMES, [Placement.B], _BATCHES, _DRS, LoRaConstraints())
