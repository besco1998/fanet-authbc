# A1, motion — every node moving on its own (decision H8)

*Registered 2026-10-21 before any run of the scenario below at a registered setting. Plan:
`docs/AUTHBC Revision Plan.md`, A1 (its fourth statement); decision H8 (Mohamed, 2026-10-21:
test relative motion at 5–15 m/s, under the rules of `docs/MOBILITY_PLAN.md`, E20). Outcome
appended below a line at the end.*

## Why

A1's S3 moved the group's reference point only; with no velocity term in the channel, 5 and
15 m/s gave identical runs (F88). What was tested was members drifting at 2–4 m/s. Here every
node moves on its own, so a receiver's neighbours and contenders change during a run.

## What is run

`ns3/authbc-spatial-mobile.cc` — a separate file, as E20 requires: a copy of
`authbc-spatial.cc` plus layout `gm` (its header gives every parameter). Nodes uniform in a
square of the area of S1's R = 1 km disc (side 1 772 m), altitude 50–150 m; each node a
Gauss–Markov process, α = 0.85, step 0.5 s, mean speed v, own mean heading, speed σ = 0.1 v,
heading σ 45°, reflecting bounds. **v ∈ {0, 5, 15} m/s; v = 0 is the static control, built with
the same model and the same random variables** (zero mean and zero noise), so that nothing but
motion differs between speeds (F37, F87). Parameters from the published envelope
(`docs/MOBILITY_SURVEY.md` §6). Same channel, traffic, metrics, d_ref = 215 m, 20 s, 30 seeds as
A1. Configurations base and design, on S1-R1000's stage-2 grids (base 60–70, design 199–234).
Plan `experiments/spatial/plan_motion.txt`; `ns3/run_spatial.py --stem motion`. 900 runs.

**Checks made before this commit** (development runs, none at a registered setting): the copy
with layout `disc` reproduces three stage-2 runs of `authbc-spatial.cc` bit for bit
(s1-r300/base/28/1, s1-r1000/base/60/2, s2/base/31/3); for `gm` at N = 60, seed 1, 3 s, base
frames, the starting positions are identical at the three speeds, the nodes of v = 0 end where
they started, and the runs at 5 and 15 m/s differ from each other and from v = 0. At 15 m/s the
nodes moved 68.4 m on average, over the 5 s the simulator runs (sources from 1 s, stop at
simTime + 2 s): 75 m at most, less with the heading noise — read as a check of the speed.

## Predictions — the plan's, as scored for A1

> Mobility up to 15 m/s changes V by less than 0.01. A node moves at most 1.2 m during one
> 80 ms fill time.

> The ratio stays between 3.0× and 4.0×.

Scored as: (1) at every node count of each configuration, |V(5) − V(0)| and |V(15) − V(0)|
< 0.01 (per-receiver V, 30-seed means); (2) design/base ratio of the interpolated crossings in
[3.0, 4.0] at each speed.

## Mine `[agent]`

* **AM-1.** |ΔV| ≤ 0.005 at every node count, both configurations, both speeds. Motion acts
  only through geometry (fading is drawn per frame at every speed), and the density stays
  uniform on average; churn of neighbours changes which nodes contend, not how many.
* **AM-2.** The ratio at 5 and at 15 m/s within ±3 % of the static control's.
* **AM-3.** The static control's crossings lie 0–5 % above S1-R1000's (217.84 design, 63.01
  base): at equal area the square has 13 % more perimeter, so more nodes near an edge, with
  fewer neighbours.
* **AM-4 (discriminators, not predictions of a result).** In the registered runs: 5 and 15 m/s
  are not identical; the per-run neighbour count (`mean_neighbours`, averaged over the run's
  sends) has the same 30-seed mean at the three speeds within 3 %.

## What this cannot show

Doppler and time-correlated fading (not in the channel at any speed); collision avoidance and
formation keeping (independent random motion is the harder case for the neighbour set, not the
realistic one for a swarm); hovering is assumed at v = 0 (rotary-wing only, E20 §5.3).

---

## Outcome (2026-10-21; 900 ns-3 runs)

`results/raw/spatial_motion.csv` (`analysis/spatial_capacity.py --score motion --d-ref 215 --out
results/raw/spatial_motion.csv`); runs `results/raw/ns3_spatial_motion_runs.csv`.

| | base: crossing [95 %] | design: crossing [95 %] | ratio |
|---|---|---|---|
| still (control) | 62.10 [60.46, 63.76] | 223.86 [220.85, 226.92] | 3.605 |
| 5 m/s | 61.38 [60.22, 63.16] | 222.53 [219.57, 225.86] | 3.625 |
| 15 m/s | 62.02 [60.44, 63.57] | 221.30 [217.75, 225.03] | 3.568 |

(Intervals are the plain percentile bootstrap, the method A1 was registered with; F101.)

ΔV against the still control, per node count (30-seed means of per-receiver V):

| | base 60 | 63 | 65 | 68 | 70 | design 199 | 208 | 217 | 225 | 234 |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 m/s | −0.0003 | −0.0005 | −0.0005 | −0.0001 | −0.0001 | −0.0002 | −0.0001 | −0.0002 | −0.0002 | −0.0001 |
| 15 m/s | −0.0001 | 0.0000 | −0.0004 | +0.0001 | +0.0001 | −0.0004 | −0.0003 | −0.0004 | −0.0004 | −0.0005 |

* Plan (1), |ΔV| < 0.01 at every node count: **HELD** — largest 0.0005, now with every node
  moving on its own (relative speeds up to ~30 m/s at 15 m/s each).
* Plan (2), ratio in [3.0, 4.0] at each speed: **HELD** (3.57–3.63).
* AM-1, |ΔV| ≤ 0.005: **HELD**. The design at 15 m/s is lower at all five node counts
  (−0.0003 to −0.0005; about 1.8 standard errors on their mean) — if real, an effect a tenth of
  the bound; not significant here.
* AM-2, ratio within ±3 % of the control's: **HELD** (+0.6 %, −1.0 %).
* AM-3, the square's control 0–5 % above the disc's crossings: design **HELD** (+2.8 %); base
  **MISSED** (−1.4 %; the two intervals overlap).
* AM-4 (discriminators): 5 and 15 m/s identical in **0 of 300** runs — motion does change the
  runs, unlike F88's group; mean neighbours equal across speeds within 0.85 % (base) and 0.22 %
  (design).

**What it means.** With every node flying its own path at up to 15 m/s — neighbours appearing and
leaving during a run — delivery moves by at most 0.0005 and the design's advantage stays at 3.6×.
In this channel, which has no Doppler or time-correlated fading, motion acts through who
contends, and at uniform density the number who contend does not change. The plan's mobility
statement is now tested for relative motion, not only for a rigid group (F88).
