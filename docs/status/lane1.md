# Lane 1 — status & handoffs

## P0 bootstrap — environment gate (Step 1) · 2026-07-03

**Result: PROCEED.** D0 (gh auth + git identity) satisfied; no ⚠️ stop. Python 3.12 present.

| Check | Command | Output | Verdict |
|---|---|---|---|
| Filesystem | `df -T .` | `/dev/sdd  ext4` (repo at `~/projects/...`) | ✓ Linux FS, not 9p/drvfs |
| Python 3.12 | `/usr/bin/python3.12 --version` | `Python 3.12.3` | ✓ present |
| git | `git --version` | `git version 2.43.0` | ✓ |
| git identity | `git config --global user.{name,email}` | `besco1998` / `mohamed.besco1998@gmail.com` | ✓ |
| gh | `gh --version` | `gh version 2.45.0` | ✓ |
| gh auth (D0) | `gh auth status` | logged in as `besco1998`, scopes `repo`,`workflow` | ✓ **D0 OK** |

### Step 0 — env switched to the existing Python 3.12 (per Mohamed)
Before: `python3` was a pyenv shim → **3.9.10** (pyenv global `3.9.10`); bare `python3.12`
resolved into an unrelated `~/venv-ardupilot`.
Action: **`pyenv global system`** → `python3 --version` = **Python 3.12.3** (shim now execs
the system interpreter). Verified `python3 -m venv` yields a standalone venv based on
`/usr/bin/python3.12` with `include-system-site-packages=false` (no ardupilot leakage).
Reversible: edits `~/.pyenv/version` only.

## P0 — dependency pin verification (Step 3): ALL CLEAN, no drift

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

## P0 — local quality gates (Step 5)
- `make lint` → `All checks passed!`
- `make test` → `9 passed` (8 stub-import params + version check), coverage reported.
- `pre-commit` hook installed; rev pinned to `v0.15.20` via `pre-commit autoupdate`.

## P0 — clean-clone proof (Steps 9–10): PASS (machine-independent)

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

## P0 — audit (Step 11)
`docs/audits/p0.md`: 5 attacks. 1 medium finding **fixed** (persistent wrong-FS guard in
`make setup`) + re-proven by fresh clone; 4 passed no-defect (pin check bites, CI runs real
pytest, `lane.sh` clobber-safe, all ownership-map dirs present).

## Handoff 2026-07-03 — phase P0 (Lane 1, mode TBD)
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
