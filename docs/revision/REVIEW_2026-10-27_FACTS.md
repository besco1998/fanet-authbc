# Review of 2026-10-27: facts for the scientific items

Each item gives:

* **Answer:** what the artifacts say.
* **Source:** the file and line, or the CSV row.
* **Sentence:** the text the paper should carry, with every number as a macro.
* **Macros:** the macros the sentence needs.

The macros come from `analysis/paper_numbers.py`, block "the review of 27-10" (`REVIEW_SECTIONS`). Each function in that block refuses to run if its artifact stops supporting the cause the sentence states.

Items covered: S-03, S-06, S-07, S-08, S-10, S-13, S-14, S-15, S-16, S-19, S-20, S-21, S-23, S-24, S-28 and S-29. S-01 is not covered here; its ns-3 campaign runs in the main tree.

New macros are marked **new**. The others already exist.

---

## S-03 Neighbors within reach

**Answer.** The definition is in `ns3/authbc-spatial.cc:30` and `:288` (`--dRefM`) and in `analysis/spatial_capacity.py:127-145` (`crossing_row`):

* A node's neighbors within reach are the **other** nodes within d_ref = 215 m of it.
* 215 m is the largest distance at which an isolated link delivers at least 99 % of frames, for all three frames simulated (`results/raw/spatial_dref.csv`, column `d_ref_m`; `predictions/A1-dref.md`).
* The count is averaged over the frames sent, then interpolated at the 95 % delivery crossing.
* In one collision domain the count is N − 1. For example, the fixed row of `spatial_capacity.csv` has n_cross 124.55 and 123.55 neighbors.

At 1 km (`spatial_capacity.csv`, scenario `s1-r1000`):

| | nodes over the area at the crossing | neighbors within reach |
|---|---|---|
| per-record signing | 63.01 | 2.46 |
| AUTHBC | 217.84 | 8.74 |

The ratio is 3.46 at 1 km and 3.46–3.58 over the spread layouts.

Per-radius values for both schemes are in the same CSV: r100, r300, r600 and r1000, plus s2. Fig. 7's middle panel plots them (workstream B, merged as af86343).

**Sentence** (Sec. VIII-A; replaces the old paragraph and keeps its macros):

> A node's neighbors within reach are the other nodes within \spReach\,m of it, the largest distance at which an isolated link delivers at least 99\% of frames; we count them for every frame sent and read the count at the 95\% delivery crossing. AUTHBC keeps its advantage: the capacity ratio lies between \spRatioLo{} and \spRatioHi{} in every layout (Fig.~\ref{fig:spread}). At a radius of 1\,km, \spHiddenPct\% of the interferers of a frame cannot hear its sender. Spread over that disc, the channel carries more nodes, \spArea{} with AUTHBC and \spAreaBase{} with per-record signing, but each has fewer neighbors within reach: \spNeighbours{} and \spNeighboursBase{}, against \nmaxLeanDesign{} and \nmaxLeanBase{} nodes in one collision domain, because a receiver contends with every node in its carrier-sensing range~\cite{hu2020hidden}. With every node on its own Gauss--Markov path at up to 15\,m/s~\cite{bujari2017fanet}, delivery changes by at most \mvDeltaV{} and the ratio stays \mvRatioLo--\mvRatioHi.

**Abstract and conclusion clause:**

> … where the gain is \spRatioLo--\mvRatioHi-fold, although each node then has fewer neighbors within reach (\spNeighbours{} with AUTHBC, \spNeighboursBase{} with per-record signing, at 1\,km).

**Macros:**
* new: `\spReach` (215), `\spNeighboursBase` (2.5), `\spAreaBase` (63)
* existing: `\spNeighbours` (8.7), `\spArea` (218), `\spHiddenPct` (11), `\spRatioLo` (3.46), `\spRatioHi` (3.58), `\mvRatioLo` (3.57), `\mvRatioHi` (3.63), `\mvDeltaV`, `\nmaxLeanDesign`, `\nmaxLeanBase`

**Guards:**
* every row of `spatial_dref.csv` names the same d_ref;
* every frame meets 99 % up to d_ref, and some frame misses it at the next distance;
* neighbors = N − 1 in one collision domain;
* AUTHBC has more neighbors in reach than per-record signing.

---

## S-06 Storage cost per record (42.9 B) against on-air cost (43.25 B)

**Answer.**
* The audit keeps the frames at their on-air length. Its 42.94 B per record is measured on the mission's own frames: `ledger_audit.csv`, `kept_bytes_per_record` = 42.943, sender 1, one hour.
* Table V's 43.25 B uses the sizing convention, which is also Table II's "sender 40000 / one hour at 50 Hz" header point: sender identifier 40 000 and sequence numbers from 180 000 (`src/authbc/bench/leanframes.py:36-38`). It is measured on the first records of each generated trajectory (`lean_frame_sizes`).
* The −0.31 B gap is the net of two effects. I re-measured both today (UAV 1, all 45 000 frames, sizes identical to the signed run).

| frames | B per record |
|---|---|
| Table V sizing (convention identifiers, trajectory starts) | 43.25 |
| the mission's records with the convention identifiers | 43.63 (+0.38) |
| the mission's records with its own identifiers (sender 1, sequence from 0) | **42.94** (−0.68) |

* **Identifiers.** Sender 1 and small sequence numbers take fewer CBOR bytes: −0.68 B per record over the hour.
* **Longer key records later in the hour.** The key record grows from 24.7 B (first 1 000 records) to 26 B (records 90 000–100 000), +0.38 B per record. The cause:
  * The generated velocities grow past CBOR's one-byte integer range. vel_y and vel_z go from about 2 B to 3 B each in plain CBOR.
  * The battery value falls below 24 and saves 1 B.
  * Together these account for +1.0 of the +1.3 B in plain CBOR. The remainder was not attributed.

⚠️ **Correction to the A16 outcome note** (`predictions/A16.md:69`). The note says "42.18 B a record at the start of the hour and 42.75 B by sequence 100 000".
* The start is reproduced: 42.19 over the first 25 frames.
* The second figure is not: frames at sequence 96 000–104 000 cost **43.25**, not 42.75.
* The note's attribution to the identifiers alone is incomplete.

Reproduce with:

```python
leanframes.lean_frame_sizes(4, seeds=(1,), n=180000, src=1, base_seq=0, step_ms=20)
```

and with the default `src`/`base_seq` (36 s for three UAVs). This was not made a macro because it would add 36 s to `paper_numbers.py`.

**Sentence** (Sec. III-C):

> Keeping the frames costs \auKept\,B per record in the audit, slightly less than the \bprLeanDesign\,B of Table~V: the mission's sender identifiers and sequence numbers are smaller than those of Table~V's sizing convention and take fewer CBOR bytes, which outweighs the longer key records later in the hour.

**Macros:** existing only: `\auKept`, `\bprLeanDesign`.

---

## S-07 What the 391 495 audited frames are

**Answer.** The audit counts:
* each UAV's own frames: 3 × 45 000 = **135 000**. 45 000 frames is one hour at 50 records/s, four records a frame.
* plus the copies of the other two UAVs' frames that each UAV kept and that verify: **256 495**. That is 3 × 2 × 45 000 over a link losing 5 %; the expected count is 256 500.

135 000 + 256 495 = 391 495.

The planted forgery (UAV 3's gap-fill in UAV 1's name) is in `frames_held` (256 496) but fails verification, so it is not a leaf.

**Source:**
* `src/authbc/ledger/audit.py:105-131`: leaves = own frames + held frames that verify.
* `analysis/ledger_audit.py:98-105`.
* `results/raw/ledger_audit.csv` row: uavs 3, frames_per_uav 45000, frames_held 256496, frames_audited 391495, loss 0.05.

**Sentence** (Table I, last row, or Sec. III-C):

> \auUavs{} UAVs, one flight hour: the audit covers the \auSent{} frames they sent and the \auHeld{} verified copies they kept of each other's frames over links losing \auLossPct\%, \auFrames{} frames in all.

**Macros:**
* new: `\auSent` (135\,000), `\auHeld` (256\,495), `\auLossPct` (5)
* existing: `\auUavs`, `\auFrames`

**Guards:**
* frames per UAV = mission_s × Λ / b;
* sent + held − 1 planted forgery = audited;
* held is within 0.5 % of what 5 % loss leaves.

---

## S-08 Floor-frame header: 16 B against Table II's 17 B

**Answer.** Both are correct. The single byte is the length prefix of the record stream:
* The stream is a CBOR byte string. Under 24 B, its length sits in the type byte. From 24 B on, it takes one byte of its own (RFC 8949 §3).
* The floor frame carries one 9 B record, so its header is **16 B**.
* Table II's header for sender 0 / record 0 is for a four-record frame. Its stream is at least 36 B, so the header is **17 B**.
* The record count n is under 24 in both, so it costs the same.
* The floor (124 B), the 115 B arithmetic, and every value in Table XIII stand.

**Source:**
* `src/authbc/models/frame.py:61` (`lean_header_bytes`): n=1, stream 9 → 16; n=4, stream 23 → 16; n=4, stream 24 → 17.
* `src/authbc/bench/frame_experiments.py:85-89`: Table II's row is measured with n=4, stream 50.
* `analysis/paper_numbers.py` `exclusion()`: floor_hdr with n=1, stream 9.

**Sentence** (Table II footnote, or Sec. XI after the floor sum):

> The floor frame's header is \exFloorHdr\,B, one byte less than in Table~\ref{tab:frame}: its record stream is a single \exFloorRec\,B record, and CBOR writes the length of a byte string shorter than \exStreamLongAt\,B in its type byte.

**Macros:**
* new: `\exStreamLongAt` (24)
* existing: `\exFloorHdr` (16), `\exFloorRec` (9), `\hdrLeanLo` (17)

**Guard:** the first stream length that lengthens the header is 24. The floor's stream is shorter than 24 and any four-record stream is not. Table II's header = floor header + 1 = the header at 24.

---

## S-10 One Python receiver, three sessions

**Answer.** These are the same Python receiver on pi-B, timed in three harnesses. All are medians per four-record frame.

| value | session | file |
|---|---|---|
| 1.426 ms (`\leanRecvMs` 1.43) | timing harness, 2026-10-09 (run_utc 20261009T121319Z), receiver that keeps frames | `results/hw/p1_lean.authbc-pi4b.frames-kept.csv`, frame_receive b=4 |
| 1.409 ms (`\rxPyUs` 1 409) | Python vs Rust comparison, committed 2026-10-22 (ea4b9af) | `results/hw/compiled_receiver.authbc-pi4b.csv`, python receive_ns_per_frame |
| 1.428 ms | flood harness, receiver alone, same commit | `results/hw/flood_cost.authbc-pi4b.csv`, receiver_only |
| 1.436 ms (`\flHonestMs` 1.44) | flood harness, honest frame through the admission layer with no policy | same file, honest_none |

The highest is 1.9 % above the lowest. The flood value includes the admission layer, about 7 µs over the receiver alone.

**Sentence** (Table IX note, or after the first use in Sec. VII-E):

> The Python receiver was timed in three sessions on the same board, \pyRecvLo--\pyRecvHi\,ms per frame (within \pyRecvSpreadPct\%); each table and paragraph quotes the session it reports, and Sec.~\ref{sec:flooding} adds the admission layer.

**Macros:**
* new: `\pyRecvLo` (1.41), `\pyRecvHi` (1.44), `\pyRecvSpreadPct` (2)
* existing: `\leanRecvMs`, `\rxPyUs`, `\flHonestMs`

**Guard:** the spread across the four values is under 3 %.

---

## S-13 Table XV: "in time" above N_max for Wong–Lam

**Answer.** Table XV's N_max column is the **integer** grid N_max; its in-time column is **interpolated**.

The interpolated delivery crossings exist for every row and come from the same ns-3 runs:
* `ns3_nmax_direct.csv`, cells SM, ST, SG, SE, SW, C and D, under the paper's traffic source;
* the deadline study's LS* cells reproduce SM, ST, SG, SE and SW exactly (`stream_deadline.csv`, `delivery_crossing`).

Put on the same basis, the in-time crossing is below delivery for MAVLink (42.08 against 42.15) and TESLA (39.6–39.8 against 40.4).

Wong–Lam is still 29.1 against 29.0. The 0.1 node is sampling:
* In-time V is counted on the 20 sender→receiver pairs traced in each run.
* Delivery is counted on every pair.
* At N = 29: in-time 0.9504, delivery 0.9500.
* For Wong–Lam a record verifies only if its packet arrived, so on the traced pairs in-time cannot exceed delivery.
* 29.1 lies inside delivery's 95 % interval, [28.8, 29.1] (expanded bootstrap; plain [28.86, 29.14]).

**Source:**
* `analysis/stream_deadline.py:156-200`: in-time per traced pair; `delivered_frac` from all pairs.
* `results/raw/stream_deadline.csv`, column `in_time_v_by_n`.

**Recommendation.** Print both columns interpolated. The N_max column becomes:

| row | value |
|---|---|
| MAVLink | `\crossMav\ \crossCiMav` = 42.1 [42.0, 42.3] |
| TESLA | 40.4 [40.2, 40.7] |
| Gennaro–Rohatgi | 39.4 [39.3, 39.6] |
| EMSS | 34.8 [34.7, 35.0] |
| Wong–Lam | 29.0 [28.8, 29.1] |
| per-record signing | 35.3 [35.1, 35.4] |
| AUTHBC | 124.5 [124.0, 125.0] |

**Sentence** (Table XV note):

> Both capacity columns are crossings of 95\%, interpolated between the two simulated neighborhood sizes around it (30 seeds each). In-time V is counted on the 20 sender--receiver pairs traced in each run and delivery on all pairs, so the in-time crossing of Wong--Lam (\sdWl) lies above its delivery crossing (\crossWl) by sampling alone, inside the latter's interval \crossCiWl.

**Macros:**
* new: `\crossMav`, `\crossTesla`, `\crossGr`, `\crossEmss`, `\crossWl`, `\crossSig`, `\crossDesign` and the matching `\crossCi…`
* existing: `\sdMav`, `\sdWl`, `\sdTeslaLo`, `\sdTeslaHi`

**Guards:**
* Each crossing is recomputed from the runs and must match the summary to 0.005, and its plain interval must match the summary's.
* The integer N_max of `stream_baselines.csv` must be the grid point just below it.
* The deadline study's delivery crossing must equal it.
* An in-time crossing above delivery must lie inside delivery's interval.

---

## S-14 124 against 124.6 against 124.7

**Answer.** All three come from **one set of 30-seed runs** (cell D, jitter 80 ms):

* **Table V, 124 [124, 125]:** the largest simulated N whose mean delivery is at least 0.95, on a 1-node grid around the crossing (122, 123, 124, 125, 127), with its bootstrap interval. Source: `ns3_nmax_direct.csv`, D CROSSING row, n_max_mean 124.
* **Interpolated crossing, the same runs:** 124.549 [124.0, 125.0].
  * ⚠️ **Fig. 6 prints 124.6, which is a double-rounding error.** The summary holds 124.55 (rounded to 0.01) and the figure rounds that half-up again (`analysis/figures_frames.py:105,142`). The value to one decimal is **124.5**.
  * Workstream B's file: fix it by reading the unrounded crossing, or the macro `\crossDesign`.
* **Table XI, 124.7 (`\phyAsixDesign`):** the same runs, interpolated on the PHY study's registered grid of 3-node steps (115, 118, …, 133), which has no point at 125.
  * The delivery at N = 124 and 127 is identical, run for run, to cell D's.
  * Between 124 (0.95072) and 127 (0.94754) the line crosses at 124.68. On the 1-node grid (125: 0.94941) it crosses at 124.55.
  * The finer grid is the better estimate.

The same double rounding exists in two other places:
* `\lineMSM` = 42.2, where the true value is 42.145 → 42.1. It is not used in `main.tex`.
* Summary values 88.85 (B), 74.75 (F) and 124.55 (spatial, fixed) would round wrongly if printed to one decimal. None is printed now.

**Recommendation.**
* Fig. 6 and every interpolated mention: `\crossDesign{}` (124.5) and `\crossSig{}` (35.3).
* Table XI: keep its registered grid and add a footnote (below). Re-scoring a registered study on another grid would change what was registered.

**Sentence** (Sec. VI-C):

> Table~\ref{tab:ladder} gives $N_{\max}$ as the largest simulated neighborhood whose mean delivery over 30 seeds is at least 95\%, with its bootstrap interval. The figures and Tables~\ref{tab:phy} and~\ref{tab:stream} give the crossing of 95\% interpolated between the two simulated sizes around it, from the same runs: \crossDesign{} \crossCiDesign{} for AUTHBC and \crossSig{} \crossCiSig{} for per-record signing.

**Footnote** (Table XI):

> The 802.11a 6\,Mb/s row reads the same runs on this study's grid of \phyGridStep-node steps, which gives \phyAsixDesign.

**Macros:**
* new: `\crossDesign`, `\crossCiDesign`, `\crossSig`, `\crossCiSig`, `\phyGridStep` (3)
* existing: `\nmaxLeanDesign`, `\ciLeanDesign`, `\phyAsixDesign`

**Guards:**
* The PHY study's Pa6D runs equal cell D's run for run at every shared (N, seed).
* Its grid steps evenly and skips the point just above the crossing.

---

## S-15 BLS: 96 B timed, 48 B in the exclusion table

**Answer.**
* blspy implements only the **minimal-pubkey-size** variant: 48 B public key in G1, **96 B signature** in G2. See `src/authbc/crypto/bls.py:1-20` and the spec-gap note in `src/authbc/crypto/base.py:9-12`.
* All BLS timings (sign 2.73 ms, verify 8.61 ms) and the CPU count (`\ncpuBls` = 10 nodes per core) are of that variant.
* The 48 B **minimal-signature-size** variant was **never timed**. No artifact holds its time.
* The draft defines both variants (draft-irtf-cfrg-bls-signature-05 §2.1). CoreVerify computes **two pairings in both** (§2.7, steps 7–8), with the groups swapped.
* §2.1 also says implementations that aggregate SHOULD use the minimal-pubkey-size variant, which is the one timed.
* Read from ietf.org/archive/id/draft-irtf-cfrg-bls-signature-05.txt on 2026-10-27, with no identifying data. The PDF is not held in `docs/literature/`.
* For the channel, not the CPU, to bind at \nmaxLeanDesign{} nodes, a verification would have to take ≤ **0.64 ms**: Eq. (cpu) with one signature a frame and the hash term. That is **13×** faster than the 8.61 ms timed.
* That a 48 B verification, with the same two pairings, is 13× faster is not shown by any measurement here. The sentence states the bound without claiming an answer.

**Sentence** (Sec. IV-F, after the 96 B remark, or Table XIII note):

> All BLS timings are of blspy's variant with 96\,B signatures; the 48\,B variant~\cite{cfrg_bls} was not timed. It verifies with the same two pairings, and to leave the channel as the binding limit at \nmaxLeanDesign{} nodes it would have to verify in \blsVerNeedMs\,ms, \blsSpeedup{} times faster than the \tVerBls\,ms we measured.

**Macros:**
* new: `\blsVerNeedMs` (0.64), `\blsSpeedup` (13)
* existing: `\tVerBls`, `\nmaxLeanDesign`, `\ncpuBls`

**Guard:** Eq. (cpu) with the timed verification reproduces the ladder's `n_cpu_one_core` for BLS (10).

**Option for Mohamed.** Time a minimal-signature-size verification on pi-B, for example with the `blst` Rust crate's `min_sig` module. This would be a new measurement, and is not proposed here.

---

## S-16 LoRaWAN spacing: 5.5 s against 5.0 s and 6.1 s

**Answer.** All three spacings are real; they measure different things.

* **5.0 s:** the spacing of records in the DR5 242 B frame. Eight records per duty-cycle interval of 40 s, 0.20 records/s (`results/raw/lora_budget.csv`, row dr 5, payload 242, "lean; frames decode alone": `record_spacing_s` 5.0).
* **5.5 s:** the spacing at which that frame's **delta records were sized** (`delta_measured_at_s` 5.5).
  * Delta sizes are measured only at strides of 0.05, 0.1, 1, 5.5 and 16.5 s (`experiments/frame-components/config.yaml:18`).
  * `_lora_fit` takes the measured stride nearest the implied spacing (`src/authbc/bench/frame_experiments.py:681-702`).
  * The 13.6 B is the mean delta at 5.5 s (`frame_components.csv`, record lean delta stride 110).
* **6.1 s:** the spacing of the frame simulated in ns-3, six records every 36.4 s (`lora_capacity.csv`). The repeater-compatible 222 B budget row gives 5.98 s.
  * Both use the 5.5 s deltas, the nearest measured stride.

Delta size grows with spacing: 12.5 B at 1 s, 13.6 B at 5.5 s. The delta at 5.0 s was not measured.
* Eight records hold with 0.83 B to spare at 242 B.
* A ninth would need about 13 B more.
* The batch is therefore not sensitive to the snap.

**Sentence** (Sec. XI):

> At this rate a frame's records are \loraSpacingLean\,s apart (\loraSimSpacing\,s in the simulated frame); their delta records were sized at the nearest spacing we measured, \loraSpacing\,s, where one costs \deltaLeanFar\,B, not the \deltaLean\,B it costs at 50\,ms.

**Macros:**
* new: `\loraSpacingLean` (5.0), `\loraSimSpacing` (6.1)
* existing: `\loraSpacing` (5.5), `\deltaLeanFar` (13.6), `\deltaLean` (9.0)

**Guards:**
* The DR5 budget row's deltas are the 5.5 s measurement: same spacing, same bytes, stride 110, and the nearest stride to the implied spacing.
* All LoRa capacity runs share one frame and period.

---

## S-19 Why 41 flooding senders

**Answer.**
* 41 is one core's share of AUTHBC's 124-node neighborhood, with that neighborhood spread over the cores the Python receiver needs.
* At 1.426 ms per frame and 12.5 frames/s per neighbor, 123 neighbors need 2.2 cores (`\cpuProtoCores`), so **three** cores; 124 // 3 = 41.
* It was chosen before any run (`analysis/flood_cost.py:27-29`; F84).
* Unattacked, the outcome confirms the choice (`results/hw/flood_udp.authbc-pi4b.csv`, rows policy none, attack forged, rate 0):
  * 41 senders: every honest frame accepted (V = 1.0); the receiver used **80 %** of its core.
  * 124 senders on one core: the kernel dropped 13 129 of 23 188 frames; V = **0.43** at 99.7 % core use.

**Sentence** (Sec. IX-B, and short form in the Fig. 9 caption):

> We flood \flSenders{} senders, one core's share of the \nmaxLeanDesign{} nodes for which the Python receiver needs \flCores{} cores (\cpuProtoCores{} at \leanRecvMs\,ms a frame): unattacked, they take \flQuietSharePct\% of the core and every honest frame is accepted, whereas all \nmaxLeanDesign{} senders on one core leave $V = \flAllV$.

**Macros:**
* new: `\flCores` (three), `\flQuietSharePct` (80), `\flAllV` (0.43)
* existing: `\flSenders`, `\nmaxLeanDesign`, `\cpuProtoCores`, `\leanRecvMs`

**Guards:**
* The two loads are N and N // ceil((N−1)·12.5·t_rx).
* V = 1.0 at the smaller load and < 0.95 at the larger.

---

## S-20 The 250 ms window budget

**Answer.** The review assumes the batch fill counts against the window. It does not.

* The timestamp acceptance window is held against a frame's **newest** record (`src/authbc/placement/freshness_rule.py:101`), and the frame leaves when that record is taken.
* An honest frame therefore arrives **3.75 ms** (T_ch + t_v, the worst channel delay and one verification) after its newest timestamp (`analysis/replay_window.py:105`).
* That leaves 246 ms of the 250 ms for clock drift (2 × 20 ppm, 144 ms/h) and the two clocks' reading errors (σ = 10 ms each, so their difference has σ√2 = 14 ms).

From `results/raw/replay_window.csv`, outage rows of policy fixed250, 72 000 honest frames each:

| outage | drift | margin left | refused |
|---|---|---|---|
| 75 min | 180 ms | 66 ms = 4.7 σ√2 | 1 of 72 000 (1.4 × 10⁻⁵) |
| 90 min | 216 ms | 30 ms = 2.1 σ√2 | 1 174 (1.6 %) |

`\rpHolds` (75) is the longest outage simulated, in 15-min steps, at which fewer than 1 in 10⁴ honest frames are refused.

**Sentence** (Sec. IX-A; one line in Table I row (v) can point to it):

> The window is held against a frame's newest record, taken as the frame leaves, so an honest frame arrives \rpAfterMs\,ms old (channel and one verification) and \rpBudgetMs\,ms of a 250\,ms window remain for clock drift and the two clocks' errors (\rpApartMs\,ms apart, one standard deviation). After 75\,min without GNSS the drift is \rpDriftHold\,ms and the margin \rpMarginMs\,ms, \rpMarginSd{} standard deviations: \rpHoldRefused{} of \rpFrames{} honest frames was refused. After \rpNextMin\,min (\rpNextDrift\,ms) \rpNextPct\% were.

Better: replace the literal "75" with `\rpHolds`.

**Macros:**
* new: `\rpAfterMs` (3.75), `\rpBudgetMs` (246), `\rpApartMs` (14), `\rpDriftHold` (180), `\rpMarginMs` (66), `\rpMarginSd` (4.7), `\rpHoldRefused` (one), `\rpNextMin` (90), `\rpNextDrift` (216), `\rpNextPct` (1.6)
* existing: `\rpHolds` (75), `\rpDrift` (144), `\rpFrames` (72\,000)

**Guards:**
* The outage rows share one window, one σ and one frame count, which equal the honest study's.
* The window holds on a prefix of outages and then stops.

**Note.** The formula window of `TimeWindow` (b/Λ + T_ch + t_v + 2σ + g = 113.75 ms at σ = 10 ms) is a different object, a design rule that counts the fill. The 250 ms result is a fixed window tested on the newest record.

---

## S-21 TS 22.125: the requirement the 50 Hz / 100 ms pair meets

**Answer.** These are not a table entry. They are two numbered requirements in **§5.2.2** of 3GPP TS 22.125 V17.6.0 (ETSI TS 122 125 V17.6.0, 2022-04), page 10 of the held PDF `docs/literature/3gpp_ts22125_v17.6.0_uav_requirements.pdf`. Verbatim:

* **[R-5.2.2-010]** "The 3GPP system shall support a direct UAV to UAV local broadcast communication transport service which can transmit messages at a frequency of at least 10 messages per second."
* **[R-5.2.2-011]** "… which can transmit messages with an end-to-end latency of at most 100ms."

They are requirements on the transport the 3GPP system must **support**: at least 10 messages/s and at most 100 ms. AUTHBC's pair falls within them either way a message is counted:
* 12.5 frames/s, or 50 records/s, ≥ 10 messages/s;
* D_max = 100 ms ≤ 100 ms.

Nearby requirements in the same section, for Mohamed's information:
* R-5.2.2-008: payloads of 50–1500 B, "not including security-related message component(s)".
* R-5.2.2-009: range up to 600 m.

**Sentence** (Sec. III-A):

> The pair lies within the 3GPP requirements for direct UAV-to-UAV broadcast: at least 10 messages per second and an end-to-end latency of at most 100\,ms (TS~22.125, R-5.2.2-010 and -011~\cite{3gpp_ts22125}).

**Macros:** none. These are constants of the standard, quoted.

---

## S-23 "Four cores give 3.36 times one"

**Answer.** 3.36 is the ratio of **frames per second**, 2329.45 / 692.45 = 3.364 (`results/hw/multicore_receive.authbc-pi4b.csv`, workers 4 and 1).

The node counts are whole nodes with the receiver itself counted, 1 + floor(fps / 12.5) (`hw/multicore_receive.py:121`): 56 and 187. Their ratio is 3.34. Both are correct; the sentence should name the frame rate.

**Sentence** (Sec. VII-E):

> Four cores receive \mcScaleFour{} times the frames of one, less than we had written down beforehand, so \nmaxLeanDesign{} nodes need three of them.

**Macros:** existing only: `\mcScaleFour`, `\mcNodesOne` … `\mcNodesFour`.

---

## S-24 Rust, batches of 64: 124 µs and 643 nodes

**Answer.** The unrounded time is 7.347 µs (decode and rebuild) + 117.071 µs (a frame's share of a 64-signature batch) = **124.418 µs** (`results/hw/compiled_receiver.authbc-pi4b.csv`).
* `\rxBatchUs` now prints **124.4** (was 124). This is the only changed value of an existing macro.
* By Eq. (cpu), 1 + floor(1/((Λ/b) t)), 124.418 µs gives 643. The table is right; the printed 124 gave 646.

⚠️ **A related inconsistency.** The table's node column is 1/((Λ/b) t) *rounded*, not Eq. (cpu)'s 1 + floor. The CSV's `derived` rows say "Eq. (4)" but compute the former. From the unrounded times:

| row | table | Eq. (cpu) |
|---|---|---|
| Python | 57 | 57 |
| Rust | **289** | **290** |
| Rust, batches of 64 | 643 | 643 |
| Rust, deferred | **628** | **629** |

The two readings differ by one node for Rust and for the deferred path. `\rxRustNodes` (289) is printed in four places in this worktree's `main.tex`: the introduction, Table XVI, the recommendations and the conclusion.

**Options (Mohamed decides):**
* (a) Print Eq. (cpu) everywhere: `\rxRustNodesEq` (290), `\rxLazyNodesEq` (629).
* (b) Keep the rounded ratio and say so in the table note.

(a) is consistent with Eq. (cpu) and with `\ncpuProto` (57), which already uses it. The change is one node.

**Sentence** (Table IX note, if (a)):

> Nodes per core by Eq.~\eqref{eq:cpu} with the time per frame in place of the cryptography, the receiver included.

**Macros:**
* changed: `\rxBatchUs` (124.4)
* new: `\rxPyNodesEq` (57), `\rxRustNodesEq` (290), `\rxBatchNodesEq` (643), `\rxLazyNodesEq` (629)

---

## S-28 Which side of the law the stream frames fall

**Answer.** ns-3 is **above** the airtime capacity law for all five one-record stream frames, by 3.5–4.2 %. The simulated crossings are higher than predicted:

| frame | predicted (line) | simulated | deviation |
|---|---|---|---|
| MAVLink | 40.6 | 42.1 | +3.8 % |
| TESLA | 38.8 | 40.4 | +4.2 % |
| Gennaro–Rohatgi | 38.0 | 39.4 | +3.8 % |
| EMSS | 33.6 | 34.8 | +3.5 % |
| Wong–Lam | 28.0 | 29.0 | +3.5 % |

Sources: `analysis/nmax_airtime_line.py` `stream_scores`; `paper/numbers.tex` `\lineDS*`, `\linePS*`. The existing guard in `_stream_cells_against_the_line` already refuses the text if any falls below.

**Sentence** (Sec. VII-D):

> … and the five one-record frames of Table~\ref{tab:stream}, whose simulated capacities lie \lineStreamLeast--\lineStreamWorst\% above the law's prediction.

**Macros:** existing only: `\lineStreamLeast` (3.5), `\lineStreamWorst` (4.2).

---

## S-29 Falcon was checked against the contention model, not the law

**Answer.**
* The law was checked on frames of 94–565 B (`\lineFrameLo`–`\lineFrameHi`).
* The Falcon-512 frames are **749 B** (one record) and **776 B** (four), outside that range.
* The registered check was the **contention model** (`results/raw/pq_capacity.csv`, `in_model_band` = 1 for both):

| frame | model | ns-3 | gap |
|---|---|---|---|
| one record | 12.34 | 12.41 | +0.57 % |
| four records | 43.23 | 43.50 | +0.62 % |

The law is off by up to **7 %** there (+7.35 %, −3.12 %), which is why it is not claimed for these frames.

**Sentence** (Sec. VII-D, after the range of the law, or Sec. VIII Falcon paragraph):

> Falcon-512's frames (\pqFrameBase{} and \pqFrameDesign\,B) lie outside that range and were checked against the contention model instead, which predicted \pqModelBase{} and \pqModelDesign{} nodes, within \pqModelWorst\% of the simulated \pqBase{} and \pqDesign; the law misses them by up to \pqLineWorst\%.

**Macros:**
* new: `\pqFrameBase` (749), `\pqFrameDesign` (776), `\pqModelBase` (12.3), `\pqModelDesign` (43.2), `\pqModelWorst` (0.6), `\pqLineWorst` (7)
* existing: `\pqBase`, `\pqDesign`, `\lineFrameLo`, `\lineFrameHi`

**Guard:** both Falcon frames are larger than every frame the law was checked on, and both are inside the model's band.

---

## Summary of code changes (`analysis/paper_numbers.py`)

* **New block "the review of 27-10".** It holds `_direct`, `review_crossings`, `review_spread`, `review_audit`, `review_header`, `review_receive`, `review_bls`, `review_lora`, `review_flood`, `review_window`, `review_receiver_nodes` and `review_pq`.
* **Where it sits.** The block goes before "tables of the revision", collected in `REVIEW_SECTIONS`. `macros()` iterates over `SECTIONS + REVIEW_SECTIONS`, so `SECTIONS` itself is untouched; that keeps the merge with `capacity_with_margin()` clean.
* **One changed value:** `\rxBatchUs` 124 → 124.4.
* **52 new macros, none yet used by `main.tex`.** They are expected to fail `test_every_generated_number_is_used` until the sentences above are placed:
  * `auHeld auLossPct auSent`
  * `blsSpeedup blsVerNeedMs`
  * `crossCiDesign crossCiEmss crossCiGr crossCiMav crossCiSig crossCiTesla crossCiWl crossDesign crossEmss crossGr crossMav crossSig crossTesla crossWl`
  * `exStreamLongAt`
  * `flAllV flCores flQuietSharePct`
  * `loraSimSpacing loraSpacingLean`
  * `phyGridStep`
  * `pqFrameBase pqFrameDesign pqLineWorst pqModelBase pqModelDesign pqModelWorst`
  * `pyRecvHi pyRecvLo pyRecvSpreadPct`
  * `rpAfterMs rpApartMs rpBudgetMs rpDriftHold rpHoldRefused rpMarginMs rpMarginSd rpNextDrift rpNextMin rpNextPct`
  * `rxBatchNodesEq rxLazyNodesEq rxPyNodesEq rxRustNodesEq`
  * `spAreaBase spNeighboursBase spReach`

  Of these, the `rx…NodesEq` macros are needed only under option (a) of S-24.
