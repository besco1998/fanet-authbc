"""Gate on the P7 broadcast finding (docs/audits/p7.md F9, docs/literature/f9_broadcast_dcf.md).

Guards the conclusion, not just the code. NS-3's measured DCF internals must keep agreeing with
**Ma & Chen's published broadcast model** (IEEE TVT 57(6):3757-3768, 2008) and keep disagreeing
with the naive reduction of unicast Bianchi that this project used until P7. If the model is
quietly swapped back, or the NS-3 scenario drifts, these fail.

`sim.dcf_ladder` is retained as an INDEPENDENT cross-check: it was written before the paper was
located, simulates counters only, and agrees with the closed form to <2 %.

Reads the measured fixture results/raw/ns3_dcf_residual.csv (produced by ns3/dcf_residual.py) —
never re-runs NS-3.
"""

from __future__ import annotations

import csv
import io
import statistics as st
from pathlib import Path

import pytest

from authbc.models import bianchi, broadcast_dcf
from authbc.sim import dcf_ladder

RAW = Path(__file__).resolve().parents[2] / "results" / "raw"
# Shorter than the figure's 3e5 run: p_s is stable to ~0.3 % here, and the effects under test are
# factors of 3–17, so the tolerances below are never Monte-Carlo limited.
_PERIODS = 100_000
_L = 1400.0
# Exact 802.11a OFDM busy-period time (audit A1): DATA PPDU + DIFS = 1974 us, measured.
_T_BUSY = bianchi.t_broadcast_exact(_L)


def _measured() -> dict[int, dict[str, float]]:
    body = "".join(ln for ln in (RAW / "ns3_dcf_residual.csv").read_text().splitlines(keepends=True)
                   if not ln.startswith("#"))
    rows = [r for r in csv.DictReader(io.StringIO(body)) if r["mode"] == "broadcast"]
    out: dict[int, dict[str, float]] = {}
    for n in sorted({int(r["N"]) for r in rows}):
        rs = [r for r in rows if int(r["N"]) == n]
        out[n] = {k: st.median(float(r[k]) for r in rs)
                  for k in ("goodput_mbps", "goodput_window_mbps", "busy_per_s",
                            "mean_multiplicity", "p_s_measured", "p_s_independent",
                            "idle_slots_per_busy", "winner_participant_frac",
                            "winner_uniform_frac", "winner_enrichment",
                            "p_succ_after_collision", "p_succ_after_success")}
    return out


def _bianchi_no_ack_p_s(n: int) -> float:
    tau = 2.0 / (bianchi.W + 1)
    p_tr = 1.0 - (1.0 - tau) ** n
    return n * tau * (1.0 - tau) ** (n - 1) / p_tr


def _model(n: int) -> broadcast_dcf.BroadcastResult:
    """Ma & Chen's published broadcast model at our measured 802.11a parameters."""
    return broadcast_dcf.solve(n, _L, _T_BUSY, w0=bianchi.W, slot_s=bianchi.SLOT)


def _ladder(n: int) -> dcf_ladder.LadderResult:
    return dcf_ladder.run(n, w=bianchi.W, busy_periods=_PERIODS, head_start=True,
                          t_busy_s=_T_BUSY, slot_s=bianchi.SLOT, payload_bytes=_L, seed=1)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_published_model_reproduces_measured_p_success(n: int) -> None:
    """The whole finding in one line: Ma & Chen predict NS-3's collision statistics."""
    assert _model(n).p_success == pytest.approx(_measured()[n]["p_s_measured"], rel=0.01)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_published_model_reproduces_measured_goodput(n: int) -> None:
    assert _model(n).throughput_bps / 1e6 == pytest.approx(
        _measured()[n]["goodput_window_mbps"], rel=0.01)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_published_model_reproduces_measured_idle_slots(n: int) -> None:
    assert _model(n).idle_slots_per_busy_period == pytest.approx(
        _measured()[n]["idle_slots_per_busy"], rel=0.02)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_slot_exact_model_reproduces_measured_p_success(n: int) -> None:
    """Independent cross-check: our own simulator, written before the paper was found."""
    assert _ladder(n).p_success == pytest.approx(_measured()[n]["p_s_measured"], rel=0.05)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_slot_exact_model_reproduces_measured_goodput(n: int) -> None:
    """Compared against the window-consistent goodput (audit A11): `goodput_mbps` is the
    PacketSink figure over [1, simTime+1] while every slot statistic here comes from the guarded
    steady-state window, and mixing the two costs ~1 % of spurious disagreement."""
    assert _ladder(n).throughput_bps / 1e6 == pytest.approx(
        _measured()[n]["goodput_window_mbps"], rel=0.02)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_measured_row_is_internally_consistent(n: int) -> None:
    """p_s x busy_per_s x 8L must reproduce the row's own windowed goodput exactly."""
    m = _measured()[n]
    assert m["p_s_measured"] * m["busy_per_s"] * 8 * _L / 1e6 == pytest.approx(
        m["goodput_window_mbps"], rel=0.005)


@pytest.mark.parametrize("n", [5, 10, 20, 35, 50])
def test_slot_exact_model_reproduces_measured_idle_slots(n: int) -> None:
    """The other half of the timing: how long the medium stays idle between busy periods."""
    assert _ladder(n).idle_slots_per_busy_period == pytest.approx(
        _measured()[n]["idle_slots_per_busy"], rel=0.05)


def test_naive_reduction_still_fails_at_high_n_and_is_not_quietly_fixed() -> None:
    """The negative result, kept explicit (Law 7): the in-house reduction is out by >10x at N=50.

    Ma & Chen open by warning that unicast models "cannot simply be reduced" to broadcast; this
    test is that warning, made executable against our own measurement.
    """
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
    assert m["winner_enrichment"] > 5.0
    assert m["p_succ_after_collision"] > 3.0 * m["p_succ_after_success"]
    # At N=5 collisions are rare, so the mechanism must be essentially absent.
    low = _measured()[5]
    assert low["p_succ_after_collision"] == pytest.approx(low["p_succ_after_success"], rel=0.10)
