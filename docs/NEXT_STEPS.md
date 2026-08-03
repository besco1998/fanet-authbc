# What to do next — pick-up guide

*Written 2026-07-31 so work can resume from a cold start on any machine. Read `CLAUDE.md`'s status
board first for **where the project is**; this file is **what to do next**.*

```bash
git clone https://github.com/besco1998/fanet-authbc.git
cd fanet-authbc && git checkout p8-audit-and-corrections
make setup && make all          # green == you have reproduced the deterministic layer
```

`make all` = lint + mypy + 1107 fast tests + the 14-test frozen gate. NS-3 and the Pi rig are
optional and only needed for the simulation and hardware targets (`docs/05_REPRODUCTION_GUIDE.md`).

---

## The strategy decision (Mohamed, 2026-07-31)

**Option 3 adopted: accept the novelty ceiling, and spend the effort on Tier 1 instead.**

This is a strong *measurement and reproducibility* study, not a novel-construction paper. Two novelty
directions were surveyed and killed on evidence before any work was built on them — PQC feasibility
(occupied at NDSS level; the closest prior art was already in our own register) and the general
feasibility-boundary framing (done for 5G broadcast in arXiv 2510.23457). Reframing would cost weeks
to move a reviewer from "solid" to "solid".

**Target: IEEE Access.** Direction C proceeds in parallel as a separate short paper.

---

## Tier 1 — publication blockers, in order

### 1. Mobility (E20) — 3–4 weeks, the biggest single objection
A Flying Ad-hoc Network paper in which nothing flies is the most quotable weakness against it.
**Full plan already written: `docs/MOBILITY_PLAN.md`.** Key constraints, decided:
* **Separate NEW scenario files**, not edits — the frozen static results stay reproducible and
  mobility becomes an additive comparison.
* **Literature survey FIRST** — what models, speeds, node counts, areas and durations FANET papers
  actually use, so our configuration sits inside published practice.
* **Not Random Waypoint** (wrong for swarms, known artifacts). Gauss–Markov + a formation model.
* **LoRa arm only.** Bianchi and Ma & Chen contain no position term, so mobility cannot change the
  802.11 validation — state that assumption instead of simulating it.
* ⚠️ Per-frame Doppler fading stays unmodelled either way and must be stated: at 20 m/s the LoRa
  channel decorrelates ~50× *within* a single 364 ms frame.

### 2. Hardware channel validation — 3–5 days
Every capacity claim is simulation. Both Pis work, the rig is wired, and the radio-energy run
already used it (`results/hw/energy/p_radio_w.md`). A 2-node broadcast delivery measurement would
anchor the channel model to hardware for the first time.
⚠️ Only Pi-A has a sync wire (`hw/RIG.md:40-42`) — that is documented and deliberate, not a gap.

### 3. Confidence intervals on the headline capacity figures — 1 day
`N_max = 100` is a threshold crossing on a noisy curve, reported as a point — **after four separate
headline numbers moved from exactly this failure mode**. Report an interval.

---

## Tier 2 — closes foreseeable reviewer questions

| # | Work | Why | Effort |
|---|---|---|---|
| 4 | Factorial ablation over the four axes | The paper *claims* coupling; the 79/21 split is a decomposition, not an ablation | 2 d |
| 5 | Sensitivity sweep over `p` | Everything rests on `p = 0.05`, asserted with no source | 1 d |
| 6 | PQC extension section | Foreseeable question; machinery exists. **Cite** the 5G/V2X prior art, claim nothing | 1 d |
| 7 | References 31 → 45–60 | Thin for a Transactions-class venue | 1 wk |

## Tier 3 — known, cheap, non-blocking
* Unicast's **−1.4…−2.6 % small-frame bias** is unexplained. Anomalous-slot (Tinnirello) is a
  hypothesis, **untested**, and labelled as such.
* `channel_utilisation` returns exactly `0.0` at N=1 — a lone sender still occupies airtime.
* The LoRa `EU`-preset run at ≥30 seeds (partially done, `lora_capacity_eu.csv` is 3-seed).

---

## Direction C — the second paper (parallel track)

**The finding:** the ns-3 LoRaWAN traffic model standard in the field (equal period, exact interval)
freezes relative transmission phases for a whole run, **inflating seed-to-seed variance 2–8×** — in a
literature that reports no seed counts or dispersion. Mechanism identified, fix demonstrated,
evidence in `results/raw/lora_phase_artifact_{30seed,eu_30seed}.csv` (300 runs) and F32/F33.

**Two things gate it, either of which could still weaken it:**
1. The **full 56-paper survey** with explicit replication counts. Five papers done — that is a pilot,
   and MDPI bot protection blocked most downloads.
2. A **defensible jitter value**. 1 s is a choice, not derived. The anchor is that LoRaWAN Class A
   mandates transmission randomisation and the module omits it — an argument, not a measurement.

⚠️ The mean-bias half of the original claim **did not generalise** and was narrowed in F33. Do not
resurrect it.

---

## Decisions recorded, do not re-litigate

* **Copyrighted PDFs in `docs/literature/` stay** despite the repo being public. Flagged 2026-07-31
  (≈7 IEEE/Elsevier PDFs are not redistributable); **Mohamed accepted the risk.** See `DECISIONS.md`.
* **History was rewritten** before going public to purge the 84 MB vendored NS-3 tree. The remote is
  authoritative. ⚠️ **Never force-push an older local branch over it** — that re-injects the blobs.
* **Mobility: separate files, survey first.** **Not** for the 802.11 arm.
* **The certificate-byte term was added BEFORE the CLAS numbers were fetched**, deliberately.

---

## Before quoting any number

Read `docs/TRADEOFFS.md`. Then remember the pattern that cost this project four headline numbers:
**every one was a small-sample mean compared against a threshold, and none was a modelling error.**
Drivers now default to 30 seeds and emit min/max/σ. Look at the *distribution*.
