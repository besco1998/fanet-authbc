# U-C4B — a burst correction to the loss expression, tested on new cells only

*Registered 2026-11-18, before any U-C4B run; the time is the commit's. Proposed by Mohamed after
U-C4 failed (`predictions/UC4.md`): "register a burst correction, not to be scored on the U-C4
data … test it on new cells only: n = 2 and 3 at 802.11b 1 Mb/s, and n = 2 with a 120 B unit at
802.11a 6 Mb/s." The spread case is `predictions/UC4S.md`.*

## The correction, written out (`src/authbc/models/burst_correction.py`)

A signed unit is sent as n frames handed to the MAC together.
* **The first frame** meets the channel as an independent start does, and keeps the original
  expression (G5).
* **Frames 2 … n** follow their own station's previous transmission, so they find the medium busy
  with probability 1. Their same-slot tie is K/(W + K) instead of a·K/(W + K); the other two terms
  are unchanged:

      p₁ = a·K/(W + K) + γ(2a/W + γ) + 2δν(1 + a)
      p₂ =   K/(W + K) + γ(2a/W + γ) + 2δν(1 + a)
      unit loss = 1 − (1 − p₁)(1 − p₂)^(n − 1)

* **The inputs,** as in (G4):
  * ν = (N − 1)·n·f, the start rate of the other stations' frames;
  * γ = ν·DIFS and η = ν·σ(W − 1)/2;
  * K = a(1 + γ + 2η)/(1 − γ − a), with a = ν(T_f − δ)(1 − p̄/2).
* **One choice the proposal leaves open, stated here:** a uses the mean frame loss
  p̄ = (p₁ + (n − 1)·p₂)/n. It is solved with p₁ and p₂ by fixed-point iteration, as the original
  `loss` does for one frame.
* **With n = 1 it is the original expression,** term for term
  (`tests/unit/models/test_burst_correction.py`).
* **The capacity** is the N at which the unit loss reaches ε = 5 % (bisection on ν).

## What is run

| cell | PHY | the unit | frames per unit, as a burst | units/s | T_f |
|---|---|---|---|---|---|
| BB2 | 802.11b, 1 Mb/s (W = 32, σ = 20 µs, DIFS = 50 µs) | 173 B | 2 × 98 B | 12.5 | 1 264 µs |
| BB3 | 802.11b, 1 Mb/s | 173 B | 3 × 73 B | 12.5 | 1 064 µs |
| AB120 | 802.11a, 6 Mb/s | 120 B | 72 B + 71 B (`--sizePattern=72,71`) | 12.5 | 168 µs (both) |

* **The cells' choices,** stated here:
  * the 802.11b cells take U-C4's unit and rate onto 802.11b;
  * the 120 B unit with its 23 B header per frame makes 120 + 23 = 143 B, split 72 + 71;
  * its rate is cell D's 12.5 units/s.
* **Sending:** `--burst=n`, as U-C4.
* **Verification:** a unit verifies only if all n frames arrive.
* **The verification wait** is measured as in U-C4S.
* **Method,** as U-C4:
  * a pilot of 5 seeds on seven node counts at ±5 % steps around the correction's capacity;
  * then 30 seeds on seven node counts by U-C2's rule;
  * 20 simulated seconds, the audit twin as rebuilt on 2026-11-18.

## Predictions (ε = 5 %)

| cell | the correction | p₁ / p₂ at it | the original root (U-C4's rule) |
|---|---|---|---|
| BB2 | **14.77** | 0.01704 / 0.03353 | 16.99 |
| BB3 | **8.96** | 0.00906 / 0.02088 | 11.50 |
| AB120 | **48.97** | 0.01775 / 0.03284 | 60.83 |

**Tolerance,** fixed now and not widened after the runs. The correction's capacity holds:
* at 802.11a, within **±5 %**;
* at 802.11b, by the bands U-D used for this PHY: **±5 %** where ns-3's crossing is 15 stations
  or more; **−9 % … +5 %** at 8–14 stations (the model's stated Poisson limit); not scored below
  8 stations.

**Reported, not scored:**
* the original root's error at the same cells;
* the measured per-frame loss of first and later fragments, where the reception trace allows;
* the verification wait.

## Expectations `[agent]`

* **The correction closes most of the gap, but stays optimistic.** On U-C4's own cells it gives
  44.19 and 22.91 against ns-3's 40.94 and 19.58 (+7.9 %, +17.0 %). That is disclosed here and
  not scored, as Mohamed set. **AB120 is therefore likely to fail ±5 % on the optimistic side.**
* **At 802.11b the correction may sit near ns-3's crossing,** with the PHY's Poisson offset (5–9 %
  pessimistic, U-D) working against the burst's optimism.

## Disclosure

* **Known before this registration:**
  * U-C4 and its diagnostic;
  * U-D's 802.11b results;
  * the correction's values on U-C4's cells, above.
* **No U-C4B run has been made.**
