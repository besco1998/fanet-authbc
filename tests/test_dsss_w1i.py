"""W1i: the adaptive preflight's tuning rule, one tuning step, and the score (analysis/dsss_w1i.py).

Held here, before any tuning run:
* the rule: too-strong Pis (loss below L_max / 1.25) go down one rung, held Pis go up when the
  TP-Link is too strong or when they are the weakest, BALANCED within 1.25x, STOP if nothing moves;
* on a toy plant fitted to the two 120 cm preflights of W1h, the rule converges from where W1h
  ended within the five steps allowed;
* a tuning step says TUNED, ADJUST, NO-GO or RETRY from the preflight's own files;
* the score is W1g's with V6 checked for every held Pi at its own setting; W1h's plan unchanged.

Everything is checked on files and plants made up for the purpose.
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


w1i = _load("dsss_w1i", REPO / "analysis" / "dsss_w1i.py")
T_PF = _load("t_hw_preflight", REPO / "tests" / "test_hw_preflight.py")
T_W1H = _load("t_dsss_w1h", REPO / "tests" / "test_dsss_w1h.py")
w1h, w1g, w1f = w1i.w1h, w1i.w1g, w1i.w1f
START = {1: 800, 2: 800, 3: None}                       # where W1h ended


class TestThePowers:
    def test_round_trip(self) -> None:
        assert w1i.parse_powers("1:600,2:800,3:auto") == {1: 600, 2: 800, 3: None}
        assert w1i.format_powers({3: None, 1: 600, 2: 800}) == "1:600,2:800,3:auto"
        assert w1i.held({1: 600, 2: 800, 3: None}) == {1: 600, 2: 800}


class TestTheRule:
    def test_within_target_is_balanced_and_nothing_moves(self) -> None:
        new, act = w1i.next_powers({1: 5.0, 2: 5.2, 3: 6.0, 4: 5.5}, START)
        assert act == "BALANCED" and new == START

    def test_too_strong_pis_go_down_one_rung(self) -> None:
        # W1h's 120 cm preflight with pi-A and pi-B at 800: pi-A 4.22 < 6.32 / 1.25
        new, act = w1i.next_powers({1: 4.22, 2: 5.10, 3: 6.32, 4: 5.98}, START)
        assert act.startswith("ADJUST") and new == {1: 600, 2: 800, 3: None}

    def test_a_too_strong_tplink_raises_the_held_pis(self) -> None:
        new, act = w1i.next_powers({1: 5.0, 2: 5.0, 3: 6.0, 4: 2.0}, START)
        assert act.startswith("ADJUST") and new == {1: 1000, 2: 1000, 3: None}

    def test_the_weakest_held_pi_goes_up_while_the_strongest_goes_down(self) -> None:
        # beyond 1.25x the strongest is always too strong, so the two moves come together
        new, _ = w1i.next_powers({1: 7.5, 2: 5.0, 3: 6.5, 4: 6.2}, {1: 600, 2: 800, 3: None})
        assert new == {1: 800, 2: 600, 3: None}

    def test_auto_is_the_top_and_400_the_floor(self) -> None:
        new, act = w1i.next_powers({1: 2.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 400, 2: None, 3: None})
        assert act.startswith("STOP") and new[1] == 400
        new, _ = w1i.next_powers({1: 9.0, 2: 6.0, 3: 6.0, 4: 6.0}, {1: 1000, 2: None, 3: None})
        assert new[1] is None

    def test_nothing_movable_stops(self) -> None:
        new, act = w1i.next_powers({1: 6.0, 2: 6.0, 3: 6.0, 4: 2.0}, {1: None, 2: None, 3: None})
        assert act.startswith("STOP") and new == {1: None, 2: None, 3: None}


# A toy plant: loss = a + c * others / (own + others), own = gain * 10^(dBm / 10). Fitted (crudely)
# to W1h's two preflights at 120 cm; `auto` taken as 19 dBm; the TP-Link fixed.
DB = {None: 19.0, 1000: 10.0, 800: 8.0, 600: 6.0, 400: 4.0}


def _plant(gains: dict[int, float], tplink: float, a: float = 2.0, c: float = 4.0):
    def losses(p):
        w = {s: gains[s] * 10 ** (DB[p[s]] / 10) for s in (1, 2, 3)} | {4: tplink}
        return {s: a + c * sum(v for j, v in w.items() if j != s)
                / (w[s] + sum(v for j, v in w.items() if j != s)) for s in w}
    return losses


def _tune(plant, powers):
    for k in range(w1i.MAX_STEPS):
        powers, act = w1i.next_powers(plant(powers), powers)
        if not act.startswith("ADJUST"):
            return k, act, powers
    return w1i.MAX_STEPS, "not tuned", powers


class TestConvergence:
    @pytest.mark.parametrize("start", [START, {1: None, 2: 800, 3: None}])
    def test_from_where_w1h_ended_within_five_steps(self, start) -> None:
        plant = _plant({1: 0.4, 2: 0.4, 3: 0.005}, tplink=1.0)
        k, act, powers = _tune(plant, dict(start))
        losses = plant(powers)
        assert act == "BALANCED" and k <= w1i.MAX_STEPS
        assert max(losses.values()) <= w1i.TUNE_TARGET * min(losses.values())

    def test_a_tplink_too_strong_for_software_stops_rather_than_loops(self) -> None:
        k, act, _ = _tune(_plant({1: 0.4, 2: 0.4, 3: 0.005}, tplink=200.0), dict(START))
        assert act.startswith("STOP") or act == "BALANCED"


class TestOneStep:
    def test_a_balanced_preflight_is_tuned(self, tmp_path) -> None:
        verdict, new, _ = w1i.step(T_PF._run(tmp_path), {1: None, 2: 800, 3: None})
        assert verdict == "TUNED" and new == {1: None, 2: 800, 3: None}

    def test_an_unbalanced_one_says_adjust_with_the_next_powers(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        verdict, new, rows = w1i.step(d, {1: None, 2: 800, 3: None})
        assert verdict == "ADJUST" and new[1] == 1000
        assert rows[-1]["check"] == "tune" and rows[-1]["group"] == w1i.format_powers(new)

    def test_any_other_failure_is_no_go_not_a_tuning_step(self, tmp_path) -> None:
        d = T_PF._run(tmp_path, cycle={3: 2.78e-3}, factors={1: 0.70, 2: 1.0, 3: 1.25, 4: 1.15})
        assert w1i.step(d, {1: None, 2: 800, 3: None})[0] == "NO-GO"

    def test_pis_too_fast_after_a_boot_retry(self, tmp_path) -> None:
        assert w1i.step(T_PF._run(tmp_path, fast=(3,)), {1: None, 2: 800, 3: None})[0] == "RETRY"


class TestTheScore:
    def test_valid_with_every_held_log_and_void_without_one(self, tmp_path) -> None:
        d = T_W1H._session(tmp_path)                       # writes node2's log at 800 only
        _, rows = w1i.score_session(d, {1: None, 2: 800, 3: None})
        assert next(r for r in rows if r["what"] == "session")["held"] is True
        _, rows = w1i.score_session(d, {1: 600, 2: 800, 3: None})
        assert next(r for r in rows if r["what"] == "session")["held"] is False
        assert next(r for r in rows if r["what"] == "node1 at 6 dBm (V6)")["held"] is False

    def test_the_plan_is_w1hs(self) -> None:
        assert w1i.PLAN == w1h.PLAN
