# Decision ledger — rationale · shortage · how to solve

Living record of every design/methodology decision, its justification, the limitation it carries,
and the mitigation. Companion to docs/00 §6 (the formal D0–D7 register) and
docs/audits/full_audit_pre_p7b.md. Updated 2026-07-10.

## Why the frozen data barely moved when we "fixed BLS" — read this first
Two facts that look contradictory but aren't:

1. **The BLS fix (F1) DID change results — but only E4.** `crossover.py` (the file that hard-coded
   BLS=48 B) is imported by **exactly two** files: `experiments/e4/run_e4.py` and its unit test.
   Nothing else. So re-running with 48→96 B changed E4 substantially and nothing else:

   | E4 quantity | before (48 B) | after (96 B) |
   |---|---|---|
   | BLS own-traffic bytes/rec (cbor, b=2) | 112.9 B | **136.9 B** |
   | own-traffic κ* (any b) | 43.2 | **∞** (BLS carries more bytes than Ed25519) |
   | ΔRADIO (ρ=0, b=8) | +2.67 µs | **−5.33 µs** |
   | conclusion (winner) | ed25519 | ed25519 (**unchanged**, now stronger) |

2. **E1/E2/E3/E5 did not change because they never used the buggy value.** E5 already used
   `g_a["bls"] = 96.0` (experiments.py:179) — the BLS=96 B decision *was* applied to T5, it was
   only T4 that got missed. E1/E2/E3 have no BLS crossover at all. So there was nothing in them to
   change.

3. **"and others" (F2, energy) was documented, not numerically changed.** I added a code NOTE that
   the energy radio term uses the unicast fixed airtime (~1 % over-count) and deferred the numeric
   fix to the P7 energy re-run — deliberately *not* re-freezing E5 for a 1 % nominal-energy tweak.
   So E5 energy is unchanged **by choice**, not because the issue is imaginary.

4. **The "byte-identical regeneration" was a *determinism re-check done after* the E4 fix was already
   committed.** It compared freshly-regenerated files against the already-fixed committed state and
   found them identical — proving the pipeline is deterministic and the fix didn't leak. It is
   **not** evidence the fix did nothing (see the table above).

## Why we freeze measurement data at all
The pipeline splits into two layers on purpose (Law 7):

- **MEASURED / frozen:** `p1_crypto.csv` (timings), `ns3_matrix.csv` (simulation). These are
  **non-deterministic** — re-running gives slightly different numbers (CPU scheduler, thermal,
  RNG-in-simulator). We measure them **once, carefully, under controlled conditions**, commit them
  with an env + config-hash header, and never silently re-roll them. Otherwise every `make` would
  quietly move the numbers and nothing would be reproducible.
- **DERIVED / regenerable:** E1–E5 CSVs (formulas over frozen sizes/timings) and every figure.
  These are **byte-stable** — `make figures` reproduces them exactly from the frozen raw, so a
  reviewer regenerates the whole paper from immutable inputs.

This is the standard "raw data immutable, analysis reproducible" scientific pipeline. D6 extends it
to the **wire format** (the on-air bytes are a contract for interop/verifiability — changing them
silently would invalidate the claims).

**The shortage of freezing:** frozen data can go **stale** when an upstream decision changes but the
frozen artifact isn't re-run. That is **exactly what produced F1** — the BLS=96 B decision landed,
E5 was updated, but the frozen E4 kept the old 48 B. Freezing buys reproducibility at the price of
silent-staleness risk.

**How we solve it (now enforced, not just documented):**
1. **Automated reproduction gate** — `tests/integration/test_frozen_reproducibility.py` (run via
   `make verify-frozen`, in CI on every push and in `make all`). It re-derives **every deterministic
   frozen artifact** (E1–E5, framesizes, p1_sizes, e4_crossover, e4_bytes, ns3_contention) from the
   CURRENT code + configs + frozen measured inputs and asserts the data rows byte-match the committed
   CSV. **Any drift ⇒ red CI failure** that forces a deliberate re-freeze — silent staleness (F1) can
   no longer be committed. Verified to catch the exact F1 regression (BLS 96→48 B ⇒ the gate fails).
   The gate is `-m frozen`, deselected from the fast local `make test`, so it doesn't slow the TDD
   loop. The genuinely MEASURED fixtures (`p1_crypto`, `ns3_matrix`) are never re-measured, only
   checked for presence/shape.
2. Every decision change ⇒ use the **decision→artifact blast-radius map** below to re-run + re-freeze
   all downstream artifacts; the gate then confirms nothing was missed.
3. Periodic **whole-repo audits** (like the pre-P7b pass) as a backstop.

## Formal decisions (docs/00 §6)
| id | decision | why | shortage / limitation | how to solve / status |
|----|----------|-----|-----------------------|-----------------------|
| **D0** | gh auth + git identity (manual) | only human step; rest is agent-run | none | settled |
| **D1** | 802.11 arm first, LoRa deferred (doc 30) | focus one PHY | results are 802.11-specific; LoRa's low rate/long range → very different airtime & energy; conclusions may not transfer | build the LoRa arm later; scope every claim to 802.11 in the paper |
| **D2** | Ed25519 self-batch default; BLS only for cross-signer aggregation | audit-corrected architecture | BLS's one strength (aggregation) is **not** exercised by the headline (self-batch); E4 confirms BLS loses on 802.11 for own traffic | keep the BLS story in the relay/cross-signer regime (placement C); don't claim BLS for self-batch |
| **D3** ⚠️ | Ed25519 **batch-verify** needs a native binding; default = sequential verify | avoid a Rust dependency now | sequential verify is slower → the verify-throughput ceiling (Λ) is **pessimistic** for Ed25519; a native batch-verify would raise it | approve a Rust/native step **iff** throughput becomes binding; today claims are scoped to sequential verify |
| **D4** | NS-3 3.41 | current stable, from source | version-pinned numbers | documented pin; approved |
| **D5** ✅ settled | energy meter: **2× INA219** (was UM25C), **Arduino as meter-host** | Mohamed owns them; I²C-scriptable beats eyeballing a USB meter; two sensors instrument **both** link nodes on one timebase; the Arduino has no OS ⇒ deterministic sampling and **zero CPU contamination** of the benchmarked Pi | shunt **burden voltage** can under-volt an RPi4; measures **whole-board** (not per-component) power; two sensors need distinct I²C addresses; Arduino/Pi timebases must be aligned | 5.15–5.2 V supply; calibrate each sensor vs a known load (>2 % ⇒ stop); bridge `A0` on sensor #2 (0x40/0x41); **GPIO17 sync line Pi→Arduino** tags the measurement window; star-ground everything. Rig + sketch: `hw/RIG.md`, `hw/arduino/ina219_logger/`. |
| **D6** ⚠️ | any change to frozen configs after data collection needs approval | reproducibility contract | can hide staleness (→ F1) | the re-run+re-freeze+re-validate discipline above; config-hash detects drift |
| **D8** ✅ settled 2026-07-28 | **the thesis platform is ARM (RPi4), not x86** | it is the actual deployment target; x86 was only ever a development baseline | every headline that depends on *timing* must be recomputed from the ARM measurements: E5's byte-tied scheme pick becomes **Ed25519** (ARM: 259.5 µs vs ECDSA 326.9; energy 186.8 vs 203.5 µJ), and E4's κ band must use measured ARM powers. The **96.4 % auth-byte headline is unchanged** — it is byte-based and both schemes are 64 B. x86 is retained as a secondary comparison platform (it is what makes the F6 portability finding visible). | re-run E4/E5 with ARM timings + measured powers, then re-freeze |
| **D7** | 2-lane execution | ~8 wks → ~5 | merge/sync overhead; shared files must be frozen | worktree-per-lane discipline; SYNC-only merges (done) |

## Ad-hoc technical decisions (made during execution)
| decision | why | shortage / limitation | how to solve |
|----------|-----|-----------------------|--------------|
| **BLS size = 96 B** (accept blspy AugSchemeMPL G2 sigs; not 48 B min-sig) | blspy default is 96 B; the measured timings are 96 B-mode; a 48 B size with 96 B timings is incoherent | BLS is byte-heavier than Ed25519 (96>64) → loses the byte game except in multi-signer aggregation; the T4 update was initially **missed** (F1) | applied 96 B everywhere (F1 fixed). **Alternative not taken:** switch blspy to PopScheme/min-sig (48 B G1 sigs) — but then **pubkeys grow to 96 B** and timings change; a real fork only worth it if 48 B sigs are specifically wanted |
| **CBOR = canonical schema arrays** (not string- or int-keyed maps) | smallest: 66–69 B vs 111 B string-key | array form needs a **fixed, versioned schema** (not self-describing); brittle to schema evolution | add a schema-version field; document the schema in the paper |
| **Delta K=16 keyframe interval** | balances keyframe overhead vs resync latency | a lost frame desyncs a src for up to K−1 records | tune K to the loss rate; keyframe-on-demand after a gap |
| **e-axis analytical size model for NS-3** (frame *sizes* from measured encoders, not encode-in-NS-3) | NS-3 needs frame-size parameters; sizes are measured-grounded | NS-3 carries opaque bytes of the right *size*, not the real encoded *content* → can't catch content-dependent PHY effects | acceptable for airtime/contention; note the abstraction |
| **Nominal power (P_cpu 3.0 W, P_radio 0.7 W)** pending P7 | keeps E5 deterministic; the auth-byte headline is power-free | energy numbers are **estimates, not measured** | P7 INA219 measurement replaces them; F2 (unicast T_FX) reconciled in the same re-run |
| **Broadcast model = Ma & Chen (2007/2008), NOT a reduction of unicast Bianchi** (F9, 2026-07-28) — *supersedes three superseded explanations: the "18× capture" over-claim, "the capture effect", and our own "we discovered the head start"* | the mechanism (backoff counter **Consecutive Freeze Process**) is published: Ma & Chen, IEEE Comm. Lett. 11(8):686–688, 2007 and IEEE TVT 57(6):3757–3768, 2008. Their closed form reproduces our NS-3 measurement to **≤0.36 %** at every N. Capture measured at **0 %** | our in-house reduction τ=2/(W+1) was wrong by **16× at N=50**; their abstract warns unicast models "cannot simply be reduced" to broadcast — we did exactly that. **No novelty is claimed for the mechanism** | `models/broadcast_dcf.py` implements their equations, cited; the reduction survives only as a labelled failure curve; `sim/dcf_ladder.py` kept as an independent cross-check; docs/02 §6a is now normative |
| **NS-3 sinks stop with the sources** (F8, 2026-07-28) | the 500-packet MAC queues drain at full rate after the sources stop; a longer-lived sink credited 0.5 s of extra delivery against a 10 s denominator | every previously frozen NS-3 goodput was **~4.8 % high**, uniformly | fixed in both scenarios and `ns3_matrix.csv` deliberately re-measured; unicast agreement tightens from +1.8…+5.3 % to +0.08…−3.31 % |
| **32 B prev_hash carried per record** | each frame round-trips standalone (frame-level verifiability) | inflates on-air size (~½ of delta's 45 B); redundant if the chain is recomputed | state as an explicit modelling assumption; a P2 chain could drop it from the wire |
| **Per-experiment record sizes** (single-seed for E2/E3/framesizes; 30-seed for E1/E5) | each experiment self-consistent | cross-experiment absolute sizes differ ~4 % (random-walk magnitude sampling — F4) | standardize the paper's headline size table on the 30-seed E1 mean±CI at P8 |
| **E5 scheme = ECDSA** (byte-tied with Ed25519; x86 energy tiebreak) | ECDSA faster on x86 (OpenSSL asm) | x86-specific; likely **flips to Ed25519 on ARM** (F6) | re-measure on RPi4 at P7b; the % auth-cut is identical either way |
| **E5 batch grid** (…24,28,32,36,40) | coarse sweep | optimum reported as b=28 is **grid-quantized**; true MTU b_max=31 (F3) | densify the grid near the MTU knee, or compute b_max analytically (E2 already gets 31) |

## Decision → downstream frozen artifacts (blast-radius map)
Use this whenever a decision changes, to know exactly what to re-run + re-freeze + re-validate.
- **BLS size** → `e4_crossover.csv`, `e4_bytes.csv`, `framesizes.csv`, E5 (`g_a` dict). *(F1: E4 was the missed one.)*
- **encoder/schema** → `p1_sizes.csv`, `e1_dominance.csv`, `framesizes.csv`, E2/E3/E5 (sizes), all size figures.
- **measured timings (P7)** → E4 (crossover), E5 (energy), the crypto anchor tables.
- **powers (P7)** → E5 energy column only (headline auth-bytes unaffected).
- **airtime/T_FX** → energy model → E5 energy; NS-3 comparison uses its own airtime (separate).
- **MTU / H_f / batch grid** → E2, E3, E5 (feasibility + b_max).
