# U-F2 — the fresh checks after U-F: (G23) with the half-duplex factor, and the every-sender criterion as two labelled statistics

*Registered 2026-11-21, before any run. Mohamed's decisions of 2026-11-21, F (a) and (b)
(`docs/DECISIONS.md`). Model: `docs/revision/unified_closed_form_model.md` §8.1 (G22a), §8.3
(G24), (G24a). Code: `analysis/uf2.py` (the values below are `results/raw/uf2_predictions.csv`,
written by `--predict` and read back by the scorer), `ns3/run_uf2.py`, `authbc.models.capture`
(`half_duplex_factor`, `worst_window_loss`, `z_n`; tests against §8.3's table and a seeded draw).*

## Why

* **U-F failed as registered** (`predictions/UF.md`), and stays failed. Its diagnostics found two
  errors in what was registered, not in ns-3:
  * the capture share omitted that a colliding partner cannot receive (F138);
  * the every-sender statistic was a sample minimum scored against a population quantity (F139).
* **Mohamed's rule (2026-11-20):** a corrected reading is used only after a fresh registered check
  on unseen points. This is that check.

## The configurations (none simulated before: `python analysis/uf2.py --scan` finds no stored row)

* **U-F's channel:**
  * nodes uniform in a disc, every node at 40 dBm;
  * α = 3 with Rayleigh fading per frame (R = 13 m), or α = 2 without fading (R = 73 m);
  * every pair ≥ 32 dB above the −82 dBm floor, so ℓ < 0.1 %;
  * ns-3's own receiver rule (the 4 µs window, θ = 4 dB).
* **Four new cells:** 802.11b 1 Mb/s at 100 B × 12.5 and 100 B × 10 frames/s; 802.11a 6 Mb/s at
  400 B × 100 and 700 B × 50.
* **Each chosen so that the scored (a) root lies at occupancy ≤ 0.78** (Mohamed): (G25) was
  checked there, and past it at 802.11b it is optimistic by 1.2–2.4 % (U-G25H).
  * At 802.11b that needs 46–60 stations, where (G22a)'s factor is 0.98 and moves the root by
    0.2–0.4 %.
  * At 802.11a it allows 11–15 stations, where the factor is 0.90–0.93 and moves the root by
    0.8–1.8 %.
* **Seeds 31–60** for the runs and their placements (U-F used 1–30). Seed 61 is statistic 1's
  fixed placement.

## (a) — (G23) with (G22a): the average criterion, scored ±5 %

* **The root:** (G25)'s root with ε′ = (ε − ℓ̄)/(1 − q̄·(N − 2)/(N − 1)) inside the bisection.
* **q̄ and ℓ̄:** U-F's method, the means over the 30 run seeds' placements at
  N_ref = 1.3 × the no-capture root.
* **Reported only:** without the factor, the Poisson version, and no capture.

| config | PHY | frame, frames/s | α | fading | N_ref | mean q | mean ℓ | **(G23), (G22a), (G25) root** | occupancy there | without the factor | Poisson, with the factor | no capture |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EB100F12.5P3R | 80211b | 100 B, 12.5 | 3 | Rayleigh | 55 | 0.3713 | 0.00008 | **48.31** | 0.773 | 48.48 | 46.45 | 42.22 |
| EB100F12.5P2N | 80211b | 100 B, 12.5 | 2 | none | 55 | 0.2539 | 0.00000 | **46.05** | 0.737 | 46.15 | 44.39 | 42.22 |
| EB100F10P3R | 80211b | 100 B, 10 | 3 | Rayleigh | 68 | 0.3712 | 0.00008 | **59.79** | 0.765 | 59.97 | 57.86 | 52.24 |
| EB100F10P2N | 80211b | 100 B, 10 | 2 | none | 68 | 0.2534 | 0.00000 | **56.98** | 0.729 | 57.08 | 55.25 | 52.24 |
| EA400F100P3R | 80211a | 400 B, 100 | 3 | Rayleigh | 13 | 0.3706 | 0.00007 | **11.93** | 0.726 | 12.15 | 11.04 | 10.31 |
| EA400F100P2N | 80211a | 400 B, 100 | 2 | none | 13 | 0.2537 | 0.00000 | **11.32** | 0.688 | 11.46 | 10.51 | 10.31 |
| EA700F50P3R | 80211a | 700 B, 50 | 3 | Rayleigh | 17 | 0.3699 | 0.00008 | **14.86** | 0.749 | 15.07 | 13.78 | 12.87 |
| EA700F50P2N | 80211a | 700 B, 50 | 2 | none | 17 | 0.2511 | 0.00000 | **14.11** | 0.711 | 14.23 | 13.12 | 12.87 |

* **Scored:** the root against ns-3's crossing of the 30-seed mean delivered fraction at 0.95,
  ±5 %.
* **The runs (`run_uf2.py`):** a pilot of 5 seeds (31–35) at ±5 % steps around the root, then
  30 seeds (31–60) on U-C2's grid around both pilot crossings, the average and the per-run worst
  sender, as U-F did. 20 s runs.

## (b) — the every-sender criterion, two labelled statistics, each scored ±5 %

**Per sender, at N stations on a given placement:**
p_j = p_c(N)·(1 − q_j·(N − 2)/(N − 1)) + ℓ_j (G22, G22a), with p_c from (G25) at N, and q_j, ℓ_j
the sender's means over its receivers.

| config | **(G24a) root, exact** | z_N closed form | frames per window | **(G24) root, fixed placement** | its grid | run length (s) | pooled frames per sender | residual |
|---|---|---|---|---|---|---|---|---|
| EB100F12.5P3R | **39.14** | 40.27 | 250 | **46.34** | 42–50 step 1 | 630 | 236250 | 1.99 % |
| EB100F12.5P2N | **37.24** | 38.23 | 250 | **44.21** | 40–48 step 1 | 620 | 232500 | 1.99 % |
| EB100F10P3R | **46.75** | 48.41 | 200 | **56.97** | 49–65 step 2 | 840 | 252000 | 2.00 % |
| EB100F10P2N | **44.42** | 45.92 | 200 | **54.83** | 47–63 step 2 | 830 | 249000 | 2.00 % |
| EA400F100P3R | **10.84** | 11.26 | 2000 | **11.13** | 7–15 step 1 | 40 | 120000 | 2.00 % |
| EA400F100P2N | **10.33** | 10.68 | 2000 | **10.54** | 7–15 step 1 | 40 | 120000 | 2.00 % |
| EA700F50P3R | **13.32** | 13.70 | 1000 | **13.92** | 10–18 step 1 | 100 | 150000 | 1.92 % |
| EA700F50P2N | **12.69** | 13.02 | 1000 | **13.16** | 9–17 step 1 | 90 | 135000 | 1.98 % |

**Statistic 2, (G24a): the worst sender per 20 s run.**
* **The registered quantity is the left side of (G24a), as §8.3 defines it:**
  * E[max_j p̂_j] with independent L_j ~ Binomial(m, p_j) and m = f × 20 s frames per sender;
  * computed exactly (`worst_window_loss`), at each N averaged over the 30 run seeds' own
    placements;
  * its root, where it reaches ε.
* **The z_N closed form** (`worst_window_loss_normal`) is reported beside it.
* **Measured on (a)'s runs:** the 30-seed mean of each run's worst sender's loss, its crossing
  of ε.
* **p̂_j measured** is the sender's loss averaged over its receivers, as U-F measured it.
* **Stated with the prediction:**
  * **independence:** shared collisions correlate the senders' losses positively, which makes the
    maximum smaller than the binomial model's;
  * **capture:** it spreads a frame's loss over receivers, so a receiver-averaged loss is less
    noisy than Binomial(m, p_j);
  * **both lean the prediction conservative.** It is registered as written, not adjusted.

**Statistic 1, (G24) with (G22a): each sender's pooled rate.**
* **One fixed placement per node count,** seed 61's (`--placementOnly`, then `--positionsFile`
  in every run).
* **30 run seeds (31–60),** each of the run length in the table.
* **Measured:** each sender's delivery pooled over all 30 runs (frames-weighted), and the worst
  pooled sender's crossing of 0.95 on the registered grid.
* **Predicted:** the long-run worst sender max_j p_j of the same placements, its crossing of ε.
* **The residual noise, stated before any run:**
  * the worst of N pooled senders still reads below the long-run worst, moving the crossing by
    about z_N·√((1 − ε)/(ε M)) of N, M the pooled frames per sender;
  * each run length was chosen to bring this to 2 %, two fifths of the tolerance, in the
    optimistic-looking direction (the model above ns-3);
  * it is an upper bound, since capture makes the per-sender count less noisy than binomial.
* **A crossing outside the registered grid** is reported as a bound and scored failed, as in U-F.

## What is reported beside the scores

* The (G25), Poisson and no-capture errors.
* The measured q̂ where the stored no-capture runs allow it (U-F's method).

## My expectations `[agent]`

* **(a) holds at all eight**, conservative at 802.11a by 1–2 % (U-F's 802.11a errors were
  −0.3 … −1.7 % without the factor, which moves the root down a further 1–2 %).
* **Statistic 2 holds, or misses conservative:** the binomial independence model overstates the
  maximum.
* **Statistic 1 holds,** with the model above ns-3 by about the stated residual.

## Disclosure

* **Known before this registration:**
  * U-F's outcome and its diagnostics, F138–F141;
  * U-G25 and U-G25H;
  * the smoke runs of `--positionsFile` (`ns3/check_twin_options.py`, 2 s at N = 3);
  * one timing run per PHY (N = 47 at 802.11b, N = 12 at 802.11a, seed 99, 50 s), with no result
    kept.
* **No run of any registered configuration has been made.**
