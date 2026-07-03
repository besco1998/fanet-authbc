# Lane 2 (Models) — status / handoff log

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
