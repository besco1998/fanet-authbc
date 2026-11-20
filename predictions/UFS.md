# U-FS — the finite-station form against ns-3, where Mohamed accepted it (N = 3–5, u ≤ 0.5)

*Registered 2026-11-20, before any U-FS run; the time is the commit's. Work package C of
`docs/prompts/NEXT_PHASE_PROMPT.md`.*

*Mohamed (2026-11-20): "Accept the finite-station form for N = 3–5 at occupancy ≤ 0.5 only, and
register it there. Do not patch it for N = 2 or high occupancy."*

## The model under test

`src/authbc/models/finite_station.py`, derived in
`docs/revision/2026-11-20_finite_station_derivation.md`:

    p = a·E[M/(W + M)]  +  γ(2a'/W + γ')  +  2δν(1 + a)

* M ~ Binomial(N − 2, K_N/(N − 2)) co-waiting bystanders;
* the primes are rates from the N − 2 stations other than the tagged one and the transmitter;
* everything else is (G4)–(G5)'s, solved at its own fixed point in p.

## The cells (new)

* 802.11b at 1 Mb/s with a **223 B** frame, and 802.11a at 6 Mb/s with a **1 031 B** frame. No
  stored result has either size; the event comparison used 145 B and 1 400 B.
* N = 3, 4, 5; airtime occupancy u = N·f·T_f = 0.3 and 0.5.
* 12 cells.

## Predictions (`python analysis/ufs.py --markdown`, generated)

| cell | PHY | frame | N | u | frames/s | T_f (µs) | **finite-station loss** | (G5) | (G25) |
|---|---|---|---|---|---|---|---|---|---|
| FSB223N3U30 | 80211b | 223 B | 3 | 0.3 | 44.1696 | 2264 | **0.00158** | 0.00256 | 0.00206 |
| FSB223N3U50 | 80211b | 223 B | 3 | 0.5 | 73.6160 | 2264 | **0.00378** | 0.00739 | 0.00537 |
| FSB223N4U30 | 80211b | 223 B | 4 | 0.3 | 33.1272 | 2264 | **0.00229** | 0.00322 | 0.00267 |
| FSB223N4U50 | 80211b | 223 B | 4 | 0.5 | 55.2120 | 2264 | **0.00603** | 0.00970 | 0.00729 |
| FSB223N5U30 | 80211b | 223 B | 5 | 0.3 | 26.5018 | 2264 | **0.00280** | 0.00366 | 0.00311 |
| FSB223N5U50 | 80211b | 223 B | 5 | 0.5 | 44.1696 | 2264 | **0.00778** | 0.01133 | 0.00875 |
| FSA1031N3U30 | 80211a | 1031 B | 3 | 0.3 | 69.0608 | 1448 | **0.00271** | 0.00459 | 0.00364 |
| FSA1031N3U50 | 80211a | 1031 B | 3 | 0.5 | 115.1013 | 1448 | **0.00661** | 0.01319 | 0.00952 |
| FSA1031N4U30 | 80211a | 1031 B | 4 | 0.3 | 51.7956 | 1448 | **0.00399** | 0.00579 | 0.00475 |
| FSA1031N4U50 | 80211a | 1031 B | 4 | 0.5 | 86.3260 | 1448 | **0.01058** | 0.01723 | 0.01292 |
| FSA1031N5U30 | 80211a | 1031 B | 5 | 0.3 | 41.4365 | 1448 | **0.00491** | 0.00658 | 0.00554 |
| FSA1031N5U50 | 80211a | 1031 B | 5 | 0.5 | 69.0608 | 1448 | **0.01363** | 0.02005 | 0.01548 |

**Scored:** **the finite-station loss holds if within ±15 % of ns-3's loss**,
|p_finite − p_ns3|/p_ns3 ≤ 0.15. Each cell is scored on its own. The tolerance is fixed now.

**Reported, not scored:** (G5)'s and (G25)'s errors at the same cells, and ns-3's bootstrap
interval over seeds.

**A failure** is reported with its side:
* *pessimistic:* the form predicts more loss than ns-3;
* *optimistic:* less.

## What is run

* **The scenario:** the audit twin (gate 9/9 identical, rebuilt 2026-11-20), through
  `ns3/run_unified.py`.
* **The runs:** the designated source; **100 s** per run, so that losses of 0.2–1 % are measured
  to a few percent; seeds 1–30 at each cell's own N.
* **The loss:** 1 − the 30-seed mean delivered fraction. With equal power, a collision loses a
  frame at every receiver, so this is the per-frame loss.
* **Scoring:** `analysis/ufs.py --score` → `results/raw/ufs_scored.csv`.

## Expectations `[agent]`

Stated from C's event comparison (`results/raw/finite_station_check.csv`), which is the evidence
for what follows. There, the form against **ns-3's rule** at the same N and u:

| N, u | 0.3 | 0.5 |
|---|---|---|
| 3 | 1.57–1.62 | 1.19–1.22 |
| 4 | 1.10–1.22 | 1.09–1.12 |
| 5 | 1.16–1.17 | 1.05–1.11 |

* **N = 3 is likely to fail on the pessimistic side,** about +60 % at u = 0.3 and +20 % at
  u = 0.5. The form was accepted on rule A's comparison (0.84–1.05), and ns-3 follows its own
  rule, in which an idle-medium arrival waits DIFS.
* **N = 4–5 should mostly hold,** with N = 4 at u = 0.3 at 802.11b, and N = 5 at u = 0.3,
  borderline.
* (G5) is pessimistic everywhere (+30 … +100 %); (G25) lies between the two.

## Disclosure

* **Known before this registration:**
  * C's derivation and event comparison, in full, including the ns-3-rule ratios above;
  * Mohamed's decision.
* **No ns-3 run has been made** at any of these cells.
