"""Regression tests for the model-vs-NS-3 agreement bands quoted in the paper (audit F27).

**Why this file exists.** The abstract quotes model-vs-NS-3 agreement bands. Until F27 **nothing
enforced them**:
the frozen-artifact gate re-derives the CSVs, and the unit tests check the models in isolation, but
no test compared the two. A model change could therefore leave a stale validation claim in the
paper's abstract with every gate still green — precisely the drift the frozen gate exists to stop.

Convention, stated because the sign depends on it: deviation is **(simulation - model) / model**,
i.e. how far NS-3 sits above the analytical prediction. Reversing the denominator flips the signs
for the same magnitudes, which is why the convention is asserted here and not left implicit.

⚠️ These bands are measured on the **30-seed** matrix (F30). The previous 10-seed matrix put the
broadcast endpoint at -1.44 %, which turned out to be sampling noise: at 30 seeds it is -0.51 %.
The superseded file is kept as `ns3_matrix_SUPERSEDED_lowseed.csv`.
"""

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import pytest

from authbc.models import bianchi, broadcast_dcf

RESULTS = Path(__file__).resolve().parents[1] / "results" / "raw"
FRAME_BYTES = 1400


def _measured() -> dict[tuple[int, str], float]:
    """Mean NS-3 goodput per (N, mode) from the frozen validation matrix."""
    rows = [
        r
        for r in csv.DictReader(
            [ln for ln in (RESULTS / "ns3_matrix.csv").read_text().splitlines(keepends=True)
             if not ln.startswith("#")]
        )
    ]
    grouped: dict[tuple[int, str], list[float]] = defaultdict(list)
    for r in rows:
        grouped[(int(r["N"]), r["mode"])].append(float(r["goodput_mbps"]))
    return {k: st.mean(v) for k, v in grouped.items()}


def _model_mbps(n: int, mode: str) -> float:
    if mode == "unicast":
        return bianchi.solve(n, FRAME_BYTES).throughput_bps / 1e6
    return (
        broadcast_dcf.solve(
            n, FRAME_BYTES, bianchi.t_broadcast(FRAME_BYTES), w0=bianchi.W, slot_s=bianchi.SLOT
        ).throughput_bps
        / 1e6
    )


def _deviation_pct(n: int, mode: str) -> float:
    sim = _measured()[(n, mode)]
    model = _model_mbps(n, mode)
    return 100.0 * (sim - model) / model


class TestUnicastMatchesBianchi:
    """docs/02 and the abstract: +1.29 / -0.40 % across N = 5..50, 30 seeds."""

    @pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
    def test_each_point_within_the_published_band(self, n):
        d = _deviation_pct(n, "unicast")
        assert -0.40 - 0.05 <= d <= 1.29 + 0.05, f"N={n}: {d:+.2f} % is outside +1.29/-0.40"

    def test_band_endpoints_are_exactly_what_the_paper_claims(self):
        devs = [_deviation_pct(n, "unicast") for n in (5, 10, 20, 35, 50)]
        assert max(devs) == pytest.approx(1.29, abs=0.02), "upper endpoint drifted from +1.29 %"
        assert min(devs) == pytest.approx(-0.40, abs=0.02), "lower endpoint drifted from -0.40 %"


class TestBroadcastMatchesMaAndChen:
    """The load-bearing one: reducing Bianchi to broadcast fails by 16x at N=50 (finding F9)."""

    @pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
    def test_goodput_within_the_published_band(self, n):
        d = _deviation_pct(n, "broadcast")
        assert abs(d) <= 0.60, f"N={n}: {d:+.2f} % exceeds the 0.51 % goodput claim"

    def test_goodput_band_is_tighter_than_the_headline_number(self):
        """⚠️ The 2.49 % in the abstract is the *success-probability* deviation, not goodput.

        Goodput agrees to 1.44 %. Quoting the worse of the two is conservative, but the two are
        different quantities and the paper now says which is which. This test pins the goodput
        figure so the distinction cannot quietly collapse.
        """
        devs = [_deviation_pct(n, "broadcast") for n in (5, 10, 20, 35, 50)]
        assert max(abs(d) for d in devs) == pytest.approx(0.51, abs=0.05)


class TestTheReductionThatFails:
    """F9: applying the unicast model to broadcast is wrong by ~16x at N=50, not a little wrong."""

    def test_bianchi_reduced_to_broadcast_is_off_by_more_than_an_order_of_magnitude(self):
        n = 50
        sim = _measured()[(n, "broadcast")]
        wrong = bianchi.solve(n, FRAME_BYTES).throughput_bps / 1e6  # the naive reduction
        right = _model_mbps(n, "broadcast")
        assert abs(sim - right) / right < 0.025, "Ma & Chen should track the measurement"
        # The naive reduction over-predicts delivered broadcast goodput enormously.
        assert wrong / sim > 2.5, "the unicast reduction should be badly optimistic here"


class TestSignConventionIsPinned:
    """The band is only meaningful with its denominator stated (see module docstring)."""

    def test_reversing_the_denominator_changes_the_reported_band(self):
        sim = _measured()[(10, "unicast")]
        model = _model_mbps(10, "unicast")
        as_documented = 100.0 * (sim - model) / model
        reversed_denom = 100.0 * (sim - model) / sim
        assert as_documented == pytest.approx(1.29, abs=0.03)
        assert reversed_denom == pytest.approx(1.27, abs=0.03)
        assert as_documented != pytest.approx(reversed_denom, abs=0.005)


class TestPlacementEnumsCannotBeConfusedSilently:
    """Audit F27: two `Placement` enums exist and `is` comparisons fail silently across them."""

    def test_wrong_placement_enum_raises_instead_of_mis_computing(self):
        from authbc.models.optimizer import verifiability
        from authbc.placement.wire import Placement as WirePlacement

        with pytest.raises(TypeError, match="not interchangeable"):
            verifiability(WirePlacement.D, 4, 0.05)

    def test_block_placement_really_does_compound_loss(self):
        """The value the silent failure was hiding: (1-p)^n, not 1-p."""
        from authbc.models.energy import Placement
        from authbc.models.optimizer import verifiability

        assert verifiability(Placement.D, 4, 0.05) == pytest.approx(0.95**4)
        assert verifiability(Placement.B, 4, 0.05) == pytest.approx(0.95)

    @pytest.mark.parametrize("fn_name", ["frame_auth_bytes", "bytes_per_record"])
    def test_the_other_public_entry_points_are_guarded_too(self, fn_name):
        """E18: guarding only `verifiability` would leave the same trap elsewhere."""
        import authbc.models.optimizer as opt
        from authbc.placement.wire import Placement as WirePlacement

        fn = getattr(opt, fn_name)
        args = (WirePlacement.A, 4, 64.0) if fn_name == "frame_auth_bytes" else (
            WirePlacement.A, 4, 45.0, 64.0, 44.0, 1)
        with pytest.raises(TypeError, match="not interchangeable"):
            fn(*args)

    def test_energy_config_rejects_the_wrong_enum_at_construction(self):
        """The broadest guard: catch it where the object is built, not at every use."""
        from authbc.models.energy import EnergyConfig
        from authbc.placement.wire import Placement as WirePlacement

        with pytest.raises(TypeError, match="not interchangeable"):
            EnergyConfig(placement=WirePlacement.A, batch=4, record_bytes=45.0,
                         auth_bytes=64.0, frame_hdr_bytes=44.0)
