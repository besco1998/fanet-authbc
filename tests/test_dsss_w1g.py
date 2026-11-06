"""W1g: balanced senders, the grid moved to bracket both crossings (analysis/dsss_w1g.py).

Held here, before any session:
* the plan: eight capacity points, the designs alternating, between two rounds of rate checks;
* the scored crossings, bands and ratio are W1f's registered values, unchanged;
* the session is void unless the senders are balanced (V5) and pi-B was held at 8 dBm (V6), on top
  of W1f's conditions;
* each sender's loss is computed per sender, as `sender_receiver.py` does.

Everything is checked on files made up for the purpose.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_w1g", REPO / "analysis" / "dsss_w1g.py")
assert _spec and _spec.loader
w1g = importlib.util.module_from_spec(_spec)
sys.modules["dsss_w1g"] = w1g
_spec.loader.exec_module(w1g)
w1f, w1d = w1g.w1f, w1g.w1d

ORDER = ["A29", "P9", "A30", "P9.25", "A31", "P9.5", "A32", "P9.75"]


def _body() -> list[str]:
    return [ln for ln in w1g.plan() if not ln.startswith("#")]


class TestThePlan:
    def test_forty_eight_windows_between_two_rounds_of_rate_checks(self) -> None:
        lines = _body()
        assert len(lines) == 48
        assert [ln.split()[0] for ln in lines[:4]] == ["R1", "R2", "R3", "R4"]
        assert [ln.split()[0] for ln in lines[-4:]] == ["R1", "R2", "R3", "R4"]
        assert w1g.plan()[0] == "# nodes: 1,2,3"

    def test_points_alternate_four_windows_each_then_a_control(self) -> None:
        mid = _body()[4:-4]
        assert [mid[i].split()[0] for i in range(0, 40, 5)] == ORDER
        assert all(mid[i + j] == mid[i] for i in range(0, 40, 5) for j in range(4))
        assert [mid[i].split()[0] for i in range(4, 40, 5)] == [f"B{1 + k % 4}" for k in range(8)]
        assert {ln.split()[2] for ln in mid if ln.startswith("A")} == {"145"}
        assert {ln.split()[2] for ln in mid if ln.startswith("P")} == {"118"}

    def test_every_point_below_overload_and_the_grid_brackets_w1fs_measured_curves(self) -> None:
        loads = [w1f.offered_load(d, n) for d, n in w1g.points()]
        assert max(loads) < 1.0
        # W1f measured the AUTHBC crossing at 31.57 and per-record above 9.5 (F127)
        assert min(w1g.NEQ_GRID["AUTHBC"]) < 31.57 < max(w1g.NEQ_GRID["AUTHBC"])
        assert max(w1g.NEQ_GRID["per-record"]) > 9.5

    def test_the_committed_plan_file_is_the_plan(self) -> None:
        assert w1g.PLAN.read_text() == "\n".join(w1g.plan()) + "\n"


class TestThePredictions:
    def test_the_scored_crossings_and_ratio_are_w1fs_registered_rows(self) -> None:
        with w1g.PREDICTIONS.open(encoding="utf-8") as fh:
            mine = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                    if r["what"] in ("crossing", "ratio")]
        keys = ("what", "design", "n_eq", "band_lo", "band_hi")
        assert [{k: r[k] for k in keys} for r in mine] == \
               [{k: r[k] for k in keys} for r in w1g._w1f_registered_rows()]

    def test_the_model_at_this_grid_is_reported_for_every_point(self) -> None:
        with w1g.PREDICTIONS.open(encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(ln for ln in fh if not ln.startswith("#"))
                    if r["what"].startswith("capacity-equivalent")]
        assert sorted(r["note"] for r in rows) == sorted(ORDER)


# ------------------------------------------------------------------------------ made-up sessions
GOOD_META = {"bssid": "be:6c:1c:9d:1b:10", "rate_ctl": "FIXED CCK_1M 0x00 0",
             "peers_reachable": [1, 2, 3]}
GOOD_LOG = ("2026-11-06T04:00:00+02:00 set 800: txpower 8.00 dBm\n"
            "2026-11-06T04:25:00+02:00 auto: txpower 31.00 dBm\n")
FACTORS = {1: 1.10, 2: 0.95, 3: 1.05, 4: 0.90}     # spread 1.22


def _w(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _point_loss(label: str) -> float:
    """Made-up mean loss per point: falls through 5 % (V = 0.95) between the 2nd and 3rd."""
    return [0.030, 0.042, 0.058, 0.075][ORDER.index(label) // 2]


def _session(d: Path, factors: dict[int, float] = FACTORS, cycle_s: float = 1.95e-3) -> Path:
    for k, line in enumerate(_body()):
        label, rate, _bytes, senders_s = line.split()
        senders = [int(s) for s in senders_s.split(",")]
        tag, fps = f"{k:02d}_{label}_{rate}fps", float(rate)
        for node in range(1, 5):
            by = {}
            for s in senders:
                if s == node:
                    continue
                if w1d.RATE_CHECK.fullmatch(label):
                    sent, recv, span = 11000, 10990, cycle_s * 10999
                elif w1d.CONTROL.fullmatch(label):
                    sent, recv, span = 1100, 1099, 21.98
                else:
                    sent = round(fps * 22)
                    recv, span = round(sent * (1 - _point_loss(label) * factors[s])), 21.99
                by[f"10.0.0.{s}"] = {"received_unique": recv, "duplicates": 0, "min_seq": 0,
                                     "max_seq": sent - 1, "span_s": span}
            _w(d, "rx", node, tag, {"received_unique": 0, "by_source": by})
            if node in senders:
                sent = 11000 if fps >= 600 else (1100 if fps == 50 else round(fps * 22))
                _w(d, "tx", node, tag, {"sent": sent, "achieved_fps": min(fps, 500),
                                        "late": 9000 if fps >= 600 else 0})
            ctr = {"senders": senders_s, "tx_dropped": 0}
            ctr |= ({"boot_before": "b3f826e2", "boot_after": "b3f826e2",
                     "bssid": GOOD_META["bssid"], "rate_ctl": GOOD_META["rate_ctl"]} if node == 4
                    else {"throttled_before": "0x0", "throttled_after": "0x0"})
            _w(d, "ctr", node, tag, ctr)
    return d


def _score(d: Path, meta: dict | None = None, log: str = GOOD_LOG) -> list[dict]:
    windows = w1f.apply_node4_rules(w1f.window_rows(d))
    return w1g.score(windows, GOOD_META if meta is None else meta,
                     w1g.sender_means(d, w1g.SPREAD_LABEL), log)


def _row(rows: list[dict], what: str, group: str | None = None) -> dict:
    return next(r for r in rows if r["what"] == what and (group is None or r["group"] == group))


class TestTheScore:
    def test_sender_means_recover_each_senders_loss(self, tmp_path) -> None:
        m = w1g.sender_means(_session(tmp_path), "A31")
        for s, f in FACTORS.items():
            assert m[s] == pytest.approx(0.058 * f, abs=5e-4)

    def test_a_balanced_session_is_valid_and_both_crossings_are_determined(self, tmp_path):
        rows = _score(_session(tmp_path))
        assert _row(rows, "session")["held"] is True
        spread = _row(rows, "senders balanced (V5)")["measured"]
        assert spread == pytest.approx(1.10 / 0.90, abs=0.01)
        xa, xp = _row(rows, "crossing", "AUTHBC"), _row(rows, "crossing", "per-record")
        assert 30 < xa["measured"] < 31 and 9.25 < xp["measured"] < 9.5
        assert _row(rows, "ratio")["measured"] == pytest.approx(xa["measured"] / xp["measured"],
                                                                abs=1e-3)

    def test_unbalanced_senders_void_the_session(self, tmp_path) -> None:
        rows = _score(_session(tmp_path, factors={1: 1.4, 2: 0.8, 3: 1.0, 4: 0.8}))
        assert _row(rows, "senders balanced (V5)")["held"] is False
        assert _row(rows, "session")["held"] is False
        assert str(_row(rows, "ratio")["held"]).startswith("void (session)")

    @pytest.mark.parametrize("log", ["", "2026-11-06T04:00:00+02:00 set 800: txpower 31.00 dBm\n"
                                         "2026-11-06T04:25:00+02:00 auto: txpower 31.00 dBm\n",
                                     "2026-11-06T04:00:00+02:00 set 800: txpower 8.00 dBm\n"])
    def test_pi_b_not_held_at_8_dbm_and_returned_to_auto_voids_the_session(self, tmp_path, log):
        rows = _score(_session(tmp_path), log=log)
        assert _row(rows, "pi-B at 8 dBm (V6)")["held"] is False
        assert _row(rows, "session")["held"] is False

    def test_w1fs_node_4_and_bracket_rules_still_apply(self, tmp_path) -> None:
        rows = _score(_session(tmp_path, cycle_s=2.7e-3))
        assert _row(rows, "session")["held"] is False
        rows = _score(_session(tmp_path / "b"), meta=GOOD_META | {"bssid": "02:11:87:00:00:01"})
        assert _row(rows, "session")["held"] is False
