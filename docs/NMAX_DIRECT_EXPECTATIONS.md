# Direct search for the 802.11 `N_max` — prediction, written before the runs

*2026-10-06. Committed **data-free**, as its own commit, so the ordering is checkable in git history
— the discipline of `docs/M4_EXPECTATIONS.md` and `docs/DR6_EXPECTATIONS.md`.*

## Why these runs exist

Every 802.11 capacity figure at the V ≥ 0.95 threshold is **derived**, not measured. One NS-3 sweep
at **N = 50 and a 288 B frame** located the load at which delivery crosses 0.95 — U = 2.435,
interpolated between two measured points 1.1 apart in U — and the envelope then applies that single
ceiling to every configuration, at neighbourhoods from 31 to 269 nodes.

M4 (2026-08-28) tested half of that assumption: the U→V mapping is frame-size invariant (crossing
2.367 at 174 B against 2.435 at 288 B, 0.45 σ). The other half, **N-invariance, was never tested**
(`docs/OPEN_ITEMS.md` M4; `docs/NEXT_STEPS.md` item 6). An external review of the paper asked for
confidence intervals on the 802.11 `N_max` "as you do for LoRa". The LoRa figure is a direct search
in N with a bootstrap interval; the 802.11 figure is not. These runs make it one.

## What is run

`ns3/run_nmax_direct.py`: the `authbc-delay` scenario (ns-3.48, 802.11a, 6 Mb/s, one collision
domain, unsaturated broadcast), 30 seeds, 20 s, at the **actual** frame size and per-node frame rate
of each configuration, over a grid of N around the model's value. `N_max` is the largest N whose
mean delivered fraction meets 0.95 with every smaller grid N also passing, with a bootstrap
interval from `stats.threshold_crossing_ci` — the function the LoRa arm uses. The per-run
criterion (≥ 95 % of runs individually meet 0.95) is reported beside it.

Adopted operating point only (Λ = 50 rec/s, D_max = 100 ms):

| cell | configuration | frame | frames/s per node | model `N_max` (U ≤ 2.435) |
|---|---|---|---|---|
| A | first format, sign every record, one record per frame | 174 B | 50 | **31** |
| B | first format, batched design, frames decode alone | 300 B | 12.5 | **97** |
| C | lean format, sign every record, one record per frame | 146 B | 50 | **34** |
| D | lean format, batched design | 173 B | 12.5 | **142** |
| E | first format, sign every record, share the frame | 565 B | 12.5 | **49** |
| F | lean format, sign every record, share the frame | 372 B | 12.5 | **80** |

Frame sizes are those of `results/raw/design_ladder.csv` rounded to whole bytes, as the simulator
requires.

## The prediction

**In every cell the direct `N_max` lies within ±10 % of the model's value.**

No direction is predicted. M4's lesson was that a directional prediction needs a power estimate
before it is worth stating, and there is no mechanism here that argues for a sign.

**Power, stated in advance.** At the crossing the N = 50 sweep shows a per-seed standard deviation of
about 0.018, so 30 seeds give a standard error of about 0.0033 on the mean. Near the crossing the
mean falls by roughly 0.06 per unit of U, and one node is worth U/N of load, so the mean falls by
about 0.0015 per node at N ≈ 100 and 0.005 per node at N ≈ 31. The crossing is therefore located
to about **±2 nodes at N ≈ 100 and ±1 node at N ≈ 31** (one standard error). A 10 % deviation is
10 nodes at N ≈ 100, about five standard errors: this test can see it.

## What each outcome means

* **Inside ±10 % in all six cells.** The single ceiling is N-invariant to the resolution that
  matters. The paper quotes the **direct** values with their intervals, says they agree with the
  model, and the open N-invariance item closes.
* **Outside ±10 % in any cell.** The ceiling is not N-invariant. The direct values replace the
  model's in every table; the model-based envelope is relabelled an approximation with its error
  stated; and the capacity **ratios** — which were protected only because one ceiling was applied
  to both sides — must be recomputed from the direct values and may move. ⚠️ Do not average it
  away, and do not report whichever of the two readings is larger.

## Disclosure

One run had been made before this file was written, to time the simulator: N = 100, 288 B,
12.5 frames/s, seed 1, delivered fraction 0.9438. That is one seed at a point the model places
exactly on the crossing, where 10 of 30 seeds fall below 0.95 in the N = 50 sweep; it does not
distinguish the two outcomes above and did not shape the prediction, which is the model's own
value in each cell.

## What these runs cannot show

Only the adopted operating point is searched. The relaxed point (20 rec/s, 250 ms) puts the design
at 208–269 nodes, where one run costs several minutes; its figures stay model-based and are
labelled so. Nothing here tests more than one collision domain, any PHY rate but 6 Mb/s, or
hardware: contention has still never been measured on radios.

---

# Stage 1 — outcome (2026-10-06)

*Everything above this line is as committed in `6f82599`, before any run. Nothing in it has been
edited.* 1080 runs (six cells × six node counts × 30 seeds, 20 s each):
`results/raw/ns3_nmax_direct_runs.csv`, summarised in `results/raw/ns3_nmax_direct.csv`.

| cell | frame, rate | `N_max` on the grid [95 %] | interpolated crossing [95 %] | model | deviation (grid / interpolated) |
|---|---|---|---|---|---|
| A | 174 B, 50 /s | 29 [27, 31] | 31.0 [29.0, 32.8] | 31 | −6.5 % / −0.1 % |
| B | 300 B, 12.5 /s | 81 [81, 89] | 87.8 [83.8, 94.7] | 97 | −16.5 % / −9.5 % |
| C | 146 B, 50 /s | 31 [28, 34] | 32.4 [30.1, 36.5] | 34 | −8.8 % / −4.7 % |
| D | 173 B, 12.5 /s | 109 [109, 120] | 118.3 [115.0, 125.1] | 142 | **−23.2 % / −16.7 %** |
| E | 565 B, 12.5 /s | 53 [49, 53] | 54.7 [52.7, 56.2] | 49 | +8.2 % / +11.7 % |
| F | 372 B, 12.5 /s | 74 [68, 74] | 74.8 [71.9, 76.9] | 80 | −7.5 % / −6.6 % |

**The prediction fails.** Cell D is outside ±10 % by either estimator and its whole interval lies
below the band (upper end 125.1 against 0.9 × 142 = 127.8). B is outside on the grid and just
inside when interpolated; E is the other way round. One clear failure is enough: **the load
ceiling is not N-invariant**, and the second outcome of "What each outcome means" applies. The
signs are not all the same — the single ceiling overstates capacity for the short, frequent frames
of the design and *understates* it for the long frames of cell E — so this is not a constant that
can be re-tuned.

Three things about the measurement itself, recorded because each could have hidden the result:

1. **The driver reported the wrong estimate.** `summarise` printed `ThresholdCI.point`, which is
   the *median of the bootstrap replicates*, as `N_max`. The registration says `N_max` is the
   sample's own crossing with the bootstrap supplying the interval. The two differed in cell A
   (31 against 29). Fixed before any number was quoted; `stats.crossing_point` is now the
   estimate, and `tests/test_threshold_crossing_ci.py` holds a case where the two differ.
2. **The interpolated crossing is an addition.** The registered estimator is the grid one. Grid
   steps of up to 11 nodes make it coarse (D: 109, then nothing until 120), so the straight-line
   crossing between the last passing and first failing grid point is reported beside it
   (`stats.interpolated_crossing`, with its own bootstrap interval). It was added after the data
   were seen and is labelled as such wherever it is used.
3. **The power estimate was optimistic.** It promised ±2 nodes at N ≈ 100; the interval in cell D
   is ±5. The per-seed spread was as assumed (0.014–0.022); the grid step was what limited it.

The per-run criterion (95 % of runs individually ≥ 0.95) is **0 in every cell**: even at the
smallest node count searched, between two and five of 30 runs fall below 0.95. That is not a property of
the channel. See below.

## What stage 1 showed beyond its prediction — exploratory, found after the data

*Nothing in this section was predicted. It is the reading of the data that the follow-ups below
were designed to test, and it must not be quoted as a result until they have run.*

**(a) The crossing does not sit at a fixed U.** At the interpolated crossings U is 2.34 (A),
2.21 (B), 2.23 (C), **1.98 (D)**, **2.61 (E)**, 2.30 (F) — against the 2.435 the envelope applies.
U divides the offered load by the *saturation* throughput of N stations, which falls as N grows;
the loss of a lightly loaded network has no reason to follow that yardstick.

**(b) It sits close to a line in airtime.** Write g = N·Λ/b for the frames per second the whole
neighbourhood offers and T for the time one frame holds the medium (`bianchi.t_broadcast`: airtime
plus DIFS). At the six crossings 1/g is linear in T:

    0.05 = g · (a·T + c),   c = 8 µs fixed (see (c)),   a = 0.0749 (mean of six; 0.0719–0.0764)

The two published N = 50 sweeps, which were not used, give a = 0.0771 (288 B) and 0.0730 (174 B).
This is a fit to the 5 % level only — loss is convex in load, so it says nothing about other
thresholds — and it was found by looking. It is a hypothesis.

**(c) The per-seed spread has a mechanical cause.** Per-seed delivery is heavily left-skewed: in
cell A at N = 25, where the mean is 0.970, the minimum is 0.907 and five runs are below 0.95.
Two facts read from source, not assumed:

* `ns3/authbc-delay.cc` uses an OnOff source at constant rate. Each node is de-synchronised by one
  start offset and is then **strictly periodic**: the relative phase of any two nodes is frozen
  for the whole run.
* ns-3.48 raises CCA-busy only at the **end** of a 4 µs preamble-detection period
  (`WifiPhy::GetPreambleDetectionDuration`, `PhyEntity::EndPreambleDetectionPeriod`). Two nodes
  whose frames reach the MAC within 4 µs of each other while the medium is idle both transmit.

Together: a pair whose phases happen to fall within ±4 µs collides in *every* period of the run,
and each such pair removes 2/N of all deliveries. The expected number of such pairs per run is
C(N,2)·8 µs·(Λ/b) — 0.16 at N = 29 and 50 frames/s, 0.59 at N = 109 and 12.5 frames/s — so the
loss is concentrated in a few unlucky seeds. The same pairs would collide equally often *on
average* if phases moved, which is why the constant c above is taken as 2 × 4 µs. This is the
802.11 cousin of the frozen-phase artifact found on the LoRa arm (F32/F33). Real senders are not
phase-locked to the microsecond.

---

# Follow-up F1 — does freezing the phases change the mean, or only the spread?

*Written 2026-10-06 before any jittered run.* `authbc-delay` gains `--txJitterMs`: each frame is
delayed by its own U(0, J) from its place on the node's periodic grid, so the mean rate is exact
and phases no longer lock. With the option absent the scenario is untouched: the rebuilt binary
reproduces eight stored stage-1 runs exactly (tx, rx, delivered fraction and three delay
statistics, in all six cells).

**Runs.** Cell A at N = 29 and 33, cell D at N = 109 and 131 — the grid points either side of each
crossing — with J = 0.1 ms, 1 ms and one full period, 30 seeds, 20 s. 360 runs, compared with the
120 stored strictly periodic runs at the same four points.

**Predictions.**

* **Mean unchanged.** At each of the four points and each J, the 30-seed mean differs from the
  strictly periodic mean by less than 2.5 standard errors of the difference, and the difference
  averaged over all twelve comparisons is within ±0.005. *Reason:* phases are independent and
  uniform, queues are almost always empty, so the average over frozen phase configurations equals
  the average over moving ones.
* **Spread collapses.** At J = 1 ms and at J = one period the per-seed standard deviation is less
  than **half** its strictly periodic value at all four points, and no run in cell A falls below
  0.90 (five of the 60 stored runs do). At J = 0.1 ms the spread falls, but by how much is not
  predicted: 0.1 ms unlocks the 4 µs pairs and leaves structure at the scale of a frame (300 µs)
  frozen.

**What each outcome means.**

* *Both hold.* Frozen phases inflate the spread and nothing else. The stage-1 means stand. The
  remaining runs (stage 2, F2) are made with **J = 1 ms**, where 30 seeds locate a crossing several
  times more tightly, and are reported **beside** the strictly periodic values, never instead of
  them. The per-run criterion is reported for the jittered source only, and the reason is stated.
* *The mean moves.* Then the traffic model changes the capacity itself. Both readings are
  reported, neither is preferred here, and which one the paper quotes is Mohamed's decision
  (a new ⚠️ item) — the range is quoted until it is made.
* *The spread does not collapse.* Then (c) above is wrong or incomplete; it is withdrawn and the
  spread is investigated before anything else is run.

# Follow-up F2 — the airtime line against the single ceiling, on cells neither was fitted to

*Written 2026-10-06 before any of these cells was run.* Seven held-out cells: the three rungs of
the adopted point that stage 1 left out, and the baseline and the design at the relaxed point in
both formats. The two candidate rules disagree most where N or the frame rate is furthest from
the N = 50 sweep that calibrated the ceiling:

| cell | configuration | frame | frames/s | **airtime line** | single ceiling | differ by |
|---|---|---|---|---|---|---|
| G | first, one signature per frame (CBOR) | 373 B | 12.5 | **74.9** | 79 | −5 % |
| H | lean, one signature per frame, no delta | 218 B | 12.5 | **105.8** | 123 | −14 % |
| I | first, batched design as published | 288 B | 12.5 | **89.5** | 100 | −10.5 % |
| RA | relaxed: first, sign every record | 174 B | 20 | **75.1** | 88 | −15 % |
| RB | relaxed: first, batched design | 300 B | 5 | **217.9** | 208 | +5 % |
| RC | relaxed: lean, sign every record | 146 B | 20 | **81.7** | 101 | −19 % |
| RD | relaxed: lean, batched design | 173 B | 5 | **300.2** | 269 | +12 % |

Airtime line: N = 0.05 / ((Λ/b)·(a·T + c)) with a = 0.0749, c = 8 µs, exactly as fitted above —
neither constant will be re-fitted before the comparison. Each cell is run on seven node counts
spanning both candidates, 30 seeds, 20 s, with the source F1 designates (J = 1 ms if both F1
predictions hold, strictly periodic otherwise). The quantity compared is the interpolated crossing.

**Prediction.** In all seven cells the interpolated crossing is within **±6 %** of the airtime
line; and in the five cells where the candidates differ by more than 10 % (H, I, RA, RC, RD) it is
closer to the airtime line than to the single ceiling in every one.

**What each outcome means.**

* *Holds.* The V ≥ 0.95 capacity depends on the offered frame rate and the frame's airtime, not
  on N as such. The airtime line replaces the load ceiling as the paper's closed form, stated with
  its domain (one collision domain, 802.11a at 6 Mb/s, the 5 % level, 146–565 B, 5–50 frames/s,
  30–300 nodes), and the table quotes the direct values.
* *Fails.* No closed form is claimed for this threshold. The paper quotes direct values only, for
  the cells simulated, and says so.

Either way the U < 1 column is untouched: it is defined by the saturation model, which was
validated against saturated runs and is not a delivery threshold.

## Disclosure for the follow-ups

* Four single-seed runs were made to time the simulator before this section was written:
  N = 120, 173 B, 12.5 /s → 0.9326 and N = 31, 174 B, 50 /s → 0.9853 (both stage-1 cells);
  **N = 270, 173 B, 5 /s → 0.9695** and **N = 100, 146 B, 20 /s → 0.9386** (cells RD and RC). The
  last two are single seeds of held-out cells and lean the way the airtime line does. The line and
  its constants were computed from stage 1 before those runs; they were not adjusted afterwards.
* The constant c was 8.32 µs when fitted freely. It is fixed at 8 µs here because that is what the
  simulator's source says the window is; a moves from 0.0747 to 0.0749.
* Rebuilding the scenario recompiled every ns-3 library: a system header update on 2026-09-03 had
  made all objects stale. No ns-3 source changed (newest non-scratch source file: 2026-07-29).
  The old binary run against the rebuilt libraries reproduces the same eight stored runs exactly,
  so the rebuild changed no 802.11 result. The LoRa library was rebuilt too and has **not** yet
  been re-checked against its artifacts (`docs/OPEN_ITEMS.md`).
* Stage 1 said the relaxed point would stay model-based because a run "costs several minutes".
  It costs about 90 s, so RA–RD are simulated after all.
