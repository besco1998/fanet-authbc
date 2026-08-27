# What to do next — pick-up guide

## ⚠️ STATE CHANGED 2026-08-08: the research is done; the calendar is the constraint

Charter phases **P0–P8 are all delivered**. Six audit passes on the paper; the last three found a
rounding error and a duplicated word, which is the signal of diminishing returns. **Stop auditing.**

**Two things remain, and only one of them exists yet:**

1. **Submit the paper.** `paper/SUBMISSION_CHECKLIST.md` is the worklist. Venue-independent items
   are done (data-availability, competing-interests and generative-AI statements, keywords).
   ⚠️ Blockers only Mohamed can clear: **affiliation** (a literal placeholder in `main.tex`),
   ORCID, funding statement, whether the supervisor is a co-author, and two MDPI PDFs that need a
   browser. Venue is undecided; the checklist tabulates what changes for Ad Hoc Networks /
   IEEE IoT-J / MDPI Drones — including that IoT-J costs **USD 1,225 in mandatory overlength** at
   15 pp, and that `\documentclass[conference]` must become `journal` for any journal.
2. **⚠️ THE THESIS DOCUMENT DOES NOT EXIST.** `paper/` holds two papers (`main.tex`,
   `methods.tex`). The thesis is the actual March-2027 deliverable and nothing has been written.
   This is the largest gap in the project.

**Why submission goes first:** review takes 7–14 weeks. Submitting in August means a decision in
October and acceptance plausibly by January; waiting a month probably costs the publication
entirely. Write the thesis while the reviews run — the referee reports improve the chapters.

---

*Rewritten 2026-08-06. Read `CLAUDE.md`'s status board first for **where the project is**; this file
is **what to do next**. ⚠️ The previous version of this file was badly stale — it still listed as
pending seven items that were finished, including all of Tier 1. If you find that again, fix this
file before doing anything else: it is the designated entry point.*

```bash
git clone https://github.com/besco1998/fanet-authbc.git
cd fanet-authbc && git checkout p8-audit-and-corrections
make setup && make all          # green == you have reproduced the deterministic layer
```

`make all` = lint + mypy + 1215 fast tests + the 24-test frozen gate. NS-3 and the Pi rig are
optional (`docs/05_REPRODUCTION_GUIDE.md`). ⚠️ A fresh clone has **no NS-3 tree** — it is gitignored
by design. Fetch it from the **GitLab** archive; `nsnam.org/releases/...` returns an HTML error page.

---

## ⚠️ FRAMING CHANGED 2026-08-07 (Mohamed) — read this before editing the paper

**The paper is now a FEASIBILITY-BOUNDARY paper, not a co-design optimization paper.** Retitled
*"AUTHBC: Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound, a Capacity
Envelope, and Hardware Validation"*. §Results opens with three boundaries ordered by durability:

1. **Impossible** — 64 B does not fit 51 B, excluding four of seven EU868 rates. Arithmetic; cannot
   move. This is the headline.
2. **Capacity-limited** — 1.9–3.2× the inline baseline on a validated channel model.
3. **Runs, and what it costs** — 58.7 % fewer bytes, now presented as the *mechanism* that moves the
   boundary, **not** as the result. Its auth term is `1−1/b`, an identity.

⚠️ **Why:** as a co-design optimization paper the work is mid-tier — the optimisation is largely
closed-form and the ablation (F39) showed only one genuine interaction. As a boundary paper the same
evidence is stronger, because an impossibility result cannot drift and four performance numbers in
this project did. Do not revert the framing without re-reading F39 and F42.

**A second, short paper now exists:** `paper/methods.tex` (`make paper-methods`) — the defect
taxonomy as a methodological note in the Kurkowski / SIGCOMM-CCR credibility lineage. It is the more
transferable output and is deliberately a *self*-audit.

---

## The strategy decision (Mohamed, 2026-07-31, unchanged)

**Option 3: accept the novelty ceiling, spend the effort on rigour instead.** This is a strong
*measurement and reproducibility* study, not a novel-construction paper. **Target: IEEE Access.**
Direction C proceeds as a separate short paper.

---

## Everything in Tier 1 is DONE. What actually remains

### ✅ Done 2026-08-06 — ablation, PQC, S9, references

* **Factorial ablation (F39).** The four-axis coupling claim was **overstated**. Placement×batching
  couple *exactly* (`g_a(1−1/b)`, zero at b=1); **encoding is perfectly separable** (every
  interaction exactly 0); scheme is byte-degenerate. The apparent encoding coupling was a
  **ratio-scale artifact** — the absolute saving is 81.0 B for every encoding. Abstract, intro and
  Related Work corrected; a new Results paragraph states it. Nothing numeric moved.
* **PQC projection.** `make exp-pqc` — ML-DSA costs 9.2×, SPHINCS+ 28.1× per record, and the
  binding problem is that **batching cannot rescue it**: freshness caps b at 5, and an ML-DSA
  signature plus header (2464 B) **exceeds the 1500 B MTU on its own**. Projection only; the prior
  art is cited and nothing is claimed.
* **S9 resolved by WITHDRAWING the claim (F40)** — deliberately not reconstructed.
* **References 29 → 46 rendered.** ⚠️ **Short of the 45–60 target, and stopped there on purpose:**
  46 is every source held in `docs/literature/` that has been read (Klimiashvili et al. 2020 added 2026-08-07). Two held PDFs were excluded —
  `arxiv2309.15340` is a **Chinese-language paper we cannot read**, and
  `sensors2025_mesh_lora_performance` is still marked `TOREAD`. Reaching 45–60 needs a genuine
  sourcing pass: find, download, **read**, then cite. Padding the list would be the same failure as
  the stale numbers this audit spent its time removing.

### What remains

**References 39 → 45–60** is now the main open item, and it is a *reading* task, not a writing one.

### Writing, not experiments

| # | work | why | effort |
|---|---|---|---|
| ~~6~~ | ~~PQC extension section~~ | **DONE** — Limitations §, backed by `results/raw/pqc_projection.csv` | — |
| 7 | References **46** → 45–60 | 29→39 done from held+read sources; the rest needs sourcing **and reading** | 1 wk |
| ~~S9~~ | ~~Re-state or drop the pre-registration claim~~ | **DONE (F40)** — withdrawn, not reconstructed | — |

### Optional

* **D5** — RPi3 / BeagleBone cross-platform points. Adds generalisation breadth only.
* **Direction C** — needs the full 56-paper survey (5 done) and a defensible jitter value. The
  generator now exists (`make sim-lora-phase-artifact`), so the evidence is reproducible.

---

## What was finished, so nobody redoes it

| item | outcome |
|---|---|
| **Mobility (E20)** | **ANSWERED, null.** 30 seeds, G-M 5/20 m/s and RWP 20 m/s vs static: every arm within **0.06 σ**. Under `aloha`, mobility **structurally cannot act** (F36/F37) |
| **Hardware channel validation** | **DONE.** p = 2.3 × 10⁻⁴, airtime **1.995 ms vs 1.99 predicted** (F35) |
| **CIs on capacity** | **DONE.** `N_max = 3, 95 % CI [2,3]`; per-realisation reading gives 1 (S3) |
| **`p` sensitivity** | **DONE.** Selection is p-invariant; feasibility is the identity `p ≤ ε` (O2) |
| **Unicast small-frame bias** | **EXPLAINED.** Anomalous slot bounds it and predicts the 1/T_s scaling (O4) |
| **`channel_utilisation` at N=1** | **FIXED** — it returned 0.0, and a test asserted the defect (O5) |
| **LoRa EU at ≥30 seeds** | **DONE**, plus the other five 3-seed artifacts (F38) |

---

## Decisions recorded — do not re-litigate

* **Report BOTH V criteria, headline the mean** (Mohamed, 2026-08-06). The co-design ratio survives
  either reading (all combinations inside 1.9×–3.3×), which is what made this safe.
* **Correct everywhere + record a retraction** when a re-run moves a published number.
* Copyrighted PDFs in `docs/literature/` **stay** despite the public repo — risk accepted.
* **History was rewritten** before going public. ⚠️ **Never force-push an older local branch.**
* **Mobility: separate files, survey first, not the 802.11 arm.**
* The certificate-byte term was added **before** the CLAS numbers were fetched, deliberately.

---

## Before quoting any number

Read `docs/TRADEOFFS.md`, then check the claim against the five defect classes in
`docs/audits/scientific_implementation_audit.md` §1:

1. small-sample mean vs a threshold · 2. an unverified constant on the measurement path ·
3. **a threshold applied to a mean instead of a distribution** · 4. a config change that perturbs
the random realisation · 5. a claim wider than the experiment supports.

⚠️ **Only class 1 is fixed by more seeds.** And two of the defects found in this project were
*protected by passing tests* — a green suite means the code does what the tests say, not that the
tests say the right thing.
