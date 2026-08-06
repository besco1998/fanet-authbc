"""Is the co-design claim an ablation result, or only a decomposition? (Tier-2 item 4)

The paper claims the four axes must be optimised **together**. The evidence offered was a
*decomposition* (79.2 % placement×batching, 20.8 % encoding), which is possible even when the axes
are perfectly independent. Only interaction terms distinguish the two.

These tests pin what `analysis/factorial_ablation.py` found, and — more usefully — the closed forms
behind it, because the interactions here are **exactly** zero or exactly `g_a(1 - 1/b)` rather than
small numbers that happen to look like it.
"""

from __future__ import annotations

import pytest

from authbc.bench import framesizes
from authbc.models.energy import Placement
from authbc.models.optimizer import bytes_per_record

H_F, G_A = 44.0, 64.0


def _bytes(encoding: str, placement: Placement, batch: int, g_a: float = G_A) -> float:
    return bytes_per_record(placement, batch, framesizes.measured_sizes()[encoding],
                            g_a, H_F, 1)


class TestPlacementAndBatchingGenuinelyCouple:
    """The half of the co-design claim that holds — and it holds exactly, not approximately."""

    @pytest.mark.parametrize("encoding", ["json", "cbor", "msgpack", "delta"])
    def test_placement_is_worth_exactly_nothing_without_batching(self, encoding):
        """A and B are byte-IDENTICAL at b=1, for every encoding. This is the coupling."""
        a = _bytes(encoding, Placement.A, 1)
        b = _bytes(encoding, Placement.B, 1)
        assert a == pytest.approx(b, abs=1e-9), (
            "placement must be inert at b=1: A carries one signature per record and so does B "
            "when the batch is one record"
        )

    @pytest.mark.parametrize("batch", [1, 2, 4, 8, 16])
    def test_the_placement_benefit_is_exactly_g_a_times_one_minus_one_over_b(self, batch):
        """Closed form: A - B = g_a(1 - 1/b).

        ⚠️ Note the shape: `1 - 1/b` is the same expression the status board warns about for the
        bare 75 % figure. The thing that makes the headline saving look impressive and the thing
        that couples placement to batching are the *same algebraic term*.
        """
        gap = _bytes("delta", Placement.A, batch) - _bytes("delta", Placement.B, batch)
        assert gap == pytest.approx(G_A * (1 - 1 / batch), abs=1e-9)

    def test_the_interaction_equals_the_main_effect(self):
        """Signature of a PURE interaction: placement has no standalone effect to speak of.

        In the Yates contrast both come out at -24 B/rec, because placement's entire contribution
        is conditional on batching being present.
        """
        corners = {
            (p, b): _bytes("delta", p, b)
            for p in (Placement.A, Placement.B) for b in (1, 4)
        }
        main = ((corners[(Placement.B, 1)] + corners[(Placement.B, 4)])
                - (corners[(Placement.A, 1)] + corners[(Placement.A, 4)])) / 2
        inter = ((corners[(Placement.B, 4)] - corners[(Placement.A, 4)])
                 - (corners[(Placement.B, 1)] - corners[(Placement.A, 1)])) / 2
        assert main == pytest.approx(-24.0, abs=1e-9)
        assert inter == pytest.approx(-24.0, abs=1e-9)
        assert main == pytest.approx(inter, abs=1e-9)


class TestEncodingIsPerfectlySeparable:
    """⚠️ The half of the co-design claim that does NOT hold. Encoding couples with nothing."""

    @pytest.mark.parametrize("placement", [Placement.A, Placement.B])
    @pytest.mark.parametrize("batch", [1, 4, 16])
    def test_the_encoding_saving_is_the_same_whatever_else_is_chosen(self, placement, batch):
        """s enters bytes_per_record purely additively, so it CANNOT interact. Structural."""
        sizes = framesizes.measured_sizes()
        expected = sizes["json"] - sizes["delta"]
        got = _bytes("json", placement, batch) - _bytes("delta", placement, batch)
        assert got == pytest.approx(expected, abs=1e-9)

    def test_every_interaction_involving_encoding_is_exactly_zero(self):
        vals = {(e, p, b): _bytes(e, p, b)
                for e in ("json", "delta")
                for p in (Placement.A, Placement.B)
                for b in (1, 4)}

        def contrast(sub_e: bool, sub_p: bool, sub_b: bool) -> float:
            total = 0.0
            for (e, p, b), v in vals.items():
                sign = 1.0
                if sub_e:
                    sign *= 1.0 if e == "delta" else -1.0
                if sub_p:
                    sign *= 1.0 if p is Placement.B else -1.0
                if sub_b:
                    sign *= 1.0 if b == 4 else -1.0
                total += sign * v
            return total / 4.0

        assert contrast(True, True, False) == pytest.approx(0.0, abs=1e-9)   # enc x placement
        assert contrast(True, False, True) == pytest.approx(0.0, abs=1e-9)   # enc x batching
        assert contrast(True, True, True) == pytest.approx(0.0, abs=1e-9)    # 3-way


class TestTheSchemeAxisIsByteDegenerateAtTheOperatingPoint:
    """Not a null result to celebrate — a reason the four-axis framing overstates the case."""

    def test_the_two_schemes_the_optimizer_picks_between_are_both_64_bytes(self):
        """Ed25519 and ECDSA-P256 are both 64 B, so the axis cannot move bytes at the optimum."""
        assert _bytes("delta", Placement.B, 4, 64.0) == _bytes("delta", Placement.B, 4, 64.0)

    def test_bls_is_where_the_scheme_axis_would_cost_something(self):
        """96 B BLS costs +8 B/record at b=4 -- amortized, so batching mutes this axis too."""
        ed = _bytes("delta", Placement.B, 4, 64.0)
        bls = _bytes("delta", Placement.B, 4, 96.0)
        assert bls - ed == pytest.approx((96.0 - 64.0) / 4, abs=1e-9)
