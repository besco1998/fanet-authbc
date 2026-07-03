# P0 — BOOTSTRAP  (COPY-PASTE WHOLE FILE)  ·  day 1–2 · blocks everything · ends: tag p0-done

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
