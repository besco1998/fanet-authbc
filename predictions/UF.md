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
