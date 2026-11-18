# U-C5-D1 — the best batch under bit errors, at 802.11a 48 Mb/s with constant received power

*Registered 2026-11-18, before any D1 capacity run; the time is the commit's. C5 of the task of
2026-11-17, respecified as work package D of `docs/prompts/CAPTURE_PROMPT.md` (§8, setting D1).
Mohamed approved the plan the same day. The model is
`docs/revision/2026-11-17_unified_model_spec.md` (`src/authbc/models/unified_capacity.py`), with
rule R5 (an interior best batch). Why C5 could not run as first specified is finding F135: at
6 Mb/s with constant power a frame is either perfect or never received.*

## What is run

* **The PHY.** 802.11a at 48 Mb/s for every frame, ns-3's published detection model
  (ThresholdPreambleDetectionModel, 4 dB / −82 dBm), its error model (TableBasedErrorRateModel,
  `yans-wifi-helper.cc`:76), no fading.
* **One received power for every link: −77.17 dBm.** It is set through the audit twin's
  `--rxPowerDbm` (FixedRssLossModel after the usual loss).
* **The traffic.** The lean format ℓ(b) = 137 + 9b at Λ = 200 records/s, so f = 200/b frames/s,
  for b = 1, 2, 4, 8, 16, 32. Cells W48B1 … W48B32 in `ns3/run_unified.py`.
* **The measured quantity:** the delivered fraction (noise and collisions together). Capacity is
  its crossing at 0.95.
* **Method,** as U-C2:
  * a pilot of 5 seeds on seven node counts at ±5 % steps around the prediction;
  * then 30 seeds on seven node counts: centred on the rounded pilot crossing, in steps of 2 % of
    it (at least one station);
  * 20 simulated seconds, the designated source (a jitter of one period), straight-line crossing
    with its bootstrap interval.
  * **b = 32 has no predicted crossing** (below). It is run at N = 2, 3 and 4 with 30 seeds.

## How the power was chosen (before this registration, from no capacity run)

* **The rule, stated before it was applied:** the 0.01 dB step at which ns-3's error model gives
  the 173 B frame the loss nearest 3.00 % (the prompt's "about 3 %"), among the powers where no
  sweep point's collision budget lies within ±0.1 % of zero.
  * −77.20 dBm was excluded: there b = 16 loses 5.003 %, a budget of −0.003 %.
* **The pilot** (`ns3/c5_power_pilot.py`; two stations, noise only, 100 s, 50 frames/s) checks
  that ns-3's PHY loses what its error model says:
  * seeds 1–3 at every length (`results/raw/c5_d1_power_pilot.csv`). At −77.17 dBm the 173 B
    frame loses **3.042 %** in ns-3 against 3.025 % computed;
  * 20 more seeds (`results/raw/c5_d1_power_pilot_s4-23.csv`), because seeds 1–3 erred high at
    every length. Within one seed the lengths share the error model's random draws, so their
    deviations have one sign; across seeds they are independent.
    * With 20 seeds every length errs slightly low, −0.5 … −1.8 σ (146 B 2.640 % against
      2.693 %; 425 B 6.395 % against 6.422 %): the opposite sign to seeds 1–3.
    * **Pooled over all 23 seeds,** the 173 B frame loses 2.968 % against 3.025 % (−1.6 σ).
    * ns-3's PHY follows its own model within sampling, with no deviation of fixed sign.
  * One frame in the 20 seeds × 2 lengths ended 63 µs after the receiving application stopped
    (101.0000627 s against 101 s). It is excluded as an end-of-run artefact, not a loss.

## Predictions (ε = 5 %; §8.3 of the prompt)

**Step 1–2.** PER(ℓ) at −77.17 dBm comes from ns-3's TableBasedErrorRateModel, called by
`ns3/authbc-per.cc` with the inputs the PHY gives it. Those are:
* the SNR: P / (F·k·290 K·20 MHz) = 16.80 dB;
* a header chunk at 6 Mb/s;
* one payload chunk of N_DBPS·N_sym bits.

The model switches from its 32 B table to its 1458 B table at 400 B. The budget is
ε_c(b) = 1 − (1 − ε)/(1 − PER).

**Step 3.** The capacity is the root of p_c(ν) = ε_c(b), with ν = (N − 1)·Λ/b, by
`analysis/c5_d1.py` → `results/raw/c5_d1_predictions.csv`. The two-constant law is not used: every
frame (52–100 µs) is shorter than 2τ0 = 196 µs.

| b | frame | frames/s | T_f | PER(ℓ) | ε_c(b) | capacity (root) |
|---|---|---|---|---|---|---|
| 1 | 146 B | 200 | 52 µs | 2.693 % | +2.371 % | 10.96 |
| 2 | 155 B | 100 | 56 µs | 3.025 % | +2.037 % | 18.59 |
| 4 | 173 B | 50 | 56 µs | 3.025 % | +2.037 % | 36.17 |
| 8 | 209 B | 25 | 64 µs | 3.684 % | +1.366 % | **51.70** |
| 16 | 281 B | 12.5 | 76 µs | 4.665 % | +0.351 % | 32.40 |
| 32 | 425 B | 6.25 | 100 µs | 6.422 % | −1.520 % | none: alone it loses more than 5 % |

* **The predicted best batch in the sweep: b = 8, at 51.70 stations.**
* **R5 holds in the model:** capacity rises to b = 8, then falls to b = 16, and is zero at 32.
* b = 2 and b = 4 have the same airtime and loss: both are 9 OFDM symbols at 48 Mb/s.

**Every integer b.** The OFDM staircase makes the curve jagged:

| b | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|
| capacity | 58.04 | 51.10 | 56.11 | 61.12 | 47.43 | 51.00 | 54.57 | 32.40 |

The integer optimum is b = 12 (61.12). It is not in the sweep, and the sweep's best is b = 8.

**The cross-check (G19), with the prompt's inputs, none fitted:**
* the secant airtime between b = 1 and b = 32: Φ_T = 50.45 µs, Ψ_T = 1.548 µs per record;
* τ̂ = 96.55 µs at ε = 5 %, so β = (Φ_T + τ̂)/Ψ_T = 94.94;
* s = PER(155 B) − PER(146 B) = 0.003315 per record. PER₀ = 0.02362, so Β₀ = 0.4920;
* e₁ = (1 − ε)·s·dΒ/dε = 0.01277.

**b_opt = β[√(1 + Β₀/(e₁β)) − 1] = 17.63.**

**How far (G19) is from the numerical optimum, stated before any run:**
* it lies 5.6 records (+47 %) above the integer optimum (12);
* the nearest sweep step to it is b = 16, one step above the sweep's best (8);
* the reasons, from the derivation: it straightens the airtime staircase into a secant, holds τ̂
  at ε, and takes the slope s from the first record only. Between b = 1 and 2 that slope is
  small; it is larger further out (209 → 281 B: 0.00123 per record).

**Step 4. What counts as failure** (the prompt's §8.3.4, not widened after the runs):
* the measured best batch in the sweep differs from **b = 8** by more than one sweep step, that
  is, it is not 4, 8 or 16;
* **or** the capacity at the measured best batch differs from that batch's prediction by more
  than **5 %**.

**Reported, not scored:**
* each b's error;
* whether b = 32 delivers less than 95 % already at N = 2;
* (G19)'s distance from the measured best batch.

## Expectations `[agent]`

* **The best batch b = 8.** b = 4 and b = 16 are predicted 30 % and 37 % lower.
* **Capacity at b = 8 within ±5 %,** ns-3 probably above the root, as at 6 Mb/s. There the root
  lies −2.43 … −4.85 % from ns-3 at the 18 stored crossings with the designated source
  (`results/raw/unified_model_vs_ns3.csv`). Uncertain: the frames are shorter than 2τ0 here, and
  no stored cell is at 48 Mb/s.
* **At b = 1 (11 stations) ns-3 above the prediction by more,** near the author's Poisson limit
  (7–9 % at 8–14 stations). Not part of the failure rule.
* **b = 16 the most fragile.** Its budget is 0.35 %, so a 0.1-point error in PER moves its capacity
  by about a quarter.

## Disclosure

* **Known before this registration:**
  * the probes (`results/raw/c5_noise_probe*.csv`, F135);
  * the power pilots above;
  * the stored campaign;
  * U-C2 and U-D.
* **No D1 capacity run has been made.**
