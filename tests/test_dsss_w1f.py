"""W1f: four stations at 2.4 GHz, the capacity ratio (analysis/dsss_w1f.py; predictions/W1f.md).

Held here, before any session:
* the plan: W1c's N = 4 contention rows and the capacity points, between two rounds of rate
  checks;
* the four-board mapping;
* the registered predictions;
* every rule of the score, on files made up for the purpose: the bracket, the background, node 4
  in the Pis' cell at 1 Mb/s, its boot ID, missing files, a crossing outside the grid.

One test reads real files from replay 3 (F126), to check that the reducer takes node 4's files.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dsss_w1f", REPO / "analysis" / "dsss_w1f.py")
assert _spec and _spec.loader
w1f = importlib.util.module_from_spec(_spec)
sys.modules["dsss_w1f"] = w1f
_spec.loader.exec_module(w1f)
w1d, w1c = w1f.w1d, w1f.w1c

CAPACITY_ORDER = ["A24", "P7", "A27", "P8", "A29", "P8.5", "A30", "P9", "A31", "P9.5", "A32"]


def _body() -> list[str]:
    return [ln for ln in w1f.plan() if not ln.startswith("#")]


class TestThePlan:
    def test_seventy_eight_windows_between_two_rounds_of_rate_checks(self) -> None:
        lines = _body()
        assert len(lines) == 78
        assert [ln.split()[0] for ln in lines[:4]] == ["R1", "R2", "R3", "R4"]
        assert [ln.split()[0] for ln in lines[-4:]] == ["R1", "R2", "R3", "R4"]

    def test_the_pis_peer_check_names_only_the_pis(self) -> None:
        assert w1f.plan()[0] == "# nodes: 1,2,3"

    def test_contention_at_w1cs_registered_n4_rates(self) -> None:
        rates = [int(ln.split()[1]) for ln in _body() if ln.startswith("ABCD ")]
        assert rates == [65] * 4 + [91] * 4 + [111] * 4
        assert [fps for _u, fps, _l in w1f.registered_contention()] == [65, 91, 111]

    def test_capacity_points_alternate_and_four_windows_each(self) -> None:
        cap = [ln.split() for ln in _body() if ln[0] in "AP" and not ln.startswith("ABCD")]
        labels = [c[0] for c in cap]
        assert labels == [lab for lab in CAPACITY_ORDER for _ in range(4)]
        assert all(c[3] == "1,2,3,4" for c in cap)
        assert {c[2] for c in cap if c[0].startswith("A")} == {"145"}
        assert {c[2] for c in cap if c[0].startswith("P")} == {"118"}

    def test_a_control_after_every_point_rotating_over_the_four_nodes(self) -> None:
        lines = _body()[4:-4]
        controls = [ln.split() for ln in lines if ln.startswith("B")]
        assert len(controls) == 3 + 11
        assert [c[0] for c in controls] == [f"B{1 + i % 4}" for i in range(14)]
        assert all(c[1] == "50" and c[3] == c[0][1:] for c in controls)
        assert all(lines[i].startswith("B") for i in range(4, len(lines), 5))

    def test_the_committed_plan_file_is_the_plan(self) -> None:
        assert w1f.PLAN.read_text() == "\n".join(w1f.plan()) + "\n"


class TestTheMapping:
    @pytest.mark.parametrize("design", ["AUTHBC", "per-record"])
    def test_each_board_contends_with_the_load_of_neq_minus_one_nodes(self, design) -> None:
        f0 = w1c.DESIGNS[design][1]
        for neq in w1f.NEQ_GRID[design]:
            assert (w1f.N_BOARDS - 1) * w1f.board_rate(design, neq) == pytest.approx((neq - 1) * f0)

    def test_every_point_below_overload(self) -> None:
        loads = [w1f.offered_load(d, n) for d, n in w1f.points()]
        assert max(loads) < 1.0 and min(loads) > 0.5


def _registered_rows() -> list[dict]:
    with w1f.PREDICTIONS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


class TestThePredictions:
    def test_the_contention_rows_are_w1cs(self) -> None:
        mine = [(int(r["fps_per_board"]), float(r["model"])) for r in _registered_rows()
                if r["what"] == "contention"]
        assert mine == [(fps, loss) for _u, fps, loss in w1f.registered_contention()]

    def test_each_crossing_lies_inside_its_grid_with_a_ten_percent_band(self) -> None:
        for r in (r for r in _registered_rows() if r["what"] == "crossing"):
            x, grid = float(r["n_eq"]), w1f.NEQ_GRID[r["design"]]
            assert min(grid) < x < max(grid)
            assert float(r["band_lo"]) == pytest.approx(0.9 * x, abs=1e-3)
            assert float(r["band_hi"]) == pytest.approx(1.1 * x, abs=1e-3)

    def test_the_ratio_is_the_crossings_ratio_and_its_floor_is_2_5(self) -> None:
        rows = _registered_rows()
        x = {r["design"]: float(r["n_eq"]) for r in rows if r["what"] == "crossing"}
        ratio = next(r for r in rows if r["what"] == "ratio")
        assert float(ratio["n_eq"]) == pytest.approx(x["AUTHBC"] / x["per-record"], abs=1e-3)
        assert float(ratio["band_lo"]) >= w1f.RATIO_FLOOR

    def test_eight_rate_checks_in_the_band(self) -> None:
        marks = [r for r in _registered_rows() if r["what"].startswith("rate check")]
        assert len(marks) == 8
        assert {(float(r["band_lo"]), float(r["band_hi"])) for r in marks} == {w1d.RATE_BAND_S}


# ------------------------------------------------------------------------------ made-up sessions
GOOD = {"bssid": "be:6c:1c:9d:1b:10", "rate_ctl": "FIXED CCK_1M 0x00 0", "boot": "8beb5ee8"}


def _w(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _model_v(label: str) -> float:
    """A made-up delivered fraction per capacity point: crosses 0.95 between the 3rd and 4th."""
    rank = CAPACITY_ORDER.index(label) // 2 if label.startswith("A") else \
        (CAPACITY_ORDER.index(label) - 1) // 2
    return [0.985, 0.975, 0.960, 0.940, 0.925, 0.900][rank]


def _session(d: Path, *, cycle_s: float = 1.95e-3, v: dict[str, float] | None = None,
             boot_change_at: int | None = None, drop_node4_rx_at: int | None = None,
             own_cell_at: int | None = None) -> Path:
    for k, line in enumerate(_body()):
        label, rate, nbytes, senders_s = line.split()
        senders = [int(s) for s in senders_s.split(",")]
        tag = f"{k:02d}_{label}_{rate}fps"
        fps = float(rate)
        if w1d.RATE_CHECK.fullmatch(label):
            sent, recv, span = 11000, 10990, cycle_s * 10999
        elif w1d.CONTROL.fullmatch(label):
            sent, recv, span = 1100, 1098, 21.98
        else:
            sent = round(fps * 22)
            frac = (v or {}).get(label, _model_v(label) if label != "ABCD" else 0.99)
            recv, span = round(sent * frac), 21.99
        for node in range(1, 5):
            by = {f"10.0.0.{s}": {"received_unique": recv, "duplicates": 0, "min_seq": 0,
                                  "max_seq": sent - 1, "span_s": span}
                  for s in senders if s != node}
            if not (node == 4 and drop_node4_rx_at == k):
                _w(d, "rx", node, tag, {"received_unique": recv * len(by), "by_source": by})
            if node in senders:
                _w(d, "tx", node, tag, {"sent": sent, "achieved_fps": fps if fps < 600 else 500,
                                        "late": 0 if fps < 600 else 9000})
            ctr = {"senders": senders_s, "tx_dropped": 0}
            if node == 4:
                after = GOOD["boot"] if boot_change_at is None or k < boot_change_at else "deadbeef"
                before = GOOD["boot"] if boot_change_at is None or k <= boot_change_at else after
                ctr |= {"boot_before": before, "boot_after": after,
                        "bssid": "02:11:87:aa:bb:cc" if own_cell_at == k else GOOD["bssid"],
                        "rate_ctl": GOOD["rate_ctl"]}
            else:
                ctr |= {"throttled_before": "0x0", "throttled_after": "0x0"}
            _w(d, "ctr", node, tag, ctr)
    return d


def _score(d: Path, meta: dict | None = None) -> tuple[list[dict], list[dict]]:
    meta = {**GOOD, "peers_reachable": [1, 2, 3]} if meta is None else meta
    windows = w1f.apply_node4_rules(w1f.window_rows(d))
    return windows, w1f.score(windows, meta)


def _row(rows: list[dict], what: str, group: str | None = None) -> dict:
    return next(r for r in rows if r["what"] == what and (group is None or r["group"] == group))


class TestTheScore:
    def test_a_good_session_is_valid_and_its_crossings_and_ratio_are_scored(self, tmp_path) -> None:
        windows, rows = _score(_session(tmp_path))
        assert len(windows) == 78
        assert _row(rows, "session")["held"] is True
        assert all(m["held"] is True for m in rows if m["what"].startswith("rate check"))
        assert _row(rows, "background")["measured"] == pytest.approx(2 / 1100, abs=1e-6)
        xa = _row(rows, "crossing", "AUTHBC")
        xp = _row(rows, "crossing", "per-record")
        b = _row(rows, "background")["measured"]

        def v(lab: str) -> float:   # recomputed here from the windows' own delivered fractions
            return sum(w["delivered_frac"] for w in windows if w["label"] == lab) / 4 / (1 - b)

        va, vb = v("A29"), v("A30")   # the last point above 0.95 and the first below
        assert va > 0.95 > vb
        assert xa["measured"] == pytest.approx(29 + (va - 0.95) / (va - vb), abs=1e-3)
        assert 8.5 < xp["measured"] < 9
        ratio = _row(rows, "ratio")
        assert ratio["measured"] == pytest.approx(xa["measured"] / xp["measured"], abs=1e-3)

    def test_a_rate_check_out_of_the_band_voids_the_session(self, tmp_path) -> None:
        _windows, rows = _score(_session(tmp_path, cycle_s=2.7e-3))
        assert _row(rows, "session")["held"] is False
        assert str(_row(rows, "ratio")["held"]).startswith("void (session)")

    def test_node_4_in_a_cell_of_its_own_at_join_voids_the_session(self, tmp_path) -> None:
        meta = {**GOOD, "bssid": "02:11:87:12:34:56", "peers_reachable": [1, 2, 3]}
        _w, rows = _score(_session(tmp_path), meta)
        assert _row(rows, "node 4 joined the Pis' cell")["held"] is False
        assert _row(rows, "session")["held"] is False

    def test_a_pi_unreached_at_join_voids_the_session(self, tmp_path) -> None:
        _w, rows = _score(_session(tmp_path), {**GOOD, "peers_reachable": [1, 3]})
        assert _row(rows, "session")["held"] is False

    def test_a_rate_not_fixed_at_join_voids_the_session(self, tmp_path) -> None:
        _w, rows = _score(_session(tmp_path), {**GOOD, "rate_ctl": "RA",
                                               "peers_reachable": [1, 2, 3]})
        assert _row(rows, "node 4 rate fixed at join")["held"] is False
        assert _row(rows, "session")["held"] is False

    def test_a_reset_of_blue_2_makes_that_window_and_every_later_one_unusable(self, tmp_path):
        windows, _rows = _score(_session(tmp_path, boot_change_at=40))
        assert all(w["node4_ok"] for w in windows if w1f._index(w) < 40)
        assert not any(w["node4_ok"] for w in windows if w1f._index(w) >= 40)

    def test_a_window_missing_node_4s_files_is_unusable_not_reduced(self, tmp_path) -> None:
        k = _body().index(next(ln for ln in _body() if ln.startswith("A29")))
        windows, rows = _score(_session(tmp_path, drop_node4_rx_at=k))
        w = next(w for w in windows if w1f._index(w) == k)
        assert w["complete"] is False and w["usable"] is False
        assert "delivered_frac" not in w
        assert _row(rows, "capacity-equivalent", "A29")["windows"] == "3/4"
        assert _row(rows, "crossing", "AUTHBC")["windows"].startswith("CI not computed")

    def test_a_window_with_node_4_in_its_own_cell_is_unusable(self, tmp_path) -> None:
        k = _body().index(next(ln for ln in _body() if ln.startswith("P8 ")))
        windows, _rows = _score(_session(tmp_path, own_cell_at=k))
        assert next(w for w in windows if w1f._index(w) == k)["usable"] is False

    def test_a_curve_that_never_falls_to_0_95_leaves_the_crossing_undetermined(self, tmp_path):
        high = {lab: 0.99 for lab in CAPACITY_ORDER}
        _w, rows = _score(_session(tmp_path, v=high))
        assert str(_row(rows, "crossing", "AUTHBC")["held"]).startswith("not determined")
        assert _row(rows, "ratio")["held"] == "not determined"


class TestRealFiles:
    def test_replay_3s_node_4_files_reduce_like_the_pis(self, tmp_path) -> None:
        src = REPO / "results" / "hw" / "channel24" / "diag_freeze_2026-11-05"
        for n in (1, 2):
            (tmp_path / f"node{n}").mkdir()
            for f in (src / "adapter_replay3" / f"node{n}").glob("*.json"):
                (tmp_path / f"node{n}" / f.name).write_bytes(f.read_bytes())
        (tmp_path / "node4").mkdir()
        with tarfile.open(src / "blue2" / "adapter_replay3_jsons.tar") as tar:
            tar.extractall(tmp_path / "node4", filter="data")
        rows = {w["window"]: w for w in w1f.window_rows(tmp_path, nodes={1, 2, 4})}
        assert {"00_F4_1000fps", "03_R1_600fps"} <= set(rows)
        assert 1.9e3 < rows["03_R1_600fps"]["cycle_us"] < 2.1e3
        assert rows["00_F4_1000fps"]["loss"] < 0.01
