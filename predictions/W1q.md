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

## Outcome — added 2026-11-22, after the session; nothing above this line was changed

* **The session:** `results/hw/channel24/w1q_2026-11-22`, 16:34–16:50, in the 1 m triangle
  (`LAYOUT.md`). All 31 windows ran on every board. Scored with `python analysis/w1q.py --score`.
  Before it, a preflight came back RETRY (the fresh-boot fast rate of F129, after the power cut),
  then GO.
* **The optional step:** `w1q_2026-11-22_opt`, 19:47–19:50.
  * Same triangle (Mohamed: untouched). Plan `experiments/channel24/plan_w1q_opt.txt`, written
    by `w1q.optional_plan(0)`.
  * It ran as its own session, so it was scored on a view that links both folders' files and
    joins the two signal-strength logs. In every other row, the view's score equals the main
    session's.

### Validity — held

* **Frame burst** read 0 before and after on all three boards, in both sessions.
* **The rate checks** were all in band:
  * pi-A 2 059.9 and 2 048.3 µs;
  * pi-B 2 127.0 and 2 098.4 µs;
  * the Pi 3 2 411.7 and 2 336.8 µs.
* **pi-A's power read back exactly as set:** 15.00, 12.00, 9.00, 5.00 and 0.00 dBm.

### The kit check at the Pi 3 — rejected, so the fallback is used

### The steps (q is the Pi 3 receiver's: the mean of three capture windows, and their range)

| step | pi-A | ΔRSSI | q_A | q_B | p_A | p_B | q_A + q_B | scored |
|---|---|---|---|---|---|---|---|---|
| 0 dB | 15 dBm | +5.0 dB | 0.985 (0.980–0.988) | 0.030 (0.024–0.043) | 0.1070 | 0.0904 | 1.015 | weak held, strong held |
| 3 dB | 12 dBm | +1.5 dB | 0.937 (0.929–0.948) | −0.001 (−0.019–0.009) | 0.0995 | 0.0834 | 0.936 | weak held, **strong failed** |
| 6 dB | 9 dBm | +1.5 dB | 0.311 (0.273–0.352) | 0.515 (0.487–0.539) | 0.1095 | 0.0836 | 0.826 | void: pi-A fell 3.5 dB, not 6 ± 1.5 |
| 10 dB | 5 dBm | 0.0 dB | −0.123 | 0.856 | 0.0961 | 0.0840 | 0.732 | void: fell 5.5 dB, not 10 ± 1.5 |
| 15 dB | 0 dBm | −4.5 dB | 0.277 | 0.896 | 0.1475 | 0.0914 | 1.172 | void: fell 9.0 dB, not 15 ± 1.5 |
| optional, pi-B receives | 15 dBm; the Pi 3 15 dBm | −10.0 dB | q_A −0.063 | q_Pi3 1.000 | | | | weak held, strong held |

* **Six predictions were scored, and five held.** Two steps were valid at the Pi 3 and one at
  pi-B, each with a weak and a strong prediction.
* **The failure:** at the 3 dB step, with a measured ΔRSSI of 1.5 dB, the Pi 3 kept the stronger
  frame 93.7 % of the time. ns-3's 4 dB rule keeps none below 3 dB.
* **Stated in advance:** a gradual curve is a finding, not a failure of the method.

### Also reported (registered)

* **p_j:**
  * p_A was 0.0961–0.1095 at steps 0–10 and 0.1475 at step 15;
  * p_B was 0.0834–0.0914;
  * so p_A moved with power at 0 dBm, which the MAC alone would not do.
* **q_A + q_B ≤ 1:**
  * held at 3, 6 and 10 dB;
  * 1.015 at 0 dB, inside the windows' ranges;
  * **1.172 at 15 dB: failed.**
* **q_A < 0 at 10 dB:** the Pi 3 lost more of pi-A's frames than its collisions and link loss
  account for.
* **The share of the Pi 3's losses that is collisions:** 1.000 for both senders at every step,
  except pi-A at 0 dB, where it lost only 0.26 % and 0.636 of that was collisions. The link lost
  ≤ 0.09 % at 50 frames/s. The scorer does not print this; it was computed afterwards with
  `w1q.losses`.

### My expectations, against the outcome

* **"At 0 dB nominal, ΔRSSI is small": wrong.** At equal set power the Pi 3 heard pi-A 5.0 dB
  louder, and pi-A dominated.
* **"Capture may be more gradual than ns-3's step":** the 3 dB step's failure points that way.
* **"The fallback is good to about ±1 dB": wrong.** See below.

### Seen after scoring — not a result

* **The fallback's second reading is not the sender's.**
  * It averages the reading taken halfway through each single-sender window with the one taken
    after the window ends.
  * After the window the sender has stopped. At pi-A's low powers that reading is 5–6 dB above
    the halfway one (A10: −51 and −45 dBm; A15: −54 and −49 dBm), so it is some other frame.
  * Averaging the two pulls pi-A's fall toward zero, which is how steps 6–15 were voided.
* **From the halfway readings alone:**
  * pi-A falls 0, 4, 7, 10 and 13 dB, against the 0, 3, 6, 10 and 15 asked;
  * ΔRSSI is +7, +3, 0, −3 and −6 dB;
  * steps 3–10 would be valid, and 15 not.
  * Under that reading, the stronger frame is kept 94 % of the time at +3 dB and 86 % at −3 dB,
    where the 4 dB rule keeps none; at 0 dB, both senders' frames are partly kept (0.31, 0.52).
* **At pi-A's lowest powers the partner link weakens.**
  * Alone, pi-A lost 5.7 % and 2.0 % of its frames at pi-B at 5 and 0 dBm, against 0.2–0.9 %
    above.
  * pi-B read pi-A at −69 and −71 dBm.
  * That breaks the identification's stated assumption at those steps, consistent with q_A < 0 at
    10 dB and q_A + q_B > 1 at 15 dB.
* **By Mohamed's rule,** a reading corrected this way is used only after a fresh registered check
  on unseen points.
