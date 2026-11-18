# U-C4S — the signed unit over n frames, its frames spread over the period (802.11a, 6 Mb/s)

*Registered 2026-11-18, before any U-C4S run; the time is the commit's. U-C4 failed: a unit's
frames handed to the MAC together lose 1.7–2.3 times the loss expression's per-frame share
(`predictions/UC4.md`). An unregistered diagnostic, with the same frames each on its own
jittered slot, lost 0.94–0.95 times the expression's share.*

*Mohamed (2026-11-18): "Record the burst result as failed, as registered. Register the spread case
as a new prediction with the same root values and test it on new seeds." This file does that. A
burst correction is registered separately, in `predictions/UC4B.md`.*

## What is run

* **The cells.** U-C4's units: cell D's 173 B signed unit (4 records), 12.5 units/s, sent as n
  frames each with its own 23 B header:
  * F2P: n = 2, frames of 98 B at 25 frames/s;
  * F3P: n = 3, frames of 73 B at 37.5 frames/s.
* **How the frames are sent.** Each frame on its own slot of the jittered periodic source: the
  designated source, a jitter of one period of the frame rate, so 40 ms at n = 2 and 26.7 ms at
  n = 3. A unit is a source's consecutive frames u·n … u·n + n − 1.
* **What verifies.** A unit verifies at a receiver only if all n of its frames arrive there.
  * Only whole units count. Per-source send counts come from the twin's `--perNode` output, so a
    unit the run ends part-way through is neither sent nor verified.
  * Code: `authbc.sim.verified.verified_units` with `sent_by_src`, tested in
    `tests/unit/sim/test_verified.py`.
* **The measured quantity:** verified units over units sent × (N − 1). Capacity is its crossing at
  0.95.
* **Also measured: the verification wait.** For every verified unit at every receiver, its last
  frame's arrival minus its first frame's (`unit_completion_ns`). Mean and 99th percentile per
  run.
* **Method,** as U-C4, but on **new seeds, 31–60**:
  * the diagnostic used seeds 1–10 at single node counts;
  * a pilot of 5 seeds (31–35) on seven node counts at ±5 % steps around the root;
  * then 30 seeds (31–60) on seven node counts by U-C2's rule;
  * 20 simulated seconds, the audit twin as rebuilt on 2026-11-18. Its gate held 9 / 9
    identical, and its option checks held.

## Predictions (unchanged from U-C4)

| cell | n | ε_n (per frame) | frames/s | T_f | root of (G5) | law (G9) |
|---|---|---|---|---|---|---|
| F2P | 2 | 0.02532 | 25 | 204 µs | **55.37** | 58.97 |
| F3P | 3 | 0.01695 | 37.5 | 172 µs | **31.70** | 35.06 |

**Tolerance, U-C4's, not widened after the runs:**
* the root holds if within **±5 %** of ns-3's crossing;
* the law (T_f < 2τ0, outside its range) holds only if it lies **above** ns-3's crossing.

**The verification wait, predicted** (Mohamed's design statement):
* spread fragments add up to (n − 1)/n of a unit period. A unit's frames sit on consecutive slots
  of 1/(n·f), each jittered by one slot, so the mean wait is (n − 1)/(n·f);
* that is **40.0 ms at n = 2 and 53.3 ms at n = 3** (a unit period is 80 ms);
* reported against this, not scored.

## Expectations `[agent]`

* **The roots within ±5 %.** The diagnostic's per-frame loss was 0.94–0.95 times the
  expression's at the U-C4 crossings. Spread, the units see what the expression assumes.
* **Uncertain at n = 3:** at about 32 stations the expression's per-frame loss is small, and a
  5 % error in it moves the capacity by more.
* **The mean wait near 40 and 53 ms,** shortened slightly by units whose last frame is lost (they
  are not verified, so not counted).

## Disclosure

* **Known before this registration:**
  * U-C4's outcome and its diagnostic (`results/raw/unified_c4_diag_spread_n{2,3}*`): at N = 41
    (n = 2) and N = 20 (n = 3), spread frames lost 1.46 % and 0.80 % against 1.53 % and 0.85 %
    computed;
  * the twin's option checks.
* **No U-C4S run has been made,** and no run on seeds 31–60 of these cells.
