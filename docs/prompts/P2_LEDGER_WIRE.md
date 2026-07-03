# P2 — LEDGER + CANONICAL WIRE FORMAT  (COPY-PASTE WHOLE FILE)
Lane 1 · week 2 · needs p1a-code-done · unblocks P3 · ends: tag p2-done · Eight Laws · PLAN MODE.
⚠️ After this phase, tests/vectors/ wire vectors are FROZEN (D6) — later changes need Mohamed.

CONTEXT BUDGET — read exactly: docs/01 §1 (ledger + security model + placements list) and §4
(wire format — the normative spec) · docs/03 §3 (ledger/ spec) and §4 (gates) · docs/06 §5.

OBJECTIVE: per-UAV hash-chain ledger with replay/equivocation handling, and the FROZEN
canonical frame format for placements A–D with vendored test vectors.

KEY FACTS INLINED:
- Record := {src:u16, seq:u32, ts:u32(ms), ph:bytes32, pl:map(telemetry)}; prev_hash =
  SHA-256 over the PREVIOUS record's canonical CBOR bytes. Define "canonical CBOR bytes of X"
  ONCE in a helper and cite docs/01 §4 in its docstring; everything hashes/signs via it.
- Placements (audit-corrected semantics): A inline per-record sig; B self-batch (ONE signer,
  b of its OWN records, ONE signature over the covered bytes); C cross-signer (b records from
  DIFFERENT originators each already signed, BLS-aggregated to 48 B); D block-level (one sig
  over b records spanning n>1 frames).
- Frame := {v:1, t:PLACEMENT_ID, src:u16, base_seq:u32, n:u8, recs:[RecordBody×n],
  auth:AuthBlock}. AuthBlock by placement: A [sig×n]; B one sig over canonical(recs);
  C agg_sig(48B)+signer_list; D sig + {block_id,frag_idx,frag_total}. Canonical CBOR; NO
  indefinite-length items; deterministic map key order.
- signature input = canonical bytes of the covered region ONLY — write covered_bytes(frame,
  placement) with its own unit tests (this boundary is the #1 audit target).

STEPS (one module = one commit):
1. ledger/record.py + chain.py: Chain.append(payload)->Record fills src/seq/ts/prev_hash.
   Tests: 1000-append chain verify; prev_hash correctness by INDEPENDENT recompute.
2. ledger/store.py + verify.py: ingest with counters replayed (seq ≤ last accepted for src ⇒
   drop+count), equivocation_flags (same (src,seq), different hash ⇒ flag + keep the evidence
   pair), tampered (hash/sig fail). Hypothesis property tests: ANY single-bit flip in ANY
   field of a signed record is detected; replay always rejected; equivocation always flagged.
3. placement/wire.py: exact Frame/AuthBlock for A–D; covered_bytes() + its unit tests.
4. VECTORS FREEZE: tests/vectors/wire/*.bin + expected-hash JSON for ≥3 frames per placement,
   with the fixed keys/seeds committed alongside; a test asserts byte-identity forever. Commit
   message: `test: freeze wire vectors (D6)`.
5. GOLDEN integration test: 3 simulated UAVs, direct handoff (no channel yet), fixed seed,
   assert EXACT final counters — this is the regression anchor for all later phases.
6. FUZZ gate: 1000 random byte-mutations of valid frames through decode+verify → zero
   crashes/hangs; malformed ⇒ clean rejection + counter.
7. RESULTS VALIDATION (Law 6, §Validate-Results): the golden counters are a "result" — state
   the EXPECTED counts in advance (records stored, replays, flags for your seeded scenario)
   and assert equality; confirm determinism (same seed ⇒ identical counters); if any count
   surprises you, debug it (do not adjust the assertion to match). Write into audits/p2.md.
8. AUDIT P2 (§Audit) — MANDATORY attacks: canonicalization ambiguity (map order? indefinite
   lengths banned?), covered_bytes off-by-one at every boundary, seq u32 wraparound policy
   (state + test), ts ms consistency, duplicate-record-in-frame handling, D fragment-header
   integrity. Fix → re-run all → `make all` → tag `p2-done` → push → §Handoff.

ACCEPTANCE: coverage ≥90% on ledger+wire · property/fuzz/golden green · vectors frozen with
provenance · results-validation + mandatory attacks in audits/p2.md · tag pushed.
