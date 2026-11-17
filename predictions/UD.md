# U-D — the 802.11b arm: the unified model at the hardware's own PHY (D1, D2, D3)

*Registered 2026-11-17, before any U-D run; the time is the commit's. Task of 2026-11-17, work
package D. The model is in `docs/revision/2026-11-17_unified_model_spec.md`
(`src/authbc/models/unified_capacity.py`), with 802.11b's constants:
* σ = 20 µs, DIFS = 50 µs, W = 32, δ = 4 µs;
* T_f = 192 µs + 8(ℓ + 36) µs at 1 Mb/s, long preamble.

These were read back from ns-3's live objects (audit item 7). This file covers D1–D3, in the
**standard 802.11b** configuration. D4, the hardware-matched configuration, waits on Mohamed for
the parameters the campaign has not measured.*

## Method (all three)

* **The runs.** `ns3/run_unified.py` through the audit twin: `--standard=80211b
  --dataMode=DsssRate1Mbps`, the designated source, 20 simulated seconds.
* **The crossing.** A pilot of 5 seeds on a coarse grid, then 30 seeds on seven node counts. The
  crossing of the mean delivered fraction is found by straight-line interpolation, with its
  bootstrap interval over seeds.

**Tolerance, fixed now and not widened after:**
* where ns-3's crossing is **15 stations or more**: the law, and separately the root, within
  **±5 %**;
* from **8 to 14 stations**: within **−9 % … +5 %**. The author states that Poisson starts
  underestimate capacity by 7–9 % for swarms of about 8–14 stations;
* **below 8 stations**, where the author states no limit: reported, **not scored**.

## D1 — the base and design frames at three loss targets and three windows

Pb1B is 146 B at 50 frames/s, and Pb1D is 173 B at 12.5 frames/s. Windows of 16 and 8 are set
with `--cwMin` (CWmin = W − 1).

| cell | W | ε = 2 %: law / root | ε = 5 % | ε = 10 % |
|---|---|---|---|---|
| Pb1B | 32 | 6.82 / 6.83 | 8.92 / 8.95 | 10.60 / 10.63 |
| Pb1B | 16 | 5.81 / 5.80 | 7.83 / 7.83 | 9.61 / 9.62 |
| Pb1B | 8 | 4.81 / 4.80 | 6.62 / 6.62 | 8.39 / 8.39 |
| Pb1D | 32 | 21.91 / 21.94 | 29.34 / 29.43 | 35.26 / 35.35 |
| Pb1D | 16 | 18.20 / 18.19 | 25.37 / 25.38 | 31.67 / 31.69 |
| Pb1D | 8 | 14.58 / 14.57 | 21.03 / 21.03 | 27.28 / 27.28 |

* The three loss targets are read from the same curves (levels 0.98, 0.95 and 0.90), so each
  window's grid must bracket all three.
* At W = 32 and ε = 5 % the stored W1b crossings exist (Pb1B 9.72, Pb1D 31.05). They are run
  again here on the twin's grid, not re-used, so that one file holds every point.
* **Expected (from the Poisson finding of work package A):** the model 5–9 % below ns-3
  throughout; more at Pb1B, which has the fewest stations.

## D2 — the batch sweep at 10 records/s

ℓ(b) = 137 + 9b and f = 10/b. The design law: N_inf = 1 009.2 and β = 24.48. At 802.11b the PHY
airtime is exactly affine in ℓ, so the design law equals the law.

| b | frame | f | T_f | law | root |
|---|---|---|---|---|---|
| 1 | 146 B | 10 | 1 648 µs | 40.60 | 40.74 |
| 2 | 155 B | 5 | 1 720 µs | 77.21 | 77.47 |
| 4 | 173 B | 2.5 | 1 864 µs | 142.72 | 143.14 |
| 8 | 209 B | 1.25 | 2 152 µs | 249.54 | 250.11 |
| 16 | 281 B | 0.625 | 2 728 µs | 399.85 | 400.46 |
| 32 | 425 B | 0.3125 | 3 880 µs | 572.74 | 573.21 |

These are the author's values to the digit. **Also reported:** the gain law against ns-3's
measured gain, (N(b) − 1)/(N(1) − 1).

## D3 — the three loss terms at 1 Mb/s (U-C1 repeated)

* **Rules.** U-C1's classification, quantities and tolerance, unchanged (`predictions/UC1.md`).
* **Loads.** Pb1B and Pb1D at the root's 1, 2, 5 and 10 % loads, with 10 seeds each and
  `--traceMac`.

| cell | N | tie | zero backoff after busy | detection window | p | a | K |
|---|---|---|---|---|---|---|---|
| Pb1B | 5 | 0.00564 | 0.00030 | 0.00212 | 0.00807 | 0.3275 | 0.5605 |
| Pb1B | 7 | 0.01733 | 0.00068 | 0.00357 | 0.02158 | 0.4879 | 1.1787 |
| Pb1B | 9 | 0.04463 | 0.00120 | 0.00525 | 0.05108 | 0.6408 | 2.3955 |
| Pb1B | 11 | 0.10730 | 0.00183 | 0.00710 | 0.11623 | 0.7742 | 5.1482 |
| Pb1D | 17 | 0.00767 | 0.00033 | 0.00219 | 0.01019 | 0.3701 | 0.6770 |
| Pb1D | 22 | 0.01647 | 0.00057 | 0.00311 | 0.02015 | 0.4833 | 1.1287 |
| Pb1D | 29 | 0.04194 | 0.00100 | 0.00458 | 0.04752 | 0.6355 | 2.2612 |
| Pb1D | 35 | 0.08866 | 0.00145 | 0.00596 | 0.09607 | 0.7525 | 4.2737 |

## Disclosure

**Known before this registration:**
* the stored W1b crossings (Pb1B 9.72, Pb1D 31.05);
* work package A's finding: periodic event models within 0.4 % of ns-3 at both cells, and Poisson
  rule A 6.9–17.5 % below;
* the audit's single traces at Pb1B (N = 10) and Pb1D (N = 31), seed 1: collisions 281 and 196,
  of which 252 and 104 had all starts at one instant.

**No U-D run has been made.**


---

## Outcome — added 2026-11-17, after the runs; nothing above this line was changed

**The runs.** All went through the audit twin, rebuilt at 20:32 with the options for C3–C5, all
off by default. Its gate passed 9 / 9 identical at 20:39, before the first U-D run at 20:45.
* **D3:** 80 traced runs, 10 seeds at each registered load (`results/raw/unified_d3{,_runs}.csv`).
* **Pilots, 5 seeds:**
  * D1: Pb1B at N = 4 … 13 and Pb1D at N = 12 … 42, at all three windows
    (`unified_d1_pilot_{b,d}`);
  * D2: ±15 % around the law (`unified_d2_pilot_b*`).
* **Then 30 seeds at seven node counts,** 2 520 runs in all (`unified_d1`, `unified_d2_b*`):
  * D1: each grid brackets that cell's three pilot crossings;
  * D2: U-C2's rule, centred on the rounded pilot crossing, in steps of 2 % of it.

**Checked before scoring.** An independent script on the raw counts reproduces all 24 crossings to
the digit:
* every node count has seeds 1–30;
* each delivered fraction equals rx / (tx (N − 1));
* every mean curve falls monotonically and crosses each level once.

**Scored** by `analysis/unified_d.py` → `results/raw/unified_d_scored.csv`. Its model values
equal the tables above (`tests/test_unified_d.py`). D3 is scored by `analysis/unified_c1.py`,
with U-C1's rules unchanged → `results/raw/unified_d3_scored.csv`.

**Scored, in sum:**

| | held | failed | not scored |
|---|---|---|---|
| D1 Pb1B (8–14 stations: −9 … +5 %) | **10** | 0 | 8 (four crossings below 8 stations) |
| D1 Pb1D (15–37 stations: ±5 %) | **1** | **17** | — |
| D2, b = 1 … 32 (42–600 stations: ±5 %) | **12** | 0 | — |
| D3, the three terms, p, a and K | **18** | **30** | — |

### D1 — three loss targets × three windows

| cell | W | ε | ns-3 (95 % CI) | band | law | error | held | root | error | held |
|---|---|---|---|---|---|---|---|---|---|---|
| Pb1B | 32 | 2 % | 7.558 (7.486–7.647) | none (< 8) | 6.82 | −9.74 % | not scored | 6.83 | −9.61 % | not scored |
| Pb1B | 32 | 5 % | 9.718 (9.678–9.76) | −9 … +5 % | 8.92 | −8.21 % | yes | 8.95 | −7.91 % | yes |
| Pb1B | 32 | 10 % | 11.158 (11.141–11.174) | −9 … +5 % | 10.60 | −5.03 % | yes | 10.63 | −4.75 % | yes |
| Pb1B | 16 | 2 % | 6.414 (6.352–6.476) | none (< 8) | 5.81 | −9.44 % | not scored | 5.80 | −9.53 % | not scored |
| Pb1B | 16 | 5 % | 8.567 (8.527–8.609) | −9 … +5 % | 7.83 | −8.61 % | yes | 7.83 | −8.57 % | yes |
| Pb1B | 16 | 10 % | 10.429 (10.406–10.452) | −9 … +5 % | 9.61 | −7.89 % | yes | 9.62 | −7.80 % | yes |
| Pb1B | 8 | 2 % | 5.382 (5.321–5.444) | none (< 8) | 4.81 | −10.69 % | not scored | 4.80 | −10.79 % | not scored |
| Pb1B | 8 | 5 % | 7.313 (7.269–7.353) | none (< 8) | 6.62 | −9.42 % | not scored | 6.62 | −9.45 % | not scored |
| Pb1B | 8 | 10 % | 9.204 (9.159–9.246) | −9 … +5 % | 8.39 | −8.90 % | yes | 8.39 | −8.89 % | yes |
| Pb1D | 32 | 2 % | 23.089 (22.86–23.336) | −5 … +5 % | 21.91 | −5.10 % | **no** | 21.94 | −4.97 % | yes |
| Pb1D | 32 | 5 % | 31.031 (30.896–31.177) | −5 … +5 % | 29.34 | −5.43 % | **no** | 29.43 | −5.17 % | **no** |
| Pb1D | 32 | 10 % | 37.32 (37.224–37.408) | −5 … +5 % | 35.26 | −5.53 % | **no** | 35.35 | −5.29 % | **no** |
| Pb1D | 16 | 2 % | 19.26 (18.985–19.567) | −5 … +5 % | 18.20 | −5.49 % | **no** | 18.19 | −5.57 % | **no** |
| Pb1D | 16 | 5 % | 26.728 (26.476–27.003) | −5 … +5 % | 25.37 | −5.08 % | **no** | 25.38 | −5.04 % | **no** |
| Pb1D | 16 | 10 % | 33.667 (33.558–33.779) | −5 … +5 % | 31.67 | −5.94 % | **no** | 31.69 | −5.86 % | **no** |
| Pb1D | 8 | 2 % | 15.553 (15.29–15.802) | −5 … +5 % | 14.58 | −6.25 % | **no** | 14.57 | −6.34 % | **no** |
| Pb1D | 8 | 5 % | 22.278 (22.066–22.515) | −5 … +5 % | 21.03 | −5.59 % | **no** | 21.03 | −5.62 % | **no** |
| Pb1D | 8 | 10 % | 29.099 (28.971–29.213) | −5 … +5 % | 27.28 | −6.26 % | **no** | 27.28 | −6.25 % | **no** |

* **Pb1D fails: 17 of 18.** The law lies 5.08–6.26 % below ns-3 at all nine crossings, and the
  root 4.97–6.34 %. The one pass is the root at W = 32, ε = 2 %, by 0.03 points.
* **Pb1B holds wherever it is scored**, 10 of 10, at −4.75 … −8.90 %. Its four crossings below 8
  stations lie −9.42 … −10.79 %.
* **The model lies below ns-3 at all 18 crossings, and more where the swarm is smaller.**

### D2 — the batch sweep at 10 records/s

| b | frame | ns-3 (95 % CI) | law | error | root | error | held |
|---|---|---|---|---|---|---|---|
| 1 | 146 B | 42.629 (42.453–42.812) | 40.60 | −4.76 % | 40.74 | −4.42 % | yes, yes |
| 2 | 155 B | 79.79 (79.396–80.307) | 77.21 | −3.23 % | 77.47 | −2.91 % | yes, yes |
| 4 | 173 B | 147.657 (146.607–148.428) | 142.72 | −3.34 % | 143.14 | −3.06 % | yes, yes |
| 8 | 209 B | 257.261 (255.266–258.363) | 249.54 | −3.00 % | 250.11 | −2.78 % | yes, yes |
| 16 | 281 B | 412.462 (409.324–415.933) | 399.85 | −3.06 % | 400.46 | −2.91 % | yes, yes |
| 32 | 425 B | 599.31 (586.78–604.118) | 572.74 | −4.43 % | 573.21 | −4.36 % | yes, yes |

**Held: 12 of 12.** Reported, not scored: the gain (N(b) − 1)/(N(1) − 1), against the design law's
b(1 + β)/(b + β), with β = 24.48:

| b | 1 | 2 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| ns-3 | 1.000 | 1.893 | 3.523 | 6.156 | 9.884 | 14.372 |
| design law | 1.000 | 1.924 | 3.579 | 6.276 | 10.072 | 14.437 |
| law − ns-3 | +0.00 % | +1.68 % | +1.58 % | +1.95 % | +1.90 % | +0.45 % |

The gain bends away from b, as the law says: 32 records to a frame buy 14.4 times the one-record
capacity. The design law tracks ns-3's gain within 2 % at every b.

### D3 — the three loss terms at 1 Mb/s (U-C1's rules)

**Held: 18 of 48.**

| quantity | held | prediction against ns-3 |
|---|---|---|
| **a**, the share arriving to a busy medium | **8 / 8** | −7.6 … +0.2 % |
| zero-backoff start after a busy period | 5 / 8 | −90 … +75 % |
| detection window | 5 / 8 | −84 … +9 % |
| tie | 0 / 8 | +19 … +138 % |
| **p**, the total loss | 0 / 8 | +14 … +44 % |
| K | 0 / 8 | +46 … +156 % |

**Reported, not scored** (`unified_c1.py --diagnose` → `results/raw/unified_d3_diagnostic.csv`):
* **Counting every all-drew collision as a tie, at any spread,** the tie term is still +13 … +71 %
  above ns-3's, against +3 … +18 % at 802.11a (U-C1).
* **At Pb1B no all-drew collision has any spread.** Why is not established.
* **p's excess at a fixed N is the capacity offset seen on a steep curve.** ns-3 reaches the
  expression's p at 4.2–8.6 % more stations, by straight-line interpolation between the measured
  loads, at the six loads where it is bracketed.

### What it means

* **At 802.11b the model is pessimistic at every one of the 24 crossings,** by −2.78 … −10.79 %.
  By group, law and root together:
  * −4.75 … −10.79 % at 5–11 stations (Pb1B);
  * −4.97 … −6.34 % at 15–37 (Pb1D);
  * −2.78 … −4.76 % at 42–600 (D2).

  The smallest swarms err most. Within a cell the error is not monotone in N: Pb1B at W = 32
  goes −9.7, −8.2, −5.0 % from 7.6 to 11.2 stations, while Pb1D at W = 32 goes −5.1, −5.4,
  −5.5 % from 23 to 37.
* **The registered band for 15 stations and more (±5 %) is too narrow at 802.11b, at 15–37
  stations.** There the model misses by 0.04–1.34 points beyond the band. This is not a bug I can
  show:
  * the model values equal the registration;
  * the crossings reproduce from the raw counts;
  * the twin is the published scenario at its defaults.
* **The evidence points to the Poisson assumption,** as in work package A.
  * At Pb1D (stored crossing 31.05), event models with ns-3's periodic sources give 30.94 and
    31.10. With Poisson starts they give 28.90, and the expression's root gives 29.43.
  * The author's statement (Poisson starts underestimate by 7–9 % at 8–14 stations) holds at
    Pb1B. At 802.11b the shortfall persists past 15 stations, at 5–6 %.
* **The tolerance is not widened.** Whether the band, or the model, should change is Mohamed's
  decision.

**Expectations.** "The model 5–9 % below ns-3 throughout; more at Pb1B, which has the fewest
stations" (D1):
* the direction and the ordering held;
* the law lies within 5–9 % at 14 of 18 crossings. The four outside are the unscored ones below
  8 stations, at −9.42 … −10.69 %.

**Decision (Mohamed, 2026-11-18), added below the outcome.** The Pb1D result is recorded as
failed, on the conservative side. The tolerance is not widened and the model is not changed. A
finite-station, periodic-source loss expression is open item U1 (`docs/OPEN_ITEMS.md`). It is
not started and waits for his go-ahead after C3–C5.
