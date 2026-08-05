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
- **Green:** 1107 fast + 14 frozen-gate tests (**1121**), `ruff` clean, **`mypy` clean (0 / 49 files)**, paper builds (**10 pp**, 0 undefined refs). `make all` exit 0.
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
- **The taxonomy to check new numbers against:** C1 small-sample mean vs threshold · C2 unverified constant on the measurement path · C3 threshold applied to a mean not a distribution · C4 config change perturbing the random realisation · C5 claim wider than the experiment. **Only C1 is fixed by more seeds.**

### The headline numbers, current
- **Total on-air bytes −58.68 %**, as a **decomposition** (placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral). ⚠️ **Never quote the bare 75 %** — it is algebraically **1 − 1/b**.
- **Adopted operating point: Λ=50 Hz, D_max=100 ms** (PX4 `MAVLINK_MODE_ONBOARD`, TS 22.125 compliant). Capacity **18→35** (U<1), **31→100** (V≥0.95). Relaxed (20 Hz/250 ms): 25/32→**103**, 55/88→**213**.
- ⚠️ **Do NOT say "≈3× holds across readings"** — the four combinations are **1.94× / 2.24× / 3.22× / 3.31×**. Quote the **range 1.9–3.3×**.
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
`docs/README.md` is the index. Findings **F1–F34** in `docs/audits/model_provenance.md`. Open items **only** in `docs/OPEN_ITEMS.md`. Trade-offs in `docs/TRADEOFFS.md`. Method and failed attempts in `docs/LOGBOOK.md`. **24 PDFs** in `docs/literature/` with each source's ROLE stated; `A3_CITATION_VERIFICATION.md` records how every citation was checked (Crossref by DOI).

### Deferred by Mohamed — plans written, DO NOT START unprompted
- **Mobility (E20)** — `docs/MOBILITY_PLAN.md`. **Separate NEW scenario files**, literature survey first. Not for the 802.11 arm (Bianchi/Ma&Chen have no position term).
- **Direction C** — the LoRaWAN frozen-phase artifact as a second short paper. Needs the full 56-paper survey (5 done) and a defensible jitter value.

### Accepted limitations, stated in the paper
E8 single SF · E10 half-duplex + full replication · E11 duty enforced at app level · E14 no capture · E15 static nodes · E12 propagation too optimistic · D5 cross-platform hardware (optional) · B5/C3/C5/C6.
