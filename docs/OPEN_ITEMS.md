# Open items register — everything not yet closed
*Created 2026-07-28 by the pre-P8 full audit. **This is the single tracked list.** Anything
"remaining", "deferred", "assumed" or "future work" belongs here, not scattered in prose.
Status: `OPEN` · `DECIDED` (needs implementing) · `ACCEPTED` (a stated limitation, will not be fixed).*

Ordered by what a thesis examiner would hit first.

---

## A. Claims and framing

| # | Item | Status | Why it matters | Action |
|---|---|---|---|---|
| **A1** | **The auth-byte headline is `1 − 1/b`** — encoding and scheme contribute zero; H_f and g_a cancel identically (audit **F13**) | **OPEN — highest priority** | Presented as "co-optimizing four axes cuts 75 %", it invites *"is your result just the definition of batching?"*, and for that metric the answer is yes | Reframe: lead with the **joint-feasibility** result (baselines are *unrunnable* at N=50, Λ=20) and report the **decomposition table**, not the single number. Pinned by `test_headline_decomposition.py` |
| **A2** | `b = 4` is not an optimizer output — it is ⌊Λ·D_max⌋ minus the airtime correction, i.e. fixed by two **inputs** | OPEN | Same exposure as A1: the "optimum" confirms arithmetic rather than discovering it | State it plainly; the genuine search happens on the 4-objective frontier, not on b |
| **A3** | `[VERIFY]` citations in `paper/main.tex` and `docs/TECHNICAL_NARRATIVE.md` §2 | OPEN — **deferred by Mohamed to start of P8** | Thematic positioning is right; exact references unconfirmed | One consolidated literature pass at P8 |
| **A4** | Λ_i = 20 rec/s is sourced to **PX4/ArduPilot source files that were not opened** — the rates came from a search, not from reading `mavlink_main.cpp` | OPEN | docs/01 §1 presents a table with file-level citations, which reads as verified | Open the two files and confirm, or downgrade the citation to "reported rates" |
| **A5** | T6's "48 B is the signature floor at 128-bit security" is **uncited** | OPEN | It is the load-bearing step in T6's tier-1 escape analysis | Cite a short-signature reference, or restate as "the smallest signature in this study's scheme set" |

## B. Unreferenced or assumed constants

| # | Item | Status | Bias | Action |
|---|---|---|---|---|
| **B1** | **H_f = 40 B** — never derived, never measured; feeds T2, T2a, T6, b_max, U, energy | OPEN — documented at docs/01 **§2a** | **Zero** on the headline (cancels, F13). **Non-zero** on T6 tiers, b_max, total bytes, U | Measure it from `placement/wire.py`, or report T6 and the byte tables over a *range* of H_f |
| **B2** | **N_local = 50** neighbours — no citation for swarm size | OPEN | Sets the aggregate verify load and U; drives the F12 "baselines unrunnable" result | Cite a FANET density source, or present U as a curve over N (the data already exists in `capacity_envelope.csv`) |
| **B3** | **D_max = 250 ms** freshness budget — no citation | OPEN | With Λ, *determines* b and therefore the headline (A1/A2) | Cite a control/telemetry latency requirement, or sweep it |
| **B4** | **p ∈ {0.02, 0.05, 0.10}** loss grid — no citation | OPEN | ε = p = 0.05 is what forces n_max = 1 in T6 | Cite a FANET PER measurement, or present as a sensitivity range |
| **B5** | **K = 16** delta keyframe interval — fixed, never optimized | ACCEPTED (docs/01 §1 says so) | Affects delta's 45 B | Stated as out of scope; re-check at P8 that the thesis says this |
| **B6** | MTU = 1500, 802.11a PHY constants (20/16/9/34 µs, 6 Mb/s, 36 B MAC) | **CLOSED** | — | All standard 802.11a values; MAC overhead cross-checked against NS-3 3.41 (D9/audit A1) |
| **B7** | LoRa constants (SF/BW/payload/sensitivity/duty cycle) | **CLOSED** | — | Every value transcribed from SX1276 Rev.7 and RP002-1.0.3 with section numbers |

## C. Model scope — what the models do not cover

| # | Item | Status | Action |
|---|---|---|---|
| **C1** | **DCF channel-access delay is absent from D(b)** — the M/M/1 term covers a node's own queue (ρ≈0.002), not medium contention | ACCEPTED, documented in `channel_utilisation` and docs/02 §7 | D(b) is a **lower bound**, credible only at low U. We report U alongside it (0.55 at the operating point). Do **not** silently quote D(b) near U→1 |
| **C2** | **Bianchi/Ma&Chen are saturation models**, applied at a non-saturated operating point (U=0.55) | ACCEPTED | Correct as a *capacity* bound, which is how U uses it. It is **not** valid for delay at our load — this is the same limitation as C1 |
| **C3** | **No mobility, no spatial reuse, no hidden terminals** — single collision domain | ACCEPTED, in the paper's limitations | Real formations get both spatial reuse (helps) and hidden terminals (hurts); neither is modelled |
| **C4** | **Loss is i.i.d. per frame**; real FANET loss is bursty | PARTLY CLOSED | F11 proved V_D ≤ V_B under *any* correlation (joint ≤ marginal), so the **T3 ordering survives**. Absolute V values still assume independence |
| **C5** | **No sender-side CPU throughput constraint** in the optimizer | ACCEPTED | Verified never to bind: worst case (BLS inline) is 13.9 % of one core; it would bind at ~360 rec/s vs our 20 |
| **C6** | Key compromise, consensus, multi-hop routing | ACCEPTED — charter scope | — |

## D. Validation gaps

| # | Item | Status | Action |
|---|---|---|---|
| **D1** | **The energy model is never validated end-to-end** — powers and timings are measured, but the composed µJ/record is not compared against a wall measurement | OPEN | Either measure one configuration end-to-end on the RPi4, or state explicitly that energy is *composed from measured parts*, not measured |
| **D2** | **The LoRa arm has no measurement of any kind** | ACCEPTED — Mohamed's "scoped chapter" decision | Chapter must say so in-chapter: no hardware, no energy column |
| **D3** | NS-3 validates **saturation throughput** only — not latency, not energy, not loss behaviour | OPEN | Say so; do not let "NS-3-validated" imply more than throughput |
| **D4** | Hardware is **2× RPi4** (charter said 4×; `hw/SETUP.md` records the real inventory) | **CLOSED 2026-07-28** | Charter corrected |
| **D5** | RPi3 / BeagleBone cross-platform points | OPEN — optional | "Secondary/stretch" tiers in `hw/SETUP.md`; only add generalization breadth |

## E. Process and reproducibility

| # | Item | Status | Action |
|---|---|---|---|
| **E1** | `lora_eu868.csv`, `lora_codesign.csv`, `capacity_envelope.csv` were **outside the frozen gate** | **CLOSED 2026-07-28** | Added to `_CASES`; gate is now 13 tests and all three re-derive byte-identically |
| **E2** | `docs/03_IMPLEMENTATION_GUIDE.md` and `docs/07_PARALLEL_EXECUTION_PLAN.md` untouched since 2026-07-03 | OPEN — low | Review for drift at P8, or mark historical |
| **E3** | `docs/status/lane1.md`, `lane2.md` stale (parallel-execution lanes, last touched 07-04/07-09) | OPEN — low | Mark historical; D7 execution mode never went parallel |
| **E4** | `docs/04 §3` and `docs/06 §2` describe a 30 s NS-3 run and a `parse_flowmon.py` that does not exist | OPEN | Recorded in DECISIONS; amend the docs at P8 |
| **E5** | `bench/micro.py` at 30 % test coverage (repo total 91 %) | ACCEPTED — low | Measurement plumbing, exercised by the frozen gate through `p1_sizes` |
| **E6** | No figure for the LoRa arm, T6, or the capacity envelope | OPEN | Needed for the scoped chapter |

## F. Carried decisions needing implementation

| # | Item | Status | Action |
|---|---|---|---|
| **F1** | **Paper restructure** — 802.11 co-design as the measured core, then "Generalisation: the low-rate regime" carrying T6 | **DECIDED, not started** | This is the P8 deliverable. Must absorb A1/A2's reframing |
| **F2** | Abstract/conclusion still claim the four-axis framing corrected by F13 | OPEN | Rewrite with the decomposition |

---

## What is genuinely settled
Freshness enforced as constraint + objective (F10) · Ma & Chen broadcast model, cited, ≤0.36 % vs
NS-3 (F9) · NS-3 sink lifetime (F8) · OFDM-quantised airtime (D9) · 30-seed size protocol (F4) ·
BLS = 96 B everywhere (F1) · measured powers and ARM timings (P7b) · T2a binding-ceiling theory ·
F11 loss-correlation ordering · F12 aggregate-vs-per-node arrival · T6 · F5 on LoRa · LoRa PHY
constants · the frozen-staleness gate.
