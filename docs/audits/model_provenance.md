# Model provenance audit — cited vs. home-derived (2026-07-28)

**Why this exists.** F9 was caused by *deriving* a broadcast channel model in-house when a published
one existed whose abstract warns against exactly the reduction we made. That class of error is
invisible to testing: the code was correct, the tests passed, the model was wrong. This audit walks
every model and formula in docs/01–02 and asks one question — **is it cited, or did we build it?** —
and where we built it, whether that is safe.

Verdict summary: **no second F9.** The remaining home-derived items are elementary algebra where
that is appropriate. Two real findings came out of the exercise (F10, F11) plus three positioning
fixes.

---

## Provenance table

| model | provenance | assessment |
|---|---|---|
| **T1** overhead fraction φ = g/(s+g); φ≥α ⇔ s ≤ g(1−α)/α | home-derived | **Safe.** A definition plus a one-line rearrangement. Nothing to cite; nothing to get wrong. |
| **T2** ω(b)=(g_a+H_f)/b; amplification A = M/(M−H_f−g_a) | home-derived | **Safe arithmetic, but see P1 below.** Substituting b=b_max and factoring. The *idea* (per-frame overhead amortised against MTU) is standard networking; only the packaging is ours. |
| **T3** V_B = 1−p, V_D = (1−p)^n, n_max = ⌊ln(1−ε)/ln(1−p)⌋ | home-derived | **Safe algebra, but rests on an assumption — see F11.** Elementary given *independent* frame loss. |
| **T4** κ\* = ΔCPU/ΔRADIO crossover | home-derived | **Safe.** Elementary energy accounting; the inputs (sizes, timings, powers) are all measured. ΔRADIO carries a documented ±5 % quantisation caveat (D9) against a ~90× verdict margin. |
| **T5** co-design separability | **asserted in prose** | **See P2.** The docs read as though separability is proven. It is not — it is *verified exhaustively*: `optimizer.solve` evaluates the full 4 encodings × 3 schemes × 4 placements × 32 batches = 1536-point grid, so a non-separable optimum would be found. That is strong evidence, and it should be described as such rather than as a theorem. |
| **§6** Bianchi DCF | **cited** ✓ | Bianchi (IEEE JSAC 2000) + Tinnirello, Bianchi & Xiao (IEEE TVT 2010) for the anomalous-slot refinement. Validated against NS-3 to +0.6/−2.9 %. |
| **§6a** broadcast DCF | **cited** ✓ | Ma & Chen (IEEE Comm. Lett. 2007; IEEE TVT 2008). Was the F9 gap; closed 2026-07-28. |
| **§7** energy E = P_c·(…) + P_r·T_air/b | home-derived | **Safe.** Additive accounting over measured terms. |
| **§7** latency M/M/1 queueing approximation | **uncited standard model — and NOT IMPLEMENTED** | **F10 below.** |
| **§8** median + bootstrap 95 % CI | standard method, uncited | **Safe.** Ubiquitous practice; a citation would be cosmetic. |

---

## F10 — the headline configuration violates the documented freshness bound, and never said so

docs/02 §7 specifies a soft freshness bound **D(b) ≤ D_max = 250 ms** and a latency model
`D(b) = b/Λ + T_air + queueing (M/M/1 approx)`. Two defects:

1. **The queueing term was never implemented.** `optimizer.py` computes `batch/λ + radio_airtime`
   with the comment `# queueing: P5b` — a deferral that was never picked up. The model in the docs
   and the model in the code are not the same model.
2. **The result was computed and then discarded.** `Candidate.meets_latency` existed but no
   experiment ever wrote it out, so `e5_codesign.csv` reported the byte win with no hint of what it
   cost in freshness.

**Measured at Λ = 20 records/s:**

| configuration | auth cut | freshness | meets 250 ms? |
|---|---|---|---|
| byte-optimal ignoring freshness — delta+Ed25519, B, **b=31** *(the headline until F10)* | **96.77 %** | **1552 ms** | ❌ **6.2× over** |
| **the headline now** — byte-optimal *subject to* D ≤ 250 ms, **b=4** | **75.00 %** | 200 ms | ✓ |
| A+CBOR baseline | — | 50 ms | ✓ |

Only **160 of 521** feasible configurations meet the freshness bound.

**The success criterion passes either way** (75 % ≫ 40 %), so nothing is retracted. But "96.77 %"
and "1.55 s of staleness on the oldest record in a batch" belong in the same sentence, and until now
they were not. For UAV telemetry that is an operational fact, not a footnote.

**Resolved by Mohamed the same day — see the F10 resolution at the end of this document.**
`e5_codesign.csv` now carries `latency_ms` and `meets_d_max` for every row, and freshness is both a
hard constraint and a Pareto objective in the optimizer.

---

## F11 — RESOLVED analytically: independence is the WORST case for D, so T3 is unconditional

V_D = (1−p)^n is exact **iff** frame losses are independent. Our emulator implements independent
Bernoulli draws, so E3 measures V against a channel built on the same assumption the theorem makes:
the agreement in `e3_loss.csv` (V_meas ≈ V_theory) is a **consistency check, not a validation**.

Real 802.11 loss is bursty (fading, interference, collision trains), and burstiness *helps*
block-level D relative to the independent prediction — losses cluster into fewer frames. So T3's
conclusion (B Pareto-dominates D) is **conservative** under burstiness rather than wrong, which is
the safe direction. It should nonetheless be stated as an assumption, not left implicit.

**Resolved 2026-07-28 — the conclusion needs no independence assumption at all.** For *any*
stationary loss process of mean rate p, whatever its correlation:

> V_D(n) = P(all n frames arrive) ≤ P(one given frame arrives) = 1−p = V_B,

because a joint probability cannot exceed a marginal. Equality only at n=1. So block-level can never
out-verify frame-level, and when ε ≤ p it can never become feasible at n ≥ 2 — **T3's direction is
correlation-independent**, and the (1−p)^n form is merely the *tightest* (worst-for-D) case.

Quantified by Gilbert–Elliott simulation at matched mean p=0.05: V_D(n=2) rises 0.9025 (independent)
→ 0.9447 (mean burst 10 frames) → 0.9498 (burst 160), asymptotic to 1−p and never reaching the 0.95
threshold. Pinned by `test_block_verifiability_can_never_exceed_frame_verifiability_under_any_loss_model`.
Measuring a real loss process on hardware remains useful for *quantifying* the gap, not for the verdict.

---

## Positioning fixes (no numbers change)

* **P1 — "amplification law" (T2) — FIXED.** Reworded to "amplification, see T2a for when it
  applies", with an explicit note that it is MTU-efficiency algebra rather than a new law. The
  investigation also produced **T2a**, a genuine refinement: A applies only in the MTU-limited
  regime, and on 802.11 that regime is never reached (see below). The stale A values were
  recomputed and one (LoRa ≈1.35) could not be reproduced at any g_a — flagged in docs/02.
* **P2 — T5 "separable" — FIXED.** Now reads "empirically separable — verified by exhaustive search
  over the full 1536-point grid, not proven".
* **P3 — §7 latency — FIXED.** The M/M/1 term is implemented (`energy.queueing_delay_s`,
  `energy.freshness_delay_s`) and used by the optimizer and by E5's baseline rows. Measured
  W_q ≈ 1.2 µs against a 250 ms budget, so it does not move the optimum — but docs and code now
  agree, and implementing it exposed a real gap: the model had **no transmit-throughput constraint
  at all**, so a station whose frame queue was 12× oversubscribed (ρ ≈ 11.9) was previously
  reported as feasible. ρ ≥ 1 now yields W_q = ∞ and is filtered.

---

## Method note for the future

The cheap, general check is: **for every model, name the source in the docstring.** Where the source
is "us", the docstring should say so explicitly. A model whose docstring cannot name a source is a
model nobody has checked against the literature — and that is exactly the F9 signature.

---

## F10 — RESOLVED (Mohamed, 2026-07-28): freshness is enforced and optimized

Mohamed's ruling: *"we must take freshness into the optimization problem and must optimize all the
parameters."* The spec supports it — docs/02 §7's verb is **enforce**, and the optimizer's own
docstring had softened that to "annotated, not filtered".

Applied, both ways:

* **Hard constraint.** A configuration that misses D_max is inadmissible, exactly like one that
  misses V. Feasible set 521 → **160**.
* **Fourth Pareto objective.** Alongside bytes, energy and verifiability, so the bytes↔freshness
  trade-off is visible *inside* the feasible region. Frontier 82 → **18** points. Without this the
  largest admissible batch dominates every smaller one and the trade-off disappears.

**Headline: 96.77 % → 75.00 %** (b=31 → b=4, 200 ms, 111.86 µJ). Still ≫ the 40 % criterion.

The co-design frontier this exposes is a better result than the single number was:

| b | auth B/record | cut | freshness | energy |
|---|---|---|---|---|
| 1 | 103.998 | 0.00 % | 50.3 ms | 317.38 µJ |
| 2 | 51.998 | 50.00 % | 100.4 ms | 180.37 µJ |
| 3 | 34.665 | 66.67 % | 150.4 ms | 134.70 µJ |
| **4** | **25.998** | **75.00 %** | **200.5 ms** | **111.86 µJ** |

And a closed form worth stating in the thesis: since fill time dominates D(b), the admissible batch
obeys **b ≲ Λ·D_max**, *independent of encoding and scheme*. At telemetry rates **freshness binds
long before the MTU does** — which reframes T2/T5: the MTU knee is not the operative limit.

Still open: the M/M/1 queueing term docs/02 §7 specifies is not implemented (P3 above). Omitting it
makes D(b) a **lower** bound on true delay, so the constraint is conservative — the safe direction.


---

## T2a — the regime finding (arose from F10, 2026-07-28)

Enforcing freshness raised a question the provenance sweep had to answer: **T2's amplification law
A = M/(M−H_f−g_a) is derived AT the MTU limit. Does it survive when freshness caps the batch first?**

**It does not.** With b fixed by freshness at ⌊Λ·D_max⌋ — independent of s — per-record cost is
C(s) = s + (g_a+H_f)/b and **dC/ds = 1 exactly**. Compression pays 1×, not A×, and the residual
authentication cost becomes a **floor that compression cannot touch**.

Verified numerically: on 802.11 the marginal rate between adjacent encodings is **1.0000** to 12
decimal places, against T2's predicted A = 1.0745.

| link | boundary s < (M−H_f−g_a)/(⌊Λ·D_max⌋+1) | encodings in study | binds | A operative? |
|---|---|---|---|---|
| 802.11 (M=1500) | 232.7 B | 45 – 191 B | **freshness** | **no** — dC/ds = 1 |
| LoRa (M=222) | 19.7 B | 45 – 66 B feasible | **MTU** | **yes** — A = 1.881 |

**This sharpens the thesis rather than weakening it.** The "compression pays ×A" leverage that
motivates the LoRa arm (docs/30) is real *and exclusive to it*: on 802.11 at telemetry rates the MTU
knee is simply never reached. Implemented as `optimizer.binding_constraint` /
`effective_amplification`; four tests pin the regimes and the boundary.

---

## F5 — DECIDED (2026-07-28): adopted on the LoRa arm only; 802.11 keeps per-record chaining

> **Outcome.** Mohamed adopted per-frame chaining **on LoRa only**. The analysis below stands as
> written; what changed is the verdict. On LoRa the regional payload limit binds, so the saving
> converts into **2.7× the sustainable record rate** (b 3→8 at DR5, Λ 0.076→0.203 rec/s) — worth the
> trade. On 802.11 freshness binds (T2a, dC/ds = 1), so the same change buys ~6 % total energy and
> **no extra records**, which does not pay for losing independent per-record tamper-evidence.
> The "−34 % airtime" row below is the **802.11** figure and is the one now declined.
> See docs/02 §9b and DECISIONS.md.

### The original investigation, unchanged


**The measurement.** Every record carries `prev_hash` = SHA-256 of the previous record — 32 bytes
that no encoder can shrink, because a hash is indistinguishable from noise:

| encoding | record | of which is the 32 B chain hash |
|---|---|---|
| JSON | 191.09 B | 16.8 % |
| CBOR | 66.25 B | 48.3 % |
| **delta** | **45.00 B** | **71.1 %** |

So delta compresses the *telemetry* to ≈13 B and then carries 32 B of hash. **Compression has
already hit a floor it cannot cross**, and that floor is the chain, not the codec.

**The redundancy.** Records travel b=4 to a frame under one signature. Inside a frame the receiver
can *derive* every prev_hash except the first, because `prev_hash_{i+1} = H(record_i)` and record_i
is fully known once its own prev_hash is known. Only the first link — which ties this frame to the
previous one — must be transmitted.

**Proven, not argued** (`test_chain_reconstructs_from_one_link_per_frame`): shipping one link per
frame plus the record bodies reconstructs records that are **byte-identical** to the originals, and
the rebuilt ledger satisfies `Chain.verify()`. A companion test pins that the *first* link is not
redundant — dropping it would let frames be reordered or lost undetected.

**What it would be worth** (delta, b=4):

| | now | one link per frame |
|---|---|---|
| record | 45.00 B | **21.00 B** (−53 %) |
| total on-air per record | 71.00 B | **47.00 B** (−34 % airtime and radio energy) |
| auth fraction φ | 58.7 % | **75.3 %** — T1 gets *stronger* |
| auth-byte headline | 75.00 % | **75.00 % — unchanged** (prev_hash is payload, not auth) |

**The honest trade-off.** This is a **wire-format** change, not a ledger change: the receiver
reconstructs and stores full per-record hashes, so the stored ledger and `Chain.verify()` are
untouched. What changes is that *within* a frame, tamper-evidence then rests on the frame signature
rather than on independently transmitted hashes. Since a frame is atomic (all-or-nothing, which is
exactly T3's V_B = 1−p) and signed over its ordered records, the two are equivalent in strength —
but they are no longer *independent* mechanisms, and the reconstruction assumes frames stay atomic.

⚠️ **Decision for Mohamed — the wire format is frozen under D6, so this is not mine to take.**
1. **Adopt it.** ~34 % less airtime and radio energy per record; re-freeze every size-dependent
   artifact (E1, E2, E3, framesizes, E5) and update T1's φ table. Large blast radius.
2. **Leave it, and state it.** Document that per-record chaining costs ~34 % of on-air bytes, and
   say what it buys (independent, per-record tamper-evidence that does not rely on the signature).
   *This is the current state and needs no re-freeze.*
3. **Adopt it for the LoRa arm only**, where 34 % of airtime is worth far more and the MTU binds.

Either way the *finding* is worth reporting: **the chain, not the codec, is what limits how small an
authenticated telemetry record can get.**

---

## F12 — the arrival rate was one number doing two jobs (2026-07-28, FIXED)

**The defect.** docs/01 §5 defines the aggregate arrival **Λ = Λ_i·N_local**, but
`experiments/e5/config.yaml` set `lam: 20` and the optimizer used that single value for two
different quantities:

| constraint | correct rate | what it got |
|---|---|---|
| freshness `b/Λ ≤ D_max` | **per-node** — a UAV batches its own records | 20 ✓ |
| verify throughput `t_vf·Λ ≤ 1` | **aggregate** — a receiver verifies everyone's | 20 ✗ (should be 1000) |

The verify-throughput constraint was under-counted by a factor of N_local: it was silently testing
a **one-sender network**.

**It changed results.** With the aggregate rate counted, verification capacity scales with fleet
size and slow verifiers drop out:

| N_local | Λ aggregate | schemes still feasible | placements |
|---|---|---|---|
| 1 *(the old behaviour)* | 20 | bls, ecdsa, ed25519 | A,B,C,D |
| 10 | 200 | bls, ecdsa, ed25519 | A,B,D — **C gone** |
| 25 | 500 | **ecdsa, ed25519 — BLS gone** | A,B,D |
| 50 | 1000 | ecdsa, ed25519 | A,B,D |

**This strengthens T4.** Ed25519 does not merely win on energy: beyond ~17 neighbours BLS
cross-signer aggregation is **not verifiable at all** — the receiver cannot keep up. The previous
model hid that by checking against one sender's output.

**Fixed:** `Constraints` now carries `lam` (per-node) and `n_local`, with `lam_aggregate` as a
derived property used only by the verify-throughput constraint. `n_local: 50` added to the E5
config. Two tests pin the split and the fleet-size behaviour.

---

## Channel capacity is now a constraint, and the baselines fail it

The NS-3-validated broadcast model was used to *check* the airtime model but never to *constrain*
the optimizer. It now is (docs/02 §6b): `channel_utilisation` computes offered ÷ deliverable frames
at each configuration's own frame size, and U ≤ 1 is hard.

**The finding this produced.** At the stated operating point (N_local=50, Λ_i=20 rec/s):

| configuration | frames needed | channel delivers | U | |
|---|---|---|---|---|
| A+JSON (naive) | 1000 /s | 438 /s | **2.28** | **cannot run** |
| A+CBOR (Pillar-1) | 1000 /s | 654 /s | **1.53** | **cannot run** |
| optimized delta+Ed25519 B b=4 | 250 /s | 452 /s | **0.55** | fits |

**The baselines are not merely wasteful at fleet scale — they are unrunnable.** That reframes the
headline: the co-design is the difference between a system that works at 50 UAVs and one that does
not, which is a stronger claim than "75 % fewer authentication bytes".

**Method note (Law 6).** My first version of this calculation compared 284–644 B configurations
against the goodput measured at 1400 B frames and concluded everything fitted with ~2× headroom.
Capacity is strongly frame-size dependent, so that was wrong by about 2× at the critical corner. It
was caught because the frame-rate arithmetic disagreed with the byte arithmetic. Capacity is now
always evaluated at the configuration's own frame size, and a test pins that smaller frames get
*less* capacity.

⚠️ **Open: DCF access delay is not modelled.** D(b) covers fill + airtime + the node's own frame
queue, not waiting for a contended medium. At U → 1 real latency rises far above D(b) invisibly, so
the freshness figure is credible only at low U. `channel_util` is now reported next to it.

---

## F13 — the auth-byte headline is placement×batching ALONE; encoding and scheme contribute zero ⚠️
*Found 2026-07-28 during the pre-P8 full audit. **Not a bug — a framing error.** No number changes;
what changes is what we are allowed to claim.*

**The arithmetic.** On-air authentication overhead per record is

        auth(b) = (H_f + g_a) / b            for placements B/C/D
        auth(1) = H_f + g_a                  for placement A (inline, b=1)

`s` — the encoded record — **does not appear**. So the headline metric is a function of placement
and batch only. Ed25519 and ECDSA-P256 are both 64 B, so the *scheme* axis cannot move it either
(BLS's 96 B moves it the wrong way).

**Verified against frozen E2, independently of the model code** (`bytes_per_rec − s`, M=1500):

| | JSON | CBOR | MessagePack | delta |
|---|---|---|---|---|
| placement A, b=1 | 103.995 | 104.002 | 104.000 | 103.998 |
| **placement B, b=4** | **25.995** | **26.002** | **26.000** | **25.998** |

**Identical to three decimal places across all four encodings.** The 75.00 % cut is
(104 − 26)/104 — it would be reported unchanged if the encoding axis were deleted from the study.

### The sharpest form: the headline is algebraically **1 − 1/b**

Both the baseline and the optimized configuration carry the *same* per-frame cost H_f + g_a. The
baseline divides it by 1, the optimized by b. So the reported cut is

        cut = [(H_f+g_a) − (H_f+g_a)/b] / (H_f+g_a)  =  **1 − 1/b**

**Every symbol cancels.** Verified by substitution over H_f ∈ {20,40,80,200} × g_a ∈ {48,64,96}:
all twelve give **75.0000 %**. The number is invariant to the header size, the signature size, the
encoding and the scheme. At b = 4, 1 − 1/4 = 0.75 exactly — which is why the headline reads
75.00 % and not 74.8 % or 75.3 %.

**So the headline carries exactly one piece of information: b = 4.** And b = 4 is not an
optimization outcome either — it is ⌊Λ·D_max⌋ = ⌊20 × 0.25⌋ = 5, reduced to 4 because b=5 puts fill
time at exactly 250.0 ms and the airtime term pushes it over the bound. **b is fixed by two model
inputs, Λ and D_max.** The optimizer confirms it; it does not discover it.

*(Corollary, useful elsewhere: because H_f cancels, the headline is immune to it. This was later
confirmed the hard way — B1 measured H_f = 44 B, not the assumed 40, and the headline did not move
at all. H_f still matters for T6, b_max, total bytes and channel utilisation.)*

**Why this was not visible earlier.** T2a is the same fact seen from the other side: when freshness
binds, b = ⌊Λ·D_max⌋ is *independent of s*, so dC/ds = 1 and the encoding decouples from the batch.
T2a stated the consequence for compression leverage; it did not state the consequence for **the
headline metric's attribution**, which is stronger and more damaging to the claim as written.

**What each axis actually buys** (A+CBOR baseline 170.252 B/rec → optimized delta/B/b=4 70.998):

| axis | metric it moves | magnitude |
|---|---|---|
| placement × batching | **auth bytes** 104 → 26.0 | 75.00 % — the headline; **78.6 %** of the total saving |
| encoding | **payload bytes** 66.25 → 45.0 | 32.1 % — **21.4 %** of the total saving |
| scheme | *neither* (64 B either way) | selected on **energy / verify-throughput / feasibility**, not bytes |
| | **total bytes/record** | **58.3 %** |

**The honest claim, and the dishonest one.**

* ✗ *"Co-optimizing encoding × authentication placement × signature scheme × batching cuts on-air
  authentication by 75 %"* — implies four contributing axes. **Two of them contribute nothing to
  that number, and the number itself is 1 − 1/b.** This phrasing is in docs/00, the abstract and
  the conclusion, and must go. Presented as a headline it invites the fatal reviewer question
  *"is your main result just the definition of batching?"* — to which, for this metric alone, the
  answer is yes.
* ✓ *"Authentication placement and batching cut on-air **authentication** bytes 75.0 %; encoding
  cuts **payload** bytes a further 32.1 %; together, **total** on-air bytes fall 58.3 %. The scheme
  axis is byte-neutral and is decided on energy and verify-throughput."*

**This does not weaken the thesis — it relocates the contribution.** The defensible co-design claim
is the *joint feasibility* one, which genuinely needs all four axes plus the channel: **at N=50 and
Λ=20 the baselines are not merely wasteful, they are unrunnable** (U = 2.28 for A+JSON, 1.53 for
A+CBOR, vs 0.55 optimized — F12/§6b), and the frontier is 4-objective (bytes, freshness, V, energy)
with hard constraints from three different physical sources. A single-axis study cannot produce that
result. The error was compressing a four-objective feasibility result into a one-number byte claim
and then attributing that number to all four axes.

**Actions.** (i) headline sentence corrected in docs/00, docs/TECHNICAL_NARRATIVE, paper abstract +
conclusion; (ii) the decomposition table above added to the results section — it is *more*
informative than the single number; (iii) `test_headline_decomposition.py` pins the encoding-
independence so the claim cannot silently regress.

---

## F14 — the energy model under-predicts CPU energy by ~32 %, uniformly across configurations
*Opened 2026-07-29 from the composition check; **CLOSED the same day by the first end-to-end
measurement**, which corrected the interim conclusion. Both halves are recorded — the wrong
inference and the measurement that overturned it.*

### What D1 asked
P7b measured every *input* to the energy model — `p_cpu_w`, `p_radio_w`, all per-operation timings —
but nothing measured its *output*. `models.energy.per_record` composes `t_enc + t_sign/b + t_verify/b`
and multiplies by power. A model can be built from correct pieces and still be wrong, because
composition is where the assumptions live.

### Two defects in the harness, found by running it
1. **The prediction included `t_verify`; the pipeline never verifies.** The first run compared a
   sender-side measurement against a sender+receiver model, inflating the prediction ~1.9×. The
   harness now predicts the sender side only and says so in its banner.
2. **The manifest schema did not match the reducer** (`label` vs `kind`/`op`), so windows could not
   be paired. Fixed at source rather than by hand-editing the artifact.

### The measurement (INA219, pi-A, 5 reps per configuration, 60 s windows)

| configuration | predicted | measured | gap | ΔP |
|---|---|---|---|---|
| optimized delta/B, b=4 | 44.25 µJ/rec | **58.38** | **+31.95 %** | 0.732 W |
| A+CBOR baseline, b=1 | 87.83 µJ/rec | **118.83** | **+35.30 %** | 0.755 W |

Well outside the ±10 % acceptance band. It decomposes into two roughly equal factors, both pushing
the same way:

* **Time (+13.3 %)** — measured pipeline 81.0 µs/record against the model's 71.5 µs (components
  re-measured on the Pi in the same process, so like-for-like). The **chain hash is 4.64 µs/record
  and the model has no term for it**; frame assembly accounts for the rest. This is the original
  F14 defect and it stands.
* **Power (+15.5 %)** — the composed pipeline draws **0.732 W**, not the **0.634 W** `p_cpu_w` from
  P7b. That constant is the *median incremental power over eight isolated primitives*; a real
  pipeline has a different instruction mix (bytes/list churn between crypto calls) and draws more.
  **Using one `p_cpu_w` for every configuration is itself a modelling simplification**, and this is
  the first evidence of its size.

Cross-check (Law 6): the energy run's own throughput implies 79.9 µs/record against 81.0 µs from an
independent benchmark — 1.4 % apart, so the two routes corroborate.

### ⚠️ RETRACTION: the interim claim about direction was wrong
Between the composition check and the measurement, this audit stated that the model **"overstates
the optimized configuration's energy advantage by ~4 points."** That was inferred from an *x86
timing* check (+6.73 % at b=4 vs +2.52 % at b=1) on the reasoning that the omitted per-record costs
do not amortize over b. **The end-to-end measurement does not support it:**

| | predicted | measured |
|---|---|---|
| advantage (baseline ÷ optimized) | 1.985× | **2.035×** |

Both configurations are under-predicted by a similar factor, and the **baseline slightly more**
(+35.30 % vs +31.95 %), so the model very slightly **understates** the advantage — 2.5 % in the
opposite direction. The reason the x86 inference misled: at b=1 the omitted framing is charged once
per *record* rather than once per *four*, but the base it is measured against is also ~2× larger
(one full signature per record), and on ARM the second effect dominates. **The claim is withdrawn
and replaced by the measurement.** It was propagated to `models/energy.py`, the paper's limitations
section, OPEN_ITEMS and the status board; all four are corrected.

### What this means for the thesis
* **Byte results are power-free and entirely unaffected.**
* **The energy column is systematically ~32 % low in absolute terms**, and this must be stated. It
  is *not* a fabricated correction factor — nothing is rescaled — it is a measured, reported gap.
* **Relative energy comparisons survive**, because the bias is near-uniform across configurations
  (31.95 % vs 35.30 %). T4's scheme crossover, which compares verify times with the same omitted
  terms on both sides, is unaffected to first order.
* A correct fix needs an **ARM SHA-256 measurement** plus a per-configuration `p_cpu_w`, neither of
  which exists yet. Patching with the x86 hash figure would be the fabrication Law 7 forbids, so the
  gap is documented rather than closed.

*Artifacts: `results/hw/energy/e2e/energy_d1{,_baseline}-summary.csv`, manifests and raw samples.
Harness: `hw/validate_energy_e2e.py`.*

### CLOSURE (same day): both causes found and fixed, gap 32 % → 7.5–14.3 %

**D7 — the chain-hash term.** SHA-256 of one chain link measured on authbc-pi4a with the P1 harness:
**2745.5 ns** over a 45 B input (prev_hash 32 + delta body 13). Added as `Measured.t_hash_s` and
charged **2× per record** — the sender hashes to extend the chain, the receiver re-hashes to verify
it — and it does **not** amortize over b, because the chain is per-record by construction. E5's
optimized row moved 112.0818 → 115.5631 µJ/record, matching the predicted +3.481 exactly.

**D6 — and the premise of D6 was wrong.** The item asked whether `p_cpu_w` is
configuration-dependent. Metered on all four E5 configurations:

| configuration | b | ΔP |
|---|---|---|
| optimized delta/B | 4 | 0.732 W |
| D-over-agg cbor/D | 40 | 0.744 W |
| A+CBOR (Pillar-1) | 1 | 0.755 W |
| A+JSON naive | 1 | 0.760 W |

**A 3.8 % spread — so no, it is not configuration-dependent.** What was wrong is that 0.634 W was
the median over eight *isolated primitives*, which understates any *composed* pipeline by **18.2 %**.
Adopted **0.749 W** (median of the four). Keeping one constant matters: a per-configuration power
would require building and metering a design before it could be modelled, which defeats the model.

**Residual after both fixes**, model vs measurement, sender side:

| configuration | model | measured | gap |
|---|---|---|---|
| optimized delta/B, b=4 | 54.33 µJ/rec | 58.38 | **+7.5 %** |
| A+CBOR, b=1 | 105.81 | 118.82 | **+12.3 %** |
| A+JSON, b=1 | 106.53 | 121.77 | **+14.3 %** |
| D-over-agg, b=40 | 41.46 | 47.02 | **+13.4 %** |

**All of the residual is frame assembly** — list building, byte concatenation and slicing between
crypto calls. It is **deliberately not charged**: that is CPython overhead of a prototype, and a
compiled implementation would carry a fraction of it. Charging it would make the model describe
*our Python code* rather than the design under study. Every energy figure is therefore a **lower
bound by roughly 10–14 %**, and is reported as such.

*Independence note: the timings (`t_enc`, `t_sign`, `t_hash`) come from the P1 micro harness, not
from these energy runs, so the time-residual column above is an independent comparison. `p_cpu_w`
is a measured input taken from these runs, so the power term is not independently validated by
them — that is stated rather than papered over.*

---

## ~~F15~~ — **RETRACTED THE SAME DAY IT WAS WRITTEN (2026-07-29). The finding was wrong.**
*Kept in full, because a retracted finding is evidence about the process and deleting it would hide
an error rather than correct it.*

**What F15 claimed.** That the "≤0.36 % on every quantity" validation of Ma & Chen's broadcast model
was really one comparison (throughput) restated three times, because the p_s and idle-slot columns
had been *back-derived from the measured throughput* rather than measured independently. Two pieces
of "evidence" were offered: (i) the trace columns in `ns3_dcf_residual.csv` disagreed with the model
by +10…+121 %, and (ii) the NS-3/model ratio for p_s tracked the ratio for throughput to 2 parts in
10 000 across all five N.

**Both were wrong.**

**(i) was a data-handling error of mine.** `ns3_dcf_residual.csv` contains **both unicast and
broadcast rows**. I aggregated across all of them; the validation is broadcast-only. Filtering
correctly (`mode == "broadcast"`, median, exactly as `test_broadcast_residual.py` does) reproduces
the audit's published table *to the digit*:

| N | model p_s | measured p_s (ns-3.41) | audit's published value |
|---|---|---|---|
| 5 | 0.7703 | 0.7712 | 0.7712 ✓ |
| 10 | 0.5551 | 0.5564 | 0.5564 ✓ |
| 20 | 0.3154 | 0.3143 | 0.3143 ✓ |
| 35 | 0.2195 | 0.2195 | 0.2195 ✓ |
| 50 | 0.2227 | 0.2234 | 0.2234 ✓ |

The measurements are genuine, independent, and reproduce. Idle-slots-per-busy-period likewise.

**(ii) was an invalid test.** Throughput and success probability are computed from the *same trace*
and are linked by construction — S is a monotone function of the success rate at fixed slot
structure. Their ratios to the model **must** track each other. I treated an expected correlation as
evidence of fabrication. That is the substantive error: the hypothesis was untestable in the form I
tested it.

**What is actually true, having redone it properly** (broadcast-only, median):

| quantity | ns-3.41 | ns-3.48 |
|---|---|---|
| p_success | ≤0.36 % | **≤2.49 %** (at N=35) |
| idle slots / busy period | ≤0.75 % | **≤0.47 %** |
| saturation throughput | ≤0.36 % | ≤1.44 % |

Two small real corrections survive, and only these:

1. **"≤0.36 % on every quantity" was always slightly optimistic** — the idle-slot column reaches
   **0.75 %** at N=10, a figure visible in the p7 audit's own table. The bound should read ≤0.75 %
   for ns-3.41.
2. **On ns-3.48 the agreement widens to ≤2.49 %**, driven by p_s at N=35.

**Process note.** The failing test `test_broadcast_residual.py` is what exposed this: it expected
p_s ≈ 0.214 where my analysis had produced 0.506, and that contradiction is what sent me back to
the data. The tests caught an error in my *analysis*, which is what they are for. The sequence —
publish a finding, propagate it to five documents, then have a test refute it — is the argument for
running the suite *before* propagating, not after.

---

## F16 — T6 is NOT novel. Prior art found before publication, unlike F9 ⚠️
*2026-07-30, from the prior-art check Mohamed asked for. The result is negative and that is the
point: F9 taught this project to search **before** claiming, and this time we did.*

**What T6 claimed to contribute.** An "authentication-exclusion threshold": a link admits
per-frame-verifiable telemetry only if `s_max = M − H_f − g_a ≥ s_min`, with fragmentation closed
off by T3.

**The inequality is established prior art.** Gündoğan, Amsüss, Schmidt and Wählisch (ACM ICN 2021)
perform exactly this computation for 802.15.4/NDN:

> "we assume the 802.15.4 MTU, a data name of 16 bytes, a structural NDN encoding overhead of
> another 16 bytes, and the link-layer header further consumes 23 bytes … This sums up to 55 bytes
> and leaves 73 bytes for the payload and signature. … Ed25519 … 64 bytes … Yet this reduces the
> available space for application data down to 9 bytes"

That is `M − H_f − g_a = s_max`, computed and used to motivate a design. The same reasoning appears
in the post-quantum literature, where NIST signatures are reported as incompatible with the 372 B
maximum of 5G SIB1 — our "tier 1", the signature alone overflowing the frame.

**The fragmentation step is also known.** That a fragmented unit needs every fragment, giving
`(1−p)^n` delivery, is standard in the 6LoWPAN literature ("the loss of only a single fragment can
render the entire packet invalid"), and "sliced signatures" are an actively proposed workaround.

**So T6 is a synthesis of two established facts, not a new theorem.** Demoted accordingly: it is
stated as an *applied threshold* with prior art cited, not as a contribution.

**What survives as ours, stated conservatively:**

1. **The composition made explicit** — that the sliced-signature escape the literature proposes is
   unavailable whenever `ε ≤ p`, because the verifiability target is then spent entirely on the
   first frame (`n_max = 1`). Each half is known; we have not found the two combined into a
   feasibility condition.
2. **The EU868 partition** — which specific LoRa data rates are excluded and by which tier
   (DR0–DR2 by the signature alone; DR3 by six bytes). That is application of a known bound to a
   link nobody had applied it to, and it is a useful negative result, but it is engineering, not
   theory.

**T2a is left flagged, not cleared.** The searches targeted T6. T2a (amplification `A` is operative
only in the MTU-limited regime; under a freshness bound `dC/ds = 1`) has *not* had an equivalent
check and must get one in the A3 pass before any novelty is implied for it.

**Why this matters more than the finding itself.** F9 cost a retraction because a claim was
published before the literature was read. The correct outcome here is unglamorous — we searched,
found prior art, and downgraded a claim we liked. That is the process working.

---

## F17 — a static type gate found three real defects the test suite could not (2026-07-30, FIXED)

**What prompted it.** Housekeeping, not suspicion: `mypy` was added to the toolchain to close a
professionalism gap. It was expected to find nothing, because the suite was green at 1077 tests.
**Expected before running: 0 substantive findings, some annotation noise.** That expectation was
wrong, and the reason it was wrong is the interesting part.

**What it found.** 18 errors, of which three were genuine design defects rather than annotation
noise:

1. **A Liskov violation across the whole `Framer` hierarchy.** The base class declared
   `unpack(frame, **verifier)` and `pack(records, *, b)`; the subclasses declared incompatible
   narrower signatures — `unpack(frame, *, pk)` in A/B/D but `unpack(frame)` in C, and
   `pack(..., sigs, pks, b)` in C alone. Any code holding a `Framer` and calling it polymorphically
   could therefore raise `TypeError` depending on which placement it was handed. The tests never
   caught it because every call site instantiates a *concrete* placement.
   **Root cause — and it is a modelling fact, not an oversight:** placement C is genuinely
   different. It aggregates signatures produced by *other* senders, so it cannot sign internally
   (needs `sigs`/`pks` on `pack`) and it carries its own public keys in the frame (needs no `pk` on
   `unpack`). The hierarchy had encoded that asymmetry by silently diverging instead of stating it.
   **Fix:** one signature for all four placements, with the placement-specific arguments optional
   and *checked at run time* with a message naming the placement. The asymmetry is now documented
   in the base-class docstring rather than implied by a signature mismatch.

2. **BLS-only methods called through the general protocol.** `micro.py` called `.aggregate()` and
   `.aggregate_verify()` on the result of `get_scheme("bls")`, typed as `SignatureScheme` — a
   protocol that does not declare them. The `crypto/base.py` docstring already said "BLS
   additionally exposes aggregate/aggregate_verify", so the *documentation* was ahead of the
   *types*. **Fix:** an `AggregateScheme(SignatureScheme, Protocol)`, so handing a non-aggregating
   scheme to placement C or the aggregation benchmarks is now a type error rather than a runtime
   `AttributeError`.

3. **Three stale `# type: ignore[arg-type]` suppressions** in `encodings/`, silently dead. Found
   only because `warn_unused_ignores = true` was set. A suppression that no longer suppresses
   anything is a claim that the code is unsafe when it is not.

Also fixed, less interesting: `b_max`/`b_max_inline` were annotated `s: int` while every caller
passes a **measured mean** (float) and relies on the floor being taken on the *quotient* — flooring
`s` first gives a different answer. The annotation was wrong, not the code; widening it to `float`
documents why the `//` is where it is.

**What this says about the test suite.** Nothing bad: 1077 tests are the reason the *numbers* are
trustworthy. But tests exercise the paths that are called, and the LSP defect lives exactly in the
path nobody calls — polymorphic use of a base class. Types and tests fail differently, which is why
both are now in `make all`.

**Standing change:** `make typecheck` is part of `make all` and `.pre-commit-config.yaml`. Config in
`pyproject [tool.mypy]` with `warn_unused_ignores`/`warn_redundant_casts` on, so dead suppressions
cannot accumulate again. Zero suppressions remain in `src/` beyond one documented cast in
`encodings/json_enc.py`, where the JSON wire dict is legitimately a different type from the record
dict (`prev_hash` becomes a hex string).

---

## ~~F18 — the LoRa capacity result corroborated against published measurements~~ ⚠️ **RETRACTED 2026-07-30, same day, by Mohamed**

**The claim was: "our simulation is slightly more optimistic than Bor et al.'s measurement-based
model, so N_max = 5 is not an artifact." That is false, and it was false in the direction that
flattered us.** Superseded by F19. Kept visible because the *way* it went wrong matters more than
the finding did.

**What I did wrong.** I extracted this sentence from the PDF and attributed it to their LoRaWAN
result: *"For 1000 nodes per gateway, around 90 % of packets collide, while the average throughput
per device is around 20 frames per hour."* It is from **§6.2, Figure 14 — their PURE ALOHA model**,
not their LoRa model. Their LoRa figure for the same configuration is **~32 %**.

**The aggravating part.** A search snippet had reported exactly the correct split — 32 % LoRaWAN
versus 90 % pure ALOHA. I overrode it from the PDF, got it backwards, and then wrote a ⚠️ warning
into `docs/literature/README.md` telling future readers that the *snippet* had lied. **The snippet
was right. I was the one who misquoted.** "Quote the PDF" is still the rule; it is not a licence to
stop reading which section the sentence came from — a quotation without its figure number is not a
quotation, it is a fragment.

**Why it survived my own check.** The Law 6 gate asks for an expected value stated in advance. I
stated one for the *arithmetic* (offered-load ratio) and it was correct — 25×, reproduced below in
F19. I never stated an expectation for the *attribution*, so there was nothing for the evidence to
contradict. **A number can be right while the sentence around it is wrong.**

---

## F18 (original text, retained for the record — DO NOT CITE)

**The exposure.** `N_max = 5` at DR5 is one of the two load-bearing claims of the low-rate chapter,
and LoRaWAN scalability papers routinely quote node counts in the hundreds to thousands. A reviewer
who knows that literature will read `5` as evidence of a broken simulation. Until now the number
rested on our own NS-3 runs alone.

**What we checked it against.** Bor, Roedig, Voigt & Alonso, *LoRa Scalability: A Simulation Model
Based on Interference Measurements*, Sensors 17(6), 2017 — a model built on measured interference
rather than an analytical idealisation, i.e. an independent and unfavourable comparison.

⚠️ **A secondary source misreported it, and reading the paper mattered.** A search summary
attributed "32 % loss at 1000 nodes" to this paper. The paper says: *"For 1000 nodes per gateway,
around 90 % of packets collide, while the average throughput per device is around 20 frames per
hour."* Had the 32 % figure been used, we would have overstated the disagreement with our own
result. **Quote the PDF, never the summary** — the same discipline as F9 and F16.

**The reconciliation.** Normalising both studies to per-node channel occupancy, computed with our
own `lora.frame_time_on_air_s`:

| | Bor et al. | AUTHBC |
|---|---|---|
| payload / ToA | 20 B / 71.9 ms | **218 B / 363.8 ms** (5.1×) |
| send interval | 180 s at their 1000-node point | **36.4 s** (the 1 % duty-cycle maximum) |
| per-node occupancy | 0.040 % | **1.000 %** (**25×**) |
| criterion | any non-zero throughput | **V ≥ 0.95** |

**Their 1000 nodes carry the same offered load as ≈40 of ours**, and at that load they report ~90 %
collisions. We measure 59 % loss at N=30 and 75 % at N=50. **Our simulation is therefore slightly
more optimistic than their measurement-based model, not more pessimistic** — so `N_max = 5` is not
a simulator artifact. It is what a 218 B frame sent at the maximum legal rate costs.

**Second, independent check** against the textbook pure-ALOHA success curve `e^(−2G)`: measured
0.866 vs predicted 0.852 at N=8; 0.580 vs 0.670 at N=20; 0.253 vs 0.368 at N=50. Better than pure
ALOHA at low load (LoRa capture lets the stronger of two overlapping frames survive), worse at high
load (a gateway has finitely many demodulation paths). **Both deviations are in the physically
expected direction**, which is the useful part — a model that matched pure ALOHA exactly would mean
the simulator was ignoring LoRa physics.

**Limitation this exposed, now stated rather than discovered by a reviewer.** Because the data rate
is a *design variable* here, each run holds one DR fixed, which forfeits the SF quasi-orthogonality
that supplies much of a real deployment's capacity. `N_max = 5` is a **within-one-spreading-factor
bound at the maximum legal rate, not a LoRaWAN network capacity.** Tracked as `OPEN_ITEMS` E7 and
stated in the low-rate chapter.

---

## F19 — what our LoRa simulation actually models, and why `N_max = 5` is a worst case (2026-07-30)

**Supersedes the retracted F18.** Prompted by Mohamed asking two questions I could not answer from
the documentation: *"Bor said 90 % is pure ALOHA and 32 % is LoRaWAN — what is our actual model, and
did we use pure ALOHA or LoRaWAN?"* Both answers required reading source, not notes.

### What Bor et al. report, by figure

| figure | configuration | access | loss @ 1000 nodes |
|---|---|---|---|
| Fig. 6 (§6.1) | 1 channel, 1 SF, 20 B | **LoRa** | ~90 % |
| Fig. 15 (§6.3) | 3 ch × 6 SF = 18 logical | **LoRa** | **~32 %** |
| Fig. 14 (§6.2) | 18 logical | **pure ALOHA** | ~90 % |
| Fig. 11 (§6.2) | 1 channel, 1 SF | **pure ALOHA** | total by 200 nodes |

Their abstract: *"the losses will be up to 32 %. In such a case, pure Aloha will have around 90 %
losses."* **F18 attributed the Figure-14 pure-ALOHA sentence to their LoRa model.** Mohamed was
right; the retraction stands above.

### What we actually simulate

`ns3/authbc-lora-capacity.cc` called `macHelper.SetRegion(LorawanMacHelper::ALOHA)`. Reading
`lorawan-mac-helper.cc::ConfigureForAlohaRegion`, that preset provisions the gateway with
**`maxReceptionPaths = 1`** and **one frequency (868.1 MHz)**. The `EU` preset
(`ConfigureForEuRegion`) provisions **8 reception paths and 3 frequencies**.

So the answer is: **we simulate the LoRaWAN PHY** — real LoRa modulation with the module's
interference and capture model, *not* an abstract ALOHA analysis — **on the module's harshest MAC
preset: one channel, one demodulator, one forced spreading factor.**

### The like-for-like comparison, which does not flatter us

Both studies transmit at the 1 % duty-cycle ceiling (Bor: *"packets were transmitted as soon as
possible, just after the waiting time imposed by the radio duty cycle mechanism"*), so per-node
occupancy is 1 % in both and offered load scales identically as `G = N × 0.01`. **The 25× per-node
load ratio asserted in F18 was an artifact of assuming their traffic was sparse; it is not.**

Their own curve fit `f_MCH_MSF(x) = f_SCH_SSF(x/18)` maps the multi-channel 1000-node point onto
**56 nodes on 1 channel / 1 SF at ~32 % loss**. We measure **74.7 % at N = 50**.

> **We are ≈2.3× more pessimistic than their measurement-based LoRa model.** Most likely cause: the
> single demodulation path. A second concurrent arrival is rejected outright rather than being given
> the capture chance their SX1301 measurements grant it.

**Expected-before-checking (Law 6), stated properly this time:** if the single-demodulator hypothesis
is right, re-running with the `EU` preset (8 paths, 3 channels, same forced SF) must raise `N_max`
**substantially** — and if it does not, the hypothesis is wrong and the loss is coming from the
interference model instead. A `gwRegion` flag has been added to the scenario to run exactly that.

### Consequence for the claim

`N_max = 5` is **not** "LoRaWAN capacity". It is a **worst-case bound: one channel, one demodulator,
one spreading factor.** Labelled that way in the paper, the register and `OPEN_ITEMS` (E8 single-SF,
**E9** single-channel/single-path). The qualitative conclusion the low-rate chapter rests on — that
LoRa is a different regime, not a slow 802.11 — is *strengthened* by being conservative, but the
number must carry its configuration or it is misleading.

### The process lesson, which is the expensive part

F18 passed my Law 6 check because I stated an expectation for the **arithmetic** (the offered-load
ratio) and verified it, while stating none for the **attribution**. The arithmetic was internally
correct and completely irrelevant, because its input premise — that their nodes were sparse — came
from a sentence I had misread. **A verified number inside a misattributed sentence is still wrong,
and it is more dangerous than an obvious error because the verification feels like diligence.**
Extend the rule: when a comparison rests on a source's operating point, state and check the
**operating point**, not only the derived quantity.

---

## F20 — the LoRa arm now has an external baseline, and it agrees (2026-07-30)

**Prompted by Mohamed:** *"why didn't we use Bor et al.'s model and test it with our optimizer and
add them as a comparison?"* There was no good reason. I read the paper *after* the LoRa result
existed and treated it as a yardstick to quote rather than a model to run. It is stated in closed
form and was implementable all along.

### What was implemented

`lora.bor2017_loss_pct()` and `lora.bor2017_n_max()` implement their **Eq. (8)** — a degree-5
polynomial fitted at R² = 0.997 to *total* packet loss (collisions **plus** wrong-payload-CRC),
measured on real SX1301 hardware — together with the scaling laws Eqs. (9)–(11) that generalise it
by the number of non-interfering logical channels.

**Why it is applicable to us despite their 20 B frames and our 218 B ones:** the model is
parameterised by *node count at the 1 % duty-cycle ceiling*. At that ceiling every node occupies
1 % of the channel whatever its SF or frame length, so offered load is `0.01·N` in both studies.
This is the same normalisation that F19 established; here it is load-bearing rather than incidental.

### Validation — against the paper's own prose, not against our expectations

| logical channels | Eq. (8) at N = 1000 | what the paper states |
|---|---|---|
| 1 (1 ch × 1 SF) | **86.6 %** | "around 90 % of all packets are collided" (Fig. 6) |
| 6 (1 ch × 6 SF) | **65.3 %** | "around 68 % for 1000 nodes per gateway" (Fig. 7) |
| 3 (3 ch × 1 SF) | **80.0 %** | "around 75 % … **lost due to collisions**" (Fig. 8) |
| 18 (3 ch × 6 SF) | **32.4 %** | "In total, **32 %** of packets are lost" (Fig. 9) |

Three land within ~3 points. The fourth looks 5 points high until you read the quantity that
sentence names: Fig. 8's 75 % is **collisions only**, while Eq. (8) fits the *total*, so the model
*must* come out above it. Asserted as such in `tests/test_bor2017_external_model.py`.

### The result

| | AUTHBC ns-3 | Bor et al. 2017 |
|---|---|---|
| **N_max at V ≥ 0.95** | **5** | **4** |

**Two independent methods — a discrete-event simulation of the LoRa PHY, and a polynomial fitted to
hardware interference measurements — land one node apart on the number the low-rate chapter rests
on.** That is the external baseline item A7 was missing, and it is a far stronger statement than the
one retracted in F18.

**Do not over-read the agreement.** Below N ≈ 10 their polynomial is dominated by its 1.7833
intercept, which is a fitting artifact (it predicts 1.78 % loss at zero nodes), so their N_max = 4
carries the fit's error rather than a measurement. The agreement is the right *order*, obtained
independently; it is not a precision result.

### The shape disagreement, which is the informative part

There is a **crossover at N ≈ 8**:

| N | AUTHBC loss | Bor loss | |
|---|---|---|---|
| 5 | 0.0 % | 5.1 % | we are **more optimistic** |
| 8 | 13.4 % | 7.0 % | we are 1.9× more pessimistic |
| 30 | 59.0 % | 19.9 % | 3.0× |
| 50 | 74.7 % | 29.9 % | 2.5× |

Consistent with F19's diagnosis: at low load our capture model saves frames their fit's intercept
penalises; at high load our **single demodulation path** rejects concurrent arrivals outright, which
their SX1301-based model does not. The two disagreements have different causes and both are in the
direction the configurations predict — which is why this is corroboration rather than coincidence.

### One defect found in their published model

⚠️ **Eq. (8) is not monotone.** It peaks at x ≈ 723 (86.61 %), falls to 85.01 % at x ≈ 923, then
rises again — i.e. it says adding 200 nodes *reduces* loss. The excursion is 1.6 points on a 0–90 %
curve at R² = 0.997, so it sits inside the fit's own residual and is an artifact of fitting a
quintic, not a claim about LoRa. It is asserted in the test suite rather than smoothed away, so a
future reader meets the explanation instead of suspecting our implementation. It does not touch any
AUTHBC result: our operating region is N ≤ 50, an order of magnitude below the turning point.

### Consequence

`make exp-lora-external` emits `results/raw/lora_external_check.csv`. **A7 is closed for the LoRa
arm** (the 802.11 arm already had Bianchi and Ma & Chen). `N_max = 5` remains labelled as a
worst-case, single-channel/single-demodulator/single-SF bound per F19 — but it is now a
*corroborated* worst case.

---

## F21 — the LoRa arm is a star topology, and what that does and does not invalidate (2026-07-30)

**Prompted by Mohamed:** *"we suppose to do this work to a decentralized ad hoc network — does the
LoRa model and what we simulated apply for this?"* It is the sharpest question asked of this work so
far, and the answer required reading the scenario rather than the notes.

### The mismatch is real

`authbc-lora-capacity.cc` creates `nGateways = 1` and reports
`delivered_frac = received_by_gateway / sent`. It is **N end devices → 1 gateway**. Meanwhile the
802.11 arm is a genuine single-collision-domain broadcast among peers, and the thesis framing —
FANET, 3GPP TS 22.125 §5.2.2 *direct UAV-to-UAV local broadcast* — is decentralised.

This is not a simulator artifact that can be configured away: **LoRaWAN is by specification a
star-of-stars topology and has no peer-to-peer mode.** UAV-to-UAV over LoRa means *raw LoRa* — the
PHY without the LoRaWAN MAC — which the module does not implement. So the two arms of the thesis
were, until now, answering topologically different questions without saying so.

### What transfers anyway, and why

**Collision statistics at a receiver depend on how many transmitters are concurrently in range, not
on what the receiver is plugged into.** From the viewpoint of a single receiver, `N` end devices
sending to a gateway and `N` peers sending to one peer produce the same arrival process. The star
simulation is therefore a valid model of **one receiver in an ad hoc network**, with the mapping

> star with N end devices ≈ ad hoc with N+1 nodes, from one receiver's viewpoint

because in ad hoc the receiver is itself one of the nodes and does not interfere with itself.

### ⚠️ This inverts E9

E9 recorded the `ALOHA` preset (1 channel, **1 demodulation path**) as unrealistically harsh, on the
grounds that a real gateway has 8. That reasoning was right for a *gateway* and wrong for our actual
system. **A UAV peer has one radio and one demodulator.** The preset I flagged as a limitation is the
*appropriate* model for the decentralised case, and the `EU` preset (3 channels, 8 paths) answers a
different question — infrastructure collection — rather than a more realistic version of ours.

`N_max = 5` therefore stands as the **ad hoc** number, and it now stands for the right reason rather
than by accident.

### What the star simulation still does not model

1. **Half-duplex.** A LoRa radio cannot receive while transmitting. Each node is blind for its own
   364 ms frame, ≈1 % of the time, so it misses roughly **2 %** of any given peer's frames (the
   ALOHA vulnerability window is twice the frame time). Small at N = 5, and it is a loss the
   gateway never suffers.
2. **Full replication.** Our `V` is a *per-receiver* metric, identical in definition to the 802.11
   arm. A record reaching **every** peer in one broadcast has probability ≈ `p^(N-1)`: at
   `p = 0.95, N = 5` that is **0.815**, not 0.95. A ledger that requires every node to hold every
   record in a single hop would need gossip or relay, which is an application-layer mechanism
   outside this thesis's scope — but the paper must say so rather than let "decentralised" imply it.
3. **Spatial diversity.** Peers sit at different distances, so capture resolves differently at each
   receiver; a gateway is a single, usually well-sited, vantage point.

### Also found while checking

The `ALOHA` preset sets its sub-band duty cycle to **1 (100 %)** —
`AddSubBand(SubBand(868.0e6, 868.6e6, 1, 14))` — so the MAC does **not** enforce the 1 % limit in our
runs. The 1 % offered load comes from our application period (`appPeriodS = 38.4` s against a
≈384 ms frame) instead. Self-consistent and correct, but it was undocumented, and anyone changing
`appPeriod` without changing the preset would silently violate the regulation the whole LoRa arm is
built around.

### Consequence

E9 is **reframed, not closed**: the `EU`-preset run is still worth doing, but as an
*infrastructure-variant comparison*, not as a correction to the ad hoc number. New item **E10**
records the half-duplex and full-replication gaps. The paper's low-rate section now states the
topology explicitly instead of leaving "LoRaWAN uplinks" to imply it.

---

## F22 — the "LoRaWAN has no peer-to-peer mode" claim, checked against the literature (2026-07-30)

**Prompted by Mohamed:** before accepting F21's reframing (*"what if a ground gateway collected the
ledger instead?"*) and spending an NS-3 rebuild on it, verify that the claim underneath it is
actually true. It was asserted from the specification and from module source, not from literature.

**Verdict: the claim holds, in almost the words used.** Three peer-reviewed sources, all now held in
`docs/literature/`, all Crossref-verified.

### 1. LoRaWAN is star-only — confirmed

Paredes, Kaushal, Vakilinia & Prodanoff, *LoRa Technology in Flying Ad Hoc Networks: A Survey of
Challenges and Open Issues*, Sensors 23(5):2403, 2023:

> "LoRaWAN—a protocol used to create a **star topology** network using LoRa technology. However, when
> it comes to MANETs and FANETs, **LoRaWAN presents some limitations regarding its star topology, its
> medium access control (MAC) layer and its lack of routing procedures**."

> "These network elements typically connect in a **star-of-stars topology**."

Berto, Napoletano & Savi, *A LoRa-Based Mesh Network for Peer-to-Peer Long-Range Communication*,
Sensors 21(13):4314, 2021, in its abstract:

> "A LoRaWAN network **assumes a star topology** where each of the nodes communicates with multiple
> gateways" — and their contribution is a mesh "**not relying on LoRaWAN**… **without the use of
> gateways**."

So peer-to-peer LoRa exists and is an active area, but it is built by *discarding* the LoRaWAN MAC.
That is exactly what F21 asserted.

### 2. Half-duplex and pure ALOHA are specification properties, not our modelling choices

Paredes et al., on LoRaWAN device classes:

> "**Class A**: The end devices of this class are **half-duplex transceivers that implement pure
> ALOHA** for their uplink transmissions… The receiver remains off, except for [the receive windows]."

Berto et al., on their peer-to-peer implementation:

> "Since the employed controller **only permits half-duplex communication**, the overall transceiver
> system should be designed to spend as much time as possible in an active listen state so that
> expensive retransmissions [are avoided]."

**This independently validates two things we had derived ourselves:** our use of a pure-ALOHA uplink
(it is what Class A specifies), and E10's half-duplex caveat (it is a real design constraint that
peer-to-peer LoRa implementers have to engineer around).

### 3. The gap is real, which is useful positioning

Paredes et al.'s own conclusion, from a 2023 survey:

> "Though **not much research work has been conducted on using LoRa as a mesh backhaul for air-to-air
> links**, this technology can be useful to maximize the communications range between UAVs in
> low-data-rate applications."

and earlier: "there is **little research activity on FANETs using LoRa technology**."

### What this changes

**Nothing needs retracting.** F21's reframing stands and is now cited rather than asserted. Three
consequences:

1. The paper's topology caveat now carries `\cite{paredes2023lorafanet,berto2021loramesh}` instead of
   resting on our reading of the specification.
2. **The gateway framing is the honest one for a LoRaWAN simulation.** A LoRa UAV-to-UAV ledger is
   possible, but it is a *different system* — raw LoRa plus a custom MAC and routing — not a
   configuration of what we simulated. Presenting our result as an ad hoc LoRa capacity without that
   caveat would have been wrong.
3. ⚠️ **A limitation of scope, now stated:** where the 802.11 arm is genuinely decentralised, the
   low-rate arm answers the *infrastructure-collected* variant. The two arms bracket the design space
   rather than being the same experiment at two data rates, and the paper says so.

⚠️ **Identified but NOT read, so not cited for any specific number:** *Swarm of Drones Using LoRa
Flying Ad-Hoc Network* (IEEE, 2021) builds a LoRa FANET with DSDV routing; secondary summaries report
it uses listen-before-talk and dedicated TX/RX radios on a single channel — which would corroborate
both our single-channel argument and E10's half-duplex point. **Not claimed here, because the F18
lesson is that a summary is not a source.** Worth obtaining before the defence.

---

## F23 — hardware says the LoRa capacity result is range-limited, and our own radius breaks it (2026-07-30)

**Mohamed supplied the paper** (`zirak2021.pdf`, a scanned IEEE copy with no text layer — read by
rendering the pages) after F22 listed it as identified-but-unread. It turned out to carry more than
the corroboration it was fetched for.

**Zirak, Shashev & Shidlovskiy, "Swarm of Drones Using LoRa Flying Ad-Hoc Network", 2021 ICIT,
pp. 400–405, DOI 10.1109/ICIT52682.2021.9491655.**

### It confirms F21/F22 in the strongest terms yet — from the abstract

> "the Media Access Control (MAC) level protocol **LoRaWAN only supports star topology**. This paper
> contributes towards decentralization by creating a Flying Ad-Hoc Network (FANET) using LoRa … with
> a customized Destination Sequenced Distance Vector (DSDV) routing protocol **optimized for a single
> channel**. Results show that … **Listen Before Talk (LBT) reduces idle wait time**, and **dedicated
> transmitter/receiver improves Packet Delivery Ratio (PDR)**."

Four of our positions, independently stated by people who built the thing:
* **LoRaWAN is star-only** — F21/F22.
* **A single channel is the right choice for an ad hoc LoRa swarm** — `TRADEOFFS.md` §1a, which we
  argued from the sub-band duty cycle and single-radio reception. They reached it by building one.
* **Half-duplex is a real cost with a known fix** — E10. Their fix is *dedicated TX and RX radios*,
  and they measure the improvement (their Fig. 10).
* Their intro also notes LoRaWAN assumes transmission "**in hours or days** … But the frequency of
  data transmission in a swarm will be much greater … **in seconds or milliseconds**" — precisely the
  mismatch our low-rate arm quantifies.

⚠️ One position of ours it **does not** support: they use **LBT**, not pure ALOHA. Our uplink is pure
ALOHA (correct for LoRaWAN Class A, per F22), so a real LoRa FANET with carrier sense would collide
*less* than we model. One more respect in which `N_max = 5` is conservative.

### The finding it actually delivered: we do not model link loss at all

Their **Table I** is a hardware PDR-versus-range measurement over 1000 packets, first hop, field
test — with two drones and a base station, so contention is negligible and the numbers isolate
**range-dependent link loss**:

| range | 200 m | 500 m | 600 m | 1000 m |
|---|---|---|---|---|
| measured PDR | 0.9711 | **0.9550** | **0.9399** | **0.9045** |

**Our scenario is configured with `radiusMeters = 1000` and `realisticChannelModel = false`.** At
that range we simulate **zero** link loss and report delivered = 1.0000 at N ≤ 5. Hardware measures
**0.9045**. *Our idealised channel is 9.6 percentage points optimistic at our own deployment radius.*

**Stated before computing (Law 6):** link loss and collision loss are independent, so delivery is
`P_link(range) × P_no_collision(N)`; therefore any range whose measured link PDR is already below
0.95 must make V ≥ 0.95 unreachable at *every* node count, and their table crosses 0.95 between 500
and 600 m. Computed:

| range | N_max at V ≥ 0.95 |
|---|---|
| 200–500 m | **5** |
| 600–1000 m | **0** |

Exactly as predicted, which is the useful part: the prediction was structural, not fitted.

### Consequence — the headline survives, with a qualifier it did not have

**`N_max = 5` holds only within ≈500 m.** Beyond that the criterion fails on path loss alone, before
a single collision, and capacity cannot rescue it. At the 1000 m radius our own scenario configures,
`N_max = 0`.

This does not overturn the low-rate chapter's argument — LoRa remains a different regime, and the
result is *conservative* in every other respect (single channel, single demodulator, pure ALOHA
rather than LBT). But a capacity number quoted without its range is incomplete, and ours was. It is
the LoRa counterpart of the 802.11 arm's known result that the idealised channel is 39 % optimistic
at 500 m — the same class of error, now caught on both arms.

Implemented as `lora.zirak2021_link_pdr()` and `lora.max_range_for_verifiability()`, with the table
asserted in tests and the range sweep emitted by `make exp-lora-external`. Tracked as **E12**.

---

## F24 — a supplied PDF was the wrong paper, and the filename is why it nearly slipped (2026-07-30)

Mohamed supplied two sources. One (`pueyo2021_beyond_star_of_stars.pdf`) is correct and is now the
strongest confirmation the topology claim has. The other, saved as **`klimiashvili2020.pdf`** and
intended to be *"LoRa vs. WiFi Ad Hoc: A Performance Analysis and Comparison"*, is a **different
paper entirely**:

> Sikder & Haque, *"Optimization of Idealized Quantum Dot Intermediate Band Solar Cells Considering
> Spatial Variation of Generation Rates"*, IEEE Access, 2013, DOI 10.1109/ACCESS.2013.2265094.

**Checked across the whole document, not just page 1:** 8 pages, **0** occurrences of "LoRa",
"WiFi", "Wi-Fi" or "ad hoc"; **54** of "solar", 20 of "intermediate band". It is a solar-cell physics
article. The repository served the wrong file, or the wrong file was saved.

**Why this is worth a finding rather than a shrug.** The filename encoded a plausible
author-year (`klimiashvili2020`) matching what was requested. Had the sweep been done at volume —
or had the file been registered from its name and read later — a citation to a solar-cell paper
could have entered the bibliography under a networking claim. That is the same failure mode as F18
(trusting a label instead of the content), reached by a different route.

**Standing rule, now applied to every supplied PDF:** *open it and confirm the title, authors and
venue against the record before it is registered or cited* — cheap, and it has now caught something
twice.

**Consequence:** "LoRa vs. WiFi Ad Hoc" remains **wanted, not held** (`docs/literature/README.md`
§4c, item 1). It is still the highest-value outstanding source, because it is our two-arm structure
as somebody else's entire paper.

---

## F25 — the NS-3 variant runs: E9 answered, E12 answered differently than expected (2026-07-30)

Four sweeps, expectations written to `EXPECTATIONS.md` **before** launching (Law 6), DR5, 218 B,
36.378 s period, 3600 s, 3 seeds, N ∈ {2,3,5,8,10,15,20,30,50}.

### 0. The baseline reproduces byte-for-byte

`aloha/ideal/r=1000` re-run against the frozen `lora_capacity.csv`: **identical on every row**. All
the scenario edits since (the `gwRegion` flag, the `channelModel` flag, the payload guard) are
behaviour-preserving for the frozen configuration.

⚠️ **A trap found on the way, now fixed.** The scenario's default `payloadBytes` was **231 B**, above
the module's enforced RP002 Table 12 limit of **222 B** at DR5. The MAC silently rejects every
oversized packet, so a manual run with the defaults sent *nothing* and surfaced only as the generic
"no packets were sent" abort 3600 simulated seconds later. Default corrected to 218 B and an
**early, explicit guard** added that names the limit and the DR. This cost real debugging time and
would have cost more later.

### 1. E9 — the gateway preset: N_max = 8, and my prediction was wrong

**Predicted N_max ≥ 14**, from Bor et al. Eq. (10) (3 channels ≈ 3× nodes) plus the removal of the
single-demodulator bottleneck. **Measured: 8.**

| N | `aloha` (1 ch, 1 path) | `EU` (3 ch, 8 paths) | ratio |
|---|---|---|---|
| 8 | 0.8656 | **0.9958** | 1.15× |
| 10 | 0.7731 | 0.9370 | 1.21× |
| 20 | 0.5795 | 0.8322 | 1.44× |
| 50 | 0.2532 | **0.6781** | **2.68×** |
| 100 | — | 0.5308 | — |

**Why the prediction failed, and it is the interesting part.** The gateway preset *does* deliver
roughly the 3× the channel count implies — but only in **aggregate delivery at high load** (2.68× at
N=50, still rising). It buys almost nothing at the **V ≥ 0.95 threshold**, because that threshold
sits on a very steep part of the curve: EU passes at N=8 with 0.9958 and fails at N=10 with 0.9370.
A 3× reduction in offered load moves a near-vertical curve sideways by very little.

**This is the same duality the 802.11 arm shows between saturation (U<1) and the measured V≥0.95
boundary:** a capacity metric and a strict-reliability metric respond very differently to the same
change. Reporting only N_max would have hidden a 2.68× improvement; reporting only aggregate
delivery would have implied a threshold gain that does not exist.

⇒ **Infrastructure collection (a ground gateway) buys ~2.7× the aggregate delivery at high load but
only 5 → 8 nodes at V ≥ 0.95.** E9 answered.

### 2. E12 — shadowing changes *nothing* at our ranges, and that is the finding

`shadowing` at r = 1000 and r = 500 returned results **identical to `ideal` on every row**. The
falsifier stated in advance was: *"if shadowing changes nothing at N=2, the shadowing model is not
active and the run is invalid — do not report it as no-effect."* So it was tested rather than
believed:

| range | `ideal` | `shadowing` |
|---|---|---|
| 3500 m | 1.0000 | 1.0000 |
| **4000 m** | **1.0000** | **0.5152** |
| 5000 m | 0.0303 | 0.0152 |

**Shadowing is correctly wired.** It simply cannot bite at 500–1000 m, and the link budget says why:
with `LogDistance(n = 3.76, 7.7 dB @ 1 m)`, 14 dBm TX and the module's **−130 dBm** SF7 gateway
sensitivity, the margin is **28.8 dB at 500 m and 17.5 dB at 1000 m**. An ~8 dB shadowing σ cannot
erode that. Simulated failure onset is ≈4200 m — confirmed, ideal drops to 0.626 at 4000 m.

**⇒ The correct conclusion is not "shadowing was missing". It is that our propagation parameters
describe a far better link than a real drone-to-drone channel, and no option the scenario exposes
fixes that.** Hardware measures 9.6 % loss at 1000 m (F23) where our model, with or without
shadowing, has 17.5 dB of margin and loses nothing.

**E12 resolution:** the range qualifier stands and is now **empirically justified rather than merely
stated** — we asked whether the simulator could produce the measured link loss and established that
it cannot at these ranges. Composing the two terms remains the honest treatment: our simulation
supplies `P_no_collision(N)`, hardware supplies `P_link(range)`, and `exp-lora-external` multiplies
them. Recalibrating the path-loss exponent against Zirak's table would be the alternative, and is
recorded as future work rather than done here, because fitting a propagation model to nine points
from one field campaign would trade a stated limitation for a hidden one.

---

## F26 — intensive audit of the NS-3 simulations: two errors of mine, one broken number (2026-07-30)

Mohamed asked for the simulations to be revised, audited and attacked. Seven issues found across the
four scenarios. **One invalidates a headline number, two are errors in my own earlier write-ups.**

### ⚠️⚠️ A1 (CRITICAL) — `N_max = 5` is not supported: frozen phases + a 3-seed sample

Every device shares **one exact period** (`Simulator::Schedule(m_interval, …)`, no jitter, no drift)
and LoRaWAN ALOHA has **no backoff to re-randomise**. Relative phases are therefore **frozen for the
entire run**: a pair that collides on its first transmission collides on *every* transmission, and a
pair that misses never collides. Delivery is consequently **bimodal**, not noisy-around-a-mean.

Per-seed `delivered_frac`, 30 seeds, the exact frozen configuration:

| N | reported (3 seeds) | **30-seed mean** | median | σ | min | seeds failing V≥0.95 |
|---|---|---|---|---|---|---|
| 4 | 1.0000 | **0.8981** | 1.0000 | 0.200 | 0.2500 | **27 %** |
| 5 | **1.0000** | **0.8905** | 1.0000 | 0.211 | 0.2000 | **27 %** |

**Seeds 1–3 happened to land on 1.0000 for both. That is luck, and it is the whole basis of
`N_max = 5`.** On a 30-seed mean, *N = 4 also fails*. Three seeds cannot characterise a bimodal
distribution, and comparing its **mean** against a hard threshold is the wrong statistic regardless
of sample size.

**Is the bimodality physical or an artifact?** Partly both, and the arithmetic decides it:

| crystal tolerance | relative drift over 3600 s | enough to clear a 2×364 ms collision? |
|---|---|---|
| ±20 ppm (realistic SX127x) | 144 ms | **no** |
| ±100 ppm | 720 ms | marginal |
| ±500 ppm | 3600 ms | yes — and measured values stop being quantised |

So for a *naive exact-period sender*, frozen phases are **physically plausible within a one-hour
window**. But real LoRaWAN Class A devices are specified to randomise transmission timing precisely
to avoid this, and the module's `PeriodicSender` does not model that. An opt-in `--clockPpm` flag was
added (**default 0, so the frozen configuration is bit-for-bit unchanged** — verified: N=8 still
gives 0.8656).

**⚠️ This is a decision for Mohamed.** `N_max = 5` should be either (a) re-derived from ≥30 seeds and
reported as a distribution rather than a mean, or (b) re-run with a sender that randomises timing as
the standard requires — probably both. It is the same artifact class the 802.11 arm already guards
against, with this comment in `authbc-delay.cc`: *"De-synchronise the sources: identical start times
would make every node's periodic transmission collide deterministically, which is an artifact, not
DCF behaviour."* **We fixed it on one arm and never applied it to the other.**

### ⚠️ A2 (MAJOR, my error) — there is no capture in our LoRa runs, and I claimed there was

The scenario selects `LoraInterferenceHelper::ALOHA`, whose matrix is `+inf` on the same-SF diagonal
and `−inf` off it: **any co-SF overlap is unconditionally fatal, and different SFs never interfere.**
Since we force a single SF, **every overlap destroys both packets — there is no capture whatsoever.**
Goursaud's diagonal is 6 dB, which *is* capture.

**I repeatedly attributed our low-N behaviour to capture** — in F19, F20, F25, the literature register
and the paper ("capture working", "our capture model saves frames"). **All of it is wrong.** Measured
cost of the choice:

| N | ALOHA matrix (used) | Goursaud (capture) | gain |
|---|---|---|---|
| 8 | 0.8656 | 0.8984 | +3.3 pts |
| 50 | 0.2532 | **0.3453** | **1.36×** |

The real reason we beat the Poisson curve `e^(−2G)` at low N is that **traffic is periodic, not
Poisson**: for periodic sources the escape probability is `(1−2τ/T)^(N−1)` = 0.868 at N=8, against
0.8656 measured — a near-exact match, and nothing to do with capture. Capture is a *further* 3–9
points we are giving away, so this makes our result more conservative than stated, for a reason we
now understand rather than guess at.

### A3 (MAJOR) — nothing moves, in a *Flying* ad-hoc network study

All four scenarios use `ConstantPositionMobilityModel`. No Doppler, no link churn, no distance
variation over time. Defensible for the 802.11 saturation analysis (MAC contention in one collision
domain is mobility-independent to first order, provided nodes stay in range) but a real gap for the
LoRa arm, where F23 established that range dominates.

### A4 (MODERATE, latent) — `n_max` takes the *last* passing N, not the first failure

`run_lora_capacity.py` does `if ok: n_max = n` inside the sweep with **no break**. On a monotone
curve this is harmless; under the noise A1 documents it would silently report a higher capacity than
the data supports. It has not bitten yet only because the reported means happened to be monotone.

### A5 (MODERATE) — no variance is reported anywhere

None of the NS-3 drivers emit a standard deviation, confidence interval, or min/max — only means
over 3 seeds. A1 is the direct consequence: a σ of 0.21 was invisible in the output.

### A6 (MINOR, latent) — `sent` counts PHY transmissions, so MAC drops are invisible

`sent` hooks `StartSending` on the device PHY, so a packet dropped by the MAC (e.g. duty-cycle
refusal) never enters the denominator and `delivered_frac` would flatter the result. **Verified not
biting today**: `sent_mean` is identical between the `aloha` and `EU` presets at every N and matches
`n × 3600/36.378` analytically, so no drops occur at the current app period. It would mislead
silently if `appPeriod` were reduced below the duty limit.

### A7 (MINOR) — no warm-up exclusion

No scenario discards a startup transient. Negligible at present durations (queues fill in
milliseconds against 30–3600 s runs) and the 802.11 counting window is correctly matched to its
denominator, so this is noted rather than actioned.

---

### What the audit confirmed as *correct*

Worth recording, because these were checked rather than assumed:

* **Seeding**: `SetSeed(1)` + `SetRun(seed)` in all four, and in every case **before** any object
  creation — the standard ns-3 replication idiom, correctly applied.
* **802.11 counting window**: sinks stop *with* sources and the denominator is exactly the source
  window (the F8 tail-drain fix); the head is clean too.
* **802.11 de-synchronisation**: jitter present and explicitly justified in a comment.
* **Broadcast scaling**: `rxScale = N−1` correctly converts summed sink bytes to channel goodput.
* **Baseline reproducibility**: the frozen `lora_capacity.csv` reproduces **byte-for-byte** after all
  scenario edits.
* **EU preset not inflated**: hypothesised that duty-cycle drops might flatter it; tested and
  rejected — `sent` is identical across presets.

---

## F27 — second audit pass: methods and scientific honesty, both arms (2026-07-30)

F26 attacked the simulations as engineering. This pass attacks the *methods* — whether what we claim
matches what we computed, and whether the two arms mean the same things by the same words.

### 1. The published validation bands reproduce exactly — but nothing was enforcing them

Recomputed from the frozen `ns3_matrix.csv`, using the convention docs/02 uses,
**(simulation − model) / model**:

| mode | N=5 | N=10 | N=20 | N=35 | N=50 | band |
|---|---|---|---|---|---|---|
| unicast (Bianchi) | +0.46 | **+1.28** | +0.94 | +0.42 | **−0.49** | **+1.28 / −0.49 %** |
| broadcast (Ma & Chen) | +0.25 | +0.06 | +0.20 | **−1.44** | −1.12 | **+0.25 / −1.44 %** |

The unicast band is **exactly** the +1.28/−0.49 % the abstract claims. ✅

⚠️ **The denominator matters and was never stated.** With `(sim − model)/sim` the same data gives
−1.26/+0.49 %. Same magnitudes, opposite signs. A reader cannot check our arithmetic without knowing
which we used, so the convention is now asserted in a test.

⚠️ **The abstract's "confirmed to within 2.49 %" is the *success-probability* deviation, not
goodput.** Goodput agrees to **1.44 %**. Quoting the worse of two metrics is the conservative
direction, but they are different quantities and the sentence does not say which. Both are now
pinned separately.

**The actual gap: no test asserted any of this.** The frozen gate re-derives the CSVs and the unit
tests exercise the models in isolation, but nothing compared the two. A model change could have left
a stale validation claim in the abstract with every gate green. `tests/test_validation_bands.py`
(16 tests) now closes that, including a test that the naive Bianchi-reduced-to-broadcast is badly
optimistic — the F9 result, previously asserted nowhere.

### 2. ⚠️ "V ≥ 0.95" means three different things, and the paper uses one symbol for all three

| where | what it is | epistemic status |
|---|---|---|
| optimizer constraint (802.11) | `V = 1 − p_loss`, with **p = 0.05 assumed** | **an input**, not a result |
| capacity boundary (802.11) | V measured in NS-3 as channel load rises; crosses 0.95 at U ≈ 2.80 | measured |
| LoRa capacity | `delivered_frac` measured at the gateway | measured |

**The consequence is uncomfortable and should be stated.** For placements A, B and C the optimizer's
`verifiability()` returns `1 − p` — **independent of encoding, batch size and scheme**. With p fixed
at 0.05 it returns exactly 0.95. So the "keep V ≥ 0.95" half of the pre-registered criterion is
satisfied *by construction, with zero margin*, for every configuration we actually adopt. It can only
fail for placement D, where V = (1−p)^n.

That does not make the byte result wrong — the ≥40 % byte cut is the falsifiable half and it was met.
But **the criterion is weaker than it reads**, and a reader entitled to think both halves were at risk
was not told otherwise. Stated plainly rather than left to be discovered.

### 3. ⚠️ Two `Placement` enums, and identity comparisons that fail silently between them

`models/energy.py` defines `Placement(StrEnum)`; `placement/wire.py` defines `Placement(IntEnum)`
whose integer values are part of the frozen frame format. **They share member names.** Seven
`is Placement.X` comparisons across `optimizer.py` and `energy.py` therefore evaluate `False` when a
caller imports the wrong one — with **no error**.

Concretely: `verifiability(wire.Placement.D, 4, 0.05)` returned **0.95** instead of **0.8145** —
overstating block-level loss robustness by 17 %.

**Live or latent?** Latent. `bench/experiments.py` imports the correct one, no `src/` file imports
both, and `mypy` covers `src/`. **But it is not hypothetical: it caught me during this session**, in
ad-hoc analysis code, which is exactly where it would catch anyone — such scripts are not
type-checked and the failure is silent. `verifiability()` now raises `TypeError` naming both modules.
The remaining six comparisons are unguarded and tracked.

### 4. Confirmed correct on this pass

* **Ma & Chen implementation is faithful.** τs = 2/W₀ (eq. 5), p_bs (eq. 7), p_ss = nτs(1−τs)^(n−1)
  (eq. 8 — the journal version, and the docstring records that the 2007 letter's eq. (6) misprints
  it as a collision probability). CFP truncation at 12 stages is justified: τ_f falls by W₀ per
  stage, so stage 6 is below 1e-9 of the first.
* **No correction, calibration or fudge factors anywhere** in `src/authbc/models/` — grepped for.
* **Throughput units are consistent**: the model returns *payload* bits/s and `channel_utilisation`
  divides by `8 × frame_bytes` of the same payload.
* **`channel_utilisation` uses a saturation model for a non-saturated load** — a deliberate and
  documented conservatism, since S_sat(n) assumes all n backlogged. Its direction was independently
  validated by D3 (98.8 % delivery still at U = 1), so it is conservative by a *measured* ≈2.8×,
  not an assumed factor.
* ⚠️ Minor: `channel_utilisation` returns exactly `0.0` for `n_local == 1`. A lone sender does not
  contend, but it does occupy airtime, so the true utilisation is small-but-positive. Harmless (N=1
  is not an operating point) and noted rather than changed.

---

## F28 — E13 fixed: `N_max` corrects from 5 to 3, and the simulation now matches theory (2026-07-30)

The fix for the frozen-phase artifact (F26/A1). **A headline number changes.**

### What was done

1. **`JitteredSender`**, a small application in our own scenario file — the module's `PeriodicSender`
   could not be subclassed (`SendPacket()` non-virtual, interval and event handle private).
   ⚠️ **The jitter is one-sided by construction**, `[T, T+J]`, never earlier. A symmetric ±J would
   let half the transmissions arrive sooner than the duty-cycle interval and silently violate the
   1 % EU868 limit that the whole LoRa arm's Λ and batch argument rest on.
2. **Seeds raised from 3 to 30** as the driver default, with min/max/σ/failing-count now emitted.
3. Default `--tx-jitter` = 1.0 s ≈ 2.7 % of the duty interval.

### The result

| N | old (3 seeds, exact period) | **new (30 seeds, jittered)** | analytic `(1−2τ/T)^(N−1)` |
|---|---|---|---|
| 2 | 1.0000 | 0.9717 | 0.9800 |
| 3 | 1.0000 | **0.9598** ✅ | 0.9604 |
| 5 | 1.0000 | **0.9167** ❌ | 0.9224 |
| 10 | 0.7731 | 0.8292 | 0.8337 |
| 50 | 0.2532 | 0.3755 | 0.3716 |

> ### ⚠️ `N_max` = **3**, not 5.
> The old 5 came entirely from seeds 1–3 landing on 1.0000 by luck against a bimodal distribution.
> A 30-seed control **without** jitter gives 3 as well, so the correction is the sampling, not the
> jitter; the jitter fixes the *shape* (the catastrophic tail at N=5 lifts from 0.20 to 0.70).

### The strongest evidence that the fix is right

Mean absolute deviation from the closed-form periodic-ALOHA escape probability:

* old data: **0.0688** (6.9 points)
* corrected data: **0.0059** (0.6 points) — a **12× improvement**

The frozen-phase artifact was exactly what pushed the simulation away from the analytical model it
should track. Correcting it brings the two into agreement across the whole sweep, and the corrected
`N_max = 3` is precisely what theory predicts: `0.98² = 0.960 ≥ 0.95`, `0.98³ = 0.941 < 0.95`.

### Three independent lines now agree

| method | N_max |
|---|---|
| our corrected NS-3 simulation | **3** |
| closed-form periodic ALOHA | **3** |
| Bor et al. 2017, measurement-fitted | **4** |

Stronger corroboration than the retracted F18 ever claimed, and obtained by fixing our own defect
rather than by reinterpreting someone else's figure.

### A second benefit that was not the goal

The frozen configuration sat at **exactly 1.0000 %** duty cycle. EU868 requires **< 1 %**, strictly.
One-sided jitter raises the mean interval to 36.878 s and the duty to **0.9864 %** — the corrected
configuration is strictly compliant where the old one sat on the boundary.

### Artifacts

`results/raw/lora_capacity.csv` regenerated (30 seeds, jittered) and now carries min/max/σ per row.
The superseded 3-seed file is kept as `lora_capacity_3seed_SUPERSEDED.csv`; `lora_capacity_30seed.csv`
is the no-jitter control. **Historical findings F19–F26 still quote 5 in their narratives and are
left untouched — they are the record of how the error was found.**

---

## F29 — the channel model was validated at 1400 B but applied at 72–288 B. Now measured. (2026-07-30)

**The gap.** Every published agreement band came from `ns3_matrix.csv`, which contains **frameSize
1400 only** — as do `ns3_dcf_residual` and `ns3_sensitivity`. But `N_max`, the feasibility region and
the whole co-design result are computed at **72–288 B**, where per-frame overhead (preamble, DIFS,
backoff) dominates instead of payload: the model puts broadcast at 1.50 Mb/s at 72 B against
3.13 Mb/s at 1400 B. Validating in one regime and applying in another is a real methodological hole,
and it was not stated anywhere.

**Now measured**, 3 seeds × N ∈ {5,10,20,35,50}, both modes, at both ends of the operating range:

| frame | unicast (Bianchi) | broadcast (Ma & Chen) |
|---|---|---|
| **72 B** | **−2.37 .. −1.51 %** | **−0.21 .. +0.35 %** |
| **288 B** | −1.19 .. +0.06 % | −1.25 .. +0.36 % |
| 1400 B (published) | +1.28 .. −0.49 % | +0.25 .. −1.44 % |

**The load-bearing answer is favourable.** `N_max` depends on the *broadcast* model through
`channel_utilisation`, and broadcast agrees to **±0.36 %** across 72–288 B — **tighter than the
±1.44 % measured at 1400 B**. The model does not degrade in the regime we actually use; it improves.

⚠️ **One real finding: unicast carries a systematic negative bias at small frames** — every N at
72 B over-predicts by 1.5–2.4 %, which is outside the published +1.28/−0.49 band and is a *bias*,
not scatter. Plausibly the anomalous-slot effect (Tinnirello et al.), whose relative weight grows as
the frame shrinks. It does not touch the headline, because the co-design result runs on broadcast,
but the unicast band should be quoted **as measured at 1400 B** rather than as general.

**Artifacts:** `ns3_matrix_72B.csv`, `ns3_matrix_288B.csv`. `run_matrix.py` gained `--out` so
small-frame sweeps are additive rather than overwriting the frozen 1400 B matrix.

---

## F30 — E22/E23/E24 re-run at 30 seeds: one band was noise, one headline number moves (2026-07-30)

Mohamed asked whether the simulation stage was clean. It was not: the LoRa arm had been sampled
hard (F26/F28) and **the 802.11 arm never had.** Re-run at 30 seeds.

### E22 — the published bands, re-measured

| frame | mode | 10-seed (published) | **30 seeds** | worst SE |
|---|---|---|---|---|
| 1400 B | unicast | +1.28 / −0.49 % | **+1.29 / −0.40 %** | ±0.13 % |
| 1400 B | broadcast | +0.25 / **−1.44 %** | **+0.24 / −0.51 %** | ±0.39 % |

**The unicast band is confirmed.** ✅ The broadcast band's −1.44 % endpoint was **sampling noise**:
at 30 seeds it tightens to **−0.51 %**. So the broadcast model agrees *better* than we published,
and the abstract's "within 2.49 %" was doubly conservative — it quoted the success-probability
figure (F27) *and* a noise-inflated goodput endpoint.

### E24 — small frames, confirmed at 30 seeds

| frame | unicast | broadcast |
|---|---|---|
| 72 B | −1.40 / −2.60 % | **+0.21 / −0.03 %** |
| 288 B | +0.33 / −1.07 % | **+0.09 / −0.12 %** |

**Broadcast — the model `N_max` depends on — holds to ±0.21 % across the whole operating range**,
tighter than at 1400 B. The F29 conclusion survives a 10× larger sample. ⚠️ Unicast's systematic
negative bias at 72 B is **confirmed, not noise**: −1.40/−2.60 % with SE ±0.06 %.

### ⚠️ E23 — the delay crossing moves, and it feeds a headline number

The measured `V = 0.95` crossing was read off **5 seeds**: `U ≈ 2.797`. At 30 seeds it is
**`U = 2.435`** — a 13 % shift, and the same under-sampling class as E13.

| operating point | published (U=2.797) | **corrected (U=2.435)** | ratio then → now |
|---|---|---|---|
| compliant 50 Hz/100 ms | 35 → **116** | 31 → **100** | 3.29× → **3.23×** |
| relaxed 20 Hz/250 ms | 103 → **233** | 88 → **213** | 2.26× → **2.42×** |

**The absolute capacity figures fall by 10–14 %; the co-design ratio is essentially unchanged.**
That is the reassuring part: the *claim* is the ratio, and it is robust to the correction, while the
absolute numbers — which we already report at two thresholds precisely because they are
threshold-sensitive — need restating as **213** and **100**.

**Pattern worth naming.** Three separate headline numbers (`N_max`, the delay crossing, a validation
band endpoint) were each distorted by small-sample means. None was a modelling error; all were
sampling. The fix in every case was more seeds and reporting spread, and the drivers now default to
30 seeds and emit min/max/σ.

---

## F31 — the 30-seed data promoted to frozen; hardware stage accepted as designed (2026-07-30)

Closing out the three items F30 left open.

### 1. The 30-seed matrices are now the frozen artifacts

`ns3_matrix.csv` (300 rows) and `ns3_delay.csv` replaced their 5/10-seed predecessors, which are
kept as `*_SUPERSEDED_lowseed.csv`. The small-frame sweeps `ns3_matrix_72B/288B.csv` are likewise
30-seed.

**Reasoning for promoting rather than footnoting:** the frozen gate exists to catch *drift*, not to
preserve a worse measurement. Keeping a 10-seed matrix as canonical while citing 30-seed numbers in
the text would have left two values for one quantity — exactly the drift the gate is for.

Bands re-baselined everywhere — paper, `docs/02`, and the 19 tests in `test_validation_bands.py`:

| | was (low seed) | **now (30 seeds)** |
|---|---|---|
| unicast | +1.28 / −0.49 % | **+1.29 / −0.40 %** |
| broadcast goodput | +0.25 / −1.44 % | **+0.24 / −0.51 %** |
| V=0.95 crossing | U ≈ 2.797 | **U = 2.435** |
| capacity at V≥0.95 (compliant) | 35 → 116 | **31 → 100** |
| capacity at V≥0.95 (relaxed) | 103 → 233 | **88 → 213** |

### 2. The unicast small-frame bias is now stated, not absorbed

The abstract now says the band is quoted **at the 1400 B frame it was measured on**, that broadcast
tightens to ±0.21 % at 72 B, and that unicast carries a systematic −1.4 to −2.6 % bias there.

Reporting it costs nothing — the co-design result runs on the *broadcast* model — and absorbing it
would have been the kind of quiet correction Law 7 forbids. Its likely cause (the anomalous-slot
effect, whose relative weight grows as the frame shrinks) is a hypothesis we have **not** tested, and
it is labelled as such rather than asserted.

### 3. Hardware stage accepted as designed

No further work. The audit's conclusion stands: the rig measures what `RIG.md` designed it to
measure, and the TX/RX radio figure was obtained correctly with the single documented sync wire.
Two real defects were found and fixed (Pi-B's venv lacked `gpiod`; the capture recorded no
per-sample host time), and a class of silent mis-reduction now **refuses** rather than returning
numbers biased −3 to −20 %.

⚠️ **Recorded so it is not re-litigated:** Pi-B CPU energy is *not* a model input — `experiments/e5`
takes a single `p_cpu_w` from the DUT — so measuring it would be a **new deliverable**, not the
closing of a gap. It would need a second sketch pin, a CSV schema change, capture and reducer
changes, plus the wire and its 10 kΩ pulldown. Not worth it unless a cross-platform energy
comparison becomes a goal.

### The pattern this whole audit sequence exposed

Three headline numbers — LoRa `N_max`, the delay crossing, and a validation-band endpoint — were
each distorted by **small-sample means against thresholds**. None was a modelling error; every one
was sampling. The models were right the whole time. The fix in each case was more seeds and
reporting spread, and the drivers now default to 30 seeds and emit min/max/σ so the next such error
is visible in the artifact itself rather than discoverable only by re-running.

---

## F32 — Direction C step 1: the standard LoRaWAN ns-3 traffic model distorts results (2026-07-30)

**Question.** The ns-3 LoRaWAN literature generates traffic with *equal period, random initial
phase*. Because the period is exact and ALOHA has no backoff, relative phases are then frozen for
the whole run (F26/A1). Does that measurably distort published-style results, or is it only a
small-N curiosity we happened to trip over?

**Pre-registered** in `scratchpad/C1_EXPECTATIONS.md` with three explicit falsifiers, before running.

**Design.** N ∈ {5, 20, 100} × jitter ∈ {0, 1.0 s} × **30 seeds** = 180 runs. Statistics chosen for
the *shape* of the data, not by habit: the frozen distribution is **bimodal**, so variance is tested
with **Levene** (robust to non-normality — an F-test would be invalid) and location with
**Mann-Whitney U** (non-parametric).

| N | CV frozen | CV jittered | ratio | Levene *p* | MWU *p* | mean shift |
|---|---|---|---|---|---|---|
| 5 | 23.7 % | 8.2 % | 2.91× | **0.19 — not significant** | 2.8e−3 | +2.9 % |
| 20 | 19.9 % | 7.0 % | **2.82×** | **2.6e−6** | 1.8e−2 | **+10.6 %** |
| 100 | 26.7 % | 3.4 % | **7.88×** | **2.7e−8** | 4.5e−4 | **+18.9 %** |

### Result

**Confirmed for N ≥ 20.** The frozen-phase model inflates seed-to-seed variance by **2.8–7.9×** and
biases mean delivery **low by 10.6–18.9 %**. All three pre-registered falsifiers failed to fire.

⚠️ **Not established at N = 5** (Levene *p* = 0.19). Reported as such. The reason is mechanical: at
N=5 the frozen distribution piles at the ceiling (22/30 runs deliver exactly 1.000), so Levene's
deviations-from-median lose power. The *means* still differ (MWU *p* = 0.003).

### ⚠️ My prior hypothesis was wrong, in the informative direction

Before the pilot I predicted the artifact would **wash out** at the large N the scalability
literature studies. It does the opposite: variance inflation grows from 2.8× at N=20 to **7.9×** at
N=100, and the mean bias grows from 10.6 % to **18.9 %**.

**Mechanism.** With frozen phases the *set* of colliding pairs is fixed at t=0, so a run cannot
self-average — only seeds can. With randomised timing, collisions redistribute continuously *within*
each run, so every run self-averages and seed-to-seed spread collapses. More nodes means more pairs
locked into their initial relationship, not fewer.

### Why this is not just our problem

The configuration is used, verbatim, by the field's most-cited ns-3 LoRaWAN work:

* *Scalability Analysis of Large-Scale LoRaWAN Networks in ns-3* (349 citations): "the transmission
  time of the first upstream packet is picked from a random variable uniformly distributed between
  zero and the upstream period. Subsequent upstream packets are **periodically generated**."
* *A Thorough Study of LoRaWAN Performance Under Different Parameter Settings* (122 citations):
  devices "generate packets periodically, **with equal period but random phases**."

372 works cite the module paper; 56 have capacity/scalability/collision titles.

⚠️ **This mean-bias claim was NARROWED by F33** — it holds only for a receiver-bottlenecked
configuration (1 channel, 1 demodulator). Under an RP002-provisioned gateway the mean is
unaffected. **The variance inflation is the part that generalises.**

### What is still NOT established

1. **Seed counts across the corpus.** I verified the *traffic model* in three papers by direct
   quotation; I have **not** surveyed how many of the 56 report ≤5 seeds. Without that, "papers
   inherit both effects" is an inference, not a measurement.
2. **One configuration.** DR5, 218 B, 1 % duty, single channel/demodulator, ideal channel. The
   `EU` preset (3 channels, 8 demodulation paths) is untested and could change the picture.
3. **1 s of jitter is a choice**, not a derived value. What is defensible is that LoRaWAN Class A
   *requires* transmission randomisation and the module's sender omits it — an argument, not a
   measurement of the correct amount.

**Artifacts:** `results/raw/lora_phase_artifact_30seed.csv` (180 runs, provenance header),
`analysis/analyse_phase_artifact.py`.

---

## F33 — Direction C steps 2 and 3: half the finding generalises, half does not (2026-07-30)

### Step 3 — EU preset replication ⚠️ splits the F32 claim

F32 reported two effects from the frozen-phase traffic model: **inflated variance** and a **mean
biased low**. Replicating under the RP002-style `EU` preset (3 channels, 8 demodulation paths),
30 seeds:

| preset | N | CV ratio | Levene *p* | mean shift | MWU *p* |
|---|---|---|---|---|---|
| ALOHA (1 ch, 1 demod) | 20 | 2.82× | 2.6e−6 | +10.6 % | 1.8e−2 |
| ALOHA | 100 | 7.88× | 2.7e−8 | +18.9 % | 4.5e−4 |
| **EU (3 ch, 8 demod)** | 20 | **2.33×** | **2.8e−4** | +0.27 % | **0.52 — NS** |
| **EU** | 100 | **2.08×** | **8.0e−4** | +0.87 % | **0.36 — NS** |

**✅ The variance inflation generalises.** 2.1–2.3× under EU, significant at *p* < 1e−3. The
pre-registered killer ("CV ratio ≈ 1 under EU, or Levene *p* > 0.05") did **not** fire.

**❌ The mean bias does NOT generalise.** Under a realistically-provisioned gateway it is +0.3 to
+0.9 % and statistically indistinguishable from zero. **F32's claim that "the standard model
underestimates delivery by 10–19 %" is therefore only true for a receiver-bottlenecked
configuration, and must not be stated generally.**

**Mechanism for the split.** Phase locking fixes *which* pairs overlap. Whether an overlap is
*fatal* depends on the receiver: with one demodulator on one channel every overlap is lost, so
locked-in collisions shift the mean; with 8 demodulators across 3 channels most overlaps survive, so
the locking still concentrates outcomes run-to-run (variance) without moving the average.

### Step 2 — what the corpus reports

Five distinct ns-3 LoRaWAN papers were obtained in full text and searched for replication and
dispersion reporting:

| searched for | result |
|---|---|
| "seed" | **not present in any** |
| independent runs / Monte Carlo / repetitions | **not present** (one hit was *packet* repetition, unrelated) |
| confidence interval / error bar / SD **of results** | **not present** in the simulation papers |
| "averaged over N runs" | **not present** |

⚠️ **This is a statement about *reporting*, not about what the authors did.** They may have run many
replications and not said so. Absence of the word "seed" is not evidence of a single seed. The
defensible claim is that **replication counts and dispersion are not reported**, which is a
reproducibility gap independent of whether the underlying runs were adequate.

⚠️ **Sample is small and non-random**: 5 papers, selected by open-access availability from 56
capacity-titled citers. MDPI's bot protection blocked most downloads. This is indicative, not a
survey. A real survey needs the full 56 and should count reported replications explicitly.

### Net position on Direction C

**What survives, with evidence:** the standard traffic model (equal period, exact interval) locks
relative phases for the whole run and **inflates seed-to-seed variance by ~2–8×** across both gateway
provisionings, in a literature that does not report replication counts or dispersion.

**What does not survive:** any general claim about biased means.

**Still required before this is publishable:** the full 56-paper survey with explicit replication
counts; and a defensible derivation of how much randomisation is right, rather than our chosen 1 s.

**Artifacts:** `results/raw/lora_phase_artifact_30seed.csv` (ALOHA, 180 runs),
`results/raw/lora_phase_artifact_eu_30seed.csv` (EU, 120 runs).

---

## F34 — certificate bytes charged, and the CLAS baseline run (2026-07-30)

### 1. The fairness fix, made before looking at the comparison

`bytes_per_record` charged **certificate bytes to nobody**. That silently assumed out-of-band
credential distribution — free on the wire — for *every* scheme, which flatters PKI and penalises
**certificateless** ones whose entire advertised advantage is carrying no certificate.

Added `cert_bytes` / `cert_period` (defaults 0/1, so every frozen artifact is bit-identical). The
period reflects practice: broadcast systems send a credential periodically and let receivers cache,
so the on-air cost is `cert_bytes / cert_period` per frame.

**This was implemented before the CLAS numbers were obtained**, deliberately — doing it afterwards
would have invited fitting the correction to the answer.

### 2. ⚠️ The finding: CLAS "aggregate signatures" do not reduce on-air bytes

From the PLOS One scheme's own Table 2 (DOI 10.1371/journal.pone.0317047), communication overhead
for *n* messages, using their stated parameters (G₁ = 128 B, G₂ = 40 B, |Z*q| = hash = 20 B,
traffic message = 67 B):

| scheme | total | security overhead per message |
|---|---|---|
| Wang et al. | 859*n* B | 792 B |
| Liang et al. | 735*n* B | 668 B |
| Xu et al. | 596*n* B | 529 B |
| Cahyadi et al. | 583*n* B | 516 B |
| PLOS 2025 (theirs) | 583*n* B | **516 B** |

**Every entry is linear in *n*.** The aggregate compresses **verification cost**, not bytes: each
message still carries its own tuple `(M, PID, vpk, t, σ)` on the wire.

### 3. The comparison

| configuration | B/record | overhead |
|---|---|---|
| AUTHBC B, b=4, no cert charged | 72.0 | 27.0 |
| AUTHBC B, b=4, **117 B cert every 10 frames** | 74.9 | 29.9 |
| AUTHBC B, b=4, **117 B cert every frame** (worst case) | 101.2 | 56.2 |
| best CLAS above | 583 | 516 |

**Even charging ourselves a certificate on every single frame — the most pessimistic assumption
available — we are 5.8× cheaper on the wire.**

### 4. What this does and does NOT establish

**It does not establish that we beat CLAS.** Three reasons, all of which must be stated:

1. **They buy something we do not.** The per-message `PID` and `vpk` provide *conditional privacy*
   — pseudonymous identity with authority traceability. AUTHBC provides no anonymity. A large part
   of their 516 B is paying for a property we do not offer, and a ledger arguably wants the
   opposite (attributable records).
2. **Different primitives.** Their G₁ element is 128 B; our Ed25519 signature is 64 B. Some of the
   gap is curve and encoding choice, not design.
3. **Different axis, which is the point.** Their aggregation reduces the verifier's work; our
   batching reduces airtime. **This measurement confirms the positioning the paper already claimed**
   for Zhang et al. — receiver-side versus sender-side — and now with a number rather than an
   argument.

**The honest headline:** *aggregate-signature schemes for vehicular broadcast do not reduce on-air
bytes; they reduce verification cost. On a byte-constrained link the axis that matters is placement
and batching, which is what this work optimises.* That is a stronger and more defensible statement
than "we are 5.8× better."

### 5. ⚠️ Certificate parameters now SOURCED (gap closed)

The earlier 117 B placeholder is replaced with a figure from a top-tier primary source:

> **"The size of the ECDSA certificate C_S is 162 bytes."** — Twardokus, Bindel, Rahbari & McCarthy,
> *Practical Post-Quantum Authentication for V2V Communications*, NDSS 2024.

The **transmission policy** is sourced from the same paper: "in an arbitrary five-second window, a
vehicle complying with these standards would transmit 10 full-certificate SPDUs" — against 10 Hz
BSMs that is a full certificate **every 5th message**, so `cert_period = 5` is standards-grounded
rather than chosen. They also report those transmissions are **"up to 93 % redundant"**, which is
independent confirmation that amortising the certificate is what real systems do.

| policy | B/record | vs best CLAS (583) |
|---|---|---|
| no certificate charged (previous model) | 72.0 | 8.1× |
| **162 B every 5th frame (standards policy)** | **80.1** | **7.3×** |
| 162 B every frame (worst case) | 112.5 | 5.2× |

**The conclusion is invariant across the whole range**, which is the point: it does not depend on
the certificate policy we assume.

---

## F35 — hardware 802.11 broadcast measured; the airtime model confirmed, one run discarded (2026-08-05)

**The gap this closes.** Every 802.11 number in the paper was simulation (D2's LoRa counterpart was
closed the same way and flagged as such). The two-Pi rig now supplies a hardware anchor for two
quantities: broadcast **link loss** and broadcast **airtime**.

### The result

Two nodes, ad-hoc IBSS on 5 GHz ch 36 (802.11a), one transmitter, 1400 B frames, 8 repeats of 22 s
at 100 fps. Full record in `results/hw/channel/RESULTS.md`; artifact `adhoc_sweep_5ghz.csv`.

| quantity | predicted **before** the run | measured |
|---|---|---|
| airtime per 1400 B broadcast frame | 1.99 ms | **1.995 ms** (0.36 %) |
| broadcast capacity | ≈503 fps | **501.19 fps** (0.36 %) |
| delivery at 100 fps (≈21 % utilisation) | ≥99 % | **99.9773 %** pooled (17 596/17 600) |
| duplicates | 0 | **0** |
| per-window dispersion | — | σ = **0.024 pp**, min 99.954 %, max 100.000 % |

Measured link loss **p = 2.273 × 10⁻⁴**.

**The airtime agreement is the load-bearing part.** DIFS 34 µs + preamble 20 µs + mean backoff
67.5 µs + 1400 B at 6 Mb/s predicts 1.99 ms; hardware says 1.995 ms. That is an independent check on
the 802.11a timing constants underneath every Bianchi and Ma & Chen figure in the paper.

**Loss is on air, not in the stack — measured, not assumed.** In each window that lost a frame the
receiver's NIC counter equals the application count (window 01: 2200 transmitted, `rx_frames_nic`
2199, `received_unique` 2199). The interface counters were added specifically to make that
separable, after the 2.4 GHz run showed why.

### ⚠️ What it does NOT show

* **It cannot validate Ma & Chen.** One transmitter means zero contention; that model describes N
  contending stations. The contention result stays simulation-only.
* **It does not license lowering `p`.** Two nodes at 1–2 m, line of sight, stationary, on a clear
  channel is the best case by construction. It bounds the optimistic end of the B4 grid: B4 argued
  `p = 0.05` is 20–100× more pessimistic than TS 22.125's 99.9 %; measured, it is conservative by
  **≈220×** here. B4's *reasoning* is corroborated; its *value* is untouched.

### ⚠️ The discarded run, and why it is kept

The first sweep ran on 2.4 GHz and produced **97.45 % delivery, σ = 0.196 pp over 8 windows** — tidy,
plausible, and **wrong**. Every offered rate from 100 to 1600 fps produced the same ~85 fps /
0.96 Mb/s on air, which is 1400 B at the 802.11b **1 Mb/s basic rate**. Broadcast uses the lowest
basic rate, so the "100 fps operating point" was ≈118 % of capacity: the number measured
**over-subscription**, not channel loss. It is retained as `adhoc_sweep_2g4.csv`, labelled.

Two things caught it, both in place *before* the run rather than constructed afterwards: the
pre-stated prediction, which named the 1 Mb/s basic rate explicitly as the risk if `mcast_rate`
could not be pinned (it could not — brcmfmac returns -95), and the offered-load sweep. **A single
100 fps run would have produced a publishable wrong number** — the exact pattern the status board
warns about, arriving this time through a PHY-rate assumption rather than a small sample.

Moving to 5 GHz is not a workaround: 802.11a has no sub-6 Mb/s rate, so its basic rate is 6 Mb/s,
which is what the NS-3 model already assumes.

### Two earlier statements corrected

* **`key-mgmt none` was blamed as the fix; it was the cause.** In NetworkManager it means *static
  WEP*, not "open" — attempt 2 died on *"Secrets were required"*. `hw/channel/README.md` said it was
  REQUIRED. Corrected.
* **`peers: 0` was read as "the link never formed".** The 2.4 GHz run reported `peers: 0` with an
  empty station dump while delivering 4988/5000 frames. FullMAC drivers do not expose IBSS peers via
  nl80211; the inference was unsound.

---

## F36 — mobility is a NO-OP under our default collision matrix, by construction (2026-08-05)

**The mobile LoRa scenario is built and validated, and the first thing it found is a trap in the
experiment design rather than a result about UAVs.**

`ns3/authbc-lora-capacity-mobile.cc` is a **separate new file** per Mohamed's direction; the static
scenario is untouched. Its control arm is exact: at `--speed=0` it reproduces
`authbc-lora-capacity.cc` **bit-identically** (seed 7, N=20: sent 323, received 249,
delivered_frac 0.770898 in both). Any difference is therefore mobility, not a porting error.

### The finding

| collision matrix | speed 5 m/s | speed 20 m/s | mean displacement (5 / 20) |
|---|---|---|---|
| `aloha` (no capture — **our default**) | 0.720859 | **0.720859** (identical) | 878 m / 1090 m |
| `goursaud` (6 dB capture) | 0.785276 | **0.791411** (differs) | 878 m / 1090 m |

The nodes demonstrably fly — mean displacement differs with speed, and the scenario now measures and
reports it precisely so this could be checked. Yet under `aloha`, delivery does not move **at all**.

**The mechanism is structural, not statistical.** The ALOHA matrix puts **+inf on the same-SF
diagonal**: any co-SF overlap is fatal *regardless of received power*. Power is the only channel
through which position can influence the outcome, so with capture disabled, delivered fraction is a
function of the transmission **schedule alone**. Mobility cannot change it at any speed, in any
model, over any distance that keeps nodes in range. Enabling capture restores the power dependence,
and the speeds immediately separate.

### ⚠️ Two consequences, both of which would have produced a wrong result

1. **`MOBILITY_PLAN.md` §M2's stated prediction is unreachable under the default config.** It
   predicted mobility would "reduce the bimodality" and "widen the delivery distribution". Under
   `aloha` that is *structurally impossible*, not merely unobserved. A 30-seed sweep run at the
   default would have concluded "mobility has no effect on the LoRa arm" — true, but for a reason
   that has nothing to do with UAVs, and it would have been reported as a physical finding.
2. ⚠️ **The static→mobile difference under `aloha` is RNG stream displacement, not mobility.**
   0.770898 static vs 0.720859 mobile looks like a 5-point mobility penalty. It is not: the
   mobility model consumes random variates and shifts the sender-jitter stream. The proof is that
   speeds 5 and 20 give *identical* delivery — if the gap were positional it would vary with speed.
   **Never compare a static arm against a mobile arm under `aloha` and attribute the difference to
   motion.**

### What this fixes going forward

Any LoRa mobility experiment must run with `--interferenceMatrix=goursaud`, and must say so, because
that is a **different collision model** from the one behind the frozen `N_max = 3` result — so
mobility numbers are not directly comparable to it and must be reported as their own arm. The
alternative reading is equally publishable and more honest: *in a no-capture ALOHA channel, node
mobility is irrelevant to capacity by construction* — which is a statement about the model, and one
the LoRa-FANET literature does not appear to make explicitly.

Displacement (`mean_displacement_m`, `max_displacement_m`) is now emitted in every run's CSV, so
"did the nodes actually move?" is never again a question answered by inference.

---

## F37 — mobility measured at 30 seeds: no significant effect, and the static assumption is now VALIDATED (2026-08-05)

**E20/M2 is answered.** The static assumption in the LoRa arm was previously an *accepted
limitation* (C3, "no mobility"). It is now a **tested and confirmed** one, which is a materially
stronger position: we ran the experiment rather than excusing it.

Artifact `results/raw/lora_mobility.csv`, driver `ns3/run_lora_mobility.py`, 140 runs.

### Both scenario properties verified before any number was trusted

| property | check | result |
|---|---|---|
| **porting correctness** | `--pinStreams=false --speed=0` vs frozen `authbc-lora-capacity.cc` | sent/received **323/249 in both** — bit-identical |
| **clean attribution** | pinned, `aloha`, four mobility configs | all four return **exactly** 0.637771 |

⚠️ These two are **mutually exclusive by construction**, which is why stream pinning is a flag. See
the confound below.

### The result — `goursaud` (capture; the module's own default, and the physical model), 30 seeds

| arm | mean | min | max | σ | Δ vs static | t | significant? |
|---|---|---|---|---|---|---|---|
| static, 0 m/s | 0.745366 | 0.640244 | 0.873065 | 0.063283 | — | — | — |
| Gauss–Markov, 5 m/s | 0.742923 | 0.609756 | 0.863777 | 0.066017 | **−0.244 pp** | −0.146 | **NO** |
| Gauss–Markov, 20 m/s | 0.745083 | 0.603659 | 0.863777 | 0.066280 | **−0.028 pp** | −0.017 | **NO** |
| Random Waypoint, 20 m/s | 0.748988 | 0.641745 | 0.873065 | 0.064528 | **+0.362 pp** | +0.220 | **NO** |

Static 95 % CI **[0.7227, 0.7680]**. Every mobile arm's mean sits inside it, within **0.06 σ** and
|t| ≤ 0.22, against mean displacements of **816–967 m**. Nodes fly nearly a kilometre and delivery
does not move.

### And `aloha`, 5 seeds × 4 arms — the structural prediction, confirmed at scale

All four arms returned **byte-identical statistics**: mean 0.671036, min 0.576324, max 0.793210,
σ 0.104392. Not "close" — identical, as F36 predicts, because with capture disabled position cannot
enter the calculation at all.

### Three conclusions

1. **Mobility does not change the LoRa capacity result**, under either collision model, at speeds
   spanning published FANET practice. Under `aloha` that is provable a priori; under `goursaud` it
   is measured and null. **The conclusion is the same either way, which is what makes it robust** —
   it does not depend on the capture assumption that A2 flagged as consequential elsewhere.
2. ⚠️ **Gauss–Markov and Random Waypoint are statistically indistinguishable here** (0.7451 vs
   0.7490, 0.06 σ apart). `MOBILITY_PLAN.md` §M1 argued RWP is "wrong for a swarm" and should not be
   used; `MOBILITY_SURVEY.md` §2a countered that it is standard practice and should be run as a
   baseline. **The empirical answer retires the argument: the model choice carries no weight in this
   result.** We ran both and say so, instead of defending a preference.
3. **The mechanism is the link margin, not luck.** F25 measured 17–29 dB of headroom; the
   Gauss-Markov bounding box keeps nodes within ~1414 m of the gateway, which costs about 5.6 dB at
   path-loss exponent 3.76. Motion never approaches the sensitivity threshold, so the only route
   left is capture SIR, and averaged over 30 seeds that washes out.

### ⚠️ The confound this run had to remove first, and how close it came to a false finding

Before stream pinning, `aloha` static read 0.770898 and mobile read 0.720859 — a clean-looking
**5-point mobility penalty**. It was **entirely RNG stream displacement**: ns-3 assigns each new
`RandomVariableStream` the next index from a global counter, and the mobility models are constructed
*before* the senders, so installing Gauss-Markov instead of ConstantPosition shifted every sender's
jitter and start-offset stream. The tell was that speeds 5 and 20 gave *identical* delivery — a real
positional effect would scale with displacement.

Pinning the senders' streams by node id removes it. ⚠️ A first attempt at the fix set the
start-offset stream **unconditionally**, so when pinning was off every node shared stream 0+1, drew
the same start offset, and transmitted in lockstep — delivery collapsed to **0.0298**. That was
caught by the porting-correctness property, which is precisely why both properties are asserted in
the driver and re-checked before every sweep.

### What still is not modelled, and must be stated wherever this is quoted

Per-frame Doppler fading. At 20 m/s the LoRa coherence time is ~7.3 ms against a 364 ms frame, so
the channel decorrelates ~50× **within** a single transmission. This scenario moves nodes between
frames; it does not fade within them. The null result above is therefore "mobility does not change
collision-limited capacity", **not** "mobility is harmless to a LoRa link".

---

## F38 — the last six 3-seed artifacts re-run at 30 seeds; A2's capture table is CORRECTED (2026-08-06)

**Why this was necessary.** F30 established the pattern that cost this project four headline
numbers: a small-sample mean compared against a threshold. Drivers were fixed to default to 30
seeds — but **six committed artifacts were never re-run**, and three of them backed published
claims. They were also frozen-phase (`txJitter = 0`), predating E13, so they were stale on *two*
counts. Every one has now been re-derived at 30 seeds with jitter and full dispersion.

### ⚠️ CORRECTION — audit A2's capture-cost table

A2 quantified what the ALOHA collision matrix gives away versus Goursaud capture. Both of its
columns came from 3-seed, frozen-phase runs. Re-measured at 30 seeds with jitter:

| N | A2 published: ALOHA / Goursaud → gain | **corrected 30-seed** | |
|---|---|---|---|
| 8 | 0.8656 / 0.8984 → **+3.3 pts** | 0.87103 / 0.89757 → **+2.7 pts** | |
| 50 | 0.2532 / 0.3453 → **1.36×** | 0.37547 / 0.48561 → **1.29×** | |

⚠️ **The ALOHA baseline at N=50 moved the most: 0.2532 → 0.3755, a 48 % relative change.** That is
the frozen-phase artifact (F32), which inflates dispersion most at high N — exactly where A2 read
its headline ratio. **A2's conclusion survives** — capture is worth a few points and we are
conservatively giving it away — but both quoted figures were wrong and are corrected here.

### Confirmed, not moved

| claim | 3-seed | 30-seed | verdict |
|---|---|---|---|
| **E9: EU preset `N_max = 8`** | 8 | **8** | ⚠️ **holds, but 95 % CI [5, 8]** — 27.6 % of bootstrap replicates give 5. Quote the interval, never the bare 8 |
| **F25: "shadowing changes nothing"** | null | **null** | holds — and now *explained*: see below |
| Goursaud `N_max` | — | **3** | capture does **not** raise `N_max` above the ALOHA value of 3; it helps well below the threshold, not at it |

### The shadowing null is structural, not empirical — and that is a stronger statement

`lora_capacity_shadow500.csv` and `lora_capacity_repro.csv` returned **byte-identical bootstrap
distributions** ({1: 0.013, 2: 0.188, 3: 0.796, 5: 0.003}) despite different radii *and* different
channel models. That is F36's mechanism again: under the ALOHA matrix any co-SF overlap is fatal
**regardless of received power**, so delivery is a function of the transmission schedule alone.
Radius and shadowing act only through power, so **neither can change the result** — the null was
guaranteed before it was measured. F25's finding is upgraded from "measured no effect" to "cannot
have an effect under this collision model".

### Three further defects found while doing it

1. ⚠️ **`config_hash` could not distinguish its own runs.** `run_lora_capacity.py` hashed only
   {dr, nodes, seeds, t, payload}, so `lora_capacity_shadow500.csv`, `_shadow1000.csv` and
   `_repro.csv` all carried the **same hash** despite different radii and channel models. Now covers
   gw_region, channel_model, radius, interference, tx_jitter and epsilon.
2. ⚠️ **`ns3/sensitivity.py` recorded a false provenance**: it hardcoded `ns3_version = "3.41"`
   while calling `ns3_root()`, which resolves to the pinned **3.48** tree. The metadata contradicted
   the binary that produced the numbers. Now read from the tree in use. Its `--seeds` default was
   also still 3.
3. ⚠️ **`lora_phase_artifact_30seed.csv` cites `expectations_preregistered=scratchpad/C1_EXPECTATIONS.md`,
   which is not in the repo.** The artifact claims pre-registered expectations and the evidence for
   that claim is missing — it lived in an agent scratchpad that is gone. The claim cannot be
   verified and should not be relied on until the expectations are re-stated in a committed file.

### The 802.11 geometry sensitivity was robust

`ns3_sensitivity.csv` re-run at 30 seeds moved by at most **2.93 pp** (nakagami1: +10.34 % →
+13.27 %) and under 1 pp for four of six scenarios. Every qualitative conclusion holds. Reported
because a null re-derivation is evidence too — it is what tells us the sampling problem was specific
to the LoRa threshold crossings rather than general to the project.

### ⚠️ The paper carried five stale numbers from this correction

I initially reported that A2's figures lived only in the audit register. That was wrong — the paper
quotes them, and the F38 re-derivation invalidated five passages, now corrected:

| passage | was | now |
|---|---|---|
| capture gain | +3.3 pts at N=8, 1.36× at N=50 | **+2.7 pts, 1.29×** |
| periodic-escape cross-check | 0.868 predicted vs **0.866** measured | vs **0.871** measured (agreement holds) |
| gateway vs peer at N=50 | 2.68× (0.2532 → 0.6781) | **1.90×** (0.3755 → 0.7134) |
| gateway at N=100 | 0.5308 | **0.5071** |
| "N_max moves only from **5** to 8" | 5 | **3** — the ALOHA baseline moved at F30 and this sentence was never updated |
| EU crossing | passes N=8 at 0.9958, fails N=10 at 0.9370 | **0.9526 / 0.9398**, now with the 95 % CI [5,8] stated |

**The narrative survives every one of them** — capture helps but does not move `N_max`, the gateway
improves delivery without moving the threshold, and the escape-probability cross-check still lands.
But six numbers were wrong, and the "from 5 to 8" sentence had been stale since F30.

### S8 closed

`ns3/run_lora_phase_artifact.py` (`make sim-lora-phase-artifact`) now generates both Direction C
artifacts, reconstructed from their own `design=` headers. ⚠️ Re-running will **not** reproduce the
committed files bit-for-bit — those predate the generator and used a different RNG realisation.
Compare distributions, not rows.

---

## F39 — the factorial ablation: the co-design claim was overstated, and is now precise (2026-08-06)

**The gap.** The paper's thesis was that all four knobs "are coupled and must be co-optimized" and
"are not separable". The evidence offered was a **decomposition** (79.2 % placement×batching,
20.8 % encoding). A decomposition attributes a total and is possible even when the axes are
perfectly independent, so it cannot establish coupling. Only interaction terms can.

`analysis/factorial_ablation.py` (`make exp-ablation`), full 2³ factorial on bytes/record:

| term | effect (B/rec) | |
|---|---|---|
| encoding | **−146.09** | largest main effect |
| batching | −57.00 | |
| placement | −24.00 | |
| encoding × placement | **−0.0000** | |
| encoding × batching | **−0.0000** | |
| **placement × batching** | **−24.00** | equal to placement's own main effect |
| encoding × placement × batching | **−0.0000** | |

### What it shows

1. **Placement and batching genuinely couple, exactly.** The placement benefit is the closed form
   **`g_a(1 − 1/b)`**, so it is **identically zero at b = 1**: placements A and B are byte-identical
   on a single-record frame. Measured, A→B saves **0.000 B at b=1** and **48.000 B at b=4**
   (= 64 × 0.75). The interaction term equalling the main effect is the signature of a *pure*
   interaction — placement has essentially no standalone effect to speak of.
   ⚠️ Note the shape: `1 − 1/b` is the same expression the status board warns about for the bare
   75 %. **The term that makes the headline look impressive and the term that couples placement to
   batching are the same algebra.**
2. ⚠️ **Encoding is perfectly separable.** Every interaction involving it is *exactly* zero, and
   structurally so: `s` enters `s + (H_f + g_a)/b` additively, so it cannot interact with anything.
3. **Scheme is byte-degenerate at the operating point** (Ed25519 and ECDSA-P256 are both 64 B). BLS
   at 96 B would cost +8 B/record at b=4 — and batching mutes even that.

### ⚠️ A claim in Related Work was a scale artifact

The paper said *"encoding is coupled to authentication: a smaller payload raises the auth fraction,
which increases the value of batching."* The absolute saving from batching is **81.000 B for JSON,
CBOR and delta alike** (spread 4 × 10⁻¹⁴ B); only the *percentage* differs (27.1 % vs 52.9 %,
a 1.95× ratio) because the denominator shrinks. **Two effects that are additive on an absolute scale
always appear to interact once expressed as ratios.** That is arithmetic, not evidence of coupling.

### ⚠️ The paper contradicted itself — again — and the results section was the correct half

§Results already derived the invariance: *"the record size does not appear, so the auth-byte
reduction … is invariant to header size, signature size, encoding and scheme."* The abstract and
introduction nonetheless claimed all four knobs were coupled and "not separable". This is the third
internal contradiction the audit has found (after `tab:envelope` and the "5 to 8" sentence), and the
same mechanism each time: **prose that no test compares against the model.**

**Corrected** in the abstract, the introduction's thesis statement and Related Work, and a new
Results paragraph states the ablation. The revised claim is *stronger* because it is falsifiable:
one genuine two-axis interaction, one additive contributor, one byte-neutral axis.

**Nothing else moves.** The 75 % auth-byte cut, the −58.68 % total, the decomposition and the
feasibility envelope are all unchanged — the ablation reinterprets them, it does not revise them.
Pinned by `tests/test_factorial_ablation.py` (19 tests), which asserts the closed forms rather than
the numbers, so the zeros cannot drift into small non-zeros unnoticed.

---

## F40 — S9: a pre-registration claim withdrawn rather than reconstructed (2026-08-06)

`results/raw/lora_phase_artifact_30seed.csv` carried the header field
`expectations_preregistered=scratchpad/C1_EXPECTATIONS.md`. **That file is not in the repository.**
It lived in an agent session scratchpad that no longer exists, so the claim that F32/F33's
expectations were stated in advance cannot be verified by anyone — including its author.

**Two ways to resolve it, and only one is honest.** The tempting fix is to write the expectations
file now, from the reasoning recorded in F32. ⚠️ **That would manufacture a pre-registration.** A
pre-registration's entire value is that it was fixed *before* the outcome was known; reconstructing
one afterwards from a document that already describes the outcome produces something that looks like
evidence and is not. It is worse than having no pre-registration at all, because it is unfalsifiable
from the outside.

**The claim is therefore withdrawn.** The header now records what it used to say, that the file is
missing, and why it was not reconstructed. **F32 and F33 stand as ordinary analyses** — their
statistics (Levene, Mann-Whitney U) and their conclusions are unaffected; what is removed is an
unearned methodological claim on top of them. F33 already narrowed the mean-bias half of F32 on
evidence, which is the substance that matters.

Any future Direction C run must commit its expectations **before** executing. Law 6 already requires
stating the expected value in advance; what was missing was a committed place to put it.

---

## F41 — reading the one unread source produced a finding, not a citation (2026-08-07)

`sensors2025_mesh_lora_performance_TOREAD.pdf` had sat in `docs/literature/` unread. Reading it
(Durand & Booysen, *Sensors* 25(5):1602 — an ns-3 LoRaMesh model) yielded three things:

1. **A citation that was earned.** Its statement that *"there is currently no standardised and
   commercialised multi-hop LoRa-based network"* directly supports our single-hop scope, and sits
   beside the mesh reviews already cited.
2. ⚠️ **A sixth Direction C data point.** A keyword sweep of the entire paper for
   seed / repetition / run count / confidence interval / standard deviation / variance returns
   **zero hits**. A 2025 ns-3 LoRa simulation study reports *no replication information at all* —
   the pattern F32/F33 describe, now observed in a paper we did not choose for that purpose.
3. The file is renamed `durand2025_loramesh_ns3.pdf`; "TOREAD" in a filename is a to-do, not a
   status, and it survived for weeks.

### ⚠️ The register was missing a fifth of its own corpus

`docs/literature/README.md` opens with *"Every source consulted for AUTHBC, with why it matters
stated explicitly"* and its header claimed **20 PDFs**. There were **25 on disk, and five had no
entry at all**. All five are now recorded with roles, along with two filename defects that were
found while doing it: `branch2019_multihop_lora_linear.pdf` is actually **Abrardo & Pozzebon**, and
the TOREAD file above. Both are recorded rather than silently renamed, because a link that already
points at the old name should still resolve.

### ⚠️ S10 — a gap the unreadable source exposed

arXiv:2309.15340 (held) is *"…Exploring ECQV Implicit Certificate Cracking"* by Abel C. H. Chen. The
filename is accurate — verified against the arXiv record, correcting an earlier characterisation of
it as mislabeled. **The full text is in Chinese**, so it is not cited: an English abstract is not
the paper, and this register's standard is that cited sources have been read.

But its abstract names exactly what we skipped: it *"analyzes the length of … explicit certificates,
and implicit certificates"*. **F34 charges an explicit 162 B ECDSA certificate and never considers
the implicit (ECQV) alternative**, which is the smaller one and is standard in IEEE 1609.2.

⚠️ The direction of the error is worth stating: charging the **larger** certificate is conservative
for us and **harsher on the CLAS comparison**, whose entire advertised advantage is carrying no
certificate. So the omission cuts against our own favour — it weakens our CLAS position rather than
flattering it, and is safe to leave stated as an upper bound while S10 is open.

---

## F42 — Direction C: the phenomenon has PRIOR ART, and the pilot's "9 of 9" was inflated (2026-08-07)

Two corrections to Direction C, both produced by writing the survey protocol *before* running the
survey (`docs/DIRECTION_C_SURVEY_PROTOCOL.md`, committed `eb3eda5`, data-free). Neither would have
surfaced from a looser process, and both narrow our own claim.

### ⚠️ 1. The frozen-phase artifact is not unobserved in the literature

Direction C's framing has been that the standard ns-3 LoRaWAN traffic model distorts results *in a
literature that does not notice*. Reading `durand2025_loramesh_ns3.pdf` closely — a paper we
downloaded for a different reason — refutes the second half:

> "In the LoRaMesh PDR analysis … the nodes typically **either have a successful up-link or not**.
> This can be attributed to the **static nature of the network configuration**. Nodes are set to
> always transmit on a **specific SF, time, and channel**; therefore, this results in **certain
> packet collisions being repeated for every transmission cycle**."
> — Durand & Booysen, *Sensors* 25(5):1602, 2025

That is the artifact: bimodal delivery ("either … or not"), correctly attributed to fixed
transmission timing. **The observation is prior art.**

**What remains ours, stated narrowly:** they note it in passing to explain the shape of one figure.
They do not *quantify* it (we measure **2–8× CV inflation** over 30 seeds), do not connect it to
replication reporting, do not observe that LoRaWAN Class A *mandates* the randomisation the module
omits, and propose reinforcement learning — adaptive parameters — rather than transmission jitter as
the remedy. Direction C's contribution is therefore the **quantification and the reporting link**,
not the discovery. ⚠️ Any draft claiming the phenomenon is unreported must be corrected.

### ⚠️ 2. The pilot's "9 of 9" did not meet the protocol's own inclusion criteria

Applying §2 strictly (simulation results **for LoRa**, simulator **is ns-3**, machine-readable,
non-duplicate) to every held PDF, only **4** qualify. The pilot's nine had counted:

* **Bor et al. 2017** — used **LoRaSim**, not ns-3. Its single ns-3 mention is future work:
  *"Implementation of modules in system level simulator, like ns-3, … will further be studied."*
* **Mehta et al. 2020** — a **survey**; its ns-3 mentions describe other people's work in a table.
* **Bhatt et al. 2025** — ns-3, but **802.11ah, not LoRa**.
* two further entries that are reviews rather than simulation studies.

So the honest baseline is **4/4 report no replication**, not 9/9. The pattern is unchanged; the
sample is smaller and the criteria are now fixed in advance rather than chosen per paper.

### ⚠️ 3. A narrower keyword set had under-reported hits

The pre-registered keyword set is broader than the ad-hoc regex used during the pilot. Under it,
`durand2025` yields **2 hits** where the earlier sweep reported **zero**. Both are false positives on
adjudication — but the earlier "zero" was an artifact of the narrower pattern, which is precisely why
§3 fixes the keyword set in advance and requires every hit to be read in context.

**Harness:** `analysis/direction_c_survey.py`, artifact `results/raw/direction_c_survey.csv`, with
every adjudication recorded in the CSV rather than held in memory. `UNREADABLE` (< 2000 extracted
characters) is excluded from the denominator, because scoring a scanned PDF as "reports nothing"
would manufacture support for our own hypothesis.

## F43 — the math audit: five constants that were conventions, and one that was a range (2026-08-28)

*Requested by Mohamed: "audit all the math deeply and compare it against the simulation."
Method: re-derive each quantity from its equations, then check it against a discrete-event
simulation written for the purpose. **Nothing here is a wrong number.** Every finding is a
convention or a limit that decides a headline and was never written down — and in three of the
five the unstated choice happens to favour our own claim.*

### The defect class, and why 30 seeds cannot touch it

All of these are **C2 — an unverified constant on the measurement path**. The 30-seed discipline
installed after F30 protects against C1 (small-sample means), which is the failure that already
happened. It offers no protection at all against a constant that is precisely reproducible and
means something other than its label.

### F43a — `D(b)` names the oldest record's age and computes the batch window

With periodic arrivals at rate Λ, a batch window opening at t=0 and closing on the b-th record:

| quantity | value |
|---|---|
| batch-window duration (open → transmit) | **b/Λ** |
| age of the OLDEST record at transmit | **(b−1)/Λ** |

Both confirmed exactly by discrete-event simulation over 200 000 frames, deterministic and Poisson
(under Poisson: Erlang(b, Λ) and Erlang(b−1, Λ), means b/Λ and (b−1)/Λ). docs/02 §7 wrote
"freshness of the oldest record in a batch: D(b) = b/Λ_i + T_air + queueing" — naming the second
and computing the first.

**`b/Λ` survives as the worst case, and it is exactly that:** a record timestamped at its sample
instant may describe state up to 1/Λ older, and (b−1)/Λ + 1/Λ = b/Λ. So it bounds end-to-end
latency including sampling quantisation. **Retained unchanged** — a latency bound should be an
upper bound, and every frozen artifact rests on it. ⚠️ **Cost, now stated:** the tight reading
admits b=5 at both operating points (66.6 B/record, −61.78 %) where the worst case admits b=4
(72.0 B, −58.68 %). **We under-report our own saving by ~3 points.**

⚠️ **One consequence was NOT conservative and is corrected.** docs/02 §7a argued the fully-compliant
corner is a "knife-edge" because "the b=2 frame takes 100.37 ms, 0.37 ms over, so b collapses to 1
and the cut goes to zero", and presented that as a fact about "how tightly this regime is squeezed".
It is a fact about the convention: the oldest record in that frame is aged **50.37 ms**, half the
bound. Corrected in place.

### F43b — H_f is a range, 38–44 B, and 44 is the end that favours the exclusion

Canonical CBOR encodes an integer 0–23 in one byte and one ≥ 65536 in five, so H_f varies with
`src` and `base_seq`: **38 B** for a fresh low-id node, **44 B** an hour into flight at 50 Hz. The
documented 44 B and its 46 B step at b≥24 both reproduce exactly at realistic magnitudes, so the
measurement was sound — docs/01 §2a simply called it constant when it is constant only in b.

⚠️ **The bias direction is opposite for T6.** docs/01 §2a analyses H_f's bias for the *byte
comparison*, where 44 B is conservative. T6's bound is `s_max = M − H_f − g_a`, so a **larger H_f
makes exclusion more likely**. DR3 is excluded for H_f ≥ 39 and **feasible at H_f ≤ 38** — where the
headline becomes *three* of seven EU868 rates, not four. Three independent levers each flip DR3:
H_f (38 vs 44), the payload column (115 vs Klimiashvili's 123 B — the paper already discloses this
one), and s_min (13 B is our own smallest record). **DR0–DR2 are untouched and remain
unconditional at any header size**, which is the half of the claim that genuinely cannot move.
`framer.measure_frame_header_bytes` makes the range measurable rather than assumed.

### F43c — the pre-registered success criterion could not have failed

The ordering is genuine and independently checkable: the ≥40 % criterion is in `docs/04` at
`3354ec1` (2026-07-03 04:42), the E5 result at `a51486a` (2026-07-05 00:34). **That part stands.**

But the quantity it tests reduces exactly to **1 − 1/b** — placement A carries `g_a + H_f` per
record, B carries `(g_a + H_f)/b`, and the ratio is the same identity F13 already forbade quoting.
So the threshold is `1 − 1/b ≥ 0.40 ⟺ b ≥ 2`, independent of encoding, scheme, placement, H_f and
g_a. The other half, V ≥ 0.95, E17 already showed is satisfied by construction with zero margin.
**Both halves are vacuous: no configuration that batches at all could have failed.** Proved for
every (g_a, H_f, b) in `tests/test_math_audit.py::TestSuccessCriterionIsAnIdentity`.

The pre-registration is real and worth keeping. What must go is the implication that it was a live
test — the abstract's "meeting a criterion committed to version control two days before the result
existed" is true about *timing* and false about *risk*.

### F43d — `s` depends on how long you run the generator; its CI is ~150× too narrow

`seq` and `ts` grow with the record index and variable-length encodings charge for the digits, so
mean record size is a property of (encoding, window), not of the encoding:

| | n=1000 | n=10 000 | e1_dominance (30×1000) | p1_sizes (seed 1, n=10 000) |
|---|---|---|---|---|
| json | 191.36 | 193.52 | 191.085 | 193.518 |
| cbor | 66.73 | 68.94 | 66.252 | 68.936 |
| msgpack | 66.29 | 68.84 | 65.160 | 68.836 |
| **delta** | 45.04 | 45.01 | 44.998 | 45.005 |

Delta is flat because it encodes differences. **Two committed artifacts disagree by up to 3.7 B on
the same named quantity and both are correct for their own protocol.** E1's bootstrap CI for cbor
is ±0.02 B — *seed* variation — while the systematic window term is ~2.7 B, **≈150× wider**.

Direction is conservative: a longer flight inflates the CBOR *baseline* and leaves the delta
*optimum* alone, so the reported saving is the pessimistic end (58.68 % at n=1000 vs 59.3 % at
n=10 000). E1 samples the **first ~50 s of each flight**; that is now stated in docs/04 §1.

### F43e — Bor's N_max = 4 sits inside his own fit's unreliable region

`lora.py` already documents that Eq. (8) does not pass through the origin and predicts 1.783 %
loss at N=0, and that "below N ~ 5 the intercept dominates". Their N_max = 4 is decided at N=4
(4.418 %) and N=5 (5.065 %) — **both inside that band**, with the non-physical intercept
contributing **40 % of the predicted loss at N=4**. Using it as corroboration while the same file
calls the region unreliable is inconsistent.

Direction is again conservative: forcing the fit through the origin gives their N_max = **5**,
which *widens* the gap against our 3. So quoting 4 is the safe choice — it simply needs saying.

⚠️ **And the "≈2× more pessimistic" summary hides a sign change.** The ratio runs 0.91× at N=2
(**we are the more optimistic model there**), 1.07× at N=3, 2.09–2.17× from N=10 up — and the
crossover sits in exactly the N ≤ 3 region where N_max is decided. F18 was retracted for a sign
error on this same comparison; a single-number summary is how that happens.
`bor2017_pessimism_ratio` now refuses to be quoted as one number.

### What the audit CHECKED AND FOUND CLEAN

| check | method | result |
|---|---|---|
| OFDM PPDU airtime | hand-derived from 802.11a symbol timing | 1940 µs / 44 µs **exact** |
| Ma & Chen broadcast closed form | vs `sim.dcf_ladder`, an independent slot-exact Monte Carlo | **≤0.08 %** at N=5–50 |
| … and vs NS-3 3.48 | 30 seeds | ≤0.51 % |
| The CFP mechanism | `head_start=False` removes only that asymmetry | collapses to the naive reduction; **16.9× gap at N=50**, reproducing F9 exactly |
| Bianchi unicast | vs NS-3 | band **−0.40 … +1.29 %**, matching the status board |
| Bianchi fixed point | residual of both DCF equations, N=1…1000 | ≤ 7×10⁻¹³ |
| `N_max` first-failure search | exhaustive vs full scan, 7 configs × 4 ceilings | **identical everywhere — search is sound** |
| −58.68 % and 213/100/88/31 | recomputed from artifacts | reproduce exactly |
| Pre-registration ordering | git | genuine, ~1.8 days |

⚠️ **One clean result is clean by accident.** Ma & Chen's saturation throughput is **non-monotone
in N** — it dips near N≈35 and recovers, because each CFP freeze stage contributes an
n·τ(1−τ)^(n−1) hump peaking at n ≈ W₀^(i+1)/2. All three implementations reproduce it, so it is
real physics of the model, not a bug. The `N_max` search breaks on the first violating N, which is
only valid if U(n) is monotone — and U(n) *is* strictly increasing, because its explicit factor n
outruns the recovery. **Safe by arithmetic, not by construction**, and nothing tested it until now.

### Minor

* `bianchi.tau_of_pc(0.5)` raised `ZeroDivisionError` on a **removable** singularity whose limit is
  `4/(2W+2+WM)`. p_c crosses 0.5 for N ≳ 21 (0.5518 at N=35, 0.5953 at N=50), so the solver walks
  through the neighbourhood on every large-N solve. Never triggered; fixed to return the limit.
* `LLC_SNAP_BYTES` / `MAC_HDR_FCS_BYTES` were dead constants — editing them changed no result while
  appearing to. Removed.
* The damped iteration's delivered residual is `_TOL/0.3 ≈ 3.33e-12`, not the documented 1e-12.
  Immaterial; documented.
* **Structural, not fixed:** every record carries `src` and `seq` while the frame already carries
  `src` and `base_seq`; in placement B all records share a sender and have consecutive seq, so both
  are derivable. **10 B/record, ~14 % of the 72.0 B headline.** D6 freezes the wire format and the
  saving does not justify re-freezing every artifact — recorded as known headroom, which makes the
  reported cost an upper bound on an untuned design.
