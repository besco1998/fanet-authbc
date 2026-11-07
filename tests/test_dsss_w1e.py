"""W1e: W1d's contention windows between rate checks (analysis/dsss_w1e.py; predictions/W1e.md).

Held here, before any session: the plan is W1d's S1 unchanged between one rate check per board
before and one after; the predictions are W1d's (so W1c's registered rows); and the session is
void unless all six rate checks lie in the band and the background holds. This is checked on
files made up for the purpose, so the rule is tested apart from any measurement.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_w1e", REPO / "analysis" / "dsss_w1e.py")
assert _spec and _spec.loader
w1e = importlib.util.module_from_spec(_spec)
sys.modules["dsss_w1e"] = w1e
_spec.loader.exec_module(w1e)
w1d = w1e.w1d


class TestThePlan:
    def test_w1ds_windows_between_two_rounds_of_rate_checks(self) -> None:
        lines = [ln for ln in w1e.plan() if not ln.startswith("#")]
        s1 = [ln for ln in w1d.plan_s1() if not ln.startswith("#")]
        assert [ln.split()[0] for ln in lines[:3]] == ["R1", "R2", "R3"]
        assert [ln.split()[0] for ln in lines[-3:]] == ["R1", "R2", "R3"]
        assert lines[3:-3] == s1 and len(lines) == 66
        assert all(ln.split()[2] == "145" for ln in lines)

    def test_the_committed_plan_file_is_the_plan(self) -> None:
        assert w1e.PLAN.read_text() == "\n".join(w1e.plan()) + "\n"


class TestThePredictions:
    def test_the_contention_rows_are_w1ds(self) -> None:
        mine = [r for r in w1e.predict() if r["what"] == "contention"]
        assert mine == [r for r in w1d.predict() if r["what"] == "contention"]
        assert len(mine) == 12

    def test_six_rate_checks_in_the_registered_band(self) -> None:
        marks = [r for r in w1e.predict() if r["what"].startswith("rate check")]
        assert len(marks) == 6
        assert {(r["band_lo"], r["band_hi"]) for r in marks} == {w1d.RATE_BAND_S}


def _write(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _ctr(d: Path, tag: str, senders: str, after: str = "0x0") -> None:
    for n in (1, 2, 3):
        _write(d, "ctr", n, tag, {"senders": senders, "tx_dropped": 0,
                                  "throttled_before": "0x0", "throttled_after": after})


def _rate(d: Path, k: int, node: int, cycle_us: float, after: str = "0x0") -> None:
    tag = f"{k:02d}_R{node}_600fps"
    _write(d, "tx", node, tag, {"sent": 10001, "achieved_fps": 500.0, "late": 0})
    for r in (1, 2, 3):
        if r != node:
            _write(d, "rx", r, tag, {"by_source": {f"10.0.0.{node}": {
                "received_unique": 9950, "min_seq": 0, "max_seq": 10000,
                "span_s": 10000 * cycle_us * 1e-6}}})
    _ctr(d, tag, str(node), after)


def _control(d: Path, k: int, node: int) -> None:
    tag = f"{k:02d}_B{node}_50fps"
    _write(d, "tx", node, tag, {"sent": 1000, "achieved_fps": 50.0, "late": 0})
    for r in (1, 2, 3):
        if r != node:
            _write(d, "rx", r, tag, {"by_source": {f"10.0.0.{node}": {
                "received_unique": 999, "min_seq": 0, "max_seq": 999, "span_s": 20.0}}})
    _ctr(d, tag, str(node))


def _pair(d: Path, k: int) -> None:
    tag = f"{k:02d}_AB_131fps"
    for s in (1, 2):
        _write(d, "tx", s, tag, {"sent": 2882, "achieved_fps": 131.0, "late": 0})
    _write(d, "rx", 1, tag, {"by_source": {"10.0.0.2": {"received_unique": 2876}}})
    _write(d, "rx", 2, tag, {"by_source": {"10.0.0.1": {"received_unique": 2876}}})
    _write(d, "rx", 3, tag, {"by_source": {}})
    _ctr(d, tag, "1,2")


def _session(d: Path, pi3_after_us: float = 2450.0, pi3_after_th: str = "0x0",
             drop_last: bool = False) -> Path:
    k = 0
    for node, cyc in ((1, 1945.0), (2, 1946.0), (3, 2480.0)):
        _rate(d, k, node, cyc)
        k += 1
    for _ in range(4):
        _pair(d, k)
        k += 1
    _control(d, k, 1)
    k += 1
    for node, cyc in ((1, 1944.0), (2, 1947.0), (3, pi3_after_us)):
        if drop_last and node == 3:
            break
        _rate(d, k, node, cyc, pi3_after_th if node == 3 else "0x0")
        k += 1
    return d


def _by(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["what"], []).append(r)
    return out


class TestTheBracket:
    def test_all_six_in_the_band_makes_the_session_valid(self, tmp_path: Path) -> None:
        rows = _by(w1e.score(w1d.window_rows(_session(tmp_path))))
        assert rows["session"][0]["held"] is True
        assert [r["what"] for r in w1e.sentinels(w1d.window_rows(tmp_path))] == \
            ["rate check before"] * 3 + ["rate check after"] * 3
        ab = next(r for r in rows["contention"] if r["group"] == "AB at 131/s")
        assert ab["windows"] == "4/4" and isinstance(ab["held"], bool)

    def test_one_board_slow_at_the_end_voids_the_session(self, tmp_path: Path) -> None:
        rows = _by(w1e.score(w1d.window_rows(_session(tmp_path, pi3_after_us=4714.0))))
        assert rows["session"][0]["held"] is False
        assert [r["held"] for r in rows["rate check after"]] == [True, True, False]
        assert all(str(r["held"]).startswith("void") for r in rows["contention"])

    def test_a_missing_rate_check_voids_the_session(self, tmp_path: Path) -> None:
        rows = _by(w1e.score(w1d.window_rows(_session(tmp_path, drop_last=True))))
        assert len(rows["rate check after"]) == 2
        assert rows["session"][0]["held"] is False

    def test_a_rate_check_that_lost_voltage_does_not_hold(self, tmp_path: Path) -> None:
        rows = _by(w1e.score(w1d.window_rows(_session(tmp_path, pi3_after_th="0x50005"))))
        assert rows["rate check after"][2]["held"] is False
        assert rows["session"][0]["held"] is False

    @pytest.mark.parametrize("cycle_us,held", [(1899.0, False), (1901.0, True),
                                               (2599.0, True), (2601.0, False)])
    def test_the_band_edges_are_w1ds(self, tmp_path: Path, cycle_us: float, held: bool) -> None:
        rows = _by(w1e.score(w1d.window_rows(_session(tmp_path, pi3_after_us=cycle_us))))
        assert rows["rate check after"][2]["held"] is held
