# Audit of the ns-3 802.11 implementation (2026-11-17)

*Work package B of Mohamed's task of 2026-11-17 (plan approved the same day). The question: does
anything in the ns-3 arm make a simulated number differ from what the paper says was simulated?
Every item states what the code does, with file and line, then the evidence from a targeted run or
trace, and ends in one of: **no effect**, **documented difference**, or **changes a number**
(→ §Decision-Request).*

**How it was done.**
* **The scenario.** All runs use `ns3/authbc-links-audit.cc`. It is `authbc-links.cc`, the
  scenario of the frozen results, plus traces that are off by default.
* **The gate.** `ns3/verify_audit_twin.py` found its default output byte-identical to the
  original binary's and to the frozen runs: 9 of 9 runs, three cells (802.11a C and D, 802.11b
  Pb1D) × seeds 1–3, `results/raw/links_audit_identity.csv`.
* **The runs.** `analysis/ns3_audit.py --run DIR` makes them, with seed 1 and the designated
  source: a jitter of one period.
* **The reductions.** `--reduce DIR` writes `results/raw/ns3_audit_items.csv` and
  `ns3_audit_access_hist.csv`.
* **The source read** is the installed ns-3.48 tree, `ns3/ns-3.48/src/wifi/model/`.

## Summary

| # | item | what the code does | evidence | effect |
|---|---|---|---|---|
| 1 | access rule | an idle (or post-busy-gap) arrival is sent **DIFS after its own arrival**, not at once; a pre-empted one keeps zero slots and goes DIFS after the busy period | 0 of 41 409 idle or gap arrivals sent at once, at four cells; 89–94 % of idle ones at exactly DIFS, the rest pre-empted | **documented difference** — ns-3 is not the loss expression's "rule A", but the two rules give the same 18 capacities within 0.40 % |
| 2 | CCA in collisions | CCA-busy from the end of the 4 µs detection, by preamble or energy | a third station idle for 0–1.6 µs of 220–364 ms of collided time; received power −30.66 dBm ≫ CCA-ED −62 dBm | **no effect** |
| 3 | EIFS | EIFS follows only a reception that ends in error | **0** receptions ending in error at all four cells: every collision falls within δ, where preamble detection fails for both frames | **no effect** (EIFS never starts) |
| 4 | post-transmission backoff | drawn after every own transmission; counts down even with an empty queue | ≤ 0.04 % of frames could meet it at three cells, ≤ 0.72 % at 802.11b 146 B (an upper bound) | **no effect** |
| 5 | PHY mode | `NonUnicastMode` set only off the default branch | every received frame at the intended mode and long preamble, all 14 cells | **no effect** |
| 6 | airtime | `OfdmPhy::GetPayloadDuration` uses a 4 µs symbol for every channel width | exact at 802.11a and 802.11b; at 802.11p **2 of 6 frames 4 µs shorter** than the standard and the model | **documented difference** (≤ 1.2 % of airtime, 802.11p only) |
| 7 | MAC constants | read back from the live objects | as the standard gives, at 802.11a, p and b | **no effect** |
| 8 | equal power, capture | one fixed loss on every link | −30.6571 dBm on every pair at N = 2 and N = 609; 0 of 98 collided frames received anywhere | **no effect** |
| 9 | delivered fraction | sink receptions ÷ (frames sent × (N − 1)) | read below; ≤ 1.2 % of frames queued behind their own, none unsent | **no effect** |
| 10 | randomness | one seed per run (`SetSeed(1)`, `SetRun(seed)`); streams assigned in construction order; designated source draws per frame | `verify_rng_isolation.py` passes on every axis; cell C under seeds 31–60: 35.08 [34.91, 35.24] against the frozen 35.26 [35.15, 35.36] | **no effect** |
| 11 | same-time ties | events at one instant run in insertion order | every collision's starts within 3 996 ns; ties at one instant are 16–90 % of collisions, and both frames are always sent | **no effect** |
| 12 | build profile | `optimized` (asserts off) for every frozen run | cell C at N = 33, 35, 37 × seeds 1–3 in a `default` build with asserts on: 9 of 9 outputs byte-identical, no assertion fired | **no effect** |
| 13 | 3.41 → 3.48 | the DCF functions changed only in form | function-by-function diff of the two installed trees | **no effect** |

---

## Item 1 — ns-3 does not follow "rule A": an idle arrival waits DIFS from its own arrival

**What the code does.**
* `ChannelAccessManager::NeedBackoffUponAccess` (`channel-access-manager.cc:548–567`): a frame
  queued to an empty queue, with no backoff left, while `IsBusy()` is false, gets zero slots and a
  backoff start of `now + SIFS + AIFSN·slot`. For the scenario's non-QoS DCF that is
  `now + DIFS` (lines 558–560).
* `IsBusy()` (499–509) counts RX, TX, NAV and CCA-busy, **not** the DIFS after a busy period. An
  arrival in that gap is therefore treated as an idle arrival.
* `GetBackoffStartFor` (789–798) takes max(own backoff start, busy end + SIFS + AIFSN·slot). A
  frame pre-empted while waiting keeps zero slots and goes DIFS after the busy period.
* The loss expression's "rule A" sends an idle arrival at once, and an arrival in the gap at the
  gap's end.
* The repository's event model (`src/authbc/sim/dcf_unsaturated.py`) sends an idle arrival at
  once, and makes a gap arrival draw a counter.
* **So three rules are in use.**

**Evidence** (`--traceMac`: each frame's MAC enqueue and PHY transmit start):

| cell | frames | idle arrivals | sent DIFS after arrival | sent at once | gap arrivals | DIFS after | at once |
|---|---|---|---|---|---|---|---|
| C (802.11a) | 34 953 | 17 548 | 15 855 | **0** | 2 048 | 1 760 | **0** |
| D (802.11a) | 30 812 | 15 351 | 14 025 | **0** | 1 554 | 1 338 | **0** |
| Pb1D (802.11b) | 7 710 | 2 306 | 2 170 | **0** | 165 | 148 | **0** |
| Pb1B (802.11b) | 9 984 | 2 206 | 1 958 | **0** | 231 | 196 | **0** |

The rest of each class were pre-empted by another start before their DIFS ran out.

**Same-instant collisions follow from this.** Pre-empted stations all hold zero slots and send at
busy end + DIFS. That is the loss expression's "zero-backoff start after a busy period". Under
ns-3 its population is the pre-empted frames, not the gap arrivals (item 11: same-instant starts
are 16–90 % of collisions).

**What it changes: nothing measurable in capacity.**
* **The method.** ns-3's rule was written as an event simulator, `src/authbc/sim/dcf_ns3rule.py`,
  with each step cited to the lines above and seven tests on frames placed by hand. It was run
  beside rule A (Mohamed's `closed_form_model.simulate`) at the eighteen configurations of docs/02
  §6g: the designated periodic source, 30 seeds, 20 s, nine node counts around each crossing
  (`analysis/ns3rule_event_check.py` → `results/raw/ns3rule_event_check.csv`).
* **The results:**
  * the ns-3 rule against ns-3: within **0.66 %** on all eighteen (largest: E −0.66 %, RB +0.62 %);
  * rule A against ns-3: within **0.74 %**;
  * **the two rules against each other: within 0.40 %.** This confirms, in ns-3, the model
    author's statement that "rule A and that rule gave the same capacity within 1 %".
* **Where the loss expression's gap comes from.** Its root is 2.5–4.5 % below ns-3 on these
  cells. That gap is not the rule; it is the Poisson-start assumption (work package A,
  `unified_gap_event.csv`).

**Verdict: documented difference.** No published number came from rule A. The repo's event
model, its closed form and ns-3 are each what they say. The loss expression's middle term was
derived for a rule ns-3 does not follow, and C1 measures it as it is.

## Item 2 — CCA holds busy through every collision

**The code.**
* CCA rises at the end of the 4 µs preamble-detection period
  (`WifiPhy::GetPreambleDetectionDuration`; `phy-entity.cc`, `StartPreambleDetectionPeriod`).
* If detection fails, the medium stays busy only while the summed power is above CCA-ED.

**Evidence.**
* **Power:** every frame arrives at −30.6571 dBm (item 8), against a CCA-ED of −62 dBm (item 7).
* **The third station:** node 0's PHY-state timeline (`--traceStateNode=0`), over every period
  in which two or more other stations' frames overlapped, from the first start + 4 µs to the last
  end:

| cell | collided periods | collided time observed | node 0 IDLE in it |
|---|---|---|---|
| C | 833 | 220.6 ms | 509 ns |
| D | 744 | 223.7 ms | 1 571 ns |
| Pb1D | 187 | 347.9 ms | 114 ns |
| Pb1B | 223 | 363.4 ms | 0 ns |

The few hundred ns are boundary effects of the 4 µs detection offset in the reduction. No station
transmits over a collision.

**Verdict: no effect.**

## Item 3 — EIFS never starts, because no reception ends in error

**The code.**
* `NotifyRxEndErrorNow` (1095–1103) sets EIFS − DIFS = SIFS + the estimated ACK time.
* `DoGetAccessGrantStart` (733–737) adds it after a reception that ended in error.
* **Values, read back from live objects:** 60 µs (802.11a, 6 Mb/s), 314 µs (802.11b, 1 Mb/s,
  long preamble), 64 µs (802.11p, 6 Mb/s).

**Evidence** (`--traceRx=1`):
* **Zero receptions ended in error at all four cells.**
* The drops, by reason (`WifiPhyRxfailureReason`, `wifi-phy-common.h`):
  * `PREAMBLE_DETECT_FAILURE` (9): 57 024 at C, 182 798 at D;
  * `TXING` (4) and `BUSY_DECODING_PREAMBLE` (8);
  * `SIGNAL_DETECTION_ABORTED_BY_TX` (24).
* **Why.** With equal power, every collision's starts fall within δ = 4 µs of each other: the
  largest spread at any cell is 3 996 ns (item 11). A later start would have been sensed. Inside
  the first frame's detection period, the signal-to-interference ratio is about 0 dB, below the
  model's 4 dB threshold. So detection fails for both frames and no reception starts, and so none
  ends in error.

**Consequence.**
* Neither the loss expression nor the event models need an EIFS term for these scenarios.
* The 802.11b −5.5 % (work package A) cannot come from EIFS. It is the Poisson assumption:
  `results/raw/unified_gap_event.csv` puts every periodic event model within 0.4 % of ns-3 there.

**Verdict: no effect** (in the equal-power scenario; with capture or unequal power it could
differ).

## Item 4 — post-transmission backoff is drawn, and almost never met

**The code.** After each own transmission the Txop draws a backoff. `UpdateBackoff` (890–923)
counts every Txop down, whether or not it has a frame.

**Evidence.** Frames enqueued within DIFS + (W − 1)·σ of their own station's last transmission
end. This is an upper bound on those that can still meet a running post-transmission backoff:
* 6 of 34 918 at C;
* 1 of 30 688 at D;
* 3 of 7 679 at Pb1D;
* 72 of 9 974 (0.72 %) at Pb1B.

**Verdict: no effect.**

## Item 5 — every frame goes at the intended mode and preamble

**The code.** `authbc-links.cc` sets `NonUnicastMode` only off the published default (802.11a,
6 Mb/s), where broadcast takes the first basic rate, which is 6 Mb/s anyway.

**Evidence** (`--traceRx=2`, `MonitorSnifferRx`): 14 cells, 802.11a at 6 / 12 / 24, 802.11p at
3 / 6 / 12, 802.11b at 1 Mb/s, with 146 B and 173 B frames.
* Every received frame was at the intended mode.
* Every frame had preamble type 0 (`WIFI_PREAMBLE_LONG`: non-HT OFDM, and the long DSSS
  preamble).

**Verdict: no effect.**

## Item 6 — airtime is exact except at 802.11p, where ns-3 rounds to half a symbol

**The code.** `OfdmPhy::GetPayloadDuration` (`non-ht/ofdm-phy.cc`, from line 245) sets
`symbolDuration = MicroSeconds(4)` for every channel width. At 10 MHz the standard's symbol is
8 µs. The payload is then a whole number of 4 µs steps, not of 8 µs symbols.

**Evidence.** Each frame's PHY transmit time (begin to end = `CalculateTxDuration`) against
`unified_capacity.airtime_s`, and against `bianchi.t_broadcast − DIFS` at 6 Mb/s:
* **Equal, to the ns, in 12 of 14 cells.** This covers every 802.11a and 802.11b cell; for
  example 268 / 304 µs at 6 Mb/s and 1 648 / 1 864 µs at 1 Mb/s.
* **At 802.11p, 6 Mb/s, 173 B:** 324 µs against 328 µs.
* **At 802.11p, 12 Mb/s, 146 B:** 164 µs against 168 µs.

**Effect.** At most 4 µs, 1.2 % of these two frames' airtime. The model (and the published
model values of `phy_links.csv`) uses the standard's airtime, so it should sit about 1 % below
ns-3 in those two cells for this reason alone. No 802.11a or 802.11b number is affected.

**Verdict: documented difference** (ns-3 departs from the standard here; it does what its source
says).

## Item 7 — the live constants are the standard's

Read from the objects (`--constants`) for 802.11a, 802.11p and 802.11b:

| | 802.11a | 802.11p | 802.11b |
|---|---|---|---|
| QoS supported | no | no | no |
| CWmin / CWmax | 15 / 1023 | 15 / 1023 | 31 / 1023 |
| AIFSN, slot, SIFS, DIFS | 2, 9, 16, 34 µs | 2, 13, 32, 58 µs | 2, 20, 10, 50 µs |
| EIFS − DIFS at the data mode | 60 µs (6 Mb/s) | 64 µs (6 Mb/s) | 314 µs |
| preamble detection | `ThresholdPreambleDetectionModel`, 4 µs | same | same |
| frame capture model | none | none | none |
| error-rate model | `TableBasedErrorRateModel` | same | same |
| CCA-ED, CCA sensitivity, RX sensitivity | −62, −82, −101 dBm | same | same |
| TX power | 16.0206 dBm | same | same |
| channel, width | 36, 20 MHz | 172, 10 MHz | 1, 22 MHz |
| MAC queue | 500 packets, 500 ms | same | same |

**Verdict: no effect.** These are the values every model in the repository assumes.

## Item 8 — equal received power on every pair, and no capture

**The code.** Log-distance loss with exponent 0 (`authbc-links.cc`, `pathLossExp = 0`) gives the
same loss on every link. Nodes stand 1 cm apart on a line.

**Evidence** (`--traceRx=2`):
* **Power:** the received signal is −30.6571 dBm on every reception, at N = 2 (198 frames) and at
  N = 609 (2 136 frames, 1 239 104 receptions), the largest N on file.
* **Capture:** none of the 98 frames that overlapped another at N = 609 was received by anyone.

**Verdict: no effect.**

## Item 9 — what the delivered fraction counts

**The code** (`authbc-links.cc`).
* **The numerator** is `g_rxCount`: every sink reception of a frame whose source recorded a send
  time (`SinkRxTrace`).
* **The denominator** is `tx_frames × (N − 1)`: every frame counts for all N − 1 peers.

**What follows.**
* **A station sending while another frame is on air** is a receiver the denominator counts and
  the numerator cannot. With equal power such overlaps are collisions, lost to all, which the
  model also counts as lost.
* **No warm-up is excluded.** Sources start at 1 s + U(0, period), so the first frames meet an
  empty channel. That is each station's first frame or so: 1 in 250–1 000 of its frames in
  these cells.
* **Frames sent just before sources and sinks stop together** (at 1 + simTime, audit F8) can
  arrive after the sinks have stopped. That is at most one airtime per station in 20 s: about
  1e-5 of frames.
* **The MAC queue** holds at most 500 packets and drops after 500 ms (item 7).

**Evidence** (`--traceMac`):
* frames queued behind their own station's earlier frame: 5, 0, 7 and 119 (1.2 %) at C, D, Pb1D
  and Pb1B;
* frames enqueued but never sent: **0** at all four.

**Verdict: no effect.** Model and simulator count the same thing.

## Item 10 — randomness

**The code** (`authbc-links.cc`).
* `RngSeedManager::SetSeed(1)` and `SetRun(seed)` (lines 265–266): each run is its own substream,
  and runs at different N are independent samples, not paired.
* Random variables take stream indices in construction order. Every option that adds one does
  so only off the default path, with a fixed stream: positions 4096 (`radiusM`), the traced
  pairs 12288 (`traceLinks`, held by `links_identity.csv`).
* The designated source draws each frame's instant within its period from its own variable.
* **The crossing.** Interpolated between the last node count whose 30-seed mean passes 0.95 and
  the first that fails. Its interval is bootstrapped over seeds at every N
  (`stats.interpolated_crossing_ci`).

**Evidence.**
* **`ns3/verify_rng_isolation.py`, re-run:** it passes on every axis. For a fixed seed, the
  frames sent do not move with the channel model, the gateway region or the interference matrix
  (the LoRa scenario's check of F37).
* **Cell C, the designated source, N = 31–37, under a second independent seed set (31–60):**
  * **crossing 35.08 [34.91, 35.24]**, against the frozen seeds 1–30's 35.26 [35.15, 35.36];
  * a difference of −0.18 nodes (−0.5 %), with the two intervals overlapping;
  * per node count, the two 30-seed means agree within 0.0008
    (`results/raw/ns3_audit_seedset2{,_runs}.csv`).

**Verdict: no effect.** A fresh 30-seed sample moves this crossing by 0.5 %. That is the size of
the sampling noise every 30-seed crossing in the paper carries.

## Item 11 — same-instant events: both stations always send

**The code.** ns-3 runs events with the same timestamp in insertion order. A start cannot be
sensed for 4 µs anyway (item 2), whatever the order and whatever the propagation delay.

**Evidence** (`--traceMac`): the start spread inside every group of overlapping frames.

| cell | collisions | same instant | spread 0–1 µs | 1–2 | 2–3 | 3–4 | largest |
|---|---|---|---|---|---|---|---|
| C | 879 | 304 | 617 | 98 | 86 | 78 | 3 996 ns |
| D | 763 | 119 | 566 | 56 | 78 | 63 | 3 978 ns |
| Pb1D | 196 | 104 | 179 | 3 | 6 | 8 | 3 958 ns |
| Pb1B | 281 | 252 | 261 | 10 | 5 | 5 | 3 845 ns |

**Propagation delay.** The scenario places nodes 1 cm apart, so it is non-zero but below 1 ns.
No collision spread reaches 4 µs, so ordering could matter only below that, where both frames are
sent regardless.

**Verdict: no effect.**

## Item 12 — build profile

**The question.** The frozen runs use the `optimized` profile, with `NS3_ASSERT` off (ns3/README.md).
An assertion that would have fired is then silent.

**Evidence.**
* **The build.** The ns-3.48 tree was copied to `ns3/ns-3.48-asserts/` (git-ignored) and
  configured `--build-profile=default` ("Build with runtime asserts: ON"). `authbc-links.cc` was
  built there, unchanged.
* **The runs.** Cell C (146 B, 50 frames/s, the designated source) at N = 33, 35 and 37, seeds
  1–3, through both builds.
* **9 of 9 outputs were byte-identical, and no assertion fired.**

**Verdict: no effect.**

## Item 13 — nothing in 3.41 → 3.48 changes the DCF rule

**The release notes.** Of the relevant entries, by section:
* 3.45 fixed the EIFS computation. EIFS never starts here (item 3).
* 3.46 changed the slot alignment of immediate access. That code (lines 590–598) runs only for QoS
  stations, and the scenario's are not.
* 3.46 also resets backoffs only after sleep or off, and 3.47 fixed CCA after a channel-width
  change. Neither applies here.

**The code.** `NeedBackoffUponAccess`, `IsBusy`, `GetBackoffStartFor` and `UpdateBackoff` were
diffed between the two installed trees:
* `IsBusy` is identical;
* the others differ only in form: a `const` overload, the access-grant start passed in, and the
  sleep/off test read from the PHY.

**Verdict: no effect.** The access rule of item 1 is the same in both versions.
