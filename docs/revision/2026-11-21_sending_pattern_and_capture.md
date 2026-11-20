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
| capacity with capture and geometry, (G23)/(G24) with (G25) | `UF` | *see F below* | |
| the hardware-matched configuration | `UH` | *see H below* (a comparison, not scored) | |

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

*Pending F's measured per-pair loss and G1.*

## (d) One table per hardware session

*Pending H.*

## The failures, and what each one means

*Pending.*

## Open questions

*Pending.*
