"""W1q's plan and scoring (analysis/w1q.py) on synthetic counts with a known q."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
import w1q  # noqa: E402


def _rx(received: dict[int, dict[int, int]], first: int = 10, span: dict[int, int] | None = None
        ) -> dict[int, dict]:
    """received[r][s] = frames of sender s received at r; every receiver spans span[s] frames."""
    span = span or {}
    return {r: {"by_source": {f"10.0.0.{s}": {"received_unique": n, "min_seq": first,
                                               "max_seq": first + span.get(s, n) - 1}
                              for s, n in by.items()}} for r, by in received.items()}


class TestTheIdentification:
    def test_q_is_recovered_from_the_partners_collision_rate(self) -> None:
        on, p_a, q_a, ell_b, ell_3 = 7000, 0.30, 0.80, 0.002, 0.004
        at_b = round(on * (1 - p_a) * (1 - ell_b))             # the partner hears no collided frame
        at_3 = round(on * (1 - (p_a * (1 - q_a) + ell_3)))
        rx = _rx({2: {1: at_b}, 3: {1: at_3}}, span={1: on})
        lo = w1q.losses(rx, 1)
        q = w1q.q_of(lo[3], ell_3, lo[2], ell_b)
        assert q == pytest.approx(q_a, abs=0.01)

    def test_frames_on_air_are_the_widest_span_over_receivers(self) -> None:
        rx = {2: {"by_source": {"10.0.0.1": {"received_unique": 90, "min_seq": 5,
                                             "max_seq": 104}}},
              3: {"by_source": {"10.0.0.1": {"received_unique": 95, "min_seq": 3,
                                             "max_seq": 110}}}}
        assert w1q.on_air(rx, 1) == 108

    def test_no_collisions_at_the_partner_is_not_a_q(self) -> None:
        with pytest.raises(ValueError):
            w1q.q_of(0.01, 0.01, 0.002, 0.002)


class TestTheScore:
    def test_a_large_difference_needs_the_stronger_frame_kept(self) -> None:
        assert w1q.score_step(8.0, 0.95, 0.02)["q_strong_held"] is True
        assert w1q.score_step(-8.0, 0.60, 0.02)["q_strong_held"] is False

    def test_a_small_difference_needs_both_lost(self) -> None:
        assert w1q.score_step(1.0, 0.05, 0.01)["q_strong_held"] is True
        assert w1q.score_step(2.5, 0.40, 0.01)["q_strong_held"] is False

    def test_the_edge_is_reported_not_scored(self) -> None:
        assert w1q.score_step(4.2, 0.5, 0.0)["q_strong_held"].startswith("reported")

    def test_the_weaker_frame_is_never_kept(self) -> None:
        assert w1q.score_step(10.0, 1.0, 0.2)["q_weak_held"] is False

    @pytest.mark.parametrize(("measured", "ok"), [(-48.0, True), (-47.0, True), (-46.0, False),
                                                   (-49.4, True), (-50.0, False)])
    def test_a_step_is_void_unless_the_signal_falls_by_it(self, measured: float, ok: bool) -> None:
        assert w1q.step_valid(measured, -42.0, 6) is ok


class TestThePlan:
    def test_five_steps_each_alone_twice_and_three_pair_windows(self) -> None:
        body = [ln for ln in w1q.plan() if not ln.startswith("#")]
        pair = [ln for ln in body if ln.startswith("C")]
        assert len(pair) == 5 * 3 and all(ln.split()[1] == "600" for ln in pair)
        powers = [ln.split()[5] for ln in body if ln.startswith("A")]
        assert powers == ["1:1500,2:1500", "1:1200", "1:900", "1:500", "1:0"]
        assert body[:3] == body[-3:] and all(ln.startswith("R") for ln in body[:3])


class TestTheSessionScore:
    """A synthetic evening whose truth is ns-3's rule exactly: ΔRSSI at the Pi 3 is 4 − d dB."""

    P_C, ELL = 0.17, 0.002

    def _session(self, tmp_path: Path, honoured: bool = True) -> Path:
        import random

        import hw_synth
        rng = random.Random(5)
        rssi_a = {d: -40.0 - (d if honoured or d < 10 else 2) for d in w1q.STEPS_DB}
        rssi_b = -44.0
        wins: list = []

        def alone(label: str, s: int, step: int) -> None:
            times = [(q * 0.02 + rng.uniform(0, 1e-3)) * 1e9 for q in range(1100)]
            got = {(s, r): {q for q in range(1100) if rng.random() > self.ELL}
                   for r in (1, 2, 3) if r != s}
            wins.append(hw_synth.Window(label, 50, (s,), 25, {s: times}, got))
            wins[-1].step = step                                  # type: ignore[attr-defined]

        for n in (1, 2, 3):
            alone(f"R{n}", n, 0)
        for d in w1q.STEPS_DB:
            alone(f"A{d}", 1, d)
            alone(f"B{d}", 2, d)
            sir = rssi_a[d] - rssi_b
            q_a = 1.0 if sir >= 4 else 0.0
            q_b = 1.0 if sir <= -4 else 0.0
            for _ in range(w1q.CAPTURE_WINDOWS):
                times, got = {}, {}
                for s, partner, q in ((1, 2, q_a), (2, 1, q_b)):
                    n = 6300
                    times[s] = [(i / 288.0) * 1e9 for i in range(n)]
                    coll = {i for i in range(1, n - 1) if rng.random() < self.P_C}
                    got[(s, partner)] = {i for i in range(n)
                                         if i not in coll and rng.random() > self.ELL}
                    got[(s, 3)] = {i for i in range(n) if (i not in coll or rng.random() < q)
                                   and rng.random() > self.ELL}
                wins.append(hw_synth.Window(f"C{d}", 600, (1, 2), 25, times, got))
                wins[-1].step = d                                 # type: ignore[attr-defined]
        for w in wins:
            if w.label.startswith("R"):
                w.times = {w.senders[0]: [(i / 470.0) * 1e9 for i in range(len(
                    next(iter(w.times.values()))))]}

        def rssi(r: int, w: object) -> dict[str, object]:
            d = w.step                                            # type: ignore[attr-defined]
            peers = {1: {2: -50.0, 3: -52.0}, 2: {1: -50.0, 3: -55.0},
                     3: {1: rssi_a[d], 2: rssi_b}}[r]
            s = w.senders[0]                                      # type: ignore[attr-defined]
            return {"any": str(peers.get(s, -60.0)), "peers": {p: str(v) for p, v in peers.items()}}
        return hw_synth.write_session(tmp_path / "w1q_synthetic", (1, 2, 3), wins,
                                      lambda r, t: 1_795_000_000_000_000_000 + round(t), rssi)

    def test_every_step_scores_as_the_rule_says(self, tmp_path: Path) -> None:
        rows = w1q.score(self._session(tmp_path))
        steps = {r["item"].split()[0]: r for r in rows if r["what"] == "step"}
        assert steps["0"]["held"] == "weak True, strong reported (3–5 dB)"
        for d in ("3", "6", "10", "15"):
            assert steps[d]["held"] == "weak True, strong True", (d, steps[d])
        kit = next(r for r in rows if r["what"].startswith("kit check"))
        assert kit["measured"] == "accepted"
        choice = next(r for r in rows if r["what"] == "the optional step, by the rule")
        assert choice["measured"] == 0

    def test_q_is_recovered_at_each_step(self, tmp_path: Path) -> None:
        rows = w1q.score(self._session(tmp_path))
        ten = next(r for r in rows if r["what"] == "step" and r["item"].startswith("10 "))
        q_b = float(ten["measured"].split("q_B ")[1].split()[0])
        q_a = float(ten["measured"].split("q_A ")[1].split()[0])
        assert q_b == pytest.approx(1.0, abs=0.05) and q_a == pytest.approx(0.0, abs=0.05)

    def test_a_step_the_chip_did_not_honour_is_void(self, tmp_path: Path) -> None:
        rows = w1q.score(self._session(tmp_path, honoured=False))
        steps = {r["item"].split()[0]: r["held"] for r in rows if r["what"] == "step"}
        assert steps["10"].startswith("void") and steps["15"].startswith("void")
        assert not steps["6"].startswith("void")
