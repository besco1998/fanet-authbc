# W1a — does AUTHBC's capacity ratio survive a radio that does not keep the standard's rule?

*Registered 2026-11-05, before any ns-3 run at these windows. Main open item W1
(`docs/OPEN_ITEMS.md` §2a), option (a), on Mohamed's word "for now do the desk work". Code and
predictions at this commit: `analysis/mac_robustness.py`, `results/raw/w1a_predictions.csv`,
`experiments/mac-robustness/plan_cw{3,7}.txt`.*

## Why

Every capacity in the paper is that of a radio that keeps the 802.11 access rule. No measured
card does: Bianchi et al. (INFOCOM 2007) found none of six, and ours does not (F74). A reviewer
can therefore say the capacities belong to an ideal radio. The paper's claim is the **ratio**:
AUTHBC (cell D) carries about 3.5 times as many nodes as per-record signing (cell C). This asks
whether that ratio survives the deviations measured on real cards.

## The deviations, a priori

* **Primary: a smaller contention window**, the deviation Bianchi et al. found most often:
  * Ralink and Realtek use CWmin 7 where 802.11b requires 31, a quarter of the window;
  * Broadcom under Linux uses 15, half of it.
  * In 802.11a terms (standard W = CWmin + 1 = 16) that is **W = 4** and **W = 8**. W = 16 is the
    control.
* **Secondary, model only:** the five rules calibrated on our own chip in G27 (`predictions/G27.md`),
  in both frame-burst states.

## Predictions (this commit; `analysis/mac_robustness.py --predict`)

The event model is `dcf_own_queue` with every counter drawn from the window (the corrected loop,
F114; at these cells it differs from the frozen one by 1 frame in about 900 000). It uses 30 seeds
× 20 s and interpolates the crossing of V = 0.95. The closed form of docs/02 §6g is beside it.

| window | C, model | D, model | **D/C, model** | C, closed form | D, closed form | D/C, closed form |
|---|---|---|---|---|---|---|
| 4 | **25.09** | **87.64** | **3.493** | 22.39 | 78.11 | 3.488 |
| 8 | **30.09** | **106.18** | **3.529** | 28.85 | 101.59 | 3.521 |
| 16 (control) | 34.99 | 124.15 | 3.548 | 35.75 | 126.70 | 3.544 |

The control reproduces the model crossings on file (`dcf_model_vs_ns3.csv`): C 34.99 exactly; D
124.15 against 123.70 (+0.36 %, interpolation on another grid). At W = 4 the closed form and the
event model part by 11 %. With a window of four, ties dominate, and the closed form's tie term is a
first-order expression (docs/02 §6g). **The model is the registered prediction.**

**Secondary: G27's rules, model only** (crossings C / D, ratio):

| | on | off |
|---|---|---|
| R1, every counter from W (3 on, 10 off) | 23.19 / 79.82, **3.442** | 31.91 / 112.24, 3.518 |
| R2, zero post-transmission counters | 35.10 / 124.26, 3.541 | 34.88 / 124.33, 3.564 |
| R3, burst | 35.17 / 124.08, 3.528 | 35.15 / 124.07, 3.530 |
| R4, small window after own frame only | 35.08 / 124.07, 3.537 | 34.94 / 124.40, 3.560 |
| R5, shorter slot (1.44 / 5.31 µs) | 24.01 / 83.57, 3.480 | 35.81 / 126.23, 3.525 |

At the operating point the own-queue rules (R2–R4) move nothing, because a station rarely holds
two frames. The window (R1) and a slot shorter than the detection time (R5 on) lower both
capacities by about a third.

## The test

ns-3, the published scenario and source, `--cw-min 3` (W = 4) and `--cw-min 7` (W = 8), 30 seeds ×
20 s on the grids of `experiments/mac-robustness/` (C step 1, D step 3, seven points around each
prediction): 840 runs. Crossings are interpolated on node counts with all 30 runs.

**Scored as:**
* **W1a-1.** Each ns-3 crossing lies within ±3 % of the model's (F5's tolerance). The bands are
  25.09 → 24.34–25.84, 87.64 → 85.01–90.26, 30.09 → 29.19–30.99, 106.18 → 103.00–109.37.
* **W1a-2 — the claim.** The ns-3 ratio D/C lies within 3.3–3.8 at both windows (S01's band).

## My expectations `[agent]`

* W1a-1 and W1a-2 hold at W = 8. At W = 4 I am less sure of W1a-1: the event model and the closed
  form already part by 11 % there, and ns-3's detection of a frame differs from the model's 4 µs
  rule. **I expect the ratio (W1a-2) to hold at both windows** even if a crossing misses.
* Written in the plan before the model ran, from the closed form: capacities fall by about 19 %
  (W = 8) and 37 % (W = 4). The model says 14 % and 28 %. ns-3 is scored against the model; this
  line records what I expected before it.

## What each outcome means

| outcome | meaning |
|---|---|
| W1a-2 holds at both windows | AUTHBC's advantage does not depend on the radio keeping the standard's window; the paper can say the capacities are a standard radio's, and the ratio is not |
| W1a-2 fails | the ratio depends on the window; the paper must state the ratio for a standard radio only |
| W1a-1 fails, W1a-2 holds | the model's capacities drift from ns-3 at small windows, but the conclusion holds |

## What it cannot show

* A window is one deviation. Forwarding delays, EIFS handling and our chip's unexplained
  behaviour (F115) are not tested in ns-3. G27's rules are in the model only.
* One collision domain, equal power and static nodes, as for the published capacities.

## Disclosure

* The closed form for W = 4–32 was computed while planning (2026-11-04). The event-model
  predictions above were run for this registration, before it was written.
* **No ns-3 run has been made at either window.**
* The same session registered W4a (`1dc2301`). Its tag broke a thesis test, so this commit adds
  a named holding list for the new registrations (`NOT_YET_IN_THE_THESIS`, Q11).
