# P7b energy-measurement protocol (RPi4)

Exact, reproducible procedure for the per-operation energy tables and the power constants fed back
into the E4/E5 model layers. Implements docs/04 §4 and docs/06 §1. **P7a commits this document; the
runs themselves are P7b** (need 4× RPi4 + the ⚠️ D5 meter). Nothing here is executed until hardware
and the meter decision are in place.

## What we measure and why
The E4/E5 energy model (`src/authbc/models/energy.py::Measured`) consumes five per-device numbers:

| field | meaning | source |
|---|---|---|
| `t_enc_s`, `t_sign_s`, `t_verify_s` | per-op wall time | `hw/run_micro.sh` (P1 harness on the Pi) |
| `t_agg_build_s`, `t_agg_verify_s` | BLS aggregate build / verify per frame | `hw/run_micro.sh` |
| `p_cpu_w` | **incremental** CPU power while computing | **this protocol** |
| `p_radio_w` | **incremental** radio power (receive/decode path) | **this protocol** |

E5 currently uses **nominal** `p_cpu_w = 3.0 W`, `p_radio_w = 0.7 W` (`experiments/e5/config.yaml`).
P7b **replaces exactly those two constants** with the medians measured below, then re-runs the E4/E5
model layers → the hardware-grounded tables. The auth-byte headline is power-free and does not change.

## Equipment (⚠️ D5)
- 1× inline USB power meter, e.g. **UM25C** (~$30) — Bluetooth/USB logging preferred so power is
  sampled programmatically, not read by eye. D5 selects the exact model.
- A **known resistive load** for calibration (a USB constant-current dummy load, or a known power
  resistor across 5 V with a measured value).
- The RPi4 under test, powered **through the meter** (meter between the PSU and the Pi's USB-C in).

## Step 0 — calibrate the meter (once per session)
1. Put the meter inline with the known resistive load (not the Pi).
2. Record the meter's V and I; compute expected `P = V²/R` (or `V·I` from a trusted reference).
3. `offset% = 100·(P_meter − P_expected)/P_expected`. Record it in the run header.
   **If |offset%| > 2 %, stop** — re-seat contacts / try another cable before measuring the Pi.

## Step 1 — pre-flight (every run)
- `hw/provision.sh` already applied → governor `performance` (verify:
  `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` = `performance`).
- Headless (no desktop), Wi-Fi power-save off, screen blank — the idle draw must be steady.
- Let the board sit idle ~3 min to reach thermal steady state before the first idle window.
- Log `vcgencmd measure_temp` every 5 s and `vcgencmd get_throttled` before+after **every** window.

## Step 2 — idle baseline `P_idle`
With no benchmark running, sample meter power for **60 s**; `P_idle` = mean over the window.
Re-measure `P_idle` at the start of each op block (drift guard).

## Step 3 — per-op active power `P_loop` and `energy/op`
For each op (see op set below): run it in a **tight loop for `t_loop` = 60 s**, counting `n_ops`
completed (the loop uses the P1 timing rules — see driver spec); sample meter power over the same
window; `P_loop` = mean.

    energy_per_op = (P_loop − P_idle) · t_loop / n_ops        # J/op  (W·s / op)

Repeat each op **≥ 5 times**; report **median + bootstrap CI** (same CI machinery as P1,
`bench.stats.summarize`). The incremental power itself is the model constant:

    p_cpu_w   = median(P_loop − P_idle)  over the crypto/encode loops
    p_radio_w = median(P_loop − P_idle)  over a saturated receive/decode loop (Step 4)

Cross-check: `energy_per_op ≈ p_cpu_w · t_op` with `t_op` from `hw/run_micro.sh` — a >10 % gap is a
STOP (Law 6): reconcile before recording.

## Step 4 — radio power `p_radio_w`
The model's `p_radio_w` is the **receive/decode** path power. Measure it with the golden 2-node
ad-hoc link (P7b step 5) saturated: the device under test **receives+decodes** a continuous broadcast
stream for 60 s; `p_radio_w = mean(P_loop − P_idle)`. (Also record the TX-side incremental power for
the paper's discussion, but the model field is the receive value.)

## Op set (each measured per Step 3)
- **Per scheme** (Ed25519, ECDSA-P256, BLS): `sign`, `verify` on the fixed 200 B seeded message.
- **BLS aggregate**: `aggregate(b)` and `agg_verify(b)` for `b ∈ {2,4,8,16,32}`.
- **Per encoding** (json, cbor, msgpack, delta): `encode` one record (delta = one **stateful**
  encoder reused across the stream — a fresh-per-record encoder emits all keyframes, the Law-6
  pitfall from the P1 audit).

## Tight-loop driver — **implemented** as `hw/energy_loop.py`
Reuses the P1 harness rules verbatim (docs/06 §3): `time.perf_counter_ns`, `gc.disable()` around the
loop, ≥1000 warmup iters, an accumulated **checksum** of outputs (defeats dead-code elimination),
fixed 200 B seeded input. Difference from P1: each op runs **for a wall-clock window** (60 s) rather
than a fixed iteration count, emitting `n_ops` and `t_loop` so it aligns with the meter window. It
reuses `authbc.crypto.registry` / `authbc.encodings.registry` — the same code paths `hw/run_micro.sh`
times, so `t_op` is consistent across the timing and energy runs.

It also **drives the GPIO17 sync line in-process** around every window (libgpiod v2 → v1 → sysfs, with
release guaranteed by `finally` + `atexit` + SIGINT/SIGTERM), and writes a manifest JSON that
`hw/ina219_capture.py --reduce` merges with the Arduino sample stream. See `hw/RIG.md` §7 for the run
order. Throttled windows are excluded and reported; a window/segment mismatch aborts the reduction
rather than guessing an alignment.

## Thermal guard (binding)
`get_throttled` is a bitmask; **any value other than `0x0` invalidates the run** (undervolt or
thermal cap). Discard-and-repeat, or flag the output filename `.THROTTLED` and exclude it from the
paper tables. Also watch temp: if it climbs toward the RPi4 cap (~80–85 °C) mid-window, add a cooler
/ longer cool-down and re-run. Every energy CSV records temp min/max and `get_throttled` before/after.

## Recording (Law 7)
Write to `results/hw/energy/<host>-<UTCstamp>.csv` with a `#`-comment header carrying: meter model,
calibration offset%, governor, temp min/max, `get_throttled` before/after, PSU, cable note. One row
per (op[, b], rep) with raw `P_idle`, `P_loop`, `t_loop`, `n_ops`, `energy_per_op`; plus a summary
block with median + CI per op and the derived `p_cpu_w`, `p_radio_w`.

## Sanity anchors (Law 6 — state before measuring)
- RPi4 timings ~5–15× the x86 P1 values (Ed25519 sign 15–60 µs x86 → ~0.1–0.9 ms Pi; BLS verify
  1–3 ms x86 → ~5–45 ms Pi). Far outside ⇒ investigate governor/throttling before recording.
- `verify ≥ sign` within each scheme; **BLS-verify ≫ Ed25519-verify** still holds on ARM.
- `energy_per_op > 0` and ordered sensibly (BLS most expensive; delta encode cheapest).
- `p_cpu_w` in the low-single-digit W range for a 4-core RPi4 under one busy core; if it lands near
  the nominal 3.0 W that is a consistency check, not a target to hit.
