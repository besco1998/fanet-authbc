# One bench session — five measurements, about three hours

*For Mohamed. Decided 2026-10-08: the four small measurements the revision left open are done in
one sitting. Everything here reuses the rig and the boards as they were set up for P7b
([`SETUP.md`](SETUP.md), [`RIG.md`](RIG.md), [`energy_protocol.md`](energy_protocol.md)); nothing
new has to be wired. Each step says what to run, where, how long it takes and what it writes.*

**What it closes** (`docs/OPEN_ITEMS.md`):

| step | closes | question it answers |
|---|---|---|
| 0 | G22 | Is the current sensor's reading right in absolute terms? |
| 1 | G9 | What do the lean format's sender and receiver cost on the Pi 4, per frame? |
| 2 | G9 | Does the meter agree with that timing, for the design that is actually reported? |
| 3 | G11 | The one energy row that was not usable (three of its five repetitions were contaminated) |
| 4 | G15 | Where does the receiver's CPU become the limit on a smaller board? |
| 5 | G19 | What does Ed25519 batch verification buy on these boards? |

## Where it stands (2026-10-09, finding F77)

| step | state |
|---|---|
| 0 calibrate the meter | **not done** — no reference resistor at the bench |
| 1 time the lean sender and receiver | **done on `authbc-pi4b`**: 0.87 ms and 1.41 ms per four-record frame — both *under* the ranges below; one core of the prototype serves 57 nodes |
| 2 meter the lean sender | **done on `authbc-pi4b`, channel 2, after the rig check passed** (F79): 155.4 µJ per record with four records to a frame, 273.1 with one; a control repeating July's baseline row gave 116.2 against July's 118.8. Every registered range held |
| 3 re-meter the contaminated row | **done** (F79): 120.9 µJ per record, ten of ten repetitions usable |
| 4 smaller boards | **not done** — they were not switched on |
| 5 Ed25519 batch verification | **done on `authbc-pi4b`**: 0.46 of the cost per signature in a batch of 64 — inside the range below |

⚠️ **The board named below as the device under test, `authbc-pi4a`, was found re-installed**
(Debian 13, Python 3.13, no project environment). Every step done was run on `authbc-pi4b`,
which has July's software and times signatures within 0.4 % of what `authbc-pi4a` did; it is
on meter **channel 2** since the supplies were swapped. What remains is step 0 (a 10 Ω
resistor) and step 4 (the smaller boards).

## Expected of the energy runs of 2026-10-09 — written and committed before the first of them

The rig is not the one this sheet was written for. The board under test is `authbc-pi4b` (it
has July's software), on meter channel 2, after the rig check passed. The power constant
0.749 W below was measured in July on the *other* board through the *other* sensor. So the
first run is a control, and the rest are read in its light.

| run | what | expected | from |
|---|---|---|---|
| C | **control**: July's baseline row again — CBOR, every record signed, first format | added power **0.72–0.79 W**; **113–125 µJ per record** | July: 0.753–0.761 W and 118.5–119.9 µJ; this board runs that pipeline at 99.6 % of July's rate |
| L4 | lean sender, four records per frame (step 2a) | the script's prediction, 0.749 W × 0.868 ms / 4 = **162.6 µJ per record**; metered within **10 %** of it (146–179) | timing of F77; the script's own acceptance, which is tighter than the 15 % of the table below |
| L1 | lean sender, one record per frame (step 2b) | 0.749 W × 0.379 ms = **284.1 µJ**; within 10 % (256–313) | the same |
| J | the JSON row again, ten repetitions (step 3) | **115–127 µJ per record**; every idle window within 0.2 W of the others | July's two usable repetitions: 119.3 and 121.8 |

Also expected: in every run the added power is 0.70–0.80 W; and batching saves 35–50 % of the
lean sender's energy per record (by timing, 43 %).

**If the control is outside its range, stop:** the two sensors or the two boards differ, and no
figure of today can be set beside July's. A window is used only if the firmware's flags and the
kernel's count of under-voltage events are unchanged across it. Step 0 is still not done — no
reference resistor — so every figure carries the sensor's unmeasured gain, as July's do.

## What is expected, written before anything is measured (Law 6)

| quantity | expected | from |
|---|---|---|
| Pi 4: lean **sender**, one 4-record frame | **1.0–2.5 ms** | 0.42 ms on a loaded x86 desktop; the Pi 4 is 2.7× slower than it at Ed25519 verification, and interpreted code usually fares worse |
| Pi 4: lean **receiver**, one 4-record frame | **2–5 ms** | 0.90 ms on the same desktop |
| … of which signature verification | 0.26 ms | measured in P7b; unchanged |
| neighbours one Pi 4 core can **decode and verify**, design (b = 4) | **15–40** | 1 / (12.5 frames/s × receiver time). ⚠️ The paper's 296 charges verification and hashing only |
| lean sender energy per record, metered against timed | within 15 % | the first format's gap was 7–14 %, all frame assembly |
| Pi 3B+: Ed25519 verify | 0.5–0.9 ms | 2–3× the Pi 4's 0.26 ms (Cortex-A53 against A72) |
| BeagleBone Black: Ed25519 verify | 1.5–4 ms | one 32-bit Cortex-A8 core |
| batch of 64 against one at a time, per signature | **0.45–0.60×** | 0.49× on x86 (best of 300 repetitions); the Ed25519 paper reports 0.49× |

If a figure lands outside its range, that is a finding to explain, not a number to average
away. Tell the agent and send the files as they are.

⚠️ **The one result that may change a sentence of the paper.** The receiver-CPU column charges
cryptography only. If the receiver's real time on the Pi 4 is what the desktop suggests, a
Python receiver on one core falls behind long before 124 neighbours. The paper says, as of
2026-10-08, that decoding in the prototype is not charged; step 1 turns that sentence into a
number.

## What the agent can run without you (2026-10-09)

The radio measurements of August were driven from the PC over the network. If the boards are
**switched on and reachable** (`ssh pi@<address>` works from WSL), the agent can run steps 1,
4 and 5 below, and the **contention experiment** (`docs/CONTENTION_HW_EXPECTATIONS.md`, open
item G4) — two Pi 4 are enough for its sharpest case, the Pi 3B+ makes three. Tell it the
addresses. Steps 0, 2 and 3 need the meter wired to the PC, and that needs your hands.

## Before you start

* Boards: **Pi 4 (`authbc-pi4a`)** on the energy rig; the **Pi 3B+**; one **BeagleBone Black**
  if it boots (optional — skip it without guilt, see step 4).
* On each board: `git pull`, `git checkout p10-followups`, `make setup`.
* Pi 4 and Pi 3B+: `./hw/provision.sh` (sets the `performance` governor). Fit the heatsink and
  fan as for P7b. The scripts flag a throttled run; a flagged file is not used.
* On this PC (WSL2): the Arduino must be visible (`RIG.md` §6) for steps 2 and 3 only.
* **Before step 0, 2 or 3: the rig check must pass** (`RIG.md` §8, item 7 — 45 seconds). On
  2026-10-09 it failed twice for two different reasons, neither of which an energy run shows.

## Step 0 — calibrate the meter (on the rig, 5 min) — closes G22

No calibration of the INA219 against a known load is on record, so every energy figure so far
is accurate to the sensor's factory tolerance and no better (finding F66). Before steps 2 and 3:

1. Put a **known resistor** in place of the Pi: 10 Ω, 5 W or more, across the 5 V supply
   (0.5 A, 2.5 W). Measure its resistance with a multimeter first and write the value down.
2. Run the capture for 60 s and note the mean voltage, current and power it reports.
3. Expected power is V²/R with the *measured* R. Send the agent the three numbers and R.

**Expected:** within 2 % of V²/R. More than that: re-seat the wiring and repeat before going on.
The ratios in the paper do not depend on this step; the microjoule values do.

## Step 1 — time the lean sender and receiver (Pi 4, 5 min)

```bash
./hw/run_micro.sh
```

Writes `results/hw/p1_{sizes,crypto,lean}.authbc-pi4a.csv`. Read the four `lean` rows:

```bash
grep -v '^#' results/hw/p1_lean.authbc-pi4a.csv
```

Note the two `frame_send` medians (rows with `agg_b` 1 and 4): steps 2a and 2b need them.

## Step 2 — meter the lean sender (Pi 4 on the rig, 2 × 11 min)

On this PC, start the capture first and leave it running (`RIG.md` §7):

```bash
./hw/ina219_capture.py --port /dev/ttyACM0
```

On the Pi 4, with `<ns4>` and `<ns1>` the two medians from step 1:

```bash
# 2a — the design: one signature per four records
python3 hw/validate_energy_e2e.py --format lean --batch 4 --t-frame-ns <ns4> \
        --p-cpu-w 0.749 --seconds 60 --reps 5 --out results/hw/energy/e2e_lean_b4/
# 2b — its baseline: one record per frame
python3 hw/validate_energy_e2e.py --format lean --batch 1 --t-frame-ns <ns1> \
        --p-cpu-w 0.749 --seconds 60 --reps 5 --out results/hw/energy/e2e_lean_b1/
```

Each prints its **expected** energy per record before it starts. Stop the capture (Ctrl-C) after
each and reduce it against that run's manifest:

```bash
./hw/ina219_capture.py --reduce results/hw/energy/e2e_lean_b4/manifest_*.json \
                                results/hw/energy/samples-<UTC>.csv --channel 1
```

## Step 3 — re-meter the row that was not usable (Pi 4 on the rig, 21 min)

Same capture procedure; ten repetitions this time:

```bash
python3 hw/validate_energy_e2e.py --batch 1 --encoding json --record-bytes 191 \
        --t-enc-ns 51370 --seconds 60 --reps 10 --out results/hw/energy/e2e_ajson_r10/
```

A repetition whose idle window sits more than 0.2 W above the others is the contamination that
spoiled the first attempt (a background process). If it shows again, stop, find the process
(`top`), and repeat — do not keep the run.

## Step 4 — crypto timing on the smaller boards (10 min each, unattended)

On the **Pi 3B+**:

```bash
./hw/run_micro.sh
```

On the **BeagleBone Black**, the same command. ⚠️ `blspy` may not build on a 32-bit board
(`SETUP.md` §9). If `make setup` fails on it, that is expected: note the error and skip the
board — the Pi 3B+ is the point that matters.

## Step 5 — Ed25519 batch verification (every board, 2 min each)

```bash
./hw/ed25519_batch/build.sh
```

Needs `git` and `gcc` on the board and a network connection the first time (it fetches a small
public-domain library at a pinned commit). Writes `results/hw/ed25519_batch.<host>.csv` and
prints six lines: `batch = 1` is one signature at a time.

## When you are done

```bash
git add results/hw/p1_*.csv results/hw/ed25519_batch.*.csv results/hw/energy/e2e_lean_b4 \
        results/hw/energy/e2e_lean_b1 results/hw/energy/e2e_ajson_r10 results/hw/meta
git commit -m "data(hw): bench session — lean codec, energy rows, smaller boards, batch verify"
git push
```

Add the files **by name**, as above — never `git add .` in this repository. Then tell the agent
the session is done. It reduces the files, compares each figure with the table at the top, and
updates the paper's CPU and energy rows; the response to the supervisor goes out after that.

## Expected of the re-timing of 2026-10-09 — the receiver keeps frames (audit F80, G28)

*Written before either run below. Mohamed's go-ahead of 2026-10-09: the receiver is to keep
every accepted frame, and the two frames of an equivocation, so that what it holds can be
checked by a third party. That adds work to the receive path whose time is in the paper
(1.411 ms for a four-record frame, 0.653 ms for one record; 57 nodes per core).*

Board: `authbc-pi4b`, governor `performance`, nothing else running, `hw/run_micro.sh` as in
step 1. Two runs in one session, so that the change is compared with the board as it is today
and not with the morning's session.

| run | code | expected |
|---|---|---|
| control | the receiver as timed this morning (`session_v2.py`, `store.py` unchanged; checked by hash on the board) | `frame_receive` within ±2 % of the morning's medians: **1.383–1.439 ms** (four records), **0.640–0.666 ms** (one) |
| new | the receiver that keeps frames | `frame_receive` between **1.00 and 1.02 times the control**, both batch sizes. The change is four dictionary look-ups and four dictionary entries per four-record frame; I expect +3 to +12 µs |
| both | — | `frame_send` within ±1 % of each other: the sender's code is not touched |

**Consequence if it holds.** One core serves 1 + ⌊1/(12.5 · t)⌋ nodes: **57** while t ≤ 1.4286 ms,
56 above it. The morning's 1.4112 ms leaves 1.2 %.

**If the control is outside its range:** the board is not in the state it was timed in. Say so,
and compare the new code with today's control only; the morning's figure is then not repeated
as if it still stood. **If the new code is above 1.02:** reported as it is, with the nodes per
core it gives; the code is not tuned to get under.

**What the paper will use.** The receiver's times from the new run — the code that is in the
repository. The sender's times stay the morning's: its code is unchanged, and the energy runs
of this sheet were registered against exactly those figures.

### Outcome (2026-10-09, runs of 12:05:26Z and 12:13:19Z) — every line held

| | morning | control | receiver that keeps frames | against the control |
|---|---|---|---|---|
| `frame_receive`, four records | 1.4112 ms | 1.4159 ms (inside 1.383–1.439) | **1.4260 ms** | **1.0071** — +10.0 µs (expected +3 to +12) |
| `frame_receive`, one record | 0.6530 ms | 0.6536 ms (inside 0.640–0.666) | **0.6582 ms** | **1.0070** — +4.6 µs |
| `frame_send`, four records | 0.8681 ms | 0.8693 ms | 0.8680 ms | 0.9985 |
| `frame_send`, one record | 0.3793 ms | 0.3798 ms | 0.3793 ms | 0.9986 |

Both runs: governor `performance`, `throttled=0x0` before and after, 51–60 °C, checksums equal
to the morning's (the same computation). One core still serves **57** nodes, by a margin of
0.18 % (1.4260 ms against the 1.4286 ms at which it becomes 56); 124 nodes still need 2.2 cores.
The receiver costs 5.5 times its verification (5.4 before).

**What I did during the runs, since it is the kind of thing that moved a number this
morning:** I logged in to the board four times while the second run was going, each for about a
second, to read the end of its log; one of those fell at the start of the lean timing. The
figure is a median of 10 000 frames and the sender's rows, timed in the same minute, are within
0.15 % of the control's. I do not think it moved anything, and I cannot show that it did not.

The three source files of the receive path were read on the board after the run and are the
ones in the repository, byte for byte (SHA-256; `tests/test_bench_session_hw.py` holds them):

    42f954ad58cdeeb98e1b3b00da057c7a7bc8aa0a13a64172102bed90997fae8a  src/authbc/placement/session_v2.py
    5fc6c4a98a8b4b14021b04192b9178e8e598abd553eb055bf3f8024a31dd2ff2  src/authbc/ledger/store.py
    6edf42a8af07c83e96f34e34b4ecac3104ed71e75dec0a5f360ddb7eddb94db0  src/authbc/placement/wire_v2.py

Files: `results/hw/p1_lean.authbc-pi4b.control-20261009.csv`,
`results/hw/p1_lean.authbc-pi4b.frames-kept.csv` and, for the same session's signature
timings, `results/hw/p1_crypto.authbc-pi4b.frames-kept.csv`.
