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

## Outcome — added 2026-11-28, after the runs; nothing above this line was changed

* **The runs:** `ns3/run_uj_ud2.py uj`, through the audit twin (gate 9/9 identical on 2026-11-28),
  1 715 runs (`results/raw/uj_*`). Every measured node count has seeds 1–30; every 30-seed mean
  curve crosses 0.95 once.
* **Scored** with `python analysis/uj.py --score` → `results/raw/uj_scored.csv`.

| cell | source | ns-3 crossing (95 % interval) | root of (G5) | law (G9) | S | A | per-seed crossings: n, min–max (σ) |
|---|---|---|---|---|---|---|---|
| JA230F40 | FZ, frozen | 32.64 (30.85–33.77) | −0.07 % | +1.13 % | reported | reported | 28, 29.9–34.8 (1.47) |
| JA230F40 | DR, 20 ppm | 33.91 (31.64–34.43) | −3.81 % | −2.66 % | **held** | **held** | 30, 30.4–35.6 (1.61) |
| JA230F40 | J01, 0.1 ms | 34.75 (31.81–35.55) | −6.14 % | −5.02 % | **held** | failed (conservative) | 28, 31.2–35.4 (1.46) |
| JA230F40 | J1, 1 ms | 34.69 (33.72–35.47) | −5.98 % | −4.86 % | **held** | failed (conservative) | 29, 32.2–37.4 (1.19) |
| JA230F40 | DS, designated | 34.10 (33.91–34.27) | −4.36 % | −3.21 % | **held** | **held** | 30, 32.9–35.1 (0.54) |
| JA260F30 | FZ, frozen | 40.09 (39.20–41.28) | −0.30 % | +0.70 % | reported | reported | 27, 36.2–41.0 (1.47) |
| JA260F30 | DS, designated | 41.88 (41.69–42.09) | −4.56 % | −3.61 % | **held** | **held** | 30, 40.6–42.5 (0.46) |

* **S, the safe side: held at all five non-frozen cells** (the root 3.8–6.1 % below ns-3).
* **A, the ±5 % band: held at three of five.** The two misses, J01 and J1, are conservative (the
  root 6.1 and 6.0 % below ns-3); by the registration they change no scope sentence.
* **Frozen phases lowered ns-3's capacity by 4.3 % in both cells** (32.64 against 34.10; 40.09
  against 41.88), to the root but not past it: −0.07 and −0.30 %. The law, which lies above the
  root, was optimistic there (+1.13, +0.70 %).

### The outcomes table: its last row applies

The frozen source came out on the safe side, by 0.07 and 0.30 %, in both cells. The registration
fixed that case as **"stop and ask Mohamed"**, so no scope sentence is chosen here. His answer is
recorded in `docs/DECISIONS.md` and below.

### The independent check

A separate script, sharing no project code, read the seven runs files and recomputed every
crossing: all seven equal the scored ones to three decimals.

### My expectations, against the outcome

* **"S holds at all five non-frozen cells, with the root 2–5 % below ns-3":** S held. The root
  lay 3.8–6.1 % below, a little lower than expected.
* **"A holds at most of them":** three of five, with two conservative misses.
* **"The frozen source: below the jittered sources' crossing, and possibly above the root":**
  below, yes, by 4.3 % in both cells; above the root, no.
* **"Its per-seed crossings spread wider than any other source's":** wrong. Drift (σ 1.61) and the
  small jitters (σ 1.46 and 1.19) spread as widely as frozen phases (σ 1.47). Only the designated
  source (σ 0.46–0.54) is narrow. Within a 20 s run, 20 ppm or a 0.1–1 ms jitter does not
  re-mix the phases fully, although the means stay on the safe side.

### Mohamed's answer (2026-11-28, the same evening)

**Frozen phases are excluded from the safe-side claim.** The scope sentence the report states:
"The root of (G5) is on the safe side for timers with jitter or clock drift (5 of 5 new cells, 68
of 68 stored). Frozen phases (strictly periodic senders with identical clocks) lower ns-3's
capacity by about 4 %, to the root or past it (stored cells C and D), so they are outside the
claim."
