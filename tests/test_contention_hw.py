"""Contention on real radios: the registration, its artifacts and the reducer (open item G4).

docs/CONTENTION_HW_EXPECTATIONS.md was committed before any board was switched on. What is held
here: that the prediction file is what the model gives; that the registration quotes it; that
the ns-3 cross-check says what the registration says it says; and that the reducer turns the
boards' files into a delivered fraction by the definition the simulations use — on files made
up for the purpose, since no measurement exists yet.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "results" / "raw"
DOC = (REPO / "docs" / "CONTENTION_HW_EXPECTATIONS.md").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("contention_hw",
                                               REPO / "analysis" / "contention_hw.py")
assert _spec and _spec.loader
hw = importlib.util.module_from_spec(_spec)
sys.modules["contention_hw"] = hw
_spec.loader.exec_module(hw)


def _rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(ln for ln in (RAW / name).read_text().splitlines()
                               if not ln.startswith("#")))


PREDICTED = _rows("contention_hw_predictions.csv")


class TestThePredictionsAsRegistered:
    def test_twelve_points_at_three_loads_for_two_to_five_boards(self) -> None:
        assert [(int(r["nodes"]), float(r["occupancy_target"])) for r in PREDICTED] == \
            [(n, u) for n in (2, 3, 4, 5) for u in (0.50, 0.70, 0.85)]

    def test_each_rate_fills_the_occupancy_it_names(self) -> None:
        for r in PREDICTED:
            assert float(r["occupancy"]) == pytest.approx(float(r["occupancy_target"]), abs=0.01)
            assert int(r["nodes"]) * int(r["rate_fps_per_node"]) * 2010e-6 == pytest.approx(
                float(r["occupancy"]), abs=1e-3)       # 1976 µs on air + 34 µs DIFS

    def test_the_bands_are_the_registered_multiples_of_the_models_loss(self) -> None:
        for r in PREDICTED:
            lo, hi = (0.6, 1.4) if r["nodes"] == "2" else (0.3, 1.4)
            loss, link = float(r["model_loss"]), float(r["link_loss_added"])
            assert link == 2.3e-4
            assert float(r["predicted_loss"]) == pytest.approx(loss + link, abs=1e-5)
            assert float(r["band_lo"]) == pytest.approx(lo * loss + link, abs=1e-5)
            assert float(r["band_hi"]) == pytest.approx(hi * loss + link, abs=1e-5)

    def test_loss_rises_with_load_and_with_boards(self) -> None:
        loss = {(int(r["nodes"]), float(r["occupancy_target"])): float(r["model_loss"])
                for r in PREDICTED}
        for n in (2, 3, 4, 5):
            assert loss[(n, 0.50)] < loss[(n, 0.70)] < loss[(n, 0.85)]
        for u in (0.50, 0.70, 0.85):
            assert loss[(2, u)] < loss[(3, u)] < loss[(4, u)] < loss[(5, u)]

    def test_the_registration_quotes_every_row(self) -> None:
        for r in PREDICTED:
            line = (f"| {r['nodes']} | {r['rate_fps_per_node']} | "
                    f"{float(r['occupancy_target']):.2f} | "
                    f"**{100 * float(r['predicted_loss']):.2f} %** | "
                    f"{100 * float(r['band_lo']):.2f}–{100 * float(r['band_hi']):.2f} % |")
            assert line in DOC, line

    def test_the_weakest_point_has_the_power_the_registration_claims(self) -> None:
        r = PREDICTED[0]
        frames = 2 * int(r["rate_fps_per_node"]) * 22 * 4
        lost = frames * float(r["model_loss"])
        assert frames == pytest.approx(21_800, rel=0.01) and "21,800" in DOC
        assert 55 < lost < 70 and "about 63 lost" in DOC
        assert lost ** -0.5 == pytest.approx(0.13, abs=0.01)

    @pytest.mark.frozen
    def test_the_file_is_what_the_model_gives(self) -> None:
        fresh = {(r["nodes"], r["rate_fps_per_node"]): r for r in hw.predict(workers=2)}
        for r in PREDICTED:
            again = fresh[(int(r["nodes"]), int(r["rate_fps_per_node"]))]
            assert {k: str(v) for k, v in again.items()} == r


class TestTheTwoSimulationsAgreeAsTheRegistrationSays:
    CHECK = _rows("contention_hw_ns3_check.csv")

    def test_within_five_percent_from_three_boards_up(self) -> None:
        for r in self.CHECK:
            if int(r["nodes"]) >= 3:
                assert abs(float(r["ns3_over_model"]) - 1.0) <= 0.055, r
        assert "At three to five nodes they agree within 5 %" in DOC

    def test_the_model_is_above_ns3_at_two_boards_and_the_band_contains_both(self) -> None:
        two = [float(r["ns3_over_model"]) for r in self.CHECK if r["nodes"] == "2"]
        assert [f"{x:.2f}" for x in two] == ["0.82", "0.84", "0.91"]
        assert "| 2 | 0.82, 0.84, 0.91 |" in DOC and "9–18 % above ns-3" in DOC
        assert all(0.6 < x < 1.4 for x in two)

    def test_the_table_in_the_registration(self) -> None:
        for n in "345":
            cells = ", ".join(f"{float(r['ns3_over_model']):.2f}"
                              for r in self.CHECK if r["nodes"] == n)
            assert f"| {n} | {cells} |" in DOC


def _board_files(tmp: Path, n_nodes: int, rate: int, sent: int, received: int, *,
                 tag: str = "00_C", dropped: int = 0, achieved: float | None = None,
                 late: int = 0) -> list[Path]:
    """Files as `run_adhoc_contention.sh` leaves them, with `received` of `sent` from each peer."""
    dirs = []
    for k in range(1, n_nodes + 1):
        d = tmp / f"node{k}"
        d.mkdir(exist_ok=True)
        name = f"{tag}_{rate}fps"
        (d / f"tx_node{k}_{name}.json").write_text(json.dumps(
            {"sent": sent, "achieved_fps": achieved if achieved is not None else float(rate),
             "rate": float(rate), "late": late, "redraw": True}))
        (d / f"rx_node{k}_{name}.json").write_text(json.dumps(
            {"duplicates": 0, "by_source": {f"10.0.0.{s}": {"received_unique": received}
                                            for s in range(1, n_nodes + 1) if s != k}}))
        (d / f"ctr_node{k}_{name}.json").write_text(json.dumps(
            {"tx_dropped": dropped, "tx_packets": sent, "rx_packets": 0}))
        dirs.append(d)
    return dirs


class TestTheReducer:
    def test_delivered_fraction_is_over_every_ordered_pair(self, tmp_path: Path) -> None:
        (row,) = hw.windows(_board_files(tmp_path, 3, 116, sent=1000, received=985), 3)
        assert (row["sent"], row["received"]) == (3000, 6 * 985)
        assert row["delivered_frac"] == pytest.approx(0.985)
        assert hw.usable(row)

    def test_a_window_is_unusable_if_the_sender_did_not_do_as_asked(self, tmp_path: Path) -> None:
        for i, kwargs in enumerate(({"dropped": 1}, {"achieved": 110.0}, {"late": 40})):
            d = tmp_path / str(i)
            d.mkdir()
            (row,) = hw.windows(_board_files(d, 3, 116, 1000, 985, **kwargs), 3)
            assert not hw.usable(row), kwargs

    def test_a_missing_board_stops_the_reduction(self, tmp_path: Path) -> None:
        dirs = _board_files(tmp_path, 3, 116, 1000, 985)
        next(dirs[2].glob("rx_*")).unlink()
        with pytest.raises(SystemExit, match="expected tx and rx files"):
            hw.windows(dirs, 3)

    def test_scoring_against_the_registered_band(self, tmp_path: Path) -> None:
        reg = {(int(r["nodes"]), int(r["rate_fps_per_node"])): r for r in PREDICTED}
        target = float(reg[(2, 211)]["predicted_loss"])
        inside = tmp_path / "in"
        inside.mkdir()
        dirs = _board_files(inside, 2, 211, sent=10_000, received=round(10_000 * (1 - target)))
        (scored,) = hw.score(hw.windows(dirs, 2))
        assert scored["inside_band"] is True and scored["usable_windows"] == 1
        outside = tmp_path / "out"
        outside.mkdir()
        dirs = _board_files(outside, 2, 211, sent=10_000, received=9_500)
        (scored,) = hw.score(hw.windows(dirs, 2))
        assert scored["inside_band"] is False

    def test_a_rate_that_was_not_registered_cannot_be_scored(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="no registered prediction"):
            hw.score(hw.windows(_board_files(tmp_path, 2, 300, 1000, 990), 2))

    def test_the_commands_start_every_board_on_one_clock(self) -> None:
        lines = hw.commands(3, ["pi@a", "pi@b", "pi@c"], "probe")
        assert lines[0].startswith("START=") and len(lines) == 4
        assert "run_adhoc_contention.sh 2 3 $START 83,116,141 5180 probe" in lines[2]
        with pytest.raises(SystemExit):
            hw.commands(3, ["pi@a"], "full")


class TestTheSenderAndReceiverScripts:
    """`hw/channel/bcast_tx.py` and `bcast_rx.py` run on the boards and import nothing of ours."""

    @staticmethod
    def _load(name: str):  # noqa: ANN205
        spec = importlib.util.spec_from_file_location(name, REPO / "hw" / "channel" / f"{name}.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_periodic_schedule_is_the_one_the_august_measurement_used(self) -> None:
        tx = self._load("bcast_tx")
        assert tx.send_offsets(4, 0.01, redraw=False, seed=1) == [0.0, 0.01, 0.02, 0.03]

    def test_redrawn_instants_fall_one_in_each_period_and_depend_on_the_seed(self) -> None:
        tx = self._load("bcast_tx")
        a = tx.send_offsets(500, 0.008, redraw=True, seed=1)
        assert all(k * 0.008 <= t < (k + 1) * 0.008 for k, t in enumerate(a))
        assert a == tx.send_offsets(500, 0.008, redraw=True, seed=1)
        assert a != tx.send_offsets(500, 0.008, redraw=True, seed=2)
        phases = [t / 0.008 % 1 for t in a]
        assert 0.45 < sum(phases) / len(phases) < 0.55

    def test_a_sender_and_a_receiver_on_the_loopback(self, tmp_path: Path) -> None:
        import subprocess
        import time

        rx = subprocess.Popen([sys.executable, str(REPO / "hw/channel/bcast_rx.py"), "--port",
                               "19997", "--seconds", "3", "--out", str(tmp_path / "rx.json")],
                              stdout=subprocess.DEVNULL)
        time.sleep(0.7)
        subprocess.run([sys.executable, str(REPO / "hw/channel/bcast_tx.py"), "--dest",
                        "127.0.0.1", "--port", "19997", "--rate", "100", "--seconds", "1",
                        "--bytes", "200", "--redraw", "--out", str(tmp_path / "tx.json")],
                       check=True, stdout=subprocess.DEVNULL)
        assert rx.wait(timeout=10) == 0
        sent = json.loads((tmp_path / "tx.json").read_text())
        got = json.loads((tmp_path / "rx.json").read_text())
        assert sent["redraw"] is True and 95 <= sent["sent"] <= 100
        assert got["by_source"]["127.0.0.1"]["received_unique"] == sent["sent"]
        assert got["received_unique"] == sent["sent"] and got["duplicates"] == 0
