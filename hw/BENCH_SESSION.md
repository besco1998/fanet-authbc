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

## Before you start

* Boards: **Pi 4 (`authbc-pi4a`)** on the energy rig; the **Pi 3B+**; one **BeagleBone Black**
  if it boots (optional — skip it without guilt, see step 4).
* On each board: `git pull`, `git checkout p10-followups`, `make setup`.
* Pi 4 and Pi 3B+: `./hw/provision.sh` (sets the `performance` governor). Fit the heatsink and
  fan as for P7b. The scripts flag a throttled run; a flagged file is not used.
* On this PC (WSL2): the Arduino must be visible (`RIG.md` §6) for steps 2 and 3 only.

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
