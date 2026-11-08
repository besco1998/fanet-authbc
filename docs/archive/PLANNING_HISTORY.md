# Planning history — the July 2026 plans, phase prompts and lane notes

*Merged on 2026-11-01 from fifteen files that described how the project was to be run when it
started (2026-07-03). All of them were marked historical or were superseded by the work itself;
they are kept here, verbatim, for provenance. The workflow templates still in use are in
[`../prompts/T_TEMPLATES.md`](../prompts/T_TEMPLATES.md); the implementation guide of that time is
[`03_IMPLEMENTATION_GUIDE.md`](03_IMPLEMENTATION_GUIDE.md), kept whole because code docstrings
cite its sections as `docs/archive/03 §N`.*

## Contents

1. [07 — PARALLEL EXECUTION PLAN](#s1) — formerly `docs/07_PARALLEL_EXECUTION_PLAN.md`
2. [PROMPTS — USAGE GUIDE](#s2) — formerly `docs/prompts/USAGE_GUIDE.md`
3. [00 — MASTER KICKOFF PROMPT  (COPY-PASTE WHOLE FILE into a fresh Claude Code session in ~/projects)](#s3) — formerly `docs/prompts/00_MASTER_KICKOFF.md`
4. [P0 — BOOTSTRAP  (COPY-PASTE WHOLE FILE)  ·  day 1–2 · blocks everything · ends: tag p0-done](#s4) — formerly `docs/prompts/P0_BOOTSTRAP.md`
5. [P1 — CRYPTO & ENCODING: CODE + MICROBENCHMARKS  (COPY-PASTE WHOLE FILE)](#s5) — formerly `docs/prompts/P1_MICROBENCH.md`
6. [P2 — LEDGER + CANONICAL WIRE FORMAT  (COPY-PASTE WHOLE FILE)](#s6) — formerly `docs/prompts/P2_LEDGER_WIRE.md`
7. [P3 — PLACEMENTS + CHANNEL EMULATOR  (COPY-PASTE WHOLE FILE)](#s7) — formerly `docs/prompts/P3_PLACEMENTS_CHANNEL.md`
8. [P4 — EXPERIMENTS E1–E3  (COPY-PASTE WHOLE FILE)  — the first thesis figures](#s8) — formerly `docs/prompts/P4_EXPERIMENTS_E123.md`
9. [P5 — MODELS + OPTIMIZER + E4  (COPY-PASTE WHOLE FILE)  — LANE 2 ENTRY (parallel to P1–P4)](#s9) — formerly `docs/prompts/P5_MODELS_OPTIMIZER.md`
10. [P6 — NS-3 VALIDATION + E5  (COPY-PASTE WHOLE FILE)  — LANE 3 (build early; validate at SYNC-3)](#s10) — formerly `docs/prompts/P6_NS3_VALIDATION.md`
11. [P7 — RPi4 HARDWARE CAMPAIGN  (COPY-PASTE WHOLE FILE)  — LANE 4 (opportunistic; scripts anytime)](#s11) — formerly `docs/prompts/P7_HARDWARE.md`
12. [P8 — CONSOLIDATION + PAPER  (COPY-PASTE WHOLE FILE)  — integrator, after SYNC-4](#s12) — formerly `docs/prompts/P8_CONSOLIDATION_PAPER.md`
13. [Lane 1 — status & handoffs](#s13) — formerly `docs/status/lane1.md`
14. [Lane 2 (Models) — status / handoff log](#s14) — formerly `docs/status/lane2.md`
15. [The external baseline: comparing against a VANET CLAS scheme](#s15) — formerly `docs/CLAS_BASELINE_PLAN.md`

---

<a id="s1"></a>

## 1. 07 — PARALLEL EXECUTION PLAN

*Formerly `docs/07_PARALLEL_EXECUTION_PLAN.md`, last changed 2026-07-29. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions.

Which phases can genuinely overlap, how to run them safely with multiple Claude Code
sessions, and what it buys. Referenced by ⚠️ D7 (Mohamed picks the mode at end of P0).

### 1. The real dependency graph (what depends on what — and what does NOT)
```
P0 ─┬─► P1a code: encodings+crypto+KATs ─► P1b benchmarks ──────────┐
    │            └────────► P2 ledger+wire ─► P3 placements+channel ─► P4 (E1–E3)
    ├─► L2: P5a models (bianchi/energy/optimizer vs SPEC, unit-tested) ─► P5b (E4)*
    ├─► L3: P6a NS-3 install+build+hello+scenario skeleton ─► P6b (validation+E5)**
    └─► L4: P7a RPi4 provisioning scripts (anytime) ─► P7b hardware campaign***
                                                        P8 needs everything
*  P5b (E4) needs P1b's measured timings + P5a.        (SYNC-2)
** P6b needs P5a (Bianchi) + P3 (real framer-exported frame sizes). (SYNC-3)
***P7b needs P1a code (+ hardware & ⚠️ D5 meter); best value after P5a exists.
```
**Key insights that unlock parallelism:**
- **P5a is spec-driven, not data-driven.** The Bianchi solver, energy model, and
  optimizer are implemented and unit-tested against doc 02's formulas and hand-computed
  values — they need NO code or data from Lane 1. Only *running E4* needs P1b numbers.
- **P6a is environment work.** The NS-3 build is 15–40 min of mostly waiting plus a
  skeleton scenario that takes frame sizes as a parameter — spec-level sizes suffice
  until SYNC-3 swaps in framer-exported ones.
- **P1 splits.** P2 needs P1a's *code* (encoders, signers), not P1b's *measurements* —
  tag `p1a-code-done` unblocks P2 while P1b runs elsewhere.
- **P7 splits.** Provisioning scripts are pure prep; the campaign itself only needs P1a
  code for the microbench rerun.

### 2. The three lanes (recommended mode: 2 concurrent sessions + NS-3 as a "freebie")
| Lane | Contents | Depends on | Owner paths (see §3) |
|---|---|---|---|
| **L1 Core** | P1a→P1b→P2→P3→P4 | P0 | encodings, crypto, ledger, placement, channel, bench, experiments/e1–e3 |
| **L2 Models** | P5a, then P5b at SYNC-2 | P0 (P5b: +P1b) | models, experiments/e4 |
| **L3 NS-3** | P6a, then P6b at SYNC-3 | P0 (P6b: +P5a,P3) | ns3/ |
| **L4 HW (optional overlap)** | P7a scripts; P7b after SYNC-1+hardware | P0 (P7b: +P1a) | hw/, results/hw |

**Sync points (merge to main, re-plan, retag):**
- **SYNC-1** = `p1a-code-done`: L1 continues to P1b *and* P2 (pipelined in one session,
  or P1b handed to a short L2-side task); P7b becomes possible.
- **SYNC-2** = P1b + P5a done: run E4 (P5b). ~end of week 2.
- **SYNC-3** = P3 + P5a done: export frame-size CSV → P6b runs the validation matrix and
  E5 prep. ~week 4.
- **SYNC-4** = P4 + P5b + P6b done: final E5 + cross-audit → P8. ~week 5.

### 3. Ownership map (conflict prevention — absolute rule)
P0 pre-creates EVERY directory, the full Makefile, pyproject, CI, and stubs, then
freezes the shared files. Each lane may modify only:
```
L1: src/authbc/{encodings,crypto,ledger,placement,channel,bench}/**, tests/{unit,property,integration}/** (matching), experiments/e{1,2,3}/**, results/raw/e{1,2,3}*, analysis/figures_e123.py
L2: src/authbc/models/**, tests/unit/models/**, experiments/e4/**, results/raw/e4*, analysis/figures_e4.py
L3: ns3/**, results/raw/ns3*, analysis/figures_ns3.py
L4: hw/**, results/hw/**
ALL lanes: docs/status/lane<N>.md (own file only), docs/audits/p<N>.md (own phase only)
NOBODY without a sync-point decision: Makefile, pyproject.toml, CLAUDE.md, docs/00–07, tests/vectors/ (frozen at P2 per ⚠️ D6)
```
Violation handling: doc 06 §8.

### 4. Practical setup (one command, created at P0)
`scripts/lane.sh 2` → `git worktree add ../fanet-authbc-lane2 -b lane2` + prints the
checklist: open that folder in a separate VSCode window, start Claude Code there, paste
`docs/prompts/P5_MODELS_OPTIMIZER.md`. Merges: at each SYNC, the L1 session (the
"integrator") merges lane branches to main, runs `make all`, tags, and pushes.

### 5. What parallelism buys — and its honest cost
| Mode | Wall time to end of E5 | Sessions to babysit | Risk |
|---|---|---|---|
| Serial | ~8 weeks | 1 | lowest |
| **2-lane (L1 + L2, L3 piggybacked)** | **~5–6 weeks** | 2 | low (disjoint paths) |
| 3-lane (+dedicated L3) | ~5 weeks | 3 | moderate (more merges) |
**Honest costs:** you review two plans and two audit files per sync instead of one;
merge discipline matters; a solo researcher's attention is the true bottleneck.
**Recommendation:** 2-lane. Start L3's NS-3 *build* early inside either session (it is
mostly unattended waiting), and keep L4 opportunistic. Do NOT parallelize P2 against P3
or split E-experiments across lanes — those dependencies are real, and false parallelism
there creates rework.

### 6. What must stay serial (do not fight these)
P0 (everything hangs off it) · P2→P3 (placements consume the frozen wire format) ·
P4 after P3 (experiments need the emulator) · P6b after P3+P5a · E5 after everything ·
P8 last. The freeze points (wire format at P2, experiment configs at first data) are
serialization *by design* — they protect scientific validity, not just tidiness.


---

<a id="s2"></a>

## 2. PROMPTS — USAGE GUIDE

*Formerly `docs/prompts/USAGE_GUIDE.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

How to run this project with Claude Code so the agent owns everything and you only make
decisions. Read once fully; then you'll mostly just paste prompt files.

### 0. One-time prerequisites (the ONLY manual setup — ⚠️ D0, ~10 minutes)
1. WSL2 Ubuntu 24.04 working; VSCode with the WSL extension.
2. Unzip this package to `~/authbc_package/` **inside WSL** (Linux filesystem).
3. `sudo apt install -y git gh` (if missing) → `gh auth login` (browser flow, once)
   → `git config --global user.name "..."` and `user.email "..."`.
4. Install/launch Claude Code per the official docs:
   https://docs.claude.com/en/docs/claude-code/overview
That's it. From here the agent creates the repo, the structure, and everything else.

### 1. The session model (how prompts map to Claude Code sessions)
- **One phase = one session** (default). Fresh session (or `/clear`) → paste the phase
  prompt file's entire contents → agent plans → you approve → it executes to the phase
  tag. This keeps context small, which keeps the agent sharp and cheap.
- **Autonomous chaining:** the Master Kickoff authorizes the agent to proceed to the
  next phase prompt (they live in the repo at `docs/prompts/`) after each green tag
  WITHOUT waiting for you — it stops only at ⚠️ decisions and failures. If a session
  grows long, the agent writes a handoff (T_TEMPLATES §Resume) so the next session
  continues seamlessly; you just open a new session and paste the Resume template.
- **Plan mode habit:** always start a phase in plan mode; approve the plan; then let it
  run. (Feature details/keybindings: see the official docs above.)


### 1b. What's new in v3 (why the prompts look self-sufficient)
- **Copy-paste self-contained:** each phase prompt inlines the exact numbers, formulas,
  APIs, and expected values it needs, so you can paste it cold and the agent rarely has to
  open other files (it still may, when a prompt says so). Less context hunting = fewer
  mistakes and lower cost.
- **Results-checking is now a LAW (Law 6):** every phase makes the agent state the expected
  value/shape IN ADVANCE, compare, run sanity gates, cross-check a point independently, and
  treat anything surprising/ambiguous as either an explained finding or a bug — never
  silently accepted. The mechanics live in T_TEMPLATES.md §Validate-Results.

### 2. Exact kickoff sequence (day 1)
1. Open VSCode → WSL → open folder `~/projects` (create it). Start Claude Code.
2. Paste **`00_MASTER_KICKOFF.md`** (whole file). The agent confirms it will fetch the
   package from `~/authbc_package/`, states the laws back, lists risks.
3. Paste **`P0_BOOTSTRAP.md`**. The agent creates the repo (local + GitHub via `gh`),
   copies docs+prompts+CLAUDE.md into it, scaffolds everything, proves a clean clone
   works, and stops at **⚠️ D7** asking you: serial or parallel?
4. Answer D7 (recommended: `2-lane` per docs/07 §5). The agent then either continues
   into P1 (serial) or prints the lane-setup checklist (parallel).

### 3. Running parallel lanes (if you chose 2-lane at D7)
- The agent's `scripts/lane.sh 2` creates the second worktree. Open
  `../fanet-authbc-lane2` in a **second VSCode window**, start a **second Claude Code
  session** there, paste `docs/prompts/P5_MODELS_OPTIMIZER.md`.
- Your main window's session runs Lane 1 (P1→P4). At each SYNC point (docs/07 §2) the
  Lane-1 session acts as integrator: merges, runs `make all`, tags, pushes.
- Never run two Claude Code sessions in the SAME directory (doc 06 §8).

### 4. Model selection (efficiency + quality)
Use the **strongest available model** for: the Master Kickoff, every phase's planning
step, every T_AUDIT run, and NS-3 debugging. Use a **fast model** for routine execution
once a plan is approved. Switch models per the official docs above (current model names
and the switch command are documented there — don't rely on memory).

### 5. What YOU do vs what the agent does
| You (only) | The agent (everything else) |
|---|---|
| D0 auth once · answer ⚠️ D1–D7 · approve phase plans · read audit files at tags · buy hardware (D5) · read Failure Reports when it stops | create repo & structure · write all code/tests/experiments · run everything · debug to root cause · write audits & handoffs · commit/push/tag · chain phases |

### 6. Efficiency rules already baked into the prompts (so you know why they look strict)
- **Context budget blocks:** each prompt names the exact files/sections to read and
  forbids reading anything else (prevents context bloat and drift).
- **Mechanical acceptance:** every criterion is a runnable command (`make test`, a diff,
  a tag) — no "looks done".
- **One module = one commit** (code+tests together); targeted tests while developing,
  full suite only at checkpoints.
- **Handoffs by default:** each phase ends by updating `docs/status/lane<N>.md`, so any
  fresh session resumes in <1 minute with T_TEMPLATES §Resume.

### 7. Monitoring from anywhere
`git log --oneline`, the tags (`p0-done`…), GitHub Actions status, `docs/status/`,
`docs/audits/`, `docs/failures/`. If the repo is green and tagged, it's real — the rules
make it impossible for the agent to fake progress silently.

### 8. If something goes wrong
The agent stops and produces a Failure Report (doc 06 §7) — read it, answer any question
it asks, and say "proceed". If a session was interrupted mid-phase: new session → paste
T_TEMPLATES §Resume → it reads the status file and continues. Never let it (or yourself)
"temporarily" skip a red test — that rule is the project's immune system.


---

<a id="s3"></a>

## 3. 00 — MASTER KICKOFF PROMPT  (COPY-PASTE WHOLE FILE into a fresh Claude Code session in ~/projects)

*Formerly `docs/prompts/00_MASTER_KICKOFF.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

You are the OWNER-AGENT for AUTHBC, a master's-thesis research system titled
"Co-Optimizing Encoding and Authentication for Communication-Efficient Blockchain
Telemetry in FANETs (802.11 arm)". You own execution end-to-end — creating the GitHub
repository, the entire architecture, all code, tests, experiments, NS-3 simulations,
audits, and the paper pipeline — from nothing to completion. Mohamed owns DECISIONS only.

======================================================================
PROJECT IN ONE SCREEN (so you can act without loading everything)
======================================================================
GOAL. Pillar-1 (a published paper) showed compact serialization (CBOR) shrinks telemetry
payloads. CONSEQUENCE we exploit: once payloads are small, the fixed cryptographic
AUTHENTICATION overhead (signatures/keys/hashes) becomes the dominant on-air cost — a 64 B
signature is 33% of a 130 B CBOR record and 62% of a 40 B delta record. THESIS: formulate
and solve the joint optimization of {encoding × authentication placement × signature scheme
× batching granularity} for per-UAV hash-chained telemetry ledgers over 802.11 links, under
security, wireless-loss-robustness, and verification-throughput constraints, with closed-
form results (theorems T1–T5), an instrumented channel emulator + NS-3 validation, and
Raspberry-Pi-4 hardware ground truth. Honest novelty ~6 (a rigorous optimization+measurement
study, not a new primitive). Venues: Ad Hoc Networks / MDPI Drones / IEEE IoT Journal.

SCOPE GUARDRAILS (do NOT drift): no new crypto primitive; no new consensus protocol; no PQC
implementation (PQ sizes appear only as analytical datapoints); no mobility modelling (loss
p is a channel parameter); no multi-hop routing research; no LoRa in this arm (that is a
later journal extension). Owned-object model: each UAV appends only to its OWN hash chain;
tampering/equivocation on (src,seq) is detectable. No consensus/finality in this arm — the
deliverable is authenticated dissemination + the optimization.

SOURCE OF TRUTH. The specification package is at ~/authbc_package/ (docs/00–07, prompts/,
CLAUDE.md). Each PHASE PROMPT you will be given is self-contained with the numbers it needs
inlined; the docs are the deeper reference when a prompt tells you to open a specific
section. If ~/authbc_package/ does not exist, STOP and ask Mohamed for the path.

======================================================================
AUTHORITY & AUTONOMY
======================================================================
You ARE authorized to execute without asking: `gh repo create` (private), all installs of
listed deps inside the venv/apt, all commits/pushes/tags, creating git worktrees, running
long builds and experiment matrices, and — after each phase's acceptance criteria pass and
its tag is pushed — LOADING THE NEXT PHASE PROMPT from docs/prompts/ and continuing on your
own (autonomous chaining). Before your context grows long, write a §Handoff (see
docs/prompts/T_TEMPLATES.md) into docs/status/ so a fresh session resumes losslessly.

You MUST stop and ask Mohamed ONLY for: items marked ⚠️ (decisions D0–D7 in docs/00 §6),
ANY deviation from the specs, any purchase, any destructive git operation, and any fix that
would change a FROZEN artifact (wire vectors, frozen experiment configs).

======================================================================
THE EIGHT LAWS (binding every session; full text also in the repo's CLAUDE.md)
======================================================================
1. PLAN FIRST. Enter plan mode; restate the objective; list risks; give a step plan with
   mechanical acceptance criteria; get approval before executing. No unplanned side quests.
2. VERIFY BEFORE ASSUMING. Unsure about any API/version/constant/formula/NS-3 detail?
   Inspect the installed package/source/official docs FIRST. Never code against a guess.
3. NEVER BYPASS A FAILURE. Any failing test/install/known-answer-test/determinism check/odd
   number ⇒ STOP → write a Failure Report (template in docs/06 §7) → find ROOT cause → fix
   the cause → add a regression test → get green → only then continue. FOREVER FORBIDDEN:
   skipping/deleting/commenting-out tests, widening a tolerance to pass, mocking real data,
   or proceeding "temporarily".
4. TDD. Known-answer vectors/tests with or before code; `main` stays green.
5. AUDIT–ATTACK–FIX–ITERATE after every module and at every phase end, from BOTH a
   scientific view (exact formula/notation conformance to the specs; units; edge cases;
   statistics) and an engineering view (determinism, seeds, error paths, CI honesty).
   Findings → docs/audits/p<N>.md → fix → re-test.
6. CHECK YOUR RESULTS (do not just produce them). Before recording/committing ANY number,
   table, or figure, run the §Validate-Results checklist (docs/prompts/T_TEMPLATES.md):
   state the EXPECTED value/shape/sign/magnitude in advance and compare; run sanity gates;
   cross-check one point by an independent path; confirm determinism and provenance. If a
   result is surprising, borderline, self-contradictory, or you're unsure whether it's a
   real finding or a bug — DO NOT average it away or assume it's fine: reproduce it, form
   hypotheses, and either explain it with evidence as a genuine finding or treat it as a bug
   (§Debug); if still ambiguous after honest effort, raise it to Mohamed. A plausible-
   looking WRONG number is the worst possible outcome — worse than a crash.
7. SCIENTIFIC INTEGRITY. Seeded runs; raw CSVs committed with config-hash + environment
   headers; provenance for every figure; NO fabricated or extrapolated numbers; any model-
   vs-measurement gap >10% investigated in writing (never silently tolerate or add hidden
   correction factors); negative/unexpected results reported plainly.
8. DECISIONS ARE MOHAMED'S. ⚠️ items and any spec deviation stop for him. You created the
   repo and run everything; he only decides.

EFFICIENCY (binding): obey each phase prompt's CONTEXT BUDGET — read exactly those
files/sections, nothing else, to keep context small and sharp. One module = one commit
(code + tests together). Targeted tests while developing; full `make all` only at
checkpoints. Keep a live task checklist for the current phase and check items off.

======================================================================
FIRST ACTIONS, NOW
======================================================================
1. Read ~/authbc_package/CLAUDE.md, then docs/00 (charter) fully, then docs/07 §1–3
   (parallel plan/ownership), then skim docs/01 §3 (repo layout) and docs/03 §1–2
   (environment + dependency pins).
2. Verify environment: WSL2? repo target on the Linux filesystem (not /mnt/c)? Python 3.12?
   `git` and `gh` present? Run `gh auth status` — if NOT authenticated, STOP: that is ⚠️ D0
   (Mohamed runs `gh auth login` once), then continue.
3. Reply with: (a) a 10-line summary of the project in your own words; (b) the Eight Laws
   restated one line each; (c) your top-5 implementation risks with a mitigation for each;
   (d) the single sentence "Ready for P0." Then await the P0 prompt.


---

<a id="s4"></a>

## 4. P0 — BOOTSTRAP  (COPY-PASTE WHOLE FILE)  ·  day 1–2 · blocks everything · ends: tag p0-done

*Formerly `docs/prompts/P0_BOOTSTRAP.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

You are executing Phase P0 of AUTHBC under the Eight Laws (already loaded via the Master
Kickoff and the repo CLAUDE.md). Start in PLAN MODE; present your plan; on approval, execute.

CONTEXT BUDGET — read exactly these, nothing else:
CLAUDE.md · docs/00 §4–6 · docs/01 §3 · docs/03 (all) · docs/07 §3–4 · docs/06 §1 and §6.
Do NOT read docs/02, docs/04, or other phase prompts now.

OBJECTIVE: a PRIVATE GitHub repo named `fanet-authbc`, created BY YOU, containing the full
skeleton, frozen shared files, working CI, and the package docs — PROVEN by a clean clone
that passes `make setup && make test && make lint` untouched.

REPO LAYOUT TO CREATE (exact; create ALL of it at P0 so parallel lanes never need to add
shared dirs later):
```
fanet-authbc/
├── CLAUDE.md                        # copy from package root
├── Makefile                         # targets below
├── pyproject.toml                   # pins below
├── .github/workflows/ci.yml         # setup+lint+unit only
├── .pre-commit-config.yaml          # ruff
├── scripts/lane.sh                  # git-worktree creator (docs/07 §4)
├── src/authbc/{encodings,crypto,ledger,placement,channel,models,bench}/__init__.py
├── experiments/{e1,e2,e3,e4,e5}/    # .gitkeep
├── analysis/                        # .gitkeep
├── ns3/                             # .gitkeep
├── hw/                              # .gitkeep
├── tests/{unit,property,integration}/   # mirror src; one placeholder test
├── tests/vectors/                   # .gitkeep (frozen later)
├── results/{raw,figures,hw}/        # .gitkeep
├── docs/                            # copy docs/00–07 from package
├── docs/prompts/                    # copy the prompts/ folder here
├── docs/status/  docs/audits/  docs/failures/   # README stubs
└── paper/                           # .gitkeep
```

DEPENDENCY PINS for pyproject.toml (VERIFY each imports at the resolved version; any drift
from these is ⚠️ — STOP with a table):
```
python>=3.12 ; cryptography>=42,<46 ; blspy>=2.0 ; cbor2==5.8.0 (DELIBERATE pin) ;
msgpack>=1.0 ; numpy ; scipy ; pandas ; matplotlib ; pyyaml ; pytest ; pytest-cov ;
hypothesis ; ruff
```

MAKEFILE TARGETS (the only supported entry points; exp-*/sim-ns3 are guarded stubs that
fail loudly "implemented in P4/P6"):
`setup lint test bench-micro bench-macro exp-e1 exp-e2 exp-e3 exp-e4 exp-e5 sim-ns3
export-framesizes figures all`

STEPS (one commit per numbered step unless noted):
1. ENV GATE: confirm Linux FS (`df -T .` → ext4, not 9p/drvfs), Python 3.12, git+gh present,
   `gh auth status` OK (else ⚠️ D0 STOP). Create docs/status/lane1.md and record outputs.
2. LOCAL SCAFFOLD: `mkdir -p ~/projects/fanet-authbc && cd ~/projects/fanet-authbc &&
   git init -b main`. Create the full layout above; copy docs/ and prompts/ and CLAUDE.md
   from ~/authbc_package/.
3. pyproject.toml with the pins; write the `setup` target (venv + install); RUN it; print a
   table {package, wanted, resolved, import-ok}; ⚠️ STOP on any drift.
4. Makefile with all targets (guarded stubs where noted).
5. QUALITY RAILS: pytest layout mirroring src; one placeholder test that imports every stub
   module; ruff configured; pre-commit(ruff); `make test lint` green.
6. CI: .github/workflows/ci.yml running setup+lint+unit (NOT ns3/benches). Commit.
7. CREATE THE GITHUB REPO YOURSELF:
   `gh repo create fanet-authbc --private --source=. --remote=origin --push`
   then poll `gh run list` until the Actions run is green (paste the result).
8. scripts/lane.sh per docs/07 §4 (refuses to clobber an existing worktree dir); commit.
9. CLEAN-CLONE PROOF: in /tmp, `git clone <url> && cd fanet-authbc && make setup && make
   test && make lint`; paste the tail of each into docs/status/lane1.md. Any failure here is
   a P0 failure — fix in the repo and re-prove.
10. RESULTS VALIDATION (Law 6, even here): the "result" of P0 is the clean-clone proof —
    confirm it green on a MACHINE-INDEPENDENT path (the /tmp clone), not just in place.
11. AUDIT P0 (docs/prompts/T_TEMPLATES.md §Audit) — attacks: wrong-FS guard real? pin
    verification real? CI actually runs the tests (not a no-op)? lane.sh safe? every
    ownership-map dir (docs/07 §3) present? Write docs/audits/p0.md; fix; re-run step 9.
12. Tag `p0-done`; push; update the CLAUDE.md status board (allowed — you are on main).

ACCEPTANCE (all mechanical): /tmp clone passes setup+test+lint · CI green on GitHub · pin
table clean or ⚠️ raised · docs+prompts present in repo · audits/p0.md has ≥3 attacks · tag
pushed.

END-OF-PHASE GATE — ⚠️ D7: STOP and ask Mohamed: "Execution mode: serial | 2-lane | 3-lane?
(docs/07 §5 recommends 2-lane, ~5–6 weeks vs ~8 serial)." On `serial`: load
docs/prompts/P1_MICROBENCH.md and continue. On parallel: run `scripts/lane.sh 2` (and 3 if
chosen), print the lane checklist (docs/07 §4 + USAGE_GUIDE §3), then load P1 yourself as
Lane 1 and continue.


---

<a id="s5"></a>

## 5. P1 — CRYPTO & ENCODING: CODE + MICROBENCHMARKS  (COPY-PASTE WHOLE FILE)

*Formerly `docs/prompts/P1_MICROBENCH.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Lane 1 · days 2–5 · split: P1a code (tag p1a-code-done → unblocks P2, P7b) → P1b measurements
(tag p1-done → unblocks E4). Under the Eight Laws; start in PLAN MODE.

CONTEXT BUDGET — read exactly: docs/01 §1–2 · docs/02 T1 and §8 · docs/03 §3 (encodings/,
crypto/, bench/) · docs/04 §1 · docs/06 §3,§4,§5. Not T2–T5, not NS-3.

OBJECTIVE: correct KAT-verified crypto + deterministic encodings (P1a); then the measured
parameter tables and the T1 overhead-dominance table — the thesis's FIRST numbers (P1b).

KEY FACTS INLINED (so you can self-check without hunting):
- Telemetry record fields, INTEGERS ONLY (floats break canonical CBOR cross-platform): lat/
  lon as int32 at 1e-7° fixed-point, alt int32 (cm), vel_{x,y,z} int16 (cm/s), battery uint8
  (%), mode uint8 (enum), plus src uint16, seq uint32, ts uint32 (ms), prev_hash 32 B.
- Encodings to implement: json (stdlib), cbor (cbor2, canonical=True, RFC 8949 §4.2),
  msgpack, delta (canonical integer field order, zigzag-varint deltas vs previous record,
  keyframe every K=16; decoder keeps per-src state; a lost frame desyncs until next keyframe
  → emit desync_count).
- Schemes + APIs: ECDSA-P256 via cryptography `ec.ECDSA(hashes.SHA256())` — for byte
  accounting use fixed-width 64 B r||s (decode_dss_signature then pad), NOT the 70–72 B DER;
  Ed25519 via cryptography `Ed25519PrivateKey`; BLS12-381 via blspy `AugSchemeMPL`
  (sign/aggregate/aggregate_verify). Ed25519 batch-verify is NOT exposed → default scope is
  SEQUENTIAL verify (scope claims accordingly; true batch = ⚠️ D3, stretch only).
- KAT sources to vendor into tests/vectors/ WITH their URLs: RFC 8032 §7.1 (Ed25519); NIST
  CAVP ECDSA P-256/SHA-256; draft-irtf-cfrg-bls-signature test vectors.
- T1 EXPECTED NUMBERS (φ = g/(s+g), g=64): JSON s≈358→15.2% ; CBOR s≈130→33.0% ; delta
  s≈40→61.5%. Your measured φ MUST reproduce these within rounding — a mismatch is a STOP.
- Timing sanity anchors on x86 (order of magnitude; far outside ⇒ STOP, audit harness, do
  NOT record): Ed25519 sign ~15–60 µs, verify ~40–120 µs; ECDSA-P256 verify ~80–300 µs;
  BLS pairing verify ~1–3 ms. Verify-time must NOT be < sign-time for the same scheme.
- Bench harness rules: `time.perf_counter_ns`; `gc.disable()` around loops (re-enable after);
  ≥1000 warmup iters; ≥10 000 timed iters OR ≥200 ms total (whichever larger); accumulate a
  checksum of outputs and assert it (defeats dead-code elimination); report MEDIAN + bootstrap
  95% CI (10 000 resamples). Every CSV header carries seeds + env block (`lscpu` model; note
  "WSL, governor uncontrolled").

P1a STEPS (one module = one commit: code + its tests):
1. bench/telemgen.py: seeded generator of the record above; property test = schema
   conformance on 1000 samples.
2. encodings/: ABC {encode,decode,name,deterministic} + the four encoders. Tests: round-trip
   (hypothesis, 1000 random records each); DETERMINISM — encode identical 1000 records in TWO
   subprocesses, compare SHA-256 of the concatenation (mismatch = STOP, Law 3); delta: loss-
   then-keyframe recovery test asserting desync_count behaviour.
3. crypto/: uniform API per scheme; vendor the KATs (with URLs); ECDSA fixed-width-64 test;
   BLS aggregate/aggregate_verify test. **KATs green BEFORE any timing exists.** blspy build
   failure ⇒ STOP → Failure Report → recovery ladder (upgrade pip; apt install cmake build-
   essential; last-resort py_ecc fallback is ⚠️ and ALL its timings get labeled "py_ecc — not
   representative").
4. AUDIT P1a (§Audit): attacks — canonical-byte boundaries, ECDSA encoding ambiguity, delta
   reference rules, KAT provenance. Fix. Tag `p1a-code-done`; push. If 2-lane, this tag is
   SYNC-1 — announce in docs/status/lane1.md. Then either continue to P2 in this session or
   hand P1b to a sibling session (say which and why).

P1b STEPS:
5. bench/timers.py + stats.py per the harness rules; UNIT-TEST the harness on a known-cost
   function (e.g., a fixed sleep or a counted loop) so you trust it before measuring crypto.
6. RUNS (seeds + env header in every CSV): (a) sizes: 10 000 records/encoding → mean±CI, max;
   delta at K=16 with keyframe amortization stated. (b) crypto: t_sg,t_vf per scheme on 200 B
   msgs; BLS t_ag(b),t_av(b) for b∈{2,4,8,16,32}.
7. RESULTS VALIDATION — Law 6, run §Validate-Results and write it into docs/audits/p1.md:
   - Compare EVERY measured φ to the inlined T1 numbers (state expectation first); mismatch
     beyond rounding ⇒ STOP.
   - Compare every crypto timing to the inlined anchors; assert verify≥sign per scheme;
     assert BLS-verify ≫ Ed25519-verify (feeds T4) and REPORT the measured ratio.
   - Cross-check ONE size and ONE timing by an independent quick calc/second method.
   - Confirm determinism (identical seed ⇒ identical sizes) and full provenance headers.
   - If anything is surprising/borderline: reproduce, hypothesize, explain-or-debug; if still
     ambiguous, raise to Mohamed. Do NOT record until all gates pass.
8. Produce results/raw/p1_*.csv + two tables (T1 auth-fraction; scheme-timing with CIs +
   the BLS/Ed25519 verify ratio). AUDIT P1b (attacks: timer resolution vs op cost, outlier
   policy stated, CI-width sanity, provenance). Fix → `make all` → tag `p1-done` → push →
   write §Handoff.

ACCEPTANCE: KATs+determinism+round-trip green · both tags pushed · CSVs with env headers ·
T1 table matches the inlined numbers · timings within anchors or investigated · Results-
validation subsection written in audits/p1.md.


---

<a id="s6"></a>

## 6. P2 — LEDGER + CANONICAL WIRE FORMAT  (COPY-PASTE WHOLE FILE)

*Formerly `docs/prompts/P2_LEDGER_WIRE.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Lane 1 · week 2 · needs p1a-code-done · unblocks P3 · ends: tag p2-done · Eight Laws · PLAN MODE.
⚠️ After this phase, tests/vectors/ wire vectors are FROZEN (D6) — later changes need Mohamed.

CONTEXT BUDGET — read exactly: docs/01 §1 (ledger + security model + placements list) and §4
(wire format — the normative spec) · docs/03 §3 (ledger/ spec) and §4 (gates) · docs/06 §5.

OBJECTIVE: per-UAV hash-chain ledger with replay/equivocation handling, and the FROZEN
canonical frame format for placements A–D with vendored test vectors.

KEY FACTS INLINED:
- Record := {src:u16, seq:u32, ts:u32(ms), ph:bytes32, pl:map(telemetry)}; prev_hash =
  SHA-256 over the PREVIOUS record's canonical CBOR bytes. Define "canonical CBOR bytes of X"
  ONCE in a helper and cite docs/01 §4 in its docstring; everything hashes/signs via it.
- Placements (audit-corrected semantics): A inline per-record sig; B self-batch (ONE signer,
  b of its OWN records, ONE signature over the covered bytes); C cross-signer (b records from
  DIFFERENT originators each already signed, BLS-aggregated to 48 B); D block-level (one sig
  over b records spanning n>1 frames).
- Frame := {v:1, t:PLACEMENT_ID, src:u16, base_seq:u32, n:u8, recs:[RecordBody×n],
  auth:AuthBlock}. AuthBlock by placement: A [sig×n]; B one sig over canonical(recs);
  C agg_sig(48B)+signer_list; D sig + {block_id,frag_idx,frag_total}. Canonical CBOR; NO
  indefinite-length items; deterministic map key order.
- signature input = canonical bytes of the covered region ONLY — write covered_bytes(frame,
  placement) with its own unit tests (this boundary is the #1 audit target).

STEPS (one module = one commit):
1. ledger/record.py + chain.py: Chain.append(payload)->Record fills src/seq/ts/prev_hash.
   Tests: 1000-append chain verify; prev_hash correctness by INDEPENDENT recompute.
2. ledger/store.py + verify.py: ingest with counters replayed (seq ≤ last accepted for src ⇒
   drop+count), equivocation_flags (same (src,seq), different hash ⇒ flag + keep the evidence
   pair), tampered (hash/sig fail). Hypothesis property tests: ANY single-bit flip in ANY
   field of a signed record is detected; replay always rejected; equivocation always flagged.
3. placement/wire.py: exact Frame/AuthBlock for A–D; covered_bytes() + its unit tests.
4. VECTORS FREEZE: tests/vectors/wire/*.bin + expected-hash JSON for ≥3 frames per placement,
   with the fixed keys/seeds committed alongside; a test asserts byte-identity forever. Commit
   message: `test: freeze wire vectors (D6)`.
5. GOLDEN integration test: 3 simulated UAVs, direct handoff (no channel yet), fixed seed,
   assert EXACT final counters — this is the regression anchor for all later phases.
6. FUZZ gate: 1000 random byte-mutations of valid frames through decode+verify → zero
   crashes/hangs; malformed ⇒ clean rejection + counter.
7. RESULTS VALIDATION (Law 6, §Validate-Results): the golden counters are a "result" — state
   the EXPECTED counts in advance (records stored, replays, flags for your seeded scenario)
   and assert equality; confirm determinism (same seed ⇒ identical counters); if any count
   surprises you, debug it (do not adjust the assertion to match). Write into audits/p2.md.
8. AUDIT P2 (§Audit) — MANDATORY attacks: canonicalization ambiguity (map order? indefinite
   lengths banned?), covered_bytes off-by-one at every boundary, seq u32 wraparound policy
   (state + test), ts ms consistency, duplicate-record-in-frame handling, D fragment-header
   integrity. Fix → re-run all → `make all` → tag `p2-done` → push → §Handoff.

ACCEPTANCE: coverage ≥90% on ledger+wire · property/fuzz/golden green · vectors frozen with
provenance · results-validation + mandatory attacks in audits/p2.md · tag pushed.


---

<a id="s7"></a>

## 7. P3 — PLACEMENTS + CHANNEL EMULATOR  (COPY-PASTE WHOLE FILE)

*Formerly `docs/prompts/P3_PLACEMENTS_CHANNEL.md`, last changed 2026-07-29. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Lane 1 · week 3 · needs p2-done · unblocks P4 and SYNC-3 (frame-size CSV) · ends: tag p3-done
Eight Laws · PLAN MODE.

CONTEXT BUDGET — read exactly: docs/01 §1 (placement semantics) and §3 (data flow) · docs/02
§6 (airtime constants — normative) and §7 (latency terms) · docs/03 §3 (placement/, channel/,
bench/macro) · docs/06 §3.

OBJECTIVE: framers A/B/C/D + a seeded broadcast channel with an airtime ledger; export real
frame sizes for NS-3.

KEY FACTS INLINED (802.11a OFDM, base rate R = 6 Mb/s):
- T_air(L bytes) = T_fx + 8L/R, with per-frame fixed overhead computed from: PHY preamble
  T_phy = 20 µs; MAC+FCS header = 34 B; SIFS = 16 µs; DIFS = 34 µs; slot = 9 µs; ACK = 14 B;
  propagation δ = 1 µs. For a successful UNICAST exchange T_s(L)=T_phy+8(L+34)/R+SIFS+δ+
  (T_phy+8·14/R)+DIFS+δ. Fixed part T_fx ≈ 123 µs. **BROADCAST has NO ACK/SIFS/retry** — for
  the broadcast airtime use T_air = T_phy + 8(L+34)/R + DIFS + δ (document which you use where;
  do not mix — this is a scientific-integrity trap revisited in P6).
- MTU application budget M = 1500 B. Frame header H_f = 44 B (measured, B1). b_max(s) = ⌊(M − H_f − g_a)/s⌋.
  EXPECTED b_max (M=1500, H_f=40): with g_a=48 (BLS) — CBOR s=130→10, JSON s=358→3, delta
  s=40→35; with g_a=64 (Ed25519 self-batch) — CBOR→9, delta→34. Unit-test b_max against these.
- Loss model: per-receiver i.i.d. Bernoulli(p), p∈{0.02,0.05,0.10}, seeded RNG per run.

STEPS (one module = one commit):
1. placement/inline.py (A) + self_batch.py (B): Framer ABC {pack(records)->frames,
   unpack(frame)->(records, ok_mask)}. B: one signature over covered bytes; expose b_max(s)
   and unit-test against the inlined numbers (mismatch = STOP).
2. relay_agg.py (C): consumes records WITH originator signatures; BLS-aggregate to 48 B;
   aggregate_verify on unpack; signer-list per docs/01 §4. Test: mixed-originator frame
   verifies; ANY one bad inner signature ⇒ whole aggregate fails + counted (document this).
3. block_agg.py (D): one signature spanning n>1 frames; fragmentation headers; reassembly
   buffer with 500 ms sim-time timeout; partial-block discard counter. Tests: reorder
   tolerance; timeout path; loss-of-one-fragment kills exactly that block.
4. channel/airtime.py: T_air per the inlined constants; unit-test against THREE hand-computed
   values you show the arithmetic for in the test comments (both unicast and broadcast forms).
5. channel/emulator.py: broadcast bus; per-receiver Bernoulli(p) seeded; MTU assert; per-node
   counters {frames_tx,frames_rx,bytes,airtime}. DETERMINISM test: same seed ⇒ byte-identical
   metrics CSV.
6. bench/macro.py: generator→framer→channel→verify→ledger→tidy CSV (row = config…, seed,
   metric, value; config-hash column). Extend the golden test end-to-end through the emulator
   with exact expected counters.
7. `make export-framesizes` → results/raw/framesizes.csv (placement×encoding→byte
   distribution). SYNC-3 artifact — announce in docs/status/lane1.md.
8. RESULTS VALIDATION (Law 6, §Validate-Results): EXPECT and check — with p=0 every sent
   frame is received (V=1) and airtime accounting balances (sender airtime = Σ frame
   airtimes; receivers add none); with p>0, measured receive fraction ≈ (1−p) within CI over
   ≥10 000 frames (state expectation, then verify with a Binomial check); airtime for a known
   frame size equals the hand value. Determinism holds. Write into audits/p3.md; debug any
   surprise rather than tolerating it.
9. AUDIT P3 (§Audit) — MANDATORY attacks: loss independence across receivers (statistical
   test vs Binomial), airtime double-counting on broadcast, C's one-bad-signer semantics, D
   timeout races, b_max off-by-one at exact MTU. Fix → `make all` → tag `p3-done` → push →
   §Handoff.

ACCEPTANCE: all four placements end-to-end · determinism proven · b_max & airtime match
inlined/hand values · framesizes.csv exported · golden updated · results-validation + five
attacks in audits/p3.md · tag pushed.


---

<a id="s8"></a>

## 8. P4 — EXPERIMENTS E1–E3  (COPY-PASTE WHOLE FILE)  — the first thesis figures

*Formerly `docs/prompts/P4_EXPERIMENTS_E123.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

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


---

<a id="s9"></a>

## 9. P5 — MODELS + OPTIMIZER + E4  (COPY-PASTE WHOLE FILE)  — LANE 2 ENTRY (parallel to P1–P4)

*Formerly `docs/prompts/P5_MODELS_OPTIMIZER.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

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


---

<a id="s10"></a>

## 10. P6 — NS-3 VALIDATION + E5  (COPY-PASTE WHOLE FILE)  — LANE 3 (build early; validate at SYNC-3)

*Formerly `docs/prompts/P6_NS3_VALIDATION.md`, last changed 2026-07-28. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Needs P0 (P6a); p5a-done + p3-done (P6b) · ends: tags p6a-done, p6-done · Eight Laws · PLAN MODE.

IF PARALLEL: Lane-3 worktree if 3-lane chosen; else the integrator runs it after P4/P5. You OWN
ONLY: ns3/**, results/raw/ns3*, analysis/figures_ns3.py. Re-read the repo CLAUDE.md.
⚠️ Read docs/06 §2 IN FULL before touching NS-3 — the broadcast/ACK subtlety below is a
scientific-integrity trap.

CONTEXT BUDGET — read exactly: docs/06 §2 (NS-3 build + no-ACK broadcast issue) · docs/04 §3
(scenario + campaign) · docs/02 §6 (the Bianchi variant to compare against) · docs/01 §1
(traffic). Nothing else.

OBJECTIVE: validate the Bianchi airtime/throughput model against NS-3, and run the end-to-end
E5 comparison of optimizer configs vs baselines.

KEY FACTS INLINED:
- NS-3 version 3.41, built from source (⚠️ D4 if it must change). Build:
  `sudo apt install g++ cmake ninja-build python3 libgsl-dev`; download ns-allinone-3.41;
  `./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja`; `./ns3 build`
  (15–40 min first time); GATE on `./ns3 run hello-simulator` before proceeding.
- THE TRAP: 802.11 BROADCAST has NO ACKs, NO retransmission, NO RTS/CTS. Classic Bianchi
  saturation throughput ASSUMES unicast with ACKs. So you MUST run BOTH: (a) saturated
  UNICAST matched to classic Bianchi (with ACK/SIFS in T_s), and (b) BROADCAST with the no-ACK
  Bianchi variant (T_air = T_phy+8(L+34)/R+DIFS+δ, no ACK, no retries). Compare each NS-3 mode
  to its MATCHING analytic variant. Mixing a broadcast NS-3 run against ACK-Bianchi is the #1
  way to fabricate a fake "model gap" — forbidden.
- Legit Bianchi-vs-NS-3 gap sources to enumerate & QUANTIFY (never silently correct): EIFS
  after errored frames, capture effect, retry/CW-reset details, propagation-delay defaults.
- Campaign: N∈{5,10,20,35,50} × 10 seeds × both modes; **10 s runs as executed** (decision C,
  2026-07-28 — 10 s already gives ~5000 busy periods/run; the written 30 s was never used).
  ⚠️ **Superseded guidance below:** broadcast must NOT be compared to a reduction of the unicast
  model — use Ma & Chen (docs/02 §6a). Transport is PacketSocket + PacketSink, not FlowMonitor. Frame sizes come from
  results/raw/framesizes.csv (real framer output from P3, imported at SYNC-3); until then use
  spec-level sizes. Runtime budget: full matrix < 2 h on WSL.

P6a STEPS (environment — mostly unattended; do EARLY, right after P0 if possible):
1. Build NS-3 3.41 per the inlined steps; gate on hello-simulator; record build flags/version
   in docs/status.
2. ns3/authbc-sat.cc skeleton: 802.11a ad-hoc, ConstantRateWifiManager OfdmRate6Mbps, RTS/CTS
   off, N senders, frame sizes read from a CSV PARAMETER; implement BOTH modes (a) and (b).
3. Wire `make sim-ns3`; a 2-node smoke run parses to CSV via a COMMITTED parse script (never
   hand-copy numbers). Tag `p6a-done`; push.

P6b STEPS (at SYNC-3):
4. Rebase to obtain results/raw/framesizes.csv; feed real sizes in.
5. Run the matrix (both modes); parse FlowMonitor (unicast) / PHY-RX-OK traces (broadcast)→CSV.
6. RESULTS VALIDATION (Law 6, §Validate-Results) — do this BEFORE writing any "gap" narrative:
   state the EXPECTED relationship (NS-3 unicast throughput should track ACK-Bianchi within a
   modest, EXPLAINABLE gap; broadcast should track the no-ACK variant); check saturation was
   actually reached (offered load ≫ capacity); throughput ≤ 6 Mb/s PHY ceiling; each NS-3 mode
   compared ONLY to its matching analytic variant. If the gap is large or wrong-signed:
   reproduce minimally, list candidate causes from the inlined set, quantify each — do NOT add
   a silent correction factor and do NOT widen a tolerance. If still ambiguous, raise to
   Mohamed. Write into audits/p6.md.
7. Comparison figure + written gap analysis (quantified causes, no hidden corrections). Export
   NS-3-informed contention (effective airtime share vs N) for the integrator's E5.
8. AUDIT P6b (§Audit): saturation reached? correct Bianchi variant per mode? seed handling in
   NS-3? runtime < 2 h? Fix → `make all` → tag `p6-done` → push → §Handoff.

ACCEPTANCE: NS-3 builds reproducibly via `make sim-ns3` · BOTH modes run · matrix < 2 h · gap
analysis with quantified causes and NO hidden corrections · results-validation in audits/p6.md ·
E5 contention export committed · tags pushed.


---

<a id="s11"></a>

## 11. P7 — RPi4 HARDWARE CAMPAIGN  (COPY-PASTE WHOLE FILE)  — LANE 4 (opportunistic; scripts anytime)

*Formerly `docs/prompts/P7_HARDWARE.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

Needs P0 (P7a scripts); p1a-code-done + hardware + ⚠️ D5 meter (P7b) · ends: tags p7a-done,
p7-done · Eight Laws · PLAN MODE.

You OWN ONLY: hw/**, results/hw/**. Re-read the repo CLAUDE.md.

CONTEXT BUDGET — read exactly: docs/04 §1 (micro suite to rerun) and §4 (hardware campaign +
energy protocol) · docs/06 §1 (governor/thermal/clock) · docs/03 §3 (the bench harness reused).

OBJECTIVE: hardware ground truth on 4× Raspberry Pi 4 — real crypto/encoding timings and
energy — fed back into the E4/E5 model layers to produce the paper's headline hardware tables.

KEY FACTS INLINED:
- RPi4, Raspberry Pi OS Bookworm 64-bit, headless, governor = performance
  (`cpufreq-set -g performance`; verify with `cpufreq-info`). Record `lscpu`, temperature,
  governor into results/hw/meta/ for every run.
- Energy protocol (external USB meter; ⚠️ D5 selects it, e.g. UM25C ≈ $30, one needed): CALIBRATE
  against a known resistive load first (note the reading). Then per operation: measure idle
  baseline power 60 s → run the op in a tight loop 60 s → energy/op = (P_loop − P_idle)·t_loop
  /n_ops; ≥5 repetitions; report median + CI. THERMAL GUARD: log temperature throughout;
  discard/flag any run showing throttling (Bookworm logs it; also watch for freq capping).
- Timing harness is the SAME as P1 (perf_counter_ns, GC off, warmup, ≥10k iters, checksum,
  bootstrap CI) — reuse it; only the platform changes. Expect RPi4 to be ~5–15× slower than
  x86 for these ops; a much larger/smaller ratio ⇒ investigate (governor? throttling?).

P7a STEPS (prep — no hardware needed; can run right after P0 in spare time):
1. hw/provision.sh (committed): OS deps, governor=performance, headless config, clock-sync note.
   hw/run_micro.sh: reruns the P1 micro suite with device metadata in CSV headers.
   hw/energy_protocol.md: the exact procedure inlined above. Tag `p7a-done`; push.

P7b STEPS (hardware present; ⚠️ D5 meter approved):
2. Provision 4× RPi4; capture lscpu/temps/governor to results/hw/meta/.
3. Rerun micro suite → hardware timing tables; compute x86/RPi4 ratios.
4. Energy: calibrate meter, then the per-op protocol → energy/op tables per scheme + encoding.
5. 2-node real-802.11 ad-hoc broadcast run of the golden scenario with MEASURED loss (not
   injected) — qualitative validation; state small-N honesty explicitly.
6. Feed back: rerun the E4/E5 MODEL layers with RPi4-measured (t_*, P_c, P_r) → hardware-
   grounded tables.
7. RESULTS VALIDATION (Law 6, §Validate-Results): state expected ranges (RPi4 ~5–15× x86;
   verify≥sign per scheme; BLS-verify ≫ Ed25519-verify still holds on ARM; energy/op positive
   and ordered sensibly — BLS most expensive); confirm NO run used throttled data (check the
   thermal logs); meter calibration within tolerance; determinism of timing medians across
   repetitions. Any anomaly ⇒ reproduce/hypothesize/explain-or-debug; ambiguous ⇒ raise to
   Mohamed. Write into audits/p7.md.
8. AUDIT P7b (§Audit): thermal throttling in ANY recorded run? meter calibration valid?
   clock/ntp effects? governor actually applied? Fix → `make all` where applicable → tag
   `p7-done` → push → §Handoff.

ACCEPTANCE: provision+micro+energy scripts committed & run · hardware tables with device
metadata + thermal logs · meter calibration noted · model layers re-run with measured params ·
results-validation in audits/p7.md · tags pushed.


---

<a id="s12"></a>

## 12. P8 — CONSOLIDATION + PAPER  (COPY-PASTE WHOLE FILE)  — integrator, after SYNC-4

*Formerly `docs/prompts/P8_CONSOLIDATION_PAPER.md`, last changed 2026-07-03. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

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


---

<a id="s13"></a>

## 13. Lane 1 — status & handoffs

*Formerly `docs/status/lane1.md`, last changed 2026-07-29. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions. **D7 resolved to serial execution — the parallel lanes described here were never used.**


### P0 bootstrap — environment gate (Step 1) · 2026-07-03

**Result: PROCEED.** D0 (gh auth + git identity) satisfied; no ⚠️ stop. Python 3.12 present.

| Check | Command | Output | Verdict |
|---|---|---|---|
| Filesystem | `df -T .` | `/dev/sdd  ext4` (repo at `~/projects/...`) | ✓ Linux FS, not 9p/drvfs |
| Python 3.12 | `/usr/bin/python3.12 --version` | `Python 3.12.3` | ✓ present |
| git | `git --version` | `git version 2.43.0` | ✓ |
| git identity | `git config --global user.{name,email}` | `besco1998` / `mohamed.besco1998@gmail.com` | ✓ |
| gh | `gh --version` | `gh version 2.45.0` | ✓ |
| gh auth (D0) | `gh auth status` | logged in as `besco1998`, scopes `repo`,`workflow` | ✓ **D0 OK** |

#### Step 0 — env switched to the existing Python 3.12 (per Mohamed)
Before: `python3` was a pyenv shim → **3.9.10** (pyenv global `3.9.10`); bare `python3.12`
resolved into an unrelated `~/venv-ardupilot`.
Action: **`pyenv global system`** → `python3 --version` = **Python 3.12.3** (shim now execs
the system interpreter). Verified `python3 -m venv` yields a standalone venv based on
`/usr/bin/python3.12` with `include-system-site-packages=false` (no ardupilot leakage).
Reversible: edits `~/.pyenv/version` only.

### P0 — dependency pin verification (Step 3): ALL CLEAN, no drift

`make setup` created `.venv` (Python **3.12.3**). blspy installed from a **wheel** (no source
build needed — the highest risk cleared). Verified with `packaging.SpecifierSet`:

| package      | wanted     | resolved | import-ok |
|--------------|------------|----------|-----------|
| cryptography | >=42,<46   | 45.0.7   | yes |
| blspy        | >=2.0      | 2.0.3    | yes |
| cbor2        | ==5.8.0    | 5.8.0    | yes |
| msgpack      | >=1.0      | 1.2.1    | yes |
| numpy        | (unpinned) | 2.5.0    | yes |
| scipy        | (unpinned) | 1.18.0   | yes |
| pandas       | (unpinned) | 3.0.3    | yes |
| matplotlib   | (unpinned) | 3.11.0   | yes |
| pyyaml       | (unpinned) | 6.0.3    | yes |
| pytest       | (unpinned) | 9.1.1    | yes |
| pytest-cov   | (unpinned) | 7.1.0    | yes |
| hypothesis   | (unpinned) | 6.155.7  | yes |
| ruff         | (unpinned) | 0.15.20  | cli |
| pre-commit   | (unpinned) | 4.6.0    | yes |

### P0 — local quality gates (Step 5)
- `make lint` → `All checks passed!`
- `make test` → `9 passed` (8 stub-import params + version check), coverage reported.
- `pre-commit` hook installed; rev pinned to `v0.15.20` via `pre-commit autoupdate`.

### P0 — clean-clone proof (Steps 9–10): PASS (machine-independent)

Repo: **https://github.com/besco1998/fanet-authbc** (private). Proven twice on `/tmp` (a
path independent of the working tree), most recently at commit `664cfc2` (post FS-guard fix):

```
git clone https://github.com/besco1998/fanet-authbc.git /tmp/... && cd ... && \
  make setup && make test && make lint
→ fs check: 'ext4' OK (Linux FS)
→ setup complete: Python 3.12.3 in .venv     (blspy-2.0.3, cbor2-5.8.0, cryptography-45.0.7)
→ 9 passed
→ All checks passed!
```

CI (GitHub Actions) green on both pushed commits: run `28633005732` and `28633198989`
(`test (pytest)` step: `9 passed`, Python 3.12.13).

### P0 — audit (Step 11)
`docs/audits/p0.md`: 5 attacks. 1 medium finding **fixed** (persistent wrong-FS guard in
`make setup`) + re-proven by fresh clone; 4 passed no-defect (pin check bites, CI runs real
pytest, `lane.sh` clobber-safe, all ownership-map dirs present).

### SYNC-1 — `p1a-code-done` (2026-07-03)
P1a code complete: `bench/telemgen` (seeded integer-only records), `encodings/{json,cbor,
msgpack,delta}` (round-trip + cross-subprocess determinism + delta recovery), `crypto/
{ecdsa_p256,ed25519,bls}` (uniform API + vendored KATs: RFC 8032, Wycheproof, Chia AugScheme).
**683 tests green**, lint clean, audit in `docs/audits/p1.md` (1 medium fixed). Tag
`p1a-code-done` pushed → **P2 (ledger+wire) and P7b are now unblocked**.

Post-SYNC-1 path: this Lane-1 session continues **P1b** (measurements) next, then **P2**
(pipelined). Lane 2 runs P5 independently.

Two byte-accounting ⚠️ carried into P1b (see audit): BLS 48-vs-96 B, and the T1 φ schema gap.

### Handoff 2026-07-05 — FULL AUDIT (pre-P7b), F1 fixed
- Whole-repo Law-5/Law-6 pass: docs/audits/full_audit_pre_p7b.md. Baseline stays 849 green / 90 %.
- **Fixed F1** (MED): E4/T4 modelled BLS at the stale 48 B vs the accepted 96 B — corrected
  crossover.py + 3 tests + E4 figure (κ*=∞-tolerant), re-ran/re-froze e4_crossover.csv + e4_bytes.csv.
  Conclusion **unchanged**: Ed25519 wins all 80 grid points (min κ*=3.21); at 96 B BLS only saves
  bytes on relay b≥2, never on own self-batch (κ*=∞) — aligns T4 with D2's cross-signer intent.
- Verified sound: all T1–T5 + Bianchi + airtime + energy formulas re-derived vs code; E5 energy
  hand-checked to 64.24 µJ = frozen; unicast Bianchi ±1.8–5.3 %; real KATs; determinism gates.
- Documented (no code change): F2 energy unicast-T_FX ~1 % over-count (P7 re-run), F3 E5 b=28
  grid-quantized (PASS either way), F4 cross-experiment size sampling (P8 standardize), F5 32 B
  prev_hash/record (assumption), F6 ECDSA<Ed on x86 may flip on ARM (P7 watch), F7 broadcast=capture.
- Nothing blocks P7b except its hardware + ⚠️ D5 meter.

### Handoff 2026-07-05 — P7a DONE (hardware-prep scripts, tag p7a-done)
- Green baseline: tag `p7a-done` on main; `make lint` clean; CI green. No Python touched (test
  count unchanged at 849). Lane: `hw/**` only.
- Done: the three P7a deliverables — `hw/provision.sh` (RPi4 Bookworm: performance governor +
  verify, pyenv-3.12 note, wifi power-save off, NTP, meta snapshot; **refuses on non-Pi**),
  `hw/run_micro.sh` (reruns the P1 micro suite on-device, folds REAL governor/temp/throttle into
  the CSV header, `--check` x86 self-test, thermal guard, never clobbers frozen x86
  `results/raw/p1_*.csv`), `hw/energy_protocol.md` (calibrate → idle 60 s → op-loop 60 s →
  energy/op=(P_loop−P_idle)·t_loop/n_ops, ≥5 reps median+CI, thermal guard; yields `p_cpu_w`,
  `p_radio_w` that replace E5's nominal 3.0/0.7 W).
- Verified on x86 (no hardware): `bash -n` clean; `run_micro.sh --check` → OK; `provision.sh`
  refuses off-Pi (exit 1); energy formula matches docs/04 §4 char-for-char.
- **P7b is the next gate — Mohamed owns it:** needs physical 4× RPi4 **and** ⚠️ **D5** (USB power
  meter, UM25C-class ~$30). Until then the other executable path is **P8** consolidation (energy
  tables flagged nominal-pending-P7).
- Gotcha for P7b: on a fresh Pi clone, `results/raw/p1_*.csv` hold committed x86 numbers;
  `run_micro.sh` backs them up and restores them so the Pi run lands only in `results/hw/`.

### Handoff 2026-07-05 — E5 DONE (SYNC-4 integrator, tag e5-done)
- Green baseline: tag `e5-done` on main; `make all` green (849); CI green.
- Done: `bench/experiments.run_e5` + `experiments/e5/config.yaml` + `analysis/figures_e5.py` +
  `make exp-e5` → frozen `results/raw/e5_codesign.csv` + byte-stable `fig_e5_codesign.png`. Audit
  `docs/audits/e5.md`.
- **HEADLINE (T5 co-design, docs/04 §2 success criterion):** optimized config = **delta + ECDSA
  + self-batch B + b=28** → on-air auth overhead **3.7 B/rec** at **V=0.95**; **96.4 % auth-byte
  cut vs A+CBOR** (104 B) at p=0.05 ⇒ **PASS** (target ≥40 %). D-over-agg fails V≥0.95 (=(1−p)²,
  T3). Inputs are the frozen measured E1 sizes + P1b timings; **energy uses nominal power ⚠ P7**.
- Next 3 steps: (1) **P8** consolidation — analysis notebook + paper skeleton pulling T1–T5 +
  E1–E5 + NS-3 validation together (all on main now). (2) **P7** RPi4 hardware (needs board + ⚠ D5
  meter) → re-run E4/E5 energy with measured power. (3) Optional broadcast-DCF deep study (P6b
  open item).
- Gotchas: E5 auth-byte headline is power-free (grounded); energy is nominal pending P7. Optimized
  scheme is a byte-tie ECDSA≈Ed25519 (D2 default) — either meets the criterion.

### Handoff 2026-07-05 — phase P6 DONE (Lane 1 integrator)
- Green baseline: tags `p6a-done`, `p6-done` on main; `make all` green (846; NS-3 not in CI).
- Done: SYNC merge of Lane 2 (P5 Bianchi/energy/optimizer/crossover + E4) → main; P6b NS-3
  matrix (`ns3/run_matrix.py` → `results/raw/ns3_matrix.csv`) + `analysis/figures_ns3.py`
  (byte-stable `fig_ns3_bianchi.png`) + `results/raw/ns3_contention.csv`. Audit `docs/audits/p6.md`.
- **Result (Law-6, honest):** **UNICAST validates Bianchi (+1.8…+5.3 %)** — the model's primary
  use. **BROADCAST** matches the no-ACK variant at N≤10 and is a **capture-limited lower bound**
  at high N; mechanism **confirmed = frame capture** via a toggle+power-spread experiment (12 dB
  spread → +17–48 % goodput; SimpleFrameCaptureModel inert at equal power). An early "~18×
  capture" over-claim was **retracted** (wrong metric/timing) — kept visible for integrity.
- Scenario hardening: rewrote to **PacketSocket** (ARP-free, single collision domain) after
  Law-6 gates caught spatial-reuse / broadcast-multi-count / ARP artifacts.
- ⚠️ NS-3 build tree git-ignored (rebuild via ns3/README); machine-local, not in CI.
- Next 3 steps: (1) **E5** integration (SYNC-4) — optimizer configs vs baselines A+JSON/A+CBOR/
  D-over-agg using P4 E1–E3 + P5b optimizer/crossover + P6b `ns3_contention.csv`; test the ≥40 %
  auth-byte-cut success criterion. (2) P8 consolidation/paper. (3) P7 hardware (needs RPi4/⚠️D5).
- Gotchas: broadcast goodput = aggregate/(N−1); unicast↔ACK-Bianchi, broadcast↔no-ACK — never mix.

### Handoff 2026-07-04 — phase P6a DONE (Lane 1 as Lane 3)
- Green baseline: tag `p6a-done` on main; `make all` green (777 tests, NS-3 not in CI); build
  tree git-ignored.
- Done: **NS-3 3.41 built** (optimized+Ninja; ⚠️ D4 settled=3.41); `ns3/authbc-sat.cc` (802.11a
  ad-hoc, both unicast+broadcast modes, size param), `ns3/parse_ns3.py`, `ns3/sim_ns3.sh`,
  `ns3/README.md`; wired `make sim-ns3`. Smoke (2 nodes, both modes) → `results/raw/ns3_smoke.csv`:
  unicast 3.27 Mb/s (FlowMonitor 3.39), broadcast 3.71 Mb/s — ≤6 Mb/s ceiling, >0, broadcast>unicast.
- Gate note: `hello-simulator` is silent in optimized (NS_LOG=OFF compiles out NS_LOG_UNCOND); it
  runs exit 0. Scenario uses ofstream/FlowMonitor, unaffected.
- ⚠️ **P6b BLOCKED**: needs P5a `bianchi.py` on main (SYNC merge of `origin/lane2`) before the
  full N∈{5,10,20,35,50}×10-seed matrix + Bianchi-vs-NS-3 gap analysis (per-mode, no mixing) +
  E5 contention export. Real frame sizes for P6b come from `results/raw/framesizes.csv` (SYNC-3).
- Next 3 steps: (1) merge `origin/lane2` (P5a Bianchi/optimizer/energy + E4) to main; (2) P6b
  matrix + gap analysis; (3) SYNC-4 → P8.
- Gotchas: NS-3 build tree not committed (rebuild via ns3/README); machine-specific, not in CI.

### Handoff 2026-07-04 — phase P4 DONE (Lane 1, 2-lane mode)
- Green baseline: tag `p4-done` on main; `make all` green (777 tests); CI green.
- Done: `bench/experiments` (run_e1/e2/e3) + `experiments/e{1,2,3}/config.yaml` +
  `analysis/figures_e123`. **First thesis figures** in `results/figures/`; frozen raw
  `results/raw/e{1,2,3}_*.csv` (⚠️ D6); audit + Law-6 in `docs/audits/p4.md`; `results/
  PROVENANCE.md`. Wired `make exp-e1/e2/e3` + `make figures`.
- Results (measured): **E1** φ JSON 25.1/CBOR 49.1/msgpack 49.6/delta 58.7% (auth≈½ a CBOR
  record). **E2** at M=1500 measured A matches M/(M−H_f−g_a) within 0.25%; batching → φ≈6.9%.
  **E3** V_B flat at 1−p; V_D=(1−p)^n drops when a block spans >1 frame (b≥21) → B Pareto-
  dominates D above V=(1−p)². All Law-6 gates pass.
- ⚠️ D6: E1–E3 raw frozen; figures regenerate byte-stable via `make figures`.
- Next 3 steps: (1) SYNC-4 territory — Lane 2 is at `p5-done` (E4). Options: load
  `docs/prompts/P6_NS3_VALIDATION.md` (needs SYNC-3 framesizes + P5a Bianchi — both ready) OR
  integrate Lane 2's E4 for the P8 narrative; (2) then P8 consolidation. (3) Mohamed picks.
- Gotchas: reuse ONE stateful encoder/stream for sizes; E1/E2/E3 raw are D6-frozen.

### Handoff 2026-07-04 — phase P3 DONE (Lane 1, 2-lane mode)
- Green baseline: tag `p3-done` on main; `make all` green (767 tests); CI green. **Unblocks P4.**
- Done: framers `A/B/C/D` (`placement/{inline,self_batch,relay_agg,block_agg}`), `channel/
  {airtime,emulator}` (broadcast bus, seeded Bernoulli loss, sender-only airtime), `bench/macro`
  end-to-end, `bench/framesizes` + **`make export-framesizes` → results/raw/framesizes.csv
  (SYNC-3)**. Audit + Law-6 in `docs/audits/p3.md`.
- **SYNC-3 artifact ready**: `results/raw/framesizes.csv` (placement×encoding×b→frame bytes,
  measured s_e json 193.5/cbor 68.9/msgpack 68.8/delta 45.0, BLS g_a=96) — for L3/NS-3 (P6b).
- Law-6: p=0 V=1 + airtime balance; p=0.1 receive fraction 0.902 within Binomial CI; loss
  independent across receivers (corr≈0); determinism holds. Caught+fixed 2 efficiency bugs.
- Flagged (carried): T_fx≈123µs vs exact components (broadcast 100.33/unicast 156µs) → revisit
  at P6; b_max CBOR/g_a=64 reference off-by-one (inlined 9 vs formula 10).
- Next 3 steps: (1) load `docs/prompts/P4_EXPERIMENTS_E123.md`; (2) P4 runs E1–E3 (dominance,
  batching cure, loss frontier) → frozen CSVs + figures; (3) SYNC-4 later.
- Gotchas: emulator uses BROADCAST airtime (no ACK); reuse ONE stateful encoder/stream for sizes.

### Handoff 2026-07-04 — phase P2 DONE (Lane 1, 2-lane mode)
- Green baseline: tag `p2-done` on main; `make all` green (738 tests); CI green. **Unblocks P3.**
- Done: `ledger/{record,chain,store,verify}` (hash chain, replay/equivocation/tamper counters,
  seq-wrap policy), `placement/wire` (canonical CBOR Frame + A–D AuthBlocks + `covered_bytes`),
  **wire vectors FROZEN (⚠️ D6)** in `tests/vectors/wire/` (12 frames + expected.json), golden
  3-UAV exact-counter test, 1000-mutation fuzz gate. Audit + Law-6 in `docs/audits/p2.md`.
- Golden result (Law 6, exact): `{stored:30, replay:5, equivocation:1, tampered:1}`.
- ⚠️ D6: wire bytes are now FROZEN — any change needs Mohamed. One flagged (low-severity,
  no-forgery) item: D fragment headers are unauthenticated (integrity still holds; DoS only,
  out of scope) — optional future hardening = a D6 change → Mohamed.
- Next 3 steps: (1) load `docs/prompts/P3_PLACEMENTS_CHANNEL.md`; (2) P3 builds the channel
  emulator + framers consuming the frozen wire format; (3) reconcile the e-axis-in-recs question
  (how encoding e appears inside frames) — flagged in `wire.py`.
- Gotchas: `covered_bytes` is the signed region (A/C per-record, B/D whole array); frozen
  vectors regenerate only via `python tests/unit/placement/test_frozen_vectors.py` (needs approval).

### Handoff 2026-07-04 — phase P1 DONE (Lane 1, 2-lane mode)
- Green baseline: tag `p1-done` on main; `make test` = 704 PASS; `make all` green; CI green.
- Done: P1a (telemgen, encodings×4, crypto×3 + vendored KATs) + P1b (bench harness, size &
  crypto-timing CSVs, T1 table). Tags `p1a-code-done` (SYNC-1) and `p1-done` pushed.
- Results (results/raw/p1_*.csv, docs/audits/p1.md): **T1 φ = JSON 24.9 / CBOR 48.1 /
  msgpack 48.2 / delta 58.7%** (g=64); scheme verify µs = ECDSA 78.5 / Ed25519 95.0 / BLS 1016;
  BLS/Ed25519 verify ≈ 10.7×. All Law-6 gates pass.
- Decisions applied: BLS byte accounting **= 96 B** (T2/T4 use 96 B, not the docs' 48 B); CBOR
  compacted to schema arrays (110.9→68.9 B) per Mohamed; T1 numbers = measured (supersede archive).
- Frozen this session: none new (wire vectors freeze at P2/D6). Makefile `bench-micro` wired.
- Open ⚠️: none blocking. Note for P7: ECDSA-verify sits at the low edge of the µs anchor on
  this fast CPU — re-confirm on RPi4.
- Next 3 steps: (1) load `docs/prompts/P2_LEDGER_WIRE.md`; (2) P2 uses P1a encoders/signers to
  build the chain + canonical CBOR wire format (freeze vectors — ⚠️ D6); (3) then P3.
- Gotchas: size harness must reuse ONE stateful encoder across the stream (delta); timings are
  wall-clock (vary within CI across runs) — sizes/KATs are deterministic.

### SYNC-1 — `p1a-code-done` (2026-07-03)
- Green baseline: commit `664cfc2`, tag `p0-done`, `make test` = PASS, CI = success.
- Done this session: full repo skeleton + docs/prompts/CLAUDE.md; pinned pyproject
  (no drift, blspy wheel OK); Makefile (setup/lint/test + guarded stubs + FS guard); ruff +
  pre-commit; CI (setup+lint+test); GitHub private repo created & pushed; `scripts/lane.sh`;
  clean-clone proof; P0 audit; env switched to system Python 3.12 (`pyenv global system`).
- Frozen this session: shared files (Makefile, pyproject, CLAUDE.md, docs/) per docs/07 §3.
  Wire vectors NOT yet frozen (that is P2 / ⚠️ D6).
- Open ⚠️ decisions awaiting Mohamed: **D7 execution mode** (serial | 2-lane | 3-lane).
- Next 3 steps: (1) Mohamed answers D7; (2) serial → load `docs/prompts/P1_MICROBENCH.md`;
  parallel → `scripts/lane.sh 2` (+3) then P1 as Lane 1; (3) begin P1a (encodings + crypto
  + KATs).
- Gotchas for next session: `python3` is 3.12 only because `pyenv global system` was set;
  `make setup` defaults `PYTHON=python3` (override `PYTHON=/usr/bin/python3.12` if needed).
  A stray `~/venv-ardupilot` sits on PATH but does not leak into the project venv.


---

<a id="s14"></a>

## 14. Lane 2 (Models) — status / handoff log

*Formerly `docs/status/lane2.md`, last changed 2026-07-29. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions. **D7 resolved to serial execution — the parallel lanes described here were never used.**


### Handoff 2026-07-04 — phase P5b / E4 (lane 2)
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

### Handoff 2026-07-03 — phase P5a (lane 2)
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


---

<a id="s15"></a>

## 15. The external baseline: comparing against a VANET CLAS scheme

*Formerly `docs/CLAS_BASELINE_PLAN.md`, last changed 2026-07-31. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*The single largest gap identified by the adversarial review: every baseline in the paper is an
internal variant of our own design. This plans the fix.*

### The key structural insight — the comparison is cheaper than it looks

**Placement C already *is* the cross-signer aggregation slot**, currently filled by BLS12-381
(96 B aggregate, invariant in b). A certificateless aggregate-signature (CLAS) scheme is an
**alternative construction for that same slot**, not a different system.

So the comparison does **not** require implementing CLAS cryptography. It requires:

| need | why | source |
|---|---|---|
| CLAS aggregate signature size (B) at a stated security level | drives every byte and capacity number | primary paper, not a survey |
| whether certificates ride on the wire | ⚠️ **the real CLAS advantage** — see below | primary paper |
| CLAS verify cost on ARM | only for the energy column | primary paper, or measure |

With (1) and (2), the existing optimizer, channel model and capacity machinery evaluate it directly.

### ⚠️ The comparison our model currently cannot make fairly

CLAS's headline claim is **certificateless**: no certificate bytes on the wire. Our byte model
assumes PKI and **does not charge certificate transmission at all** — for any scheme. So a naive
comparison would understate CLAS's advantage.

**This must be fixed before the comparison is run**, or the result is rigged in our favour. Two
options:
* charge certificates to the PKI schemes explicitly (correct, and it changes our own numbers), or
* state the comparison as *signature bytes only* and say plainly that certificate distribution is
  excluded from both sides.

The first is more honest and more work. **Recommended: the first.** ⚠️ It may reduce our reported
advantage, which is precisely why it must be done before, not after, seeing the CLAS numbers.

### What the comparison should report

1. **Bytes/record vs b**, placement C, for BLS vs CLAS — the direct substitution.
2. **Capacity** at both thresholds, via the existing `channel_utilisation` path.
3. **Feasibility** — does the CLAS aggregate fit the LoRa 222 B payload where BLS does not?
4. **What we do NOT claim**: we are not proposing a better construction. The axis stays
   *configuration of standardised primitives* vs *new construction*, as §Related Work already states.

### Honest expected outcome

**[SPECULATION — flagged as such]** CLAS schemes are typically ECC-based with aggregate sizes in the
tens of bytes, i.e. plausibly *smaller* than BLS's 96 B. **The comparison may well show a CLAS
construction beating our placement-C configuration on bytes.** That is a publishable and honest
result: it would say the co-design framework correctly identifies *which axis* matters, while a
purpose-built construction wins on the crypto axis — which is exactly the division of labour the
paper already claims.

**Do not run this expecting to win.** Run it to find out.

### Effort

* obtaining and verifying two primary sources: ~1 day
* certificate-byte correction to the model: ~2 days, touches frozen artifacts
* evaluation and write-up: ~2 days

Roughly one week, not the 2–3 weeks estimated in the review, because no cryptographic implementation
is required.
