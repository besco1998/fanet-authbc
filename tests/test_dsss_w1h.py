"""W1h: W1g's session preceded, on the same Blue 2 boot, by a balance gate (analysis/dsss_w1h.py).

Held here, before any attempt:
* the plan: the rate checks, four gate windows at W1g's A31 line, W1g's capacity block verbatim,
  the rate checks again;
* the gate says GO only with the four rate checks before in band, node 4 joined at 1 Mb/s, all
  four gate windows complete and usable, and the senders within 1.5x of each other;
* the score is W1g's, unchanged: the gate windows reach neither a point nor b.

Everything is checked on files made up for the purpose.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_w1h", REPO / "analysis" / "dsss_w1h.py")
assert _spec and _spec.loader
w1h = importlib.util.module_from_spec(_spec)
sys.modules["dsss_w1h"] = w1h
_spec.loader.exec_module(w1h)
w1g, w1f, w1d = w1h.w1g, w1h.w1f, w1h.w1d

POINTS = ["A29", "P9", "A30", "P9.25", "A31", "P9.5", "A32", "P9.75"]


def _body() -> list[str]:
    return [ln for ln in w1h.plan() if not ln.startswith("#")]


def _w1g_body() -> list[str]:
    return [ln for ln in w1g.plan() if not ln.startswith("#")]


class TestThePlan:
    def test_fifty_two_windows_in_the_registered_order(self) -> None:
        lines = _body()
        assert len(lines) == 52
        assert [ln.split()[0] for ln in lines[:4]] == ["R1", "R2", "R3", "R4"]
        assert [ln.split()[0] for ln in lines[4:8]] == ["G31"] * 4
        assert [ln.split()[0] for ln in lines[-4:]] == ["R1", "R2", "R3", "R4"]
        assert w1h.plan()[0] == "# nodes: 1,2,3"

    def test_the_gate_is_w1gs_a31_line_relabelled(self) -> None:
        a31 = next(ln for ln in _w1g_body() if ln.startswith("A31 "))
        assert set(_body()[4:8]) == {"G" + a31[1:]}

    def test_w1gs_session_is_carried_verbatim(self) -> None:
        assert _body()[:4] == _w1g_body()[:4]
        assert _body()[8:] == _w1g_body()[4:]

    def test_the_committed_plan_file_is_the_plan(self) -> None:
        assert w1h.PLAN.read_text() == "\n".join(w1h.plan()) + "\n"


# ------------------------------------------------------------------------------ made-up sessions
GOOD_META = {"bssid": "be:6c:1c:9d:1b:10", "rate_ctl": "FIXED CCK_1M 0x00 0",
             "peers_reachable": [1, 2, 3]}
GOOD_LOG = ("2026-11-06T10:00:00+02:00 set 800: txpower 8.00 dBm\n"
            "2026-11-06T10:30:00+02:00 auto: txpower 31.00 dBm\n")
BALANCED = {1: 1.10, 2: 0.95, 3: 1.05, 4: 0.90}     # spread 1.22
DOMINANT = {1: 1.30, 2: 1.00, 3: 1.20, 4: 0.25}     # the TP-Link wins: spread 5.2


def _w(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _loss(label: str) -> float:
    """Made-up mean loss: the curve falls through 5 % (V = 0.95) between its 2nd and 3rd points."""
    label = "A31" if label == "G31" else label
    return [0.030, 0.042, 0.058, 0.075][POINTS.index(label) // 2]


def _session(d: Path, factors: dict[int, float] = BALANCED, cycle_s: float = 1.95e-3,
             upto: int | None = None, gate_extra: float = 0.0, bssid: str = GOOD_META["bssid"],
             skip: tuple[int, int] | None = None) -> Path:
    """Write a session's files; `upto` stops after that many windows (the gate's eight).

    `gate_extra` adds loss to the gate windows only, to show they reach nothing scored.
    """
    for k, line in enumerate(_body()[:upto]):
        label, rate, _bytes, senders_s = line.split()
        senders = [int(s) for s in senders_s.split(",")]
        tag, fps = f"{k:02d}_{label}_{rate}fps", float(rate)
        for node in range(1, 5):
            if skip == (k, node):
                continue
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
                    extra = gate_extra if label == "G31" else 0.0
                    recv = round(sent * (1 - _loss(label) * factors[s] - extra))
                    span = 21.99
                by[f"10.0.0.{s}"] = {"received_unique": recv, "duplicates": 0, "min_seq": 0,
                                     "max_seq": sent - 1, "span_s": span}
            _w(d, "rx", node, tag, {"received_unique": 0, "by_source": by})
            if node in senders:
                sent = 11000 if fps >= 600 else (1100 if fps == 50 else round(fps * 22))
                _w(d, "tx", node, tag, {"sent": sent, "achieved_fps": min(fps, 500),
                                        "late": 9000 if fps >= 600 else 0})
            ctr = {"senders": senders_s, "tx_dropped": 0}
            ctr |= ({"boot_before": "b3f826e2", "boot_after": "b3f826e2",
                     "bssid": bssid, "rate_ctl": GOOD_META["rate_ctl"]} if node == 4
                    else {"throttled_before": "0x0", "throttled_after": "0x0"})
            _w(d, "ctr", node, tag, ctr)
    (d / "node4").mkdir(parents=True, exist_ok=True)
    (d / "node4" / "meta_node4_join.json").write_text(json.dumps(GOOD_META | {"bssid": bssid}))
    (d / "node2").mkdir(parents=True, exist_ok=True)
    (d / "node2" / "txpower.log").write_text(GOOD_LOG)
    return d


def _row(rows: list[dict], what: str, group: str | None = None) -> dict:
    return next(r for r in rows if r["what"] == what and (group is None or r["group"] == group))


class TestTheGate:
    def test_a_balanced_boot_says_go(self, tmp_path) -> None:
        rows, go = w1h.gate(_session(tmp_path, upto=8))
        assert go is True
        assert _row(rows, "gate: senders balanced")["measured"] == pytest.approx(1.10 / 0.90,
                                                                                 abs=0.01)
        assert _row(rows, "gate: windows usable")["measured"] == "4/4"

    def test_a_dominant_tplink_says_abort(self, tmp_path) -> None:
        rows, go = w1h.gate(_session(tmp_path, factors=DOMINANT, upto=8))
        assert go is False
        assert _row(rows, "gate: senders balanced")["held"] is False

    def test_a_rate_check_out_of_band_says_abort(self, tmp_path) -> None:
        assert w1h.gate(_session(tmp_path, cycle_s=2.78e-3, upto=8))[1] is False

    def test_node_4_in_its_own_cell_says_abort(self, tmp_path) -> None:
        assert w1h.gate(_session(tmp_path, bssid="02:11:87:00:00:01", upto=8))[1] is False

    def test_a_missing_gate_file_says_abort(self, tmp_path) -> None:
        rows, go = w1h.gate(_session(tmp_path, upto=8, skip=(6, 3)))
        assert go is False
        assert _row(rows, "gate: windows usable")["measured"] == "3/4"

    def test_nothing_fetched_says_abort(self, tmp_path) -> None:
        assert w1h.gate(tmp_path)[1] is False

    def test_the_gate_reads_only_the_rate_checks_before_and_its_own_windows(self, tmp_path):
        # The same verdict from the whole session as from the first eight windows.
        whole = w1h.gate(_session(tmp_path / "whole"))
        first = w1h.gate(_session(tmp_path / "first", upto=8))
        assert whole[1] is first[1] is True
        assert ([r["measured"] for r in whole[0]] == [r["measured"] for r in first[0]])


class TestTheScore:
    def test_a_balanced_session_is_valid_and_matches_w1gs_score_of_the_same_windows(self, tmp_path):
        rows = w1h.score(_session(tmp_path))[1]
        assert _row(rows, "session")["held"] is True
        xa, xp = _row(rows, "crossing", "AUTHBC"), _row(rows, "crossing", "per-record")
        assert 30 < xa["measured"] < 31 and 9.25 < xp["measured"] < 9.5
        assert _row(rows, "gate (reported, not scored)")["held"] is True

    def test_gate_windows_reach_neither_the_background_nor_a_point(self, tmp_path) -> None:
        clean = w1h.score(_session(tmp_path / "a"))[1]
        noisy = w1h.score(_session(tmp_path / "b", gate_extra=0.30))[1]
        assert _row(noisy, "background")["measured"] == _row(clean, "background")["measured"]
        assert [r["measured"] for r in noisy if r["what"] in ("crossing", "ratio")] == \
               [r["measured"] for r in clean if r["what"] in ("crossing", "ratio")]
        assert _row(noisy, "session")["held"] is True

    def test_the_session_is_judged_on_its_own_a31_not_the_gate(self, tmp_path) -> None:
        # Balanced at the gate, unbalanced at the session's A31: void on V5.
        d = _session(tmp_path)
        for path in d.rglob("rx_node*_A31_*.json"):
            obj = json.loads(path.read_text())
            src = obj["by_source"].get("10.0.0.4")
            if src:
                src["received_unique"] = round(src["received_unique"] / (1 - 0.058 * 0.9)
                                               * (1 - 0.058 * 0.2))
            path.write_text(json.dumps(obj))
        rows = w1h.score(d)[1]
        assert _row(rows, "gate (reported, not scored)")["held"] is True
        assert _row(rows, "senders balanced (V5)")["held"] is False
        assert _row(rows, "session")["held"] is False
