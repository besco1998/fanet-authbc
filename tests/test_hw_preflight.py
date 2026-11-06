"""The preflight before every long hardware run (analysis/hw_preflight.py; hw/channel/README.md).

Held here: six windows (R1-R4, G31 x2) checked mechanically, GO only if
1. every Pi broadcasts at 1 Mb/s: its rate check in band and limited by the channel, not by itself;
2. the TP-Link at 1 Mb/s: `rate_ctl` fixed at join and its rate check in band;
3. pi-B held at 8 dBm and returned to auto;
4. node 4 in the Pis' cell, all Pis reached, Blue 2 on one boot throughout;
5. no Pi under-voltage;
6. the senders within 1.5x of each other at G31.
A run whose failing Pis were all sender-limited (6 Mb/s, their first ad-hoc session after a boot;
F129) and otherwise fine asks for one retry.

Everything is checked on files made up for the purpose.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hw_preflight",
                                               REPO / "analysis" / "hw_preflight.py")
assert _spec and _spec.loader
pf = importlib.util.module_from_spec(_spec)
sys.modules["hw_preflight"] = pf
_spec.loader.exec_module(pf)
w1g, w1f, w1d = pf.w1g, pf.w1f, pf.w1d

META = {"bssid": "be:6c:1c:9d:1b:10", "rate_ctl": "FIXED CCK_1M 0x00 0", "boot": "b3f826e2",
        "peers_reachable": [1, 2, 3]}
LOG = ("2026-11-06T14:00:00+02:00 set 800: txpower 8.00 dBm\n"
       "2026-11-06T14:03:30+02:00 auto: txpower 31.00 dBm\n")
BALANCED = {1: 1.10, 2: 0.95, 3: 1.05, 4: 0.90}
CYCLE = {1: 1.946e-3, 2: 1.946e-3, 3: 2.30e-3, 4: 1.958e-3}


def _w(d: Path, kind: str, node: int, tag: str, obj: dict) -> None:
    (d / f"node{node}").mkdir(parents=True, exist_ok=True)
    (d / f"node{node}" / f"{kind}_node{node}_{tag}.json").write_text(json.dumps(obj))


def _run(d: Path, cycle: dict[int, float] | None = None, fast: tuple[int, ...] = (),
         factors: dict[int, float] = BALANCED, meta: dict = META, log: str | None = LOG,
         reset_at: int | None = None, undervolt_at: int | None = None) -> Path:
    """A made-up preflight. `fast` Pis send at the offered 600/s (sender-limited, F129)."""
    cycle = CYCLE | (cycle or {})
    for k, line in enumerate(ln for ln in pf.plan() if not ln.startswith("#")):
        label, rate, _bytes, senders_s = line.split()
        senders = [int(s) for s in senders_s.split(",")]
        tag, fps = f"{k:02d}_{label}_{rate}fps", float(rate)
        for node in range(1, 5):
            by = {}
            for s in senders:
                if s == node:
                    continue
                if w1d.RATE_CHECK.fullmatch(label):
                    c = 1 / fps if s in fast else cycle[s]
                    sent = round(22 / c)
                    by[f"10.0.0.{s}"] = {"received_unique": sent - 5, "duplicates": 0,
                                         "min_seq": 0, "max_seq": sent - 1,
                                         "span_s": c * (sent - 1)}
                else:
                    sent = round(fps * 22)
                    by[f"10.0.0.{s}"] = {"received_unique": round(sent * (1 - 0.05 * factors[s])),
                                         "duplicates": 0, "min_seq": 0, "max_seq": sent - 1,
                                         "span_s": 21.99}
            _w(d, "rx", node, tag, {"received_unique": 0, "by_source": by})
            if node in senders:
                if w1d.RATE_CHECK.fullmatch(label):
                    c = 1 / fps if node in fast else cycle[node]
                    sent, ach = round(22 / c), 1 / c
                else:
                    sent, ach = round(fps * 22), fps
                _w(d, "tx", node, tag, {"sent": sent, "achieved_fps": ach,
                                        "late": 0 if ach >= 0.98 * fps else 9000})
            ctr: dict = {"senders": senders_s, "tx_dropped": 0}
            if node == 4:
                after = "c0ffee00" if reset_at is not None and k >= reset_at else meta["boot"]
                before = "c0ffee00" if reset_at is not None and k > reset_at else meta["boot"]
                ctr |= {"boot_before": before, "boot_after": after, "bssid": meta["bssid"],
                        "rate_ctl": meta["rate_ctl"]}
            else:
                thr = "0x50005" if undervolt_at == k and node == 1 else "0x0"
                ctr |= {"throttled_before": "0x0", "throttled_after": thr}
            _w(d, "ctr", node, tag, ctr)
    (d / "node4" / "meta_node4_join.json").write_text(json.dumps(meta))
    if log is not None:
        (d / "node2" / "txpower.log").write_text(log)
    return d


def _held(rows: list[dict], number: int) -> list[bool]:
    return [r["held"] for r in rows if r["check"] == number]


class TestThePlan:
    def test_six_windows_r1_to_r4_then_two_gate_windows(self) -> None:
        body = [ln for ln in pf.plan() if not ln.startswith("#")]
        assert [ln.split()[0] for ln in body] == ["R1", "R2", "R3", "R4", "G31", "G31"]
        assert pf.plan()[0] == "# nodes: 1,2,3"

    def test_the_gate_line_is_w1gs_a31_line_relabelled(self) -> None:
        a31 = next(ln for ln in w1g.plan() if ln.startswith("A31 "))
        assert pf.plan()[-1] == "G" + a31[1:]

    def test_the_committed_plan_file_is_the_plan(self) -> None:
        assert pf.PLAN.read_text() == "\n".join(pf.plan()) + "\n"


class TestTheVerdict:
    def test_a_good_run_is_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path))
        assert verdict == "GO", [r for r in rows if r["held"] is not True]
        assert sorted({r["check"] for r in rows}) == [1, 2, 3, 4, 5, 6]

    def test_pis_at_6_mbps_ask_for_one_retry(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, fast=(1, 2, 3)))
        assert verdict == "RETRY"
        assert _held(rows, 1) == [False, False, False]
        assert all("sender-limited" in r["note"] for r in rows if r["check"] == 1)

    def test_one_freshly_booted_pi_alone_asks_for_one_retry(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, fast=(3,)))
        assert verdict == "RETRY" and _held(rows, 1) == [True, True, False]

    def test_one_pi_too_slow_is_no_go_without_retry(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, cycle={3: 2.78e-3}))
        assert verdict == "NO-GO"
        assert _held(rows, 1) == [True, True, False]

    def test_pis_fast_and_another_fault_is_no_go(self, tmp_path) -> None:
        assert pf.check(_run(tmp_path, fast=(1, 2, 3), log=""))[1] == "NO-GO"

    def test_the_tplink_rate_not_fixed_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, meta=META | {"rate_ctl": "AUTO"}))
        assert verdict == "NO-GO" and False in _held(rows, 2)

    def test_the_tplink_rate_check_out_of_band_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, cycle={4: 1.2e-3}))
        assert verdict == "NO-GO" and False in _held(rows, 2)

    def test_pi_b_power_missing_or_wrong_is_no_go(self, tmp_path) -> None:
        assert pf.check(_run(tmp_path / "a", log=None))[1] == "NO-GO"
        wrong = LOG.replace("8.00 dBm", "31.00 dBm")
        rows, verdict = pf.check(_run(tmp_path / "b", log=wrong))
        assert verdict == "NO-GO" and _held(rows, 3) == [False]

    def test_pi_a_held_too_needs_its_own_log(self, tmp_path) -> None:
        d = _run(tmp_path)
        assert pf.check(d, held_at_8dbm=(1, 2))[1] == "NO-GO"
        (d / "node1" / "txpower.log").write_text(LOG)
        rows, verdict = pf.check(d, held_at_8dbm=(1, 2))
        assert verdict == "GO" and _held(rows, 3) == [True, True]

    def test_node_4_in_its_own_cell_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, meta=META | {"bssid": "02:11:87:00:00:01"}))
        assert verdict == "NO-GO" and False in _held(rows, 4)

    def test_a_blue_2_reset_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, reset_at=4))
        assert verdict == "NO-GO" and False in _held(rows, 4)

    def test_under_voltage_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, undervolt_at=5))
        assert verdict == "NO-GO" and _held(rows, 5) == [False]

    def test_a_spread_of_two_is_no_go(self, tmp_path) -> None:
        rows, verdict = pf.check(_run(tmp_path, factors={1: 1.4, 2: 1.0, 3: 1.2, 4: 0.7}))
        assert verdict == "NO-GO" and _held(rows, 6) == [False]

    def test_nothing_collected_is_no_go(self, tmp_path) -> None:
        assert pf.check(tmp_path)[1] == "NO-GO"
