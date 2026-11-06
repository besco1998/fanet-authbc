# W1k — a second session of W1j, unchanged: does the hardware ratio repeat?

*Registered 2026-11-06, before the run. Main open item W1. It repeats W1j (F132: valid, the ratio
3.280).
* **Mohamed:** "Start a second run".
* W1j had one session; this asks whether its result repeats on the same setup, untouched.

Code, plan and kit at this commit, all unchanged since `prereg-W1j`:
* the plan `plan_w1h.txt`;
* the gate `dsss_w1h.py`;
* the score `dsss_w1i.py --score … --powers 1:600,2:auto,3:1100`;
* the preflight `hw_preflight.py`;
* the kit `hw/channel/`.

The predictions are W1f's, unchanged.*

## Setup

**W1j's, untouched since its run** (checked at 20:34: no Pi rebooted, nothing moved):
* the 1 m square;
* the Pi 3 35 cm inward;
* antennas to the centre;
* pi-A at 600 mBm, the Pi 3 at 1100 mBm, pi-B at default;
* Blue 2 rebooted for each session;
* channel 11, 802.11b at 1 Mb/s.

## The run

1. **One preflight at these powers** (`hw_preflight.py --check --held 1:600,3:1100`, its default
   limit 1.5×).
   * GO starts the long run.
   * RETRY runs one more preflight.
   * NO-GO stops W1k with no session. **No re-tuning:** this is a repeat.
2. **One long run,** `plan_w1h.txt`, read by W1h's gate after it.
   * GO: the session, scored once.
   * ABORT: discarded, and W1k ends.

## Scored as (W1j's, unchanged)

The session is void unless V1–V6 hold:
* V1: the eight rate checks in 1.9–2.6 ms;
* V2: b ≤ 1 %;
* V3, V4: node 4 joined at `FIXED CCK_1M`;
* V5: the session's A31 within 1.5×;
* V6: pi-A at 6 dBm and the Pi 3 at 11 dBm, read back.

Scored against W1f's bands:
* **W1k-1:** the bracket.
* **W1k-2:** the background.
* **W1k-3:** AUTHBC's crossing within 26.55–32.45.
* **W1k-4:** per-record's crossing within 8.04–9.82.
* **W1k-5:** the ratio within 2.974–3.635, and above 2.5.

**W1k-6, repeatability (fixed now):** the ratio within ±5 % of W1j's 3.280, that is 3.116–3.444.
The threshold is my choice, set before the run, at half the model band's width.

## My expectations `[agent]`

* **The preflight GO.** W1j's gate read 1.09× and its A31 1.21×. The balance has wandered about
  ±0.1× within an evening.
* **V1–V6 hold**, though V5 is less sure: an untouched setup can still drift.
* **The ratio within 3.15–3.40,** inside W1k-6's band.

## Disclosure

* Known: W1j's result (3.280; crossings 30.48 / 9.29) and everything before it (F124–F132).
* The same setup and powers as W1j, untouched; no tuning since.
* **No window of W1k has been run.**

---

## Outcome — added 2026-11-06, 21:25, after the run; nothing above this line was changed

**How it ran.**
* The preflight (20:38–20:42) said GO, spread 1.136×.
* **The long run lasted 20:46:53–21:12:53**, on Blue 2's boot `360209bd`.
  * All four boards ran all 52 windows and reverted.
  * Node 4 was in the Pis' cell (`f6:2e:4e:89:8b:b7`) at `FIXED CCK_1M`, with every Pi reached.
  * pi-A was held at 6.00 dBm and the Pi 3 at 11.00 dBm (20:46:03), both returned to auto
    (21:12:58).
* **The gate said GO** (1.169×), so it is the session.
* Scored by `dsss_w1i.py`, unchanged since `prereg-W1k` (an empty diff). Outputs:
  * `results/raw/w1i_w1k_2026-11-06_run.csv`;
  * `results/hw/channel24/w1k_2026-11-06_run_windows.csv`;
  * the files in `results/hw/channel24/w1k_2026-11-06/w1k_2026-11-06_run/`.
* An independent script agrees exactly.

**The session is VALID. Every condition held:**
* V1: the Pi 3 at 2 343.5 / 2 463.0 µs;
* V2: b = 0.52 %;
* V3, V4;
* **V5: 1.149×**;
* V6.

| | W1k | W1j | model | band | held |
|---|---|---|---|---|---|
| W1k-3 AUTHBC crossing | **30.67** (95 % CI 30.58–30.76) | 30.48 | 29.50 | 26.55–32.45 | **yes** |
| W1k-4 per-record crossing | **9.37** (95 % CI 9.34–9.43) | 9.29 | 8.93 | 8.04–9.82 | **yes** |
| **W1k-5 the ratio** | **3.272** | 3.280 | 3.304 | 2.974–3.635 | **yes** |
| **W1k-6 repeat**, within ±5 % of 3.280 | **−0.26 %** | | | 3.116–3.444 | **yes** |

**Reported, not scored: one control window.** b came from eight control windows reading
0.06–0.36 %, and one reading 2.58 %: the last, the TP-Link's frames lost 65 times at pi-B. Without
it, b would be 0.22 %. The crossings would then be 30.45 / 9.30 and the ratio 3.273. **The ratio
moves by 0.04 %.**

**My expectations.** Each held:
* the preflight GO;
* V1–V6;
* the ratio within 3.15–3.40.

**What it means.** **The hardware ratio repeats: 3.272 against W1j's 3.280, both within 1 % of
the model's 3.304.** F133.
