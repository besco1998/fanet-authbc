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
- Last green commit: main — **964 fast tests + 10 frozen-gate green, `ruff` clean.** Headline: **75.00 % auth-byte cut** (delta + Ed25519 + placement B + **b=4**, 26.0 B/rec vs 104) at V≥0.95, p=0.05 **and D≤250 ms** — **PASS**, on fully measured ARM parameters. (Byte-optimal ignoring freshness is 96.77 % at b=31, but that costs **1.55 s** of staleness — F10.)
- Hardware (P7b, done): both RPi4s healthy; **p_cpu_w = 0.634 W** (nominal 3.0 was 4.7× high), **p_radio_w = 0.218 W** (nominal 0.7 was 3.2× high) ⇒ **κ = 0.34**, inside E4's assumed ≤0.5 band. **F6 confirmed:** ECDSA wins on x86, **Ed25519 on ARM** (D8: ARM is the thesis platform); both 64 B so the headline is byte-unchanged.
- **NS-3 broadcast: F9 CLOSED, and REFRAMED (2026-07-28).** Capture measured at **0 %** — the earlier "capture effect" explanation is retracted. The real cause is the **backoff counter Consecutive Freeze Process**, and it is **published**: Ma & Chen, *IEEE Comm. Lett.* 11(8):686–688, 2007 and *IEEE TVT* 57(6):3757–3768, 2008 — their abstract warns unicast models "cannot simply be reduced" to broadcast, which is exactly what we had done (τ=2/(W+1), wrong by **16× at N=50**). `models/broadcast_dcf.py` now implements their equations, cited; their closed form reproduces our NS-3 measurement to **≤0.36 %** at every N. **No novelty claimed for the mechanism.** Ours: validation at W₀=16/802.11a (they used W₀=32,128 at 1 Mb/s), direct PHY-trace measurement, and the reproduced non-monotonic throughput reversal near N≈40. `sim/dcf_ladder.py` retained as an independent cross-check. Papers in `docs/literature/`.
- **F8 fixed + deliberate re-freeze:** NS-3 sinks outlived the sources by 0.5 s on a 10 s window ⇒ every goodput was **~4.8 % high**. `ns3_matrix.csv` re-measured; with exact OFDM timing too, unicast↔Bianchi tightens **+1.8…+5.3 % → +0.6…−2.9 %**. New artifact `results/raw/ns3_dcf_residual.csv`; new entry points `make sim-ns3-matrix`, `make sim-ns3-dcf`.
- ⚠️ decisions: **RESOLVED** — (a) docs/02 §6a normatively specifies Ma & Chen's broadcast model, cited; (b) **D9 applied** — airtime is OFDM-symbol quantised everywhere (E5 energy +0.096 %, E3 goodput −2.1 %, headline unchanged); (c) correction banners on superseded audits; (d) the 10 s / PacketSocket drifts recorded. **Still open: F10 freshness (below).** Also (1) **docs/04 §1's 5–15× x86→ARM anchor** is unreachable (clock floor 2.61×) — restated per-cycle, needs blessing. (3) `[VERIFY]` citations in the paper. D6 wire freeze active.
- **F10 SETTLED (Mohamed, 2026-07-28): freshness is enforced AND optimized.** docs/02 §7's verb is *enforce*; the optimizer had softened it to "annotated, not filtered" and then discarded the result, so b=31 was reported at **1552 ms — 6.2× over D_max=250 ms**. Freshness is now a **hard constraint** (feasible 521→160) **and a 4th Pareto objective** (frontier 82→18). **Headline 96.77 % → 75.00 %** at b=4/200 ms — still ≫40 %, PASS. Closed form **b ≲ Λ·D_max** ⇒ at telemetry rates **freshness binds before the MTU**, which reframes T2/T5. Frontier b=1→4: 0/50/66.7/75 % cut at 50/100/150/200 ms. Sweep: `docs/audits/model_provenance.md`.
- **Deployment sensitivity measured (2026-07-28):** the "conservative lower bound" claim is now bounded, not asserted — realistic geometry gives **+42.9 % (50 m), +50.8 % (150 m), +13.9 % (300 m), −15.7 % (500 m)** vs the controlled scenario, so the idealised model is conservative only up to a ~300–400 m cluster and **optimistic beyond**. Fading costs 5–13 points. Artifact `results/raw/ns3_sensitivity.csv`, `make sim-ns3-sensitivity`. The co-design optimum is unaffected (bytes are channel-independent).
- **T2a (NEW theory result, 2026-07-28):** T2's amplification A=M/(M−H_f−g_a) is derived AT the MTU limit and **does not survive freshness-limited batching** — with b=⌊Λ·D_max⌋ independent of s, C(s)=s+(g_a+H_f)/b so **dC/ds = 1 exactly** (measured 1.0000 to 12 dp). Boundary: freshness binds iff s < (M−H_f−g_a)/(⌊Λ·D_max⌋+1) = **232.7 B on 802.11**, and every encoding here (45–191 B) is below it ⇒ **A=1.0745 never operative on the 802.11 arm**. On **LoRa (M=222)** the boundary is 19.7 B, the MTU binds, and **A=1.881 IS operative** — the low-rate leverage is real and *exclusive* to that arm, which strengthens docs/30. `optimizer.binding_constraint` / `effective_amplification`.
- **F11 RESOLVED analytically:** V_D(n)=P(all n frames arrive) ≤ P(one arrives)=1−p=V_B for **any** loss correlation (a joint cannot exceed a marginal), equality only at n=1. So independence is the **worst case for D** and T3's direction is correlation-independent. Gilbert–Elliott at matched p=0.05: V_D(n=2) 0.9025 → 0.9447 (burst 10) → 0.9498 (burst 160), asymptotic to 1−p, never reaching 0.95.
- **P3 RESOLVED:** the M/M/1 queueing term docs/02 §7 specified is implemented (`energy.queueing_delay_s`/`freshness_delay_s`); W_q≈1.2 µs so the optimum is unchanged, but implementing it exposed that the model had **no transmit-throughput constraint** — a station 12× oversubscribed (ρ≈11.9) used to be "feasible". ρ≥1 now ⇒ W_q=∞ and is filtered.
- Known issues: **FIXED/CLOSED — F1, F3, F8, F9, F10, F11, D9, and audit items P1/P2/P3 + A0–A12.** Still open: **F4** (cross-experiment record sizes differ ~4 % — single-seed vs 30-seed sampling; standardise on the 30-seed E1 mean±CI at P8), **F5** (32 B prev_hash carried per record — a stated modelling assumption, not a defect), **F6 mechanism** (why ECDSA is less portable to ARM; the ADX story was retracted — the measured 1.05× vs 1.60× cycles difference stands on its own and the thesis does not need the mechanism). Minor: `e4_crossover.png` missing from PROVENANCE.md. **⚠️ For Mohamed: the `[VERIFY]` citations in paper/main.tex and docs/TECHNICAL_NARRATIVE.md must be replaced with real references before submission** — domain-specific FANET/UAV-blockchain/VANET entries only; all foundational ones are verified.
