"""LoRa / LoRaWAN EU868 PHY model — the LoRa arm's own parameters (docs/02 §9).

**Every constant here is transcribed from a primary source.** The 802.11 arm must not lend its
numbers to this one: they differ by two to three orders of magnitude, and the binding constraint is
different in kind (a regulatory airtime quota, not a frame size or a latency budget).

Sources, both retrieved and read in full:

* **Semtech SX1276/77/78/79 datasheet, Rev. 7, May 2020** — §4.1.1.5 (symbol rate) and §4.1.1.7
  ("Time on air", p. 32) give the packet-duration formula implemented in `time_on_air_s`.
* **LoRa Alliance RP002-1.0.3 LoRaWAN® Regional Parameters** (2021) — Table 8 (EU863-870 TX
  DataRate table), Table 13 (maximum payload size, *not* repeater compatible), and the regional
  parameter summary giving EU868 **Duty Cycle < 1 %**.

Time on air (SX1276 §4.1.1.7), verbatim structure:

    Ts        = 1/Rs,  Rs = BW / 2^SF                       (§4.1.1.5)
    Tpreamble = (npreamble + 4.25) · Tsym
    npayload  = 8 + max(ceil((8·PL − 4·SF + 28 + 16·CRC − 20·IH) / (4·(SF − 2·DE))) · (CR+4), 0)
    Tpacket   = Tpreamble + npayload · Ts

with PL the **PHY** payload in bytes, IH=1 for implicit header, DE=1 when LowDataRateOptimize is
on, and CR ∈ 1..4 for coding rates 4/5..4/8.

**Why this arm is separate.** On 802.11 the batch is capped by freshness (docs/02 T2a). Here the
cap is a *duty-cycle quota*: EU868 allows under 1 % of airtime, so a maximum-size DR5 frame
(≈400 ms) may be sent only once every ≈40 s. That makes the sustainable record rate Λ roughly
0.1 rec/s — over two orders of magnitude below the 802.11 arm's 20 rec/s — and makes the 802.11
freshness budget of 250 ms unreachable at any batch size. The LoRa arm therefore needs its own Λ
and D_max, derived here rather than inherited.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- SX1276 Rev.7 §4.1.1.7 defaults ---------------------------------------------------------
PREAMBLE_SYMBOLS: int = 8       # LoRaWAN uplink preamble
CODING_RATE: int = 1            # CR=1 ⇒ 4/5, the LoRaWAN uplink rate
CRC_ON: int = 1                 # uplinks carry a CRC
IMPLICIT_HEADER: int = 0        # LoRaWAN uses the explicit header

# LoRaWAN frame overhead added to the application payload before it reaches the PHY.
# RP002-1.0.3 §2.4.6 defines M = max MACPayload and N = max application payload; M − N = 8 B
# (FHDR 7 + FPort 1, with no FOpts). PHYPayload = MHDR(1) + MACPayload + MIC(4), so the PHY sees
# N + 8 + 5 = N + 13 bytes.
LORAWAN_OVERHEAD_BYTES: int = 13

# EU868 regulatory airtime quota — RP002-1.0.3 regional parameter summary ("Duty Cycle < 1%").
# Sub-band-specific values (0.1 %/1 %/10 %) come from ETSI EN 300 220, which is NOT transcribed
# here; 1 % is the figure RP002 states for the band and is what this model uses.
DUTY_CYCLE: float = 0.01


@dataclass(frozen=True)
class DataRate:
    """One EU868 uplink data rate (RP002-1.0.3 Tables 8 and 13)."""

    dr: int
    sf: int
    bw_hz: int
    bitrate_bps: int          # "indicative physical bit rate", Table 8
    max_app_payload: int      # N, non-repeater-compatible, Table 13
    sensitivity_dbm: float    # SX1276 Rev.7 RFS_L125_HF / RFS_L250_HF, Band 1, LnaBoost

    @property
    def low_data_rate_optimize(self) -> int:
        """DE=1 where the symbol time exceeds ~16 ms — i.e. SF11/SF12 at 125 kHz."""
        return 1 if (2**self.sf) / self.bw_hz > 16e-3 else 0


# RP002-1.0.3 Table 8 (SF/BW, indicative bit rate) × Table 13 (max application payload N).
# LoRa modulation only: DR7 is FSK and DR8–11 are LR-FHSS, neither of which this model covers.
# Sensitivity is the LINK-BUDGET axis: it is what a higher spreading factor buys in exchange for
# airtime, and without it a duty-cycle optimizer trivially selects the fastest rate every time.
# SX1276 Rev.7 electrical spec, Long-Range Mode, highest LNA gain + LnaBoost, Band 1 (862-1020 MHz,
# which is where EU868 sits): RFS_L125_HF gives SF7..SF12 = -123/-126/-129/-132/-133/-136 dBm at
# 125 kHz, and RFS_L250_HF gives SF7 = -120 dBm at 250 kHz.
EU868_DATA_RATES: dict[int, DataRate] = {
    0: DataRate(0, 12, 125_000, 250, 51, -136.0),
    1: DataRate(1, 11, 125_000, 440, 51, -133.0),
    2: DataRate(2, 10, 125_000, 980, 51, -132.0),
    3: DataRate(3, 9, 125_000, 1_760, 115, -129.0),
    4: DataRate(4, 8, 125_000, 3_125, 242, -126.0),
    5: DataRate(5, 7, 125_000, 5_470, 242, -123.0),
    6: DataRate(6, 7, 250_000, 11_000, 242, -120.0),
}


def relative_range(dr: int, reference_dr: int = 6, path_loss_exponent: float = 2.0) -> float:
    """Range of *dr* relative to *reference_dr*, from the sensitivity difference alone.

    A link closes when received power ≥ sensitivity, so a sensitivity improvement of Δ dB buys
    10^(Δ/(10·n)) in range under a path-loss exponent n (n=2 is free space, the right choice for
    air-to-ground/air-to-air LoS). TX power, antennas and fading are identical across data rates
    and therefore cancel — this is a *ratio*, not an absolute range, and needs no link budget.
    """
    delta_db = _rate(reference_dr).sensitivity_dbm - _rate(dr).sensitivity_dbm
    return 10.0 ** (delta_db / (10.0 * path_loss_exponent))


def symbol_time_s(sf: int, bw_hz: int) -> float:
    """Tsym = 2^SF / BW (SX1276 §4.1.1.5: Rs = BW/2^SF, Ts = 1/Rs)."""
    if not 6 <= sf <= 12:
        raise ValueError(f"SF must be 6..12, got {sf}")
    if bw_hz <= 0:
        raise ValueError(f"bandwidth must be > 0 Hz, got {bw_hz}")
    return (2**sf) / bw_hz


def payload_symbols(phy_payload_bytes: int, sf: int, *, coding_rate: int = CODING_RATE,
                    crc: int = CRC_ON, implicit_header: int = IMPLICIT_HEADER,
                    low_data_rate_optimize: int = 0) -> int:
    """npayload per SX1276 §4.1.1.7 — the packet's symbol count including the 8 header symbols."""
    if not 1 <= coding_rate <= 4:
        raise ValueError(f"coding_rate must be 1..4 (4/5..4/8), got {coding_rate}")
    denom = 4 * (sf - 2 * low_data_rate_optimize)
    numer = 8 * phy_payload_bytes - 4 * sf + 28 + 16 * crc - 20 * implicit_header
    return 8 + max(math.ceil(numer / denom) * (coding_rate + 4), 0)


def time_on_air_s(phy_payload_bytes: int, sf: int, bw_hz: int, *,
                  preamble_symbols: int = PREAMBLE_SYMBOLS, coding_rate: int = CODING_RATE,
                  crc: int = CRC_ON, implicit_header: int = IMPLICIT_HEADER,
                  low_data_rate_optimize: int | None = None) -> float:
    """Total LoRa packet duration [s] — SX1276 §4.1.1.7 Tpacket.

    *phy_payload_bytes* is the PHY payload; for LoRaWAN that is the application payload plus
    `LORAWAN_OVERHEAD_BYTES`. Use `frame_time_on_air_s` to go straight from an application payload.
    """
    if low_data_rate_optimize is None:
        low_data_rate_optimize = 1 if symbol_time_s(sf, bw_hz) > 16e-3 else 0
    t_sym = symbol_time_s(sf, bw_hz)
    n_pay = payload_symbols(phy_payload_bytes, sf, coding_rate=coding_rate, crc=crc,
                            implicit_header=implicit_header,
                            low_data_rate_optimize=low_data_rate_optimize)
    return (preamble_symbols + 4.25) * t_sym + n_pay * t_sym


def frame_time_on_air_s(app_payload_bytes: int, dr: int) -> float:
    """Airtime [s] of a LoRaWAN uplink carrying *app_payload_bytes* of application data at *dr*."""
    rate = _rate(dr)
    if app_payload_bytes > rate.max_app_payload:
        raise ValueError(
            f"DR{dr} allows at most {rate.max_app_payload} B of application payload "
            f"(RP002-1.0.3 Table 13), got {app_payload_bytes}")
    return time_on_air_s(app_payload_bytes + LORAWAN_OVERHEAD_BYTES, rate.sf, rate.bw_hz,
                         low_data_rate_optimize=rate.low_data_rate_optimize)


def duty_cycle_interval_s(airtime_s: float, duty_cycle: float = DUTY_CYCLE) -> float:
    """Minimum spacing between transmissions to respect the regulatory quota [s].

    A transmitter occupying *airtime_s* may repeat only every airtime_s/duty_cycle. At EU868's
    1 %, a 400 ms DR5 frame may be sent once every 40 s.
    """
    if not 0.0 < duty_cycle <= 1.0:
        raise ValueError(f"duty_cycle must be in (0, 1], got {duty_cycle}")
    if airtime_s <= 0:
        raise ValueError(f"airtime_s must be > 0, got {airtime_s}")
    return airtime_s / duty_cycle


def sustainable_record_rate(batch: int, app_payload_bytes: int, dr: int,
                            duty_cycle: float = DUTY_CYCLE) -> float:
    """Λ [records/s] a single node can sustain under the duty-cycle quota.

    This is the LoRa arm's *binding* constraint and has no 802.11 counterpart: there, airtime is
    contended but not rationed. Here it is a hard regulatory budget, so every byte saved converts
    directly into either more records per hour or more nodes on the channel.
    """
    if batch < 1:
        raise ValueError(f"batch must be ≥ 1, got {batch}")
    interval = duty_cycle_interval_s(frame_time_on_air_s(app_payload_bytes, dr), duty_cycle)
    return batch / interval


def max_batch_for_mtu(record_bytes: float, auth_bytes: int, frame_hdr_bytes: int, dr: int) -> int:
    """Largest batch whose frame fits DR*dr*'s application-payload limit (RP002 Table 13)."""
    usable = _rate(dr).max_app_payload - frame_hdr_bytes - auth_bytes
    return int(usable // record_bytes) if usable > 0 and record_bytes > 0 else 0


def _rate(dr: int) -> DataRate:
    if dr not in EU868_DATA_RATES:
        raise ValueError(
            f"DR{dr} is not a LoRa-modulated EU868 uplink rate; this model covers "
            f"{sorted(EU868_DATA_RATES)} (DR7 is FSK, DR8–11 are LR-FHSS)")
    return EU868_DATA_RATES[dr]


# --------------------------------------------------------------- external model (Bor et al. 2017)
# Bor, Roedig, Voigt & Alonso, "LoRa Scalability: A Simulation Model Based on Interference
# Measurements", Sensors 17(6):1193, 2017. DOI 10.3390/s17061193. PDF in docs/literature/.
#
# Why this belongs in our codebase: it is the only published LoRa capacity model we found that is
# grounded in *hardware interference measurements* rather than an analytical collision assumption,
# and it is stated in closed form, so it can be evaluated at our operating point instead of merely
# quoted at theirs. It gives the LoRa arm the external baseline that the 802.11 arm gets from
# Bianchi and Ma & Chen (item A7).
#
# Their Eq. (8) is a degree-5 polynomial fitted (R^2 = 0.997) to the TOTAL packet-loss percentage
# — collisions *plus* wrong-payload-CRC — for a single channel, a single SF, 20 B payload, at the
# 1 % duty-cycle ceiling. Eqs. (9)–(11) generalise it by scaling the node count by the number of
# non-interfering logical channels.
#
# ⚠️ Two properties that make it applicable to AUTHBC, and one that limits it:
#  * It is parameterised by NODE COUNT at the duty-cycle ceiling, not by payload size. At that
#    ceiling every node occupies 1 % of the channel whatever its SF or frame length, so offered
#    load is 0.01·N in both their study and ours. This is what makes the comparison like-for-like
#    despite our 218 B frames against their 20 B.
#  * The fit is for SF 12; the paper reports SF 7 loss as "similar" (Fig. 6), differing in
#    throughput rather than in loss fraction — consistent with the duty-cycle normalisation above.
#  * ⚠️ It is only valid for x < 1000, and the polynomial does not pass through the origin: it
#    predicts 1.78 % loss at N = 0. Below N ~ 5 the intercept dominates, so small-N predictions
#    carry the fit's error, not a physical claim. `bor2017_loss_pct` clamps to [0, 100] but does
#    NOT hide the intercept, because hiding it would misrepresent their model.
#  * ⚠️ The quintic is also NOT monotone near the top of its domain: it peaks at x ~ 723 (86.61 %),
#    falls to 85.01 % at x ~ 923, then rises again. Loss cannot fall as nodes are added, so this
#    is a fitting artifact — but it is only 1.6 points on a 0-90 % curve, i.e. inside the fit's own
#    residual at R^2 = 0.997. Documented and asserted in tests rather than smoothed away; it does
#    not touch AUTHBC results, whose operating region is N <= 50.
_BOR2017_EQ8_COEFFS = (  # highest power first, Eq. (8)
    1.1318e-12,   # x^5
    -3.4342e-9,   # x^4
    4.0194e-6,    # x^3
    -0.0023,      # x^2
    0.6678,       # x^1
    1.7833,       # x^0
)
BOR2017_VALID_MAX_X = 1000  # Eqs. (8)–(11) are stated "x < 1000"


def bor2017_loss_pct(n_devices: float, *, logical_channels: int = 1) -> float:
    """Total packet loss (%) predicted by Bor et al. 2017 Eq. (8), scaled per Eqs. (9)-(11).

    ``logical_channels`` is the number of non-interfering (channel x SF) combinations: 1 for a
    single channel and single SF, 6 for one channel and six SFs, 3 for three channels and one SF,
    18 for three channels and six SFs. Their scaling law is that loss depends on nodes *per
    logical channel*, which is why all four of their figures collapse onto one curve.

    Raises ValueError outside the fit's stated domain rather than extrapolating silently.
    """
    if n_devices < 0:
        raise ValueError("n_devices must be non-negative")
    if logical_channels < 1:
        raise ValueError("logical_channels must be >= 1")
    x = n_devices / logical_channels
    if x >= BOR2017_VALID_MAX_X:
        raise ValueError(
            f"Bor et al. Eq. (8) is stated for x < {BOR2017_VALID_MAX_X}; got x={x:.1f} "
            f"(n_devices={n_devices}, logical_channels={logical_channels})"
        )
    y = 0.0
    for c in _BOR2017_EQ8_COEFFS:
        y = y * x + c
    return min(100.0, max(0.0, y))


def bor2017_n_max(verifiability: float = 0.95, *, logical_channels: int = 1) -> int:
    """Largest N whose predicted delivery ratio still meets ``verifiability`` under Bor et al.

    The same V >= 0.95 criterion the AUTHBC simulation uses, applied to the external model, so the
    two capacity numbers are directly comparable rather than merely adjacent.
    """
    if not 0.0 < verifiability <= 1.0:
        raise ValueError("verifiability must be in (0, 1]")
    max_loss_pct = 100.0 * (1.0 - verifiability)
    n = 0
    for cand in range(1, BOR2017_VALID_MAX_X * logical_channels):
        if bor2017_loss_pct(cand, logical_channels=logical_channels) > max_loss_pct:
            break
        n = cand
    return n


# ------------------------------------------------- measured air-to-air link (Zirak et al. 2021)
# Zirak, Shashev & Shidlovskiy, "Swarm of Drones Using LoRa Flying Ad-Hoc Network", 2021 Int. Conf.
# on Information Technology (ICIT), pp. 400-405. DOI 10.1109/ICIT52682.2021.9491655.
#
# Why this matters more than another simulation would: it is the only **hardware** measurement of
# LoRa *air-to-air* packet delivery we have found, from a real FANET (drones plus a base station)
# rather than a ground testbed. Our LoRa arm has no hardware of its own (D2 was closed by
# simulation and explicitly flagged "still not hardware"), so this is the closest thing to ground
# truth for the link itself.
#
# Table I, PDR at Drone 1 over 1000 packets, FIRST HOP, field test. Their topology carries only
# two drones plus a base station, so contention is negligible and these figures isolate
# **range-dependent link loss** from collision loss — the term our collision-only sim omits.
_ZIRAK2021_FIELD_PDR_FIRST_HOP: dict[int, float] = {
    200: 0.9711, 300: 0.9675, 400: 0.9610, 500: 0.9550, 600: 0.9399,
    700: 0.9266, 800: 0.9201, 900: 0.9113, 1000: 0.9045,
}


def zirak2021_link_pdr(range_m: float) -> float:
    """Measured air-to-air LoRa link PDR at ``range_m``, interpolated (Zirak et al. Table I).

    This is the *link* term only: what one frame achieves against path loss with no contention.
    Multiply by a collision-model delivery ratio to get end-to-end delivery, since the two loss
    mechanisms are independent.

    Refuses to extrapolate outside 200-1000 m, the measured span. Below 200 m the trend is still
    rising and we have no data; above 1000 m their second-hop results show it still falling.
    """
    lo, hi = min(_ZIRAK2021_FIELD_PDR_FIRST_HOP), max(_ZIRAK2021_FIELD_PDR_FIRST_HOP)
    if not lo <= range_m <= hi:
        raise ValueError(f"measured only over {lo}-{hi} m; got {range_m} m (no extrapolation)")
    xs = sorted(_ZIRAK2021_FIELD_PDR_FIRST_HOP)
    for a, b in zip(xs, xs[1:], strict=False):
        if a <= range_m <= b:
            t = 0.0 if b == a else (range_m - a) / (b - a)
            return (_ZIRAK2021_FIELD_PDR_FIRST_HOP[a] * (1 - t)
                    + _ZIRAK2021_FIELD_PDR_FIRST_HOP[b] * t)
    raise AssertionError("unreachable: range_m is within [lo, hi]")


def max_range_for_verifiability(verifiability: float = 0.95) -> float | None:
    """Furthest range at which the LINK ALONE can still meet ``verifiability``, or None.

    ⚠️ This is the constraint our collision-only capacity result omits. Because delivery is
    ``P_link(range) x P_no_collision(N)``, any range whose measured link PDR is already below the
    target makes it unreachable at **every** node count — capacity cannot rescue a link that is
    already losing frames to path loss. Returns None if even the shortest measured range fails.
    """
    ok = [r for r in sorted(_ZIRAK2021_FIELD_PDR_FIRST_HOP)
          if _ZIRAK2021_FIELD_PDR_FIRST_HOP[r] >= verifiability]
    return float(max(ok)) if ok else None
