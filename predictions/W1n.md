# W1n — W1m's rules, unchanged, on W1j's layout re-measured with a tape

*Registered 2026-11-08 at 09:05, before any W1n preflight. Main open item W1. It follows W1m: no session.
Power alone did not balance the square rebuilt by eye: not TUNED in six steps, 1.52–2.22×. pi-A was
the strongest sender at every power down to the 4 dBm floor.
* **Mohamed (2026-11-08):** chose "Re-measure W1j's layout": the square re-set with a tape to
  W1j's recorded geometry, then W1m's rules again, unchanged.

Code, plan and kit at this commit, all unchanged since `prereg-W1m`:
* the plan `plan_w1h.txt`;
* the gate `dsss_w1h.py`;
* the tuning `dsss_w1m.py --step`;
* the score `dsss_w1i.py --score`;
* the preflight `hw_preflight.py`;
* the kit `hw/channel/`.

The predictions are W1f's, unchanged.*

## Setup (re-measured by Mohamed)

W1j's recorded geometry:
* the four boards on the corners of a 1 m square, each on its W1j corner, at the same height,
  antennas toward the centre;
* the Pi 3 35 cm along its diagonal toward the centre;
* channel 11, 802.11b at 1 Mb/s;
* Blue 2 rebooted by the launcher for each run;
* the Pis never rebooted between a GO and its long run.

**As measured:** Mohamed re-set the square with a tape to the geometry above. He reported it as
"done" at about 09:00. **No measured distances were reported**, so none are stated here.

**Disclosed:**
* **No board rebooted in the move** (read at 09:00):
  * the Pis up 7.9 h (booted about 01:07), so past their first ad-hoc session (F129);
  * Blue 2 up 6.0 h, since the launcher's last reboot of it for W1m.
* **No RETRY is expected.**
* W1j's record names neither which board stood on which corner nor the antenna angles. Those
  follow Mohamed's memory of that night.

## The series — W1m's, word for word

**Powers P.** They start at W1j's: `1:600,2:auto,3:1100`.

Each session k = 1, 2, … runs as follows:
1. **W1k's preflight at P** (`hw_preflight.py --check --held P`, its limit 1.5×).
   * **GO:** the long run at P.
   * **RETRY:** one more preflight at P.
   * **NO-GO on check 6 alone** (balance): a tuning, below.
   * **NO-GO on any other check:** the series ends, and the failing check is reported.
2. **The tuning, only after a balance NO-GO.**
   * `dsss_w1m.py --step` (W1i's rule on the 1 dB grid, target 1.25×).
   * The NO-GO preflight is step 1; then tuning preflights.
   * **TUNED:** the long run starts at once, and the tuned powers become P.
   * **RETRY:** the same powers once more.
   * **STOP, NO-GO, or no TUNED within six steps:** the series ends.
3. **One long run** (`plan_w1h.txt`, about 26 minutes) at P, then W1h's gate.
   * **GO:** the session, scored once by `dsss_w1i.py --score … --powers P`.
   * **ABORT:** void, and the series continues at P.

Sessions follow one another until Mohamed says stop. A session running when he says stop is let
finish. **Every session and every tuning preflight is reported, in the order it ran.**

## Scored per session (W1j's, unchanged)

A session is void unless V1–V6 hold:
* V1: the eight rate checks in 1.9–2.6 ms;
* V2: b ≤ 1 %;
* V3, V4: node 4 joined at `FIXED CCK_1M`;
* V5: the session's A31 within **1.5×**;
* V6: every held Pi read back at its setting in P, then auto.

Each valid session is scored against W1f's bands:
* **W1n-1:** the bracket.
* **W1n-2:** the background.
* **W1n-3:** AUTHBC's crossing within 26.55–32.45.
* **W1n-4:** per-record's crossing within 8.04–9.82.
* **W1n-5:** the ratio within 2.974–3.635, and above 2.5.
* **W1n-6, repeatability:** the ratio within ±5 % of W1j's 3.280, that is 3.116–3.444.

**Across the series:** the sessions run, valid and void, with their powers; the valid ratios with
W1j's and W1k's, their mean, spread and range; how many fall inside W1n-6.

## My expectations `[agent]`

* **If the geometry is W1j's, the first preflight GO, or a balance NO-GO that tunes in one or two
  steps.** W1j read 1.249× at these powers; W1k's preflight 1.136×.
* **Less sure than that:** W1j's corners were set by eye too, and its record has no antenna angles.
  A tape fixes the distances, not everything.
* **If a session runs: V5 holds, and the ratio is within 3.15–3.40**, inside W1n-6.

## Disclosure

* Known: W1j (3.280), W1k (3.272), W1l and W1m (no session, above), and everything before them
  (F124–F134).
* **The launch and tuning tools hold credentials** and are not in the repo. They do only what this
  file states.
* **No preflight or window of W1n has been run.**
