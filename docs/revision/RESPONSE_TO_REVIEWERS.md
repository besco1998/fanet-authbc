# Response to the reviewers — AUTHBC revision

*Draft for Mohamed, 2026-10-24.*

* **The comments.** Each comment below is an objection the revision plan (`docs/AUTHBC Revision
  Plan.md`) was written to answer. When the reviews arrive, map each one to the reviewer's own
  wording.
* **Locations.** Sections are named by their labels (`sec:capacity`, …) until the paper text is
  final (open item H1).
* **Sources.** Every number comes from the result file named beside it. Every experiment was
  registered before it ran (`predictions/<ID>.md`, git tag `prereg-<ID>`).

---

We thank the reviewers for their careful reading. The revision adds fifteen experiments. Each
was registered, with its expected outcome and pass criterion, in a tagged commit before it ran.
Predictions that failed are reported as failed, and a new appendix table (`tab:prereg`) lists
every registered prediction with its outcome and whether it held. The main changes are:

1. the capacity result is re-established for a spread, mobile swarm with fading, capture and
   hidden terminals;
2. the operating point is replaced by a design map over rate and deadline, validated in
   simulation;
3. the security argument is formalized in Tamarin, and a bounded-delay freshness rule closes the
   delayed-replay gap;
4. the receiver and sender were re-implemented in compiled code and re-measured on the
   Raspberry Pi 4, which resolves the CPU and energy anomalies of the prototype;
5. the stream-signing comparators were implemented and simulated rather than sized on paper.

---

## Comment 1 — "Single collision domain: no hidden terminals, spatial reuse or mobility."

**Response.** The swarm was spread over discs of radius up to 1 km and over a grouped layout. The
channel has log-distance path loss, Nakagami-3 fading and 4 dB capture (4 230 ns-3 runs).

* **The design keeps its advantage** in every layout: the ratio of the design's capacity to the
  baseline's lies between 3.46 and 3.58.
* **At R = 1 km**, 11 % of the nodes able to spoil a frame cannot hear its sender. Capacity
  counted in neighbours falls (8.7 within 215 m), because a receiver contends with every node in
  its carrier-sensing range. This is the mechanism of Hu and Dai, not a new one. Counted in
  nodes over the area, capacity rises to 218.
* **Mobility** (900 further runs): every node follows its own Gauss–Markov path at 0, 5 or
  15 m/s, with parameters taken from the FANET mobility literature. Delivery changes by at most
  0.0005, and the ratio stays at 3.57–3.63.

**Stated plainly:**

* Our registered bracket for the neighbour count ([10, 40]) missed (8.7).
* A first mobility test that moved the whole group rigidly could not distinguish speeds, so it
  was replaced by independent motion.
* The channel has no Doppler and no time-correlated fading.

*Results:* `spatial_capacity.csv`, `spatial_motion.csv` (F88, F103).

**Changes.** `sec:capacity`: the paragraph "A Spread, Moving Swarm" and Fig. `fig:spread` (nodes
served and the design's ratio against disc radius, with the share of hidden spoilers under each
radius and the moving swarm beside it). `sec:limits`: hidden terminals, spatial reuse and
relative motion are now simulated, with the channel's caveat.

## Comment 2 — "b ≤ 4 holds only at the chosen operating point."

**Response.** The single operating point is replaced by a design map over the record rate Λ and
the deadline D_max, giving the best batch b\* and the capacity ratio. Fifteen of its cells,
chosen as distinct roles, were simulated in ns-3: every crossing lies within 1.05 % of the
model, and the ratio reaches 6.63 at 100 records/s and 100 ms (3 150 runs).

Under loss the mean peak age still meets the deadline (87.7 ms at p = 0.05). One lost frame,
however, takes an update to 169.75 ms. The deadline therefore holds for a share 1 − p of
updates, the same share that V counts.

*Results:* `design_map.csv`, `design_map_validation.csv`, `aoi_under_loss.csv` (F90, F100).

**Changes.** Fig. `fig:map`, the design map (model-computed; the cells simulated in ns-3 are
outlined), beside the existing figure of capacity against deadline. The Freshness subsection
gains the age-under-loss sentence.

## Comment 3 — "The design meets V ≥ 0.95 with no margin."

**Response.**

1. **The loss model.** ns-3 traces of 3 000 neighbour links at the capacity crossing show that
   collision loss is independent from frame to frame: mean burst 1.06 frames, against 1.055
   for independent loss. Eq. (3) is therefore the model for V; it is the pessimistic one when
   frames depend on each other.
2. **A deployment rule:** set the loss budget ε at least 0.02 above the expected frame loss for
   the mean V. At 0.03 the 95 % interval also clears the target under bursts of four frames or
   more.
3. **Misses:** the margin rule fails by its interval in 5 of 192 cells, all under bursty loss (one is the
   design at ε = 0.1 and p = 0.08 with bursts of eight frames, where under bit errors its interval
   also falls short; every mean meets its target), and one
   registered statement missed by 0.0002.

While answering this comment we tested the paper's intervals themselves. With a known truth and
30 seeds, the percentile bootstrap covered 92–94 % of the time instead of 95 %. Every interval of
a mean is now a Student-t interval, and every interval of a capacity crossing an expanded
percentile bootstrap interval (Hesterberg, 2015); both cover 95 %. The printed intervals widen
by 0.001–0.003; no estimate moves.

*Results:* `verifiability_margin.csv`, `verifiability_margin_trace.csv`, `interval_coverage.csv`
(F86, F98, F101).

**Changes.** `sec:loss` and Fig. `fig:margin` (the design's V against loss under five loss
processes, with the region the rule admits), `sec:limits` (the "no channel trace" limitation is
removed), Discussion (the rule), Methods (the intervals).

## Comment 4 — "The contribution is accounting, not a mechanism."

**Response.** We implemented an adaptive batching controller that chooses b from the channel's
measured occupancy, and tested it in ns-3 on a growing swarm, a merging swarm and a mobile swarm
(180 runs).

* **The registered controller fell short of its own predictions.** It held V ≥ 0.95 in 75 % of
  one-second windows and failed at 76 nodes, against 127 for fixed b = 4.
* **With twice the margin** (0.02, from its measured scatter), the controller holds the target
  in 93 % of windows, fails at 116 nodes, and saves 21 ms of peak age against fixed b = 4.
  These ages include the instant at which the simulated source sends each frame, drawn over the
  next period, so they run half a frame period above ages at fill; the paper says so (F113).

We present it as a trade-off between freshness and reliability margin, not as a headline
contribution. The nearest prior work is FMAC, which adapts the contention window; its
predictive term is the precedent of ours. The mobile scenario cannot discriminate between
controllers (every threshold is exceeded from the first second), and is not used as evidence.

*Results:* `adaptive_batching.csv`, `adaptive_batching_b.csv` (F102).

**Changes.** `sec:capacity`: the paragraph "Choosing the Batch at Run Time" and Fig.
`fig:adaptive` (the growing swarm, second by second: the batch each policy chooses, V per second
and the peak age).

## Comment 5 — "Delayed replay is accepted."

**Response.** A bounded-delay freshness rule is added while GNSS time is held. A receiver refuses
any frame stamped more than Δ before its own clock reads, with Δ = 150–250 ms.

* **Honest traffic:** in 72 000 honest frames per setting, none was refused at clock errors up to
  σ = 10 ms.
* **Delayed frames:** every frame held back 250 ms or more was refused.
* **In a GNSS outage** two clocks part by 144 ms an hour. A fixed 250 ms window therefore holds
  for 75 minutes; our registered estimate of two hours failed. A window widened by the worst
  drift keeps working, its bound growing by 144 ms an hour.

*Results:* `replay_window.csv`.

**Changes.** `sec:model`: the delaying attacker moves from "not protected" to a protected
property (v), with its condition, and Table `tab:security` gives its evidence. `sec:limits` is
updated.

## Comment 6 — "The security argument is informal."

**Response.** The frame protocol is modelled in Tamarin (`formal/`). The following are proven:

* origin and integrity, no replay, injective agreement, equivocation evidence implying a
  revealed key, and gap detection, in a model with counters and signatures;
* continuity through the chain, in the full frame model;
* the effect of the time window: a delayed frame is accepted without it and refused with it.

The properties are proven in three models, not one: a single model with the chain and the clock
did not terminate within 1 GB per lemma. In the registered model 3 of 9 lemmas settled. Two
encodings were changed after registration (counters keyed by a session identifier, a receiver
start rule), and both changes are disclosed. Canonical encoding is assumed injective.

**Changes.** `sec:model`: Table `tab:security` lists each property with the model that proves
it. `sec:limits` ("Security Scope"): "informal" is replaced by the proven properties, with the
three-model caveat in the same sentence.

## Comment 7 — "Flooding is not resisted."

**Response.** Measured on the Raspberry Pi 4. Per frame:

| frame | cost |
|---|---|
| forged (a real sender, a newer sequence number, a well-formed signature by another key) | 1.08 ms in the Python receiver |
| outsider's frame, refused by an 8-byte group tag | 22.5 µs |

In a UDP flood against one receiver core carrying 41 senders:

* behind the tag, 3 000 outsider frames/s leave honest delivery at 0.984. One 802.11a channel
  carries at most 2 857 such frames per second.
* With no tag, 247 forged frames/s push honest delivery below 0.95.
* A swarm member holding the tag key is stopped by neither the tag, nor cheap header checks, nor
  a per-sender rate cap. Spreading forgeries over every sender, it breaks the receiver at about
  130 frames/s. This remains a stated limitation.

The tag costs 3.1 % of capacity. Our registered figures for the forged-frame cost (700 frames/s
per core; measured 928) and for the tag (100 000 frames/s per core; measured 44 400) missed;
both conclusions held.

*Results:* `flood_cost.authbc-pi4b.csv`, `flood_udp.authbc-pi4b.csv` (F109).

**Changes.** `sec:model` (the tag in the threat model, and Table `tab:security`),
`sec:capacity` (the paragraph "Flooding" and Fig. `fig:flood`: honest delivery against the
forged-frame rate for each defence and attacker), `sec:limits` (insiders). The figure also shows
that a per-sender cap holds one forging sender at V ≥ 0.96 up to the rate one channel carries.

## Comment 8 — "The receiver's CPU and the sender's energy are artifacts of an interpreted prototype."

**Response.** We re-implemented the receiver and sender in Rust. The compiled codec emits the
same bytes as the prototype, checked on 10 000 frames. Measured on the Raspberry Pi 4:

**Receiver** (per four-record frame):

| receiver | time | nodes per core |
|---|---|---|
| compiled | 0.277 ms (5.1× faster) | 289; 643 with batched verification |
| Python | 1.409 ms | 57 |

124 neighbours need 0.43 of one core, so the radio channel, not the CPU, is again the binding
limit.

**Sender** (INA219 rig, the rig check passed):

| sender | µJ per record (4 records a frame) |
|---|---|
| compiled lean format | **17.1** |
| first format | 58.4 |
| Python lean format | 155.4 |

The reversed order in the prototype was the interpreter's. Our registered energy ranges missed
low: compiled code draws 0.65 W of added power, against the 0.75 W measured for Python. The
sensor's gain was not calibrated against a reference load; this scales every value alike and
leaves the comparisons unchanged.

*Results:* `compiled_receiver.authbc-pi4b.csv`, `energy_runs_2026-10-22.csv` (F108, F112).

**Changes.** Receiver CPU paragraph ("three cores" becomes the prototype's) and Table
`tab:receiver` (interpreted, compiled, batched and lazy receivers, timed in one session), Table
`tab:energy` (two compiled rows), and the energy paragraph.

## Comment 9 — "The 9-field telemetry is synthetic."

**Response.** 50 PX4 software-in-the-loop flights were made at 50 Hz: a quadrotor, a fixed
wing and a VTOL. Ten fixed-wing and ten VTOL missions were flown a second time at their planned
15–25 m/s. Records of 9, 15 and 25 fields were coded at their exact lengths.

* At 50 Hz each field costs one byte per delta on every airframe.
* At the planned speeds, fixed-wing records cost the quadrotor's plus 0.2 B.
* With 25 fields the design still saves 63.3 % of the bytes and serves 3.04 times the nodes
  (9 fields: 70 % and 3.5×). The advantage stays above 2× until a record's delta reaches
  159–282 B.

**Misses:** our registered keyframe (about 60 B) and fixed-wing delta (10–13 B) missed; they are
45 B and 9.2 B.

**Limitations of the simulator, disclosed with measured effects:**

* SIH's airplane needed its artificial drag term removed to fly the planned speeds;
* its altitude controller started from sea level in the first flights, which put a quarter of
  their records at ground level (no effect on any size);
* the simulator holds GNSS-quality fields constant.

*Results:* `record_size.csv`, `record_size_fast.csv`, `a9_fast_speeds.csv` (F105, F107, F111).

**Changes.** `sec:px4`: one paragraph on richer records and airframes, and Table
`tab:airframes` (keyframe and per-airframe delta at 9, 15 and 25 fields, the saving and the
ratio). `sec:limits`: the simulator's limits.

## Comment 10 — "The stream-signing comparators are only sized on paper."

**Response.** TESLA, EMSS, Wong–Lam, Gennaro–Rohatgi and MAVLink 2 signing were implemented and
run on simulated links (1 860 runs). A record counts only if it verifies within D_max. Table 5's
earlier values are reproduced within their intervals.

Against a 100 ms deadline, only three schemes reach the 0.95 target:

| scheme | capacity (nodes) |
|---|---|
| MAVLink 2 | 42.1 |
| Wong–Lam | 29.1 |
| TESLA with a disclosure delay of 2 and intervals ≤ 20 ms | 39.6–39.8 |

Gennaro–Rohatgi, every EMSS variant and TESLA with four records a frame never do.

*Results:* `stream_deadline.csv` (F99).

**Changes.** Table `tab:stream` gains a simulated, deadline-aware column. The footnote "upper
bound" and the limitation "none is implemented" are removed.

## Comment 11 — "Only one physical layer."

**Response.** The capacity crossings were simulated on six 802.11 physical layers: 802.11a at 6,
12 and 24 Mb/s, and 802.11p (10 MHz) at 3, 6 and 12 Mb/s (2 520 runs). The design's capacity is
3.39–3.80 times the baseline's, rising slightly with the rate; the plan's estimate was 1.7–4.3.
Our access-rule model is within 1.5 % at every rate but the fastest of each channel width,
where it is 2.9–4.6 % optimistic. **5G NR sidelink is stated as future work.**

*Results:* `phy_links.csv` (F104).

**Changes.** `sec:capacity`: the paragraph "Other PHY Rates" and Table `tab:phy` (each PHY and
rate: frame airtime, both capacities, the ratio and the model's error). Conclusion: the NR
sidelink as future work.

## Comment 12 — "The receiver is CPU-bound; is there a cheaper verification path?"

**Response.** Lazy verification, with two tiers:

* records are usable at once, after the group tag and decoding (10.2 µs per frame);
* signatures are verified in batches of 64 before records enter the ledger (117.2 µs per frame).

One Raspberry Pi 4 core then serves 628 neighbours. A record becomes signed evidence within
191 ms by the paper's freshness convention (Eq. (2), which counts the whole filling period), or
171 ms after the oldest record of its frame was sampled. The cost: in that window a swarm member holding the group key could
inject records that are acted on and only later purged.

*Results:* `compiled_receiver.authbc-pi4b.csv` (F108).

**Changes.** Receiver CPU paragraph (the two tiers and their trade-off) and the lazy row of Table
`tab:receiver`.

## Comment 13 — "There is no post-quantum path."

**Response.** Falcon-512's padded signature (666 B) fits in the frame.

| design signed with Falcon-512 | |
|---|---|
| capacity | 43.5 nodes (12.4 when every record is signed; 3.5×, as with Ed25519) |
| sign / verify on the Raspberry Pi 4 | 0.64 ms / 0.088 ms (verification three times faster than Ed25519's) |

The gain comes from sending a quarter as many frames, whatever the signature's size. Our
registered expectation that batching matters *more* with a post-quantum signature failed: it
matters the same. ML-DSA's 2 420 B signature still does not fit.

*Results:* `pq_capacity.csv`, `pq_speed_sig.authbc-pi4b.csv` (F110).

**Changes.** `sec:capacity`: the paragraph "A Post-Quantum Signature" and the Falcon-512 row of
Table `tab:phy`. `sec:limits` ("Post-Quantum Signatures"), Conclusion.

## Comment 14 — "The blockchain framing is not supported."

**Response.** A ledger is audited from the uploads alone. One pass over a mission's frames finds
every equivocation and every frame that does not verify, using only the senders' public keys,
and the auditor signs a Merkle root of what it accepted. For three UAVs over a flight hour
(391 495 frames), a planted equivocation and a planted forgery were both found, with no false
finding, in 6.4 minutes of one core. Keeping the frames costs 42.9 B per record, about 1 GB an
hour for 124 neighbours.

*Results:* `ledger_audit.csv`.

**Changes.** `sec:model` (Ledger) and the audit row of Table `tab:security`. ⚠️ *For Mohamed: whether the title keeps "blockchain-style
ledger" or becomes "hash-chained log" is your decision.*

## Comment 15 — "The generality claim is not examined."

**Response.** The same accounting was applied to ADS-B, Remote ID and V2X:

* ADS-B 1090ES and Bluetooth-4 Remote ID cannot carry a signature at all.
* Bluetooth-5 and Wi-Fi Remote ID fit up to seven records. But at one message a second, a
  record waits a whole message period under the paper's freshness convention, so no frame meets
  any deadline up to 1 s.
* V2X CAM at 10 Hz with a 100 ms deadline admits no frame; it admits one record at 200 ms and
  two at 300 ms. CAM's standard bounds how often a message is generated, not when it must be
  delivered, so the deadline is our assumption.

This is consistent with these standards signing each message; we do not claim it explains why
they do.

*Results:* `other_links.csv`.

**Changes.** Discussion: the paragraph on other broadcast systems and Table `tab:links` (records
per frame each system admits at 100 ms, 200 ms, 300 ms and 1 s, with this design's row).
