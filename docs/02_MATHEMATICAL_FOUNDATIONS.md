# 02 — MATHEMATICAL FOUNDATIONS
All symbols per doc 01 §2. Every theorem lists its empirical validation hook.
All numeric examples below were verified by script (`pathA_opt.py`, research archive).

## T1 — Overhead-dominance threshold
**Claim.** With inline per-record authentication, the authentication byte fraction is
φ(s,g) = g/(s+g), and φ ≥ α ⇔ **s ≤ g·(1−α)/α**. In particular auth dominates (α=½)
exactly when s ≤ g.
**Proof.** φ ≥ α ⇔ g ≥ α(s+g) ⇔ g(1−α) ≥ αs. ∎
**Numbers (g=64):** JSON 358→15.2%; CBOR 130→33.0%; delta 40→61.5%. Compression moved the
bottleneck to authentication — the thesis motivation. **Validate:** E1.

## T2 — Frame-level batching optimum and the amplification law
**Setup.** Placement B/C packs b records + one auth object (g_a bytes) + header H_f into
one frame: feasibility b ≤ b_max(s) = ⌊(M − H_f − g_a)/s⌋.
**Claim (i).** Per-record auth overhead ω(b) = (g_a+H_f)/b is strictly decreasing, so the
byte-minimal feasible batch is b = b_max(s).
**Claim (ii) (amplification, see T2a for when it applies).** Relaxing the floor, per-record on-air bytes are
C(s) = s + (g_a+H_f)·s/(M−H_f−g_a) = **s · A**, with **A = M/(M − H_f − g_a) ≥ 1**.
Hence every payload byte saved by compression saves A on-air bytes **in the MTU-limited regime**,
and A grows as M shrinks (802.11: A≈1.07; LoRa M=222: A≈1.88 — the low-rate leverage, doc 30).
This is MTU-efficiency algebra, not a new law; ⚠️ **and on 802.11 the regime is never reached —
see T2a.**
> *Provenance of the A values (2026-07-28):* both were recomputed at the current g_a = 64 B
> (Ed25519). The previous figures were 1.06 and 1.35; 1.06 reproduces exactly at the superseded
> g_a = 48 B assumption (1500/1412 = 1.0623), but **1.35 could not be reproduced at g_a ∈ {48, 64,
> 96}** — the LoRa value at g_a=48 is 222/134 = 1.657. Treat the old LoRa figure as unsourced; the
> current one is 222/118 = 1.881.
**Proof.** (i) ω′(b)<0. (ii) substitute b=(M−H_f−g_a)/s into s+ω(b) and factor. ∎
**Numbers (M=1500, H_f=40, g_a=48):** CBOR b_max=10 → 138.8 B/rec, φ=6.3%; JSON b_max=3 →
387.3 B/rec, φ=7.6%; delta b_max=35 → 42.5 B/rec, φ=5.9%. Batching restores auth overhead
to O((g_a+H_f)/M) regardless of encoding. **Validate:** E2.

## T2a — Which ceiling binds, and what compression is therefore worth ⚠️ (2026-07-28)
**Motivation.** T2 derives A **at the MTU limit**, where b = b_max(s) = (M−H_f−g_a)/s makes the
overhead term proportional to s. Once freshness is enforced (docs/02 §7, audit F10) the batch may
be capped *before* the MTU, and then the derivation no longer applies.

**Two ceilings.** b* = min(b_MTU, b_fresh) with b_MTU = ⌊(M−H_f−g_a)/s⌋ and **b_fresh = ⌊Λ·D_max⌋**
(fill time dominates D(b), so the freshness ceiling depends on **neither the encoding nor the
scheme**). Freshness binds ⇔ ⌊Λ·D_max⌋ < ⌊(M−H_f−g_a)/s⌋, i.e. exactly when
**s < (M−H_f−g_a)/(⌊Λ·D_max⌋+1)**.

**Claim (marginal value of compression).**
- *MTU-limited:* C(s) = s·A, so **dC/ds = A = M/(M−H_f−g_a)** — T2 as written.
- *Freshness-limited:* b is independent of s, so C(s) = s + (g_a+H_f)/b_fresh and
  **dC/ds = 1 exactly**. Compression pays 1×, not A×, and the residual authentication cost is a
  **floor (g_a+H_f)/(Λ·D_max) that compression cannot touch at all.**
**Proof.** Differentiate C in each regime; b is constant in s in the second. ∎

**Measured consequence (802.11, M=1500, H_f=40, g_a=64, Λ=20 rec/s, D_max=250 ms).** The boundary
is s < 232.7 B. Every encoding in this study is below it — delta 45, msgpack 65.2, cbor 66.3, json
191.1 — so **freshness binds for all of them and A = 1.0745 is never operative on the 802.11 arm.**
Verified numerically: the marginal rate between adjacent encodings is 1.0000 to 12 decimal places.

**Contrast — the low-rate link is where the leverage actually lives.** On LoRa (M=222) the boundary
falls to s < 19.7 B, so the **MTU binds** for every feasible encoding and **A = 222/118 = 1.881 IS
operative**. The "compression pays ×A" leverage that motivates docs/30 is real — and this analysis
shows it is *exclusive* to the low-rate arm, which strengthens rather than weakens that motivation.

Implemented as `optimizer.binding_constraint` / `effective_amplification`. **Validate:** E2/E5.

## T3 — Loss-robustness frontier (frame-level Pareto-dominates block-level)
**Setup.** Frame-level (B/C): each frame self-verifiable ⇒ V_B = 1−p; a loss costs b
records (loss-locality). Block-level (D): b_D records span n(b_D) = ⌈(b_D·s+g_a+H_f)/M⌉
frames with one signature over all ⇒ V_D = (1−p)^n.
**Claim (i).** The verifiability constraint V ≥ 1−ε admits at most
n_max = ⌊ln(1−ε)/ln(1−p)⌋ frames; if ε ≤ p then n_max = 1 and block-level is infeasible
beyond a single frame — i.e., **whenever the robustness target is at least as strict as
the loss rate, frame-level batching is forced**.
**Claim (ii).** Even when n>1 is feasible, D's byte saving over B is bounded:
ω(b_B_max) − ω(b_D) ≤ (g_a+H_f)/b_max(s) = (g_a+H_f)·s/(M−H_f−g_a) bytes/record
(≤ 8.8 B for CBOR), while verifiability degrades geometrically. On the (bytes, V) plane,
B Pareto-dominates D for all V > (1−p)^2.
**Proof.** (i) solve (1−p)^n ≥ 1−ε. (ii) ω differences telescope; bound at b_max; V_D
monotone decreasing in n. ∎  **Validate:** E3 (measured V and goodput vs b, p).

**Claim (iii) — robustness to correlated loss (audit F11, 2026-07-28).** The (1−p)^n form assumes
*independent* frame loss, which our emulator also implements — so E3's V_meas≈V_theory agreement is
a consistency check, not a validation. The conclusion nonetheless holds for **any** loss process:

> V_D(n) = P(all n frames of the block arrive) ≤ P(one given frame arrives) = 1−p = V_B,

for any stationary loss process of mean rate p, whatever its correlation — because a joint
probability cannot exceed a marginal. **Equality only at n=1.** So block-level can never
out-verify frame-level, and when ε ≤ p it can never become feasible at n ≥ 2. **Independence is the
worst case for D**; correlation narrows the gap but cannot invert it.
Quantified by Gilbert–Elliott simulation at matched mean p=0.05: V_D(n=2) rises from 0.9025
(independent) to 0.9447 at a mean burst of 10 frames and 0.9498 at 160 — asymptotically 1−p, never
past it, and never reaching the 0.95 feasibility threshold.

## T4 — Scheme selection: Ed25519 self-batch vs BLS cross-signer aggregation
**Own records (self-batch).** One ordinary signature covers b own records, so for
byte-cost Ed25519 and BLS are near-equivalent (64 vs 48 B amortized over b). Ed25519's
verify t_vf^ed ≈ 20–60× cheaper than a BLS pairing on RPi4-class CPUs ⇒ **Ed25519 wins
self-batching outright** (bytes ~equal, compute far lower). [Audit fix of doc 25.]
**Relayed records (cross-signer).** Forwarding b records from distinct signers:
Ed25519 must carry b·64 B; BLS aggregates to 48 B. BLS saves Δ(b) = 64 − (48+H_a)/b
bytes/record but costs Δt = t_av^bls(b)/b − t_vf^ed extra CPU per record.
**Crossover.** BLS is energy-optimal for relayed traffic iff
**P_r · 8·Δ(b)/R > P_c · Δt**, and throughput-feasible iff t_av^bls(b)/b ≤ 1/Λ.
At R=6 Mb/s: radio side ≈ P_r·75 µs vs CPU side ≈ P_c·(1–3 ms) ⇒ **Ed25519 wins on
802.11; BLS's regime is low-rate links and attestation compression** — a falsifiable,
regime-dependent rule the hardware measurements (E4/P7) will pin down.
**Proof.** Energy difference per record = P_r·8Δ/R − P_c·Δt; sign at the stated point. ∎

## T5 — Co-design theorem ("compression pays A-times, then binds")
Combining T1–T4: the joint optimum is **empirically separable** — *verified by exhaustive search
over the full grid (4 encodings × 3 schemes × 4 placements × 32 batches = 1536 points), not proven*;
a non-separable optimum would be found if one existed. Pick the smallest deterministic
encoding e* (min s), placement B (self) / C (relay) at **b\* = min(b_max(s), ⌊Λ·D_max⌋)** (T2a — on 802.11 the second
term binds), scheme per T4; total
on-air bytes per record = s·A (T2), so compression's benefit is amplified by A and grows
as b_max(s) rises, until either the verify-throughput constraint t_verify(b)·Λ ≤ 1 or the
MTU binds. **Validate:** E5 end-to-end vs baselines {A+JSON, A+CBOR, D-overagg}.

## T6 — Authentication-exclusion threshold (2026-07-28) ⚠️
*Implemented: `models/optimizer.py` (`max_fragments`, `max_record_bytes`, `exclusion_tier`);
pinned: `tests/unit/models/test_exclusion_t6.py`.*

T1–T5 ask what a saved byte **buys**. T6 asks the prior question: **whether the link admits
authenticated telemetry at all.** It is a closed form, needs no simulation, and is link-agnostic —
LoRa is just where it bites.

**Statement.** A frame that is independently verifiable must carry the frame header H_f, the
authentication object g_a, and at least one record s. So a link of maximum payload M admits
authenticated telemetry **iff**

        s_max(M) = M − H_f − g_a  ≥  s_min                                        (T6)

and no choice of batch size, chain placement, or aggregation changes this: those decide only how
the space *above* the floor is used.

**Fragmentation does not escape it.** The obvious objection is to split an oversized signature
across frames. T3 forecloses that: a unit spanning n frames verifies with probability (1−p)^n, so
V ≥ 1−ε requires n ≤ ⌊ln(1−ε)/ln(1−p)⌋. **At ε ≤ p this is exactly n = 1** — the entire
verifiability budget is spent on the first frame. At the study's ε = p = 0.05, fragmenting is
already a constraint violation, so (T6) is evaluated at n = 1 and is an exclusion, not an
inconvenience.

**Three tiers, because each one names a different escape route** (`exclusion_tier`):

| tier | condition | what could fix it | what cannot |
|---|---|---|---|
| **signature** | M < g_a | a smaller signature scheme only | header design, *any* encoding, batching, chaining |
| **framing** | g_a ≤ M < H_f + g_a | a leaner frame header | the encoding |
| **encoding** | H_f + g_a ≤ M < H_f + g_a + s_min | a smaller record encoding — **and here T2a's A applies** | — |

**Applied to EU868** (H_f = 44 B **measured**, docs/01 §2a; g_a = 64 B for Ed25519/ECDSA; s_min =
13 B, the delta record under the adopted per-frame chaining of §9b):

| DR | M (RP002 T.13) | s_max | tier | note |
|---|---|---|---|---|
| 0, 1, 2 | 51 B | −57 | **signature** | 64 B signature alone overflows a 51 B payload |
| 3 | 115 B | **7 B** | **encoding** | misses by **6 bytes** — 7 B of room, 13 B record |
| 4, 5, 6 | 242 B | 134 B | — feasible | |
| *802.11* | 1500 B | 1392 B | — feasible | |

**The tier-1 result is the strong one.** DR0/DR1/DR2 stay excluded *with a zero-byte header and a
zero-byte record*: it is the signature alone that does not fit. The only escape is a smaller
authentication object, and the smallest standardised one is **48 B** — a compressed BLS12-381 G1
point in the `minimal-signature-size` variant of draft-irtf-cfrg-bls-signature-05, which the draft
states targets **126-bit security** (not 128 — corrected 2026-07-29, item A5). The same draft records
ECDSA at 64 B, so 48 B is genuinely the short end of the standardised range. It *does* fit 51 B, but
leaves **3 bytes** for the header and the record together. So the
exclusion is not an artifact of this design: **the four longest-range LoRa modes cannot carry
per-frame-verifiable telemetry at 128-bit security, period.**

**Why this matters to the thesis.** It converts the LoRa arm from a table of numbers into a
*negative result with a proof*: co-design has a domain of validity, and T6 is its boundary. It also
locates exactly where compression is worth pursuing — tier 3 (DR3) is the only regime an encoder can
attack, and T2a says that is precisely where the amplification A is operative.

## ~~T7 — Medium-exclusion threshold~~ — **WITHDRAWN 2026-07-29, same day it was written** ⚠️
*Retracted by its own validation experiment (D3, `results/raw/ns3_delay.csv`). Kept visible rather
than deleted, because the way it failed is instructive.*

**What was claimed.** That capacity can exclude what frame size permits, with the exclusion
threshold at **U ≥ 1** — U being offered load over *saturation* throughput. From that: at N = 50
under the 3GPP 100 ms bound only 4 operating points are runnable, only 2 batch, and the achievable
authentication cut caps at **50 %**.

**Why it is wrong.** U ≥ 1 is not a feasibility boundary. Saturation throughput is what the channel
carries when *every* node is backlogged; a lightly loaded channel collides far less and carries
substantially more. NS-3 measurement at N = 50, 288 B broadcast:

| U (offered ÷ saturation) | delivered | mean delay | access delay omitted by D(b) |
|---|---|---|---|
| 0.111 | 1.0000 | 0.50 ms | +0.011 ms |
| 0.557 *(reference point)* | 0.9898 | 0.52 ms | **+0.033 ms** |
| 1.003 | 0.9884 | 0.57 ms | +0.073 ms |
| 1.672 | 0.9808 | 0.63 ms | +0.133 ms |
| 2.230 | 0.9719 | 0.69 ms | +0.199 ms |
| **≈2.80** | **0.9500** | — | — *(V = 1−ε crossing)* |
| 3.345 | 0.9292 | 0.92 ms | +0.418 ms |
| 6.690 | 0.4228 | 2.69 ms | +2.185 ms |

*(N=50, 288 B broadcast, 5 seeds × 20 s per point; `results/raw/ns3_delay.csv`.)*

**The system is still delivering 98.8 % of frames at U = 1.00.** The real boundary — where
verifiability falls to V = 0.95 — sits at **U ≈ 2.80**, and at that boundary the 3GPP-compliant
configuration (Λ = 50 Hz, D = 100 ms, U = 1.394) is comfortably **feasible**. So the claimed
exclusion does not exist at N = 50, and the "50 % ceiling" was an artifact of the wrong threshold.

**Second structural error.** The theorem assumed overload manifests as *delay*. It does not:
**802.11 broadcast has no ARQ and no queue buildup**, so excess offered load is dropped, not
queued. Even at U = 8.9 — nine times saturation throughput — mean delay is 2.7 ms. Overload
degrades **delivery**, never latency. Any capacity argument here must be made in V, not in D.

### What survives: the latency–capacity coupling (a cost, not an exclusion)
The underlying mechanism is real and worth stating. Because b ≤ ⌊Λ·D_max⌋ (T2a), tightening the
freshness deadline **shrinks the batch** and therefore **raises the frame rate** the medium must
carry for the same Λ. Latency and capacity genuinely pull in opposite directions. Measured against
the V ≥ 0.95 boundary, that costs swarm size rather than forbidding operation:

| operating point | b | bytes | largest neighbourhood (V ≥ 0.95) |
|---|---|---|---|
| Λ = 20, D = 250 ms *(reference)* | 4 | 58.68 % cut | **N ≤ 233** |
| Λ = 50, D = 100 ms *(3GPP-compliant)* | 4 | **58.68 % cut — identical** | **N ≤ 116** |

**Meeting the standard's deadline costs a factor of two in supportable swarm size and nothing in
bytes.** That is the honest, measured statement, and it is a better result than the theorem it
replaces: the co-design is standards-compliant, and the price is quantified.

**Lesson recorded.** T7 was written from a model quantity (saturation throughput) treated as a
physical limit, and published into docs and the paper before the experiment that tested it existed.
The validation was already scheduled as item D3; running it first would have prevented the claim.

## 6. Channel model — Bianchi DCF (802.11, saturation)
Fixed point over (τ, p_c): τ = 2(1−2p_c) / [(1−2p_c)(W+1) + p_c·W(1−(2p_c)^m)],
p_c = 1−(1−τ)^{N−1}; W=16, m=6. **Solve with damped iteration** p←0.7p+0.3p_new,
tol 1e−12 (undamped oscillates at high N — verified).

**Slot durations — airtime is QUANTISED, not linear (decision D9, 2026-07-28).** An 802.11a PHY
transmits whole 4 µs OFDM symbols and prepends 16 SERVICE + 6 TAIL bits; the MAC carries 36 B of
overhead (LLC/SNAP 8 + MAC header 24 + FCS 4). Therefore:

    PPDU(N) = T_phy + ceil((16 + 8N + 6) / (R·4 µs)) · 4 µs        [N = PSDU bytes]
    T_s(L)  = PPDU(L+36) + SIFS + T_ack + DIFS                     [unicast success]
    T_c(L)  = PPDU(L+36) + DIFS                                    [collision]
    T_air(L)= PPDU(L+36) + DIFS                                    [broadcast; the energy model]
    T_ack   = PPDU(14) = 44 µs

with T_phy=20 µs, SIFS=16 µs, slot=9 µs, DIFS=34 µs. Throughput S = P_tr·P_s·E[payload]/E[slot].

**There is deliberately no "T_fx ≈ 123 µs" constant and no affine `T_air(L) = T_fx + 8L/R`.**
Airtime is a *step* function of L, so no fixed part plus linear term exists. The superseded
continuous form understated a 1400 B data frame by **0.41 %** and an ACK by **12.1 %** measured
against NS-3 3.41 (audit A1); it also used 34 B of MAC overhead instead of the real 36 B.

Verified: PPDU(1436) = 1940 µs and PPDU(14) = 44 µs, both matching NS-3 3.41 exactly, and the
post-success deferral floor SIFS+T_ack+DIFS = 94 µs matching the measured trace.

**Validate:** E5 vs NS-3; expect and *report* known gaps rather than force-fitting. Measured
against NS-3: unicast agrees to **+1.28 … −0.49 %** across N=5–50, broadcast (Ma & Chen) to
**≤1.44 %** — both re-measured on **ns-3.48** after the D4 migration (2026-07-29). On ns-3.41 the
same comparison read +0.6/−2.9 % and ≤1.1 %: **unicast agreement improved, broadcast widened
slightly**, and both are reported rather than quoting whichever version flattered the model.

### 6b. Channel capacity as a co-design constraint (2026-07-28, audit F12)
The channel model was validated against NS-3 but never *used* by the optimizer. It is now a hard
constraint, which turns "how many bytes?" into the question an operator actually asks —
**how many UAVs, at what telemetry rate?**

    U = frames offered / frames deliverable
      = (N_local·Λ_i / b) ÷ (S(N_local, frame) / 8·frame)          [S from §6a, Ma & Chen]

Capacity is **strongly frame-size dependent** — small frames pay the preamble and signature
overhead more often — so U must be evaluated at each configuration's own frame size. Evaluating a
284 B design against the 1400 B figure the NS-3 matrix happens to use overstates headroom by ~2× at
the critical corner.

**Envelope** (`results/raw/capacity_envelope.csv`, `make exp-capacity`), delta + Ed25519 + B:

| N_local | 1 Hz | 5 Hz | 10 Hz | **20 Hz** | 50 Hz |
|---|---|---|---|---|---|
| 20 | 0.02 | 0.10 | 0.12 | 0.14 | 0.26 |
| 35 | 0.05 | 0.25 | 0.30 | 0.35 | 0.65 |
| **50** | 0.07 | 0.35 | 0.42 | **0.50** | 0.91 |
| 75 | 0.09 | 0.47 | 0.57 | 0.67 | **over** |
| 100 | 0.12 | 0.61 | 0.72 | 0.86 | **over** |

PX4's companion-computer rate (50 Hz) is supported to ~50 UAVs; the chosen (50, 20 Hz) point sits
at exactly 50 % utilisation.

**A result, not just a constraint: the baselines cannot physically run at fleet scale.** At
N_local=50, Λ_i=20 the inline baselines demand more frames than the medium delivers —
**A+JSON U = 2.28, A+CBOR U = 1.53** — against the co-design optimum's **U = 0.55**. The
optimisation is not merely more efficient than the Pillar-1 baseline; at this fleet size it is the
difference between working and not working.

⚠️ **This is a THROUGHPUT envelope only.** D(b) in §7 carries no channel-access delay — its M/M/1
term covers a node's own frame queue (ρ ≈ 0.002 here), not waiting for a contended medium. As U
approaches 1 the DCF saturates and real latency rises far above the modelled D(b), *invisibly*.
Read `channel_util` alongside any freshness figure; treat D(b) as credible only at low U. Modelling
DCF access delay is open work.

### 6a. Broadcast is a DIFFERENT model — do not reduce the unicast one ⚠️
The above is the **ACK/unicast** model. AUTHBC's telemetry substrate is **broadcast**, which never
ACKs, never retransmits, and therefore never doubles CW. The obvious reduction — keep the formula,
drop the ACK, fix τ = 2/(W+1) — is **WRONG**: it under-predicts NS-3 by **16× at N=50** (audit F9).
This project used that reduction until P7; it is retained in code only as a labelled failure.

Use instead **Ma & Chen's broadcast model** (`models.broadcast_dcf`), which accounts for the
**backoff counter Consecutive Freeze Process (CFP)**: with CW frozen at W₀, a station that has
just transmitted redraws its backoff and may draw **0**, taking the medium immediately after DIFS,
while every station that deferred necessarily holds a counter ≥ 1. In unicast the ACK timeout
(> DIFS) blocks colliders from doing this, so CFP can only follow a success; **in broadcast there
is no ACK timeout, so every collider can seize the next slot**, and with W₀ small relative to N
this becomes the dominant way any frame succeeds alone.

    τ_s = 2/W₀                                  (NOT 2/(W+1))
    τ_f(i) = τ_s / W₀^i                          (i-th freeze stage)
    p_bs = 1−(1−τ_s)^n ,  p_ss = n·τ_s(1−τ_s)^{n−1}
    E[N_sf] = Σ_i n·τ_f(i)(1−τ_f(i))^{n−1} ,  E[N_bf] = Σ_i 1−(1−τ_f(i))^n
    S = (p_ss + E[N_sf])·8L / (σ + (p_bs + E[N_bf])·T),  T = T_phy + 8(L+MAC)/R + DIFS + δ

Verified against our own NS-3 runs (802.11a, 6 Mb/s, W₀=16, L=1400 B): **saturation throughput**
agrees to **≤0.36 %** on ns-3.41 and **≤1.44 %** on ns-3.48, at N = 5, 10, 20, 35, 50 — a regime the
original papers did not test (they used W₀ = 32 and 128 at 1 Mb/s).

All three quantities are **independently measured** from the PHY trace (`ns3_dcf_residual.csv`,
broadcast rows, median over seeds). Full bounds, both simulator versions:

| quantity | ns-3.41 | ns-3.48 |
|---|---|---|
| success probability p_s | ≤0.36 % | **≤2.49 %** (N=35) |
| idle slots per busy period | ≤0.75 % | **≤0.47 %** |
| saturation throughput | ≤0.36 % | **≤1.44 %** |

⚠️ *Two corrections, 2026-07-29.* The previous text said "all within ≤0.36 %"; the idle-slot column
actually reaches **0.75 %** at N=10 on ns-3.41 — visible in the p7 audit's own table and simply
mis-summarised. And on ns-3.48 the overall bound widens to **≤2.49 %**. (An intermediate claim that
these were not independent measurements — audit F15 — was **retracted**: it rested on a
broadcast/unicast filtering error and on treating an expected correlation as evidence.)

**References (verified from primary sources, docs/literature/):**
- G. Bianchi, "Performance Analysis of the IEEE 802.11 Distributed Coordination Function,"
  *IEEE JSAC* 18(3):535–547, 2000. doi:10.1109/49.840210
- X. Ma and X. Chen, "Saturation Performance of IEEE 802.11 Broadcast Networks,"
  *IEEE Communications Letters* 11(8):686–688, Aug. 2007. doi:10.1109/LCOMM.2007.070040
  *(the letter's eq. (6) misprints p_ss; use the journal's eq. (8))*
- X. Ma and X. Chen, "Performance Analysis of IEEE 802.11 Broadcast Scheme in Ad Hoc Wireless
  LANs," *IEEE Trans. Veh. Technol.* 57(6):3757–3768, Nov. 2008. doi:10.1109/TVT.2008.918731
- I. Tinnirello, G. Bianchi, Y. Xiao, "Refinements on IEEE 802.11 Distributed Coordination
  Function Modeling Approaches," *IEEE Trans. Veh. Technol.* 59(3):1055–1067, Mar. 2010 —
  the unicast counterpart ("anomalous slots"); confirms consecutive channel slots are correlated.

**Decision D9 applied (2026-07-28):** the exact quantised form above is now normative and is used
by **every** consumer — the NS-3 comparison, `models.energy`, and `channel.airtime` — so the repo
has exactly one airtime implementation. Re-freeze consequences: E5's energy column moved
**+0.096 %** (52.1487 → 52.1985 µJ) and E3's goodput **−2.1 %** (small frames pay proportionally
more for symbol rounding). The **auth-byte headline is byte-based and did not move under D9**.
(It later changed for an unrelated reason — freshness enforcement, audit F10 — to **75.00 %, PASS**.)

*Scope note:* T4/E4's ΔRADIO = 8·Δbytes/R is a byte *difference*, which quantisation makes
frame-size dependent (±5 % on ~43 µs). E4 is left on the continuous form: the verdict has ~90×
margin (min κ\* = 31.64 vs plausible κ = 0.34), so no conclusion is sensitive to it.

## 9. LoRa arm — EU868, its OWN parameter set (2026-07-28) ⚠️
**The 802.11 arm's numbers do not transfer.** They differ by two to three orders of magnitude and
the binding constraint is different *in kind*: a regulatory airtime quota, not a frame size or a
latency budget. `models/lora.py` implements this arm; `experiments/lora/` runs it separately.

**Sources (both retrieved and read in full, not recalled):**
- **Semtech SX1276/77/78/79 datasheet, Rev. 7, May 2020** — §4.1.1.5 (Rs = BW/2^SF) and §4.1.1.7
  "Time on air", p. 32:

      Tsym      = 2^SF / BW
      Tpreamble = (npreamble + 4.25)·Tsym
      npayload  = 8 + max(ceil((8·PL − 4·SF + 28 + 16·CRC − 20·IH)/(4·(SF − 2·DE)))·(CR+4), 0)
      Tpacket   = Tpreamble + npayload·Tsym

- **LoRa Alliance RP002-1.0.3 Regional Parameters (2021)** — Table 8 (EU863-870 DR→SF/BW/bitrate),
  Table 13 (max application payload N, *non*-repeater-compatible), regional summary: EU868
  **Duty Cycle < 1 %**. *(docs/02's earlier "LoRa M=222" is Table 12, the **repeater-compatible**
  figure; the non-repeater limit is **242 B**. Provenance now stated.)*

**Λ and D are DERIVED here, not configured.** A frame of airtime T may repeat only every T/duty, so
the sustainable rate is Λ = b·duty/T and the freshness of the oldest record in a batch is that same
interval. **Duty cycle fixes both**, so this arm has no independent D_max to trade against bytes the
way 802.11 does (T2a). This is the **third regime**:

| regime | what caps the batch | where |
|---|---|---|
| MTU-limited | frame size | — |
| freshness-limited | Λ·D_max | **802.11** |
| **duty-cycle-limited** | regulatory airtime quota | **LoRa** |

### Two findings (measured, `results/raw/lora_eu868.csv`)

**(1) Authentication does not fit at all below DR4 — and this is a theorem, not a measurement.**
Per-frame overhead is H_f 44 (**measured**, docs/01 §2a) + signature 64 = **108 B**, against a
regional limit of 51 B at DR0–DR2 and 115 B at DR3, which leaves 7 B — under the 13 B smallest
AUTHBC record. Only DR4/5/6 are feasible, and JSON never fits. **See T6** for the general form, the
proof that fragmenting cannot escape it, and the tier structure: DR0–DR2 fail on the *signature
alone* (64 B > 51 B payload, so no encoding or header design can rescue them), while DR3 fails on
the encoding by **six bytes**.

**(2) The sustainable rate is 55–193× below the 802.11 arm.** At DR5, delta, per-frame chaining,
b=7: frame 231 B, so one frame per **38.4 s** and **Λ = 0.182 rec/s** — a record every 5.5 s, against
the 802.11 arm's 20 rec/s (**110×**). Freshness is likewise **38.4 s**, i.e. **154× the 802.11 D_max
of 250 ms**. Under the 802.11 per-record format it is worse still (Λ = 0.060 rec/s at DR5, **333×**
below).

### 9c. The LoRa capacity envelope — SIMULATED, not derived (D2, 2026-07-29)
*Artifact: `results/raw/lora_capacity.csv` · scenario `ns3/authbc-lora-capacity.cc` on ns-3.48 with
the signetlabdei LoRaWAN module · driver `ns3/run_lora_capacity.py`.*

Everything else in this arm is analytical, deliberately: time on air is the SX1276 formula and the
sustainable rate is the duty cycle, both deterministic, so simulating them would be circular.
Exactly one quantity resists that — **how many nodes can share the channel** — because LoRaWAN
uplinks are pure ALOHA, with no carrier sense and no ACK. The duty cycle says what *one* node may
legally send; it says nothing about fifty.

Measured at DR5, AUTHBC frame 218 B (b=6), one transmission per duty-cycle interval, 3 seeds × 1 h,
against the same **V ≥ 1−ε** criterion the 802.11 envelope uses:

| N | delivered | meets V ≥ 0.95 |
|---|---|---|
| 2, 3, 5 | 1.0000 | ✅ |
| 8 | 0.8656 | ✗ |
| 10 | 0.7731 | ✗ |
| 20 | 0.5795 | ✗ |
| 50 | 0.2532 | ✗ |

**N_max = 5**, and the cliff is brutally sharp — perfect at 5, 13 % loss at 8. That is ALOHA without
carrier sense: there is no backoff to absorb contention, so the transition from "fine" to "unusable"
spans less than a factor of two in N.

**The two penalties compound, and this is the number the chapter should lead with:**

| | per-node Λ | N_max (V≥0.95) | aggregate |
|---|---|---|---|
| 802.11a, delta/B, b=4 | 20 rec/s | 103 | **2060 rec/s** |
| LoRa EU868 DR5, b=6 | 0.165 rec/s | **5** | **0.82 rec/s** |
| ratio | 121× | 21× | **≈2500×** |

The arm was already known to be ~120× slower *per node*; it is also ~20× smaller *per domain*, and
the product is what separates the two regimes. **LoRa is not a slower version of the 802.11 arm — it
is a different regime**, which is precisely the "generalisation to the low-rate regime" framing.

⚠️ **Frame size is the module's limit, not ours.** The module enforces RP002-1.0.3 **Table 12**
(repeater-compatible, 222 B); `models/lora.py` uses **Table 13** (non-repeater, 242 B) and documents
that choice. At DR5 that caps b at 6 here where our model reports 7. Both readings of the standard
are defensible; we simulate what the module accepts and state the difference rather than reconcile
it silently.

**Scope.** This is *simulation*, not hardware — item D2's "no measurement of any kind" becomes "a
simulated bound", not a measured one. No LoRa radio was metered, and no energy column exists.

### 9b. Per-frame chaining is the adopted LoRa wire format (F5, decided 2026-07-28) ⚠️

Moving the chain hash from per-record to per-frame (audit F5) is worth far more here than on 802.11,
because the regional payload limit binds — so smaller records convert into *more records per frame*:

| DR | chain mode | b | bytes/record | **Λ (rec/s)** |
|---|---|---|---|---|
| 4 | per_record *(802.11 format)* | 2 | 99.0 | 0.0337 |
| 4 | **per_frame** | **7** | **33.0** | **0.1035** — **3.08×** |
| 5 | per_record | 2 | 99.0 | 0.0601 |
| 5 | **per_frame** | **7** | **33.0** | **0.1822** — **3.03×** |
| 6 | per_record | 2 | 99.0 | 0.1201 |
| 6 | **per_frame** | **7** | **33.0** | **0.3643** — **3.03×** |

**≈3.0× the sustainable telemetry rate for the same regulatory budget**, versus a 26 % airtime
saving and *no* extra records on 802.11 (where freshness, not size, is the wall).

*Two corrections landed here on 2026-07-29, both raising the benefit.* The measured H_f = 44 B
(docs/01 §2a) tightened every batch, and the batch grid was **sparse** — it listed
`[…5, 6, 8, 10…]`, omitting 7, so the DR5 per-frame optimum was reported as b=6 when the payload
limit allows b=7. That is the **same grid-quantization defect as audit F3**, and it *understated*
F5's benefit as 2.75×. The grid is now contiguous 1..20 and the true figure is **3.03×**.

**Decision (Mohamed, 2026-07-28): adopt per-frame chaining on the LoRa arm only.** The two arms now
carry the same ledger in two framings, and that asymmetry is the point rather than an inconsistency:

* **LoRa adopts it** because the regional payload limit binds (T2a), so the 32 B saved per record
  becomes *more records per frame*, which the duty cycle converts directly into sustainable rate.
* **802.11 keeps per-record chaining** because freshness binds there (T2a: dC/ds = 1 exactly), so
  the same change buys ~6 % total energy and **no extra records** — too little to pay for losing
  independently-transmitted per-record tamper-evidence.

**This is a wire-format decision, not a ledger change.** `prev_hash_{i+1} = H(record_i)`, so a
receiver holding the frame's first link and the ordered records derives every omitted hash; the
stored ledger is byte-identical either way and `Chain.verify()` is untouched. What changes on the
LoRa wire is that *within* a frame, tamper-evidence rests on the frame signature rather than on
independent hashes — equivalent in strength, since a frame is atomic and signed over its ordered
records, but no longer two independent mechanisms. The first link is **not** redundant and is always
sent: without it, frames could be reordered or dropped undetected.

*Since D6 froze the wire format, this is a recorded deviation, scoped to the LoRa arm. It does not
touch E1–E5 or the 75.00 % headline.* Config: `experiments/lora/config.yaml:adopted_chain_mode`.
Pinned by `tests/unit/models/test_lora_chain_adoption.py`, which also fails if the 802.11 configs
ever acquire a chain-mode key.

### 9a. The LoRa arm as a joint optimization (T5 on the LoRa side)
The LoRa arm is solved the same way as 802.11 — exhaustive enumeration, hard constraints, **full
Pareto set, no hand-picked configuration** (`models/lora_codesign.py`, `make exp-lora-codesign`).
Two structural differences, both forced by the medium:

**(i) The data rate is a fifth design variable.** Spreading factor trades airtime against link
budget, and airtime is exactly what the regulator rations, so DR cannot be fixed in advance without
begging the question. Range enters as a **ratio** between data rates derived from the SX1276
receiver-sensitivity table (Rev. 7, RFS_L125_HF/RFS_L250_HF, Band 1): TX power, antennas and fading
are identical across DRs and cancel, so no link budget is assumed.

    DR6 −120 dBm (1.00×) · DR5 −123 (1.41×) · DR4 −126 (2.00×) · DR3 −129 (2.82×)
    DR2 −132 (3.98×) · DR1 −133 (4.47×) · DR0 −136 dBm (6.31×)

*Without this objective the optimization degenerates:* DR6 has the shortest airtime, so it dominates
on both Λ and D and the entire DR axis collapses to a single point. A test pins that it does not.

**(ii) Λ and freshness are objectives, not inputs.** The duty cycle derives both — Λ = b·duty/T and
D = T/duty — so there is no D_max to respect and no Λ to be given. A larger batch raises Λ (the
preamble and signature amortise) but lengthens T and therefore *worsens* freshness. **That tension
is the LoRa co-design problem and has no 802.11 counterpart.**

Objectives: min bytes/record · **max Λ** · min freshness · max V · **max range**.
Constraints: frame ≤ N(DR) · V ≥ 1−ε · t_verify(b)·Λ ≤ 1.

**Result (`results/raw/lora_codesign.csv`): most design points do not physically exist** — they
exceed the regional payload limit — leaving **258 feasible and 108 on the Pareto front, spanning
DR4/DR5/DR6** (measured H_f = 44 B, contiguous batch grid 1..20). Representative front (delta, placement B, chain per-frame):

| DR | range | b | B/record | Λ (rec/s) | freshness |
|---|---|---|---|---|---|
| 4 | **2.00×** | 7 | 33.0 | 0.1035 | 67.6 s |
| 5 | 1.41× | 7 | 33.0 | 0.1822 | 38.4 s |
| 6 | 1.00× | 7 | 33.0 | **0.3643** | **19.2 s** |
| 6 | 1.00× | 1 | 153.0 | 0.0751 | 13.3 s |

Reading: **doubling range costs ~3.5× the record rate**; within a data rate, batching to b=8 buys
5× the record rate and 5× fewer bytes but 1.5× worse freshness. Every row is a defensible operating
point — the frontier *is* the result.

⚠️ **No energy column.** The only measured radio power in this project (`p_radio_w = 0.218 W`) is a
Wi-Fi figure from the RPi4 rig; reusing it for a LoRa transceiver would be fabrication. Airtime per
record is reported instead — it is what the regulator rations, and it is computed, not assumed.
A LoRa energy column needs a LoRa radio measurement.

## 7a. The operating point is an OPTIMIZATION RESULT, not a chosen constant (B3, 2026-07-29) ⚠️
*Artifact: `results/raw/operating_region.csv` (`make exp-operating-region`). 70 points.*

Λ and D_max are **decision variables of the same optimization the rest of this thesis solves**, not
settings to be picked and then defended. Treating them as constants was the actual defect in item
B3; the fix is to enumerate the region, state every trade-off, and then *declare* a reference point
with its costs attached.

**The governing relation** is b ≤ ⌊Λ·D_max⌋ (T2a), so **the byte results depend only on the
product**. Everything distinguishing equal-product points is channel load: a faster stream at a
tighter deadline buys *identical bytes* and *costs capacity*. That is the whole of B3.

**The constraint that makes it interesting.** 3GPP TS 22.125 V17.6.0 §5.2.2 specifies the direct
UAV-to-UAV local broadcast service — precisely this system: **R-5.2.2-010 ≥ 10 messages/s** and
**R-5.2.2-011 ≤ 100 ms end-to-end**. Applying both to the region:

| | points | best auth cut achievable | at |
|---|---|---|---|
| whole region | 70 | **98.0 %** | Λ=50, D=1000 ms, b=49 |
| TS 22.125 compliant | 18 | **75.0 %** | Λ=50, D=100 ms, b=4 |
| **compliant AND feasible at N=50** | **18** | **75.0 %** | same — **U = 1.39 is well inside the measured V≥0.95 boundary of U ≈ 2.80** |

⚠️ **Corrected 2026-07-29.** An earlier version of this table applied a **U < 1** feasibility test and
concluded that only 4 points were runnable and the compliant ceiling was 50 %. That test was wrong:
U is measured against *saturation* throughput, and NS-3 shows 98.8 % delivery still at U = 1.00,
with the V = 0.95 crossing at **U ≈ 2.80** (`results/raw/ns3_delay.csv`, and the withdrawal notice
above). **The 75 % cut is achievable at the 3GPP deadline.**

**So the honest result of B3 is that compliance costs swarm size, not bytes.** The
standards-compliant point (Λ = 50 Hz — PX4 `MAVLINK_MODE_ONBOARD` — at D = 100 ms) has Λ·D = 5,
therefore b = 4, therefore **exactly the same 75.0 % / 58.68 %** as the reference point. What
differs is channel load, and measured against the V ≥ 0.95 boundary:

| operating point | b | total cut | U at N=50 | largest neighbourhood |
|---|---|---|---|---|
| Λ=20, D=250 ms *(reference)* | 4 | 58.68 % | 0.557 | **N ≤ 233** |
| Λ=50, D=100 ms *(3GPP-compliant)* | 4 | **58.68 %** | 1.394 | **N ≤ 116** |

**Meeting the standard's deadline halves the supportable swarm and changes nothing else.**

### Declared reference operating point: Λ = 20 rec/s, D_max = 250 ms

**Declared, with its costs stated in full — not defended as optimal:**

| what it buys | what it costs |
|---|---|
| b = 4 → **75.0 %** auth-byte cut, **58.68 %** total-byte cut | **Violates TS 22.125 R-5.2.2-011** (250 ms vs ≤100 ms). This is a **declared deviation.** |
| U = 0.557 at N=50 — comfortable headroom | The 100 ms-compliant point with the *same* bytes (Λ=50) is **unrunnable at N=50** (U=1.39, N_max=35) |
| N_max = **103**, vs 32 for the Pillar-1 baseline (3.2×) | Under full compliance the best available cut is **50 %**, not 75 % — a third of the headline is bought by the deviation |
| Λ=20 sits between the standard's 10 msg/s floor and PX4 `ONBOARD`'s 50 Hz | A **ledger** freshness argument, not a control-loop one: TS 22.125 §5.2.2 is *collision avoidance*; a tamper-evident provenance log has a genuinely different deadline. This is a **scope argument and must be presented as one.** |

**Why not the compliant corner (Λ=21, D=100 ms)?** It is reported, and it is *not* dismissed — but
it is a **knife-edge**: at Λ = 20.0 the b=2 frame takes **100.37 ms**, 0.37 ms over, so b collapses
to 1 and the cut goes to **zero**; at Λ = 20.2 it is 99.38 ms and b=2 holds. A 1 % change in
telemetry rate flips the result between 50 % and nothing. That fragility is itself a finding about
how tightly this regime is squeezed, and it is why the corner is reported rather than adopted.

**Both are in the paper.** Reporting the compliant point costs nothing and forecloses the obvious
objection: the mechanism does not depend on the relaxed deadline — only b does, and b depends only
on Λ·D_max.

*(The impossibility this exposes is stated as **T7** below, beside T6.)*

### Loss probability p — mechanism, not a borrowed number (item B4)
p ∈ {0.02, 0.05, 0.10} is a **declared sensitivity range**, and the reason it is not tied to a
single measured PER is structural: **802.11 broadcast frames carry no ACK and are never
retransmitted** (docs/02 §6a — the same fact that makes T_air = PPDU + DIFS with no SIFS/ACK). A
broadcast receiver therefore sees the *raw* channel error rate, with none of the ARQ that hides loss
on a unicast link. For contrast, TS 22.125 Table 7.2-1 sets 99.9 % reliability (p = 10⁻³) for
managed C2 links *with* retransmission — so our grid is deliberately one to two orders of magnitude
more pessimistic, which is conservative for every claim that depends on it.

**T6 does not depend on the particular value.** Its no-fragmentation step needs only **ε ≤ p**, not
p = 0.05: whenever the verifiability target is no looser than the loss rate, n_max = 1. Every
exclusion in T6 therefore holds across the whole grid.

## 7. Energy and latency models
Energy/record: **E = P_c·(t_enc + t_sg/b + t_ver_amort(b)) + P_r·T_air(frame)/b**, where
t_ver_amort = t_vf (A/B receiver-side per record… receiver verifies once per frame in B:
t_vf/b) — implement exactly per placement; document each term. Latency/freshness of the
oldest record in a batch: D(b) = b/Λ_i + T_air + queueing (M/M/1 approx at load ρ =
Λ·T_air(b)/b) — report, and **enforce D ≤ D_max=250 ms in the optimizer**.

**Enforcement is real (audit F10, 2026-07-28).** "Soft constraint" had been read as
"annotated, not filtered", and was then not annotated either: the optimizer computed
`meets_latency` and discarded it, so the byte-optimal b=31 was reported as the optimum while
sitting at **1552 ms — 6.2× over the bound**. Freshness is now BOTH a hard constraint (a stale
configuration is inadmissible, exactly like one that misses V) and a **fourth Pareto objective**
alongside bytes, energy and verifiability — batching buys bytes with staleness, so an optimizer
blind to freshness is not solving the co-design problem.

Since fill time dominates D(b), the freshness-feasible batch obeys **b ≲ Λ·D_max**, independent of
encoding and scheme (Λ=20, D_max=250 ms ⇒ b ≤ 5; airtime makes b=4 bind).

*Caveat:* the M/M/1 queueing term above is **not implemented** (docs/audits/model_provenance.md P3).
It is omitted rather than approximated, which makes D(b) a **lower bound** on the true delay — the
conservative direction for a constraint.

## 8. Statistical methodology (binding for ALL experiments)
≥30 seeded repetitions per config (seeds 1..30 logged in CSV); report **median and
bootstrap 95% CI** (10k resamples); microbenchmarks: ≥10k iterations after 1k warmup,
GC disabled, single pinned core if possible, discard runs after suspend (clock skew);
comparisons state effect size, never bare means; raw CSVs are immutable once frozen (⚠️ D6).
Any model-vs-measurement deviation >10% must be investigated and either explained in
writing or the model corrected — silent tolerance widening is forbidden.
