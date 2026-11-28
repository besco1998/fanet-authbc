# U-D2 — (G25) where U-D's Poisson model failed: 802.11b at windows 8, 16 and 32, loss targets 2, 5 and 10 %

*Registered 2026-11-28, before any U-D2 run; the time is the commit's. Decided by Mohamed on
2026-11-28 (`docs/DECISIONS.md`, "fixing the model report's three open issues", issue 3). Code:
`analysis/ud2.py` (`tests/test_ud2.py`); cells in `ns3/run_unified.py`, imported from it.*

## Why

* **U-D (2026-11-17)** tested the Poisson model at the hardware's PHY, 802.11b at 1 Mb/s. At 15–37
  stations the root of (G5) lay 4.97–6.34 % below ns-3 and failed its ±5 % band at 8 of 9 cells
  (`predictions/UD.md`). **U-D stays failed as registered.**
* **The cause** was the Poisson assumption: ns-3's telemetry source is periodic. (G25) was written
  for it and registered on new cells in **U-G25**, where it held at all 16.
* **What U-G25 did not cover:** at 802.11b it tested only W = 32 and ε = 2 and 5 %. U-D failed at
  W = 8 and 16 as well, and at ε = 10 %. U-D2 tests (G25) there, on new cells.

## The model under test

(G25), `authbc.models.periodic_capacity.n_root_periodic`, unchanged since U-G25. Its stated limit
is 8 or more other stations; every root below is at 14 or more. The Poisson root of (G5) is
reported beside it.

## The cells (new)

| PHY | constants | frames | frames/s | windows |
|---|---|---|---|---|
| 802.11b, 1 Mb/s, long preamble | slot 20 µs, DIFS 50 µs, δ 4 µs | 200 B (2 080 µs), 320 B (3 040 µs) | 10, 8 | W = 8, 16, 32 (`--cwMin` = W − 1) |

* **Six cells,** each crossed at three targets: 18 predictions.
* **New:** `python analysis/ud2.py --scan` finds no stored CSV row at either (bytes, frames/s),
  and the driver's cell list held neither before this commit.
* **The roots fall at 15–42 stations,** U-D's range and a little above.

## Predictions (`python analysis/ud2.py --markdown`, generated)

| cell | frame | frames/s | W | T_f (µs) | ε | **(G25) root** | Poisson root | u at the root |
|---|---|---|---|---|---|---|---|---|
| QB200F10W8 | 200 B | 10 | 8 | 2080 | 0.02 | **16.93** | 16.31 | 0.35 |
| QB200F10W8 | 200 B | 10 | 8 | 2080 | 0.05 | **24.44** | 23.56 | 0.51 |
| QB200F10W8 | 200 B | 10 | 8 | 2080 | 0.1 | **31.81** | 30.58 | 0.66 |
| QB200F10W16 | 200 B | 10 | 16 | 2080 | 0.02 | **21.18** | 20.43 | 0.44 |
| QB200F10W16 | 200 B | 10 | 16 | 2080 | 0.05 | **29.64** | 28.51 | 0.62 |
| QB200F10W16 | 200 B | 10 | 16 | 2080 | 0.1 | **37.27** | 35.59 | 0.78 |
| QB200F10W32 | 200 B | 10 | 32 | 2080 | 0.02 | **25.65** | 24.75 | 0.53 |
| QB200F10W32 | 200 B | 10 | 32 | 2080 | 0.05 | **34.61** | 33.13 | 0.72 |
| QB200F10W32 | 200 B | 10 | 32 | 2080 | 0.1 | **42.03** | 39.75 | 0.87 (past 0.78) |
| QB320F8W8 | 320 B | 8 | 8 | 3040 | 0.02 | **14.98** | 14.36 | 0.36 |
| QB320F8W8 | 320 B | 8 | 8 | 3040 | 0.05 | **21.48** | 20.60 | 0.52 |
| QB320F8W8 | 320 B | 8 | 8 | 3040 | 0.1 | **27.87** | 26.65 | 0.68 |
| QB320F8W16 | 320 B | 8 | 16 | 3040 | 0.02 | **18.82** | 18.06 | 0.46 |
| QB320F8W16 | 320 B | 8 | 16 | 3040 | 0.05 | **26.15** | 25.00 | 0.64 |
| QB320F8W16 | 320 B | 8 | 16 | 3040 | 0.1 | **32.76** | 31.07 | 0.80 (past 0.78) |
| QB320F8W32 | 320 B | 8 | 32 | 3040 | 0.02 | **22.96** | 22.02 | 0.56 |
| QB320F8W32 | 320 B | 8 | 32 | 3040 | 0.05 | **30.71** | 29.18 | 0.75 |
| QB320F8W32 | 320 B | 8 | 32 | 3040 | 0.1 | **37.13** | 34.80 | 0.90 (past 0.78) |

**Scored:**
* the (G25) root holds if it is within **±5 %** of ns-3's crossing: |root − ns-3| / ns-3 ≤ 0.05;
* 18 predictions, each scored on its own;
* the tolerance is fixed here and is not widened after the runs.

**Three crossings lie past (G25)'s stated range at 802.11b,** occupancy 0.78 (U-G25H): the
ε = 0.10 roots of QB200F10W32 (0.87), QB320F8W16 (0.80) and QB320F8W32 (0.90).
* They are scored at ±5 % like the others and labelled *past the stated range* in the scored file.
* U-G25H measured (G25) there +1.16 to +2.41 % optimistic, inside the band. A pass there is
  reported as such; it does not by itself move the stated range.

**Reported, not scored:**
* the Poisson root's error at each crossing;
* each failure with its side: *conservative* (the root below ns-3) or *optimistic* (above).

A failure is explained with evidence, or raised with Mohamed. No fit is made.

## What is run

U-D's scenario and source; the grids by U-G25's rule, per target, which is finer than U-D's single
seven-count grid per cell (driver: `ns3/run_uj_ud2.py ud2`, up to about 4 300 runs):
* **The scenario:** the audit twin, gated bit-identical (`ns3/verify_audit_twin.py`, run on
  2026-11-28 before any run).
* **The source:** the designated one (jitter of one period); 20 simulated seconds.
* **The pilot:** 5 seeds (1–5) on the union of seven-count grids at ±5 % steps around each of the
  cell's three (G25) roots.
* **The measurement:** 30 seeds (1–30) on node counts by U-C2's rule, each target's seven
  counts around its pilot crossing:
  * the centre is the pilot crossing rounded;
  * the step is max(1, round(2 % of the centre));
  * a count shared by two targets is run once.
* **The crossings** of the 30-seed mean delivered fraction at 0.98, 0.95 and 0.90, with bootstrap
  95 % intervals over seeds (`ns3/run_unified.py --levels 0.98 0.95 0.9`).
* **Checked before scoring:**
  * every node count has seeds 1–30;
  * every mean curve crosses each level once.
* **Scoring:** `analysis/ud2.py --score` → `results/raw/ud2_scored.csv`. An independent script,
  sharing no project code, recomputes every crossing from the runs files.

## Expectations `[agent]`

* **(G25) holds at most of the 18, on either side, within a few percent.**
  * U-G25 at 802.11b, W = 32: −1.9 to +0.3 %.
  * The model document's consistency check of U-D's own cells at W = 8 and 32 (not a test):
    −1.3 to +1.7 %.
* **The Poisson root lies 4–6 % below ns-3,** as in U-D.
* **The likeliest failures:**
  * at ε = 0.02 with W = 8, the smallest swarms (15–17 stations), nearest the (G25) limit;
  * at the three crossings past occupancy 0.78, on the optimistic side, where U-G25H found (G25)
    optimistic.

## Disclosure

* **Seen before this registration:**
  * U-D's results and the model document's §10.1 check of (G25) on them;
  * U-G25 and U-G25H.
* **The cells were chosen** by computing (G25)'s roots to fall in U-D's range. No ns-3 run at
  them exists.
* **None of U-D2's runs has been made.**

## Outcome — added 2026-11-28, after the runs; nothing above this line was changed

* **The runs:** `ns3/run_uj_ud2.py ud2`, through the audit twin (gate 9/9 identical on
  2026-11-28): 550 pilot runs and 3 720 measurement runs (`results/raw/ud2_*`). Every measured
  node count has seeds 1–30; every 30-seed mean curve crosses each level once.
* **Scored** with `python analysis/ud2.py --score` → `results/raw/ud2_scored.csv`.

**Scored: 18 of 18 held.** (G25)'s error lies between −3.16 and +0.56 %, at every window
(8, 16, 32) and every target (2, 5, 10 %).

| cell | W | ε | ns-3 crossing (95 % interval) | (G25) root | error | held | Poisson error |
|---|---|---|---|---|---|---|---|
| QB200F10W16 | 16 | 0.02 | 21.616 (21.328–22.082) | 21.18 | -2.03 % | yes | -5.47 % |
| QB200F10W16 | 16 | 0.05 | 30.097 (29.846–30.277) | 29.64 | -1.51 % | yes | -5.28 % |
| QB200F10W16 | 16 | 0.1 | 37.847 (37.686–38.046) | 37.27 | -1.52 % | yes | -5.97 % |
| QB200F10W32 | 32 | 0.02 | 25.661 (25.440–25.976) | 25.65 | -0.06 % | yes | -3.55 % |
| QB200F10W32 | 32 | 0.05 | 34.832 (34.640–35.065) | 34.61 | -0.63 % | yes | -4.88 % |
| QB200F10W32 | 32 | 0.1 | 42.160 (42.074–42.235) | 42.03 | -0.30 % (past 0.78) | yes | -5.72 % |
| QB200F10W8 | 8 | 0.02 | 17.296 (17.113–17.442) | 16.93 | -2.13 % | yes | -5.71 % |
| QB200F10W8 | 8 | 0.05 | 24.817 (24.624–25.070) | 24.44 | -1.54 % | yes | -5.06 % |
| QB200F10W8 | 8 | 0.1 | 32.637 (32.460–32.814) | 31.81 | -2.53 % | yes | -6.29 % |
| QB320F8W16 | 16 | 0.02 | 18.825 (18.366–19.310) | 18.82 | -0.03 % | yes | -4.07 % |
| QB320F8W16 | 16 | 0.05 | 26.680 (26.498–26.883) | 26.15 | -2.00 % | yes | -6.31 % |
| QB320F8W16 | 16 | 0.1 | 33.261 (33.073–33.408) | 32.76 | -1.51 % (past 0.78) | yes | -6.60 % |
| QB320F8W32 | 32 | 0.02 | 23.213 (22.819–23.452) | 22.96 | -1.07 % | yes | -5.13 % |
| QB320F8W32 | 32 | 0.05 | 31.073 (30.824–31.256) | 30.71 | -1.16 % | yes | -6.08 % |
| QB320F8W32 | 32 | 0.1 | 36.920 (36.809–37.076) | 37.13 | +0.56 % (past 0.78) | yes | -5.75 % |
| QB320F8W8 | 8 | 0.02 | 15.471 (15.156–15.729) | 14.98 | -3.16 % | yes | -7.20 % |
| QB320F8W8 | 8 | 0.05 | 21.787 (21.600–22.061) | 21.48 | -1.42 % | yes | -5.44 % |
| QB320F8W8 | 8 | 0.1 | 28.596 (28.406–28.807) | 27.87 | -2.55 % | yes | -6.82 % |

* **The three crossings past occupancy 0.78 held** (−0.30, −1.51, +0.56 %), labelled as
  registered. By the registration, a pass there does not by itself move (G25)'s stated range.
* **The Poisson root of (G5), reported:** −3.55 to −7.20 %, outside ±5 % at 15 of 18. It repeats
  U-D's failure on new cells, on the same (safe) side.
* **U-D stays failed as registered;** U-D2 shows that (G25), the correction written for its cause,
  holds where U-D failed.

### The independent check

A separate script, sharing no project code, read the six runs files and recomputed all 18
crossings: each equals the scored one to three decimals, and each mean curve crosses its level
once.

### My expectations, against the outcome

* **"(G25) holds at most of the 18, within a few percent":** it held at all 18, within 3.2 %.
* **"The Poisson root lies 4–6 % below ns-3":** 3.6–7.2 %, close.
* **"The likeliest failures: ε = 0.02 at W = 8, and past 0.78 on the optimistic side":** none
  failed. The largest error is at ε = 0.02, W = 8 (QB320F8W8, −3.16 %), as expected in place
  though not in size. Past 0.78 one of three is optimistic (+0.56 %).
