# W1p — the contention window against slot and DIFS, on the three Pis at 2.4 GHz (session 3)

*Registered 2026-11-21, before the session. Plan: session 3 of
`docs/revision/2026-11-20_session_plans.md`, approved by Mohamed on 2026-11-21 with his changes
(`docs/DECISIONS.md`): the saturated pair is the primary test of W, and the gap distribution is
supporting evidence; the timestamp jitter on the same boards is measured and reported first.
Code: `analysis/w1p.py`. Kit: `hw/channel/run_window_plan2.sh`, `rssi.sh`, `bcast_rx.py
--timestamps`, tested off the boards (`tests/test_session_kit.py`, `tests/test_w1p.py`).*

## Why

* **The one-sender cycle fits two settings.** At 2.4 GHz the Pis' one-sender cycle (1 941–1 945 µs
  for the Pi 4s, 2 413 µs for the Pi 3, W1f) fits both:
  * the standard slot and DIFS, σ 20 µs and DIFS 50 µs, with W = 4, 4, 51;
  * σ 9 µs and DIFS 28 µs, with W = 12, 13, 117.
* **The mean of a cycle cannot separate them** (`analysis/uh.py`, U-H).
* **F116's W = 16 is a literature value, not a measurement,** and is not used (Mohamed,
  2026-11-19).
* **U-H (b):** W1f at 65 frames/s lay between the 9 µs family's two capture ends. By Mohamed's
  rule that session cannot choose the family, because H reproduces it. This one can: no session
  H reproduces is used.

## The boards and the layout

* pi-A (node 1) and pi-B (node 2), BCM4345/6; the Pi 3 (node 3), BCM43430/1;
* channel 11, 802.11b at 1 Mb/s, the 145 B UDP frame (1 864 µs on air);
* the redrawn sender (`bcast_tx.py --redraw`);
* **the side-by-side layout** of W1e (10–15 cm apart), the one session 2 uses, with positions taped
  and photographed;
* **frame burst set off on all three** (`run_window_plan2.sh`), read back before the first window
  and after the last.

## The session (`experiments/channel24/plan_w1p.txt`, 15 windows, about 10 minutes)

| windows | what | why |
|---|---|---|
| J1, J2, J3 | each board alone at 50 frames/s for 60 s; the other two keep every frame's receive time | step 0: the jitter; the kit check; link backgrounds |
| R1, R2, R3 | each board alone at 600 frames/s offered, 25 s | rate checks; the gap distributions |
| P × 6 | pi-A and pi-B both at 600 frames/s offered, 25 s | **the primary test** |
| R1, R2, R3 | as before | the bracket |

## Step 0 — the receive-timestamp jitter, reported first

* In window J_j, the other two boards timestamp the same frames.
* Per receiver pair, a least-squares line t_k = a + b·t_i removes the two clocks' offset and drift.
  The residual variance is J_i² + J_k², if the boards' jitters are independent (stated).
* Three windows give three pair variances, and so each board's J:
  J_a² = (V_ab + V_ac − V_bc)/2, and so on (`board_jitter_us`).
* **The precision, stated now:**
  * each J² is a difference of pair variances, with standard error
    ½·√(Σ 2V²/(n − 2)) (`board_jitter_sq_se_us2`);
  * the smallest jitter is resolved only if that error is below its square;
  * with 3 000 frames per pair (60 s at 50 frames/s), the synthetic test recovers 12 and 25 µs to
    15 % and 10 %, and a 5 µs jitter beside them only within its error.
* **Also given:** the robust form (1.4826·MAD)², and the same estimate from the rate-check windows,
  where the senders are saturated.
* **Reported, not scored.**

## The kit check, in the step-0 windows (`per_mac_accepted`)

* At each receiver, the firmware's per-peer RSSI (`rssi.sh <mac>`) is **accepted** only if:
  * each peer's readings lie within ±2 dB of their median in every window;
  * in the peer's own window they lie within 2 dB of the zero-address reading;
  * at least two peers differ by 4 dB or more, so that a reading tied to the address can be told
    from one that follows the last frame.
* **Otherwise** it is "not shown" or "rejected", and **the fallback** applies to every later
  session that evening: the zero-address reading in each single-sender window.

## Primary — the saturated pair (6 windows)

* **What is measured, as `contention_hw.saturated` measures it:**
  * a sender's frames on air are its partner's span of sequence numbers;
  * the loss is the share of them its partner did not receive;
  * the rate is frames on air per second.
* A board that is transmitting cannot receive, so capture cannot rescue a collided frame at the
  partner. Per window, the two directions are averaged.
* **The predictions, ns-3** (`python analysis/w1p.py --predict`, `results/raw/w1p_predictions.csv`):
  * the audit twin, N = 2, 600 frames/s offered, frameSize 173, 802.11b 1 Mb/s;
  * each board's window from its cycle (`--cwMinList`), the slot by `--slotUs`;
  * 30 seeds × 20 s; frames on air from the MAC trace's transmission starts, receptions from
    `--perPair`.

| family | W (pi-A, pi-B) | loss at the partner | frames/s on air per board |
|---|---|---|---|
| σ 20 µs, DIFS 50 µs | 4, 4 | **0.4128** (sd over seeds 0.0056) | **331.0** (1.1) |
| σ 9 µs, DIFS 28 µs | 12, 13 | **0.1686** (0.0042) | **288.2** (0.6) |

* **The rule, fixed now (`consistent`):**
  * a family is **consistent** if its ns-3 value lies inside the measured 95 % interval over the
    six windows, the mean ± t(0.975, 5)·sd/√6, **for both the loss and the rate**;
  * **if exactly one family is consistent, it is the one W1r's analysis uses;**
  * if neither is, W is not identified within these two families. That is a finding: the nearer
    family by loss is reported, not adopted, and W1r reports both;
  * if both are (not expected: the losses are 2.4 times apart), W1r reports both.
* **The approximation 2/(W + 1)** for saturated broadcast at N = 2 is reported beside them, marked
  model-dependent, and not used for the rule.

## Supporting — the gap distribution of each board alone, saturated (R windows)

* **The gap after a frame:** the receive-time difference of consecutive sequence numbers, less
  T_f = 1 864 µs (`gaps_us`).
* **Predicted, on the lattice DIFS + kσ, k uniform on 0 … W − 1** (`gap_moments_us`):

| board | σ 20 / DIFS 50: W, mean, sd (µs) | σ 9 / DIFS 28: W, mean, sd (µs) |
|---|---|---|
| pi-A | 4, 80.0, 22.4 | 12, 77.5, 31.1 |
| pi-B | 4, 80.0, 22.4 | 13, 82.0, 33.7 |
| the Pi 3 | 51, 550.0, 294.4 | 117, 550.0, 304.0 |

* **What separates the families:**
  * the means agree by construction (W was derived from the cycle);
  * the Pi 4s' spreads differ, 22.4 against 31–34 µs;
  * so does the smallest gap, 50 against 28 µs.
* **What is reported:**
  * the measured standard deviation corrected for two timestamps' jitter, √(sd² − 2J_r²), with
    J_r the receiver's from step 0 (`gap_summary`);
  * the 5th percentile of the gaps.
* **Reported, not scored.** It supports the primary result or questions it, and the evidence is
  weak if J_r is comparable to 20 µs.

## Validity, fixed now

* **Frame burst:** a board that does not read 0 before the first window and after the last voids
  the session.
* **The rate checks:** all six inside W1d's band, 1.9–2.6 ms per frame, or the session is void
  (W1e's bracket).
* **A window is unusable** if a board's supply was throttled (W1d's rule), or a saturated sender
  put fewer than 5 000 frames on air.
* **At least five of the six pair windows** must be usable.

## My expectations `[agent]`

* **The 9 µs family is consistent and the 20 µs family is not.** U-H (b) put the hardware between
  the 9 µs family's capture ends, though by the rule that does not count. If instead neither is,
  the hardware's queue or retry behaviour differs from ns-3's, the F115 pattern.
* **The jitter will be tens of µs** (SDIO interrupts), large enough to blur the 9 µs lattice; the
  gap spread may then not separate the families.

## Disclosure

* **Known before this registration:**
  * W1d–W1n, F115, F116, F121–F134;
  * U-H (a) and (b), including the H (b) comparison above;
  * the ns-3 predictions in the table.
* **No session of this kind has been run.** No 2.4 GHz saturated pair has ever been recorded with
  frame burst logged.
