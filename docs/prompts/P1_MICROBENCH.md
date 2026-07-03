# P1 — CRYPTO & ENCODING: CODE + MICROBENCHMARKS  (COPY-PASTE WHOLE FILE)
Lane 1 · days 2–5 · split: P1a code (tag p1a-code-done → unblocks P2, P7b) → P1b measurements
(tag p1-done → unblocks E4). Under the Eight Laws; start in PLAN MODE.

CONTEXT BUDGET — read exactly: docs/01 §1–2 · docs/02 T1 and §8 · docs/03 §3 (encodings/,
crypto/, bench/) · docs/04 §1 · docs/06 §3,§4,§5. Not T2–T5, not NS-3.

OBJECTIVE: correct KAT-verified crypto + deterministic encodings (P1a); then the measured
parameter tables and the T1 overhead-dominance table — the thesis's FIRST numbers (P1b).

KEY FACTS INLINED (so you can self-check without hunting):
- Telemetry record fields, INTEGERS ONLY (floats break canonical CBOR cross-platform): lat/
  lon as int32 at 1e-7° fixed-point, alt int32 (cm), vel_{x,y,z} int16 (cm/s), battery uint8
  (%), mode uint8 (enum), plus src uint16, seq uint32, ts uint32 (ms), prev_hash 32 B.
- Encodings to implement: json (stdlib), cbor (cbor2, canonical=True, RFC 8949 §4.2),
  msgpack, delta (canonical integer field order, zigzag-varint deltas vs previous record,
  keyframe every K=16; decoder keeps per-src state; a lost frame desyncs until next keyframe
  → emit desync_count).
- Schemes + APIs: ECDSA-P256 via cryptography `ec.ECDSA(hashes.SHA256())` — for byte
  accounting use fixed-width 64 B r||s (decode_dss_signature then pad), NOT the 70–72 B DER;
  Ed25519 via cryptography `Ed25519PrivateKey`; BLS12-381 via blspy `AugSchemeMPL`
  (sign/aggregate/aggregate_verify). Ed25519 batch-verify is NOT exposed → default scope is
  SEQUENTIAL verify (scope claims accordingly; true batch = ⚠️ D3, stretch only).
- KAT sources to vendor into tests/vectors/ WITH their URLs: RFC 8032 §7.1 (Ed25519); NIST
  CAVP ECDSA P-256/SHA-256; draft-irtf-cfrg-bls-signature test vectors.
- T1 EXPECTED NUMBERS (φ = g/(s+g), g=64): JSON s≈358→15.2% ; CBOR s≈130→33.0% ; delta
  s≈40→61.5%. Your measured φ MUST reproduce these within rounding — a mismatch is a STOP.
- Timing sanity anchors on x86 (order of magnitude; far outside ⇒ STOP, audit harness, do
  NOT record): Ed25519 sign ~15–60 µs, verify ~40–120 µs; ECDSA-P256 verify ~80–300 µs;
  BLS pairing verify ~1–3 ms. Verify-time must NOT be < sign-time for the same scheme.
- Bench harness rules: `time.perf_counter_ns`; `gc.disable()` around loops (re-enable after);
  ≥1000 warmup iters; ≥10 000 timed iters OR ≥200 ms total (whichever larger); accumulate a
  checksum of outputs and assert it (defeats dead-code elimination); report MEDIAN + bootstrap
  95% CI (10 000 resamples). Every CSV header carries seeds + env block (`lscpu` model; note
  "WSL, governor uncontrolled").

P1a STEPS (one module = one commit: code + its tests):
1. bench/telemgen.py: seeded generator of the record above; property test = schema
   conformance on 1000 samples.
2. encodings/: ABC {encode,decode,name,deterministic} + the four encoders. Tests: round-trip
   (hypothesis, 1000 random records each); DETERMINISM — encode identical 1000 records in TWO
   subprocesses, compare SHA-256 of the concatenation (mismatch = STOP, Law 3); delta: loss-
   then-keyframe recovery test asserting desync_count behaviour.
3. crypto/: uniform API per scheme; vendor the KATs (with URLs); ECDSA fixed-width-64 test;
   BLS aggregate/aggregate_verify test. **KATs green BEFORE any timing exists.** blspy build
   failure ⇒ STOP → Failure Report → recovery ladder (upgrade pip; apt install cmake build-
   essential; last-resort py_ecc fallback is ⚠️ and ALL its timings get labeled "py_ecc — not
   representative").
4. AUDIT P1a (§Audit): attacks — canonical-byte boundaries, ECDSA encoding ambiguity, delta
   reference rules, KAT provenance. Fix. Tag `p1a-code-done`; push. If 2-lane, this tag is
   SYNC-1 — announce in docs/status/lane1.md. Then either continue to P2 in this session or
   hand P1b to a sibling session (say which and why).

P1b STEPS:
5. bench/timers.py + stats.py per the harness rules; UNIT-TEST the harness on a known-cost
   function (e.g., a fixed sleep or a counted loop) so you trust it before measuring crypto.
6. RUNS (seeds + env header in every CSV): (a) sizes: 10 000 records/encoding → mean±CI, max;
   delta at K=16 with keyframe amortization stated. (b) crypto: t_sg,t_vf per scheme on 200 B
   msgs; BLS t_ag(b),t_av(b) for b∈{2,4,8,16,32}.
7. RESULTS VALIDATION — Law 6, run §Validate-Results and write it into docs/audits/p1.md:
   - Compare EVERY measured φ to the inlined T1 numbers (state expectation first); mismatch
     beyond rounding ⇒ STOP.
   - Compare every crypto timing to the inlined anchors; assert verify≥sign per scheme;
     assert BLS-verify ≫ Ed25519-verify (feeds T4) and REPORT the measured ratio.
   - Cross-check ONE size and ONE timing by an independent quick calc/second method.
   - Confirm determinism (identical seed ⇒ identical sizes) and full provenance headers.
   - If anything is surprising/borderline: reproduce, hypothesize, explain-or-debug; if still
     ambiguous, raise to Mohamed. Do NOT record until all gates pass.
8. Produce results/raw/p1_*.csv + two tables (T1 auth-fraction; scheme-timing with CIs +
   the BLS/Ed25519 verify ratio). AUDIT P1b (attacks: timer resolution vs op cost, outlier
   policy stated, CI-width sanity, provenance). Fix → `make all` → tag `p1-done` → push →
   write §Handoff.

ACCEPTANCE: KATs+determinism+round-trip green · both tags pushed · CSVs with env headers ·
T1 table matches the inlined numbers · timings within anchors or investigated · Results-
validation subsection written in audits/p1.md.
