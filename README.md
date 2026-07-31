# fanet-authbc

Reproducible testbed for the **AUTHBC** thesis: co-optimizing **record encoding × authentication
placement × signature scheme × batching** for blockchain-grade UAV telemetry ledgers over 802.11
FANET links, with a low-rate (LoRa) generalisation. Owner: Mohamed A. Farouk.

Everything here is derived from frozen, seeded data. An automated gate re-derives every
deterministic artifact on each run and fails if a committed number has gone stale.

## What the study found

**A telemetry record is smaller than the signature that authenticates it.** A 64-byte Ed25519
signature against a 45-byte delta-encoded record means authentication, not payload, dominates the
air. The question is what to do about it, and the answer is a co-design.

| result | value |
|---|---|
| **total on-air bytes** vs the inline-CBOR baseline | **−58.68 %** (174.25 → 72.00 B/record) |
| — of which placement × batching | 79.2 % (auth 108 → 27.0 B) |
| — of which encoding | 20.8 % (payload 66.25 → 45.0 B) |
| **supportable neighbourhood** (the load-bearing claim) | **≈3× larger** — 32 → 103 nodes at saturation, 104 → 233 at the measured verifiability boundary |
| verifiability / freshness / channel load | V = 0.95, D = 200 ms ≤ 250 ms, U = 0.56 |

⚠️ **Do not quote the auth-byte cut (75 %) on its own.** It is algebraically **1 − 1/b** — invariant
to header size, signature size, encoding and scheme — so as a headline it credits four axes for what
two produce. See finding F13 in [`docs/audits/model_provenance.md`](docs/audits/model_provenance.md).
The claim that genuinely needs the whole co-design is **feasibility**.

**Two exclusion results bound where any of this applies.** **T6**: a link whose payload cannot hold
one header, one signature and one record carries no per-frame-verifiable telemetry at *any* encoding
or batch size — which removes the four longest-range LoRa modes outright, and loss makes
fragmentation no escape. **Capacity**: LoRa's ALOHA uplink supports **N ≤ 5** at DR5, which with the
121× per-node rate gap compounds to **≈2500× less aggregate capacity** than the 802.11 arm. LoRa is
not a slow 802.11; it is a different regime.

That `N ≤ 5` looks wrong against the node counts usually quoted for LoRaWAN, so it is checked — and
the check goes against us. We simulate the LoRa PHY on the module's harshest MAC preset: **one
channel, one gateway demodulation path, one forced spreading factor.** Mapped through a published
measurement-based model's own curve fit, their ~32 % loss lands at 56 nodes in that configuration
where we measure ~75 % at 50. **We are ≈2.3× more pessimistic, not more optimistic.** `N ≤ 5` is a
**worst-case bound**, not a LoRaWAN network capacity — see [`docs/literature/`](docs/literature/) §5
and finding F19. It is conservative in the direction that matters least here: the claim is that the
low-rate regime is *qualitatively* different, and a conservative bound understates the margin rather
than manufacturing it.

## Status

**P8 — consolidation and paper.** 1077 tests green (1063 fast + 14 frozen-reproduction), `ruff` and
`mypy` clean, `paper/main.pdf` builds at 8 pages. Simulation runs on **NS-3 3.48**; hardware
measurements on **2× Raspberry Pi 4B** with INA219 metering.

Current state is always in **[`CLAUDE.md`](CLAUDE.md)**'s status board. What is still unresolved is
in **[`docs/OPEN_ITEMS.md`](docs/OPEN_ITEMS.md)** and nowhere else.

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
make figures                                 # figures, from the frozen CSVs
make verify-frozen                           # re-derive everything; fail on staleness
```

Simulation and hardware are machine-dependent, run locally, and commit their CSVs; CI runs setup,
lint, tests and the frozen gate only.

```bash
make sim-ns3-matrix sim-ns3-dcf sim-ns3-delay   # 802.11 validation (needs NS-3, see ns3/README.md)
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
| `paper/` | IEEEtran manuscript and bibliography |
| [`docs/literature/`](docs/literature/) | Primary sources, each with its **role** stated: `USED` / `VALIDATES` / `PRIOR ART` / `POSITIONING` |
| `tests/` | Unit, property and integration tests, including the frozen-reproduction gate |

## How this repo stays honest

- **Frozen artifacts + a staleness gate.** Every deterministic CSV is re-derived and compared
  byte-for-byte. This exists because a decision once landed while a frozen artifact kept the old
  value.
- **Retractions stay visible.** Three claims were withdrawn during the work (one theorem, two audit
  findings); each is struck through with the evidence that refuted it, rather than deleted.
- **Every reported configuration carries its alternatives.** This is an optimization problem, so a
  result without its trade-offs is a selection — see [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md).
- **Failed attempts are recorded** in [`docs/LOGBOOK.md`](docs/LOGBOOK.md), so a wrong turn is not
  taken twice.
- **Every source states what it does for the work** — including the two that cost us novelty claims.
  A citation with no stated role is one nobody checks; see [`docs/literature/`](docs/literature/).
- **Types and tests both gate `main`.** They fail differently: adding `mypy` to a suite of 1077
  passing tests still surfaced a Liskov violation, because tests only exercise paths that get
  called and that defect lived in the one nobody calls.

## Requirements

Python **3.12+**; Linux (developed on WSL2 Ubuntu 24.04, repo on the Linux filesystem).
NS-3 3.48 and the RPi4 rig are optional, needed only for the simulation and hardware targets.

## Licence

**All rights reserved** — see [`LICENSE`](LICENSE). NS-3 and the `signetlabdei/lorawan` module are
fetched by the setup scripts, remain under their own GPLv2 terms, and are not redistributed here.
