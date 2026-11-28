# U-J — is the root of (G5) on the safe side for every real timer? Frozen phases against jitter and drift

*Registered 2026-11-28, before any U-J run; the time is the commit's. Decided by Mohamed on
2026-11-28 (`docs/DECISIONS.md`, "fixing the model report's three open issues", issue 2). Code:
`analysis/uj.py` (`tests/test_uj.py`); cells in `ns3/run_unified.py`, imported from it.*

## Why

The model report (2026-11-27) states that the root of (G5) misses ns-3 only on the safe side. That
holds for the root but not for the law (G9), which has one optimistic miss of +6.4 %. Looking for
the cause before registering:
* **every positive error in the scorecard is a frozen-phase run.** In `unified_model_vs_ns3.csv`
  those are the rows with source `0/0ppm`: strictly periodic senders whose phases never move, so a
  pair that collides once collides in every period (audit A1, `docs/audits/model_provenance.md`).
  * The root's two positive errors are both such runs: +4.02 % (cell C) and +1.97 % (cell D).
  * So is the law's +6.36 % (cell C).
* **With jittered or drifting timers, the root lies below ns-3 in all 68 stored cases,** the worst
  at −1.22 %. The law's largest error there is +2.32 %.

Stating "the safe side holds except for frozen phases" from those rows alone would be fitting the
scope to the answer. U-J tests it on new cells instead.

## The model under test

The root of (G5) and the law (G9) at ε = 0.05, 802.11a at 6 Mb/s, W = 16
(`authbc.models.unified_capacity`, unchanged). The model has no input for the source; its values
are the same for every source of a cell.

## The cells and sources (new)

Two 802.11a cells that no stored CSV holds (`python analysis/uj.py --scan`: 0 rows), with law
airtimes above 2τ0 (196 µs):

| cell | frame | frames/s | sources |
|---|---|---|---|
| JA230F40 | 230 B (380 µs) | 40 | all five |
| JA260F30 | 260 B (420 µs) | 30 | FZ and DS |

**The sources** (the audit twin's options, `ns3/authbc-links-audit.cc`):

| | what | option |
|---|---|---|
| **FZ** | frozen: the default OnOff source, one random start phase per station for the whole run | no `--txJitterMs` |
| **DR** | drift: each station's period stretched by U(−20, +20) ppm, a crystal's tolerance | `--txSkewPpm=20` with `--txJitterMs=0.001` |
| **J01** | each frame moved by U(0, 0.1 ms) from its place on the station's grid | `--txJitterMs=0.1` |
| **J1** | the same, U(0, 1 ms) | `--txJitterMs=1` |
| **DS** | the designated source: each frame at an instant drawn anew in its period | `--txJitterMs` = one period |

* **DR is not pure drift.** The scenario allows a skew only on the jittered source. So DR carries a
  1 µs jitter, the smallest that the option accepts in practice and a quarter of the 4 µs detection
  window.
* **The second cell** runs the two ends only. The campaign is about 1 700 runs (driver:
  `ns3/run_uj_ud2.py uj`).

## Predictions (`python analysis/uj.py --markdown`, generated)

| cell | frame | frames/s | source | T_f (µs) | **root of (G5)** | **law (G9)** |
|---|---|---|---|---|---|---|
| JA230F40FZ | 230 B | 40 | FZ | 380 | **32.62** | **33.01** |
| JA230F40DR | 230 B | 40 | DR | 380 | **32.62** | **33.01** |
| JA230F40J01 | 230 B | 40 | J01 | 380 | **32.62** | **33.01** |
| JA230F40J1 | 230 B | 40 | J1 | 380 | **32.62** | **33.01** |
| JA230F40DS | 230 B | 40 | DS | 380 | **32.62** | **33.01** |
| JA260F30FZ | 260 B | 30 | FZ | 420 | **39.97** | **40.37** |
| JA260F30DS | 260 B | 30 | DS | 420 | **39.97** | **40.37** |

**Scored, for each non-frozen source (DR, J01, J1, and DS in both cells; 5 cells), as two claims:**
* **S, the safe side:** the root of (G5) at or below ns-3's crossing.
* **A, the accuracy:** the root within ±5 % of ns-3's crossing, and the law within ±5 %.
* A cell holds if both hold. S is the claim the report makes; A is the scorecard's band.
* The tolerances are fixed here and are not widened after the runs.

**Reported, not scored:**
* the frozen source FZ in both cells: root and law errors;
* the per-seed spread of every cell: each seed's own crossing, its min, max and σ. Under frozen
  phases A1 found it bimodal.

## Outcomes, fixed before the runs

| result | what the report then states |
|---|---|
| S holds at all five non-frozen cells | "The root of (G5) is on the safe side for any timer with jitter or clock drift; with frozen phases (strictly periodic, identical clocks) it can be optimistic" |
| S fails at DR only | the scope is "timer jitter of at least 0.1 ms"; drift alone is a stated limit |
| S fails at DR and J01, holds at J1 and DS | the scope is "timer jitter of at least 1 ms" |
| any other pattern, or the frozen source on the safe side in both cells | stop and ask Mohamed |

A failure of A without a failure of S (the root more than 5 % below ns-3) is reported as a
conservative miss and changes no scope sentence.

## What is run

* **The scenario:** the audit twin, its default path gated bit-identical to `authbc-links.cc` and
  to the frozen results (`ns3/verify_audit_twin.py`, run on 2026-11-28 before any U-J run).
* **20 simulated seconds,** as every stored scorecard run.
* **The pilot:** 5 seeds (1–5) on seven node counts at ±5 % steps around the cell's root.
* **The measurement:** 30 seeds (1–30) on seven node counts by U-C2's rule, around each cell's
  pilot crossing:
  * the centre is the pilot crossing rounded;
  * the step is max(1, round(2 % of the centre)).
* **The crossing** of the 30-seed mean delivered fraction at 0.95, with its bootstrap 95 % interval
  over seeds (`ns3/run_unified.py --levels 0.95`).
* **If a mean curve does not cross once,** which frozen phases could cause, the cell is reported as
  measured and Mohamed is asked; nothing is re-gridded to make it cross.
* **Scoring:** `analysis/uj.py --score` → `results/raw/uj_scored.csv`. An independent script,
  sharing no project code, recomputes every crossing from the runs files.

## Expectations `[agent]`

* **S holds at all five non-frozen cells, with the root 2–5 % below ns-3.** At the 4 µs scale of
  the detection window, phases unfreeze quickly:
  * a 0.1 ms jitter re-draws every frame's offset over 25 detection windows;
  * with each station's period off by up to 20 ppm, a pair's relative phase moves by 4 µs in
    about 0.1–0.3 s, so 70–200 times in a 20 s run.
* **A holds at most of them.** The 18 stored designated-source rows of the direct search lie
  −2.43 to −4.85 % (root) at 802.11a. A conservative miss below −5 % is possible.
* **The frozen source:** below the jittered sources' crossing in one cell or both, and possibly
  above the root, which would repeat the stored cell C. Its per-seed crossings are spread wider
  than any other source's.

## Disclosure

* **Seen before this registration:**
  * the scorecard rows by source (`unified_model_vs_ns3.csv`): A, C and D at `0/0ppm`, `0.1/0ppm`,
    `1/0ppm`, `0.1/5000ppm` and the designated jitters;
  * audit A1 (frozen phases in LoRaWAN) and the phase-lock diagnostic
    (`ns3/run_phase_lock_diagnostic.py`).
* **Chosen after seeing them:** the sources and the scope sentences. The cells, never simulated,
  are the test.
* **None of U-J's runs has been made.**
