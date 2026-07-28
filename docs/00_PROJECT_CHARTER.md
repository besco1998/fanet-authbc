# 00 — PROJECT CHARTER

## 1. One-paragraph statement
Payload compression (Pillar 1, published) shifts the dominant on-air cost of an
authenticated blockchain telemetry ledger from data to cryptography: a fixed 64 B
signature is 33% of a CBOR record's bytes and 62% of a delta record's. This thesis
formulates and solves the **joint optimization of encoding × authentication placement ×
signature scheme × batching granularity** for per-UAV hash-chained telemetry ledgers over
802.11 FANET links, under **security, wireless-loss-robustness, and verification-throughput
constraints** — with closed-form results (T1–T6), validation in an instrumented channel
emulator and NS-3, and hardware ground truth on **2× Raspberry Pi 4** (the docs' original
"4× RPi4" exceeds the actual inventory; the campaign is tiered in `hw/SETUP.md`). The LoRa arm (doc 30)
extends the same framework to low-rate links afterward.

## 2. Research questions
- **RQ1** How large is authentication overhead after compression, and where is the
  payload-size threshold below which it dominates? (T1, E1)
- **RQ2** Which authentication placement minimizes on-air bytes while keeping records
  verifiable under loss — and what does self-batching vs cross-signer aggregation change?
  (T2, T3, E2, E3)
- **RQ3** When does an aggregatable scheme (BLS) beat a fast conventional scheme
  (Ed25519) on energy/latency, as a function of relay fraction, arrival rate, and the
  radio/CPU power ratio? (T4, E4)
- **RQ4** What is the end-to-end optimal configuration, how much does it beat the naive
  and Pillar-1-only baselines, and do the analytical models survive NS-3 contention and
  real hardware? (T5, E5, RPi4 campaign)

## 3. Contributions (honest scoping, novelty ~6)
1. Quantified **overhead-dominance characterization** for compressed authenticated
   FANET ledgers (T1) — the motivating result.
2. **Placement theory**: self-batch vs cross-signer aggregation distinction; frame-level
   optimum and the "compression pays ×A" amplification (T2), **with its regime boundary (T2a): A
   applies only where the MTU caps the batch — under a freshness bound the cap is ⌊Λ·D_max⌋, which
   is independent of record size, and compression then pays exactly 1×. On 802.11 A is never
   operative; on low-rate links it is** (T5); the **loss-robustness
   frontier** proving frame-level Pareto-dominates block-level under realistic loss (T3).
3. **Scheme-selection rule** with the measured Ed25519↔BLS crossover (T4) — regime-dependent,
   hardware-grounded.
4. **Validated models**: Bianchi-based airtime/throughput and the energy model, checked
   against NS-3 and RPi4, with honest corrections where they miss.
5. **Feasibility envelope (the load-bearing co-design claim, reframed 2026-07-29).** Joining the byte
   model to the NS-3-validated broadcast model gives the largest neighbourhood each configuration can
   serve: **N ≤ 25** (A+JSON), **N ≤ 32** (A+CBOR Pillar-1), **N ≤ 103** (co-designed) — a **3.2×**
   larger swarm on the same medium. ⚠️ **This, not the auth-byte percentage, is the contribution that
   requires all four axes**: the auth-byte ratio reduces algebraically to **1 − 1/b**, invariant to
   H_f, g_a, encoding and scheme (audit **F13**). Report the *decomposition* (total bytes −58.7 %:
   placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral), never the bare 75 %.
6. **Authentication-exclusion threshold (T6)**: a link admits per-frame-verifiable telemetry only if
   M ≥ H_f + g_a + s_min, and T3 (n_max = 1 at ε ≤ p) closes the fragmentation escape — bounding
   where co-design is possible at all, and excluding the four longest-range LoRa modes outright.
7. **Reproducible open testbed + dataset** (repo, seeds, raw CSVs, figures pipeline).

Target venues: Ad Hoc Networks / MDPI Drones primary; IEEE IoT Journal if results are strong.

## 4. Explicit non-goals (guard rails against scope creep)
- No new cryptographic primitive, no new consensus protocol, no PQC implementation
  (PQ sizes appear only as analytical datapoints), no mobility modeling (loss p is a
  channel parameter), no multi-hop routing research. ⚠️ **LoRa: superseded 2026-07-28** — the arm
  now ships in THIS thesis as a scoped *modelling* chapter ("Generalisation: the low-rate regime"),
  carrying **T6**. Analysis only: no hardware, no energy column, no measured validation.

## 5. Timeline & first-results milestones (calendar-fast, correctness-first)
| Phase | Weeks | Deliverable | First numbers |
|---|---|---|---|
| P0 bootstrap | wk 1 (days 1–2) | repo, CI, Makefile, CLAUDE.md live | — |
| P1 microbench | wk 1 (days 2–5) | crypto+encoding timings & sizes (x86) | **Day 3: T1 table + scheme timing table** |
| P2 ledger+wire | wk 2 | chain, canonical frames, KAT tests green | — |
| P3 placements+channel | wk 3 | emulator, all placements end-to-end | **Week 3: E1–E3 plots (dominance, cure, loss frontier)** |
| P4 experiments E1–E3 | wk 3–4 | frozen CSVs + figures | — |
| P5 models+optimizer | wk 4–5 | Bianchi/energy modules, optimizer, E4 (x86) | **Week 5: crossover + optimum tables** |
| P6 NS-3 validation | wk 6–8 | scenario, Bianchi-vs-NS-3, E5 | **Week 8: model-validation figure** |
| P7 RPi4 campaign | wk 9–12 (flexible) | hardware timings + energy; E4/E5 re-run | **Week 12: hardware tables** |
| P8 consolidation+paper | wk 12–16 | analysis notebook, paper skeleton→draft | — |
Buffer: ~2 months before the March-2027 deadline; the LoRa arm (doc 30) slots after P8
if time allows, else becomes the journal extension.

## 6. Decision log (⚠️ = requires Mohamed's approval when reached)
- ⚠️ D0: one-time GitHub authentication (`gh auth login`) and git identity — the ONLY
  manual setup step; everything after (including repo creation) is agent-executed.
- ⚠️ D7: execution mode after P0 — serial, 2-lane, or 3-lane parallel (see
  docs/07_PARALLEL_EXECUTION_PLAN.md; parallel compresses ~8 weeks to ~5).
- D1 (settled, **amended 2026-07-28**): 802.11 arm first; the LoRa arm ships as a scoped modelling
  chapter in this thesis (not deferred to doc 30). See DECISIONS.md.
- D2 (settled): Ed25519 self-batch is the frame-batching default; BLS reserved for
  cross-signer aggregation (relay/attestation) — the audit-corrected architecture.
- ⚠️ D3: true Ed25519 *batch verification* needs a native binding (see doc 06 §4);
  default = sequential verify with claims scoped accordingly; approve before any Rust step.
- ⚠️ D4: NS-3 version pin at first build (3.41 recommended) — approve deviations.
- ⚠️ D5: energy meter model for P7 (UM25C vs INA219) — approve purchase.
- ⚠️ D6: any change to frozen experiment configs after data collection starts.
