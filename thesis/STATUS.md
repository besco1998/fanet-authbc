# Thesis status — what is written, what was checked, what is still missing

*Created 2026-08-30; rewritten 2026-10-08 after the whole built PDF was audited, and updated
2026-10-09 (findings F63–F71 in `docs/audits/model_provenance.md`). `main.pdf` builds to 119
pages with no errors, no undefined references and no layout warnings. **Read this before showing the PDF to anyone.***

## In one paragraph

Every chapter is written and was read end to end in the built PDF on 2026-10-08. The red
"STATUS" boxes are gone because what they listed is done. **Three red markers remain, and all
three are yours:** the declaration, the statement on generative AI, and the acknowledgements —
with the degree and the department on the title page. What else is open needs a browser (four
papers the publishers will not serve to a script) or the boards switched on.

## Per chapter

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter | written | ⚠️ **degree, department, declaration, AI statement, acknowledgements — only Mohamed** |
| 1 | Introduction | audited | — |
| 2 | Background and Related Work | audited; a general survey and the Remote ID standard added; one aggregate-signature scheme read at source, which corrected a claim (F68) | three older analyses of non-saturated broadcast and three of the four aggregate-signature schemes are not obtained (`OPEN_ITEMS` G23, G24) |
| 3 | System Model and Threat Model | audited | — |
| 4 | Theoretical Framework | audited; two figures and one theorem statement corrected (F64); worked examples for T2 and T4 | — |
| 5 | Implementation | **expanded**: package figure, one frame byte by byte, receiver outcomes, test layers | — |
| 6 | Experimental Methodology | **expanded**: generator, how a capacity is read, timings, energy rig, uncertainty | the energy sensor's calibration (G22) — a bench step |
| 7 | Results I | audited | — |
| 8 | Results II | audited; RQ3 now has its numbers; prior work for the derivation credited (F65) | lean codec timing and receiver CPU on the board (bench session) |
| 9 | Model validation and hardware | audited; the contention experiment is registered with its predictions | **running it** (G4): the boards must be on and reachable |
| 10 | Low-rate regime | audited; **mobility subsection added** | — |
| 11 | Reproducibility | **expanded**: how citations are checked, where the chapter sits | Kurkowski et al. 2005 is not held and is not cited |
| 12 | Conclusions | audited; **research questions answered one by one**; four stale items corrected | — |
| A | Reproducing the results | new | — |
| B | Predictions registered before their data | fourteen, by commit; one not yet run | ⚠️ **merge pull requests with a merge commit** — squashing would erase the commits this table cites |
| C | Results that were corrected | new 2026-10-09: the three superseded figures and the old envelope table, moved out of the results chapters | — |

## What a supervisor may still say, and why it is not fixed

* **"The contention result is simulated."** True, and stated first among the limitations. It
  needs radios (G4).
* **"Fifty-four references is few."** Every one was read at source. Raising the number means
  reading more, not listing more (G23, G24).
* **"Has the capacity mechanism been seen on a radio?"** Not yet. The experiment that would
  show it is registered and ready (ch. 9, Appendix B); it needs the boards.
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
