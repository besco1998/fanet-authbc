# Thesis status — what is drafted, what is not

*Created 2026-08-30. **This file is the honest inventory.** `main.pdf` currently builds to 60 pages
with 0 errors and 0 undefined references, and that number will tempt you to think the thesis is
further along than it is. It is not. Read this before showing the PDF to anyone.*

## The one-line summary

**A complete, building skeleton with the technical core drafted from existing material.** The
chapters that could be written from what the project already knows are written. The chapters that
need new *reading* are outlined with their sources named. No chapter is submission-ready.

## Per-chapter state

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter, abstract | **drafted** | ⚠️ degree, department, declaration, generative-AI statement, acknowledgements are placeholders **only Mohamed can fill** |
| 1 | Introduction | **drafted** | fine as a draft; revisit after ch.2 |
| 2 | Background and Related Work | ⚠️ **OUTLINED** | **the largest gap.** FANET vs MANET/VANET; the telemetry workload; CLAS as external comparator; ECQV; LoRaWAN regional parameters as regulation. Sources named in-chapter |
| 3 | System Model and Threat Model | **drafted** | add a frame-layout figure and one worked byte-level example |
| 4 | Theoretical Framework | **drafted** | proofs complete for T1–T3, T6; T5 stated honestly as empirical separability |
| 5 | Implementation | **drafted** | add a module-dependency figure |
| 6 | Experimental Methodology | **drafted** | add the pre-registration table (material exists in `docs/`); energy uncertainty budget |
| 7 | Results I — bytes, placement, loss | **drafted** | — |
| 8 | Results II — co-design, envelope | **drafted** | — |
| 9 | Model validation and hardware | **drafted** | — |
| 10 | Low-rate regime, exclusion bound | **drafted** | — |
| 11 | Reproducibility and defects | **drafted** | port the credibility-literature comparison from `paper/methods.tex` |
| 12 | Conclusions, limitations, future work | **drafted** | — |

## What a 60-page skeleton is not

A thesis in this field typically runs 80–150 pages. The gap is not padding — it is:

* **Chapter 2**, which is genuinely short and must roughly triple.
* **Figures.** Nine exist and are reused from the paper. A thesis wants more, and wants some drawn
  for explanation rather than for results — a frame layout, the placement taxonomy, the regime map.
* **Worked examples.** The paper compresses; a thesis should expand. Every theorem in ch.4 deserves
  a concrete instantiation the reader can follow arithmetically.
* **Depth in ch.5–6.** The implementation and methodology chapters are currently summaries of
  `docs/05` and `docs/04` rather than thesis-depth treatments.

## What is genuinely done and should not be redone

Every **number, table and claim** in chapters 7–10 is drawn from a committed artifact and is
guarded by a test that fails if it drifts. The self-corrections in ch.9–11 (the pre-registration
power flaw, the header finding, the criterion identity) are written and are, in this author's view,
the chapters most likely to distinguish the thesis from an ordinary one. Do not soften them.

## Reference count

46 rendered, and it stops there **deliberately**: 46 is every source held and *read*. A thesis of
this scope would normally carry more. Reaching a higher count requires find → download → **read** →
cite. ⚠️ Padding the list would be the same defect the project's audit spent its time removing.

## Build

```bash
make thesis        # → thesis/main.pdf
```

⚠️ The `\needswork{...}` macro renders its argument in red. Every one of them is a real outstanding
item. **Before any submission, `grep -c needswork thesis/*.tex` must return 0.**
