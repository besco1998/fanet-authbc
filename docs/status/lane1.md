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

## P0 — clean-clone proof (Steps 9–10)
_(filled in after the GitHub repo exists)_
