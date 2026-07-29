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
- **Phase: P8. Paper restructured (F1 DONE). NS-3 migrated 3.41→3.48. LoRa arm now simulated.**
- **Green:** 1063 fast + 14 frozen-gate tests (1077), `ruff` clean, paper builds (7 pp, 0 undefined refs).
- **METHODOLOGY (Mohamed):** this is an optimization problem — *state everything, choose what to stick with, state the trade-offs for every decision*. **`docs/TRADEOFFS.md` is required reading before quoting any number.**
- **Headline:** total on-air bytes **−58.68 %**, as a **decomposition** (placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral). **Never quote the bare 75 %** — it is algebraically **1 − 1/b**. Load-bearing claim is the **feasibility envelope**, reported at BOTH thresholds: **25/32/103** at saturation (U<1) and **65/104/233** at the measured V≥0.95 boundary (U≈2.80). **The ~3× ratio is the claim**, since it survives either reading.
- **NS-3 = 3.48** (D4 amended). Both trees kept; `ns3/ns3_paths.py` + `AUTHBC_NS3` select one. Migration gate passed: matrix **2.56 %**, DCF trace **2.62 %**, smoke **2.44 %**, delay crossing **identical (U=2.80)**. Bands re-measured: unicast↔Bianchi **+1.28/−0.49 %** (improved), broadcast↔Ma&Chen **≤2.49 %** (widened from ≤0.75 %). ⚠️ **Build with `-j 3` under `nohup`** — 7.8 GB RAM vs ninja's default `-j 15` OOMs and takes WSL down.
- ⚠️ **Sensitivity moved a lot on 3.48 at marginal SNR:** `realistic_500m` **−26.5 %**, `nakagami1` **−18.2 %**, near-field all <2 %. Paper limitations updated: idealised model is **39 % optimistic at 500 m** (was 15.7 %), Rayleigh fading costs **27 points** (was 9).
- **D2 CLOSED by simulation:** LoRaWAN module on ns-3.48 gives **N_max = 5** at DR5 (V≥0.95), a sharp ALOHA cliff (1.000 at N=5 → 0.866 at N=8). With the 121× per-node gap that is **≈2500× less aggregate capacity** than 802.11. Still **not hardware**. Module enforces RP002 **Table 12** (222 B) vs our **Table 13** (242 B) → b=6 not 7; both defensible, difference stated.
- **⚠️ TWO RETRACTIONS this session, both mine, both kept visible:** **T7** (capacity excludes at U≥1 — refuted by its own validation experiment) and **F15** (the ≤0.36 % validation is one comparison restated — refuted by a broadcast/unicast filtering error of mine plus an invalid independence test). Lesson recorded: **run the suite before propagating a finding**, not after.
- **Energy validated end-to-end** (D1/F14): was ~32 % low, both causes fixed (D7 chain hash 2745.5 ns ×2/record; D6 `p_cpu_w` 0.634→**0.749 W** from composed pipelines). Residual **+7.5…+14.3 %**, all uncharged CPython framing. **Energy figures are lower bounds by ~10–14 %.**
- **Still open:** **A3** `[VERIFY]` citations (**deferred by Mohamed to the end — this is now next**) · ⚠️ **B3** keep D_max=250 ms or re-anchor to the compliant (50 Hz, 100 ms) point · B5/C3/C5/C6/D5 accepted limitations.
