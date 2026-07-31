"""External LoRa references: Bor et al. 2017 (capacity) and Zirak et al. 2021 (measured link).

This is the LoRa arm's external baseline (item A7): a published, closed-form, *hardware-measurement
grounded* capacity model that can be evaluated at OUR operating point rather than quoted at theirs.
Every expected value below is a figure the paper states in prose, cited by its figure number, so
these tests fail if the implementation of Eq. (8) drifts from the source.

Source: Bor, Roedig, Voigt & Alonso, "LoRa Scalability: A Simulation Model Based on Interference
Measurements", Sensors 17(6):1193, 2017. PDF in docs/literature/.
"""

import pytest

from authbc.models import lora
from authbc.models.lora import (
    BOR2017_VALID_MAX_X,
    bor2017_loss_pct,
    bor2017_n_max,
)


class TestReproducesThePapersOwnFigures:
    """Eqs. (9)-(11) scale Eq. (8) by the logical-channel count; all four must land on the prose."""

    @pytest.mark.parametrize(
        "logical_channels, stated_pct, tol, figure",
        [
            (1, 90.0, 4.0, "Fig. 6 — 1 channel, 1 SF: 'around 90% of all packets are collided'"),
            (6, 68.0, 4.0, "Fig. 7 — 1 channel, 6 SFs: 'around 68% for 1000 nodes per gateway'"),
            (18, 32.0, 1.0, "Fig. 9 — 3 channels, 6 SFs: 'In total, 32% of packets are lost'"),
        ],
    )
    def test_total_loss_at_1000_nodes(self, logical_channels, stated_pct, tol, figure):
        got = bor2017_loss_pct(999.9, logical_channels=logical_channels)
        assert got == pytest.approx(stated_pct, abs=tol), figure

    def test_three_channels_single_sf_exceeds_the_collision_only_figure(self):
        """Fig. 8 says 'around 75% ... lost due to COLLISIONS' — collisions only, not the total.

        Eq. (8) fits TOTAL loss (collisions + wrong-CRC), so the model must come out *above* 75%.
        This test exists because the 5-point gap looks like an implementation error until you read
        which quantity that sentence names.
        """
        total = bor2017_loss_pct(999.9, logical_channels=3)
        assert 75.0 < total < 85.0


class TestDomainIsEnforcedNotExtrapolated:
    def test_rejects_x_at_or_beyond_the_fits_stated_limit(self):
        with pytest.raises(ValueError, match="x < 1000"):
            bor2017_loss_pct(BOR2017_VALID_MAX_X)

    def test_scaling_extends_the_node_domain_but_not_the_x_domain(self):
        # 18 logical channels admit 18x the nodes because the fit sees x = N/18.
        assert bor2017_loss_pct(17_000, logical_channels=18) > 0
        with pytest.raises(ValueError):
            bor2017_loss_pct(18_000, logical_channels=18)

    @pytest.mark.parametrize("bad", [-1.0])
    def test_rejects_negative_node_counts(self, bad):
        with pytest.raises(ValueError):
            bor2017_loss_pct(bad)

    def test_rejects_zero_logical_channels(self):
        with pytest.raises(ValueError):
            bor2017_loss_pct(10, logical_channels=0)


class TestShape:
    def test_loss_is_monotone_increasing_over_the_usable_range(self):
        """Monotone up to N=700, which covers our operating region (N <= 50) with wide margin."""
        vals = [bor2017_loss_pct(n) for n in range(0, 701, 5)]
        assert all(b >= a for a, b in zip(vals, vals[1:], strict=False))

    def test_high_end_non_monotonicity_is_a_known_fit_artifact(self):
        """⚠️ Eq. (8) is NOT monotone near the top of its domain, and that is unphysical.

        The quintic turns over at N ~ 723 (86.61%), bottoms at N ~ 923 (85.01%), then rises again:
        the model says adding 200 nodes *reduces* loss. The excursion is 1.6 percentage points on
        a curve spanning 0-90% with R^2 = 0.997, so it sits inside the fit's own residual — it is
        an artifact of fitting a degree-5 polynomial, not a claim about LoRa.

        Asserted rather than worked around, because a future reader who finds the dip should meet
        this explanation instead of concluding our implementation is broken. It does not touch any
        AUTHBC result: our operating region is N <= 50.
        """
        peak = bor2017_loss_pct(723)
        trough = bor2017_loss_pct(923)
        assert trough < peak, "the documented artifact has vanished — re-derive the coefficients"
        assert peak - trough < 2.0, "artifact larger than the fit residual: check the coefficients"
        # and it stays clear of our operating region by an order of magnitude
        assert 723 > 50 * 10

    def test_more_logical_channels_never_increase_loss(self):
        for n in (50, 200, 900):
            assert bor2017_loss_pct(n, logical_channels=18) <= bor2017_loss_pct(n)

    def test_the_fit_does_not_pass_through_the_origin(self):
        """Documented limitation, asserted so nobody 'fixes' it into a physical claim.

        The polynomial's constant term is 1.7833, so it predicts ~1.8% loss at zero nodes. That is
        a curve-fitting artifact over x<1000, and it means small-N predictions carry the fit's
        error rather than a measurement. Our N_max comparison is reported with that caveat.
        """
        assert bor2017_loss_pct(0) == pytest.approx(1.7833, abs=1e-4)


class TestCapacityAgreesWithOurSimulation:
    """The point of the whole exercise: an independent number for the same criterion."""

    def test_n_max_matches_the_authbc_simulation_within_one_node(self):
        """AUTHBC ns-3 measures N_max = 5 at DR5, V >= 0.95, 1 channel / 1 SF / 1 demod path.

        Bor et al.'s measurement-fitted model, evaluated under the identical V >= 0.95 criterion,
        gives 4. Two independent methods, one node apart. See finding F20.
        """
        assert bor2017_n_max(0.95, logical_channels=1) == 4

    def test_n_max_grows_with_logical_channels(self):
        single = bor2017_n_max(0.95, logical_channels=1)
        full = bor2017_n_max(0.95, logical_channels=18)
        assert full > single
        # 18 orthogonal logical channels should buy close to 18x the nodes.
        assert full == pytest.approx(18 * single, rel=0.35)

    def test_stricter_verifiability_never_admits_more_nodes(self):
        assert bor2017_n_max(0.99) <= bor2017_n_max(0.95) <= bor2017_n_max(0.90)


class TestZirak2021MeasuredAirToAirLink:
    """Hardware PDR for LoRa air-to-air (Zirak et al. 2021, Table I).

    The LoRa arm's only ground truth: our own result has no hardware behind it (D2 was closed by
    simulation and flagged as such). These figures come from a real FANET field test with two
    drones and a base station, so contention is negligible and they isolate range-dependent link
    loss — the term our collision-only simulation does not model at all. See finding F23.
    """

    @pytest.mark.parametrize(
        "range_m, pdr",
        [(200, 0.9711), (500, 0.9550), (600, 0.9399), (1000, 0.9045)],
    )
    def test_reproduces_the_published_table(self, range_m, pdr):
        assert lora.zirak2021_link_pdr(range_m) == pytest.approx(pdr, abs=1e-6)

    def test_pdr_falls_monotonically_with_range(self):
        vals = [lora.zirak2021_link_pdr(r) for r in range(200, 1001, 50)]
        assert all(b <= a for a, b in zip(vals, vals[1:], strict=False))

    @pytest.mark.parametrize("bad", [199.0, 1001.0, 0.0])
    def test_refuses_to_extrapolate(self, bad):
        with pytest.raises(ValueError, match="no extrapolation"):
            lora.zirak2021_link_pdr(bad)

    def test_v95_is_unreachable_beyond_500_m_at_any_node_count(self):
        """⚠️ The constraint our capacity result omits, and it binds at our own configured radius.

        Delivery is P_link(range) x P_no_collision(N). Their measured link PDR is already below 0.95
        at 600 m, so no node count — not even N=1 — can reach V >= 0.95 there. Our scenario is
        configured with radiusMeters = 1000, where the link alone delivers 0.9045.
        """
        assert lora.max_range_for_verifiability(0.95) == 500.0
        assert lora.zirak2021_link_pdr(600) < 0.95
        assert lora.zirak2021_link_pdr(1000) < 0.95

    def test_our_idealised_channel_is_optimistic_by_the_amount_f23_records(self):
        """At 1000 m we simulate zero link loss; hardware measures 9.6 points of it."""
        simulated_link_loss = 0.0            # realisticChannelModel = false, no fading/shadowing
        measured_loss = 1.0 - lora.zirak2021_link_pdr(1000)
        assert measured_loss - simulated_link_loss == pytest.approx(0.0955, abs=5e-4)
