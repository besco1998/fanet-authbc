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
- **Phase: P8 (consolidation/paper). Pre-P8 audit + all approved recommendations DONE (2026-07-28/29).**
- **Green:** 1053 fast + 13 frozen-gate tests, `ruff` clean. **Headline reframed (F13/A1):** lead with **total on-air bytes −58.68 %** (174.25 → 72.00 B/rec) reported as a **decomposition** — placement×batching 79.2 % (auth 108 → 27.0, a 75.00 % cut), encoding 20.8 % (payload 66.25 → 45.0), scheme byte-neutral. **Never quote the bare 75 %:** it is algebraically **1 − 1/b**, invariant to H_f, g_a, encoding and scheme.
- **The load-bearing claim is now FEASIBILITY:** largest single collision domain each config serves — **N≤25** (A+JSON), **N≤32** (A+CBOR), **N≤103** (co-design) = **3.2×**. N=50 is quoted because it lies between. Needs all four axes + the channel model; no single axis produces it.
- **Every operating-point constant is now cited at source.** **H_f = 44 B MEASURED** from `wire.py` (was an assumed 40; headline unmoved — the first real test of F13). **3GPP TS 22.125 §5.2.2** anchors the whole service: R-5.2.2-010 ≥10 msg/s, R-5.2.2-011 ≤100 ms, R-5.2.2-008 payload "not including security-related components". **PX4 verified at source** (ONBOARD 50 Hz); **ArduPilot corrected** — default is vehicle-specific, **Copter 0 Hz**, not a universal 1 Hz. 48 B signature floor cited to draft-irtf-cfrg-bls-signature-05 (**126**-bit, not 128).
- ⚠️ **OPEN DECISION (B3): our D_max = 250 ms EXCEEDS the standard's 100 ms.** Recoverable — only Λ·D_max matters, so 50 Hz at 100 ms is compliant, PX4-real and gives the *identical* b=4 / 75 % / 58.68 %. **Mohamed decides:** keep 250 ms as a declared deviation, or re-anchor and report N≤35 instead of N=50. Related new finding **B8**: at N=50 the 100 ms bound is unsatisfiable on 802.11a at all.
- **New audit findings:** **F13** (headline is 1−1/b) · **F14** (energy model has **no chain-hash term**; under-predicts CPU **+7.97 %** and **asymmetrically** — +6.73 % at b=4 vs +2.52 % at b=1, so it **overstates the optimized config's energy advantage by ~4 points**; not patched, a correct fix needs an ARM SHA-256 measurement) · **F5 corrected upward to 3.03×** (a sparse batch grid omitting b=7 had quantized it to 2.75× — the F3 defect again).
- **T6** authentication-exclusion threshold: `s_max = M − H_f − g_a ≥ s_min`, with n_max=1 at ε≤p closing fragmentation. DR0–2 excluded by the **signature alone**, DR3 by 6 bytes.
- **Housekeeping done:** docs/03, docs/07 and both lane files marked HISTORICAL; docs/04 §3 + docs/06 §2 checked and were **already correct** (the DECISIONS entries were the stale ones); three new figures. **docs/OPEN_ITEMS.md is the single tracked open list.**
- **Still open:** ⚠️ B3 (above) · A3 `[VERIFY]` citations (**deferred by Mohamed to P8 start**) · D1 meter half (RPi4s powered down; `hw/validate_energy_e2e.py` written and smoke-tested) · C1/C2 DCF access delay absent from D(b) · D3 NS-3 validates throughput only · **F1 paper restructure (the P8 deliverable)**.
