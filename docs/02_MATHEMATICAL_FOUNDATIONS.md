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
**Claim (ii) (amplification law).** Relaxing the floor, per-record on-air bytes are
C(s) = s + (g_a+H_f)·s/(M−H_f−g_a) = **s · A**, with **A = M/(M − H_f − g_a) ≥ 1**.
Hence every payload byte saved by compression saves A on-air bytes, and A grows as M
shrinks (802.11: A≈1.06; LoRa M=222: A≈1.35 — the low-rate leverage, doc 30).
**Proof.** (i) ω′(b)<0. (ii) substitute b=(M−H_f−g_a)/s into s+ω(b) and factor. ∎
**Numbers (M=1500, H_f=40, g_a=48):** CBOR b_max=10 → 138.8 B/rec, φ=6.3%; JSON b_max=3 →
387.3 B/rec, φ=7.6%; delta b_max=35 → 42.5 B/rec, φ=5.9%. Batching restores auth overhead
to O((g_a+H_f)/M) regardless of encoding. **Validate:** E2.

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
Combining T1–T4: the joint optimum is separable — pick the smallest deterministic
encoding e* (min s), placement B (self) / C (relay) at b_max(s), scheme per T4; total
on-air bytes per record = s·A (T2), so compression's benefit is amplified by A and grows
as b_max(s) rises, until either the verify-throughput constraint t_verify(b)·Λ ≤ 1 or the
MTU binds. **Validate:** E5 end-to-end vs baselines {A+JSON, A+CBOR, D-overagg}.

## 6. Channel model — Bianchi DCF (802.11, saturation)
Fixed point over (τ, p_c): τ = 2(1−2p_c) / [(1−2p_c)(W+1) + p_c·W(1−(2p_c)^m)],
p_c = 1−(1−τ)^{N−1}; W=16, m=6. **Solve with damped iteration** p←0.7p+0.3p_new,
tol 1e−12 (undamped oscillates at high N — verified). Slot durations (OFDM, 6 Mb/s):
T_s(L) = T_phy + 8(L+34)/R + SIFS + δ + T_ack + DIFS + δ; T_c(L) = T_phy + 8(L+34)/R +
DIFS + δ, with T_phy=20 µs, SIFS=16 µs, slot=9 µs, DIFS=34 µs, ACK 14 B, δ=1 µs.
Fixed overhead **T_fx ≈ 123 µs**. Throughput S = P_tr·P_s·E[payload]/E[slot] as standard.
Airtime per frame: T_air(L) = T_fx + 8L/R. **Validate:** E5 vs NS-3; expect and *report*
known gaps (EIFS handling, capture, retry limit) rather than force-fitting.

## 7. Energy and latency models
Energy/record: **E = P_c·(t_enc + t_sg/b + t_ver_amort(b)) + P_r·T_air(frame)/b**, where
t_ver_amort = t_vf (A/B receiver-side per record… receiver verifies once per frame in B:
t_vf/b) — implement exactly per placement; document each term. Latency/freshness of the
oldest record in a batch: D(b) = b/Λ_i + T_air + queueing (M/M/1 approx at load ρ =
Λ·T_air(b)/b) — report, and enforce D ≤ D_max=250 ms as a soft constraint in the optimizer.

## 8. Statistical methodology (binding for ALL experiments)
≥30 seeded repetitions per config (seeds 1..30 logged in CSV); report **median and
bootstrap 95% CI** (10k resamples); microbenchmarks: ≥10k iterations after 1k warmup,
GC disabled, single pinned core if possible, discard runs after suspend (clock skew);
comparisons state effect size, never bare means; raw CSVs are immutable once frozen (⚠️ D6).
Any model-vs-measurement deviation >10% must be investigated and either explained in
writing or the model corrected — silent tolerance widening is forbidden.
