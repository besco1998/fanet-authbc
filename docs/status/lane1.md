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

## SYNC-1 — `p1a-code-done` (2026-07-03)
P1a code complete: `bench/telemgen` (seeded integer-only records), `encodings/{json,cbor,
msgpack,delta}` (round-trip + cross-subprocess determinism + delta recovery), `crypto/
{ecdsa_p256,ed25519,bls}` (uniform API + vendored KATs: RFC 8032, Wycheproof, Chia AugScheme).
**683 tests green**, lint clean, audit in `docs/audits/p1.md` (1 medium fixed). Tag
`p1a-code-done` pushed → **P2 (ledger+wire) and P7b are now unblocked**.

Post-SYNC-1 path: this Lane-1 session continues **P1b** (measurements) next, then **P2**
(pipelined). Lane 2 runs P5 independently.

Two byte-accounting ⚠️ carried into P1b (see audit): BLS 48-vs-96 B, and the T1 φ schema gap.

## Handoff 2026-07-05 — FULL AUDIT (pre-P7b), F1 fixed
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

## Handoff 2026-07-05 — P7a DONE (hardware-prep scripts, tag p7a-done)
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

## Handoff 2026-07-05 — E5 DONE (SYNC-4 integrator, tag e5-done)
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

## Handoff 2026-07-05 — phase P6 DONE (Lane 1 integrator)
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

## Handoff 2026-07-04 — phase P6a DONE (Lane 1 as Lane 3)
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

## Handoff 2026-07-04 — phase P4 DONE (Lane 1, 2-lane mode)
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

## Handoff 2026-07-04 — phase P3 DONE (Lane 1, 2-lane mode)
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

## Handoff 2026-07-04 — phase P2 DONE (Lane 1, 2-lane mode)
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

## Handoff 2026-07-04 — phase P1 DONE (Lane 1, 2-lane mode)
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

## SYNC-1 — `p1a-code-done` (2026-07-03)
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
