"""W3a: frame loss measured on air, traced frame by frame (analysis/w3a_loss.py).

Held here, before any session:
* the plans: a session is R1, then S A L four times, then R1, with pi-A the only sender;
* a received-sequence list becomes a lost-frame mask of the length the sender sent;
* the statistics: loss, mean burst against the independent value, the length ratio against the
  paper's bit-error model;
* V through the real decoder: for AUTHBC as built (r = 1) it is exactly the share of frames
  received; a dependent design (r = 4) fails only if shown below its independent value;
* the three scored claims hold and fail where they should.

Everything is checked on traces made up for the purpose.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("w3a_loss", REPO / "analysis" / "w3a_loss.py")
assert _spec and _spec.loader
w3a = importlib.util.module_from_spec(_spec)
sys.modules["w3a_loss"] = w3a
_spec.loader.exec_module(w3a)


class TestThePlans:
    def test_a_session_is_r1_then_sal_four_times_then_r1_pi_a_alone(self) -> None:
        body = [ln for ln in w3a.plan() if not ln.startswith("#")]
        assert [ln.split()[0] for ln in body] == ["R1"] + ["S", "A", "L"] * 4 + ["R1"]
        assert {ln.split()[3] for ln in body} == {"1"}
        assert {ln.split()[2] for ln in body if ln[0] in "SAL"} == {"119", "145", "1000"}
        assert w3a.plan()[0] == "# nodes: 1,2,3"

    def test_a_tuning_run_is_r1_and_one_window_of_each_size(self) -> None:
        body = [ln for ln in w3a.plan(tuning=True) if not ln.startswith("#")]
        assert [ln.split()[0] for ln in body] == ["R1", "S", "A", "L"]

    def test_the_sizes_are_the_real_frames(self) -> None:
        # one-record frame 147 B and four-record frame 173 B on the IP layer, less IP/UDP's 28 B
        assert w3a.FRAME_BYTES["S"] - w3a.IP_UDP == w3a.SIZES["S"] == 119
        assert w3a.SIZES["A"] == 145


class TestTheMask:
    def test_received_numbers_become_a_lost_mask_of_the_sent_length(self) -> None:
        m = w3a.lost_mask([0, 1, 3, 4, 7], sent=9)
        assert m.tolist() == [False, False, True, False, False, True, True, False, True]

    def test_numbers_beyond_what_was_sent_are_refused(self) -> None:
        with pytest.raises(ValueError):
            w3a.lost_mask([0, 12], sent=10)


def _iid(p: float, n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).random(n) < p


def _bursty(p: float, burst: float, n: int, seed: int) -> np.ndarray:
    r = 1 / burst
    a = p * r / (1 - p)
    rng, bad, out = np.random.default_rng(seed), False, []
    for _ in range(n):
        bad = (rng.random() >= r) if bad else (rng.random() < a)
        out.append(bad)
    return np.array(out)


class TestTheStatistics:
    def test_independent_loss_has_the_independent_mean_burst(self) -> None:
        masks = [_iid(0.05, 20000, s) for s in range(3)]
        st = w3a.loss_stats(masks)
        assert st["p_hat"] == pytest.approx(0.05, abs=0.004)
        assert st["mean_burst"] == pytest.approx(1 / (1 - 0.05), abs=0.03)

    def test_bursty_loss_shows_its_bursts(self) -> None:
        st = w3a.loss_stats([_bursty(0.05, 6.0, 40000, 1)])
        assert st["mean_burst"] > 4

    def test_the_length_model_ratio_is_the_papers(self) -> None:
        # a 1000 B payload at the bit error rate that loses the one-record frame with 2 %
        ratio = w3a.model_length_ratio(0.02, "L")
        p_l = 1 - (1 - 0.02) ** ((1028 + 36) / (147 + 36))
        assert ratio == pytest.approx(p_l / 0.02)


class TestVThroughTheDecoder:
    def test_r1_is_exactly_the_share_received(self) -> None:
        masks = [_iid(0.08, 300, s) for s in range(2)]
        v = w3a.v_through_decoder(masks, ref=1)
        assert v == [pytest.approx(1 - m.mean(), abs=1e-12) for m in masks]

    def test_r4_is_below_r1_under_loss(self) -> None:
        masks = [_iid(0.08, 300, 3)]
        assert w3a.v_through_decoder(masks, ref=4)[0] < w3a.v_through_decoder(masks, ref=1)[0]


# ------------------------------------------------------------------------- made-up sessions
def _write(d: Path, node: int, kind: str, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _session(d: Path, p: dict[int, float], burst: float | None = None,
             length_power: float = 1.0) -> Path:
    """pi-A sends; receivers 2, 3, 4 lose with p[r] at S, scaled by length at A and L."""
    for k, line in enumerate(ln for ln in w3a.plan() if not ln.startswith("#")):
        label, rate, size, _senders = line.split()
        tag = f"{k:02d}_{label}_{rate}fps"
        sent = 11000 if label == "R1" else int(float(rate) * 22)
        _write(d, 1, "tx", tag, {"sent": sent, "achieved_fps": 50.0, "late": 0})
        for r in (2, 3, 4):
            if label == "R1":
                seqs = list(range(sent))
                span = 1.95e-3 * (sent - 1)
            else:
                scale = 1.0 if label == "S" else (w3a.model_length_ratio(p[r], label)
                                                  ** length_power)
                q = min(p[r] * scale, 0.9)
                seed = 100 * k + r
                m = _bursty(q, burst, sent, seed) if burst else _iid(q, sent, seed)
                seqs = [i for i in range(sent) if not m[i]]
                span = 21.98
            _write(d, r, "rx", tag, {"by_source": {"10.0.0.1": {
                "received_unique": len(seqs), "duplicates": 0, "min_seq": 0,
                "max_seq": sent - 1, "span_s": span, "seqs": seqs}}})
        for n in (1, 2, 3, 4):
            ctr = {"senders": "1", "tx_dropped": 0}
            ctr |= ({"boot_before": "aa", "boot_after": "aa", "bssid": "be:6c:00:00:00:01",
                     "rate_ctl": "FIXED CCK_1M 0x00 0"} if n == 4
                    else {"throttled_before": "0x0", "throttled_after": "0x0"})
            _write(d, n, "ctr", tag, ctr)
    (d / "node1" / "txpower.log").write_text(
        "t set 400: txpower 4.00 dBm\nt auto: txpower 31.00 dBm\n")
    return d


class TestTheScore:
    P = {2: 0.02, 3: 0.05, 4: 0.09}

    def test_independent_loss_at_the_models_length_scaling_holds_all_three(self, tmp_path):
        rows = w3a.score(_session(tmp_path, self.P), mbm=400)
        verdict = {r["what"]: r["held"] for r in rows if r["what"].startswith("W3a-")}
        assert verdict["W3a-2"] is True and verdict["W3a-3"] is True
        assert next(r for r in rows if r["what"] == "session")["held"] is True

    def test_independent_loss_does_not_fail_w3a_1_on_noise(self, tmp_path) -> None:
        rows = w3a.score(_session(tmp_path, self.P), mbm=400)
        assert next(r for r in rows if r["what"] == "W3a-1")["held"] is True

    def test_bursty_loss_helps_the_dependent_design(self, tmp_path) -> None:
        rows = w3a.score(_session(tmp_path, self.P, burst=6.0), mbm=400)
        assert next(r for r in rows if r["what"] == "W3a-1")["held"] is True

    def test_loss_growing_faster_than_the_model_fails_w3a_3(self, tmp_path) -> None:
        rows = w3a.score(_session(tmp_path, self.P, length_power=1.6), mbm=400)
        assert next(r for r in rows if r["what"] == "W3a-3")["held"] is False

    def test_the_power_not_read_back_voids_the_session(self, tmp_path) -> None:
        d = _session(tmp_path, self.P)
        (d / "node1" / "txpower.log").write_text("t set 400: txpower 31.00 dBm\n")
        assert next(r for r in w3a.score(d, mbm=400) if r["what"] == "session")["held"] is False

    def test_a_rate_check_out_of_band_voids_it(self, tmp_path) -> None:
        d = _session(tmp_path, self.P)
        for path in d.glob("node*/rx_node*_00_R1_*.json"):
            obj = json.loads(path.read_text())
            obj["by_source"]["10.0.0.1"]["span_s"] = 1.666e-3 * 10999      # 6 Mb/s, F129
            path.write_text(json.dumps(obj))
        assert next(r for r in w3a.score(d, mbm=400) if r["what"] == "session")["held"] is False


class TestTheReport:
    """Reporting added after the outcome (2026-11-07): the window counts and the interval."""
    P = {2: 0.02, 3: 0.05, 4: 0.09}

    def test_the_windows_add_up_to_the_scored_traces(self, tmp_path) -> None:
        d = _session(tmp_path, self.P)
        rows = w3a.cycles(d, mbm=400)
        assert len(rows) == 3 * 3 * 4                     # receivers x sizes x cycles
        traces = {(r["receiver"], r["size"]): r for r in w3a.score(d, mbm=400)
                  if r["what"] == "trace"}
        for (rx, size), t in traces.items():
            mine = [r for r in rows if r["receiver"] == rx and r["size"] == size]
            assert sum(r["lost"] for r in mine) == t["lost"]
            assert sum(r["sent"] for r in mine) == t["frames"]

    def test_the_interval_holds_the_pooled_ratio_and_repeats_for_its_seed(self, tmp_path) -> None:
        rows = w3a.cycles(_session(tmp_path, self.P), mbm=400)
        pooled, lo, hi = w3a.length_penalty_bootstrap(rows, n=500)
        assert lo < pooled < hi
        assert w3a.length_penalty_bootstrap(rows, n=500) == (pooled, lo, hi)
        assert w3a.length_penalty_bootstrap(rows, seed=1, n=500) != (pooled, lo, hi)

    def test_the_committed_windows_give_the_outcomes_interval(self) -> None:
        """W3a's outcome: 1.24, 95 % 1.06-1.45, over the 36 paired cycles of the three sessions."""
        import csv
        path = REPO / "results" / "raw" / "w3a_w3a_2026-11-06_cycles.csv"
        rows = list(csv.DictReader(ln for ln in path.read_text().splitlines()
                                   if not ln.startswith("#")))
        assert len(rows) == 3 * 3 * 3 * 4
        pooled, lo, hi = w3a.length_penalty_bootstrap(rows)
        assert (round(pooled, 3), round(lo, 3), round(hi, 3)) == (1.242, 1.062, 1.448)
