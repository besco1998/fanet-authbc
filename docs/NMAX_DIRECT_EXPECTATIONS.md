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
