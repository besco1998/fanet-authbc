# Document index — where everything lives

*There was no index until 2026-07-29, and its absence is a large part of why the same number could
sit at three different values in three files. Start here.*

## Read in this order

| # | Document | What it answers |
|---|---|---|
| 0 | **[`NEXT_STEPS.md`](NEXT_STEPS.md)** | **What to do next** — the prioritised work plan, the strategy decision, and decisions not to re-litigate. Start here if you are resuming |
| 1 | [`../CLAUDE.md`](../CLAUDE.md) | Standing policy, the Eight Laws, and the **current status board** — always current, read first |
| 1b | **[`THE_STORY.md`](THE_STORY.md)** | **What we did, in plain language.** The problem, how we thought, the results, the mistakes, the decisions and why. Start here if you want to *understand* the work rather than run or verify it |
| 1c | **[`HONEST_ASSESSMENT.md`](HONEST_ASSESSMENT.md)** | **What the work is actually worth.** Adversarial self-assessment: which claims survive a hostile reviewer, where this sits in the field, what genuinely lacks, and ranked future work. Written to be uncomfortable |
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
| [`audits/model_provenance.md`](audits/model_provenance.md) | **The findings register: F1–F54**, each with evidence. **Retractions are kept visible** — T7, F15, F18, the Direction C literature claim (2026-08-08), and **F44** (withdrawn 2026-10-06 by F47) |
| [`audits/p0.md` … `p7.md`](audits/) | Per-phase audits, contemporaneous |
| **[`CLAIM_AUDIT.md`](CLAIM_AUDIT.md)** | **Every headline number re-derived from first principles and checked against simulation** (F43/F44, 2026-08-28). ⚠️ Nothing was a wrong number; five constants were conventions nobody wrote down, and one of them moved the headline from four excluded EU868 rates to three |
| [`audits/scientific_implementation_audit.md`](audits/scientific_implementation_audit.md) | The 2026-08 scientific-implementation, idea/framing and full-paper audits (S1–S10, I1–I4, P1–P2) |

## Reference

| Document | Contents |
|---|---|
| [`06_AGENT_KNOWLEDGE_BASE.md`](06_AGENT_KNOWLEDGE_BASE.md) | Tooling facts: NS-3, crypto libraries, timing methodology, failure-report format |
| [`LICENSE`](../LICENSE) | **All rights reserved.** Vendored NS-3 and the LoRaWAN module remain GPLv2 and are not redistributed |
| [`../ns3/README.md`](../ns3/README.md) | NS-3 build (⚠️ **`-j 3` under `nohup`** — the default OOMs this host), the LoRaWAN module and its required patch |
| [`../hw/SETUP.md`](../hw/SETUP.md) | Hardware inventory and the tiered measurement campaign |
| **[`literature/`](literature/)** | **Primary sources, with a register stating what role each plays** — `USED` / `VALIDATES` / `PRIOR ART` / `POSITIONING`. 51 PDFs in the repository; 11 more are held but not redistributed (`literature/HELD_LOCALLY.csv`). Read [`literature/README.md`](literature/README.md) before citing anything |
| [`prompts/`](prompts/) | Phase prompts and templates |
| **[`../thesis/`](../thesis/)** | The thesis. ⚠️ **A DRAFT SKELETON** — build with `make thesis`, and read [`../thesis/STATUS.md`](../thesis/STATUS.md) first, which grades every chapter honestly. It builds to about 89 pages with 0 errors, and that number will mislead you: ch. 2 is only partly drafted, and every `\needswork` marker is a real outstanding item (`make thesis` prints the count) |
| **Pre-registrations** | [`DR6_EXPECTATIONS.md`](DR6_EXPECTATIONS.md), [`M4_EXPECTATIONS.md`](M4_EXPECTATIONS.md), [`DIRECTION_C_SURVEY_PROTOCOL.md`](DIRECTION_C_SURVEY_PROTOCOL.md), **[`NMAX_DIRECT_EXPECTATIONS.md`](NMAX_DIRECT_EXPECTATIONS.md)** (the 802.11 capacity search and its three follow-ups — ⚠️ **the first prediction failed; read it before quoting a capacity**), **[`PX4_LOGS_EXPECTATIONS.md`](PX4_LOGS_EXPECTATIONS.md)** (record sizes on real flight logs) — each **committed data-free** so the ordering is checkable in git. ⚠️ F40 forced a pre-registration claim to be withdrawn once because the file had never been committed |

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
| a theorem statement | `02`, T1–T7, T3′, T6′ (**T7 is withdrawn**; **T6 and T2a are applied analysis, not novel** — F16, A6; **T3′ and T6′ are the 2026-10 corrections**) |
| the operating point and its cost | `02` §7a, and `TRADEOFFS.md` §1 |
| why a number changed | `audits/model_provenance.md` (findings) or `DECISIONS.md` (choices) |
| whether something is still open | `OPEN_ITEMS.md` — nowhere else |
| what a failed attempt looked like | `LOGBOOK.md` |
| whether a source supports or attacks us | `literature/README.md` — each entry states its role |
| why LoRa `N_max` is 3 and not 1000 | `literature/README.md` §5 and **F19** — 1 channel / 1 demodulator / 1 SF, so it is a **worst case**; we are more pessimistic than the published model above N≈3 (**F18 said the opposite and is retracted**) — ⚠️ but quote the **curve, not a ratio**: it runs 0.91× at N=2 (we are the more *optimistic* model there), 1.07× at N=3, 2.09–2.17× from N=10 up, and the sign change sits in exactly the region where N_max is decided. ⚠️ Quote it as **3, 95 % CI [2, 3]**; the per-realisation reading gives **1** (S3) |
| how to re-run an experiment | `05_REPRODUCTION_GUIDE.md` §1–4, or `make help` |
| a plain-language explanation of anything here | [`THE_STORY.md`](THE_STORY.md) |
| whether a claim will survive review | [`HONEST_ASSESSMENT.md`](HONEST_ASSESSMENT.md) — graded claim by claim |
| whether a number was independently re-derived | [`CLAIM_AUDIT.md`](CLAIM_AUDIT.md) |
| why the exclusion is **eight of twelve** data rates | **F47** and `02` T6′ — `results/raw/exclusion_matrix.csv`. Five by the signature alone; three because header + chain link + signature + one self-contained record exceed 115 B. ⚠️ "Three of seven" (**F44**) is **withdrawn**: it charged neither the link nor a record that decodes alone, and `wire_profile.py` is deleted |
| what H_f actually is | **a range, 38–44 B** — `framer.measure_frame_header_bytes` (F43b). ⚠️ 44 B is the end most favourable to T6 |
| whether one U ceiling gives the V ≥ 0.95 capacity | ⚠️ **no** — **F50**. It is invariant to frame size at N = 50 (`M4_EXPECTATIONS.md`) and **not** to N: a direct search misses it by up to 23 %. Capacities are simulated per configuration (`02` §6e, `NMAX_DIRECT_EXPECTATIONS.md`) |
| what the design is, byte by byte | `01` §4b (the lean wire format, field table) and `results/raw/frame_components.csv` — every lean size is an emitted frame |
| why every frame starts with a keyframe | `02` T3′ and **F46** — a frame coded against its predecessor is not self-verifiable |
| where the classical stream-signing schemes stand | `02` §6f, `results/raw/stream_baselines.csv` (**a model, not an implementation**) |
| what the 2026-10 revision decided | `DECISIONS.md`, R1–R18; what it left open, `OPEN_ITEMS.md` §G |
| where a number in the paper comes from | `paper/numbers.tex`, written by `analysis/paper_numbers.py` from `results/` — the paper has **no typed results** |
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
