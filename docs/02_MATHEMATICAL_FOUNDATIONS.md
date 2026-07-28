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
against NS-3 3.41: unicast agrees to **+0.6 … −2.9 %** across N=5–50 (audit F8/F9).

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

Verified against our own NS-3 3.41 runs (802.11a, 6 Mb/s, W₀=16, L=1400 B): throughput, p_s and
idle-slots-per-busy-period all within **≤0.36 %** at N = 5, 10, 20, 35, 50 — a regime the original
papers did not test (they used W₀ = 32 and 128 at 1 Mb/s).

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
