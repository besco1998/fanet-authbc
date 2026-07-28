"""Gate on the P7 broadcast-residual finding (docs/audits/p7.md F9).

Guards the conclusion, not just the code: NS-3's measured DCF internals must keep agreeing with
the slot-exact model and keep disagreeing with the no-ACK Bianchi variant. If someone "fixes" the
ladder back into an independence approximation, or the NS-3 scenario drifts, these fail.

Reads the measured fixture results/raw/ns3_dcf_residual.csv (produced by ns3/dcf_residual.py) —
never re-runs NS-3.
"""

from __future__ import annotations

import csv
import io
import statistics as st
from pathlib import Path

import pytest

from authbc.models import bianchi
from authbc.sim import dcf_ladder

RAW = Path(__file__).resolve().parents[2] / "results" / "raw"
# Shorter than the figure's 3e5 run: p_s is stable to ~0.3 % here, and the effects under test are
# factors of 3–17, so the tolerances below are never Monte-Carlo limited.
_PERIODS = 100_000
_L = 1400.0
_T_BUSY = (bianchi.T_PHY + 8 * (_L + bianchi.MAC_OVH_BYTES) / bianchi.R_BPS
           + bianchi.DIFS + bianchi.DELTA)


def _measured() -> dict[int, dict[str, float]]:
    body = "".join(ln for ln in (RAW / "ns3_dcf_residual.csv").read_text().splitlines(keepends=True)
                   if not ln.startswith("#"))
    rows = [r for r in csv.DictReader(io.StringIO(body)) if r["mode"] == "broadcast"]
    out: dict[int, dict[str, float]] = {}
    for n in sorted({int(r["N"]) for r in rows}):
        rs = [r for r in rows if int(r["N"]) == n]
        out[n] = {k: st.median(float(r[k]) for r in rs)
                  for k in ("goodput_mbps", "busy_per_s", "mean_multiplicity", "p_s_measured",
                            "p_s_independent", "winner_participant_frac", "winner_uniform_frac",
                            "p_succ_after_collision", "p_succ_after_success")}
    return out


def _bianchi_no_ack_p_s(n: int) -> float:
    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    return n * tau * (1.0 - tau) ** (n - 1) / p_tr


def _ladder(n: int) -> dcf_ladder.LadderResult:
    return dcf_ladder.run(n, w=bianchi.W, busy_periods=_PERIODS, head_start=True,
                          t_busy_s=_T_BUSY, slot_s=bianchi.SLOT, payload_bytes=_L, seed=1)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_slot_exact_model_reproduces_measured_p_success(n: int) -> None:
    """The whole finding in one line: the corrected model predicts NS-3's collision statistics."""
    assert _ladder(n).p_success == pytest.approx(_measured()[n]["p_s_measured"], rel=0.05)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_slot_exact_model_reproduces_measured_goodput(n: int) -> None:
    assert _ladder(n).throughput_bps / 1e6 == pytest.approx(
        _measured()[n]["goodput_mbps"], rel=0.03)


def test_no_ack_bianchi_still_fails_at_high_n_and_is_not_quietly_fixed() -> None:
    """The negative result, kept explicit (Law 7): the textbook variant is out by >10× at N=50."""
    m = _measured()
    assert m[50]["p_s_measured"] / _bianchi_no_ack_p_s(50) > 10.0
    assert m[5]["p_s_measured"] / _bianchi_no_ack_p_s(5) == pytest.approx(1.0, abs=0.05)


def test_the_failure_is_correlation_not_access_rate() -> None:
    """Even at NS-3's OWN measured mean multiplicity, independent stations cannot reach the
    measured p_s — so the defect is the decoupling assumption, not the value of τ."""
    m = _measured()[50]
    assert m["p_s_measured"] / m["p_s_independent"] > 5.0


def test_channel_time_arithmetic_was_never_the_problem() -> None:
    """Busy-period rate matches the model to ~1 % at every N: E[slot] and the airtime are right."""
    tau = 2.0 / (bianchi.W + 1)
    for n, meas in _measured().items():
        p_tr = 1.0 - (1.0 - tau) ** n
        e_slot = (1.0 - p_tr) * bianchi.SLOT + p_tr * _T_BUSY
        assert meas["busy_per_s"] == pytest.approx(p_tr / e_slot, rel=0.02), f"N={n}"


def test_head_start_signature_is_present_in_the_measurement() -> None:
    """The mechanism's fingerprints: at N=50 the next transmitter is disproportionately a station
    from the previous busy period, and a collision makes the NEXT period more likely to succeed."""
    m = _measured()[50]
    assert m["winner_participant_frac"] > 2.5 * m["winner_uniform_frac"]
    assert m["p_succ_after_collision"] > 3.0 * m["p_succ_after_success"]
    # At N=5 collisions are rare, so the mechanism must be essentially absent.
    low = _measured()[5]
    assert low["p_succ_after_collision"] == pytest.approx(low["p_succ_after_success"], rel=0.10)
