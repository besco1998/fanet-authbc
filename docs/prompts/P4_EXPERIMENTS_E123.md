# P4 — EXPERIMENTS E1–E3  (COPY-PASTE WHOLE FILE)  — the first thesis figures
Lane 1 · weeks 3–4 · needs p3-done · ends: tag p4-done · Eight Laws · PLAN MODE.
⚠️ Once a config's data is collected it is FROZEN (D6): no silent re-runs over it.

CONTEXT BUDGET — read exactly: docs/02 T1,T2,T3 (claims under test) and §8 (stats) · docs/04
§2 (E1–E3 rows, baselines, success criterion) · docs/03 §3 (bench/experiments layout).

OBJECTIVE: frozen data + regenerable figures for E1 (dominance), E2 (batching cure), E3 (loss
frontier), each stamped with config hash + seeds; and the measured-vs-theory checks.

THEORY EXPECTATIONS INLINED (state these BEFORE running; deviations trigger Law 6):
- E1 (T1): auth fraction φ=g/(s+g), g=64 → JSON 15.2%, CBOR 33.0%, delta 61.5% (inline sigs).
- E2 (T2): per-record on-air bytes with self-batch ≈ s·A where amplification
  A = M/(M − H_f − g_a). For M=1500,H_f=40,g_a=48 → A ≈ 1.033; batching drives φ down to
  ≈ (g_a+H_f)/M ≈ 5.9%. Measured A within 5% of the formula, else investigate.
- E3 (T3): frame-level (B) verifiability V_B = 1−p (each frame self-verifiable); block-level
  (D) V_D = (1−p)^{n(b)}, n(b)=⌈(b·s+g_a+H_f)/M⌉. B Pareto-dominates D for all V > (1−p)^2.
  If robustness target ε ≤ p, D beyond one frame is infeasible.
- Baselines everywhere: A+JSON (naive), A+CBOR (Pillar-1-only), D over-aggregated (b=40).
- Thesis success criterion (for the P8 narrative): optimized config cuts on-air auth bytes
  ≥40% vs A+CBOR at V≥0.95 under p=0.05.

STEPS:
1. experiments/e{1,2,3}/config.yaml (seeds 1..30; sweeps exactly per docs/04 §2) + shared
   runner.py stamping config hash + env header on every row.
2. Run E1 → bytes/rec + φ for 4 encodings × inline. Freeze CSV.
3. Run E2 → placement A vs B × encodings × M∈{256,576,1500}; compute measured A; compare to
   the inlined formula.
4. Run E3 → B vs D, b∈{1..40}, p∈{.02,.05,.10}, ≥30 seeds; record measured V and goodput.
5. RESULTS VALIDATION (Law 6, §Validate-Results) BEFORE plotting: for each experiment write
   the expected value/shape (inlined above), then compare; sanity gates (φ,V∈[0,1]; V_B flat
   in b; V_D decreasing in b; A within 5%); cross-check one point by hand; determinism +
   provenance. Any surprise (e.g., measured V_B not flat, or A off) ⇒ reproduce, hypothesize,
   explain-or-debug; if still ambiguous, raise to Mohamed. Write it into audits/p4.md.
6. analysis/figures_e123.py (reads ONLY results/raw): E1 bar(φ); E2 φ-vs-b with the A-theory
   overlay; E3 measured-V-vs-theory overlay + the (bytes,V) Pareto plot showing B dominating
   D above V=(1−p)^2. Captions: config hash, seeds, CI type. results/PROVENANCE.md rows for
   every figure.
7. AUDIT P4 (§Audit): bootstrap-CI correctness (test on a known distribution), seed
   independence (no shared RNG across configs), unit/axis errors, any measured-vs-theory gap
   left unexplained, baseline fairness (same records/seeds across encodings). Fix → regenerate
   figures (must be byte-stable from frozen raw) → tag `p4-done` → push → §Handoff.

ACCEPTANCE: E1–E3 raw frozen with provenance · figures byte-stable via `make figures` ·
measured A and V match theory or documented · results-validation subsection in audits/p4.md ·
tag pushed.
