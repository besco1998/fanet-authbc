"""802.11b DSSS timing (models/phy.py `DsssPhy`; predictions/W1b.md).

Held here: that the PHY the 2.4 GHz campaign is modelled with is ns-3.48's arithmetic, read from its
source (`WifiPhy::Configure80211b`, `dsss-phy.cc`, `wifi-mac.cc`), and the hand figures the plan
used.
"""
from __future__ import annotations

import pytest

from authbc.models import bianchi
from authbc.models.phy import DSSS_1M, DsssPhy


def test_the_constants_are_ns3s() -> None:
    assert DSSS_1M.sifs_s == pytest.approx(10e-6)
    assert DSSS_1M.slot_s == pytest.approx(20e-6)
    assert DSSS_1M.difs_s == pytest.approx(50e-6)       # SIFS + 2 slots
    assert DSSS_1M.plcp_s == pytest.approx(192e-6)      # 144 + 48
    assert DSSS_1M.w0 == 32                              # CWmin 31


@pytest.mark.parametrize("payload,us", [(146, 192 + 8 * 182), (173, 192 + 8 * 209),
                                        (1400, 192 + 8 * 1436)])
def test_a_frame_is_192_us_plus_8_us_a_byte(payload: int, us: int) -> None:
    assert DSSS_1M.ppdu_s(bianchi.mpdu_bytes(payload)) == pytest.approx(us * 1e-6)


def test_the_cycle_of_the_rate_check() -> None:
    # W1c's pilot: 145 B of UDP is 173 B of MAC payload; at 1 Mb/s one saturated sender's cycle
    # is the frame, DIFS and a mean backoff of 15.5 slots: 1 864 + 50 + 310 µs
    cycle = DSSS_1M.t_broadcast(173) + (DSSS_1M.w0 - 1) / 2 * DSSS_1M.slot_s
    assert cycle == pytest.approx(2224e-6)


def test_bad_constants_are_refused() -> None:
    with pytest.raises(ValueError):
        DsssPhy("bad", 1e6, plcp_s=0.0, sifs_s=10e-6, slot_s=20e-6, w0=32)
