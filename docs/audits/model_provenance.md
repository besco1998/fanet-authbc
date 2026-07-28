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

## F11 — T3's loss model assumes independence, and is self-consistent rather than validated

V_D = (1−p)^n is exact **iff** frame losses are independent. Our emulator implements independent
Bernoulli draws, so E3 measures V against a channel built on the same assumption the theorem makes:
the agreement in `e3_loss.csv` (V_meas ≈ V_theory) is a **consistency check, not a validation**.

Real 802.11 loss is bursty (fading, interference, collision trains), and burstiness *helps*
block-level D relative to the independent prediction — losses cluster into fewer frames. So T3's
conclusion (B Pareto-dominates D) is **conservative** under burstiness rather than wrong, which is
the safe direction. It should nonetheless be stated as an assumption, not left implicit.

Not fixed here: measuring a real loss process needs the hardware link and is P8/future work.

---

## Positioning fixes (no numbers change)

* **P1 — "amplification law" (T2).** Calling A = M/(M−H_f−g_a) a *law* invites the reading that it
  is a new result. It is MTU-efficiency algebra. Recommend presenting it as a lemma/observation used
  to quantify the coupling, not as a contribution.
* **P2 — T5 "separable" (above).** Say "verified by exhaustive search over the 1536-point grid",
  not "the joint optimum is separable" stated as a theorem.
* **P3 — §7 latency.** Either implement the M/M/1 term the docs specify or amend the docs to the
  model actually used (fill time + airtime). Do not leave them disagreeing.

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
