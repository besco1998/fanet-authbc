# F9 — literature positioning of the broadcast DCF head start

**RESOLVED 2026-07-28 — outcome (a): the mechanism is published. F9 is a rediscovery.**
All three papers were obtained by Mohamed and read in full; the Ma & Chen letter's bibliographic
record was confirmed from IEEE Xplore. Ma & Chen's closed form reproduces our NS-3 measurement to
**≤0.36 %** at every N. No novelty is claimed for the mechanism; see §2.3 and §3 below.

---

## 1. The mechanism, stated for a literature search

In saturated 802.11 DCF, after a busy period ends a station transmits at `DIFS + index·slot`, where

* **index = a fresh draw from {0 … CW}** if the station transmitted in that busy period, and
* **index = its residual counter, necessarily ≥ 1**, if the station deferred — a counter of 0 would
  already have fired.

A station that has just transmitted, and only such a station, can therefore hold index 0 and seize
the medium **one slot ahead of the entire field**. Consecutive channel slots are consequently
*correlated*, and the stations are *not* statistically homogeneous — which is exactly the pair of
assumptions Bianchi's decoupling approximation makes.

**The broadcast-specific amplification.** Broadcast is never acknowledged, so there is no
retransmission and **no contention-window doubling**: CW is frozen at CW_min. N stations stay packed
into CW_min+1 counter values indefinitely, collisions become near-certain, and the one-slot head
start becomes the *dominant* channel through which any transmission ever succeeds alone.

Closed form for the resulting conditional success probability, where k is the number of colliders:

```
P(next busy period succeeds | previous was a k-way collision) = k · (1/W) · (1 − 1/W)^(k−1)
```

Measured at N=50, W=16, k̄=6.108: predicted **0.2745**, measured **0.2679** — 2.4 %, nothing fitted.

### Measured signature (search terms a matching paper should exhibit)

| observable | measured (NS-3 3.41, N=50, 802.11a 6 Mb/s, L=1400 B) |
|---|---|
| p_s, textbook no-ACK Bianchi | 0.0128 |
| p_s, measured | **0.2234** (17.5×) |
| p_s for independent stations at the *measured* mean multiplicity | 0.0308 → the residual is **correlation**, not access rate |
| idle slots per busy period, model / measured | 0.0019 / **0.741** (386×) |
| gap after a collision, winner **was** a collider | **DIFS + 0 slots** |
| gap after a collision, winner was **not** | **DIFS + 1 slot** (hard floor) |
| P(winner ∈ previous busy period), measured / uniform | **0.9645 / 0.1272** (7.58×) |
| throughput error of the textbook no-ACK variant at N=50 | **+1654 %** |

---

## 2. What was found

### 2.1 The mechanism IS published — for unicast [VERIFIED-PRIMARY]

> **I. Tinnirello, G. Bianchi, and Y. Xiao, "Refinements on IEEE 802.11 Distributed Coordination
> Function Modeling Approaches," IEEE Transactions on Vehicular Technology, vol. 59, no. 3,
> pp. 1055–1067, March 2010.**
> Retrieved and read in full from `https://yangxiao.cs.ua.edu/IEEE_TVT_New_802.11Model.pdf`.

Verbatim from the abstract:

> "a careful look at backoff counter decrement rules allows us to conclude that, under saturation
> conditions, **the slot immediately following a successful transmission can be accessed only by the
> station (STA) that has successfully transmitted in the previous channel access**. Moreover, due to
> the specific acknowledgment (ACK) timeout setting adopted in the standard, **the slot immediately
> following a collision cannot be accessed by any STA**. Thus, **the hypothesis of uncorrelation
> between consecutive channel slots and statistical homogeneity is not generally true.**"

Section III is titled **"Backoff Decrement and Anomalous Slots"**. The paper gives
`ACKTimeout = SIFS + T_Ack + δ` and `EIFS = SIFS + T_Ack + DIFS`.

Note the third author is **Bianchi himself** — this is the original model's author publishing the
refinement, which makes it the authoritative statement of the effect.

**Scope check: the paper is unicast-only.** A full-text search returns **zero** occurrences of
"broadcast", "multicast", "no ACK", "fixed/constant contention window".

**Our unicast measurements independently confirm both of its claims** (audit A10, N=50 unicast):

| their claim | our measurement |
|---|---|
| post-success slot accessible only to the successful STA | gap floor **94 µs = SIFS + T_Ack + DIFS**, taken 220×; everyone else at 103 µs (+1 slot) ✓ |
| post-collision slot accessible to nobody (ACK timeout) | only **30 of 1099** transitions took the immediate slot; 1069 at DIFS+1 ✓ |

### 2.2 Why broadcast is a different regime (Ma & Chen reach the same conclusion, §2.3)

Their post-collision result depends entirely on the **ACK timeout** holding the colliders back.
**Broadcast has no ACK and therefore no ACK timeout.** The colliders resume after DIFS like everyone
else, except that they alone can hold index 0. So in broadcast the post-collision slot is not
inaccessible — it is *exclusively* accessible to the stations that just collided. That is the
opposite of the unicast conclusion, and it is the regime that produces the 16× error. Ma & Chen
state exactly this in §II-C of their 2008 paper; the derivation below was ours, the result was not.

Our broadcast measurement: **1315** post-collision winners at DIFS+0 (all previous colliders) against
a hard **DIFS+1** floor for everyone else.

### 2.3 The broadcast model was already published — and warns against our exact error

> **X. Ma and X. Chen, "Saturation Performance of IEEE 802.11 Broadcast Networks," IEEE
> Communications Letters, vol. 11, no. 8, pp. 686–688, Aug. 2007,
> doi:10.1109/LCOMM.2007.070040.** [VERIFIED-PRIMARY + Xplore record]
> **X. Ma and X. Chen, "Performance Analysis of IEEE 802.11 Broadcast Scheme in Ad Hoc Wireless
> LANs," IEEE Trans. Veh. Technol., vol. 57, no. 6, pp. 3757–3768, Nov. 2008,
> doi:10.1109/TVT.2008.918731.** [VERIFIED-PRIMARY]

*(Note: the author-copy PDF of the letter carries a placeholder header "vol. 11, no. 5, May 2007".
The Xplore record — vol. 11, no. 8, pp. 686–688, August 2007 — is authoritative.)*

Verbatim from the abstract: analytic models for unicast *"**cannot simply be reduced** for the
analysis of broadcast service."* They name the mechanism the **backoff counter Consecutive Freeze
Process (CFP)** and state the unicast/broadcast asymmetry in §II-C of the journal version. Their
model splits the backoff counter into the sequential backoff process and the CFP, and yields a
closed form for saturation throughput and packet delivery ratio.

**Their closed form vs our NS-3 measurement: ≤0.36 % on p_s, idle-slots-per-busy-period and
throughput at N = 5, 10, 20, 35, 50.** Implemented in `models/broadcast_dcf.py`. Their
τ_s = 2/W₀ = 0.125; our discarded reduction used 2/(W+1) = 0.1176.

**Caution for implementers:** the 2007 letter's eq. (6) prints `pss = 1−(1−τs)^(n−1)`, which is a
collision probability and cannot be a success probability. The 2008 journal eq. (8) gives the
correct `pss = n·τs·(1−τs)^(n−1)`. Use the journal.

**That is precisely the error this project made**: `analysis/figures_ns3.py` reduced the unicast
model to broadcast by setting τ = 2/(W+1), and it failed by 16×. It has been replaced by
`models/broadcast_dcf.py`.

Also surfaced, unread: *"Comments on IEEE 802.11 saturation throughput analysis with freezing of
backoff counters"* (IEEE Xplore doc 1388729) — part of the backoff-freezing debate that Tinnirello
et al. resolve. **[VERIFY]**

---

## 3. Resolution

**The question was:** does Ma & Chen's broadcast backoff model treat consecutive channel slots as
*independent*, or does it carry the anomalous-slot correlation? (Chronology suggested independence —
Ma & Chen 2007 predates Tinnirello et al. 2010 — which turned out to be wrong.)

**ANSWERED: outcome (a).** Ma & Chen's model carries the correlation explicitly — the CFP *is*
the correlation. Actions taken: `models/broadcast_dcf.py` implements their equations with citation;
our in-house reduction is deleted from the analysis path and kept only as a labelled failure curve;
`sim/dcf_ladder.py` is retained as an independent cross-check (agrees to <2 %); docs/02 §6a now
specifies the broadcast model normatively.

**What remains ours, stated conservatively:** independent validation at W₀=16 / 802.11a / 6 Mb/s
(they tested W₀=32 and 128 at 1 Mb/s — and they conclude CFP matters *most* at small W₀); direct
PHY-trace measurement of the mechanism rather than curve-fitting; and reproduction of the
non-monotonic throughput reversal near N≈40 that the naive reduction cannot produce.

The superseded framing follows, kept visible:

> Tinnirello et al. showed that DCF's backoff decrement rules make consecutive slots correlated, and
> that in unicast the ACK timeout blocks the post-collision slot. We show that in **broadcast**,
> where no ACK timeout exists and the contention window never doubles, the same rules produce the
> opposite effect — the post-collision slot is seized exclusively by the colliders — and that this,
> not capture, accounts for a **16×** discrepancy between the standard no-ACK Bianchi adaptation and
> a reference simulator. A slot-exact model carrying only this asymmetry matches NS-3 to ≤0.40 %
> across N=5–50.

---

## 4. Regardless of outcome — one correction is already owed to the docs

`docs/02 §6` cites Bianchi without the 2010 refinement, and the project's broadcast variant was
derived in-house rather than cited. Both should change:

* add Tinnirello et al. (2010) as the refinement of the unicast model **[VERIFIED-PRIMARY]**;
* stop presenting τ = 2/(W+1) as *the* broadcast model — it is our own reduction, and it is wrong.
