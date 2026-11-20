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
