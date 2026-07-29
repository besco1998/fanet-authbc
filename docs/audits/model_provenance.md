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

