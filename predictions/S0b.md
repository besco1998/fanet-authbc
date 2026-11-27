# S0b — the AR9271 sniffer's gate, recorded beside the TP-Link

*Registered 2026-11-27, before the adapter arrives, so that the gate can run the day it does
(Mohamed, 2026-11-23, "After the gate S0 failed"; his deadline is 2026-11-30). The signal criterion
is his of 2026-11-27 (`docs/DECISIONS.md`, "S0b's signal criterion"). Code: `analysis/s0b.py`
(`tests/test_s0b.py`). Kit: `run_sniffer2.sh` (`MODULE=ath9k_htc` for the AR9271), the TP-Link's
TSF build, `run_window_plan2.sh` with `chip_check.sh`.*

## The adapter, and what its driver says (Law 2, read before any data)

* **Any adapter with the Atheros AR9271** (for example an Alfa AWUS036NHA, or a TL-WN722N version 1),
  driven by mainline **`ath9k_htc`**. Blue 2's kernel (5.10.168-ti-r84) ships the module.
* **Its firmware:** the driver tries `ath9k_htc/htc_9271-1.4.0.fw` and falls back to the legacy
  `htc_9271.fw` (`hif_usb.c`), which Blue 2 has (`firmware-atheros`). Which one loaded is logged.
* **TSFT:** `rx_status->mactime` from the chip's `rs_tstamp`, flagged `RX_FLAG_MACTIME_END`
  (`htc_drv_txrx.c`). mac80211 writes it to radiotap as the frame's start.
* **Bad-checksum frames:** in monitor mode with the `fcsfail` flag, frames with a CRC error are
  accepted and flagged `RX_FLAG_FAILED_FCS_CRC` (`common.c`, `ath9k_cmn_rx_accept`). So **some are
  expected** in the saturated pair: collisions become visible.
* **The preamble** is reported per frame (mac80211's short-preamble flag).

## The session (`experiments/channel24/plan_s0b.txt`, 22 windows, about 11 minutes)

* **Both sniffers record the same frames,** their dongles within 10 cm of each other:
  * the AR9271 (`SESSION/sniffer_ar/`), on Blue 1, or on Blue 2 through a powered USB hub, as
    Mohamed chooses at the boards;
  * the TP-Link (`SESSION/sniffer/`).
  * Both are placed and recorded in `geometry.json`, which must be complete.
* **The windows:**
  * rate checks R1–R3 before and after;
  * G1–G3: each Pi alone, 1 000 frames at 50 frames/s, 145 B;
  * PA, PB, PC: **each Pi** at 15, 12, 9 and 6 dBm, 25 s each, the others at 15 dBm;
  * X: the saturated pi-A + pi-B pair, 25 s.
* **Validity:**
  * frame burst read 0 before and after;
  * no chip stop;
  * the AR9271's log names `ath9k_htc`;
  * a preflight GO before it.

## Scored (all required, on the AR9271)

| criterion | passes if |
|---|---|
| **completeness**, each Pi's 1 000 frames (G1, G2, G3) | **≥ 0.99 for every sender** (S0 found the misses depend on the sender) |
| **TSFT present** on our frames | **≥ 0.99** |
| **TSFT per frame:** in each rate check, consecutive intervals below the airtime (1 864 µs) | **< 1 %** |
| **TSFT in µs:** in each rate check, the **mean** interval against the receivers' cycle | **within 1 %** (S0's median against a mean was a registration error) |
| **signal:** pi-A's fall from 15 dBm at 12, 9 and 6 dBm, on the frames **both** sniffers recorded | **the AR9271's equals the TP-Link's within ±1.0 dB** at each step |
| **rate** | every frame of ours at **1 Mb/s** |

**If any fails, the gate fails:** stop, report which, ask Mohamed. From 2026-11-30, without a
passing adapter, the collision and capture sessions use the receivers' logs as in W1p and W1q, with
the sniffer for timing only (DECISIONS).

## Reported, not scored

* **The short-preamble share** of our frames.
* **Bad-checksum frames** in X: their count.
* **The TP-Link's completeness,** the same windows.
* **pi-A's falls against the set power,** at both sniffers.
* **The diagnostic** (Mohamed, 2026-11-27): pi-B's and the Pi 3's falls at the AR9271 against
  their set steps.
  * If every step of both tracks the set power within ±1.5 dB: **the AR9271 is linear and the
    compression is pi-A's transmitter.**
  * Otherwise: **sender and receiver compression cannot be separated without an external
    reference, and the HackRF measurement is proposed.**

## My expectations `[agent]`

* **Completeness and TSFT:** pass. The driver is mainline, and its receive path drops nothing that
  is well formed.
* **The signal:** the two sniffers agree within 1 dB if both read power linearly. pi-A's falls stay
  near 0.7 dB per dB at both if its transmitter compresses.
* **The diagnostic:** I cannot predict pi-B's and the Pi 3's steps. No session has stepped them
  with a per-frame receiver.
* **Bad-checksum frames:** some, a few percent of the pair's frames.

## Disclosure

* **Known:**
  * S0, D1a and D1b (the TP-Link misses 1–11 %);
  * S0's TSFT and signal readings;
  * the ath9k_htc source read above.
* No AR9271 has been on these boards, and pi-B and the Pi 3 have never been stepped in power with a
  sniffer recording.
