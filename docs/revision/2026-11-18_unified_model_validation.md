# Validation of the unified closed-form capacity model in ns-3

*Report of the task of 2026-11-17 ("validate the unified closed-form capacity model in ns-3, audit
the ns-3 arm, and add an 802.11b arm"), with C5 as respecified on 2026-11-18. Branch
`p12-unified-model`. Nothing here is in the paper or the thesis.*

**What was tested.** The unified closed-form model predicts how many stations can share one
802.11 collision domain while each delivers at least 95 % of its broadcast frames. The
specification is in `docs/revision/2026-11-17_unified_model_spec.md`, and the code in
`src/authbc/models/unified_capacity.py`. Its parts:
* **the loss expression:** the share of frames lost to collisions at a given load, as the sum of
  three mechanisms;
* **two capacity formulas:**
  * the *law*, an explicit formula with two constants of the access protocol;
  * the *root*, the node count at which the loss expression reaches the target;
* **the design law:** how capacity grows with the number of records per frame;
* **three design rules:** a key record carried once in r frames, a signed unit split over n
  frames, and an interior best batch under bit errors.

**How.**
* **First against the 74 capacities already on file**, then with new ns-3 runs. Every new
  prediction was registered and tagged before its runs (`predictions/U*.md`, tags `prereg-U*`).
* **Every new run** used an instrumented copy of the published scenario. At its defaults that
  copy is byte-identical to the original and to the frozen results: 9 of 9 runs, checked again
  after every rebuild.
* **A capacity** is the node count at which the mean delivered fraction over 30 seeds crosses
  95 %, by straight-line interpolation, with a bootstrap interval over seeds.
* **The tolerance** is ±5 % unless stated, never widened after a run.

**The two PHYs.**
* IEEE 802.11a at 6 Mb/s: slot 9 µs, DIFS 34 µs, contention window 16;
* IEEE 802.11b at 1 Mb/s with the long preamble: slot 20 µs, DIFS 50 µs, window 32.

**The frames.** Telemetry records of 9 bytes are packed b to a frame in the lean format,
137 + 9b bytes:
* the *base frame* is one record (146 bytes);
* the *design frame* is four records (173 bytes).

## Table A — every claim of the model, held or failed

| claim | where tested | result |
|---|---|---|
| The implementation reproduces the specification's test vectors | 802.11a and 802.11b vectors | **held**: every vector to the digits given |
| **Total loss** of the loss expression | 8 loads at 802.11a (6 Mb/s), 8 at 802.11b (1 Mb/s), ±10 % | **802.11a held, 7 of 8; 802.11b failed, 0 of 8.** At 802.11b the excess at a fixed node count is the capacity offset below, seen on a steep curve: ns-3 reaches the predicted loss at 4–9 % more stations |
| **The three loss terms one by one** | the same 16 loads | **failed**: 17 of 48 and 18 of 48 cases held. See *Failure 2* |
| **The share of frames arriving to a busy medium** | the same 16 loads | **held**, 16 of 16: within 0.7 % at 802.11a, within 7.6 % at 802.11b |
| **The law, ±5 %**, where the frame is at least twice the protocol time τ0 | 74 stored capacities; 3 new at 16–64 records; 6 new at 802.11b, 10 records/s; 18 at 802.11b, three windows × three loss targets | **held at 802.11a**: the stored capacities outside the cells the author names, but for two rows at −5.06 % (window 4) and +6.36 % (strictly periodic sources), and every new case it was scored on. **At 802.11b it held at 42–600 stations and at 8–14 stations, and failed at 15–37 stations** (0 of 9, 5.1–6.3 % below). See *Failure 1* |
| **The root, ±5 %** | the same | **held at every new case at 802.11a.** In the stored capacities it held except in seven rows the author does not name, all on the conservative side at 5.0–5.9 % below: window 4 (two cells), a 10 % loss target, two 802.11p cells, one design-map cell, and one source with a 0.1 ms jitter. **At 802.11b, 15–37 stations, 1 of 9 held** |
| **The design law**: the gain from batching bends away from b | 802.11a to 64 records; 802.11b to 32 | **held**: within 0.95 % of ns-3's gain at 802.11a, within 2 % at 802.11b (reported, not scored) |
| **The key record once in r frames** | r = 2, 4 at 802.11a (a 173-byte key frame, then 158-byte frames) | **held**, 4 of 4: the law +0.10 % and +2.80 %, the root −2.73 % and −1.71 % from ns-3 (105.57 and 81.44 stations). The frame-to-record formula holds on the measured loss within ±0.0005 |
| **The signed unit over n frames** | the 173-byte unit as 2 × 98 or 3 × 73 bytes at 802.11a, its frames handed to the MAC together | **failed**: the root +35 % and +62 % above ns-3 (40.94 and 19.58 stations), on the optimistic side. The unit rule itself holds; the frames' burst raises the loss per frame. See *Failure 3*. **The same units with each frame on its own slot: held** (the root −2.79 % and −2.81 %, new seeds). A registered burst correction, on new cells: failed where scored (+8.8 %, +8.9 %) |
| **An interior best batch under bit errors** | 6 Mb/s constant power; 48 Mb/s constant power; 6 Mb/s with fading | **does not apply at 6 Mb/s**, with constant power (F135) or with per-frame fading (F136): a frame is error-free or undetected. **At 48 Mb/s it held:** the measured best batch is the predicted 8 records, with capacity 2.0 % above the prediction |
| **Duty-cycled ALOHA (LoRa)** | — | **not tested** (C7 not run) |
| **An added loss term 2h·ν·T_f for stations hidden from part of the swarm** | — | **not tested** (C6 not run) |
| **The ns-3 access rule gives the same capacity as the rule the expression assumes, within 1 %** | 18 capacities, both rules as event models | **held**: within 0.40 % |
| **Poisson starts underestimate capacity by 7–9 % at 8–14 stations** | 802.11b, 5–11 stations | **consistent** where scored (4.75–8.90 % below). **The shortfall persists past 14 stations at 802.11b** (5–6 % at 15–37), where the author states no limit |
| **The law overestimates when the frame is shorter than 2τ0** | stored 802.11a at 24 Mb/s; fragments of 98 and 73 bytes | **held** at 24 Mb/s (+8.4 %, +8.9 %), and for both fragment sizes (+44 %, +79 %) |
| **Mean access delay** ≈ ρ[T/(2(1 − ρ)) + (W − 1)σ/2] | 9 stored delay cells at delivery ≥ 95 % | **failed as registered** (2 of 9). The registration wrote ρ = ν·T_f, where the model document means T = T_f + DIFS. Under that reading it holds 7 of 9. No reading was adopted after the fact |
| **Age-of-information tail** = p^⌊(D − S)Λ/b⌋ | stored traces | **held**, 8 of 8 |
| **Verifiability under bursty loss** (a Gilbert fit) | 24 ns-3 traces, 81 on-air traces | **held**, 105 of 105 |

## Table B — the model against ns-3 at 802.11a and at 802.11b, case by case

Errors are model − ns-3, in % of ns-3's capacity; the loss target is 5 % unless stated.

| case | 802.11a, 6 Mb/s: ns-3 / law / root | 802.11b, 1 Mb/s: ns-3 / law / root |
|---|---|---|
| base frame, 146 B at 50 frames/s | 35.26 / −2.23 % / −4.39 % | 9.72 / −8.21 % / −7.91 % |
| design frame, 173 B at 12.5 frames/s | 124.55 / −1.36 % / −3.14 % | 31.03 / −5.43 % / −5.17 % |
| design frame at a 2 % loss target | — | 23.09 / −5.10 % / −4.97 % |
| design frame at a 10 % loss target | — | 37.32 / −5.53 % / −5.29 % |
| base frame, window 8 | 30.35 / −3.26 % / −4.83 % | 7.31 / −9.42 % / −9.45 % (below 8 stations: not scored) |
| batching, the largest batch run | 64 records: 717.27 / −2.70 % / −2.87 % | 32 records: 599.31 / −4.43 % / −4.36 % |
| batching, the gain law against ns-3's gain | within 0.95 % to 64 records | within 2 % to 32 records |
| total loss of the expression at four loads, per cell | held 7 of 8 | held 0 of 8 |
| the three terms | 17 of 48 | 18 of 48 |

**What the table says.**
* **At 802.11a, 6 Mb/s, window 16 and a 5 % target, with the designated source:**
  * the root lies 1.7–5.7 % below ns-3 in every case. The exceptions are frames sent in a burst,
    and the one-record Falcon frame the author names (−7.9 %);
  * the law lies 0.0–4.6 % below, except in the key-record cells, for frames shorter than 2τ0,
    and the Falcon frame (−7.8 %).
* At 802.11b it is more pessimistic, and more so the smaller the swarm:
  * 4.75–10.79 % below at 5–11 stations;
  * 4.97–6.34 % at 15–37;
  * 2.78–4.76 % at 42–600.
* **The direction of the errors.**
  * **The root lies below ns-3 in every case with the designated source** (a periodic source with
    a random phase), **except units whose frames are sent as a burst.** There it is 25–62 % too
    high.
  * **The law lies above ns-3 in three places:** in the key-record cells (+0.1 %, +2.8 %), with
    strictly periodic sources (up to +6.4 %), and for frames shorter than 2τ0, as its author
    states.

## Table C — model, ns-3 and hardware per hardware session

**Not yet available.** Reproducing each hardware session in ns-3 needs a hardware-matched
802.11b configuration. The campaign has not measured several of its parameters in simulator
terms: the capture margin, the effective contention window, and frame-burst behaviour. The task
says to list these as unknown and ask, not guess. The comparison waits on that decision.

The hardware results stand as recorded. On four real radios at 802.11b, 1 Mb/s, the ratio of
the batched to the one-record capacity was 3.280, 3.272 and 3.297 in three sessions, against the
model's 3.304 (findings F132 and F133, and session 2 of W1n).

## The failures, and what each one means

### Failure 1 — 802.11b, 15–37 stations: the model is 4.97–6.34 % low

* **The result.** At 802.11b, for the design frame at windows 32, 16 and 8 and loss targets 2,
  5 and 10 %, the law lies 5.08–6.26 % below ns-3 and the root 4.97–6.34 % below. Only the root
  at window 32 and a 2 % target held (−4.97 %); the other 17 cases failed. Recorded as failed
  (Mohamed, 2026-11-18).
* **It fails on the conservative side.** The model predicts fewer stations than ns-3 supports.
  A design that follows it does not overload the channel.
* **The cause, with evidence: the model's assumption that frame starts are Poisson.**
  * The scenario's sources are periodic with a random phase.
  * Event simulations of the same access rule at the stored 802.11b design cell (ns-3: 31.05):
    with ns-3's periodic sources they give 30.94 and 31.10, within 0.4 % of ns-3; with Poisson
    starts, 28.90 (−6.9 %).
  * The loss expression's root gives 29.43 (−5.2 %), close to the Poisson simulation.
  * At the base cell (ns-3 9.72) the periodic simulation gives 9.72 and the Poisson one 8.02.
* **The link to the model's stated limit.** Its author states that Poisson starts underestimate
  capacity by 7–9 % at 8–14 stations. At 802.11b that holds (4.75–8.90 % below where scored). The
  shortfall does not end at 14 stations: it is 5–6 % at 15–37, just outside the ±5 % the
  registration set there.
* **What would fix it:** a finite-station, periodic-source version of the loss expression (open
  item U1). Not started; it waits for Mohamed's go-ahead.

### Failure 2 — the loss expression's three terms do not map onto ns-3's mechanisms

The expression splits collision loss into three terms:
* a **same-slot tie** between frames that drew a backoff;
* a **DIFS-gap term**: a frame that arrives in the gap after a busy period and starts without
  backoff;
* a **detection window**: a start within δ = 4 µs of another, before the first can be sensed.

Every lost frame of 160 runs was classified by a rule fixed before the runs. The share of each
term is out of all frames sent, predicted / measured, and ✓ marks a term within ±10 % or inside
the measured 95 % interval. **802.11a, 6 Mb/s** (cell C: 146 B at 50 frames/s; cell D: 173 B at
12.5 frames/s):

| cell | stations | same-slot tie | DIFS-gap term | detection window | total | busy share | K |
|---|---|---|---|---|---|---|---|
| C | 14 | 0.0025 / 0.0021 ✗ | 0.0010 / 0.0009 ✓ | 0.0061 / 0.0058 ✓ | 0.0095 / 0.0088 ✓ | 0.171 / 0.172 ✓ | 0.235 / 0.200 ✗ |
| C | 21 | 0.0069 / 0.0051 ✗ | 0.0023 / 0.0015 ✗ | 0.0101 / 0.0119 ✗ | 0.0193 / 0.0185 ✓ | 0.261 / 0.261 ✓ | 0.434 / 0.349 ✗ |
| C | 34 | 0.0260 / 0.0135 ✗ | 0.0061 / 0.0034 ✗ | 0.0188 / 0.0301 ✗ | 0.0510 / 0.0470 ✓ | 0.425 / 0.426 ✓ | 1.045 / 0.713 ✗ |
| C | 45 | 0.0620 / 0.0264 ✗ | 0.0108 / 0.0051 ✗ | 0.0273 / 0.0569 ✗ | 0.1001 / 0.0884 ✗ | 0.552 / 0.556 ✓ | 2.027 / 1.184 ✗ |
| D | 51 | 0.0030 / 0.0013 ✗ | 0.0009 / 0.0006 ✗ | 0.0059 / 0.0074 ✗ | 0.0099 / 0.0093 ✓ | 0.187 / 0.187 ✓ | 0.260 / 0.231 ✗ |
| D | 77 | 0.0082 / 0.0032 ✗ | 0.0022 / 0.0008 ✗ | 0.0097 / 0.0157 ✗ | 0.0201 / 0.0196 ✓ | 0.282 / 0.282 ✓ | 0.478 / 0.395 ✗ |
| D | 121 | 0.0277 / 0.0070 ✗ | 0.0054 / 0.0016 ✗ | 0.0173 / 0.0384 ✗ | 0.0503 / 0.0469 ✓ | 0.439 / 0.440 ✓ | 1.078 / 0.766 ✗ |
| D | 161 | 0.0662 / 0.0136 ✗ | 0.0095 / 0.0022 ✗ | 0.0251 / 0.0769 ✗ | 0.1008 / 0.0926 ✓ | 0.570 / 0.571 ✓ | 2.104 / 1.285 ✗ |

**802.11b, 1 Mb/s** (the same frames at 50 and 12.5 frames/s):

| cell | stations | same-slot tie | DIFS-gap term | detection window | total | busy share | K |
|---|---|---|---|---|---|---|---|
| base | 5 | 0.0056 / 0.0038 ✗ | 0.0003 / 0.0005 ✓ | 0.0021 / 0.0022 ✓ | 0.0081 / 0.0065 ✗ | 0.327 / 0.334 ✓ | 0.561 / 0.306 ✗ |
| base | 7 | 0.0173 / 0.0109 ✗ | 0.0007 / 0.0013 ✗ | 0.0036 / 0.0035 ✓ | 0.0216 / 0.0156 ✗ | 0.488 / 0.504 ✓ | 1.179 / 0.600 ✗ |
| base | 9 | 0.0446 / 0.0261 ✗ | 0.0012 / 0.0045 ✗ | 0.0053 / 0.0048 ✓ | 0.0511 / 0.0354 ✗ | 0.641 / 0.673 ✓ | 2.395 / 1.061 ✗ |
| base | 11 | 0.1073 / 0.0639 ✗ | 0.0018 / 0.0185 ✗ | 0.0071 / 0.0065 ✓ | 0.1162 / 0.0889 ✗ | 0.774 / 0.837 ✓ | 5.148 / 2.011 ✗ |
| design | 17 | 0.0077 / 0.0065 ✗ | 0.0003 / 0.0002 ✓ | 0.0022 / 0.0023 ✓ | 0.0102 / 0.0089 ✗ | 0.370 / 0.369 ✓ | 0.677 / 0.464 ✗ |
| design | 22 | 0.0165 / 0.0110 ✗ | 0.0006 / 0.0007 ✓ | 0.0031 / 0.0057 ✗ | 0.0202 / 0.0174 ✗ | 0.483 / 0.486 ✓ | 1.129 / 0.704 ✗ |
| design | 29 | 0.0419 / 0.0200 ✗ | 0.0010 / 0.0009 ✓ | 0.0046 / 0.0176 ✗ | 0.0475 / 0.0385 ✗ | 0.636 / 0.641 ✓ | 2.261 / 1.204 ✗ |
| design | 35 | 0.0887 / 0.0373 ✗ | 0.0015 / 0.0015 ✓ | 0.0060 / 0.0378 ✗ | 0.0961 / 0.0767 ✗ | 0.753 / 0.765 ✓ | 4.274 / 1.925 ✗ |

*K is the number of other stations holding a frame when a busy period ends. Source files:
`results/raw/unified_c1_scored.csv`, `unified_d3_scored.csv`.*

**Which term fails where.**
* **The same-slot tie is overpredicted at all 16 loads**, by a factor of 1.2–4.9.
* **The detection window is underpredicted** at 802.11a from 21 stations on, up to three times,
  and at the 802.11b design cell from 22 stations on, up to six times. It holds at the 802.11b
  base cell.
* **K is overpredicted at all 16 loads,** by a factor of 1.1–2.6.
* **The busy-medium share holds at all 16.**

**Is the failure in the DIFS-gap term, as the task anticipated?** Not mainly.
* **At 802.11a** the DIFS-gap term is overpredicted at 7 of 8 loads, as anticipated: it was
  derived for an access rule ns-3 does not follow. In ns-3 an arrival to an idle medium waits a
  full DIFS, and if pre-empted keeps zero slots. But it is the smallest term, and most of the
  error lies elsewhere. At 161 stations of cell D the tie is overpredicted by 0.053 and the
  detection window underpredicted by 0.052, against 0.007 for the DIFS-gap term.
* **At 802.11b** the DIFS-gap term holds at 5 of 8 loads. Where it fails (the base cell at 7–11
  stations), ns-3 has 2–10 times more of it, the opposite direction.
* **The main mechanism is ns-3's per-station slot grid.** ns-3 counts each station's backoff
  slots from that station's own backoff start (`ChannelAccessManager::GetBackoffStartFor`). So
  two counters that expire "in the same slot" can start a few µs apart. Within 4 µs they
  collide, and the registered rule files them under the detection window.
* **Counted as ties at any spread** (reported, not scored), the tie term lies 3–18 % above
  ns-3's at 802.11a and 13–71 % above at 802.11b.

**What it means.**
* The expression's total and its busy share are right at 802.11a, but its split is not a
  description of ns-3's mechanisms.
* Capacity predictions use only the total, so they are not affected at 802.11a.
* At 802.11b the total is off by the Poisson offset of *Failure 1*.

### Failure 3 — the signed unit over n frames

**The result.**
* **The test:** a signed unit of 173 bytes (four records, 12.5 units per second) sent as two
  frames of 98 bytes or three of 73 bytes, all handed to the MAC at the unit's instant.
* **ns-3:** 40.94 and 19.58 stations.
* **The registered root:** 55.37 and 31.70, 35 % and 62 % too high.
* **The law** lies above ns-3, as its author states for frames this short.
* **Recorded as failed** (Mohamed, 2026-11-18).

**The rule is right; the sending pattern breaks the capacity.**
* **The unit rule holds.** At every node count the share of verified units equals (1 − p)^n on
  the measured per-frame delivery, within 0.002. The rule is ε_n = 1 − (1 − ε)^(1/n), a unit
  verifying only if all n frames arrive.
* **The per-frame loss is what is wrong.** ns-3 loses 1.7 times the expression's share per frame
  at n = 2, and 2.1–2.3 times at n = 3.
* **A diagnostic, not registered,** puts the cause in the burst. The same frames, each sent on its
  own slot of the period, lose 0.95 and 0.94 times the expression's share:

| n, stations | the expression | frames spread | frames in a burst |
|---|---|---|---|
| 2, 41 | 1.53 % | 1.46 % | 2.58 % |
| 3, 20 | 0.85 % | 0.80 % | 1.80 % |

* **The likely mechanism,** read from the ns-3 source and not measured: a station's second and
  third frames always contend at the end of its own transmission's busy period. None of them
  finds the medium idle, as independent starts often do.

**The follow-ups** (Mohamed, 2026-11-18), both registered before their runs:
* **The spread case: held.** The same units, each frame on its own slot of the period, on seeds
  never used before (31–60): ns-3 56.96 and 32.62 stations, the root −2.79 % and −2.81 %. Sent
  this way, a split unit is what the fragmentation rule and the loss expression predict
  (`predictions/UC4S.md`).
* **A burst correction,** tested on new cells only. Fragments 2 … n find the medium busy, so
  their tie term is K/(W + K) instead of a·K/(W + K), and the unit loss is
  1 − (1 − p₁)(1 − p₂)^(n−1). **Failed where scored, on the optimistic side**
  (`predictions/UC4B.md`):

| cell | the correction | ns-3 | error | the original root's error |
|---|---|---|---|---|
| 802.11b, 1 Mb/s, 2 × 98 B | 14.77 | 13.58 | +8.79 % (band −9 … +5 %) | +25.2 % |
| 802.11b, 1 Mb/s, 3 × 73 B | 8.96 | 7.49 | +19.6 % (below 8 stations: not scored) | +53.4 % |
| 802.11a, 6 Mb/s, 120 B unit as 72 + 71 B | 48.97 | 44.96 | +8.93 % (band ±5 %) | +35.3 % |

  * The correction removes 63–75 % of the burst's excess, but not enough.
  * Changing only the tie term of frames 2 … n does not capture all a burst does. A reading, not
    tested: the burst also raises the number of stations holding a frame when a busy period ends,
    which the correction keeps as for independent starts.

**The design consequence.**
* **Fragments sent back to back cost more than the fragmentation rule allows.** The rule (G18)
  holds for how frames become units, but the capacity at n·f frames per second is lower than the
  loss expression gives, by the burst.
* **Fragments spread over the period match the rule,** at a price in verification delay. A
  receiver waits up to (n − 1)/n of a unit period for the last fragment. **Measured:** at 12.5
  units per second the mean wait is **39.99 ms for two fragments and 53.32 ms for three**,
  against the predicted 40.0 and 53.3 ms. The 99th percentile is 74–76 ms. A burst at 802.11a
  waits 0.31 ms.

### Failure 4 — the mean access delay, as registered

* **The registration** wrote the occupancy as ρ = ν·T_f and the holding time as T = T_f. The
  model document means T = T_f + DIFS: medium holding time, its equation (M16).
* **As registered,** the formula held at 2 of the 9 stored delay cells with at least 95 % of
  frames delivered.
* **With T = T_f + DIFS:**
  * it held at 7 of 9 against the measured delay minus (T_f + DIFS);
  * it held at 9 of 9 against the file's own access-delay column.
* **Recorded as failed under both readings, with the registration defect noted** (Mohamed). Any
  corrected formula is to be registered and tested on new runs only.
* The 99th percentile is reported from simulation, and cells delivering below 95 % are outside
  the formula's range. Source: `results/raw/unified_trace_claims.csv`.

## C5 — the best batch under bit errors

### The probe: at 6 Mb/s with constant power, a frame is perfect or never received (F135)

* **The probe.** Two stations at a fixed received power, 802.11a 6 Mb/s, the published PHY
  (`results/raw/c5_noise_probe.csv`).
* **The result:**
  * from −70.0 to −81.9 dBm, a 173-byte or 425-byte frame suffers no bit errors at all;
  * at −82.0 dBm and below, every frame is lost because its preamble is not detected.
* **The reason, from the ns-3 source:**
  * a preamble is detected only at an SNR of at least 4 dB and a received power of at least
    −82 dBm (`threshold-preamble-detection-model.cc`, lines 31–40);
  * the noise floor is −93.97 dBm (a 7 dB noise figure over 20 MHz), so the weakest detected
    frame has an SNR of 12 dB or more;
  * there, ns-3's error model (`TableBasedErrorRateModel`) gives a 6 Mb/s frame a loss below its
    precision floor, which it sets to zero.
* **At 6 Mb/s the decoding threshold sits below the detection floor.**
* **What it means for the model.** An interior best batch needs a range of received power in
  which loss grows with frame length. With constant power at 6 Mb/s, ns-3 has no such range, so
  the batch is bounded only by the deadline and the payload. This is a statement about the
  conditions of the rule, not a failure of it.

### At 48 Mb/s with constant power (setting D1)

* **The setting.** Every link at −77.17 dBm, chosen by a rule stated before any capacity run: a
  173-byte frame loses about 3 % to noise alone. 200 records per second, b = 1 … 32.
* **The loss to noise** of each frame length is computed from ns-3's own error model. It matches
  the PHY within sampling over 23 seeds.
* **The prediction:** the best batch is 8 records, at 51.70 stations. The closed form (G19)
  gives 17.6 records; the numerical integer optimum is 12.

**Held.**
* **The best batch is the predicted one:** 8 records, at 52.78 stations against the predicted
  51.70 (−2.0 %).
* **Capacity follows the predicted shape:** it rises from 11.50 stations at one record to 52.78 at
  eight, falls to 35.10 at sixteen, and is zero at thirty-two. At 32 records a frame loses 6.4 %
  to noise alone, more than the 5 % target, and two stations already deliver only 93.4 %.
* **The model is below ns-3 at every batch:** 2–5 % up to eight records, and 7.7 % at sixteen.
  There the collision budget is only 0.35 %, so a small error in the loss moves the capacity a
  lot, as registered.
* **The closed form for the best batch (G19)** gives 17.6 records, one sweep step above the
  measured best. It straightens the airtime staircase and takes the noise slope from the first
  record only.
* **About the eight-record curve:** it is flat, falling 0.002 in delivery over 51–57 stations, and
  its 30-seed mean crosses 95 % three times (52.78, 53.70, 54.16). The prediction is within 5 % of
  each.
* Source: `predictions/UC5D1.md`, `results/raw/c5_d1_scored.csv`.

### At 6 Mb/s with per-frame fading (setting D2)

**The prediction cannot be tested in this setting** (finding F136).
* **The setting:** 6 Mb/s with Rayleigh fading on every link (Nakagami m = 1), at mean received
  powers of −70, −66.84 and −64 dBm.
* **The result:** a 146- to 425-byte frame suffers no bit errors at all. Every lost frame faded
  below the detection floor, the same share at every length (2.81 % at −66.84 dBm).
* **The reason:** ns-3 draws the fading once per frame and holds it over the frame. So each frame
  has one SNR and is either error-free or undetected, and no length dependence can arise at any
  mean power.
* **The length dependence measured on hardware must come from variation within a frame,** which
  ns-3's channel does not model. W3a found long frames losing 2.0 times the one-record frame at
  802.11b, 1 Mb/s.
* **Recorded with no capacity runs** (Mohamed, 2026-11-18).

### The hardware link

A prediction for a future hardware session, not scheduled.
* **The inputs,** at 802.11b, 1 Mb/s and 10 records per second:
  * the loss W3a measured on air through three walls, at three frame sizes per link: 147, 173 and
    1 028 bytes on the IP layer;
  * straight lines between those sizes, with nothing fitted;
  * the unified model's collision budget and root.
* **ns-3 is used nowhere** (`analysis/c5_hardware_link.py`, `results/raw/c5_hardware_bestbatch.csv`).

| receiver | transmit power | loss at 147 / 173 / 1 028 B | best batch | capacity there | capacity at 4 records |
|---|---|---|---|---|---|
| pi-B | 10 dBm | 3.14 / 3.43 / 4.45 % | **67** | 436 | 98 |
| pi-B | 4 dBm | 3.27 / 4.09 / 5.48 % | **35** | 261 | 79 |
| pi-B | 1 dBm | 13.0 / 16.5 / 29.7 % | none: even one record loses more than 5 % | — | — |
| Pi 3 | 10 dBm | 0.14 / 0.07 / 0.23 % | beyond the measured range | 827 at 101 | 143 |
| Pi 3 | 4 dBm | 0.27 / 0.45 / 0.68 % | beyond the measured range | 806 at 101 | 139 |
| Pi 3 | 1 dBm | 3.11 / 4.70 / 12.6 % | **3** | 59 | 46 |
| TP-Link | 10 dBm | 3.66 / 3.75 / 3.98 % | beyond the measured range | 505 at 101 | 90 |
| TP-Link | 4 dBm | 4.77 / 6.73 / 4.89 % | no usable prediction (the measured loss falls with length) | — | — |
| TP-Link | 1 dBm | 10.9 / 12.8 / 23.5 % | none | — | — |

**What it says.**
* **An interior best batch appears where loss grows clearly with length and is moderate:** 67 and
  35 records on pi-B's link, 3 on the Pi 3's weakest.
* **On the cleanest links the optimum lies beyond the 101 records the measurements reach.**
  There the batch is bounded by the deadline and the payload, not by loss.
* **W3a's loss swung 2–10 times between 22-second windows,** so these predictions carry that
  uncertainty. One link's loss even falls with length.

## The audit of ns-3

13 items (`docs/audits/2026-11-17_ns3_implementation_audit.md`). **None changes a published
number.** Two are documented differences:
* **The access rule.** ns-3 sends a frame that arrives to an idle medium DIFS after its arrival,
  not at once (0 of 41 409 such frames sent at once). The two rules give the same 18 capacities
  within 0.40 %.
* **802.11p airtime.** ns-3 uses a 4 µs OFDM symbol at every channel width, so 2 of 6 frames are
  4 µs shorter than the standard at 10 MHz. That is at most 1.2 % of airtime; 802.11a and b are
  exact.

The other eleven have no effect:
* EIFS never starts, because every collision's starts fall within 4 µs and no reception ends in
  error;
* the clear-channel assessment, the MAC constants, equal power with no capture, the PHY mode,
  and the delivered-fraction count;
* the random streams, and a second seed set (35.08 against 35.26);
* same-time ties;
* an assertions-on build (9 of 9 identical);
* and the 3.41 → 3.48 changes.

## Open questions

1. **U1, a finite-station, periodic-source loss expression,** for the small swarms of
   *Failure 1* and the 2–5-station hardware sessions. Registered and tested on new cells only.
   C3–C5 are now done; it waits for Mohamed's go-ahead.
2. **The hardware-matched 802.11b configuration (D4).** It needs the capture margin, the
   effective contention window and the frame-burst behaviour, which the campaign has not
   measured in simulator terms.
3. **C6 (stations hidden from part of the swarm) and C7 (LoRa duty cycle)** are not run.
4. **Fragmented units.** Spread out, fragments match the rule at a verification wait of
   (n − 1)/n of a unit period. Sent as a burst, they cost capacity, and the registered correction
   predicts only 63–75 % of the loss. Whether to model the burst further is Mohamed's decision.
5. **The detection floor under fading:** ns-3 left 2.81 % of frames below the floor where an
   exact exponential gives 3.00 % (−2.3 σ pooled). This is borderline, and it is not
   established.

### Decided by Mohamed, 2026-11-19 (added after the report; nothing above was changed)

The next phase is specified in `docs/prompts/NEXT_PHASE_PROMPT.md`. The full record, with what each
choice costs, is in `docs/DECISIONS.md` (2026-11-19).
1. **U1: go ahead,** redefined as (G25) on new ns-3 cells and a finite-station form for 2–5
   stations. The form is proposed to him before any registration.
2. **D4: no guessed values.** It becomes work package H, after the receiver rule and capture on
   hardware.
   * **Two groups:** the 5 GHz sessions recorded with frame burst off, and the 2.4 GHz sessions
     where no station's queue can build up.
   * **The window:** F116 is a literature value, not a measurement; candidate settings from the
     measured cycle, with the spread reported.
   * **Capture:** a bracket. Its capture end is an assumed channel.
3. **Fragmented units: spread fragments are the design rule.** The verification wait of
   (n − 1)/n of a unit period counts in the freshness budget. Burst sending stays a stated
   limitation. **A real implementation bursts by default, so pacing is an explicit requirement.**
   No further burst modelling.
4. **C7: run. C6: left as a stated, untested limitation.**
5. **The branch:** Mohamed merges `p12-unified-model` once CI passes. New work is on
   `p13-sending-pattern`.

## Handoff 2026-11-18 — the unified-model task (serial)

* **Green baseline:** branch `p12-unified-model` (not merged), at the commit that adds this
  report.
  * Each commit's fast suite passed in a clean worktree before it was pushed, and CI passed.
  * Registration tags: `prereg-UC1`, `UC2`, `UD`, `UC3`, `UC4`, `UC5D1`, `UC4S`, `UC4B`. All are
    held in `NOT_YET_IN_THE_THESIS`.
* **Done:**
  * the model module and its tests;
  * the 74 stored capacities scored;
  * the ns-3 audit (13 items);
  * registered runs U-C1–U-C4, U-C4S, U-C4B, U-D and U-C5-D1;
  * findings F135 and F136, and the hardware best-batch prediction;
  * this report.
* **Frozen this session:** nothing. No frozen file, paper or thesis file was touched.
* **Open, awaiting Mohamed:**
  1. **U1**, a finite-station, periodic-source loss expression: the go-ahead;
  2. **D4**, the hardware-matched 802.11b configuration: values or a rule for the capture
     margin, the effective contention window and the frame-burst behaviour;
  3. **the burst:** whether to model it further (U-C4B failed at +9 %), or to make spread
     fragments the design rule;
  4. **C6 and C7:** run them or leave them;
  5. **the branch:** merging `p12-unified-model` is his.
* **Next three steps:**
  1. whichever of 1–4 he chooses;
  2. if U1: register it on new small-swarm cells (802.11b, 5–40 stations) and the 2–5-station
     hardware sessions, before any run;
  3. if D4: document the hardware-matched configuration from live objects, each value cited or
     marked unknown.
* **Gotchas:**
  * `scripts/capped.sh NAME` names the unit `authbc-NAME`. Waiting on a misspelt unit returns at
    once, and `systemctl show` of a missing unit prints Result=success.
  * **Adding a new scratch program re-runs ns-3's configure and relinks every library.** Build
    only when no run is in flight; editing an existing program rebuilds only that target.
  * One ns-3 launch exited 127 with no recorded cause. The driver now records the stderr of any
    failed run (`run_checked`).
  * The local fast-suite count runs 3 above the recorded one while Mohamed's two untracked test
    files are present; a clean worktree matches.
  * The full reception traces (`--traceAllRx`) at about 100 stations are 50–60 MB per run, which
    the driver parses and deletes. Keep the workers at 12 or fewer.
