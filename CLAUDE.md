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
- **NEXT SESSION: read `docs/NEXT_STEPS.md` first** — prioritised work plan, strategy decision, and decisions not to re-litigate.
- ⚠️ **Repo is PUBLIC and history was REWRITTEN** to purge the 84 MB vendored NS-3 tree. **The remote is authoritative — never force-push an older local branch over it.** Copyrighted PDFs in `docs/literature/` stay by Mohamed's decision (risk accepted, `DECISIONS.md`).
- **Phase: P8 audit complete. COMMITTED AND PUSHED** to branch `p8-audit-and-corrections`. Work from any machine: `git clone`, `git checkout p8-audit-and-corrections`, `make setup && make all`.
- **Green:** 1184 fast + **24** frozen-gate tests (**1208**), `ruff` clean, **`mypy` clean (0 / 49 files)**, paper builds (**14 pp**, **45 refs**, 0 undefined, abstract **265 w**). `make all` exit 0.
- **METHODOLOGY (Mohamed):** this is an optimization problem — *state everything, choose what to stick with, state the trade-offs for every decision*. **`docs/TRADEOFFS.md` is required reading before quoting any number.**
- **LICENSE = all rights reserved** (© 2026 Mohamed A. Farouk). Vendored NS-3 + `signetlabdei/lorawan` stay GPLv2, **not** redistributed.

### Hardware 802.11 channel validation — DONE 2026-08-05 (F35), the 802.11 arm is no longer simulation-only
- Two-Pi ad-hoc IBSS, **5 GHz ch 36**: broadcast **link loss p = 2.3 × 10⁻⁴** (99.9773 % pooled, 8 windows, σ = 0.024 pp, 0 duplicates) and **airtime 1.995 ms/frame vs 1.99 ms predicted** — an independent check on the 802.11a timing constants under Bianchi and Ma & Chen.
- ⚠️ **One transmitter ⇒ zero contention. This does NOT validate Ma & Chen** — that stays simulation-only.
- ⚠️ **Use 5 GHz, never 2.4 GHz.** A first 2.4 GHz sweep gave a tidy 97.45 % that was **saturation at the 802.11b 1 Mb/s broadcast basic rate**, not channel loss. Caught by the pre-stated prediction plus a load sweep; kept labelled as `adhoc_sweep_2g4.csv`.
- ⚠️ `eth0` still has **no carrier** on either Pi — every session severs its own SSH path and relies on the deadman + reboot timer. **Never put a deadman marker in `/tmp`** (systemd `PrivateTmp`). Plugging in ethernet removes the whole risk class.

### Mobility (E20) — ANSWERED 2026-08-05 (F36 + F37): measured, and the effect is null
- Survey pilot in `docs/MOBILITY_SURVEY.md`; scenario `ns3/authbc-lora-capacity-mobile.cc` (separate new file), driver `ns3/run_lora_mobility.py`, artifact `results/raw/lora_mobility.csv` (140 runs).
- **ANSWERED (F37): mobility does NOT change the LoRa capacity result.** 30 seeds under **goursaud** (capture, the physical model): Gauss-Markov 5 m/s **−0.24 pp**, G-M 20 m/s **−0.03 pp**, RWP 20 m/s **+0.36 pp** vs static — every arm within **0.06 σ**, |t| ≤ 0.22, at 816–967 m mean displacement. Under **aloha** all four arms are **byte-identical** (mobility structurally cannot act). **Same conclusion under both matrices, which is what makes it robust.** So C3's static assumption is **tested**, not merely excused.
- **Both Law-8 questions are now settled empirically, not by preference:** we ran *both* matrices (conclusion identical), and *both* mobility models — **Gauss-Markov and RWP are statistically indistinguishable** (0.06 σ apart), so the "not Random Waypoint" argument in `MOBILITY_PLAN.md` §M1 carries no weight in this result.
- ⚠️ **Per-frame Doppler is still unmodelled** (~50 coherence intervals inside one 364 ms LoRa frame). The null result means "mobility does not change *collision-limited capacity*", NOT "mobility is harmless to a LoRa link".
- ⚠️ **The confound that nearly produced a false 5-point mobility penalty:** ns-3 assigns RNG streams by creation order, so installing a mobility model shifts every sender's stream. Fixed by pinning sender streams per node id. `ns3/run_lora_mobility.py --verify` asserts **two** properties before any sweep: `--pinStreams=false --speed=0` reproduces the frozen scenario bit-identically, and pinned `aloha` arms are all equal.

### ⚠️ Scientific-implementation audit 2026-08-05 — read `docs/audits/scientific_implementation_audit.md`
- ⚠️ **S3 — `N_max` was certified on a MEAN, not a distribution.** At the certified N=3, **9 of 30 seeds fail** V≥0.95. Correct reporting: **N_max = 3, 95 % CI [2, 3]** (knife edge). Under a **per-realisation** reading (≥95 % of runs meet V) it is **1**. ⚠️ **Which criterion the paper quotes is Mohamed's decision** — both are emitted (`lora_capacity_ci.csv`).
- ⚠️ **S7 — `make sim-ns3-delay` did not reproduce `ns3_delay.csv`** (defaults stopped at U=1.34 vs the artifact's 6.69). Fixed. ⚠️ **U ≈ 2.435 is an INTERPOLATION** between measured U=2.23 and U=3.34 — label it as such.
- **S4** delay driver now emits min/max/σ (it was means-only, against the project's own post-F30 standard). **O5** `channel_utilisation` no longer returns 0.0 at N=1 — and ⚠️ **a unit test had asserted that defect**.
- **S5 checked CLEAN:** F25/E9/A2 are **not** RNG-confounded (`sent` invariant). Guarded by `make verify-rng-isolation`.
- **DECISION (Mohamed, 2026-08-06): report BOTH criteria, headline the mean.** Paper table now has three N_max columns (U<1 / V≥0.95 mean / V≥0.95 per-run) and a paragraph explaining why. **The co-design ratio survives either reading** — every combination lies in 1.9×–3.3×.
- ⚠️ **CORRECTED stale numbers:** the paper's `tab:envelope` V≥0.95 column still held the pre-F30 crossing — **233/116, now 213/100** — while the prose already said 213/100. Two ratios were stale too: **3.31→3.23** and **2.24→2.42**. The four combinations are now **1.94× / 2.42× / 3.22× / 3.23×**; quote the range **1.9–3.2×**.
- **Drift is now impossible:** `tests/test_paper_matches_artifacts.py` parses the LaTeX table and compares every cell to `capacity_envelope.csv`.
- **O2 CLOSED — `p` is not load-bearing.** The optimizer picks `delta/ed25519/B, b=4` at *every* feasible p (2.3e-4 → 0.05). ⚠️ But feasibility needs **p ≤ ε identically**, so p=ε=0.05 has **zero model margin**; hardware (F35) puts the real link ~200× inside it.
- **O4 CLOSED — the unicast small-frame bias is the anomalous slot.** Predicted bound −3.32 % (72 B) → **−0.44 % (1400 B)** against measured −2.60 % → **−0.40 %**: right sign, bounded everywhere, and the 1/T_s scaling matches over a 20× frame range. Broadcast is unaffected (±0.21 % at 72 B), so the headline is untouched.
- ⚠️ **NEW S8 — no committed generator for `lora_phase_artifact_*.csv`.** The 300 runs behind Direction C cannot be regenerated. Also fixed: `analyse_phase_artifact.py` had a **hardcoded agent-scratchpad path**.
- **F38 — the last six 3-seed artifacts are gone.** All re-run at 30 seeds with jitter and dispersion. ⚠️ **A2's capture table is CORRECTED**: +3.3→**+2.7 pts** at N=8, 1.36×→**1.29×** at N=50. The ALOHA baseline at N=50 moved **0.2532→0.3755** (48 % relative) because those runs were frozen-phase as well as 3-seed. A2's conclusion survives; its numbers did not.
- **Confirmed, not moved:** E9's EU `N_max = 8` holds ⚠️ **but 95 % CI [5, 8]** — never quote it bare. F25's shadowing null holds and is now *structural*: under `aloha`, radius and shadowing act only through power, which cannot matter (F36) — `shadow500` and `repro` returned **byte-identical** bootstrap distributions. 802.11 geometry sensitivity moved ≤2.93 pp.
- ⚠️ **Three provenance defects fixed:** `config_hash` could not distinguish its own runs (shadow500/shadow1000/repro shared one hash); `sensitivity.py` recorded `ns3_version=3.41` while running **3.48**; its `--seeds` default was still 3.
- **S8 closed** — `make sim-lora-phase-artifact` regenerates Direction C's 300 runs. ⚠️ **NEW S9**: that artifact cites a pre-registration file `scratchpad/C1_EXPECTATIONS.md` **not in the repo**, so its pre-registration claim is unverifiable.
- ⚠️ **F39 — the four-axis "co-design" claim was OVERSTATED, now precise.** Factorial ablation: **placement×batching couple exactly** (benefit is `g_a(1−1/b)`, so **exactly zero at b=1** — A and B are byte-identical on a single-record frame), **encoding is perfectly separable** (every interaction exactly 0; `s` is additive so it *cannot* interact), scheme is byte-degenerate. The old "smaller payload increases the value of batching" line was a **ratio-scale artifact**: the absolute saving is **81.0 B for every encoding**. Abstract/intro/Related-Work corrected. ⚠️ Note `1−1/b` is the same term as the bare-75 % warning — the coupling and the flattering headline are the same algebra. **No number moved.**
- **F40 — S9 closed by WITHDRAWING a pre-registration claim**, not reconstructing it: writing an expectations file after the results are known would manufacture evidence. F32/F33 stand as ordinary analyses.
- **PQC projection** (`make exp-pqc`): ML-DSA **9.2×**, SPHINCS+ **28.1×** per record; batching cannot rescue it — freshness caps b at 5 and an ML-DSA signature **+ header (2464 B) exceeds the 1500 B MTU alone**. Projection only, prior art cited.
- **References 29 → 39 rendered.** ⚠️ Short of the 45–60 target **deliberately**: 39 is every held source that has been *read*. `arxiv2309.15340` is a **Chinese-language paper we cannot read**; `sensors2025_...` is still `TOREAD`. Padding would repeat the failure this audit removed.
- ⚠️ **IDEA/FRAMING audit 2026-08-07 — the first pass to question the premise, not the numbers.** Four framing defects, and the pattern is the same one that produced every earlier contradiction: **prose no test compares against anything.**
  - **I1** the paper disagreed with itself about its own best contribution — the abstract filed the payload-exclusion result under "applications of established results", the conclusion called it "the more durable contribution". **Promoted to first result**, because it is *arithmetic*: 64 B does not fit in 51 B, so unlike every performance number here (four of which this audit moved) **it cannot drift**.
  - **I2** the conclusion said "≈3× stable under either threshold" — the phrasing this file forbids, contradicting §Results in the same paper, and wrong (**3.22× vs 2.42×**). Fixed.
  - **I3** the abstract was **693 words** (IEEE Access ~250) and defensive: more words qualifying than claiming. Rewritten to **267**, ordered exclusion → feasibility → bytes. ⚠️ **The rewrite deleted an honesty disclosure** (the criterion's verifiability half is satisfied *by construction*) that lived only in the abstract — restored to §Results, expanded. Improving impact silently removed a self-criticism; caught only by checking.
  - **P1 CHECKED AND TRUE:** the pre-registration is real and third-party verifiable — criterion in `3354ec1` (2026-07-03), result in `a51486a` (2026-07-05). Unlike S9, this one survived scrutiny.
  - **P2** "all results are reproduced by an automated staleness gate" covered **16/41**. Four ungated artifacts were pure model computation — **gated rather than the sentence softened** (frozen suite 14 → 18). Every remaining ungated artifact now has a stated reason.
- **DIRECTION C IS RETIRED as a second paper (Mohamed, 2026-08-07)** — folded into the main paper as a methods contribution in §Reproducibility: the traffic model inflates CV **2–8×**, which is *why* every capacity figure is 30 seeds with a distribution. Protocol/harness/artifact kept for resumption.
- ⚠️ **DIRECTION C, 2026-08-07 (F42) — two self-corrections, both from pre-registering the protocol first.**
  - **The protocol was committed BEFORE any data** (`docs/DIRECTION_C_SURVEY_PROTOCOL.md`, `eb3eda5`, data-free) — the F40 lesson applied. Harness `make survey-direction-c`; artifact `results/raw/direction_c_survey.csv` with every keyword hit adjudicated in writing.
  - ⚠️ **The phenomenon has PRIOR ART.** Durand & Booysen 2025 attribute their own bimodal delivery to nodes that "always transmit on a specific SF, time, and channel", giving "certain packet collisions being repeated for every transmission cycle". **Direction C did not discover the frozen-phase artifact.** What remains ours is the *quantification* (2–8× CV inflation) and the link to replication reporting. Any draft saying it is unobserved must be corrected.
  - ⚠️ **"9 of 9" was inflated and is RETRACTED.** Under the pre-registered inclusion criteria only **4** papers qualify (Bor used **LoRaSim not ns-3**; Mehta is a **survey**; Bhatt is **802.11ah not LoRa**). Honest baseline: **4/4 report no replication.** The paper said "nine studies" for a few hours today; corrected.
  - ⚠️ **UNREADABLE (<2000 chars extracted) is EXCLUDED from the denominator** — scoring a scanned PDF as "reports nothing" would manufacture support for our own hypothesis. Zirak extracts 5 characters.
- **The taxonomy to check new numbers against:** C1 small-sample mean vs threshold · C2 unverified constant on the measurement path · C3 threshold applied to a mean not a distribution · C4 config change perturbing the random realisation · C5 claim wider than the experiment. **Only C1 is fixed by more seeds.**

### ⚠️ PAPER FRAMING CHANGED 2026-08-07 — feasibility boundary, not co-design optimization
- **Retitled** *"Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound, a Capacity Envelope, and Hardware Validation"*. §Results opens with **three boundaries ordered by durability**: impossible (arithmetic, cannot move) → capacity-limited (1.9–3.2×) → runs (58.7 %, now the *mechanism*, not the headline).
- **Rationale:** as a co-design paper the work is mid-tier (the optimisation is closed-form; F39 found one real interaction). As a boundary paper the same evidence is stronger — **an impossibility cannot drift, and four performance numbers here did.** ⚠️ Do not revert without re-reading F39 and F42.
- **Second paper: `paper/methods.tex`** (`make paper-methods`, 2 pp) — the five-class defect taxonomy as a methodological note in the Kurkowski 2005 / SIGCOMM-CCR 2018 credibility lineage. Self-audit by design: 10 results moved, only 4 catchable by seeds, 2 protected by passing tests, 3 paper-vs-artifact contradictions.

### The headline numbers, current
- **Total on-air bytes −58.68 %**, as a **decomposition** (placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral). ⚠️ **Never quote the bare 75 %** — it is algebraically **1 − 1/b**.
- **Adopted operating point: Λ=50 Hz, D_max=100 ms** (PX4 `MAVLINK_MODE_ONBOARD`, TS 22.125 compliant). Capacity **18→35** (U<1), **31→100** (V≥0.95). Relaxed (20 Hz/250 ms): 25/32→**103**, 55/88→**213**.
- ⚠️ **Do NOT say "≈3× holds across readings"** — the four combinations are **1.94× / 3.23× / 3.22× / 2.42×**. Quote the **range 1.9–3.2×**. (Recomputed 2026-08-07 from `capacity_envelope.csv`: Λ=50 U<1 18→35, V 31→100; Λ=20 U<1 32→103, V 88→213. The board previously said 2.24/3.31 and "1.9–3.3×" — both wrong; guarded now by `test_abstract_ratio_range_matches_artifact`.)
- **LoRa `N_max` = 3** (not 5), and only within **≈500 m**. Composed with measured link loss, **V≥0.95 admits no multi-node network**; V≥0.90 restores 3.
- **Validation, 30 seeds:** unicast **+1.29/−0.40 %**, broadcast goodput **±0.51 %**, crossing **U=2.435**. ⚠️ Unicast has a real **−1.4..−2.6 % bias at 72 B** — quote the band as measured at 1400 B.

### ⚠️ THE PATTERN of the whole audit — read this before trusting any new number
**Four headline numbers were distorted by small-sample means against thresholds. NONE was a modelling error; every one was sampling.** Drivers now default to **30 seeds** and emit min/max/σ. Before reporting any threshold crossing, look at the *distribution*.

### External baselines (A7 closed)
- **Bor et al. 2017 implemented** (`lora.bor2017_loss_pct`), validated against their own four figures: **their N_max=4 vs our 3**; closed-form periodic ALOHA also gives 3.
- **Zirak et al. 2021** — the only **hardware** air-to-air LoRa PDR-vs-range data; it range-limits our result.
- **CLAS (F34).** ⚠️ **The finding is the AXIS, not the ratio:** every published CLAS overhead is **linear in message count** (583–859 B/rec) because aggregation compresses the *verifier's work*, not the wire; ours is **80.1 B/rec** with certificates charged at the standards policy (162 B every 5th frame, NDSS 2024). **Do NOT claim we beat CLAS** — they buy conditional privacy we do not offer, and their group element is 128 B vs our 64 B.
- ⚠️ **METHOD RULE:** the certificate-byte term was added **BEFORE** the CLAS numbers were fetched. Doing it after would have been fitting the correction to the answer. Defaults are 0/1 so frozen artifacts stay bit-identical.

### Retractions, kept visible
**T7** (capacity excludes at U≥1) · **F15** (the ≤0.36 % validation) · **F18** (I claimed we were the *more optimistic* model vs Bor — I quoted their **pure-ALOHA** figure as their LoRa result). ⚠️ **Quoting the PDF is not enough: quote the FIGURE.**

### Where things live
`docs/README.md` is the index. Findings **F1–F42** in `docs/audits/model_provenance.md`. Open items **only** in `docs/OPEN_ITEMS.md`. Trade-offs in `docs/TRADEOFFS.md`. Method and failed attempts in `docs/LOGBOOK.md`. **24 PDFs** in `docs/literature/` with each source's ROLE stated; `A3_CITATION_VERIFICATION.md` records how every citation was checked (Crossref by DOI).

### Deferred by Mohamed — plans written, DO NOT START unprompted
- **Mobility (E20)** — `docs/MOBILITY_PLAN.md`. **Separate NEW scenario files**, literature survey first. Not for the 802.11 arm (Bianchi/Ma&Chen have no position term).
- **Direction C** — the LoRaWAN frozen-phase artifact as a second short paper. Needs the full 56-paper survey (5 done) and a defensible jitter value.

### Accepted limitations, stated in the paper
E8 single SF · E10 half-duplex + full replication · E11 duty enforced at app level · E14 no capture · E15 static nodes · E12 propagation too optimistic · D5 cross-platform hardware (optional) · B5/C3/C5/C6.
