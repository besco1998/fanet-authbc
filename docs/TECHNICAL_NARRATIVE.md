# AUTHBC — Technical narrative: theory, math, implementation, and results

A single-document account of the whole project: the problem, the mathematics behind it, how we
built and reasoned through it phase by phase, and the detailed results. It is the internal reference
that the P8 IEEEtran paper will condense. Every number here is traced to a frozen CSV in
`results/raw/` (and guarded by `make verify-frozen`). Companion docs: docs/00 (charter),
docs/01–02 (specs/theorems), docs/DECISIONS.md, docs/audits/*.

---
## 1. The problem

**Setting.** A fleet of UAVs (a FANET) streams telemetry — position, velocity, altitude, battery,
mode — at Λ ≈ 20 records/s per node over 802.11, into a blockchain-grade, hash-chained, signed
ledger. Every record must be **authenticated** (a signature so a verifier trusts its origin) and
**chained** (a hash of the previous record, so the log is tamper-evident).

**The tension.** Telemetry records are *tiny* — tens of bytes. Cryptographic authentication objects
are *not*: an Ed25519/ECDSA signature is 64 B, a SHA-256 chain hash is 32 B, a BLS signature is 96 B.
Naively signing every record inline means the **authentication overhead rivals or exceeds the
payload itself**, and on a shared, lossy, contended 802.11 channel that wasted airtime directly costs
goodput, energy, and freshness.

**The four coupled knobs.** How much overhead you actually pay depends on four choices that interact:
1. **Encoding** `e` — how compactly a record is serialized (JSON / CBOR / MessagePack / a custom delta codec) → the record size `s`.
2. **Authentication placement** — *where* the signature sits:
   - **A (inline):** one signature per record (the naive Pillar-1 baseline).
   - **B (self-batch):** one signature covers `b` records packed in a frame.
   - **C (relay / cross-signer):** originators sign; a relay aggregates into one signature per frame.
   - **D (block-level):** one signature over a block that may span several frames.
3. **Signature scheme** `σ` — Ed25519, ECDSA-P256, or BLS (aggregatable but slow to verify).
4. **Batch size** `b` — how many records share one authentication object.

**The thesis.** These knobs are *not* separable — the best encoding depends on the placement, the
best scheme depends on the batch size and the platform's power ratio, and so on. **Co-optimizing
them jointly** beats tuning any one in isolation. We make this precise with five theorems (T1–T5),
implement measurable models for each, and test one falsifiable headline:

> **Success criterion (docs/04 §2):** the co-optimized configuration cuts on-air authentication
> bytes by **≥ 40 %** versus the Pillar-1 baseline (inline signatures over CBOR) while keeping
> verifiability **V ≥ 0.95** under per-frame loss **p = 0.05**.

---
## 1a. Prior work and positioning

> **Citation integrity note.** Foundational works below (Bianchi's DCF, ECDSA, Ed25519, BLS/aggregate
> signatures, CBOR, Nakamoto's ledger, NS-3) are cited with verified bibliographic detail. Entries
> for the *domain-specific* FANET-authentication / UAV-blockchain / VANET-batch-verification
> literature are marked **[VERIFY]** — the thematic positioning is correct, but the exact references
> and any figures from them must be confirmed against the primary sources before submission. No
> reported number is quoted from an unverified source.

**(a) Digital signatures for constrained authentication.** *Problem:* authenticate messages with
compact, fast-to-verify signatures. *Approaches & results:* **ECDSA** (NIST FIPS 186) gives 64 B
P-256 signatures at 128-bit security via the EC discrete-log problem, but is randomness-sensitive;
**Ed25519** (Bernstein et al., CHES 2011; RFC 8032) uses a twisted-Edwards curve with deterministic
nonces for fast, misuse-resistant, batchable verification and 64 B signatures; **BLS** (Boneh–Lynn–
Shacham, ASIACRYPT 2001) produces the shortest signatures via pairings, and (Boneh–Gentry–Lynn–
Shacham, EUROCRYPT 2003) shows *n* signatures **aggregate into one** — at the cost of expensive
pairing verification. *Positioning:* AUTHBC introduces **no new primitive**; it quantifies, on 802.11,
*where and when* each existing scheme wins once placement and batching are chosen (T4/E4), finding
Ed25519 dominant for self-batch and BLS's aggregation worthwhile only for cross-signer relay traffic.

**(b) Batch and aggregate verification in vehicular / IoT networks [VERIFY].** *Problem:* a receiver
must verify many signed messages cheaply. *Approaches:* batch signature verification and aggregate
MAC/signature schemes amortize verification across messages. *Positioning:* AUTHBC generalizes the
idea from receiver-side batching to **authentication placement** (A/B/C/D) and co-designs it with the
encoding and scheme (T2, T5), and adds the loss-robustness frontier (T3) that pure aggregation ignores.

**(c) Blockchain / hash-chained ledgers for UAV & IoT provenance [VERIFY except Nakamoto].**
*Problem:* trustworthy, tamper-evident provenance of drone/IoT data. *Approach & result:* Nakamoto's
hash-chained ledger (2008) makes a log tamper-evident; UAV-blockchain systems put telemetry or
attestations on such a chain, gaining integrity at a per-record overhead cost. *Positioning:* AUTHBC
targets exactly that **substrate byte/energy cost** — the per-record signature + chain-hash overhead
these systems inherit — and is agnostic to the consensus layer above it.

**(d) Compact serialization for telemetry.** *Problem:* minimize on-air bytes of structured records.
*Approaches & results:* **CBOR** (RFC 8949) and **MessagePack** give compact binary encodings;
**differential/delta** coding sends small deltas against periodic keyframes. *Positioning:* AUTHBC
measures these head-to-head (E1) and shows the encoding choice is **coupled** to authentication — a
smaller payload raises the auth fraction φ (T1), which *increases* the value of batching (T2/T5).

**(e) Analytical 802.11 modelling and validation.** *Problem:* predict CSMA/CA throughput under
contention. *Approach & result:* **Bianchi** (IEEE JSAC 2000) models the DCF as a per-station Markov
chain whose τ/p_c fixed point yields closed-form saturation throughput matching simulation.
*Positioning:* AUTHBC uses Bianchi as the **airtime cost model inside the optimizer** and validates it
against **NS-3** (unicast within +0.6…−2.9 %). Its no-ACK *broadcast* variant is shown to fail by
up to 16×, root-caused to the Consecutive Freeze Process, and replaced by Ma & Chen's published
broadcast model, which matches NS-3 to ≤0.75 % on ns-3.41 and ≤2.49 % on ns-3.48 across p_s,
idle-slots and throughput (docs/audits/p7.md F9).

**Overall positioning.** AUTHBC is a **rigorous, hardware-validated co-design + measurement study**,
not a new cryptographic construction. Its contribution is the joint optimization of *encoding ×
placement × scheme × batching* under a single falsifiable headline (≥40 % auth-byte cut at V≥0.95),
grounded in measured microbenchmarks, an analytical channel model validated against NS-3, and a
reproducibility gate — a combination the prior work, which typically fixes three of the four knobs,
does not provide.

---
## 2. System model and mathematics

### 2.1 The record and the on-air cost
A telemetry record is integer-only fixed-point (floats break canonical-CBOR determinism): `src, seq,
ts, lat, lon, alt, vel_{x,y,z}, battery, mode`, plus a 32 B `prev_hash` (the chain link). Encoded
size is `s` bytes (encoding-dependent). A frame carries `b` records + a frame header `H_f` (≈ 40 B) +
an authentication object of size `g_a` (64 B Ed25519/ECDSA, 96 B BLS), bounded by the link MTU `M`
(1500 B on 802.11).

**On-air bytes per record**, by placement:
```
A (inline)      : bytes/rec = s + g_a + H_f/b     (every record carries its own g_a — no amortization)
B (self-batch)  : bytes/rec = s + (g_a + H_f)/b    (one g_a + one H_f amortized over b records)
C (relay agg)   : bytes/rec = s + (g_agg + H_f)/b  (one aggregate over b originators)
D (block)       : bytes/rec = s + (g_a + n·H_f)/b  (one g_a for a block spanning n frames)
```

### 2.2 T1 — overhead dominance
For inline authentication the fraction of on-air bytes that is *pure authentication* is
```
        g
φ  =  ───────           (auth object g against a payload of size s)
      s + g
```
For small telemetry (`s` = 45–190 B) and `g` = 64 B, **φ = 25–59 %**. The smaller the payload, the
more the signature dominates. This is the disease; T2–T5 are the cure and its limits.

### 2.3 T2 — batching cure and amplification
Self-batch (B) folds `b` records under **one** signature, so the per-record auth cost is `(g_a+H_f)/b`
→ 0 as `b` grows. Packing to the MTU gives a **goodput amplification** over single-record framing:
```
             M
A  =  ─────────────────         (asymptotic, at the batch b_max that fills the MTU)
      M − H_f − g_a
```

**⚠️ T2a — when does A actually apply?** The derivation above assumes the batch is capped by the
**MTU**. Once freshness is enforced (docs/02 §7) the cap may instead be `b = ⌊Λ·D_max⌋`, which does
**not depend on `s`** — and then `C(s) = s + (g_a+H_f)/b`, so `dC/ds = 1` exactly: **compression
pays 1×, not A×**, and the residual auth cost is a floor compression cannot touch. The regime
boundary is `s < (M−H_f−g_a)/(⌊Λ·D_max⌋+1)`.

E2's own MTU sweep straddles it (Λ=20 rec/s, D_max=250 ms, delta s=45):

| MTU | b_max (MTU) | b ceiling | binds | A formula | **A effective** |
|---|---|---|---|---|---|
| 256 (LoRa-like) | 3 | 3 | **MTU** | 1.6842 | **1.6842** |
| 576 | 10 | 5 | freshness | 1.2203 | **1.0000** |
| 1500 (802.11) | 31 | 5 | freshness | 1.0745 | **1.0000** |

So on 802.11 **A is never operative**; on a low-rate link it is. The "compression pays ×A" leverage
is real and **exclusive to the low-rate arm** — which is the strongest form of the LoRa motivation.

*Derivation:* at `b_max` the frame ≈ `M`, so bytes/rec ≈ `M/b_max`, and the data filling it is
`b_max·s ≈ M − H_f − g_a`; hence `(bytes/rec)/s = M/(M−H_f−g_a) = A`. Inline (A) can **never**
amortize its per-record signature — only the header `H_f/b` shrinks — which is exactly why A is the
naive baseline.

### 2.4 T3 — loss-robustness frontier
Let `p` be the per-frame loss probability and `V` = P(a received record is independently verifiable).
- **Self-batch (B):** each frame self-verifies; a record is verifiable iff *its* frame arrived →
  `V_B = 1 − p`, **independent of b** (loss-local).
- **Block (D):** one signature spans `n(b) = ⌈(b·s + g_a + H_f)/M⌉` frames; **all** fragments are
  needed → `V_D = (1 − p)^n`. D saves ~one signature in bytes but its verifiability collapses
  geometrically once the block spans more than one frame.

**Frontier:** whenever a block spans `n > 1` frames, `V_B = 1−p > V_D = (1−p)^n` — B Pareto-dominates
D's marginal byte saving. Byte-optimal over-aggregation is verifiability-fragile.

### 2.5 T4 — scheme-selection crossover (power-independent)
Per-record energy is `E = P_c·(CPU time) + P_r·(radio time)` with CPU power `P_c` and radio power
`P_r`. Comparing Ed25519 vs BLS: BLS aggregates (fewer on-air auth bytes → less radio time) but its
pairing verify is ~10× slower (more CPU time). Which wins depends on the powers **only through their
ratio** `κ = P_r/P_c`:
```
BLS wins  ⇔  P_r·ΔRADIO > P_c·ΔCPU  ⇔  κ = P_r/P_c > κ* = ΔCPU / ΔRADIO
```
where `ΔCPU` = extra CPU BLS costs, `ΔRADIO` = radio time BLS saves. `κ*` is the **break-even power
ratio** — found without measuring a single watt. Physically, Wi-Fi receive power sits below CPU-active
power, so plausible platforms have `κ ≲ 0.5`; BLS only wins if `κ* < 0.5`.

### 2.6 T5 — co-design optimum
Enumerate the discrete space `(e, σ, placement, b)` and take the **Pareto front** over three
objectives — minimize bytes/record, minimize energy/record, maximize `V` — subject to hard
constraints: MTU fit, `V ≥ 1−ε`, and verify-throughput `t_verify(b)·Λ ≤ 1`. The co-design optimum is
the smallest deterministic encoding under self-batch at the largest MTU-feasible batch.

### 2.7 The channel: 802.11a airtime and the Bianchi DCF
On-air time of one frame carrying `L` payload bytes at the 6 Mb/s OFDM base rate:
```
broadcast (no ACK):  T_air(L) = T_phy + 8(L+MAC)/R + DIFS + δ           (fixed part ≈ 100 µs)
unicast (with ACK):  T_s(L)  = T_phy + 8(L+MAC)/R + SIFS + δ + T_ack + DIFS + δ   (fixed ≈ 156 µs)
```
with `T_phy=20 µs, SIFS=16 µs, DIFS=34 µs, slot σ=9 µs, δ=1 µs, MAC+FCS=34 B, ACK=14 B, R=6 Mb/s`.
Under contention among `N` saturated stations, the **Bianchi (2000) DCF** fixed point gives the
per-slot transmit probability and collision probability:
```
      2(1−2p_c)                                              m=6 backoff stages, W=CW_min=16
τ = ───────────────────────────────────── ,   p_c = 1 − (1−τ)^(N−1)
    (1−2p_c)(W+1) + p_c·W(1−(2p_c)^m)
```
solved by damped iteration `p_c ← 0.7 p_c + 0.3 p_c^new` (undamped oscillates at high N). Saturation
throughput `S = P_tr·P_s·8L / E[slot]`, with `P_tr = 1−(1−τ)^N`, `P_s = Nτ(1−τ)^(N−1)/P_tr`, and
`E[slot] = (1−P_tr)σ + P_tr P_s T_s + P_tr(1−P_s)T_c`. Broadcast has no ACK/retry, so `τ = 2/(W+1)`.

### 2.8 The energy model
Self-batch per-record energy (docs/02 §7):
```
E = P_c·(t_enc + t_sign/b + t_verify/b)  +  P_r·T_air(frame)/b        [Joules/record]
```
Placements differ only in how the sign/verify CPU terms amortize (A: no /b; C: relay builds one
aggregate; D: one block signature). The radio term is the receiver's on-air time per record.

---
## 3. Implementation and reasoning, phase by phase

Governed by the **Eight Laws** (docs/00): plan-first, verify-before-assume, never-bypass-a-failure,
TDD, audit-attack-fix, check-your-results, scientific-integrity, escalate-decisions. `main` is always
green; every result carries an env + config-hash header; anomalies are investigated in writing, never
averaged away.

### P0 — bootstrap
Repo skeleton, pinned toolchain (Python 3.12, `cbor2==5.8.0` deliberately, `blspy`, `cryptography`),
CI, Makefile as the only entry points, clean-clone reproducibility proof. Decided **D7 = 2-lane**
execution. *Thinking:* lock the environment and the green-trunk discipline before any science.

### P1 — microbenchmarks (encoders + crypto)
Built four encoders and three signature schemes and measured them under a strict harness
(`perf_counter_ns`, GC disabled, ≥1 k warmup, ≥10 k iterations, output checksum to defeat dead-code
elimination, bootstrap CIs). Crypto is validated against **real Known-Answer-Tests** — RFC 8032
(Ed25519), Wycheproof (ECDSA-P256), Chia vectors (BLS) — not mocks.
- *Gotcha caught (delta codec):* our first delta measurement read 60 B instead of 45 B because a
  fresh encoder was created per record inside a generator → every record became a keyframe. Root
  cause: the delta codec is **stateful**; it must be *one* instance reused across the stream. Fixed,
  and turned into a standing harness rule (guarded everywhere it recurs).
- *Decision (BLS size):* `blspy`'s AugSchemeMPL produces **96 B** G2 signatures, not the 48 B the docs
  assumed. **Accepted 96 B** and propagated it (later audit found T4 had been missed — see §5).

### P1b — CBOR recheck
On review, CBOR was larger than expected (110 B with string-keyed maps). Re-examined the encoding and
switched the binary codecs to **canonical schema arrays** (positional, no field-name strings) → CBOR
66 B, MessagePack 65 B. *Thinking:* the payload is a fixed schema, so self-describing keys are pure
waste; arrays are the honest minimum for a versioned schema.

### P2 — ledger and wire format
Hash-chained record store, canonical CBOR wire format, and **frozen wire vectors** (⚠️ D6): the
on-air bytes are a contract, so they are pinned and any change requires approval. Fuzz + property
tests for round-trip and chain integrity.

### P3 — placements and channel
Implemented the four placements (inline / self-batch / relay-agg / block-agg) and the 802.11a airtime
model. *Integrity trap avoided:* the docs' "T_fx ≈ 123 µs" fits neither the broadcast fixed part
(100 µs) nor the unicast one (156 µs); we kept the two airtime models **separate and labelled** rather
than splitting the difference.

### P4 — experiments E1–E3
Turned T1–T3 into seeded, config-hashed experiments over 30 seeds, comparing measured behavior to the
formulas (not just re-plotting them). E1 = overhead dominance, E2 = batching amplification, E3 = loss
frontier. Baselines everywhere: A+JSON (naive), A+CBOR (Pillar-1), D-over-aggregated.

### P5 — models and the optimizer (+ E4)
Built the energy model, the exhaustive Pareto optimizer, and the **power-independent** Ed25519↔BLS
crossover (T4, E4) — locating `κ*` from measured timings + byte accounting with **no assumed watts**.
*Thinking:* absolute energy needs hardware power (deferred to P7), but the *crossover* is power-free,
so T4 is fully grounded now.

### P6 — NS-3 validation
Validated the Bianchi model against NS-3 3.41 (built from source). Used a **PacketSocket** scenario to
avoid ARP/IP artifacts, co-located nodes to avoid spatial-reuse inflation, and matched each NS-3 mode
to its own analytic variant (never crossed unicast↔broadcast).
- *The hardest anomaly, handled honestly:* broadcast goodput did **not** collapse at high N the way
  the no-ACK model predicts. This took **three** explanations to get right, and the first two were
  wrong. (1) "18× capture" — wrong, it compared a per-transmission success against a per-busy-slot
  probability; retracted in writing (docs/audits/p6.md). (2) "the capture effect" — also **wrong**,
  and retracted at P7: instrumenting NS-3's PHY showed **0 %** of successful decodes came from a
  collided busy period, and forcing equal power changes nothing byte-for-byte. (3) The measured
  cause is the **backoff counter Consecutive Freeze Process**: with no ACK the contention window
  never doubles, so a station that just transmitted may redraw backoff 0 and take the medium a slot
  before any deferring station (whose counter is necessarily ≥ 1). (4) A literature check then showed
  this is **published** — Ma & Chen, IEEE Comm. Lett. 11(8):686–688, 2007 — so the novelty claim was
  retracted as well; their closed form reproduces our measurement to **≤0.75 %** (ns-3.41)
  (docs/audits/p7.md F9).
  Verdict: **both** arms are now quantitatively validated — unicast against ACK-Bianchi, broadcast
  against the slot-exact model; the textbook no-ACK Bianchi variant is the thing that fails.

### E5 — the co-design headline (T5)
Fed the optimizer the **measured** E1 sizes and P1 crypto timings, extracted the byte-optimal feasible
configuration, and tested the success criterion against the baselines. This is the thesis headline (§4).

### P7a — hardware-prep + the audit + the reproduction gate
Wrote the RPi4 provisioning / micro-rerun / energy-protocol scripts (no hardware needed yet). Then ran
a **whole-repo audit** (§5) that found and fixed the T4/BLS inconsistency, and built an automated
**frozen-data reproduction gate** so stale results can never be committed silently again.

---
## 4. Results in detail

All values from frozen `results/raw/*.csv`. Model/byte results derived on x86 (Intel i5-14400F);
the energy column's crypto timings, encode timings **and both powers are MEASURED on the RPi4**
(D8) — `p_cpu_w`=0.749 W (composed-pipeline median, D6 — supersedes the 0.634 W isolated-primitive figure),
`p_radio_w`=0.218 W. Energy is no longer nominal.

### E1 — overhead dominance (T1), 30 seeds
| encoding | mean bytes s | φ = 64/(s+64) | notes |
|---|---|---|---|
| JSON | **191.1** | 25.1 % | verbose text |
| CBOR | **66.25** | 49.1 % | canonical arrays |
| MessagePack | **65.16** | 49.6 % | ~CBOR |
| **delta** | **45.00** | **58.7 %** | K=16 keyframes, zigzag-varint deltas |

The auth fraction climbs from 25 % (JSON) to **59 %** (delta): the more you compress the payload, the
more a fixed 64 B signature dominates — T1 confirmed, and the motivation for T2.

### P1 — crypto timings (x86, median)
| scheme | sign | verify | note |
|---|---|---|---|
| ECDSA-P256 | 26.2 µs | **78.5 µs** | OpenSSL nistp256 asm |
| Ed25519 | 29.1 µs | 95.0 µs | |
| BLS (96 B) | 324.6 µs | **1016.5 µs** | pairing verify |
| BLS agg-verify(b=8) | — | 3445 µs | one aggregate over 8 |

*Anomaly (F6):* on x86, ECDSA **beats** Ed25519 on both sign and verify (OpenSSL's hand-tuned P-256
assembly) — the reverse of the usual ordering, and the reason E5 picks ECDSA on the energy tiebreak.
This edge is expected to **disappear on ARM (RPi4)**, possibly flipping the pick back to Ed25519 — a
finding to confirm at P7b (both are 64 B, so the byte headline is unchanged either way).

### E2 — batching amplification (T2)
At MTU 1500, self-batch, at the MTU-filling `b_max`, the measured amplification `A_at_b = (bytes/rec)/s`
matches the formula `A = M/(M−H_f−g_a)` to **< 5 %** (the small gap is integer-`b` slack, which shrinks
as `s` shrinks): delta reaches `b_max = 31` with `A_at_b = A = 1.0745` exactly. Inline (A) never
amortizes its signature (`bytes/rec` barely moves with `b`), confirming the placement distinction.

**But T2a: that `b_max = 31` is unreachable.** Freshness caps the batch at `⌊Λ·D_max⌋ = 5` long
before the MTU does, so the realised amplification at M=1500 is **1.0000, not 1.0745**. E2 now
records `binds` and `A_effective` per row: **MTU-limited at M=256 (A=1.68 operative), freshness-
limited at M=576 and M=1500 (A=1)**. The formula is verified — and shown to apply only on low-rate
links.

### E3 — loss frontier (T3), p=0.05 & 0.10
`V_B ≈ 1−p` flat in `b` (e.g. 0.90 at p=0.10, any b); `V_D = (1−p)^n` drops the moment a block spans
`n>1` frames (0.81 = 0.9² at p=0.10, b=40). B strictly dominates D's marginal byte saving above the
single-frame threshold — the frontier is exactly T3.

### E4 — scheme crossover (T4), corrected to BLS=96 B
Ed25519 verify is **33.2×** cheaper than BLS verify on ARM (10.7× on x86 — the thesis platform is the Pi, D8). Across the full ρ (relay fraction) × b × Λ grid
(**80 points**), **Ed25519 wins every one** — minimum `κ* = 31.6 ≫ 0.5`. At 96 B, BLS carries *more*
auth bytes than Ed25519's 64 B on own self-batch traffic (`κ*=∞`, it can never win there) and saves
bytes only on relay traffic for `b≥2` — but its 33.2× verify cost keeps Ed25519 optimal for any
plausible power ratio. This aligns T4 with the D2 architecture: **BLS is for cross-signer aggregation,
not self-batch.**

### E5 — the co-design headline (T5) — **PASS**
| configuration | encoding | scheme | placement | on-air auth B/rec | V |
|---|---|---|---|---|---|
| **optimized** | delta | Ed25519 | **B, b=4** | **27.00** | 0.95 |
| A+CBOR (Pillar-1) | cbor | Ed25519 | A (inline) | 108.0 | 0.95 |
| A+JSON (naive) | json | Ed25519 | A | 108.0 | 0.95 |
| D-over-agg | cbor | Ed25519 | D, b=40 | 3.80 | **0.9025** ✗ |

**Headline (reframed 2026-07-29, audit F13 + item A1): total on-air bytes 174.25 → 72.00 B/record
= 58.68 %**, of which placement×batching contributes 79.2 % (auth 108 → 27.0, a 75.00 % cut) and the
encoding 20.8 % (payload 66.25 → 45.0, a 32.1 % cut). **PASS** against the ≥40 % criterion at
V = 0.95, p = 0.05, D ≤ 250 ms. Hand-checked: `45.0 + 108/4 = 72.0 B/rec` at b=4, whose freshness is
`4/20 + 0.49 ms = 200.5 ms`. D-over-aggregation is byte-competitive (3.60 B) but **fails** the
V≥0.95 constraint (0.9025 = (1−p)²) — a live demonstration of the T3 frontier — *and* misses
freshness by 8×.

*(Earlier drafts reported 96.77 % at b=31, under the then-assumed H_f = 40 B; at the measured 44 B
the MTU knee is b=30 and 96.67 %. Either way that configuration is byte-optimal but sits at
**~1.5 s** of staleness, 6× over the D_max = 250 ms bound docs/02 §7 requires the optimizer to enforce; the
optimizer computed the violation and discarded it — audit **F10**. Freshness is now a hard constraint
AND a fourth Pareto objective, so the reported optimum is the byte-best configuration that a UAV
telemetry system could actually deploy.)*

**The freshness-constrained co-design frontier** (delta + Ed25519, placement B, Λ=20 rec/s,
D_max=250 ms) — this, not a single number, is the co-design result:

| b | auth B/record | auth cut | freshness | energy/record |
|---|---|---|---|---|
| 1 | 108.000 | 0.00 % | 50.3 ms | 367.83 µJ |
| 2 | 54.000 | 50.00 % | 100.4 ms | 210.40 µJ |
| 3 | 36.000 | 66.67 % | 150.4 ms | 157.92 µJ |
| **4** | **27.000** | **75.00 %** | **200.5 ms** | **131.68 µJ** |

*(At the measured H_f = 44 B, with the chain-hash term and the composed-pipeline power. Bytes read
104/52/34.7/26.0 and energy 317/180/135/112 µJ before B1, D6 and D7 — the **auth-cut column is
unchanged**, which is F13's point: it is 1 − 1/b and nothing else.)*

Every 50 ms of freshness spent buys auth-byte reduction, with sharply diminishing returns. The
freshness-feasible batch is bounded by **b ≲ Λ·D_max** (=5 here; airtime pushes b=5 just over, so
b=4 binds) — a bound that is independent of encoding and scheme.

**And that changes what compression is worth (T2a).** T2's amplification A = M/(M−H_f−g_a) is
derived *at the MTU limit*. When freshness caps the batch first, b no longer depends on s, so
C(s) = s + (g_a+H_f)/b and **dC/ds = 1 exactly** — compression pays 1×, not A×, and the residual
auth cost is a floor compression cannot touch. On 802.11 the regime boundary is s < 232.7 B, and
*every* encoding here (45–191 B) is below it, so **A = 1.0745 is never operative on this arm**
(measured marginal rate: 1.0000 to 12 dp). On LoRa (M=222) the boundary falls to 19.7 B, the MTU
binds again, and **A = 1.881 is** operative — the low-rate leverage is real and exclusive to it.


### NS-3 validation (Bianchi vs NS-3 3.41)
*(All NS-3 numbers below are the F8-corrected re-measurement: the sinks used to outlive the sources by
0.5 s on a 10 s window, inflating every goodput by ~4.8 %.)*

| N | unicast vs ACK-Bianchi | broadcast vs naive reduction | broadcast vs **Ma & Chen** |
|---|---|---|---|
| 5 | +0.61 % | −0.2 % | −0.33 % |
| 10 | +0.85 % | +3.1 % | −0.39 % |
| 20 | +0.64 % | +31.3 % | −0.71 % |
| 35 | −1.39 % | +273.1 % | +0.93 % |
| 50 | **−2.85 %** | **+1654.1 %** | **+1.06 %** |

**Unicast validates the DCF model to +0.6…−2.9 %** across N=5–50. The broadcast column explodes not
because of capture — measured at **0 %** — but because reducing the unicast model to broadcast
(τ = 2/(W+1)) omits the **backoff counter Consecutive Freeze Process**: with no ACK the contention
window never doubles, so a station that just transmitted may redraw backoff 0 and take the medium a
slot before any deferring station can. That is **Ma & Chen's published broadcast model** (IEEE Comm.
Lett. 11(8):686–688, 2007; IEEE TVT 57(6):3757–3768, 2008), whose abstract warns that unicast models
"cannot simply be reduced" to broadcast — exactly the error we made. Their closed form reproduces our
measurement to **≤0.75 %** (ns-3.41; ≤2.49 % re-measured on ns-3.48). We claim **no novelty** for the mechanism; what is ours
is validation at W₀=16 / 802.11a (they tested W₀=32, 128 at 1 Mb/s) and a direct PHY-trace measurement
of the mechanism rather than curve-fitting.

---
## 5. How we thought about correctness (scientific integrity)

The project's second product (after the results) is the *discipline*. The anomalies we caught and how:
- **delta 60→45 B** — stateful codec used statelessly; root-caused, fixed, made a standing rule.
- **CBOR 110→66 B** — string keys are waste for a fixed schema; switched to canonical arrays.
- **BLS 48→96 B** — accepted the real `blspy` size; a later audit found T4 still used 48 B (**F1**) and
  we corrected it (conclusion unchanged, strengthened).
- **"18× capture" over-claim** — a wrong metric comparison; **retracted in writing**. Its replacement
  ("the capture effect") was **also wrong and also retracted**, at P7, when PHY instrumentation
  measured capture at **0 %**. The third and measured explanation is the **backoff counter
  Consecutive Freeze Process** — and a literature check then showed it was **published in 2007**
  (Ma & Chen), so our "discovery" was a rediscovery and the novelty claim was retracted too.
  Three retractions on one question, all kept visible. The result is stronger for it: the broadcast
  arm now rests on a cited IEEE model that our measurement validates to ≤0.75 % (ns-3.41).
- **Pre-P7b whole-repo audit** (docs/audits/full_audit_pre_p7b.md) — re-derived every formula against
  the code, hand-checked one point per experiment (E5 energy = 64.24 µJ = frozen), and produced seven
  findings F1–F7 (one fixed, six documented as P7/P8 items).
- **The freezing shortage → the reproduction gate.** Freezing raw data buys reproducibility but risks
  *silent staleness* (exactly what produced F1). We built `make verify-frozen` — it re-derives every
  deterministic frozen artifact from current code and fails loudly on any drift, verified to catch the
  F1 regression. Staleness can no longer be committed.

Every energy number is now **measured and validated end-to-end** (`p_cpu_w`=**0.749 W** from four
composed pipelines, `p_radio_w`=0.218 W). E5's optimized configuration is **131.68 µJ/record**.
⚠️ Absolute energy is a **lower bound by ~10–14 %** — the residual is uncharged CPython frame
assembly (F14). The auth-byte headline is **power-free** either way. Nothing is fabricated, no test is skipped, no tolerance is widened, and negative/limiting
results (two retracted broadcast explanations, BLS losing on 802.11) are reported plainly.

---
## 6. Status and what remains
- **Complete and green:** P0–P6 + E5 headline + P7a prep + the audit + the reproduction gate, all on
  one trunk (tags through `p7-done`). Theorems T1–T5 all validated; NS-3 confirms the unicast DCF
  to **+1.28/−0.49 %** and the broadcast model (Ma & Chen) to **≤1.44 %** (ns-3.48; on ns-3.41
  these read +0.6/−2.9 % and ≤1.1 % — unicast improved, broadcast widened slightly).
- **Headline:** co-design cuts on-air auth bytes **75.00 %** vs the Pillar-1 baseline at V≥0.95,
  p=0.05 **and freshness ≤ 250 ms** — **PASS**. (Byte-optimal ignoring freshness is 96.67 % at
  b=30, but that costs 1.50 s of staleness — audit F10.)
- **P7b (hardware):** measure real timings + INA219 energy on RPi4, watch the F6 scheme flip, then
  re-run E4/E5 with measured power and re-freeze through the gate. Setup: hw/SETUP.md.
- **P8 (paper):** condense this narrative into the IEEEtran write-up with an honest limitations section
  (small-N hardware, emulated vs real loss, no mobility, H_f assumed — see the open-items list).
