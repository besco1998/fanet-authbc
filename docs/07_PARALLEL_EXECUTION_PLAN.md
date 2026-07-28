# 07 — PARALLEL EXECUTION PLAN
> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions.

Which phases can genuinely overlap, how to run them safely with multiple Claude Code
sessions, and what it buys. Referenced by ⚠️ D7 (Mohamed picks the mode at end of P0).

## 1. The real dependency graph (what depends on what — and what does NOT)
```
P0 ─┬─► P1a code: encodings+crypto+KATs ─► P1b benchmarks ──────────┐
    │            └────────► P2 ledger+wire ─► P3 placements+channel ─► P4 (E1–E3)
    ├─► L2: P5a models (bianchi/energy/optimizer vs SPEC, unit-tested) ─► P5b (E4)*
    ├─► L3: P6a NS-3 install+build+hello+scenario skeleton ─► P6b (validation+E5)**
    └─► L4: P7a RPi4 provisioning scripts (anytime) ─► P7b hardware campaign***
                                                        P8 needs everything
*  P5b (E4) needs P1b's measured timings + P5a.        (SYNC-2)
** P6b needs P5a (Bianchi) + P3 (real framer-exported frame sizes). (SYNC-3)
***P7b needs P1a code (+ hardware & ⚠️ D5 meter); best value after P5a exists.
```
**Key insights that unlock parallelism:**
- **P5a is spec-driven, not data-driven.** The Bianchi solver, energy model, and
  optimizer are implemented and unit-tested against doc 02's formulas and hand-computed
  values — they need NO code or data from Lane 1. Only *running E4* needs P1b numbers.
- **P6a is environment work.** The NS-3 build is 15–40 min of mostly waiting plus a
  skeleton scenario that takes frame sizes as a parameter — spec-level sizes suffice
  until SYNC-3 swaps in framer-exported ones.
- **P1 splits.** P2 needs P1a's *code* (encoders, signers), not P1b's *measurements* —
  tag `p1a-code-done` unblocks P2 while P1b runs elsewhere.
- **P7 splits.** Provisioning scripts are pure prep; the campaign itself only needs P1a
  code for the microbench rerun.

## 2. The three lanes (recommended mode: 2 concurrent sessions + NS-3 as a "freebie")
| Lane | Contents | Depends on | Owner paths (see §3) |
|---|---|---|---|
| **L1 Core** | P1a→P1b→P2→P3→P4 | P0 | encodings, crypto, ledger, placement, channel, bench, experiments/e1–e3 |
| **L2 Models** | P5a, then P5b at SYNC-2 | P0 (P5b: +P1b) | models, experiments/e4 |
| **L3 NS-3** | P6a, then P6b at SYNC-3 | P0 (P6b: +P5a,P3) | ns3/ |
| **L4 HW (optional overlap)** | P7a scripts; P7b after SYNC-1+hardware | P0 (P7b: +P1a) | hw/, results/hw |

**Sync points (merge to main, re-plan, retag):**
- **SYNC-1** = `p1a-code-done`: L1 continues to P1b *and* P2 (pipelined in one session,
  or P1b handed to a short L2-side task); P7b becomes possible.
- **SYNC-2** = P1b + P5a done: run E4 (P5b). ~end of week 2.
- **SYNC-3** = P3 + P5a done: export frame-size CSV → P6b runs the validation matrix and
  E5 prep. ~week 4.
- **SYNC-4** = P4 + P5b + P6b done: final E5 + cross-audit → P8. ~week 5.

## 3. Ownership map (conflict prevention — absolute rule)
P0 pre-creates EVERY directory, the full Makefile, pyproject, CI, and stubs, then
freezes the shared files. Each lane may modify only:
```
L1: src/authbc/{encodings,crypto,ledger,placement,channel,bench}/**, tests/{unit,property,integration}/** (matching), experiments/e{1,2,3}/**, results/raw/e{1,2,3}*, analysis/figures_e123.py
L2: src/authbc/models/**, tests/unit/models/**, experiments/e4/**, results/raw/e4*, analysis/figures_e4.py
L3: ns3/**, results/raw/ns3*, analysis/figures_ns3.py
L4: hw/**, results/hw/**
ALL lanes: docs/status/lane<N>.md (own file only), docs/audits/p<N>.md (own phase only)
NOBODY without a sync-point decision: Makefile, pyproject.toml, CLAUDE.md, docs/00–07, tests/vectors/ (frozen at P2 per ⚠️ D6)
```
Violation handling: doc 06 §8.

## 4. Practical setup (one command, created at P0)
`scripts/lane.sh 2` → `git worktree add ../fanet-authbc-lane2 -b lane2` + prints the
checklist: open that folder in a separate VSCode window, start Claude Code there, paste
`docs/prompts/P5_MODELS_OPTIMIZER.md`. Merges: at each SYNC, the L1 session (the
"integrator") merges lane branches to main, runs `make all`, tags, and pushes.

## 5. What parallelism buys — and its honest cost
| Mode | Wall time to end of E5 | Sessions to babysit | Risk |
|---|---|---|---|
| Serial | ~8 weeks | 1 | lowest |
| **2-lane (L1 + L2, L3 piggybacked)** | **~5–6 weeks** | 2 | low (disjoint paths) |
| 3-lane (+dedicated L3) | ~5 weeks | 3 | moderate (more merges) |
**Honest costs:** you review two plans and two audit files per sync instead of one;
merge discipline matters; a solo researcher's attention is the true bottleneck.
**Recommendation:** 2-lane. Start L3's NS-3 *build* early inside either session (it is
mostly unattended waiting), and keep L4 opportunistic. Do NOT parallelize P2 against P3
or split E-experiments across lanes — those dependencies are real, and false parallelism
there creates rework.

## 6. What must stay serial (do not fight these)
P0 (everything hangs off it) · P2→P3 (placements consume the frozen wire format) ·
P4 after P3 (experiments need the emulator) · P6b after P3+P5a · E5 after everything ·
P8 last. The freeze points (wire format at P2, experiment configs at first data) are
serialization *by design* — they protect scientific validity, not just tidiness.
