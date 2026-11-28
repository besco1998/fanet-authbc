"""V1a's sizing, plan and scorer (analysis/v1.py): every point expects its registered lost frames,
the plan interleaves the occupancies, and on a synthetic session whose truth is known the scorer
measures each point's loss and scores the finite-station form at ±15 %."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "tests"), str(REPO / "src")]

import v1  # noqa: E402


class TestTheSizing:
    def test_each_point_expects_its_lost_frames(self) -> None:
        for fps, p in ((52, 0.0017), (70, 0.0027), (87, 0.004), (87, 0.05)):
            s = v1.window_seconds(fps, p)
            lost = v1.ROUNDS * 3 * 2 * fps * (s - 3) * p
            assert lost >= v1.MIN_LOST_POINT and s % 5 == 0 and s >= 25

    def test_the_points_are_w1cs_rates(self) -> None:
        assert v1.POINTS == [(0.3, 52), (0.4, 70), (0.5, 87)]


class TestThePlan:
    ROWS = [{"fps_per_board": f, "seconds": 100 + f} for _u, f in v1.POINTS]

    def test_rounds_interleave_every_occupancy_and_end_with_a_control(self) -> None:
        lines = [ln for ln in v1.plan(self.ROWS) if not ln.startswith("#")]
        assert [ln.split()[0] for ln in lines[:3]] == ["R1", "R2", "R3"]
        assert lines[0].split()[5] == "1:1500,2:1500,3:1500", "15 dBm on every board, first"
        assert all(len(ln.split()) == 5 for ln in lines[1:])
        assert [ln.split()[0] for ln in lines[-3:]] == ["R1", "R2", "R3"]
        body = lines[3:-3]
        assert len(body) == v1.ROUNDS * 4
        for k in range(v1.ROUNDS):
            rnd = body[4 * k : 4 * k + 4]
            assert sorted(int(ln.split()[1]) for ln in rnd[:3]) == [52, 70, 87]
            assert all(ln.split()[0] == "ABC" and ln.split()[3] == "1,2,3" for ln in rnd[:3])
            assert rnd[3].split()[0] == f"B{1 + k % 3}" and rnd[3].split()[1] == "50"
        firsts = [int(body[4 * k].split()[1]) for k in range(v1.ROUNDS)]
        assert len(set(firsts)) == 3, "the order rotates between rounds"
        for ln in body:
            if ln.startswith("ABC"):
                assert int(ln.split()[4]) == 100 + int(ln.split()[1])


@pytest.mark.skipif(not v1.OUT.exists(), reason="V1a's predictions are not written yet")
class TestTheScore:
    B = 0.002

    def _session(self, tmp: Path, factor: dict[int, float]) -> Path:
        """Each point's true contention loss is the finite-station prediction times factor."""
        import hw_synth

        rng = random.Random(28)
        pred = v1._predictions()
        wins = []
        for ln in v1.PLAN.read_text().splitlines():
            if ln.startswith("#"):
                continue
            label, fps_s, _b, senders_s, sec_s = ln.split()[:5]  # sixth: power
            fps, sec = float(fps_s), int(sec_s)
            senders = tuple(int(x) for x in senders_s.split(","))
            n = int(fps * (sec - 3)) if not label.startswith("R") else 11000
            rate = 470.0 if label.startswith("R") else fps
            times = {s: [(i / rate) * 1e9 for i in range(n)] for s in senders}
            p = float(pred[int(fps)]["finite_w32"]) * factor[int(fps)] if label == "ABC" else 0.0
            got = {}
            for s in senders:
                for r in (1, 2, 3):
                    if r != s:
                        got[(s, r)] = {
                            i for i in range(n) if rng.random() > p and rng.random() > self.B
                        }
            wins.append(hw_synth.Window(label, fps, senders, sec, times, got))
        return hw_synth.write_session(
            tmp / "v1a_synthetic",
            (1, 2, 3),
            wins,
            lambda r, t: 1_795_000_000_000_000_000 + round(t),
            lambda r, w: {"any": "-50", "peers": {}},
        )

    def test_held_where_the_truth_is_the_prediction_failed_where_it_is_half_again(
        self, tmp_path: Path
    ) -> None:
        rows = v1.score(self._session(tmp_path, {52: 1.0, 70: 1.0, 87: 1.5}))
        points = {r["item"]: r for r in rows if r["what"] == "point"}
        assert points["ABC at 52/s (u = 0.3)"]["held"] is True
        assert points["ABC at 70/s (u = 0.4)"]["held"] is True
        assert points["ABC at 87/s (u = 0.5)"]["held"] is False
        b = next(r for r in rows if r["what"] == "background b")
        assert abs(b["measured"] - self.B) < 0.0015 and b["held"] is True
        assert all(r["held"] for r in rows if r["what"] in ("rate check", "link loss alone"))
