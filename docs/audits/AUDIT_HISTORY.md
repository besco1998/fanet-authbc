# Audit history — every audit of the project, in date order

*Merged on 2026-11-01 from twelve files, each copied verbatim. The findings these audits produced
are kept, current, in [`model_provenance.md`](model_provenance.md) (F1–F113); this file is the
record of how each audit was done and what it found at the time. Numbers in the older sections are
those of their date; several were superseded later, and the sections say so where they were
corrected.*

## Contents

1. [Audit — P0 bootstrap](#s1) — formerly `docs/audits/p0.md`
2. [Audit — P1 (crypto & encodings + microbenchmarks)](#s2) — formerly `docs/audits/p1.md`
3. [Audit — P2 (ledger + canonical wire format)](#s3) — formerly `docs/audits/p2.md`
4. [Audit — P3 (placements + channel emulator)](#s4) — formerly `docs/audits/p3.md`
5. [Audit — P4 (experiments E1–E3)](#s5) — formerly `docs/audits/p4.md`
6. [Audit — P5a models (bianchi / energy / optimizer)](#s6) — formerly `docs/audits/p5.md`
7. [Audit — E5 (co-design end-to-end, T5)](#s7) — formerly `docs/audits/e5.md`
8. [Audit — P6 (Bianchi ↔ NS-3 validation)](#s8) — formerly `docs/audits/p6.md`
9. [Full project audit — scientific + engineering, pre-P7b (2026-07-05)](#s9) — formerly `docs/audits/full_audit_pre_p7b.md`
10. [Audit — P7b (RPi4 hardware campaign)](#s10) — formerly `docs/audits/p7.md`
11. [Scientific-implementation audit](#s11) — formerly `docs/audits/scientific_implementation_audit.md`
12. [Claim audit — every headline number, re-derived from first principles](#s12) — formerly `docs/CLAIM_AUDIT.md`

---

<a id="s1"></a>

## 1. Audit — P0 bootstrap

*Formerly `docs/audits/p0.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: the `fanet-authbc` skeleton, build/setup, CI, and `scripts/lane.sh` against
P0_BOOTSTRAP + docs/03, docs/06 §6, docs/07 §3–4. Method: adversarial attacks with
reproducible evidence (T_TEMPLATES §Audit). Date 2026-07-03. Baseline commit at audit start:
`3e226c8`.

### Findings table

| # | severity | attack / evidence | root cause | fix |
|---|---|---|---|---|
| 1 | **medium** | **Wrong-FS guard was not persistent.** Step-1 `df -T .` (ext4) was a one-time manual check; a later `git clone` onto `/mnt/c` (drvfs/9p) would `make setup` silently despite the 10–50× I/O penalty / NS-3 breakage (docs/06 §1). | The FS check lived only in the human gate, not in the tooling. | Added an FS guard as the first step of `make setup`: `df -T .` → `case` on fstype, **exit 1** on `drvfs\|9p\|cifs\|v9fs\|fuseblk`, else print `fs check: '<fs>' OK`. Verified: prints `fs check: 'ext4' OK` locally; passes on GitHub (`overlay`/`ext4`). |
| 2 | info (no defect) | **Is pin verification real or cosmetic?** | — | Real. (a) `cbor2==5.8.0` and `cryptography>=42,<46` are enforced by **pip at every `make setup`** (a bad resolution fails the install). (b) The P0 table is computed from `importlib.metadata` + `packaging.SpecifierSet`, not hand-typed. (c) Drift detection demonstrated to bite: `cbor2 5.8.0 in '==5.8.1' -> False (would STOP)`, `in '>=42,<46' -> False (would STOP)`. |
| 3 | info (no defect) | **Does CI actually run the tests (not a no-op)?** | — | Real. CI invokes the *same* `make setup/lint/test` targets; run `28633005732` step `test (pytest)` log shows `.venv/bin/pytest … 9 passed in 1.15s` on Python 3.12.13. `make test` is `pytest` (exit code propagates), so a failing test reddens CI. |
| 4 | info (no defect) | **Is `scripts/lane.sh` safe (no clobber, no footguns)?** | — | Real. `set -euo pipefail`; rejects missing/`1`/out-of-range args (exit 2); **refuses to clobber** an existing dir (exit 1) and an existing branch (exit 1) — both demonstrated live, then cleaned up (main left clean). Executable bit committed (100755). |
| 5 | info (no defect) | **Is every docs/07 §3 ownership-map directory present?** | — | Yes. Census of all 26 named dirs (`src/authbc/{7 subpkgs}`, `tests/{unit,property,integration,vectors}`, `experiments/e1–e5`, `results/{raw,figures,hw}`, `analysis`, `ns3`, `hw`, `paper`, `docs/{status,audits,failures}`) → all `ok`. Per-module test subdirs (e.g. `tests/unit/models`) are created by each lane as tests land — consistent with the `(matching)` annotation in docs/07 §3 and the P0 layout block (which lists only `tests/{unit,property,integration}/`). |

### Non-blocking notes
- CI emits a benign annotation: "Node.js 20 is deprecated … forced to run on Node.js 24"
  for `actions/checkout@v4` / `actions/setup-python@v5`. `v4`/`v5` are the current major
  tags; the warning is about the runner's Node runtime, not our config. No action.
- `docs/05` does not exist in the source package (present: 00,01,02,03,04,06,07). Copied
  what exists; nothing fabricated.

### Results validation (Law 6) — the P0 "result" is the clean-clone proof
- **EXPECTATION (stated in advance):** a fresh `git clone` on a machine-independent path
  (`/tmp`) should pass `make setup && make test && make lint` with **no manual step**,
  building a **Python 3.12** venv, installing **blspy** and **cbor2 5.8.0**, and reporting
  **9 passed** + **ruff clean**.
- **OBSERVED:** matches exactly (see docs/status/lane1.md clone-proof block): venv 3.12.3,
  blspy-2.0.3, cbor2-5.8.0, `9 passed`, `All checks passed!`.
- **SANITY GATES:** no pin drift; deterministic (identical resolved versions in-place, in
  CI, and in the `/tmp` clone); CI green.
- **CROSS-CHECK:** the same three targets pass in three independent environments (in-place,
  GitHub Actions, `/tmp` clone) — reproducibility confirmed.
- **PROVENANCE:** commit hash, env, and versions recorded in docs/status/lane1.md.

### Verdict
1 medium finding **fixed** (FS guard) and re-proven by a fresh `/tmp` clone after the fix;
4 attacks passed with no defect. P0 acceptance criteria met.


---

<a id="s2"></a>

## 2. Audit — P1 (crypto & encodings + microbenchmarks)

*Formerly `docs/audits/p1.md`, last changed 2026-07-04. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

### P1a — code audit (2026-07-03)

Scope: `bench/telemgen`, `encodings/*`, `crypto/*` + their tests, against docs/01 §1,
docs/03 §3, docs/06 §3–5. Method: adversarial attacks with reproducible evidence
(T_TEMPLATES §Audit). Baseline at audit start: `c23b283`.

#### Findings

| # | severity | attack / evidence | root cause | fix |
|---|---|---|---|---|
| 1 | **medium** | **Delta encoder tested only single-src.** Interleaved streams from different `src` could corrupt each other's delta state if per-src keying were wrong. | Coverage gap — no interleaving test. | Added `test_delta_multi_src_interleaved` (two srcs, frame-by-frame interleave, full round-trip + both srcs recovered). **Passes** — `src` is carried absolutely in every frame and enc/dec state is keyed by src; regression now guarded. |
| 2 | info (no defect) | **ECDSA DER-vs-raw ambiguity** (docs/06 §4): could sizes be inflated by 70–72 B DER, or could raw↔DER lose r/s with leading zeros? | — | `sign` emits fixed-width **64 B r‖s**; `der_to_raw64`/`raw64_to_der` round-trip losslessly (32-B big-endian pads leading zeros); verified by `test_signature_is_fixed_width_64_not_der` + **484** Wycheproof SigVer cases through `verify_der`. Wrong-length sig → `False` (no raise). |
| 3 | info (no defect) | **Canonical-byte / determinism**: hash-seed-dependent dict order or float creep would break cross-platform reproducibility (docs/06 §5). | — | All four encoders pass a **two-subprocess SHA-256** determinism gate (PYTHONHASHSEED randomized per process); telemetry is integer-only and `validate()` rejects float/bool/out-of-range. |
| 4 | info (no defect) | **KAT provenance & non-triviality**: are vectors authoritative, exercised, and not passable by a trivial always-true verify? | — | Vectors vendored with source URLs (tests/vectors/README): RFC 8032 §7.1 (5 deterministic sign KATs reproduced exactly), Wycheproof ECDSA (484) + Ed25519 (150) incl. negatives, Chia AugScheme aggregate + BasicScheme sign. Negative cases (tamper→False, invalid→False) defeat a trivial verify. 652 crypto tests run in CI. |

#### Byte-accounting decisions — RESOLVED by Mohamed (2026-07-03/04)
- **BLS: accept 96 B** (min-pubkey blspy) for all byte accounting; **T2's `g_a` and the T4
  crossover anchors are updated to 96 B** at P5/P2 (was the docs' 48 B min-sig assumption).
  Recorded in `crypto/base.py`.
- **CBOR compaction (Mohamed: "recheck CBOR, it can reduce more").** Root cause found: the
  string-keyed CBOR map spent **~42 B/record on field-name keys** (of 108). For a fixed
  telemetry schema those names are pure overhead, so the binary encoders (CBOR, MessagePack)
  now serialize a **schema-implied array** (no keys). Result (10 000 recs, seed 1):
  CBOR **110.9 → 68.9 B** (φ 36.6 → **48.1%**); msgpack 68.8 (φ 48.2%); delta 45.0 (φ 58.7%);
  JSON kept keyed as the naive Pillar-1 baseline 193.5 (φ 24.9%). Round-trip + cross-subprocess
  determinism still green.
- **T1 numbers** are the honestly-measured φ above (option: report measured, update the T1
  reference); the archive's 15.2/33.0/61.5 used a different, larger record schema and are
  superseded by these. Full CI'd table + Law-6 validation land in P1b.

#### Law-6 catch during the CBOR recheck
A throwaway size snippet created a **fresh delta encoder per record** (`new_encoder()` inside
the loop) → all-keyframes → delta mis-measured as 60.1 B. Investigated (not accepted): delta
code is unchanged and deterministic (run1==run2==60.085); true amortized delta = **45.0 B**
(keyframe 60.1 + delta-frame 44.0 over K=16). **P1b size harness must reuse one stateful
encoder across the stream** — captured as a harness requirement.

#### Verdict (P1a)
1 medium finding fixed (multi-src regression guard); 3 attacks passed no-defect. Codecs and
KAT-verified crypto are correctness-complete. `make all` green; ready to tag `p1a-code-done`
(SYNC-1). Two byte-accounting ⚠️ items carried into P1b.

### P1a — CBOR compaction floor + deep correctness verification (2026-07-04)

#### Can CBOR compact more? (incl. integer keys) — measured, seed 1, 10 000 recs
| variant | s (B) | φ | note |
|---|---|---|---|
| string-key map (original) | 110.9 | 36.6% | keys cost ~42 B/rec |
| **integer-key map** | 80.9 | 44.2% | better than strings, **worse than the array** |
| **array — no keys (adopted)** | **68.9** | **48.1%** | near-optimal for CBOR |
| bespoke fixed-width struct pack | 62.0 | 50.8% | theoretical floor (not self-describing) |
| array + 16 B truncated hash | 51.9 | 55.2% | needs a security/spec change (⚠️) |

Conclusion: **integer keys do not beat the keyless array**; the array is within **~7 B (11%)**
of a bespoke packed struct, so little more is extractable *within CBOR*. **49% of the CBOR
record is the 32 B SHA-256 `prev_hash`** — the only large further reduction is truncating it,
which is a security/spec decision (docs/01 §1 fixes SHA-256) → **⚠️ for Mohamed, not done
unilaterally**. Delta already exploits inter-record correlation to reach 45.0 B.

#### Deep correctness verification (independent cross-checks — all pass)
- **varint/zigzag**: `zigzag` matches an independent reference over −10¹⁵…10¹⁵ incl.
  2³², 2³³; `svarint`/`uvarint` round-trip; LEB128 lengths exact (127→1 B, 128→2 B, 2³²−1→5 B).
- **CBOR canonical**: shortest int/length forms verified (0→1 B, 24→2 B, −1→1 B, 32 B bstr→34 B).
- **round-trip + determinism**: all 4 encoders — hypothesis (1000/enc) + boundary min/max/extreme
  (`test_boundaries.py`, 16 cases) + a 2000-rec double-encode determinism check + the
  two-subprocess SHA-256 gate.
- **crypto**: valid✓ / tamper✗ / zero-sig✗ for all schemes; KATs RFC 8032 ×5 (deterministic
  sign), Wycheproof ECDSA ×484 + Ed25519 ×150, Chia AugScheme aggregate + BasicScheme sign.
- **methodology note (scientific)**: JSON is measured as a keyed object (self-describing naive
  baseline); CBOR/MessagePack as schema-implied arrays (a fixed-schema deployment omits field
  names). This is a documented, deliberate comparison — stated so the JSON≫CBOR gap is not
  mistaken for pure binary-vs-text efficiency.
- Suite: **699 tests green**, ruff clean, `make all` green.

### P1b — measurements + Results validation (Law 6) — 2026-07-04

Runner `authbc.bench.micro` (`make bench-micro`), seed 1, i5-14400F, WSL (governor
uncontrolled). CSVs `results/raw/p1_{sizes,crypto}.csv` carry the full env block + config hash.

#### Table 1 — auth-fraction (T1), measured, g = 64 inline
| encoding | s (B) mean [95% CI] | max | φ = 64/(s+64) |
|---|---|---|---|
| JSON (keyed baseline) | 193.5 [193.50, 193.54] | 195 | **24.9%** |
| CBOR (schema array) | 68.9 [68.92, 68.96] | 71 | **48.1%** |
| MessagePack (array) | 68.8 [68.81, 68.86] | 70 | **48.2%** |
| delta (K=16) | 45.0 [44.93, 45.08] | 61 | **58.7%** |

#### Table 2 — scheme timings, median [95% CI] (µs), 200 B msg
| scheme | sign | verify |
|---|---|---|
| ECDSA-P256 | 26.2 [25.4, 27.1] | 78.5 [76.1, 81.1] |
| Ed25519 | 29.1 [28.3, 29.8] | 95.0 [92.2, 97.7] |
| BLS (AugScheme) | 324.6 [322.7, 326.2] | 1016.5 [1007, 1024] |

BLS aggregate / aggregate_verify (µs) — cross-signer, distinct messages:
b=2: 149.9 / 1469 · b=4: 296.1 / 1931 · b=8: 606.9 / 3445 · b=16: 1278.7 / 5912 · b=32: 2588.4 / 11393.
**BLS-verify / Ed25519-verify ≈ 10.7×** (feeds T4).

#### §Validate-Results checklist
1. **EXPECTATION (stated in advance) vs got.** Sizes: expected the compacted φ (JSON 24.9 /
   CBOR 48.1 / delta 58.7) established earlier — reproduced exactly. Timings vs the inlined
   anchors: Ed25519 sign 15–60 → **29.1 ✓**, verify 40–120 → **95.0 ✓**; ECDSA verify 80–300 →
   **78.5** (just under the low anchor — see gate 2); BLS pairing verify 1–3 ms → **1.02 ms ✓**.
2. **SANITY GATES.** verify > sign for every scheme ✓ (no docs/06 §9 red flag). agg_verify
   monotonically increasing in b ✓. φ ∈ (0,1) ✓. CI widths non-zero and sane (sizes ~0.05 B;
   timings 2–10%) ✓. ECDSA-verify 78.5 µs is ~2% below the 80 µs anchor floor — same order of
   magnitude, explained by a fast 2024 CPU + OpenSSL's optimized P-256; **not** "far outside",
   so recorded, not a STOP.
3. **CROSS-CHECK (independent).** Size: CBOR array = 34 B (32 B hash) + ~35 B for 11 numeric
   fields = ~69 B, matching 68.9 within rounding, and within 11% of a bespoke 62 B struct pack.
   Timing: Ed25519 sign ~29 µs and verify ~95 µs match published `cryptography`/OpenSSL x86
   figures (tens of µs); the sign<verify ordering and the ~10× BLS gap are structurally correct.
4. **AMBIGUITY.** The only borderline value (ECDSA verify vs 80 µs anchor) is explained above
   with evidence — a fast-CPU effect, not a bug; nothing buried.
5. **DETERMINISM.** Sizes are byte-identical across runs (seeded) ✓. Timings are wall-clock and
   vary run-to-run *within CI* (ECDSA sign 23.6 µs first run → 26.2 µs second) — expected for a
   noisy WSL host; the seeded computations (sizes, KATs, bootstrap CI) are reproducible.
6. **PROVENANCE.** Both CSVs carry python/cpu/governor/lib-versions + seed + config_hash; the
   checksum column proves outputs were consumed (DCE guard). BLS rows carry `n_ops` (200–5806;
   fewer than 10 000 for ms-scale ops, justified by the wall-time cap — see timers.time_op).

#### Verdict (P1b)
All gates pass or are explained. T1 auth-fraction and scheme-timing tables are trustworthy and
committed. The compaction result **strengthens** T1 (auth ≈ half the CBOR record). Ready to tag
`p1-done`. Carry-forward to later phases: BLS byte accounting = 96 B (T2/T4); ECDSA-verify sits
at the low edge of the anchor on this CPU (re-confirm on RPi4 at P7).


---

<a id="s3"></a>

## 3. Audit — P2 (ledger + canonical wire format)

*Formerly `docs/audits/p2.md`, last changed 2026-07-04. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: `ledger/{record,chain,store,verify}`, `placement/wire`, frozen vectors, golden, fuzz —
against docs/01 §1 & §4, docs/03 §3–4, docs/06 §5. Method: T_TEMPLATES §Audit + §Validate-
Results. Date 2026-07-04. Baseline at audit start: `0b13236`.

### Results validation (Law 6) — the golden counters
- **EXPECTATION (stated in advance)** for the 3-UAV seeded scenario (`tests/integration/
  test_golden.py`): `stored=30` (3×10 valid signed), `replay=5` (re-ingest UAV-1's first five),
  `equivocation=1` (a second (src2,seq0) with a different payload), `tampered=1` (a UAV-3 record
  under the wrong key).
- **OBSERVED**: `{stored:30, replay:5, equivocation:1, tampered:1}` — exact match; 1 evidence
  pair retained; 30 records stored.
- **SANITY GATES**: counters are non-negative and sum to the 37 ingests; a tampered/equivocating
  record is never stored (stored=30, not 32). ✓
- **CROSS-CHECK**: prev_hash verified by an INDEPENDENT recompute path (`test_chain`), separate
  from `Record.record_hash()`; both agree over a 200-record chain.
- **DETERMINISM**: `run_scenario().counters == run_scenario().counters` ✓; frozen frames rebuild
  byte-identically (Ed25519 + BLS signing are deterministic).
- **PROVENANCE**: frozen vectors carry `expected.json` (frame + covered SHA-256, fixed ed seed).

### Mandatory attacks
| # | attack | finding | evidence / fix |
|---|---|---|---|
| 1 | **Canonicalization ambiguity** — map order? indefinite lengths? | clean | `canonical_bytes` = `cbor2.dumps(canonical=True)` (sorted keys, shortest forms, definite lengths). `test_canonical_no_indefinite_lengths`: canonical re-encode is byte-identical (idempotent), which an indefinite-length item would break. pl key insertion order does not change bytes. |
| 2 | **covered_bytes off-by-one at every boundary** | clean | `test_covered_bytes_boundaries`: A/C = per-record canonical bytes, B/D = canonical bytes of the whole `recs` array; **B ≠ concat(per-record)** (array framing distinct). `test_covered_bytes_changes_with_any_record`: any field change flips the covered bytes. |
| 3 | **seq u32 wraparound** | clean (policy stated) | Monotonic-increasing required; wrap (seq ≤ last) ⇒ REPLAY. `test_seq_wraparound_rejected_as_replay`. Documented in `store.py` (u32 ≈ 6.8 yr at 20 rec/s). |
| 4 | **ts ms consistency** | clean | `ts` is u32 milliseconds, range-validated in `Record.__post_init__` (integer — no float/tz drift). Ordering is by `seq`, not `ts`, so `ts` jitter cannot reorder or break the chain; out-of-range ts is rejected. |
| 5 | **duplicate-record-in-frame** | clean | `test_duplicate_record_in_frame`: the same record twice ⇒ first STORED, second REPLAY (keyed on (src,seq)+hash); no double-count. |
| 6 | **D fragment-header integrity** | analyzed — low severity, no forgery | The block signature covers the **records only** (docs/01 §4), so `block_id/frag_idx/frag_total` are not authenticated. Verified: header-only tamper leaves `verify_D` True, but ANY wrong reassembly (dropped/reordered records) ⇒ `verify_D` **False** — **no forged data is ever accepted** (integrity holds). Impact is limited to DoS-via-reassembly, which is out of scope (docs/01: availability is a robustness metric) and trivially available to a channel attacker who can drop frames anyway. ⚠️ Optional future hardening (binding headers into the D sig) would change `covered_bytes` ⇒ a D6 wire-vector change ⇒ Mohamed's call; NOT done here. |

### Engineering attacks
- **Determinism / seeds**: golden + frozen-vector determinism asserted (above).
- **Error paths / fuzz**: `test_fuzz` — 1000 seeded byte-mutations of valid A–D frames → zero
  crashes/hangs; `decode_frame` raises exactly one `WireDecodeError` (auth shape validated),
  `verify_*` return bool (verify_C tolerates malformed pubkey bytes). Malformed > 0, all handled.
- **CI honesty**: these run in `make test` (unit+integration); `make all` green.

### Coverage (P2 gate ≥90% on ledger + wire)
record 100 · store 100 · verify 100 · chain 96 · wire 94 → aggregate ~95%. ✓

### Verdict
All 6 mandatory attacks + engineering attacks pass or are analyzed (attack 6 = low-severity,
no-forgery, documented). Golden counters validated (Law 6). Wire vectors frozen (⚠️ D6).
Ready to tag `p2-done`. Carry-forward: e-axis-in-recs reconciliation → P3; optional D header
binding → Mohamed (post-freeze).


---

<a id="s4"></a>

## 4. Audit — P3 (placements + channel emulator)

*Formerly `docs/audits/p3.md`, last changed 2026-07-04. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: `placement/{framer,inline,self_batch,relay_agg,block_agg}`, `channel/{airtime,emulator}`,
`bench/{macro,framesizes}` — against docs/01 §1&3, docs/02 §6-7, docs/03 §3, docs/06 §3. Method:
T_TEMPLATES §Audit + §Validate-Results. Date 2026-07-04. Baseline at audit start: `e356e5d`.

### Results validation (Law 6)
- **p=0 ⇒ V=1 and airtime balances.** Macro golden through the emulator (`test_macro`): 3 UAVs ×
  10 records, p=0 ⇒ broadcast=verified=total_stored=60, V=1.0. Airtime: sender charged
  Σ `airtime_broadcast(L)` = 1701.000µs for L∈{100,250,700}; receivers 0.0; total = sender-only
  (no double-count). ✓
- **p>0 ⇒ receive fraction ≈ (1−p) (Binomial).** 20 000 frames, p=0.10, two receivers:
  rx2=0.9020, rx3=0.9032, both inside the 95% Binomial CI 0.900 ± 0.0042. ✓ (State-first
  expectation = 0.90 met.)
- **Airtime for a known size = hand value.** `airtime_broadcast(100)=233.667µs`, `(0)=100.333`,
  `(1500)=2100.333`; unicast `(0)=156`, `(100)=289.333` — all match hand arithmetic (test_airtime).
- **Determinism.** Emulator metrics byte-identical across identical seeds (test_emulator);
  `run_macro` identical across identical seeds (test_macro). ✓
- **PROVENANCE.** `framesizes.csv` carries env + config_hash + s_e; measured s_e = json 193.5 /
  cbor 68.9 / msgpack 68.8 / delta 45.0 (reproduces P1 — one stateful encoder/stream).

### Mandatory attacks
| # | attack | finding | evidence |
|---|---|---|---|
| 1 | **Loss independence across receivers** | clean | corr(rx2,rx3)=+0.004 (~0); P(both rx)=0.815 vs (1−p)²=0.81; P(both drop)=0.0098 vs p²=0.01 — matches the independent-Binomial model. |
| 2 | **Airtime double-counting on broadcast** | clean | Airtime charged to the **sender only, once per frame**; receivers add 0 (verified at p=0: total == Σ frame airtimes). `test_p0_all_receive_and_airtime_is_sender_only`. |
| 3 | **C one-bad-signer semantics** | clean (documented) | BLS `aggregate_verify` is all-or-nothing; one corrupted inner signature ⇒ whole frame ok_mask=[False×n] and cannot localize the bad signer. `test_one_bad_inner_signature_fails_whole_aggregate`. |
| 4 | **D timeout races** | clean | Reassembly buffer keyed by **(src, block_id)** (block_id alone collides across srcs — caught + fixed); reorder-tolerant; a block past the 500 ms sim-time timeout is swept into `discarded_partial`; loss of one fragment kills exactly that block. `test_block_agg`. |
| 5 | **b_max off-by-one at exact MTU** | clean | `b_max(100,60)=14` ⇒ frame=1500 B (= MTU, fits); 15th record ⇒ 1600 B (> MTU). Emulator accepts a 1500 B frame, rejects 1501 B. Floor division is exact at the boundary. |

### Engineering attacks
- **Determinism / seeds**: emulator + macro determinism asserted (above).
- **Efficiency**: caught + fixed an O(n²) payload generator in `macro` and the fresh-encoder-per-
  record pitfall in `framesizes` (delta was 60.1, corrected to 45.0) — Law 6 both times.
- **CI honesty**: framers/emulator/airtime/macro run in `make test`; `make all` green.

### Flagged reconciliations (carried, per plan)
- **T_fx ≈ 123µs vs components**: I implement exact component formulas (broadcast fixed 100.33µs,
  unicast 156µs); the docs' ≈123µs matches neither — labelled, not mixed; revisited at P6 (NS-3).
- **b_max CBOR/g_a=64 reference**: inlined 9 vs formula **10** (10·130+40+64=1404≤1500); formula
  is arithmetically correct, reference is an off-by-one.
- **Superseded sizes / BLS=96 B**: framesizes use measured s_e + g_a=96 (Mohamed's P1 decisions).

### Coverage (P3 gate ≥90% on placement + channel)
framer 100 · inline 100 · self_batch 100 · relay_agg 100 · block_agg ~97 · airtime 100 ·
emulator ~97 → aggregate well above 90%.

### Verdict
All Law-6 gates + 5 mandatory attacks pass; two efficiency bugs caught and fixed en route.
Four placements end-to-end; framesizes.csv exported (SYNC-3). Ready to tag `p3-done`.


---

<a id="s5"></a>

## 5. Audit — P4 (experiments E1–E3)

*Formerly `docs/audits/p4.md`, last changed 2026-07-04. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: `bench/experiments` (run_e1/e2/e3), `experiments/e{1,2,3}/config.yaml`, `analysis/
figures_e123`, frozen `results/raw/e{1,2,3}_*.csv` + figures — against docs/02 T1-T3 & §8,
docs/04 §2. Method: T_TEMPLATES §Audit + §Validate-Results. 2026-07-04. Baseline: `96c9a8f`.

### Results validation (Law 6) — expected stated BEFORE running
#### E1 (T1, overhead dominance)
- **EXPECTED**: φ = g/(s+g), g=64, exactly; absolute φ from **measured** sizes (supersede the
  archive 15.2/33.0/61.5). **OBSERVED** (30 seeds × 1000 recs): JSON 25.09% / CBOR 49.14% /
  msgpack 49.55% / delta 58.72%. Formula holds by construction; CROSS-CHECK: 64/(66.25+64)=
  49.14% ✓. Auth ≈ half a CBOR record — the motivating result, stronger with compacted CBOR.

#### E2 (T2, batching cure)
- **EXPECTED**: per-record on-air ≈ s·A, A=M/(M−H_f−g_a); at M=1500 measured A within 5%; φ→≈
  (g_a+H_f)/M. **OBSERVED**: at **M=1500 measured A within 0.00–0.25%** of the formula (delta
  1.0745 = formula exactly); φ@b_max ≈ 6.94–7.13%. CROSS-CHECK: 1500/1396 = 1.0745 ✓.
- **AMBIGUITY handled**: at small MTU the discrete b_max deviates > 5% (delta@M=256 = 5.11%).
  Explained, not tolerated: this is integer-b_max discretization (b_max=3) vs the continuous
  relaxed-floor formula — expected and monotonically shrinking as M grows (M=576 ≤ 3.97%,
  M=1500 ≤ 0.25%). Not a bug.

#### E3 (T3, loss frontier)
- **EXPECTED**: V_B = 1−p flat in b; V_D = (1−p)^{n(b)} decreasing; B Pareto-dominates D above
  V=(1−p)². **OBSERVED** (p=0.05, seeds 1..30): V_B flat 0.946–0.953 (theory 0.95) for all b;
  V_D = 0.95 for b≤20 (n=1), drops to ≈0.902 for b≥21 (n=2). CROSS-CHECK: (0.95)²=0.9025 =
  measured V_D(b=40)=0.90207 ✓. On (bytes, V), D's tiny byte saving (72.5 vs 74.1 B/rec) is
  dominated by its V loss (0.90 vs 0.95) — B dominates.
- **SANITY GATES**: φ,V ∈ [0,1] ✓; V_B flat ✓; V_D non-increasing in b ✓; A within 5% at
  M=1500 ✓; CI widths sane (bootstrap over 30 seeds).
- **DETERMINISM**: run_e1/e2/e3 reproduce identical rows across runs (unit tests); figures
  byte-identical across regenerations (verified sha256). **PROVENANCE**: every CSV has env +
  config_hash; PROVENANCE.md maps each figure → raw → sha256.

### Mandatory attacks
| # | attack | finding | evidence |
|---|---|---|---|
| 1 | **Bootstrap-CI correctness** | clean | `stats.bootstrap_ci` unit-tested on a known distribution (brackets the median, seeded ⇒ reproducible, degenerate-constant → zero width) — `test_harness`. |
| 2 | **Seed independence (no shared RNG across configs)** | clean | E3 seeds a fresh `default_rng([base, b, round(p·1000), seed])` per (b,p,seed) — no global/shared RNG; E1/E2 are deterministic size computations (no RNG). Distinct configs ⇒ independent streams. |
| 3 | **Unit / axis errors** | clean | φ in %, V dimensionless ∈[0,1], bytes/record, goodput Mbit/s; figure axes/labels match; s·A and (1−p)ⁿ overlays in the same units as the measured series. |
| 4 | **Measured-vs-theory gaps** | all explained | E1 exact; E2 ≤0.25% at M=1500 (small-M discretization documented); E3 within CI of theory. No unexplained gap. |
| 5 | **Baseline fairness** | clean | E1 uses the SAME seeds across all encodings ⇒ identical records ⇒ fair φ comparison; baselines A+JSON / A+CBOR flagged in-row (`baseline=1`). E2/E3 use one shared measured s_e stream. |

### ⚠️ D6 — frozen
`results/raw/e{1,2,3}_*.csv` are FROZEN after this collection; figures regenerate byte-stable
from them via `make figures`. Re-runs reproduce identical raw (determinism) — any change is a
D6 event needing Mohamed.

### Flagged reconciliations (carried)
- E1/E2 absolute numbers use measured s_e + g_a=64/96 (Mohamed's P1 decisions), superseding the
  archive/P4 inlines (15.2/33.0/61.5; "A≈1.033"); the T1/T2/T3 FORMULAS all validate.
- D on-air modeled byte-optimally (one signature per block, T3 (ii)); the P3 block_agg
  implementation replicates the sig per fragment — a possible P-later optimization, noted.
- Thesis success criterion (≥40% auth-byte cut vs A+CBOR at V≥0.95, p=0.05) — the pieces exist
  (B batched vs A+CBOR inline); the full optimized-config claim is evaluated at E5.

### Verdict
All Law-6 gates + 5 attacks pass or are explained. E1–E3 raw frozen with provenance; figures
byte-stable. Ready to tag `p4-done`.


---

<a id="s6"></a>

## 6. Audit — P5a models (bianchi / energy / optimizer)

*Formerly `docs/audits/p5.md`, last changed 2026-07-04. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: `src/authbc/models/{bianchi,energy,optimizer}.py` + `tests/unit/models/**` against the
specs they implement: docs/02 §6 (Bianchi), §7 (energy/latency), T1–T5; docs/03 §3 (models/).
Method: adversarial attack with reproducible evidence (T_TEMPLATES §Audit). Lane 2, branch
`lane2`. Date 2026-07-03. Baseline at audit start: `p0-done` (0275bf1). This phase produces
**no experimental data** — the deliverable is spec-driven code validated against hand/independent
values; E4 data + its provenance/seed discipline are P5b (SYNC-2).

### Findings table

| # | severity | attack / evidence | root cause | fix |
|---|---|---|---|---|
| 1 | **medium** | **Baseline fairness — did the byte model amortize the naive baseline's signature?** Placement A is *inline per-record* authentication (T1): each record carries its own g_a, and batching must NOT reduce that (A is the "A+CBOR/A+JSON" baseline the thesis headline compares against, docs/04 §2). An early byte model computed `s + (g_a+H_f)/b` for *all* placements — amortizing A's signature would understate A's bytes and **inflate the co-design win**. | One byte formula applied to every placement; A's per-record-auth semantics not honored. | `frame_auth_bytes(placement,b,g_a)` → **A carries b·g_a**, B/C/D carry one g_a. `bytes_per_record`, the EnergyConfig auth bytes, and the MTU check all use it. Evidence: `test_bytes_model_A_does_not_amortize_signature` asserts A=`s+g_a+H_f/b` > B=`s+(g_a+H_f)/b`. |
| 2 | info (no defect) | **Does `T_fx` match the doc's "≈123 µs" anchor (docs/02 §6)?** | — | Literal term breakdown = `T_phy+8·34/R+SIFS+T_ack+2δ` = **122.0 µs** = `T_s(0) − DIFS` (channel-busy part of a successful exchange minus the DIFS idle deferral). Reconciles with the doc's rounded "≈123 µs". `test_tfx_reconciles_with_doc_anchor` pins both the exact value and the ≤1.5 µs agreement. No fudge factor. |
| 3 | info (no defect) | **Solver robustness at high N (docs/02 §6 warns undamped oscillates).** | — | Production solver is the damped substitution in p_c (`p←0.7p+0.3p_new`, tol 1e-12); converges at N=100 in 13 iters, residual 1.5e-13. The *independent* brentq reference initially failed at N≥50 because p_c crosses the `2p_c=1` singularity of τ(p_c) — resolved by bracketing the reference on **τ∈(0,2/(W+1)]** (τ is bounded, monotone in N). Production path never touches that singularity. |
| 4 | info (limitation, documented) | **D frame-span vs header accounting.** `n(b)=⌈(b·s+g_a+H_f)/M⌉` (docs/02 T3, one nominal header) while the energy airtime bills one `T_fx`+one `H_f` per frame (`radio_airtime_s`). For large blocks the extra `(n−1)·H_f` could nudge true bytes past `n·M` by < one frame. | Two doc-faithful formulas meet at a sub-frame seam. | Kept the **normative** T3 formula for n; bill real per-frame headers for airtime; discrepancy bounded by `(n−1)·H_f` (≪ M) and disclosed here. Latency's M/M/1 queueing term (docs/02 §7) is likewise **deferred to P5b** — current `D(b)=b/Λ+T_air` is the fill+on-air lower bound, labeled in code. |
| 5 | info (no defect) | **Determinism & error paths (engineering attack).** | — | All three modules are pure/deterministic (`test_determinism` ×3). Non-convergence **raises** `ConvergenceError`, never returns a half-solved point (`test_non_convergence_raises_not_silent`, monkeypatched budget). Bad inputs raise `ValueError` (n<1, payload≤0, batch<1, negative bytes, powers≤0, n_frames<1). C without aggregate timings raises rather than fabricating them (`test_placement_C_without_aggregate_params_raises`, `…without_agg_verify_raises`). Grid guard `MAX_GRID_POINTS` raises on oversize/empty sweeps. |

### Results validation (Law 6) — Bianchi, energy, optimizer

**1. EXPECTATION (stated in advance) vs OBSERVED**
| quantity | expected (why) | observed |
|---|---|---|
| τ, p_c | ∈[0,1]; N=1 ⇒ τ=2/(W+1)=0.117647, p_c=0 (closed form); N=2 ⇒ p_c=τ | exact at N=1; p_c=τ at N=2 to 1e-9 |
| τ,p_c at N=5 | independent brentq: 0.076148902235 / 0.271536297612 | damped solver matches < 1e-9 (resid 1.1e-12) |
| τ,p_c at N=50 | independent brentq: 0.018290394373 / 0.595266660858 | damped solver matches < 1e-9 (resid 1.0e-13) |
| S vs N (L=1000 B) | "roughly flat / slowly varying, NOT dip-then-rise" (docs/02 §6) | monotone non-increasing 4.96→2.93 Mb/s over N=2..100; no dip |
| S vs PHY ceiling | S < 6 Mb/s | max 5.14 Mb/s at N=1 < 6 |
| energy/rec (B toy) | hand-calc 2·(50+6+10)µs·W + 0.8·1994µs/10 = **291.5 µJ** | `per_record` = 291.52 µJ (exact to 1e-15) |
| optimizer Pareto toy | hand-derived front = {P1,P2,P3} of 5 | exact (`test_pareto_front_toy_is_exact`) |

**2. SANITY GATES** — all pass: probabilities ∈[0,1]; S < PHY bound; S monotone where theory
says gently monotone; verify-time never asserted below sign-time for a scheme (not compared
here); the three Bianchi spot values and the energy hand-calc match; CI widths N/A (no
stochastic P5a runs). No gate breached ⇒ nothing suppressed.

**3. CROSS-CHECK (independent path)** — Bianchi: a bracketed-bisection (`scipy.brentq`) solver,
a genuinely different algorithm from the damped substitution, agrees at N∈{2,5,10,50,100} to
<1e-9 (`test_matches_independent_brentq`). Energy: `291.5 µJ` recomputed by hand above and in
`test_placement_B_matches_hand_calc`. Optimizer: the 5-point Pareto front derived by hand and
asserted exactly.

**4. AMBIGUITY RULE** — the only surprise (brentq failing at high N) was chased to a genuine
cause (τ(p_c) singularity at p_c=0.5, reference-only) and fixed, not averaged away. S declining
~40% over N=2..100 is expected contention behavior, not a dip-then-rise → a real feature, not a
bug.

**5. DETERMINISM** — identical outputs across repeated calls (three `test_determinism` cases);
no seeds involved (deterministic analytic models).

**6. PROVENANCE** — P5a emits no CSV/figure; provenance (seeds, config-hash, env headers) binds
at **P5b/E4** where measured timings enter. Green baseline recorded in docs/status/lane2.md.

### Verdict
1 medium finding **fixed** (naive-baseline byte model) with a regression test; 4 attacks passed
with no defect (2 documented limitations bounded and deferred to P5b). `make lint` clean;
`make test` = 65 passed; **100 % line coverage on all three model modules**. P5a acceptance
criteria met — ready to tag `p5a-done` and announce SYNC-2.

---

## Audit — P5b / E4 (Ed25519↔BLS crossover)

Scope: `models/crossover.py`, `experiments/e4/run_e4.py`, `analysis/figures_e4.py`,
`results/raw/e4_{crossover,bytes}.csv` against docs/02 T4 and docs/04 §2, driven by the P1
measured data (`p1_crypto.csv`, `p1_sizes.csv`). Date 2026-07-04. Lane 2, rebased on `p1-done`
(e33a149). **Decision in force (Mohamed):** absolute joules deferred to P7 (powers unmeasured,
⚠️ D5); E4 delivers the **power-independent** crossover (κ\*=P_r/P_c) + bytes + verify-throughput.

### Findings table

| # | severity | attack / evidence | root cause | resolution |
|---|---|---|---|---|
| 1 | **finding (reported, not massaged)** | **Measured Ed25519-verify is only ~10.7× cheaper than BLS single-verify** (94 972 ns vs 1 016 469 ns), *below* doc-02 T4's "20–60×" anticipation. | The blspy AugScheme single-verify (~1.02 ms) is faster than T4's assumed pairing cost, and Ed25519 verify (~95 µs) on this i5-14400F sits mid-anchor. Both values are inside the docs/04 §1 anchors and `verify>sign` holds ⇒ a genuine measurement, not a harness bug. | Reported verbatim in the CSV header (`ed25519_verify_speedup_vs_bls=10.703`) and here; the **direction is unchanged** (Ed25519 decisively cheaper), only the doc's magnitude was optimistic. Not averaged away (Law 6/7). |
| 2 | info (decision) | **No absolute joules.** The energy model needs P_c/P_r, unmeasured until P7. | Powers require the ⚠️ D5 meter. | E4 reports κ\* (break-even P_r/P_c); `models.energy.per_record` (already unit-tested) yields joules once P7 powers land. Documented; tag semantics noted in the handoff. |
| 3 | info (no defect) | **Is the crossover encoding-dependent?** A reader might expect κ\* to move with record size s. | — | κ\* depends only on the auth-byte difference (the b·s data bytes are identical for both schemes and cancel in ΔRADIO) ⇒ κ\* is **independent of encoding**. Verified by construction (no `s` in the crossover API) and by `test_kappa_star_*`. Reported as a clean structural finding; `e4_bytes.csv` still gives absolute bytes/rec per encoding. |
| 4 | info (limitation, documented) | **Byte-accounting approximations.** `H_a` (BLS aggregate header) and the ΔRADIO frame-count/T_fx second-order term. | Protocol parameter + sub-frame seam. | `H_a=0` is the **BLS-best case** (any larger `H_a` only widens Ed25519's lead); ΔRADIO uses the auth-byte difference per T4 (data bytes cancel), the T_fx frame-count effect is ≤ one T_fx and disclosed. |
| 5 | info (no defect) | **Determinism / provenance (engineering attack).** | — | Runner is a deterministic function of the P1 medians (rerun byte-identical). CI columns are **propagated monotonically** from P1's bootstrap CIs (BLS-time↑, Ed-time↓ bound ΔCPU). Both CSVs carry the env block + `config_hash`; the figure is regenerated from the frozen CSV only (docs/04 §5). |

### Results validation (Law 6) — the E4 crossover

**1. EXPECTATION (stated in advance) vs OBSERVED** (H_a=0, R=6 Mb/s, from the measured medians):
| quantity | expected (why) | observed (e4_crossover.csv) |
|---|---|---|
| κ\*(ρ=1): b=2…32 | 12.0, 5.6, 4.3, 3.4, **3.13** (T4: Δt·R/8Δ) | 11.99, 5.59, 4.34, 3.38, **3.13** |
| κ\*(ρ=0) ∀b | 43.2 (own-verify diff; b cancels) | 43.2 (b-independent) |
| winner ∀ (ρ,b,Λ) | **ed25519** (plausible P_r/P_c≈0.2–0.5 ≪ κ\*) | winners set = **{ed25519}**, min κ\*=3.1327 |
| BLS verify-throughput @ Λ=2000 | infeasible at b=2 (t_av/2·Λ=1.47>1), feasible b≥4 | `bls_verify_ok`=False@b=2, True@b≥4 |
| Ed25519 verify speedup | doc "20–60×" | **10.7×** (finding #1) |

**2. SANITY GATES** — κ\* finite/positive wherever ΔCPU,ΔRADIO>0; `verify>sign` for every scheme;
CI band tight and **entirely above the plausible bound** (at the min point κ\*∈[3.03, 3.22] ⇒ the
Ed25519 verdict survives measurement uncertainty). No gate breached.

**3. CROSS-CHECK (independent hand calc)** — κ\*(ρ=1, b=32): ΔCPU = 11 392 958.5/32 − 94 972.4 =
261 057.6 ns; ΔRADIO = 8·(64−48/32)/6e6 = 83.333 µs; κ\* = 261.058/83.333 = **3.1327** = the CSV
cell to 4 dp.

**4. AMBIGUITY RULE** — the only deviation from doc anticipation (10.7× vs 20–60×) was chased to a
genuine cause (fast blspy single-verify) and **reported as a finding**, not buried.

**5. DETERMINISM** — analytic over fixed medians; `make exp-e4` reproduces byte-identical CSVs.

**6. PROVENANCE** — `e4_crossover.csv`/`e4_bytes.csv` carry the env block, `config_hash`, CI
columns, `ed25519_verify_speedup_vs_bls`, `plausible_kappa_max`, `R_bps`; figure caption cites
the source CSV + config hash.

### Verdict (P5b)
**T4 confirmed**: Ed25519 wins self-batch (bytes ≈ BLS, verify far cheaper) **and** relayed traffic
on 802.11 (break-even needs P_r/P_c > 3.1–43, i.e. an implausibly radio-heavy platform); BLS's
regime (low-rate links) is not reached at 6 Mb/s, and at Λ=2000 BLS is additionally throughput-
infeasible below b=4. The one quantitative gap (verify speedup 10.7× vs the doc's 20–60×) is
reported honestly. Absolute joules deferred to P7 per decision. `make all` green (**773 passed**),
crossover.py 100 % coverage. P5b acceptance met — ready to tag `p5-done`.


---

<a id="s7"></a>

## 7. Audit — E5 (co-design end-to-end, T5)

*Formerly `docs/audits/e5.md`, last changed 2026-07-05. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: `bench/experiments.run_e5`, `experiments/e5/config.yaml`, `analysis/figures_e5.py`, frozen
`results/raw/e5_codesign.csv` — against docs/02 T5, docs/04 §2 (success criterion). Method:
T_TEMPLATES §Audit + §Validate-Results. 2026-07-05. Integrator (SYNC-4).

### Results validation (Law 6)
- **EXPECTED (stated first):** batching amortizes the 64 B signature ⇒ the co-optimized config
  cuts on-air auth bytes far past the 40 % target; the optimum is **self-batch (B)** with the
  smallest deterministic encoding (**delta**) at the largest feasible batch, and V = 1−p = 0.95.
- **OBSERVED:** optimized = **delta + ECDSA-P256 + placement B + b=28** → on-air auth overhead
  **3.71 B/record** (bytes/rec 48.7), V = 0.95. A+CBOR (Pillar-1) overhead = **104 B** →
  **auth-byte cut = 96.4 %** ≥ 40 % ⇒ **PASS**.
- **SANITY GATES:** bytes/rec ≥ s for every row ✓; V ∈ [0,1] ✓; A+CBOR overhead = 104 =
  g_a(64) + H_f(40) exactly (inline b=1) ✓; **D-over-agg V = 0.9025 = (1−p)²** (spans 2 frames)
  ⇒ correctly **fails** V≥0.95, demonstrating T3 (block-level dominated) ✓; the optimized point
  is in `res.feasible`/Pareto (min bytes over the feasible pool).
- **CROSS-CHECK (hand):** optimized bytes/rec = s + (g_a+H_f)/b = 45.0 + (64+40)/28 = 45.0 + 3.71 =
  48.71 ✓; auth cut = (104 − 3.71)/104 = 96.43 % ✓.
- **DETERMINISM:** `run_e5` reproduces identical rows (unit test); figure byte-stable (PROVENANCE
  sha). **PROVENANCE:** inputs are the FROZEN measured CSVs — sizes from `e1_dominance.csv`,
  timings from `p1_crypto.csv`; env + config_hash header on `e5_codesign.csv`.

### Mandatory attacks
| attack | finding |
|---|---|
| Input provenance (measured, not fabricated)? | Sizes ← E1 (30-seed measured); sign/verify ← P1b crypto (measured); g_a = 64/64/**96** (BLS). Only t_enc + power are **nominal** (flagged). |
| Baseline fairness? | Optimized and all baselines share the SAME platform + constraints + models; A+CBOR/A+JSON are inline b=1 (the naive/Pillar-1 points), D-over-agg is b=40 as specified. |
| Success arithmetic? | 104 → 3.71 B = 96.4 % cut; hand-verified. Criterion also requires V≥0.95 (met); `pass` is the AND of both. |
| Scheme tie (ECDSA vs Ed25519)? | Both are 64 B ⇒ **byte-identical**; the byte-optimum is a tie. ECDSA-P256 wins the energy tiebreak on x86 (faster sign) so it's the Pareto point; the D2-default Ed25519 is **equally byte-optimal** — the ≥40 % headline holds for either. Documented, not a deviation. |

### ⚠️ Power caveat (P7)
The **auth-byte headline is power-free** and fully grounded in measured bytes. The `energy_uj`
column and the (nominal) `t_enc`/`P_cpu`/`P_radio` are **model estimates pending RPi4 measurement
at P7** — never presented as measured hardware energy. E5 re-runs with P7 powers for the final
energy story.

### Verdict
Success criterion **PASS** (96.4 % ≥ 40 % at V=0.95, p=0.05) — the T5 co-design result holds:
smallest deterministic encoding + self-batch placement amortizes authentication to ~4 B/record,
a ~96 % cut vs the Pillar-1 baseline, while keeping V ≥ 0.95. All Law-6 gates pass. `e5_codesign.csv`
frozen; figure byte-stable. Ready to tag `e5-done`.


---

<a id="s8"></a>

## 8. Audit — P6 (Bianchi ↔ NS-3 validation)

*Formerly `docs/audits/p6.md`, last changed 2026-07-28. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

> # ⚠️ SUPERSEDED IN PART — read this first (correction added 2026-07-28)
> This audit's **broadcast** conclusions are wrong and are kept only as the audit trail.
> Specifically, §"Mechanism — DEFINITIVELY the frame capture effect" and the "timing capture"
> explanation are **RETRACTED**. PHY instrumentation at P7 measured capture at **0 %**: all 1149
> successful decodes at the monitored receiver came from single-transmitter busy periods, and an
> equal-power channel is byte-identical to the default (which was *already* equal-power — NS-3
> clamps log-distance below d₀, so the "50.7 dB near-far spread" never existed).
>
> The real cause is the **backoff counter Consecutive Freeze Process**, published by Ma & Chen
> (IEEE Comm. Lett. 11(8):686–688, 2007; IEEE TVT 57(6):3757–3768, 2008). Our own model was an
> in-house reduction of unicast Bianchi, which their abstract warns against; it was wrong by 16×.
>
> Every NS-3 number below also predates finding **F8** (a ~4.8 % goodput over-count) and the
> exact-OFDM airtime of decision **D9**, so all gap percentages here are stale.
> **Current state: docs/audits/p7.md (F8, F9 and the NS-3 simulation audit) + docs/02 §6/§6a.**


Scope: `ns3/authbc-sat.cc` (PacketSocket scenario), `ns3/run_matrix.py`, `analysis/
figures_ns3.py`, frozen `results/raw/ns3_matrix.csv` — against docs/02 §6 (Bianchi), docs/04 §3,
docs/06 §2 (the ACK trap). Method: T_TEMPLATES §Audit + §Validate-Results. 2026-07-04.
NS-3 3.41, optimized. 100 runs = N∈{5,10,20,35,50} × {unicast,broadcast} × 10 seeds, L=1400 B.

### Scenario hardening (Law-6 sanity gates caught three artifacts → fixed BEFORE any numbers)
1. **Spatial reuse** — nodes 1 m apart span 49 m at N=50; distant nodes don't carrier-sense →
   aggregate 18.8 Mb/s > 6 ceiling. Fixed: co-locate all N in a ~0.5 m cluster (ONE domain).
2. **Broadcast multi-count** — summing Rx over all N−1 receivers counts each broadcast N−1×.
   Fixed: channel goodput = aggregate / (N−1).
3. **ARP collapse** — UDP/IP unicast → 0 delivered at N≥40 (ARP can't resolve under saturation).
   Fixed: rewrote to **PacketSocket** (raw 802.11 frames, no IP/ARP; MAC payload == L exactly).

### Results validation (Law 6)
- **EXPECTED** (stated first): NS-3 **unicast** tracks ACK-Bianchi (`solve`) within a modest,
  explainable gap; NS-3 **broadcast** tracks the no-ACK/no-retry variant (τ=2/(W+1)).
- **OBSERVED** (median over 10 seeds):

  | N | unicast NS-3 / ACK-Bianchi (gap) | broadcast NS-3 / no-ACK (gap) |
  |---|---|---|
  | 5 | 4.913 / 4.673 (+5.1%) | 4.534 / 4.341 (+4.4%) |
  | 10 | 4.522 / 4.293 (+5.3%) | 3.278 / 3.036 (+8.0%) |
  | 20 | 4.131 / 3.926 (+5.2%) | 1.853 / 1.353 (+37%) |
  | 35 | 3.742 / 3.626 (+3.2%) | 1.321 / 0.337 (+292%) |
  | 50 | 3.488 / 3.427 (+1.8%) | 1.336 / 0.073 (+1735%) |

- **SANITY GATES**: every value ≤ 6 Mb/s PHY ceiling ✓; offered 12 Mb/s/node ≫ delivered ⇒
  saturation reached ✓; throughput monotone-decreasing in N ✓; **each NS-3 mode compared ONLY to
  its matching analytic variant** (unicast↔ACK, broadcast↔no-ACK) — never crossed (the trap) ✓.
- **DETERMINISM**: distinct `RngRun` per seed; figure byte-stable (sha in PROVENANCE.md);
  re-running the matrix with the same seeds reproduces the CSV. **PROVENANCE**: env + config_hash
  header on `ns3_matrix.csv`. Runtime: 100 runs ≈ 4 min (≪ 2 h budget).

### Gap analysis — quantified causes, NO silent correction (docs/06 §2)
#### Unicast → Bianchi VALIDATED
Consistent **+1.8 % … +5.3 %** across all N (NS-3 slightly above ACK-Bianchi). Attributed to:
(a) NS-3 802.11a uses `CW_min=15`; the doc/model uses `W=16` → slightly higher τ / throughput;
(b) mild capture (some collisions decoded); (c) EIFS-after-error and propagation-delay defaults.
All small, same-signed, N-stable → the DCF throughput model holds for unicast.

#### Broadcast → large high-N gap; mechanism NOT cleanly resolved (honest open item)
Reasonable agreement at low N (+4.4 % N=5, +8.0 % N=10), diverging to +292 % (N=35), +1735 %
(N=50). A **capture-isolation experiment** (Mohamed's call) — a direct `PhyTxBegin` measurement of
NS-3's real per-transmission success rate — **retracts my first, back-computed capture number**:

| N | NS-3 success (delivered/transmitted) | ideal no-ACK p_s | ratio |
|---|---|---|---|
| 5  | 60.4 % | 76.6 % | 0.79× (NS-3 **below** ideal) |
| 20 | 12.7 % | 23.8 % | 0.53× (NS-3 **below** ideal) |
| 50 | 4.4 %  | 1.3 %  | 3.5×  (NS-3 above ideal) |

**The earlier "p_s 1.3 %→23.5 %, ~18× capture" claim is WITHDRAWN** — it wrongly compared NS-3's
*per-transmission* success (delivered/tx = (1−τ)^(N−1)) against Bianchi's *per-busy-slot* p_s
(different quantities), and back-computed with ideal slot timing (Law 6/7 — the retraction is kept
visible). Corrected comparison (per-transmission success vs (1−τ)^(N−1) at τ=2/(W+1)):

| N | NS-3 delivered/tx | model (1−τ)^(N−1) | τ inverted from NS-3 |
|---|---|---|---|
| 5  | 0.604 | **0.606** (match) | 0.119 ≈ 2/(W+1) |
| 20 | 0.127 | 0.091 | 0.103 |
| 50 | 0.044 | 0.0022 | 0.062 |

**Robust finding**: at N=5 NS-3 matches the no-ACK τ=2/(W+1) model exactly; at high N NS-3's
per-transmission success **increasingly exceeds** the constant-τ binary-collision model.

**Mechanism — DEFINITIVELY the frame capture effect** (dedicated toggle experiment, per Mohamed):

| N=50 broadcast config | goodput Mb/s | note |
|---|---|---|
| equal power (default) | 1.314 | baseline |
| + `SimpleFrameCaptureModel` | 1.314 | **no change** — restart-capture needs a power difference |
| + 12 dB tx-power spread | 1.543 (**+17 %**) | stronger frames win collisions → capture |
| + spread + capture model | 1.543 | same (SINR reception already captures) |
(N=20: spread gives +48 %.) Adding tx-power diversity makes collisions survivable — that IS frame
capture; and the explicit `SimpleFrameCaptureModel` is inert at equal power (it only does
power-based *restart* capture). The large gap that remains at **equal** power is therefore
**timing capture** — NS-3's continuous-time SINR PHY decodes a frame whose colliding frame overlaps
it only partially — which is fundamental to the PHY and not toggleable in stock NS-3.

**Conclusion (no correction):** the no-ACK Bianchi variant is exact for NS-3 broadcast at low
contention (N≤10) and is a **lower bound at high N**; the under-prediction is the **frame capture
effect** (docs/06 §2), demonstrated directly by the power-spread lever. The idealized binary-
collision model omits capture by construction. Both are reported; **no correction factor applied**.
**Unicast — the model's primary use in this thesis — is validated (+1.8…+5.3 %).**

### Mandatory attacks
| attack | finding |
|---|---|
| Saturation reached? | Yes — offered load ≫ delivered; throughput plateaus (unicast) / collapses (broadcast) as N grows. |
| Correct Bianchi variant per mode? | Yes — unicast↔ACK (`solve`), broadcast↔no-ACK (τ=2/(W+1)); never mixed. |
| NS-3 seed handling? | Distinct `RngRun=seed` per run; 10 seeds → bootstrap CI. |
| Runtime < 2 h? | ~4 min for 100 runs. |

### Investigation (Mohamed asked to dig deeper) — CONCLUDED: capture confirmed
Three escalating experiments were run: (1) a direct `PhyTxBegin` success-rate measurement (which
retracted my "18× capture" over-claim — wrong metric + ideal-timing artifact); (2) a
τ-from-channel-idle probe (inconclusive — slot accounting vs NS-3 internals); (3) a **capture
toggle + tx-power-spread experiment** that is **conclusive**: power diversity makes collisions
survivable (+17–48 % goodput), i.e. the high-N over-performance IS frame capture; the residual at
equal power is timing capture inherent to the SINR PHY. So: **unicast validates Bianchi (+1.8…
+5.3 %); broadcast is a capture-limited lower bound at high N, mechanism now identified, no
correction applied.** This is a complete, honest P6b result → recommend tagging `p6-done`.
Contention is exported for E5 regardless.

#### Lesson (kept for integrity)
The first pass back-computed a "~18× capture" from goodput using ideal slot timing, and compared
per-transmission success against per-busy-slot p_s — both wrong. The `PhyTxBegin`/delivered
measurement caught it. This is exactly why Law 6 forbids recording a plausible-looking number
without an independent cross-check; the retraction is left visible.

### Contention export
`results/raw/ns3_contention.csv`: per (N, mode) NS-3 goodput, matching-Bianchi, gap%, and
effective airtime share (goodput / 6 Mb/s) — the input the integrator's E5 consumes.


---

<a id="s9"></a>

## 9. Full project audit — scientific + engineering, pre-P7b (2026-07-05)

*Formerly `docs/audits/full_audit_pre_p7b.md`, last changed 2026-07-28. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

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

### Verdict
The project is **scientifically sound and the headline (T5, 96.4 % auth-byte cut, PASS) is robust.**
One real inconsistency was found and **fixed** (E4/T4 modelled BLS at the stale 48 B instead of the
accepted 96 B); it did not change the T4 conclusion. Six further items are documented below — all are
low-severity, nominal-pending-P7, or methodological notes for P8, none invalidates a result.

### Findings

| # | Sev | Area | Status | One-line |
|---|-----|------|--------|----------|
| F1 | **MED** | E4/T4 crossover | **FIXED** | BLS modelled at 48 B (stale min-sig) vs accepted 96 B; corrected → re-ran E4. |
| F2 | LOW | energy radio term | documented (code note) | uses unicast T_FX 122 µs on a broadcast system (~1 % over-count); reconcile at P7. |
| F3 | LOW | optimizer batch grid | documented | E5 optimum b=28 is grid-quantized; true MTU b_max=31 (96.4 %→96.8 %, PASS either way). |
| F4 | MED | cross-experiment sizes | documented (P8) | record sizes differ (single-seed 68.9 vs 30-seed 66.25 cbor) — random-walk magnitude sampling. |
| F5 | INFO | record schema | documented | 32 B `prev_hash` carried per record (~half of delta's 45 B) — a stated modelling assumption. |
| F6 | INFO | crypto ordering | documented (P7 watch) | ECDSA beats Ed25519 on x86 (OpenSSL asm); likely flips on ARM → may change E5 scheme pick. |
| F7 | INFO | NS-3 broadcast | documented (already in p6) | broadcast gap →1735 % at N=50 is the capture effect; unicast (±5 %) is the quantitative validation. |

#### F1 — E4/T4 used BLS = 48 B (FIXED)
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

#### F2 — energy radio term uses the unicast fixed airtime (documented, P7)
`energy.radio_airtime_s` bills `bianchi.T_FX≈122 µs` (unicast success minus DIFS, includes SIFS+ACK)
per frame, but the telemetry substrate is 802.11 **broadcast** (no ACK; fixed part ≈100 µs). This
over-counts the receiver radio term by ~22 µs/frame ≈ 1 % of E5 energy. Energy is nominal-power and is
re-derived at P7 with the measured meter powers; a code NOTE now flags the reconciliation. The auth-byte
headline is power-free and unaffected. (Left un-refrozen deliberately: changing it now would desync the
code from the tagged E5 CSV for a 1 % nominal-energy tweak.)

#### F3 — E5 optimum batch is grid-quantized (documented)
The E5 batch grid is `[…24,28,32,36,40]`. With delta s=45.0 B, one frame fits `45·b+104 ≤ 1500 ⇒
b_max=31`; the grid jumps 28→32 (32 spans 2 frames ⇒ V<0.95, infeasible), so the reported optimum is
**b=28**, not the true b_max=31. Auth overhead 104/28=3.71 B (reported) vs 104/31=3.35 B (true) → cut
96.4 % vs 96.8 %. **PASS either way**; the headline conclusion is unaffected. For the paper, either
disclose the grid or densify it near the MTU knee.

#### F4 — record sizes differ across experiments (documented, P8)
The absolute encoders (json/cbor/msgpack) encode field *magnitudes*, which drift with the seeded
random walk; delta encodes magnitude-invariant deltas. So the same encoder measures differently by
(seed, n): **verified** cbor = 68.94 B at seed 1/n 10 000 (P1, framesizes, E2, E3) vs 66.25 B at
seeds 1–30/n 1 000 (E1, E5); delta is invariant (45.00 vs 45.00, +0.02 %). Each experiment is
internally consistent, but the cross-experiment absolute sizes are not directly comparable. **P8
recommendation:** report the 30-seed E1 mean±CI as the single headline size table and note per-figure
sizes in captions. Not a bug.

#### F5 — 32 B prev_hash per record (documented assumption)
Every telemetry record carries a raw 32 B `prev_hash` (SHA-256), ~half of delta's 45 B on the wire. It
is carried so each frame round-trips standalone (frame-level self-verifiability). All encoders/experiments
use the same schema, so every relative conclusion holds; the absolute on-air sizes include this 32 B.
State it as an explicit modelling assumption in the paper (records self-carry the chain hash).

#### F6 — ECDSA beats Ed25519 on x86 (P7 watch)
Measured (i5-14400F): ECDSA sign 26.2 µs < Ed25519 29.1 µs; ECDSA verify 78.5 µs < Ed25519 95.0 µs —
the reverse of the usual ordering, from OpenSSL's hand-tuned nistp256 assembly in `cryptography`. This
is why E5's byte-tied optimum breaks toward ECDSA on the energy tiebreak. On RPi4 ARM (no such asm
edge) Ed25519 is likely to reclaim the lead → the E5 scheme pick may flip ECDSA→Ed25519 (both 64 B,
identical auth-byte cut). **Watch at P7b; the headline % cut is unchanged regardless.** Also: ECDSA
verify 78.5 µs is 1.9 % below the doc's 80 µs anchor floor — inside run-to-run noise, not a fault.

#### F7 — NS-3 broadcast gap = capture effect (already in p6.md)
Unicast Bianchi validates to **±1.8–5.3 %** across N=5–50 (excellent). The no-ACK broadcast model is a
conservative lower bound; its gap to NS-3 grows 4.4 %→1735 % (N=5→50) because it assumes *all* colliding
frames are lost, while NS-3's capture effect recovers the stronger frame (confirmed at P6 via the
power-spread experiment; broadcast goodput correctly plateaus ~1.3 Mb/s). Hand-check: at N=50 the model
gives 0.073 Mb/s (τ=2/17, p_s=1.3 %) — internally correct. **Use unicast for the quantitative DCF
validation; present broadcast qualitatively as capture-dominated.**

### Formula conformance (re-derived vs code — all ✓)
- **T1 φ = g/(s+g):** matches [experiments.py:72]; measured φ rises json 25 %→delta 59 % as s shrinks. ✓
- **T2 A = M/(M−H_f−g_a):** matches; A_at_b(b_max)→A within 5 % at MTU 1500 (integer-b slack at small M). ✓
- **T3 V_B=1−p, V_D=(1−p)^n:** matches [optimizer.py:124]; E3 measured V tracks theory. ✓
- **T4 κ*=ΔCPU/ΔRADIO:** matches [crossover.py]; corrected to 96 B (F1). ✓
- **T5 bytes/rec = s+(g_a+H_f)/b (B):** matches [optimizer.py:141]; E5 optimized 45+104/28=48.71 hand-checked. ✓
- **Bianchi DCF:** τ/p_c fixed point + S = P_tr·P_s·8L/E[slot] textbook-correct; damped iteration; residual gate. ✓
- **802.11a airtime:** broadcast (100.33 µs) and unicast (156 µs) kept separate & labelled; no 123 µs mixing. ✓
- **Energy E = P_c·(t_enc+t_sg'+t_vf') + P_r·T_air/b:** hand-checked E5 optimized = 15.72+48.52 = **64.24 µJ** = frozen 64.2318. ✓

### Results — expected vs measured (Law 6)
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

### Engineering attack (✓)
Real KATs present and passing (RFC 8032 Ed25519, Wycheproof ECDSA, Chia BLS); cross-process/SHA
determinism gate; frozen wire vectors; damped-fixed-point convergence guard (never returns non-converged);
input validation on records/energy/crossover; delta encoder is one stateful instance everywhere (the
keyframe pitfall is guarded in micro/framesizes/E1). 90 % line coverage. No engineering defects found;
no mocked data, no skipped asserts, no widened tolerances.

### Open / unsolved (cannot close without hardware or a Mohamed decision)
1. **P7b hardware ground truth** — timings + energy need 4× RPi4 + ⚠️ D5 meter. All energy numbers are
   nominal until then (auth-byte headline is power-free and final).
2. **F6 scheme-pick flip** — only resolvable by measuring Ed25519/ECDSA on ARM at P7b.
3. **F2 broadcast T_FX** — fix during the P7 energy re-run (bundled with measured powers).
4. **F3/F4 precision/consistency** — optional P8 polish (densify batch grid; standardize the size table);
   neither changes a conclusion.

### Actions taken this pass
- **Fixed F1**: crossover.py 48→96 B, 3 tests updated to hand-checked 96 B values, E4 figure tolerant of
  κ*=∞, E4 re-run/re-frozen. 849 tests green.
- **Documented F2** in-code (energy NOTE) + F2–F7 here for the P8 limitations section.


---

<a id="s10"></a>

## 10. Audit — P7b (RPi4 hardware campaign)

*Formerly `docs/audits/p7.md`, last changed 2026-07-29. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Scope: the physical measurement rig (2× RPi4 B, 2× INA219, Arduino meter-host), the hardware micro
timing run, the x86↔ARM comparison, and the energy campaign. Method: T_TEMPLATES §Audit +
§Validate-Results. Started 2026-07-27, agent-executed on Mohamed's rig.

### Rig as built (Path A, hw/RIG.md)
| item | value |
|---|---|
| DUT | **authbc-pi4a**, RPi4 B **Rev 1.5**, Debian 12 bookworm **arm64**, kernel 6.12.93-rpi-v8 |
| link partner | **authbc-pi4b**, RPi4 B **Rev 1.4**, same OS *(⚠️ blocked, see below)* |
| interpreter | pyenv **CPython 3.12.13** on both — matches the x86 baseline 3.12.3 so only the platform varies |
| governor | **performance**, verified on all cores by `provision.sh` |
| meter | 2× INA219 (0.1 Ω), Arduino Uno meter-host, 50 Hz, GPIO17→D2 sync with a 10 kΩ pulldown |
| x86 baseline | Intel i5-14400F (frozen `results/raw/p1_*.csv`) |

**Channel mapping VERIFIED empirically**, not assumed: loading each Pi in turn moved exactly one
channel — pi-A ⇒ ch1 (0x40) +2.76 W, pi-B ⇒ ch2 (0x41); channels distinct.

### ⚠️ pi-B blocked — under-voltage, localised to its last wiring leg (REVISED 2026-07-27, 2nd test)
After Mohamed rewired, a second load test with simultaneous INA219 capture **revises the earlier
"supply is sagging" diagnosis**. Measured at our feed point (the INA219 output):

| | rail under its own 4-core load | draw | clock | throttled |
|---|---|---|---|---|
| pi-A | **4.868 V** (min 4.840) | 2.40 → **5.38 W** (1.105 A) | **1800 MHz** held | `0x0` |
| pi-B | **5.079 V** (sag only 0.020 V) | 2.43 → **3.03 W** (0.597 A) | **600 MHz** | `0x50005` |

**pi-A tolerates 4.84 V at the shunt without tripping; pi-B trips at 5.08 V.** The supply and our
measured feed are therefore *not* the problem — the drop occurs **downstream of the shunt**, in
pi-B's final connection to the board. Its low current (0.597 A vs pi-A's 1.105 A) is a *consequence*
of the 3× clock cut, not evidence of a light load.

Most likely cause: series resistance in that last leg — Dupont jumpers, a breadboard rail, a loose
screw terminal, or a thin USB cable. ~0.6 A across ~0.5–0.75 Ω of contact resistance is enough to put
the SoC below its ~4.63–4.75 V trip point while our shunt still reads 5.08 V. **Actions for Mohamed:**
shorten/thicken that last leg, solder or use a proper connector rather than jumpers/breadboard,
re-seat and tighten the screw terminals, and confirm nothing else feeds pi-B in parallel (a second
supply would also explain the low measured current). Re-run `hw/energy_loop.py --quick`; the
pre-flight now aborts if the board is throttled.

### ⚠️ Original diagnosis (first test, superseded by the above)
pi-B **cannot** be measured in its present wiring. Under a 4-core load its clock collapses
**1800 → 600 MHz** and `get_throttled` reads **`0x50005`** (bit 0 = under-voltage **now**, bit 2 =
throttled **now**). pi-A under the identical load holds 1800 MHz at `0x0`. This is why pi-B's power
delta was only +0.56 W versus pi-A's +2.76 W — the firmware is capping it, so *any* pi-B timing or
energy number would be invalid.

Cause is the 5 V rail sagging under load (shunt burden + wiring resistance): pi-B idles ~0.10 V below
pi-A. **Fix before use:** raise the supply to 5.2 V, shorten/thicken the feed wires, tighten the screw
terminals, and give each Pi its own supply if they currently share one. Consequence: **`p_radio_w`
(which needs the 2-node link) is not yet measured**, so the E5 energy re-freeze is deliberately
deferred rather than done half-measured.

### Results validation (Law 6)

#### R1 — encoded sizes must be platform-independent
- **EXPECTED (stated first):** the encoders are deterministic and integer-only, so ARM sizes must be
  **byte-identical** to x86; any difference is a portability bug, not a platform effect.
- **OBSERVED:** all **12/12** size metrics identical. ✓ Cross-platform determinism confirmed.

#### R2 — crypto timing, x86 → RPi4
- **EXPECTED:** RPi4 5–15× slower (docs/04 §1); `verify ≥ sign` per scheme; BLS-verify ≫ Ed25519.
- **OBSERVED (medians, µs):**

| op | x86 | RPi4 | wall ratio | **cycles ARM/x86** |
|---|---|---|---|---|
| ed25519 sign | 29.1 | 88.1 | 3.03× | **1.16×** |
| ed25519 verify | 95.0 | 259.5 | 2.73× | **1.05×** |
| ecdsa sign | 26.2 | 135.5 | 5.17× | 1.98× |
| ecdsa verify | 78.5 | 326.9 | 4.16× | 1.60× |
| bls sign | 324.6 | 2729.8 | 8.41× | 3.22× |
| bls verify | 1016.5 | 8611.8 | 8.47× | 3.25× |
| bls agg_verify(8) | 3445.4 | 26209.3 | 7.61× | — |

- Ordering gates: `verify ≥ sign` holds for all three schemes ✓; BLS-verify = **33.2×** Ed25519-verify ✓.
- **⚠️ ANOMALY — three ops fall BELOW the 5–15× band** (ed25519 sign/verify, ecdsa verify).
  **Investigated, not averaged away:** normalising by clock (x86 4.7 GHz turbo ÷ ARM 1.80 GHz =
  **2.61× floor**) shows Ed25519 needs only **1.05–1.16× the cycles** on ARM — i.e. it is *as well
  optimised* on ARM as on x86, so its wall ratio necessarily collapses to the clock floor. The ratio
  rises exactly with how much x86-specific assembly a primitive exploits: Ed25519 ≈1.1× cycles,
  ECDSA-P256 1.6–2.0× (OpenSSL's ADX/BMI2 nistp256 path), BLS 3.2× (relic's x86 big-integer paths).
  **Conclusion: the docs/04 §1 "5–15×" anchor is unreachable for a primitive equally optimised on
  both platforms and should be restated per-cycle.** This is a spec-anchor finding, ⚠️ raised to
  Mohamed — the band was **not** silently widened. *(Caveat: the x86 sustained frequency is not
  observable under WSL2, so cycle counts use nominal turbo and are approximate; the ordering and
  magnitudes are robust, the absolute cycle counts are not.)*

#### R3 — F6 CONFIRMED: the scheme order flips on ARM
- **EXPECTED (pre-stated in the pre-P7b audit, finding F6):** ECDSA beats Ed25519 on x86 only because
  of OpenSSL's hand-tuned P-256 assembly; on ARM that edge should vanish and Ed25519 may reclaim the
  lead, flipping E5's byte-tied scheme pick. Both are 64 B ⇒ the auth-byte headline cannot change.
- **OBSERVED:** x86 ECDSA 78.5 µs < Ed25519 95.0 µs; **ARM ECDSA 326.9 µs > Ed25519 259.5 µs**.
  **The order flipped, exactly as predicted, with the mechanism confirmed by the cycle analysis.**
- **CONSEQUENCE:** on the real target platform the co-design optimum selects **Ed25519** — which is
  also the D2 architectural default. **The 96.4 % auth-byte headline is UNCHANGED** (64 B either way).
  A predicted anomaly that reproduced is a strengthened result, and is reported as a finding.

#### R3b — WHY Ed25519 wins on ARM: the three candidate causes, separated
F6 must not be reported as a hardware result until the alternatives are excluded. Tool:
`hw/why_ed25519_wins.py`.

**(b) LIBRARY VERSION — RULED OUT (measured).** Both platforms run byte-identical dependency
versions: `cryptography` **45.0.7**, blspy 2.0.3, cbor2 5.8.0, msgpack 1.2.1; Python 3.12.3 (x86) vs
3.12.13 (ARM), a patch difference only. `cryptography`'s wheels statically bundle their own OpenSSL,
so the crypto backend is the same build on both. *(Remaining check: print
`backend.openssl_version_text()` on ARM to confirm 3.5.2 — pending, pi-A is mid-campaign.)*

**(c) OUR WRAPPER — RULED OUT as the cause (measured + bounded).** There **is** a real asymmetry in
our code: `Ed25519Scheme.sign/verify` are single bare C calls, while `EcdsaP256Scheme` additionally
performs ASN.1 DER encode/decode plus bigint↔bytes conversion **in Python** on every operation
(because the project accounts ECDSA at fixed-width 64 B r‖s, not 70–72 B DER — docs/02 T1). Measured
on x86 that overhead is **1.05 µs, only 1.7 % of ECDSA verify**, and ECDSA wins there *both* wrapped
(62.4 µs) and core-only (61.3 µs) against Ed25519's 83.7 µs.
On ARM the gap to explain is **67.4 µs** (ECDSA 326.9 vs Ed25519 259.5). For the wrapper to cause the
flip it would have to be **64× slower on ARM than on x86**; Python on a Cortex-A72 @1.8 GHz runs
~3–8× slower than on this x86 @4.7 GHz. Even assuming a pessimistic **20×**, ECDSA core-only would be
305.9 µs — **Ed25519 still wins**. The wrapper contributes a low-single-digit percentage and is
reported, but it does not produce the flip.

**(a) HARDWARE — the operative cause, but the MECHANISM IS NOT ESTABLISHED.** What is measured and
solid: normalising out clock speed, ARM needs **1.05× the cycles for Ed25519 but 1.60× for
ECDSA-P256**, so the two primitives are *not* equally portable and the ordering is ISA-dependent.

**⚠️ RETRACTED (2026-07-27): the ADX/BMI2 explanation.** I previously attributed the x86 advantage to
OpenSSL's `ecp_nistz256` assembly exploiting ADX/BMI2 (ADCX/ADOX dual carry chains). **A direct
experiment refutes it.** Masking those features at OpenSSL init:

| `OPENSSL_ia32cap` | ECDSA verify | Ed25519 verify | winner |
|---|---|---|---|
| (none — full features) | 61.10 µs | 85.36 µs | ECDSA |
| `:~0x80000` (ADX off) | **56.75 µs** | 85.10 µs | ECDSA |
| `:~0x180000` (ADX+BMI2 off) | **56.76 µs** | 84.66 µs | ECDSA |

Disabling ADX did **not** slow ECDSA — it got ~7 % *faster*, consistently, and still beat Ed25519.
The mask demonstrably took effect (timings moved and reproduced), so this is not a no-op. Whatever
gives x86 its P-256 advantage, **it is not ADX/BMI2 as I claimed**, and no mechanism is currently
demonstrated. Reported as an open question rather than a plausible-sounding story (Law 6/7).

**Net, defensible claim:** ECDSA-P256 is comparatively less portable than Ed25519 (1.60× vs 1.05×
cycles), so the x86 ordering does not carry to ARM. **On the deployment platform Ed25519 wins**,
consistent with the D2 architectural default. The auth-byte headline is unaffected (both 64 B).

**ARM CONFIRMATION (measured on pi-B, governor=performance, throttled=0x0 throughout).** The bound
above is now replaced by direct measurement:

| | x86 wrapper overhead | ARM wrapper overhead | ARM core-only |
|---|---|---|---|
| sign | ≈0 µs (0 %) | **11.80 µs (8.8 %)** | ECDSA 122.53 vs Ed25519 **89.59** |
| verify | 1.05 µs (1.7 %) | **12.58 µs (3.9 %)** | ECDSA 312.37 vs Ed25519 **263.31** |

The wrapper is ~12× costlier on ARM, in the predicted 3–8×+ range and an order of magnitude short of
the 64× that would have been required. **Ed25519 wins both wrapped AND core-only on ARM, and ECDSA
wins both wrapped and core-only on x86** ⇒ **F6 is a genuine hardware effect, not an artefact of our
code.** The pre-stated bound ("even at 20× the wrapper, Ed25519 still wins") was quantitatively
validated. *Cross-board reproducibility:* pi-B's wrapped ECDSA verify (324.94 µs) matches pi-A's
independent micro-suite value (326.9 µs) to **0.6 %** — two harnesses, two boards.

**Residual note (reported, not corrective):** the wrapper does inflate ECDSA by 4–9 % on ARM. It is a
deliberate modelling choice (64 B r‖s wire accounting, docs/02 T1) and it *disadvantages* the scheme
E5 no longer selects, so it cannot flatter the headline. Deducting it entirely leaves Ed25519 ahead
by 49 µs on verify.

#### R4 — energy rig self-consistency (validation run: 5 s × 2 reps, 3 ops)
`energy/op = ΔP·t_loop/n_ops` is algebraically ΔP·t_op, so that identity is **not** an independent
check. Two genuinely independent checks were run instead:
- **vs the separate micro suite:** energy-loop throughput implies ed25519 sign 92.9 µs / verify
  275.3 µs against the micro suite's 88.1 / 259.5 µs → **+5.4 % / +6.1 %**, the expected small excess
  from the anti-DCE checksum and loop overhead. ✓
- **single-core vs 4-core:** measured single-core ΔP = **0.728 W** (0.704–0.765) versus the 4-core
  stress test's 2.76 W ⇒ **0.690 W/core** — agreement within ~5 %. ✓
- **HEADLINE:** measured **`p_cpu_w` ≈ 0.73 W**, against the **nominal 3.0 W** E5 used — the nominal
  was **4.1× too high**. The full 60 s × 5-rep campaign refines this and the per-op table.

### Engineering findings fixed during bring-up
| # | issue | fix |
|---|---|---|
| H1 | Pi-B flashed 32-bit (`dpkg`=armhf, "Raspbian"); no scipy wheel ⇒ `make setup` died at metadata generation. `uname -m` says `aarch64` even then, so it is not a valid check. | `provision.sh` now aborts on non-arm64 with reflash instructions; live-tested on the 32-bit board |
| H2 | `sudo provision.sh` left `results/hw/meta` root-owned ⇒ `run_micro.sh` failed with Permission denied | provision.sh chowns `results/` back to `$SUDO_USER` |
| H3 | Throttle guard used `!= 0x0`, conflating "now" bits with sticky "since boot" bits, so every run was flagged until reboot | guard now invalidates only if a NOW bit is set or the sticky half **changes during the run**; decodes under-voltage (power) vs thermal and names the fix |
| H4 | Opening the serial port resets the Arduino (DTR); captures began with stale pre-reset samples and a fragment line | capture writes its own canonical header, drops malformed lines, and keeps only the final monotonic `ms` run |
| H5 | **Adjacent sync windows merged** — the inter-window gap was only the `device_state()` calls (~20 ms = one sample at 50 Hz), so 12 windows produced 3 segments | a deliberate `GAP_S = 1.0 s` LOW guard gap before every window (~50 low samples); reducer also trims 5 leading samples per segment to exclude the transition edge |

All five were caught by the tooling's own guards rather than by inspection of the numbers — the
reducer refused to guess an alignment (H5) rather than emit a plausible wrong table.

### Status / remaining
- **Done:** rig verified end-to-end; clean hardware micro run (`p1_*.authbc-pi4a.csv`, no throttle,
  1800 MHz, `0x0`); x86↔ARM comparison; **F6 resolved**; energy chain validated with two independent
  cross-checks; `p_cpu_w` measured.
- **Running:** full energy campaign (8 ops × 5 reps × 60 s) → per-op energy table + refined `p_cpu_w`.
- **Blocked on Mohamed:** pi-B power fix ⇒ `p_radio_w` ⇒ the E5/E4 re-run and re-freeze. Holding the
  re-freeze keeps E5's energy column internally consistent (all-nominal) instead of half-measured.
- **⚠️ For Mohamed:** the docs/04 §1 5–15× anchor (R2) needs restating per-cycle.

### NS-3 broadcast: near-far hypothesis TESTED and REFUTED (2026-07-28)
> **Correction (audit A5, 2026-07-28):** the premise below — that the geometry produced a
> 50.7 dB near-far spread — is **wrong**. NS-3's `LogDistancePropagationLossModel` clamps at
> `distance <= m_referenceDistance` (d0 = 1 m) and the cluster spans 0.49 m, so every link
> always had the *same* 46.68 dB loss. The experiment's conclusion (no near-far advantage) was
> right; the reason is stronger than measured — the spread never existed to begin with.

I hypothesised that the 1 cm-spaced line placement (log-distance n=3 ⇒ a 50.7 dB near-far spread)
manufactured the capture effect blamed for the broadcast gap. Added `--equalPower` to
`ns3/authbc-sat.cc`, which builds the channel explicitly with a path-loss **exponent of 0** so every
link has identical loss — electrically equidistant stations, exactly Bianchi's assumption, capture
impossible. (Note: `YansWifiChannelHelper::Default()` already installs a log-distance model and
`AddPropagationLoss` *chains* models, so the helper must be built from scratch, not amended.)

| broadcast, N=50, 6 s | goodput |
|---|---|
| default (near-far line) | 1.0056 Mb/s |
| **`--equalPower`** | **1.0056 Mb/s — identical** |
| `--powerSpreadDb=20` | 1.4962 Mb/s (+49 %) |

**Result: the hypothesis is refuted.** Equalising path loss changes the outcome not at all, so the
geometry was *not* creating an exploitable near-far advantage. A deliberate 20 dB TX-power spread
*does* raise goodput by 49 %, so capture is real and the simulation responds to power asymmetry —
but our placement was not exercising it.

**Consequence: the broadcast gap remains UNEXPLAINED.** Even with capture made impossible
(equal power), NS-3 delivers ~1.0 Mb/s at N=50 where the analytic no-ACK model predicts 0.073 Mb/s.
Capture therefore cannot be the whole story, and the earlier "capture-limited lower bound" framing is
weaker than stated. Candidate causes still to test: the τ = 2/(W+1) assumption for broadcast backoff
(and W=16 vs the 802.11a aCWmin of 15), and whether the NS-3 goodput normalisation is comparable to
the model's per-slot success definition. `--equalPower` is retained as a permanent experimental
control. **Unicast remains the sound quantitative validation (±1.8–5.3 %); no broadcast claim should
be made until this is resolved.**

### NS-3 rethought: TWO scenarios, because realism and model-validation conflict (2026-07-28)
Making the simulation "realistic" and using it to validate Bianchi are **mutually exclusive goals**.
Bianchi assumes one collision domain, symmetric stations, saturation, no hidden terminals, no
capture. A realistic FANET (UAVs tens–hundreds of metres apart, in 3D, moving) violates every one of
those. Conflating the two is what produced the confused "broadcast gap" narrative. The scenario now
supports both explicitly.

**A — validation (`default` / `--equalPower`).** Idealised: one collision domain, stations
electrically equidistant. Purpose: does our Bianchi implementation match a reference simulator?
Realism is *not* the goal; controlled conditions are. Unicast validates to ±1.8–5.3 %.

**B — deployment (`--realistic`).** Air-to-air UAV links are line-of-sight, so **Friis free-space
(exponent 2)** is correct — not the log-distance **n=3** default, which models cluttered
indoor/urban propagation and, with d₀=1 m, even returns *negative* loss (gain) at the sub-metre
spacings scenario A uses. Nodes are placed on an area-uniform 3D spiral within `--clusterM` (default
150 m) at 50–120 m altitude; `--nakagamiM` adds multipath/airframe fading. Link budget checked:
Friis at 5.18 GHz gives Rx = −70.7 dBm at 100 m and −76.7 at 200 m against ~−82 dBm sensitivity for
6 Mb/s, so links stay viable to ~300 m and break beyond ~500 m (where hidden terminals would appear).

**Measured (broadcast, N=20, 8 s):**

| scenario | goodput |
|---|---|
| validation | 1.390 Mb/s |
| `--equalPower` | 1.390 Mb/s (identical) |
| `--realistic` 150 m | **2.101 Mb/s (+51 %)** |
| `--realistic` 300 m | 1.593 Mb/s (+15 %) |
| `--realistic` 150 m + Nakagami m=3 | 2.026 Mb/s |

**Reading.** Realistic geometry *raises* aggregate goodput because spatial separation lets
concurrent transmissions succeed at different receivers — partial spatial reuse that the
single-collision-domain model cannot represent by construction. Goodput falls again at 300 m as path
loss starts costing frames, and fading costs a few percent. This supports framing the analytic
no-ACK model as a **conservative lower bound for real deployments**, now with evidence rather than
assertion.

**Still open (unchanged):** within scenario A, where capture is impossible and there is no spatial
reuse, NS-3 still exceeds the analytic no-ACK prediction by a wide margin. That residual is *not*
explained by geometry, capture, or propagation, and remains the open question (candidates: the
τ=2/(W+1) broadcast-backoff assumption, W=16 vs 802.11a aCWmin=15, and the goodput-normalisation
definition). **No broadcast claim is made until it is resolved; unicast remains the sound validation.**

---

### F9 — the scenario-A broadcast residual: SOLVED by direct measurement (2026-07-28)

The last open scientific question of P6/P7. Method: instrument NS-3's DCF **access process** and test
Bianchi's *assumptions*, instead of inferring from goodput. New scenario `ns3/authbc-dcf-trace.cc` is
a twin of `authbc-sat.cc` — same channel, MAC, apps and goodput accounting, trace output added — and
its control passed exactly: goodput `1.31376` for N=50/seed=1, **byte-identical** to the then-frozen
matrix, so every trace-derived number below belongs to the same experiment.

#### What was measured (N=50 broadcast, 5 seeds, `results/raw/ns3_dcf_residual.csv`)

| quantity | Bianchi no-ACK | **NS-3 measured** | verdict |
|---|---|---|---|
| busy periods / s | 508.4 | **504.8** | model's channel-time arithmetic is **right** (−0.7 %) |
| mean multiplicity | 5.894 | **4.951** | access rate slightly low (−16 %) |
| **p_s = P(1 tx \| busy)** | **0.0128** | **0.2234** | **17.5× — the whole gap lives here** |
| p_s for *independent* stations at the measured mean | — | 0.0308 | still 7.3× short ⇒ **correlation**, not rate |
| idle slots per busy period | 0.0019 | **0.741** | model off by 386× |
| CW_min / AIFSN (read back from the built objects) | W=16 | **cw_min=15, aifsn=2** | **the model's W was correct all along** |

#### Root cause

Bianchi's virtual-slot abstraction decrements **every** station's backoff counter once per busy
period. Real DCF (IEEE 802.11-2020 §10.3.4.3, and NS-3) does not:

* a station that **just transmitted** redraws its backoff and may draw **0**, transmitting at
  `DIFS + 0` slots;
* a station that **deferred** necessarily holds a counter **≥ 1** — a 0 would already have fired —
  so it can transmit no earlier than `DIFS + 1` slot.

The just-transmitted stations therefore get an **exclusive one-slot head start**. Because broadcast
never ACKs, there is no retry and no CW doubling, so W is *frozen at 16* and this head start becomes
the dominant success channel as collisions come to dominate. When exactly one of the k colliders
redraws 0, it transmits **alone** — a collision *causes* the next period to succeed.

**The trace shows the mechanism directly.** Gap from the end of a collided busy period to the next
transmission:

| next transmitter | n | gap |
|---|---|---|
| **was** in the previous period | 1315 | **34 000 ns = DIFS + 0 slots** (only a redrawing station can be here) |
| was **not** | 2212 | **43 000 ns = DIFS + 1 slot** (hard floor) |

Consequences, all measured: P(next winner ∈ previous period) = **0.3065** vs **0.0993** if the winner
were uniform over N; P(success \| prev collision) = **0.268** vs P(success \| prev success) = **0.067**.

**Closed-form cross-check (Law 6, nothing fitted).** If a collision of k stations is followed by a
success exactly when one of them redraws 0, then P = k·(1/16)·(15/16)^(k−1). At the measured
k̄ = 6.108 that is **0.2745** against **0.2679** measured — **2.4 %**.

#### Third independent implementation (`src/authbc/sim/dcf_ladder.py`)

A slot-process simulator: no PHY, no channel, no packets, just counters — independent of both NS-3
and `models.bianchi`. One boolean, `head_start`, adds or removes exactly the asymmetry above.

| N | Bianchi no-ACK | ladder `head_start=False` | ladder `head_start=True` | **NS-3** |
|---|---|---|---|---|
| 5 | 4.3415 | 4.3197 | 4.3458 | 4.3187 |
| 10 | 3.0360 | 3.0269 | 3.1432 | 3.1198 |
| 20 | 1.3525 | 1.3482 | 1.7894 | 1.7696 |
| 35 | 0.3368 | 0.3366 | 1.2451 | 1.2522 |
| 50 | 0.0728 | 0.0746 | **1.2630** | **1.2729** |

With the head start **removed** it reproduces Bianchi (≤2.5 %); with it **present** it reproduces NS-3
(**≤1.1 %** at every N, and idle-slots-per-busy-period 0.741 vs 0.741 measured). Flipping one boolean
moves the prediction 17× and lands it on the simulator. The mechanism is established, not inferred.

#### The four hypotheses this replaces — all now refuted *by measurement*, not argument

* **capture / near-far** — every one of node 0's 1149 successful decodes came from a
  multiplicity-**1** busy period: **0 % capture**. `--equalPower` is now byte-identical to the default
  (same goodput, same 1149 decodes, same 24321 drops). Drop reasons are `PREAMBLE_DETECT_FAILURE`
  (17 625), `BUSY_DECODING_PREAMBLE` (4 050), `TXING` (2 646) — collisions destroy frames exactly as
  the model assumes.
* **W=16 vs aCWmin=15** — `cw_min=15` read back from the object: W=16 values is correct.
* **goodput normalisation** — total successes over the trace = **1173** = `rx_bytes/(N−1)/L` exactly,
  and successes not from node 0 = **1149** = `rx_ok_node0` exactly. The (N−1) divisor is right.
* **not saturated** — unchanged, still refuted.

#### Why unicast was never affected

With ACKs, colliding stations double CW (16→32→…→1024), so P(redraw 0) collapses and the field
spreads over up to 1024 counter values. The head-start channel is negligible there — which is exactly
why the ACK model validated to a few percent while the no-ACK one failed by 16×.

#### Status of the broadcast arm

The embargo ("no broadcast claim until resolved") is **lifted**: broadcast is now validated
quantitatively against a slot-exact model to **≤1.1 %** across N=5–50. The textbook no-ACK Bianchi
variant is retained in `analysis/figures_ns3.py` and in the figure — labelled as what it is, a model
that **fails by up to 16×** — because the failure is the finding.

⚠️ **For Mohamed (Law 8):** whether docs/02 §6 should be amended to make the slot-exact process the
normative broadcast model (rather than the τ=2/(W+1) no-ACK Bianchi variant) is a spec decision, not
an agent one. The code, figure and CSV now carry both; only the doc is unchanged.

---

### F8 — every NS-3 goodput number was ~5 % high (found while instrumenting F9, FIXED)

`sinkApps.Stop(simTime + 1.5)` outlived `srcApps.Stop(simTime + 1.0)`. Under saturation the MAC
queues are 500 packets deep and keep draining at full channel rate after the sources stop, so 0.5 s
of extra delivery was credited to `rx_bytes` while the goodput denominator stayed `simTime`. The
trace made it unmissable: traffic spans **1.001 → 11.501 s = 10.5 s**, divided by 10 s ⇒ **+4.76 %**.

Fixed in both scenarios (sinks now stop **with** the sources) and the matrix deliberately re-measured.
The correction is uniform, as a pure denominator error must be:

| | N=5 | N=10 | N=20 | N=35 | N=50 |
|---|---|---|---|---|---|
| broadcast | −4.74 % | −4.82 % | −4.50 % | −5.21 % | −4.74 % |
| unicast | −4.80 % | −4.76 % | −4.84 % | −4.91 % | −4.99 % |

**This improves the thesis's channel validation.** The unicast↔ACK-Bianchi agreement — the result the
optimizer's airtime model actually rests on — tightens from **+1.8…+5.3 %** to **+0.08…−3.31 %**. The
old "±5 %" was mostly this bug, not model error.

#### Re-freeze performed (deliberate, Law 7)
`results/raw/ns3_matrix.csv` re-measured (100 runs, F8-corrected); `ns3_contention.csv` and
`fig_ns3_bianchi.png` re-derived; new artifact `results/raw/ns3_dcf_residual.csv` (50 runs).
Gates: `ruff` clean, **901** fast tests, **10** frozen-reproduction checks green.

---

## NS-3 simulation audit — deep review of scenario, drivers and comparison (2026-07-28)

Scope: `ns3/authbc-sat.cc`, `ns3/authbc-dcf-trace.cc`, `ns3/run_matrix.py`, `ns3/dcf_residual.py`,
`src/authbc/sim/*`, and the model↔simulator comparison in `analysis/figures_ns3.py`. Method:
attack as an engineer (silent failures, accounting, determinism) **and** as a scientist (does the
scenario measure the quantity the model predicts?), with expected values stated before measuring.
Everything below is measured from PHY traces, not argued.

### Defects found and FIXED

| # | defect | impact | fix |
|---|---|---|---|
| **A0** | `TraceConnectWithoutContext` returns `bool`; its value was ignored for all 6 trace hooks in `authbc-dcf-trace.cc`. A wrong trace name connects **nothing** and still yields a file that looks like a valid measurement. | latent — all names were correct, so no result was affected | every connection now aborts on a false return. *(`authbc-sat.cc` was already safe: `Config::ConnectWithoutContext` is `NS_FATAL_ERROR` on no-match.)* |
| **A1** | Airtime modelled as continuous `8N/R`. A real 802.11a PHY sends whole 4 µs OFDM symbols and adds SERVICE+TAIL, and the MAC adds LLC/SNAP. **Measured: data frame 1940 µs vs model 1932 µs (0.41 % short); ACK 44 µs vs model 38.67 µs (12.1 % short).** | the model was compared against a PHY it did not describe | added exact `ofdm_ppdu` / `t_success_exact` / `t_collision_exact` / `t_broadcast_exact`, pinned by test to the measured 1940/44 µs, and `solve()` gained `t_s`/`t_c` overrides. The NS-3 comparison now uses them. **The docs/02 §6 constants are untouched** — they feed `models.energy` and the frozen E5 column (see ⚠️ below). |
| **A7** | The head-start statistic picked `nodes[0]` as "the winner" even when the next busy period was itself a collision — i.e. an arbitrary choice of the lowest-numbered simultaneous starter, in **78 %** of transitions at N=50. | the reported effect was **diluted**: 3.1× instead of 7.6× | restricted to pairs with an unambiguous winner. **Corrected result: 96.45 % of clean winners were previous participants vs 12.72 % uniform — a 7.58× enrichment.** |
| **A11** | `ns3_dcf_residual.csv` mixed measurement windows: `p_s`/`busy_per_s` from the guarded steady-state window, `goodput_mbps` from the scenario's full `[1, simTime+1]`. `p_s × busy_per_s × 8L` therefore did **not** reproduce the row's own goodput (−1.13 % at N=50). | ~1 % of spurious model-vs-simulator disagreement | added `goodput_window_mbps` (+ `window_s`, `idle_slots_per_busy`, `winner_enrichment`) computed from the same busy periods; the row is now self-consistent and the gate checks it. |

### Corrections to the written record

**A5 — the "50.7 dB near-far spread" never existed.** Both the scenario comment and
docs/audits/p7.md claimed the 1 cm-spaced line under log-distance n=3 produced a ~50 dB near-far
spread that could manufacture capture. It cannot: NS-3's `LogDistancePropagationLossModel` **clamps**

```
if (distance <= m_referenceDistance) return txPowerDbm - m_referenceLoss;
```

with d₀ = 1 m, while the whole cluster spans 0.49 m — so **every link always had the identical
46.68 dB reference loss**. The default channel was equal-power by construction. Verified: goodput is
**byte-identical** with and without `--equalPower` at N=5/20/50 in *both* modes. The earlier
experiment's conclusion (no near-far advantage) was right; the true reason is stronger than what was
measured. Corrected in `authbc-sat.cc` and in the superseded audit section.

### Verified correct (no change needed)

| # | check | result |
|---|---|---|
| **A2** | slot-time accounting | measured cycle **1980.66 µs** = 1974 (DATA+DIFS) + 0.741×9 (idle) — exact |
| **A3/A6** | saturation and warm-up | all 50 stations backlogged; p_s is at steady state within **~200 ms** of the sources starting, so the 10 s window carries no meaningful transient |
| **A4** | channel errors | `rx_begin == rx_ok` **exactly** in both modes ⇒ **zero** noise/SNR losses. Every frame loss is contention (`PREAMBLE_DETECT_FAILURE`, `BUSY_DECODING_PREAMBLE`, `TXING`), which is precisely the model's premise |
| **A9/A10** | unicast timing | SIFS **16 000 ns**; post-success gap floor **94 µs** = SIFS+ACK+DIFS; post-collision floor **43 µs** = DIFS+slot. ACK count matches the single-transmitter period count |
| **A12** | goodput accounting | the scenario's `goodput_mbps` equals trace successes × 8L / simTime to **0.00 % on every seed** — an independent proof that the `(N−1)` divisor and delivery accounting are exact |
| **A8** | unicast fairness | per-station transmission CV = **30 %** (broadcast 14.6 %). Tested for a scheduler artifact and found none: low/high-half ratio scatters 0.93–1.09 and cross-seed rank correlation is ≈0 (−0.16…+0.13). This is genuine DCF short-term unfairness from binary exponential backoff — a real 802.11 property, and a **stated limitation** of comparing against Bianchi's symmetric-station idealisation |

**A10 also confirms F9's explanation of why unicast is immune:** the head-start channel exists there
too, but is ~13× rarer (30 DIFS+0 starts vs 1069 DIFS+1) because colliding stations back off into a
doubled window.

### Result of the audit

With the exact airtime and the window-consistent comparison, the slot-exact model now matches NS-3's
broadcast measurement to **≤0.40 %** at every N (previously ≤1.14 %), and the idle-slot occupancy to
**≤0.7 %**:

| N | NS-3 (window-consistent) | slot-exact | gap | p_s NS-3 | p_s model | gap | idle/busy NS-3 | model |
|---|---|---|---|---|---|---|---|---|
| 5 | 4.3369 | 4.3305 | +0.15 % | 0.7712 | 0.7698 | +0.18 % | 1.8900 | 1.8930 |
| 10 | 3.1385 | 3.1321 | +0.20 % | 0.5564 | 0.5551 | +0.23 % | 1.2140 | 1.2230 |
| 20 | 1.7758 | 1.7830 | −0.40 % | 0.3143 | 0.3156 | −0.40 % | 0.9169 | 0.9208 |
| 35 | 1.2407 | 1.2407 | **0.00 %** | 0.2195 | 0.2195 | +0.02 % | 0.8012 | 0.8006 |
| 50 | 1.2631 | 1.2585 | +0.37 % | 0.2234 | 0.2226 | +0.39 % | 0.7409 | 0.7410 |

Unicast against ACK-Bianchi with exact OFDM airtimes: **+0.6, +0.8, +0.6, −1.4, −2.9 %** for
N=5…50. The residual at high N is not airtime — it is Bianchi's own decoupling approximation plus
the 30 % short-term unfairness above, both now quantified rather than absorbed.

⚠️ **For Mohamed (Law 8) — one spec question this audit raises.** `docs/02 §6` models airtime as
continuous `8N/R` with a 34 B MAC overhead. The real 802.11a PHY is symbol-quantised and the real
overhead is 36 B (LLC/SNAP 8 + MAC header 24 + FCS 4), making the doc's airtime **0.41 % short**.
Those constants feed `models.energy` and hence the frozen E5 energy column, so I did **not** change
them — a ~0.4 % shift in the reported energy is your call, not mine. The auth-byte headline is
byte-based and unaffected either way. The NS-3 comparison already uses the exact form.

---

### F9 — REFRAMED after locating the literature (2026-07-28, same day)

**The mechanism reported above is not new. It was published in 2007–2008 and we rediscovered it.**
This section supersedes the framing of the F9 write-up, not its measurements — every number stands.

#### What the literature already had

* **X. Ma and X. Chen, "Saturation Performance of IEEE 802.11 Broadcast Networks," IEEE
  Communications Letters, vol. 11, no. 8, pp. 686–688, Aug. 2007, doi:10.1109/LCOMM.2007.070040**
* **X. Ma and X. Chen, "Performance Analysis of IEEE 802.11 Broadcast Scheme in Ad Hoc Wireless
  LANs," IEEE Trans. Veh. Technol., vol. 57, no. 6, pp. 3757–3768, Nov. 2008,
  doi:10.1109/TVT.2008.918731**

They name the mechanism the **backoff counter Consecutive Freeze Process (CFP)** and state the
unicast/broadcast asymmetry exactly (2008 §II-C, verbatim):

> "In unicast, CFP may happen only after a station just successfully transmitted a packet… the
> involved transmitters must wait for ACK/CTS timeout… **In broadcast, CFP could happen either
> after a successful transmission or after a failed transmission**… it possibly selects zero as
> its new backoff time and **thus monopolizes the channel**… This leads to a more frequent
> occurrence of CFP in broadcast than that in unicast."

Their abstract also warns against precisely the error this project made:

> "analytical models for saturation performance evaluation of IEEE 802.11 unicast communication
> **cannot simply be reduced** for the analysis of broadcast service."

The unicast counterpart is **I. Tinnirello, G. Bianchi, Y. Xiao, IEEE TVT 59(3):1055–1067, 2010**
("anomalous slots"), whose abstract states the post-success slot is accessible only to the station
that just transmitted and the post-collision slot to nobody — both of which our unicast traces
independently confirm (94 µs floor taken 220×; only 30/1099 taking the post-collision slot).

#### Their closed form against our measurement — nothing fitted

> ⚠️ **Annotated 2026-07-29.** Two small corrections to this table's summary, both verified by
> re-measurement: the stated "≤0.36 % on every quantity" is optimistic — the **idle/busy column
> reaches +0.75 % at N=10**, visible in the row below. And on **ns-3.48** the bound widens to
> **≤2.49 %** (p_s at N=35). The measurements themselves reproduce exactly and are independent;
> a claim to the contrary (audit F15) was raised and **retracted** the same day.

| N | p_s model | p_s NS-3 | err | idle/busy model | NS-3 | err | S model | S NS-3 | err |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.7703 | 0.7712 | −0.12 % | 1.8934 | 1.8900 | +0.18 % | 4.3329 | 4.3369 | −0.09 % |
| 10 | 0.5551 | 0.5564 | −0.23 % | 1.2232 | 1.2140 | +0.75 % | 3.1319 | 3.1385 | −0.21 % |
| 20 | 0.3154 | 0.3143 | +0.36 % | 0.9205 | 0.9169 | +0.39 % | 1.7823 | 1.7758 | +0.36 % |
| 35 | 0.2195 | 0.2195 | −0.02 % | 0.8008 | 0.8012 | −0.05 % | 1.2407 | 1.2407 | −0.00 % |
| 50 | 0.2227 | 0.2234 | −0.31 % | 0.7413 | 0.7409 | +0.07 % | 1.2595 | 1.2631 | −0.29 % |

**≤0.36 % on every quantity at every N.** Their model also agrees with our own slot-exact simulator
(written before the paper was found) to <2 % on ns-3.41 and <2.7 % on ns-3.48 (worst N=35). Note their τ_s = 2/W₀ = 0.125; our discarded
reduction used 2/(W+1) = 0.1176, so even that constant was wrong.

#### What is still ours, stated conservatively

1. **Independent validation in an untested regime.** Ma & Chen's numerical study used W₀ = 32 and
   128 at 1 Mb/s. We validate at **W₀ = 16, 802.11a, 6 Mb/s** — the worst case, since they conclude
   CFP matters most "as the backoff window size is relatively small comparing with the number of
   stations."
2. **Direct measurement of the mechanism, not just the curve.** They validated throughput and
   delivery ratio against their own simulator. We measured the microscopic fingerprint in NS-3: the
   **34 µs vs 43 µs** deferral split, the **7.58×** winner enrichment, and
   P(success | prev collision) = 0.268 against a hand formula's 0.2745.
3. **A reproduced non-obvious prediction.** Broadcast throughput is **non-monotonic in N** —
   it bottoms out near N≈40 and rises again as the freeze process takes over. NS-3 measures the
   reversal (1.2407 Mb/s at N=35 → 1.2631 at N=50) and the model predicts it; the naive reduction
   decays monotonically and cannot.

**No novelty is claimed for the mechanism.** Any such claim would be misattribution.

#### Consequences applied

* `models/broadcast_dcf.py` implements Ma & Chen (eqs. 5–12), cited, with the letter's eq. (6)
  misprint noted; `naive_reduction_mbps` retained only as the labelled failure.
* `analysis/figures_ns3.py` now compares broadcast against Ma & Chen and plots the naive reduction
  as an explicit failure curve. `ns3_contention.csv` columns renamed accordingly.
* `sim/dcf_ladder.py` retained as an independent cross-check — three implementations now agree.
* docs/02 §6 gains a normative **§6a broadcast** section with the equations and all four citations.

#### Process finding (Law 5, worth more than the result)

The failure was not choosing Bianchi — the unicast model is right and validates to ±3 %. It was
**deriving a broadcast variant in-house without checking the literature**, and the published work
warns against that exact reduction in its abstract. Before P8, every model in docs/01–02 should be
checked for whether it is cited or home-derived.

---

### Deployment-geometry sensitivity — the "conservative lower bound" claim, measured (2026-07-28)

The thesis previously asserted that the idealised single-collision-domain model is a *conservative
lower bound* for real deployments. That assertion is now **measured and bounded**, and it turns out
to hold only over a finite range. Artifact: `results/raw/ns3_sensitivity.csv`, driver
`ns3/sensitivity.py` (`make sim-ns3-sensitivity`), N=20 broadcast, 3 seeds, 10 s, L=1400 B.

| scenario | goodput | vs controlled |
|---|---|---|
| **controlled** (co-located, one collision domain) | 1.7752 Mb/s | — |
| realistic, 50 m cluster | 2.5370 | **+42.9 %** |
| realistic, **150 m** cluster | 2.6768 | **+50.8 %** (peak) |
| realistic, 300 m cluster | 2.0223 | +13.9 % |
| realistic, **500 m** cluster | **1.4964** | **−15.7 %** |
| realistic 150 m + Nakagami m=3 (strong LoS) | 2.5912 | +46.0 % |
| realistic 150 m + Nakagami m=1 (Rayleigh) | 2.4391 | +37.4 % |

**Reading.** Spreading the formation *raises* aggregate goodput, because concurrent transmissions
succeed at different receivers — spatial reuse, which a single-collision-domain model cannot
represent by construction. The benefit peaks near a 150 m cluster and then decays as path loss
starts costing frames.

**The finding that matters: the bound is not unconditional.** At a **500 m** cluster the controlled
model becomes **optimistic by 15.7 %**, not conservative — links begin to break and hidden terminals
appear, and neither analytic model represents either. So the honest statement is:

> the idealised model is a conservative lower bound for clusters up to roughly 300–400 m, and
> becomes an *over*-estimate beyond that.

Fading costs a few points and does not change the picture: strong-LoS Nakagami m=3 costs ~5 points
against the fading-free case, Rayleigh m=1 costs ~13.

**Does this move the thesis's chosen configuration? No.** The optimizer selects on bytes (channel
independent) with energy as the tie-break, and energy depends on per-frame airtime rather than on
contention. `ns3_contention.csv` has no code consumer. So the co-design optimum is unchanged; what
this study bounds is how far the *channel-level* prediction transfers to a deployment.


---

<a id="s11"></a>

## 11. Scientific-implementation audit

*Formerly `docs/audits/scientific_implementation_audit.md`, last changed 2026-10-06. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*Requested by Mohamed 2026-08-05: "fix all things with correct scientifically correct
implementation, then audit the whole project from the scientific implementation point of view."*

**Scope.** Not a code-quality review and not a re-check of the arithmetic — `docs/audits/model_provenance.md`
already carries F1–F37 for formula conformance. This asks a narrower and harder question:

> **Does each number in this project measure the thing it is claimed to measure?**

Every finding below is backed by a command that was run, not by inspection alone. Where a check
*passed*, the evidence is recorded too — a clean result is only useful if you can see what was tested.

---

### 1. Defect taxonomy — the classes this project actually produces

Five distinct ways a plausible number has turned out wrong here. The first two were already known;
**S3 is new in this pass** and is the most consequential.

| class | mechanism | instances |
|---|---|---|
| **C1 — small-sample mean vs a threshold** | too few seeds; the mean lands on the wrong side | four headline numbers (F26, F30); `N_max` 5→3; delay crossing 2.797→2.435 |
| **C2 — an unverified constant on the measurement path** | the rig did not do what the config said | 2.4 GHz broadcast basic rate (F35). ⚠️ σ was 0.196 pp over 8 windows — **repeatability did not protect against it** |
| **C3 — a threshold applied to a mean instead of to the distribution** | the criterion answers a different question from the one asked | **S3 below — `N_max`** |
| **C4 — a configuration change that perturbs the random realisation** | comparison arms differ in bookkeeping, not just physics | RNG stream displacement (F36/F37) |
| **C5 — a claim wider than the experiment supports** | the measurement is sound; the sentence around it is not | 2-node hardware ≠ Ma & Chen validation (F35); F18 retraction |

**More seeds only fixes C1.** C2–C5 are immune to sample size, which is why "we ran 30 seeds" is not
by itself a statement of correctness.

---

### 2. S3 (MAJOR, new) — `N_max` applies its acceptance test to a mean, and V is a reliability target

#### The finding

`run_lora_capacity.py` accepted an N when the **mean delivered fraction across seeds** met V ≥ 0.95.
The published `N_max = 3` rests on this row of `lora_capacity.csv`:

```
n=2   delivered=0.97166   seeds_failing_v = 8/30    meets_v=1
n=3   delivered=0.95981   seeds_failing_v = 9/30    meets_v=1
```

**At N = 3, nine of thirty runs fail the very criterion being certified.** V is a *verifiability /
reliability* target. A network that delivers ≥95 % "on average" while 30 % of realisations fall below
it does not meet a 95 % reliability requirement in any operational sense — the mean is answering a
throughput question, not the reliability question the paper asks.

#### Re-derived with both criteria and a bootstrap interval

```
N_max (mean V >= 0.95)             = 3
N_max 95 % bootstrap CI            = [2, 3]     <-- KNIFE EDGE, do not quote bare
bootstrap distribution             = {1: 0.013, 2: 0.188, 3: 0.796, 5: 0.003}
N_max (>= 95 % of individual runs) = 1          <-- DISAGREES with the mean criterion
```

Artifact: `results/raw/lora_capacity_ci.csv`.

**Two things follow, and both matter:**

1. **`N_max = 3` was never a point estimate the data supported.** Its 95 % CI spans [2, 3]; 18.8 % of
   bootstrap replicates return 2. It must be quoted as **3 (95 % CI [2, 3])**.
2. ⚠️ **Under a per-realisation reading, the LoRa arm admits ONE node.** The mean and reliability
   criteria differ by 3×.

This is **independent of**, and points the same way as, the already-recorded result that composing
with Zirak's measured link loss leaves V ≥ 0.95 admitting no multi-node network (`CLAUDE.md`). Two
unrelated routes reaching the same conclusion is a strong signal, not a coincidence.

#### Fixed

`run_lora_capacity.py` now computes and prints **both** criteria plus the bootstrap CI, emits
`seed_pass_frac` and `meets_v_strict` per row, and records `n_max_ci95` / `n_max_is_knife_edge` /
`n_max_strict_criterion` in the provenance header. ⚠️ **Which criterion the paper quotes is
Mohamed's decision (Law 8)** — both are defensible, they answer different questions, and the honest
move is to report both and say which one the headline uses.

#### New machinery, with tests

`authbc.bench.stats.threshold_crossing_ci` — a nonparametric bootstrap for "largest N whose mean
still meets a threshold". A crossing is discrete and non-linear in the sample, so unlike a mean it
does not get an interval for free. `tests/test_threshold_crossing_ci.py` (10 tests) pins the
behaviour, including the knife-edge and single-outlier cases that motivated it.

⚠️ **A criterion I got wrong first, kept visible.** `is_knife_edge` originally asked whether the
point estimate held a *majority* of replicates. That passed a **56/44** split as settled, which is
plainly not settled. The defensible criterion is whether the 95 % CI is degenerate: if it spans more
than one candidate, the data do not distinguish them and a bare number misleads.

---

### 3. S4 (MODERATE, new) — the delay driver reported 30-seed means with no dispersion at all

After F30 the project's standard became "drivers default to 30 seeds and emit min/max/σ".
`run_matrix.py` and `run_lora_capacity.py` were brought up to it; **`run_delay.py` was not.** It
emitted `delivered_frac` as a bare 30-seed mean — and the **U ≈ 2.435 crossing that produces the
swarm-size figures is a threshold applied to exactly that column**, i.e. class C3 again, with the
distribution not even visible to a reader.

**Fixed:** now emits `delivered_min`, `delivered_max`, `delivered_stdev`, `seeds_failing_v` and
`delay_mean_stdev_ms`, and prints the range and failure count per rate. Re-derived as
`results/raw/ns3_delay_ci.csv`.

---

### 4. S5 (checked, CLEAN) — are the project's other comparisons confounded by RNG displacement?

F37 found that installing a mobility model shifts every sender's RNG stream, because ns-3 allocates
stream indices by object-creation order. That defect class threatens **any** comparison whose arms
construct different objects. The published comparisons were therefore tested rather than assumed.

**The invariant used:** `sent` counts *transmissions*. None of these options can physically change
how many packets a device transmits — they act on propagation, gateway configuration, or collision
resolution, all of which affect *reception*. So for a fixed seed, `sent` must be identical.

| axis | published in | `sent` | verdict |
|---|---|---|---|
| `channelModel` ideal vs shadowing | F25 | 323 vs 323 (**and received 249 vs 249**) | **clean** |
| `gwRegion` aloha vs eu | E9 | 323 vs 323 | **clean** |
| `interferenceMatrix` aloha vs goursaud | A2 | 323 vs 323 | **clean** |
| `txJitter` 1.0 vs 0 | E13/F32/F33 | 323 vs 325 | **not comparable this way** — selects a different sender *class* (`JitteredSender` vs the module's `PeriodicSender`), so a different `sent` is expected. Handled distributionally over 30 seeds instead, which is the right treatment |

**So F25, E9 and A2 are not confounded.** The structural reason the mobility case differed:
`GaussMarkovMobilityModel` creates its random variables **at install time, before the senders are
constructed**, whereas the shadowing and gateway models do not.

**Made permanent:** `make verify-rng-isolation` (`ns3/verify_rng_isolation.py`) asserts the invariant
on every axis and fails loudly with the reason if it is ever violated.

---

### 4b. S7 (MAJOR, new) — `make sim-ns3-delay` does not reproduce its own artifact

The committed `results/raw/ns3_delay.csv` sweeps rates **1 2 3 5 7 9 12 15 20 30 40 60**, reaching
U = 6.69. The driver's default `--rates` were **1 2 3 5 7 8 9 10 12**, topping out at **U = 1.34**.

**So the documented entry point produced a different file from the committed artifact — and one
that cannot contain the headline crossing.** The paper quotes the V = 0.95 crossing at **U ≈ 2.44**;
a default run stops at 1.34, well short of it. Anyone reproducing from `docs/05` would get a CSV
that silently omits the region the claim lives in.

⚠️ **Related, and worth stating in the paper:** U ≈ 2.435 is an **interpolation** between two
measured rows — U = 2.2299 (delivered 0.96246) and U = 3.3448 (0.89479). Interpolating between
bracketing measurements is legitimate, unlike extrapolation, but it is not itself a measured point
and should be labelled as interpolated.

**Fixed:** the driver's defaults are now the rates that generated the artifact, with a comment
saying why they must not be narrowed again.

**Re-derived with dispersion** (`results/raw/ns3_delay_ci.csv`). The delay arm turns out to be
well behaved where the LoRa arm was not — through U = 1.338 the spread is tight and at most
**1 of 30** seeds falls below V, so unlike S3 this crossing is not a knife edge in the swept region.

---

### 4c. S3b (MAJOR, new) — the U crossing has the SAME defect as `N_max`, and it moves the headline

The full-range re-derivation (`results/raw/ns3_delay_ci.csv`, 12 rates x 30 seeds) makes the
dispersion visible for the first time:

| fps | U | mean delivered | min | max | seeds failing V |
|---|---|---|---|---|---|
| 12 | 1.338 | 0.98435 | 0.93925 | 0.99925 | **1 / 30** |
| 15 | 1.672 | 0.97814 | 0.94421 | 0.99639 | **1 / 30** |
| **20** | **2.230** | **0.96246** | 0.92842 | 0.99378 | ⚠️ **10 / 30** |
| 30 | 3.345 | 0.89479 | 0.82494 | 0.94367 | 30 / 30 |

**At U = 2.23 the mean (0.9625) clears V ≥ 0.95 while a third of the runs fail it.** This is exactly
S3 in the 802.11 arm: the crossing that yields the headline swarm capacities (**31→100** compliant,
**88→213** relaxed) is a threshold applied to a mean whose distribution straddles it.

* **Mean criterion:** crossing at U ≈ 2.435 (interpolated) — the published value.
* **Per-realisation criterion** (≤5 % of runs may fail): the crossing is bracketed by
  **U ∈ (1.672, 2.230]** — at U = 1.672 only 1/30 fails, at U = 2.230 ten do.

So the strict crossing is at most **~69 %** of the quoted one, and the V ≥ 0.95 capacity figures
would fall by roughly a third.

#### ✅ The adopted operating point is NOT affected — and that is the important part

The 3GPP-compliant point sits at **U = 1.39** (B8). At U = 1.338 only **1 of 30** seeds falls below
V, and every rate up to U = 1.672 behaves the same. **The operating point the thesis actually adopts
is comfortably inside the safe region under either criterion.** What moves is the *maximum* capacity
claim, not the configuration being proposed.

The delay arm is also markedly better behaved than the LoRa arm: 0/30 failures up to U = 0.557 and
≤1/30 through U = 1.672, where LoRa was already failing 8/30 at N = 2.

---

### 5. S6 (MINOR) — three raw CSVs carry no provenance header

Law 7 requires raw CSVs to carry config-hash + environment headers. Missing on:

| file | assessment |
|---|---|
| `ns3_smoke.csv` | **real gap.** Generated by `ns3/sim_ns3.sh`, which writes no `#` header |
| `lora_phase_artifact_eu_30seed.csv` | **real gap.** Stores good per-seed rows, no header |
| `ns3_contention.csv` | ⚠️ **correctly headerless — do not "fix" it.** It is *derived* deterministically from `ns3_matrix.csv`, and its frozen test compares `read_text()` **exactly**. Adding an `env_block` header (which contains cpu and platform) would make that test **pass on this machine and fail on any other** — converting a reproducibility guarantee into a machine lock-in. If provenance is wanted here it must be the *source artifact's* hash only, with no machine-specific fields, and the test left comparing full text |

That last row is itself an audit finding: **provenance headers and exact-text reproducibility tests
are in tension**, and the resolution differs for raw vs derived artifacts. The other frozen CSVs are
safe because `_frozen_body()` strips `#` lines before comparing.

---

### 6. Verified good — practices worth not regressing

| practice | evidence |
|---|---|
| **Per-seed raw data retained, not just summaries** | `ns3_matrix.csv` stores 30 rows per (N, mode); `lora_phase_artifact_*.csv` likewise. This is the gold standard — it let the validation bands be re-derived at 30 seeds without re-simulating, and it is what makes any future re-analysis possible |
| **First-failure crossing rule** | A4's fix (`if ok and not failed_yet`) is present in `run_lora_capacity.py` and is now mirrored in `threshold_crossing_ci`, so the bootstrap cannot disagree with the driver |
| **Stated-in-advance predictions** | the practice that caught C2 on the hardware rig, and that the mobile scenario's two property checks now enforce mechanically rather than by discipline |
| **Retractions kept visible** | T7, F15, F18 remain in the register with the reasoning. This is rarer than it should be and is worth preserving |

---

### 7. Open, with precise next actions

| # | item | action |
|---|---|---|
| **O1** | ⚠️ Which `N_max` criterion the paper quotes (mean vs per-realisation) | **Mohamed's decision.** Both are computed and emitted; the paper must state which and why |
| **O2** | `p = 0.05` has no sensitivity analysis | The 802.11 envelope (`N_max` 100/213) is analytic in `p`, so it carries no seed uncertainty — but all of its uncertainty is inherited from `p`. Sweep it (Tier 2 #5). Hardware now bounds the optimistic end at 2.3 × 10⁻⁴ (F35) |
| **O3** | `ns3_smoke.csv`, `lora_phase_artifact_eu_30seed.csv` lack headers | Add `env_block` + `config_hash` to their generators and re-derive. Safe: neither is compared by exact text |
| **O4** | Unicast −1.4…−2.6 % small-frame bias | Still unexplained; anomalous-slot (Tinnirello) remains an untested hypothesis, and is labelled as such |
| **O5** | ✅ **FIXED** — `channel_utilisation` returned exactly 0.0 at N=1 | It conflated *contention* with *utilisation*: a lone sender does not collide but still occupies airtime, and U = 0 declared a single node able to carry unbounded traffic. Ma & Chen already handles n = 1 correctly (1793.72 frames/s at 288 B, matching the closed form `1/(t_broadcast + (W−1)/2·slot)` — an independent cross-check), so the special case was removed. ⚠️ A unit test **asserted the defect** (`"a lone sender never contends"`); it has been corrected with the reasoning kept visible. Latent until S3 began reporting N = 1 |

⚠️ **O5 is the kind of thing this audit exists to catch:** a defect that was harmless yesterday
became relevant the moment another number moved — and it was *protected by a passing test* that had
encoded the wrong behaviour as intended behaviour. A green suite is evidence that the code does what
the tests say, not that the tests say the right thing.

---

### 7b. Second pass (2026-08-06) — Mohamed: "report both, headline the mean" + execute all fixes

#### A. The paper contradicted itself, and the V column was never generated

`tab:envelope`'s $V{\geq}0.95$ column was **hand-written in LaTeX**. When F30 corrected the crossing
2.797 → 2.435 the prose was updated to 213/100 but the table kept **233/116**, and two further rows
(A+CBOR@50/100, optimized@20/100) existed in the table with no generator at all.

**Fixed properly rather than patched:** every column is now derived by `_n_max_envelope` at four U
ceilings, and `tests/test_paper_matches_artifacts.py` **parses the LaTeX table and compares it to
the CSV**, so the two cannot diverge again.

**The load-bearing claim survives the criterion change** — which is what had to be checked before
adopting "report both":

| criterion | compliant | relaxed |
|---|---|---|
| U < 1 | 1.94× | 3.22× |
| V ≥ 0.95 (mean) | 3.23× | 2.42× |
| V ≥ 0.95 (per run) | 2.67–3.14× | 2.51–3.02× |

Every ratio lies between **1.94×** and **3.23×**, i.e. the quotable range is **1.9–3.2×**. ⚠️ Two published ratios were also stale (3.31→**3.23**,
2.24→**2.42**), so the four-number list in the status board needed correcting too.

#### B. `p` sensitivity (O2) — the constant is not load-bearing, but it sits on a boundary

`analysis/sensitivity_p.py`, 16 points from the hardware measurement (2.3 × 10⁻⁴, F35) to 0.20:

* **The selection never changes.** `delta / ed25519 / B, b = 4, 71.998 B/rec` at **every** feasible
  p. One distinct selection across the whole grid, so the unsourced `p = 0.05` is *not*
  load-bearing.
* ⚠️ **Feasibility collapses at p > ε, identically.** At p = 0.051 *nothing* is feasible. This is an
  identity, not a finding: placement B attains V = 1 − p and D gives (1 − p)ⁿ ≤ 1 − p, so the best
  achievable V is 1 − p and `V ≥ 1 − ε ⟺ p ≤ ε`. With p = ε = 0.05 the adopted point has **zero
  margin in the model** — a property of the *requirement*, not a defect in the design, and the
  hardware measurement puts the real link ~200× inside it.

#### C. Provenance (S6) — and two worse things found while fixing it

* `ns3_smoke.csv` had no header because `parse_ns3.py` wrote none. **Fixed at the generator.**
* ⚠️ **`analysis/analyse_phase_artifact.py` read a hardcoded path into an agent session scratchpad**
  (`/tmp/claude-.../c1_raw.csv`). It was unrunnable by anyone else and did not read the committed
  artifact. **Fixed**: defaults to the committed CSV, `--csv` to override. It now reproduces F32's
  2–8× variance inflation (2.91× / 2.82× / 7.88×) from data in the repo.
* ⚠️ **Neither `lora_phase_artifact_*.csv` has a committed generator** — 300 runs that are Direction
  C's entire evidence base cannot be re-derived. Recorded as open; a retrospective header was added
  to the EU file stating config and findings, with the **env block deliberately absent rather than
  guessed**, plus an explicit warning that no generator reproduces it.

#### D. The unicast small-frame bias (O4) — hypothesis tested, and it holds

E21 recorded the anomalous-slot effect (Tinnirello, Bianchi & Xiao, TVT 2010) as a *plausible,
untested* cause. Bianchi omits the anomalous slot, so it under-counts the cycle by one idle slot σ
per success and over-predicts by σ/(T_s + σ) — a worst case that should **bound** the bias and,
crucially, **scale as 1/T_s**:

| L | predicted bound | measured deviation |
|---|---|---|
| 72 B | −3.32 % | −2.60 … −1.40 % |
| 288 B | −1.61 % | −1.07 … +0.33 % |
| **1400 B** | **−0.44 %** | **−0.40** … +1.29 % |

Correct sign, bounded at every size, and the predicted 7.5× collapse across a 20× frame-size range
is matched. At 1400 B the bound and the measured floor agree to **0.04 points**. ⚠️ This is a
consistency check against a bounding argument, not a fit of the full Tinnirello model — and
broadcast (which the headline runs on) holds to ±0.21 % at 72 B, so the explanation is asserted for
the unicast arm only. `tests/test_anomalous_slot_bias.py` pins all of it.

---

### 8. Summary — what changed in this pass

| # | severity | finding | state |
|---|---|---|---|
| **S3** | MAJOR | `N_max` applied V to a **mean**, not a distribution: 9/30 seeds fail at the certified N. `N_max = 3` has CI **[2, 3]**; the per-realisation criterion gives **1** | fixed (both criteria + bootstrap CI emitted); ⚠️ **which one the paper quotes is Mohamed's call** |
| **S7** | MAJOR | `make sim-ns3-delay` swept to U = 1.34 while the artifact and the headline crossing need U ≈ 2.44+ | fixed (defaults corrected, re-derived) |
| **S4** | MODERATE | delay driver emitted 30-seed means with **no dispersion**, against the project's own post-F30 standard | fixed |
| **O5** | MODERATE | `channel_utilisation` = 0 at N = 1, pinned by a test asserting the defect | fixed, test corrected |
| **S5** | — | are F25 / E9 / A2 confounded by RNG displacement? | **checked: clean**, and now guarded by `make verify-rng-isolation` |
| **S6** | MINOR | 3 raw CSVs lack provenance headers (one of them correctly so) | recorded with the precise fix |

**New machinery:** `threshold_crossing_ci` + 13 tests, `verify_rng_isolation.py`, and two make
targets. The through-line is that each replaces a discipline with a mechanical check — the project
has repeatedly found that "remember to look at the distribution" is not a control.

---

### 9. Idea and framing audit (2026-08-07) — the first pass that questioned the *premise*

*Requested: "audit the project, the idea and the process." Every earlier pass asked whether numbers
measure what they claim. This one asks whether the claims are worth making, and whether the paper
states them well. It found four framing defects and verified two integrity claims — one of which
survived and one of which did not.*

#### I1 (MAJOR) — the paper did not agree with itself about its own best contribution

| where | valuation of the payload-exclusion result |
|---|---|
| Abstract | listed among "**applications of established results rather than new ones**" |
| Conclusion | "an exclusion result that we regard as **the more durable contribution**" |

Both readings are defensible — *durable* is not *novel* — but a paper that files its strongest
result under "not new" in the abstract and "most durable" in the conclusion has not decided what it
is arguing. **Resolved by promoting it to the first result in the abstract and the first
contribution bullet**, stated precisely: the bound is Gündoğan's, the *instantiation on EU868 with a
measured H_f*, and the fragmentation corollary, are ours.

⚠️ It also deserves the promotion on merit: it is arithmetic. 64 B does not fit in 51 B, so DR0--2
are excluded whatever the encoding, batch or scheme. **Unlike every performance number in this
project — four of which this audit had to move — an impossibility result cannot drift.**

#### I2 (MAJOR) — the conclusion violated a rule the same paper states

* §Results: *"a single `≈3×` would be true of two of those four numbers and misleading about the
  other two."*
* §Conclusion: *"a `≈3×` ratio that is **stable under either feasibility threshold**."*

The artifact says **3.22× at saturation and 2.42× at the verifiability boundary**. The conclusion
was both wrong and self-contradicting, and it is the phrasing `CLAUDE.md` explicitly forbids.
**Fourth internal contradiction found by this audit, and the same mechanism every time: prose that
no test compares against anything.**

#### I3 (MAJOR) — the abstract was 693 words and structurally defensive

IEEE Access expects ~250. More important than length was the *shape*: it spent more words
qualifying the result than stating it — three separate self-criticisms before the reader reached
the feasibility envelope, which is the contribution that actually requires the co-design.

⚠️ **Honesty and impact were not in tension here; the abstract was failing at both.** Burying a
sound result under hedges tells a reader "this work is weak", which is itself inaccurate. Rewritten
to **267 words**, ordered by durability (exclusion → feasibility → bytes), with the limitations
stated once and precisely instead of woven through every sentence.

⚠️ **The rewrite caused a regression, which is worth recording.** The disclosure that the
pre-registered criterion's verifiability half was *satisfied by construction* existed **only in the
abstract**. Shortening deleted it. It is now restored to §Results, expanded with the stronger
statement the `p` sweep later established (feasibility requires `p ≤ ε` identically). **Improving
impact silently removed a self-criticism — exactly the failure this audit exists to catch, produced
by the audit itself.**

#### I4 — no contributions list

A reader could not extract what was new in ten seconds. Four bullets added, each naming what is
*not* ours alongside what is.

#### P1 (CHECKED — the claim is TRUE and verifiable)

The abstract calls the ≥40 % criterion **pre-registered**. Given S9 — where an identical claim was
withdrawn because its evidence had vanished — this had to be checked rather than trusted.

```
docs/04_EVALUATION_PLAN.md   3354ec1  2026-07-03  "Success criterion for the thesis headline:
                                                   optimized config reduces on-air auth bytes >=40%
                                                   vs A+CBOR at V >= 0.95 under p=0.05"
results/raw/e5_codesign.csv  a51486a  2026-07-05
```

**The criterion was committed two days before the result existed, in the public history.** This is
the rare case where a pre-registration claim is checkable by a third party with nothing but the
repository, and the paper now says so with that ordering rather than asserting the word.

#### P2 (MAJOR) — "all results are reproduced by an automated staleness gate" was an overstatement

The gate covered **16 of 41** artifacts. Most of the remainder genuinely require NS-3 or the Pi rig —
but **four did not**: `factorial_ablation`, `pqc_projection`, `sensitivity_p` and
`lora_external_check` are pure model computation and were ungated only because they were new. That
is the same F1 hole the gate exists to close.

**Fixed by closing the hole rather than softening the sentence.** All four are now gated (each
re-derives byte-identically; the frozen suite is 14 → 18 tests), every remaining ungated artifact
has a stated reason, and the paper now claims exactly "all 20 model-derived artifacts" instead of
"all results".

---

### 10. Full paper audit (2026-08-07) — read end to end, every table checked against its artifact

*Requested: "understand it deeply, rewrite every section to standard, audit for contradictions,
tone, clarity, claims, results and methodology, fix and re-audit; check formatting, graphs and
tables; think about what visualisations we lack."*

#### ⚠️ The largest finding: a whole table was stale, and a shipped figure plotted superseded data

**`tab:ns3` disagreed with its artifact in every cell.** It carried pre-30-seed values:

| N | paper had | artifact |
|---|---|---|
| 5 | +0.6 / −0.3 | **+0.54 / −0.07** |
| 10 | +0.9 / −0.4 | **+1.33 / −0.12** |
| 20 | +0.6 / −0.7 | **+1.14 / +0.39** |
| 35 | −1.4 / +0.9 | **+0.24 / −0.56** |
| 50 | −2.9 / +1.1 | **−0.37 / −0.27** |

Regenerated from the frozen `ns3_contention.csv`, with the statistic now named (median over 30
seeds, exact OFDM airtimes).

⚠️ **`fig_e5_codesign.png` had been shipping since 28 July plotting $H_f{=}40$\,B**, three days
before B1 measured it at 44\,B. Its caption said "104\,B to 26.0\,B" while the table beside it said
108 to 27.0 — 104 = 40+64. Two further figures (`e4_crossover`, `fig_envelope`) were equally stale.

**Root cause, and it is structural:** `make figures` regenerated only `figures_e123`, so four of the
five generators were never run by any gate. The frozen gate covers CSVs; nothing covered figures.
Fixed — `make figures` now runs all five, and `tests/test_figures_are_current.py` asserts every
generator still runs and every cited figure exists.

#### Contradictions found and fixed

| # | contradiction | resolution |
|---|---|---|
| 1 | §Theory said $H_f \approx 40$\,B (assumed) while the rest of the paper used 44\,B measured | 44\,B measured, everywhere; all 9 mentions now agree |
| 2 | Text said the optimizer "breaks a byte-tie toward **ECDSA**"; the artifact selects **Ed25519** | corrected to Ed25519, which is what E5 reports |
| 3 | `tab:envelope` caption said the crossing is $U{\approx}2.80$; the text said 2.44 | 2.44, labelled as interpolated between the measured $U{=}2.23$ and $3.34$ rows |
| 4 | Text said the advantage "needs … the scheme (auth bytes)" while `tab:decomp` reports the scheme axis as moving *neither* | scheme removed from the list; stated byte-neutral and decided on energy |
| 5 | Validation band quoted as $+1.28/-0.49\%$ — matching neither derivation | $+1.29/-0.40\%$ (mean, guarded by a test), with the median-based $+1.33/-0.37\%$ named as such |
| 6 | `fig:ns3` caption claimed agreement "within 1.44 %" — the superseded 10-seed figure | 0.51 % |
| 7 | "within 2.49 % on success probability, idle-slot occupancy **and throughput**" — throughput is 0.51 % | statistics separated, each with its own figure |
| 8 | Naive-reduction failure quoted as $16\times$; the regenerated table gives $+1631\%$ | $17.3\times$, consistent in all three places |

⚠️ **Two derivations of the same band existed** and neither was wrong: `figures_ns3.py` uses the
*median* with exact OFDM airtimes, `test_validation_bands.py` uses the *mean* with defaults. The
paper now names which statistic it is quoting instead of implying there is only one.

#### Visualisations: the gap was not missing figures but unused ones

The paper cited 3 of 9 generated figures — and the two it omitted were **exactly boundaries 1 and 2
of the new framing**. `figures_envelope_lora.py`'s own docstring had already said the envelope
"deserves a figure more than the auth-byte ratio does", and the paper was doing the opposite.
Added `fig:t6` (the exclusion tiers) and `fig:envelope` (the capacity envelope); 5 figures now.

#### Rewritten for standard

* **§Implementation** was a project changelog ("P0 locked the toolchain… P1b switched…") in internal
  phase numbering, with "an eight-law discipline" as jargon. Rewritten as
  **Implementation and Validation**: what was built and how each component was checked.
* **Abstract** now opens on the feasibility question, matching the title, before naming the knobs.
* **Tone:** "This is the disease; T2--T5 are the cure" removed; "AUTHBC is a **rigorous**…" removed
  (self-praise); "we **jointly optimize all four**" softened to "search all four jointly, and report
  which of them actually interact" — the previous wording contradicted the F39 ablation.
* **Consistency:** the intro called the four choices "coupled" two sentences before showing that
  only one pair is.

#### Methodological inconsistency between the two arms, fixed

The 802.11 arm reported `N_max` under both the mean and per-realisation readings; **the LoRa arm
reported only the mean**, with the caveat buried in §Reproducibility. `N_max = 3` is now given at the
point of use with its 95 % interval $[2,3]$, the 9-of-30 failure count, and the per-run value of 1.

#### ⚠️ Re-audit pass 2 — the worst finding came last: a table built on the PURGED 3-seed run

`tab:lora-external` (the Haxhibeqiri et al. cross-check) still carried the superseded data. Its AUTHBC column
matched `lora_capacity_3seed_SUPERSEDED.csv` **to three decimals**:

| N | paper had | 3-seed (purged) | 30-seed (current) |
|---|---|---|---|
| 5 | 0.0 % | **0.000** | 8.33 % |
| 8 | 13.4 % | **13.443** | 12.90 % |
| 30 | 59.0 % | **59.030** | 42.97 % |
| 50 | 74.7 % | **74.683** | 62.45 % |

Six 3-seed artifacts were purged weeks earlier (F38) and **this table was never re-derived with
them**. So the defect class CLAUDE.md calls *"the pattern of the whole audit"* — small samples read
against a threshold — was still being printed, after the audit that named it.

Two claims rode on the stale column:

1. **`N_max` was quoted as 5.** The 30-seed run gives **3** (0.9508 at $N{=}3$, 0.8981 at $N{=}4$);
   Haxhibeqiri et al.'s closed form gives **4** (4.418 % at $N{=}4$, 5.065 % at $N{=}5$). CLAUDE.md had said "their
   N_max=4 vs our 3" all along — the status board was right and the paper was wrong.
2. ⚠️ **The row annotated "we are more optimistic" restated retracted finding F18** — while a bold
   sentence 100 lines earlier said the exact opposite. The crossover is at $N{\approx}3$, not
   $N{=}8$: beyond it we are the *more pessimistic* model (1.6× at $N{=}5$, 2.1× at $N{=}50$).

**Why it survived three passes:** the Haxhibeqiri et al. column was correct throughout. Half the table agreed with
its source, so it read as verified. ⚠️ *A partially-correct table is harder to catch than a wholly
wrong one.*

It propagated: `tab:lowrate` used $N_{\max}{=}5$ to compute an aggregate of 0.82 rec/s and a
"$\approx$2500×" 802.11-vs-LoRa gap. Corrected: 0.495 rec/s and **≈4200×**, which *strengthens* the
section's argument that LoRa is a different regime rather than a slow 802.11. The prose figure
"we measure ≈75 % at $N{=}50$" (also 3-seed) is now 62 %, and "2.3× more pessimistic" is 2×.

**Guards added:** `TestLoraExternalTable` compares every cell to `lora_external_check.csv`, asserts
no row revives F18 (it checks the *artifact*, not the wording), pins both $N_{\max}$ values, and
recomputes `tab:lowrate`'s arithmetic from its own columns.

#### Re-audit pass 3 — rendering the PDF to images, not reading the log

The build log said "0 errors, 0 undefined refs" throughout every pass above. Rasterising the pages
and looking at them found six defects the log could not report:

| defect | how it presented |
|---|---|
| Bianchi equation overflowed its column | **collided with the adjacent column's text** — unreadable |
| 5 tables ran past the column edge | 2 promoted to `table*`, 3 narrowed |
| `fig_envelope` title collision | the "N=50 quoted" note was anchored *above* the axes and overprinted the title |
| ⚠️ `fig_envelope` axis label said $U{\approx}2.8$ | the **stale crossing**; corrected to 2.44 in `tab:envelope`'s caption but never in the figure |
| ⚠️ `fig_ns3_bianchi` said "NS-3 3.41" | the paper says 3.48 in four places and its own Limitations section documents the migration |
| ⚠️ `fig_ns3_bianchi` said "fails, 16x" | the 30-seed regeneration moved it to **17.3×** |
| ⚠️ `fig_e5_codesign` footed "energy/power are nominal (pending P7)" | P7 closed; the paper states both powers are **measured on the Pi 4** (D8). The figure contradicted the text beside it *and understated the work.* |

**The pattern, again in a new place.** Every one of these is text baked into a figure or a layout,
where no CSV comparison could reach it. `verify-frozen` re-derives data; nothing had ever *looked* at
the output. ⚠️ **A clean LaTeX log is not evidence that a page is correct.**

Guards added: generators may no longer hardcode an NS-3 version that disagrees with the paper, may
not carry `pending P<N>` notes, and the naive-reduction factor is now *derived from the CSV* rather
than typed into a label.

#### Coverage after three passes

All **10** tables and all **5** figures are now checked against the data that produced them.
Each new guard was **mutation-tested** — deliberately corrupted to confirm it fails — including
replays of two real bugs (`N_max` 3→5, ratio range 3.2→3.3×).

---

### 11. Pass 4 — reading every sentence, not just every number

The first three passes compared printed values to CSVs. This pass read the argument. It found a
different defect class: **constants DERIVED from a measured input, which never print that input.**

#### ⚠️ Five numbers still carried the superseded H_f = 40 B

Grepping for "40" found nothing, because none of these prints H_f — each prints a function of it:

| quantity | paper had | H_f=40 | H_f=44 (measured) |
|---|---|---|---|
| T2a boundary $(M{-}H_f{-}g_a)/(b{+}1)$ | 232.7 B | 232.67 | **232.00** |
| low-rate $A = M/(M{-}H_f{-}g_a)$, M=222 | 1.88 | 1.881 | **1.947** |
| 802.11 $A$ at MTU 1500 | 1.0745 | 1.0744 | **1.0776** |
| $b_{\max}$ at MTU 1500, delta | 31 | 31 | **30** |
| $A$ realised at MTU 256 | 1.68 | 1.684 | **1.730** |

⚠️ **The models were right the whole time.** `e2_batching.csv` already carried `A_formula=1.7297`
and `b_max=30`. Only the prose lagged — the hardest case to see, because every artifact agrees with
every other artifact and disagrees only with the sentence describing them. Guarded by
`TestDerivedConstants`, mutation-tested against all five historical values.

#### Other findings

* ⚠️ **"Results are 802.11-only (a LoRa arm is future work)"** — flatly contradicted Sec.~VI, an
  entire LoRa arm with its own tables, figures and external validation. A leftover from before that
  work existed, sitting in Limitations where a reviewer looks hardest.
* ⚠️ **The reproducibility contribution was overstated**: the paper claimed the gate re-derives
  **20** model-derived artifacts; it re-derives **16**. An inflated count in a headline
  contribution is the worst place for one. Now guarded against the gate itself.
* $\varphi$ was defined with an undefined symbol $g$ where the rest of the paper uses $g_a$.
* The fragmentation bound said $n$ "is exactly 1" when $\epsilon \leq p$; $\lfloor \cdot \rfloor$
  is **0** for $\epsilon < p$. Corrected to "at most 1" — the operational conclusion is unchanged.
* Delivery at $U{\approx}1$ was quoted as 98.8 %; the artifact says 0.98896 → **98.9 %** (two places).
* A duplicated "and and" across a line break.
* The Conclusion's hardware figure of **0.36 % is correct** — but only reconstructible from the
  unrounded 1.9882 ms prediction, since the printed 1.99/1.995 implies 0.25 %. Now stated as 1.988.

#### ⚠️ A citation error of my own, corrected

Verifying `N_max=3` I quoted 0.9508/0.8981 from `lora_capacity_30seed.csv`. **That file is the
no-jitter control**, not the canonical run — the `_30seed` suffix is misleading because the
canonical `lora_capacity.csv` is *also* 30 seeds (jittered). The paper is right and consistent
(0.960 at N=3, nine of thirty seeds failing, both from `lora_capacity.csv`); the wrong citation was
mine. Recorded in `results/PROVENANCE.md` so the next reader does not repeat it.

**Verified correct in this pass, against artifacts:** the factorial effects (interaction $-24.0$,
placement main effect $-24.0$, encoding $146.1$), the CLAS row ($72.0 + 162/(5{\times}4) = 80.1$),
the PQ projection ($45 + 2464/4 = 661.0$), the per-run crossing $U \in (1.67, 2.23]$ with 10/30
seeds failing, and `tab:t6`'s three tiers.

---

### 12. A new source, and what it cost (2026-08-07)

Mohamed supplied Klimiashvili, Tapparello & Heinzelman, *LoRa vs. WiFi Ad Hoc* (IEEE ICNC 2020,
DOI `10.1109/ICNC47757.2020.9049724`, Crossref-verified). It touched three separate claims, and
**two of the three went against us.**

#### ⚠️ 1. A counter-example to our own hypothesis, kept

The paper reports *"the average of 50 independent runs over channel realization and nodes'
position"*. It is an ns-3 LoRa simulation study, so it enters the Direction C corpus under the
**pre-registered** inclusion criteria — no discretion available — with the verdict `REPORTS`.

The sweep moves **0/4 → 1/5 REPORTS (20 %)** against a pre-registered falsification threshold of
25 %. H1 survives, *narrowly*, and the paper's wording changed from "none of the four" to "four of
five; the fifth does". We now report the **count** and explicitly refuse the percentage: the
protocol targeted 56 papers, the achieved $n$ is 5, and one paper moves the estimate 20 points.

⚠️ **A counter-example to one's own hypothesis is the easiest thing in science to quietly drop.**
`TestDirectionCSurvey` now fails if the corpus loses it, if the paper stops disclosing it, or if
REPORTS ever reaches 25 % — in which case the instruction in the assertion message is to *withdraw*
the claim, not soften it.

#### ⚠️ 2. A payload figure that would have flipped our headline exclusion

Their Table I lists **DR3 = 123 B**; our `tab:t6` uses **115 B**. At 123 B the residual is
$123-44-64 = 15 \geq s_{\min}$ and **DR3 becomes feasible** — "four of seven data rates excluded"
would become three, in the result we call the most durable in the paper.

Both numbers are correct readings of RP002-1.0.3: **123 is $M$** (MACPayload), **115 is $N$**
(application payload), differing by the 8 B `FHDR`+`FPort`. $N$ is the applicable one, because our
header, signature and record travel inside `FRMPayload` — and `lora.py` already said so
(`max_app_payload  # N, non-repeater-compatible, Table 13`). The model was right; what was missing
was any statement of *which column and why*, so a reader holding the other table would have found
the exclusion contradicted rather than explained. Now argued in §VI-A.

#### 3. Corroboration — qualitative, and bounded as such

They find neither technology uniformly better (WiFi ad hoc wins delay while single-hop; LoRa wins
energy only once WiFi degrades to multi-hop) and recommend *selecting between* them. That is our
two-regime conclusion reached independently and from the other direction.

⚠️ **Their "almost 5000×" is not our "≈4200×".** Theirs is a PHY bit-rate ratio against DR6's
11 kb/s with no duty cycle, framing or authentication; ours is an application-level aggregate of
authenticated records per second across a domain. The two are close in magnitude and measure
different things. The paper says so in the sentence that cites them, because leaving two similar
numbers adjacent is how a false corroboration gets made. **This is the F18 discipline applied
deliberately: quoting the sentence was not enough — the configuration it depends on had to be read.**

#### Two more C6 instances, found in passing

The literature register itself carried superseded values: the Bianchi validation band as
**+1.28/−0.49 %** (now +1.29/−0.40 %) and the naive-reduction error as **16×** (now 17.3×). Both had
been corrected in the paper weeks earlier. The register is where a reader goes to check a number,
which makes it a bad place for a stale one.

---

### 13. The Direction C claim, withdrawn (2026-08-08)

Mohamed's decision, on the evidence below. This is the audit's only *withdrawal on new data* rather
than on a defect, and it is recorded here because a claim removed quietly is indistinguishable from
one that was never made.

#### What happened

The claim: ns-3 LoRa simulation studies do not report the replication information a reader needs.
The pre-registered rule for abandoning it: **≥ 25 % of the corpus reporting**, fixed before the
corpus existed (`eb3eda5`, data-free).

| $n$ | 4 | 5 | 14 | 20 | **23** |
|---|---|---|---|---|---|
| REPORTS | 0 % | 20 % | 14.3 % | 15.0 % | **21.7 %** |

At $n=23$: **5/23 = 21.7 %, 95 % Clopper–Pearson [7.5 %, 43.7 %]**. ⚠️ **The interval contains the
threshold.** A test that cannot separate its hypothesis from its own falsification has not produced
a weak result; it has produced no result. The claim is cut from the paper.

#### Two temptations, both recorded because both were real

1. **The point estimate favours us.** 21.7 % is below 25 %, so "H1 supported" was available and
   arithmetically true. Quoting it without the interval would have been the exact error this audit
   spent a fortnight removing — the plausible number that survives because nobody states its spread.
2. **The subset that is not retrieval-biased goes the other way.** Journal-sourced papers read
   **4/14 = 28.6 %, above the threshold**; arXiv-sourced read 1/9. We had flagged that confound two
   rounds earlier, *before* these papers entered the corpus. It is nonetheless **not reported as a
   finding** — Fisher exact $p = 0.61$ — because a non-significant subgroup identified after the
   fact is the forking-paths error dressed as vindication.

#### What is kept

The corpus (23 papers, every verdict hand-adjudicated), the protocol, the sweep log with every
exclusion and its reason, and the harness. ⚠️ **Deleting them would make a null result
indistinguishable from an experiment never run.** The withdrawal is now a case study in the methods
companion, where a pre-registration that cost its author the claim is the strongest available
evidence that pre-registration works.

#### What survives in the paper on its own evidence

The phase-artifact measurement (bimodal delivery, CV inflated 2–8×), the attribution of the
phenomenon to Durand and Booysen, and the 30-seed reporting discipline. None of them ever needed
the literature claim.

**Guarded:** `TestDirectionCSurvey` fails if the corpus shrinks, if the withdrawal statement leaves
the paper, if the old claim reappears, or if the point estimate is ever quoted without its interval.
Mutation-tested against the claim creeping back.


---

<a id="s12"></a>

## 12. Claim audit — every headline number, re-derived from first principles

*Formerly `docs/CLAIM_AUDIT.md`, last changed 2026-10-07. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

> ⚠️ **Written before the October 2026 revision, and superseded in four places.** An external
> review showed that the design this document describes had been a *sum of sizes* and never one
> frame (findings F45–F53 in [`audits/model_provenance.md`](model_provenance.md)). Read
> what follows as the account of the work *up to August 2026*:
>
> | this document says | what is true now |
> |---|---|
> | 72.0 B per record, **−58.7 %** | that design verified 0.881 of its records at 5 % loss, not 0.95. With a full record in every frame: 74.96 B (−57.0 %) in the first format, **43.25 B (−70.3 %)** in the lean format that was then built |
> | "three" (or "four") "of seven" LoRa data rates excluded | **eight of twelve**, under four stated conditions |
> | capacities 31 → 100, 88 → 213, "1.9–3.2×" from one load ceiling U = 2.435 | the ceiling is not invariant; capacities are **simulated per configuration** — `results/raw/design_ladder.csv` |
> | "Bor et al." | Haxhibeqiri, Van den Abeele, Moerman & Hoebeke |
>
> The current account is the top entry of [`LOGBOOK.md`](../LOGBOOK.md), the paper, and the
> repository README. This file is kept because it records how the work was understood then.

*2026-08-28/30. Requested by Mohamed: "audit deeply each scientific claim, number, result,
implementation, literature comparison, value, methods and placement", then "audit all the math
deeply and compare it against the simulation". Readable rendering published as an artifact;
**this file is canonical**.*

**Method.** Re-derive each quantity from its equations, then check it against a discrete-event
simulation written for the purpose — never re-read the project's own conclusion about it. That
distinction is the whole point: every published number reproduced, so nothing here was found by
recomputing arithmetic. It was found by asking *what does this constant actually mean*.

Full evidence: **F43** and **F44** in [`audits/model_provenance.md`](model_provenance.md).
Outstanding items: [`OPEN_ITEMS.md`](../OPEN_ITEMS.md) §A9. Guards:
`tests/test_math_audit.py` (46 tests) and `tests/test_wire_profile.py` (30 tests).

---

### The verdict

**Nothing was a wrong number.** Every finding is a convention or a limit that decides a headline
and was never written down. All are defect class **C2 — an unverified constant on the measurement
path**, which is the one class the post-F30 30-seed discipline cannot touch.

⚠️ **In three of the five major findings, the unstated choice happens to favour our own claim** —
and in all three it does so *conservatively*, except one, which cost a headline.

---

### Major findings

#### F44 — the exclusion bound rested on a header we declined to optimise

⚠️ **This one moved the headline: "four of seven EU868 rates" became THREE.**

Two facts the project had always known separately, and never composed:

1. `docs/01` §2a: the frame skeleton is mostly CBOR **text key names**, and "an integer-keyed
   profile would shrink substantially — a wire-format optimisation this thesis does not claim."
2. `docs/02` T6: the exclusion bound is `s_max = M − H_f − g_a`. **It depends on H_f.**

| profile | H_f | B/record | DR3 `s_max` | DR3 |
|---|---|---|---|---|
| current (text keys, `src`+`seq` per record) | **44 B** | 94.0 | 7 B | excluded |
| **integer keys only** | **22 B** | 76.5 | **29 B** | ⚠️ **FEASIBLE** |
| integer keys + `src`/`seq` elided | 22 B | 66.5 | 29 B | feasible |

Seven text keys cost **29 B**; the same seven as small integers cost **7 B** — the convention COSE
and SenML already use. That single change halves the header and takes DR3 from missing by six bytes
to clearing by sixteen. The record elision is not even needed.

**What survives, and it was always the strong half.** DR0–DR2 stay excluded at a **zero-byte header
and a one-byte record**, because `M = 51 B < g_a = 64 B`. The smallest standardised alternative
(48 B compressed BLS12-381 G1, 126-bit security) leaves three bytes for header and record together.
That is arithmetic and cannot move.

**And the boundary became constructive** — it now names what would have to change, and shows that
for DR3 the answer is a header redesign rather than new cryptography. T6's tier taxonomy always
named "encoding" as the tier compression can attack. This is that tier being attacked.

⚠️ **The wire format is NOT changed.** D6 freezes it; `placement/wire_profile.py` measures an
alternative and `TestTheFrozenFormatIsUntouched` fails if it leaks into the shipped format.

#### F43c — the pre-registered success criterion could not have failed

The **ordering is genuine** and independently verified: the ≥40 % criterion is in `docs/04` at
`3354ec1` (2026-07-03 04:42); the E5 result at `a51486a` (2026-07-05 00:34).

But the quantity it tests reduces **exactly** to `1 − 1/b` — placement A carries `g_a + H_f` per
record, B carries `(g_a + H_f)/b`, and the ratio is the identity F13 already forbade quoting. So:

```
1 − 1/b ≥ 0.40   ⟺   b ≥ 1.667   ⟺   b ≥ 2
```

Independent of encoding, scheme, placement, H_f and g_a. The other half, V ≥ 0.95, E17 already
showed is satisfied by construction with zero margin. **Both halves are vacuous: no configuration
that batches at all could have failed.**

Keep the pre-registration and the date. What had to go is the implication that it was a live test.

#### F43b — H_f is a range, 38–44 B, and 44 favours the exclusion

Canonical CBOR encodes integers 0–23 in one byte and those ≥65536 in five, so the measured header
moves with `src` and `base_seq`: **38 B** for a fresh low-id node, **44 B** an hour into flight at
50 Hz. The documented 44 B reproduces exactly at realistic magnitudes — the measurement was sound;
`docs/01` §2a simply called it constant when it is constant only in *b*.

⚠️ **The bias direction is opposite for T6.** docs/01 §2a analyses H_f's bias for the *byte
comparison*, where 44 B is conservative. T6's bound means a **larger H_f makes exclusion more
likely** — so 44 B is the end of the range most favourable to the paper's most durable claim.
`framer.measure_frame_header_bytes` makes the range measurable rather than assumed.

#### F43a — `D(b)` names the oldest record's age and computes the batch window

With periodic arrivals: the **batch-window duration** is `b/Λ`; the **age of the oldest record** at
transmit is `(b−1)/Λ`. Both confirmed exactly by simulation, deterministic and Poisson (Erlang(b)
and Erlang(b−1)). `docs/02` §7 named the second and computed the first.

**`b/Λ` survives as the worst case** — it is exactly `(b−1)/Λ` plus one sampling quantum — and is
retained unchanged. ⚠️ Cost now stated: the tight reading admits **b=5** at both operating points
(66.6 B/rec, **−61.78 %**) where we publish b=4 (72.0 B, −58.68 %). **We under-report our own saving
by ~3 points.**

⚠️ One consequence was *not* conservative: `docs/02` §7a's "knife-edge" (100.37 ms, "b collapses to
1") is a property of the convention, not the design space — the oldest record in that frame is aged
**50.37 ms**. Corrected in place.

#### F43d — `s` depends on the generator window; the CI is ~150× too narrow

`seq` and `ts` grow with the record index and variable-length encodings charge for the digits:

| | n=1000 | n=10 000 | `e1_dominance` (30×1000) | `p1_sizes` (seed 1, n=10 000) |
|---|---|---|---|---|
| json | 191.36 | 193.52 | 191.085 | 193.518 |
| cbor | 66.73 | 68.94 | 66.252 | 68.936 |
| msgpack | 66.29 | 68.84 | 65.160 | 68.836 |
| **delta** | 45.04 | 45.01 | 44.998 | 45.005 |

Delta is flat because it encodes differences. **Two committed artifacts disagree by up to 3.7 B on
the same named quantity and both are correct for their own protocol.** E1's bootstrap CI for cbor is
±0.02 B — *seed* variation — while the systematic window term is ~2.7 B, **≈150× wider**.

Direction is conservative: a longer flight inflates the CBOR *baseline* and leaves the delta
*optimum* alone. E1 samples the **first ~50 s of each flight**, now stated in `docs/04` §1.

#### F43e — Haxhibeqiri et al.'s `N_max`=4 sits inside their own fit's unreliable region

`lora.py` already documents that Eq. (8) does not pass through the origin and predicts 1.783 % loss
at N=0, and that "below N ~ 5 the intercept dominates". Their N_max = 4 is decided at N=4 (4.418 %)
and N=5 (5.065 %) — **both inside that band**, with the non-physical intercept contributing **40 %
of the predicted loss at N=4**.

Direction is conservative: forcing the fit through the origin gives their N_max = **5**, *widening*
the gap against our 3. So quoting 4 is the safe choice — it simply needs saying.

⚠️ **"≈2× more pessimistic" hides a sign change.** The ratio runs **0.91× at N=2** (*we* are the more
optimistic model there), 1.07× at N=3, and 2.09–2.17× from N=10 up — and the crossover sits in
exactly the region where N_max is decided. F18 was retracted for a sign error on this same
comparison. `haxhibeqiri2017_pessimism_ratio` now refuses to be quoted as one number.

---

### M4 — closed by measurement

The U→V crossing was measured at a second frame size (**174 B**, the A+CBOR frame that produces the
baselines the capacity ratios divide by): **2.367** against 288 B's **2.435** — a **0.45 σ**
difference, **statistically indistinguishable** across a 1.66× change. The universal ceiling is
justified and no published number moves.

⚠️ **The pre-registration also made a DIRECTIONAL prediction the run had no power to test.** I
predicted the crossing would drift *higher*; it drifted lower, at 0.45 σ against a combined standard
error of ±0.151. **Had the noise fallen the other way I would have recorded a confirmation I had not
earned.** Kept visible as a flaw in my own pre-registration: *a directional prediction needs a power
estimate, or must be stated as a band.*

⚠️ **N-invariance remains untested** — both arms are N=50 while the envelope applies the ceiling from
N=2 to N=213.

---

### Checked and found CLEAN

*Recorded because a clean result is only useful if you can see what was tested.*

| check | method | result |
|---|---|---|
| OFDM PPDU airtime | hand-derived from 802.11a symbol timing | 1940 µs / 44 µs **exact** |
| Ma & Chen broadcast | vs `sim.dcf_ladder`, an independent slot-exact Monte Carlo | **≤0.08 %** at N=5–50 |
| … and vs NS-3 3.48 | 30 seeds | ≤0.51 % |
| the CFP mechanism | `head_start=False` removes only that asymmetry | collapses to the naive reduction; **16.9× at N=50**, reproducing F9 |
| Bianchi unicast | vs NS-3 | band **−0.40 … +1.29 %** |
| Bianchi fixed point | residual of both DCF equations, N=1…1000 | ≤ 7×10⁻¹³ |
| `N_max` first-failure search | exhaustive vs full scan, 7 configs × 4 ceilings | **identical everywhere** |
| −58.68 % and 213/100/88/31 | recomputed from artifacts | reproduce exactly |
| pre-registration ordering | git | genuine, ~1.8 days |

⚠️ **One clean result is clean by ACCIDENT.** Ma & Chen's S(n) is **non-monotone** in N — it dips near
N≈35 and recovers, and all three implementations agree, so it is real physics of the CFP series. The
`N_max` search breaks on the first violating N, which is valid only if U(n) is monotone. It is —
because U(n)'s explicit factor n outruns the recovery — but that is **safe by arithmetic, not by
construction**, and nothing tested it until now.

---

### Minor

* `bianchi.tau_of_pc(0.5)` raised on a **removable** singularity whose limit is `4/(2W+2+WM)`, and
  p_c crosses 0.5 for N ≳ 21. Never triggered; now returns the limit.
* Two dead constants removed (`LLC_SNAP_BYTES`, `MAC_HDR_FCS_BYTES`) — editing them changed no result
  while appearing to.
* The delivered fixed-point residual is `TOL/0.3`, not the documented `TOL`. Immaterial; documented.
* **Structural, not fixed:** 10 B/record of wire redundancy (`src` and `seq` duplicated against the
  frame header), ~14 % of the 72.0 B headline. D6 freezes the wire, so it is recorded as known
  headroom — which makes the reported cost an upper bound on an untuned design.

---

### The transferable lesson

Three times in this project a claim survived because two facts were each individually recorded and
never placed side by side — **F18** (quoting the PDF instead of the figure), **docs/02 §9c**
(asserting `N_max = 3` one line above a table of 3-seed data saying otherwise), and now **F44**.

> **A register that stores facts separately does not compose them. Only re-derivation does.**

---

*Companions: [`THE_STORY.md`](../archive/NARRATIVES_2026-08.md) (plain-language account) ·
[`HONEST_ASSESSMENT.md`](../archive/NARRATIVES_2026-08.md) (what the work is worth) ·
[`../thesis/STATUS.md`](../../thesis/STATUS.md) (thesis draft state).*
