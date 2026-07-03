# P5 — MODELS + OPTIMIZER + E4  (COPY-PASTE WHOLE FILE)  — LANE 2 ENTRY (parallel to P1–P4)
Needs P0 (P5a); p1-done (P5b/E4) · ends: tags p5a-done, p5-done · Eight Laws · PLAN MODE.

IF PARALLEL: this runs in the Lane-2 worktree (../fanet-authbc-lane2, branch lane2) in a
SEPARATE Claude Code session. You OWN ONLY: src/authbc/models/**, tests/unit/models/**,
experiments/e4/**, results/raw/e4*, analysis/figures_e4.py (docs/07 §3). Touch nothing else.
Re-read the repo CLAUDE.md first.

CONTEXT BUDGET — read exactly: docs/02 §6 (Bianchi — normative), §7 (energy/latency), T4, T5 ·
docs/03 §3 (models/ spec) · docs/04 §2 (E4 row) · docs/06 §3. You do NOT need ledger/placement
internals — only P1b's measured outputs (at SYNC-2).

KEY FACTS INLINED:
- Bianchi DCF fixed point: τ = 2(1−2p_c)/[(1−2p_c)(W+1)+p_c·W(1−(2p_c)^m)], p_c=1−(1−τ)^{N−1},
  with W=16, m=6. SOLVE WITH DAMPING p←0.7·p+0.3·p_new, tol 1e-12 — the UNDAMPED iteration
  OSCILLATES at high N; your unit test must assert convergence at N∈{5,50,100}. Throughput
  S = P_tr·P_s·E[payload]/E[slot] (standard). Expected shape: S roughly flat / slowly varying
  in N once saturated (NOT wildly non-monotonic — if you see a dip-then-rise, suspect the
  solver, per the project's earlier debugging history).
- Energy per record: E = P_c·(t_enc + t_sg/b + t_ver_amort(b)) + P_r·T_air(frame)/b, where the
  receiver verifies once per frame in B so t_ver_amort = t_vf/b (implement per placement;
  comment each term + unit).
- T4 crossover (the headline of E4): for OWN records (self-batch) Ed25519 and BLS cost ~equal
  bytes but Ed25519 verify is ~20–60× cheaper ⇒ Ed25519 SHOULD win on 802.11. BLS's win is for
  RELAYED records: it saves Δ(b)=64−(48+H_a)/b bytes/record but costs extra CPU; BLS is
  energy-optimal iff P_r·8·Δ(b)/R > P_c·Δt. At R=6 Mb/s the radio side ≈ P_r·75 µs vs CPU side
  ≈ P_c·(1–3 ms) ⇒ EXPECT Ed25519 to win across 802.11; state clearly if the data disagrees
  (that is a finding to investigate, not to massage).

P5a STEPS (spec-driven — needs NO Lane-1 code):
1. models/bianchi.py: damped solver. Unit tests: (a) converges at N∈{5,50,100}; (b) matches
   THREE spot values you compute by hand and paste into the test; (c) document S-vs-N shape.
2. models/energy.py: per_record() exactly as inlined; unit test with synthetic measured values
   → hand-checked expected energy.
3. models/optimizer.py: EXHAUSTIVE search over (e,σ,placement,b) (≤~2000 points); constraints
   V≥1−ε via n(b), verify-throughput t_verify(b)·Λ≤1, D_max=250 ms soft; return the FULL Pareto
   set (bytes,energy,V). Unit test on a 5-point hand-checkable toy that the Pareto set is exact.
4. RESULTS VALIDATION (Law 6): Bianchi outputs — τ,p_c∈[0,1]; S below the 6 Mb/s PHY ceiling;
   the three hand values match; S-vs-N shape sane. Optimizer — the toy Pareto set is provably
   correct. Write into audits/p5.md. AUDIT P5a (§Audit). Fix → tag `p5a-done` → push lane2 →
   announce SYNC-2 readiness.

P5b STEPS (at SYNC-2: rebase lane2 on main to get results/raw/p1_*.csv):
5. experiments/e4: energy/rec using MEASURED t_* (never guesses); sweep σ × relay-fraction
   ρ∈{0,.25,.5,1} × Λ∈{50,200,800,2000}; ≥30 seeds where stochastic. Freeze CSV.
6. Locate the Ed25519↔BLS crossover vs ρ and Λ; crossover table + figure. RESULTS VALIDATION
   (Law 6): state the inlined T4 expectation (Ed25519 wins self-batch/802.11), compare, and if
   the data disagrees investigate the cause and report it honestly. Cross-check one energy
   value by hand from the model.
7. AUDIT P5b; `make all`; tag `p5-done`; push; §Handoff.

ACCEPTANCE: Bianchi/energy/optimizer unit tests green (incl. hand values + Pareto toy) ·
`p5a-done` early · E4 CSV + crossover artifacts · T4 tested & reported honestly · results-
validation in audits/p5.md · tags pushed.
