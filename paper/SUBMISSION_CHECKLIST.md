# Submission checklist — `main.tex`

*Venue-agnostic. Everything that does not depend on the venue is done; the rest is listed with
what changes per venue. Written 2026-08-08; **rewritten in part 2026-10-06** after the paper was
revised in answer to an external review — the sections marked ⚠️ SUPERSEDED describe the paper as
it was and are kept only so the change is visible.*

---

## ⚠️ BLOCKERS — only Mohamed can clear these

| # | item | what is needed |
|---|---|---|
| 1 | **Affiliation** | `main.tex` carries `[AFFILIATION -- TO BE COMPLETED]`. Needs department, institution, city, country. |
| 2 | **ORCID** | Required by Elsevier and MDPI, optional for IEEE. Register at orcid.org if you do not have one. |
| 3 | **Funding statement** | If the work was funded, every venue requires the grant number. If unfunded, say so explicitly — silence is not accepted. |
| 4 | **Supervisor / co-authors** | **Decided 2026-10-08: single author; the supervisor is thanked.** ⚠️ `main.tex` carries `[SUPERVISOR -- TO BE COMPLETED]` in the acknowledgement: the name is needed. |
| 5 | **Two citations** | **Both settled** (2026-10-07 and 2026-10-08): one read and cited, one read and not needed. See below. |

### The two citations that had been open

| paper | status |
|---|---|
| Rajasekaran, Maria, Al-Turjman, Altrjman & Mostarda, *Anonymous Mutual and Batch Authentication with Location Privacy of UAV in FANET*, Drones 6(1):14, 2022 · `10.3390/drones6010014` | **DONE 2026-10-07.** Held (CC BY, in `docs/literature/`), read in full, checked against Crossref (five authors, not the four listed here before), cited in the related work of the paper and the thesis (`docs/audits/model_provenance.md` F57). |
| Al Majmaie, Ghajari, Bhatta, Ibrahem & Amsaad, *SSDBFAN: Scalable and Secure Cluster-Based Data Aggregation with Blockchain for FANETs*, Sensors 26(9):2585, 2026 · `10.3390/s26092585` | **DONE 2026-10-08: read, and not cited.** It aggregates *data* at cluster heads and gives no per-message byte budget; nothing in it bears on this paper (`docs/literature/README.md`). |

⚠️ Per the project's own rule, a source is not cited unless it is held and read.

---

## ⚠️ NEW BLOCKERS since the 2026-10 revision — Mohamed's decisions

| # | item | what is needed |
|---|---|---|
| 6 | **Title** | **Decided 2026-10-08: kept.** |
| 7 | **What "AUTHBC" stands for** | **Decided 2026-10-08: kept** — "authenticated telemetry for a blockchain-style, hash-chained ledger". |
| 8 | **Venue and page target** | **Decided 2026-10-08: a networking journal without page charges, after contention has been measured on radios** (`docs/OPEN_ITEMS.md` G4). The class changes from `conference` then; the journal is chosen then. |
| 9 | **One chain link per frame on 802.11** | **Decided 2026-10-08: confirmed.** |
| 10 | **The supervisor's sign-off on the revision** | The point-by-point response stays outside this repository (decided 2026-10-08) and is sent after the bench session. |

## DONE in the 2026-10 revision

- [x] **The design is built**: a frame format with a sender and a receiver; the design and its
      baseline are emitted frames, and every size that is a sum of measured parts is marked
- [x] **No typed results**: every number is a macro generated from `results/`; a test fails if
      one is typed, stale or unused
- [x] **Every bibliography entry compared with its registry record** by a script
      (`make verify-citations`); two wrong author lists corrected
- [x] **Threat model, protocol description, field-by-field byte table, tamper census**
- [x] **Related work** on per-message authentication, stream signing, aggregate signatures and
      hash-linked records, with the stream-signing schemes placed in a table
- [x] **Confidence intervals on every simulated capacity**, from a direct search per configuration
- [x] **Limitations section** naming what is simulated, modelled or synthetic
- [x] Declarations: data and code availability, competing interests, use of generative AI

## DONE — venue-independent (as of 2026-08; ⚠️ SUPERSEDED where it quotes results)

- [x] **Data and Code Availability** statement, naming what the gate does re-derive (16 artifacts,
      byte-identically) and what it cannot (NS-3, hardware rig) rather than claiming "all results"
- [x] **Declaration of Competing Interests**
- [x] **Use of Generative AI** statement — required now by IEEE, Elsevier and MDPI, and the honest
      disclosure for how this work was produced
- [x] **Keywords** broadened from 8 to 11, adding the terms a *feasibility* paper is searched by
      (feasibility analysis, LoRaWAN, ns-3, reproducibility)
- [x] Abstract **279 words**, no undefined references, no overfull boxes, all 10 tables and 5 figures
      checked against their generating data
- [x] Seven audit passes; every quantitative claim guarded by a test that fails if it drifts
- [x] ⚠️ **Math audit 2026-08-28 (F43/F44/M4) — the headline was requalified.** The exclusion now
      reads **three of seven EU868 rates unconditionally**, plus DR3 as contingent on our own
      untuned header with the recovery named (an integer-keyed profile halves H_f and makes DR3
      feasible). The pre-registration keeps its date and drops the implied risk: the criterion
      reduces to `1 − 1/b`, so any batch b ≥ 2 met it. Both changes are honesty edits and both
      make the paper harder to attack — see `docs/audits/model_provenance.md` F43/F44.

---

## PER VENUE — do once the venue is chosen

| | Ad Hoc Networks (Elsevier) | IEEE IoT-J | MDPI Drones |
|---|---|---|---|
| template | `elsarticle`, single column, line numbers | `IEEEtran` **`journal`** (currently `conference` — must change) | MDPI LaTeX template |
| page cost | **none** (subscription) | overlength charge per page over 8 — ⚠️ the paper is now 10 pp in the conference class and will be longer in the journal class; re-check the venue's current fee | APC — re-check the current fee |
| first decision | ~8 weeks | 6.9 weeks | ~2–3 weeks |
| extras | **Highlights** (3–5 bullets, ≤85 chars each) + graphical abstract optional | none | graphical abstract |
| CRediT | required | not required | required |

⚠️ **`\documentclass[conference]{IEEEtran}` is wrong for any journal submission.** It is fine for
the current draft; switch the class before a journal submission and re-check the page count.

### Draft Highlights (for Elsevier, if chosen) — rewritten 2026-10-06

* One signature and one chain link cover four records; every frame verifies alone
* Built as a frame format with sender and receiver; sizes are emitted frames
* A frame that depends on its predecessor misses its verifiability target
* Capacity found by direct simulation per configuration, with bootstrap intervals
* Eight of twelve EU863-870 LoRaWAN data rates cannot carry one signed, chained frame

### ⚠️ SUPERSEDED highlights (the paper as it was in 2026-08)

* Signature bytes exclude three of seven EU868 rates outright, at any encoding, batch or header
* That exclusion is arithmetic, so it cannot move as models or hardware improve
* A fourth rate is excluded only by our framing, and we show the header redesign that recovers it
* Co-design sustains 1.9–3.2x the neighbourhood of inline signing on a validated channel
* Frame header measured at 44 B from the implemented wire format, not assumed
* All model-derived results re-derived byte-identically by a gate on every commit

---

## Suggested cover-letter argument — rewritten 2026-10-06

The reviewer question is still *"where is your new scheme?"*. The answer is two boundaries, and
the object they are boundaries of:

> We introduce no new primitive. We change the unit that is authenticated — from the record to
> the frame — and build it: a frame format, a sender and a receiver in which one signature and one
> chain link cover several records and every frame still decodes and verifies alone. What such a
> frame must carry decides where it can be sent at all, and we give that boundary on a real band
> with its conditions. Where it can be sent, we show what it buys in neighbours. The classical
> stream-signing schemes amortise the cost of *signing*; on a contended channel the cost that
> binds is the *frame*.

Worth saying plainly, because it is unusual and checkable from the public history: an earlier
version of this work reported the design as a sum of separately measured sizes. Building it
changed three results — the design as first specified missed its own verifiability target, the
low-rate exclusion was restated over the full set of data rates, and every capacity was
re-measured by direct simulation after a pre-registered prediction failed. Those corrections are
recorded in the repository and in a companion methods paper, not removed.

## ⚠️ SUPERSEDED cover-letter argument (the paper as it was in 2026-08)

The reviewer question this paper must survive is *"where is your new scheme?"* — because every
adjacent recent paper proposes one. The answer, and it should be the cover letter's first
paragraph:

> We deliberately introduce no new primitive. The contribution is a boundary: the set of
> configurations in which **no** choice of existing, standardised cryptography is feasible at all.
> That result is arithmetic rather than empirical, so unlike a performance figure it does not move
> as models, hardware or schemes improve — and it is invisible to the byte models the literature
> optimises against.

Worth adding, because it is unusual and verifiable from the public history: we audited our own
exclusion bound against the possibility that it rested on our own wire format, **found that it
partly did, and reported the smaller result**. Three of seven EU868 data rates are excluded by
arithmetic; a fourth was excluded by a frame header we had already documented as untuned, and we
give the redesign that recovers it. The boundary is weaker and the paper is stronger, because a
reviewer asking "is this just your encoding?" now finds the question already answered.

Worth stating plainly in the letter as well: **corrections and retractions made during the study are
recorded in the repository rather than removed**, including a survey claim withdrawn when its own
pre-registered test came back inconclusive. Editors read that as a positive signal, and it is
verifiable from the public history.
