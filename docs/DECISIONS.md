# Decision ledger — rationale · shortage · how to solve

Living record of every design/methodology decision, its justification, the limitation it carries,
and the mitigation. Companion to docs/00 §6 (the formal D0–D7 register) and
docs/audits/AUDIT_HISTORY.md. Updated 2026-07-10.

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
with D0–D9 above. R17 and R18 were Mohamed's to choose; he chose on 2026-10-08 (the section after this one).*

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
| **R17 — venue and page target** | **DECIDED 2026-10-08 — a networking journal without page charges, after the contention experiment** | the paper is written to 9 two-column pages in the conference class and changes class at submission | the next section |
| **R18 — whether the analysis of the review is committed to this public repository** | **DECIDED 2026-10-08 — no.** It stays outside; nothing here quotes the review | — | — |

**Taken during execution under the same instruction.** ⚠️ Each needed Mohamed's confirmation; **on 2026-10-08 he confirmed** the chain link per frame on both arms, the title and the methods paper's title (next section):

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

## Decided by Mohamed, 2026-10-08 — every point the revision had left to him

*Asked with options and a recommendation for each (the private audit of the review, §7.6). He
chose; the cost of each choice is stated beside it, as for every decision in this file.*

| decision | chosen | what it costs, or leaves open |
|---|---|---|
| **One chain link per frame on 802.11 as well as LoRa** (was `OPEN_ITEMS` G5) | **Yes.** The lean format carries one link per frame on both arms | Inside a frame, order rests on the frame signature alone. The stored ledger is unchanged: the receiver rebuilds every record's link and the signature covers it. The 2026-07-28 decision still governs the first format |
| **What "AUTHBC" stands for** (G1) | *"authenticated telemetry for a blockchain-style, hash-chained ledger"* stays | "blockchain-style" appears once; there is no consensus layer and the text says so |
| **Paper title** (G1b) | *"AUTHBC: Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound and a Capacity Envelope"* stays | The design-first alternative is dropped |
| **Authors** | ~~Mohamed alone; the supervisor is thanked~~ — **superseded 2026-10-25: four authors** (below) | ⚠️ The acknowledgement carries a placeholder for the name. Affiliation, ORCID and a funding statement are still his to supply |
| **Venue (R17)** | A networking journal without page charges, **after** contention has been measured on radios | Submission now waits on hardware he has yet to find. The class changes from `conference` at that point; the exact journal is chosen then |
| **The analysis of the review (R18)** | **Stays private.** This repository refers to the review and never quotes it | — |
| **Sending the response to the supervisor** | After the bench session | The response will then report the bench results as well |
| **Publishing the revision** | A pull request from `p9-supervisor-revision` to `main`, merged after he has read it | Until then `main` still carries the superseded results |
| **The methods paper** | Keeps its new title ("Nine Ways …") and is held until the main paper is submitted | — |
| **Contention on real radios** (G4) | **Find one or two more 5 GHz radios first**, then run it | Not three stations now. The paper keeps "contention is simulated" until then |
| **One bench session** | All four measurements in one sitting: the lean codec timed and metered (G9), the unusable energy row re-metered (G11), crypto timing on the Pi 3B+ and the BeagleBone (G15), Ed25519 batch verification (G19) | Needs his hands; the scripts and the expected values are prepared first |
| **A real LoRa link** | **No** | The exclusion stays arithmetic on the standard's payload table, with emitted frames |
| **Telemetry at 50 Hz and the real stream's timing** (G7, G12) | PX4 software-in-the-loop on the development machine | Real autopilot software, simulated vehicle and clock: not a flight, and not a radio |
| **Two questions about the simulator** (G6, G18) | Both: fresh seeds for the traffic-source difference, **and** a derivation of the airtime rule's slope | Simulation time; the derivation is tested on predictions committed before its runs |
| **Stream-signing baselines** (G14) | Left as they are: sized from their definitions, simulated as frames | None is implemented |
| **Implicit certificates** (S10) | One sentence; they are not priced | The certificate column is an upper bound, and says so |
| **Two sources** (G8, G21) | He obtains Kurkowski et al. 2005; SSDBFAN is read by the agent | Until the first arrives it stays quoted through a held paper |
| **The thesis, next** | Chapter 2 | — |

*Deferred by him and unchanged: mobility (E20) and the LoRaWAN frozen-phase artifact as a second
short paper.*

## Decided by Mohamed, 2026-10-24 — the reviewer revision in the paper and the thesis

| decision | chosen | what it costs, or leaves open |
|---|---|---|
| **Which `main.tex`** | His uncommitted 2026-10-12 restyle (committed as his, 87bd25a) | — |
| **A14 and the hardware items B1–B5** | Not stated in the paper or the reply, not even as future work, until the purchases | A reader sees no plan for measured capacity |
| **5G NR sidelink (A11)** | Future work | One PHY family is simulated, 802.11 only |
| **Generative-AI statement** | Removed from the paper and the thesis | IEEE, Elsevier and MDPI require a disclosure at submission; that statement is his to make there |
| **The registration table the reply promises** | ~~In the paper's appendix~~ — **removed 2026-10-25**; the reply no longer promises it | The paper does not show its registrations; the thesis's Appendix B does |
| **A figure or table for every reviewer point** | Yes, in the paper | The paper grows from 15 pages |
| **The thesis** | Each revision result goes into the chapter it belongs to | More edits than one new chapter |
| **Paper and thesis names (2026-10-25)** | "first format" → **record-linked format**; "lean format" → **frame-linked format**; "keyframe" → **key record**, "delta" → **delta record**, reference interval → **key-record interval**; the configuration → **AUTHBC**, the baseline → **per-record signing**; access-rule model → **contention model** (an event simulation, so not "analytical"); the airtime line → **airtime capacity law**; spoilers → interferers; group tag → **group MAC**; lazy → **deferred batch verification**; GNSS-time window → **timestamp acceptance window**. In paper, thesis, figures, tables and the reply | Code and data keep the old identifiers (`lean`, `first`, `\bprLean…`); only printed text changed |
| **Readability review (2026-10-25)** | Every recommendation of `docs/revision/PAPER_CHANGES.md` applied except L2 and L3 (the introduction's questions and the contribution bullets stay as written) | The paper is 18 pages |
| **AUTHBC's expansion (T5)** | **AUTHenticated telemetry for BlockChain-style ledgers** — supersedes the 2026-10-08 decision ("authenticated telemetry for a blockchain-style, hash-chained ledger") | **Confirmed by Mohamed 2026-10-26**, knowing it reverses his choice of 2026-10-08 |
| **Section order (L5)** | The low-rate section now follows the 802.11 results — supersedes the 2026-10 decision that the exclusion is the paper's first result in the body; the abstract still states it first | **Confirmed by Mohamed 2026-10-26**, knowing it reverses the October order |
| **Authors (2026-10-25)** | Mohamed A. Farouk, Mahmoud Abdelaziz, Ahmed F. Darwesh, Ashraf D. Elbayoumy, all Dept. of Communication Engineering, Military Technical College, Cairo | ORCID iDs and a funding statement are still to be supplied |

## Decided by Mohamed, 2026-10-27 — the review of the 18-page paper (`docs/review 27-10-2026/`)

| decision | chosen | what it costs, or leaves open |
|---|---|---|
| **Format (L-01)** | The Springer Nature template of his earlier Communications Engineering submission: `sn-jnl` with `lineno, pdflatex, sn-mathphys-num`; Introduction / Methods / Results / Discussion / Declarations, appendices; **no cuts until he decides** | 40 pages in this layout. Communications Engineering charges an article processing charge, which conflicts with the 2026-10-08 entry "a networking journal without page charges": his to settle |
| **Order (L-02)** | The 802.11 result first everywhere: abstract, contributions, body, conclusion | Supersedes the abstract's exclusion-first order (2026-10-26 entry above) |
| **Capacity at the margin (S-01)** | New ns-3 runs at 97 % delivery, registered first (`prereg-S01`, 3149f70) | 420 runs; both crossings held their predictions (`predictions/S01.md`) |
| **Traffic source and the deadline (S-02)** | Argued from existing data: the strictly periodic (send-at-fill) source gives the same mean capacity; a $D_{\max}$ line and a caption note on Fig. 8 | No new runs with a send-at-fill source |
| **Fig. 1** | Redrawn in TikZ with the agreed names | — |
| **Title (L-21)** | Kept | — |
| **Corresponding author (L-26)** | Mahmoud Abdelaziz, mkaremm@mtc.edu.eg | — |
| **Data and code availability (S-36)** | Not mentioned, nothing done, for now | A journal will ask for the statement at submission |
| **AUTHBC's expansion (L-22)** | Unchanged, as confirmed 2026-10-26 | — |

## Decided by Mohamed, 2026-10-28 — the open options of the 2026-10-27 review

He took the recommendation on each of: venue, length, Table 8, the 48 B BLS variant, the ETSI
version, ASTM F3411, Fig. 10's colors and the template files. The rest (placeholders, S-36, PR #1
and #2, thesis markers, hardware, deferred studies) waits.

| decision | chosen | what it costs, or leaves open |
|---|---|---|
| **Venue** | Keep the Springer Nature layout; choose the journal later. The 2026-10-08 rule (no page charges) stands | The paper is not yet aimed at one journal |
| **Length** | No cuts until the journal is chosen; then cut to its limit | 40 pages for now |
| **Table 8, nodes per core (S-24)** | Eq. (4), 1 + ⌊1/((Λ/b)t)⌋, the receiver included: Rust **290**, deferred **629** (were 289 and 628); Python 57 and batches 643 unchanged | One node more in two cells; the reply letter and the revision documents follow |
| **48 B BLS (S-15)** | Not timed; the text states it and the speed it would need | A CPU claim for the 48 B variant rests on its two pairings, not on a measurement |
| **ETSI TS 103 097 (S-30)** | V1.2.1 (2015), the version read | The 2021 version is not cited |
| **ASTM F3411 (S-34)** | RFC 9575 only | — |
| **Fig. 10 colors** | The project's palette: purple, orange and aqua (validated, all pairs) | — |
| **Springer template files** | Kept local and git-ignored | A fresh clone downloads the template before `make paper` |
| **The review folder** | Not decided (the recommendation covered only the template files) | Stays out of git |

> **Open items live in [`OPEN_ITEMS.md`](OPEN_ITEMS.md)** — the single tracked list of
> everything assumed, deferred, unvalidated or accepted-as-a-limitation. Decisions live here.
> **What each decision COST is in the trade-off register at the end of this file** (formerly
> `TRADEOFFS.md`) — required reading before
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

---

## Trade-off register — what every decision bought, and what it gave up

*Formerly `docs/TRADEOFFS.md`, merged here on 2026-11-01 so that each decision and its cost are
in one document. Rows written before the October 2026 revision carry the numbers of their date;
where a later finding changed a row, a correction note follows it.*

### Trade-off register — what every decision bought, and what it gave up

*Formerly `docs/TRADEOFFS.md`, last changed 2026-10-09. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*Created 2026-07-29 on Mohamed's instruction: **this is an optimization problem, so the work does
not rest on finding the best numbers. State everything, choose what to stick with, and state the
trade-offs for every decision.***

That is a methodological requirement, not a formatting one. An optimization result is only
meaningful if the feasible region and the objectives are visible; a single reported configuration
with its alternatives suppressed is a *selection*, not an *optimization*. This file is the index of
every choice that shapes a reported number, with its cost stated in the same breath as its benefit.

**How to read the status column.** `DECLARED` — chosen deliberately, alternatives reported, cost
accepted. `MEASURED` — settled by measurement, not judgement. `FORCED` — the alternatives are
infeasible, so there was no real choice. `OPEN` — not yet settled (see `OPEN_ITEMS.md`).

Companion documents: **`DECISIONS.md`** (the decision log with dates and blast radius),
**`OPEN_ITEMS.md`** (what is still unresolved), **`audits/model_provenance.md`** (the findings
behind several rows here).

---

#### 1. The operating point

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Λ = 50 rec/s, D_max = 100 ms** — **ADOPTED 2026-07-30** | primary operating point | b=4 ⇒ 75.0 % auth / **58.68 % total cut** (identical to the alternative — only Λ·D_max sets b); **fully compliant** with 3GPP TS 22.125 (≥10 msg/s, ≤100 ms); Λ=50 Hz is PX4 `MAVLINK_MODE_ONBOARD`, read from source | **~2× swarm size**: N ≤ 100 at V≥0.95 (35 at saturation) instead of 213 (103). Requires the vehicle to actually stream at 50 Hz | **ADOPTED** (B3, docs/01) |
| Λ = 20 rec/s, D_max = 250 ms | reported alternative, **no longer the headline** | b=4 ⇒ same 58.68 % cut; supports **N ≤ 213** at V≥0.95 | **Violates TS 22.125 R-5.2.2-011** (≤100 ms). The deviation buys **no bytes** — only swarm size. Retained because a deployment outside §5.2.2's scope may prefer it, and because hiding it would hide the size of the trade | **REPORTED, not adopted** |
| ⚠️ **Λ < 40 Hz with D_max = 100 ms** | — | compliant | **b = 1: the co-design collapses to a 12.2 % cut.** b ≤ Λ·D_max means holding b=4 under a 100 ms deadline needs Λ ≥ 40 Hz. **The batching benefit is not available at every compliant point** — it is a constraint on the application's telemetry rate, not on the cryptography | **FLOOR OF THE REGION** (B3) |
| | *alternative:* Λ=50, D=100 ms | fully compliant, **identical bytes** (Λ·D=5 ⇒ b=4), PX4 `ONBOARD` is a real mode, and **feasible** — U=1.39 is inside the measured V≥0.95 boundary of U≈2.435 | halves the supportable swarm: N≤213 → **N≤100** | reported |
| | *alternative:* Λ=21, D=100 ms | compliant, lowest channel load | cut halves to 50 %; **knife-edge** — at Λ=20.0 the b=2 frame takes 100.37 ms, so b→1 and the cut → **0 %**. Superseded: Λ=50 is compliant *and* keeps the full cut | reported, not adopted |
| **N_local = 50** | neighbourhood size | a swarm the baselines cannot serve (32) and the co-design can (103) | not independently cited; justified *by* the envelope rather than by a density source | **MEASURED** as a curve (B2) |
| **p ∈ {0.02, 0.05, 0.10}** | loss grid | mechanism-grounded (802.11 broadcast has no ACK, no retransmission ⇒ receiver sees raw channel error) | no single measured FANET PER; 20–100× more pessimistic than TS 22.125's managed-C2 99.9 % — conservative, but not tied to a measurement | **DECLARED** (B4) |
| **ε = p** | verifiability target | makes T6's n_max = 1 exact, closing the fragmentation escape | a looser ε would admit fragmentation and weaken T6; the theorem is stated with its condition (ε ≤ p) rather than the value | **DECLARED** |

> **Corrected 2026-11-01.** The capacities in this table (100, 213, 103, 35 and 25 / 32 / 103)
> came from one load ceiling, which a registered test showed is not invariant (F50, 2026-10-06).
> Capacities are now simulated per configuration: 35 → 124 drones at 5 % frame loss and
> 27.6 → 97.3 at 3 % (`results/raw/design_ladder.csv`, `results/raw/capacity_97.csv`). The
> 58.68 % saving is now 70.3 % in the frame-linked format. The decisions themselves stand.

#### 1a. LoRa channel count — why "use as many channels as possible" is right for a gateway and wrong for us

*Raised by Mohamed 2026-07-30. The intuition is correct for the infrastructure case and inverts for
ours, so it is recorded rather than answered in passing.*

| option | what it buys | what it costs | verdict |
|---|---|---|---|
| **1 channel (868.1), all nodes** — **ADOPTED** | **every node can hear every other node.** The only configuration in which a single-radio peer receives the whole neighbourhood | ~3× the collisions of a 3-channel deployment at the same load | **ADOPTED for the ad hoc arm** |
| 3 channels (868.1/.3/.5), gateway collects | **MEASURED (F25):** ~**2.68× aggregate delivery at N=50** (0.2532→0.6781) and reaches N=100 at 0.5308, which the peer config cannot. ⚠️ But **N_max only 5 → 8** at V≥0.95 — the threshold sits on a near-vertical part of the curve | ⚠️ **a single-radio peer tuned to 868.1 cannot hear a frame sent on 868.3.** Fine for a gateway with 8 demodulators across all three; **broken for peer-to-peer broadcast** | **correct for infrastructure, not for us** |
| 3 channels + multi-radio peers | collision reduction *and* full reception | 3 radios per UAV — a hardware change, not a configuration | out of scope |

**Two facts behind this, both verified at source:**

1. ⚠️ **Extra channels buy zero extra airtime.** The EU868 duty cycle is enforced **per sub-band**,
   not per channel, and all three mandatory channels sit inside **g1 (868.0–868.6 MHz), which has a
   single 1 % budget** — confirmed in the ns-3 module: `AddSubBand(SubBand(868.0e6, 868.6e6, 0.01,
   14))`. Hopping across them spreads the *collisions*, it does not raise the *rate*. So `Λ` and the
   whole duty-cycle-derived batch argument (docs/02 §9) are unchanged by channel count.
2. **Broadcast requires a shared channel.** For a provenance ledger every peer must receive every
   record. With one radio per node, that is only possible if all nodes transmit and listen on the
   same frequency. Channel diversity and broadcast reachability are in direct conflict, and the
   ledger needs reachability.

**Net:** more channels is the right answer to "how many UAVs can report to a ground station" and the
wrong answer to "how many UAVs can hear each other". We are asking the second. See F21.


#### 2. What is claimed, and how

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Headline = total bytes (−58.68 %), reported as a decomposition** | honest attribution | claim matches evidence; all four axes genuinely contribute to *total* bytes | a smaller, less quotable number than the 75 % it replaces | **FORCED** by F13 |
| **Never quote the bare 75 % auth cut** | — | forecloses *"is your result just the definition of batching?"* — for that metric it is: the ratio is **1 − 1/b**, invariant to H_f, g_a, encoding and scheme | the most memorable number in the thesis | **FORCED** by F13 |
| **Load-bearing claim = feasibility envelope** | N_max 25 / 32 / **103** | a capability statement that genuinely needs all four axes *plus* the channel model | depends on the channel model's validity, which is validated for throughput only (D3) | **DECLARED** |
| **Report both the compliant and the declared operating point** | costs nothing (identical bytes) | kills the "you picked a loose bound" objection outright | two numbers to explain instead of one | **DECLARED** |

> **Corrected 2026-11-01.** The capacities in this table (100, 213, 103, 35 and 25 / 32 / 103)
> came from one load ceiling, which a registered test showed is not invariant (F50, 2026-10-06).
> Capacities are now simulated per configuration: 35 → 124 drones at 5 % frame loss and
> 27.6 → 97.3 at 3 % (`results/raw/design_ladder.csv`, `results/raw/capacity_97.csv`). The
> 58.68 % saving is now 70.3 % in the frame-linked format. The decisions themselves stand.

#### 3. Model scope — what is deliberately not modelled

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **No DCF channel-access delay in D(b)** | tractable closed form | **measured negligible**: +0.046 ms at the reference point, +2.2 ms even at 6.7× saturation load, against 250 ms. Broadcast has no ARQ so it cannot queue — overload degrades *delivery*, not latency | **MEASURED** (C1/D3) |
| **Saturation channel models at a non-saturated point** | Bianchi / Ma & Chen are validated and closed-form | measured to understate usable capacity by **≈2.8×**; U<1 is *sufficient, not necessary*, so every N_max computed that way is a **lower bound**. Comparative ratios unaffected | **MEASURED** (C2/D3) |
| **Single collision domain; no mobility, spatial reuse or hidden terminals** | one clean, validated regime | a real formation gets spatial reuse (helps) and hidden terminals (hurts); bounded by a sweep showing the idealised model is conservative to ≈300–400 m and optimistic by 15.7 % at 500 m | **DECLARED** (C3) |
| **i.i.d. per-frame loss** | closed-form V | real FANET loss is bursty. F11 proved V_D ≤ V_B under *any* correlation, so the **T3 ordering survives**; absolute V still assumes independence | **PARTLY OPEN** (C4) |
| **No sender-side CPU throughput constraint** | simpler optimizer | verified never to bind (worst case 13.9 % of one core; binds at ~360 rec/s vs our 20) | **DECLARED** (C5) |
| **K = 16 delta keyframe interval, unoptimized** | bounded scope | K is a real design variable left on the table; delta's 45 B depends on it | **DECLARED** (B5) |

#### 4. Wire format and cryptography

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **H_f = 44 B** | measured from `wire.py` | replaced an unreferenced 40 B assumption | it is *placement-dependent* in reality (A 45→51, D 81); the flat value understates A by 1 B and D by 37 B — **both conservative** | **MEASURED** (B1) |
| **CBOR text keys in the frame header** | readable, standard, deterministic, and self-describing on the wire | ⚠️ **QUANTIFIED 2026-08-28 (F44), and it costs a headline.** 29 of the 44 header bytes are key *names*; the same seven keys as small integers cost 7 B, so an integer-keyed profile gives **H_f = 22 B** and **B/record 94 → 76.5** (→ 66.5 with `src`/`seq` elided). Because T6's bound is `s_max = M − H_f − g_a`, that halving **makes EU868 DR3 feasible** and takes the exclusion from *four* of seven data rates to **three**. The readable format is bought at the price of one excluded data rate | **DECLARED — cost now measured, not asserted** (`placement/wire_profile.py`) |
| **Keeping the frozen text-keyed wire despite F44** | every frozen artifact stays bit-identical; D6 is not reopened; the reported byte cost becomes an **upper bound on an untuned design**, which is the conservative direction | the paper reports a boundary it could move itself, and must say so rather than imply the fourth exclusion is arithmetic | **DECLARED** (D6) |
| **Per-record `src` and `seq`** | independent, self-contained records | ⚠️ **10 B/record — ~14 % of the 72.0 B headline — is redundant** in placement B: the frame already carries `src` and `base_seq`, and every record in a self-batch shares a sender with consecutive sequence numbers. Cancels in the ratios, not in the absolute byte figure, and it inflates `s_min`, one of the three constants deciding DR3 | **ACCEPTED** (M5, D6 freezes the wire) |
| **32 B `prev_hash` per record (802.11)** | independent per-record tamper evidence | ~71 % of a delta record is incompressible hash; its CPU cost (2×2745.5 ns/record) is now charged too (D7) | **DECLARED** (F5) |
| **Per-frame chaining on LoRa only** | b 2→7 at DR5, **3.03×** the sustainable rate | two framings of one ledger; within a LoRa frame tamper-evidence rests on the frame signature rather than independent hashes — equivalent in strength, no longer independent | **DECLARED** (F5) |
| **BLS = 96 B (blspy min-pubkey)** | timings and size are coherent | the 48 B min-sig variant was specified originally; 96 B makes BLS lose the byte game outside multi-signer aggregation | **DECLARED** |
| **Ed25519 over ECDSA** | wins on ARM (259 vs 327 µs verify), the thesis platform | order **flips on x86**; the choice is platform-specific and the auth-byte result is identical either way (both 64 B) | **MEASURED** (D8/F6) |

#### 5. Measurement and reproducibility

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Energy composed from measured parts** | per-op timings and powers are all measured; **validated end-to-end** on four configurations | was ~32 % low; both causes found and fixed (D7 chain hash, D6 composed-pipeline power). **Residual +7.5…+14.3 %, all frame assembly.** Absolute energy is a **lower bound by ~10–14 %** | **MEASURED** (D1/F14) |
| **One `p_cpu_w` for all configurations** | keeps the model **predictive** — a per-config power would mean metering a design before you could model it | measured spread across four configurations is only **3.8 %**, so this holds. The old 0.634 W was wrong for a different reason: it came from *isolated primitives* and understated composed pipelines by 18.2 %. Now **0.749 W** | **MEASURED** (D6) |
| **LoRa arm is analysis-only** | the result is derivable from primary specs alone | **no hardware, no energy column, no measured validation** — must be stated in-chapter | **DECLARED** |
| **NS-3 validates throughput only** | the airtime/contention model is grounded | latency, energy and loss behaviour are **not** validated by simulation; "NS-3-validated" must not imply more | **OPEN** (D3) |
| **10 s NS-3 runs, not 30 s** | ~5000 busy periods/run × 10 seeds; tight CIs | a documented deviation from docs/04 §3 | **DECLARED** |
| **Frozen artifacts + staleness gate** | staleness cannot be committed unnoticed | every deliberate change costs a re-freeze | **DECLARED** |
| **Contiguous batch grids** | no quantized optima | larger sweeps. *Sparse grids caused F3 **and** understated F5 as 2.75× when the true value is 3.03×* | **FORCED** by F3/F5 |

#### 6. The 2026-10-06 revision — the design as one frame

*Numbers here are read from `results/raw/design_ladder.csv`, `e3_codec_loss.csv`,
`exclusion_matrix.csv` and `stream_baselines.csv`; capacities are deliberately not repeated —
quote them from the ladder, with their intervals.*

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **A keyframe in every frame (r = 1)** | every frame decodes alone, so V = 1 − p as T3 assumed | **3.0 B/record** in the first format (71.99 → 74.96), 3.5 B/record against r = 16 in the lean one. The saving quoted since July (−58.68 %) becomes −56.98 % for the first format | **FORCED** at ε ≤ p (T3′, F46) |
| **A second, lean frame format beside the frozen first** | the design exists as an object with a sender and a receiver; 43.25 B/record against 74.96 | two formats to explain; the first format's delta rows remain a byte model and say so (`sized_from`) | **DECLARED** (R2) |
| **One chain link per frame in the lean format** | 32 B per record becomes 35 B per frame | inside a frame, continuity rests on the frame signature, not on an independent hash per record — on 802.11 as well as LoRa | ⚠️ **OPEN — Mohamed** (`OPEN_ITEMS` G5) *(Corrected 2026-11-01: G5 was closed on 2026-10-08, Mohamed confirmed it.)* |
| **Batching four records** | fewer bytes and a quarter of the frames | a lost frame takes four records; a record waits up to 80 ms; and **a longer frame is lost more often at one bit error rate** — V = 0.943 where the one-record frame loses 5 % | **DECLARED** — the last cost was not stated before E10's `ber` rows |
| **Capacity simulated per configuration** | a V ≥ 0.95 capacity with a bootstrap interval, instead of one load ceiling that was off by up to 23 % | hours of simulation per change; a rung that was not simulated has **no** such capacity | **MEASURED** (R7, F50) |
| **The airtime line stated as a closed form** | a rule that predicted seven unseen configurations within 3.4 %, and says why a utilisation ceiling could not work | it is a fit: one loss level, one PHY rate, 5–50 frames/s, a simulator; its residuals are ordered by frame rate. It is never quoted as a capacity | **MEASURED** — held-out, pre-registered (F54) |
| **Send time redrawn within every period** | a run samples the channel, not one frozen phase configuration; per-run sd 0.034 → 0.0016 | not the published scenario's default; a real autopilot's jitter is unmeasured (G7). Mean delivery differs by 0.003 between the sources, and the strictly periodic crossings are 1–9 % lower — within the tolerance registered, not zero, and not yet explained *(Corrected 2026-11-01: the 1–9 % difference was withdrawn; it did not replicate on 1 260 fresh runs, F61, and the means agree, 0.0004 ± 0.0009.)* | **DECLARED** — by the rule registered before the runs (F51) |
| **N_max on the mean, at the grid** | the estimator registered in advance, and the LoRa arm's | coarse where the grid is; a per-run reading is stricter | **DECLARED** |
| **A graded exclusion verdict** | "excluded" means a content-independent floor exceeds the limit — arithmetic, not telemetry | the count *eight of twelve* joins five rates excluded by the signature alone with three excluded by header + link + signature + one record (124 B > 115 B); the second kind is conditional on carrying the link on air | **DECLARED** (R4, F47) |
| **Certificates as a second column** | both accountings visible | explicit certificates only; not in any simulated frame | **DECLARED** (R13) |
| **Stream-signing schemes modelled, not implemented** | five classical schemes in one table at this operating point | a saturation bound only, with our primitives in place of the papers' | **DECLARED** (R5) |
| **No typed results** | prose cannot drift from the artifacts, and a sentence that states a verdict is checked against them | LaTeX source is harder to read | **DECLARED** |
| **A shorter paper** | a results paper: the frame, the ladder, the exclusion | the LoRa capacity work and the audit history — the most distinctive material — are in the thesis and the methods paper, not the paper | **DECLARED** (R11, R12) |
| **Real telemetry from public logs** | a check chosen by a rule fixed in advance | nothing below 0.2 s spacing; the mean flatters a fast swarm (fixed wings need up to 13.2 B per delta) | **MEASURED**, limited (F52) |

---

#### The rows an examiner will press hardest

1. ~~**The 250 ms deviation**~~ — **resolved 2026-07-30**: the compliant (50 Hz, 100 ms) point is now
   primary and gives identical bytes. Kept in the list only as the historical entry. It was the only place a
   headline number depended on a choice looser than
   the applicable standard. Answer with the region: the mechanism is deadline-independent, only b
   depends on Λ·D_max, and the compliant point is reported.
2. **`1 − 1/b`** (§2) — answered by refusing to lead with that metric at all.
3. **D(b) has no channel-access delay** (§3) — the freshness constraint that *sets b* omits the
   dominant delay term at high load. Mitigated by reporting U, not by fixing the model.
4. **Energy is 10–14 % low** (§5) — was 32 %, root-caused and fixed; the residual is uncharged
   prototype framing overhead, measured and stated. Absolute values are lower bounds.
5. **A withdrawn theorem** (docs/02, ~~T7~~) — capacity was claimed to exclude at U ≥ 1; the
   validation experiment refuted it the same day. Kept visible, with the lesson recorded.
6. **"Was this design ever built?"** (§6) — until October 2026, no: it was a sum of sizes, and as
   published it missed its own verifiability target. Answer with the lean format, its receiver,
   and E10, which measures V with the codec in the loop.
7. **A batch is a longer frame** (§6) — at one bit error rate the design verifies 0.943 where a
   one-record frame loses 5 %. Stated in the paper; the comparisons are at equal *frame* loss.
8. **Contention is simulated, and the simulated source matters** (§6) — the capacities come from
   ns-3, and strictly periodic senders freeze their phases in it. Answered by the registered
   source study (the mean moves by 0.003, inside the tolerance set in advance) and by saying
   plainly that no radio has measured a capacity. ⚠️ Since 2026-10-09 two radios *have* been
   measured (item 9).
9. **Two radios, and which of their numbers to quote** (F73–F76, 2026-10-09). Three choices
   were made and each costs something.
   * *Quote the pooled 36 windows (1.13 / 0.79 / 0.56 of the model), not the registered session
     alone (1.00 / 0.80 / 0.46).* The registered session is the one that was predicted, and its
     verdict — held, held, failed — is reported as registered. But its top-load figure is the
     lowest of three sessions that should be the same, and quoting it alone overstates the miss.
     Cost: the pooled figure mixes frame burst on and off, on the evidence that it makes no
     difference there — which is an absence of evidence at this sample size, not a proof.
   * *Lead with the saturated result (12.4 % against 11.8 %).* It is the one place where the
     contention is isolated and the one prediction that held cleanly. Cost: it is the regime
     furthest from the operating point, and a reader may take "the rule holds" for more than
     two saturated stations show. The paper says "no capacity was measured" in the same
     paragraph for that reason.
   * *Say the cause of the shortfall has not been shown.* The radio's handling of its own
     queued frames is measurably non-standard and is the candidate the saturated test leaves
     standing. Naming it as the cause would read better and is not established.

   > **Corrected 2026-11-03 (F115, G27).** The saturated test does not isolate the contention:
   > every saturated station holds a queue, so the radio's own-queue rule acts there too. It
   > constrains that rule. Five rules for it, each set from the single sender's spacing, were
   > tested. With frame burst on none fits the saturated result; with it off, the one that does
   > misses the loss below saturation. "The candidate the saturated test leaves standing" is
   > therefore withdrawn. The choice itself, *say the cause has not been shown*, stands and is
   > now better founded.
10. **The prototype's receiver does not keep up with 124 nodes on one core** (F77) — 57. The
    capacity is the channel's; the ceiling in the table is cryptography's. Answered by giving
    the number beside the ceiling, not by quoting only the ceiling.

