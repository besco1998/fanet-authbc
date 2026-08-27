# Document index — where everything lives

*There was no index until 2026-07-29, and its absence is a large part of why the same number could
sit at three different values in three files. Start here.*

## Read in this order

| # | Document | What it answers |
|---|---|---|
| 0 | **[`NEXT_STEPS.md`](NEXT_STEPS.md)** | **What to do next** — the prioritised work plan, the strategy decision, and decisions not to re-litigate. Start here if you are resuming |
| 1 | [`../CLAUDE.md`](../CLAUDE.md) | Standing policy, the Eight Laws, and the **current status board** — always current, read first |
| 2 | [`00_PROJECT_CHARTER.md`](00_PROJECT_CHARTER.md) | Scope, research questions, contributions, what is explicitly out of scope |
| 3 | [`01_SYSTEM_MODEL_ARCHITECTURE.md`](01_SYSTEM_MODEL_ARCHITECTURE.md) | System model, traffic, security model, and the **notation table** (single source of truth for symbols) |
| 4 | [`02_MATHEMATICAL_FOUNDATIONS.md`](02_MATHEMATICAL_FOUNDATIONS.md) | Theorems **T1–T7**, the channel and energy models, the operating region |
| 5 | [`04_EVALUATION_PLAN.md`](04_EVALUATION_PLAN.md) | Experiments **E1–E8** and the success criterion |
| 6 | **[`05_REPRODUCTION_GUIDE.md`](05_REPRODUCTION_GUIDE.md)** | **How to set up and run everything on a new machine, and what every source file does.** Start here if you want to *run* rather than read |

## Before you quote any number

| Document | Why |
|---|---|
| **[`TRADEOFFS.md`](TRADEOFFS.md)** | **Required.** Every decision with what it bought and what it gave up. This is an optimization problem: a configuration reported without its alternatives is a *selection*, not an optimization |
| [`OPEN_ITEMS.md`](OPEN_ITEMS.md) | The single tracked list of everything assumed, deferred, unvalidated or accepted-as-a-limitation |
| [`DECISIONS.md`](DECISIONS.md) | The decision log, with dates and a blast-radius map (which frozen artifacts a decision invalidates) |

## Understanding how we got here

| Document | Contents |
|---|---|
| [`LOGBOOK.md`](LOGBOOK.md) | **Method and trial**, newest first — including the paths that failed and the claims that were retracted. If you are about to try something, check here first |
| [`TECHNICAL_NARRATIVE.md`](TECHNICAL_NARRATIVE.md) | The results told as a story, phase by phase |
| [`audits/model_provenance.md`](audits/model_provenance.md) | **The findings register: F1–F42**, each with evidence. **Retractions are kept visible** — T7, F15, F18, and the Direction C literature claim (2026-08-08) |
| [`audits/p0.md` … `p7.md`](audits/) | Per-phase audits, contemporaneous |
| [`audits/scientific_implementation_audit.md`](audits/scientific_implementation_audit.md) | The 2026-08 scientific-implementation, idea/framing and full-paper audits (S1–S10, I1–I4, P1–P2) |

## Reference

| Document | Contents |
|---|---|
| [`06_AGENT_KNOWLEDGE_BASE.md`](06_AGENT_KNOWLEDGE_BASE.md) | Tooling facts: NS-3, crypto libraries, timing methodology, failure-report format |
| [`LICENSE`](../LICENSE) | **All rights reserved.** Vendored NS-3 and the LoRaWAN module remain GPLv2 and are not redistributed |
| [`../ns3/README.md`](../ns3/README.md) | NS-3 build (⚠️ **`-j 3` under `nohup`** — the default OOMs this host), the LoRaWAN module and its required patch |
| [`../hw/SETUP.md`](../hw/SETUP.md) | Hardware inventory and the tiered measurement campaign |
| **[`literature/`](literature/)** | **Primary sources, with a register stating what role each plays** — `USED` / `VALIDATES` / `PRIOR ART` / `POSITIONING`. 50 PDFs. Read [`literature/README.md`](literature/README.md) before citing anything |
| [`prompts/`](prompts/) | Phase prompts and templates |

## Historical — kept for provenance, **not** current

| Document | Status |
|---|---|
| [`03_IMPLEMENTATION_GUIDE.md`](03_IMPLEMENTATION_GUIDE.md) | HISTORICAL — untouched since 2026-07-03 |
| [`07_PARALLEL_EXECUTION_PLAN.md`](07_PARALLEL_EXECUTION_PLAN.md) | HISTORICAL — D7 resolved to serial execution; the lanes were never used |
| [`status/lane1.md`, `lane2.md`](status/) | HISTORICAL — same reason |
| `../summary/results_summary.tex` | **SUPERSEDED** by `paper/main.tex` + this doc set; carries pre-2026-07-29 numbers |

---

## Where a given fact lives

| Looking for… | Go to |
|---|---|
| a symbol's meaning or default | `01` §2 notation table |
| why H_f is 44 B | `01` §2a (measured, with the sensitivity) |
| a theorem statement | `02`, T1–T7 (**T7 is withdrawn**; **T6 and T2a are applied analysis, not novel** — F16, A6) |
| the operating point and its cost | `02` §7a, and `TRADEOFFS.md` §1 |
| why a number changed | `audits/model_provenance.md` (findings) or `DECISIONS.md` (choices) |
| whether something is still open | `OPEN_ITEMS.md` — nowhere else |
| what a failed attempt looked like | `LOGBOOK.md` |
| whether a source supports or attacks us | `literature/README.md` — each entry states its role |
| why LoRa `N_max` is 3 and not 1000 | `literature/README.md` §5 and **F19** — 1 channel / 1 demodulator / 1 SF, so it is a **worst case**; we are ≈2.1× *more pessimistic* than the published model (**F18 said the opposite and is retracted**). ⚠️ Quote it as **3, 95 % CI [2, 3]**; the per-realisation reading gives **1** (S3) |
| how to re-run an experiment | `05_REPRODUCTION_GUIDE.md` §1–4, or `make help` |
| what a given source file does | `05_REPRODUCTION_GUIDE.md` §5 |
| why the build keeps killing WSL | `05_REPRODUCTION_GUIDE.md` §8 (it is the OOM killer) |

## Rules that keep this set honest

1. **One home per fact.** A number lives in exactly one document; everything else points at it.
   Most drift found in the 2026-07-29 audit was the same value maintained in two places.
2. **Retractions stay visible.** Struck through, with the reason. Deleting a withdrawn claim hides
   the error instead of correcting it.
3. **Open items live in `OPEN_ITEMS.md` only.** Prose elsewhere saying "TODO" or "pending" is a bug.
4. **Run the test suite before propagating a finding.** Both 2026-07-29 retractions were published
   into several documents before the suite refuted them.
