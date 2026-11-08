# Revision status — one row per item of `docs/revision/REVISION_PLAN.md`

*Updated 2026-10-22. Branch `p11-reviewer-revision`. Registrations are
`predictions/<ID>.md`, tagged `prereg-<ID>` at the commit that registered them; outcomes are
appended to the same file below a line. Rules: `docs/revision/STATUS.md`. Long jobs run
as memory-capped systemd user units (`scripts/capped.sh`; `systemctl --user list-units
'authbc-*'`), logs in `~/.cache/authbc-logs/`.*

| ID | State | What is known |
|---|---|---|
| A1 | ✔ stage 2 (4 230 runs) | ratio 3.46–3.58 in every layout, equal power to a 1 km disc (hidden share up to 0.11); capacity in neighbours falls (8.7 at R = 1 km), in nodes it rises (218). My A1-2 bracket [10, 40] missed. ⚠️ S3's 5 and 15 m/s are identical runs: group speed untestable in this scenario (F88, H8) |
| A1-motion | ✔ (900 runs) | every node moving on its own at 0/5/15 m/s: ΔV ≤ 0.0005, ratio 3.57–3.63; motion changes the runs (0/300 identical) but not the neighbour count. F103 (closes H8) |
| A2 | ✔ map, age part, ns-3 validation (3 150 runs) | one lost frame breaks the deadline; the map holds in ns-3 at 15 roles within 1.05 % of the model; ratio 6.63 at (100 /s, 100 ms) (F90, F100) |
| A3 | ✔ part 1 and part 2 (60 traced runs, 3 000 links) | tolerable loss held; the margin rule fails in 5 of 192 cells, all bursty, by its interval (F86; one is the design, b = 4, at ε = 0.1, p = 0.08, Gilbert-8; under bit errors, outside the 192, the design misses by its interval at the same point). Traces: ns-3 collision loss is independent frame to frame (burst 1.06), so V follows Eq. (3) for independent loss, not the Gilbert form (F98); plan (3) missed in 1 of 4 by 0.0002 |
| A4 | ✔ (120 runs) | the controller saves 9–41 ms of peak age but runs at the target's edge: V ≈ 0.955, a quarter of windows < 0.95 on the ramp, fails at 76 nodes (fixed b = 4: 127; oracle: 125). Plan (2), (3) failed; (1), (4)–(6) held. H9 |
| A4b | ✔ (60 runs) | the shortfall was mostly margin: margin 0.02 holds 93 % of windows, fails at 116 (A4: 75 %, 76), saves 20 ms vs fixed b = 4; growth term alone 85 %, 108. Neither within 5 % of fixed b = 4. Mobile cannot discriminate (identical series). F102 |
| A5 | ✔ | the window closes the delay-line attack; the plan's "2 hours" failed as predicted (75 min) |
| A6 | ✔ — registered model: 3 of 9 settled (19 predicted verdicts, 4 came true). **After registration**, two encodings changed (counters keyed by a fresh session id; a receiver start rule) and helpers added: lemmas 1–3 and gap detection verified in `formal/authbc_counters.spthy` (all 15, one run); continuity in the registered model; lemma 5 attack-then-fix in `formal/authbc_time.spthy`. One model with everything (`formal/authbc_full.spthy`) did not settle | the plan's statement held across three models, two made after registration |
| A7 | ✔ timing + flood on pi-B (2026-10-22) | the 8 B group tag stops an outsider (refused at 22.5 µs; V = 0.984 at 3 000 forged/s with 41 senders); a forged frame costs 1.08 ms, not 1.4 (928/s per core, not 700); cheap checks and the cap do nothing against an insider spreading forgeries (V < 0.95 from ~125/s); the tag costs 3.1 % of capacity. F109. Reboot during the first flood (a jostled power supply): re-run whole, disclosed |
| A8 | ✔ timing and energy on pi-B (2026-10-22) | compiled receive 0.277 ms vs Python 1.409 (×5.1); 290 nodes per core by Eq. (4), 643 with batches of 64 (F108). Energy (rig check passed; calibration waived by Mohamed): the compiled lean sender spends 17.1 µJ/record (b = 4) and 60.7 (b = 1) against the first format's 58.4 and 118.0: the anomaly is the interpreter's; my ranges missed low (power 0.65 W, not 0.75). F112 |
| A9 | ✔ (30 SIH flights) + **A9-fast ✔** (the 20 fixed-wing/VTOL missions re-flown at their drawn 15–25 m/s, 2026-10-22) | delta = one byte per field on every airframe; at the registered speeds fixed wings cost +0.2 B (9.22 vs 9.00); 25 fields: saving 63.3 %, ratio 3.04. The plan's ~60 B keyframe and 10–13 B fixed-wing delta missed at every speed. A9's airplane flights had a ground-level first leg (TECS reference from sea level): no effect. F105, F107, F111 | the gain is set by the frame count: 2× until a 159–282 B delta |
| A10 | ✔ (1 860 runs) | Table 5 reproduced (all N_max in their intervals); against 100 ms only MAVLink 2 (42.1), Wong–Lam (29.1) and TESLA with d = 2, I ≤ 20 ms (39.6–39.8) cross; G-R, every EMSS and TESLA-batch4 never do. F99 |
| A11 | ✔ 802.11 (2 520 runs); NR sidelink: **future work** (Mohamed, 2026-10-24) | ratio 3.39–3.80 on six PHYs/rates, rising with rate (not the plan's 1.7–4.3); the model within 1.5 % except at the fastest rate of each channel width, 2.9–4.6 % optimistic there (F104, corrected 2026-10-24) |
| A12 | ✔ (330 runs) | delivery follows the total frame rate: every plan statement held, the model within 0.0011 up to 350 frames/s per node; eight radios can stand for 124 nodes in ns-3. Not in the paper: it only prepared B2 |
| A13 | ✔ (pi-B, 2026-10-22) | lazy verification: tier 1 10.2 µs, tier 2 117.2 µs per frame → 629 nodes per core by Eq. (4); evidence ≤ 171 ms (my 170 ms bound missed by 1 ms). F108 |
| A14 | not done — **not stated** in the paper or the letter, not even as future work, until the purchases (Mohamed, 2026-10-24) | |
| A15 | ✔ capacity and timing (host + pi-B, 2026-10-22) | Falcon fits; the design with it serves 43.5 nodes; the ratio is 3.5, as with Ed25519 (the plan's "larger" failed). Falcon-512 on pi-B: sign 638 µs, verify 88 µs (3× faster than Ed25519's 259). F110 |
| A16 | ✔ | both faults caught, no false finding; 6.4 min of a core per flight hour; 0.96 GB/h for 124 neighbours |
| A17 | ✔ | the CAM deadline is not in its standard |
| B1–B5 | not executable here — purchases, flights (H3); **not stated** in the paper or the letter until the purchases (Mohamed, 2026-10-24) | |

## The crash of 2026-10-20 01:02

WSL ran out of memory: two Tamarin proofs (5.7 GB, growing), the test gate (4.2 GB), ten ns-3
runs (3.4 GB) and the editor (2.4 GB) against 14 GB + 4 GB swap; the kernel's OOM killer then
took WSL's own init processes (`journalctl -b -1`: "init.scope: Failed with result
'oom-kill'"). Lost: ~2.5 h of A2 runs (the driver checkpointed in submission order), the A5
run, both Tamarin runs, and everything under `/tmp`. Fixed: memory-capped units, completion-
order checkpoints, logs and the clean gate under `~/.cache`.

---

## How the revision was run

*The execution rules written on 2026-10-19, before any run (formerly `docs/revision/EXECUTION_PLAN.md`).*

### Executing the AUTHBC Revision Plan — what runs, in what order, under which rules

*Formerly `docs/revision/EXECUTION_PLAN.md`, last changed 2026-10-19. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*Written 2026-10-19, before any run of the revision. The plan itself is
`docs/revision/REVISION_PLAN.md` (Mohamed, 2026-10-19). This file says how it is executed, what
cannot be executed here, and where the plan's predictions were checked against what the
repository already knows. Status of each item: `docs/revision/STATUS.md`.*

#### Objective

Answer the reviewer objections the plan lists — single collision domain, one operating point,
zero verifiability margin, accounting without a mechanism, delayed replay, informal security,
unquantified flooding, an interpreted prototype — with experiments whose outcomes are written
down before they are run.

#### Rules carried over unchanged

* **Registration.** Before the first run of experiment X, `predictions/X.md` is committed with
  the plan's Expected outcome **verbatim**, the pass criterion, and the analysis script; the
  commit is tagged `prereg-X`. A prediction file is never edited after its first run. Misses are
  reported as misses.
* **Where I disagree with a prediction of the plan before running,** the file keeps the plan's
  sentence and adds mine beside it, with the reason, marked `[agent]`. Both are scored. A
  prediction that can be computed without running anything is computed and the computation
  committed with it — it is then a check of arithmetic, not a prediction, and is labelled so.
* **Thirty seeds, bootstrap intervals, distributions before thresholds** (the lesson of four
  headline numbers distorted by small samples). Configurations run in pairs: baseline (ladder
  row 5, lean/inline-1, 145.77 B/record) and design (row 8, lean/batch-delta, 43.25 B/record),
  plus row 6 (lean/inline-b) where the plan asks for it.
* **The published scenario stays bit-identical.** New ns-3 behaviour lives in new scenario
  files or behind options that are absent by default; every new code path first reproduces
  the published crossings (35 / 124) before it produces anything new.
* **Timed source files are not edited.** `tests/test_bench_session_hw.py` holds the SHA-256 of
  `session_v2.py`, `store.py`, `wire_v2.py` as timed on pi-B. New receiver rules (A5 time
  window, A7 checks and HMAC envelope, A13 two tiers) are layers *around* the receiver, so the
  frame bytes and the timed code do not move.
* **Search prior work before a derivation enters the paper** (F9, F65): two or three queries,
  recorded in the registration, before the registration commit.
* Every number the paper prints stays generated (`analysis/paper_numbers.py`).

#### What cannot be executed in this session, and why

| Item | Needs | State on 2026-10-19 |
|---|---|---|
| A7, A8, A13, A15 measurements on the Pi | pi-B switched on (192.168.1.20) | both boards are off (no ping). Code and host-side (x86) numbers are prepared; the Pi runs wait for the boards. Host numbers are never presented as Pi numbers |
| A8 energy and its calibration | the rig with the sync wire, a power resistor, a bench multimeter | Mohamed at the bench (open item G22) |
| B1–B5 | new radios, a power profiler, drones, permits | purchases and flights are Mohamed's decisions. Nothing is run; B1/B2 protocols can be prepared |
| A11 NR sidelink | 5G-LENA built on its own ns-3 version | a large separate build; scheduled last |

#### Substitutions — methods that differ from the plan's wording, stated before running

1. **Shared baseline.** The plan's listing uses `FixedRssLossModel(-60 dBm)`; the published runs
   used `LogDistancePropagationLossModel` with exponent 0 and the nodes 1 cm apart (equal
   received power, about −30.7 dBm). Both give equal power and no capture. The A1 reproduction
   check runs the plan's `FixedRss` through the new code path, as the plan says.
2. **802.11p (A11).** ns-3.48 has no `OcbWifiMac` (the WAVE module was removed). The 802.11p
   PHY (10 MHz, `WIFI_STANDARD_80211p`) is run under the same ad-hoc, non-QoS DCF MAC as the
   802.11a baseline, so only the PHY changes. OCB's EDCA access categories are not modelled.
3. **TESLA, EMSS, Wong–Lam (A10).** Broadcast has no acknowledgement and no feedback, so which
   frames a receiver gets does not depend on what the frames contain, only on their size and
   timing. The schemes are implemented as sender and receiver code with real keys, hashes and
   signatures, and their frames are put through per-frame reception traces exported from ns-3
   runs at their own frame size and rate. This is exactly equivalent to an ns-3 application for
   a channel without feedback, and lets the same traces score both delivery and deadline-aware
   verification. Stated in the paper if used.
4. **AoI (A2).** "Peak age at the receiver for every verified record" is read two ways and both
   are reported: the per-record delay to verification (which loss does not change — a lost
   record is never verified), and the peak age of information of each sender at each receiver
   (which loss does change). The plan's formula is about the second.

#### Order of execution

Compute is the bottleneck (16 cores, one host; one design run at N = 124 takes 45 s, and a
1 km disc at N = 400 several minutes). Long campaigns run detached while the next item is
built.

| Wave | Items | Why this order |
|---|---|---|
| 1 | A2 (analytic grid + 10 ns-3 cells), A17, A3, A12 | cheap, no new simulator code beyond options; A3's trace-driven part waits for A1 |
| 1 | **A1** scenario, d_ref, reproduction check, campaign | the longest; A3, A4, A14 reuse its scenarios and traces |
| 1 | A5 | codec harness only |
| 2 | A4 controller | needs A1's scenario |
| 2 | A6 Tamarin, A10, A15 (simulation), A9, A16 | independent of the Pi |
| 2 | A7, A8, A13 code; Pi runs when the boards are on | |
| 3 | A11 (802.11p, then sidelink), A14 | lowest priority in the plan |

#### Where the plan's predictions were checked before running

Found while reading the plan against the repository (2026-10-19). Each is repeated in the
registration of its experiment.

* **A2, tail of the age.** The plan: "the 99th percentile exceeds D_max whenever two consecutive
  frames are lost." One lost frame is enough: the next update then arrives 2b/Λ after the last,
  so the peak age is 2·80 + 3.49 + 0.26 = 163.75 ms > 100 ms. With independent loss p, a share
  p of the inter-update gaps contains a loss, so the 99th percentile of peak age exceeds D_max
  for every p ≥ 0.01 and the 95th for p ≥ 0.05. Registered beside the plan's sentence.
* **A3, tolerable loss under length-dependent loss.** Computed from the frame sizes:
  0.0436 at b = 4 and 0.0476 at b = 2 (plan: about 0.044 and 0.047). Agrees. This is arithmetic
  on the frame lengths, not a prediction of the measurement.
* **A3, r = 1 under independent loss.** V = 1 − p exactly in expectation, so "passes with margin
  whenever ε ≥ p + 0.02" holds by definition; what the run measures is the spread.
* **A15.** The closed form (Eq. 6) was fitted to frames of 0.3–0.5 ms; a Falcon frame is about
  1.1 ms on air, outside its range. The access-rule model has nothing fitted and is used for the
  prediction as well; both are registered.
* **A2, gain region.** On the plan's grid, "ratio 1.0 exactly where ΛD_max ≤ 2" coincides with
  b* = 1. In general b* ≥ 2 needs ΛD_max ≥ 2 + Λ(T_ch + t_v); no cell of the grid falls between.

#### Decisions that remain Mohamed's

Listed in `docs/OPEN_ITEMS.md` §H as they arise. Known at the start:

* **The uncommitted paper edits of 2026-10-12** (`paper/main.tex` rewritten in the published
  style, `block_diagram.png`, the `platforms()` table in `analysis/paper_numbers.py`). They are
  not mine to commit; the revision's commits stage files by name and leave them as they are.
  Text changes from the revision wait until he says which `main.tex` they go into.
* Part B purchases (B1 radio, B2 radios, B3 profiler); flights (B4, B5).
* Whether the optional HMAC envelope (A7) becomes part of the frame format, and whether
  "blockchain-style ledger" becomes "hash-chained log" if A16's audit is not adopted.

#### Acceptance criteria

An experiment is done when: its registration commit precedes its first run; its raw CSVs carry
config hash and environment headers; the analysis script reproduces the summary from the raw
file; each prediction is scored pass/fail in its registration's outcome section; one point is
cross-checked by a second method; `make all` is green on the branch; and its finding is entered
in `docs/audits/model_provenance.md`.

