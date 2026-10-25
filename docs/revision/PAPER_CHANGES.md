# What the revision changes in the paper — proposals, item by item

*Drafted 2026-10-21 for Mohamed. **Applied 2026-10-24** to the 2026-10-12 `main.tex` (Mohamed:
"edit the latest uncommitted main.tex"), except A12, which prepared a hardware test, and every
hardware item (B1–B5) and A14: by Mohamed's decision of 2026-10-24 these are neither stated nor
listed as future work until the purchases are made. Places are given by the section labels, which both versions share. Every number
below must reach the paper through `analysis/paper_numbers.py` (one macro each), not typed in;
the source CSV is named with each. Scoring and caveats are in `predictions/<ID>.md`; the one-line
findings are F86–F112 in `docs/audits/model_provenance.md`.*

## A figure or table for every reviewer point (Mohamed, 2026-10-24)

"Make sure the paper has the corresponding figures, tables or proper visualization for the
results and tests we made." Figures come from `analysis/figures_revision.py`, and table cells are
macros of `analysis/paper_numbers.py`. `tests/test_figures_revision.py` pins what each figure's
sentence claims.

| label | kind | point | what it shows |
|---|---|---|---|
| `fig:system` | figure*, Mohamed's block diagram | — | now full width (it was unreadable in one column); caption covers the whole system |
| `tab:security` | table* | 5, 6, 7, 14 | each property or threat, its mechanism, the Tamarin model or measurement, the result |
| `fig:margin` | figure | 3 | V of the design against loss under five processes, the rule's region |
| `fig:map` | figure | 2 | b\* and ratio over Λ × D_max; ns-3 cells outlined |
| `fig:spread` | figure | 1 | nodes served and ratio against disc radius; hidden share; moving swarm |
| `fig:adaptive` | figure | 4 | the growing swarm: batch, V per second, peak age (F113: ages include the send instant) |
| `tab:receiver` | table | 8, 12 | interpreted, compiled, batched and lazy receivers |
| `fig:flood` | figure | 7 | honest V against forged rate, six defence/attacker pairs; the channel's limit |
| `tab:phy` | table | 11, 13 | six PHYs and Falcon-512: frame airtime, both capacities, ratio, model error |
| `tab:airframes` | table | 9 | 9/15/25 fields: keyframe, per-airframe delta, saving, ratio |
| `tab:links` | table | 15 | records per frame per system at 100/200/300 ms and 1 s, with this design's row |
| ~~`tab:prereg`~~ | removed 2026-10-25 (Mohamed) | — | the registrations stay in `predictions/` and in the thesis's Appendix B |

The paper is 17 pages (18 with the registration appendix, removed 2026-10-25). Comment 10's table already had its column (`tab:stream`).

## Ready (experiment scored)

### A1 — spread swarm, fading, capture (`sec:capacity`, `sec:limits`, `sec:method`, Conclusion)

**Now says:** "one collision domain of static nodes … hidden terminals and mobility are identified
as future work"; Limitations: "hidden terminals, spatial reuse and mobility are absent".

**Proposed:** a paragraph in `sec:capacity` and the plan's figure (capacity against neighbour
density, S1 at four radii, S2, S3): *"Spread over a disc of up to 1 km with log-distance loss,
Nakagami-3 fading and 4 dB capture, the design keeps its advantage: the ratio of crossings lies
between 3.46 and 3.58 in every layout, although at R = 1 km 11 % of the nodes able to spoil a
frame cannot hear its sender. Capacity counted in neighbours falls (8.7 within 215 m at
R = 1 km) because a receiver contends with every node in its carrier-sensing range [Hu & Dai];
counted in nodes in the area it rises (218)."* Limitations: hidden terminals and spatial reuse
are then simulated, and so is relative motion: *"with every node moving on its own Gauss–Markov path at up to 15 m/s, delivery changes by at most 0.0005 and the ratio stays at 3.6 (F103)"* — with the caveat that the channel has no Doppler or time-correlated fading. Numbers: `spatial_motion.csv`. Cite Bujari et al. 2017 (held, CC BY) for the model's parameters.

Numbers: `results/raw/spatial_capacity.csv`. Cite Hu & Dai 2020 (held, CC BY; needs a bib
entry). ⚠️ Do not write "because hidden terminals add collisions" (the plan's reason): the
hidden share is a minority of the spoilers.

### A2, age part (Results, the Freshness subsection)

**Proposed:** *"Under loss the mean peak age still meets D_max (87.7 ms at p = 0.05), but one
lost frame takes an update to 169.75 ms: the deadline holds for a share 1 − p of updates, as V
does."* Numbers: `results/raw/aoi_under_loss.csv`. **The design map** (the plan's main design figure, a heatmap of b\* and the capacity ratio over Λ × D_max) is now validated: fifteen roles in ns-3, every crossing within 1.05 % of the model, ratio 6.63 at (100 /s, 100 ms) (`design_map.csv`, `design_map_validation.csv`). It can replace the single operating point as the design figure, captioned as model-computed and simulation-checked at the marked cells.

### A3 — margin against the target, and a channel trace (`sec:loss`, `sec:limits`, Discussion)

**Now says (Limitations):** loss "all generated at the frame level, not a channel trace".

**Proposed:** *"ns-3 traces of 3 000 neighbour links at the crossing show collision loss that is
independent from frame to frame (mean burst 1.06 frames against 1.055 for independent loss), so
Eq. (3) is the model for V, the pessimistic one when frames depend on each other."* Deployment
rule for the Discussion: *"set ε at least 0.02 above the expected frame loss for the mean V; at
0.03 the 95 % interval also clears the target under bursts of four frames or more."* Numbers:
`verifiability_margin.csv`, `verifiability_margin_trace.csv`. ⚠️ H2 first: every V interval in
the paper is a percentile bootstrap that covers 92–94 % (F86).

### A4 / A4b — adaptive batching (decisions H9 done; text still Mohamed's)

A4's registered controller (margin 0.01) holds V ≥ 0.95 in 75 % of a growing swarm's one-second
windows and fails at 76 nodes; A4b's second controllers, one change each: margin 0.02 → 93 %,
fails at 116, saves 20–21 ms of peak age against fixed b = 4 (ramp, merge); a growth term alone →
85 %, 108. Fixed b = 4: 99 %, 127. **Proposed:** a Results subsection or Discussion paragraph,
not a headline contribution: *"Choosing b from the channel's measured occupancy buys 20 ms of
freshness at a cost in reliability margin; with a 0.02 margin the controller holds V ≥ 0.95 in
93 % of one-second windows of a swarm growing by 1.5 nodes a second and fails at 116 nodes,
against 127 for b = 4 fixed."* The plan's figure (merge time series) from `ns3_adaptive_b_ts/`.
Numbers: `adaptive_batching.csv`, `adaptive_batching_b.csv`. ⚠️ Cite FMAC (held locally) as the
nearest prior work (it adapts the contention window; its prediction is the growth term's
precedent). ⚠️ Do not use the mobile scenario as evidence for any controller (identical runs).

### A5 — bounded-delay freshness (`sec:model` "What Is Not Protected", `sec:limits` "Security Scope")

**Now says:** "a frame that an attacker withholds and delivers later is accepted … refusing it
requires a clock shared with the sender, which we do not assume."

**Proposed:** a protected property (v): *"Bounded-delay freshness, while GNSS time is held: a
receiver refuses a frame stamped more than Δ before its own clock reads (Δ = 150–250 ms). In
72 000 honest frames per setting none was refused at clock error σ ≤ 10 ms, and every frame held
back 250 ms or more was refused. In a GNSS outage two clocks part by 144 ms an hour, so a fixed
250 ms window holds for 75 minutes; one widened by the worst drift keeps working, its bound
growing by 144 ms an hour."* The delaying attacker leaves the "not protected" list, with that
condition. Numbers: `replay_window.csv`.

### A6 — the protocol in Tamarin (`sec:limits` "Security Scope")

**Now says:** "the security argument is informal."

**Proposed:** *"The frame protocol is modelled in Tamarin (files in the repository). Origin and
integrity, no replay, injective agreement, equivocation evidence implying a revealed key, and
gap detection are proven in a model with counters and signatures; continuity through the chain
in the full frame model; and a delayed frame is accepted without the time window and refused
with it. The properties are proven in three models, not one: a single model with the chain and
the clock did not terminate within 1 GB a lemma. Canonical encoding is assumed injective."* The
three-model caveat must stay in the sentence (`predictions/A6.md`).

### A12 — few radios for many — **not used in the paper** (it prepared a hardware test; Mohamed, 2026-10-24)

**Proposed:** *"At a fixed total frame rate, delivery depends on how the rate is split among
nodes only through each node's not colliding with itself: after an (N − 1)/N correction, splits
from 124 nodes at 12.5 frames/s to 5 at 350 agree within 0.005 of V in ns-3, and the access-rule
model agrees with every split within 0.0011."* With the caveat that real drivers' queues are
B1/B2's question. Numbers: `nf_equivalence.csv`. ⚠️ Cite Kumar, Choi & Kim 2019 (held, CC BY) as the earlier use of the emulation, with hidden transmitters only; claim only the contended case.

### A15 — post-quantum (`sec:limits` "Post-Quantum Signatures", Conclusion)

**Now says:** "An ML-DSA signature is 2420 B … A post-quantum variant would be a different design."

**Proposed:** keep the ML-DSA sentence and add: *"Falcon-512's padded signature (666 B) fits: the
design signed with it serves 43.5 nodes against 12.4 for signing each record, a ratio of 3.5, as
with Ed25519 — the gain comes from sending a quarter as many frames, whatever the signature's
size."* Numbers: `pq_capacity.csv`. Sign/verify timing waits for pi-B (H4); until then no
energy or CPU claim for Falcon.

### A16 — the audit (`sec:model` Ledger subsection)

**Proposed:** *"A ledger is audited from the uploads alone: one pass over the frames of a mission
finds every equivocation and every frame that does not verify, with the senders' public keys,
and the auditor signs a Merkle root of what it accepted. For three UAVs over a flight hour
(391 495 frames) a planted equivocation and a planted forgery were found with no false finding,
in 6.4 minutes of one core; keeping frames costs 42.9 B a record, about 1 GB an hour for 124
neighbours."* This also bears on the plan's question whether "blockchain-style ledger" becomes
"hash-chained log" (`EXECUTION_PLAN.md`, decisions). Numbers: `ledger_audit.csv`.

### A17 — other broadcast standards (Discussion table)

**Proposed:** the plan's short table — ADS-B 1090ES and Bluetooth-4 Remote ID cannot carry a
signature; Bluetooth-5/Wi-Fi Remote ID fits up to seven records, but at one message a second
the freshness rule admits no frame for deadlines up to 1 s and one record at 2 s; CAM at 10 Hz with a 100 ms deadline admits no frame, one record at 200 ms, two at 300 ms —
with the sentence that this is consistent with these standards signing each message, not an
explanation of it. Numbers: `other_links.csv`.

### A10 — the stream schemes against the deadline (Table `tab:stream`, its footnote)

**Now says:** the stream-signing columns "are upper bounds" (footnote ‡: "a packet does not
verify alone: N_max is an upper bound"); Limitations: "none is implemented".

**Proposed:** Table 5 gains a simulated, deadline-aware column — MAVLink 2 42.1, Wong–Lam 29.1,
TESLA 39.6–39.8 with d = 2 and I ≤ 20 ms; Gennaro–Rohatgi, EMSS (any k) and TESLA with four
records a frame: no crossing — and the footnote becomes *"implemented and run on simulated
links; a record counts if it verifies within D_max"*. Limitations loses "none is implemented".
Numbers: `stream_deadline.csv`. ⚠️ TESLA's d = 1 cells depend on the 1 ms arrival assumed
(F99); print the d = 2 values.

### H2 — the intervals (Methods; every printed interval)

**Proposed Methods sentence:** *"A 95 % interval of a mean over seeds is a Student-t interval; an
interval of a crossing is an expanded percentile bootstrap interval (Hesterberg, 2015). With a
known truth and 30 seeds, the plain percentile bootstrap covered 92–94 % of the time, these 95 %
(F86, F101)."* Already in `numbers.tex`: `\lossCi…`, `\lossBerCi` (t), `\sprCi…`, `\batCi…`
(expanded). Grid intervals (`\ci…`, `\strCi…`) are unchanged (≈ 100 % coverage). Needs the
Hesterberg bib entry (held locally; arXiv:1411.5279).

### A11 — other 802.11 PHYs and rates (the Discussion paragraph on other links; Supplementary Note 7)

**Now says:** the gain "follows … 1.7× to 4.3×" across links (a closed form's saturation
ratios). **Proposed:** a short table, simulated: *"On 802.11a at 6, 12 and 24 Mb/s and 802.11p at
3, 6 and 12 Mb/s, the design's capacity is 3.4–3.8 times the baseline's, rising slightly with the
rate."* Numbers: `phy_links.csv`. ⚠️ State that the no-fit model is 4–4.6 % optimistic at the
fastest rates (F104) if model values are printed beside ns-3's. NR sidelink stays unsimulated (H6).

### A9 — richer records, three airframes (`sec:px4`, its "Operating Rate" paragraph; `sec:limits`)

**Now says:** one simulated quadrotor at 50 Hz, nine fields: "every delta record is
\deltaLean\,B, the floor of the format". **Proposed** (after that paragraph): *"Thirty further
flights — ten each of a quadrotor, a fixed wing and a VTOL, PX4 SIH at 50 Hz — show the same floor
for every airframe: one byte per field. With 15 fields (adding attitude and body rates) the design
saves 67 % and serves 3.3 times the nodes; with 25 (adding GNSS quality, airspeed, wind, mission
item, status and thrust) 63 % and 3.05 times. The gain is set by the frame count, not by the
record: it stays above 2× until a record's delta reaches about 160 B."* Numbers:
`record_size.csv` (one macro each via `analysis/paper_numbers.py`). ⚠️ With it, in `sec:limits`:
the fixed-wing and VTOL flights were re-flown at their drawn 15–25 m/s with SIH's damping
term removed (A9-fast, F111): the delta is the quadrotor's plus 0.2 B and the ratio unchanged; and
SIH's GNSS fields are constant. Do not write "fixed wings cost more bytes at 50 Hz" (F111: +0.2 B).

### A8, A13 — the compiled receiver (`sec:validation` or `sec:discussion`, where the receiver's three cores are stated; `sec:limits`)

**Now says:** the Python receiver takes 1.43 ms per frame, so 124 neighbours need about three
cores (F84). **Proposed:** *"Compiled (Rust, ed25519-dalek), the same receiver takes 0.28 ms per
frame on the Raspberry Pi 4, five times faster; one core serves 289 neighbours, 643 when
signatures are checked 64 at a time. With a fast tier (group tag and decode, 10 µs) and an
evidence tier (batched signatures), one core serves 628 neighbours and a record is signed
evidence within 171 ms of being sampled."* Numbers: `results/hw/compiled_receiver.authbc-pi4b.csv`.
⚠️ The three-core statement must then be said to be the prototype's, not the design's.

### A7 — flooding (`sec:model` threat model; `sec:limits`)

**Proposed:** *"A forged frame — a real sender, a newer sequence number, a well-formed signature by
another key — costs the Python receiver 1.08 ms on a Pi 4. An 8-byte group tag refuses an
outsider's frame in 22.5 µs: with 3 000 forged frames/s, more than one channel can carry, honest
delivery stays at 0.98. The tag costs 3 % of capacity. A member holding the group key is not
stopped by the tag, cheap checks or a per-sender rate cap: forgeries spread over every sender
reduce honest delivery below 0.95 from about 130 frames/s."* Numbers:
`results/hw/flood_cost.authbc-pi4b.csv`, `flood_udp.authbc-pi4b.csv`. ⚠️ Do not write "the cap
limits an insider to the sender it impersonates" without "when it names one sender" (F109).

### A15 — Falcon timing (with the A15 capacity text)

**Proposed:** *"On the Raspberry Pi 4, Falcon-512 signs in 0.64 ms and verifies in 0.09 ms, three
times faster than Ed25519 verifies; a sender spends 0.8 % of a core and a receiver of 124
neighbours 14 %."* Numbers: `results/hw/pq_speed_sig.authbc-pi4b.csv`.

### A8 — energy of the compiled sender (`sec:energy`, Table `tab:energy` and its paragraph)

**Now says:** the lean sender costs 2.7 times the first format's energy per record; "the design
that is smallest on air is not the cheapest to compute". **Proposed:** two rows added to Table
`tab:energy`: compiled lean sender, 17.1 µJ (four records a frame) and 60.7 µJ (one). And:
*"Compiled, the lean sender spends 17.1 µJ per record on the Raspberry Pi 4 — a third of the
first format's 58.4 and a ninth of the Python prototype's 155.4: the reversed order was the
interpreter's."* Numbers: `results/raw/energy_runs_2026-10-22.csv`. ⚠️ State that the sensor's
gain is not calibrated (G22 waived), as for the other rows, and that compiled code drew 12–14 %
less power than the single power figure the model uses (F112).

### Future work (Conclusion; decided by Mohamed, 2026-10-24)

**Proposed:** one paragraph listing what was not done, each with what it would answer:

* **5G NR sidelink (A11):** the capacity accounting on the 3GPP V2X link, which needs a separate
  simulator (5G-LENA).
* A variant for post-quantum signatures that do not fit one frame (kept from the paper).

A14 and the hardware items B1–B5 are not stated (Mohamed, 2026-10-24: not until the purchases).

## Not ready

| item | waits for |
|---|---|
| A14 | not started — the plan keeps it for a follow-up paper |
| B1–B5 | purchases and flights (H3) |

## Claims to keep out

* "Hidden terminals reduce capacity" as the mechanism (A1: they are a minority of spoilers; the
  carrier-sensing range is the cause, and it is Hu & Dai's model, not ours).
* "Mobility does not matter" without the channel's caveat (no Doppler, no time-correlated fading; F103).
* "The adaptive controller keeps V ≥ 0.95 up to 120 nodes" (A4: it did not).
* "Batching matters more with post-quantum signatures" (A15: the same ×3.5).
* Any Tamarin sentence without "in three models".
