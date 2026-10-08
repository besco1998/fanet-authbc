# Thesis status — what is drafted, what is not

*Created 2026-08-30; **updated 2026-10-08** after the revision that followed the supervisor's
review and the work Mohamed chose after it. **This file is the honest inventory.** `main.pdf` builds to about 100 pages with 0 errors
and 0 undefined references, and that number will tempt you to think the thesis is further along
than it is. It is not. Read this before showing the PDF to anyone.*

## What changed in October 2026

An external review of the paper showed that the headline design had never been built as a frame.
It was built, and the chapters that reported it were corrected — not appended to:

| ch | what changed |
|---|---|
| front | abstract rewritten on the built design; title is the August one less "Hardware Validation" |
| 2 | **new section** on per-message practice, stream signing and hash-linked records; the CLAS comparison written; the false "every citation was checked against Crossref" claim removed |
| 3 | the full threat model; the two frame formats, field by field; the frame drawn to scale |
| 4 | **Theorem T3′** (a frame coded against its predecessor is not self-verifiable); the exclusion theorem restated with four graded verdicts |
| 6 | experiments E9–E17 in the matrix |
| 7 | loss with the decoder in the loop, including loss that grows with frame length; record sizes on real flight logs |
| 8 | **rewritten**: the design ladder, receiver CPU, the classical stream-signing schemes, capacity by direct search, the airtime rule and its held-out test, how the traffic source was chosen |
| 9 | the invariance assumption tested and failed |
| 10 | **rewritten**: the exclusion with its history (stated wrongly twice), scope and relaxations; the low-rate batch at its own record spacing |
| 11 | five errors that survived two audits; defect classes C7–C9 |
| 12 | conclusions and limitations brought into line |

⚠️ **The corrected results are not typed.** They are macros from `numbers.tex`, which
`make thesis` copies from `paper/numbers.tex`, which `analysis/paper_numbers.py` writes from
`results/`. `tests/test_thesis_matches_artifacts.py` holds what is still typed (frozen LoRa
figures, the stage-1 table) against its artifacts.

## The one-line summary

**A complete, building skeleton with the technical core drafted from existing material.** The
chapters that could be written from what the project already knows are written. The chapters that
need new *reading* are outlined with their sources named. No chapter is submission-ready.

## Per-chapter state

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter, abstract | **drafted** | ⚠️ degree, department, declaration, generative-AI statement, acknowledgements are placeholders **only Mohamed can fill** |
| 1 | Introduction | **drafted** | fine as a draft; revisit after ch.2 |
| 2 | Background and Related Work | **DRAFTED 2026-10-08** from sources that are held and read | FANETs and the telemetry workload read at source (PX4, ArduPilot, 3GPP); how such networks are evaluated; what a hash chain gives and what a signature gives; certificates, explicit and implicit; the rules that bound the LoRa arm. **Two gaps of reading remain and are marked in the chapter**: no general FANET survey is held, and four of the five aggregate-signature schemes are known only through one paper's table |
| 3 | System Model and Threat Model | **drafted** | the frame-layout figure is in (2026-10); still wants one worked byte-level example |
| 4 | Theoretical Framework | **drafted** | proofs complete for T1–T3, T6; T5 stated honestly as empirical separability |
| 5 | Implementation | **drafted** | add a module-dependency figure |
| 6 | Experimental Methodology | **drafted** | add the pre-registration table (material exists in `docs/`); energy uncertainty budget |
| 7 | Results I — bytes, placement, loss | **drafted** | — |
| 8 | Results II — co-design, envelope | **drafted** | — |
| 9 | Model validation and hardware | **drafted** | — |
| 10 | Low-rate regime, exclusion bound | **drafted** | — |
| 11 | Reproducibility and defects | **drafted** | port the credibility-literature comparison from `paper/methods.tex`. ⚠️ One source that comparison needs, Kurkowski et al. 2005, is **not held** (`docs/OPEN_ITEMS.md` G8) — obtain and read it before citing it in the thesis |
| 12 | Conclusions, limitations, future work | **drafted** | — |

## What a 99-page draft is not

A thesis in this field typically runs 80–150 pages. The gap is not padding — it is:

* **Chapter 2**, drafted in October 2026 but from the sources held: it still wants a general FANET
  survey and the aggregate-signature schemes read at source.
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

45 rendered in the thesis (the shared bibliography has 59 entries; the thesis cites the ones it
uses), and it stops there **deliberately**: every one is a source held and *read*. A thesis of
this scope would normally carry more. Reaching a higher count requires find → download → **read** →
cite. ⚠️ Padding the list would be the same defect the project's audit spent its time removing.

## Build

```bash
make thesis        # → thesis/main.pdf
```

⚠️ The `\needswork{...}` macro renders its argument in red. Every one of them is a real outstanding
item. **Before any submission, `grep -c needswork thesis/*.tex` must return 0.**
