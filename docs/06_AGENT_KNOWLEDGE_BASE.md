# 06 — AGENT KNOWLEDGE BASE (pitfalls, gotchas, protocols)

## 1. WSL2 essentials
- Repo MUST live on the Linux filesystem (`~/...`). `/mnt/c` paths break NS-3 builds and
  slow I/O 10–50×. Check with `df -T .` (ext4, not 9p/drvfs).
- `.wslconfig` (Windows side): `memory=12GB`, `processors=N` — NS-3 link steps OOM below
  ~8 GB. Restart WSL after edits (`wsl --shutdown`).
- Clock skew after host sleep corrupts wall-clock timing; bench code uses
  `time.perf_counter_ns` (monotonic) and discards any run spanning a suspend.
- CPU frequency scaling: note governor in every bench CSV (`cpufreq` may be hidden under
  WSL; record `lscpu` model + note "WSL, governor uncontrolled" honestly; RPi4 runs pin
  `performance`).

## 2. NS-3 3.41 on WSL2 (follow exactly; deviations are ⚠️ D4)
```
sudo apt install g++ cmake ninja-build python3 libgsl-dev
wget https://www.nsnam.org/releases/ns-allinone-3.41.tar.bz2 && tar xf ...
cd ns-3.41 && ./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
./ns3 build   # expect 15–40 min first time
./ns3 run hello-simulator   # gate: must print before proceeding
```
- Custom scenario lives in `scratch/authbc-sat.cc` (or contrib); rebuild via `./ns3 build`.
- **Broadcast has no ACKs/retries in 802.11.** Decide and DOCUMENT: either (a) simulate
  saturated *unicast* to match classic Bianchi (with ACKs), or (b) broadcast + the
  no-ACK Bianchi variant (remove ACK/SIFS from T_s, no retransmission). Mixing them is
  the #1 way to fabricate a fake "model gap". Recommended: run BOTH, report both.
- Bianchi-vs-NS-3 gap sources, as MEASURED at P6/P7 (list, quantify, never silently correct):
  **backoff counter Consecutive Freeze Process** (the big one — 16× on broadcast; use Ma & Chen's
  model, docs/02 §6a, not a reduction of the unicast one); **F8** sinks outliving sources
  (~4.8 %); **D9** OFDM symbol quantisation (0.41 % on data, 12.1 % on an ACK). Frame **capture is
  0 %** in the validation scenario — NS-3 clamps log-distance below d₀=1 m, so the co-located
  cluster is already equal-power and `--equalPower` is byte-identical. Also note EIFS is NOT
  triggered by broadcast collisions (the PHY drops at preamble detection, so no RX-error).
- Use **PacketSocket + PacketSink** for both modes, not FlowMonitor: MAC-level goodput with no
  ARP/IP artifacts. Parse with the committed `ns3/parse_ns3.py` / `ns3/run_matrix.py`; never
  hand-copy numbers. Instrumented twin for slot statistics: `ns3/authbc-dcf-trace.cc`.

## 3. Timing methodology traps
- Disable GC around timed loops (`gc.disable()`), re-enable after; warmup ≥1k iters.
- Guard against dead-code elimination: accumulate a checksum of outputs and assert it.
- ≥10k iterations per op OR total ≥200 ms, whichever larger; report median + bootstrap CI.
- Never time through pytest overhead; bench harness is standalone.

## 4. Crypto libraries
- `cryptography`: Ed25519 = `Ed25519PrivateKey`; ECDSA P-256 = `ec.ECDSA(hashes.SHA256())`.
  DER-encoded ECDSA sigs vary 70–72 B — for byte accounting use raw r||s (64 B) via
  `utils.decode_dss_signature` + fixed-width encode; document this.
- **Ed25519 batch verification is NOT exposed in `cryptography`/PyNaCl.** Default scope:
  sequential verify (claims worded accordingly). True batch (~2× at b≈64) needs
  ed25519-dalek via pyo3 — that is ⚠️ D3, stretch only.
- `blspy` (Chia): use `AugSchemeMPL` (distinct messages ⇒ rogue-key safe for our use;
  document why PopScheme unnecessary here). API: `sign`, `aggregate`,
  `aggregate_verify(pks, msgs, agg_sig)`. If wheel build fails on the machine: STOP →
  Failure Report → try `pip install blspy` upgraded pip / build deps (`cmake`,
  `build-essential`) → last resort py_ecc fallback (⚠️: ~100× slower; timing tables must
  be labeled "py_ecc — not representative", and D3-style native fix proposed).
- KAT sources: RFC 8032 §7.1 (Ed25519), NIST CAVP ECDSA P-256 SHA-256, BLS sigs
  draft-irtf-cfrg-bls-signature test vectors. Vendor them into tests/vectors/ with URLs.

## 5. cbor2 / encodings
- Pin `cbor2==5.8.0` (5.8.1 regression in project history). `dumps(obj, canonical=True)`
  for RFC 8949 §4.2 core deterministic encoding. Determinism test: encode the same 1k
  records in two subprocesses, compare SHA-256 of concatenation.
- Floats break canonical stability across platforms if NaN/precision sneak in — telemetry
  payload uses INTEGERS ONLY (fixed-point per docs/04 §1). Enforce with a schema check.
- Delta encoder: decoder keeps per-src state; a lost frame desyncs until next keyframe —
  emit `desync_count` metric; tests cover loss-then-keyframe recovery.

## 6. GitHub / CI
- CI = lint + unit/property/integration only (no NS-3, no benches — machine-dependent).
- Benches and experiments run locally via make and COMMIT their CSVs (results/raw is
  data-of-record; never regenerate over frozen data — ⚠️ D6).
- `gh auth status` at P0; pushes at every green checkpoint; tags `p<N>-done`.

## 7. FAILURE REPORT template (docs/failures/YYYYMMDD-<slug>.md)
```
WHAT: exact command + full error output (verbatim)
CONTEXT: phase, module, commit hash, environment (uname, python, package versions)
REPRO: minimal reproduction steps/script
HYPOTHESES: H1/H2/H3 with the evidence that supports/kills each
ROOT CAUSE: the actual cause (not the symptom)
FIX: change made + why it addresses the root cause
REGRESSION GUARD: test added
VERIFICATION: full suite output after fix
```

## 8. Parallel-execution gotchas (when D7 = 2-lane or 3-lane)
- One Claude Code session per **worktree**, never two per directory (state files clash).
- `gh auth` and git identity are per-user, shared across worktrees — set once (D0).
- Lane branches rebase on main ONLY at sync points; never cherry-pick between lanes.
- pytest caches / venv are per-worktree: each lane runs `make setup` once in its tree.
- Status/handoff files are per-lane (`docs/status/lane<N>.md`) precisely so lanes never
  write the same file; CLAUDE.md's status board is updated only on main at sync points.
- If two lanes accidentally touch the same file: STOP, do not resolve by guessing —
  the ownership map (docs/07 §3) decides the owner; the other lane reverts.

## 9. Scientific red flags (STOP conditions, always)
Suspiciously perfect model fits (<1% everywhere) · CI widths ~0 · throughput above the
theoretical PHY bound · verify faster than sign for the same scheme · byte counts that
change between identical seeded runs · any KAT/determinism failure · any urge to widen a
tolerance to make a test pass.
