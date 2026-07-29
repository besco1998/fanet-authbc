# Trade-off register — what every decision bought, and what it gave up

*Created 2026-07-29 on Mohamed's instruction: **this is an optimization problem, so the work does
not rest on finding the best numbers. State everything, choose what to stick with, and state the
trade-offs for every decision.***

That is a methodological requirement, not a formatting one. An optimization result is only
meaningful if the feasible region and the objectives are visible; a single reported configuration
with its alternatives suppressed is a *selection*, not an *optimization*. This file is the index of
every choice that shapes a reported number, with its cost stated in the same breath as its benefit.

**How to read the status column.** `DECLARED` — chosen deliberately, alternatives reported, cost
accepted. `MEASURED` — settled by measurement, not judgement. `FORCED` — the alternatives are
infeasible, so there was no real choice. `OPEN` — not yet settled (see `OPEN_ITEMS.md`).

Companion documents: **`DECISIONS.md`** (the decision log with dates and blast radius),
**`OPEN_ITEMS.md`** (what is still unresolved), **`audits/model_provenance.md`** (the findings
behind several rows here).

---

## 1. The operating point

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Λ = 20 rec/s, D_max = 250 ms** | reference operating point | b=4 ⇒ 75.0 % auth / 58.68 % total cut; U=0.557 and N_max=103 at N=50 | **Violates 3GPP TS 22.125 R-5.2.2-011** (≤100 ms). Under full compliance the best achievable cut is **50 %**, so a third of the headline is bought by the deviation. Rests on a *scope* argument — §5.2.2 targets collision avoidance; a provenance ledger has a different deadline | **DECLARED** (docs/02 §7a) |
| | *alternative:* Λ=50, D=100 ms | fully compliant, **identical bytes** (Λ·D=5 ⇒ b=4), PX4 `ONBOARD` is a real mode | **unrunnable at N=50** (U=1.39); N_max falls 103→35, and the baseline ratio weakens 3.2×→1.8× | reported |
| | *alternative:* Λ=21, D=100 ms | compliant **and** runnable at N=50 (U=0.888, N_max=58) | cut halves to 50 %; **knife-edge** — at Λ=20.0 the b=2 frame takes 100.37 ms, so b→1 and the cut → **0 %** | reported, not adopted |
| **N_local = 50** | neighbourhood size | a swarm the baselines cannot serve (32) and the co-design can (103) | not independently cited; justified *by* the envelope rather than by a density source | **MEASURED** as a curve (B2) |
| **p ∈ {0.02, 0.05, 0.10}** | loss grid | mechanism-grounded (802.11 broadcast has no ACK, no retransmission ⇒ receiver sees raw channel error) | no single measured FANET PER; 20–100× more pessimistic than TS 22.125's managed-C2 99.9 % — conservative, but not tied to a measurement | **DECLARED** (B4) |
| **ε = p** | verifiability target | makes T6's n_max = 1 exact, closing the fragmentation escape | a looser ε would admit fragmentation and weaken T6; the theorem is stated with its condition (ε ≤ p) rather than the value | **DECLARED** |

## 2. What is claimed, and how

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Headline = total bytes (−58.68 %), reported as a decomposition** | honest attribution | claim matches evidence; all four axes genuinely contribute to *total* bytes | a smaller, less quotable number than the 75 % it replaces | **FORCED** by F13 |
| **Never quote the bare 75 % auth cut** | — | forecloses *"is your result just the definition of batching?"* — for that metric it is: the ratio is **1 − 1/b**, invariant to H_f, g_a, encoding and scheme | the most memorable number in the thesis | **FORCED** by F13 |
| **Load-bearing claim = feasibility envelope** | N_max 25 / 32 / **103** | a capability statement that genuinely needs all four axes *plus* the channel model | depends on the channel model's validity, which is validated for throughput only (D3) | **DECLARED** |
| **Report both the compliant and the declared operating point** | costs nothing (identical bytes) | kills the "you picked a loose bound" objection outright | two numbers to explain instead of one | **DECLARED** |

## 3. Model scope — what is deliberately not modelled

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **No DCF channel-access delay in D(b)** | tractable closed form; the M/M/1 term covers a node's own queue (ρ≈0.002) | D(b) is a **lower bound**, credible only at low U. Must be read alongside U, never quoted near U→1 | **OPEN** (C1) |
| **Saturation channel models at a non-saturated point** | Bianchi / Ma & Chen are validated and closed-form | correct as a *capacity* bound (which is how U uses them), **not** valid for delay at our load | **DECLARED** (C2) |
| **Single collision domain; no mobility, spatial reuse or hidden terminals** | one clean, validated regime | a real formation gets spatial reuse (helps) and hidden terminals (hurts); bounded by a sweep showing the idealised model is conservative to ≈300–400 m and optimistic by 15.7 % at 500 m | **DECLARED** (C3) |
| **i.i.d. per-frame loss** | closed-form V | real FANET loss is bursty. F11 proved V_D ≤ V_B under *any* correlation, so the **T3 ordering survives**; absolute V still assumes independence | **PARTLY OPEN** (C4) |
| **No sender-side CPU throughput constraint** | simpler optimizer | verified never to bind (worst case 13.9 % of one core; binds at ~360 rec/s vs our 20) | **DECLARED** (C5) |
| **K = 16 delta keyframe interval, unoptimized** | bounded scope | K is a real design variable left on the table; delta's 45 B depends on it | **DECLARED** (B5) |

## 4. Wire format and cryptography

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **H_f = 44 B** | measured from `wire.py` | replaced an unreferenced 40 B assumption | it is *placement-dependent* in reality (A 45→51, D 81); the flat value understates A by 1 B and D by 37 B — **both conservative** | **MEASURED** (B1) |
| **CBOR text keys in the frame header** | readable, standard, deterministic | 29 of 43 skeleton bytes are key *names*; an integer-keyed profile would be materially smaller. **This thesis does not claim a tuned wire format** | **DECLARED** |
| **32 B `prev_hash` per record (802.11)** | independent per-record tamper evidence | ~71 % of a delta record is incompressible hash; its CPU cost (2×2745.5 ns/record) is now charged too (D7) | **DECLARED** (F5) |
| **Per-frame chaining on LoRa only** | b 2→7 at DR5, **3.03×** the sustainable rate | two framings of one ledger; within a LoRa frame tamper-evidence rests on the frame signature rather than independent hashes — equivalent in strength, no longer independent | **DECLARED** (F5) |
| **BLS = 96 B (blspy min-pubkey)** | timings and size are coherent | the 48 B min-sig variant was specified originally; 96 B makes BLS lose the byte game outside multi-signer aggregation | **DECLARED** |
| **Ed25519 over ECDSA** | wins on ARM (259 vs 327 µs verify), the thesis platform | order **flips on x86**; the choice is platform-specific and the auth-byte result is identical either way (both 64 B) | **MEASURED** (D8/F6) |

## 5. Measurement and reproducibility

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Energy composed from measured parts** | per-op timings and powers are all measured; **validated end-to-end** on four configurations | was ~32 % low; both causes found and fixed (D7 chain hash, D6 composed-pipeline power). **Residual +7.5…+14.3 %, all frame assembly.** Absolute energy is a **lower bound by ~10–14 %** | **MEASURED** (D1/F14) |
| **One `p_cpu_w` for all configurations** | keeps the model **predictive** — a per-config power would mean metering a design before you could model it | measured spread across four configurations is only **3.8 %**, so this holds. The old 0.634 W was wrong for a different reason: it came from *isolated primitives* and understated composed pipelines by 18.2 %. Now **0.749 W** | **MEASURED** (D6) |
| **LoRa arm is analysis-only** | the result is derivable from primary specs alone | **no hardware, no energy column, no measured validation** — must be stated in-chapter | **DECLARED** |
| **NS-3 validates throughput only** | the airtime/contention model is grounded | latency, energy and loss behaviour are **not** validated by simulation; "NS-3-validated" must not imply more | **OPEN** (D3) |
| **10 s NS-3 runs, not 30 s** | ~5000 busy periods/run × 10 seeds; tight CIs | a documented deviation from docs/04 §3 | **DECLARED** |
| **Frozen artifacts + staleness gate** | staleness cannot be committed unnoticed | every deliberate change costs a re-freeze | **DECLARED** |
| **Contiguous batch grids** | no quantized optima | larger sweeps. *Sparse grids caused F3 **and** understated F5 as 2.75× when the true value is 3.03×* | **FORCED** by F3/F5 |

---

## The rows an examiner will press hardest

1. **The 250 ms deviation** (§1) — the only place a headline number depends on a choice looser than
   the applicable standard. Answer with the region: the mechanism is deadline-independent, only b
   depends on Λ·D_max, and the compliant point is reported.
2. **`1 − 1/b`** (§2) — answered by refusing to lead with that metric at all.
3. **D(b) has no channel-access delay** (§3) — the freshness constraint that *sets b* omits the
   dominant delay term at high load. Mitigated by reporting U, not by fixing the model.
4. **Energy is 10–14 % low** (§5) — was 32 %, root-caused and fixed; the residual is uncharged
   prototype framing overhead, measured and stated. Absolute values are lower bounds.
