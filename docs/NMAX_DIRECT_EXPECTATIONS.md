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

---

# F2 — outcome (2026-10-07)

1470 runs: the seven held-out cells on the seven-point grids listed above, 30 seeds, 20 s,
J = one period. Scored by `analysis/nmax_airtime_line.py`, which was committed with the
predictions (`fad28e0`) and has not changed.

| cell | frame, rate | interpolated crossing [95 %] | **line, a = 0.0710** | deviation | line as first registered | deviation | single ceiling | deviation |
|---|---|---|---|---|---|---|---|---|
| G | 373 B, 12.5 /s | 76.25 [75.71, 76.64] | 78.4 | **−2.7 %** | 74.9 | +1.7 % | 79 | −3.5 % |
| H | 218 B, 12.5 /s | 108.89 [108.40, 109.50] | 110.3 | **−1.3 %** | 105.8 | +2.9 % | 123 | −11.5 % |
| I | 288 B, 12.5 /s | 91.34 [90.90, 91.91] | 93.5 | **−2.3 %** | 89.5 | +2.0 % | 100 | −8.7 % |
| RA | 174 B, 20 /s | 78.35 [77.97, 78.69] | 78.1 | **+0.3 %** | 75.1 | +4.4 % | 88 | −11.0 % |
| RB | 300 B, 5 /s | 219.83 [218.87, 220.77] | 227.6 | **−3.4 %** | 217.9 | +0.9 % | 208 | +5.7 % |
| RC | 146 B, 20 /s | 85.52 [85.09, 86.04] | 84.9 | **+0.7 %** | 81.7 | +4.7 % | 101 | −15.3 % |
| RD | 173 B, 5 /s | 308.06 [307.13, 309.02] | 312.4 | **−1.4 %** | 300.2 | +2.6 % | 269 | +14.5 % |

**The prediction holds, in both forms.**

1. *All seven within ±6 % of the line.* The largest deviation is 3.4 % (RB), and every interval
   lies inside its band.
2. *Closer to the line than to the ceiling in H, I, RA, RC and RD.* In all five, by a factor of
   four to thirty.

It also holds with the slope **as first registered** (a = 0.0749, from the strictly periodic
crossings): all seven within 4.7 %, and closer to that line than to the ceiling in the same five
cells. So the result does not depend on the recalibration the amendment introduced. Against the
first-registered line every deviation is positive (mean +2.8 %), which is the shift between the
two traffic sources seen in the six calibration cells.

**What follows, as registered under "Holds".** The V ≥ 0.95 crossing of a configuration is set by
the frame rate it offers and the time its frames hold the medium, not by N as such:

    N_max ≈ 0.05 / ( f · (a·T + c) ),    a = 0.0710,  c = 8 µs

with f the frames per second a node sends and T = `bianchi.t_broadcast` (airtime plus DIFS). It
replaces the single load ceiling as the closed form the paper states, **with its domain**: one
collision domain, 802.11a at 6 Mb/s, the 5 % loss level, frames of 146–565 B, 5–50 frames/s,
32–308 nodes, send instants redrawn each period, in ns-3. The tables quote simulated values, not
the line. Over the thirteen cells the single ceiling misses by up to 15.3 %, in both directions.

**What the test does not show — read before leaning on the line.**

* **The residuals are not noise.** By frame rate they average +3.6 % at 50 /s (the two
  calibration cells), +0.5 % at 20 /s, −2.0 % at 12.5 /s and −2.4 % at 5 /s. The slope falls
  slowly as the frame rate rises; one constant absorbs that to within ±4 % over a tenfold range
  of rates. This is the pattern recorded before the test. It did not break the prediction, and
  it means the line should not be extrapolated beyond 5–50 frames/s.
* **One loss level.** Loss is convex in load; nothing here says the line holds at 1 % or 10 %.
* **G cannot discriminate.** There the line and the ceiling differ by under 1 %.
* **It is a fit to a simulator.** The constant c is tied to ns-3's 4 µs preamble-detection
  period; on radios it would be whatever the hardware's detection latency is.
* **`N_max` on these grids is coarse.** The grids were chosen to test the line, in steps of 3 to
  15 nodes, so the grid value under-reports by up to a step (RD: 300 on the grid, 308
  interpolated). The cells the paper tabulates get unit or two-node steps round their crossing
  next; those runs are not part of this test, and the table above is fixed as of this commit.


---

# Fine grids — the capacities the paper tabulates (2026-10-07)

810 further runs at unit or two-node steps round the crossings of G, H, I, RA, RB, RC and RD,
as A–F had. They locate `N_max`; **they are not part of the F2 test**, which stays scored on the
seven-point grids above (`analysis/nmax_airtime_line.py` restricts itself to `F2_GRIDS`, and a
test holds the seven recorded crossings). 4980 runs in all; every node count simulated is in
`experiments/nmax-direct/plan.txt`.

| cell | configuration | `N_max` [95 %] | interpolated [95 %] | per-run | single ceiling | deviation of the ceiling's figure |
|---|---|---|---|---|---|---|
| A | first, per-record signing | **32** [32, 32] | 32.32 [32.17, 32.46] | 31 | 31 | +3.2 % |
| B | first, design | **88** [88, 89] | 88.85 [88.42, 89.26] | 86 | 97 | -9.3 % |
| C | lean, per-record signing | **35** [35, 35] | 35.26 [35.15, 35.36] | 34 | 34 | +2.9 % |
| D | lean, design | **124** [124, 125] | 124.55 [124.07, 125.02] | 120 | 142 | -12.7 % |
| E | first, shared frame | **56** [56, 56] | 56.28 [56.05, 56.45] | 54 | 49 | +14.3 % |
| F | lean, shared frame | **76** [76, 77] | 76.83 [76.63, 77.07] | 73 | 80 | -5.0 % |
| G | first, one signature per frame | **76** [75, 76] | 76.26 [75.81, 76.62] | 73 | 79 | -3.8 % |
| H | lean, one signature, no delta | **108** [107, 109] | 108.91 [107.96, 109.45] | 106 | 123 | -12.2 % |
| I | first, design as first specified | **91** [90, 91] | 91.34 [90.84, 91.83] | 89 | 100 | -9.0 % |
| RA | relaxed: first, per-record signing | **78** [77, 78] | 78.35 [77.98, 78.67] | 76 | 88 | -11.4 % |
| RB | relaxed: first, design | **219** [215, 221] | 219.19 [217.76, 221.14] | 205 | 208 | +5.3 % |
| RC | relaxed: lean, per-record signing | **85** [85, 86] | 85.58 [85.28, 86.03] | 84 | 101 | -15.8 % |
| RD | relaxed: lean, design | **306** [306, 308] | 307.95 [307.13, 309.4] | 300 | 269 | +13.8 % |

`deviation` is (N_max − ceiling) / ceiling on the grid. Each `N_max` was recomputed from the raw
runs with a few lines sharing no code with the summary (first node count whose 30-run mean falls
below 0.95); all agree.

Three crossings sit on a knife edge and their intervals say so: H (mean 0.95042 at 108, 0.94996
at 109), RB (0.95005 at 219, 0.94977 at 220) and RD (0.95109 at 306, 0.94997 at 308).

---

# Follow-up F3 — the stream-signing baselines, simulated. Written before their runs (2026-10-07)

**Why.** `results/raw/stream_baselines.csv` places five classical stream-signing schemes at the
adopted point as the lean one-record frame with each scheme's authenticator. Their capacity
there is the saturation bound only, while every rung of the design ladder has a simulated
`N_max`. The review this revision answers called the baselines weak; a baseline with a modelled
capacity beside a design with a simulated one is still weak. Each is one more (frame, rate) cell.

**What is run.** Five cells, J = one period, 30 seeds, 20 s, seven node counts at unit steps:

| cell | scheme | frame | frames/s | airtime line (a = 0.0710, unchanged) | ±6 % band | single ceiling | node counts |
|---|---|---|---|---|---|---|---|
| SM | MAVLink 2 tag | 94 B | 50 | **40.6** | 38.2–43.1 | 44 | 39 40 41 42 43 44 45 |
| ST | TESLA | 106 B | 50 | **38.8** | 36.5–41.2 | 41 | 37 38 39 40 41 42 43 |
| SG | Gennaro–Rohatgi | 114 B | 50 | **38.0** | 35.7–40.3 | 39 | 36 37 38 39 40 41 42 |
| SE | EMSS | 146 B | 50.5 | **33.6** | 31.6–35.6 | 34 | 32 33 34 35 36 37 38 |
| SW | Wong–Lam tree, block of 4 | 211 B | 50 | **28.0** | 26.3–29.7 | 28 | 26 27 28 29 30 31 32 |

**Prediction.** In all five the interpolated crossing lies inside the ±6 % band of the line, with
the slope and the constant exactly as calibrated before F2 — nothing is re-fitted.

**Recorded expectation, weaker than a prediction.** These cells are at 50 frames/s, where the
two calibration cells sat 3.4 and 3.8 % *above* the line. If that residual is a property of the
frame rate, all five will be above it too, by about that much: 42, 40, 39.5, 35 and 29.

**What this cannot show.** (i) Here the line and the single ceiling differ by 1–8 %, so these
cells do not discriminate between them; F2 did that. (ii) ⚠️ **A simulated delivery is an upper
bound on what three of these schemes verify.** A TESLA packet waits for a later key, an EMSS
packet for a later signature packet, and a Gennaro–Rohatgi packet needs every packet before it;
delivery of a frame is not verification of its record. Only the MAVLink 2 and Wong–Lam rows, and
the two rows already simulated (per-record signature, cell C; the design, cell D), are frames
that verify alone. (iii) EMSS's signature packets are simulated as data-sized frames at
50.5 frames/s. (iv) The schemes are still not implemented: this is the channel cost of their
frames, nothing more.

A crossing that falls outside its grid is extended and the extension is reported as one.

## F3 — outcome (2026-10-07, 1,050 runs, 19:22)

**The prediction held in all five cells.** Slope and constant exactly as calibrated before F2.

| cell | scheme | frame | line | band | simulated crossing [95 %] | `N_max` [95 %] | vs line | inside the band | recorded expectation |
|---|---|---|---|---|---|---|---|---|---|
| SM | MAVLink 2 tag | 94 B | 40.6 | 38.2–43.1 | 42.15 [41.96, 42.29] | **42** [41, 42] | +3.8 % | yes | 42 |
| ST | TESLA | 106 B | 38.8 | 36.5–41.2 | 40.44 [40.20, 40.65] | **40** [40, 40] | +4.2 % | yes | 40 |
| SG | Gennaro–Rohatgi | 114 B | 38.0 | 35.7–40.3 | 39.44 [39.27, 39.57] | **39** [39, 39] | +3.8 % | yes | 39.5 |
| SE | EMSS | 146 B, 50.5 /s | 33.6 | 31.6–35.6 | 34.81 [34.69, 34.96] | **34** [34, 34] | +3.5 % | yes | 35 |
| SW | Wong–Lam tree, block of 4 | 211 B | 28.0 | 26.3–29.7 | 29.00 [28.86, 29.14] | **28** [28, 29] | +3.5 % | yes | 29 |

(`python analysis/nmax_airtime_line.py --stream`; held by `tests/test_nmax_airtime_line.py`.)
Every interval lies inside its band as well as every point. No grid had to be extended.

**The recorded expectation was met too.** All five cross 3.5–4.2 % *above* the line, where the
two calibration cells at 50 frames/s had sat 3.4 and 3.8 % above it. The line's error at this
frame rate is therefore a small, repeatable bias and not noise — the residual ordered by frame
rate that F54 recorded, seen again on frames it had not seen. It is one more reason the line is
never quoted as a capacity.

**Checks made before recording it** (Law 6). (i) `N_max` of all five recomputed from the raw
runs with code that shares nothing with the summary — first node count whose thirty-run mean
falls below 0.95: 42, 40, 39, 34, 28, the same. (ii) An internal cross-check that needs no
model: the EMSS frame is the per-record-signature frame (146 B) sent 1 % more often, and its
crossing is 34.81 where cell C's is 35.26 — 1.3 % lower. (iii) Capacity falls monotonically with
frame length at one frame per record: 42 > 40 > 39 > 35 > 28.

**What it does not show** is unchanged from the registration: these cells do not separate the
line from the single ceiling; a delivered frame is not a verified record for TESLA, EMSS and
Gennaro–Rohatgi; nothing is implemented.

⚠️ **One defect was found while scoring, and it would have passed unnoticed if the scoring had
not been written to refuse a missing cell.** The first scored table had four rows. The summary
stores the send jitter to six significant figures; three readers looked it up by its exact value.
Every period so far had been 20, 50, 80 or 200 ms. EMSS's is 1000/50.5 = 19.80198… ms, stored as
19.802, and its cell was dropped by the scorer, by the artifact that fills the stream table, and
by the plan writer (which would also have made a resumed campaign run it all again). Fixed at the
root (`provenance.as_written`), with regression tests; F56.

---

# Follow-up F4 — do the two traffic sources deliver the same on average? Fresh seeds. Written before the runs (2026-10-08)

**The open question** (`OPEN_ITEMS` G6b). Fourteen (configuration, N) points were simulated with
strictly periodic senders and with a send time redrawn in every period. F1 registered that the
two means agree within 0.005, and they do. But over seeds 1–30 the redrawn source delivers
**D = +0.00312** more on average, with a standard error of **0.00142** propagated from the
spread between runs: **z = +2.20**. Ten of the fourteen differences are positive. That is weak
evidence of a real difference and no more, and it was noticed in the data, not predicted.

**Why it should be zero.** A period's losses depend on that period's phases and backoffs only: a
station's post-transmission backoff is over long before its next frame. With phases uniform in
both sources, the expected loss per period is the same whether the phases are redrawn or kept.
A real difference would need a mechanism that carries state across periods, and none is known.

**What is run.** The same fourteen points, on seeds that have never been used, into their own
file (`results/raw/ns3_source_fresh_runs.csv`) so that every reported point keeps exactly thirty
runs numbered from 1:

| source | seeds | runs |
|---|---|---|
| strictly periodic (jitter 0) | **31–90** (sixty) | 14 × 60 = 840 |
| redrawn every period | **31–60** (thirty) | 14 × 30 = 420 |

Sixty for the periodic source because it carries nearly all the noise: its spread between runs
is 0.014–0.044 where the redrawn source's is 0.002–0.003. Plans:
`experiments/nmax-direct/plan_source_fresh_periodic.txt`, `…_redrawn.txt`.

**The statistic**, fixed now (`analysis/source_difference.py`, held by
`tests/test_source_difference.py`): d_i = mean(redrawn) − mean(periodic) at point i;
D = mean of the d_i; SE = √(Σ_i (s²_redrawn,i / n + s²_periodic,i / n)) / 14;
z = D / SE. Expected SE of the fresh sample: about 0.0010.

**Prediction.** **The difference does not replicate: z_fresh < 2**, one-sided, the direction
(redrawn higher) being fixed by the first sample. Expected D_fresh: 0 ± 0.001.

**How it will be read**, decided now:

| fresh sample | reading |
|---|---|
| z_fresh < 1 | the first result was sampling; item closed. The combined estimate is reported with its error |
| 1 ≤ z_fresh < 2 | not replicated, not excluded; the combined estimate is reported and the item stays open as it is |
| z_fresh ≥ 2 | **the prediction failed**: the difference is real at about +0.003, the argument above is wrong somewhere, and the mechanism is the next thing to find |

The combined estimate is the inverse-variance weighted mean of the two samples. It is reported
in every case and decides nothing: the first sample is the one in which the effect was noticed.

**A second claim this makes it possible to check.** All six crossings are 1–9 % *lower* under the
strictly periodic source. If the means are equal that cannot come from the means. The
registered `N_max` is the largest N whose mean passes *with every smaller N also passing*; on a
noisier curve an early chance failure is likelier, so the rule reads low. **Expectation, to be
checked on the runs already on file and not on these:** resampling the periodic source's runs
around the redrawn source's means reproduces a downward shift of that size with no difference
in means at all.

**What this cannot show.** Nothing about a reported number: every capacity uses the redrawn
source. It bears only on how the strictly periodic figures of earlier work should be read.

---

# Follow-up F5 — a derivation of the crossing, and three conditions it has never seen. Written before their runs (2026-10-08)

**Why.** The airtime line of F2 is a fit: one constant, a = 0.0710, chosen to pass through six
crossings at one loss level. F3 showed its error at 50 frames per second is a repeatable bias.
`OPEN_ITEMS` G18 asked for a derivation, and Mohamed chose (2026-10-08) to do it now.

**What was derived** (docs/02 §6g). A frame is lost in this scenario in exactly two ways:

1. **A tie.** A frame that arrives while the medium is held (another frame, or the DIFS after
   it) draws a counter from {0 … W−1}. Two stations whose counters reach zero in the same slot
   send together. Any two stations that are waiting at the same time tie with probability 1/W.
2. **The detection window.** A station cannot sense a transmission during its first 4 µs, so one
   that decides to send inside that window sends as well.

Counting the first with a queue (a share ρ of frames defers; each meets ρ/(1−ρ) others) and the
second directly gives, with ρ = (N−1)·f·T and nothing fitted,

    loss ≈ ρ · [1 − (1 − 1/W)^(ρ/(1−ρ))] + (N−1)·f·8 µs

which puts all eighteen simulated crossings within 5.5 % (mean 2.3 %), and says what the fitted
slope *is*: a = ρ/(W·(1−ρ)), which equals 0.071 at ρ = 0.53 — the occupancy at which loss reaches
5 %. It was near 1/W by that coincidence and no other.

> *Clarification added 2026-10-08, before any run of F5.* 0.53 is the **average** occupancy at
> the eighteen crossings; they span 0.48–0.60, over which ρ/(W(1−ρ)) runs from 0.058 to 0.092.
> The fitted slope is that quantity averaged, not matched cell by cell — which is the reason
> one constant fitted only to a few percent. Nothing registered below depends on this
> sentence.

**The model that is tested** is the exact version of the same two mechanisms:
`src/authbc/sim/dcf_unsaturated.py`, an event simulator of the access rule alone — arrival
times, the carrier-sense rule, counters. No PHY, no channel, no packets, no line of ns-3, and no
fitted constant: the slot, DIFS, W = 16 and the 4 µs are the standard's and the simulator's.
Against the eighteen configurations already simulated (`results/raw/dcf_model_vs_ns3.csv`):
**every crossing within −1.2 … +0.6 % (mean 0.5 %), every one of the 153 delivered fractions within 0.0023.**

⚠️ That agreement is **not a prediction**: the model was written, and one omission in it found
and fixed (half of the detection window), while looking at one of those eighteen cells. What
follows is.

**What is run.** Six crossings in conditions no run has been made at, cells C (146 B, 50
frames/s) and D (173 B, 12.5 frames/s), 30 seeds, 20 s, send time redrawn each period; into their
own files, so the reported sample is untouched:

| case | window | delivered level | **model crossing** | band (±3 %) | node counts | file |
|---|---|---|---|---|---|---|
| C, window doubled | 32 | 0.95 | **39.09** | 37.92–40.27 | 36 37 38 39 40 41 42 | `ns3_rule_cw31_runs.csv` |
| D, window doubled | 32 | 0.95 | **139.03** | 134.86–143.20 | 131 135 139 143 147 | 〃 |
| C, 10 % loss | 16 | 0.90 | **46.77** | 45.36–48.17 | 44 45 46 47 48 49 50 | `ns3_rule_levels_runs.csv` |
| D, 10 % loss | 16 | 0.90 | **165.30** | 160.34–170.26 | 157 161 165 169 173 | 〃 |
| C, 2 % loss | 16 | 0.98 | **22.49** | 21.82–23.17 | 20 21 22 23 24 25 26 | 〃 |
| D, 2 % loss | 16 | 0.98 | **79.65** | 77.26–82.04 | 74 77 80 83 86 | 〃 |

(`results/raw/dcf_model_predictions.csv`, written by `analysis/dcf_model_check.py --predict`
and committed with this text.) The doubled window needs a scenario option, `--cwMin`, which is
absent by default; the binary is rebuilt only after the F4 campaign has finished, and stored
runs must reproduce bit for bit with it before any new run is made.

**Prediction.** **All six ns-3 crossings fall inside ±3 % of the model's.** The model's worst
error on the eighteen it was built beside is 1.2 %; 3 % leaves room for conditions further from
them.

**Why these three conditions.** They are where the candidate explanations part:

| | fitted line, slope scaled by 1/W | closed form above | **event model** |
|---|---|---|---|
| C, window doubled | 53.4 | 42.6 | **39.1** |
| C, 10 % loss | 67.9 (the line has no other level) | 45.0 | **46.8** |
| C, 2 % loss | 13.6 | 23.6 | **22.5** |

If doubling the window nearly doubled the capacity, ties would be the whole story and the line's
slope a pure 1/W. The model says the capacity rises by an eighth: a longer countdown keeps
stations waiting longer, so more of them wait together, and the detection window is untouched.

**How it will be read.** Six inside: the capacities of this scenario are explained by two named
mechanisms and constants of the standard, and the paper may say so. Any outside: reported as a
failure, with the size and sign of the miss, and the model is not adjusted to fit — a second
model would need its own registration. A crossing outside its grid is extended and the
extension reported.

**What this cannot show.** That ns-3's access rule is a radio's. The model and ns-3 implement
the same standard; their agreement says the capacities follow from that rule and the 4 µs, not
that either describes hardware. That is `OPEN_ITEMS` G4.

## F4 — outcome (2026-10-08, 1,260 runs)

**The prediction held: the difference does not replicate.**

| sample | points | D = redrawn − periodic | SE | z | differences > 0 |
|---|---|---|---|---|---|
| seeds 1–30 (where it was noticed) | 14 | +0.00312 | 0.00142 | +2.20 | 10 of 14 |
| **fresh: periodic 31–90, redrawn 31–60** | 14 | **+0.00043** | 0.00086 | **+0.50** | 5 of 14 |
| combined, inverse-variance | — | +0.00116 | 0.00074 | +1.57 | — |

(`python analysis/source_difference.py`; `results/raw/ns3_source_fresh_runs.csv`. Recounted from
the runs with code that shares nothing with that script: the same D, SE and z, and every point
holds exactly the registered seeds.)

z_fresh < 1, so by the reading fixed beforehand **the first result was sampling and the item is
closed** (`OPEN_ITEMS` G6b). The expected D_fresh was 0 ± 0.001; it is 0.0004. The combined
estimate is given because the registration said it would be; it decides nothing, being
dominated by the sample in which the effect was first seen.

The spread between runs, on the fresh seeds: 0.011–0.033 for strictly periodic senders against
0.0014–0.0026 for the redrawn source — six to twenty-three times wider at the same point.

### The second claim — ⚠️ refuted

The registration added an expectation: that the lower crossings read under the strictly periodic
source (all six, by 1–9 %) are what the first-failure rule gives on a noisier curve, with no
difference in means. **Checked on the runs already on file, it is false as stated.** Taking the
common mean from the access-rule model (which matches the redrawn source within 0.002), adding
the periodic source's own run-to-run residuals and reading the crossing as the summary does,
2,000 times per cell:

| cell | crossing under equal means, median [95 %] | the model's own crossing | observed, periodic, seeds 1–30 | P(≤ observed) |
|---|---|---|---|---|
| A | 32.10 [28.72, 34.11] | 32.24 | 30.97 | 0.26 |
| B | 88.88 [84.81, 92.18] | 88.72 | 87.76 | 0.34 |
| C | 34.99 [30.58, 37.22] | 35.09 | 32.41 | 0.08 |
| D | 123.96 [117.05, 130.82] | 123.80 | 118.30 | 0.08 |
| E | 55.33 [52.44, 56.82] | 55.62 | 54.74 | 0.27 |
| F | 76.47 [72.63, 79.45] | 76.42 | 74.75 | 0.19 |

The rule's median sits on the true crossing: **it does not read low.** What noise does is widen
it — a capacity read from thirty strictly periodic runs is uncertain by about ±5 to ±12 % —
and each observed crossing lies inside its range. All six being on the low side is not six
pieces of evidence: they come from the same thirty seeds whose means were low, the same
fluctuation as the +0.0031. The fresh seeds, where their coarser points bracket the threshold,
put the periodic crossing above the redrawn one in two cells and below it in two
(A +1.5 %, E +0.1 %, D −2.3 %, C −4.9 %).

**So the statement "capacities read from the strictly periodic source are 1–9 % lower" is
withdrawn.** It described one sample. What is true: the two sources have the same mean
delivery, and thirty periodic runs locate a capacity about ten times less precisely.

**Lesson.** The same one as on 2026-10-06, taken again: *an explanation is a claim.* I wrote a
mechanism ("an early chance failure is likelier, so the rule reads low") into a registration
because it sounded right. This time it was written as something to be checked, it was checked,
and it was wrong — which is the difference a registration makes.
