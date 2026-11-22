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

## Outcome — added 2026-11-22, after the session; nothing above this line was changed

* **The session:** `results/hw/channel24/w1p_2026-11-22`, 09:32–09:44, side by side, all 15
  windows done on every board. Scored with `python analysis/w1p.py --score` on the three boards'
  files. pi-B's were collected at 15:59: its chip locked during the revert after the last window,
  and only a power cut recovered it (`docs/LOGBOOK.md`). The windows were complete by then.

### Validity — held

* **Frame burst** read 0 before the first window and after the last, on all three.
* **The rate checks,** all inside 1.9–2.6 ms per frame:
  * pi-A 2 032.1 and 2 033.9 µs;
  * pi-B 2 096.7 and 2 098.6 µs;
  * the Pi 3 2 309.4 and 2 278.1 µs.
* **No board throttled.** **6 of 6 pair windows usable** (the fewest frames on air was 5 556).

### Step 0 — the receive-timestamp jitter (reported)

| board | J, least squares (µs) | J, robust (µs) |
|---|---|---|
| pi-A | 161.65 | −24.87 (its square is negative: not resolved) |
| pi-B | 307.59 | 25.69 |
| the Pi 3 | 447.61 | 30.18 |

* The standard error of each J² is 5 187 µs², so a jitter below about 72 µs is not resolved by
  the least-squares form.
* **The two forms disagree by an order of magnitude.** The least-squares residuals are dominated
  by rare long delays; the robust form gives the tens of µs expected. Both are reported, as
  registered; neither is adopted here.

### The kit check — rejected at all three boards

* `per_mac_accepted` rejected the per-peer reading at pi-A, pi-B and the Pi 3. A per-peer reading
  equalled the zero-address reading in 19, 21 and 14 of the 30 reads.
* **The registered fallback applies to W1q and W1r:** the zero-address reading in each
  single-sender window.

### Primary — the saturated pair

| | measured, 6 windows (95 % interval) | σ 20 / DIFS 50, W 4, 4 | σ 9 / DIFS 28, W 12, 13 |
|---|---|---|---|
| loss at the partner | **0.1029** (0.0979–0.1079) | 0.4128 | 0.1686 |
| frames/s on air per board | **262.7** (261.7–263.8) | 331.0 | 288.2 |
| consistent (both inside) | | **no** | **no** |

* **By the registered rule, W is not identified within these two families.** The nearer by loss
  is σ 9 µs / DIFS 28 µs (0.169 against a measured 0.103); it is reported and not adopted. W1r
  reports both families.
* **Model-dependent, not used:** 2/(W + 1) gives 0.400 at W = 4 and 0.154 / 0.143 at W = 12 / 13.
  Under it, the measured 0.103 corresponds to W ≈ 18.4.
* **Checked independently:** a separate script read the raw receive files without the project's
  code and gave the same loss and rate to four places.
  * At the partner, frames on air equal the sender's own count within 2 frames in every window.
  * The two directions lose 567–662 frames per window and differ by 2.5–5.1 %; in every window
    15–31 more of pi-A's frames are lost than of pi-B's.
  * At 50 frames/s the link lost 5 and 4 of 2 850, so the loss at saturation is collisions.

### Supporting — the gaps (reported)

* **The gap means** agree with this session's own first rate checks less T_f:
  * pi-A 166.5 and 165.8 µs (rate check: 168.1);
  * pi-B 231.9 and 230.1 µs (232.7);
  * the Pi 3 447.5 and 448.0 µs (445.4).
* **Against the families:** their gap means are 80–82 µs for the Pi 4s and 550 µs for the Pi 3.
* **The spreads** are 291–790 µs, against the families' 22–34 µs (Pi 4s) and 294–304 µs (Pi 3).
* The jitter correction gives negative variances (shown signed), so the gaps do not separate the
  families. The registered caveat for a large J applies.

### My expectations, against the outcome

* **"The 9 µs family is consistent and the 20 µs family is not": wrong.** The 20 µs family's
  rejection held. The 9 µs family failed too, on both loss and rate.
* **"The jitter will be tens of µs":** right for the robust form (25–30 µs), wrong for the
  least-squares form (162–448 µs).

### Seen after scoring — not a result

* **Both families' W were fitted to W1f's single-sender cycle,** 1 941–1 945 µs for the Pi 4s.
  W1f ran with frame burst at the driver's setting, on; it did not log it.
* **With frame burst off, this session's cycles are longer:**
  * pi-A 2 032 µs, 4.7 % longer;
  * pi-B 2 097 µs, 7.8 % longer;
  * the Pi 3 2 309 / 2 278 µs, against W1f's 2 413.
* **So both families assumed a shorter backoff than these boards had.** That predicts more frames
  on air and more collisions than measured, the direction of both misses.
* **F76** (2026-10-09, a saturated pair with frame burst off) measured 12.40 % (sd 0.70) and
  262.7 frames/s per sender. Today's rate is the same; the loss is 2.1 points lower.
* **By Mohamed's rule,** a W re-derived from today's cycles needs a fresh registered check on unseen
  points before it is used. It is not used here, and W1r runs as registered.
