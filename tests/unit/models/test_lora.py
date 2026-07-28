"""Unit tests for the LoRa/LoRaWAN EU868 PHY model (guards src/authbc/models/lora.py).

Every expected value is either transcribed from a primary source or hand-computed here from the
SX1276 formula by plain arithmetic — never by calling the module back on itself (Law 6).

Sources: Semtech SX1276/77/78/79 datasheet Rev. 7 (May 2020) §4.1.1.5/§4.1.1.7; LoRa Alliance
RP002-1.0.3 Regional Parameters, Tables 8 and 13 and the regional summary (EU868 duty cycle <1 %).
"""

from __future__ import annotations

import math

import pytest

from authbc.models import lora


# --- spec transcription ---------------------------------------------------------------------
def test_eu868_data_rate_table_matches_rp002_table_8() -> None:
    """RP002-1.0.3 Table 8: DR0..DR6 SF/BW and indicative physical bit rate."""
    expected = {
        0: (12, 125_000, 250), 1: (11, 125_000, 440), 2: (10, 125_000, 980),
        3: (9, 125_000, 1_760), 4: (8, 125_000, 3_125), 5: (7, 125_000, 5_470),
        6: (7, 250_000, 11_000),
    }
    for dr, (sf, bw, rate) in expected.items():
        d = lora.EU868_DATA_RATES[dr]
        assert (d.sf, d.bw_hz, d.bitrate_bps) == (sf, bw, rate)


def test_max_payload_matches_rp002_table_13_not_repeater_compatible() -> None:
    """RP002-1.0.3 Table 13 (N, non-repeater): 51 for DR0-2, 115 for DR3, 242 for DR4-6.

    NOTE the repeater-compatible Table 12 gives 222 at DR4-6 — which is where docs/02's original
    LoRa "M=222" came from. This model uses the non-repeater figure and says so.
    """
    assert [lora.EU868_DATA_RATES[d].max_app_payload for d in range(7)] == [
        51, 51, 51, 115, 242, 242, 242]


def test_only_lora_modulated_rates_are_modelled() -> None:
    """DR7 is FSK and DR8-11 are LR-FHSS — outside this PHY model, and rejected loudly."""
    assert set(lora.EU868_DATA_RATES) == {0, 1, 2, 3, 4, 5, 6}
    with pytest.raises(ValueError, match="not a LoRa-modulated"):
        lora.frame_time_on_air_s(10, dr=7)


def test_low_data_rate_optimize_turns_on_for_sf11_and_sf12_at_125khz() -> None:
    """DE=1 where Tsym > 16 ms, i.e. SF11/SF12 at 125 kHz."""
    assert [lora.EU868_DATA_RATES[d].low_data_rate_optimize for d in range(7)] == [
        1, 1, 0, 0, 0, 0, 0]


# --- the time-on-air formula ------------------------------------------------------------------
def test_symbol_time_is_two_to_the_sf_over_bandwidth() -> None:
    assert lora.symbol_time_s(7, 125_000) == pytest.approx(128 / 125_000)   # 1.024 ms
    assert lora.symbol_time_s(12, 125_000) == pytest.approx(4096 / 125_000)  # 32.768 ms
    with pytest.raises(ValueError, match="SF must be 6..12"):
        lora.symbol_time_s(13, 125_000)


def test_time_on_air_matches_hand_computation_at_sf7() -> None:
    """SF7/125 kHz, 242 B application payload ⇒ 255 B PHY payload, CR 4/5, CRC on, DE=0.

    Tsym      = 128/125000                                       = 1.024 ms
    npayload  = 8 + ceil((8·255 − 4·7 + 28 + 16)/(4·7))·5 = 8 + ceil(2056/28)·5 = 8 + 74·5 = 378
    Tpreamble = (8+4.25)·1.024 ms                                = 12.544 ms
    ToA       = 12.544 + 378·1.024                               = 399.616 ms
    """
    n = 8 + math.ceil((8 * 255 - 4 * 7 + 28 + 16) / (4 * 7)) * 5
    assert n == 378
    assert lora.time_on_air_s(255, 7, 125_000) == pytest.approx(0.399616, abs=1e-9)
    assert lora.frame_time_on_air_s(242, dr=5) == pytest.approx(0.399616, abs=1e-9)


def test_time_on_air_matches_hand_computation_at_sf12_with_de_on() -> None:
    """SF12/125 kHz, 51 B app ⇒ 64 B PHY, DE=1 (Tsym 32.768 ms > 16 ms).

    npayload  = 8 + ceil((8·64 − 48 + 28 + 16)/(4·(12−2)))·5 = 8 + ceil(508/40)·5 = 8 + 13·5 = 73
    ToA       = (12.25 + 73)·32.768 ms = 2793.472 ms
    """
    n = 8 + math.ceil((8 * 64 - 4 * 12 + 28 + 16) / (4 * (12 - 2))) * 5
    assert n == 73
    assert lora.frame_time_on_air_s(51, dr=0) == pytest.approx((12.25 + 73) * 0.032768, abs=1e-9)


def test_airtime_grows_with_spreading_factor_by_orders_of_magnitude() -> None:
    """Why LoRa needs its own arm: DR0 costs ~20x the airtime of DR5 for the same bytes."""
    small = lora.frame_time_on_air_s(51, dr=5)
    large = lora.frame_time_on_air_s(51, dr=0)
    assert large / small > 20


def test_payload_over_the_regional_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="RP002-1.0.3 Table 13"):
        lora.frame_time_on_air_s(243, dr=5)
    lora.frame_time_on_air_s(242, dr=5)          # the limit itself is fine


# --- the duty-cycle quota: the LoRa arm's binding constraint ----------------------------------
def test_duty_cycle_interval_at_one_percent() -> None:
    """EU868 <1 % (RP002-1.0.3 summary): a 400 ms frame may repeat only every ~40 s."""
    toa = lora.frame_time_on_air_s(242, dr=5)
    assert lora.duty_cycle_interval_s(toa) == pytest.approx(toa / 0.01)
    assert lora.duty_cycle_interval_s(toa) == pytest.approx(39.96, abs=0.05)
    with pytest.raises(ValueError, match="duty_cycle must be in"):
        lora.duty_cycle_interval_s(toa, duty_cycle=0.0)


def test_sustainable_rate_is_two_orders_below_the_80211_arm() -> None:
    """The finding that forces a separate arm: Λ=20 rec/s is impossible on LoRa.

    A full DR5 frame carrying b records may be sent once per ~40 s, so even at the largest batch
    the sustainable record rate is a fraction of a record per second — vs 20 rec/s on 802.11.
    """
    lam = lora.sustainable_record_rate(batch=5, app_payload_bytes=242, dr=5)
    assert lam < 0.2
    assert 20.0 / lam > 100, "the 802.11 arrival rate is >100x what LoRa can carry"


def test_slowest_data_rate_is_dramatically_more_constrained() -> None:
    at_dr5 = lora.sustainable_record_rate(batch=1, app_payload_bytes=51, dr=5)
    at_dr0 = lora.sustainable_record_rate(batch=1, app_payload_bytes=51, dr=0)
    assert at_dr5 / at_dr0 > 20


def test_mtu_batch_uses_the_regional_payload_limit() -> None:
    """b_max = ⌊(N − H_f − g_a)/s⌋ with N from RP002 Table 13, not an 802.11 MTU."""
    assert lora.max_batch_for_mtu(45.0, auth_bytes=64, frame_hdr_bytes=40, dr=5) == int(
        (242 - 40 - 64) // 45.0)
    # DR0's 51 B cannot even hold one 45 B record plus a 64 B signature and a 40 B header
    assert lora.max_batch_for_mtu(45.0, auth_bytes=64, frame_hdr_bytes=40, dr=0) == 0
