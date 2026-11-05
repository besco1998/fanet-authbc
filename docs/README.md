# Documentation index — every document, what it is for, and where the old ones went

*Rewritten 2026-11-01, when the documents were tidied: about 70 files became about 25, and nothing
was lost. Historical documents were merged, verbatim, into a few archive files; every registration
moved to `predictions/`. The last section maps every old path to its new place.*

## Start here

| If you want to … | Read |
|---|---|
| **understand the project**: the problem, the theory, every decision and its reason, every experiment | **[`PROJECT_GUIDE.md`](PROJECT_GUIDE.md)** |
| **know where the work is and what to do next** | **[`OPEN_ITEMS.md`](OPEN_ITEMS.md) §1** |
| know the agent's standing policy and the current counts | [`../CLAUDE.md`](../CLAUDE.md) (the Eight Laws and the status board) |
| run everything on a new machine | [`05_REPRODUCTION_GUIDE.md`](05_REPRODUCTION_GUIDE.md), or `make help` |

## Every document

### The current state

| Document | What it holds |
|---|---|
| [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) | The whole project in plain language, with every term defined and every number sourced |
| [`OPEN_ITEMS.md`](OPEN_ITEMS.md) | Where the work is and what to do next (§1), what is open (§2), questions for Mohamed (§3), and the full register of every open and closed item since July (§4) |
| [`DECISIONS.md`](DECISIONS.md) | Every decision with its date, the blast-radius map of frozen artifacts, and the **trade-off register** at the end: what each decision bought and what it gave up. **Required reading before quoting any number** |
| [`DEFERRED_PLANS.md`](DEFERRED_PLANS.md) | Work Mohamed deferred (mobility for the LoRa arm, Direction C). Not to be started unprompted |

### The specifications (cited by number in code: `docs/02 T3'`, `docs/01 §4b`, …)

| Document | What it holds |
|---|---|
| [`00_PROJECT_CHARTER.md`](00_PROJECT_CHARTER.md) | Scope, research questions, contributions, non-goals, as chartered on 2026-07-03, with dated restatements |
| [`01_SYSTEM_MODEL_ARCHITECTURE.md`](01_SYSTEM_MODEL_ARCHITECTURE.md) | System model, traffic, security model, the wire formats and the **notation table** (single source of truth for symbols) |
| [`02_MATHEMATICAL_FOUNDATIONS.md`](02_MATHEMATICAL_FOUNDATIONS.md) | Theorems T1–T7 (T7 withdrawn), T3′ and T6′, the channel, contention and energy models |
| [`04_EVALUATION_PLAN.md`](04_EVALUATION_PLAN.md) | The July experiment plan, E1–E8, and the statistical rules |
| [`05_REPRODUCTION_GUIDE.md`](05_REPRODUCTION_GUIDE.md) | How to set up and run everything, and what every source file does |
| [`06_AGENT_KNOWLEDGE_BASE.md`](06_AGENT_KNOWLEDGE_BASE.md) | Tooling facts: WSL, ns-3, crypto libraries, timing method, the failure-report format |

### The record of the work

| Document | What it holds |
|---|---|
| [`LOGBOOK.md`](LOGBOOK.md) | **Method and trials**, newest first, including the paths that failed and the claims that were retracted. Check here before trying something |
| [`audits/model_provenance.md`](audits/model_provenance.md) | **The findings register, F1–F123**, each with its evidence. Retractions stay visible |
| [`audits/AUDIT_HISTORY.md`](audits/AUDIT_HISTORY.md) | Every past audit in date order: the phase audits P0–P7 and E5, the pre-P7b full audit, the scientific-implementation audit and the claim audit of 2026-08-28 |
| [`../predictions/README.md`](../predictions/README.md) | **Every registration** (a prediction committed before its experiment ran), with its commit and outcome. Registrations are never edited |

### The reviewer revision and the paper's history (`revision/`)

| Document | What it holds |
|---|---|
| [`revision/REVISION_PLAN.md`](revision/REVISION_PLAN.md) | The 2026-10-19 plan, A1–A17 and B1–B5 |
| [`revision/STATUS.md`](revision/STATUS.md) | One row per plan item with its outcome, and how the revision was run |
| [`revision/PAPER_CHANGES.md`](revision/PAPER_CHANGES.md) | What changed in the paper and why, item by item, and the readability review of 2026-10-25 |
| [`revision/REVIEW_2026-10-27_FACTS.md`](revision/REVIEW_2026-10-27_FACTS.md) | The sourced answers to the factual items of the 2026-10-27 review |
| [`revision/RESPONSE_TO_REVIEWERS.md`](revision/RESPONSE_TO_REVIEWERS.md) | The point-by-point reply letter (draft) |
| `review 27-10-2026/` | The review of 2026-10-27 and its change log. **Not in git** (Mohamed's choice, open item I6) |

### Sources, templates and history

| Document | What it holds |
|---|---|
| [`literature/README.md`](literature/README.md) | **The source register**: each source with its role (`USED`, `VALIDATES`, `PRIOR ART`, `POSITIONING`); how every citation was verified; the F9 positioning. Read before citing anything |
| [`literature/HELD_LOCALLY.csv`](literature/HELD_LOCALLY.csv) | The sources held on Mohamed's machine but not redistributed, with their SHA-256 |
| [`prompts/T_TEMPLATES.md`](prompts/T_TEMPLATES.md) | The workflow templates the Eight Laws cite: §Validate-Results, §Resume, §Debug, §Audit |
| [`archive/PLANNING_HISTORY.md`](archive/PLANNING_HISTORY.md) | The July plans: the parallel-execution plan, the phase prompts, the lane notes, the CLAS baseline plan |
| [`archive/03_IMPLEMENTATION_GUIDE.md`](archive/03_IMPLEMENTATION_GUIDE.md) | The July implementation guide, kept whole because code cites it as `docs/archive/03 §N` |
| [`archive/NARRATIVES_2026-08.md`](archive/NARRATIVES_2026-08.md) | The August accounts: the plain-language story, the technical narrative, the adversarial self-assessment |
| [`archive/PICKUP_GUIDE_HISTORY.md`](archive/PICKUP_GUIDE_HISTORY.md) | The dated sections of the old pick-up guide, July to October |
| [`archive/results_summary_2026-07/`](archive/results_summary_2026-07/) | The superseded July summary (LaTeX), with pre-2026-07-29 numbers |
| [`direction_c_corpus.json`](direction_c_corpus.json) | Data: the Direction C survey corpus |

### Documents beside the code they describe (outside `docs/`)

| Document | What it holds |
|---|---|
| [`../paper/README.md`](../paper/README.md), [`../paper/SUBMISSION_CHECKLIST.md`](../paper/SUBMISSION_CHECKLIST.md) | How the paper is built (including the Springer template files git does not hold) and what a submission still needs |
| [`../thesis/STATUS.md`](../thesis/STATUS.md) | What each thesis chapter holds and what Mohamed has not yet read |
| [`../hw/SETUP.md`](../hw/SETUP.md), [`../hw/BENCH_SESSION.md`](../hw/BENCH_SESSION.md), [`../hw/RIG.md`](../hw/RIG.md), [`../hw/energy_protocol.md`](../hw/energy_protocol.md), [`../hw/INA219_wiring.md`](../hw/INA219_wiring.md) | The hardware, the energy rig and the bench procedures |
| [`../ns3/README.md`](../ns3/README.md) | Building ns-3 (⚠️ `-j 3` under `nohup`), the LoRaWAN module and its patch |
| [`../results/PROVENANCE.md`](../results/PROVENANCE.md), [`../results/hw/channel/CONTENTION_RESULTS.md`](../results/hw/channel/CONTENTION_RESULTS.md) | How result files record their provenance; the two-radio outcomes |

---

## Where a given fact lives

| Looking for… | Go to |
|---|---|
| a symbol's meaning or default | `01` §2 notation table |
| why H_f is 44 B | `01` §2a (measured, with the sensitivity) |
| a theorem statement | `02`, T1–T7, T3′, T6′ (**T7 is withdrawn**; **T6 and T2a are applied analysis, not novel** — F16, A6; **T3′ and T6′ are the 2026-10 corrections**) |
| the operating point and its cost | `02` §7a, and the trade-off register in `DECISIONS.md`, §1 |
| why a number changed | `audits/model_provenance.md` (findings) or `DECISIONS.md` (choices) |
| whether something is still open | `OPEN_ITEMS.md` — nowhere else |
| what a failed attempt looked like | `LOGBOOK.md` |
| whether a source supports or attacks us | `literature/README.md` — each entry states its role |
| why LoRa `N_max` is 3 and not 1000 | `literature/README.md` §5 and **F19** — 1 channel / 1 demodulator / 1 SF, so it is a **worst case**; we are more pessimistic than the published model above N≈3 (**F18 said the opposite and is retracted**) — ⚠️ but quote the **curve, not a ratio**: it runs 0.91× at N=2 (we are the more *optimistic* model there), 1.07× at N=3, 2.09–2.17× from N=10 up, and the sign change sits in exactly the region where N_max is decided. ⚠️ Quote it as **3, 95 % CI [2, 3]**; the per-realisation reading gives **1** (S3) |
| how to re-run an experiment | `05_REPRODUCTION_GUIDE.md` §1–4, or `make help` |
| a plain-language explanation of anything here | [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) (current); the August account is in `archive/NARRATIVES_2026-08.md` |
| whether a claim will survive review | `PROJECT_GUIDE.md` §11 (limitations); the August adversarial self-assessment, graded claim by claim, is in `archive/NARRATIVES_2026-08.md` |
| whether a number was independently re-derived | the claim audit (2026-08-28) in `audits/AUDIT_HISTORY.md`, and the re-checks in the appendix of `PROJECT_GUIDE.md` |
| why the exclusion is **eight of twelve** data rates (five in any format, three in ours: **F80**, **F81**) | **F47** and `02` T6′ — `results/raw/exclusion_matrix.csv`. Five by the signature alone; three because header + chain link + signature + one self-contained record exceed 115 B. ⚠️ "Three of seven" (**F44**) is **withdrawn**: it charged neither the link nor a record that decodes alone, and `wire_profile.py` is deleted |
| what H_f actually is | **a range, 38–44 B** — `framer.measure_frame_header_bytes` (F43b). ⚠️ 44 B is the end most favourable to T6 |
| whether one U ceiling gives the V ≥ 0.95 capacity | ⚠️ **no** — **F50**. It is invariant to frame size at N = 50 (`../predictions/M4_EXPECTATIONS.md`) and **not** to N: a direct search misses it by up to 23 %. Capacities are simulated per configuration (`02` §6e, `../predictions/NMAX_DIRECT_EXPECTATIONS.md`) |
| what the design is, byte by byte | `01` §4b (the frame-linked wire format, field table), `results/raw/frame_components.csv`, and `PROJECT_GUIDE.md` §6.3 |
| why every frame starts with a key record | `02` T3′ and **F46** — a frame coded against its predecessor is not self-verifiable |
| where the classical stream-signing schemes stand | `02` §6f, `results/raw/stream_baselines.csv`, and (implemented and simulated against the deadline, A10) `results/raw/stream_deadline.csv` |
| **why** the capacities are what they are | `02` §6g and **F58** — two loss mechanisms, nothing fitted; `src/authbc/sim/dcf_unsaturated.py` reproduces every simulated crossing within 1.2 % (`results/raw/dcf_model_vs_ns3.csv`). Its predictions and their outcome: `../predictions/NMAX_DIRECT_EXPECTATIONS.md`, follow-up F5 |
| whether the receiver's CPU binds | **F59**, **F84** and A8 — cryptography alone allows 296 nodes per core; the Python receiver, decoding included, 57 (124 nodes need three cores); the Rust receiver 290 |
| what telemetry costs at 50 Hz, and how regular a real stream is | **F60** — PX4 in software-in-the-loop, `../predictions/PX4_LOGS_EXPECTATIONS.md` (the follow-up and its outcome), `results/raw/px4_sitl_*.csv` |
| whether the two simulated traffic sources differ | **F61** — no: `../predictions/NMAX_DIRECT_EXPECTATIONS.md` follow-up F4 |
| what the 2026-10 revision decided | `DECISIONS.md`, R1–R18, and **"Decided by Mohamed, 2026-10-08"** for every point it had left to him; what is still open, `OPEN_ITEMS.md` |
| what the reviewer revision (2026-10-19) found, and what changed in the paper | per item: `revision/STATUS.md`; registrations and outcomes: `../predictions/README.md`; the changes to the paper (applied 2026-10-24 and after): `revision/PAPER_CHANGES.md`; the reply: `revision/RESPONSE_TO_REVIEWERS.md`; findings **F86–F113** |
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
5. **A registration is never edited.** Its commit, made before the run, is the evidence; outcomes
   are appended below a line.

---

## Where did it go? (paths before 2026-11-01)

Older documents, commit messages and result-file headers still name these paths. Each now lives
here:

| Old path | Now |
|---|---|
| `docs/CONTENTION_HW_EXPECTATIONS.md`, `…_FRAMEBURST_…`, `…_SATURATED_…`, `docs/DR6_EXPECTATIONS.md`, `docs/M4_EXPECTATIONS.md`, `docs/NMAX_DIRECT_EXPECTATIONS.md`, `docs/PX4_LOGS_EXPECTATIONS.md`, `docs/DIRECTION_C_SURVEY_PROTOCOL.md` | `predictions/<same name>` (moved unchanged) |
| `docs/AUTHBC Revision Plan.md` | `docs/revision/REVISION_PLAN.md` |
| `docs/NEXT_STEPS.md` | its current part: `docs/OPEN_ITEMS.md` §1; its dated sections: `docs/archive/PICKUP_GUIDE_HISTORY.md` |
| `docs/TRADEOFFS.md` | `docs/DECISIONS.md`, the trade-off register at its end |
| `docs/THE_STORY.md`, `docs/TECHNICAL_NARRATIVE.md`, `docs/HONEST_ASSESSMENT.md` | `docs/archive/NARRATIVES_2026-08.md` |
| `docs/CLAIM_AUDIT.md`, `docs/audits/p0.md` … `p7.md`, `e5.md`, `full_audit_pre_p7b.md`, `scientific_implementation_audit.md` | `docs/audits/AUDIT_HISTORY.md` |
| `docs/03_IMPLEMENTATION_GUIDE.md` (cited as `docs/03 §N`) | `docs/archive/03_IMPLEMENTATION_GUIDE.md` (cited as `docs/archive/03 §N`) |
| `docs/07_PARALLEL_EXECUTION_PLAN.md` (cited as `docs/07 §N`), `docs/prompts/*` except `T_TEMPLATES.md`, `docs/status/lane1.md`, `lane2.md`, `docs/CLAS_BASELINE_PLAN.md` | `docs/archive/PLANNING_HISTORY.md` |
| `docs/MOBILITY_PLAN.md`, `docs/MOBILITY_SURVEY.md`, `docs/DIRECTION_C_DOWNLOAD_LIST.md` | `docs/DEFERRED_PLANS.md` |
| `docs/revision/EXECUTION_PLAN.md` | `docs/revision/STATUS.md`, "How the revision was run" |
| `docs/revision/PAPER_READABILITY_REVIEW.md` | `docs/revision/PAPER_CHANGES.md`, at its end |
| `docs/literature/A3_CITATION_VERIFICATION.md`, `docs/literature/f9_broadcast_dcf.md` | `docs/literature/README.md`, at its end |
| `summary/` | `docs/archive/results_summary_2026-07/` |
| `docs/failures/README.md`, `docs/status/README.md`, `docs/audits/README.md` | removed: pointer files that held no data ("never used"; folder indexes); this index replaces them |

**Old paths kept on purpose**, because the bytes are evidence: the registrations themselves; the
timed, hash-pinned `src/authbc/ledger/store.py` (cites `docs/03 §3`); the registered model
`src/authbc/sim/dcf_unsaturated.py` (cites `docs/NMAX_DIRECT_EXPECTATIONS.md`); the headers that
generators write into result files; tests that read a registration as it stood at its commit; and
the verbatim copies in `docs/archive/` and `docs/audits/AUDIT_HISTORY.md`.
