# Full project audit — scientific + engineering, pre-P7b (2026-07-05)

> # ⚠️ PARTIALLY SUPERSEDED — correction added 2026-07-28
> Finding **F7** ("broadcast gap → 1735 % at N=50 is the capture effect; unicast ±5 % is the
> quantitative validation") is **RETRACTED on both halves**:
> * capture was later measured at **0 %** — the cause is the backoff counter Consecutive Freeze
>   Process, and the corrected broadcast model is Ma & Chen's published one (2007/2008);
> * the unicast ±1.8–5.3 % was mostly measurement bug **F8** (sinks outliving sources) plus the
>   0.41 %/12.1 % airtime approximation fixed by decision **D9**. Unicast now agrees to
>   **+0.6 … −2.9 %**, and broadcast to **≤1.1 %** against the published model.
> Kept unedited below as the audit trail. **Current state: docs/audits/p7.md + docs/02 §6/§6a.**


Whole-repo Law-5 (audit–attack–fix) + Law-6 (results-check) pass across every layer built P0→E5+P7a,
requested before opening the hardware gate. Baseline: `p7a-done`, **849 tests / 90 % coverage green**.
Method: re-derive each formula from docs/01–02 and check against code; hand-cross-check one point per
experiment; state expected-before-measured for every headline number; attack determinism/seeds/edges.

## Verdict
The project is **scientifically sound and the headline (T5, 96.4 % auth-byte cut, PASS) is robust.**
One real inconsistency was found and **fixed** (E4/T4 modelled BLS at the stale 48 B instead of the
accepted 96 B); it did not change the T4 conclusion. Six further items are documented below — all are
low-severity, nominal-pending-P7, or methodological notes for P8, none invalidates a result.

## Findings

| # | Sev | Area | Status | One-line |
|---|-----|------|--------|----------|
| F1 | **MED** | E4/T4 crossover | **FIXED** | BLS modelled at 48 B (stale min-sig) vs accepted 96 B; corrected → re-ran E4. |
| F2 | LOW | energy radio term | documented (code note) | uses unicast T_FX 122 µs on a broadcast system (~1 % over-count); reconcile at P7. |
| F3 | LOW | optimizer batch grid | documented | E5 optimum b=28 is grid-quantized; true MTU b_max=31 (96.4 %→96.8 %, PASS either way). |
| F4 | MED | cross-experiment sizes | documented (P8) | record sizes differ (single-seed 68.9 vs 30-seed 66.25 cbor) — random-walk magnitude sampling. |
| F5 | INFO | record schema | documented | 32 B `prev_hash` carried per record (~half of delta's 45 B) — a stated modelling assumption. |
| F6 | INFO | crypto ordering | documented (P7 watch) | ECDSA beats Ed25519 on x86 (OpenSSL asm); likely flips on ARM → may change E5 scheme pick. |
| F7 | INFO | NS-3 broadcast | documented (already in p6) | broadcast gap →1735 % at N=50 is the capture effect; unicast (±5 %) is the quantitative validation. |

### F1 — E4/T4 used BLS = 48 B (FIXED)
`crossover.py:G_AGG_BYTES` was 48.0 (old min-sig assumption) and `run_e4.py:SCHEME_G` inherited it,
while (a) Mohamed **accepted BLS = 96 B** with an explicit "update T2/**T4**", and (b) the p1_crypto BLS
timings are for blspy's 96 B-mode operations — so a 48 B *size* with 96 B *timings* was physically
incoherent. E5/framesizes already used 96 B; only E4 lagged. **Fix:** `G_AGG_BYTES 48→96`, updated the
three hand-value tests, made the E4 figure tolerant of the resulting κ*=∞, re-ran `make exp-e4`,
re-froze `e4_crossover.csv`/`e4_bytes.csv`/figure. **Effect on the conclusion: none — strengthened.**
At 96 B, BLS carries *more* auth bytes than Ed25519's 64 B on own self-batch traffic (κ*=+∞, can never
win) and saves bytes only on relay traffic for b≥2; either way BLS's 10.7× verify cost keeps **Ed25519
the winner at every one of the 80 grid points** (min κ*=3.21 ≫ plausible 0.5). This actually aligns T4
with the D2 design intent (BLS reserved for cross-signer aggregation, not self-batch).

### F2 — energy radio term uses the unicast fixed airtime (documented, P7)
`energy.radio_airtime_s` bills `bianchi.T_FX≈122 µs` (unicast success minus DIFS, includes SIFS+ACK)
per frame, but the telemetry substrate is 802.11 **broadcast** (no ACK; fixed part ≈100 µs). This
over-counts the receiver radio term by ~22 µs/frame ≈ 1 % of E5 energy. Energy is nominal-power and is
re-derived at P7 with the measured meter powers; a code NOTE now flags the reconciliation. The auth-byte
headline is power-free and unaffected. (Left un-refrozen deliberately: changing it now would desync the
code from the tagged E5 CSV for a 1 % nominal-energy tweak.)

### F3 — E5 optimum batch is grid-quantized (documented)
The E5 batch grid is `[…24,28,32,36,40]`. With delta s=45.0 B, one frame fits `45·b+104 ≤ 1500 ⇒
b_max=31`; the grid jumps 28→32 (32 spans 2 frames ⇒ V<0.95, infeasible), so the reported optimum is
**b=28**, not the true b_max=31. Auth overhead 104/28=3.71 B (reported) vs 104/31=3.35 B (true) → cut
96.4 % vs 96.8 %. **PASS either way**; the headline conclusion is unaffected. For the paper, either
disclose the grid or densify it near the MTU knee.

### F4 — record sizes differ across experiments (documented, P8)
The absolute encoders (json/cbor/msgpack) encode field *magnitudes*, which drift with the seeded
random walk; delta encodes magnitude-invariant deltas. So the same encoder measures differently by
(seed, n): **verified** cbor = 68.94 B at seed 1/n 10 000 (P1, framesizes, E2, E3) vs 66.25 B at
seeds 1–30/n 1 000 (E1, E5); delta is invariant (45.00 vs 45.00, +0.02 %). Each experiment is
internally consistent, but the cross-experiment absolute sizes are not directly comparable. **P8
recommendation:** report the 30-seed E1 mean±CI as the single headline size table and note per-figure
sizes in captions. Not a bug.

### F5 — 32 B prev_hash per record (documented assumption)
Every telemetry record carries a raw 32 B `prev_hash` (SHA-256), ~half of delta's 45 B on the wire. It
is carried so each frame round-trips standalone (frame-level self-verifiability). All encoders/experiments
use the same schema, so every relative conclusion holds; the absolute on-air sizes include this 32 B.
State it as an explicit modelling assumption in the paper (records self-carry the chain hash).

### F6 — ECDSA beats Ed25519 on x86 (P7 watch)
Measured (i5-14400F): ECDSA sign 26.2 µs < Ed25519 29.1 µs; ECDSA verify 78.5 µs < Ed25519 95.0 µs —
the reverse of the usual ordering, from OpenSSL's hand-tuned nistp256 assembly in `cryptography`. This
is why E5's byte-tied optimum breaks toward ECDSA on the energy tiebreak. On RPi4 ARM (no such asm
edge) Ed25519 is likely to reclaim the lead → the E5 scheme pick may flip ECDSA→Ed25519 (both 64 B,
identical auth-byte cut). **Watch at P7b; the headline % cut is unchanged regardless.** Also: ECDSA
verify 78.5 µs is 1.9 % below the doc's 80 µs anchor floor — inside run-to-run noise, not a fault.

### F7 — NS-3 broadcast gap = capture effect (already in p6.md)
Unicast Bianchi validates to **±1.8–5.3 %** across N=5–50 (excellent). The no-ACK broadcast model is a
conservative lower bound; its gap to NS-3 grows 4.4 %→1735 % (N=5→50) because it assumes *all* colliding
frames are lost, while NS-3's capture effect recovers the stronger frame (confirmed at P6 via the
power-spread experiment; broadcast goodput correctly plateaus ~1.3 Mb/s). Hand-check: at N=50 the model
gives 0.073 Mb/s (τ=2/17, p_s=1.3 %) — internally correct. **Use unicast for the quantitative DCF
validation; present broadcast qualitatively as capture-dominated.**

## Formula conformance (re-derived vs code — all ✓)
- **T1 φ = g/(s+g):** matches [experiments.py:72]; measured φ rises json 25 %→delta 59 % as s shrinks. ✓
- **T2 A = M/(M−H_f−g_a):** matches; A_at_b(b_max)→A within 5 % at MTU 1500 (integer-b slack at small M). ✓
- **T3 V_B=1−p, V_D=(1−p)^n:** matches [optimizer.py:124]; E3 measured V tracks theory. ✓
- **T4 κ*=ΔCPU/ΔRADIO:** matches [crossover.py]; corrected to 96 B (F1). ✓
- **T5 bytes/rec = s+(g_a+H_f)/b (B):** matches [optimizer.py:141]; E5 optimized 45+104/28=48.71 hand-checked. ✓
- **Bianchi DCF:** τ/p_c fixed point + S = P_tr·P_s·8L/E[slot] textbook-correct; damped iteration; residual gate. ✓
- **802.11a airtime:** broadcast (100.33 µs) and unicast (156 µs) kept separate & labelled; no 123 µs mixing. ✓
- **Energy E = P_c·(t_enc+t_sg'+t_vf') + P_r·T_air/b:** hand-checked E5 optimized = 15.72+48.52 = **64.24 µJ** = frozen 64.2318. ✓

## Results — expected vs measured (Law 6)
| result | expected (stated first) | measured | verdict |
|---|---|---|---|
| E1 sizes | json ≫ cbor≈msgpack > delta; φ grows as s↓ | 191 / 66.3 / 65.2 / 45.0; φ 25→59 % | ✓ T1 |
| P1 crypto | Ed sign 15–60/vf 40–120 µs; BLS vf 1–3 ms | Ed 29/95; BLS vf 1.02 ms | ✓ (ECDSA<Ed anomaly → F6) |
| E2 batching | A→M/(M−H−g); φ_ov↓ with b; A never amortizes | gap <5 % at MTU 1500 | ✓ T2 |
| E3 loss | V_B flat ≈1−p; V_D=(1−p)^n | V_B 0.980; V_D drops when n>1 | ✓ T3 |
| E4 crossover | Ed25519 wins for plausible P_r/P_c | ed25519 in 80/80; κ* 3.21–∞ | ✓ T4 (post-F1) |
| E5 co-design | ≥40 % auth cut at V≥0.95 | 96.4 % cut, V=0.95, PASS | ✓ T5 |
| NS-3 unicast | Bianchi ±~5 % | gap 1.8–5.3 % | ✓ validation |
| NS-3 broadcast | lower bound < capture-limited NS-3 | gap up to 1735 % | ✓ expected (F7) |

## Engineering attack (✓)
Real KATs present and passing (RFC 8032 Ed25519, Wycheproof ECDSA, Chia BLS); cross-process/SHA
determinism gate; frozen wire vectors; damped-fixed-point convergence guard (never returns non-converged);
input validation on records/energy/crossover; delta encoder is one stateful instance everywhere (the
keyframe pitfall is guarded in micro/framesizes/E1). 90 % line coverage. No engineering defects found;
no mocked data, no skipped asserts, no widened tolerances.

## Open / unsolved (cannot close without hardware or a Mohamed decision)
1. **P7b hardware ground truth** — timings + energy need 4× RPi4 + ⚠️ D5 meter. All energy numbers are
   nominal until then (auth-byte headline is power-free and final).
2. **F6 scheme-pick flip** — only resolvable by measuring Ed25519/ECDSA on ARM at P7b.
3. **F2 broadcast T_FX** — fix during the P7 energy re-run (bundled with measured powers).
4. **F3/F4 precision/consistency** — optional P8 polish (densify batch grid; standardize the size table);
   neither changes a conclusion.

## Actions taken this pass
- **Fixed F1**: crossover.py 48→96 B, 3 tests updated to hand-checked 96 B values, E4 figure tolerant of
  κ*=∞, E4 re-run/re-frozen. 849 tests green.
- **Documented F2** in-code (energy NOTE) + F2–F7 here for the P8 limitations section.
