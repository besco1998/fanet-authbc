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
