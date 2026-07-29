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
- **Phase: P8 (consolidation/paper). Pre-P8 audit + every approved recommendation DONE (2026-07-28/29). Hardware campaign D1 COMPLETE.**
- **Green:** 1048 fast + 14 frozen-gate tests (1062 total), `ruff` clean.
- **METHODOLOGY (Mohamed, 2026-07-29): this is an optimization problem — state everything, choose what to stick with, state the trade-offs for every decision.** A reported configuration without its alternatives is a *selection*, not an optimization. **`docs/TRADEOFFS.md` is now required reading before quoting any number.**
- **Headline (F13/A1):** total on-air bytes **−58.68 %** (174.25 → 72.00 B/rec), reported as a **decomposition** — placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral. **Never quote the bare 75 %:** it is algebraically **1 − 1/b**. Load-bearing claim is the **feasibility envelope**: N_max **25 / 32 / 103** (3.2×).
- **B3 SETTLED AS AN OPTIMIZATION** (`results/raw/operating_region.csv`, 70 points). Λ and D_max are decision variables, and the answer is a **bound, not a choice**: whole region best 98.0 % · TS 22.125-compliant 18 points, best 75.0 % but unrunnable (U=1.39) · **compliant AND runnable at N=50: exactly 4 points, best 50.0 %, requiring Λ∈[21,22] Hz**. **Declared reference point Λ=20, D=250 ms is kept with its cost stated: it violates R-5.2.2-011, and a third of the headline is bought by that deviation.** The compliant corner is reported, not adopted — knife-edge (at Λ=20.0 the b=2 frame is 100.37 ms, so b→1 and the cut→0 %).
- **D1/D6/D7 CLOSED — energy model validated end-to-end and FIXED.** Initially ~32 % low; both causes root-caused and corrected. **D7:** no chain-hash term — SHA-256 measured **2745.5 ns** on ARM, now charged **2× per record** (sender extends chain, receiver verifies), does *not* amortize over b; E5 optimized 112.08→115.56 µJ. **D6:** its premise was wrong — `p_cpu_w` is **not** config-dependent (four configs spread only **3.8 %**: 0.732/0.744/0.755/0.760 W); 0.634 W was wrong because it came from *isolated primitives* and understates composed pipelines by **18.2 %**. Adopted **0.749 W**. **Residual now +7.5…+14.3 %**, all frame assembly — deliberately uncharged (CPython prototype overhead, not a property of the design). **Energy figures are lower bounds by ~10–14 %.** E5 optimized energy now **131.68 µJ/rec**.
- ⚠️ **RETRACTED 2026-07-29:** the interim claim that the model "overstates the optimized config's energy advantage by ~4 points" was inferred from x86 timings and is **contradicted by measurement** — measured advantage 2.035× vs predicted 1.985×. Corrected in energy.py, paper, OPEN_ITEMS.
- **Every operating-point constant cited at source:** H_f = **44 B measured** from `wire.py` · **3GPP TS 22.125 §5.2.2** (≥10 msg/s, ≤100 ms, payload "not including security-related components") · PX4 verified (ONBOARD 50 Hz) · **ArduPilot corrected — Copter default is 0 Hz**, not a universal 1 Hz · 48 B signature floor → draft-irtf-cfrg-bls-signature-05 (**126**-bit).
- **T6** exclusion threshold: `s_max = M − H_f − g_a ≥ s_min`, n_max=1 at ε≤p. DR0–2 excluded by the **signature alone**; DR3 by 6 B. **F5 on LoRa corrected upward to 3.03×** (sparse grid omitting b=7 had quantized it).
- **Hardware access:** `ssh -i hw/keys/pi-a/pi-a pi@192.168.1.21` (pi-b: `.20`); INA219 Arduino on `/dev/ttyACM0`. Harness `hw/validate_energy_e2e.py` (two of its own defects fixed by running it).
- **Still open:** A3 `[VERIFY]` citations (**deferred by Mohamed to P8 start**) · C1/C2 DCF access delay absent from D(b) · D3 NS-3 validates throughput only · **D6** one `p_cpu_w` for all configs · **D7** no ARM SHA-256 timing (blocks the F14 fix) · **F1 paper restructure (the P8 deliverable)**.
