# W1g calibration protocol: making the four senders equal. Written 2026-11-06 00:05, before any calibration run

**Purpose.** In W1f (F127), loss depended on the sender, not the receiver. At A32: pi-A 8.3 %,
pi-B 7.7 %, Pi 3 4.9 %, TP-Link 1.5 %, a spread of 5.6×. The stronger sender wins collisions
(capture), which the model omits. W1g repeats W1f's design with the senders made equal, to test
that reading and, if the model then holds, to measure the ratio. This file fixes the calibration
rule before any calibration data exist.

**Controls available** (verified in source, 2026-11-05/06):
* **TP-Link, none in software.** In aircrack-ng/rtl8188eus `af3bf004`:
  * `iw … set txpower` stores `CurrentTxPwrIdx`, which the hardware path never reads
    (`os_dep/linux/ioctl_cfg80211.c` l. 3957–3990).
  * `/proc/…/tx_power_offset` sets `adapter->power_offset`, which is only zeroed, set and printed.
  * So it is weakened **physically**: Blue 2 moved farther from the Pis.
* **Pis, in software.** brcmfmac's `set_tx_power` writes the firmware's `qtxpower` with its
  override flag (`brcmfmac/cfg80211.c`, rpi-6.12.y). It is used to lower the Pi 3 if needed, set
  after the Pi has joined the cell and returned to `auto` after the run. The Pis' kit is unchanged.

**One calibration run** (disclosed, not scored):
* Blue 2 rebooted, so that it joins the Pis' cell, checked by the BSSID rule.
* Four windows with all four boards sending 145 B at 125 frames/s each: W1f's A31 rate, offered
  load 0.957, near the crossings.
* Then the loss of each ordered (sender, receiver) pair is read off
  (`results/hw/channel24/w1f_2026-11-05/analysis/sender_receiver.py`).

**"Equal", fixed now: every sender's mean loss lies within 1.5× of every other sender's**
(max/min ≤ 1.5). For reference, the two Pi 4s differed by 1.08× in W1f.

**Moves, in this order:**
1. Blue 2 at about 50 cm from the Pis;
2. then about 1 m, or back nearer, as the spread says;
3. then the Pi 3's power lowered in steps of about 3 dB if it still out-wins the Pi 4s.

**Stop rule.** If no run meets the rule within five runs, equalization is not reached with this
kit. That is reported, and W1f stands as the hardware result. Every run is kept and reported,
whatever its outcome.

**If a run meets the rule,** W1g is registered with W1f's plan, code and predictions unchanged,
the equalized setup fixed, this calibration disclosed, and one more validity rule: the session's
own per-sender spread at the A31 windows must also be ≤ 1.5×, or the session is void.
