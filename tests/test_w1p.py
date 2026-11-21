"""W1p's scoring (analysis/w1p.py), on synthetic sessions whose answer is known: the jitter of
each board from three receiver pairs, the saturated pair's decision rule, and the gap moments."""
from __future__ import annotations

import random
import statistics as st
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
import w1p  # noqa: E402


def _stamps(true_ns: list[float], jitter_ns: float, offset_ns: float, ppm: float,
            rng: random.Random) -> dict[int, int]:
    return {s: round(offset_ns + t * (1 + ppm * 1e-6) + rng.gauss(0, jitter_ns))
            for s, t in enumerate(true_ns)}


class TestTheJitter:
    @pytest.mark.parametrize("seed", [7, 8, 9])
    def test_each_boards_jitter_is_recovered_within_its_standard_error(self, seed: int) -> None:
        rng = random.Random(seed)
        j = {"a": 5_000.0, "b": 12_000.0, "c": 25_000.0}             # ns
        clocks = {"a": (1e12, 0.0), "b": (3e11, 41.0), "c": (-5e10, -27.0)}
        n = 50 * w1p.JITTER_S
        v = {}
        for i, k in (("a", "b"), ("a", "c"), ("b", "c")):
            true = [s * 20e6 + rng.uniform(0, 1e6) for s in range(n)]
            ti = _stamps(true, j[i], *clocks[i], rng)
            tk = _stamps(true, j[k], *clocks[k], rng)
            v[i + k] = w1p.pair_variance_ns2(ti, tk)["var_ns2"]
        got = w1p.board_jitter_us(v["ab"], v["ac"], v["bc"])
        se = w1p.board_jitter_sq_se_us2(v["ab"], v["ac"], v["bc"], n)
        for b in "abc":
            sq = got[b] * abs(got[b])
            assert abs(sq - (j[b] / 1e3) ** 2) < 3 * se
        # the two larger jitters are resolved to about 10 %
        assert got["b"] == pytest.approx(12.0, rel=0.15)
        assert got["c"] == pytest.approx(25.0, rel=0.1)

    def test_a_frame_heard_by_one_receiver_only_is_left_out(self) -> None:
        ti = {s: s * 1000 for s in range(100)}
        tk = {s: s * 1000 + 7 for s in range(50, 160)}
        assert w1p.pair_variance_ns2(ti, tk)["frames"] == 50

    def test_too_few_common_frames_is_an_error(self) -> None:
        with pytest.raises(ValueError):
            w1p.pair_variance_ns2({1: 0, 2: 10}, {1: 0, 2: 10})

    def test_a_negative_square_stays_negative(self) -> None:
        assert w1p.board_jitter_us(1e6, 1e6, 9e6)["a"] < 0


class TestThePairRule:
    def test_inside_both_intervals_is_consistent(self) -> None:
        loss = [0.30, 0.31, 0.29, 0.30, 0.32, 0.28]
        fps = [300.0, 302, 298, 301, 299, 300]
        assert w1p.consistent(0.30, 300.0, loss, fps)

    def test_outside_either_interval_is_not(self) -> None:
        loss = [0.30, 0.31, 0.29, 0.30, 0.32, 0.28]
        fps = [300.0, 302, 298, 301, 299, 300]
        assert not w1p.consistent(0.15, 300.0, loss, fps)
        assert not w1p.consistent(0.30, 260.0, loss, fps)

    def test_the_interval_uses_t_with_five_degrees_of_freedom(self) -> None:
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        m, lo, hi = w1p.interval(v)
        assert m == 3.5 and hi - m == pytest.approx(2.571 * st.stdev(v) / 6 ** 0.5)


class TestTheGaps:
    @pytest.mark.parametrize(("family", "w"), [("s20d50", 4), ("s9d28", 12), ("s9d28", 13)])
    def test_the_lattice_moments_are_recovered_through_the_jitter(self, family: str,
                                                                    w: int) -> None:
        rng = random.Random(3)
        slot, difs = w1p.uh.FAMILIES[family]
        mean_us, sd_us = w1p.gap_moments_us(family, w)
        jit_ns = 6_000.0
        t, ts = 0.0, {}
        for s in range(8000):
            ts[s] = round(t * 1e9 + rng.gauss(0, jit_ns))
            t += w1p.T_F_S + difs + slot * rng.randrange(w)
        got = w1p.gap_summary(w1p.gaps_us(ts), jit_ns / 1e3)
        assert got["mean_us"] == pytest.approx(mean_us, abs=1.5)
        assert got["sd_corrected_us"] == pytest.approx(sd_us, rel=0.06)
        assert got["sd_us"] > got["sd_corrected_us"]

    def test_a_missing_frame_does_not_make_a_gap(self) -> None:
        tf = w1p.T_F_S * 1e9
        ts = {0: 0, 1: round(tf + 80e3), 3: round(3 * tf + 240e3)}
        assert w1p.gaps_us(ts) == [pytest.approx(80.0, abs=0.01)]

    def test_the_two_families_share_the_mean_and_differ_in_spread(self) -> None:
        a = w1p.gap_moments_us("s20d50", 4)
        b = w1p.gap_moments_us("s9d28", 12)
        assert abs(a[0] - b[0]) < 3 and b[1] - a[1] > 8


class TestTheKitCheck:
    @staticmethod
    def _windows(values: dict[int, float], follows_last: bool = False) -> dict[int, list[dict]]:
        out = {}
        for j in values:
            rs = []
            for _ in range(2):            # mid and after
                peers = {k: (values[j] if follows_last else values[k]) for k in values}
                rs.append({"any": values[j], "peers": peers})
            out[j] = rs
        return out

    def test_readings_tied_to_the_address_are_accepted(self) -> None:
        assert w1p.per_mac_accepted(self._windows({1: -40.0, 2: -52.0})) == "accepted"

    def test_readings_that_follow_the_last_frame_are_rejected(self) -> None:
        assert w1p.per_mac_accepted(self._windows({1: -40.0, 2: -52.0}, True)) == "rejected"

    def test_peers_too_alike_cannot_show_it(self) -> None:
        assert w1p.per_mac_accepted(self._windows({1: -40.0, 2: -42.0})) == "not shown"


class TestThePlan:
    def test_jitter_first_then_checks_pair_checks(self) -> None:
        body = [ln for ln in w1p.plan() if not ln.startswith("#")]
        assert [ln.split()[0] for ln in body] == (["J1", "J2", "J3", "R1", "R2", "R3"]
                                                  + ["P"] * 6 + ["R1", "R2", "R3"])
        assert all(ln.split()[4] == "60" for ln in body[:3])
        assert all(ln.split()[3] == "1,2" and ln.split()[1] == "600" for ln in body[6:12])


class TestTheSessionScore:
    """A synthetic evening whose truth is the 9 µs family: the scorer must find it."""

    JIT = {1: 4_000.0, 2: 9_000.0, 3: 16_000.0}             # ns
    # kernel clocks: epoch-like offsets (ns), each with its own drift (ppm)
    CLOCK = {1: (1_795_000_000_000_000_000, 0.0), 2: (1_795_000_123_456_789_000, 33.0),
             3: (1_794_999_876_543_210_000, -21.0)}
    RSSI = {1: {2: -38, 3: -47}, 2: {1: -38, 3: -49}, 3: {1: -47, 2: -49}}   # node 3: 2 dB

    def _session(self, tmp_path: Path) -> Path:
        import hw_synth
        rng = random.Random(11)
        slot, difs = w1p.uh.FAMILIES["s9d28"]
        w_of = dict(zip(w1p.NODES, w1p.uh.board_windows("s9d28")[:3], strict=True))
        pred = {r["family"]: r for r in [*_pred_rows()]}
        p_pair = float(pred["s9d28"]["pair_loss"])
        f_pair = float(pred["s9d28"]["pair_air_fps"])
        wins = []

        def solo(label: str, s: int, rate: float, times: list[float], link: float) -> None:
            got = {(s, r): {q for q in range(len(times)) if rng.random() > link}
                   for r in w1p.NODES if r != s}
            wins.append(hw_synth.Window(label, rate, (s,), 60 if label[0] == "J" else 25,
                                        {s: times}, got))

        def lattice(s: int) -> list[float]:
            t, out = 0.0, []
            while t < 22.0:
                out.append(t * 1e9)
                t += w1p.T_F_S + difs + slot * rng.randrange(w_of[s])
            return out

        for s in w1p.NODES:
            solo(f"J{s}", s, 50, [(q * 0.02 + rng.uniform(0, 1e-3)) * 1e9 for q in range(2850)],
                 0.002)
        rate_checks = []
        for s in w1p.NODES:
            solo(f"R{s}", s, 600, lattice(s), 0.001)
            rate_checks.append(wins[-1])
        for _ in range(6):
            fps = rng.gauss(f_pair, 0.6)
            times = {s: [(q / fps + rng.uniform(0, 1e-4)) * 1e9 for q in range(int(22 * fps))]
                     for s in (1, 2)}
            got = {}
            for s, r in ((1, 2), (2, 1)):
                n = len(times[s])
                lost = {q for q in range(1, n - 1) if rng.random() < p_pair}
                got[(s, r)] = set(range(n)) - lost
                got[(s, 3)] = set(range(n))
            wins.append(hw_synth.Window("P", 600, (1, 2), 25, times, got))
        wins += rate_checks

        def stamp(r: int, t: float) -> int:
            off, ppm = self.CLOCK[r]
            return off + round(t * (1 + ppm * 1e-6) + rng.gauss(0, self.JIT[r]))

        def rssi(r: int, w: object) -> dict[str, object]:
            s = w.senders[0]                                     # type: ignore[attr-defined]
            return {"any": str(self.RSSI[r].get(s, -60)),
                    "peers": {p: str(v) for p, v in self.RSSI[r].items()}}
        return hw_synth.write_session(tmp_path / "w1p_synthetic", w1p.NODES, wins, stamp, rssi)

    def test_the_9_us_family_is_found_and_the_20_us_one_is_not(self, tmp_path: Path) -> None:
        rows = w1p.score(self._session(tmp_path))
        fam = {r["item"]: r["held"] for r in rows if r["what"] == "family consistent"}
        assert fam == {"s20d50": False, "s9d28": True}
        assert next(r for r in rows if r["what"] == "family for W1r")["measured"] == "s9d28"
        assert all(r["held"] for r in rows if r["what"] in ("rate check",
                                                          "frame burst off on every board"))

    def test_the_jitter_and_the_kit_check(self, tmp_path: Path) -> None:
        rows = w1p.score(self._session(tmp_path))
        jit = {r["item"]: r["measured"] for r in rows if r["what"] == "timestamp jitter (us)"}
        assert jit["node 2"] == pytest.approx(9.0, rel=0.2)
        assert jit["node 3"] == pytest.approx(16.0, rel=0.1)
        kit = {r["item"]: r["measured"] for r in rows if r["what"] == "kit check: per-peer RSSI"}
        assert kit == {"at node 1": "accepted", "at node 2": "accepted", "at node 3": "not shown"}

    def test_the_gap_spread_is_the_families_after_the_jitter(self, tmp_path: Path) -> None:
        rows = w1p.score(self._session(tmp_path))
        gap = next(r for r in rows if r["item"] == "node 1 at node 2")["measured"]
        corrected = float(gap.split("corrected ")[1].split(",")[0])
        assert corrected == pytest.approx(w1p.gap_moments_us("s9d28", 12)[1], rel=0.1)


def _pred_rows() -> list[dict[str, str]]:
    import csv as _csv
    with w1p.OUT.open() as fh:
        return list(_csv.DictReader(ln for ln in fh if not ln.startswith("#")))
