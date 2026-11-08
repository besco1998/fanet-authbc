"""W1m: W1j's powers first, W1i's tuning rule on W1j's 1 dB grid after a balance NO-GO
(analysis/dsss_w1m.py, predictions/W1m.md).

Held here, before any W1m preflight:
* the grid is auto, then 14 … 4 dBm in 1 dB steps, so W1j's 1100 mBm and its neighbours are on it;
* the rule is W1i's word for word, on this grid: on W1i's own test cases it moves the same Pis
  in the same directions, one 1 dB rung instead of one 2 dB rung;
* on W1l's NO-GO reading at W1j's powers it lowers pi-A and the Pi 3 by 1 dB each;
* only a preflight that fails on balance alone is a tuning step; any other failure is NO-GO;
* the session's preflight is W1k's, unchanged (1.5x), and W1m's score is W1j's.

Everything is checked on files made up for the purpose, except W1l's four measured losses.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


w1m = _load("dsss_w1m", REPO / "analysis" / "dsss_w1m.py")
w1i = w1m.w1i
T_PF = _load("t_hw_preflight_w1m", REPO / "tests" / "test_hw_preflight.py")
W1J = {1: 600, 2: None, 3: 1100}                        # W1j's and W1k's registered powers
W1L_PF2 = {1: 3.49, 2: 6.18, 3: 4.06, 4: 5.63}           # W1l preflight 2, G31, 1.769x


class TestTheGrid:
    def test_auto_on_top_then_14_to_4_dbm_in_1_db_steps(self) -> None:
        assert w1m.GRID[0] is None
        assert w1m.GRID[1:] == tuple(range(1400, 399, -100))

    def test_w1js_powers_and_their_neighbours_are_on_it(self) -> None:
        for p in (500, 600, 700, 1000, 1100, 1200):
            assert p in w1m.GRID

    def test_the_target_and_floor_are_w1is(self) -> None:
        assert w1m.TUNE_TARGET == w1i.TUNE_TARGET == 1.25
        assert w1m.GRID[-1] == w1i.LADDER[-1] == 400


class TestTheRule:
    def test_w1ls_no_go_lowers_pi_a_and_the_pi_3_by_1_db(self) -> None:
        new, act = w1m.next_powers(W1L_PF2, W1J)
        assert act.startswith("ADJUST") and new == {1: 500, 2: None, 3: 1000}

    def test_within_target_is_balanced_and_nothing_moves(self) -> None:
        new, act = w1m.next_powers({1: 5.0, 2: 5.2, 3: 6.0, 4: 5.5}, W1J)
        assert act == "BALANCED" and new == W1J

    @pytest.mark.parametrize("losses, start", [
        ({1: 4.22, 2: 5.10, 3: 6.32, 4: 5.98}, {1: 800, 2: 800, 3: None}),
        ({1: 5.0, 2: 5.0, 3: 6.0, 4: 2.0}, {1: 800, 2: 800, 3: None}),
        ({1: 7.5, 2: 5.0, 3: 6.5, 4: 6.2}, {1: 600, 2: 800, 3: None}),
        ({1: 6.0, 2: 6.0, 3: 6.0, 4: 2.0}, {1: None, 2: None, 3: None}),
        (W1L_PF2, {1: 600, 2: None, 3: 1000}),
    ])
    def test_w1is_rule_on_a_finer_grid_moves_the_same_pis_the_same_way(self, losses, start) -> None:
        old, act_old = w1i.next_powers(losses, start)
        new, act_new = w1m.next_powers(losses, start)
        assert act_old.split(":")[0] == act_new.split(":")[0]

        def sign(before, after, grid):
            i, j = grid.index(before), grid.index(after)
            return (j > i) - (j < i)
        for n in (1, 2, 3):
            assert sign(start[n], new[n], w1m.GRID) == sign(start[n], old[n], w1i.LADDER)

    def test_one_rung_is_1_db(self) -> None:
        new, _ = w1m.next_powers({1: 2.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 1100, 2: None, 3: None})
        assert new[1] == 1000
        new, _ = w1m.next_powers({1: 9.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 1100, 2: None, 3: None})
        assert new[1] == 1200

    def test_auto_is_the_top_and_400_the_floor(self) -> None:
        new, act = w1m.next_powers({1: 2.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 400, 2: None, 3: None})
        assert act.startswith("STOP") and new[1] == 400
        new, _ = w1m.next_powers({1: 9.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 1400, 2: None, 3: None})
        assert new[1] is None

    def test_a_too_strong_pi_at_auto_comes_down_to_14_dbm(self) -> None:
        new, act = w1m.next_powers({1: 6.0, 2: 2.0, 3: 6.0, 4: 6.0}, W1J)
        assert act.startswith("ADJUST") and new[2] == 1400


class TestOneStep:
    def test_a_preflight_within_target_is_tuned(self, tmp_path) -> None:
        verdict, new, _ = w1m.step(T_PF._run(tmp_path), {1: None, 2: 800, 3: None})
        assert verdict == "TUNED" and new == {1: None, 2: 800, 3: None}

    def test_an_unbalanced_one_says_adjust_with_the_next_powers(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        verdict, new, rows = w1m.step(d, {1: None, 2: 800, 3: None})
        assert verdict == "ADJUST" and new[1] == 1400
        assert rows[-1]["check"] == "tune" and rows[-1]["group"] == w1i.format_powers(new)

    def test_any_other_failure_is_no_go_not_a_tuning_step(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, cycle={3: 2.78e-3}, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        assert w1m.step(d, {1: None, 2: 800, 3: None})[0] == "NO-GO"

    def test_pis_too_fast_after_a_boot_retry(self, tmp_path) -> None:
        assert w1m.step(T_PF._run(tmp_path, fast=(3,)), {1: None, 2: 800, 3: None})[0] == "RETRY"


class TestUnchanged:
    def test_the_score_and_the_plan_are_w1js(self) -> None:
        assert w1m.score_session is w1i.score_session
        assert w1m.PLAN == w1i.PLAN == w1i.w1h.PLAN
