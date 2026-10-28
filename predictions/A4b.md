# A4b — a second adaptive controller, after A4's failed as built (decision H9)

*Registered 2026-10-21 before any run of the two policies below at a registered setting. Plan:
`docs/AUTHBC Revision Plan.md`, A4; decision H9 (Mohamed, 2026-10-21: "register a second
controller and run it"). Outcome appended below a line at the end.*

## Why there is an A4b

A4's controller (smallest b whose predicted delivery is ≥ 0.95 + 0.01) realised V ≈ 0.955 on a
growing swarm; one-second windows scatter by about ±0.01, so a quarter fell below 0.95 and it
failed at 76 nodes (fixed b = 4: 127; an oracle that knows N: 125). `predictions/A4.md`
explains it as two things: **too little margin** for the scatter, and **lag** (one period
measured, two of hysteresis, while the ramp adds 1.5 nodes a second). Changing both at once would
not say which mattered, so two policies are registered, each changing one:

* **`adaptive-m20`** — A4's controller, unchanged, with margin 0.02. **The rule, stated so it
  is not a value chosen from the result:** twice the ±0.01 scatter of one-second windows A4
  measured (`predictions/A4.md`, outcome). Same binary path as A4's `adaptive`.
* **`predict`** — A4's controller with margin 0.01, deciding on the occupancy carried over its
  own lag while it grows: ρ_ahead = ρ + 3·max(0, ρ − ρ_prev), ρ normalised to b = 1 as in A4,
  3 = one period measured + two of hysteresis (`ns3/authbc-adaptive.cc`, `kLagPeriods`). Only
  growth is anticipated, never decline. The idea of acting on the predicted next state is FMAC's
  (Huang et al., IEEE IoT J 2021, held locally): it predicts a flock's density from the
  neighbours' announced motion; here the prediction is from the busy time alone.

Everything else is A4's: scenarios (ramp, merge, mobile), seeds 1–10, metrics and scoring script
(`analysis/adaptive_batching.py`, which reads a set's runs file). Baselines (fixed b = 1, fixed
b = 4, oracle, A4's adaptive) are A4's runs, not repeated. Runs:
`ns3/run_adaptive.py --set a4b` → `results/raw/ns3_adaptive_b_runs.csv`, `…_b_ts/`. 60 runs.

**The binary.** Adding `predict` changed no other policy: three registered A4 runs re-run on the
rebuilt binary (mobile/adaptive/1, ramp/oracle/2, mobile/fixed4/3) are identical to their
committed summaries and per-second series, every value and every line — checked before this
commit.

## Where the controllers should step up (computed before this commit)

From the controller's own model (`PredictedDelivery`, `Load`), the largest number of nodes each
batch serves at each target:

| target | b = 1 | b = 2 | b = 3 | b = 4 |
|---|---|---|---|---|
| 0.95 (the capacity) | 35 | 68 | 98 | 126 |
| 0.96 (A4's `adaptive`, `predict`) | 32 | 62 | 89 | 115 |
| 0.97 (`adaptive-m20`) | 28 | 54 | 78 | 101 |

## Predictions — mine `[agent]`

A4's six scoring criteria are applied to each new policy as written in `predictions/A4.md`, and:

* **A4b-1 (`adaptive-m20`, ramp).** `failure_n` ≥ 115, i.e. within 10 % of fixed b = 4's 127.2
  — above 101 nodes it sits at b = 4 like the fixed policy, and below it its predicted V stays
  ≥ 0.97, which the A4 lag (≈ 0.005) does not take below 0.95. Windows ≤ 115 nodes at V ≥ 0.95:
  ≥ 0.95. Mean peak age on the ramp between A4's adaptive and fixed b = 4: 100–115 ms. Below
  30 nodes, still within 10 % of fixed b = 1's age (it steps to b = 2 at ≈ 28 nodes plus its lag).
* **A4b-2 (`predict`, ramp).** `failure_n` ≥ 105; windows ≤ 115 at V ≥ 0.95 between 0.85 and
  0.95 (better than A4's 0.75, worse than `adaptive-m20`: at steady load its margin is still
  0.01); mean peak age 95–110 ms.
* **A4b-3 (merge).** `adaptive-m20` merged-minute share of windows ≥ 0.95: ≥ 0.95. `predict`
  merged minute: 0.93–0.96, like A4's adaptive — a step cannot be extrapolated from the
  occupancy before it, so the first seconds after the merge lag as before.
* **A4b-4 (cost).** Both change b at most 6 times per node per minute; `predict` changes it no
  more than twice as often as A4's adaptive on the ramp.

## Disclosure

Before this commit, no run of `predict` or of `adaptive` at margin 0.02 exists at any setting.
The thresholds above were computed from the model, not from runs. The literature that shaped
`predict` (FMAC) was read on 2026-10-21, after A4's outcome.

## What this cannot show

As A4: one-hop neighbourhoods, homogeneous scaling, no telemetry content, one PHY. A rule fixed
from A4's measured scatter is checked here on the same scenarios; a different swarm could need a
different margin.

---

## Outcome (2026-10-21; 60 ns-3 runs, 10 seeds per cell)

`results/raw/adaptive_batching_b.csv` (`analysis/adaptive_batching.py --set a4b`); runs
`results/raw/ns3_adaptive_b_runs.csv`, series `…_b_ts/`. Baselines are A4's runs.

| ramp (20 → 140 nodes) | A4 adaptive | **adaptive-m20** | **predict** | oracle | fixed b = 4 |
|---|---|---|---|---|---|
| `failure_n` [seed range] | 75.9 [39, 108] | **116.2** [111, 123] | **107.9** [73, 118] | 124.6 | 127.2 |
| windows ≤ 115 nodes at V ≥ 0.95 | 0.75 | **0.93** [0.87, 0.97] | **0.85** [0.79, 0.92] | 0.95 | 0.99 |
| mean b reaches 1.5 / 2.5 / 3.5 at N | 41 / 62 / 92 | 34 / 55 / 81 | 35 / 56 / 89 | 34 / 64 / 91 | — |
| mean peak age (ms) | 98.2 | **103.1** | **98.9** | 107.3 | 124.3 |
| bytes per record | 59.5 | 56.0 | 58.7 | 54.0 | 43.25 |

| merge (60 + 60 → 120) | A4 adaptive | adaptive-m20 | predict | oracle | fixed b = 4 |
|---|---|---|---|---|---|
| windows ≥ 0.95, all / merged minute | 0.977 / 0.948 | **0.988 / 0.980** | 0.977 / 0.948 | 0.997 / 0.990 | 0.997 / 0.992 |
| mean peak age (ms) | 81.4 | 102.7 | 81.8 | 82.0 | 122.3 |

**Mobile (100 nodes from the start): the three controllers give the same runs, series line for
line** (checked for seeds 1, 5, 9) — at 100 nodes each wants b = 4 from its first decision and
climbs 1 → 2 → 3 → 4 at the pace of the hysteresis; no threshold binds. That scenario cannot tell
the controllers apart, and it is not counted as agreement.

* **A4b-1 (`adaptive-m20`):** `failure_n` ≥ 115 **HELD** on the mean (116.2; three seeds of ten
  at 111–114); windows ≤ 115 at V ≥ 0.95 ≥ 0.95 **MISSED** (0.93); mean peak age 100–115 ms
  **HELD** (103.1); below 30 nodes within 10 % of fixed b = 1 **HELD** (equal).
* **A4b-2 (`predict`):** `failure_n` ≥ 105 **HELD** on the mean (107.9; one seed at 73); windows in
  0.85–0.95 **MISSED** by 0.003 (0.847); age 95–110 ms **HELD** (98.9).
* **A4b-3:** `adaptive-m20` merged minute ≥ 0.95 **HELD** (0.980); `predict` in 0.93–0.96 **HELD**
  (0.948 — as A4's adaptive, the step is not anticipated).
* **A4b-4:** ≤ 6 changes per node per minute **HELD** (3.2, 1.3); `predict` no more than twice
  A4's **HELD** (equal).
* A4's criteria applied to each: (1) age below 30 nodes **HELD** (both); (2) "about 30 ms" fresher
  than fixed b = 4 **FAILED** (both: 89.7 ms, the plan's figure is a mean wait); (3) `failure_n`
  within 5 % of fixed b = 4's **FAILED** (both: −8.6 %, −15 %) — the second half, mean b ≥ 3.5
  before failure, **HELD** for both (81, 89 < 116, 108); (4) merge ≥ 0.95 **HELD** (both);
  (6) fixed b = 4 older in every scenario **HELD** (both).

**What it means.** The margin was the larger cause, the lag the smaller. Doubling the margin
holds V ≥ 0.95 in 93 % of the windows of a growing swarm (A4's: 75 %), fails at 116 nodes instead
of 76, and still saves 20–21 ms of peak age against fixed b = 4 (ramp, merge); the growth term
alone, at A4's margin, lifts the share to 85 % and the failure point to 108 at almost no cost in
age (98.9 against 98.2). Neither reaches the plan's "within 5 % of fixed b = 4", and neither holds
V in every window: an adaptive batch trades some reliability margin for freshness, and how much
is a parameter (the margin), not a free gain. The two changes are independent and could be
combined; that would be a third registration, not done here.
