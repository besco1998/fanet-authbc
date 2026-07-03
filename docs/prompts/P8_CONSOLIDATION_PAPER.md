# P8 — CONSOLIDATION + PAPER  (COPY-PASTE WHOLE FILE)  — integrator, after SYNC-4
Needs everything (p4-done, p5-done, p6-done; p7-done if hardware ready) · ends: tag p8-draft ·
Eight Laws · PLAN MODE.

CONTEXT BUDGET — read: all frozen results/raw + results/hw + all docs/audits · docs/00 §3
(contributions) · docs/04 §5 (reporting standards) · docs/02 (theorems, for the paper proofs) ·
plus the research-archive positioning docs if present. Read results/audits; do NOT re-run frozen
experiments (D6).

OBJECTIVE: consolidate E1–E5 (+P7) into the thesis narrative and a build-clean IEEEtran paper
skeleton, with a final whole-repo audit and an honest limitations section.

NARRATIVE SPINE (map each result to its theorem):
overhead dominance (T1, E1) → batching cure + amplification A (T2, E2) → loss-robustness
frontier (T3, E3) → scheme-selection crossover (T4, E4) → co-design optimum + model validation
(T5, E5, NS-3) → hardware grounding (P7). One results table per research question (RQ1–RQ4 in
docs/00 §2). Headline success criterion (docs/04): optimized config cuts on-air auth bytes ≥40%
vs A+CBOR at V≥0.95 under p=0.05 — state whether it was met.

STEPS:
1. CROSS-AUDIT (final): verify every claim in docs/00 §3 maps to a frozen experiment and each
   experiment's audit is closed. Write docs/audits/final.md — whole-repo scientific + engineering
   attack: reproducibility from a clean clone, provenance complete, NO orphan/fabricated numbers,
   every model-vs-measurement gap explained. This is a Law-6 gate at project scale.
2. analysis notebook (or `make report`): consolidate all experiments into the spine above; one
   table per RQ; every number traced to results/PROVENANCE.md.
3. paper/ IEEEtran skeleton: sections wired to figures via PROVENANCE; theorems from docs/02
   WITH proofs; HONEST limitations section — small-N hardware, emulated vs real loss, x86↔RPi4
   gaps, no-consensus scope, single-arm/802.11 with LoRa as future work; related work from the
   archive with the doc-25 §7 differentiation; abstract written LAST. Novelty stated honestly
   (~6): a rigorous, hardware-validated optimization+measurement study — claim no new primitive.
4. `make figures && make paper` → the PDF builds clean from FROZEN raw. Commit
   paper/claims_map.md mapping every claim → experiment ID.
5. RESULTS VALIDATION at thesis scale (Law 6): re-state each headline number with its expected
   value/theorem, confirm the figure matches the frozen CSV, and confirm the success-criterion
   verdict is supported by the data (not asserted). Tag `p8-draft`; push; summarize for Mohamed:
   headline numbers, criterion met/not, and the venue recommendation.

ACCEPTANCE: final.md audit closed · report/notebook regenerates from frozen raw · paper PDF
builds · claims_map complete · limitations honest · results-validation at thesis scale done ·
tag pushed.

AFTER P8: the LoRa arm (research-archive doc 30) is the journal extension — same framework, ALOHA
+ quantized-Time-on-Air models, the feasibility-collapse results, 4× SX1262 hardware. Spin up a
new phase set only on Mohamed's go.
