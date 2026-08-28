# Submission checklist — `main.tex`

*Venue-agnostic. Everything that does not depend on the venue is done; the rest is listed with
what changes per venue. Written 2026-08-08.*

---

## ⚠️ BLOCKERS — only Mohamed can clear these

| # | item | what is needed |
|---|---|---|
| 1 | **Affiliation** | `main.tex` carries `[AFFILIATION -- TO BE COMPLETED]`. Needs department, institution, city, country. |
| 2 | **ORCID** | Required by Elsevier and MDPI, optional for IEEE. Register at orcid.org if you do not have one. |
| 3 | **Funding statement** | If the work was funded, every venue requires the grant number. If unfunded, say so explicitly — silence is not accepted. |
| 4 | **Supervisor / co-authors** | The paper is currently single-author. If your supervisor is to be a co-author, that must be settled before submission, not after. |
| 5 | **Two citations** | See below — both are behind MDPI's script block. |

### The two citations still needed

Both are one browser click. Save into `docs/literature/` with these names:

| paper | why it matters | save as |
|---|---|---|
| Rajasekaran, Maria, Al-turjman & Altrjman, *Anonymous Mutual and Batch Authentication with Location Privacy of UAV in FANET*, Drones 6(1):14, 2022 · `10.3390/drones6010014` | ⚠️ **A real gap.** We cite Zhang 2008 (*vehicular* batch verification) as our batch-verification comparator. This is the **UAV-specific** equivalent, 20 citations, in the exact community that will review us. Its absence is the kind of thing a reviewer notices first. | `rajasekaran2022_uav_batch_auth_fanet.pdf` |
| Al Majmaie, Ghajari, Bhatta & Ibrahem, *SSDBFAN: Scalable and Secure Cluster-Based Data Aggregation with Blockchain for FANETs*, Sensors 26(9):2585, 2026 · `10.3390/s26092585` | Defensive. Same group as `almajmaie2026pqfanet`, which we already cite; FANET + blockchain + aggregation, ns-3, 2026. Adjacent enough that omitting it looks like we stopped reading in 2025. | `almajmaie2026_ssdbfan_fanet_ns3.pdf` |

⚠️ Per the project's own rule, a source is not cited unless it is held and read. I will not add
either citation until the PDFs are in the repository.

---

## DONE — venue-independent

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
| page cost at 15 pp | **none** (subscription) | **$1,225** mandatory overlength ($175 × 7 pp over 8) | ~2,600 CHF APC |
| first decision | ~8 weeks | 6.9 weeks | ~2–3 weeks |
| extras | **Highlights** (3–5 bullets, ≤85 chars each) + graphical abstract optional | none | graphical abstract |
| CRediT | required | not required | required |

⚠️ **`\documentclass[conference]{IEEEtran}` is wrong for any journal submission.** It is fine for
the current draft, but a 15-page paper must not go to a journal in the conference class.

### Draft Highlights (for Elsevier, if chosen)

* Signature bytes exclude three of seven EU868 rates outright, at any encoding, batch or header
* That exclusion is arithmetic, so it cannot move as models or hardware improve
* A fourth rate is excluded only by our framing, and we show the header redesign that recovers it
* Co-design sustains 1.9–3.2x the neighbourhood of inline signing on a validated channel
* Frame header measured at 44 B from the implemented wire format, not assumed
* All model-derived results re-derived byte-identically by a gate on every commit

---

## Suggested cover-letter argument

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
