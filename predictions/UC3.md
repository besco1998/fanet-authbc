# U-C3 — a key record once in r frames: capacity at 95 % of records verified (802.11a, 6 Mb/s)

*Registered 2026-11-18, before any U-C3 run; the time is the commit's. Task of 2026-11-17, work
package C, item C3. The rule is in `docs/revision/2026-11-17_unified_model_spec.md` §4 ("Design
rules to test"), and in `src/authbc/models/unified_capacity.py` (`eps_keyrecord`). Mohamed
(2026-11-18): go on with C3–C5 after U-D.*

## What is run

* **The cells.** Cell D's design frame: b = 4 records, 50 records/s, so 12.5 frames/s.
  * The key record rides in one frame of every r. That frame is 173 B, and the other r − 1 are
    158 B. All carry 4 records.
  * Cell K2 has r = 2 (`--sizePattern=173,158`); cell K4 has r = 4 (`--sizePattern=173,158,158,158`).
* **What a receiver verifies** (`src/authbc/sim/verified.py`, `verified_key_chain`).
  * A source's frames form groups of r, and the first frame of each group carries the key.
  * Frame j of a group verifies at a receiver only if frames 1 … j of that group all arrived
    there. That is the dependency the rule's own formula encodes:
    (1 − p)(1 − (1 − p)^r)/(r·p) = (1/r)·Σ_j (1 − p)^j.
* **The measured quantity.** The share of (receiver, record) pairs verified: verified frames over
  frames sent × (N − 1). Every frame carries 4 records, so records and frames count alike.
  * The driver computes it per run from the full reception trace (`--traceAllRx`), then deletes
    the trace (`ns3/run_unified.py`, `verified_frac`).
* **Method**, as in U-C2:
  * a pilot of 5 seeds on seven node counts at ±5 % steps around the law;
  * then 30 seeds on seven node counts: centred on the rounded pilot crossing, in steps of 2 % of
    it;
  * 20 simulated seconds, the designated source (a jitter of one period);
  * the crossing of the mean verified share at 0.95, by straight-line interpolation, with its
    bootstrap interval over seeds.

**Checked before this registration** (`ns3/check_twin_options.py` →
`results/raw/twin_options_check.csv`, all passed):
* `--sizePattern` alternates the airtime frame by frame (304 / 284 µs);
* with r = 1 the verified share equals the delivered fraction on a real run of cell D (N = 40).

## Predictions (ε = 5 %, 802.11a: σ = 9 µs, DIFS = 34 µs, W = 16, δ = 4 µs)

| cell | r | ε_r (per frame) | mean T_f | 2τ0 | law (G9) | root of (G5) |
|---|---|---|---|---|---|---|
| (D) | 1 | 0.05 | 304 µs | 196.1 µs | 122.85 | 120.64 |
| K2 | 2 | 0.03371 | 294 µs | 230.6 µs | **105.67** | **102.68** |
| K4 | 4 | 0.02041 | 289 µs | 284.1 µs | **83.72** | **80.05** |

* The rule (spec): N_max(ε_r), with the mean airtime of the key and dependent frames.
* The author's values: about 105.7 and 83.7, against 122.9 at r = 1. They agree.
* T_f ≥ 2τ0 in both cells, so the law is inside its stated range.

**Tolerance (the task's §9), not widened after the runs:** each crossing holds if the law, and
separately the root, is within **±5 %** of ns-3's.

**Reported, not scored:**
* the ratio N(r)/N(1) against the model's, with ns-3's N(1) = 124.55 (cell D, stored);
* at each node count, the measured verified share against the rule's formula applied to the
  measured per-frame delivered fraction. This tests the frame-to-record step on its own, without
  the capacity law.

## Expectations `[agent]`

* **Both laws within ±5 %, below ns-3 by 1–4 %.**
  * At cell D the law is 1.4 % below ns-3 (122.85 against 124.55).
  * At 6 Mb/s the 40 stored crossings put the law −4.55 … −0.01 % from ns-3.
* **The roots lower, 3–6 % below ns-3; the K4 root is the likeliest miss.** At cell D the root is
  3.1 % below ns-3, and at K4 the root is 4.4 % below the law.
* **The formula's frame-to-record step close,** if losses of a source's frames at one receiver
  are nearly independent.

## Disclosure

* **Known before this registration:**
  * the stored cell D crossing (124.55);
  * U-C2 and the 74 scored stored crossings;
  * the two N = 3 option checks;
  * the r = 1 control at cell D, N = 40, seed 1 (delivered 0.994164).
* **No U-C3 run has been made.**

---

## Outcome — added 2026-11-18, after the runs; nothing above this line was changed

**The runs.** As registered, through the audit twin:
* pilots of 5 seeds (`results/raw/unified_c3_pilot_r{2,4}{,_runs}.csv`): crossings 105.59 and
  79.76;
* then 30 seeds on seven node counts each: K2 at N = 100 … 112 (step 2), K4 at N = 74 … 86 (step
  2), 210 runs per cell (`results/raw/unified_c3_r{2,4}{,_runs}.csv`).

**One launch failed and was re-run.** At 07:54 one ns-3 process (K2, N = 104, seed 3) exited 127
at launch, before it ran, and the driver stopped with 53 runs on file.
* The cause is undetermined (`docs/LOGBOOK.md`, 2026-11-18, failure report).
* The driver was resumed at 07:58. It re-ran that launch in full and skipped the completed runs.
* A completed run reproduced identically, so no data was affected.
* **Also:** ns-3's libraries were relinked at 07:34 under this job, when a new program was added.
  Afterwards the twin gate held, 9 / 9 and byte-identical, and the same completed run reproduced.

**Checked before scoring.** An independent script on the raw counts reproduces both crossings to
the digit:
* every node count has seeds 1–30;
* each verified share equals verified / (frames sent × (N − 1));
* both curves fall monotonically and cross 0.95 once.

**Scored** by `analysis/unified_c34.py` → `results/raw/unified_c34_scored.csv`. Its model values
are the registered ones (`tests/test_unified_c34.py`).

**Scored: 4 of 4 held.**

| cell | r | ns-3 crossing (95 % CI) | law | error | root | error |
|---|---|---|---|---|---|---|
| K2 | 2 | **105.567** (104.364–106.492) | 105.67 | +0.10 % | 102.68 | −2.73 % |
| K4 | 4 | **81.440** (79.783–82.671) | 83.72 | +2.80 % | 80.05 | −1.71 % |

**Reported, not scored.**
* **The ratio to r = 1.** ns-3 gives 0.848 (r = 2) and 0.654 (r = 4), with N(1) = 124.55. The law
  gives 0.860 and 0.681, and the root 0.851 and 0.664.
* **The frame-to-record step on its own.** At every node count, the verified share lies within
  −0.0005 … +0.0005 of the rule's formula (1/r)·Σ(1 − p)^j applied to the measured per-frame
  delivered fraction. The dependency the formula encodes is what ns-3 shows: a source's losses at
  one receiver are close to independent.

**What it means.** The key-record rule holds in ns-3 at r = 2 and 4: both the per-frame target
ε_r and the capacity at the mean airtime. The law lies slightly above ns-3, the root slightly
below, and both within 3 %.

**Expectations:**
* "Both laws within ±5 %, below ns-3 by 1–4 %": within ±5 % held; **below ns-3 missed**, at
  +0.10 % and +2.80 %;
* "the roots 3–6 % below; the K4 root the likeliest miss": missed, at −2.73 % and −1.71 %, both
  held;
* "the frame-to-record step close": held.
