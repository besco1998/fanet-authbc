# Thesis status — what is written, what was checked, what is still missing

*Created 2026-08-30; rewritten 2026-10-08 after the whole built PDF was audited, and updated
three times on 2026-10-09 (findings F63–F83 in `docs/audits/model_provenance.md`). `main.pdf` builds
to 128 pages with no errors, no undefined references and no layout warnings. **Read this before showing the PDF to anyone.***

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

⚠️ **On the afternoon of 2026-10-09 a review of the paper changed seven places of the thesis,
and you have not read them either** (F80–F83). In reading order: ch. 2 — three new passages
(erasure-coded stream authentication, ADS-B, a subsection on frame aggregation); ch. 3 — the
remark *What the receiver keeps, and what it did not*; ch. 4 — the last paragraph of the
freshness remark (the bound is a peak age); ch. 8 — a second certificate column with its
remark, the receiver's time after it keeps frames, and the table of three other batch sizes;
ch. 10 — a fifth scope condition; ch. 12 — the limitations; Appendix B — two more
registrations.

## Per chapter

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter | written | ⚠️ **degree, department, declaration, AI statement, acknowledgements — only Mohamed** |
| 1 | Introduction | audited | — |
| 2 | Background and Related Work | **three passages added 2026-10-09 (F83)**: erasure-coded stream authentication, ADS-B, frame aggregation — each source read first; audited before that; a general survey and the Remote ID standard added; all four aggregate-signature schemes and the 2009 analysis of non-saturated broadcast obtained and read (F68, F72) | two older analyses of non-saturated broadcast are closed access and not held (`OPEN_ITEMS` G23) |
| 3 | System Model and Threat Model | audited; **remark added 2026-10-09 (F80, F81): the receiver did not keep what it verified, and now does** | — |
| 4 | Theoretical Framework | audited; the freshness bound named a peak age (F83); two figures and one theorem statement corrected (F64); worked examples for T2 and T4 | — |
| 5 | Implementation | **expanded**: package figure, one frame byte by byte, receiver outcomes, test layers | — |
| 6 | Experimental Methodology | **expanded**: generator, how a capacity is read, timings, energy rig, uncertainty; says since 2026-10-09 that the energy table tests times and not power, describes the rig check, and reports the second-sensor control and the re-metered JSON row | the energy sensor's calibration (G22) |
| 7 | Results I | audited | — |
| 8 | Results II | audited; RQ3 now has its numbers; prior work for the derivation credited (F65); **the lean codec timed and metered on the board, Ed25519 batch verification measured (F77, F79)** — the prototype's receiver serves 57 nodes per core; the lean sender costs 2.7 times the first format's energy | — |
| 9 | Model validation and hardware | **hardware section rewritten 2026-10-09**: link loss; a withdrawn airtime figure (F74); one radio's frame spacing; two radios at a set load (F73, F75); two saturated radios (F76) | three to five radios (G4); the cause of the shortfall below saturation (G27) |
| 10 | Low-rate regime | audited; **mobility subsection added**; **a fifth scope condition (F80, F81): three of the eight exclusions are this format's** | — |
| 11 | Reproducibility | **expanded**: how citations are checked, where the chapter sits; Kurkowski et al. 2005 now held and cited directly | — |
| 12 | Conclusions | audited; **research questions answered one by one**; four stale items corrected | — |
| A | Reproducing the results | new | — |
| B | Predictions registered before their data | twenty, by commit; seven failed in whole or in part; one run with two boards of the five it covers | ⚠️ **merge pull requests with a merge commit** — squashing would erase the commits this table cites |
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
* **"Sixty-five references is few."** Every one was read at source. Raising the number means
  reading more, not listing more (G23).
* **"Chapter 11 is unusual."** It is deliberate. It now says where it sits in the literature.
* **"Most of your capacity gain is frame aggregation."** About three fifths, yes. Ch. 2 and
  ch. 8 say so, cite the 802.11n mechanism, and say why a broadcast sender cannot use it.
* **"Your exclusion count depends on your own header."** For three of the eight, yes; five
  hold in any format. Ch. 10 has it as a fifth condition and the abstract gives the split.
* **"You only simulated one batch size."** One and four for every result; two, three and eight
  for the capacity rule, predicted before they were run, all six predictions held (ch. 8).
* **"Does a receiver keep anything a third party could check?"** Since 2026-10-09, the frames.
  Before that, no — and the thesis says so in ch. 3.

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
