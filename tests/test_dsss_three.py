"""W1d: three ad-hoc radios at 2.4 GHz (analysis/dsss_three.py; predictions/W1d.md).

What is held here, before any board session: that the contention predictions are W1c's registered
rows, unchanged; that the plans run what the predictions name, below overload; and that the
reducer computes a window's loss, a sender's cycle, the background and the power rule as the
registration defines them — on files made up for the purpose, so the reducer is tested apart
from any measurement (as F73's was).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_three", REPO / "analysis" / "dsss_three.py")
assert _spec and _spec.loader
w1d = importlib.util.module_from_spec(_spec)
sys.modules["dsss_three"] = w1d
_spec.loader.exec_module(w1d)


class TestThePredictionsAreW1cs:
    def test_the_rows_are_registered_ones(self) -> None:
        with w1d.w1c.OUT.open(encoding="utf-8") as fh:
            w1c_rows = {(int(r["n"]), int(r["fps_per_board"])): float(r["model_loss"])
                        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                        if r["what"] == "contention"}
        for r in w1d.predict():
            if r["what"] == "contention":
                n = len(w1d.GROUPS[r["group"]])
                assert r["model_loss"] == w1c_rows[(n, r["fps_per_board"])]

    def test_no_point_is_in_overload(self) -> None:
        for n, rows in w1d.registered_contention().items():
            for _u, fps, _l in rows:
                assert n * fps * w1d.w1c.DSSS_1M.t_broadcast(173) < 1.0


class TestThePlans:
    def test_s1_runs_every_group_at_every_registered_rate(self) -> None:
        lines = [ln.split() for ln in w1d.plan_s1() if not ln.startswith("#")]
        want = {(r["group"], r["fps_per_board"]) for r in w1d.predict()
                if r["what"] == "contention"}
        got = {(label, int(rate)) for label, rate, _b, _s in lines
               if not w1d.CONTROL.fullmatch(label)}
        assert got == want
        assert sum(1 for ln in lines if w1d.CONTROL.fullmatch(ln[0])) == 12
        assert all(b == "145" for _l, _r, b, _s in lines)

    def test_s0_is_the_rate_check_and_the_controls(self) -> None:
        lines = [ln.split() for ln in w1d.plan_s0() if not ln.startswith("#")]
        assert [ln[0] for ln in lines] == ["R1", "R1", "R2", "R2", "R3", "R3", "B1", "B2", "B3"]


def _write(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _rx(sources: dict[int, tuple[int, int, int, float]]) -> dict:
    return {"by_source": {f"10.0.0.{s}": {"received_unique": got, "min_seq": lo, "max_seq": hi,
                                         "span_s": span}
                          for s, (got, lo, hi, span) in sources.items()}}


@pytest.fixture()
def session(tmp_path: Path) -> Path:
    # a rate check: node 1 alone; its receivers span 1000 frames in 2.0 s -> 2000 µs a frame
    tag = "00_R1_600fps"
    _write(tmp_path, "tx", 1, tag, {"sent": 1100, "achieved_fps": 500.0, "late": 0})
    for r in (2, 3):
        _write(tmp_path, "rx", r, tag, _rx({1: (990, 0, 1000, 2.0)}))
    for n in (1, 2, 3):
        _write(tmp_path, "ctr", n, tag, {"senders": "1", "tx_dropped": 0,
                                         "throttled_before": "0x0", "throttled_after": "0x0"})
    # a control: node 2 alone sends 1000, its receivers get 995 and 997
    tag = "01_B2_50fps"
    _write(tmp_path, "tx", 2, tag, {"sent": 1000, "achieved_fps": 50.0, "late": 0})
    _write(tmp_path, "rx", 1, tag, _rx({2: (995, 0, 999, 20.0)}))
    _write(tmp_path, "rx", 3, tag, _rx({2: (997, 0, 999, 20.0)}))
    for n in (1, 2, 3):
        _write(tmp_path, "ctr", n, tag, {"senders": "2", "tx_dropped": 0,
                                         "throttled_before": "0x0", "throttled_after": "0x0"})
    # a pair A-C at 131/s: each sends 2882, each gets 2870 of the other's; node 2 only listens
    for k, th in ((2, "0x0"), (3, "0x0"), (4, "0x50005")):    # the last window lost voltage
        tag = f"0{k}_AC_131fps"
        for s in (1, 3):
            _write(tmp_path, "tx", s, tag, {"sent": 2882, "achieved_fps": 131.0, "late": 0})
        _write(tmp_path, "rx", 1, tag, _rx({3: (2870, 0, 2881, 22.0)}))
        _write(tmp_path, "rx", 3, tag, _rx({1: (2870, 0, 2881, 22.0)}))
        _write(tmp_path, "rx", 2, tag, _rx({1: (2880, 0, 2881, 22.0), 3: (2880, 0, 2881, 22.0)}))
        for n in (1, 2, 3):
            _write(tmp_path, "ctr", n, tag, {"senders": "1,3", "tx_dropped": 0,
                                             "throttled_before": "0x0",
                                             "throttled_after": th if n == 3 else "0x0"})
    return tmp_path


class TestTheReducer:
    def test_the_rate_check_cycle(self, session: Path) -> None:
        w = {r["window"]: r for r in w1d.window_rows(session)}["00_R1_600fps"]
        assert w["cycle_us"] == pytest.approx(2000.0)

    def test_a_control_windows_loss(self, session: Path) -> None:
        w = {r["window"]: r for r in w1d.window_rows(session)}["01_B2_50fps"]
        assert w["loss"] == pytest.approx(1 - 996 / 1000)

    def test_a_pair_counts_only_its_own_receivers(self, session: Path) -> None:
        w = {r["window"]: r for r in w1d.window_rows(session)}["02_AC_131fps"]
        assert w["delivered_frac"] == pytest.approx(2 * 2870 / (2 * 2882))
        assert w["usable"] is True

    def test_a_window_that_lost_voltage_is_not_usable(self, session: Path) -> None:
        w = {r["window"]: r for r in w1d.window_rows(session)}["04_AC_131fps"]
        assert w["power_ok"] is False and w["usable"] is False

    def test_the_score_subtracts_the_background_and_needs_three_windows(self,
                                                                       session: Path) -> None:
        rows = {r["what"] + r["group"]: r for r in w1d.score(w1d.window_rows(session))}
        assert rows["backgroundcontrols"]["measured"] == pytest.approx(0.004)
        ac = rows["contentionAC at 131/s"]
        assert ac["windows"] == "2/3" and str(ac["held"]).startswith("not scored")


def test_a_bc_pair_is_never_taken_for_a_control() -> None:
    assert w1d.CONTROL.fullmatch("B2") and not w1d.CONTROL.fullmatch("BC")
    assert w1d.RATE_CHECK.fullmatch("R3") and not w1d.RATE_CHECK.fullmatch("AB")


class TestThePowerRule:
    @pytest.mark.parametrize("before,after,spoiled", [("0x0", "0x0", False),
                                                      ("0x0", "0x50000", True),
                                                      ("0x50000", "0x50000", False),
                                                      ("0x50000", "0x50005", True)])
    def test_undervoltage(self, before: str, after: str, spoiled: bool) -> None:
        assert w1d._undervoltage(before, after) is spoiled
