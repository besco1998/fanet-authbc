# Thesis status — what is written, what was checked, what is still missing

*Created 2026-08-30; rewritten 2026-10-08 after the whole built PDF was audited, and updated
twice on 2026-10-09 (findings F63–F77 in `docs/audits/model_provenance.md`). `main.pdf` builds
to 125 pages with no errors, no undefined references and no layout warnings. **Read this before showing the PDF to anyone.***

## In one paragraph

Every chapter is written and was read end to end in the built PDF on 2026-10-08. The red
"STATUS" boxes are gone because what they listed is done. **Three red markers remain, and all
three are yours:** the declaration, the statement on generative AI, and the acknowledgements —
with the degree and the department on the title page.

⚠️ **Chapter 9's hardware section was rewritten on the night of 2026-10-09 and has not been read
by you.** It now reports contention measured between two radios — one registered prediction
that held, one that failed at one load of three, a follow-up in which all four failed —
and withdraws a figure ("airtime within 0.36 %") that earlier versions and the paper carried.
Read the section *Hardware* of chapter 9 before the supervisor does.

## Per chapter

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter | written | ⚠️ **degree, department, declaration, AI statement, acknowledgements — only Mohamed** |
| 1 | Introduction | audited | — |
| 2 | Background and Related Work | audited; a general survey and the Remote ID standard added; all four aggregate-signature schemes and the 2009 analysis of non-saturated broadcast obtained and read (F68, F72) | two older analyses of non-saturated broadcast are closed access and not held (`OPEN_ITEMS` G23) |
| 3 | System Model and Threat Model | audited | — |
| 4 | Theoretical Framework | audited; two figures and one theorem statement corrected (F64); worked examples for T2 and T4 | — |
| 5 | Implementation | **expanded**: package figure, one frame byte by byte, receiver outcomes, test layers | — |
| 6 | Experimental Methodology | **expanded**: generator, how a capacity is read, timings, energy rig, uncertainty; says since 2026-10-09 that the energy table tests times and not power, describes the rig check, and reports the second-sensor control and the re-metered JSON row | the energy sensor's calibration (G22) |
| 7 | Results I | audited | — |
| 8 | Results II | audited; RQ3 now has its numbers; prior work for the derivation credited (F65); **the lean codec timed and metered on the board, Ed25519 batch verification measured (F77, F79)** — the prototype's receiver serves 57 nodes per core; the lean sender costs 2.7 times the first format's energy | — |
| 9 | Model validation and hardware | **hardware section rewritten 2026-10-09**: link loss; a withdrawn airtime figure (F74); one radio's frame spacing; two radios at a set load (F73, F75); two saturated radios (F76) | three to five radios (G4); the cause of the shortfall below saturation (G27) |
| 10 | Low-rate regime | audited; **mobility subsection added** | — |
| 11 | Reproducibility | **expanded**: how citations are checked, where the chapter sits; Kurkowski et al. 2005 now held and cited directly | — |
| 12 | Conclusions | audited; **research questions answered one by one**; four stale items corrected | — |
| A | Reproducing the results | new | — |
| B | Predictions registered before their data | eighteen, by commit; seven failed in whole or in part; one run with two boards of the five it covers | ⚠️ **merge pull requests with a merge commit** — squashing would erase the commits this table cites |
| C | Results that were corrected | new 2026-10-09: the three superseded figures and the old envelope table, moved out of the results chapters | — |

## What a supervisor may still say, and why it is not fixed

* **"The capacities are simulated."** True, and stated first among the limitations. No capacity
  was measured: two radios cannot reach one.
* **"Has the capacity mechanism been seen on a radio?"** Between two saturated radios, yes,
  within 6 % of the standard's rule, from a prediction registered first. Below saturation the
  registered prediction failed at the highest load, and the thesis says so and says what is
  not explained (ch. 9).
* **"Your own hardware check of August was wrong."** Yes. It is withdrawn in a remark in ch. 9
  that says how two errors cancelled; `results/hw/channel/RESULTS.md` keeps the old text under
  a correction.
* **"Your prototype cannot keep up with 124 nodes on one core."** True: 57. Ch. 8 gives the
  number and says the ceilings are for a compiled receiver.
* **"Is your energy table of the design you report?"** Since 2026-10-09, yes: the lean sender
  is metered (155.4 µJ per record) on a second board and sensor, with a control that ties that
  rig to July's within 2.2 %. It costs 2.7 times the first format's energy per record, and
  ch. 8 says so in bold.
* **"Was the meter calibrated?"** No. Two sensors agree with each other within 2.2 %; neither
  has been checked against a known load (G22). Ch. 6 says so.
* **"Is your meter-against-model comparison circular?"** In its power, yes, and ch. 6 says so:
  the model's power is the median of the metered runs. What the table tests is the times.
* **"Sixty-one references is few."** Every one was read at source. Raising the number means
  reading more, not listing more (G23).
* **"Chapter 11 is unusual."** It is deliberate. It now says where it sits in the literature.

## Rules that keep it true

* **No typed results.** Numbers are macros from `numbers.tex`, which `make thesis` copies from
  `paper/numbers.tex`, which `analysis/paper_numbers.py` writes from `results/`. What *is*
  typed is held to its artifact by `tests/test_thesis_matches_artifacts.py`.
* **After changing a results chapter, re-read chapters 1, 11 and 12.** Four statements there had
  gone stale because a correction stopped at the chapter it was made in (F64).
* **`thesis/tab_worked_frame.tex` is generated** (`analysis/worked_frame.py`); a test compares.
* **Before any submission, `grep -c '\\needswork{' thesis/*.tex` must total 0.**

## Build

```bash
make thesis        # → thesis/main.pdf
```
