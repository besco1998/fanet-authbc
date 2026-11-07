# W1e — three ad-hoc radios side by side at 2.4 GHz: the contention model, with the session between two rounds of rate checks

*Registered 2026-11-05, before the session. Main open item W1 (`docs/OPEN_ITEMS.md` §2a). Q15:
Mohamed chose this option ("yes", 2026-11-05). It follows W1d, whose S0 stopped the campaign
(F121), and the finding that what stopped it lay outside the Pi 3 (F122). Code, plan and
predictions at this commit:
* `analysis/dsss_w1e.py`, which imports `analysis/dsss_three.py` (registered at `prereg-W1d`) and
  leaves it unchanged;
* `experiments/channel24/plan_w1e.txt`;
* `results/raw/w1e_predictions.csv`;
* the kit, `hw/channel/run_window_plan.sh`, unchanged since W1d.*

## Why

* **W1d's S0 failed for the Pi 3.** Its cycle was 4.7–5.0 ms against the 1.9–2.6 ms band, so the
  registered stop rule ended that campaign.
* **The repeat passed.** Mohamed moved the Pi 3 beside the Pi 4s and unplugged one Blue, then S0 was
  repeated, disclosed and not scored (F122):
  * the Pi 3 ran at 2.45–2.51 ms;
  * the decay test showed no decay.

  The cause lay outside the Pi 3. Which of the two changes removed it is confounded and will stay
  so.
* **Loss cannot show that disturbance.** A sender made to defer loses nothing, it only sends less:
  the background was 0.09 % in both sessions. Only a single-sender rate check sees it. **So W1e
  runs W1d's contention windows between two rounds of rate checks, and the session counts only if
  every one of them is in the band.**

## What differs from W1d

| | W1d | W1e |
|---|---|---|
| placement | a circle of about 2 m | **side by side, 10–15 cm apart** (Mohamed), same height, antennas unobstructed |
| BeagleBone Blues | sniffers on channel 11 | **both unplugged** (their capture delivered nothing, F121; one was a suspect, F122) |
| rate checks | S0 only, two per board, the mean scored | **one per board before the contention windows and one after; each must be in the band, or the session is void** |
| sessions | S0, then S1 | **one session of 66 windows**, about 35 min |

**Everything else is W1d's, unchanged:**
* channel 11 (2462 MHz), 802.11b at 1 Mb/s, the ad-hoc cell `authbc-mesh`;
* frames of 145 B, each at an instant drawn anew in its period;
* windows of 25 s, senders sending for 22 s, starts 30 s apart on one shared clock;
* the delivered fraction, the usable-window rule (including the voltage rule) and the background;
* at least three usable windows per scored point;
* W1c's model rows and the bands.

Nodes: 1 = pi-A, 2 = pi-B (Raspberry Pi 4, BCM4345/6), 3 = the Raspberry Pi 3 (BCM43430/1).

## The session (`plan_w1e.txt`)

1. **R1, R2, R3:** each board alone, offered 600 frames/s.
2. **W1d's S1, unchanged:** at occupancies 0.50, 0.70 and 0.85, for each group (A–B, A–C, B–C and
   A–B–C), four windows, then a control window (one board alone at 50 frames/s).
3. **R1, R2, R3** again.

## Predictions (`analysis/dsss_w1e.py --predict`): W1d's, which are W1c's registered rows

| group (frames/s per board at occupancy 0.50 / 0.70 / 0.85) | model loss | band |
|---|---|---|
| a pair: A–B, A–C or B–C (131 / 183 / 222) | 0.217 / 0.552 / 1.426 % | 0.6–1.4× |
| the trio A–B–C (87 / 122 / 148) | 0.446 / 1.059 / 2.395 % | 0.3–1.4× |

The model knows nothing of chips, so a mixed pair carries the Pi 4 pair's prediction.

## Scored as

* **W1e-1 — the bracket.** In each of the six rate-check windows, the board's cycle lies within
  1.9–2.6 ms and no board lost voltage. **If any one fails or is missing, the session is void:** its
  contention points are reported, not scored, and anything further needs a new registration.
* **W1e-2 — background.** b ≤ 1 %, else the session is void.
* **W1e-3 — contention.** At each group and occupancy, the mean loss of the usable windows minus b
  lies in its band (12 points), as W1d-3.
* **Reported, not scored:**
  * each board's cycle before and after the session (a second chip and band for G27);
  * each chip's loss in the mixed pairs;
  * what the third board hears in pair windows;
  * the one-sender loss when saturated.

## My expectations `[agent]`

* **W1e-1:**
  * the Pi 4s hold (1 944–1 950 µs in every rate window so far);
  * the Pi 3 probably holds (2 452 and 2 507 µs in the repeat). But it is within about 100 µs of
    the band's top, so **a void session is a real possibility**, and I state it now.
* **W1e-2** holds (0.09 % in both sessions so far).
* **W1e-3:**
  * A–B fails low at occupancy 0.85, as the Pi 4 pair did at 5 GHz (F73: 0.56×; F115);
  * the trio holds, its band being wide;
  * I have no expectation for the mixed pairs: the two chips depart from the standard in
    opposite directions.

## What each outcome means

| outcome | meaning |
|---|---|
| valid, W1e-3 holds at most points | **the contention model, which every capacity rests on, predicts loss on real radios of two chip families with two and three stations**, at a second PHY, with nothing fitted |
| valid, W1e-3 fails at high load for the Pi 4 pair only | F73's own-queue departure recurs at 2.4 GHz and belongs to that chip; the mixed pairs say whether the Pi 3 shares it |
| valid, W1e-3 fails broadly | the model does not describe these radios at 802.11b; reported plainly, and the hardware support for the capacities is weaker than the paper states |
| void | the disturbance of S0, or another like it, was present. Nothing is scored, and the bracket did its job |

## What it cannot show

* **The capacity ratio:** three stations reach the crossing only in overload (F120).
* **The paper's PHY:** this is 802.11b at 1 Mb/s, not 802.11a at 6 Mb/s.
* **The cause of W1d's S0 failure:** it stays confounded (F122).
* **Capture** is limited only by the placement. At 10–15 cm the three receive one another at
  similar, strong levels. **Interference** is limited by the channel, the controls and the
  bracket.

## Disclosure

* On this kit and these boards, at channel 11, the following have already run (all on record in
  `predictions/W1d.md`, F121 and F122):
  * W1d's probe: one trio window at 87 frames/s, loss 0.25 %;
  * W1d's S0;
  * the repeat of S0 in the present placement, with Blue 1 still powered;
  * three diagnostics and the repeated decay test of the Pi 3.
* Known before registering:
  * the Pi 4s' cycles (1 944–1 950 µs) and the Pi 3's (2 452–2 507 µs in the repeat);
  * the background (0.09 %);
  * the one-sender saturated loss (0.70–0.81 %).
* **No contention window of W1d's S1 has ever been run on these boards.**

---

## Outcome — added 2026-11-05, after the session; nothing above this line was changed

Registered at `2409d36` (tag `prereg-W1e`, pushed 13:31). The session ran 13:34–14:07 on channel 11;
`analysis/dsss_w1e.py --score` (unchanged since) → `results/raw/w1e_w1e_2026-11-05.csv`, windows
`results/hw/channel24/w1e_2026-11-05_windows.csv`, files `results/hw/channel24/w1e_2026-11-05/`.
**All 66 windows were usable**: nothing dropped before the air, no late frame, every sender at its
rate, no board lost voltage. A re-score is identical, and the one miss was recomputed
independently from the raw files.

**W1e-1, the bracket: held, so the session is valid.**

| | before | after |
|---|---|---|
| pi-A | 1 945.8 µs | 1 945.4 µs |
| pi-B | 1 944.4 µs | 1 944.5 µs |
| Pi 3 | 2 292.7 µs | 2 358.2 µs |

**W1e-2, the background: held,** b = 0.174 % over 12 control windows (0.045–0.455 %; standard
error 0.033 %). It is higher than S0's 0.09 %.

**W1e-3, contention: 11 of 12 held.** Measured loss minus b, against the model:

| group | occupancy 0.50 | 0.70 | 0.85 |
|---|---|---|---|
| A–B (Pi 4 + Pi 4) | **0.311 % vs 0.217 % = 1.44× — failed** (band top 1.40×) | 0.524 % = 0.95× | 1.154 % = 0.81× |
| A–C (Pi 4 + Pi 3) | 0.251 % = 1.16× | 0.617 % = 1.12× | 1.367 % = 0.96× |
| B–C (Pi 4 + Pi 3) | 0.273 % = 1.26× | 0.642 % = 1.16× | 1.328 % = 0.93× |
| A–B–C (trio) | 0.577 % vs 0.446 % = 1.29× | 1.339 % vs 1.059 % = 1.26× | 2.540 % vs 2.395 % = 1.06× |

**The one miss, as it is.**
* A–B at 131 frames/s: its four windows gave 0.398, 0.277, 0.259 and 0.312 % (net). Their mean
  exceeds the band's top by 0.0075 percentage points, less than the background's own standard
  error.
* These were the first contention windows of the session (13:35–13:37), before any of the events
  below.
* By the registered rule it is a miss, and it is reported as one.

**My expectations.**
* "A–B fails low at occupancy 0.85" was **wrong**: 0.81×, inside the band. At 5 GHz the Pi 4 pair
  gave 0.56× (F73); at 802.11b it does not depart below.
* "The Pi 3 probably holds the bracket" held.
* "The trio holds" held.

**A pattern across all twelve points (reported, not scored).**
* Every group lies above the model at low load (1.16–1.44× at occupancy 0.50) and drifts down to
  0.81–1.06× at 0.85.
* W2 lists the same symptom at 5 GHz ("loss above the model at occupancy 0.50").
* One reading fits what was measured here, but is not tested: a receiver-side loss that grows
  with the received rate. One saturated sender loses 0.66–0.80 % at the receivers, while 50
  frames/s loses about 0.17 %. The background is measured at 50 frames/s, so it under-subtracts at
  higher received rates, and the excess weighs most where contention loss is smallest.

**Disclosed events during the session (Mohamed's, while preparing the next step).** In neither
period does a window differ from the rest:
* **A USB Wi-Fi adapter (TP-Link TL-WN722N) was plugged into the PC from about 13:48 to 13:57**
  (windows 28–46), disconnected under Windows, which scans with it. Controls in that period:
  0.045–0.273 %. All points there held.
* **BeagleBone Blue 2, with that adapter, was powered from the PC's USB at about 14:02** (up four
  minutes at 14:06:09). Its radios were taken down at 14:06:29, before the last rate check.
  Windows 55–65 overlap. Their control (0.091 %) and rate checks were in range.

**What it means.** The contention model, on which every capacity rests, predicted the loss of real
radios of two chip families with two and three stations, at a second PHY, with nothing fitted,
within its bands at 11 of 12 points. The miss is marginal and at the lowest load. The
consistent excess at low load is a second appearance of W2's open symptom. F123.
