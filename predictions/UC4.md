# U-C4 — a signed unit split over n frames: capacity at 95 % of units verified (802.11a, 6 Mb/s)

*Registered 2026-11-18, before any U-C4 run; the time is the commit's. Task of 2026-11-17, work
package C, item C4. The rule is in `docs/revision/2026-11-17_unified_model_spec.md` §4 ("Design
rules to test"), and in `src/authbc/models/unified_capacity.py` (`eps_fragment`). Mohamed
(2026-11-18): go on with C3–C5 after U-D.*

## What is run

* **The cells.** Cell D's 173 B signed unit (4 records, 12.5 units/s, 50 records/s), sent as n
  frames. Each frame carries its own 23 B header and 150/n B of the rest:
  * cell F2: n = 2, two frames of 98 B, 25 frames/s;
  * cell F3: n = 3, three frames of 73 B, 37.5 frames/s.
* **How the frames are sent.** "Sent as n frames" is read as **handed to the MAC together at the
  unit's instant** (`--burst=n`). Each frame then contends after its own backoff.
  * The model treats the frames as independent starts at n·f. A unit's frames never collide with
    each other, and they leave close together. That difference is part of what is tested.
* **What a receiver verifies** (`src/authbc/sim/verified.py`, `verified_units`): unit u is the
  frames numbered u·n … u·n + n − 1 of its source. It verifies only if all n arrived.
* **The measured quantity.** The share of (receiver, unit) pairs verified: verified units over
  units sent × (N − 1). The driver computes it per run from the full reception trace, then
  deletes the trace.
* **Method:** as U-C3. The pilot uses ±5 % steps around the root, since the law is outside its
  range here.

**Checked before this registration** (`ns3/check_twin_options.py` →
`results/raw/twin_options_check.csv`, all passed):
* `--burst=3` enqueues each node's frames three at one instant, 172 µs each;
* with n = 1 the verified share equals the delivered fraction on a real run of cell D (N = 40).

## Predictions (ε = 5 %, 802.11a: σ = 9 µs, DIFS = 34 µs, W = 16, δ = 4 µs)

| cell | n | ε_n (per frame) | frames/s | T_f | 2τ0 | law (G9) | root of (G5) |
|---|---|---|---|---|---|---|---|
| F2 | 2 | 0.02532 | 25 | 204 µs | 259.7 µs | 58.97 | **55.37** |
| F3 | 3 | 0.01695 | 37.5 | 172 µs | 307.2 µs | 35.06 | **31.70** |

* The rule (spec): ε_n = 1 − (1 − ε)^(1/n), at frame rate n·f.
* The author's values: about 59.0 and 35.1. They agree, for the law.
* **T_f < 2τ0 in both cells,** so the law is outside its stated range. The author says it
  overestimates there, and that the root should be used.

**Tolerance (the task's §9), not widened after the runs:**
* **the root:** holds if within **±5 %** of ns-3's crossing;
* **the law:** scored only for the author's stated limit. It holds if it lies **above** ns-3's
  crossing (it overestimates), and fails otherwise.

**Reported, not scored:**
* the law's error;
* at each node count, the measured verified share against (1 − p)^n with the measured per-frame
  delivered fraction p. This checks the unit rule on its own; a unit's frames leave together, so
  their losses need not be independent.

## Expectations `[agent]`

* **The roots within ±5 %.** The two laws are 6.5 % and 10.6 % above their roots.
* **The laws above ns-3, as the author states;** less sure at F2, where T_f is 0.79 × 2τ0.
* **The unit share above (1 − p)^n.** A unit's frames are sent close together, so they may lose
  together. That would make the all-arrive event likelier than independence gives.

## Disclosure

* **Known before this registration:**
  * the stored cell D crossing (124.55);
  * U-C2;
  * the two N = 3 option checks;
  * the n = 1 control at cell D, N = 40, seed 1.
* **No U-C4 run has been made.**

---

## Outcome — added 2026-11-18, after the runs; nothing above this line was changed

**The runs:**
* **the registered pilot** (5 seeds, ±15 % around the root: F2 at N = 46 … 64, F3 at 26 … 38;
  `results/raw/unified_c4_pilot_n{2,3}{,_runs}.csv`) **did not bracket 0.95.** ns-3 lies below it
  everywhere: F2 delivered 94.3 % of units at N = 46, and F3 92.7 % at N = 26;
* **a second pilot,** 5 seeds further down (F2 at N = 36 … 48, F3 at 16 … 22;
  `unified_c4_pilot2_n{2,3}`), put the crossings at 42.21 and 18.45. This step was not
  registered. It is disclosed here, and it changes no prediction;
* **then 30 seeds on seven node counts,** by U-C2's rule: F2 at N = 39 … 45, F3 at 15 … 21
  (`unified_c4_n{2,3}{,_runs}.csv`, 210 runs each).

**Checked before scoring.** An independent script on the raw counts reproduces both crossings to
the digit:
* every node count has seeds 1–30;
* the frames sent are whole units;
* each verified share equals verified / (units sent × (N − 1));
* both curves fall monotonically and cross 0.95 once.

**Scored** by `analysis/unified_c34.py` → `results/raw/unified_c34_scored.csv`. Its model values
are the registered ones.

**Scored: the root failed at both n; the law held only for its stated direction.**

| cell | n | ns-3 crossing (95 % CI) | root | error | held | law | error | above ns-3? |
|---|---|---|---|---|---|---|---|---|
| F2 | 2 | **40.937** (39.996–41.393) | 55.37 | +35.25 % | **no** | 58.97 | +44.04 % | yes |
| F3 | 3 | **19.584** (18.907–20.156) | 31.70 | +61.87 % | **no** | 35.06 | +79.04 % | yes |

**Reported, not scored.**

* **The unit rule on its own holds.** At every node count the verified share lies within
  +0.0006 … +0.0022 of (1 − p)^n on the measured per-frame delivered fraction. It is slightly
  above independence, as expected for frames sent together.
* **The failure is in the per-frame loss.** At the crossings ns-3 loses 1.7 times the loss
  expression's share per frame at n = 2 (2.58 % against 1.53 % at N = 41), and 2.1–2.3 times at
  n = 3 (1.80 % against 0.85 % at N = 20).

**A diagnostic, not registered and not scored** (cells F2S and F3S in `ns3/run_unified.py`;
`results/raw/unified_c4_diag_spread_n{2,3}{,_runs}.csv`, 10 seeds):
* the same frames at the same frame rate, but each sent on its own jittered slot instead of all
  n at the unit's instant;
* the per-frame loss then falls to the model's: **1.46 % against 1.53 % at n = 2, N = 41
  (0.95×), and 0.80 % against 0.85 % at n = 3, N = 20 (0.94×).**

| n, N | the model | frames spread | frames in a burst (registered) |
|---|---|---|---|
| 2, 41 | 1.53 % | 1.46 % | 2.58 % |
| 3, 20 | 0.85 % | 0.80 % | 1.80 % |

**What it means.**
* **The fragmentation rule ε_n = 1 − (1 − ε)^(1/n) is right** about how per-frame loss becomes unit
  loss.
* **What fails is the capacity at frame rate n·f, as soon as a unit's frames leave together.**
  * **The evidence:** with the frames spread out, the expression's per-frame loss holds within
    6 %; in a burst it is 1.7–2.3 times too low.
  * **The likely reason,** read from the source and not measured: ns-3 sends a unit's frames one
    after another, each after its own backoff. The station's second and third frames therefore
    always contend at the end of a busy period. None of them finds the medium idle, as the
    expression's independent starts assume.
* **The capacity is 26 % (n = 2) and 38 % (n = 3) below the registered root.** The root is
  optimistic here; in every other new case it lies below ns-3.
* **The registration's reading** of "sent as n frames" as a burst was stated before the runs.
  It is the case that fails.
* **Whether the spread case should be registered and tested as its own prediction** is Mohamed's
  decision. Nothing is adopted after the fact.

**Expectations:**
* "The roots within ±5 %": missed by far;
* "the laws above ns-3": held;
* "the unit share above (1 − p)^n": held, by up to 0.002.
