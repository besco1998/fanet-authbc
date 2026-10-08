"""The arithmetic of the traffic-source comparison (docs/NMAX_DIRECT_EXPECTATIONS.md, F4).

Whether the two sources differ is a question for the simulator. What is held here is that the
statistic the registration names is the one the script computes, and that a campaign which has
not finished cannot be scored.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("source_difference",
                                               REPO / "analysis" / "source_difference.py")
assert _spec and _spec.loader
sd = importlib.util.module_from_spec(_spec)
sys.modules["source_difference"] = sd
_spec.loader.exec_module(sd)


def _runs(cell: str, n: int, fps: float, jitter: str, values: dict[int, float]) -> list[dict]:
    return [{"cell": cell, "n_nodes": str(n), "frames_per_s": str(fps), "seed": str(seed),
             "delivered_frac": str(v), "jitter_ms": jitter, "skew_ppm": "0"}
            for seed, v in values.items()]


class TestWhichRunsAreCompared:
    def test_zero_jitter_is_periodic_and_one_period_is_redrawn(self) -> None:
        runs = _runs("A", 29, 50.0, "0", {1: 0.9}) + _runs("A", 29, 50.0, "20", {1: 0.95}) \
            + _runs("A", 29, 50.0, "1", {1: 0.5})                     # neither source
        assert dict(sd.by_source(runs)[("A", 29)]) == {"periodic": {1: 0.9}, "redrawn": {1: 0.95}}

    def test_a_period_is_matched_as_the_result_file_holds_it(self) -> None:
        runs = _runs("SE", 34, 50.5, "19.802", {1: 0.95})
        assert "redrawn" in sd.by_source(runs)[("SE", 34)]

    def test_a_run_with_a_rate_offset_belongs_to_neither(self) -> None:
        runs = _runs("A", 29, 50.0, "0", {1: 0.9})
        runs[0]["skew_ppm"] = "5000"
        assert not sd.by_source(runs)


class TestTheStatistic:
    SEEDS = {"periodic": range(1, 5), "redrawn": range(1, 3)}

    def _samples(self) -> dict:
        runs = _runs("A", 29, 50.0, "0", {1: 0.90, 2: 0.94, 3: 0.92, 4: 0.96}) \
            + _runs("A", 29, 50.0, "20", {1: 0.95, 2: 0.97}) \
            + _runs("D", 120, 12.5, "0", {1: 0.94, 2: 0.96, 3: 0.94, 4: 0.96}) \
            + _runs("D", 120, 12.5, "80", {1: 0.95, 2: 0.95})
        return sd.by_source(runs)

    def test_d_is_the_mean_of_the_per_point_differences(self) -> None:
        got = sd.difference(self._samples(), self.SEEDS)
        assert got.per_point == pytest.approx({("A", 29): 0.03, ("D", 120): 0.0})
        assert (got.points, got.d) == (2, pytest.approx(0.015))

    def test_the_standard_error_is_propagated_from_the_spread_between_runs(self) -> None:
        # point A: var 0.000667/4 + 0.0002/2 ; point D: 0.000133/4 + 0
        expected = math.sqrt(0.0006666667 / 4 + 0.0002 / 2 + 0.0001333333 / 4) / 2
        assert sd.difference(self._samples(), self.SEEDS).se == pytest.approx(expected, rel=1e-6)

    def test_a_point_missing_one_seed_is_left_out_whole(self) -> None:
        samples = self._samples()
        del samples[("D", 120)]["periodic"][4]
        assert set(sd.difference(samples, self.SEEDS).per_point) == {("A", 29)}

    def test_nothing_to_score_is_an_error_not_a_zero(self) -> None:
        with pytest.raises(ValueError):
            sd.difference(self._samples(), {"periodic": range(31, 35), "redrawn": range(31, 33)})

    def test_two_estimates_combine_by_inverse_variance(self) -> None:
        a = sd.Difference(14, 0.003, 0.0014, {})
        b = sd.Difference(14, 0.0, 0.0010, {})
        d, se = sd.combine(a, b)
        assert se == pytest.approx(1 / math.sqrt(1 / 0.0014 ** 2 + 1 / 0.0010 ** 2))
        assert d == pytest.approx(0.003 * (1 / 0.0014 ** 2) / (1 / 0.0014 ** 2 + 1 / 0.0010 ** 2))


class TestTheSampleAlreadyReported:
    """Seeds 1–30, as quoted in the paper and in the registration of F4."""

    FIRST = sd.difference(sd.by_source(sd.read(sd.FIRST)), sd.FIRST_SEEDS)

    def test_fourteen_points_were_run_under_both_sources(self) -> None:
        assert self.FIRST.points == 14

    def test_the_difference_and_its_standard_error(self) -> None:
        assert round(self.FIRST.d, 4) == 0.0031 and round(self.FIRST.se, 4) == 0.0014
