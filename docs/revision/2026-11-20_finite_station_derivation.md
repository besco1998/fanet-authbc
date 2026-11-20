# A finite-station form of the loss expression, for 2–5 stations — derivation and test

*Work package C of `docs/prompts/NEXT_PHASE_PROMPT.md` (2026-11-20). **A proposal to Mohamed, not
a registration.** Nothing here is scored against ns-3 or hardware until he accepts it.*

* Code: `src/authbc/models/finite_station.py`, tests in
  `tests/unit/models/test_finite_station.py`.
* Comparison: `analysis/finite_station_check.py` → `results/raw/finite_station_check.csv`.

## 1. What is being fixed

The loss expression (G5) counts co-waiting frames and gap arrivals as if the other stations'
starts were Poisson at rate ν = (N − 1)f. Two things are wrong with that for a few stations, each
sending one frame per period:

* **The station whose transmission makes the busy period cannot also be co-waiting.** Its next
  frame is about a period away. At N = 2 that leaves nobody to tie with.
* **No station holds more than one frame at a time,** so the co-waiting count is bounded by the
  number of other stations.

(G25) corrects the clustering of many periodic sources through the Brownian bridge. Its author
states that it is wrong for 1–4 other stations.

## 2. Derivation

**Setting:**
* N stations; the tagged frame's station; n = N − 1 others;
* while the tagged frame waits through a busy period, m = N − 2 of those others are neither the
  tagged station nor the one transmitting.

**What is kept from (G4)–(G5):**
* the probability that the tagged frame arrives to a busy medium,
  a = ν(T_f − δ)(1 − p/2), with ν = n·f. Every other station contributes its airtime to the busy
  fraction;
* γ = ν·DIFS and η = ν·σ(W − 1)/2, for the tagged frame's own exposure;
* the detection-window term 2δν(1 + a): any of the n others may start within δ of the tagged
  frame.

**What changes, the co-waiting stations.** The frames that wait with the tagged one through a busy
period come only from the m bystanders.
* Their rates are the m-station share of (G4)'s: a' = (m/n)·a, γ' = (m/n)·γ, η' = (m/n)·η.
* G4's mean co-waiting count is then taken over the m bystanders alone:

      K_N = a'(1 + γ' + 2η') / (1 − γ' − a')

* **Counting them as a binomial.** Each bystander co-waits, independently, with probability
  π = K_N/m, so M ~ Binomial(m, π) and M ≤ m. The tie term sums over that count with (G5)'s own
  per-count form:

      tie = a · Σ_k P(M = k) · k/(W + k)

* **The zero-backoff term.** The tagged frame starts without backoff at the end of the DIFS gap.
  It collides with a gap arrival or a co-waiter that drew slot 0, and either comes from the
  bystanders: γ(2a'/W + γ').

**The form:**

    p = a·E[M/(W + M)]  +  γ(2a'/W + γ')  +  2δν(1 + a)

**Its limits:**
* **N = 2:** m = 0, so the first two terms vanish and p = 2δf(1 + a).
* **N → ∞:** m/n → 1, K_N → K, and the binomial tends to a Poisson count of mean K. The tie term
  tends to a·E_Poisson(K)[M/(W + M)].
  * That is (G5)'s a·K/(W + K) to first order in K/W, but not exactly. (G5)'s K/(W + K) is
    1 − E[(1 − 1/W)^M] for M geometric of mean K: an M/M/1-like backlog.
  * At the crossings of this work (K/W ≤ 0.05), the gap is −2.8 % of the tie term
    (`finite_station.tie_limit_gap`).
  * **So the form reduces to (G5) only to first order.** A variant that reduces exactly exists:
    replace k/(W + k) by the polynomial whose Poisson mean is K/(W + K), Σ_j (−1)^(j+1)
    k!/((k − j)!·W^j). It has no physical reading per count, so I have not used it.

## 3. The test: event simulations of the access rule, N = 2–5

**The two simulations** share nothing with the models but the rule:
* **rule A:** the loop of Mohamed's `closed_form_model.simulate`, given an arrival list;
* **ns-3's rule:** `authbc.sim.dcf_ns3rule`.

**The sources:**
* **the designated one**, a frame drawn anew in each period, which is also the hardware's sender;
* a fixed random phase;
* Poisson, as the reference.

**The runs:**
* 10 seeds of 100 s each;
* 802.11b at 1 Mb/s with the 2.4 GHz sessions' 145 B frame, and 802.11a at 6 Mb/s with the
  5 GHz sessions' 1 400 B frame;
* airtime occupancy u = N·f·T_f of 0.3 to 0.85. The 5 GHz pair ran 0.48–0.82.

**Model over simulation, designated source** (`python analysis/finite_station_check.py
--markdown`, generated). The simulated loss is given, then each model's ratio to it:

| PHY | N | u | rule A: sim | (G5) | (G25) | **finite** | ns-3 rule: sim | (G5) | (G25) | **finite** |
|---|---|---|---|---|---|---|---|---|---|---|
| 80211b_145B | 2 | 0.3 | 0.00089 | 2.01 | 1.62 | **0.95** | 0.00015 | 11.60 | 9.35 | **5.50** |
| 80211b_145B | 2 | 0.5 | 0.00260 | 1.75 | 1.27 | **0.59** | 0.00077 | 5.86 | 4.27 | **1.97** |
| 80211b_145B | 2 | 0.7 | 0.00707 | 1.31 | 0.86 | **0.33** | 0.00244 | 3.79 | 2.50 | **0.95** |
| 80211b_145B | 2 | 0.85 | 0.02491 | 0.59 | 0.36 | **0.12** | 0.01551 | 0.94 | 0.57 | **0.19** |
| 80211b_145B | 3 | 0.3 | 0.00200 | 1.48 | 1.22 | **0.96** | 0.00119 | 2.48 | 2.05 | **1.62** |
| 80211b_145B | 3 | 0.5 | 0.00529 | 1.57 | 1.17 | **0.85** | 0.00368 | 2.25 | 1.68 | **1.22** |
| 80211b_145B | 3 | 0.7 | 0.01233 | 1.50 | 1.00 | **0.68** | 0.00819 | 2.26 | 1.50 | **1.02** |
| 80211b_145B | 3 | 0.85 | 0.03364 | 0.95 | 0.56 | **0.37** | 0.02545 | 1.25 | 0.74 | **0.48** |
| 80211b_145B | 4 | 0.3 | 0.00268 | 1.38 | 1.17 | **1.01** | 0.00221 | 1.67 | 1.41 | **1.22** |
| 80211b_145B | 4 | 0.5 | 0.00771 | 1.40 | 1.08 | **0.90** | 0.00618 | 1.75 | 1.34 | **1.12** |
| 80211b_145B | 4 | 0.7 | 0.01741 | 1.47 | 0.99 | **0.81** | 0.01397 | 1.83 | 1.24 | **1.01** |
| 80211b_145B | 4 | 0.85 | 0.04064 | 1.13 | 0.67 | **0.54** | 0.03454 | 1.33 | 0.79 | **0.64** |
| 80211b_145B | 5 | 0.3 | 0.00313 | 1.34 | 1.15 | **1.05** | 0.00281 | 1.49 | 1.29 | **1.17** |
| 80211b_145B | 5 | 0.5 | 0.00844 | 1.49 | 1.17 | **1.04** | 0.00795 | 1.59 | 1.25 | **1.11** |
| 80211b_145B | 5 | 0.7 | 0.02106 | 1.46 | 1.01 | **0.90** | 0.01892 | 1.62 | 1.12 | **1.00** |
| 80211b_145B | 5 | 0.85 | 0.04574 | 1.24 | 0.75 | **0.68** | 0.04221 | 1.35 | 0.82 | **0.74** |
| 80211a_1400B | 2 | 0.3 | 0.00096 | 2.53 | 1.85 | **0.74** | 0.00025 | 9.84 | 7.20 | **2.89** |
| 80211a_1400B | 2 | 0.5 | 0.00314 | 2.11 | 1.40 | **0.41** | 0.00113 | 5.84 | 3.88 | **1.14** |
| 80211a_1400B | 2 | 0.7 | 0.00758 | 1.82 | 1.11 | **0.26** | 0.00307 | 4.50 | 2.73 | **0.63** |
| 80211a_1400B | 2 | 0.85 | 0.01784 | 1.23 | 0.69 | **0.14** | 0.00735 | 2.98 | 1.68 | **0.34** |
| 80211a_1400B | 3 | 0.3 | 0.00248 | 1.69 | 1.31 | **0.95** | 0.00150 | 2.80 | 2.17 | **1.57** |
| 80211a_1400B | 3 | 0.5 | 0.00708 | 1.75 | 1.23 | **0.84** | 0.00496 | 2.49 | 1.76 | **1.19** |
| 80211a_1400B | 3 | 0.7 | 0.01722 | 1.61 | 1.02 | **0.67** | 0.01183 | 2.34 | 1.49 | **0.97** |
| 80211a_1400B | 3 | 0.85 | 0.03350 | 1.39 | 0.81 | **0.52** | 0.02330 | 2.00 | 1.16 | **0.74** |
| 80211a_1400B | 4 | 0.3 | 0.00354 | 1.50 | 1.21 | **1.00** | 0.00323 | 1.65 | 1.33 | **1.10** |
| 80211a_1400B | 4 | 0.5 | 0.01057 | 1.54 | 1.13 | **0.92** | 0.00891 | 1.82 | 1.34 | **1.09** |
| 80211a_1400B | 4 | 0.7 | 0.02399 | 1.57 | 1.04 | **0.84** | 0.01959 | 1.93 | 1.28 | **1.03** |
| 80211a_1400B | 4 | 0.85 | 0.04528 | 1.45 | 0.87 | **0.71** | 0.03843 | 1.71 | 1.02 | **0.83** |
| 80211a_1400B | 5 | 0.3 | 0.00457 | 1.33 | 1.11 | **0.97** | 0.00381 | 1.60 | 1.32 | **1.16** |
| 80211a_1400B | 5 | 0.5 | 0.01297 | 1.46 | 1.11 | **0.98** | 0.01206 | 1.57 | 1.20 | **1.05** |
| 80211a_1400B | 5 | 0.7 | 0.02956 | 1.53 | 1.04 | **0.93** | 0.02716 | 1.66 | 1.13 | **1.01** |
| 80211a_1400B | 5 | 0.85 | 0.05551 | 1.44 | 0.88 | **0.81** | 0.05005 | 1.59 | 0.98 | **0.90** |

## 4. What the test shows

* **Where the form works:** N = 3–5 at occupancy up to 0.5, with the designated source.
  * Rule A: within 0.84–1.05 of the simulation.
  * ns-3's rule: within 1.05–1.22. The exception is N = 3 at u = 0.3, at 1.57–1.62
    (pessimistic), where the loss is only 0.0012–0.0015.
  * (G5) overestimates there by 1.33–1.75 times against rule A. (G25), outside its stated range,
    overestimates by 1.08–1.31 times.
* **Where it degrades, then fails:**
  * **occupancy 0.7, N = 3–5:** 0.67–0.93 against rule A, 0.97–1.03 against ns-3's rule;
  * **occupancy 0.85, N = 3–5,** on the optimistic side (too little loss): 0.37–0.81 against
    rule A, 0.48–0.90 against ns-3's rule;
  * **N = 2, on both sides.** Against rule A, 0.12–0.95: optimistic, worse with load. Against
    ns-3's rule, 0.19–5.5: pessimistic at low load (5.5 and 2.9 at u = 0.3), optimistic at 0.85.
* **The cause, seen in the simulations, not fitted:**
  * with the designated source a station's next frame can arrive soon after its last (the
    inter-arrival runs from 0 to 2 periods);
  * so at high per-station load the transmitter's own next frame is often already waiting, and
    the form's exclusion of the transmitter is then wrong;
  * at N = 2 that frame is the only possible co-waiter.
* **N = 2 is also where the two access rules differ most** (rule A 0.00089 against ns-3's 0.00015
  at u = 0.3, 802.11b). ns-3 sends an idle-medium arrival DIFS after it arrives. So the
  detection-window term, all that is left at N = 2, depends on the rule.
* **The fixed-phase source cannot be measured this way.** Two stations' relative phase is
  frozen: they collide on every frame or never. 10 seeds give zeros (shown as — in the CSV) and
  ratios of 0.3–4.7. It needs many more seeds, or the clock drift of real boards.

## 5. The proposal (for Mohamed)

* **(a) Accept the form for N = 3–5 at occupancy ≤ 0.5,** with the designated source. That covers
  W1e's three-board groups at occupancy 0.50 and the four-board sessions' lower loads.
  * Register it there against ns-3 on new cells, ±15 % on the loss.
  * State that it does not hold at N = 2 or at high load.
* **(b) Before any registration, extend the derivation by one term:** the transmitter's own next
  frame as a co-waiter, with the probability that it arrives before the busy period ends. That
  probability comes from the triangular inter-arrival of the designated source. It is the
  mechanism the simulations show, at N = 2 and at high load, and it would be derived, not fitted.
  * **This is the option I recommend.** The 5 GHz anchor (N = 2 at u = 0.48–0.82) falls exactly
    where the present form fails.
* **(c) Use the event simulation itself as the small-N model:** ns-3's rule, at the session's own
  rates. It is exact for the access rule and needs no closed form.
* For the fixed-phase case, whichever is chosen: more seeds or drifting clocks.

## Note added 2026-11-20, after U-FS and F137 (the text above is unchanged)

* **"ns-3's rule" in §§3–4 means the event model `authbc.sim.dcf_ns3rule`, not ns-3.** At N = 2–3
  that model loses 0.14–0.79 of ns-3's loss, while rule A's simulation tracks ns-3 within
  0.79–1.31 (F137).
* **Against ns-3 itself, the form held 12 of 12 at N = 3–5, u ≤ 0.5:** −11.9 … +4.1 %
  (`predictions/UFS.md`).
* **At N = 2 and at high load it still fails against ns-3,** 0.14–0.75 of ns-3's loss
  (F137's table). That is why it is not used there (Mohamed, 2026-11-20).
