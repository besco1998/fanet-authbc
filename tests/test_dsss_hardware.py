"""W1c: the predictions of the 2.4 GHz hardware campaign (analysis/dsss_hardware.py; W1c.md).

What is held here, before any board session: that every grid point stays below overload (W1b: in
overload a queue's discard policy, not the access rule, decides delivery); that the rate check can
tell 1 Mb/s apart from every other DSSS rate; that the boards' rates are A12's mapping at five
boards; that the boards' UDP payloads put the paper's frames on air; and that each
capacity-equivalent grid brackets its crossing.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_hardware",
                                               REPO / "analysis" / "dsss_hardware.py")
assert _spec and _spec.loader
w1c = importlib.util.module_from_spec(_spec)
sys.modules["dsss_hardware"] = w1c
_spec.loader.exec_module(w1c)

ROWS = list(csv.DictReader(ln for ln in w1c.OUT.read_text().splitlines()
                           if not ln.startswith("#")))


def _of(what: str) -> list[dict[str, str]]:
    return [r for r in ROWS if r["what"] == what]


class TestTheDesign:
    def test_no_grid_point_is_in_overload(self) -> None:
        for r in _of("contention") + _of("capacity-equivalent"):
            assert float(r["offered_load"]) < 1.0, r

    def test_the_rate_check_tells_1_mbps_apart(self) -> None:
        one = w1c.cycle_s(1e6, 173)
        assert one == pytest.approx(2224e-6)
        assert 1.9e-3 < one < 2.6e-3
        assert all(w1c.cycle_s(r, 173) < 1.9e-3 for r in w1c.OTHER_RATES_BPS)

    def test_the_boards_put_the_papers_frames_on_air(self) -> None:
        assert w1c.udp_payload(173) == 145 and w1c.udp_payload(146) == 118

    @pytest.mark.parametrize("design", ["AUTHBC", "per-record"])
    def test_the_board_rates_are_a12s_mapping(self, design: str) -> None:
        f0 = w1c.DESIGNS[design][1]
        for neq in w1c.NEQ_GRID[design]:
            assert 1 + 4 * w1c.board_rate(design, neq) / f0 == pytest.approx(neq)


class TestThePredictionsOnFile:
    @pytest.mark.parametrize("design", ["AUTHBC", "per-record"])
    def test_each_grid_brackets_its_crossing(self, design: str) -> None:
        cross = next(float(r["n_eq"]) for r in _of("crossing") if r["design"] == design)
        grid = w1c.NEQ_GRID[design]
        assert grid[0] < cross < grid[-1]

    def test_the_ratio(self) -> None:
        x = {r["design"]: float(r["n_eq"]) for r in _of("crossing")}
        ratio = float(_of("ratio")[0]["n_eq"])
        assert ratio == pytest.approx(x["AUTHBC"] / x["per-record"], abs=0.002)
