"""W1s's scorer (`analysis/w1s.py`), on W1q's stored session and on synthetic sessions whose
answer is known: the capture curve and its band, the halfway reading alone, the negative step's
read-back, the pair rule at 345 B, and the fixed-time statistic for the Pi 3."""
from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "analysis"), str(REPO / "tests"), str(REPO / "src"), str(REPO / "ns3")]

import uh  # noqa: E402
import w1p  # noqa: E402
import w1s  # noqa: E402

import hw_synth  # noqa: E402

T_F_NS = w1p.T_F_S * 1e9


# ---- A: the curve ---------------------------------------------------------------------------
class TestTheCurveFromW1q:
    def test_the_points_with_the_halfway_reading(self) -> None:
        pts = {m["step"]: m for m in w1s.curve_points()}
        assert [pts[d]["delta_db"] for d in ("0", "3", "6", "10", "15")] == [7, 3, 0, -3, -6]
        assert pts["0"]["q_a"] == pytest.approx(0.9847, abs=5e-5)
        assert pts["3"]["q_a"] == pytest.approx(0.9373, abs=5e-5)
        assert pts["6"]["q_b"] == pytest.approx(0.5148, abs=5e-5)

    def test_mohameds_criterion_admits_0_3_6_and_refuses_10_and_15(self) -> None:
        enters = {m["step"]: m["enters"] for m in w1s.curve_points()}
        assert enters == {"0": True, "3": True, "6": True, "10": False, "15": False}


CURVE = [(0.0, 0.3111, 0.5148), (3.0, 0.9373, -0.0012), (7.0, 0.9847, 0.0303)]


class TestTheBand:
    def test_at_a_point_with_no_tolerance_it_is_the_point(self) -> None:
        b = w1s.curve_band(CURVE, 3.0, tol=0, widen=0)
        assert b is not None
        assert b["q_a"] == pytest.approx((0.9373, 0.9373))
        assert b["q_b"] == pytest.approx((-0.0012, -0.0012))

    def test_a_vertex_inside_the_window_sets_the_extreme(self) -> None:
        b = w1s.curve_band(CURVE, 4.0, tol=1.5, widen=0)   # 2.5 … 5.5 spans the vertex at 3
        assert b is not None
        assert b["q_b"][0] == pytest.approx(-0.0012)
        assert b["q_a"][1] == pytest.approx(0.9373 + (0.9847 - 0.9373) * 2.5 / 4)

    def test_the_window_is_cut_at_the_span(self) -> None:
        b = w1s.curve_band(CURVE, 1.0, tol=1.5, widen=0.02)   # −0.5 … 2.5 → 0 … 2.5
        assert b is not None
        assert b["q_a"][0] == pytest.approx(0.3111 - 0.02)

    def test_a_negative_step_is_read_on_the_mirror(self) -> None:
        b = w1s.curve_band(CURVE, -3.0, tol=0, widen=0)
        assert b is not None
        assert b["q_a"] == pytest.approx((-0.0012, -0.0012))
        assert b["q_b"] == pytest.approx((0.9373, 0.9373))

    @pytest.mark.parametrize("delta", [7.5, -7.5])
    def test_outside_the_span_is_not_scored(self, delta: float) -> None:
        assert w1s.curve_band(CURVE, delta) is None


# ---- A on a synthetic session: q known, the after-window reading wrong ----------------------
N_SAT, N_ALONE = 4000, 1200


def _alone(label: str, s: int, lost: dict[int, int]) -> hw_synth.Window:
    times = {s: [k * 2e7 for k in range(N_ALONE)]}
    got = {(s, r): set(range(lost.get(r, 0), N_ALONE)) for r in (1, 2, 3) if r != s}
    return hw_synth.Window(label=label, rate=50, senders=(s,), times=times, got=got)


def _pair(label: str, p: float, q: dict[int, float]) -> hw_synth.Window:
    """Both senders saturated; frames 1 … p·n of each collide: lost at the partner, kept at the
    Pi 3 in the share q[s]. The first and last frames arrive everywhere, so every receiver sees
    the whole span on air."""
    m = round(p * N_SAT)
    every = set(range(N_SAT))
    times = {s: [k * 4e6 for k in range(N_SAT)] for s in (1, 2)}
    got = {}
    for s, partner in ((1, 2), (2, 1)):
        got[(s, partner)] = every - set(range(1, m + 1))
        got[(s, 3)] = every - set(range(1, round(m * (1 - q[s])) + 1))
    return hw_synth.Window(label=label, rate=600, senders=(1, 2), times=times, got=got)


def _capture_session(tmp: Path, steps: dict[str, tuple[int, int, dict[int, float]]],
                     log_extra: str = "", link_lost: int = 0) -> Path:
    """steps: label -> (RSSI_A at the Pi 3, RSSI_B, q per sender)."""
    windows = []
    for d, (_ra, _rb, q) in steps.items():
        windows.append(_alone(f"A{d}", 1, {2: link_lost}))
        windows.append(_alone(f"B{d}", 2, {}))
        windows += [_pair(f"C{d}", 0.10, q)] * 3

    def rssi(r: int, w: hw_synth.Window) -> dict[str, object]:
        d = w.label[1:]
        if r != 3 or d not in steps or w.label[0] not in "AB":
            return {"any": "-50", "peers": {}}
        return {"any": str(steps[d][0] if w.label[0] == "A" else steps[d][1]), "peers": {}}

    s = hw_synth.write_session(tmp / "s", (1, 2, 3), windows, stamp=lambda r, t: int(t),
                               rssi=rssi, rssi_after=lambda r, w: {"any": "-30", "peers": {}})
    if log_extra:
        with (s / "node2" / "session.log").open("a") as fh:
            fh.write(log_extra)
    return s


class TestPartAOnASession:
    def test_q_and_delta_are_recovered_from_the_halfway_reading(self, tmp_path: Path) -> None:
        s = _capture_session(tmp_path, {"13": (-43, -48, {1: 0.96, 2: 0.01})})
        m = w1s.measure_step(s, "13")
        assert m["delta_db"] == 5.0          # the after-window −30 would have given 0
        assert m["q_a"] == pytest.approx(0.96, abs=1e-3)
        assert m["q_b"] == pytest.approx(0.01, abs=1e-3)

    def _score(self, tmp_path: Path, q13: dict[int, float], readback: str) -> list[dict]:
        steps = {"15": (-41, -48, {1: 0.985, 2: 0.03}), "13": (-43, -48, q13),
                 "11": (-46, -48, {1: 0.80, 2: 0.10}), "10": (-47, -48, {1: 0.55, 2: 0.30}),
                 "N": (-50, -47, {1: 0.0, 2: 0.94})}      # Δ −3 dB: pi-B the stronger
        s = _capture_session(tmp_path, steps,
                             log_extra=f"[t] txpower asked 1800:  txpower {readback} dBm\n")
        return w1s.score_a(s, CURVE)

    def test_steps_inside_their_bands_make_the_curve_used(self, tmp_path: Path) -> None:
        rows = self._score(tmp_path, {1: 0.96, 2: 0.01}, "18.00")
        assert rows[-1]["held"] == "used" and rows[-1]["item"] == "4 of 4 scored steps held"
        neg = next(r for r in rows if r["item"] == "pi-B 18 dBm, pi-A 15 dBm")
        assert neg["measured"].startswith("Δ -3.0 dB") and neg["predicted"].endswith("(mirrored)")

    def test_the_mirror_is_scored_not_skipped(self, tmp_path: Path) -> None:
        # pi-B 3 dB stronger, but its frames kept as if it were the weaker: the mirror refuses it
        steps = {"15": (-41, -48, {1: 0.985, 2: 0.03}), "N": (-50, -47, {1: 0.94, 2: 0.0})}
        s = _capture_session(tmp_path, steps,
                             log_extra="[t] txpower asked 1800:  txpower 18.00 dBm\n")
        rows = [r for r in w1s.score_a(s, CURVE) if r["item"] == "pi-B 18 dBm, pi-A 15 dBm"]
        assert rows and rows[0]["held"] is False

    def test_one_step_outside_its_band_and_the_curve_is_not_used(self, tmp_path: Path) -> None:
        rows = self._score(tmp_path, {1: 0.50, 2: 0.01}, "18.00")
        assert rows[-1]["held"].startswith("not used")

    def test_a_negative_step_not_read_back_at_18_dbm_is_dropped(self, tmp_path: Path) -> None:
        rows = self._score(tmp_path, {1: 0.96, 2: 0.01}, "17.00")
        neg = next(r for r in rows if r["what"] == "A: negative step")
        assert neg["held"] == "dropped: the curve covers Δ ≥ 0 only"
        assert rows[-1]["item"] == "3 of 3 scored steps held"

    def test_a_step_whose_link_lost_more_than_1_percent_is_not_scored(self, tmp_path: Path
                                                                      ) -> None:
        s = _capture_session(tmp_path, {"13": (-43, -48, {1: 0.96, 2: 0.01})}, link_lost=15)
        assert w1s.measure_step(s, "13")["worst_link"] == pytest.approx(15 / N_ALONE)
        assert w1s.measure_step(s, "13")["worst_link"] > w1s.LINK_MAX


# ---- B: the windows and the pair rule -------------------------------------------------------
class TestPartB:
    def test_the_formula_is_uh_board_windows(self) -> None:
        for fam in uh.FAMILIES:
            assert w1s.windows_from(list(uh.W1F_CYCLES_US), fam) == uh.board_windows(fam)

    def test_the_days_cycles_are_the_six_scored_rate_checks(self) -> None:
        c = w1s.day_cycles_us()
        assert c[1] == [2032.1, 2033.9, 2059.9, 2048.3, 2196.0, 2046.2]
        assert [len(c[n]) for n in (1, 2, 3)] == [6, 6, 6]

    def test_the_registered_windows(self) -> None:
        assert w1s.windows_from(w1s.chosen_cycles("mean"), "s20d50") == [17, 21, 44]
        assert w1s.windows_from(w1s.chosen_cycles("mean"), "s9d28") == [40, 50, 101]

    def test_the_frame_is_345_bytes_of_payload_373_in_ns3(self) -> None:
        assert w1s.FRAME_B == 373

    @staticmethod
    def _pair_session(tmp: Path, loss: float, fps: float) -> Path:
        rng = random.Random(1)
        windows = []
        for _ in range(w1s.PAIR_WINDOWS):
            n = int(fps * 22)
            l_w = loss + rng.uniform(-0.004, 0.004)
            times = {s: [k * 1e9 / fps for k in range(n)] for s in (1, 2)}
            got = {(1, 2): {0, n - 1} | set(range(round(l_w * n), n)),
                   (2, 1): {0, n - 1} | set(range(round(l_w * n), n))}
            windows.append(hw_synth.Window(label="P", rate=600, senders=(1, 2), times=times,
                                           got=got))
        return hw_synth.write_session(tmp / "b", (1, 2, 3), windows, stamp=lambda r, t: int(t),
                                      rssi=lambda r, w: {"any": "-50", "peers": {}})

    def test_the_family_inside_both_intervals_is_chosen(self, tmp_path: Path) -> None:
        s = self._pair_session(tmp_path, 0.10, 135.0)
        pred = {"s20d50": {"loss": 0.10, "fps": 135.0}, "s9d28": {"loss": 0.04, "fps": 150.0}}
        rows = w1s.score_b(s, pred)
        assert rows[-1]["measured"] == "s20d50"

    def test_neither_and_between_is_stated_as_bracketed(self, tmp_path: Path) -> None:
        s = self._pair_session(tmp_path, 0.07, 140.0)
        pred = {"s20d50": {"loss": 0.12, "fps": 132.0}, "s9d28": {"loss": 0.04, "fps": 150.0}}
        verdict = w1s.score_b(s, pred)[-1]["measured"]
        assert verdict.startswith("neither: the window is not identifiable without a frame sniffer")
        assert verdict.endswith("the hardware lies between the two settings")


# ---- C: the fixed time ----------------------------------------------------------------------
class TestPartC:
    @staticmethod
    def _gaps(difs: float, g0: float, slot: float, w: int, n: int, seed: int) -> list[float]:
        rng = random.Random(seed)
        return [difs + g0 + slot * rng.randrange(w) for _ in range(n)]

    def test_median_less_iqr_is_difs_plus_the_fixed_time(self) -> None:
        g = self._gaps(50, 250, 20, 17, 20000, 1)
        assert w1s.fixed_part_us(g) == pytest.approx(300, abs=10)

    def test_a_wide_backoff_leaves_only_difs(self) -> None:
        g = self._gaps(50, 0, 20, 44, 20000, 2)
        assert w1s.fixed_part_us(g) == pytest.approx(50, abs=12)

    @pytest.mark.parametrize(("d", "c", "word"), [(260, 270, "fixed"), (20, 270, "backoff"),
                                                  (135, 270, "unresolved"), (50, 0, "unresolved")])
    def test_the_registered_thirds(self, d: float, c: float, word: str) -> None:
        assert w1s.timing_verdict(d, c).startswith(word)

    def _session(self, tmp: Path, g0_pi3: float, w_pi3: int) -> Path:
        windows = []
        for label, s, g0, w in (("R1", 1, 0, 17), ("S1", 1, 0, 17), ("R3", 3, g0_pi3, w_pi3),
                                ("S3", 3, g0_pi3, w_pi3), ("R2", 2, 0, 21)):
            gaps = self._gaps(50, g0, 20, w, 9000, hash(label) % 1000)
            t, times = 0.0, []
            for g in gaps:
                times.append(t)
                t += T_F_NS + 1e3 * g
            got = {(s, r): set(range(len(times))) for r in (1, 2, 3) if r != s}
            windows.append(hw_synth.Window(label=label, rate=600, senders=(s,),
                                           times={s: times}, got=got))
        return hw_synth.write_session(tmp / "c", (1, 2, 3), windows, stamp=lambda r, t: int(t),
                                      rssi=lambda r, w: {"any": "-50", "peers": {}})

    def test_a_fixed_extra_time_is_found_as_fixed(self, tmp_path: Path) -> None:
        rows = w1s.score_c(self._session(tmp_path, 250, 17))
        assert rows[0]["held"].startswith("fixed per frame")

    def test_a_wider_backoff_is_found_as_backoff(self, tmp_path: Path) -> None:
        rows = w1s.score_c(self._session(tmp_path, 0, 44))
        assert rows[0]["held"].startswith("backoff")


# ---- the plan --------------------------------------------------------------------------------
class TestThePlan:
    def test_the_plan_parses_and_ends_well_before_30_minutes(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.txt"
        plan.write_text("\n".join(w1s.plan()) + "\n")
        run = subprocess.run(["bash", str(REPO / "hw" / "channel" / "run_window_plan2.sh"), "2",
                              "0", str(plan)], env={"DRY": "1", "PATH": "/usr/bin:/bin"},
                             capture_output=True, text=True, check=True)
        lines = run.stdout.splitlines()
        windows = [ln for ln in lines if ln.startswith("window ")]
        assert len(windows) == 42
        session_s = int(lines[-1].split()[1])
        assert session_s - 120 <= 30 * 60
        # pi-B takes 15 dBm at the anchor, 18 dBm at the negative step, 15 dBm again at 345 B
        powers = [ln.split("power ")[1] for ln in windows if not ln.endswith("power -")]
        assert powers == ["1500", "1800", "1500"]

    def test_no_label_is_read_as_a_rate_check_or_a_control_by_mistake(self) -> None:
        import dsss_three as w1d
        labels = {ln.split()[0] for ln in w1s.plan() if not ln.startswith("#")}
        assert {lb for lb in labels if w1d.RATE_CHECK.fullmatch(lb)} == {"R1", "R2", "R3"}
        assert not {lb for lb in labels if w1d.CONTROL.fullmatch(lb)}
