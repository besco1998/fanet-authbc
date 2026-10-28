# AUTHBC Revision Plan

Oct 19, 2026 · @Mohamed Ashraf

## How to read this plan

Run Part A first: 17 experiments that need only the existing Intel host, the two Raspberry Pi 4 boards and free software. Part B (5 experiments) needs new hardware and is ordered from cheapest to most expensive. Within each part, experiments are ordered by how strongly they answer a likely reviewer objection or add novelty.

Every experiment is written as: **Fixes** (which weakness), **Setup**, **ns-3 / software configuration**, **Sweep**, **Metrics**, **Expected outcome** (a prediction to register before running), **Effort**, and **Paper deliverable**.

| ID | Experiment | Fixes | Priority | Effort | New hardware |
| --- | --- | --- | --- | --- | --- |
| A1 | Multi-hop, mobility, realistic propagation | Single collision domain | Critical | 3 weeks | None |
| A2 | Λ × Dmax design map + AoI under loss | Fragile b ≤ 4 operating point | Critical | 1 week | None |
| A3 | Verifiability margin (ε > p, loss-aware b) | Zero margin at 0.95 | Critical | 1 week | None |
| A4 | Adaptive batching controller | Novelty | High | 4 weeks | None |
| A5 | GNSS-time replay rule | Delayed replay accepted | High | 1 week | None |
| A6 | Tamarin formal model | Informal security argument | High | 2–3 weeks | None |
| A7 | DoS quantification + Ed25519 batch verify | Flooding not resisted | High | 1 week | None (existing Pi) |
| A8 | Compiled C/Rust receiver and sender | Python CPU and energy anomaly | High | 2–3 weeks | None (existing Pi) |
| A9 | Record-size sensitivity + 50 Hz SITL flights | Synthetic 9-field telemetry | Medium | 1 week | None |
| A10 | TESLA and EMSS implemented in ns-3 | Comparators only sized on paper | Medium | 2 weeks | None |
| A11 | 802.11p and NR sidelink | One PHY only | Medium | 2–3 weeks | None |
| A12 | N·f equivalence check | Prepares B2 | Medium | 2 days | None |
| A13 | Lazy verification | Novelty, CPU bound | Medium | 2 weeks | None |
| A14 | Relay signature aggregation | Novelty, multi-hop | Low–medium | 3 weeks | None |
| A15 | Post-quantum path (Falcon-512) | No PQ path | Low–medium | 1 week | None |
| A16 | Ledger audit and merge protocol | "Blockchain" framing | Low | 2 weeks | None |
| A17 | Accounting for ADS-B, Remote ID, V2X | Generality claim | Low | 3 days | None |
| B1 | Third radio for monitor-mode capture | Unexplained hardware mismatch | High | 1 week | 1 radio |
| B2 | Scaled testbed, 5–10 radios | No hardware capacity | High | 3–4 weeks | 3–8 radios |
| B3 | MCU port + calibrated energy meter | Energy measurement quality | Medium | 3 weeks | MCU boards, meter |
| B4 | Air-to-air loss traces | Synthetic loss models | Medium | 2–3 weeks | Drones or masts |
| B5 | Multi-drone flight test | End-to-end realism | Low (next paper) | 6+ weeks | 3+ drones |

### Shared ns-3 baseline (reused by every simulation)

Keep the paper's baseline unchanged, so every new result is comparable with Table 3. Each experiment below lists only what it changes.

```cpp
// ns-3.48 baseline: one collision domain, equal received power
WifiHelper wifi;
wifi.SetStandard(WIFI_STANDARD_80211a);
wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
    "DataMode", StringValue("OfdmRate6Mbps"),
    "NonUnicastMode", StringValue("OfdmRate6Mbps"));

YansWifiChannelHelper ch;
ch.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel");
ch.AddPropagationLoss("ns3::FixedRssLossModel", "Rss", DoubleValue(-60.0));

YansWifiPhyHelper phy;
phy.SetChannel(ch.Create());
// no capture in the baseline; A1 enables SimpleFrameCaptureModel

WifiMacHelper mac;
mac.SetType("ns3::AdhocWifiMac");

// Traffic: one broadcast frame per period b/Λ, send instant drawn
// uniformly inside each period (the paper's jittered periodic source).
// Run: 20 s, 30 seeds via RngSeedManager::SetRun(k), k = 1..30.
```

Common rules for all simulations:

- **Nmax**: the largest N whose mean delivered (or verified) fraction is at least 0.95, with every smaller N also passing; 95% CI from 10 000 bootstrap resamples of the seeds.
- **Configurations always run in pairs**: baseline (row 5, 145.77 B/record) and design (row 8, 43.25 B/record), so the ratio is reported in every scenario.
- **Registration**: write each Expected outcome into the repository, with a commit hash, before the first run. This keeps the paper's pre-registration claim true for the revision.

## Part A — No new hardware: critical experiments

These four answer the objections most likely to block acceptance. A1–A3 can run in parallel on the Intel host; A4 depends on A1's scenarios.

### A1. Multi-hop topologies, swarm mobility and realistic propagation

**Fixes:** every capacity number comes from one collision domain with equal received power, static nodes and no hidden terminals.

**Setup:** three scenarios, each run for the baseline (row 5), row 6 and the design (row 8).

1. **S1 static random disc.** N nodes placed uniformly in a disc at 50–150 m altitude. Radius R ∈ {100, 300, 600, 1000} m, so the mean neighbor count and the hidden-node share both vary.
2. **S2 hidden-terminal grid.** Two clusters whose centers are farther apart than the carrier-sense range but whose receivers sit between them. This isolates the hidden-terminal effect.
3. **S3 swarm mobility.** Group mobility: one reference point moving with Gauss–Markov, members moving around it. Speeds {0, 5, 15} m/s.

**ns-3 configuration (changes from the baseline):**

```cpp
// Propagation: air-to-air is close to free space; add mild fading
ch.AddPropagationLoss("ns3::LogDistancePropagationLossModel",
    "Exponent", DoubleValue(2.0),
    "ReferenceDistance", DoubleValue(1.0),
    "ReferenceLoss", DoubleValue(46.7));   // ~5.2 GHz at 1 m
ch.AddPropagationLoss("ns3::NakagamiPropagationLossModel",
    "m0", DoubleValue(3.0), "m1", DoubleValue(3.0), "m2", DoubleValue(3.0));

phy.Set("TxPowerStart", DoubleValue(20.0));
phy.Set("TxPowerEnd",   DoubleValue(20.0));
phy.SetFrameCaptureModel("ns3::SimpleFrameCaptureModel",
    "Margin", DoubleValue(4.0));            // same 4 dB as the paper

// S3 mobility: GroupMobilityHelper (ns-3 >= 3.34)
GroupMobilityHelper group;
group.SetReferenceMobilityModel("ns3::GaussMarkovMobilityModel",
    "MeanVelocity", StringValue("ns3::UniformRandomVariable[Min=5|Max=15]"),
    "Bounds", BoxValue(Box(-1000, 1000, -1000, 1000, 50, 150)));
group.SetMemberMobilityModel("ns3::RandomWalk2dMobilityModel",
    "Bounds", RectangleValue(Rectangle(-60, 60, -60, 60)));
```

Run one more scenario with `FixedRssLossModel` and the same code path. It must reproduce Table 3; this proves the new code did not shift the baseline.

**Sweep:** N from 20 to 400 in steps of 20 (finer near each crossing) × R × speed × 3 configurations × 30 seeds.

**Metrics:**

- **Neighbor set**: nodes within d\_ref, the distance at which an isolated two-node link delivers at least 99%. Measure d\_ref first.
- **Per-receiver V**: the fraction of neighbors' records that are received, decoded and verified.
- **Capacity**: the largest mean neighbor count (and the node density per km²) with mean V ≥ 0.95. In a single disc this reduces to Nmax.
- Hidden-node share per receiver, peak age of information (mean and 95th percentile), and the design-to-baseline capacity ratio.

**Expected outcome (register before running):**

- The fixed-RSS run reproduces Table 3 within its CIs (35 and 124).
- In S1 at R = 1000 m and S2, absolute capacity falls below the single-domain value, because hidden terminals add collisions.
- **The ratio stays between 3.0× and 4.0×.** Reason: a hidden-node collision needs two overlapping frames, and the design sends a quarter as many frames, each only about 15% longer on air.
- Mobility up to 15 m/s changes V by less than 0.01. A node moves at most 1.2 m during one 80 ms fill time.
- If the ratio falls below 2.5×, report it as a finding and explain it with the hidden-node share.

**Optional extension:** add a spatial Poisson term for hidden nodes to the access-rule event model. Show that it predicts the S2 crossings with nothing fitted.

**Effort:** 3 weeks. **Paper deliverable:** a figure of capacity against neighbor density for the three scenarios, and a new paragraph in Results 3.5 that replaces the single-domain limitation.

### A2. Λ × Dmax design map and age of information under loss

**Fixes:** b ≤ 4 follows from ΛDmax = 5 exactly, so the headline numbers depend on one chosen operating point.

**Setup:** mostly analytic, using equations (1), (2) and (6) and the event model. ns-3 validates a subset of cells.

- Λ ∈ {10, 20, 25, 40, 50, 75, 100} records/s.
- Dmax ∈ {40, 60, 80, 100, 150, 200, 250, 500} ms.
- For each cell: b\* = the largest b with b/Λ + Tch + tv ≤ Dmax. Use Tch = 3.49 ms (worst case observed) and tv = 0.26 ms.
- **Emit real frames at each Λ**, because the delta-record size depends on the record spacing (9.0 B at 20–50 ms, 13.6 B at 5.5 s).
- Check the MTU in every cell. It should never bind below 151 records.

**ns-3 configuration:** the baseline unchanged. Validate 10 cells: the four corners, the diagonal and (50, 100) as a control. 30 seeds each.

**AoI under loss:** run the codec-in-the-loop harness with frame loss p ∈ {0, 0.01, 0.05, 0.10}. Record the peak age at the receiver for every verified record.

**Metrics:** b\*, bytes per record, predicted and simulated Nmax, the design-to-baseline ratio per cell, and the AoI mean, 95th and 99th percentiles.

**Expected outcome (register before running):**

- The gain region is exactly ΛDmax > 2; every cell with ΛDmax ≤ 2 shows a ratio of 1.0.
- The ratio grows with b\*. At (100 records/s, 100 ms), b\* = 9 and the ratio exceeds 5×.
- Simulated Nmax at the 10 validation cells falls within 5% of the event model.
- Under loss, the mean extra age is about (b/Λ)·p/(1−p): at b = 4 and p = 0.05 that is about 4 ms, so the 16.2 ms margin holds on average. The 99th percentile exceeds Dmax whenever two consecutive frames are lost. Report this honestly.

**Effort:** 1 week. **Paper deliverable:** a two-panel heatmap (b\* and capacity ratio over Λ × Dmax) that replaces the single operating point as the main design figure, plus an AoI CDF in the Supplement.

### A3. Verifiability margin

**Fixes:** the design meets V ≥ 0.95 with zero margin (0.952, CI \[0.947, 0.957\]), and length-dependent loss pushes it to 0.947.

**Setup:** the existing codec-in-the-loop harness: 7 200 frames per cell and 30 seeds.

- **Loss models:** independent; Gilbert–Elliott with the same mean and burst lengths of 2, 4 and 8 frames; length-dependent, with the BER set so that a one-record baseline frame is lost with probability p.
- **Trace-driven loss** taken from the A1 ns-3 runs: per-link success sequences exported from S1 and S3. This gives correlated, realistic loss without new hardware.

**Sweep:** p ∈ {0.01, 0.02, 0.03, 0.05, 0.08} × ε ∈ {0.05, 0.08, 0.10} × b ∈ {1, 2, 3, 4} × r ∈ {1, 2, 4}.

**Metrics:** V with its bootstrap CI, the largest p that still meets the target for each b (the "tolerable loss"), and bytes per record.

**Expected outcome (register before running):**

- r = 1 passes with margin whenever ε ≥ p + 0.02. Example: p = 0.05 and ε = 0.08 gives V ≈ 0.95, which is 0.03 above the target.
- Under length-dependent loss, the tolerable baseline-frame loss is about 0.044 at b = 4 (as in the paper) and about 0.047 at b = 2.
- Trace-driven V lies between the independent and Gilbert values, because ns-3 collision loss is mildly bursty.

**Effort:** 1 week. **Paper deliverable:** a figure of V against p per b with the ε lines, and a stated deployment rule ("set ε at least 0.02 above the expected frame loss") in the Discussion.

### A4. Adaptive batching controller (main novelty addition)

**Fixes:** reviewers may see the contribution as accounting only. This turns the validated capacity model into a control law.

**Design:**

- Each node re-chooses b once per control period (1 s).
- It estimates channel occupancy ρ̂ from its own PHY state (time in CCA-busy, RX and TX over the period), and frame loss p̂ from sequence gaps in its neighbors' frames.
- **Policy:** use the smallest b (lowest age of information) whose predicted delivery at ρ̂, from equation (6) or the event model, is at least 0.95 plus a margin. b never exceeds b\_max from the freshness bound.
- Hysteresis: change b by at most one step per period, and only after two periods agree.
- **Deadline flush:** send a partial frame early when a record changes sharply (for example a velocity change above a threshold). This keeps maneuvers fresh.

**ns-3 configuration:** implement the controller inside the traffic application. Read occupancy from the PHY state trace:

```cpp
Config::Connect(
  "/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/State",
  MakeCallback(&BusyTimeTracker::OnState));
// accumulate time in CCA_BUSY, RX and TX per 1 s control period -> rho_hat
```

**Scenarios:** a density ramp from 20 to 200 nodes over 120 s; a swarm merge (two groups of 60 merge at t = 60 s and split at t = 120 s); and S3 mobility from A1.

**Baselines:** fixed b = 1, fixed b = 4, and an oracle that knows the true N.

**Metrics:** V over time, the fraction of time with V ≥ 0.95, mean and 95th-percentile AoI, bytes per record, and the number of b changes per minute.

**Expected outcome (register before running):**

- Below about 35 nodes, the controller stays at b = 1 and its mean AoI matches fixed b = 1 within 10%. That is about 30 ms fresher than fixed b = 4, since the mean wait drops by (b−1)/(2Λ).
- At high density it reaches b = 4 and keeps V ≥ 0.95 up to about 120 nodes, within 5% of fixed b = 4.
- It meets the target at least 95% of the time in the merge scenario. Fixed b = 1 fails above 35 nodes, and fixed b = 4 pays the extra age at all densities.

**Effort:** 4 weeks. **Paper deliverable:** a new contribution bullet and a Results subsection ("Adaptive batching"), with a time-series figure of the merge scenario.

## Part A — No new hardware: security, implementation and workload

These close the security and prototype weaknesses. A7 and A8 use the two Raspberry Pi 4 boards you already have.

### A5. GNSS-time replay rule

**Fixes:** a frame held back by an attacker is accepted however old it is, because replay is refused by sequence number only.

**Design:** every record already carries `ts` in ms, and every UAV has GNSS time. Add one receiver rule at **zero extra bytes**:

```latex
t_{\text{local}} - ts_{\text{newest}} \le \Delta_{\text{acc}} = \frac{b}{\Lambda} + T_{ch} + t_v + 2\sigma_{clk} + g
```

Here σ\_clk is the clock error between sender and receiver and g is a guard time. If GNSS time is lost, the margin grows with crystal drift. After a set outage time, the receiver falls back to sequence-only checking and marks the records as "time unverified".

**Setup:** the codec harness plus a delay-injection adversary. No radio is needed.

- Clock error: Gaussian with σ ∈ {1, 10, 50} ms. GNSS outage drift of 20 ppm per node, with outages of 0–60 min.
- Adversary delays a fraction of frames by δ ∈ {10, 50, 100, 250, 1000, 10 000} ms.

**Metrics:** detection rate of delayed frames against δ; false rejection of honest frames; the longest GNSS outage before the fallback.

**Expected outcome (register before running):**

- With σ ≤ 10 ms and Δ\_acc = 150 ms, honest false rejection stays below 10⁻⁴, and every delay above 150 ms is detected.
- Two clocks drifting at 20 ppm in opposite directions separate by 72 ms per hour, so a 250 ms window survives about 2 hours of outage.

**Effort:** 1 week. **Paper deliverable:** a new security property (v), "bounded-delay freshness", which moves an item from "not protected" to "protected while GNSS time is held".

### A6. Formal security model in Tamarin

**Fixes:** the security argument is informal.

**Model:**

- **Roles:** a sender that signs a frame over its ledger records, sequence number and link; a receiver that rebuilds, verifies and stores.
- **Adversary:** Dolev–Yao (the network), plus a Reveal rule to compromise a sender's key.
- **Canonical encoding** is modeled as an injective function. State this as an assumption, supported by the 10 000-trial byte-identity test and the all-bit-flip test.
- **Sequence numbers** are kept as monotonic per-sender state facts.

**Lemmas:**

1. **Origin and integrity:** injective agreement on the frame content between an honest sender and the receiver, unless the sender's key is revealed.
2. **Replay:** no frame is accepted twice by the same receiver.
3. **Equivocation evidence:** two accepted frames with the same sender and sequence number but different content imply two valid signatures by that sender. Either the sender equivocated, or its key was revealed.
4. **Continuity:** a receiver that holds records i and i+2 of one sender but not i+1 detects the gap.
5. **Sanity check:** without the A5 time rule, Tamarin finds a delayed-replay trace. With A5 added (an abstract clock), the trace disappears.

**Expected outcome:** lemmas 1–4 are proven; lemma 5 shows the attack first and then its fix. This turns two stated limitations into one proof plus one demonstrated mitigation.

**Effort:** 2–3 weeks (counter state can need hand-written helper lemmas). **Paper deliverable:** replace "we did not verify it with a formal tool" with the model, and publish the `.spthy` file in the repository.

### A7. Flooding / DoS quantification and mitigation

**Fixes:** every injected frame costs a receiver one decode and one verification, and the cost was never quantified.

**Setup:** existing Pi 4 receiver. Feed frames through a local UDP socket, so the radio is not in the loop. This measures CPU cost only; radio-level injection belongs to Part B.

- **Attack frames:** well-formed CBOR that names a known sender, with a newer sequence number and an invalid signature. This is the worst case, because it passes every cheap check.
- **Attack rate:** 0–3 000 frames/s. For reference, one 173-byte frame at 6 Mb/s takes roughly 0.3 ms of air, so a single attacker radio can send close to 3 000 frames/s.
- **Honest load:** 124 senders at 12.5 frames/s each.

**Mitigations compared:**

| Mitigation | Bytes added | What it costs the attacker |
| --- | --- | --- |
| None (current) | 0 | Nothing beyond airtime |
| Cheap checks first (length, canonical form, sequence window) | 0 | Must craft valid-looking frames |
| Per-sender rate cap at (Λ/b)·(1 + slack) | 0 | Can only crowd out the sender it impersonates |
| 8-byte truncated group HMAC, checked before the signature | 8 per frame (2 per record) | An outsider is rejected at hash cost (a few µs) |
| Ed25519 batch verification (64 per batch) | 0 | A bad signature forces a slower fallback search |

**Metrics:** honest V against attack rate for each mitigation, receiver core share, and the attack rate at which honest V drops below 0.95.

**Expected outcome (register before running):**

- With no mitigation, about 700 fake frames/s saturate one core of the Python receiver (1.43 ms per frame).
- With the group HMAC, an outsider needs more than 100 000 frames/s to saturate a core, which the channel cannot carry. Outsider flooding is effectively removed.
- An insider holding a valid swarm key remains a threat; the per-sender cap limits that damage to the sender being impersonated.
- The HMAC's 2 bytes per record reduce Nmax by about 2% (by equation 6).

**Effort:** 1 week. **Paper deliverable:** a DoS paragraph in the threat model, and an optional HMAC field in the frame format.

### A8. Compiled sender and receiver on the existing Pi

**Fixes:** the interpreted receiver makes the CPU bind before the channel (57 nodes per core), and the lean sender uses 2.7× the energy of the first format.

**Setup:**

- Rust (`ed25519-dalek`, `p256`, a canonical CBOR encoder) or C (libsodium plus QCBOR or TinyCBOR). Rust is safer to get right quickly.
- **Byte-identity gate:** 10 000 frames encoded by Python and by the compiled codec must match byte for byte, and each implementation must verify the other's frames. Publish these as golden test vectors.
- **Energy:** the same INA219 rig and procedure (5 repetitions, idle subtracted). Add a basic calibration against a known power resistor and a bench multimeter.

**Metrics:** time per received 4-record frame (decode, rebuild, verify), nodes per core from equation (4) with the real cost, sender energy per record for both formats, and batch-verify speedup.

**Expected outcome (register before running):**

- Receive time per frame drops from 1.43 ms to at most 0.35 ms. Verification (about 259 µs, already native code) then dominates.
- One core serves at least 230 nodes, so 124 nodes need one core and **the channel binds again**, as the theory says.
- Energy per record follows the bytes: the lean format becomes cheaper than the first format. This removes the anomaly from the Results.

**Effort:** 2–3 weeks. **Paper deliverable:** an updated Results 3.6 and Table 6 row ("compiled receiver"), and the compiled code in the artifact repository.

### A9. Record-size sensitivity and 50 Hz SITL flights

**Fixes:** a 9-field synthetic record, and 50 Hz validation that rests on one simulated flight.

**Setup:**

- **Record sets:** 9 fields (current); 15 fields (adding attitude, body rates and GNSS fix quality); 25 fields (adding mission item, airspeed, wind estimate and health flags).
- **PX4 SITL** with Gazebo: a quadrotor, a VTOL and a fixed-wing airframe, 10 missions each. Fixed-wing missions go up to 25 m/s. Log position, attitude and status topics at 20 ms intervals using a custom logger profile.
- Add any public Flight Review logs that carry estimator topics faster than 5 Hz, chosen by the same pre-fixed rule as before.

**Metrics:** keyframe and delta sizes, B(b) for b = 1–4, the byte reduction, and the predicted capacity ratio by equation (6). Find the record size at which the capacity ratio falls below 2×.

**Expected outcome (register before running):**

- At 25 fields (keyframe about 60 B, delta about 25 B), the byte reduction is still about 65%.
- The capacity ratio stays near 3×, because frame count, not bytes, dominates.
- Fixed-wing deltas reach 10–13 B at 50 Hz, about 1–2 B more than the quadrotor.

**Effort:** 1 week. **Paper deliverable:** a record-size sensitivity figure, and a general rule in the Discussion (batching pays while the authenticator is large relative to the record).

## Part A — No new hardware: comparators, other links and extensions

These widen the evidence and add novelty. Run them after A1–A9, or keep the later ones (A13–A16) for a follow-up paper.

### A10. TESLA, EMSS and Wong–Lam implemented in ns-3

**Fixes:** Table 5 sizes the comparators from their definitions; none is implemented.

**Setup:** implement each as an application on the shared baseline.

- **TESLA:** a MAC per frame; the key is disclosed d intervals later; receivers buffer until the key arrives. Interval length ∈ {10, 20, 50} ms, d ∈ {1, 2}.
- **EMSS:** each packet carries the hashes of earlier packets, with a signature packet every k ∈ {4, 8, 16} packets.
- **Wong–Lam tree:** block of 4, as in Table 5.
- **Extra hybrid: TESLA with b = 4 batching.** This shows whether batching is independent of the authenticator.

**Metrics:** frame delivery Nmax (should reproduce Table 5), and the more important **deadline-aware V**: the fraction of records verified within Dmax = 100 ms, including the wait for a key or a signature packet.

**Expected outcome (register before running):**

- Delivery Nmax reproduces Table 5 within its CIs: 42, 40, 39, 34 and 28 nodes.
- Deadline-aware V falls well below delivery for TESLA and EMSS whenever the key disclosure or signature interval approaches Dmax. Their real capacity under the freshness constraint is therefore below the Table 5 upper bound.
- TESLA with b = 4 gives the smallest frames of all, but still without non-repudiation. This supports the claim that the frame, not the authenticator, binds.

**Effort:** 2 weeks. **Paper deliverable:** Table 5 becomes simulated, with a new deadline-aware V column, and footnote 2 ("an upper bound") goes away.

### A11. 802.11p and NR sidelink

**Fixes:** one PHY at one rate. Sidelink is the most relevant 3GPP link for UAV-to-UAV broadcast, and reviewers will ask about it.

**802.11p configuration:**

```cpp
wifi.SetStandard(WIFI_STANDARD_80211p);   // 10 MHz channel
wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
    "DataMode", StringValue("OfdmRate6MbpsBW10MHz"),
    "NonUnicastMode", StringValue("OfdmRate6MbpsBW10MHz"));
// OCB mode (no BSS). The WAVE helper was removed in recent releases;
// check how ns-3.48 exposes OCB through WifiMacHelper before running.
```

Sweep: 802.11p at 3, 6 and 12 Mb/s, and 802.11a at 6, 12 and 24 Mb/s. Baseline and design at each rate, single collision domain.

**NR sidelink:** the 5G-LENA NR V2X extension, mode 2 (sensing-based semi-persistent scheduling). It is released against a specific ns-3 version, so run it on that version rather than 3.48. Configuration: numerology µ = 0 and 1, 10 MHz and 20 MHz, fixed MCS. Set the reservation period to match the frame period (20 ms for the baseline, 80 ms or the nearest allowed value for the design).

**Metrics:** Nmax per link and rate, the design-to-baseline ratio, and the event model's prediction for 802.11 links.

**Expected outcome (register before running):**

- On 802.11, the simulated ratio follows the Supplementary Note 7 trend (1.7× to 4.3×) and grows with PHY rate. The event model predicts every crossing within 3%.
- On NR sidelink, the gain is smaller (about 1.5–2.5×). The fixed cost there is the granularity of the resource allocation rather than a preamble and backoff, and payloads are rounded up to whole subchannels.

**Effort:** 2–3 weeks (most of it setting up the sidelink build). **Paper deliverable:** a capacity table across link layers; the Discussion paragraph on other links becomes simulated.

### A12. N·f equivalence check (preparation for B2)

**Fixes:** nothing yet; this enables hardware capacity measurement with few radios.

**Setup:** the shared baseline. Keep the total offered frame rate N·f fixed and vary how it is split: for the design at its crossing, (N, f) = (124, 12.5), (62, 25), (31, 50), (16, 97), (8, 194) frames/s. Repeat for the baseline crossing.

**Metrics:** delivered fraction for each split.

**Expected outcome (register before running):** delivery is the same within 0.01 for N ≥ 16. For small N it is slightly higher, because a node never collides with itself. A correction factor of (N − 1)/N on the contending load brings all splits within 2%.

**Effort:** 2 days. **Paper deliverable:** a Supplementary Note that justifies the B2 testbed method.

### A13. Lazy verification: a real-time path and an evidence path

**Fixes:** novelty, and the receiver CPU bound.

**Design:** two tiers per frame.

- **Real-time tier:** check the 8-byte group HMAC from A7 immediately (a few µs). Use the records at once for collision avoidance. This blocks outsiders.
- **Evidence tier:** queue the frames and verify Ed25519 signatures in batches of 64 every 100 ms before writing to the ledger. A frame that fails is purged from the ledger and flagged.

**Setup:** the A8 compiled receiver on the existing Pi, with recorded frame streams from A1 replayed at 50–500 senders.

**Metrics:** nodes per core, time until a record becomes evidence, and under an insider attack the fraction of real-time actions taken on frames that later fail.

**Expected outcome (register before running):** with batch verification at 0.46× per signature, nodes per core roughly double compared with one-at-a-time verification, and exceed 500 with the compiled receiver. Records become evidence within 100–200 ms. The insider risk is limited to the HMAC holder, which is stated as a trade-off.

**Effort:** 2 weeks.

### A14. Signature aggregation at relays

**Fixes:** novelty; it also links the work properly to the CLAS literature instead of a loose comparison.

**Setup:** the A1 S1 multi-hop scenario. Relays forward neighbors' frames toward distant nodes or a ground station. Compare:

- forwarding frames unchanged;
- Ed25519 half-aggregation (about 32 bytes per signature plus 32), noting that it is a research construction, not a standard;
- BLS12-381 aggregation (one 48-byte signature for many frames), with verification at a ground station that has a stronger CPU.

**Metrics:** bytes on the relay links, relay and verifier CPU, and end-to-end delay.

**Expected outcome:** half-aggregation cuts relay signature bytes by about 50% at little CPU cost. BLS gives the smallest relay frames but is only practical where the verifier is a ground station, consistent with its 10 nodes per core on the Pi.

**Effort:** 3 weeks.

### A15. Post-quantum path with Falcon-512

**Fixes:** the paper concludes that post-quantum signatures do not fit, but checks only ML-DSA (2 420 B).

**Setup:**

- Falcon-512 (about 666 B) through liboqs on the existing Pi. Measure sign and verify times.
- Frame at b = 4: about 23 + 35 + 666 + 24 + 27 ≈ 775 B, well under the 1 500-byte MTU.
- Simulate the baseline and design with Falcon on the shared ns-3 baseline.
- Hybrid variant: Ed25519 on every frame for real-time checking, plus a Falcon signature every k frames over the hash chain for post-quantum evidence.

**Expected outcome (register before running):** an equation (6) estimate gives about 12 nodes with per-record Falcon and about 45 with the design. That is a ratio near 3.9×, **larger than with Ed25519**, because batching amortizes a much bigger signature. If confirmed, this turns a limitation into a positive finding: batching matters more in the post-quantum era.

**Effort:** 1 week. **Paper deliverable:** the limitation paragraph on post-quantum signatures is replaced with a short result.

### A16. Ledger audit and merge protocol

**Fixes:** "blockchain-style ledger" may promise more than the paper delivers; there is no consensus or audit step.

**Design:** after the mission, each UAV uploads its own chain and the neighbor records it stored. A merge step:

1. checks each sender's own chain for continuity;
2. checks the links that receivers stored unchecked against the senders' own chains;
3. collects equivocation pairs as evidence;
4. publishes a signed audit report with a Merkle root per mission.

**Setup:** run on recorded ledgers from A1 and A4 scenarios. Add a forensic test in which one UAV equivocates and another tries to fill a gap with a forged record.

**Metrics:** audit time per flight hour, storage per hour, and detection of the injected faults.

**Expected outcome:** both injected faults are detected. Storage is the likely surprise: 50 records/s for an hour at about 60 B per ledger record is about 11 MB per sender, so a node storing 124 neighbors needs about 1.3 GB per hour. Report this and propose storing neighbors at a reduced rate.

**Effort:** 2 weeks. If skipped, rename "blockchain-style ledger" to "hash-chained log" in the title and text.

### A17. The same accounting for ADS-B, Remote ID and V2X

**Fixes:** the closing claim that the accounting carries over to other broadcast systems is untested.

**Setup:** analysis only. Apply equations (1)–(5) to:

- ADS-B 1090ES (112-bit messages);
- Broadcast Remote ID over Bluetooth 4 legacy advertising, Bluetooth 5 extended advertising and Wi-Fi;
- ETSI CAM at 10 Hz with a certificate digest.

**Expected outcome:** ADS-B and Bluetooth 4 Remote ID cannot carry a self-verifying frame; Bluetooth 5 and Wi-Fi Remote ID can. CAM at 10 Hz with a 100 ms deadline has ΛDmax = 1, so no batch is admitted. That explains, from your own rule, why V2X standards sign each message.

**Effort:** 3 days. **Paper deliverable:** a short Discussion table that supports the generality claim.

## Part B — Additional hardware

Part B is ordered by value per unit of cost. B1 and B2 answer the strongest remaining objection: no capacity was measured on hardware. Costs are rough estimates from memory, not quotes.

| ID | New hardware | Approx. cost | Depends on |
| --- | --- | --- | --- |
| B1 | 1 USB 5 GHz adapter with monitor mode | USD 40–80 | — |
| B2 | 3–8 more radio nodes (same chipset), wired control network | USD 300–800 | A12, B1 |
| B3 | MCU boards + power profiler (e.g., Nordic PPK2) or Joulescope | USD 150–1 100 | A8 |
| B4 | Radios on 2–3 drones or on masts | Existing drones, or masts | A3 |
| B5 | 3–5 drones with companion computers | Existing fleet, flight permits | A4, A8, A16 |

### B1. Third radio for monitor-mode capture

**Fixes:** below saturation, the two-radio test lost 1.13, 0.79 and 0.56 times the predicted loss, and the cause was not found (Supplementary Note 6).

**Setup:** a third radio capturing every frame on air with radiotap timestamps, next to the two existing transmitters. Use an adapter with a chipset known to support 5 GHz monitor mode on Linux. Repeat the paper's loads: 50%, 70%, 85% occupancy and saturation.

**What to check, from most to least likely cause:**

1. **Access category.** Broadcast frames may go out with different EDCA parameters (a different CWmin or AIFS) than the DCF that ns-3 and the event model assume. This alone could explain the mismatch.
2. **Actual PHY rate** of broadcast frames, which some drivers set to a basic rate rather than the configured one.
3. **Queue behavior**: back-to-back bursts and post-backoff when the driver queue holds several frames.
4. Carrier-sense threshold and transmit power.

**Metrics:** measured inter-frame gaps and backoff slot distribution, overlapping-start events (collisions), rate per frame, and burst lengths.

**Expected outcome (register before running):** at least one of causes 1–3 differs from the model. With measured parameters fed back into the event model, the below-saturation error falls within ±15% at every load.

**Effort:** 1 week. **Paper deliverable:** Supplementary Note 6 states the cause instead of "we have not found the cause".

### B2. Scaled testbed: capacity on hardware

**Fixes:** "no capacity was measured on hardware", the paper's biggest limitation.

**Setup:**

- 5–10 radio nodes of one chipset and driver, all within range on a quiet 5 GHz channel outside DFS (channels 36–48). Use a shielded room if available.
- A wired control network for start triggers and log collection, synchronized with PTP or NTP, so the control plane never touches the radio channel.
- **Emulate large N with A12's method:** each radio sends at k times the per-node frame rate, so 8 radios offer the load of up to about 200 nodes. Apply the (N − 1)/N correction from A12.
- The B1 monitor radio logs ground truth.
- Run baseline and design frames, increasing the total load until delivery crosses 0.95.

**Metrics:** delivered fraction against equivalent N, the hardware crossing for baseline and design, and their ratio. Repeat 10 times.

**Expected outcome (register before running):** hardware crossings fall within 15% of ns-3 (35 and 124 nodes), and the design-to-baseline ratio is between 3× and 4×. If B1 found different EDCA parameters, register the prediction using the measured values.

**Bonus:** repeat A7's flooding test with a real injecting radio.

**Effort:** 3–4 weeks. **Paper deliverable:** the abstract changes from "capacities are simulated" to "capacities were confirmed on an 8-radio testbed at emulated scale".

### B3. Flight-controller-class MCU and calibrated energy

**Fixes:** energy was measured on the sender only, with an uncalibrated INA219, on a Raspberry Pi rather than flight hardware.

**Setup:**

- Port the A8 compiled codec to a Cortex-M7 board such as an STM32H7, and optionally an ESP32-S3. Use Monocypher or a comparable small library for Ed25519, micro-ecc for P-256 and QCBOR for CBOR.
- Run the same byte-identity gate as A8.
- Measure energy with a calibrated power profiler, for both sender and receiver roles.

**Metrics:** sign and verify time, energy per record, peak RAM, and nodes per core from equation (4).

**Expected outcome:** run a microbenchmark first and register the prediction from it. Sender duty at 12.5 frames/s should stay low. **On an MCU the receiver is likely to bind before the channel**, which makes batching's 4× cut in verifications a CPU result as well as an airtime result.

**Effort:** 3 weeks.

### B4. Air-to-air loss traces

**Fixes:** every loss model in the verifiability results is synthetic.

**Setup:** radios on 2–3 drones (masts or rooftops as a first step). Fly separation sweeps and maneuvers. Interleave baseline-size (146 B) and design-size (173 B) frames on the same link, so length-dependent loss is measured directly.

**Metrics:** per-frame success against distance, altitude and attitude; burst-length distribution; and V from replaying traces in the A3 harness.

**Expected outcome:** loss rises sharply near the edge of the link budget. The length effect between 146 and 173 B is small (under 10% relative). Bursts during turns, from body shadowing, are longer than the 4-frame Gilbert case, which favors r = 1.

**Effort:** 2–3 weeks, plus flight permissions and safety planning.

### B5. Multi-drone flight test (next paper)

**Fixes:** end-to-end realism.

**Setup:** 3–5 drones with companion computers running the compiled AUTHBC, reading PX4 telemetry over MAVLink at 50 Hz. Use GNSS timestamps for end-to-end freshness, run the A4 controller, and audit the ledgers afterward with A16.

**Expected outcome:** V ≥ 0.95 within the link budget, and the 99th-percentile age stays under 100 ms except during consecutive frame losses.

**Effort:** 6 weeks or more.

## Schedule, minimum package and prediction registration

The minimum revision package (A1–A5) takes about 7 weeks. The full software plan plus B1 and B2 fits in 12 weeks, assuming the B2 radios arrive by week 6.

&#91;embedded content: revision schedule · 15 workstreams over 12 weeks\]

A1 runs first because A3, A4 and A14 reuse its scenarios and traces. B2 starts only after A12 has validated the N·f method and B1 has measured the real access parameters.

### Minimum revision package

If time is short, submit with these five. Together they remove the three strongest objections and add one clear new contribution.

| ID | Objection it removes | Paper sections changed |
| --- | --- | --- |
| A1 | "Single collision domain, no hidden terminals or mobility" | Results 3.5, Discussion limitations |
| A2 | "b ≤ 4 holds only at your chosen operating point" | Methods 2.4, new main design figure |
| A3 | "The design meets its target with no margin" | Results 3.3, Discussion |
| A4 | "The contribution is accounting, not a mechanism" | Contributions, new Results subsection |
| A5 | "Delayed replay is accepted" | Threat model 2.2 |

Next in line: A6 (formal proof) and B1 (the cheapest hardware item, which may explain Supplementary Note 6).

### Registering predictions

The paper's credibility rests partly on predictions written before the runs. Keep that true for every new result.

1. Before an experiment, commit `predictions/<ID>.md` with the numbers from its Expected outcome, the pass criterion and the analysis script.
2. Tag the commit and cite the tag in the Supplementary Information.
3. Never edit a prediction file after the first run. Report misses as misses, as the paper already does for the hardware test.
4. Add a Supplementary Table listing each prediction, its commit tag, the result and pass or fail.

### Text changes once results are in

- **Abstract:** replace "the capacities are simulated" with the A1 ratio across topologies and, if done, the B2 hardware confirmation.
- **Contributions:** add the adaptive controller (A4) and the formal model (A6).
- **Limitations:** remove each item that A1, A3, A5, A6 and A8 resolve; keep the rest, stated as plainly as now.
- **Title and framing:** if A16 is not done, consider "hash-chained log" instead of "blockchain-style ledger".
