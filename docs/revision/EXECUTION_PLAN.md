# Executing the AUTHBC Revision Plan — what runs, in what order, under which rules

*Written 2026-10-19, before any run of the revision. The plan itself is
`docs/AUTHBC Revision Plan.md` (Mohamed, 2026-10-19). This file says how it is executed, what
cannot be executed here, and where the plan's predictions were checked against what the
repository already knows. Status of each item: `docs/revision/STATUS.md`.*

## Objective

Answer the reviewer objections the plan lists — single collision domain, one operating point,
zero verifiability margin, accounting without a mechanism, delayed replay, informal security,
unquantified flooding, an interpreted prototype — with experiments whose outcomes are written
down before they are run.

## Rules carried over unchanged

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

## What cannot be executed in this session, and why

| Item | Needs | State on 2026-10-19 |
|---|---|---|
| A7, A8, A13, A15 measurements on the Pi | pi-B switched on (192.168.1.20) | both boards are off (no ping). Code and host-side (x86) numbers are prepared; the Pi runs wait for the boards. Host numbers are never presented as Pi numbers |
| A8 energy and its calibration | the rig with the sync wire, a power resistor, a bench multimeter | Mohamed at the bench (open item G22) |
| B1–B5 | new radios, a power profiler, drones, permits | purchases and flights are Mohamed's decisions. Nothing is run; B1/B2 protocols can be prepared |
| A11 NR sidelink | 5G-LENA built on its own ns-3 version | a large separate build; scheduled last |

## Substitutions — methods that differ from the plan's wording, stated before running

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

## Order of execution

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

## Where the plan's predictions were checked before running

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

## Decisions that remain Mohamed's

Listed in `docs/OPEN_ITEMS.md` §H as they arise. Known at the start:

* **The uncommitted paper edits of 2026-10-12** (`paper/main.tex` rewritten in the published
  style, `block_diagram.png`, the `platforms()` table in `analysis/paper_numbers.py`). They are
  not mine to commit; the revision's commits stage files by name and leave them as they are.
  Text changes from the revision wait until he says which `main.tex` they go into.
* Part B purchases (B1 radio, B2 radios, B3 profiler); flights (B4, B5).
* Whether the optional HMAC envelope (A7) becomes part of the frame format, and whether
  "blockchain-style ledger" becomes "hash-chained log" if A16's audit is not adopted.

## Acceptance criteria

An experiment is done when: its registration commit precedes its first run; its raw CSVs carry
config hash and environment headers; the analysis script reproduces the summary from the raw
file; each prediction is scored pass/fail in its registration's outcome section; one point is
cross-checked by a second method; `make all` is green on the branch; and its finding is entered
in `docs/audits/model_provenance.md`.
