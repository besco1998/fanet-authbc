# fanet-authbc

Reproducible testbed for the **AUTHBC** thesis: authenticated telemetry for a hash-chained UAV
ledger, over IEEE 802.11 with a low-rate (LoRaWAN) boundary. Owner: Mohamed A. Farouk.

Every number here is generated from seeded, committed data. A gate re-derives each deterministic
artifact on every run and fails if a committed value has gone stale; the paper's numbers are
written by a script from those artifacts and are never typed.

## What the study found

**A telemetry record is smaller than what authenticates it.** A 64-byte signature and a 32-byte
chain link accompany a record of about 24 bytes.

AUTHBC makes the **frame**, not the record, the unit of authentication: one signature and one
chain link cover several records, and every frame still decodes and verifies on its own. It is
built — a frame format, a sender and a receiver — and every size below is the length of a frame
that was emitted, decoded and verified.

| result | value | artifact |
|---|---|---|
| **Bytes per record on air** | **43.25 B** against 145.77 B for a signature on every record: **70.3 % fewer** | `results/raw/design_ladder.csv` |
| **Neighbours one 802.11a collision domain serves** at 95 % delivery, 50 records/s, 100 ms deadline | **124** [124, 125] against **35** [35, 35] — simulated per configuration in ns-3, 30 seeds, bootstrap interval | `ns3_nmax_direct.csv` |
| **A rule for that capacity** | N_max ≈ 0.05 / (f·(a·T + c)) with a = 0.071, c = 8 µs — fitted to six configurations, then it predicted seven others **within 3.4 %**, with the predictions committed first. A fit at one loss level and one PHY rate, not a model | `docs/NMAX_DIRECT_EXPECTATIONS.md` |
| **Where no frame fits** | **eight of the twelve** EU863-870 LoRaWAN data rates cannot carry one signed, hash-chained frame that verifies alone: five because a 64 B signature exceeds a 50/51 B payload, three because header, link and signature fill 115 B | `exclusion_matrix.csv` |
| **A frame must not depend on its predecessor** | a delta-coded frame that does verifies **0.881** of its records at 5 % frame loss, not 0.95 — so every frame starts with a full record | `e3_codec_loss.csv` |
| **Receiver CPU** | one Raspberry Pi 4 core serves a neighbourhood of 296 nodes with Ed25519 and of 10 with BLS (cryptography only) | `design_ladder.csv` |

**What is not measured.** Contention is simulated, not measured on radios. Record sizes come from
a synthetic generator, checked against twelve public flight logs at 5 Hz and against nothing at
50 Hz. At equal bit error rate a four-record frame is lost more often than a one-record frame, and
the design is then 0.7 points below its verifiability target at the 5 % point. Energy is metered
for the sender only. All of it is stated in the paper's limitations and in
[`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md).

⚠️ **This page said something else until October 2026.** It reported a 58.7 % byte saving and a
"≈3×" neighbourhood for a design that turned out never to have been built: it was a sum of sizes
measured separately. An external review exposed that; building the design changed three headline
results. What was wrong, how it was found and what it cost is in
[`docs/LOGBOOK.md`](docs/LOGBOOK.md) and findings F45–F53 of
[`docs/audits/model_provenance.md`](docs/audits/model_provenance.md).

## Status

Revision after external review, on branch `p9-supervisor-revision`. Simulation runs on
**NS-3 3.48**; hardware measurements on **2× Raspberry Pi 4B** with INA219 metering.

Current state, test counts and decisions pending are in **[`CLAUDE.md`](CLAUDE.md)**'s status
board. What is still unresolved is in **[`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md)** and nowhere
else.

## Quickstart

```bash
make setup        # .venv (Python 3.12) + pinned deps + pre-commit
make all          # lint + types + tests + the frozen-reproduction gate
make help         # every entry point
```

`make all` green means you have reproduced the thesis's deterministic layer. For a new machine —
including NS-3, the LoRa module and the hardware rig — follow
**[`docs/05_REPRODUCTION_GUIDE.md`](docs/05_REPRODUCTION_GUIDE.md)**, which also explains what every
source file does and lists the traps we actually hit.

Reproducing the results:

```bash
make exp-e1 exp-e2 exp-e3 exp-e4 exp-e5      # byte / loss / energy / co-design experiments
make exp-lora exp-lora-codesign              # the low-rate arm
make exp-capacity exp-operating-region       # feasibility envelope, (Λ × D_max) region
make exp-frames                              # everything computed on the frame as built (E9–E17)
make figures                                 # figures, from the frozen CSVs
make verify-frozen                           # re-derive everything; fail on staleness
make paper                                   # numbers.tex from results/, then the PDF
```

Simulation and hardware are machine-dependent, run locally, and commit their CSVs; CI runs setup,
lint, tests and the frozen gate only.

```bash
make sim-ns3-matrix sim-ns3-dcf sim-ns3-delay   # 802.11 validation (needs NS-3, see ns3/README.md)
make sim-ns3-nmax                               # capacity by direct search — hours; resumable
make sim-lora-capacity                          # LoRa capacity (needs the LoRaWAN contrib module)
make hw-capture hw-reduce                       # RPi4 + INA219 energy campaign
```

⚠️ **Building NS-3 on a memory-limited host:** use `-j 3` under `nohup`. Ninja's default (`-j 15`
here) exhausts the VM and the OOM killer takes WSL down mid-build, which looks like a broken build.
See [`ns3/README.md`](ns3/README.md).

## Layout

| path | contents |
|---|---|
| [`docs/`](docs/) | Specification, theory, decisions, audits. **Start at [`docs/README.md`](docs/README.md)** — it indexes everything |
| `src/authbc/` | Library: encodings, crypto, ledger, placements, channel/energy/optimizer models |
| `experiments/` | One config per experiment; runners live in `src/authbc/bench/` |
| `results/raw/` | **Frozen** CSVs with provenance headers; `results/figures/` derives from them |
| `ns3/` | Simulation scenarios and drivers (the NS-3 tree itself is git-ignored) |
| `hw/` | Hardware harnesses, INA219 rig, measurement protocol |
| `paper/` | The results paper, the methods paper, the bibliography, and `numbers.tex` — generated, never edited |
| `thesis/` | The thesis — a draft; read `thesis/STATUS.md` first |
| [`docs/literature/`](docs/literature/) | Primary sources, each with its **role** stated: `USED` / `VALIDATES` / `PRIOR ART` / `POSITIONING` |
| `tests/` | Unit, property and integration tests, including the frozen-reproduction gate |

## How this repo stays honest

- **Frozen artifacts + a staleness gate.** Every deterministic CSV is re-derived and compared
  byte-for-byte. This exists because a decision once landed while a frozen artifact kept the old
  value.
- **Retractions stay visible.** Claims withdrawn during the work — a theorem, several audit
  findings, a headline count — are struck through with the evidence that refuted them, not
  deleted.
- **Predictions are committed before the data,** in data-free commits whose order anyone can
  check in the history (see the pre-registrations listed in [`docs/README.md`](docs/README.md)).
  Several failed — among them the prediction that one load ceiling gives every configuration's
  capacity — and are reported as failures.
- **No typed results.** Every number in the paper is a macro that a script writes from
  `results/`; a sentence that states a verdict is checked against the artifact by the same script.
- **Every reported configuration carries its alternatives.** This is an optimization problem, so a
  result without its trade-offs is a selection — see [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md).
- **Failed attempts are recorded** in [`docs/LOGBOOK.md`](docs/LOGBOOK.md), so a wrong turn is not
  taken twice.
- **Every source states what it does for the work** — including the two that cost us novelty claims.
  A citation with no stated role is one nobody checks; see [`docs/literature/`](docs/literature/).
- **Types and tests both gate `main`.** They fail differently: adding `mypy` to a suite of 1077
  passing tests still surfaced a Liskov violation, because tests only exercise paths that get
  called and that defect lived in the one nobody calls.
- **Building the thing.** The errors of October 2026 had survived two audits and thirteen hundred
  tests because each part was right. What exposed them was assembling the parts into one frame
  with a receiver that could refuse it.

## Requirements

Python **3.12+**; Linux (developed on WSL2 Ubuntu 24.04, repo on the Linux filesystem).
NS-3 3.48 and the RPi4 rig are optional, needed only for the simulation and hardware targets.

## Licence

**All rights reserved** — see [`LICENSE`](LICENSE). NS-3 and the `signetlabdei/lorawan` module are
fetched by the setup scripts, remain under their own GPLv2 terms, and are not redistributed here.
