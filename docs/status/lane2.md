# Lane 2 (Models) — status / handoff log
> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions. **D7 resolved to serial execution — the parallel lanes described here were never used.**


## Handoff 2026-07-04 — phase P5b / E4 (lane 2)
- **Green baseline:** branch `lane2` **rebased on `p1-done` (e33a149)**, tag **`p5-done`** (this
  commit); `make all` = **773 passed**, ruff clean; `models/crossover.py` 100 % coverage. `p5a-done`
  tag still pins the pre-rebase P5a commits (history preserved).
- **Done this session (P5b / E4 — from MEASURED P1 timings):**
  - `models/crossover.py` — power-independent T4 crossover math (Δ(b), ΔRADIO, ΔCPU, κ\*=P_r/P_c,
    verify-throughput). Pure, hand-checked (`tests/unit/models/test_crossover.py`, 13 tests).
  - `experiments/e4/run_e4.py` — reads `p1_crypto.csv`+`p1_sizes.csv` → `results/raw/e4_crossover.csv`
    (80 rows, ρ×b×Λ, κ\* med+CI, verify-feasibility, winner) + `e4_bytes.csv`; provenance headers
    reuse `authbc.bench.provenance`.
  - `analysis/figures_e4.py` → `results/figures/e4_crossover.png` (κ\*(b) per ρ vs the plausible band).
  - Makefile `exp-e4` wired (**shared-file edit** — integrator confirms at the SYNC merge).
  - `docs/audits/p5.md` — P5b §Audit + Law-6 results validation (hand cross-check of κ\*).
- **Headline result (T4 confirmed):** **Ed25519 wins across the whole ρ×b×Λ grid on 802.11**;
  break-even needs P_r/P_c > **3.13** (ρ=1,b=32) up to 43 (ρ=0) ≫ plausible ≈0.2–0.5. BLS is also
  verify-throughput-**infeasible** below b=4 at Λ=2000. **Honest gap:** measured Ed25519 verify is
  **10.7×** cheaper than BLS single-verify, below doc-02 T4's "20–60×" — reported, not massaged.
- **Frozen this session (D6):** `results/raw/e4_crossover.csv`, `results/raw/e4_bytes.csv`
  (data-of-record; regenerate-from-raw only).
- **Open ⚠️ decisions awaiting Mohamed:** none new. Recorded decision: **absolute-joule E4 deferred
  to P7** (powers P_c/P_r need the ⚠️ D5 meter) — `p5-done` marks the crossover deliverable.
- **Next 3 steps:**
  1. Integrator: at the SYNC point merge `lane2` → `main` (carries `models/**`, `experiments/e4/**`,
     `results/raw/e4_*`, and the `exp-e4` Makefile edit), `make all`, tag, push.
  2. P7: plug MEASURED P_c, P_r into `models.energy.per_record` → absolute-joule E4 re-run (no new
     modeling; the model is already unit-tested).
  3. P6b (SYNC-3): P5a Bianchi + P3 framer-exported frame sizes feed the NS-3 validation.
- **Gotchas for next session:**
  - `exp-e4` is the **only shared-file edit** on lane2 — confirm it at the integrator merge.
  - κ\* is **Λ-independent** (Λ only gates verify-throughput feasibility) and **encoding-independent**
    (data bytes cancel); `H_a=0` is the BLS-best case (larger only helps Ed25519).
  - CI columns are monotone-propagated from P1 bootstrap CIs — the Ed25519 verdict holds even at the
    CI lower bound (κ\*_lo=3.03 at the min point).

## Handoff 2026-07-03 — phase P5a (lane 2)
- **Green baseline:** branch `lane2`, tag **`p5a-done`** (this commit), `make test` = **65 passed**,
  `make lint` = clean, **100 % line coverage** on `models/{bianchi,energy,optimizer}.py`.
  Base: `p0-done` (0275bf1). Env: WSL2 ext4, `.venv` Python 3.12.3, numpy 2.5.0 / scipy 1.18.0.
- **Done this session (P5a — spec-driven, no Lane-1 code):**
  - `models/bianchi.py` — damped DCF fixed-point solver (`p←0.7p+0.3p_new`, tol 1e-12) +
    802.11a OFDM slot/collision/airtime times (docs/02 §6). `solve(N,L)` → τ, p_c, P_tr, P_s,
    E_slot, throughput. `T_fx`=122 µs reconciled to the doc's ≈123 µs anchor.
  - `models/energy.py` — `per_record(cfg, measured)` = docs/02 §7 formula, per placement A/B/C/D;
    `n_frames` extension models block-level D over multiple frames (reduces exactly to the
    single-frame form at n=1). Refuses to fabricate BLS aggregate timings.
  - `models/optimizer.py` — exhaustive Pareto search over (e,σ,placement,b); constraints
    V≥1−ε (via n(b)), verify-throughput t_verify(b)·Λ≤1, MTU; D_max=250 ms as a soft annotation.
    Returns the FULL Pareto set. A modeled as the true naive baseline (b·g_a, no amortization).
  - Tests: three frozen Bianchi spot values (N=1 exact + N=5,50 via independent brentq),
    convergence at N∈{5,50,100}, S-vs-N shape, energy hand-calc per placement, 5-point Pareto toy
    (exact), constraint-filter cases (MTU / verify-throughput / over-aggregated-D verifiability).
  - `docs/audits/p5.md` — §Audit (1 medium fixed + 4 clean) + Law-6 results validation.
- **Frozen this session:** none. P5a emits no vectors/configs/CSVs (those bind at P5b). (D6 N/A.)
- **Open ⚠️ decisions awaiting Mohamed:** none newly raised by P5a. Project-level D7 (exec mode)
  is unaffected — P5a depended only on P0 and is mergeable under any mode.
- **Next 3 steps (P5b, gated at SYNC-2 = P1b measured timings on main):**
  1. Rebase `lane2` on `main` to pull `results/raw/p1_*.csv`; wire `make exp-e4`
     (**shared Makefile edit → coordinate at the sync point**, do not touch solo).
  2. `experiments/e4`: energy/rec from MEASURED t_* over σ × ρ∈{0,.25,.5,1} × Λ∈{50,200,800,2000},
     ≥30 seeds where stochastic; freeze CSV with config-hash + env header.
  3. Locate the Ed25519↔BLS crossover vs ρ, Λ; crossover table + figure; state T4's expectation
     (Ed25519 wins self-batch/802.11), compare honestly, cross-check one energy value by hand.
- **Gotchas for next session:**
  - Independent Bianchi cross-checks must bracket on **τ**, not p_c (p_c crosses the 2p_c=1
    singularity of τ(p_c) for N≳45); the production damped solver is unaffected.
  - Energy/optimizer take **dependency-injected** measured params — at P5b feed the real P1b
    CSV values, never guesses (Law 2/7). `Measured` needs t_agg_build/t_agg_verify for BLS (C).
  - D's latency omits the M/M/1 queueing term (documented) — add it with the real Λ sweep in P5b.
