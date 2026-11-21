# U-F — capacity with capture and geometry: (G22)–(G24) with (G25) in ns-3

*Registered 2026-11-20, before any U-F capacity run; the time is the commit's. Work package F of
`docs/prompts/NEXT_PHASE_PROMPT.md`.*

*Mohamed (2026-11-20): "Register F's capacities under both the Poisson model and (G25), so that F
stays valid whatever B shows". B then held (`prereg-UG25`, 16 of 16). The corrected receiver rule
may be used after U-CAP2, which held 552 of 552.*

## The model under test (`src/authbc/models/capture.py`)

    p_ij = p_c(ν)·(1 − q_ij) + ℓ_ij                                              (G22)
    the average criterion:      p_c(ν) = ε′,  ε′ = (ε − mean ℓ)/(1 − mean q)    (G23)
    the every-sender criterion: ε_w = min over senders j of (ε − ℓ_j)/(1 − q_j)  (G24)

* **The capacity** is the root of the loss expression at ε′ or ε_w in place of ε, under (G25)
  (scored) and under the Poisson (G5) (reported).
* **q for ns-3's rule:**
  * every DCF collision starts within the 4 µs preamble window, where the strongest frame is
    kept if its SINR is at least θ = 4 dB, and the capture model never acts
    (`predictions/UCAP.md`, `UCAP2.md`);
  * Rayleigh: q_ij is the mean over the other stations m of 1/(1 + θ(d_ij/d_im)^α);
  * no fading: the share of m with d_im > θ^(1/α)·d_ij;
  * q_j and ℓ_j are sender j's means over its receivers.
* **ℓ_ij:** 0 without fading. With Rayleigh, the probability of fading below the −82 dBm
  detection floor, 1 − exp(−10^((−82 − P̄_ij)/10)).

## The configurations (`analysis/uf.py`)

* **Cells:** C (146 B at 50 frames/s) and D (173 B at 12.5 frames/s).
* **PHYs:** 802.11a 6 Mb/s and 802.11b 1 Mb/s.
* **Path loss:** exponent α = 2 and 3, with and without Nakagami m = 1 (Rayleigh) per frame and
  link.
* **The ns-3 receiver:** the scenario's own, with no frame-capture model.
* **The channel:**
  * every node transmits at 40 dBm, nodes uniform in a disc;
  * ns-3's log-distance model, 46.6777 dB at 1 m, clamped below 1 m;
  * the radius is the largest whole metre at which a pair 2R apart still receives −50 dBm on
    average, 32 dB above the floor: **R = 73 m at α = 2, R = 13 m at α = 3**.
* **Checked before registration** (`python analysis/uf.py --radius`):
  * the longest pair receives −49.96 dBm (α = 2) and −49.13 dBm (α = 3);
  * Rayleigh ℓ at that pair is 0.063 % and 0.052 %, **below the required 0.1 %**;
  * every pair is above the −82 dBm carrier-sense floor on average;
  * about 0.02 % (α = 2) and 0.59 % (α = 3) of pairs are closer than 1 m, where ns-3 clamps the
    loss, stated as a caveat;
  * ns-3's Rayleigh draw below a floor was checked in F136 (2.81 % against the exact 3.00 %).
* **The placements are the runs' own:** the twin's `--placementOnly` at seeds 1–30 and at a
  reference N, 1.3 × the no-capture (G25) root. Mean q depends only on the distance ratios, so on
  the geometry and not on N. ε_w is taken at that N.

## Predictions (`python analysis/uf.py --markdown`, generated)

| config | cell | PHY | α | fading | R (m) | N_ref | mean q | mean ℓ | ε′ | ε_w | **(G23), (G25) root** | (G23), Poisson | **(G24), (G25) root** | (G24), Poisson | no capture, (G25) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FCAP2N | C | 80211a | 2 | none | 73 | 45 | 0.2532 | 0.00000 | 0.0670 | 0.0567 | **39.07** | 38.28 | **36.36** | 35.66 | 34.35 |
| FCAP2R | C | 80211a | 2 | Rayleigh | 73 | 45 | 0.3436 | 0.00016 | 0.0759 | 0.0652 | **41.21** | 40.33 | **38.63** | 37.86 | 34.35 |
| FCAP3N | C | 80211a | 3 | none | 13 | 45 | 0.3218 | 0.00000 | 0.0737 | 0.0598 | **40.70** | 39.84 | **37.20** | 36.47 | 34.35 |
| FCAP3R | C | 80211a | 3 | Rayleigh | 13 | 45 | 0.3712 | 0.00008 | 0.0794 | 0.0655 | **41.98** | 41.06 | **38.70** | 37.92 | 34.35 |
| FCBP2N | C | 80211b | 2 | none | 73 | 13 | 0.2532 | 0.00000 | 0.0670 | 0.0554 | **10.76** | 9.65 | **10.19** | 9.19 | 9.89 |
| FCBP2R | C | 80211b | 2 | Rayleigh | 73 | 13 | 0.3439 | 0.00016 | 0.0760 | 0.0636 | **11.14** | 9.96 | **10.60** | 9.53 | 9.89 |
| FCBP3N | C | 80211b | 3 | none | 13 | 13 | 0.3220 | 0.00000 | 0.0738 | 0.0585 | **11.05** | 9.88 | **10.35** | 9.32 | 9.89 |
| FCBP3R | C | 80211b | 3 | Rayleigh | 13 | 13 | 0.3716 | 0.00008 | 0.0794 | 0.0639 | **11.28** | 10.07 | **10.61** | 9.54 | 9.89 |
| FDAP2N | D | 80211a | 2 | none | 73 | 158 | 0.2531 | 0.00000 | 0.0669 | 0.0579 | **137.79** | 136.80 | **129.55** | 128.67 | 121.43 |
| FDAP2R | D | 80211a | 2 | Rayleigh | 73 | 158 | 0.3434 | 0.00016 | 0.0759 | 0.0663 | **145.15** | 144.05 | **137.27** | 136.28 | 121.43 |
| FDAP3N | D | 80211a | 3 | none | 13 | 158 | 0.3219 | 0.00000 | 0.0737 | 0.0611 | **143.43** | 142.36 | **132.54** | 131.62 | 121.43 |
| FDAP3R | D | 80211a | 3 | Rayleigh | 13 | 158 | 0.3710 | 0.00008 | 0.0794 | 0.0668 | **147.79** | 146.66 | **137.71** | 136.72 | 121.43 |
| FDBP2N | D | 80211b | 2 | none | 73 | 40 | 0.2531 | 0.00000 | 0.0669 | 0.0563 | **33.58** | 31.90 | **31.95** | 30.44 | 30.84 |
| FDBP2R | D | 80211b | 2 | Rayleigh | 73 | 40 | 0.3434 | 0.00016 | 0.0759 | 0.0648 | **34.79** | 32.98 | **33.27** | 31.62 | 30.84 |
| FDBP3N | D | 80211b | 3 | none | 13 | 40 | 0.3219 | 0.00000 | 0.0737 | 0.0593 | **34.51** | 32.73 | **32.43** | 30.87 | 30.84 |
| FDBP3R | D | 80211b | 3 | Rayleigh | 13 | 40 | 0.3710 | 0.00008 | 0.0794 | 0.0650 | **35.23** | 33.36 | **33.31** | 31.65 | 30.84 |

**The outlier configuration** `FOUT`, scored on its own: FCAP3R (802.11a cell C, α = 3, Rayleigh)
with node 0 moved to (250 m, 0) by `--outlierM`.
* Every link of node 0 is about −79 dBm on average, 3 dB over the floor, so ℓ_0 ≈ 0.37.
* Run at N = 42, round(FCAP3R's (G23) root).
* **Predicted** (`python analysis/uf.py --outlier`): node 0's own loss
  p_0 = p_c(1 − q_0) + ℓ_0 = **0.448** (p_c = 0.0795 from (G25), q_0 ≈ 0, ℓ_0 = 0.368).
* So ε_w,0 = −0.32: **(G24) admits no swarm containing node 0, at any N.**

## What is run and how it is scored

* **The runs:** the audit twin (gate 9/9) through `ns3/run_unified.py`; the designated source;
  20 s; `--perNode` and `--perPair` kept (`--trace`).
* **Pilot:** 5 seeds on seven node counts at ±5 % steps around the (G23), (G25) root.
* **Main:** 30 seeds (1–30) on node counts by U-C2's rule around **both** pilot crossings. The
  average crossing is the mean delivered fraction; the every-sender crossing is the per-seed
  worst sender's delivery, averaged over seeds.
* **Scored, ±5 %, fixed now,** 32 predictions:
  * **(G23), (G25) root** against ns-3's crossing of the 30-seed mean delivered fraction at 0.95;
  * **(G24), (G25) root** against ns-3's crossing of the 30-seed mean of each seed's *worst
    sender's* delivered fraction at 0.95.
* **Reported, not scored:**
  * the Poisson versions;
  * the no-capture root's error;
  * the measured per-pair loss against (G22) with p_c from (G25), from `_pairs.csv`.
* **FOUT** (30 seeds at N = 42): node 0's measured loss against 0.448, **held if within ±20 %
  relative**. A loss this large cannot be resolved finer: link and collision terms interact.
  The others' (G23) crossing is reported.
* **A failure** is reported with its side:
  * *optimistic:* the model admits more stations than ns-3;
  * *conservative:* fewer.

## Expectations `[agent]`

* **(G23) holds in most configurations.** The capture closed forms assume two-frame collisions
  and the ns-3 rule as U-CAP measured it. At these loads most collisions are pairs.
* **The likeliest misses are the no-fading configurations at α = 2.** There q is a step in
  distance, and the disc's geometry, its edges especially, decides it.
* **(G24) is harder:** it rests on the worst sender at one reference N. A miss on the
  conservative side is more likely than on the optimistic one.
* **FOUT:** node 0 loses about 40–50 %; the others are barely affected.

## Disclosure

* **Known before this registration:**
  * U-CAP, U-CAP2, U-G25 and U-FS outcomes;
  * F136;
  * one smoke run of the options (`--radiusM=13 --pathLossExp=3 --txPowerDbm=40 --nakagamiM=1`)
    at N = 10, seed 99, 2 s, to check that the run and its per-node and per-pair files work
    (delivered 0.997). Not a registered cell.
* **No capacity run has been made** at any configuration.


---

## Outcome — added 2026-11-21, after the runs; nothing above this line was changed

**The runs.** As registered: `ns3/run_uf.py` through the audit twin (gate 9/9), the designated
source, 20 s. Pilots of 5 seeds, then 30 seeds (1–30) at 7–14 node counts per configuration around
both pilot crossings (`results/raw/uf_<config>{_pilot,}_runs.csv`); FOUT at N = 42, 30 seeds.
Every 30-seed node count has all 30 seeds.

**Checked before writing:**
* **one crossing recomputed from the raw runs without the project's code:** FDBP2N's average
  crossing, 33.5239, the scored value;
* **the bootstrap interval of each crossing over seeds** (`results/raw/uf_diagnose_ci.csv`),
  computed after scoring and reported, not scored.

**Scored** by `python analysis/uf.py --score` → `results/raw/uf_scored.csv`. Every table below is
generated by `python analysis/uf_outcome.py`; none is typed by hand.

**Scored: (G23) 12 of 16 held; (G24) 2 of 16 held; FOUT failed. 14 of 33.** Errors are
model − ns-3, in % of ns-3's crossing.

| config | ns-3 average crossing (95 % CI) | (G23), (G25) | error | | Poisson error | no-capture error | ns-3 every-sender crossing (95 % CI) | (G24), (G25) | error | |
|---|---|---|---|---|---|---|---|---|---|---|
| FCAP2N | 39.45 (39.37–39.53) | 39.07 | -0.97 % | held | -2.98 % | -12.94 % | 33.91 (33.54–34.28) | 36.36 | +7.24 % | **failed**, optimistic |
| FCAP2R | 41.32 (41.15–41.45) | 41.21 | -0.27 % | held | -2.40 % | -16.87 % | 36.31 (35.89–36.86) | 38.63 | +6.38 % | **failed**, optimistic |
| FCAP3N | 41.33 (41.21–41.42) | 40.70 | -1.51 % | held | -3.60 % | -16.88 % | 35.25 (34.90–35.51) | 37.20 | +5.52 % | **failed**, optimistic |
| FCAP3R | 42.55 (42.43–42.68) | 41.98 | -1.35 % | held | -3.51 % | -19.28 % | 36.95 (36.68–37.26) | 38.70 | +4.74 % | held |
| FCBP2N | 10.24 (10.22–10.27) | 10.76 | +5.05 % | **failed**, optimistic | -5.79 % | -3.44 % | 9.73 (9.64–9.83) | 10.19 | +4.75 % | held |
| FCBP2R | 10.42 (10.40–10.45) | 11.14 | +6.87 % | **failed**, optimistic | -4.45 % | -5.12 % | 10.02 (9.94–10.07) | 10.60 | +5.78 % | **failed**, optimistic |
| FCBP3N | 10.41 (10.39–10.44) | 11.05 | +6.14 % | **failed**, optimistic | -5.10 % | -5.00 % | 9.79 (9.70–9.91) | 10.35 | +5.67 % | **failed**, optimistic |
| FCBP3R | 10.52 (10.49–10.54) | 11.28 | +7.26 % | **failed**, optimistic | -4.25 % | -5.96 % | 10.00 (9.91–10.05) | 10.61 | +6.14 % | **failed**, optimistic |
| FDAP2N | 139.60 (139.27–139.95) | 137.79 | -1.30 % | held | -2.00 % | -13.01 % | below the grid: 0.9316 at N = 121 | 129.55 | > +7.07 % | **failed**, optimistic |
| FDAP2R | 146.76 (146.40–147.26) | 145.15 | -1.09 % | held | -1.84 % | -17.26 % | below the grid: 0.9331 at N = 128 | 137.27 | > +7.24 % | **failed**, optimistic |
| FDAP3N | 145.76 (145.35–146.27) | 143.43 | -1.60 % | held | -2.34 % | -16.69 % | below the grid: 0.9345 at N = 124 | 132.54 | > +6.89 % | **failed**, optimistic |
| FDAP3R | 150.40 (150.03–150.87) | 147.79 | -1.73 % | held | -2.49 % | -19.26 % | below the grid: 0.9337 at N = 129 | 137.71 | > +6.75 % | **failed**, optimistic |
| FDBP2N | 33.52 (33.33–33.66) | 33.58 | +0.17 % | held | -4.84 % | -8.01 % | 28.34 (27.90–28.67) | 31.95 | +12.75 % | **failed**, optimistic |
| FDBP2R | 34.52 (34.41–34.65) | 34.79 | +0.78 % | held | -4.46 % | -10.66 % | 29.88 (29.65–30.14) | 33.27 | +11.34 % | **failed**, optimistic |
| FDBP3N | 34.40 (34.28–34.51) | 34.51 | +0.32 % | held | -4.86 % | -10.35 % | 29.29 (28.78–29.57) | 32.43 | +10.73 % | **failed**, optimistic |
| FDBP3R | 35.07 (34.94–35.17) | 35.23 | +0.45 % | held | -4.88 % | -12.06 % | 29.96 (29.66–30.53) | 33.31 | +11.17 % | **failed**, optimistic |

* **FDAP's every-sender crossing lies below the grid** at all four configurations: the pilot did
  not bracket it, so the main grid was centred on the (G24) prediction, and the 30-seed mean of the
  worst sender is below 0.95 at the grid's lowest N. Each is scored failed, with its error given as
  a bound.

**The outlier:**

| run | node 0 | error | scored | the others |
|---|---|---|---|---|
| FOUT, N = 42, 30 seeds | node 0's loss: measured 0.6813, predicted 0.4480 | -34.25 % | **failed** (±20 %) | the others' mean loss 0.0580 |

**What it shows:**
* **(G23) held at all 12 configurations of 802.11a and of 802.11b cell D,** within −1.73 … +0.78 %.
* **(G23) failed at the four 802.11b cell C configurations, optimistic,** by +5.05 … +7.26 %.
  * Most of each miss is (G25)'s loss curve at occupancy ≈ 0.85 and loss 6.4–7.9 %, outside the
    range U-G25 checked (F140).
  * The rest is the capture share: the closed form omits that a colliding partner cannot
    receive, and the registered q̄ is too high by (N − 2)/(N − 1), a factor of 0.89 at N = 10
    (F138).
* **Capture matters to the capacity:** the no-capture root lies −3.4 … −19.3 % below ns-3's
  crossing, most at α = 3 with fading.
* **The Poisson versions** (reported only) lie −1.8 … −5.8 % below, conservative.
* **(G24) held at 2 of 16 (FCAP3R, FCBP2N), failed at 14, every one optimistic.**
  * The statistic registered, the 30-seed mean of each run's worst sender, is the minimum of N
    finite samples. Its noise lowers it below the worst sender's expected delivery, which is what
    ε_w models (F139).
  * The measured worst sender equals geometry plus count noise within 0.004 at every point;
    geometry alone lies 0.001–0.027 higher. **So these are not a test of ε_w**, and they stay
    failed as registered.
* **FOUT failed, optimistic** (0.448 predicted, 0.681 measured; F141).
  * The link term is right: node 0's frames that overlap no other lose 0.360–0.368, against
    ℓ_0 = 0.364–0.371 from the placement.
  * Node 0's collision probability is not the swarm's. 48–53 % of its frames overlap another,
    against p_c = 0.08. Its neighbours' carrier sense fails as often as its link does, because
    ns-3 uses one −82 dBm threshold for both.
  * The others are barely affected, as expected (mean loss 0.058). (G24)'s registered verdict,
    that no swarm containing node 0 meets the every-sender criterion, stands.
* **The expectations `[agent]`:**
  * *(G23) holds in most configurations:* true, 12 of 16.
  * *The likeliest misses are the no-fading configurations at α = 2:* not true. The misses were
    802.11b cell C at every α and fading.
  * *(G24) misses on the conservative side:* not true. Every miss was optimistic.
  * *FOUT loses 40–50 %:* not true; 68 %.

## Diagnostics, not scored (`analysis/uf_diagnose.py`, `results/raw/uf_diagnose_*.csv`)

Each was run after scoring. Where a diagnostic states an expectation, it was written into its
function before the data were read.

**The capture share q, four ways.** The registered closed form; that form with F138's factor;
ns-3's ratio of capture to no-capture loss at equal configuration (q̂, from the stored
no-capture runs, "approximate" where the no-capture grid does not hold that N); and ns-3's own
collision events, from the MAC and reception traces.

| config | closed form, registered q̄ | × (N − 2)/(N − 1) at ns-3's crossing | ns-3, no-capture ratio q̂ at the nearest N | ns-3, on the collision events |
|---|---|---|---|---|
| FCAP2N | 0.2532 | 0.2466 | 0.241 ± 0.007 (N = 34) | 0.2454 (N = 39) |
| FCAP2R | 0.3436 | 0.3351 | 0.315 ± 0.006 (N = 34, approximate) | — |
| FCAP3N | 0.3218 | 0.3138 | 0.317 ± 0.007 (N = 34) | 0.3078 (N = 41) |
| FCAP3R | 0.3712 | 0.3623 | 0.349 ± 0.004 (N = 45, approximate) | — |
| FCBP2N | 0.2532 | 0.2258 | 0.217 ± 0.011 (N = 10) | 0.2105 (N = 10) |
| FCBP2R | 0.3439 | 0.3074 | 0.282 ± 0.010 (N = 10, approximate) | — |
| FCBP3N | 0.3220 | 0.2878 | 0.278 ± 0.011 (N = 10) | 0.2705 (N = 10) |
| FCBP3R | 0.3716 | 0.3326 | 0.321 ± 0.007 (N = 11, approximate) | — |
| FDAP2N | 0.2531 | 0.2513 | 0.226 ± 0.011 (N = 121) | — |
| FDAP2R | 0.3434 | 0.3410 | — | — |
| FDAP3N | 0.3219 | 0.3197 | — | — |
| FDAP3R | 0.3710 | 0.3685 | — | — |
| FDBP2N | 0.2531 | 0.2453 | 0.234 ± 0.015 (N = 33) | 0.2440 (N = 33) |
| FDBP2R | 0.3434 | 0.3332 | 0.315 ± 0.008 (N = 36, approximate) | — |
| FDBP3N | 0.3219 | 0.3123 | 0.297 ± 0.011 (N = 33) | 0.3027 (N = 34) |
| FDBP3R | 0.3710 | 0.3601 | 0.348 ± 0.008 (N = 36, approximate) | — |

**The registered per-pair report:** each pair's measured loss against (G22) with p_c from (G25),
pooled over 30 seeds at the grid N nearest ns-3's average crossing. The ceiling is the correlation
a perfect model would reach under the count noise alone.

| config | N | pairs | mean loss: measured | (G22), p_c from (G25) | sd across pairs: measured | predicted + count noise | correlation | ceiling |
|---|---|---|---|---|---|---|---|---|
| FCAP2N | 39 | 44460 | 0.0485 | 0.0498 | 0.0202 | 0.0220 | 0.942 | 0.950 |
| FCAP2R | 41 | 49200 | 0.0492 | 0.0494 | 0.0158 | 0.0167 | 0.903 | 0.912 |
| FCAP3N | 41 | 49200 | 0.0490 | 0.0509 | 0.0231 | 0.0253 | 0.956 | 0.962 |
| FCAP3R | 43 | 54180 | 0.0512 | 0.0530 | 0.0197 | 0.0215 | 0.936 | 0.944 |
| FCBP2N | 10 | 2700 | 0.0435 | 0.0387 | 0.0172 | 0.0183 | 0.933 | 0.943 |
| FCBP2R | 10 | 2700 | 0.0400 | 0.0342 | 0.0122 | 0.0125 | 0.880 | 0.888 |
| FCBP3N | 10 | 2700 | 0.0401 | 0.0352 | 0.0181 | 0.0189 | 0.935 | 0.952 |
| FCBP3R | 11 | 3300 | 0.0610 | 0.0457 | 0.0213 | 0.0193 | 0.940 | 0.940 |
| FDAP2N | 140 | 583800 | 0.0505 | 0.0519 | 0.0245 | 0.0258 | 0.826 | 0.839 |
| FDAP2R | 147 | 643860 | 0.0502 | 0.0516 | 0.0204 | 0.0211 | 0.730 | 0.747 |
| FDAP3N | 146 | 635100 | 0.0502 | 0.0522 | 0.0267 | 0.0285 | 0.861 | 0.870 |
| FDAP3R | 151 | 679500 | 0.0505 | 0.0527 | 0.0231 | 0.0245 | 0.803 | 0.818 |
| FDBP2N | 34 | 33660 | 0.0526 | 0.0522 | 0.0249 | 0.0261 | 0.823 | 0.843 |
| FDBP2R | 35 | 35700 | 0.0526 | 0.0511 | 0.0210 | 0.0210 | 0.727 | 0.748 |
| FDBP3N | 34 | 33660 | 0.0478 | 0.0474 | 0.0250 | 0.0264 | 0.841 | 0.862 |
| FDBP3R | 35 | 35700 | 0.0496 | 0.0488 | 0.0224 | 0.0232 | 0.792 | 0.809 |

* **(G22)'s geometry holds pair by pair.** The correlation lies within 0.021 of its ceiling at
  every configuration. The spread across pairs equals the predicted spread plus count noise
  within ±0.0022.
* **The mean is off where (G23) failed:** at 802.11b cell C, (G22) is 0.005–0.015 below the
  measured mean (F138, F140). Elsewhere it is within ±0.0023.

**The (G23) misses, split** (F140): (G25)'s root at ε′ against ns-3's stored no-capture curve
crossed at the same ε′ (the loss-curve term); that crossing against the same curve at
ε/(1 − q̂) (the q term); and the closure against the capture crossing. FCAP's and FDAP's
no-capture grids come from U-C1. FDAP2R, FDAP3N and FDAP3R have no no-capture run near their
crossing, so no split is given for them.

| config | total (G23) error | loss-curve term (linear; quadratic) | q term | closure |
|---|---|---|---|---|
| FCAP2N | -0.94 % | -0.56 %; -1.88 % | +0.73 % | -1.11 % |
| FCAP2R | -0.29 % | -1.14 %; -2.13 % | +2.00 % | -1.14 % |
| FCAP3N | -1.52 % | -0.95 %; -2.04 % | +0.34 % | -0.92 % |
| FCAP3R | -1.35 % | -1.47 %; -2.22 % | +1.70 % | -1.59 % |
| FCBP2N | +5.02 % | +4.11 %; +3.61 % | +0.90 % | +0.01 % |
| FCBP2R | +6.90 % | +5.21 %; +4.28 % | +1.85 % | -0.16 % |
| FCBP3N | +6.16 % | +4.96 %; +3.95 % | +1.29 % | -0.09 % |
| FCBP3R | +7.24 % | +5.51 %; +4.76 % | +1.65 % | +0.09 % |
| FDAP2N | -1.32 % | -0.52 %; -2.08 % | +1.45 % | -2.25 % |
| FDBP2N | +0.16 % | -0.25 %; -0.46 % | +0.60 % | -0.19 % |
| FDBP2R | +0.79 % | +0.02 %; -0.35 % | +1.14 % | -0.37 % |
| FDBP3N | +0.32 % | -0.01 %; -0.41 % | +0.93 % | -0.60 % |
| FDBP3R | +0.46 % | +0.02 %; -0.26 % | +1.00 % | -0.56 % |

* **(G22) closes at 802.11b cell C** within ±0.16 %: fed ns-3's own q̂ and no-capture curve, it
  gives ns-3's capture crossing. Elsewhere the closure is −0.19 … −2.25 %, so part of those
  configurations' small (G23) errors lies outside the two terms.

**With F138's factor,** the same roots recomputed (not a registration):

| config | (G23) registered → with the factor | error registered → with it | (G24) registered → with it | error with it |
|---|---|---|---|---|
| FCAP2N | 39.07 → 38.92 | -0.97 % → -1.34 % | 36.36 → 36.30 | +7.04 % |
| FCAP2R | 41.21 → 40.98 | -0.27 % → -0.81 % | 38.63 → 38.50 | +6.02 % |
| FCAP3N | 40.70 → 40.50 | -1.51 % → -2.00 % | 37.20 → 37.11 | +5.28 % |
| FCAP3R | 41.98 → 41.73 | -1.35 % → -1.95 % | 38.70 → 38.57 | +4.38 % |
| FCBP2N | 10.76 → 10.65 | +5.05 % → +3.98 % | 10.19 → 10.15 | +4.36 % |
| FCBP2R | 11.14 → 10.98 | +6.87 % → +5.37 % | 10.60 → 10.51 | +4.93 % |
| FCBP3N | 11.05 → 10.91 | +6.14 % → +4.76 % | 10.35 → 10.29 | +5.09 % |
| FCBP3R | 11.28 → 11.10 | +7.26 % → +5.58 % | 10.61 → 10.52 | +5.29 % |
| FDAP2N | 137.79 → 137.65 | -1.30 % → -1.40 % | 129.55 → 129.48 | — |
| FDAP2R | 145.15 → 144.93 | -1.09 % → -1.24 % | 137.27 → 137.13 | — |
| FDAP3N | 143.43 → 143.23 | -1.60 % → -1.74 % | 132.54 → 132.45 | — |
| FDAP3R | 147.79 → 147.55 | -1.73 % → -1.89 % | 137.71 → 137.57 | — |
| FDBP2N | 33.58 → 33.48 | +0.17 % → -0.12 % | 31.95 → 31.91 | +12.62 % |
| FDBP2R | 34.79 → 34.65 | +0.78 % → +0.36 % | 33.27 → 33.18 | +11.05 % |
| FDBP3N | 34.51 → 34.38 | +0.32 % → -0.07 % | 32.43 → 32.38 | +10.55 % |
| FDBP3R | 35.23 → 35.06 | +0.45 % → -0.03 % | 33.31 → 33.22 | +10.85 % |

**The worst sender, at the two grid N nearest each every-sender crossing** (F139): each sender's
expected delivery from (G22) with the run's own p_c, plus binomial noise, 200 Monte Carlo draws
per run. For FDAP, whose crossing is below the grid, the grid's lowest two N.

| config | N | sd across senders: measured | geometry alone | binomial noise | geometry + noise | worst sender: measured | geometry alone (what ε_w models) | geometry + noise |
|---|---|---|---|---|---|---|---|---|
| FCAP2N | 34 | 0.0059 | 0.0037 | 0.0051 | 0.0063 | **0.9497** | 0.9576 | **0.9505** |
| FCAP2N | 33 | 0.0061 | 0.0035 | 0.0049 | 0.0060 | **0.9525** | 0.9602 | **0.9534** |
| FCAP2R | 36 | 0.0057 | 0.0031 | 0.0048 | 0.0057 | **0.9506** | 0.9575 | **0.9509** |
| FCAP2R | 37 | 0.0057 | 0.0034 | 0.0049 | 0.0060 | **0.9488** | 0.9543 | **0.9476** |
| FCAP3N | 35 | 0.0064 | 0.0051 | 0.0048 | 0.0070 | **0.9508** | 0.9569 | **0.9504** |
| FCAP3N | 36 | 0.0069 | 0.0054 | 0.0049 | 0.0073 | **0.9475** | 0.9545 | **0.9479** |
| FCAP3R | 37 | 0.0060 | 0.0042 | 0.0047 | 0.0063 | **0.9498** | 0.9555 | **0.9493** |
| FCAP3R | 36 | 0.0057 | 0.0040 | 0.0045 | 0.0061 | **0.9529** | 0.9580 | **0.9520** |
| FCBP2N | 10 | 0.0066 | 0.0058 | 0.0056 | 0.0080 | **0.9460** | 0.9473 | **0.9431** |
| FCBP2N | 9 | 0.0058 | 0.0041 | 0.0046 | 0.0062 | **0.9606** | 0.9648 | **0.9610** |
| FCBP2R | 10 | 0.0058 | 0.0047 | 0.0050 | 0.0069 | **0.9506** | 0.9523 | **0.9484** |
| FCBP2R | 11 | 0.0080 | 0.0069 | 0.0062 | 0.0093 | **0.9222** | 0.9246 | **0.9204** |
| FCBP3N | 10 | 0.0079 | 0.0071 | 0.0051 | 0.0087 | **0.9466** | 0.9495 | **0.9456** |
| FCBP3N | 9 | 0.0059 | 0.0049 | 0.0042 | 0.0065 | **0.9630** | 0.9662 | **0.9630** |
| FCBP3R | 10 | 0.0067 | 0.0057 | 0.0048 | 0.0075 | **0.9499** | 0.9524 | **0.9492** |
| FCBP3R | 9 | 0.0049 | 0.0040 | 0.0039 | 0.0056 | **0.9670** | 0.9690 | **0.9660** |
| FDAP2N | 121 | 0.0107 | 0.0034 | 0.0102 | 0.0108 | **0.9316** | 0.9579 | **0.9345** |
| FDAP2N | 124 | 0.0113 | 0.0036 | 0.0105 | 0.0111 | **0.9290** | 0.9556 | **0.9316** |
| FDAP2R | 128 | 0.0100 | 0.0028 | 0.0096 | 0.0100 | **0.9331** | 0.9579 | **0.9362** |
| FDAP2R | 131 | 0.0103 | 0.0029 | 0.0098 | 0.0102 | **0.9327** | 0.9562 | **0.9339** |
| FDAP3N | 124 | 0.0108 | 0.0047 | 0.0095 | 0.0106 | **0.9345** | 0.9585 | **0.9366** |
| FDAP3N | 127 | 0.0111 | 0.0050 | 0.0098 | 0.0110 | **0.9309** | 0.9559 | **0.9333** |
| FDAP3R | 129 | 0.0102 | 0.0037 | 0.0092 | 0.0099 | **0.9337** | 0.9584 | **0.9376** |
| FDAP3R | 132 | 0.0103 | 0.0039 | 0.0094 | 0.0102 | **0.9327** | 0.9558 | **0.9345** |
| FDBP2N | 28 | 0.0093 | 0.0029 | 0.0090 | 0.0095 | **0.9516** | 0.9671 | **0.9524** |
| FDBP2N | 29 | 0.0098 | 0.0031 | 0.0093 | 0.0098 | **0.9469** | 0.9647 | **0.9493** |
| FDBP2R | 30 | 0.0090 | 0.0027 | 0.0088 | 0.0092 | **0.9493** | 0.9640 | **0.9495** |
| FDBP2R | 29 | 0.0084 | 0.0024 | 0.0083 | 0.0086 | **0.9552** | 0.9682 | **0.9545** |
| FDBP3N | 29 | 0.0091 | 0.0040 | 0.0085 | 0.0094 | **0.9515** | 0.9665 | **0.9526** |
| FDBP3N | 30 | 0.0101 | 0.0046 | 0.0091 | 0.0102 | **0.9462** | 0.9615 | **0.9467** |
| FDBP3R | 30 | 0.0089 | 0.0034 | 0.0084 | 0.0091 | **0.9498** | 0.9648 | **0.9515** |
| FDBP3R | 29 | 0.0084 | 0.0030 | 0.0079 | 0.0085 | **0.9550** | 0.9686 | **0.9558** |

**FOUT, frame by frame** (F141; seeds 1–5 rerun with traces, each delivered fraction identical to
the stored run's): `results/raw/uf_diagnose_outlier.csv`, tabled in F141.
