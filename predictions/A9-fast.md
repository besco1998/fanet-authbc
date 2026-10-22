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
