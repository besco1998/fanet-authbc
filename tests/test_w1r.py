"""W1r's plan and scoring (analysis/w1r.py): the windows are sized as registered, and on a synthetic
session whose truth is the 9 µs family the scorer finds it consistent and the 20 µs family not."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import w1r  # noqa: E402


class TestTheSizing:
    def test_a_window_gives_each_sender_twenty_five_lost_frames(self) -> None:
        for fps, p in ((131, 0.00129), (222, 0.0143), (87, 0.002)):
            s = w1r.seconds_for(fps, p)
            assert fps * (s - 3) * p >= w1r.MIN_LOST and s % 5 == 0 and s >= 25

    def test_the_registered_plan_matches_the_predictions(self) -> None:
        plan = (w1r.PLAN).read_text().splitlines()
        rows = w1r._predictions()
        for ln in plan:
            if ln.startswith("#"):
                continue
            label, fps, _b, _s, sec = ln.split()
            if (label, int(fps)) in rows:
                assert int(sec) == int(rows[(label, int(fps))]["seconds"])


class TestTheSessionScore:
    B = 0.002

    def _session(self, tmp_path: Path) -> Path:
        import hw_synth
        rng = random.Random(21)
        pred = w1r._predictions()
        wins = []
        for ln in w1r.PLAN.read_text().splitlines():
            if ln.startswith("#"):
                continue
            label, fps_s, _b, senders_s, sec_s = ln.split()
            fps, sec = float(fps_s), int(sec_s)
            senders = tuple(int(x) for x in senders_s.split(","))
            n = int(fps * (sec - 3)) if not label.startswith("R") else 11000
            rate = 470.0 if label.startswith("R") else fps
            times = {s: [(i / rate) * 1e9 for i in range(n)] for s in senders}
            key = (label, int(fps))
            if key in pred:
                per = [float(x) for x in pred[key]["ns3_s9d28_equal_per_sender"].split()]
            else:
                per = [0.0] * len(senders)
            got = {}
            for s, p in zip(senders, per, strict=True):
                for r in (1, 2, 3):
                    if r != s:
                        got[(s, r)] = {i for i in range(n)
                                       if rng.random() > p and rng.random() > self.B}
            wins.append(hw_synth.Window(label, fps, senders, sec, times, got))
        return hw_synth.write_session(tmp_path / "w1r_synthetic", (1, 2, 3), wins,
                                      lambda r, t: 1_795_000_000_000_000_000 + round(t),
                                      lambda r, w: {"any": "-50", "peers": {}})

    def test_the_true_family_is_consistent_and_the_other_is_not(self, tmp_path: Path) -> None:
        session = self._session(tmp_path)
        right = w1r.score(session, "s9d28")
        wrong = w1r.score(session, "s20d50")
        def count(rows: list[dict]) -> int:
            return sum(r["held"] is True for r in rows if r["what"] == "point")
        assert count(right) >= 10 and count(wrong) <= 6
        b = next(r for r in right if r["what"] == "background b")
        assert abs(b["measured"] - self.B) < 0.0015 and b["held"] is True
        assert all(r["held"] for r in right if r["what"] == "rate check")

    def test_without_a_family_nothing_is_scored(self, tmp_path: Path) -> None:
        rows = w1r.score(self._session(tmp_path), None)
        assert all(str(r["held"]).startswith("reported") for r in rows if r["what"] == "point")
