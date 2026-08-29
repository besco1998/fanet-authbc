# What AUTHBC is worth — an adversarial self-assessment

*Written 2026-08-30 at Mohamed's request: "an honest real scientific audit of the honest value and
placement of our work and what lacks and what can be made as future work." Written to be
uncomfortable rather than encouraging. Readable rendering published as an artifact; **this file is
canonical**.*

---

## The one-paragraph verdict

This is a **strong measurement-and-reproducibility study with one genuinely durable negative
result**, wrapped around an engineering optimisation that is largely closed-form and — by the
project's own ablation — less interactive than originally claimed. It introduces no new cryptography
and does not pretend to. Its real distinction is methodological: the standard of self-criticism is
well above the field norm, which is simultaneously its best feature and the thing least likely to be
rewarded by a conventional review process.

| dimension | grade |
|---|---|
| Rigour | **High** |
| Novelty | Modest |
| Reproducibility | **Exceptional** |
| Empirical breadth | Narrow |
| Honesty | Unusual |

---

## Claim by claim: what survives a hostile reviewer

### ✅ SURVIVES — three EU868 data rates admit no per-frame-verifiable telemetry

A 64 B signature does not fit a 51 B payload. It holds at a zero-byte header and a one-byte record.
The smallest standardised alternative at comparable security is 48 B, which fits and leaves three
bytes for everything else.

**Why it survives:** arithmetic, not measurement. No model improvement, hardware advance or better
scheme touches it. **This is the most valuable thing in the thesis** and should be the first
sentence of any talk.

⚠️ **Honest caveat:** the underlying inequality is *not novel* — it appears in the
constrained-networking literature. Ours is the instantiation on this band, the measured constant,
and the composition with the loss argument that forecloses fragmentation. The project checked this
prior art *before* publishing, which is to its credit.

### ✅ SURVIVES — frame-level batching dominates block-level under any loss process

A joint probability cannot exceed a marginal, so a multi-frame unit can never out-verify a
single-frame one. Proved without the independence assumption the emulator makes — which is what
rescues it from being a mere consistency check.

### ⚠️ SURVIVES WITH WORK — the capacity envelope (1.9×–3.2×)

**Solid:** the channel model is validated three ways — a published closed form, an independently
written slot-exact simulator sharing none of its assumptions (≤0.08 %), and NS-3 (≤0.51 %). Better
validation than most work in this space. The *ratios* are protected by construction.

**Where a reviewer will push:** the *absolute* capacities rest on a utilisation ceiling measured at
one node count. Frame-size invariance was tested (0.45 σ, indistinguishable); **node-count
invariance was not**. The envelope assumes a single collision domain with no spatial reuse and no
hidden terminals.

### ⚠️ SURVIVES, NARROWED — 58.7 % fewer on-air bytes

Reproducible, guarded, correctly reported as a decomposition rather than the 75 % figure that is
really `1−1/b`.

**The weakness is the framing, not the number.** A skeptic will say *this is batching, and batching
is not new* — and be substantially right. The defence is that the contribution is the *constraint
analysis* (which ceiling binds, hence what compression is worth), not the batching. Sound, but it
must be made explicitly and early.

### ❌ WEAKEST CLAIM — "co-design" as an organising idea

The project's own ablation undercuts it: encoding is **perfectly separable** (every interaction
exactly zero), the scheme axis is byte-degenerate, and only placement×batching interact — by a term
that is exactly zero at b=1.

**Of four axes, two interact, and their interaction is one line of algebra.** That is not co-design
in any strong sense. The thesis was reframed around feasibility partly for this reason, correctly —
but "co-design" still appears where the evidence does not support its full weight. **A reviewer who
reads the ablation will notice.**

### ❌ SHOULD BE DROPPED AS A RIGOUR SIGNAL — pre-registration

The ordering is genuine and git-verifiable. But the criterion reduces to `1−1/b` with a 40 %
threshold, i.e. **any batch ≥ 2 passes** — independent of every design choice. The companion
verifiability condition is satisfied by construction with zero margin.

**No configuration that batched at all could have failed.** The paper now says so. But it should not
be offered as evidence of falsifiability; it is better presented as a *methodological cautionary
example*, which is what it actually is.

---

## Where this sits in the field

The adjacent literature almost uniformly **proposes a new construction** and evaluates it against
predecessors. This work proposes none, deliberately.

| dimension | field norm | this work | verdict |
|---|---|---|---|
| New primitive | usually yes | none | weaker on novelty, honest about it |
| Channel-model validation | often one source, sometimes none | three independent | **above norm** |
| Hardware | frequently absent | 2 nodes, airtime only | present but thin |
| Seeds / dispersion | often unreported | 30, with min/max/σ | **above norm** |
| Artifact availability | improving, often partial | full, gated, byte-exact | **exceptional** |
| Negative results | rare | several, prominent | **rare and valuable** |
| Self-retractions | almost never | 4+ documented | unusual; see below |

⚠️ **The uncomfortable strategic fact.** The strongest features of this work — the retractions, the
withdrawn theorem, the criterion shown vacuous, the header finding that cost a headline — are the
ones a conventional review process is **least equipped to reward**. Reviewers hunt for weaknesses; a
paper that hands them a list can read as weak rather than rigorous.

Manage this by **framing, not concealment**. Lead with the arithmetic result, which is unassailable.
Present the self-corrections as a *methodological contribution*, because they are one. The cover
letter should say plainly: *we audited our own bound, found it partly rested on our own file format,
and report the smaller result.*

---

## What genuinely lacks

1. **Contention has never been measured.** The capacity envelope is the load-bearing performance
   claim and rests on a **simulation-only** contention model. The hardware work used two nodes —
   zero contention — so it validates airtime constants, not the model carrying the result. **The
   single largest empirical gap.**

2. **The low-rate arm has no measurement at all.** No radio metered, no energy column, one spreading
   factor per run. The capacity figure is a within-one-SF bound with a knife-edge interval: 3, CI
   [2,3], and 9 of 30 seeds failing at the certified value. The *exclusion* needs no radio; the
   *capacity* badly wants one.

3. **The freshness model omits the term that matters at load.** The constraint that sets the batch
   size — hence every byte number — carries no channel-access delay. Mitigated by reporting
   utilisation alongside, not by fixing the model.

4. **Energy is a known lower bound**, 10–14 % low, the residual being uncharged prototype framing
   overhead. Measured and stated, not corrected — right behaviour, but absolute figures need the
   caveat.

5. **Breadth.** One band, one PHY per arm, one traffic pattern, static nodes for 802.11, 46
   references. Mobility was tested and found null for collision-limited capacity — a real result —
   but per-frame Doppler is unmodelled, so "mobility doesn't matter" is **not** what was shown.

---

## Future work, ranked by value per unit effort

1. **Measure contention on real hardware.** Highest value by a wide margin. Converts the envelope
   from "simulation-validated" to "measured" — the difference between a good paper and a strong one.
   Needs more radios than the project has.

2. **Node-count invariance of the utilisation ceiling.** Cheap; the scenario exists and frame-size
   invariance was already done this way. Closes the last unexamined assumption behind the absolute
   capacities. Hours.

3. **Adopt the integer-keyed wire format and re-derive the boundary.** The measurement exists; the
   format was kept frozen for reproducibility. A successor should adopt it, re-freeze, and report
   the resulting — *smaller* — boundary. Turns a self-criticism into a system improvement.

4. **Channel-access delay in the freshness model.** Makes the batch-setting constraint credible at
   the loads where it currently is not. Touches every byte number, so needs a careful re-freeze.

5. **Multi-spreading-factor low-rate capacity.** Answers the question an operator actually asks —
   deployment capacity rather than per-configuration feasibility — and lifts the weakest empirical
   result.

6. **Price implicit (ECQV) certificates.** Current accounting charges explicit certificates, an
   upper bound that cuts *against* our own comparison. Safe, but a reviewer who knows IEEE 1609.2
   will ask.

7. **A measured post-quantum arm.** The projections show batching cannot rescue post-quantum
   signature sizes — freshness caps the batch and one signature plus header already exceeds the
   frame budget. A strong negative result currently supported by arithmetic alone.

8. **Generalise the exclusion across bands and post-quantum sizes.** The bound is link-agnostic.
   Instantiating it against mandated post-quantum signature sizes would say which future radio and
   cryptography combinations are feasible *before* either is deployed. Speculative, and the most
   interesting item here.

---

## The honest summary

**What to claim.** A rigorous, fully reproducible feasibility study of authenticated telemetry on
constrained links, containing one arithmetic impossibility result that cannot drift, a
three-way-validated channel model, and an unusually explicit account of the defects found in
establishing them.

**What not to claim.** Novelty of construction. A strong four-way co-design. That the exclusion
bound is entirely ours. That the capacity numbers are hardware-validated. That 30 seeds made the
results correct — the project's own record shows four later defects were immune to sample size.

> The best defence of this work is also the most accurate description of it: a study that took its
> own results seriously enough to keep breaking them, reported what broke, and ended with fewer
> claims than it started with — every one of which is now worth more.
