# Open items register — everything not yet closed
*Created 2026-07-28 by the pre-P8 full audit. **This is the single tracked list.** Anything
"remaining", "deferred", "assumed" or "future work" belongs here, not scattered in prose.
Status: `OPEN` · `DECIDED` (needs implementing) · `ACCEPTED` (a stated limitation, will not be fixed).*

Ordered by what a thesis examiner would hit first.

---

## A. Claims and framing

| # | Item | Status | Why it matters | Action |
|---|---|---|---|---|
| **A1** | Headline framing | **CLOSED 2026-07-29** | Reframed everywhere: paper abstract/results/conclusion, charter §3, narrative. Headline is now **total bytes −58.7 %** reported as a **decomposition** (placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral), and the load-bearing claim is the **feasibility envelope** (N_max 103 vs 32 vs 25). Two new paper tables + `tab:envelope`. Pinned by `test_headline_decomposition.py` | — |
| **A2** | b=4 is fixed by inputs, not discovered | **CLOSED 2026-07-29** | Stated plainly in the paper's attribution paragraph and docs/02 §7a, which shows b depends only on the product Λ·D_max | — |
| **A3** | `[VERIFY]` citations in `paper/main.tex` and `docs/TECHNICAL_NARRATIVE.md` §2 | OPEN — **deferred by Mohamed to start of P8** | Thematic positioning is right; exact references unconfirmed | One consolidated literature pass at P8 |
| **A4** | Autopilot stream rates | **CLOSED 2026-07-29** | PX4 confirmed at source (NORMAL 5, OSD/CONFIG 10, **ONBOARD 50** Hz). ArduPilot corrected: the default is **vehicle-specific** — Plane/Rover 1 Hz, Sub 3 Hz, **Copter 0 Hz** (on-demand), not a universal 1 Hz. Additionally anchored to **3GPP TS 22.125 R-5.2.2-010** (≥10 msg/s); Λ=20 is bracketed by both | — |
| **A5** | T6's 48 B signature floor | **CLOSED 2026-07-29** | Cited to **draft-irtf-cfrg-bls-signature-05** (Boneh et al.), `minimal-signature-size` = 48 B G1. **Correction: the draft states 126-bit security, not 128** — fixed in docs/02 T6 | — |

## B. Unreferenced or assumed constants

| # | Item | Status | Bias | Action |
|---|---|---|---|---|
| **B1** | H_f | **CLOSED 2026-07-29** | **Measured = 44 B** from `placement/wire.py` (was an assumed 40). Placement-dependent (A 45→51, D 81); the flat 44 B is conservative for both. Headline unmoved; b_max 31→30; total cut 58.30→58.68 % | — |
| **B2** | N_local | **CLOSED 2026-07-29** | Reported as a **curve**, not an assumption: N_max = **103** (co-design) vs **32** (A+CBOR) vs **25** (A+JSON). N=50 is quoted because it lies between — a swarm the baselines cannot serve and the co-design can. New `ENVELOPE` rows in `capacity_envelope.csv` | — |
| **B3** | D_max | ⚠️ **CITED — and the citation is STRICTER than us** | **3GPP TS 22.125 R-5.2.2-011 requires ≤100 ms** for direct UAV-to-UAV broadcast; we run 250 ms. Recoverable because only Λ·D_max matters: (50 Hz, 100 ms) is compliant, PX4-real, and gives the **identical** b=4 / 75 % / 58.68 %. Full sweep in docs/02 §7a | ⚠️ **Mohamed decides:** keep 250 ms as a declared deviation, or re-anchor to (50 Hz, 100 ms) and report N ≤ 35 instead of N = 50 |
| **B4** | Loss grid p | **CLOSED 2026-07-29** | Justified by **mechanism**: 802.11 broadcast carries no ACK and is never retransmitted, so the receiver sees the raw channel error rate. TS 22.125 Table 7.2-1's 99.9 % is for *managed* C2 links with ARQ — our grid is 20–100× more pessimistic (conservative). **T6 needs only ε ≤ p**, so it holds across the whole grid | — |
| **B5** | **K = 16** delta keyframe interval — fixed, never optimized | ACCEPTED (docs/01 §1 says so) | Affects delta's 45 B | Stated as out of scope; re-check at P8 that the thesis says this |
| **B6** | MTU = 1500, 802.11a PHY constants (20/16/9/34 µs, 6 Mb/s, 36 B MAC) | **CLOSED** | — | All standard 802.11a values; MAC overhead cross-checked against NS-3 3.41 (D9/audit A1) |
| **B7** | LoRa constants (SF/BW/payload/sensitivity/duty cycle) | **CLOSED** | — | Every value transcribed from SX1276 Rev.7 and RP002-1.0.3 with section numbers |

| **B8** | ⚠️ **NEW (2026-07-29): at N=50 the 3GPP 100 ms bound is unsatisfiable on 802.11a at all** — every variant either saturates the channel (U=1.42/1.39) or forbids batching (b=1) | OPEN — reported as a finding | An 802.11-side impossibility of the same kind as T6: the *medium*, not the cryptography, forecloses it | Feature it in the paper alongside T6; it is evidence for the feasibility framing (A1) |

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
| **D1** | End-to-end energy validation | **PARTIALLY CLOSED 2026-07-29 — and it found a defect (F14)** | Composition half done (needs no meter, since power enters linearly): the model has **no chain-hash term**, under-predicting CPU by **+7.97 %**, and **asymmetrically** — optimized +6.73 % vs baseline +2.52 %, so it **overstates the optimized config's energy advantage by ~4 points**. Meter half blocked: `hw/validate_energy_e2e.py` is written and smoke-tested but the RPi4s are powered down | (a) power the boards and run the harness; (b) add an **ARM** SHA-256 timing to the P1 harness, then add the term and re-freeze — not patchable with the x86 number we have |
| **D2** | **The LoRa arm has no measurement of any kind** | ACCEPTED — Mohamed's "scoped chapter" decision | Chapter must say so in-chapter: no hardware, no energy column |
| **D3** | NS-3 validates **saturation throughput** only — not latency, not energy, not loss behaviour | OPEN | Say so; do not let "NS-3-validated" imply more than throughput |
| **D4** | Hardware is **2× RPi4** (charter said 4×; `hw/SETUP.md` records the real inventory) | **CLOSED 2026-07-28** | Charter corrected |
| **D5** | RPi3 / BeagleBone cross-platform points | OPEN — optional | "Secondary/stretch" tiers in `hw/SETUP.md`; only add generalization breadth |

## E. Process and reproducibility

| # | Item | Status | Action |
|---|---|---|---|
| **E1** | `lora_eu868.csv`, `lora_codesign.csv`, `capacity_envelope.csv` were **outside the frozen gate** | **CLOSED 2026-07-28** | Added to `_CASES`; gate is now 13 tests and all three re-derive byte-identically |
| **E2** | docs/03 and docs/07 stale | **CLOSED 2026-07-29** | Both marked **HISTORICAL** with a banner pointing at DECISIONS / OPEN_ITEMS / TECHNICAL_NARRATIVE |
| **E3** | Parallel-lane status files | **CLOSED 2026-07-29** | Marked historical, and annotated that D7 resolved to serial — the lanes were never used |
| **E4** | docs/04 §3 / docs/06 §2 wrong NS-3 references | **CLOSED — were already correct** | Checked 2026-07-29: both already say 10 s × 10 seeds, PacketSocket+PacketSink (not FlowMonitor), and `ns3/parse_ns3.py`. The DECISIONS entries saying "to be amended at P8" were themselves stale |
| **E5** | `bench/micro.py` at 30 % test coverage (repo total 91 %) | ACCEPTED — low | Measurement plumbing, exercised by the frozen gate through `p1_sizes` |
| **E6** | Missing figures | **CLOSED 2026-07-29** | `analysis/figures_envelope_lora.py` produces `fig_envelope.png` (N_max per config), `fig_t6_exclusion.png` (T6 tiers over EU868) and `fig_lora_chain.png` (F5). Visually checked, not just generated |

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
