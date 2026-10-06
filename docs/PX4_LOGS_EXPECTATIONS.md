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
