# 03 — IMPLEMENTATION GUIDE
> ⚠️ **HISTORICAL (marked 2026-07-29).** This document reflects the plan as written at project start and has not been maintained since 2026-07-03. It is kept for provenance. **Current state lives in `docs/DECISIONS.md`, `docs/OPEN_ITEMS.md` and `docs/TECHNICAL_NARRATIVE.md`.** Do not use it to make decisions.


## 1. Environment (WSL2)
- Ubuntu 24.04 on WSL2; work ONLY on the Linux filesystem (`~/projects/...`), never
  `/mnt/c` (10–50× I/O penalty, breaks NS-3 builds). Python 3.12 venv per repo.
- `.wslconfig` on Windows: `memory=12GB` (or ≥8), `processors=<cores>` before NS-3 builds.
- Git identity + `gh` CLI authenticated for GitHub pushes from day 1.

## 2. Dependency pins (pyproject.toml; agent verifies availability at P0, ⚠️ if drift)
```
python = ">=3.12"
cryptography = ">=42,<46"     # ECDSA-P256, Ed25519
blspy = ">=2.0"               # BLS12-381 (Chia, C++); fallback: py_ecc (slow, flag ⚠️)
cbor2 = "==5.8.0"             # pinned (5.8.1 regression noted in project history)
msgpack = ">=1.0"
numpy, scipy, pandas, matplotlib, pyyaml, pytest, pytest-cov, hypothesis, ruff
```
NS-3: **3.41**, built from source (doc 06 §2). No Python bindings — C++ scenario + CSV.

## 3. Module specifications (implement in this order; each = code + tests same commit)

**encodings/** — ABC `Encoder{encode(rec)->bytes, decode(bytes)->rec, name, deterministic:bool}`.
CBOR: `cbor2.dumps(obj, canonical=True)`; verify byte-identical output across two runs and
(later) across x86/RPi4 — a failing determinism test is a STOP. `delta_enc`: canonical
integer field order, zigzag varint deltas vs previous record, keyframe every K=16, decoder
state per (src); document reference-loss behavior (re-sync at next keyframe).

**crypto/** — uniform API per scheme: `keygen() sign(sk,msg) verify(pk,msg,sig)`;
BLS adds `aggregate(sigs) agg_verify(pks,msgs,agg_sig)` (AugScheme — doc 06 §5).
**KATs first:** RFC 8032 Ed25519 vectors, NIST CAVP P-256 vectors, BLS IETF draft vectors
in `tests/vectors/`. No timing work until KATs green.

**ledger/** — `Chain.append(payload)->Record` (fills seq, ts, prev_hash),
`verify_record`, `Store.ingest(frame_records)` with replay rejection (seq ≤ last seen →
drop+count) and equivocation detection (same (src,seq), different hash → flag+count).
Property tests (hypothesis): any single-bit tamper in any field is detected.

**placement/** — ABC `Framer{pack(records)->frames, unpack(frame)->(records, ok_mask)}`
for A/B/C/D per doc 01 §4. Enforce MTU; C requires per-record originator sigs as input;
D fragments with (block_id, idx, total) and reassembly buffer + timeout.

**channel/** — in-process broadcast bus: `send(frame)` → per-receiver Bernoulli(p) drop
(seeded RNG per run), MTU assert, airtime ledger via `airtime.py` (T_air from doc 02 §6),
per-node byte/airtime counters. Deterministic given seed — integration tests rely on it.

**models/** — `bianchi.solve(N,L)` (damped, doc 02 §6) returning (tau, p_c, S, E_slot);
`energy.per_record(cfg, measured)`; `optimizer.solve(constraints)` = exhaustive search
over the small discrete space (e × σ × placement × b ≤ ~2k points) — no fancy solver;
returns full Pareto set, not just argmin.

**bench/** — `timers.time_ns_loop(fn, iters, warmup)` with GC off; `stats.bootstrap_ci`;
micro (per-op) and macro (end-to-end through emulator) harnesses writing tidy CSVs:
one row = {param..., seed, metric, value}.

## 4. Testing & quality gates (CI-enforced)
- Unit ≥90% line coverage on `src/authbc`; KATs and determinism tests are release gates.
- Property tests: encode/decode round-trip (all encodings, 1k random records),
  tamper-detection, framer pack/unpack inverse.
- Integration: golden end-to-end run (fixed seed) asserting exact counters — catches any
  silent behavior change.
- `ruff check` clean; every module docstring cites the doc-01/02 section it implements.
- GitHub Actions: on push → setup, lint, tests (exclude NS-3 & RPi4 jobs; those run locally
  via Makefile and commit their CSVs).

## 5. Makefile targets (the only supported entry points)
`setup` (venv+pins+pre-commit) · `lint` · `test` · `bench-micro` · `bench-macro` ·
`exp-e1 … exp-e5` (each: run → results/raw/eX_*.csv) · `sim-ns3` (build+run matrix+parse) ·
`figures` (regenerate all from raw) · `all` (lint+test).

## 6. Git/GitHub workflow
**Repo creation is agent-executed** (P0): after `gh auth status` passes (⚠️ D0 is the
only manual step), the agent scaffolds locally, then
`gh repo create fanet-authbc --private --source=. --remote=origin --push`.
**Parallel lanes use git worktrees** (never two agents in one working tree):
`scripts/lane.sh <lane>` creates `../fanet-authbc-lane<N>` on branch `lane<N>`; each lane
edits ONLY its owned paths (ownership map in docs/07 §3); shared files (Makefile,
pyproject, CLAUDE.md, docs/) are P0-frozen — a lane needing a shared change stops and
coordinates at a sync point. Merges to main happen at sync points, fast-forward preferred.
main always green; feature branches `p<phase>/<topic>`; conventional commits
(`feat|fix|test|exp|docs|bench:`); commit raw result CSVs with the config+seed that made
them; tag phase completions (`p1-done`…); never rewrite pushed history; push at every
green checkpoint so any machine can resume with `git clone && make setup && make test`.

## 7. Definition of done (per phase — the agent audits against this)
All acceptance criteria in the phase prompt met; tests green in CI; audit checklist
answered in `docs/audits/p<N>.md` (attack → finding → fix → re-test); results (if any)
committed with seeds; CLAUDE.md decision log updated; tag pushed.
