# Trade-off register — what every decision bought, and what it gave up

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

## 1. The operating point

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

## 1a. LoRa channel count — why "use as many channels as possible" is right for a gateway and wrong for us

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


## 2. What is claimed, and how

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Headline = total bytes (−58.68 %), reported as a decomposition** | honest attribution | claim matches evidence; all four axes genuinely contribute to *total* bytes | a smaller, less quotable number than the 75 % it replaces | **FORCED** by F13 |
| **Never quote the bare 75 % auth cut** | — | forecloses *"is your result just the definition of batching?"* — for that metric it is: the ratio is **1 − 1/b**, invariant to H_f, g_a, encoding and scheme | the most memorable number in the thesis | **FORCED** by F13 |
| **Load-bearing claim = feasibility envelope** | N_max 25 / 32 / **103** | a capability statement that genuinely needs all four axes *plus* the channel model | depends on the channel model's validity, which is validated for throughput only (D3) | **DECLARED** |
| **Report both the compliant and the declared operating point** | costs nothing (identical bytes) | kills the "you picked a loose bound" objection outright | two numbers to explain instead of one | **DECLARED** |

## 3. Model scope — what is deliberately not modelled

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **No DCF channel-access delay in D(b)** | tractable closed form | **measured negligible**: +0.046 ms at the reference point, +2.2 ms even at 6.7× saturation load, against 250 ms. Broadcast has no ARQ so it cannot queue — overload degrades *delivery*, not latency | **MEASURED** (C1/D3) |
| **Saturation channel models at a non-saturated point** | Bianchi / Ma & Chen are validated and closed-form | measured to understate usable capacity by **≈2.8×**; U<1 is *sufficient, not necessary*, so every N_max computed that way is a **lower bound**. Comparative ratios unaffected | **MEASURED** (C2/D3) |
| **Single collision domain; no mobility, spatial reuse or hidden terminals** | one clean, validated regime | a real formation gets spatial reuse (helps) and hidden terminals (hurts); bounded by a sweep showing the idealised model is conservative to ≈300–400 m and optimistic by 15.7 % at 500 m | **DECLARED** (C3) |
| **i.i.d. per-frame loss** | closed-form V | real FANET loss is bursty. F11 proved V_D ≤ V_B under *any* correlation, so the **T3 ordering survives**; absolute V still assumes independence | **PARTLY OPEN** (C4) |
| **No sender-side CPU throughput constraint** | simpler optimizer | verified never to bind (worst case 13.9 % of one core; binds at ~360 rec/s vs our 20) | **DECLARED** (C5) |
| **K = 16 delta keyframe interval, unoptimized** | bounded scope | K is a real design variable left on the table; delta's 45 B depends on it | **DECLARED** (B5) |

## 4. Wire format and cryptography

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

## 5. Measurement and reproducibility

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **Energy composed from measured parts** | per-op timings and powers are all measured; **validated end-to-end** on four configurations | was ~32 % low; both causes found and fixed (D7 chain hash, D6 composed-pipeline power). **Residual +7.5…+14.3 %, all frame assembly.** Absolute energy is a **lower bound by ~10–14 %** | **MEASURED** (D1/F14) |
| **One `p_cpu_w` for all configurations** | keeps the model **predictive** — a per-config power would mean metering a design before you could model it | measured spread across four configurations is only **3.8 %**, so this holds. The old 0.634 W was wrong for a different reason: it came from *isolated primitives* and understated composed pipelines by 18.2 %. Now **0.749 W** | **MEASURED** (D6) |
| **LoRa arm is analysis-only** | the result is derivable from primary specs alone | **no hardware, no energy column, no measured validation** — must be stated in-chapter | **DECLARED** |
| **NS-3 validates throughput only** | the airtime/contention model is grounded | latency, energy and loss behaviour are **not** validated by simulation; "NS-3-validated" must not imply more | **OPEN** (D3) |
| **10 s NS-3 runs, not 30 s** | ~5000 busy periods/run × 10 seeds; tight CIs | a documented deviation from docs/04 §3 | **DECLARED** |
| **Frozen artifacts + staleness gate** | staleness cannot be committed unnoticed | every deliberate change costs a re-freeze | **DECLARED** |
| **Contiguous batch grids** | no quantized optima | larger sweeps. *Sparse grids caused F3 **and** understated F5 as 2.75× when the true value is 3.03×* | **FORCED** by F3/F5 |

## 6. The 2026-10-06 revision — the design as one frame

*Numbers here are read from `results/raw/design_ladder.csv`, `e3_codec_loss.csv`,
`exclusion_matrix.csv` and `stream_baselines.csv`; capacities are deliberately not repeated —
quote them from the ladder, with their intervals.*

| # | Decision | Bought | Gave up | Status |
|---|---|---|---|---|
| **A keyframe in every frame (r = 1)** | every frame decodes alone, so V = 1 − p as T3 assumed | **3.0 B/record** in the first format (71.99 → 74.96), 3.5 B/record against r = 16 in the lean one. The saving quoted since July (−58.68 %) becomes −56.98 % for the first format | **FORCED** at ε ≤ p (T3′, F46) |
| **A second, lean frame format beside the frozen first** | the design exists as an object with a sender and a receiver; 43.25 B/record against 74.96 | two formats to explain; the first format's delta rows remain a byte model and say so (`sized_from`) | **DECLARED** (R2) |
| **One chain link per frame in the lean format** | 32 B per record becomes 35 B per frame | inside a frame, continuity rests on the frame signature, not on an independent hash per record — on 802.11 as well as LoRa | ⚠️ **OPEN — Mohamed** (`OPEN_ITEMS` G5) |
| **Batching four records** | fewer bytes and a quarter of the frames | a lost frame takes four records; a record waits up to 80 ms; and **a longer frame is lost more often at one bit error rate** — V = 0.943 where the one-record frame loses 5 % | **DECLARED** — the last cost was not stated before E10's `ber` rows |
| **Capacity simulated per configuration** | a V ≥ 0.95 capacity with a bootstrap interval, instead of one load ceiling that was off by up to 23 % | hours of simulation per change; a rung that was not simulated has **no** such capacity | **MEASURED** (R7, F50) |
| **The airtime line stated as a closed form** | a rule that predicted seven unseen configurations within 3.4 %, and says why a utilisation ceiling could not work | it is a fit: one loss level, one PHY rate, 5–50 frames/s, a simulator; its residuals are ordered by frame rate. It is never quoted as a capacity | **MEASURED** — held-out, pre-registered (F54) |
| **Send time redrawn within every period** | a run samples the channel, not one frozen phase configuration; per-run sd 0.034 → 0.0016 | not the published scenario's default; a real autopilot's jitter is unmeasured (G7). Mean delivery differs by 0.003 between the sources, and the strictly periodic crossings are 1–9 % lower — within the tolerance registered, not zero, and not yet explained | **DECLARED** — by the rule registered before the runs (F51) |
| **N_max on the mean, at the grid** | the estimator registered in advance, and the LoRa arm's | coarse where the grid is; a per-run reading is stricter | **DECLARED** |
| **A graded exclusion verdict** | "excluded" means a content-independent floor exceeds the limit — arithmetic, not telemetry | the count *eight of twelve* joins five rates excluded by the signature alone with three excluded by header + link + signature + one record (124 B > 115 B); the second kind is conditional on carrying the link on air | **DECLARED** (R4, F47) |
| **Certificates as a second column** | both accountings visible | explicit certificates only; not in any simulated frame | **DECLARED** (R13) |
| **Stream-signing schemes modelled, not implemented** | five classical schemes in one table at this operating point | a saturation bound only, with our primitives in place of the papers' | **DECLARED** (R5) |
| **No typed results** | prose cannot drift from the artifacts, and a sentence that states a verdict is checked against them | LaTeX source is harder to read | **DECLARED** |
| **A shorter paper** | a results paper: the frame, the ladder, the exclusion | the LoRa capacity work and the audit history — the most distinctive material — are in the thesis and the methods paper, not the paper | **DECLARED** (R11, R12) |
| **Real telemetry from public logs** | a check chosen by a rule fixed in advance | nothing below 0.2 s spacing; the mean flatters a fast swarm (fixed wings need up to 13.2 B per delta) | **MEASURED**, limited (F52) |

---

## The rows an examiner will press hardest

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
10. **The prototype's receiver does not keep up with 124 nodes on one core** (F77) — 57. The
    capacity is the channel's; the ceiling in the table is cryptography's. Answered by giving
    the number beside the ceiling, not by quoting only the ceiling.
