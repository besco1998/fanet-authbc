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

---

# Follow-up F1 — outcome (2026-10-06)

360 runs, `results/raw/ns3_nmax_direct_runs.csv`. Each cell is the 30-seed mean delivered fraction
and, in brackets, its per-seed standard deviation.

| point | strictly periodic | J = 0.1 ms | J = 1 ms | J = one period |
|---|---|---|---|---|
| A, N = 29 | 0.9625 (0.0343) | 0.9662 (0.0183) | 0.9664 (0.0114) | 0.9610 (0.0016) |
| A, N = 33 | 0.9408 (0.0305) | 0.9527 (0.0229) | 0.9536 (0.0182) | 0.9480 (0.0016) |
| D, N = 109 | 0.9644 (0.0136) | 0.9620 (0.0103) | 0.9618 (0.0090) | 0.9625 (0.0015) |
| D, N = 131 | 0.9421 (0.0205) | 0.9419 (0.0117) | 0.9422 (0.0093) | 0.9436 (0.0018) |

**Mean unchanged — holds.** All twelve differences from the strictly periodic mean are under
2.5 standard errors (the largest is 1.97, at A/33 with J = 1 ms), and their average is +0.0027,
inside ±0.005. Freezing the phases does not bias the 30-seed mean.

**Spread collapses — fails as predicted, and holds where it was not.** At J = 1 ms the standard
deviation falls to 0.33, 0.60, 0.67 and 0.45 of its strictly periodic value: under half at two
points of four, not at all four. (No run in cell A falls below 0.90 at J ≥ 1 ms; that part holds.)
At J = one period it falls to 0.05–0.11 of it — a ten- to twenty-fold collapse — at every point.

So explanation (c) is **incomplete**, and the rule registered above applies: it is not to be
relied on, and the spread is investigated before anything else is run. What the four columns say:

* 0.1 ms of jitter is more than enough to break a 4 µs lock, and it removes only a quarter to a
  half of the spread. Locked pairs are real and are not most of it.
* What remains at 0.1 ms and 1 ms is removed only when every phase is redrawn every period. So it
  belongs to the **phase configuration as a whole** — which nodes share a busy period, period after
  period — at the time scale of a frame (0.3 ms) and longer, not of a preamble.
* The stage-1 verdict does not depend on any of this. Cell D crosses at 118.3 [115.0, 125.1]
  strictly periodic, 122.3 [119.6, 125.0] at J = 1 ms and 123.5 [123.0, 124.1] at J = one period:
  outside 142 ± 10 % every way it has been measured.

One reading that the data do **not** support, noted so it is not picked up later: in cell A the
J = one period mean is 0.005 below the J = 1 ms mean at both node counts, which looks like a
second effect. In cell D the sign reverses. The two node counts of a cell share seeds, and a seed
fixes the same phase draws, so the two cell-A differences are one observation, not two.

# Follow-up F1b — is the remaining spread the frozen configuration? Written before its runs

Two instruments, both added to `authbc-delay` behind options that leave the default run untouched.

**A phase sweep** (`--txSkewPpm`). Each node's period is stretched by its own factor from
U(−5000, +5000) ppm, with 0.1 ms of jitter. Every node stays strictly periodic — one frame per
period of its own, which is what makes the traffic telemetry — but every pair now drifts through
every relative phase during a run, so one run time-averages what otherwise takes many frozen
seeds. Real oscillators do this at 20–50 ppm, a hundred times more slowly; the offset is a
numerical device for visiting the configurations in 20 s, not a claim about crystals. Rates
differ by at most 0.5 %, and their sum by about 0.05 %.

**Per-node delivery** (`--perNode`), which says *which* nodes lose frames.

**Runs.** The sweep at the four F1 points, 30 seeds. Per-node output for cell A at N = 29, seeds
6 and 13 (the two worst strictly periodic runs, 0.859 and 0.866), 15 (the median) and 16 (the
best), under all five sources.

**Predictions.**

1. *The spread is the configuration.* Under the sweep the per-seed standard deviation is below
   **0.004** at all four points.
2. *All sources estimate one number.* The sweep mean is within **0.002** of the J = one period
   mean at each point. (Both are precise to about 0.0003, so this is a real test: it fails if
   strictly periodic traffic and traffic re-drawn every period deliver differently.)
3. *Frozen loss sits on a few nodes.* In strictly periodic seeds 6 and 13, at least **two nodes
   deliver under 20 %** of their frames while the median node delivers over 95 %; in seed 16 no
   node is under 90 %.
4. *Moving phases spread it out.* Under the sweep and under J = one period, in all four seeds,
   every node delivers between 0.92 and 0.995.

**What each outcome means.**

* *1 and 2 hold.* The sweep is the source for every remaining run: it is the same traffic as the
  published scenario, measured without the accident of one frozen configuration per seed. Stage-1
  values stay in the record beside it. The per-run criterion is reported for the sweep, where a
  run is no longer a single configuration.
* *1 holds, 2 fails.* Regular and re-drawn traffic differ. The sweep is still the source (it is
  the regular one), and the difference is reported as a finding about traffic models.
* *1 fails.* The spread is not explained. The remaining runs use J = one period, which F1 has
  shown to be unbiased within noise and tight, and the unexplained spread goes to
  `docs/OPEN_ITEMS.md` as an open question rather than being given a story.
* *3 or 4 fails.* The mechanism in (c) is withdrawn as an explanation of the spread, whatever
  1 and 2 say.

---

# Follow-up F1b — outcome (2026-10-06)

Sweep: 120 runs (`ns3_nmax_direct_runs.csv`). Per-node: 20 runs
(`results/raw/ns3_phase_lock_diagnostic.csv`, `ns3/run_phase_lock_diagnostic.py`). The rebuilt
scenario reproduces eight stored strictly periodic runs and six stored jittered runs exactly.

| point | J = one period | sweep (0.1 ms, ±5000 ppm) | difference of means |
|---|---|---|---|
| A, N = 29 | 0.9610 (0.0016) | 0.9618 (0.0052) | +0.0008 |
| A, N = 33 | 0.9480 (0.0016) | 0.9490 (0.0040) | +0.0010 |
| D, N = 109 | 0.9625 (0.0015) | 0.9630 (0.0029) | +0.0005 |
| D, N = 131 | 0.9436 (0.0018) | 0.9425 (0.0057) | −0.0011 |

1. **The spread is the configuration — FAILS as stated.** The sweep's per-seed standard deviation
   is 0.0052, 0.0040, 0.0029 and 0.0057: under the 0.004 predicted at one point of four. It is
   four to eight times below the strictly periodic value and still two to four times above
   J = one period. A sweep of ±5000 ppm does not visit configurations as thoroughly as redrawing
   them does, and whether a faster one would is untested.
2. **All sources estimate one number — holds.** The sweep mean is within 0.0011 of the
   J = one period mean at every point. Strictly periodic traffic whose phases move and traffic
   re-drawn every period deliver the same. (The 0.005 by which J = 1 ms sat above J = one period
   in cell A is gone under the sweep: it was one sample of thirty configurations, as suspected.)
3. **Frozen loss sits on a few nodes — holds.** Strictly periodic, seed 6: **four nodes deliver
   0 %**, 22 deliver exactly 100 %, the median node 100 %. Seed 13: two nodes at 0 %, one at 78 %,
   median 100 %. Seed 16: no node under 94 %, 25 at exactly 100 %.
4. **Moving phases spread it out — holds.** Under J = one period every node delivers 0.948–0.973
   in all four seeds; under the sweep 0.921–0.981.

**What the per-node data say that the totals could not.** A strictly periodic run is not a noisy
sample of the mean. It is close to deterministic: most nodes never lose a frame, and a few —
those whose fixed phase puts them inside the same busy period, or within 4 µs of another node —
lose a sixteenth, an eighth, or all of theirs, for the whole run. The 30-seed mean of such runs
is unbiased (F1, and prediction 2 here), but each run is one phase configuration, and the
dispersion across runs describes the lottery of configurations, not a property of the channel.

**Decision, by the rule registered above ("1 fails").** The remaining runs use
**J = one period**: unbiased against every other source tested (twelve comparisons in F1, four
here), and the tightest. The sweep is not used. That the sweep's spread stopped at 0.003–0.006
rather than collapsing further is **not explained**, and goes to `docs/OPEN_ITEMS.md` as a
question, not a story. Stage-1 values (strictly periodic) stay in the record beside the new
ones. The per-run criterion is reported for J = one period only.

# Amendment to F2 — made before any held-out cell is run with the designated source

F2 above was written for "the source F1 designates" and with constants fitted to the **strictly
periodic** stage-1 crossings. The designated source is now J = one period, and the two F1 points
that exist under both sources put the crossing about 4 % higher under it (cell A: 31.0 → 32.4;
cell D: 118.3 → 123.5), which is inside the stage-1 intervals but would eat most of F2's ±6 %
tolerance for a reason that has nothing to do with the question F2 asks.

So the calibration is moved to the same source as the test, **by a procedure fixed here**:

1. The six registered cells A–F are run with J = one period.
2. From their interpolated crossings N*ᵢ, aᵢ = (0.05 / (N*ᵢ·Λ/b) − c) / Tᵢ with c = 8 µs
   unchanged, and **a = the mean of the six**. Nothing else is fitted, and no held-out cell is
   looked at.
3. The seven held-out predictions are recomputed with that a and committed, **before** any
   held-out cell is run.

The prediction keeps its form and its tolerance: all seven within ±6 % of the airtime line, and
closer to it than to the single ceiling in the five diagnostic cells. The predictions made with
the original a = 0.0749 stay in the table above and their outcome is reported too; a result
that holds only with the re-estimated constant is reported as exactly that.

---

# The six registered cells under the designated source — outcome (2026-10-06)

750 runs with J = one period: seven node counts per cell at unit or near-unit steps round the
crossing (eight for D), 30 seeds each. `results/raw/ns3_nmax_direct.csv`, rows with
`jitter_ms` = one sending period.

| cell | `N_max` on the grid [95 %] | interpolated [95 %] | per-run `N_max` | single ceiling | deviation (grid / interpolated) | stage 1, interpolated |
|---|---|---|---|---|---|---|
| A | **32** [32, 32] | 32.32 [32.17, 32.46] | 31 | 31 | +3.2 % / +4.3 % | 31.0 |
| B | **88** [88, 89] | 88.85 [88.42, 89.26] | 86 | 97 | −9.3 % / −8.4 % | 87.8 |
| C | **35** [35, 35] | 35.26 [35.15, 35.36] | 34 | 34 | +2.9 % / +3.7 % | 32.4 |
| D | **124** [124, 125] | 124.55 [124.07, 125.02] | 120 | 142 | **−12.7 % / −12.3 %** | 118.3 |
| E | **56** [56, 56] | 56.28 [56.05, 56.45] | 54 | 49 | **+14.3 % / +14.9 %** | 54.7 |
| F | **76** [76, 77] | 76.83 [76.63, 77.07] | 73 | 80 | −5.0 % / −4.0 % | 74.8 |

**The stage-1 verdict does not depend on the source.** D and E are outside ±10 % by either
estimator, in opposite directions. The utilisation at the crossing runs from 2.09 (D) to 2.66 (E)
against the 2.435 the envelope applied.

**What the source bought.** The per-seed standard deviation is 0.0013–0.0030 (0.014–0.044
strictly periodic, at the points simulated under both), so the interval on a crossing is a fraction of a node. The per-run criterion,
which was 0 in every cell of stage 1, is now a number: 31, 86, 34, 120, 54, 73 — one to four
nodes below the criterion on the mean.

**Exploratory, found after the data — and it qualifies F1.** Every one of the six interpolated
crossings is higher than its strictly periodic value: by 4.4, 1.2, 8.8, 5.3, 2.8 and 2.8 %. The
stage-1 intervals contain five of the six new values (E is 0.13 nodes above its interval). At the
14 (cell, N) points simulated under both sources, mean delivery is higher under J = one period
by **0.0031** on average (10 of 14 positive; the largest single difference is 1.81 standard
errors).

> ⚠️ **The next paragraph is WRONG and was committed (`fad28e0`). Kept struck through; the
> correction follows it.**
>
> ~~That is not six confirmations of a bias, and it is not none. The 30 seeds are the same 30
> draws of start offsets in every cell — offsets are drawn as a fraction of the period, in node
> order — so the strictly periodic sample's error is common to all six cells and cannot average
> out across them. The data on hand cannot separate "these 30 phase configurations happen to be a
> little unlucky" from "a frozen source delivers 0.003 less".~~

**Correction, same day, before any held-out result was read.** The struck paragraph explained the
common sign by shared phase draws. I had inferred that from reading the scenario and did not
check it. Checked: under the strictly periodic source, per-seed delivery at *different* node
counts of one cell is uncorrelated (30 adjacent pairs: mean correlation +0.01, range −0.27 to
+0.44), and between two cells at the *same* node count it is almost perfectly correlated (A and C
at N = 31: 0.98). ns-3 hands out random streams in creation order, so the start offsets depend on
N and not on the cell. Of the 14 common points only A/31 and C/31 share draws.

So the 14 differences are close to independent, and their average, **+0.0031, has a standard
error of 0.0014** (2.2 standard errors; weighted by precision, +0.0019 ± 0.0012). That is weak
evidence of a real difference of about 0.002–0.003, not sampling error shared between cells —
and it is not established. If the phases are uniform and a period's losses depend only on that
period's phases, the expected difference is zero, so a real one would need a mechanism that is
not yet identified.

F1's registered criterion (every difference under 2.5 standard errors, average within ±0.005) is
met by the larger set as it was by the first; what F1 did **not** establish is that the
difference is zero. In nodes, 0.003 is one to three. More strictly periodic runs would decide it
(`docs/OPEN_ITEMS.md` G6). No reported capacity depends on the answer — they are all from the
source designated in F1b.

*Correction to the disclosure above:* the LoRaWAN library, rebuilt in the same pass as the
scenario, has since been re-checked. `run_lora_capacity.py` at N = 2, 3 and 5 (90 runs)
reproduces the stored rows of `lora_capacity.csv` in every cell.

# F2 — the recalibrated predictions. Committed before any held-out cell is run

By the amended procedure, from the six interpolated crossings above
(`analysis/nmax_airtime_line.py`; its tests reproduce the stage-1 slope and the seven original
predictions to the digit given):

    a_i:  A 0.0679   B 0.0732   C 0.0674   D 0.0713   E 0.0732   F 0.0732
    a  =  0.0710  (mean of six),   c = 8 µs unchanged

In-sample the line misses the six crossings by +3.4, −2.4, +3.8, −0.3, −2.6 and −2.5 %.
⚠️ Recorded before the test, not adjusted for: the two cells at 50 frames/s give 0.068 and the
four at 12.5 frames/s give 0.071–0.073. If the slope depends on the frame rate, the relaxed cells
— at 20 and 5 frames/s, where no calibration cell sits — are where the line will fail.

| cell | frame | frames/s | **airtime line, a = 0.0710** | ±6 % band | airtime line as first registered (a = 0.0749) | single ceiling | node counts to be run |
|---|---|---|---|---|---|---|---|
| G | 373 B | 12.5 | **78.4** | 73.7–83.1 | 74.9 | 79 | 70 73 76 79 82 85 88 |
| H | 218 B | 12.5 | **110.3** | 103.7–116.9 | 105.8 | 123 | 100 105 110 115 120 125 130 |
| I | 288 B | 12.5 | **93.5** | 87.8–99.1 | 89.5 | 100 | 84 88 92 96 100 104 108 |
| RA | 174 B | 20 | **78.1** | 73.4–82.8 | 75.1 | 88 | 70 74 78 82 86 90 94 |
| RB | 300 B | 5 | **227.6** | 213.9–241.2 | 217.9 | 208 | 195 205 215 225 235 245 255 |
| RC | 146 B | 20 | **84.9** | 79.8–90.0 | 81.7 | 101 | 76 81 86 91 96 101 106 |
| RD | 173 B | 5 | **312.4** | 293.7–331.2 | 300.2 | 269 | 255 270 285 300 315 330 345 |

**The prediction, unchanged in form.** In all seven cells the interpolated crossing lies inside
the ±6 % band of the line with a = 0.0710; and in H, I, RA, RC and RD it is closer to that line
than to the single ceiling. The outcome against the line as first registered is reported beside
it. In G the two rules now differ by under 1 %, so G can confirm neither over the other.

**What will be run.** Seven node counts per cell as listed — chosen to span both rules and the
band — 30 seeds, 20 s, J = one period: 1470 runs. A cell whose crossing falls outside its grid is
extended and the extension is reported as one. Afterwards the cells the paper tabulates get a
unit-step grid round their crossing, as A–F did; those runs locate `N_max` and are not part of
the test, which is on the seven-point grids above.
