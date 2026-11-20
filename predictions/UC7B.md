# U-C7B — one new 10 % cell that Class A timing cannot hold back; and per-node loss for C7

*Registered 2026-11-20, before any U-C7B run and before any per-node count of any C7 cell; the
time is the commit's.*

*Mohamed (2026-11-20), after U-C7: "(a) d = 10 % with 20 B is recorded as not applicable: the
Class A receive windows prevent the duty limit. Register one new 10 % cell whose period T/d exceeds
2.5 s (larger payload or higher spreading factor) and run it. (b) The two 1 % failures stay failed
as registered; report their bootstrap intervals. (c) Report the per-node loss distribution and the
worst node for every cell, and state whether loss is bimodal under frozen phases. If it is, that is
a finding for the ledger's every-sender criterion."*

## Part 1 — the new cell (scored)

**The cell `D10C8L120SF8`:**
* d = 10 %, C = 8 channels;
* a 120 B payload at **SF8** (DR4), on air for 379.392 ms (the module's own `durations.txt`);
* a period of ToA/d = **3.794 s**. After its frame, a node waits 3.41 s on average, past RX2 (2 s)
  and its short window;
* everything else as U-C7 (`predictions/UC7.md`):
  * a one-sided jitter of 2·ToA, so d_eff = d/(1 + d) = 0.090909;
  * the `aloha` matrix (no capture), one SF, no network server, a gateway on all 8 channels;
  * 60 mean intervals per node.
* **Never run:** no earlier cell used SF8 or 120 B.

**The prediction:**
* N* = 1 + 8·ln(1/0.95)/(2·0.090909) = **3.257**, so **N_max = 3**;
* the per-frame loss, 1 − exp(−2(N − 1)d_eff/C), is 0.0444 at N = 3 and 0.0659 at N = 4.

**The run:** N = 2 … 7, seeds 1–30 (`ns3/run_c7.py --cell D10C8L120SF8 --per-node`).

**Scored as U-C7's cells with 2 ≤ N* < 5,** fixed now:
* **held if** the 30-seed mean delivery is at least 0.95 at N = 3 and below 0.95 at N = 4;
* **the cell counts as run at its limit only if the measured duty**, sent × ToA/(N × run
  length), **is at least 0.089 in every run.** Otherwise it is recorded as not applicable, as the
  20 B cells were;
* a failure is reported with its side and its bootstrap interval over seeds.

## Part 2 — per-node loss in every C7 cell (reported, not scored)

**The runs:** every cell of U-C7 is run again on its own 30-seed grid (the same node counts and
seeds), with per-device counts (`--per-node`, rows in `results/raw/uc7_<cell>_pn_{runs,nodes}.csv`),
plus the new cell.
* The twin's per-node accounting is trace sinks only. **Every rerun must reproduce its stored
  totals exactly**, checked run by run. If any differs, stop.

**The measure,** fixed before any count:
* **per-node loss** = 1 − received/sent for one device in one run;
* for each cell, at the grid node count nearest N* (for N* < 2, at N = 2), over all devices and
  seeds:
  * the mean, median, 90th percentile and maximum;
  * **the worst node:** the largest per-node loss and its seed;
  * **the share of node-runs with zero loss** and the share with more than twice the mean;
  * **Sarle's bimodality coefficient** BC = (g² + 1)/(κ + 3(n − 1)²/((n − 2)(n − 3))), with g
    the skewness and κ the excess kurtosis. BC > 5/9 is read as bimodal;
* **"bimodal under frozen phases"** is stated if BC > 5/9 and at least 25 % of node-runs lose
  nothing. In that case the every-sender criterion (G24) is the relevant one, and the worst node,
  not the mean, decides.

## Expectations `[agent]`

* **Part 1 holds.** The same formula held at D10C8L200 (N_max 3, crossing 3.36), with a period of
  3.33 s. SF and length should not matter in the module, which scales exactly in time.
* **Part 2: per-node loss is bimodal at the small-N, low-duty cells** (d = 1 %, C = 1 and 3),
  where phases freeze for a whole run. It is not bimodal at d = 0.1 % with many nodes, where each
  node meets many others.

## Disclosure

* **Known before this registration:** U-C7's outcome, totals only (`predictions/UC7.md`), and the
  per-node accounting's check on two stored runs (totals reproduced, per-node sums equal).
* **No per-node count of any C7 cell has been looked at, and no SF8 run has been made.**


---

## Outcome — added 2026-11-20, after the runs; nothing above this line was changed

**The runs.** `ns3/run_uc7b.py` (in the repo; the first orchestration copies were lost in a
restart, after their results were committed):
* the new cell at N = 2 … 7, seeds 1–30;
* every U-C7 cell again on its stored 30-seed grid, with `--per-node`
  (`results/raw/uc7_<cell>_pn_{runs,nodes}.csv`).

**The identity check held:** every rerun reproduced its stored totals, sent and received, run by
run (0 differences in 18 cells).

### Part 1 — the new cell: held

* **The duty used,** 0.0899–0.0924 in every run, so the cell ran at its limit (≥ 0.089). No
  gateway transmission.
* **The 30-seed mean delivery:** 0.9734 / **0.9595** / **0.9333** / 0.9203 / 0.8864 / 0.8796 at
  N = 2 … 7. **N_max = 3, as predicted.**
* The crossing is 3.363 (bootstrap 3.024–3.670), against N* = 3.257.
* **Seen after scoring:** the cell reproduces D10C8L200 (SF7, 200 B) to the last digit, per node
  included. Both run past the Class A windows, and every time in them scales by one factor. In
  this module, SF and length cannot change the result once the duty limit is kept.

### Part 2 — per-node loss in every C7 cell (reported)

At the grid node count nearest N* (N = 2 where N* < 2), over all devices and seeds
(`analysis/uc7.py --per-node` → `results/raw/uc7_per_node.csv`):

| cell | N | node-runs | mean loss | median | 90th pct | **worst node** (seed, node) | share at zero | BC | bimodal |
|---|---|---|---|---|---|---|---|---|---|
| D0.1C1L20 | 27 | 810 | 0.0516 | 0.0000 | 0.2000 | **0.7167** (4, 17) | 0.74 | 0.796 | **yes** |
| D0.1C1L200 | 27 | 810 | 0.0516 | 0.0000 | 0.2000 | **0.7167** (4, 17) | 0.74 | 0.796 | **yes** |
| D0.1C3L20 | 76 | 2280 | 0.0507 | 0.0167 | 0.1667 | **0.4667** (2, 7) | 0.48 | 0.660 | **yes** |
| D0.1C3L200 | 76 | 2280 | 0.0507 | 0.0167 | 0.1667 | **0.4667** (2, 7) | 0.48 | 0.660 | **yes** |
| D0.1C8L20 | 206 | 6180 | 0.0497 | 0.0333 | 0.1167 | **0.3667** (25, 38) | 0.23 | 0.501 | no |
| D0.1C8L200 | 206 | 6180 | 0.0497 | 0.0333 | 0.1167 | **0.3667** (25, 38) | 0.23 | 0.501 | no |
| D1C1L20 | 4 | 120 | 0.0756 | 0.0000 | 0.3167 | **0.6667** (10, 1) | 0.65 | 0.766 | **yes** |
| D1C1L200 | 4 | 120 | 0.0756 | 0.0000 | 0.3167 | **0.6667** (10, 1) | 0.65 | 0.766 | **yes** |
| D1C3L20 | 9 | 270 | 0.0571 | 0.0333 | 0.1500 | **0.2833** (20, 3) | 0.42 | 0.619 | **yes** |
| D1C3L200 | 9 | 270 | 0.0571 | 0.0333 | 0.1500 | **0.2833** (20, 3) | 0.42 | 0.619 | **yes** |
| D1C8L20 | 22 | 660 | 0.0481 | 0.0333 | 0.1167 | **0.2500** (15, 1) | 0.24 | 0.578 | no |
| D1C8L200 | 22 | 660 | 0.0481 | 0.0333 | 0.1167 | **0.2500** (15, 1) | 0.24 | 0.578 | no |
| D10C1L20 (not applicable: not at the limit) | 2 | 60 | 0.1123 | 0.0625 | 0.2500 | **0.3750** (6, 0) | 0.33 | 0.583 | **yes** |
| D10C1L200 | 2 | 60 | 0.1915 | 0.2000 | 0.3500 | **0.5833** (4, 1) | 0.17 | 0.417 | no |
| D10C3L20 (not applicable: not at the limit) | 2 | 60 | 0.0373 | 0.0000 | 0.0625 | **0.1875** (9, 0) | 0.57 | 0.662 | **yes** |
| D10C3L200 | 2 | 60 | 0.0681 | 0.0667 | 0.1500 | **0.1833** (17, 0) | 0.23 | 0.535 | no |
| D10C8L20 (not applicable: not at the limit) | 3 | 90 | 0.0222 | 0.0000 | 0.0625 | **0.1875** (28, 0) | 0.77 | 0.792 | **yes** |
| D10C8L200 | 3 | 90 | 0.0405 | 0.0333 | 0.0833 | **0.1333** (5, 0) | 0.16 | 0.483 | no |
| D10C8L120SF8 | 3 | 90 | 0.0405 | 0.0333 | 0.0833 | **0.1333** (5, 0) | 0.16 | 0.483 | no |

**What it shows:**
* **With one or three channels, loss is bimodal under frozen phases.** Most nodes lose nothing
  in a run, and a few lose much:
  * at **d = 0.1 %, C = 1**, the mean is 0.0516, but 74 % of node-runs lose nothing, the 90th
    percentile loses 0.20 and the worst node 0.72;
  * at **d = 1 %, C = 1**, 65 % lose nothing and the worst loses 0.67;
  * C = 3 is bimodal at both duties (42–48 % at zero, worst 0.28–0.47).
* **With eight channels it is not bimodal** (BC 0.50–0.58, 23–24 % at zero). Each frame draws a
  new channel, which breaks up the frozen pairs.
* **This is the finding Mohamed named for the ledger's every-sender criterion.** At the formula's
  N_max, the mean meets ε = 5 % while individual senders lose 20–72 % in a run. With one or
  three channels and these timings, (G24) and not (G23) is the relevant test: the worst sender
  decides.
* **The d = 10 % cells at 20 B are not applicable**, as recorded. Their sent rate was capped by
  the Class A windows.

**Expectations:**
* "Part 1 holds": held;
* "bimodal at d = 1 %, C = 1 and 3": held;
* "**not** bimodal at d = 0.1 % with many nodes": **wrong for C = 1 and 3.** With 27 or 76 nodes
  each node still meets few others per channel at this duty, and phases freeze for the run. Only
  eight channels broke it.
