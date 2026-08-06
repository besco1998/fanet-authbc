# What to do next — pick-up guide

*Rewritten 2026-08-06. Read `CLAUDE.md`'s status board first for **where the project is**; this file
is **what to do next**. ⚠️ The previous version of this file was badly stale — it still listed as
pending seven items that were finished, including all of Tier 1. If you find that again, fix this
file before doing anything else: it is the designated entry point.*

```bash
git clone https://github.com/besco1998/fanet-authbc.git
cd fanet-authbc && git checkout p8-audit-and-corrections
make setup && make all          # green == you have reproduced the deterministic layer
```

`make all` = lint + mypy + 1147 fast tests + the 14-test frozen gate. NS-3 and the Pi rig are
optional (`docs/05_REPRODUCTION_GUIDE.md`). ⚠️ A fresh clone has **no NS-3 tree** — it is gitignored
by design. Fetch it from the **GitLab** archive; `nsnam.org/releases/...` returns an HTML error page.

---

## The strategy decision (Mohamed, 2026-07-31, unchanged)

**Option 3: accept the novelty ceiling, spend the effort on rigour instead.** This is a strong
*measurement and reproducibility* study, not a novel-construction paper. **Target: IEEE Access.**
Direction C proceeds as a separate short paper.

---

## Everything in Tier 1 is DONE. What actually remains

### The one substantive scientific gap

**Factorial ablation over the four axes — 2 days.** The paper's central claim is that the axes
**couple** ("co-design"). The evidence offered is a **decomposition** (79.2 % placement×batching,
20.8 % encoding), which is a different thing: a decomposition attributes a total, an ablation shows
that removing one axis degrades what the others deliver. ⚠️ **If the axes turn out to be separable,
"co-design" is overclaimed** — and that is the question a reviewer will ask. The optimizer can be
run with each axis pinned, so the machinery already exists.

### Writing, not experiments

| # | work | why | effort |
|---|---|---|---|
| 6 | PQC extension section | foreseeable question; **cite** the 5G/V2X prior art and claim nothing | 1 d |
| 7 | References 31 → 45–60 | thin for a Transactions-class venue | 1 wk |
| **S9** | Re-state the Direction C pre-registration, or drop the claim | the artifact cites `scratchpad/C1_EXPECTATIONS.md`, **which is not in the repo** — the claim of pre-registered expectations cannot be verified | 1 h |

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
