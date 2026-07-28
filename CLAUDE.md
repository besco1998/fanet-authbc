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
- **Phase: P7 done (`p7-done`). P8 (consolidation/paper) in progress — pre-P8 FULL AUDIT complete 2026-07-28.**
- **Green:** 1020 fast + 13 frozen-gate tests, `ruff` clean. Headline **75.00 %** auth-byte cut (delta + Ed25519 + placement B + b=4, 26.0 B/rec vs 104) at V≥0.95, p=0.05, D≤250 ms, U=0.55 — on fully **measured** ARM parameters (`p_cpu_w`=0.634 W, `p_radio_w`=0.218 W, κ=0.34).
- ⚠️ **BIGGEST OPEN ITEM — audit F13:** the auth-byte headline is **algebraically 1 − 1/b**. Encoding and scheme contribute **zero**; H_f and g_a cancel identically (verified over H_f∈{20,40,80,200}×g_a∈{48,64,96} → 75.0000 % every time). And b=4 is ⌊Λ·D_max⌋ minus the airtime correction, i.e. fixed by two **inputs**. The four-axis "co-optimizing … cuts 75 %" framing must be **retired**: lead with joint **feasibility** (at N=50, Λ=20 the baselines are *unrunnable* — U=2.28 A+JSON, 1.53 A+CBOR, vs 0.55 optimized) and report the **decomposition** (auth 75.0 % via placement×batching = 78.6 % of the saving; payload 32.1 % via encoding = 21.4 %; **total bytes 58.3 %**). Pinned by `test_headline_decomposition.py`.
- **New this session:** **T6** authentication-exclusion threshold (`s_max = M − H_f − g_a ≥ s_min`; T3 gives n_max=1 at ε≤p so fragmenting cannot escape; DR0–2 excluded by the **signature alone**, DR3 by **2 bytes**) · **F5 adopted on LoRa only** (b 3→8 at DR5, Λ 0.076→0.203 rec/s, 2.67×; 802.11 keeps per-record chaining) · LoRa arm = **scoped modelling chapter**, no hardware/energy · frozen gate extended to the 3 previously **ungated** artifacts (lora ×2, capacity) · **docs/OPEN_ITEMS.md** is now the single tracked open list.
- **Docs fixed this session:** narrative E5 table still said ECDSA/b=28/3.71 (F10 never propagated) · docs/01 said BLS **48 B** (it is 96) and still listed the D9-deleted `T_fx≈123 µs` · paper contradicted itself on nominal-vs-measured power · charter said "no LoRa in this arm" and "4× RPi4" (real: 2×) · docs/04 had **no entry** for 3 runnable experiments (now E6/E7/E8) · **H_f = 40 B labelled an assumption** (docs/01 §2a) — it was a bare table default feeding every formula.
- **Open ⚠️ for Mohamed:** (1) accept the F13 reframing before the paper restructure; (2) `[VERIFY]` citations — deferred by Mohamed to start of P8; (3) H_f/N_local/D_max/p have no citations (docs/OPEN_ITEMS.md §B); (4) energy model never validated end-to-end (§D1).
