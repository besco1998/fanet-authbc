# A9-fast — A9's fixed-wing and VTOL missions at their registered speeds

*Registered 2026-10-22 before any flight of missions 1–10 under the profile below. Mohamed's
instruction (2026-10-22): re-fly the fixed wing for completeness. Plan: approved the same day.
Outcome appended below a line at the end.*

## Why

A9's fixed-wing and VTOL missions were registered at 15–25 m/s (VTOL 15–22), but they flew at
13–14 and 12.8 m/s. The cause is SIH's linear brake `SIH_KDV` (F107). The airplane also flew
part of its first leg at ground level: TECS's reference started at sea level (A9, Addendum 2).
The speed part of the plan's prediction (3) was therefore never tested.

## What is flown

* **Missions 1–10 of the airplane and the VTOL**, the same geometry as A9, each at its
  **drawn** speed: airplane 15.7–24.7 m/s, VTOL 15.2–21.2 m/s. There is no cap.
  `analysis/px4_airframe_flight.py --profile fast`; outputs in `~/.cache/authbc-px4/fast/`.
* **Profile `fast`** (in the script, `PROFILES`, tested):
  * airplane: `SIH_KDV` 0, `SIH_T_MAX` 12 N, and three seconds in manual mode before the
    mission (`reset_tecs`);
  * VTOL: `SIH_KDV` 0.
  * Everything else is as A9: logged topics, `FW_AIRSPD_TRIM` = the cruise,
    `FW_AIRSPD_MAX` = max(20, cruise + 5), no landing pattern, the airspeed check off.
* **The quadrotor is not re-flown.** Its flights were not affected; A9's ten are used for the
  rows over all airframes.
* **Retry rule as A9:** a failed flight is flown once more, and both attempts are reported.
* **Analysis:**
  * registered method: `record_size_sensitivity.py`, sample-and-hold, all in-flight records;
  * sensitivities: `--nearest` (F105) and `--min-alt 20`;
  * flown speeds: `sih_speed_limit.py`, extended to `fast/`.

## How the profile was chosen — development flights, mission 98 only (all kept)

The rule was fixed in the approved plan:

* remove the brake;
* raise thrust only as needed;
* the first rung that completes, holds cruise airspeed within 1 m/s of the command, and has
  median throttle below 0.95 is the profile.

"Cruise" is level flight more than 20 m up. Two additions were made while the ladder ran, and
both are stated here:

* **No touchdown after takeoff.** The first airplane rungs showed the descent of Addendum 2.
* **The VTOL tested at 21.2 m/s,** its fastest drawn speed, instead of 22.

| flight | change | commanded | cruise airspeed | throttle | result |
|---|---|---|---|---|---|
| dev-plane-kdv0-t9 | KDV 0, 9 N | 25 | 25.5 | 0.98 | fails throttle (and touched down) |
| dev-plane-kdv0-t12 | KDV 0, 12 N | 25 | 25.7 | 0.75 | touched down |
| dev-plane-stock-climb | climb-out waypoint (stock) | 15 | 14.0 | 1.00 | touched down: not the cause |
| dev-plane-kdv0-t9-climb | KDV 0, 9 N, climb-out | 25 | — | — | circled the waypoint 15 min |
| dev-plane-stock-setpoints | stock, setpoints logged | 15 | 14.0 | 1.00 | showed TECS's reference from sea level |
| dev-plane-stock-reset | stock, TECS reset | 15 | 14.0 | 1.00 | no touchdown: the fix works |
| **dev-plane-kdv0-t12-reset** | **KDV 0, 12 N, TECS reset** | **25** | **25.3** | **0.73** | **passes** |
| dev-vtol-kdv0 | KDV 0 | 22 | 20.6 | 1.00 | 1.4 m/s short |
| dev-vtol-kdv0-t3 | KDV 0, 3 N | 22 | — | — | takeoff failed: "unable to reach heading" |
| dev-vtol-kdv0-t3-q | KDV 0, 3 N, torque × 1.5 | 22 | — | — | the same |
| **dev-vtol-kdv0-212** | **KDV 0** | **21.2** | **20.4** | **0.97** | within 1 m/s; **misses the throttle margin** |

The 12 N rung with the climb-out waypoint was stopped unflown, because it would have repeated
the 9 N one.

**The VTOL profile meets no rung's rule.** Raising its thrust breaks its takeoff. With the
brake removed, its fastest missions (21.1 and 21.2 m/s) fly up to about 0.8 m/s short, near
full throttle. That is stated, not hidden.

## Predictions

The plan's A9 statements, verbatim, now at the speeds they were written for:

> - At 25 fields (keyframe about 60 B, delta about 25 B), the byte reduction is still about 65%.
> - The capacity ratio stays near 3×, because frame count, not bytes, dominates.
> - Fixed-wing deltas reach 10–13 B at 50 Hz, about 1–2 B more than the quadrotor.

They are scored as in A9, over the 20 fast flights and A9's 10 quadrotor flights:

1. 25 fields: keyframe 50–70 B, delta 20–30 B, saving 60–70 %.
2. Ratio at 25 fields within 2.6–3.4.
3. Fixed-wing 9-field delta mean 10–13 B, and 1–2 B above the quadrotor's (9.000).

**Mine `[agent]`**, from F105, F107 and the encoding bound. One byte per field holds below 63
units per record: 23.7 m/s east–west and 35 m/s north–south at 20 ms, halved under hold, whose
steps alternate 0 and 40 ms.

* **AF-1:** plan (1) keyframe **MISSED** (45–48 B); delta and saving held. Plan (2) held.
  Plan (3) **MISSED**.
* **AF-2:** 9-field delta, hold: airplane 9.1–9.8 B, VTOL 9.05–9.6 B. Nearest sample: both
  9.0–9.25 B.
* **AF-3:**
  * ratio at 9 fields 3.50–3.53 for each airframe;
  * ratio at 25 fields 3.02–3.07;
  * 25-field saving 63.0–63.6 %.
* **AF-4:** against A9's own flights of the same missions (14 / 12.8 m/s):
  * the airplane's 9-field delta grows by 0.0–0.8 B under hold and 0.0–0.25 B with the
    nearest sample;
  * no ratio moves by more than 0.03.
* **AF-5 (flight quality, a check that the procedure did what it should, not a prediction of
  the result):**
  * cruise airspeed within 1 m/s of the drawn speed on all 10 airplane flights and on at
    least 9 of 10 VTOL flights;
  * no touchdown after takeoff in any of the 20.

## Disclosure

* No registered mission (1–10) has been flown under this profile.
* The size code has run on the development flights above, only to read their speeds and
  throttle; it has not run on any registered fast flight.

---

## Outcome (2026-10-22, 23:21; 20 flights, each at the first attempt)

* Sizes: `results/raw/record_size_fast.csv` (registered: hold, all in-flight records),
  `record_size_fast_nearest.csv`, `record_size_fast_airborne.csv` (`--min-alt 20`). The 20 fast
  flights plus A9's 10 quadrotor flights.
* Flown speeds and each log's SHA-256: `results/raw/a9_fast_speeds.csv`. The logs stay in
  `~/.cache/authbc-px4/fast/`.

**Flown.**

* Airplane cruise airspeed was 0.28 below to 0.67 above its drawn speed (16.4–25.1 m/s), at
  30–71 % throttle; mean ground speed 20.1 m/s, against A9's 11.9.
* The VTOL was 0.47 below to 0.56 above its drawn speed (15.8–20.7 m/s), at full throttle on
  its four fastest missions; mean ground speed 16.2 m/s, against A9's 11.2.
* No flight touched down after takeoff.

| fields | airframe | keyframe | delta (hold / nearest) | saving | ratio |
|---|---|---|---|---|---|
| 9 | airplane | 23.06 | **9.215** / 9.061 | 70.05 % | 3.511 |
| 9 | VTOL | 22.76 | **9.205** / 9.029 | 70.03 % | 3.503 |
| 9 | quadrotor (A9's) | 22.69 | 9.000 / 9.000 | 70.13 % | 3.503 |
| 25 | airplane | 46.04 | 26.256 / 26.102 | 63.28 % | 3.039 |
| 25 | VTOL | 45.67 | 26.221 / 26.046 | 63.26 % | 3.036 |
| **25** | **all 30** | **45.49** (44.3–46.6) | **26.15** | **63.29 %** | **3.042** (3.026–3.058) |

### Scoring

* Plan (1), 25 fields:
  * keyframe 50–70 B: **MISSED** (45.5);
  * delta 20–30 B: **HELD** (26.1);
  * saving 60–70 %: **HELD** (63.3 %).
* Plan (2), ratio within 2.6–3.4: **HELD** (3.04).
* Plan (3), fixed-wing delta 10–13 B and 1–2 B above the quadrotor: **MISSED, now at the speeds
  it was written for.** The airplane's delta is 9.22 B, 0.22 above the quadrotor; at 20 ms and
  ≤ 25 m/s almost every field still changes by less than its first byte holds.
* AF-1, the pattern of the plan's three statements: **HELD**.
* AF-2:
  * hold, airplane 9.1–9.8 B: **HELD** (9.215);
  * hold, VTOL 9.05–9.6 B: **HELD** (9.205);
  * nearest sample 9.0–9.25 B: **HELD** (9.061, 9.029).
* AF-3:
  * 9-field ratio 3.50–3.53: **HELD** (3.511, 3.503);
  * 25-field ratio 3.02–3.07: **HELD** (3.039, 3.036, 3.051);
  * saving 63.0–63.6 %: **HELD** (63.29).
* AF-4:
  * the airplane's delta grows by 0.0–0.8 B (hold) and 0.0–0.25 B (nearest) over A9's flights
    of the same missions: **HELD** (+0.16 and +0.06 on average; single flights −0.17 to +0.54
    and +0.01 to +0.18);
  * no ratio moves by more than 0.03: **MISSED narrowly.** The airframe means move by at most
    0.015, but one flight's 9-field ratio moved by 0.041, which is one OFDM symbol of airtime.
* AF-5, cruise within 1 m/s of the drawn speed (all airplane flights, ≥ 9 VTOL) and no
  touchdown: **HELD** (20 of 20, no touchdown).
* The `--min-alt 20` sensitivity changes no delta by more than 0.01 B. These flights had no
  ground segment to remove.

**What it means.** At the speeds the plan registered, fixed-wing and VTOL records cost what
the quadrotor's do, plus about 0.2 B. The 25-field gain stays at 63 % of the bytes and 3.04
times the capacity. Speed, the reason the plan expected fixed wings to differ, does not move
the result. That conclusion now rests on clean registered flights, not on A9's speed-limited
ones or F107's two diagnostic flights.
