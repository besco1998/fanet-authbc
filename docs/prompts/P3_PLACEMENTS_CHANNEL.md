# P3 — PLACEMENTS + CHANNEL EMULATOR  (COPY-PASTE WHOLE FILE)
Lane 1 · week 3 · needs p2-done · unblocks P4 and SYNC-3 (frame-size CSV) · ends: tag p3-done
Eight Laws · PLAN MODE.

CONTEXT BUDGET — read exactly: docs/01 §1 (placement semantics) and §3 (data flow) · docs/02
§6 (airtime constants — normative) and §7 (latency terms) · docs/03 §3 (placement/, channel/,
bench/macro) · docs/06 §3.

OBJECTIVE: framers A/B/C/D + a seeded broadcast channel with an airtime ledger; export real
frame sizes for NS-3.

KEY FACTS INLINED (802.11a OFDM, base rate R = 6 Mb/s):
- T_air(L bytes) = T_fx + 8L/R, with per-frame fixed overhead computed from: PHY preamble
  T_phy = 20 µs; MAC+FCS header = 34 B; SIFS = 16 µs; DIFS = 34 µs; slot = 9 µs; ACK = 14 B;
  propagation δ = 1 µs. For a successful UNICAST exchange T_s(L)=T_phy+8(L+34)/R+SIFS+δ+
  (T_phy+8·14/R)+DIFS+δ. Fixed part T_fx ≈ 123 µs. **BROADCAST has NO ACK/SIFS/retry** — for
  the broadcast airtime use T_air = T_phy + 8(L+34)/R + DIFS + δ (document which you use where;
  do not mix — this is a scientific-integrity trap revisited in P6).
- MTU application budget M = 1500 B. Frame header H_f = 44 B (measured, B1). b_max(s) = ⌊(M − H_f − g_a)/s⌋.
  EXPECTED b_max (M=1500, H_f=40): with g_a=48 (BLS) — CBOR s=130→10, JSON s=358→3, delta
  s=40→35; with g_a=64 (Ed25519 self-batch) — CBOR→9, delta→34. Unit-test b_max against these.
- Loss model: per-receiver i.i.d. Bernoulli(p), p∈{0.02,0.05,0.10}, seeded RNG per run.

STEPS (one module = one commit):
1. placement/inline.py (A) + self_batch.py (B): Framer ABC {pack(records)->frames,
   unpack(frame)->(records, ok_mask)}. B: one signature over covered bytes; expose b_max(s)
   and unit-test against the inlined numbers (mismatch = STOP).
2. relay_agg.py (C): consumes records WITH originator signatures; BLS-aggregate to 48 B;
   aggregate_verify on unpack; signer-list per docs/01 §4. Test: mixed-originator frame
   verifies; ANY one bad inner signature ⇒ whole aggregate fails + counted (document this).
3. block_agg.py (D): one signature spanning n>1 frames; fragmentation headers; reassembly
   buffer with 500 ms sim-time timeout; partial-block discard counter. Tests: reorder
   tolerance; timeout path; loss-of-one-fragment kills exactly that block.
4. channel/airtime.py: T_air per the inlined constants; unit-test against THREE hand-computed
   values you show the arithmetic for in the test comments (both unicast and broadcast forms).
5. channel/emulator.py: broadcast bus; per-receiver Bernoulli(p) seeded; MTU assert; per-node
   counters {frames_tx,frames_rx,bytes,airtime}. DETERMINISM test: same seed ⇒ byte-identical
   metrics CSV.
6. bench/macro.py: generator→framer→channel→verify→ledger→tidy CSV (row = config…, seed,
   metric, value; config-hash column). Extend the golden test end-to-end through the emulator
   with exact expected counters.
7. `make export-framesizes` → results/raw/framesizes.csv (placement×encoding→byte
   distribution). SYNC-3 artifact — announce in docs/status/lane1.md.
8. RESULTS VALIDATION (Law 6, §Validate-Results): EXPECT and check — with p=0 every sent
   frame is received (V=1) and airtime accounting balances (sender airtime = Σ frame
   airtimes; receivers add none); with p>0, measured receive fraction ≈ (1−p) within CI over
   ≥10 000 frames (state expectation, then verify with a Binomial check); airtime for a known
   frame size equals the hand value. Determinism holds. Write into audits/p3.md; debug any
   surprise rather than tolerating it.
9. AUDIT P3 (§Audit) — MANDATORY attacks: loss independence across receivers (statistical
   test vs Binomial), airtime double-counting on broadcast, C's one-bad-signer semantics, D
   timeout races, b_max off-by-one at exact MTU. Fix → `make all` → tag `p3-done` → push →
   §Handoff.

ACCEPTANCE: all four placements end-to-end · determinism proven · b_max & airtime match
inlined/hand values · framesizes.csv exported · golden updated · results-validation + five
attacks in audits/p3.md · tag pushed.
