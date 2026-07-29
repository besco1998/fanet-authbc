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

| **B8** | Medium-exclusion finding | ⚠️ **CLOSED 2026-07-29 — promoted to T7, then T7 WITHDRAWN the same day** | T7 claimed capacity excludes at **U ≥ 1**. Its own validation experiment (D3) refuted it: NS-3 delivers **98.8 % at U = 1.00**, and the V≥0.95 crossing is at **U ≈ 2.80**, so the 3GPP-compliant point (U=1.39) is feasible and **the 75 % cut is achievable at the deadline**. T7 is withdrawn; the surviving mechanism is a **cost** — meeting the 100 ms bound halves the swarm (N≤233 → N≤116) and changes nothing in bytes | Lesson recorded in docs/02: the claim was published before the experiment already scheduled to test it |

## C. Model scope — what the models do not cover

| # | Item | Status | Action |
|---|---|---|---|
| **C1** | DCF channel-access delay absent from D(b) | **CLOSED 2026-07-29 — MEASURED, and it is negligible** | NS-3 non-saturated sweep (`ns3_delay.csv`): the omitted access delay is **+0.033 ms** at the reference point and **+2.2 ms even at 9× saturation load**, against a 250 ms budget. D(b) is validated. The structural reason: **802.11 broadcast has no ARQ and no queue buildup**, so overload degrades *delivery*, never latency |
| **C2** | Saturation models at a non-saturated point | **PARTLY CLOSED 2026-07-29** | Measurement shows the consequence precisely: saturation throughput **understates usable capacity by ≈2.8×** (98.8 % delivery still at U=1.00; V=0.95 crossing at U≈2.80). So U is a **conservative admission metric, not a feasibility boundary** — the envelope figures computed at U<1 are lower bounds, and the comparative ratio is unaffected since all are computed alike |
| **C3** | **No mobility, no spatial reuse, no hidden terminals** — single collision domain | ACCEPTED, in the paper's limitations | Real formations get both spatial reuse (helps) and hidden terminals (hurts); neither is modelled |
| **C4** | **Loss is i.i.d. per frame**; real FANET loss is bursty | PARTLY CLOSED | F11 proved V_D ≤ V_B under *any* correlation (joint ≤ marginal), so the **T3 ordering survives**. Absolute V values still assume independence |
| **C5** | **No sender-side CPU throughput constraint** in the optimizer | ACCEPTED | Verified never to bind: worst case (BLS inline) is 13.9 % of one core; it would bind at ~360 rec/s vs our 20 |
| **C6** | Key compromise, consensus, multi-hop routing | ACCEPTED — charter scope | — |

## D. Validation gaps

| # | Item | Status | Action |
|---|---|---|---|
| **D1** | End-to-end energy validation | **CLOSED 2026-07-29 — measured, then the model was FIXED** | Initially ~32 % low. Root-caused to D7 (no chain-hash term) + D6 (`p_cpu_w` from isolated primitives). Both fixed; **residual is now +7.5 % to +14.3 %** across four configurations, all of it frame assembly. The interim "overstates the optimized advantage" claim is **retracted** — measured advantage 2.035× vs predicted 1.985× | Energy figures are **lower bounds by ~10–14 %** (uncharged CPython framing). Deliberate: charging it would model our prototype, not the design |
| **D2** | LoRa arm had no measurement of any kind | **CLOSED 2026-07-29 — now simulated** | NS-3.48 + signetlabdei LoRaWAN module gives the multi-node capacity envelope, the one LoRa quantity that is not analytically derivable: **N_max = 5** at DR5 (V≥0.95), a sharp ALOHA cliff (1.0000 at N=5 → 0.8656 at N=8). Combined with the 121× per-node rate gap this is **≈2500× less aggregate capacity** than the 802.11 arm. Still **not hardware**: no LoRa radio metered, no energy column — the chapter must say "simulated bound", not "measured" |
| **D3** | NS-3 validated throughput only | **CLOSED 2026-07-29** | New scenario `ns3/authbc-delay.cc` + `make sim-ns3-delay` validate **delivery delay and delivered fraction** under non-saturated load (the saturated scenario cannot measure delay — an always-backlogged queue diverges by construction). Artifact `results/raw/ns3_delay.csv`. Energy is separately validated end-to-end by D1 |
| **D4** | Hardware is **2× RPi4** (charter said 4×; `hw/SETUP.md` records the real inventory) | **CLOSED 2026-07-28** | Charter corrected |
| **D6** | `p_cpu_w` methodology | **CLOSED 2026-07-29 — and the premise was wrong** | The question was *"is p_cpu_w configuration-dependent?"*. Metered on all four E5 configurations: **0.732 / 0.744 / 0.755 / 0.760 W — a 3.8 % spread**, so **no**. What was wrong is that 0.634 W came from *isolated primitives* and understates any composed pipeline by **18.2 %**. Adopted **0.749 W** (median of four composed pipelines); one constant keeps the model predictive. Artifact `results/hw/energy/p_cpu_w_composed.md` |
| **D7** | ARM SHA-256 timing / chain-hash term | **CLOSED 2026-07-29** | Measured on authbc-pi4a with the P1 harness: **2745.5 ns** (45 B = prev_hash 32 + delta body 13). Added to `Measured.t_hash_s` and charged **2× per record** (sender extends the chain, receiver verifies it) — it does **not** amortize over b. E5 optimized energy 112.08 → **115.56 µJ/rec**, exactly the predicted +3.481. Bytes untouched. Artifact `results/hw/p1_hash.authbc-pi4a.csv`; pinned by `test_chain_hash_term.py` |
| **D5** | RPi3 / BeagleBone cross-platform points | OPEN — optional | "Secondary/stretch" tiers in `hw/SETUP.md`; only add generalization breadth |

## E. Process and reproducibility

| # | Item | Status | Action |
|---|---|---|---|
| **E1** | `lora_eu868.csv`, `lora_codesign.csv`, `capacity_envelope.csv` were **outside the frozen gate** | **CLOSED 2026-07-28** | Added to `_CASES`; gate is now 13 tests and all three re-derive byte-identically |
| **E2** | docs/03 and docs/07 stale | **CLOSED 2026-07-29** | Both marked **HISTORICAL** with a banner pointing at DECISIONS / OPEN_ITEMS / TECHNICAL_NARRATIVE |
| **E3** | Parallel-lane status files | **CLOSED 2026-07-29** | Marked historical, and annotated that D7 resolved to serial — the lanes were never used |
| **E4** | docs/04 §3 / docs/06 §2 wrong NS-3 references | **CLOSED — were already correct** | Checked 2026-07-29: both already say 10 s × 10 seeds, PacketSocket+PacketSink (not FlowMonitor), and `ns3/parse_ns3.py`. The DECISIONS entries saying "to be amended at P8" were themselves stale |
| **E5** | `bench/micro.py` coverage | **CLOSED 2026-07-29** | "Measurement plumbing" failed as a justification: two bugs were introduced into `measure_crypto` on 2026-07-29 and **both were caught by hardware, not tests** (a missing keyword-only arg, and a row reporting `msg_bytes=200` for a 45 B input — a silent provenance error). `test_micro_rows.py` now pins the row contract, the per-op input sizes and the schema |
| **E6** | Missing figures | **CLOSED 2026-07-29** | `analysis/figures_envelope_lora.py` produces `fig_envelope.png` (N_max per config), `fig_t6_exclusion.png` (T6 tiers over EU868) and `fig_lora_chain.png` (F5). Visually checked, not just generated |

## F. Carried decisions needing implementation

| # | Item | Status | Action |
|---|---|---|---|
| **F1** | Paper restructure | **CLOSED 2026-07-29** | Done in the decided shape: T6 added as theory (§III-F), new §VI "Generalisation: the Low-Rate Regime" (T6 on EU868 + chaining + the N_max=5 capacity result), Results reordered feasibility-first. 7 pages, builds clean. Fixed three stale claims en route (T5's MTU wording, the missing chain-hash term, E4's x86 ratio) and caught one repeat of the retracted T7 error before it shipped |
| **F2** | Abstract/conclusion framing | **CLOSED 2026-07-29** | Rewritten in the A1 pass: abstract leads with total bytes + decomposition + the feasibility envelope; conclusion states the `1−1/b` result explicitly. One residual: the success criterion is still phrased as an *auth-byte* target (§I), which is fine — it is the pre-registered criterion and must not be moved after the fact |

---

## What is genuinely settled
Freshness enforced as constraint + objective (F10) · Ma & Chen broadcast model, cited, ≤0.36 % vs
NS-3 (F9) · NS-3 sink lifetime (F8) · OFDM-quantised airtime (D9) · 30-seed size protocol (F4) ·
BLS = 96 B everywhere (F1) · measured powers and ARM timings (P7b) · T2a binding-ceiling theory ·
F11 loss-correlation ordering · F12 aggregate-vs-per-node arrival · T6 · F5 on LoRa · LoRa PHY
constants · the frozen-staleness gate.
