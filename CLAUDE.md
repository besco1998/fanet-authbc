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
`make setup | lint | test | bench-micro | bench-macro | exp-e1..e5 | sim-ns3 | figures`

## Environment facts
WSL2 Ubuntu 24.04; repo on Linux FS only (never /mnt/c); Python 3.12 venv; pins in
pyproject (cbor2==5.8.0 is deliberate); NS-3 3.41 from source (docs/06 §2); GitHub via
`gh`, private repo, conventional commits, push at green checkpoints, tag `p<N>-done`.

## Style
Small pure functions; every module docstring cites the docs section it implements;
type hints; no dead code; comments explain WHY, not what.

## Current status board (agent updates this section every session)
- Phase: **P4 DONE** (tags …`p3-done`, `p4-done`) — E1–E3 experiments + first thesis figures; next P6/P8 + SYNC-4. Mode: **2-lane** (Lane 2 `p5-done`).
- Last green commit: `p4-done` on main — CI green; 777 tests; audit docs/audits/p4.md; E1–E3 raw FROZEN (⚠️ D6) + byte-stable figures.
- Open ⚠️ decisions: none blocking. D6 wire freeze active (post-freeze changes → Mohamed; e.g. optional D fragment-header binding). Settled: D7=2-lane; BLS=96 B; CBOR=arrays; T1=measured φ. D4/D5 later.
- Known issues: none. P7 note: ECDSA-verify at low edge of µs anchor — re-confirm on RPi4. e-axis-in-recs reconciliation deferred to P3.
- Env note: `pyenv global system` makes `python3` = system 3.12.3; `make setup` defaults `PYTHON=python3`
