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
| **D4** | ~~NS-3 3.41~~ → **NS-3 3.48** (amended 2026-07-29) | the LoRaWAN module pins 3.48; see the amendment row below for the migration gate | version-pinned numbers | documented pin; approved. ⚠️ Every NS-3 artifact was re-measured, both trees kept, `AUTHBC_NS3` selects one |
| **D5** ✅ settled | energy meter: **2× INA219** (was UM25C), **Arduino as meter-host** | Mohamed owns them; I²C-scriptable beats eyeballing a USB meter; two sensors instrument **both** link nodes on one timebase; the Arduino has no OS ⇒ deterministic sampling and **zero CPU contamination** of the benchmarked Pi | shunt **burden voltage** can under-volt an RPi4; measures **whole-board** (not per-component) power; two sensors need distinct I²C addresses; Arduino/Pi timebases must be aligned | 5.15–5.2 V supply; calibrate each sensor vs a known load (>2 % ⇒ stop); bridge `A0` on sensor #2 (0x40/0x41); **GPIO17 sync line Pi→Arduino** tags the measurement window; star-ground everything. Rig + sketch: `hw/RIG.md`, `hw/arduino/ina219_logger/`. |
| **D6** ⚠️ | any change to frozen configs after data collection needs approval | reproducibility contract | can hide staleness (→ F1) | the re-run+re-freeze+re-validate discipline above; config-hash detects drift |
| **D8** ✅ settled 2026-07-28 | **the thesis platform is ARM (RPi4), not x86** | it is the actual deployment target; x86 was only ever a development baseline | every headline that depends on *timing* must be recomputed from the ARM measurements: E5's byte-tied scheme pick becomes **Ed25519** (ARM: 259.5 µs vs ECDSA 326.9; energy 186.8 vs 203.5 µJ), and E4's κ band must use measured ARM powers. The **auth-byte headline is unchanged by D8** — it is byte-based and both schemes are 64 B. *(It read 96.4 % at the time; F3 later moved it to 96.77 % and F10 to the current **75.00 %** — D8 itself moved nothing.)* x86 is retained as a secondary comparison platform (it is what makes the F6 portability finding visible). | re-run E4/E5 with ARM timings + measured powers, then re-freeze |
| **D7** | 2-lane execution | ~8 wks → ~5 | merge/sync overhead; shared files must be frozen | worktree-per-lane discipline; SYNC-only merges (done) |

## Ad-hoc technical decisions (made during execution)
| decision | why | shortage / limitation | how to solve |
|----------|-----|-----------------------|--------------|
| **BLS size = 96 B** (accept blspy AugSchemeMPL G2 sigs; not 48 B min-sig) | blspy default is 96 B; the measured timings are 96 B-mode; a 48 B size with 96 B timings is incoherent | BLS is byte-heavier than Ed25519 (96>64) → loses the byte game except in multi-signer aggregation; the T4 update was initially **missed** (F1) | applied 96 B everywhere (F1 fixed). **Alternative not taken:** switch blspy to PopScheme/min-sig (48 B G1 sigs) — but then **pubkeys grow to 96 B** and timings change; a real fork only worth it if 48 B sigs are specifically wanted |
| **CBOR = canonical schema arrays** (not string- or int-keyed maps) | smallest: 66–69 B vs 111 B string-key | array form needs a **fixed, versioned schema** (not self-describing); brittle to schema evolution | add a schema-version field; document the schema in the paper |
| **Delta K=16 keyframe interval** | balances keyframe overhead vs resync latency | a lost frame desyncs a src for up to K−1 records | tune K to the loss rate; keyframe-on-demand after a gap. ⚠️ **Superseded 2026-10-06 (R3, F46):** the shortage in this row was the defect — with b = 4, K = 16 leaves three frames in four undecodable alone and the design verifies 0.881 at p = 0.05. The interval is now a design variable r, and r = 1 (a keyframe in every frame) is adopted. `encodings/delta_enc.py` keeps K = 16 because the first format is frozen (D6) |
| **e-axis analytical size model for NS-3** (frame *sizes* from measured encoders, not encode-in-NS-3) | NS-3 needs frame-size parameters; sizes are measured-grounded | NS-3 carries opaque bytes of the right *size*, not the real encoded *content* → can't catch content-dependent PHY effects | acceptable for airtime/contention; note the abstraction |
| ~~**Nominal power (P_cpu 3.0 W, P_radio 0.7 W)** pending P7~~ — **SUPERSEDED 2026-07-28 by the P7b measurement: `p_cpu_w`=0.634 W, `p_radio_w`=0.218 W (κ=0.34). E4/E5 re-frozen on measured values.** | keeps E5 deterministic; the auth-byte headline is power-free | energy numbers are **estimates, not measured** | P7 INA219 measurement replaces them; F2 (unicast T_FX) reconciled in the same re-run |
| **Broadcast model = Ma & Chen (2007/2008), NOT a reduction of unicast Bianchi** (F9, 2026-07-28) — *supersedes three superseded explanations: the "18× capture" over-claim, "the capture effect", and our own "we discovered the head start"* | the mechanism (backoff counter **Consecutive Freeze Process**) is published: Ma & Chen, IEEE Comm. Lett. 11(8):686–688, 2007 and IEEE TVT 57(6):3757–3768, 2008. Their closed form reproduces our NS-3 measurement (p_s, idle-slots and throughput, all independently traced) to **≤0.75 %** on ns-3.41 and **≤2.49 %** on ns-3.48 at every N. Capture measured at **0 %** | our in-house reduction τ=2/(W+1) was wrong by **16× at N=50**; their abstract warns unicast models "cannot simply be reduced" to broadcast — we did exactly that. **No novelty is claimed for the mechanism** | `models/broadcast_dcf.py` implements their equations, cited; the reduction survives only as a labelled failure curve; `sim/dcf_ladder.py` kept as an independent cross-check; docs/02 §6a is now normative |
| **NS-3 sinks stop with the sources** (F8, 2026-07-28) | the 500-packet MAC queues drain at full rate after the sources stop; a longer-lived sink credited 0.5 s of extra delivery against a 10 s denominator | every previously frozen NS-3 goodput was **~4.8 % high**, uniformly | fixed in both scenarios and `ns3_matrix.csv` deliberately re-measured; unicast agreement tightens from +1.8…+5.3 % to +0.08…−3.31 % |
| **32 B prev_hash carried per record** | each frame round-trips standalone (frame-level verifiability) | inflates on-air size (~½ of delta's 45 B); redundant if the chain is recomputed | state as an explicit modelling assumption; a P2 chain could drop it from the wire |
| **Per-experiment record sizes** (single-seed for E2/E3/framesizes; 30-seed for E1/E5) | each experiment self-consistent | cross-experiment absolute sizes differ ~4 % (random-walk magnitude sampling — F4) | standardize the paper's headline size table on the 30-seed E1 mean±CI at P8 |
| **E5 scheme = ECDSA** (byte-tied with Ed25519; x86 energy tiebreak) | ECDSA faster on x86 (OpenSSL asm) | x86-specific; likely **flips to Ed25519 on ARM** (F6) | re-measure on RPi4 at P7b; the % auth-cut is identical either way |
| **E5 batch grid** (…24,28,32,36,40) | coarse sweep | optimum reported as b=28 is **grid-quantized**; true MTU b_max=31 (F3) | densify the grid near the MTU knee, or compute b_max analytically (E2 already gets 31) |

| **NS-3 runs are 10 s, not the docs' 30 s** (recorded 2026-07-28, decision C) | 10 s already gives ~5000 busy periods per run × 10 seeds; CIs are tight and the runtime budget was never at risk | an undocumented deviation from docs/04 §3 and the P6 prompt, now recorded rather than silently carried | keep 10 s; docs/04 §3 to be amended at P8 |
| **PacketSocket + PacketSink, not FlowMonitor** (recorded 2026-07-28, decision C) | FlowMonitor measures IP flows; we need MAC-level goodput with no ARP/IP artifacts, and the accounting is provably exact (goodput == trace successes × 8L / simTime to 0.00 % on every seed, audit A12) | deviates from docs/04 §3 and docs/06 §2, which also name a `parse_flowmon.py` that does not exist (the real script is `ns3/parse_ns3.py`) | keep; docs/04 §3 and docs/06 §2 to be amended at P8 |
| **Airtime is OFDM-symbol quantised** (⚠️ **D9**, settled 2026-07-28 by Mohamed) | the continuous 8N/R form was **0.41 %** short on a 1400 B frame and **12.1 %** short on an ACK against NS-3 3.41, and used 34 B MAC overhead instead of the real 36 B (audit A1) | airtime is a **step** function of L, so `T_fx` and the affine `T_air(L)` are gone; E4's ΔRADIO stays continuous (±5 % on a byte difference, immaterial against a ~90× verdict margin) | applied everywhere (NS-3 path, `models.energy`, `channel.airtime`); deliberate re-freeze: **E5 energy +0.096 %** (52.1487→52.1985 µJ), **E3 goodput −2.1 %**; **auth-byte headline unchanged by D9** (it read 96.77 % then; F10 later moved it to **75.00 %**) |

| **Freshness is ENFORCED and is a Pareto objective** (**F10**, settled 2026-07-28 by Mohamed) | docs/02 §7 says "enforce D ≤ D_max=250 ms **in the optimizer**"; batching buys bytes with staleness, so a co-design optimizer blind to freshness is not solving the stated problem | the previous reading ("soft = annotated, not filtered") let the byte-optimal b=31 be reported as the optimum at **1552 ms — 6.2× over** the bound, with the violation computed and discarded. **Headline changes 96.77 % → 75.00 %** (b=31 → b=4, 200 ms, 111.9 µJ) — still a comfortable PASS | freshness is now a **hard constraint** (521→160 feasible) **and a 4th Pareto objective** (82→18 frontier points). Closed form: **b ≲ Λ·D_max**, independent of encoding/scheme. E5 re-frozen; paper/narrative/summary updated. M/M/1 queueing term still unimplemented ⇒ D(b) is a conservative lower bound |
| **Record sizes: one 30-seed sampling protocol** (**F4**, settled 2026-07-28 by Mohamed) | docs/02 §8 mandates ≥30 seeded reps with a bootstrap CI; single-seed sampling met neither | E1 (30 seeds) and everything else (1 seed × 10 000) disagreed by **4.1 %** (cbor 66.25 vs 68.94) because the telemetry generator random-walks, so one long stream drifts to larger magnitudes | `framesizes.size_samples` / `measured_sizes` are now the single implementation (30×1000, fresh stateful encoder per seed) and E1 uses them too; `size_seed`/`size_n` removed from the E2/E3 configs; E1/E2/E3/E5/framesizes re-frozen. **Headline unchanged at 75.00 %**; T2a boundary unchanged |
| **docs/04 §1 cross-platform anchor is PER-CYCLE** (settled 2026-07-28 by Mohamed) | the old "RPi4 is 5–15× slower than x86" is arithmetically unreachable — the clock ratio alone (4.7/1.8 GHz) is a **2.61× floor**, so equally-optimised code *must* land below the band | three measured ops fell below it and the rule said "stop, the harness is broken" when the harness was fine | anchor **withdrawn, not widened** (Law 3) and restated as **"expect 1–4× the CYCLES on ARM; wall-clock = cycles × clock ratio"**. All measurements inside: Ed25519 1.05–1.16×, ECDSA 1.60–1.98×, BLS 3.2× |
| **F6 mechanism: report the measurement, claim no cause** (settled 2026-07-28 by Mohamed) | the portability difference is measured and reproducible on two boards; *why* OpenSSL's P-256 is less portable is a fact about that library, not about this thesis | the first explanation (ADX/BMI2) was **refuted by experiment** — masking those features made ECDSA *faster* — and retracted | state "Ed25519 needs 1.05× the cycles on ARM, ECDSA 1.60×" as an empirical finding with no mechanism attached; no further investigation planned |

| **Per-frame chaining adopted on the LoRa arm ONLY** (**F5**, settled 2026-07-28 by Mohamed) | on LoRa the regional payload limit binds (T2a), so lifting the 32 B `prev_hash` out of each record raises b from 2 to 7 at DR5 and buys **3.03× the sustainable record rate** (Λ 0.060→0.182 rec/s, 99.0→33.0 B/rec) for the same duty-cycle budget *(final values: measured H_f = 44 B and a contiguous batch grid. The first report of 2.7× was low on both counts — a sparse grid omitting b=7 had quantized the optimum, the F3 defect again)*. On 802.11 freshness binds (dC/ds = 1), so the identical change buys ~6 % energy and **zero** extra records | a **recorded deviation from the D6-frozen wire format**, scoped to LoRa: the two arms now frame the same ledger differently. Within a LoRa frame, tamper-evidence rests on the frame signature rather than on independently transmitted hashes — equivalent in strength (frames are atomic and signed over ordered records) but no longer two independent mechanisms | `experiments/lora/config.yaml:adopted_chain_mode: per_frame`; `per_record` retained in the sweep as the labelled counterfactual; stored ledger and `Chain.verify()` **unchanged** (receiver derives the omitted links); **E1–E5 and the 75.00 % headline untouched**; docs/02 §9b; pinned by `test_lora_chain_adoption.py` |
| **LoRa arm ships as a scoped modelling chapter, not a measured arm** (settled 2026-07-28 by Mohamed) | the analytical result (T6 + the 130–470× rate gap) is the thesis-relevant content, and it is derivable from primary specs alone; the hardware to measure it does not exist in the inventory | the chapter must not read as an experimental arm — **no hardware, no energy column, no measured validation** — and LoRa's role is long-range *provenance*, not live telemetry | framed as "Generalisation: the low-rate regime", carrying **T6** as its headline; energy deliberately absent from `lora_codesign.py` (the only measured `p_radio_w` is a Wi-Fi figure); limitations stated in-chapter |

| **NS-3 migrated 3.41 → 3.48** (⚠️ **D4 amended**, 2026-07-29, at Mohamed's direction) | the LoRaWAN module (signetlabdei) pins ns-3.48 exactly, and the LoRa arm needs a multi-node capacity envelope that no analytical model can supply (item D2). Migrating is cheaper than maintaining two simulators | **every NS-3 artifact is re-measured.** Both trees are kept — `ns3/ns3_paths.py` selects one via `AUTHBC_NS3` — because results cannot be shown unmoved by deleting the simulator that produced them | **Gate passed** (`ns3/compare_versions.py`, tolerance stated in advance): worst per-point Δ **2.56 %** inside ±3 %. Agreement bands re-measured and **both reported**: unicast↔Bianchi **+0.6/−2.9 % → +1.28/−0.49 % (improved)**, broadcast↔Ma&Chen **≤1.1 % → ≤1.44 % (widened)**. Delay sweep reproduces with the load-bearing number **identical** (V=0.95 crossing at **U=2.80** on both); 3.48 delivers better at low load (loss 1.02 % → 0.12 % at the reference point), consistent with its `WifiPhy` state-machine race fix. Build needs `-j 3` on this 7.8 GB host or the OOM killer takes WSL down |
| **LoRaWAN module payload limit is 222 B, not our 242 B** (found 2026-07-29 while building the LoRa capacity scenario) | the module enforces **RP002-1.0.3 Table 12** (repeater-compatible); our `models/lora.py` uses **Table 13** (non-repeater) and says so in `test_lora.py` | an independent implementation reads the standard the other way. At DR5 this caps the per-frame batch at **b=6**, where our model reports **b=7** | keep Table 13 in the model (it is the documented choice) and run the *simulation* at a payload the module accepts (218 B, b=6); the discrepancy is recorded in `TRADEOFFS.md` rather than silently reconciled |

## Revision decisions, 2026-10-06 (R1–R18) — the external review of the paper

*Mohamed's instruction: "do the recommended decision". Each row is the option recommended in the
revision plan and adopted on that instruction. Labelled **R** so that they cannot be confused
with D0–D9 above. R17 and R18 were Mohamed's to choose and are still open.*

| decision | rationale | shortage | how to solve |
|---|---|---|---|
| **R1 — corrections plus every piece of evidence that needs no new equipment** | answers every statement of the review inside the thesis calendar | contention is still simulated only | R9 |
| **R2 — build the design as one frame format** (`wire_v2`, "lean": sender, receiver, loss), report first and lean side by side; **the first format stays frozen** (D6) | removes the root cause (F45): a design that is a sum of sizes has no receiver to refuse a frame | two formats to explain; the first format's delta rows are still a byte model and are labelled so (`sized_from`) | none needed — the lean rows are emitted frames |
| **R3 — the keyframe interval r is a design variable**, chosen with b under V ≥ 1 − ε | turns F46 into a result: at ε ≤ p only r = 1 passes | costs 3.0 B/record in the first format (71.99 → 74.96) | a cleaner link admits r > 1; the prize is ≤ 3.5 B/record |
| **R4 — the exclusion is restated on one frame definition, over all twelve EU863-870 data rates, with a matrix of what each relaxation buys** | F47: the old test charged neither the chain link nor a self-contained record, and counted seven rates | **"three of seven" and F44 are withdrawn**; the claim is now eight of twelve under four stated conditions | — |
| **R5 — baselines are a ladder (each rung changes one thing) plus an analytic table of the classical stream-signing schemes** (E11, E17) | A+CBOR confounds "sign every record" with "one record per frame" | the stream schemes are **modelled, not implemented**; capacity for them is the saturation bound only | implementing EMSS in the loss emulator was the rejected, larger option |
| **R6 — V is measured with the codec in the loop, under i.i.d., Gilbert-burst and length-dependent loss** (E10) | E3 drew a Bernoulli per frame and compared it with its own mean | under length-dependent loss the design is **below** 0.95 at the 5 % point (V = 0.943) | stated in the paper; no repair protocol is proposed |
| **R7 — the V ≥ 0.95 capacity is found by direct ns-3 search in N, 30 seeds, bootstrap interval** | the same treatment the LoRa arm already had; closes M4 | **the pre-registered ±10 % prediction failed** (F50) and every 802.11 capacity changed | capacities are now per-configuration simulated values |
| **R8 — record sizes are checked on public PX4 flight logs** | no hardware needed | the logs carry position at 5 Hz: nothing is tested below 0.2 s spacing (F52) | a 50 Hz log, or software-in-the-loop |
| **R9 — no new hardware now; "Hardware Validation" leaves the title** | two radios validate airtime, not contention; the title claimed more | the single most valuable missing measurement (three or four radios in one collision domain) is still missing | Mohamed's Pi 3 is a **3B+**, which has a 5 GHz radio, so a third station is available — `OPEN_ITEMS` G4 |
| **R10 — PHY generality by a model-only sweep** (E15) | cheap, and answers "is 6 Mb/s special?" with a mechanism | validated at 6 Mb/s, 20 MHz only; every other row is labelled a prediction | one ns-3 validation point at 802.11p timing |
| **R11 — the paper's low-rate section becomes the exclusion matrix and one paragraph; the rest moves to thesis ch. 10** | the section was a second paper inside the first | the LoRa capacity work is no longer in the paper | it is intact in the thesis |
| **R12 — retraction and audit history moves to the methods paper, thesis ch. 11 and this repository** | a results paper should state results; the history is a contribution of its own | the paper no longer shows how its numbers were corrected | `paper/methods.tex`, `LOGBOOK.md` |
| **R13 — certificates are a second column, both designs charged** (docs/02 §6d) | neither accounting hidden behind the other | explicit certificates only; capacities are simulated without certificate bytes | `OPEN_ITEMS` S10 |
| **R14 — AUTHBC is defined once; "hash-chained ledger" replaces "blockchain-grade"** | the paper builds a signed hash chain, not a consensus protocol | ⚠️ the expansion written is *"authenticated telemetry for a blockchain-style, hash-chained ledger"* — **Mohamed to confirm the wording** | G1 |
| **R15 — an energy table from the existing INA219 runs** (E16) | the paper said energy was measured and showed none | first format only; one configuration is not reportable (contaminated idle windows) and is shown as such | re-meter with ≥ 10 repetitions; time the lean codec on the Pi |
| **R16 — relay placement gets its equation and a pointer to E4; multi-hop is declared out of scope** | it was named as a design axis and never evaluated | no multi-hop result | future work |
| **R17 — venue and page target** | ⚠️ **OPEN — Mohamed** | the paper is written to 8–9 two-column pages | — |
| **R18 — whether the analysis of the review is committed to this public repository** | ⚠️ **OPEN — Mohamed**; until decided it stays outside it, and nothing here quotes the review | — | — |

**Taken during execution under the same instruction — ⚠️ each needs Mohamed's confirmation:**

| decision | rationale | shortage | how to solve |
|---|---|---|---|
| **The lean format carries one chain link per frame on both arms** | it is one format; a link per record would put back the 32 B the format exists to remove | ⚠️ the 2026-07-28 decision adopted per-frame chaining **on the LoRa arm only**. It still governs the first format, which is unchanged; the lean format extends it to 802.11. Continuity *inside* a frame then rests on the frame signature alone | confirm, or keep the lean format for LoRa only and report 802.11 in the first format |
| **Reported capacities use a send time redrawn within every period** (`nmax_source: period`) | the rule registered in follow-up F1b before its runs; strictly periodic sources freeze phases (F51) | not the published scenario's default source; a real autopilot's timing jitter is not measured here | the strictly periodic results are kept in the same file for comparison |
| **N_max is the largest simulated N whose mean delivery is ≥ 0.95**, with the interpolated crossing beside it | as registered; the interpolated value was added after the data and is labelled | the grid value is coarse where the grid is | grids were refined near every reported crossing |
| **Every result in the paper is a generated macro** (`analysis/paper_numbers.py`) | a typed number is a copy, and copies drifted three times | LaTeX source is harder to read | `paper/numbers.tex` is the table of values |
| **New experiments are E9–E17; review decisions are R1–R18** | E6–E8 and D0–D9 were taken | `OPEN_ITEMS` also has items named E1–E24 — a third namespace, older | none; cite as "experiment E9" / "item E9" |
| **The paper keeps its August title, less the phrase R9 removed:** *"AUTHBC: Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound and a Capacity Envelope"*; the exclusion is its first result, as the revision plan specified | the 2026-08-07 framing decision stands, and the review asked for the exclusion first | ⚠️ **A first rewrite in this revision had retitled the paper *"AUTHBC: Co-Designing Record Encoding, Signature Placement and Batching for Hash-Chained UAV Telemetry"* and placed the exclusion after the 802.11 results.** Neither was in the approved plan; both were found on a second pass over it and undone. The thesis title is likewise the August one less "Hardware Validation" | if Mohamed prefers the design-first title, it is one line and the section order is one move (`tests/test_paper_numbers.py` holds the current order) |
| **The methods paper is retitled "Nine Ways …"** and gains three classes (C7–C9) | six classes were found by self-audit, three by an outside reader | ⚠️ a title change | revert the title and keep the section |
| **Eleven of the twelve PDFs added in October are NOT redistributed** (**decided by Mohamed, 2026-10-07**, when asked before the branch was first pushed) | the August decision that copyrighted PDFs stay covered what was already public; it did not clearly cover new ones, and a public history cannot be taken back | the rule "a source is not cited unless it is held and read" can no longer be checked by cloning. `docs/literature/HELD_LOCALLY.csv` lists each file with its SHA-256, size and where to obtain it; the tests accept an absent held file only if it is listed there, and check the hash when it is present. ⚠️ The unpublished commits from `e9d9e44` on were rewritten to remove the files — trees otherwise identical, author and committer dates preserved, cited hashes updated; the four pre-registration commits before it (`6f82599`, `47ebbbb`, `e4e3cdf`, `c2080fd`) are unchanged | a new source is added to the manifest and to `.gitignore`, not committed, unless its licence allows redistribution (the one kept, Li et al. 2025, is CC BY) |
| **The stream-signing baselines are simulated as frames** (follow-up F3, 2026-10-07): five more cells of the direct search, predictions committed first | a baseline with a modelled capacity beside a design with a simulated one is still a weak baseline | ⚠️ a simulated delivery is an **upper bound** on what three of the schemes verify (a packet that waits for a later key, a later signature packet or every earlier packet); the schemes are still not implemented | implement one in the loss emulator — the option R5 rejected |
| **Every ladder size that is not an emitted frame is marked** (†): all first-format rows and the lean row without delta coding (F55) | the caption claimed more than the artifact's `sized_from` column says | one lean row stays a sum of parts | a keyframes-only switch in the lean codec (`OPEN_ITEMS` G20) |
| **The paper cites Haber and Stornetta alone for the hash chain; the body uses the title's two nouns** ("exclusion bound", "capacity envelope") | the review asked for the first; the second keeps the approved title honest | none | — |
| **One new source is redistributed: Rajasekaran et al. 2022, CC BY 4.0** | the 2026-10-07 rule withholds *copyrighted* PDFs; an open-licence one may be shared with attribution, as the one that stayed in October | — | — |

> **Open items live in [`OPEN_ITEMS.md`](OPEN_ITEMS.md)** — the single tracked list of
> everything assumed, deferred, unvalidated or accepted-as-a-limitation. Decisions live here.
> **What each decision COST lives in [`TRADEOFFS.md`](TRADEOFFS.md)** — required reading before
> quoting any number: this is an optimization problem, so a reported configuration without its
> alternatives is a selection, not an optimization.

## Decision → downstream frozen artifacts (blast-radius map)
Use this whenever a decision changes, to know exactly what to re-run + re-freeze + re-validate.
- **BLS size** → `e4_crossover.csv`, `e4_bytes.csv`, `framesizes.csv`, E5 (`g_a` dict). *(F1: E4 was the missed one.)*
- **encoder/schema** → `p1_sizes.csv`, `e1_dominance.csv`, `framesizes.csv`, E2/E3/E5 (sizes), all size figures.
- **measured timings (P7)** → E4 (crossover), E5 (energy), the crypto anchor tables.
- **powers (P7)** → E5 energy column only (headline auth-bytes unaffected).
- **airtime/T_FX** → energy model → E5 energy; NS-3 comparison uses its own airtime (separate).
- **MTU / H_f / batch grid** → E2, E3, E5 (feasibility + b_max).
- **lean frame layout (`wire_v2`, `models/frame.py`)** → `frame_components`, `e3_codec_loss`, `design_ladder`, `exclusion_matrix`, `lora_budget`, `phy_sweep`, `stream_baselines` → `paper/numbers.tex` → every table of the paper and of thesis ch. 7, 8, 10.
- **`ns3/authbc-delay.cc` or the direct-search plan** → `ns3_nmax_direct_runs.csv` → `ns3_nmax_direct.csv` → `design_ladder.csv` (`n_max_v95*`) → `numbers.tex`, `fig_nmax_direct.png`. ⚠️ Hours of simulation; the frozen gate checks the summary against the runs file, not the runs against ns-3.
- **measured timings (P7)** also → `design_ladder` (`n_cpu_one_core`), `freshness_budget`, `energy_table`.
