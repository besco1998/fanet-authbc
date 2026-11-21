# The sending pattern, capture and LoRa duty cycle: validation in ns-3 and on the hardware's logs

*Report of the phase specified in `docs/prompts/NEXT_PHASE_PROMPT.md` (Mohamed, 2026-11-19), with
his decisions of 2026-11-19 and 2026-11-20 (`docs/DECISIONS.md`). Branch `p13-sending-pattern`.
Nothing here is in the paper or the thesis, except the removal of ch. 5's line count, made at his
request.*

**What this phase tested.** The capacity model predicts how many stations can share one 802.11
collision domain while each delivers at least 95 % of its broadcast frames. The validation report
of 2026-11-18 found its two failures had one cause: the loss expression (G5) assumes frame starts
arrive as a Poisson process.
* **Periodic telemetry timers are less clustered than Poisson,** and the model was 5–9 %
  pessimistic.
* **Fragments sent back to back are more clustered,** and the model was optimistic.

This phase made the sending pattern an input, and added two more:
* **(G25):** a periodic-source correction for 8 or more other stations;
* **a finite-station form** for 2–5 stations;
* **capture:** the receiver decodes the stronger of two colliding frames, (G22)–(G24);
* **duty-cycled ALOHA over C channels** for LoRa.

Each was registered before its runs (`predictions/U*.md`, tags `prereg-U*`), with a tolerance
that was not widened afterwards.

**Terms used below:**
* **ns-3:** the simulator, version 3.48, through an instrumented copy of the published scenario
  that is byte-identical to it at its defaults;
* **rule A:** the access rule the loss expression was derived for, simulated by Mohamed's event
  model;
* **q:** the probability that a collided frame is still received;
* **ℓ:** link loss with no other sender;
* **N_max:** the largest swarm at 95 % delivery.

## (a) Every registered claim, held or failed, with its side

| claim | registration | result | side |
|---|---|---|---|
| (G25) capacity on 8 new ns-3 cells (802.11b and 802.11a, two targets), ±5 % | `UG25` | **held, 16 of 16**: −3.45 … +0.31 % | conservative at 15 of 16 |
| ns-3's receiver rule for two overlapping frames, as read in the source | `UCAP` | **failed, 430 of 460**: my reading missed one window condition | — (a reading error) |
| the corrected reading, on fresh points | `UCAP2` | **held, 552 of 552** | — |
| the finite-station form at N = 3–5, u ≤ 0.5, ±15 % | `UFS` | **held, 12 of 12**: −11.9 … +4.1 % | both sides |
| Malone–Duffy–Leith, adapted to broadcast, at N = 2, ±15 % of rule A (a test before any proposal) | criterion committed first | **does not hold**: 0.49–2.96 (802.11b), 0.65–1.04 (802.11a) | both sides |
| LoRa N_max = 1 + floor(C ln(1/(1 − ε))/(2d)), 18 cells | `UC7` | **12 of 18**. The d = 1 % misses lie inside their bootstrap intervals; three 20 B cells at d = 10 % did not run at their limit | optimistic where failed |
| one new 10 % LoRa cell past the Class A windows | `UC7B` part 1 | **held** (N_max 3) | — |
| capacity with capture, (G23) with (G25), 16 configurations, ±5 % | `UF` | **held, 12 of 16**: −1.73 … +0.78 %; failed at 802.11b cell C, +5.05 … +7.26 % | optimistic where failed |
| the worst sender's capacity, (G24) with (G25), ±5 % | `UF` | **held, 2 of 16**: the statistic registered was a sample minimum (F139) | optimistic at all 14 misses |
| an outlier node's own loss, ±20 % | `UF` | **failed**: 0.448 predicted, 0.681 measured; a partially hidden station (F141) | optimistic |
| the hardware-matched configuration | `UH` | a comparison, not scored: see (d) | — |

## (b) (G25) against ns-3 on new cells, beside the Poisson model

Eight cells no stored result had used, two loss targets, 30 seeds per node count, the designated periodic source (`predictions/UG25.md`). Errors are model − ns-3, in % of ns-3's crossing.

| cell | PHY | frame, frames/s | ε | ns-3 crossing (95 % CI) | (G25) root, error | Poisson (G5) root, error |
|---|---|---|---|---|---|---|
| GB120F15 | 802.11b 1 Mb/s | 120 B, 15 | 0.05 | 32.60 (32.47–32.76) | 32.25, **-1.07 %** | 30.91, -5.19 % |
| GB120F15 | 802.11b 1 Mb/s | 120 B, 15 | 0.02 | 23.69 (23.51–23.91) | 23.63, **-0.24 %** | 22.83, -3.63 % |
| GB120F20 | 802.11b 1 Mb/s | 120 B, 20 | 0.05 | 24.95 (24.81–25.08) | 24.69, **-1.05 %** | 23.43, -6.09 % |
| GB120F20 | 802.11b 1 Mb/s | 120 B, 20 | 0.02 | 18.43 (18.22–18.66) | 18.13, **-1.64 %** | 17.37, -5.74 % |
| GB240F15 | 802.11b 1 Mb/s | 240 B, 15 | 0.05 | 21.18 (21.05–21.29) | 21.09, **-0.42 %** | 19.76, -6.70 % |
| GB240F15 | 802.11b 1 Mb/s | 240 B, 15 | 0.02 | 16.05 (15.74–16.25) | 15.74, **-1.91 %** | 14.92, -7.05 % |
| GB240F20 | 802.11b 1 Mb/s | 240 B, 20 | 0.05 | 16.25 (16.17–16.32) | 16.30, **+0.31 %** | 15.07, -7.23 % |
| GB240F20 | 802.11b 1 Mb/s | 240 B, 20 | 0.02 | 12.40 (12.24–12.56) | 12.20, **-1.60 %** | 11.44, -7.76 % |
| GA640F20 | 802.11a 6 Mb/s | 640 B, 20 | 0.05 | 32.31 (32.11–32.44) | 31.76, **-1.70 %** | 30.71, -4.95 % |
| GA640F20 | 802.11a 6 Mb/s | 640 B, 20 | 0.02 | 22.88 (22.40–23.16) | 22.09, **-3.45 %** | 21.44, -6.31 % |
| GA640F30 | 802.11a 6 Mb/s | 640 B, 30 | 0.05 | 22.16 (22.04–22.25) | 21.77, **-1.74 %** | 20.81, -6.10 % |
| GA640F30 | 802.11a 6 Mb/s | 640 B, 30 | 0.02 | 15.54 (15.35–15.71) | 15.23, **-2.00 %** | 14.63, -5.89 % |
| GA900F20 | 802.11a 6 Mb/s | 900 B, 20 | 0.05 | 24.70 (24.58–24.84) | 24.32, **-1.54 %** | 23.26, -5.81 % |
| GA900F20 | 802.11a 6 Mb/s | 900 B, 20 | 0.02 | 17.50 (17.32–17.72) | 17.18, **-1.82 %** | 16.51, -5.66 % |
| GA900F30 | 802.11a 6 Mb/s | 900 B, 30 | 0.05 | 17.11 (17.02–17.19) | 16.80, **-1.81 %** | 15.84, -7.40 % |
| GA900F30 | 802.11a 6 Mb/s | 900 B, 30 | 0.02 | 12.01 (11.86–12.20) | 11.95, **-0.48 %** | 11.34, -5.59 % |

* **(G25) held at all 16, within −3.45 … +0.31 %.** It is on the conservative side at 15, by 2 % or less at 14.
* **The Poisson root lies −3.63 … −7.76 %,** beyond ±5 % at 14 of 16: the shortfall that failed U-D's 802.11b cells on 2026-11-18, now removed by the sending-pattern term.
* **Not every inner quantity matches.** The number of co-waiting frames that (G25) predicts, R·K, exceeds ns-3's measured count: the measured count is 0.57–0.87 of R·K, falling with load. The totals hold while this inner quantity does not, the same pattern as the 2026-11-18 three-term split.

## (c) q: closed form, ns-3 and hardware

q is the share of collided frames still received. The model needs it per pair, q_ij, and as a
swarm mean, q̄ (G22)–(G24).

**ns-3's rule** (U-CAP, corrected and checked afresh in U-CAP2):
* within the 4 µs preamble window, the stronger frame is received if its SINR is at least 4 dB;
* so **q = 0 at equal power,** and every DCF collision, all of them same-slot ties, falls in that
  window;
* the frame-capture model acts only on a frame arriving 4–16 µs after the first. No DCF collision
  does, so it changes nothing here.

**In ns-3's swarms (U-F),** four estimates side by side: the registered closed form; that form
with F138's half-duplex factor; ns-3's ratio of capture to no-capture loss (q̂); and ns-3's own
collision events from the MAC and reception traces.

| config | closed form, registered q̄ | × (N − 2)/(N − 1) at ns-3's crossing | ns-3, no-capture ratio q̂ at the nearest N | ns-3, on the collision events |
|---|---|---|---|---|
| FCAP2N | 0.2532 | 0.2466 | 0.241 ± 0.007 (N = 34) | 0.2454 (N = 39) |
| FCAP2R | 0.3436 | 0.3351 | 0.315 ± 0.006 (N = 34, approximate) | — |
| FCAP3N | 0.3218 | 0.3138 | 0.317 ± 0.007 (N = 34) | 0.3078 (N = 41) |
| FCAP3R | 0.3712 | 0.3623 | 0.349 ± 0.004 (N = 45, approximate) | — |
| FCBP2N | 0.2532 | 0.2258 | 0.217 ± 0.011 (N = 10) | 0.2105 (N = 10) |
| FCBP2R | 0.3439 | 0.3074 | 0.282 ± 0.010 (N = 10, approximate) | — |
| FCBP3N | 0.3220 | 0.2878 | 0.278 ± 0.011 (N = 10) | 0.2705 (N = 10) |
| FCBP3R | 0.3716 | 0.3326 | 0.321 ± 0.007 (N = 11, approximate) | — |
| FDAP2N | 0.2531 | 0.2513 | 0.226 ± 0.011 (N = 121) | — |
| FDAP2R | 0.3434 | 0.3410 | — | — |
| FDAP3N | 0.3219 | 0.3197 | — | — |
| FDAP3R | 0.3710 | 0.3685 | — | — |
| FDBP2N | 0.2531 | 0.2453 | 0.234 ± 0.015 (N = 33) | 0.2440 (N = 33) |
| FDBP2R | 0.3434 | 0.3332 | 0.315 ± 0.008 (N = 36, approximate) | — |
| FDBP3N | 0.3219 | 0.3123 | 0.297 ± 0.011 (N = 33) | 0.3027 (N = 34) |
| FDBP3R | 0.3710 | 0.3601 | 0.348 ± 0.008 (N = 36, approximate) | — |

* **On ns-3's own collision events, the two-frame closed form is right** within 0.001–0.007 (F138).
* **The registered q̄ is too high** because a colliding partner cannot receive. Over all N − 1
  receivers the share is smaller by (N − k)/(N − 1) for a k-frame collision: 0.89 at N = 10, 0.97
  at N = 40, 0.99 at N = 140.
* **Per pair, (G22)'s geometry holds:** across 2 700–680 000 pairs per configuration, the measured
  pair loss correlates with the predicted within 0.021 of the ceiling that count noise allows
  (`predictions/UF.md`, outcome).

**On the hardware (G1),** from the existing 2.4 GHz logs. They hold counts per sender and
receiver per window, and no per-frame sequences, timestamps or signal strength, so no single
capture event can be seen.
* **D:** the spread across receivers of one sender's collision loss, beyond its link loss. Without
  capture it would be zero up to count noise.
* **The double difference** over two senders and two receivers cancels a receiver that drops every
  sender's frames.
* **Both are sample extremes,** so both are positive even with no capture (F139's pattern). The
  null keeps each window as measured and removes every receiver effect but count noise
  (`python analysis/g1_capture.py --null`, 1 000 draws).

| session | layout | sender-windows | D median: measured | null mean (95th pct) | windows above their own null | double difference median: measured | null mean (95th pct) | windows above |
|---|---|---|---|---|---|---|---|---|
| W1e | side by side, 2–3 boards | 108 | 0.27 % | 0.09 % (0.10 %) | 54 % | not computable (3 boards) | — | — |
| W1f | side by side, 4 boards | 224 | 0.28 % | 0.12 % (0.13 %) | 50 % | 1.02 % | 0.25 % (0.28 %) | 88 % |
| W1j | 1 m square, 4 boards | 144 | 1.40 % | 0.18 % (0.20 %) | 85 % | 2.53 % | 0.40 % (0.45 %) | 100 % |
| W1k | 1 m square, 4 boards | 144 | 2.01 % | 0.23 % (0.25 %) | 100 % | 3.77 % | 0.58 % (0.68 %) | 100 % |
| W1n s2 | 1 m square, 4 boards | 144 | 1.56 % | 0.24 % (0.26 %) | 71 % | 5.32 % | 0.55 % (0.63 %) | 100 % |

* **Both exceed count noise in every session.**
* **Side by side,** the median D (0.27–0.28 %) is 2.3–3.1 times its null, and only half the
  sender-windows clear their own null. The effect is real but small.
* **In the 1 m square,** D is 1.4–2.0 %, 6.6–8.8 times its null, against a collision-attributable loss
  of 4.7–5.2 % (median). A sender's collided frames are received at some receivers and not at
  others.
* **The double difference clears its null at 88–100 % of windows,** so the spread is a sender ×
  receiver effect, geometry, not receivers dropping frames.
* **What this does not give:** q itself. Counts identify only differences between receivers.
  Session 1 of the plans measures q against power difference.
* **A correction to G1's framing:** I committed D as "a model-free lower bound". It is biased
  upward by count noise; side by side, the noise is about a third to two-fifths of the median.

## (d) One table per hardware session

**H (a): the 5 GHz anchor, two Pi 4s, frame burst off** (2026-10-09 sessions R1, R2, S1;
`predictions/UH.md`). 802.11a 6 Mb/s, 1 464 B MPDU, N = 2.

| frames/s | hardware (burst off) | ns-3, W = 10 | ns-3, W = 16 | rule A, W = 10 / 16 | hardware ÷ ns-3, W = 10 / 16 |
|---|---|---|---|---|---|
| 124 | 0.00321 (0.00257–0.00422) | 0.00302 | 0.00228 | 0.00375 / 0.00279 | 1.06 / 1.41 |
| 174 | 0.00516 (0.00353–0.00666) | 0.00768 | 0.00557 | 0.01018 / 0.00708 | 0.67 / 0.93 |
| 211 | 0.00837 (0.00668–0.00970) | 0.01785 | 0.01269 | 0.02286 / 0.01638 | 0.47 / 0.66 |

| the saturated pair (S1) | lost on air | frames/s on air per board |
|---|---|---|
| hardware, burst off | 12.4 % (11.4–13.1) | 259–266 |
| ns-3, W = 10 | 20.1 % | 277.2 |
| ns-3, W = 16 | **13.8 %** | **265.9** |

* **The two window readings conflict inside ns-3:** the one-sender cycle gives W ≈ 10, and only
  W = 16 reproduces the saturated pair. This is F115, now shown without a formula.
* **The hardware departs from ns-3 in one direction with load,** at either W: more loss at 124
  frames/s, less at 211. With frame burst off, frame burst is not the cause.

**H (b): W1f, four boards at 65 frames/s, 2.4 GHz** (802.11b 1 Mb/s, 145 B, u = 0.485). The only
2.4 GHz windows that pass the frame-burst rule (S²f²/2 = 0.80 % < 1 %).

| family (per-board W) | capture end | ns-3 loss (± 1.96 SE) | ns-3 over seeds | hardware ÷ ns-3 |
|---|---|---|---|---|
| σ 20 µs, DIFS 50 µs (W = 4, 4, 51, 6) | equal power | 0.01400 (± 0.00038) | 0.0121–0.0162 | 0.41 |
| σ 20 µs, DIFS 50 µs | assumed channel: Rayleigh, capture model | 0.01160 (± 0.00035) | 0.0096–0.0132 | 0.49 |
| σ 9 µs, DIFS 28 µs (W = 12, 13, 117, 17) | equal power | 0.00620 (± 0.00026) | 0.0043–0.0074 | 0.93 |
| σ 9 µs, DIFS 28 µs | assumed channel: Rayleigh, capture model | 0.00513 (± 0.00018) | 0.0037–0.0058 | 1.12 |

* **The hardware:** 0.00573 (four windows, 0.00506–0.00675), less the background b = 0.000996.
* **The closed forms at the standard W = 32:** (G5) 0.00961, (G25) 0.00737, finite-station 0.00613.
* **The hardware lies between the 9 µs family's two capture ends,** and below every run of the
  20 µs family. By Mohamed's rule this does not choose the family: W is not inferred from a
  session H reproduces. Session 3 separates them.

**Not reproduced: every other 2.4 GHz window,** flagged by the frame-burst rule before any run:

| session | N | windows | S²f²/2 | reproduced |
|---|---|---|---|---|
| W1e | 2, 3 | 48 | 1.43–9.31 % | 0 windows |
| W1f | 4 | 56 | 0.80–3.15 % | 4 windows (65 frames/s) |
| W1j | 4 | 36 | 2.57–3.18 % | 0 windows |
| W1k | 4 | 36 | 2.57–3.18 % | 0 windows |
| W1n s2 | 4 | 36 | 2.57–3.18 % | 0 windows |

They wait for session 2 of the plans (frame burst off).

## The failures, and what each one means

Each failure stays failed as registered. What follows is why it failed, with the evidence, and
what it does and does not show about the model.

**U-CAP, ns-3's receiver rule (430 of 460): a reading error, mine.**
* All 30 misses were one case: the capture model on, a stronger frame arriving 19 µs after the
  first. I predicted it would take over. ns-3 never switched.
* ns-3's capture model needs two conditions. I had read only one (`phy-entity.cc:439–442`). The
  other is that the first frame started at most 16 µs ago (`simple-frame-capture-model.cc:71–72`).
  So the window ends 16 µs after the first frame's start, not 20 µs.
* **The corrected reading was used only after a fresh registered check** (Mohamed, 2026-11-20):
  U-CAP2 on new offsets and a frame size not used before, which held 552 of 552.
* **What it does not touch:** the 4 µs preamble window, which decides every DCF collision. It held
  184 of 184, and q = 0 at equal power, as assumed.

**UC7, LoRa duty cycle (12 of 18 held).**
* **d = 1 %, one channel and three channels: optimistic.**
  * Predicted N_max 3 and N* 8.77. ns-3 gave N_max 2 and a crossing at 8.05 (+9.0 %).
  * Both predictions lie inside ns-3's bootstrap interval over seeds (2.10–4.01; 8.02–10.69).
  * With the jitter at twice the time on air, the phases stay nearly frozen. The spread over
    seeds is then large, and these two misses lie inside it: the small-sample pattern, not shown
    to be a model error.
* **d = 10 % with 20 B frames (three cells): not a test of the formula.**
  * A Class A device holds its next uplink until both receive windows have closed (RX1 at 1 s,
    RX2 at 2 s). So a period of 0.67 s cannot be kept, and the nodes sent at 2.4–2.6 %, not
    9.1 %.
  * Two were scored as failed, one as held. Mohamed recorded them as not applicable
    (2026-11-20), and the new cell past the windows (UC7B, 120 B at SF8) held.
* **What it shows:** at d = 0.1 % (N* 27–206), the formula lies +2.5 … +3.5 % above ns-3, slightly
  optimistic; at d = 1 % with eight channels, +4.6 %.
* **A finding for the ledger, from UC7B:** under frozen phases the loss is bimodal across nodes at
  one and three channels. At d = 0.1 % with one channel, the mean loss is 5.2 %, but 74 % of
  node-runs lose nothing and the worst node loses 72 %. An average criterion hides nodes that
  never get through, which is what the every-sender criterion exists to catch. It is not bimodal
  at eight channels.

**Malone–Duffy–Leith at N = 2: does not hold, so no closed form is claimed there.**
* Their unsaturated fixed-point model, adapted to broadcast, was tested against rule A's
  simulation at N = 2 before any proposal (Mohamed, 2026-11-20), with ±15 % fixed first.
* It lies 0.49–2.96 of rule A at 802.11b and 0.65–1.04 at 802.11a.
* **Why at 802.11b:** a slotted model makes two arrivals to an idle medium collide when they share
  a 20 µs slot, while ns-3 and rule A need them within the 4 µs detection time.
* **So** the 5 GHz anchor is compared with ns-3 and rule A's simulation only.

**U-F, capacity with capture and geometry: (G23) 12 of 16, (G24) 2 of 16, the outlier failed.**
Every miss was optimistic. Unregistered diagnostics found three causes, none of them a bug in the
runs or the scoring.
* **(G23) at 802.11b cell C (+5.05 … +7.26 %):**
  * mostly (G25)'s own loss curve: at occupancy ≈ 0.85 and loss 6.4–7.9 %, past the range U-G25
    checked, it is optimistic by about 3.6–5.5 % with no capture in play (F140);
  * the rest is the capture share. The closed form is right on ns-3's collisions, but the
    registered q̄ counted the colliding partner as a possible receiver. With the factor
    (N − 2)/(N − 1), the four errors fall to +3.98 … +5.58 % (F138; not a registration).
  * fed ns-3's own q̂ and no-capture curve, (G22) reproduces ns-3's capture crossing within
    ±0.16 %.
* **(G24) at 14 configurations (+5.52 … +12.75 %; FDAP's four as bounds, above +6.75 %): a
  registration error, mine.**
  * The registered statistic, each run's worst sender averaged over seeds, is the minimum of N
    sample fractions of 250 or 1 000 frames. Count noise pushes it below the worst sender's
    expected delivery, which is what ε_w models.
  * The measured worst sender equals geometry plus count noise within 0.004 at every point.
    Geometry alone lies 0.023–0.027 higher at 802.11a cell D, falling to 0.001–0.004 at 802.11b
    cell C (F139).
  * **So these misses are not a test of ε_w.**
* **The outlier (0.681 measured against 0.448): a partially hidden station.**
  * Its link term is right (0.360–0.368 against 0.364–0.371).
  * Its frames overlap another six times as often as the swarm's p_c. ns-3 uses one −82 dBm
    threshold for reception and for carrier sense, so a link that fades below it also fails to
    make its neighbours defer (F141).
  * (G22) holds only where every pair senses every other reliably.
* **What holds:** (G22)'s geometry pair by pair, with correlations within 0.021 of the count-noise
  ceiling, and capture's size: without it, every root lies 3.4–19.3 % too low.

## Open questions

**Decisions for Mohamed** — *all three answered on 2026-11-21* (`docs/DECISIONS.md`): F (a) a fresh check of (G22a) at occupancy ≤ 0.78; (b) two labelled every-sender statistics, (G24) pooled and (G24a) per window; (c) (G25) past 0.78 at 802.11b a stated limit, quantified once; (d) **the model is limited to swarms where every station hears every other** (F141). U5: values kept with a note in ch. 10; the drift rebuilt once from a clean tree. The session plans approved in the order 3, 1, 2. *The questions as they were put:*
1. **F's next step** (U-F stays failed as registered):
   * **(a)** whether to register the corrected q, with the half-duplex factor (N − k)/(N − 1)
     (F138), for a fresh check on unseen configurations, as your rule of 2026-11-20 requires;
   * **(b)** which every-sender statistic matches (G24) (F139). Either a long-run worst sender
     (the same placement over several channel seeds, or runs long enough that the noise of the
     minimum is below the tolerance), or a criterion that names its window, for the ledger;
   * **(c)** whether (G25) at 802.11b beyond occupancy 0.78 and 5 % loss is in scope (F140), or
     stated as a limit;
   * **(d)** whether a hidden-station term for a sender with lossy links (F141) is derived and
     registered, or (G22)'s scope is stated as "every pair senses every other", with the
     deployment rule that a node is admitted only above a link margin.
2. **U5** (`docs/revision/2026-11-20_u5_frozen_lora.md`):
   * whether thesis ch. 10's printed LoRa deliveries are rerun without the downlinks, at the true
     1 % duty, both, or kept with the two behaviours stated. No N_max or headline interval
     moves;
   * whether the reproduction drift at N ≥ 20 (at most 6 × 10⁻⁵) needs more than its record.
3. **The three hardware session plans** (`docs/revision/2026-11-20_session_plans.md`): approval,
   and you at the boards. Session 3 (separating W from slot and DIFS) comes first, because H's
   two window families stay unresolved without it.

**Open, not decisions:**
* **F115, the window conflict, now inside ns-3** (U-H (a)): at 5 GHz with frame burst off, the
  one-sender cycle gives W ≈ 10, but only W = 16 reproduces the saturated pair (13.8 % against
  12.4 %). And at either W, the hardware loses more than ns-3 at low load and less at high load.
* **F137's cause:** why `dcf_ns3rule` loses far less than ns-3 at two or three stations. Not tested.
* **The LoRa twin's reproduction drift at N ≥ 20** (U5): cause not established.

## Handoff 2026-11-21 — the sending-pattern and capture phase (serial)

* **Green baseline:** branch `p13-sending-pattern` (from `p12-unified-model`; neither merged),
  at the commit that adds this report.
  * Before the push, the fast suite passed in a clean worktree, with ruff and mypy clean.
  * Registration tags: `prereg-UG25`, `UCAP`, `UCAP2`, `UFS`, `UC7`, `UC7B`, `UF`, `UH`. All are
    held in `NOT_YET_IN_THE_THESIS`.
* **Done:**
  * **A:** the decisions recorded, the two scripts committed byte-unchanged, and
    `periodic_capacity` and `capture` with their tests;
  * **B:** (G25) 16 of 16;
  * **C:** the finite-station form 12 of 12 where accepted, and no closed form at N = 2;
  * **D:** U-CAP failed (a misreading), U-CAP2 552 of 552;
  * **E:** U-C7 12 of 18, U-C7B held;
  * **F:** U-F 14 of 33, with three causes found (F138, F139, F141) and one limit (F140);
  * **G1,** with its count-noise null; the three session plans;
  * **H (a) and (b);**
  * **U5;**
  * this report.
* **Frozen this session:** nothing. No frozen file was touched. In the thesis, only ch. 5's line
  count and its guard were removed, at Mohamed's request.
* **Open, awaiting Mohamed:**
  1. **F's next step**, (a)–(d) under the open questions;
  2. **U5's two decisions;**
  3. **the three hardware session plans,** and him at the boards;
  4. **merging** `p12-unified-model` and this branch.
* **Next three steps:**
  1. whichever of F (a)–(d) he chooses, each registered on configurations not used here;
  2. session 3 (W against slot and DIFS) once approved, then sessions 1 and 2, with the kit
     changes tested on made-up data first;
  3. H (b) for the 2.4 GHz windows flagged here, from session 2's frame-burst-off data.
* **Gotchas:**
  * **The U-F traces** (`~/.cache/authbc_uf_traces`, `~/.cache/authbc_ufdiag_traces`) are outside
    the repo. `analysis/uf_diagnose.py` and `uf.score_outlier` need them, and the reruns check
    that a traced run delivers exactly the stored fraction.
  * **The twin now has `--cwMinList` and `--slotUs`,** built and gated (9 of 9 identical; 16 of 16
    option checks). The scratch copy in `ns3/ns-3.48/scratch/` must be refreshed by `cp` after
    any edit to `ns3/authbc-links-audit.cc`.
  * **Any statistic that is an extreme** (a worst sender, a range across receivers, a largest
    difference) needs its count-noise null before it is scored or quoted. F139 and G1 both
    needed it.
  * `scripts/capped.sh NAME` names the unit `authbc-NAME`; a misspelt unit's `systemctl show`
    prints Result=success.
