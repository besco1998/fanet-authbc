# W1j — the 1 m square, the Pi 3 moved inward, powers fixed at the setting that balanced: one long run

*Registered 2026-11-06, before the run. Main open item W1. It follows W1i (F131), and tonight's
square-layout preflights (`results/hw/channel24/square_2026-11-06/`).
* **Mohamed:** "can we run the long test directly to save time".
* **So no new code:** the powers are the ones the last preflight balanced at, and are fixed here.

Code, plan and kit at this commit, all unchanged:
* the plan `experiments/channel24/plan_w1h.txt`;
* the gate `analysis/dsss_w1h.py` (`prereg-W1h`);
* the score `analysis/dsss_w1i.py --score … --powers 1:600,2:auto,3:1100` (`prereg-W1i`);
* the kit `hw/channel/` as in W1i.

The scored predictions are W1f's (through `w1g_predictions.csv`), unchanged.*

## Setup (fixed here)

* **The square**, set by Mohamed:
  * the four boards on the corners of a 1 m square, at the same height, all antennas toward the
    centre;
  * pi-B and the Pi 3 swapped from his first placement;
  * **the Pi 3 moved 35 cm along its diagonal toward the centre**;
  * Blue 2 at its corner, router signal −67 dBm.
* **Powers held through the windows:** pi-A at **600 mBm**, the Pi 3 at **1100 mBm**, pi-B at
  default (`auto`). Each is set by `set_txpower_window.sh`, read back, and returned to `auto` after.
* **The rest:**
  * channel 11, 802.11b at 1 Mb/s;
  * node 4 at `FIXED CCK_1M` on a freshly rebooted Blue 2;
  * the Pis not rebooted (F129: a warm Pi creates the cell);
  * Bluetooth on, as in every earlier session.

## The run

* **One long run:** `plan_w1h.txt` (R1–R4, G31 ×4, W1g's capacity block, R1–R4), about 26 minutes.
* **The gate is W1h's, unchanged,** read after the run: the G31 senders within 1.5×, the rate
  checks before in band, node 4 joined.
  * **GO:** the run is the session, scored once, whatever its outcome.
  * **ABORT:** discarded unscored, and W1j ends. No further run under W1j.

## Predictions

**W1f's registered values, unchanged:**
* the AUTHBC crossing 29.50 (band 26.55–32.45);
* the per-record crossing 8.93 (8.04–9.82);
* **the ratio 3.304 (2.974–3.635, and above 2.5).**

## Validity: the session is void if any of these fails

`dsss_w1i.score`:
* **V1:** all eight rate checks in 1.9–2.6 ms, with no Pi under-voltage;
* **V2:** b ≤ 1 %;
* **V3:** node 4 in the Pis' cell, all Pis reached;
* **V4:** `rate_ctl` fixed;
* **V5:** the session's own A31 windows within **1.5×**, not widened;
* **V6:** pi-A's log at 6.00 dBm and the Pi 3's at 11.00 dBm read back, then `auto`.

## Scored as

* **W1j-1:** the bracket (V1).
* **W1j-2:** the background (V2).
* **W1j-3:** AUTHBC's crossing within 26.55–32.45.
* **W1j-4:** per-record's crossing within 8.04–9.82.
* **W1j-5 — the claim:** the ratio within 2.974–3.635, and above 2.5.

## My expectations `[agent]`

* **The gate GO.** The last preflight read 1.249×.
* **V5 probably holds, not certainly.** Readings at one setting wandered about ±0.1× today, and the
  rule allows 1.5×. Here the balance depends on 1–2 dB of the Pi 3's power: at 10 dBm it was the
  weakest sender, at 12 dBm the strongest.
* **V1 holds.** The Pi 3 read 2 226–2 380 µs at this spot.
* **The crossings near 31 and 9.3, and the ratio near 3.3, inside its band.**

## Disclosure

* **Known before this registration:**
  * W1h's void session (crossings 30.99 / 9.33, ratio 3.32);
  * W1i (F131);
  * W1g, the calibration, W1f, the probes (F124–F130).
* **Tonight's square preflights, all at 1 Mb/s unless noted** (each 6 windows, no capacity
  window):
  * the first square at default power (6 Mb/s after a power-cycle; then 1.59×, the Pi 3 slow at
    3 245 µs);
  * pi-B and the Pi 3 swapped (2.17×, the Pi 3 still slow at 3 485 µs);
  * Bluetooth off (2.39×, no change; turned back on);
  * the Pi 3 35 cm inward (2.22×, the Pi 3 back in band at 2 226 µs);
  * then four power settings: 10 / auto / 10 dBm 2.12×, 4 / auto / auto 2.10×,
    6 / auto / 10 dBm 1.36×, 6 / auto / 12 dBm 1.46×;
  * **6 / auto / 11 dBm 1.249×.**

  The powers registered here were chosen from these, on G31 windows only.
* **The launch and collect tools hold credentials** and are not in the repo. They do only what
  this file states.
* **No window of the W1j run has been run.**

---

## Outcome — added 2026-11-06, 20:25, after the run; nothing above this line was changed

**How it ran.**
* The run lasted 19:52:18–20:18:18, on Blue 2's boot `5ad256eb`.
  * All four boards ran all 52 windows and reverted.
  * Node 4 was in the Pis' cell (`2a:e2:ae:2d:71:69`) at `FIXED CCK_1M`, with every Pi reached.
  * pi-A was held at 6.00 dBm and the Pi 3 at 11.00 dBm (from 19:51:28), both returned to auto
    (20:18:23).
* **The gate said GO**: G31 spread 1.092× (pi-A 5.64 %, pi-B 5.79 %, Pi 3 5.48 %, TP-Link
  5.98 %), the rate checks before in band. So it is the session.
* Scored by `dsss_w1i.py --score … --powers 1:600,2:auto,3:1100`; the registered code is unchanged
  since `prereg-W1j` (an empty diff).
* Outputs:
  * `results/raw/w1i_w1j_2026-11-06_run.csv`;
  * `results/hw/channel24/w1j_2026-11-06_run_windows.csv`;
  * the files in `results/hw/channel24/w1j_2026-11-06/w1j_2026-11-06_run/`.
* An independent script (plain Python on the raw files) agrees exactly.

**The session is VALID. Every condition held:**
* V1: all eight rate checks in band, the Pi 3 at 2 344.9 µs before and 2 286.9 µs after;
* V2: b = 0.22 %;
* V3, V4;
* **V5: the A31 spread 1.208×**, each of its four windows within 1.07–1.39×;
* V6 for both held Pis.

**Scored:**

| | measured | registered model | band | held |
|---|---|---|---|---|
| W1j-1 the bracket | 8/8 in band | | 1.9–2.6 ms | **yes** |
| W1j-2 the background | 0.22 % | | ≤ 1 % | **yes** |
| W1j-3 AUTHBC crossing | **30.48** (95 % CI 30.29–31.05) | 29.50 | 26.55–32.45 | **yes** (+3.3 %) |
| W1j-4 per-record crossing | **9.29** (95 % CI 9.27–9.32) | 8.93 | 8.04–9.82 | **yes** (+4.1 %) |
| **W1j-5 the ratio** | **3.280** | **3.304** | 2.974–3.635, > 2.5 | **yes** (−0.7 %) |

**The points** (V/(1 − b); four windows each, each standard deviation 0.002–0.005):
* AUTHBC A29–A32: 0.9649 / 0.9539 / 0.9458 / 0.9345;
* per-record P9–P9.75: 0.9595 / 0.9523 / 0.9393 / 0.9332.

Every point lies above the model's (capture, F127). Both crossings shift up by similar fractions,
and in the ratio the shifts nearly cancel.

**My expectations.** Each held:
* the gate GO;
* V5 (1.208×);
* V1;
* the crossings near 31 / 9.3 (30.48 / 9.29);
* the ratio near 3.3 (3.28).

**What it means.** **The AUTHBC / per-record capacity ratio was measured on four real radios —
balanced and with capture present — at 3.28, within 0.7 % of the model's 3.30.** The paper's claim
holds on hardware, within the limits below. F132.

**Limits, as registered:**
* 802.11b at 1 Mb/s, not the paper's PHY;
* four boards, through A12's mapping;
* one session;
* capture present;
* the layout and powers were selected by preflights on G31 windows, never on scored ones.
