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
