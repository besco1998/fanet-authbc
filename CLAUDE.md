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
pyproject (cbor2==5.8.0 is deliberate); NS-3 **3.48** from source (docs/06 §2; migrated from 3.41 — see paper §Limitations); GitHub via
`gh`, private repo, conventional commits, push at green checkpoints, tag `p<N>-done`.

## Style
Small pure functions; every module docstring cites the docs section it implements;
type hints; no dead code; comments explain WHY, not what.

## Current status board (agent updates this section every session)
- **NEXT SESSION: read `docs/NEXT_STEPS.md` first** — prioritised work plan, strategy decision, and decisions not to re-litigate.
- ⚠️ **Repo is PUBLIC and history was REWRITTEN** to purge the 84 MB vendored NS-3 tree. **The remote is authoritative — never force-push an older local branch over it.** Copyrighted PDFs in `docs/literature/` stay by Mohamed's decision (risk accepted, `DECISIONS.md`).
- **Phase: P9 — revision after the supervisor's review (2026-10).** Branch `p9-supervisor-revision`, cut from `p8-audit-and-corrections`. Work from any machine: `git clone`, `git checkout p9-supervisor-revision`, `make setup && make all`.
- ⚠️ **`make all` green on this machine is NOT the claim — CI green is** (2026-10-08: the gate passed here and failed on a clean install over an undeclared package). **Before every push run the WHOLE of `make all VENV=<a venv built from pip install -e '.[dev]' alone>`** — never a hand-picked subset of tests (the fix for that failure broke the build again exactly that way: a figure was regenerated and its copy in `thesis/` was not) — and do not say green until CI on the pushed commit has finished. Guards: `tests/test_declared_dependencies.py`, and no figure may embed a library version.
- ⚠️ **TWO COPIES OF THIS FILE EXIST.** Sessions that start in `~/authbc_package` auto-load `~/authbc_package/CLAUDE.md`, which is an OLD copy. **This file, in the repository, is the status board.** A stale count read from the other one was "corrected" into the thesis on 2026-10-06 and had to be reverted.
- **Green:** 2025 fast + **39** frozen-gate tests (**2064**), `ruff` clean, **`mypy` clean (0 / 57 files)**, paper builds (**10 pp**, **38 refs**, 0 undefined, 0 overfull, abstract **179 w** by the board's counter, about 190 as printed), methods paper 4 pp, thesis **119 pp** (54 refs, 0 overfull, 3 markers left — all Mohamed's). `make all` exit 0.
- **METHODOLOGY (Mohamed):** this is an optimization problem — *state everything, choose what to stick with, state the trade-offs for every decision*. **`docs/TRADEOFFS.md` is required reading before quoting any number.**
- **LICENSE = all rights reserved** (© 2026 Mohamed A. Farouk). Vendored NS-3 + `signetlabdei/lorawan` stay GPLv2, **not** redistributed.

### ⚠️⚠️ OCTOBER 2026 — THE DESIGN WAS BUILT, AND THREE HEADLINE RESULTS CHANGED. READ THIS FIRST

**Mohamed's supervisor reviewed the paper. Every statement of the review held; behind several of
them was one cause it did not name: the headline design was a SUM OF SIZES and had never existed
as a frame** (a record size from one module, a header measured on frames of another encoding, a
signature length). Findings **F45–F71**; method and wrong turns in the top entry of
`docs/LOGBOOK.md`; decisions **R1–R18** in `docs/DECISIONS.md`; what is open in
`docs/OPEN_ITEMS.md` §G.

**What exists now that did not:** a second frame format (`placement/wire_v2.py`, "lean") with a
sender and a receiver (`session_v2.py`); one definition of a frame (`models/frame.py`) held equal
to emitted frames by a test; nine experiments on it (E9–E17, `make exp-frames`); a direct ns-3
capacity search (`make sim-ns3-nmax`); **and no typed results** — `analysis/paper_numbers.py`
writes every number the paper prints into `paper/numbers.tex` and stops if an artifact no longer
supports a sentence. ⚠️ The first format (`wire.py`) and every pre-October artifact are untouched
and bit-identical (D6).

**What it cost — everything below this section that contradicts these is SUPERSEDED:**

| below, you will read | what is true |
|---|---|
| total bytes **−58.68 %**, 72.0 B/record | that design verifies **0.881** of its records at p = 0.05, not 0.95 (F46: a delta-coded frame needs its predecessor). With a keyframe in every frame: **74.96 B (−56.98 %)** first format, **43.25 B (−70.33 %)** lean format |
| "**three** of seven" (or "four") EU868 rates excluded; F44; `wire_profile.py` | **F44 is WITHDRAWN** and the file deleted. **Eight of twelve** EU863-870 data rates cannot carry one self-contained, chained, signed frame — five by the signature alone, three by header + link + signature (F47). Four stated conditions |
| capacities 31→100, 88→213, ratios "1.9–3.2×" from the ceiling **U = 2.435** | **the ceiling is not N-invariant (F50; a pre-registered ±10 % prediction FAILED).** Capacities are simulated per configuration, 30 seeds, bootstrap interval — quote them from `results/raw/design_ladder.csv`, never from the ceiling |
| "ratios are protected by construction" | **withdrawn** — the ceiling's error depends on the frame and does not cancel |
| "Bor et al." | **Haxhibeqiri, Van den Abeele, Moerman & Hoebeke** (F49). Renamed everywhere |

### ⚠️ 2026-10-09 — "solve all the issues": what closed, and what needs a browser or the boards (F68–F71)

- **Contention on radios is REGISTERED, not measured (F70).** Registration `456a4e7`,
  `docs/CONTENTION_HW_EXPECTATIONS.md`; kit in `hw/channel/` (`run_adhoc_contention.sh` — ⚠️ never
  run on hardware, use `probe` first); `analysis/contention_hw.py --predict|--ns3-check|--commands|--reduce`.
  **If the boards answer `ssh pi@<addr>`, the agent can run it** — two Pi 4 suffice for the sharp
  case (no third radio, so no capture). Predicted loss with two boards: 0.29 / 0.64 / 1.40 %.
  ⚠️ The event model is **9–18 % above ns-3 at N = 2** (agrees within 5 % at 3–5): a bias at the
  smallest network, inside the registered band.
- ⚠️ **"n messages cost n times one" was true of one link only (F68).** Aggregate-signature
  schemes: each signer still sends its own full message (583–859 B), but the *aggregator*
  forwards a compact aggregate (Wang et al.: 388 B single, 784 B for a hundred). Say which link.
  Batching = placement B (own records); aggregation = placement C (an intermediary).
- **Superseded figures and the old envelope table are in thesis Appendix C**, not in the results
  chapters. `sec:envelope-history`, `tab:envelope`, `fig:e5`, `fig:lorachain` live there.
- **`one_period_ms(fps)`** in the ns-3 driver: 1000/fps can exceed the scenario's one-period
  guard by one ulp (116 frames/s aborted, F69). Never pass 1000/fps directly.
- **Sources:** 54 in the thesis, 38 in the paper; 14 held locally. ⚠️ Publishers (Springer,
  Hindawi/Wiley, SAGE) and CORE refuse scripted download even of CC BY papers — **do not work
  round it**; list the DOI for Mohamed (G23, G24). A long source read in part is recorded as
  such in `docs/literature/README.md`.
- ⚠️ **To split a working tree into two commits, do not edit a file after `git stash
  --keep-index`** — it conflicted on pop (three count lines; resolved, verified identical).

### ⚠️ 2026-10-08, later — the built paper and thesis audited whole (F63–F67). READ BEFORE EDITING EITHER

Mohamed asked that both be "strong and complete". Both were read from the built PDFs, end to end.
- **No result moved.** The paper had twelve defects of presentation (F63): four references with
  no identifier, a table whose total and margin did not add up, "124 neighbours" for 124 *nodes*,
  the generator's 50 ms spacing unexplained against a 20 ms operating point (now a test).
- ⚠️ **N counts NODES.** A neighbourhood of N nodes; each hears N−1. Never write "N neighbours".
- ⚠️ **The thesis held typed statements that were wrong or stale (F64):** T2a's boundary is
  **232.0 B** (not 232.7 — that was H_f = 40) and 22.3 B at M = 242; batching needs
  **Λ > 2/D_max**; ch. 12 contradicted ch. 7 in four places. **A corrected chapter does not
  correct the chapters that summarise it** — after any change to ch. 7–10, re-read ch. 1, 11, 12.
- ⚠️ **The derivation of F58 had prior work and no search had been made (F65)** — Cao et al.,
  arXiv:2102.07023: the *tie* mechanism for periodic 802.11p broadcast. Credited in paper and
  thesis; ours adds the detection window, the ns-3 comparison and registered predictions.
  **Search BEFORE deriving. This was F9 a second time.**
- **Energy (F66):** ratios and the meter-vs-model gap are sound; the sensor was **never
  calibrated against a reference load**, so absolute µJ values carry its unmeasured gain error.
  Step 0 of `hw/BENCH_SESSION.md`.
- **Thesis (F67): 117 pp, no red status boxes, no layout warnings.** Added: module figure, one
  frame byte by byte (`analysis/worked_frame.py`), receiver outcomes, generator, energy rig and
  uncertainty, RQ3's numbers, mobility (§10.4.6), credibility literature, RQ answers, two
  appendices. **Appendix B lists thirteen registrations by commit hash** — ⚠️ **merge pull
  requests with a MERGE COMMIT, never squash** (G25); CI fetches full history for that test.
- **Still Mohamed's:** degree, department, declaration, AI statement, acknowledgements;
  affiliation and supervisor's name in the paper. **Still unread:** G23, G24.

### ⚠️ 2026-10-08 — every open point decided; what was done under those decisions (F58–F61)
Branch **`p10-followups`** (cut from `p9-supervisor-revision`). ⚠️ **Pull request #1
(`p9-supervisor-revision` → `main`) is open and is MOHAMED'S to merge after he has read it. Do
not merge it.** What a later session must know:
- **Why the capacities are what they are (F58).** A frame is lost in two ways: two backoff
  counters reach zero in the same slot, or a station sends inside the 4 µs in which it cannot
  yet sense another. `src/authbc/sim/dcf_unsaturated.py` simulates that rule and nothing else —
  no fitted constant, no ns-3 code — and reproduces **all 18 simulated crossings within 1.2 %**
  (`results/raw/dcf_model_vs_ns3.csv`). The airtime line's slope 0.071 is ρ/(W(1−ρ)) at the
  *mean* occupancy of the crossings. ⚠️ **That agreement is a comparison, not a prediction** —
  the model was completed beside one of those cells. **The predictions came after, and held
  (F62, follow-up F5):** six crossings registered before any run — window doubled, 2 % and
  10 % loss, baseline and design — all inside the ±3 % band, **worst 1.73 %** (1,080
  ns-3 runs). Doubling the contention window buys **11–12 %** capacity (35.3→39.2, 124.6→139.6),
  not a doubling: stations that count down for longer wait together more often.
- ⚠️ **The receiver-CPU figures (296 / 77 / 10) charge CRYPTOGRAPHY ONLY (F59).** The Python
  prototype's decoder costs several times the verification. "The channel binds first" is true
  of a compiled receiver, not of the prototype. The Pi number is step 1 of the bench session.
- **Records at 50 Hz (F60):** PX4 v1.17.0 in software-in-the-loop — every delta record 9 B; the
  design costs **42.47 B/record** (generator 43.25). Its 50 Hz stream holds **20.0 ms ± 0.37 ms**:
  nearer to strictly periodic senders than to the redrawn source. Two of that measurement's
  predictions did not hold as written and are recorded so.
- **The two traffic sources have the same mean delivery (F61):** the +0.003 of seeds 1–30 did
  not replicate on 1,260 fresh runs. ⚠️ **"Capacities read from the periodic source are 1–9 %
  lower" is WITHDRAWN** — the crossing rule is unbiased; that was one fluctuation.
- **The bench session is Mohamed's** (`hw/BENCH_SESSION.md`, five steps, expectations written
  first). **Contention on radios waits for one or two more 5 GHz stations** (`OPEN_ITEMS` G4).
- ⚠️ **On this machine the wall clock is stepped back under load** — a timing statistic was
  lost to it. Stamp with a monotonic clock. ⚠️ **`pkill -f X` kills its own shell if X appears
  anywhere in the command line**, bracket trick or not.
- PX4 lives OUTSIDE the repository at `~/projects/px4/` (source tree, build, its own Python
  environment). Nothing of it is committed; the flight's raw files are, in
  `results/raw/px4_sitl/quadx/`.

### ⚠️ SECOND PASS 2026-10-07 — the revision was audited again, against the built PDF (F55–F57)
Mohamed asked for a re-audit against the review. **Eleven places in the paper said less than the
response claimed, and the thesis still carried the review's own example of an over-claim in four
places** ("no choice of existing cryptography helps"). All fixed, each with a test. What a later
session must know:
- ⚠️ **AUDIT THE DELIVERABLE, NOT THE DESCRIPTION OF IT.** Look each "done" up in the built PDF.
  And re-read the thesis whole — a claim the paper lost was still standing in a chapter.
- ⚠️ **Not every size is an emitted frame.** In the ladder, lean rows 5, 6 and 8 are; row 7 (no
  delta coding) and all four first-format rows are sums of measured parts and are marked †
  (`design_ladder.csv`, column `sized_from`). Never write "all lean sizes are emitted frames".
- **The curve** (`fig_bytes_vs_batch.png`, `analysis/figures_frames.py`): of the 31.71 B/record
  between the two designs at b = 4, **24 B is where the chain link sits**; the first format with
  one link per frame would be 50.96 B. A link in every record costs 54.32 B at twelve records.
- ⚠️ **The first format's "45 B record" is 13 B of telemetry + 32 B of chain link.** Signature
  and link are 96 of 109 B = **88 %**; φ = 58.7 % counted the link as data.
- **LoRa capacity was simulated at 218 B / six records / 0.165 rec/s** (the simulator's module
  carries 222 B at most), not at the 242 B / eight-record frame. Quote the pair together.
- **Stream-signing baselines are now simulated as frames** (follow-up F3, predictions committed
  first) — sizes from the schemes' definitions; ⚠️ for the three whose packets do not verify alone
  a simulated delivery is an *upper bound*.
- **New PDFs:** a CC BY one may be committed (Rajasekaran et al. 2022 was); a copyrighted one
  goes in `HELD_LOCALLY.csv`. MDPI article pages refuse scripts; the publisher's static server
  does not (`paper/SUBMISSION_CHECKLIST.md`).
- ⚠️ **Never send Mohamed's e-mail address to an outside service.** It went to one (Unpaywall)
  on 2026-10-07, by mistake; reported to him.

### The headline numbers, current (2026-10)
- **43.25 B/record** against 145.77 B for a signature on every record: **−70.33 %** (lean format, emitted frames). First format: 74.96 against 174.25, −56.98 %.
- **Capacity at V ≥ 0.95, ns-3 direct search, 30 seeds, bootstrap interval** (`design_ladder.csv`):

  | | per-record signing | design | ratio |
  |---|---|---|---|
  | adopted (50 rec/s, 100 ms), lean | 35 [35, 35] | **124** [124, 125] | 3.5× |
  | adopted, first format | 32 [32, 32] | 88 [88, 89] | 2.8× |
  | relaxed (20 rec/s, 250 ms), lean | 85 [85, 86] | 306 [306, 308] | 3.6× |
  | relaxed, first format | 78 [77, 78] | 219 [215, 221] | 2.8× |

  Ladder at the adopted point: first 32 → 56 → 76 → 88; lean 35 → 76 → 108 → 124. ⚠️ **The ratio depends on the FORMAT and hardly on the operating point** — quote it with the format; "1.9–3.2×" is dead. ⚠️ Never quote a capacity for a rung that was not simulated; the artifact leaves those cells empty on purpose.
- **A closed form that passed a held-out test (F54):** N_max ≈ 0.05 / (f·(a·T + c)), f = Λ/b frames/s, T = airtime + DIFS, **a = 0.0710, c = 8 µs**. Seven configurations it was not fitted to, predicted before they were simulated, all within **3.4 %** (tolerance 6 %). ⚠️ **A fit, with a narrow domain** — 5 % loss level only, 802.11a 6 Mb/s, 5–50 frames/s, ns-3; residuals ordered by frame rate. **Never quote it as a capacity; quote the simulated value.**
- **Exclusion: eight of twelve** EU863-870 data rates, with its four conditions. ⚠️ Never without the conditions; never "no cryptography helps" (a 48 B signature fits 51 B; a 13 B tag fits 115 B).
- **Receiver CPU:** one Pi 4 core verifies **296** neighbours (Ed25519, one signature per frame), **77** (a signature per record), **10** (BLS).
- ⚠️ **At equal BIT error rate the design is BELOW its V target at the 5 % point (0.943)** — a batch is a longer frame. Stated in the paper; every comparison is at equal *frame* loss.
- **Real telemetry (12 public PX4 logs):** delta 11.06 B vs the generator's 10.83 at 0.2 s. ⚠️ Logs are 5 Hz; nothing is tested at 50 Hz.
- **The one-line message:** *batching and header design decide what can run; among standard 64 B elliptic-curve signatures the scheme does not change it.* ⚠️ Not "no signature scheme changes that".

### ⚠️ THE PATTERN of October — three classes seeds, audits and tests could not catch
- **C7 — a composite that was never built.** Each part was right, so re-deriving any number reproduced it. **What composes facts is building the thing they describe and making it run.**
- **C8 — a simulated source more regular than any real one.** Strictly periodic senders freeze their phases; ns-3 raises carrier sense only after a 4 µs preamble-detection period. In the worst run 4 of 29 nodes deliver nothing and 22 lose nothing. **All capacities use a send time redrawn each period** (`nmax_source: period`). ⚠️ The two sources differ by **+0.003** in mean delivery (≈ 2 standard errors) — inside the registered tolerance, not zero, not explained (G6).
- **C9 — a source taken on trust.** A wrong author list for two months; a survey quoted in the methods paper that was never held. `make verify-citations` now compares every entry with its registry record.
- ⚠️ **AN EXPLANATION IS A CLAIM.** On 2026-10-06 I explained a result away ("the seeds share phase draws across cells") from reading code, committed it, and it was false — one correlation on data already on disk refuted it. Check explanations like numbers.
- ⚠️ **A `pgrep -f pattern` WAITER MUST NOT MATCH ITSELF** — use `'[p]attern'`. One sat four hours after the campaign it was watching had finished (docs/06 §10).
- ⚠️ **CHECK THE PLAN AGAINST THE DELIVERABLE, ROW BY ROW.** The first rewrite of the paper silently departed from the approved plan (a new title; the exclusion after the 802.11 results) and left two approved items undone. No test could see that.

### Decisions of the revision — ALL TAKEN by Mohamed on 2026-10-08 (do not re-open without new evidence)
The table is in `docs/DECISIONS.md` ("Decided by Mohamed, 2026-10-08"). In one line each: **one
chain link per frame on both arms — confirmed** · the name's wording and the paper's title —
**kept** · **single author**, the supervisor thanked (⚠️ name, affiliation, ORCID and funding
statement still to come from him) · **venue: a networking journal without page charges, after
the contention experiment** · the analysis of the review **stays private** (`~/authbc_package/docs/`)
· the response goes to the supervisor **after the bench session** · the revision reaches `main`
by **pull request, merged only after he has read it** · the methods paper keeps "Nine Ways…" and
waits · contention on radios: **find one or two more radios first** (G4) · **one bench session**
for G9, G11, G15, G19 · **no** real LoRa link · **PX4 software-in-the-loop** for 50 Hz records
and stream timing · **fresh seeds and a derivation** for the two simulator questions · stream
baselines and implicit certificates left as stated · thesis next: **chapter 2**.

**DECIDED by Mohamed 2026-10-07 — new PDFs are not published.** Eleven of the twelve sources added in October were stripped from the branch before its first push; the unpublished commits from `e9d9e44` on were rewritten for that (dates preserved; the four pre-registration commits before it kept their hashes). ⚠️ **A new source goes in `HELD_LOCALLY.csv` and `.gitignore`, not in a commit, unless its licence allows redistribution.** A local branch `p9-backup-before-strip` still holds the old commits — **never push it.**

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
  - ⚠️ **"9 of 9" was inflated and is RETRACTED.** Under the pre-registered inclusion criteria only **4** papers qualify (Haxhibeqiri et al. used **their own simulator, not ns-3**; Mehta is a **survey**; Bhatt is **802.11ah not LoRa**). Honest baseline: **4/4 report no replication.** The paper said "nine studies" for a few hours today; corrected.
  - ⚠️ **UNREADABLE (<2000 chars extracted) is EXCLUDED from the denominator** — scoring a scanned PDF as "reports nothing" would manufacture support for our own hypothesis. Zirak extracts 5 characters.
- **The taxonomy to check new numbers against:** C1 small-sample mean vs threshold · C2 unverified constant on the measurement path · C3 threshold applied to a mean not a distribution · C4 config change perturbing the random realisation · C5 claim wider than the experiment. **Only C1 is fixed by more seeds.**

### ⚠️ PAPER FRAMING CHANGED 2026-08-07 — feasibility boundary, not co-design optimization
- **Retitled** *"Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound, a Capacity Envelope, and Hardware Validation"*. §Results opens with **three boundaries ordered by durability**: impossible (arithmetic, cannot move) → capacity-limited (1.9–3.2×) → runs (58.7 %, now the *mechanism*, not the headline).
- **Rationale:** as a co-design paper the work is mid-tier (the optimisation is closed-form; F39 found one real interaction). As a boundary paper the same evidence is stronger — **an impossibility cannot drift, and four performance numbers here did.** ⚠️ Do not revert without re-reading F39 and F42.
- **Second paper: `paper/methods.tex`** (`make paper-methods`, 2 pp) — the five-class defect taxonomy as a methodological note in the Kurkowski 2005 / SIGCOMM-CCR 2018 credibility lineage. Self-audit by design: 10 results moved, only 4 catchable by seeds, 2 protected by passing tests, 3 paper-vs-artifact contradictions.

### ⚠️ MATH AUDIT 2026-08-28 (F43, F44, M4) — read before quoting the exclusion

**Mohamed: "audit all the math deeply and compare it against the simulation."** Every published
number reproduced. **Nothing was a wrong number.** Every finding is a convention or a limit that
decides a headline and was never written down — defect class **C2**, the one class the post-F30
30-seed discipline cannot touch.

- ⚠️ **THE HEADLINE MOVED: "four of seven EU868 rates" is now THREE (F44).** Authorised knowing it
  might cost the claim. The frame header is 29 B of CBOR **text key names**; the same seven keys as
  integers cost 7 B, so **H_f 44 → 22 B**, DR3's budget goes 7 B → 29 B, and **DR3 becomes
  feasible**. docs/01 §2a always said the header was untuned; docs/02 T6 always depended on it;
  nobody composed them. **What survives is the strong half** — DR0–DR2 stay excluded at a
  *zero-byte header and a one-byte record* (64 B will not fit 51 B), and the boundary is now
  **constructive**: it names what would have to change. ⚠️ The wire format is **NOT** changed (D6);
  `placement/wire_profile.py` measures an alternative and a test fails if it leaks into the wire.
- ⚠️ **The pre-registered ≥40 % criterion could not have failed (F43c).** It reduces exactly to
  **1 − 1/b**, so the threshold is `b ≥ 2`, independent of encoding, scheme, placement, H_f and
  g_a; the V half is satisfied by construction (E17). **The ordering is genuine** and independently
  verified (`3354ec1` → `a51486a`, ~1.8 days). Keep the date; the abstract no longer implies risk.
- ⚠️ **H_f is a RANGE, 38–44 B (F43b)**, varying with `src`/`base_seq` because canonical CBOR
  integers are variable-length. 44 B is the end **most favourable to the exclusion** —
  `s_max = M − H_f − g_a`. docs/01 §2a analysed the bias for the byte comparison and never for T6,
  where the sign is opposite.
- **`D(b)` names the oldest record's age and computes the batch window (F43a).** Simulation
  confirms both closed forms exactly. `b/Λ` **survives as the worst case** — it is `(b−1)/Λ` plus
  one sampling quantum — and is kept. ⚠️ Cost stated: the tight reading admits b=5 (**−61.78 %**)
  where we publish b=4 (−58.68 %). ⚠️ docs/02 §7a's "knife-edge" was an artifact of the convention.
- **`s` depends on the generator window (F43d).** `e1_dominance` and `p1_sizes` disagree by up to
  3.7 B on the same quantity and both are right for their protocol. E1's ±0.02 B CI is **~150×**
  narrower than the systematic term. Direction is conservative.
- **Haxhibeqiri et al.'s `N_max`=4 sits inside their own fit's unreliable region (F43e)** — 40 % of their predicted
  loss at N=4 is a non-physical intercept. ⚠️ **Never quote "≈2× more pessimistic" as one number:**
  it is 0.91× at N=2 (*we* are more optimistic there) and 2.1× from N=10 up.
- **M4 CLOSED by measurement.** The U ceiling is frame-size invariant: crossing **2.367** at 174 B
  vs **2.435** at 288 B — **0.45 σ**, indistinguishable across a 1.66× change. `tab:envelope`'s
  absolute 213/100/88/31 keep support they previously only assumed. ⚠️ **N-invariance is still
  untested** (both arms N=50). ⚠️ My own pre-registration made a *directional* prediction the run
  had no power to resolve — recorded as a flaw: **a directional prediction needs a power estimate.**
- **Verified CLEAN against simulation:** OFDM PPDU exact; Ma & Chen vs the independent slot-exact
  simulator **≤0.08 %** at N=5–50 and vs NS-3 ≤0.51 %; the CFP mechanism reproduced (16.9× at N=50);
  Bianchi unicast −0.40…+1.29 %; fixed-point residual ≤7×10⁻¹³; the `N_max` first-failure search
  identical to a full scan over 7 configs × 4 ceilings. ⚠️ Ma & Chen's S(n) is **non-monotone** in N
  (all three implementations agree — real physics); the search is safe only because U(n)'s explicit
  factor n outruns it. **Safe by arithmetic, not by construction** — now guarded.

### The headline numbers as of AUGUST 2026 — ⚠️ SUPERSEDED, see the October section at the top
- **Total on-air bytes −58.68 %**, as a **decomposition** (placement×batching 79.2 %, encoding 20.8 %, scheme byte-neutral). ⚠️ **Never quote the bare 75 %** — it is algebraically **1 − 1/b**.
- **Adopted operating point: Λ=50 Hz, D_max=100 ms** (PX4 `MAVLINK_MODE_ONBOARD`, TS 22.125 compliant). Capacity **18→35** (U<1), **31→100** (V≥0.95). Relaxed (20 Hz/250 ms): 25/32→**103**, 55/88→**213**.
- ⚠️ **Do NOT say "≈3× holds across readings"** — the four combinations are **1.94× / 3.23× / 3.22× / 2.42×**. Quote the **range 1.9–3.2×**. (Recomputed 2026-08-07 from `capacity_envelope.csv`: Λ=50 U<1 18→35, V 31→100; Λ=20 U<1 32→103, V 88→213. The board previously said 2.24/3.31 and "1.9–3.3×" — both wrong; guarded now by `test_abstract_ratio_range_matches_artifact`.)
- **LoRa `N_max` = 3** (not 5), and only within **≈500 m**. Composed with measured link loss, **V≥0.95 admits no multi-node network**; V≥0.90 restores 3.
- **Validation, 30 seeds:** unicast **+1.29/−0.40 %**, broadcast goodput **±0.51 %**, crossing **U=2.435**. ⚠️ Unicast has a real **−1.4..−2.6 % bias at 72 B** — quote the band as measured at 1400 B.

### ⚠️ THE PATTERN of the whole audit — read this before trusting any new number
**Four headline numbers were distorted by small-sample means against thresholds. NONE was a modelling error; every one was sampling.** Drivers now default to **30 seeds** and emit min/max/σ. Before reporting any threshold crossing, look at the *distribution*.
> ⚠️ **And a table survived the purge.** Six 3-seed artifacts were deleted (F38), but `tab:lora-external` was still built on `lora_capacity_3seed_SUPERSEDED.csv` — matching it to three decimals — until 2026-08-07. It quoted `N_max`=5 where the 30-seed run gives **3**. It survived three read-throughs because the *other* column (Haxhibeqiri et al.) was correct: **a half-correct table reads as verified.** Purging an artifact is not enough — re-derive everything that consumed it.

### External baselines (A7 closed)
- **Haxhibeqiri et al. 2017 implemented** (`lora.haxhibeqiri2017_loss_pct`), validated against their own four figures: **their N_max=4 vs our 3**; closed-form periodic ALOHA also gives 3.
- **Zirak et al. 2021** — the only **hardware** air-to-air LoRa PDR-vs-range data; it range-limits our result.
- **CLAS (F34).** ⚠️ **The finding is the AXIS, not the ratio:** every published CLAS overhead is **linear in message count** (583–859 B/rec) because aggregation compresses the *verifier's work*, not the wire; ours is **80.1 B/rec** with certificates charged at the standards policy (162 B every 5th frame, NDSS 2024). **Do NOT claim we beat CLAS** — they buy conditional privacy we do not offer, and their group element is 128 B vs our 64 B.
- ⚠️ **METHOD RULE:** the certificate-byte term was added **BEFORE** the CLAS numbers were fetched. Doing it after would have been fitting the correction to the answer. Defaults are 0/1 so frozen artifacts stay bit-identical.

### Retractions, kept visible
**WITHDRAWN 2026-08-08 — the Direction C literature claim.** We claimed ns-3 LoRa studies do not report replication. Pre-registered threshold: abandon at ≥25 % reporting. As retrieval improved the estimate walked to **21.7 % (5/23), 95 % CI [7.5, 43.7]** — **the interval contains the threshold**, so the test cannot answer its own question. Claim cut from the paper; corpus and protocol kept in-repo as a null result. ⚠️ Two temptations resisted and recorded: the point estimate sits on the favourable side of 25 %, and the non-arXiv subset reads **28.6 %** (above threshold, p=0.61, *not* reported as a finding). Guarded by `TestDirectionCSurvey`, which fails if the claim returns.
**T7** (capacity excludes at U≥1) · **F15** (the ≤0.36 % validation) · **F18** (I claimed we were the *more optimistic* model vs Haxhibeqiri et al. — I quoted their **pure-ALOHA** figure as their LoRa result). ⚠️ **Quoting the PDF is not enough: quote the FIGURE.**
> ⚠️ **F18 came back.** On 2026-08-07 it was found still printed in `tab:lora-external` ("we are more optimistic" at N=5) — 100 lines below a bold sentence saying the opposite. **Retracting a finding in the register does not remove it from the paper.** When you retract, grep the paper. Guarded now by `test_no_row_revives_the_retracted_optimism_claim`, which checks the *artifact* rather than the wording.

### Where things live
`docs/README.md` is the index. Findings **F1–F71** in `docs/audits/model_provenance.md`. Open items **only** in `docs/OPEN_ITEMS.md`. Trade-offs in `docs/TRADEOFFS.md`. Method and failed attempts in `docs/LOGBOOK.md`. **51 PDFs** in `docs/literature/` with each source's ROLE stated, and **14 more held on Mohamed's machine but NOT redistributed** (`docs/literature/HELD_LOCALLY.csv`, git-ignored files — ⚠️ never `git add -f` them); every bibliography entry is checked against its registry record by `make verify-citations` (`A3_CITATION_VERIFICATION.md` is the August record of a check that turned out not to compare authors — F49).

### Deferred by Mohamed — plans written, DO NOT START unprompted
- **Mobility (E20)** — `docs/MOBILITY_PLAN.md`. **Separate NEW scenario files**, literature survey first. Not for the 802.11 arm (Bianchi/Ma&Chen have no position term).
- **Direction C** — the LoRaWAN frozen-phase artifact as a second short paper. Needs the full 56-paper survey (5 done) and a defensible jitter value.

### Accepted limitations, stated in the paper
E8 single SF · E10 half-duplex + full replication · E11 duty enforced at app level · E14 no capture · E15 static nodes · E12 propagation too optimistic · D5 cross-platform hardware (optional) · B5/C3/C5/C6.
