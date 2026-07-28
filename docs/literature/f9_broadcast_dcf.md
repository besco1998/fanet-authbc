# F9 — literature positioning of the broadcast DCF head start

Prepared 2026-07-28 so the finding can be checked against the published record before P8.
Citation discipline (CLAUDE.md): entries below are marked **[VERIFIED-PRIMARY]** only where the
paper itself was retrieved and read. Everything else is **[VERIFY]** and must be confirmed by
Mohamed against the primary source before it appears in the thesis.

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

### 2.2 Why broadcast is a different regime — and why it is ours

Their post-collision result depends entirely on the **ACK timeout** holding the colliders back.
**Broadcast has no ACK and therefore no ACK timeout.** The colliders resume after DIFS like everyone
else, except that they alone can hold index 0. So in broadcast the post-collision slot is not
inaccessible — it is *exclusively* accessible to the stations that just collided. That is the
opposite of the unicast conclusion, and it is the regime that produces the 16× error.

Our broadcast measurement: **1315** post-collision winners at DIFS+0 (all previous colliders) against
a hard **DIFS+1** floor for everyone else.

### 2.3 The broadcast literature exists and warns against exactly our error [VERIFY]

> **X. Ma and X. Chen, "Saturation Performance of IEEE 802.11 Broadcast Networks," IEEE
> Communications Letters, vol. 11, no. 5, May 2007.** *(page range unconfirmed)*
> Companion/journal version: **X. Ma and X. Chen, "Performance Analysis of IEEE 802.11 Broadcast
> Scheme in Ad Hoc Wireless LANs," IEEE Trans. Veh. Technol., vol. 57, pp. 3757–3768** *(2008,
> unconfirmed)*.

Reported key claim (from search abstracts, **not** the primary source): the paper argues that
*analytic models for saturation performance evaluation of IEEE 802.11 unicast communication cannot
be simply reduced for analysis of broadcast service*, and builds a model of the broadcast backoff
counter yielding closed-form saturation throughput and packet delivery ratio.

**That is precisely the error this project made**: `analysis/figures_ns3.py` reduced the unicast
model to broadcast by setting τ = 2/(W+1), and it failed by 16×.

Also surfaced, unread: *"Comments on IEEE 802.11 saturation throughput analysis with freezing of
backoff counters"* (IEEE Xplore doc 1388729) — part of the backoff-freezing debate that Tinnirello
et al. resolve. **[VERIFY]**

---

## 3. What Mohamed must check, and what each outcome means

**The single question:** does Ma & Chen's broadcast backoff model treat consecutive channel slots as
*independent*, or does it carry the anomalous-slot correlation?

Chronology suggests it does not — Ma & Chen (2007) predates Tinnirello et al. (2010) — but this must
be read, not inferred.

| outcome | what it means | action |
|---|---|---|
| **(a)** their model already carries the correlation | the corrected broadcast model is published; our slot-exact simulator becomes an *independent validation* of it | cite Ma & Chen as the model; drop our own derivation; strongest possible footing |
| **(b)** their model assumes independence *(most likely)* | the state of the art for broadcast still decouples; the anomalous-slot insight exists only for unicast | cite Ma & Chen as prior art, Tinnirello et al. for the mechanism, and claim the **extension to broadcast with a measured 16× magnitude** as the contribution |
| **(c)** neither model applies | broader search needed (VANET safety-broadcast literature) | — |

Under (b) the honest and defensible framing is:

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
