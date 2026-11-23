# W1s — the last board session of this phase: the capture curve, the window, the Pi 3's timing

*Registered 2026-11-23, before the session. Decided by Mohamed on 2026-11-23 (`docs/DECISIONS.md`):
items 1–3 form one session with a fixed end; U3 closes after it, whatever the outcomes; no further
hardware sessions in this phase. Plan approved the same day, with his changes to part A (below).
Code: `analysis/w1s.py` (`tests/test_w1s.py`). Kit: `hw/channel/run_window_plan2.sh` with
`chip_check.sh`, `rssi.sh`, `frameburst.sh`, tested off the boards.*

## The session (`experiments/channel24/plan_w1s.txt`, 42 windows)

* **The layout:** W1q's 1 m triangle, every side about 1 m, for the whole session. No board moves.
  * Part A needs this layout.
  * Parts B and C don't depend on the receivers' geometry. In a pair, the receiver is the other
    sender, so capture cannot occur.
  * It differs from W1p, which ran side by side.
* **The radio:** channel 11, 802.11b 1 Mb/s, the redrawn sender, frame burst off on all three
  boards, read back before and after.
* **The fixed end:** the last window ends at START + 21 min (1 260 s), and the boards are back on
  the LAN by about START + 23 min. Nothing is extended or re-run within this phase; a void part is
  recorded as void.
* **A board whose chip stops** (Mohamed, 2026-11-23) stops its own windows: `chip_check.sh`, before
  each window. Its stop is recorded, and every part that needs its windows is reported as not run.
* **Order:**
  * rate checks R1–R3;
  * part A: the anchor, then pi-A at 13, 11 and 10 dBm, then the negative step;
  * part B: the two 345 B backgrounds, then six pair windows;
  * part C: one more saturated window per board, then R1–R3 again.

## Validity, fixed now

* Frame burst reads 0 on every board, before and after.
* The six rate checks are inside W1d's band, 1.9–2.6 ms.
* No board throttled.
* Otherwise the session is void.

## Part A — W1q's gradual capture curve, checked on steps W1q did not use

**The reading under test:** the halfway RSSI reading alone, in each single-sender window, the
zero-address value (W1p's kit check rejected the per-peer one). ΔRSSI = pi-A − pi-B at the Pi 3.

**The curve.** Mohamed's criterion, applied to every step: **a step enters the curve only if each
sender's single-sender loss at every receiver is ≤ 1 %.** In W1q:

| W1q step | pi-A | Δ (halfway) | q_A | q_B | worst single-sender loss | enters |
|---|---|---|---|---|---|---|
| 0 | 15 dBm | +7 dB | 0.9847 | 0.0303 | 0.55 % | yes |
| 3 | 12 dBm | +3 dB | 0.9373 | −0.0012 | 0.91 % | yes |
| 6 | 9 dBm | 0 dB | 0.3111 | 0.5148 | 0.64 % | yes |
| 10 | 5 dBm | −3 dB | −0.1233 | 0.8557 | **5.73 %** (pi-A at pi-B) | **no** |
| 15 | 0 dBm | −6 dB | 0.2768 | 0.8957 | **2.00 %** (pi-A at pi-B) | **no** |

* So the curve is q_A(Δ) and q_B(Δ), piecewise linear through Δ = 0, +3 and +7 dB, with no fitted
  parameter (`results/raw/w1s_predictions.csv`, part A).

**The new steps** (pi-B at 15 dBm unless stated; whole dBm, as the driver has only been seen to
read back whole dB):

| step | pi-A | pi-B | Δ expected (W1q's halfway falls) | scored? |
|---|---|---|---|---|
| anchor | 15 dBm | 15 dBm | +7 dB | reported only, as day-to-day drift |
| 13 | 13 dBm | 15 dBm | about +5 dB | yes |
| 11 | 11 dBm | 15 dBm | about +2 dB | yes |
| 10 | 10 dBm | 15 dBm | about +1 dB | yes |
| negative | 15 dBm | **18 dBm** | about −3 dB | yes, if pi-B reads back 18.00 dBm |

* Each step is W1q's: one single-sender window per sender at 50 frames/s, then three capture
  windows at 600 frames/s. q is W1q's (`w1q.q_of`), the Pi 3 receiver's.
* **The same ≤ 1 % criterion applies to each new step,** judged from its own single-sender windows.
  A step that fails it is not scored.
* **The negative step** (Mohamed): pi-B raised to 18 dBm, so no link is weakened. **If the driver
  does not read back 18.00 dBm, the step is dropped, and the curve is stated as covering Δ ≥ 0
  only.**

**Holds, per step:**
* each sender's measured q (the mean of its three windows) lies within the curve's range over the
  measured Δ ± 1.5 dB (W1q's step tolerance), cut at the curve's span, widened by ±0.02 (W1q's
  typical window-to-window range);
* both senders must hold;
* a step whose |Δ| lies outside 0 … 7 dB is not scored.

**A step with Δ < 0 is read on the mirror.** The stronger sender's q comes from q_A's branch at
|Δ|, and the weaker's from q_B's.
* This is the hypothesis that capture follows the power difference, not which sender is stronger.
* The negative step tests it. W1q's Δ = 0 point already shows the senders are not identical
  (0.311 against 0.515).

**The curve is used only if at least two steps are scored and every scored step holds.**
Otherwise the thesis states W1q's scored result alone (5 of 6).

## Part B — the contention window, re-derived once, and one test

**The windows**, from each board's six in-session rate checks of 2026-11-22 (W1p, W1q and W1r,
before and after; frame burst off). The formula is `uh.board_windows`'s: cycle = T_f + DIFS +
σ(W − 1)/2, with T_f = 1 864 µs for the 145 B frame they were measured with.

| | cycles (µs): pi-A / pi-B / the Pi 3 | σ 20/DIFS 50: W | σ 9/DIFS 28: W |
|---|---|---|---|
| **mean (registered)** | 2 069.4 / 2 114.5 / 2 340.1 | **17, 21**, 44 | **40, 50**, 101 |
| minimum (reported) | 2 032.1 / 2 096.7 / 2 278.1 | 13, 19, 37 | 32, 46, 87 |
| maximum (reported) | 2 196.0 / 2 144.2 / 2 411.7 | 29, 24, 51 | 69, 57, 116 |

* Fixed now. This session's own rate checks are reported, not used to refit.

**The test:** the saturated pi-A + pi-B pair at **345 B of UDP payload**, a length no 2.4 GHz
session has used (stored plans and sessions used 118, 119, 145 and 1 000 B).
* Six windows of 25 s at 600 frames/s offered, both boards at 15 dBm.
* A window is usable with at least 2 500 frames on air per sender (about 3 000 expected).
* At least five usable windows.
* Each board alone at 50 frames/s at 345 B gives the link loss, reported.

**Predictions** (`python analysis/w1s.py --predict`): ns-3 through the audit twin (gate 9/9,
2026-11-23):
* N = 2, frameSize 373, 802.11b 1 Mb/s;
* `--cwMinList` W − 1 per board, `--slotUs=9` for σ 9;
* 30 seeds × 20 s.

| family | W (pi-A, pi-B) | pair loss (sd over seeds) | frames/s on air per sender | registered |
|---|---|---|---|---|
| **σ 20/DIFS 50** | 17, 21 | **0.1227** (0.0040) | **149.5** | yes |
| **σ 9/DIFS 28** | 40, 50 | **0.0686** (0.0040) | **145.9** | yes |
| σ 20/DIFS 50, minimum cycles | 13, 19 | 0.1418 | 151.5 | reported |
| σ 20/DIFS 50, maximum cycles | 29, 24 | 0.0955 | 145.9 | reported |
| σ 9/DIFS 28, minimum cycles | 32, 46 | 0.0754 | 147.0 | reported |
| σ 9/DIFS 28, maximum cycles | 69, 57 | 0.0556 | 143.3 | reported |

**Scored as:**
* **W1p's rule:** a family is consistent if its prediction lies inside the measured 95 % interval
  over windows (Student t, n − 1 degrees of freedom) for both the loss and the rate.
* **If exactly one is consistent,** it is the window this phase reports.
* **If neither is** (Mohamed, 2026-11-23), the window is recorded as **not identifiable without a
  frame sniffer**. The hardware is reported as bracketed by the two settings if its mean loss and
  rate each lie between their predictions; otherwise that it is not.
* **If both are,** they are not separated.

## Part C — the Pi 3's extra time per frame

**The hypothesis** (W1r, seen after scoring): the Pi 3's longer one-sender cycle is not a wider
random backoff.

**The measurement:**
* each board alone and saturated at 600 frames/s, 145 B, in R (before), S and R (after);
* the gap after each frame, from the receive timestamps, less the frame's airtime
  (`w1p.gaps_us`), pooled over the three windows;
* **primary:** the Pi 3 against pi-A, at the receiver that hears both, pi-B. Reported beside it:
  the Pi 3 against pi-B, at pi-A.

**The statistic:**
* If gap = DIFS + g₀ + kσ with k uniform on 0 … W − 1, then **median − IQR = DIFS + g₀**. The
  quartiles are `statistics.quantiles(n = 4)`.
* d = (median − IQR) of the Pi 3, less that of pi-A: the Pi 3's extra fixed time per frame. DIFS
  cancels.
* c = the Pi 3's mean rate-check cycle, less pi-A's, both from this session.

**Registered outcomes:**
* **d ≥ ⅔c:** most of the extra time is fixed per frame. The hypothesis is supported.
* **d ≤ ⅓c:** it is backoff. The hypothesis is rejected.
* **Between:** unresolved, so it is recorded as an unexplained property of the BCM43430 (Mohamed,
  2026-11-23).
* **Validity:** fewer than 5 % of gaps negative, which would be shorter than the frame itself.
  Otherwise the timestamps cannot resolve it, and the same "unexplained" line applies.

## My expectations `[agent]`

* **A:** the steps at +5 and +2 dB hold; the one at +1 dB is the hardest, on the steepest part of
  the curve. The negative step's mirror is uncertain: at 0 dB the two senders already differ.
* **B:** neither family is consistent, as at 145 B (see the disclosure). The loss lies between
  them; whether the rate does is open, since at 145 B it fell just below both.
* **C:** d is a large part of c, so the hypothesis is supported, or at least unresolved.

## Disclosure

* **Known before this registration:**
  * W1p, W1q and W1r with their outcomes;
  * W1q's halfway readings (`W1q.md`, "Seen after scoring");
  * W1r's direction split.
* **W1p's pair at 145 B** lost 0.1029 (0.0979–0.1079) at 262.7 (261.7–263.8) frames/s per sender.
  2/(W + 1) gives W ≈ 18.4, near σ 20's re-derived 17 and 21. **Run on 2026-11-23 for this
  disclosure, not as a prediction** (`python analysis/w1s.py --known145`,
  `results/raw/w1s_known145.csv`): the same windows at 145 B, 30 seeds, give:
  * σ 20/DIFS 50: 0.1228 at 268.6 frames/s;
  * σ 9/DIFS 28: 0.0675 at 263.0 frames/s.
  * Against W1p's measurement, **neither is consistent** (both losses fall outside its interval).
    The loss lies between them, but the rate 262.7 lies just below both.
* **The predicted loss does not depend on the frame length** (0.1228 against 0.1227; 0.0675
  against 0.0686): the collision rate is set by W.
  * So for the loss, the 345 B test nearly repeats W1p's point. What 345 B adds is the rate, which
    the frame length changes.
  * This was found after the length was chosen (the approved plan), and is stated here before the
    session.
* **W1p has saturated single-sender gaps for every board.** Their medians and IQRs were not computed
  before this registration.
* No session has used 345 B, pi-B at 18 dBm, or pi-A at 13, 11 or 10 dBm.
