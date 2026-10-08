# Reproduction guide — set up anywhere, run everything, know what each file does

*Purpose: take a bare machine to a full reproduction of every number in this thesis, and explain
what each source file is for. Written so that future-you on a different laptop — or an examiner —
can get from `git clone` to verified results without asking anyone.*

**Read [`README.md`](README.md) first** for where documents live. This one is about *running* things.

---

## 0. Four paths, pick what you need

Not everything requires everything. The paths are ordered by cost.

| path | what it reproduces | needs | time |
|---|---|---|---|
| **A — analytical** | every byte, energy, optimizer and LoRa-model result; the whole frozen gate | Python 3.12, ~1 GB disk | **~10 min** |
| **B — 802.11 simulation** | the channel-model validation (Bianchi, Ma & Chen, delay) | + NS-3 3.48, ~8 GB disk, 4 GB RAM | +1–2 h (mostly build) |
| **C — LoRa simulation** | the LoRa capacity envelope | + the LoRaWAN contrib module | +30 min |
| **D — hardware** | the measured timings, powers and end-to-end energy | + 2× RPi 4B, INA219, Arduino | +half a day |

**Path A alone reproduces the headline.** Everything in the paper's Results section except the NS-3
validation tables and the measured-energy column comes from path A, because the simulation and
hardware outputs are *committed as frozen CSVs* and the analytical layer reads them.

That is the key design decision to understand: **machine-dependent work runs locally and commits its
data; everything derived from that data is re-computed and checked on every run.**

---

## 1. Path A — analytical (start here)

```bash
git clone https://github.com/besco1998/fanet-authbc.git
cd fanet-authbc
make setup            # creates .venv with Python >=3.12 and pinned deps
make all              # lint + mypy + 2011 fast tests + the 39-test frozen gate
```

`make all` green means **you have reproduced the thesis's deterministic layer.** The frozen gate
re-derives every committed CSV from the current code and fails if a single data row differs.

Regenerate the artifacts yourself if you want to watch it happen:

```bash
make bench-micro                              # p1_sizes.csv, p1_crypto.csv   (x86 timings)
make exp-e1 exp-e2 exp-e3 exp-e4 exp-e5       # the five core experiments
make exp-capacity exp-operating-region        # feasibility envelope; (Λ × D_max) region
make exp-lora exp-lora-codesign               # the low-rate arm
make exp-frames                               # E9–E17: everything computed on the frame as built
make export-framesizes figures                # frame-size table; all figures
make verify-frozen                            # ← the check that matters
make paper thesis                             # numbers.tex from results/, then both PDFs
```

⚠️ **The paper and the corrected thesis chapters contain no typed results.** `make paper` first
runs `analysis/paper_numbers.py`, which writes `paper/numbers.tex` from `results/` and stops if an
artifact no longer supports a sentence the paper makes. To change a number, re-run its
experiment; never edit `numbers.tex`.

⚠️ **`make bench-micro` overwrites `p1_crypto.csv` with *your* machine's timings.** The thesis uses
ARM figures from `results/hw/p1_crypto.authbc-pi4a.csv` (decision D8 — the Pi is the platform).
Running it on x86 and re-freezing would silently swap the platform. `git checkout results/raw/` to
undo.

### Requirements
Python **3.12+**, Linux (developed on WSL2 Ubuntu 24.04). `make setup PYTHON=python3.12` if your
default `python` is older. On WSL, keep the repo on the **Linux filesystem**, not `/mnt/c` — the
timing harness is unusable across the 9p mount.

---

## 2. Path B — 802.11 simulation (NS-3 3.48)

### 2.1 Build

```bash
sudo apt install -y g++ cmake ninja-build python3 libgsl-dev git
cd ns3
wget https://www.nsnam.org/releases/ns-3.48.tar.bz2
tar xf ns-3.48.tar.bz2 && cd ns-3.48
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
nohup ./ns3 build -j 3 > /tmp/ns3build.log 2>&1 &   # ← read the two warnings below
tail -f /tmp/ns3build.log
```

⚠️ **`-j 3`, not the default.** Ninja defaults to one job per core. NS-3 translation units need
1–2 GB each, so on a 16-core / 8 GB host the default (`-j 15`) exhausts memory, the OOM killer
fires, and **WSL itself goes down** — which presents as "the build broke, restart the IDE". Budget
roughly `RAM_GB / 2` jobs.

⚠️ **`nohup`.** A build attached to your IDE's shell dies with the IDE. It takes 40–90 minutes at
`-j 3`; you will want to close the laptop.

Verify: `./ns3 run hello-simulator` exits 0 (it prints nothing — the optimized profile compiles out
`NS_LOG`).

### 2.2 Run

The drivers copy the scenarios into `scratch/`, build and run them, so you never touch NS-3 by hand:

```bash
make sim-ns3              # 2-node smoke, both modes
make sim-ns3-matrix       # N × mode × 10 seeds saturation matrix  (the Bianchi/Ma&Chen validation)
make sim-ns3-dcf          # PHY-trace slot statistics
make sim-ns3-delay        # non-saturated delivery delay  (the C1/D3 result)
make sim-ns3-sensitivity  # deployment-geometry sweep
make sim-ns3-nmax         # the V ≥ 0.95 capacity of each configuration, by direct search
```

⚠️ **`make sim-ns3-nmax` is hours, not minutes.** It runs every node count listed in
`experiments/nmax-direct/plan.txt` at 30 seeds × 20 s. It is resumable: runs already in
`results/raw/ns3_nmax_direct_runs.csv` are skipped, so on a clone it only re-writes the summary.
To re-simulate from nothing, move that file aside first. Each run is seeded by (cell, N, seed) and
is reproducible on its own; `ns3/run_nmax_direct.py --verify` first checks that the cached binary
is the one `./ns3 run` would build. Read `docs/NMAX_DIRECT_EXPECTATIONS.md` before quoting any
value from it.

### 2.3 Using a different NS-3 tree

Every driver imports one constant, so a second version needs no code change:

```bash
AUTHBC_NS3=ns3/ns-allinone-3.41/ns-3.41 python ns3/run_matrix.py   # the old tree
python ns3/compare_versions.py --fresh results/raw/ns3_matrix.csv --frozen <old.csv>
```

That comparator exists because a version migration must *prove* results didn't move. It states its
tolerance before comparing and exits non-zero if any point breaches it.

---

## 3. Path C — LoRa simulation

```bash
cd ns3/ns-3.48/contrib
git clone --depth 1 https://github.com/signetlabdei/lorawan.git
cd ../../..                       # back to repo root
python ns3/patch_lorawan.py       # ← REQUIRED, see below
cd ns3/ns-3.48
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
nohup ./ns3 build -j 3 >> /tmp/ns3build.log 2>&1 &
```

⚠️ **The patch is not optional.** 57 of the module's sources use `NS_LOG_*` macros and none include
`ns3/log.h`; they rely on a transitive include that our `optimized` profile (`NS3_ASSERT=OFF`)
does not provide. Without it you get *"'NS_LOG_FUNCTION' was not declared in this scope"*. The
script is idempotent — re-run it after any `git pull` inside the module.

*Why patch instead of switching build profile:* the frozen 802.11 results were produced under
`optimized`, and changing the profile would confound a module fix with a build-configuration change.

```bash
make sim-lora-capacity    # → results/raw/lora_capacity.csv
```

⚠️ **The module caps the DR5 payload at 222 B** (RP002 Table 12, repeater-compatible) while
`models/lora.py` uses Table 13's 242 B. Both are defensible readings of the standard; the simulation
runs at what the module accepts (218 B, b=6) and the difference is stated in `TRADEOFFS.md`.

---

## 4. Path D — hardware

See [`../hw/SETUP.md`](../hw/SETUP.md) for provisioning and [`../hw/energy_protocol.md`](../hw/energy_protocol.md)
for the measurement procedure. In outline:

```bash
ssh -i hw/keys/pi-a/pi-a pi@<pi-a-ip>          # provision per hw/SETUP.md
bash hw/run_micro.sh                            # timings  → results/hw/p1_crypto.authbc-pi4a.csv
python hw/ina219_capture.py --port /dev/ttyACM0 --out samples.csv &   # on the capture host
python hw/energy_loop.py --seconds 60 --reps 5                        # on the Pi
python hw/ina219_capture.py --reduce <manifest.json> samples.csv --channel 1
python hw/validate_energy_e2e.py --seconds 60 --reps 5                # the end-to-end check
```

The energy harness prints its **predicted** value before reading the meter, deliberately, so a
measurement cannot be quietly fitted to expectation.

---

## 5. What every file does

### `src/authbc/` — the library

**`encodings/`** — the *e* axis. `base.py` defines the encoder protocol; `json_enc`, `cbor_enc`
(canonical, RFC 8949 §4.2), `msgpack_enc`, `delta_enc` (delta-vs-previous with keyframes every
K=16) implement it; `registry.py` maps names to constructors. Delta encoders are **stateful** — a
fresh instance per record emits all keyframes and silently inflates sizes.

**`crypto/`** — the *σ* axis. `ed25519.py`, `ecdsa_p256.py` (both 64 B), `bls.py` (96 B — blspy's
min-pubkey variant, not the 48 B min-sig the spec originally assumed), `registry.py`. `base.py`
documents the size table and that spec gap.

**`ledger/`** — the data structure being authenticated. `record.py` holds the canonical CBOR record
and **the single definition of `canonical_bytes`** used everywhere something is hashed or signed;
`chain.py` the hash chain; `store.py` persistence; `verify.py` chain verification.

**`placement/`** — the placement axis, A/B/C/D. `wire.py` is the frame format and the one place that
decides *what bytes a signature covers* — the audit boundary. `inline.py` (A), `self_batch.py` (B),
`relay_agg.py` (C), `block_agg.py` (D). `framer.py` holds `H_F` (44 B, **measured** from `wire.py`)
and the batch bounds, plus `measure_frame_header_bytes` / `frame_header_bytes_range` — ⚠️ H_f is a
**range, 38–44 B**, not a constant (F43b: canonical CBOR integers are variable-length, so it moves
with `src` and `base_seq`).

**`placement/wire_v2.py` and `session_v2.py` — the lean format (2026-10).** `wire_v2.py` is a
second frame format: integer keys, one chain link per frame, a keyframe followed by delta records
in one varint stream. `session_v2.py` is the protocol around it — `LeanSender`, `LeanReceiver` —
and is where "what happens when a frame is lost, replayed or forged" is running code. The first
format (`wire.py`) is **frozen and untouched** (D6); the two share the ledger record and the
signature. ⚠️ `wire_profile.py`, which measured an integer-keyed header in isolation and produced
the withdrawn "three of seven" exclusion (F44), is **deleted**: it charged neither the chain link
nor a record that decodes alone (F47).

**`models/`** — the analytical layer, and where the theorems live.

| file | implements |
|---|---|
| `bianchi.py` | 802.11a DCF fixed point + **exact OFDM-symbol airtime**. Deliberately has no `T_fx` constant — airtime is a step function (D9), and a test asserts its absence |
| `broadcast_dcf.py` | Ma & Chen's *published* broadcast model. Also carries our discarded reduction as a labelled failure curve |
| `energy.py` | per-record energy, freshness `D(b)`, queueing. Includes the chain-hash term (D7) |
| `optimizer.py` | the Pareto search, plus T2a's binding-ceiling helpers and the certificate-byte term. ⚠️ T6's exclusion tiers moved to `frame.py` in 2026-10 |
| `frame.py` | **the single definition of a frame** (2026-10): what a header, a link, a signature and the records of both formats add up to — held equal to emitted frames by a test — plus verifiability with a keyframe interval (T3′), under bursts and under loss that grows with frame length, and the exclusion test (T6′) |
| `phy.py` | OFDM timing as a parameter, for the model-only sweep over other rates (E15) |
| `stream_auth.py` | per-packet authenticator sizes of the classical stream-signing schemes (E17) |
| `crossover.py` | T4's power-independent scheme crossover |
| `lora.py` | EU868 PHY — every constant transcribed from SX1276 Rev.7 and RP002-1.0.3 |
| `lora_codesign.py` | the LoRa Pareto search, with data rate as a fifth design variable |

**`bench/`** — how measurements are taken. `timers.py` (`time_op` — the primitive every timing
depends on), `stats.py` (bootstrap CIs), `micro.py` (P1 size/crypto/hash benchmarks),
`telemgen.py` (the seeded telemetry generator), `provenance.py` (the `# key=value` headers on every
CSV), `experiments.py` (**the runner registry — every `make exp-*` target lands here**),
`framesizes.py`, `macro.py`. Since 2026-10: `leanframes.py` (sizes of **emitted** lean frames and
record streams, and the single-bit-flip census) and `frame_experiments.py` (the runners of
E9–E17 — every `make exp-frames` artifact lands here).

**`channel/`** — `airtime.py` (frame airtime) and `emulator.py` (in-process broadcast emulator).

**`sim/`** — `dcf_trace.py` analyses NS-3 PHY traces; `dcf_ladder.py` is an independent slot-exact
simulator, written *before* Ma & Chen's paper was found and kept as a cross-check that does not
share the model's assumptions.

### `ns3/` — simulation

| file | purpose |
|---|---|
| `authbc-sat.cc` | saturated 802.11a, both modes — the Bianchi/Ma&Chen validation scenario |
| `authbc-dcf-trace.cc` | instrumented twin of the above; emits slot statistics. Its control is that goodput must reproduce `authbc-sat` exactly |
| `authbc-delay.cc` | **non-saturated** delivery delay. Separate scenario because a saturated queue makes delay diverge by construction. Since 2026-10 it takes `--txJitterMs`, `--txSkewPpm` and `--perNode`; with all three absent the published path is bit-identical |
| `authbc-lora-capacity.cc` | LoRa N-node capacity. **Derived from the module's own working example** after a from-scratch version configured correctly and transmitted nothing |
| `ns3_paths.py` | the one NS-3 root, with `AUTHBC_NS3` override |
| `patch_lorawan.py` | the required `ns3/log.h` patch, idempotent |
| `compare_versions.py` | the migration gate — states tolerance before comparing |
| `run_matrix.py`, `dcf_residual.py`, `run_delay.py`, `run_lora_capacity.py`, `sensitivity.py` | drivers: build, sweep, aggregate seeds, write the CSV |
| `run_nmax_direct.py` | the direct capacity search (2026-10): one row per run in `ns3_nmax_direct_runs.csv`, crossing and bootstrap interval in `ns3_nmax_direct.csv`. Resumable; driven by a plan file |
| `run_phase_lock_diagnostic.py` | per-node delivery under five traffic sources — the evidence for the frozen-phase mechanism (F51) |
| `parse_ns3.py` | scenario output → rows |

### `hw/`, `analysis/`, `experiments/`, `tests/`

`hw/` — `energy_loop.py` (GPIO-marked measurement windows on the Pi), `ina219_capture.py`
(capture + reduce on the host), `validate_energy_e2e.py` (the end-to-end check),
`run_micro.sh`, `provision.sh`, `compare_platforms.py`.

`analysis/` — one figure script per result group; all read frozen CSVs and are byte-stable (Agg
backend, no timestamp metadata) so figures can be diffed. Four scripts are not figure scripts:
`paper_numbers.py` (**every number the paper prints**, → `paper/numbers.tex`),
`verify_citations.py` (each bibliography entry against its registry record — needs network),
`px4_log_sizes.py` (record sizes on pinned public flight logs — needs network), and
`nmax_airtime_line.py` (the arithmetic of follow-up F2 in `NMAX_DIRECT_EXPECTATIONS.md`).

`experiments/<name>/config.yaml` — **one config per experiment, and the only place parameters live.**
`experiments/e4/run_e4.py` is the exception: a standalone script, for the reason its `__init__.py`
explains.

`tests/` — `unit/` mirrors `src/`; `integration/test_frozen_reproducibility.py` **is the staleness
gate**; `integration/test_broadcast_residual.py` guards the channel-model validation.

---

## 6. How the artifacts depend on each other

```
   MEASURED (machine-dependent, committed, never re-derived by the gate)
   ├── results/hw/p1_crypto.authbc-pi4a.csv   ARM timings        [path D]
   ├── results/hw/p1_hash.authbc-pi4a.csv     ARM SHA-256        [path D]
   ├── results/hw/energy/*                    INA219 powers      [path D]
   └── results/raw/ns3_*.csv                  simulation         [paths B, C]
                    │
                    ▼
   DERIVED (deterministic — the gate re-computes and compares all of these)
   ├── p1_sizes ──► framesizes ──► e2, e3
   ├── p1_crypto ──► e4_crossover, e4_bytes
   ├── e1, e5 ◄── configs + measured timings + measured powers
   ├── capacity_envelope, operating_region ◄── bianchi + broadcast_dcf
   ├── lora_eu868, lora_codesign ◄── lora.py + measured timings
   ├── ns3_contention ◄── ns3_matrix
   ├── frame_components, e3_codec_loss, exclusion_matrix, lora_budget,
   │   phy_sweep, stream_baselines ◄── the lean frame as emitted (wire_v2, models/frame.py)
   ├── ns3_nmax_direct ◄── ns3_nmax_direct_runs      (the summary of the simulated runs)
   ├── design_ladder ◄── the frame + measured timings + ns3_nmax_direct
   └── freshness_budget, energy_table ◄── ns3_delay, results/hw/energy
                    │
                    ▼
   paper/numbers.tex ◄── every artifact the paper quotes  (analysis/paper_numbers.py)
                    │
                    ▼
   FIGURES (results/figures/*.png) ── all from frozen CSVs, never from a live run
```

**Rule:** if you change a model, the gate tells you which derived artifact moved. If you change a
*measurement*, consult the blast-radius map in [`DECISIONS.md`](DECISIONS.md) — it lists which
frozen artifacts each input invalidates.

---

## 7. Verifying you got it right

```bash
make verify-frozen      # every deterministic artifact re-derives byte-identically
make all                # + lint + mypy + the full fast suite
```

Spot-checks that a reproduction is genuine:

| check | expected |
|---|---|
| E5 optimized row | delta / ed25519 / placement B / b=4, 71.998 B/record, V=0.95. ⚠️ **As frozen.** That row's V is the model's; with the codec in the loop the same design verifies 0.881 (F46). The corrected first-format design is 74.963 B/record (`design_ladder.csv`, `first/batch-delta`) |
| auth-byte cut | exactly **75.00 %** — and it must stay 75.00 % if you change `H_f` or `g_a`, because it is `1 − 1/b` |
| total-byte cut | 58.68 % in `e5_codesign.csv` (frozen); **56.98 %** for the first format once every frame carries a keyframe, **70.33 %** for the lean format (`design_ladder.csv`) |
| exclusion on EU863-870 | `exclusion_matrix.csv`: of **twelve** data rates, five excluded by the signature alone (50/51 B), three by header + link + signature + one record (115 B), four feasible. ⚠️ The older reading in `lora_eu868.csv` (seven rates, DR3 by "encoding") is the frozen first-format artifact and is superseded (F47) |
| the design as one frame | `design_ladder.csv`, lean `batch-delta`, adopted: 172.999 B frame, **43.25 B/record**, V = 0.95, `sized_from` = "emitted frames" |
| a dependent frame misses V | `e3_codec_loss.csv`, `iid`, p = 0.05, r = 4: V_theory **0.8811**, `meets_target` 0 |
| the paper's numbers | `python analysis/paper_numbers.py --check` → "is current" |
| H_f range | `frame_header_bytes_range(4)` → `(38, 44)` |
| U crossing, both frames | 2.435 at 288 B, 2.367 at 174 B — 0.45 σ apart (M4) |
| unicast ↔ Bianchi | +1.29 / −0.40 % (ns-3.48, 30 seeds) |

---

## 8. Troubleshooting — the traps we actually hit

| symptom | cause and fix |
|---|---|
| build "breaks", WSL disconnects, IDE must restart | **OOM.** Ninja's default job count. Use `-j 3` under `nohup` (§2.1) |
| `'NS_LOG_FUNCTION' was not declared` | LoRaWAN module missing `ns3/log.h`. Run `python ns3/patch_lorawan.py` (§3) |
| ruff reports ~1000 errors | it is linting a vendored NS-3 tree. `pyproject.toml` excludes `ns3/ns-3.*` and `ns3/ns-allinone-*`; a tree at a new path needs adding |
| `mypy` reports "Unused type: ignore" | that is deliberate — `warn_unused_ignores` is on so dead suppressions cannot accumulate. **Delete the comment**, do not turn the flag off |
| a `Framer` subclass raises `ValueError: placement X requires…` | placement-specific arguments are optional in the base signature and checked at run time (F17). Pass `pk=` for A/B/D, `sigs=`/`pks=` for C |
| LoRa scenario sends 0 packets | payload above the module's 222 B limit. It aborts loudly rather than reporting `delivered_frac = 0` |
| a LoRaWAN example "prints 0 0" | you are reading the SF8–SF12 rows, which are zero by construction. **The first row has the numbers** |
| `verify-frozen` fails after a model change | correct behaviour. Re-run the affected `make exp-*` and re-freeze deliberately; check the blast-radius map first |
| timings wildly slow or noisy | repo on `/mnt/c` under WSL, or thermal throttling on the Pi (`vcgencmd get_throttled` must read `0x0`) |
| `bench-micro` changed the headline | it overwrote ARM timings with x86 ones. `git checkout results/raw/p1_crypto.csv` (§1) |

More failure modes, with what was tried and what actually fixed them, are in
[`LOGBOOK.md`](LOGBOOK.md).

---

## 9. Conventions worth knowing before you edit

- **Every module docstring cites the docs section it implements.** If you add a module, cite yours.
- **Parameters live in `experiments/*/config.yaml`**, never inline in a runner.
- **Every CSV carries a provenance header** (`# python=`, `# cpu=`, `# config_hash=`) written by
  `bench/provenance.py`. Never hand-edit a frozen CSV.
- **Tests state expected values independently** — hand-computed from the equations or transcribed
  from a source, never obtained by calling the module under test.
- **A surprising number is a finding, not a nuisance.** State the expectation *before* looking, and
  if it disagrees, investigate rather than widen the tolerance.
