# W1q — capture against power difference on the hardware, the Pi 3 as receiver (session 1)

*Registered 2026-11-21, before the session. Plan: session 1 of
`docs/revision/2026-11-20_session_plans.md` (work package G2), approved by Mohamed on 2026-11-21
with his changes (`docs/DECISIONS.md`): both senders' signal strength logged at every step; q
stated as the Pi 3 receiver's; time permitting, one step repeated with another board as receiver.
Code: `analysis/w1q.py` (`tests/test_w1q.py`). Kit: `hw/channel/run_window_plan2.sh`, `rssi.sh`.*

## Why

* **(G22) needs q, the share of a collided frame still received.** No session has measured it on
  these radios.
* **G1 bounded it from counts only:** a receiver × sender effect of 1.4–2.0 % in the 1 m square,
  6.6–8.8 times its count-noise null. That gives no q.
* **ns-3's rule** (U-CAP, U-CAP2) keeps the stronger of two frames that start within 4 µs if its
  SINR is at least 4 dB. This session asks whether the Pi 3's radio does.

## The layout

* pi-A and pi-B send; the Pi 3 receives. On a line or a triangle, the positions taped, each
  distance measured with a tape and recorded before the first window.
* Photographed at the start and the end. No board moves.
* Channel 11, 802.11b 1 Mb/s, the 145 B frame, the redrawn sender, frame burst off on all three
  (read back).

## The steps (`experiments/channel24/plan_w1q.txt`, 31 windows, about 16 minutes)

* **pi-A's power:** 15, 12, 9, 5 and 0 dBm (steps of 0, 3, 6, 10 and 15 dB), set by
  `iw … txpower fixed` before the step's first window and read back.
* **pi-B:** fixed at 15 dBm throughout.
* **A change from the plan as approved, with its reason.** The plan said "pi-A at its default"
  and "pi-B stays at its default".
  * Every earlier read-back of the default (`auto`) shows 31.00 dBm (225 log lines,
    `results/hw/channel24/*/txpower.log`). That is the driver's cap, not the radio's power, so a
    step "3 dB below the default" has no defined value.
  * A fixed 15 dBm has been set and read back exactly before (W1g: `set txpower fixed 1500`, read
    back 15.00 dBm).
  * **Confirmed by Mohamed on 2026-11-22, before the tag:** pi-A starts at a fixed 15 dBm,
    pi-B is fixed at 15 dBm.
* **Per step:**
  * A_d: pi-A alone at 50 frames/s, 25 s;
  * B_d: pi-B alone, 25 s;
  * C_d × 3: both at 600 frames/s offered, 25 s.
* **Rate checks,** one per board, before and after.

**The signal strength at every step, of both senders** (Mohamed, 2026-11-21):
* each board reads `rssi.sh` for every peer address and for the zero address, halfway through and
  after every window;
* **ΔRSSI = RSSI_A − RSSI_B at the Pi 3,** from the step's single-sender windows:
  * the per-peer reading if the kit check accepts it at the Pi 3;
  * otherwise the zero-address reading in each sender's own window (the fallback).
* **The kit check here** is W1p's rule (`w1p.per_mac_accepted`), applied to this session's own
  step-0 windows A0 and B0 at the Pi 3. W1p's verdict is not carried over, because the layout
  changes, and with it whether the two peers differ by 4 dB.

## What is measured, and how q is identified

* **q here is the Pi 3 receiver's,** the share of a sender's collided frames that the Pi 3 still
  receives. It is not a swarm's mean, and F138's half-duplex factor is not applied.
* **The partner gives the window's own collision rate, without a channel model:**
  * in a saturated pair each board is the other's only sender, and a board that is transmitting
    cannot receive;
  * so sender j's loss at its partner, less the partner's link loss for j, is the share of j's
    frames that overlapped the partner's: p_j in that window.
  * At the Pi 3, by (G22), L_j3 = p_j(1 − q_j) + ℓ_j3, so
    **q_j = 1 − (L_j3 − ℓ_j3) / (L_j,partner − ℓ_j,partner)** (`q_of`).
  * ℓ comes from the step's single-sender windows. A sender's frames on air are its receivers'
    widest span of sequence numbers (`on_air`).
* **Stated with it:** (G22)'s split assumes a captured frame then meets only its link loss, and a
  pair collision involves one frame of each sender.
* **The step is void** if pi-A's signal at the Pi 3 does not fall by the step within ±1.5 dB, which
  checks that the chip honoured the fixed power (`step_valid`). It is reported, not scored.

## Predictions (ns-3's rule, U-CAP and U-CAP2, at 802.11b 1 Mb/s)

* The stronger frame is kept if |ΔRSSI| ≥ 4 dB, both frames being far above the noise:
  **q_strong = 1 above 4 dB, 0 below; q_weak = 0 at every step.**
* **Scored per valid step (`score_step`):**
  * q_weak ≤ 0.10;
  * q_strong ≥ 0.90 where |ΔRSSI| ≥ 5 dB;
  * q_strong ≤ 0.10 where |ΔRSSI| ≤ 3 dB;
  * between 3 and 5 dB, reported. The rule's threshold sits there, with RSSI read in whole dB.
* **q per step** is the mean over its three capture windows, with their range reported.
* **Stated in advance:** a real chip is not ns-3. A gradual curve, or capture of a later and
  stronger frame (message in message), is a finding, not a failure of the method.

## Time permitting: one step with pi-B as receiver

* **The step:** the valid step whose |ΔRSSI| at the Pi 3 is nearest 4 dB, chosen by that rule.
* **Its windows:** pi-A at that power and the Pi 3 at 15 dBm send; pi-B receives. Single-sender
  windows of each, then three pair windows.
* **Scored by the same rule:** q identified at pi-B, with pi-A and the Pi 3 as each other's
  partners.

## Also reported

* **p_j per step:** the MAC does not change with power, so p_j should not either.
* **q_A + q_B ≤ 1** at every step: one receiver decodes at most one frame of a two-frame collision.
* **The share of the Pi 3's losses that is collisions.**

## My expectations `[agent]`

* At 0 dB nominal the boards sit near equal power, so ΔRSSI is small and q is near 0 for both. By
  10–15 dB pi-B dominates (q_B near 1).
* The Pi 3's radio may capture more gradually than ns-3's step (W1f, F127: capture by the stronger
  sender showed in counts).
* If the per-peer RSSI is rejected, the single-sender fallback is good to about ±1 dB, enough
  away from 3–5 dB.

## Disclosure

* **Known before this registration:**
  * G1 and its null;
  * F127–F133 ("the louder frame survived", inferred from counts);
  * U-CAP and U-CAP2;
  * every earlier read-back of the transmit power.
* **No capture session has been run.**
