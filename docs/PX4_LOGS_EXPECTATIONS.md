# Record sizes on real flight telemetry — prediction, written before any log was opened

*2026-10-06. Committed **data-free**, with the script and the selection rule, before a single log
was parsed — the discipline of `docs/M4_EXPECTATIONS.md` and `docs/NMAX_DIRECT_EXPECTATIONS.md`.*

## Why this exists

Every record size in this project comes from one seeded generator (`bench/telemgen.py`): a random
walk with ±2-unit position jitter and velocity steps of at most 10 cm/s. Its delta record is
**exactly 9 B at 50 ms spacing, in all 29 970 samples** — nine fields, one byte each, the smallest
the format allows. An external review called that out as looking synthetic, and it is: no real
sensor is that quiet. The byte result (−70 % for the lean design) rests on it.

`analysis/px4_log_sizes.py` runs real flight logs through the **same encoders** and reports the
same sizes.

## What is measured, and from what

Public logs of the PX4 Flight Review service (index: `https://review.px4.io/dbinfo`, 473 088 logs
on 2026-10-06). Twelve are taken by a rule fixed here, before any was opened:

* duration 300–900 s; zero logged errors; PX4 release v1.14–v1.17; not a simulator build
  (`SITL` not in the hardware name); a vehicle UUID present;
* at most 45 MB (a practical limit, set after seeing that candidates run from 11 to 175 MB —
  their sizes, not their contents; it leans toward the default logging profile);
* **one log per vehicle**;
* strata: 4 quadrotors, 2 hexa/octorotors, 3 fixed wings, 3 VTOLs;
* within a stratum, **the first by `log_id`** — a UUID, so the order is arbitrary and fixed.
  A log that lacks a needed topic or has under 60 s of flight is skipped for the next one, and
  every skip is recorded with its reason.

The chosen ids and the SHA-256 of each file go into `experiments/px4-logs/manifest.yaml`, so a
re-run uses the same logs whatever is uploaded later. The logs themselves are not redistributed.

Records are built on a fixed time grid by sample-and-hold from `vehicle_global_position`
(lat, lon, alt), `vehicle_local_position` (vx, vy, vz), `battery_status` and `vehicle_status`,
in the generator's units (1e-7 deg, cm, cm/s, percent), **in flight only**
(`vehicle_land_detected`). A grid is used only if it is no finer than the rate at which the log
itself carries position: sampling faster than the source would manufacture zero differences.
⚠️ Public logs carry position at 5–10 Hz, so **the 50 Hz spacing of the adopted operating point
cannot be measured from them**; the comparison is made at matched spacing, 0.1 s and above.

## The prediction

Worked from the encoding rules, not from any log. A varint holds |Δ| < 64 in one byte and
|Δ| < 8192 in two.

| quantity | generator | real logs — predicted | reasoning |
|---|---|---|---|
| lean keyframe | 24.0 B (21–25) | **22–25 B** | 5 B each for lat and lon at 1e-7 deg, 3 B altitude in cm, 3 B timestamp minutes into a flight, 1–2 B per velocity |
| lean delta, 0.1 s apart | 10.06 B | **10–12 B** | timestamp 2 B; lat/lon take a second byte above ≈ 7 m/s per axis; the rest 1 B |
| lean delta, 1 s apart | 12.52 B | **12–15 B** | position and velocity differences reach two bytes |
| lean delta, 5.5 s apart | 13.60 B | **13–17 B** | every moving field at two bytes, some at three |

**Load-bearing: at 0.1 s spacing the mean delta over the twelve logs is at most 13 B, and the lean
design's saving against the one-record frame, recomputed with real sizes at that spacing, is at
least 68 %** (generator: 70.3 % at 50 ms).

## What each outcome means

* **Holds.** The generator understates a real delta by a byte or two and the headline moves by
  under three points. The paper states the real-log sizes beside the generator's and says which
  the tables use.
* **Fails** (mean delta above 13 B, or saving below 68 %). The generator is not representative.
  Every byte figure that depends on a delta record is re-stated from the real-log sizes, and the
  generator's are relabelled a lower bound. ⚠️ Not averaged away, and not rescued by choosing a
  spacing or a subset of logs after the fact.

## What this cannot show

Sizes only: no loss, capacity or energy result uses the logs. Twelve logs are a check on a
generator, not a census of UAV telemetry. Nothing is measured at 50 Hz.

---

# Amendment — after the logs were selected, before any size was computed (2026-10-06)

Selecting the logs meant opening them far enough to see which topics they carry, at what rate,
and whether the values are valid. No record was encoded and no size was computed. Two things
that the rule above did not foresee, and what is done about each:

**1. The logs carry global position at 5 Hz, not 10.** In all twelve,
`vehicle_global_position` arrives every 200 ms and `vehicle_local_position` every 100 ms. By the
rule above — no grid finer than the log's own position rate — **the 0.1 s row cannot be
measured, and the load-bearing prediction was written at 0.1 s.** It is not re-pointed at
whatever spacing looks best afterwards. It is applied, unchanged in its numbers, at the finest
spacing the logs support:

> **at 0.2 s spacing the mean delta over the twelve logs is at most 13 B, and the lean design's
> saving against the one-record frame at that spacing is at least 68 %.**

This is the stricter of the two readings: a difference taken over 0.2 s is never smaller than one
taken over 0.1 s, and the thresholds are the ones set for 0.1 s. The 1 s and 5.5 s rows stand as
written. The 0.1 s prediction itself is recorded as **untested**, not as passed.

**2. One selected log has no battery estimate.** `battery_status.remaining` is NaN in every sample
of `0007e5ac…`; cast to an integer that is garbage, and it would have entered the sizes as a
ten-byte field. A field that is never valid is a missing field, so by the rule's own skip clause
the log is replaced by the next in its stratum and the skip is recorded. The script now also ends
a run at any grid point where a field is invalid, exactly as it does at a landing.

---

# Outcome (2026-10-06)

`results/raw/px4_log_sizes.csv`: twelve logs, 29 092 in-flight records at 0.2 s. Each log counts
once. The generator is run through the same sizing code at the same spacing.

| spacing | real: keyframe | real: delta (range of the twelve log means) | generator: delta | real: saving | generator: saving |
|---|---|---|---|---|---|
| 0.05 s | *not measurable — position is logged at 5 Hz* | | 9.00 B | | 70.33 % |
| 0.1 s | *not measurable* | | 10.06 B | | 69.78 % |
| **0.2 s** | 21.98 B (19–24) | **11.06 B** (10.00–13.21) | 10.83 B | **69.08 %** | 69.38 % |
| 1 s | 21.98 B | 12.38 B (10.01–15.23) | 12.52 B | 68.38 % | 68.51 % |
| 5.5 s | 21.98 B | 13.40 B (10.03–16.90) | 13.60 B | 67.85 % | 67.96 % |

**The amended load-bearing prediction holds:** mean delta at 0.2 s is 11.06 B (≤ 13) and the
saving is 69.08 % (≥ 68 %). The 0.1 s prediction is **untested**, as recorded in the amendment.

Against the ranges predicted from the encoding rules: delta at 1 s, 12.38 B (predicted 12–15) ✓;
at 5.5 s, 13.40 B (13–17) ✓; **keyframe 21.98 B (predicted 22–25) ✗ — under by 0.02 B.** The
prediction assumed two-byte velocities; multicopters fly slowly enough for one.

What the data say beyond the prediction:

* **At matched spacing the generator is within 0.25 B of real telemetry** in every row, and errs
  high as often as low. Its keyframe is 2 B *larger* than a real one, mostly because the project's
  convention places it an hour into a flight (a four-byte timestamp) and these logs are minutes
  long.
* **The spread is by speed, as the encoding rules say it should be.** The three fixed wings
  (median ground speed 16, 16 and 31 m/s) need a second byte for position and average
  12.5–13.2 B at 0.2 s; the six multicopters average 10.0–10.5 B. One fixed-wing log (13.21 B)
  is above the 13 B set for the mean.
* ⚠️ **The mean flatters a fast swarm.** Five of the six multicopter logs are mostly hover
  (median ground speed under 1.5 m/s), and one octorotor (`0050ea4f…`) moves 0.3 m in 553 s and
  sits at the 10 B floor. They were selected by the rule and stay, but a neighbourhood of
  vehicles in forward flight is described by the fixed-wing rows, not by the mean: up to 13.2 B
  per delta at 0.2 s (46.3 B per record, a saving of 68.2 %) — about one point under the
  generator.
* **The generator's flat 9 B at 50 ms is not contradicted, and is not confirmed.** Nine bytes is
  the floor of the format (nine fields, one byte each); a real delta at 50 ms lies between that
  floor and its 0.2 s value. So with real telemetry the design is between 43.25 and 44.29 B per
  record, and its saving between 69.1 and 70.3 %.

Cross-check: the mean delta and keyframe of three (log, spacing) cells were re-derived with a
stand-alone varint routine sharing no code with `wire_v2`; all three agree to the third decimal.

**What this does not license.** Twelve logs chosen from the default-logging-profile end of one
autopilot's public archive. No statement about telemetry at 50 Hz, and none about any loss,
capacity or energy result.

---

# Follow-up — records at the operating rate, from PX4 software-in-the-loop. Written before any flight (2026-10-08)

## Why

The twelve public logs carry position at 5 Hz, so the outcome above says nothing at the 50 Hz of
the adopted operating point (`OPEN_ITEMS` G12). And the capacity results assume a send time
redrawn in every period, with strictly periodic senders as the other extreme; how regular a real
autopilot's 50 Hz stream is has not been measured (G7). Mohamed chose (2026-10-08) to close both
with PX4 run in software-in-the-loop on the development machine.

## What is run

PX4 **v1.17.0**, built for `px4_sitl` with its built-in simulator (`sihsim_quadx`: the
autopilot's own estimator, controllers, logger and MAVLink module, flying a simulated
quadrotor). No hardware, no radio, no Gazebo.

* **Records.** The logger is told to write `vehicle_global_position`, `vehicle_local_position`,
  `battery_status` and `vehicle_status` every 20 ms. The resulting log goes through **the same
  code as the public logs** (`analysis/px4_log_sizes.py`: `flight_runs`, `sizes`) on a 20 ms grid
  and, for comparison with the real multicopters, on a 200 ms grid.
* **The flight.** One mission, fixed now: take off to 30 m; four legs of 150 m round a square at
  a commanded 5 m/s; the same square at 12 m/s; 60 s of position hold; land. About six minutes.
* **Stream timing.** The companion-computer MAVLink instance (`-m onboard`, the mode the paper's
  50 Hz comes from) is received on UDP with kernel receive timestamps. The statistic is the
  interval between consecutive `GLOBAL_POSITION_INT` messages.

## The prediction

| quantity | predicted | why |
|---|---|---|
| mean lean delta record, **20 ms** grid, whole flight | **9.0–9.5 B** | every field's change over 20 ms fits one byte at these speeds: 12 m/s is 0.24 m, about 22 units of 10⁻⁷ degree; the generator's floor is 9.0 |
| … on the 12 m/s legs alone | 9.0–10.0 B | the least favourable part |
| mean lean delta record, **200 ms** grid | **10.0–10.6 B** | the six real multicopter logs span 10.00–10.52 B; if the simulated vehicle is representative it lands among them |
| mean lean keyframe | 20–24 B | the real logs give 20.0–23.8; the generator 24.0 |
| bytes per record of the design (b = 4) with these records at 20 ms | **42.3–43.8 B** | 43.25 with the generator's records |
| mean interval between 50 Hz position messages | **20.0 ± 0.2 ms** | the stream is rate-limited to 50 Hz |
| standard deviation of that interval | **0.05–2 ms** | the MAVLink module sends from a loop a few milliseconds long, so intervals are quantised by it |

## What each outcome means

* **Sizes inside the ranges:** the generator's record sizes hold at the operating rate, the
  limitation "nothing was measured at 50 Hz" is replaced by "measured on PX4 in simulation", and
  no reported number moves.
* **Mean delta at 20 ms above 9.5 B:** the generator flatters the design at its own operating
  point. The ladder's bytes are then recomputed with the measured record sizes and reported
  beside the generator's.
* **The 200 ms figure outside 10.0–10.6 B:** the simulated vehicle does not resemble the real
  multicopters on the one axis where they can be compared, and the 20 ms figure is reported with
  that warning attached.
* **Interval spread:** this is a measurement, not a test. Its use is to say which of the two
  simulated traffic sources a PX4 stream is nearer to: a spread well under the frame's airtime
  (0.2–0.9 ms) means nearly frozen phases; a spread of a millisecond or more means the phases of
  neighbours are reshuffled from one period to the next.

## What this cannot show

It is the autopilot's software on a simulated vehicle and a simulated clock. Sensor noise is the
simulator's model of it. There is no wind unless configured, no radio and no serial link, so the
timing figure contains the host's scheduling noise and none of a real telemetry link's. One
airframe type. A fixed-wing or VTOL flight is attempted only if the quadrotor result leaves the
question open.
