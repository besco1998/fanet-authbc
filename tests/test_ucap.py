"""U-CAP (predictions/UCAP.md): the registered capture-curve predictions follow the rule as read.

Checked without ns-3 (802.11b's DSSS model is a closed form; the 802.11a values call ns-3's own
table through `ns3/authbc-per.cc` and are not exercised here):
* within the 4 µs detection window the later, stronger frame is received from SIR = 5 dB (SINR
  3.998 dB at SIR = 4), and the earlier one never; the capture model changes nothing;
* at equal power and Δ < 4 µs neither frame is received: q = 0;
* after the window, with the capture model, X takes over only strictly above the 5 dB margin;
* a detected DSSS frame survives a later interferer down to about −3.6 dB SINR.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ucap():
    spec = importlib.util.spec_from_file_location("ucap", REPO / "analysis" / "ucap.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ucap"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("offset", [0.0, 2.0])
@pytest.mark.parametrize("capture", [False, True])
def test_inside_the_window_the_stronger_wins_from_4_db_of_sinr(ucap, offset, capture) -> None:
    got = [ucap.predict("80211b", capture, offset, float(s)) for s in range(-2, 21)]
    assert [px for px, _ in got] == [0.0] * 7 + [pytest.approx(1.0)] * 16
    assert all(py == 0.0 for _, py in got)


def test_equal_power_inside_the_window_loses_both(ucap) -> None:
    for offset in (0.0, 2.0):
        assert ucap.predict("80211b", False, offset, 0.0) == (0.0, 0.0)


def test_the_capture_model_takes_over_strictly_above_its_margin(ucap) -> None:
    px5, py5 = ucap.predict("80211b", True, 19.0, 5.0)
    px6, py6 = ucap.predict("80211b", True, 19.0, 6.0)
    assert px5 == 0.0 and py5 > 0.4 and px6 == pytest.approx(1.0) and py6 == 0.0
    assert ucap.predict("80211b", True, 21.0, 10.0)[0] == 0.0     # after the 16 µs window


def test_a_detected_dsss_frame_survives_down_to_minus_3_6_db(ucap) -> None:
    assert ucap.dsss_success(-3.0, 1720) > 0.98
    assert ucap.dsss_success(-5.0, 1720) < 0.5
    assert ucap.decode("80211b", 0.0, 19.0) == pytest.approx(1.0, abs=1e-6)


def test_the_check_uses_the_corrected_window_and_new_points(ucap) -> None:
    # 802.11b only: its decode is a closed form; 802.11a calls ns-3's table, absent in CI
    assert ucap.CHECK_PAYLOAD == 97 and ucap.CORRECTED_WINDOW_END_US == 16.0
    assert ucap.CHECK_OFFSETS == (12.0, 15.0, 16.0, 17.0, 20.0, 30.0)
    w, pl = ucap.CORRECTED_WINDOW_END_US, ucap.CHECK_PAYLOAD
    assert ucap.predict("80211b", True, 16.0, 6.0, w, pl)[0] == pytest.approx(1.0)  # the edge
    assert ucap.predict("80211b", True, 17.0, 20.0, w, pl)[0] == 0.0                # past it
    assert ucap.dsss_bits_us(97) == (144.0, 1256.0)
