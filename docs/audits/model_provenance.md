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
