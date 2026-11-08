"""W1o: W1m's tuning rule with floors, pi-A >= 500 and the Pi 3 >= 1100 mBm
(analysis/dsss_w1o.py, predictions/W1o.md).

Held here, before any W1o preflight:
* where no Pi would go below its floor, the rule is W1m's exactly;
* a Pi at its floor never goes down, but may still go up;
* on W1n's session-3 preflight (pi-A at 500 and the Pi 3 at 1100, both strong) nothing can move:
  STOP, which ends the series (Mohamed, 2026-11-08);
* on W1n's session-2 preflight it lowers pi-A to 500, as W1m's rule did;
* only a preflight that fails on balance alone is a tuning step; the score is W1j's.

Everything is checked on files made up for the purpose, except W1n's measured losses.
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


w1o = _load("dsss_w1o", REPO / "analysis" / "dsss_w1o.py")
w1m, w1i = w1o.w1m, w1o.w1m.w1i
T_PF = _load("t_hw_preflight_w1o", REPO / "tests" / "test_hw_preflight.py")
W1J = {1: 600, 2: None, 3: 1100}
W1N_S2_PF = {1: 3.96, 2: 5.96, 3: 5.42, 4: 6.18}        # W1n s2 preflight, 1.558x
W1N_S3_PF = {1: 4.16, 2: 5.93, 3: 5.09, 4: 6.74}        # W1n s3 preflight, 1.619x
TUNED_N = {1: 500, 2: None, 3: 1100}                     # W1n's tuned powers


class TestTheFloors:
    def test_pi_a_5_dbm_the_pi_3_11_dbm_pi_b_the_grids(self) -> None:
        assert w1o.FLOORS == {1: 500, 2: 400, 3: 1100}
        assert all(f in w1m.GRID for f in w1o.FLOORS.values())
        assert w1o.GRID == w1m.GRID and w1o.TUNE_TARGET == w1m.TUNE_TARGET == 1.25

    def test_w1n_session_3_cannot_move_and_stops(self) -> None:
        new, act = w1o.next_powers(W1N_S3_PF, TUNED_N)
        assert act.startswith("STOP") and new == TUNED_N
        assert w1m.next_powers(W1N_S3_PF, TUNED_N)[0] == {1: 400, 2: None, 3: 1000}

    def test_w1n_session_2_lowers_pi_a_to_its_floor(self) -> None:
        new, act = w1o.next_powers(W1N_S2_PF, W1J)
        assert act.startswith("ADJUST") and new == TUNED_N
        assert new == w1m.next_powers(W1N_S2_PF, W1J)[0]

    def test_a_pi_at_its_floor_may_still_go_up(self) -> None:
        new, act = w1o.next_powers({1: 8.0, 2: 6.0, 3: 6.0, 4: 6.0}, TUNED_N)
        assert act.startswith("ADJUST") and new[1] == 600

    def test_the_pi_3_at_its_floor_stays_while_pi_a_goes_down(self) -> None:
        new, act = w1o.next_powers({1: 4.0, 2: 6.0, 3: 4.2, 4: 6.0}, {1: 700, 2: None, 3: 1100})
        assert act.startswith("ADJUST") and new == {1: 600, 2: None, 3: 1100}

    def test_pi_b_keeps_the_grids_floor(self) -> None:
        new, _ = w1o.next_powers({1: 6.0, 2: 2.0, 3: 6.0, 4: 6.0}, {1: 600, 2: 500, 3: 1100})
        assert new[2] == 400


class TestOtherwiseW1msRule:
    @pytest.mark.parametrize("losses, start", [
        ({1: 4.22, 2: 5.10, 3: 6.32, 4: 5.98}, {1: 800, 2: 800, 3: None}),
        ({1: 5.0, 2: 5.0, 3: 6.0, 4: 2.0}, {1: 800, 2: 800, 3: None}),
        ({1: 7.5, 2: 5.0, 3: 6.5, 4: 6.2}, {1: 600, 2: 800, 3: None}),
        ({1: 6.0, 2: 6.0, 3: 6.0, 4: 2.0}, {1: None, 2: None, 3: None}),
        ({1: 5.0, 2: 5.2, 3: 6.0, 4: 5.5}, W1J),
        (W1N_S2_PF, W1J),
    ])
    def test_the_same_moves_when_no_floor_binds(self, losses, start) -> None:
        new_o, act_o = w1o.next_powers(losses, start)
        new_m, act_m = w1m.next_powers(losses, start)
        assert new_o == new_m and act_o.split(":")[0] == act_m.split(":")[0]
        if not act_m.startswith("STOP"):            # STOP's wording names the floors; moves match
            assert act_o == act_m


class TestOneStep:
    def test_a_preflight_within_target_is_tuned(self, tmp_path) -> None:
        verdict, new, _ = w1o.step(T_PF._run(tmp_path), {1: None, 2: 800, 3: None})
        assert verdict == "TUNED" and new == {1: None, 2: 800, 3: None}

    def test_an_unbalanced_one_says_adjust_with_the_next_powers(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        verdict, new, rows = w1o.step(d, {1: None, 2: 800, 3: None})
        assert verdict == "ADJUST" and new[1] == 1400
        assert rows[-1]["check"] == "tune" and rows[-1]["group"] == w1i.format_powers(new)

    def test_nothing_movable_at_the_floors_is_stop(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, factors={1: 0.70, 2: 1.0, 3: 0.75, 4: 1.15})
        for n, mbm in ((1, 500), (3, 1100)):        # the held Pis' logs, read back then auto
            (d / f"node{n}" / "txpower.log").write_text(
                f"2026-11-08T17:00:00+02:00 set {mbm}: txpower {mbm / 100:.2f} dBm\n"
                "2026-11-08T17:03:30+02:00 auto: txpower 31.00 dBm\n")
        verdict, new, _ = w1o.step(d, TUNED_N)
        assert verdict == "STOP" and new == TUNED_N

    def test_any_other_failure_is_no_go_not_a_tuning_step(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, cycle={3: 2.78e-3}, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        assert w1o.step(d, {1: None, 2: 800, 3: None})[0] == "NO-GO"

    def test_pis_too_fast_after_a_boot_retry(self, tmp_path) -> None:
        assert w1o.step(T_PF._run(tmp_path, fast=(3,)), {1: None, 2: 800, 3: None})[0] == "RETRY"


class TestUnchanged:
    def test_the_score_and_the_plan_are_w1js(self) -> None:
        assert w1o.score_session is w1i.score_session
        assert w1o.PLAN == w1i.PLAN
