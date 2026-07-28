# CLAUDE.md — Standing Policy for the AUTHBC Agent

## Project (agent owns execution end-to-end; Mohamed owns decisions only)
AUTHBC: co-optimizing encoding × authentication placement × signature scheme × batching
for blockchain-grade UAV telemetry ledgers over 802.11 (LoRa arm later). Full specs in
`docs/00–06`. Owner: Mohamed A. Farouk. Thesis deadline: March 2027.

## Read-first order (every new session)
1) this file → 2) docs/00 charter → 3) the current phase prompt in docs/prompts/ →
4) ONLY the docs sections that prompt's CONTEXT BUDGET names → 5) docs/06 for the tools
you're about to touch. Phase prompts + templates live in docs/prompts/. Parallel plan:
docs/07. Resuming? use docs/prompts/T_TEMPLATES.md §Resume.

## The Eight Laws (non-negotiable)
1. **Plan first.** Restate objective, risks, step plan + acceptance criteria; get approval
   (plan mode) before executing. No unplanned side quests.
2. **Verify before assuming.** Unsure about an API/version/constant/formula? Inspect the
   installed package, source, or official docs BEFORE writing code against it.
3. **Never bypass a failure.** Failing test/install/KAT/determinism/odd number ⇒ STOP →
   Failure Report (docs/06 §7) → root cause → fix → regression test → green → continue.
   Forbidden forever: skipping tests, commenting out asserts, widening tolerances,
   mocking real data, proceeding "temporarily".
4. **TDD.** Vectors/tests with or before code. `main` is always green.
5. **Audit–attack–fix–iterate.** After each module and phase: attack scientifically
   (formula conformance vs docs/01–02, units, edge cases, stats per 02§8) and as an
   engineer (determinism, seeds, error paths). Findings → docs/audits/p<N>.md → fix →
   re-test.
6. **Check your results.** Before recording/committing ANY number, table, or figure, run
   §Validate-Results (docs/prompts/T_TEMPLATES.md): state the EXPECTED value/shape/sign/
   magnitude in advance and compare; run sanity gates; cross-check one point independently;
   confirm determinism + provenance. If a result is surprising, borderline, self-
   contradictory, or you're unsure finding-vs-bug — DO NOT average it away or assume it's
   fine: reproduce, hypothesize, explain-with-evidence or §Debug; if still ambiguous, raise
   to Mohamed. A plausible-looking WRONG number is worse than a crash.
7. **Scientific integrity.** Seeded runs; raw CSVs with config-hash + env headers; no
   fabricated/extrapolated numbers; >10% model-vs-measurement gaps investigated in writing
   (no hidden correction factors); negative results reported plainly.
8. **Decision points.** Items marked ⚠️ (D0–D7 in docs/00) and ANY spec deviation: stop and
   ask Mohamed. You created the repo and run everything; Mohamed only decides.
Plus: **Autonomous chaining** — after a green phase tag, load the next docs/prompts file and
continue; stop only at ⚠️ gates/failures; write a §Handoff every phase. **Parallel discipline
(if D7≠serial)** — one session per worktree; edit only your lane's owned paths (docs/07 §3);
shared files are P0-frozen; merges at SYNC points only.

## Commands (the only supported entry points)
`make setup | lint | test | verify-frozen | bench-micro | bench-macro | exp-e1..e5 |
sim-ns3 | sim-ns3-matrix | sim-ns3-dcf | hw-capture | hw-reduce | figures`

## Environment facts
WSL2 Ubuntu 24.04; repo on Linux FS only (never /mnt/c); Python 3.12 venv; pins in
pyproject (cbor2==5.8.0 is deliberate); NS-3 3.41 from source (docs/06 §2); GitHub via
`gh`, private repo, conventional commits, push at green checkpoints, tag `p<N>-done`.

## Style
Small pure functions; every module docstring cites the docs section it implements;
type hints; no dead code; comments explain WHY, not what.

## Current status board (agent updates this section every session)
- Phase: **P7 COMPLETE and tagged `p7-done`.** Next: **P8 consolidation/paper** (`docs/prompts/P8_CONSOLIDATION_PAPER.md`); draft exists at `paper/main.pdf`, citations marked `[VERIFY]` for Mohamed.
- Last green commit: main — **901 fast tests + 10 frozen-gate green, `ruff` clean.** Headline: **96.77 % auth-byte cut** (delta + Ed25519 + placement B + **b=31**, 3.355 B/rec vs 104) at V≥0.95, p=0.05 — **PASS**, on fully measured ARM parameters.
- Hardware (P7b, done): both RPi4s healthy; **p_cpu_w = 0.634 W** (nominal 3.0 was 4.7× high), **p_radio_w = 0.218 W** (nominal 0.7 was 3.2× high) ⇒ **κ = 0.34**, inside E4's assumed ≤0.5 band. **F6 confirmed:** ECDSA wins on x86, **Ed25519 on ARM** (D8: ARM is the thesis platform); both 64 B so the headline is byte-unchanged.
- **NS-3 broadcast residual: SOLVED (F9, 2026-07-28).** PHY instrumentation, not inference. **Capture = 0 %** (all 1149 decodes at the monitored receiver came from single-transmitter busy periods; `--equalPower` byte-identical) — the earlier "capture effect" explanation is **retracted**. Real cause: the **post-transmission head start** (a station that just transmitted may redraw backoff 0 and take the medium a slot before any deferring station, whose counter is necessarily ≥1). A slot-exact simulator (`src/authbc/sim/dcf_ladder.py`) carrying only that asymmetry reproduces NS-3 to **≤1.1 %** across N=5–50, and reproduces Bianchi when it is switched off. The broadcast-claim embargo is **lifted**.
- **F8 fixed + deliberate re-freeze:** NS-3 sinks outlived the sources by 0.5 s on a 10 s window ⇒ every goodput was **~4.8 % high**. `ns3_matrix.csv` re-measured; unicast↔Bianchi tightens **+1.8…+5.3 % → +0.08…−3.31 %**. New artifact `results/raw/ns3_dcf_residual.csv`; new entry points `make sim-ns3-matrix`, `make sim-ns3-dcf`.
- Open ⚠️ decisions for Mohamed: (1) should **docs/02 §6** adopt the slot-exact process as the normative broadcast model (code/figure/CSV already carry both; only the doc is unchanged)? (2) **docs/04 §1's 5–15× x86→ARM anchor** is unreachable (clock floor 2.61×) — restated per-cycle, needs blessing. (3) `[VERIFY]` citations in the paper. D6 wire freeze active.
- Known issues: **F1/F3/F8/F9 fixed.** Open: F2 (energy used unicast T_FX — resolved at the P7 re-freeze), F4 (cross-experiment record sizes differ ~4 %, standardize at P8), F5 (32 B prev_hash/record — stated assumption), **F6 mechanism unexplained** (ADX story retracted; the measured 1.05× vs 1.60× cycles portability difference stands on its own). Minor: `e4_crossover.png` missing from PROVENANCE.md (P8).
