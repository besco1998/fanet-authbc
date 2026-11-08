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

---

## Outcome — added 2026-11-08, 11:05, after the series ended; nothing above this line was changed

**Correction to the header above.** It says "Registered 2026-11-08 at 09:05". That time was my
estimate, not a reading. The registration commit (`402864a1`) and the tag `prereg-W1n` are at
**09:00:36**. The series started at 09:00:50, and the first preflight's windows at 09:05:14. The
order, registration before any preflight, holds.

**Three sessions were started: one VALID, one VOID, one ended in tuning.** The series then ended
as registered, on a NO-GO other than balance.

| | windows | powers pi-A / pi-B / Pi 3 (mBm) | what happened |
|---|---|---|---|
| s1 preflight | 09:05–09:08 | 600 / auto / 1100 | **GO**, 1.410× |
| **s1 long run** | 09:13–09:39 | 600 / auto / 1100 | gate GO (1.478×); **VOID: V5 1.643×** |
| s2 preflight | 09:45–09:48 | 600 / auto / 1100 | NO-GO on balance alone, 1.558× → tuning step 1: pi-A down |
| s2 tuning step 2 | 09:53–09:56 | 500 / auto / 1100 | **TUNED**, 1.218× |
| **s2 long run** | 10:01–10:27 | 500 / auto / 1100 | gate GO (1.410×); **VALID** (V5 1.495×) |
| s3 preflight | 10:33–10:36 | 500 / auto / 1100 | NO-GO on balance alone, 1.619× → step 1: pi-A and the Pi 3 down |
| s3 tuning step 2 | 10:41–10:44 | 400 / auto / 1000 | **NO-GO on check 7**: links into node 4 at 95.2 % and 76.7 % → **the series ends** |

The window times are from each run's own log. Every Pi's rate was in band in every run, node 4
joined at `FIXED CCK_1M` every time, and every held power read back, then auto.

### Session 1 — VOID on V5 alone

* **V5:** the A31 spread was **1.643×** against 1.5×. pi-A 3.84 %, pi-B 6.24 %, the Pi 3 5.40 %,
  TP-Link 6.31 %.
* **Everything else held:**
  * V1: rates 1 938–2 226 µs;
  * V2: b = 0.39 %;
  * V3, V4;
  * V6: pi-A 6.00 dBm, the Pi 3 11.00 dBm.
* **Reported, not scored** (as W1h's were): crossings 30.88 / 9.40, ratio 3.286. ⚠️ Never quote
  this as measured.
* pi-A strengthened through the session: its loss was 4.56 % at the preflight, 4.26 % at the gate
  and 3.84 % over A31.

### Session 2 — VALID; every scored claim held

Tuned in two steps, at 500 / auto / 1100. Scored by `dsss_w1i.py --score … --powers
1:500,2:auto,3:1100`; the registered code is unchanged since `prereg-W1n`.

**Validity:**
* V1: all eight rate checks in band (1 938–2 218 µs);
* V2: b = 0.44 %;
* V3, V4: node 4 in the cell at `FIXED CCK_1M`;
* **V5: 1.495× — inside 1.5× by 0.005×**;
* V6: pi-A at 5.00 dBm and the Pi 3 at 11.00 dBm read back, then auto.

| | measured | registered model | band | held |
|---|---|---|---|---|
| W1n-1 the bracket | 8/8 in band | | 1.9–2.6 ms | **yes** |
| W1n-2 the background | 0.44 % | | ≤ 1 % | **yes** |
| W1n-3 AUTHBC crossing | **31.11** (95 % CI 30.93–31.19) | 29.50 | 26.55–32.45 | **yes** (+5.4 %) |
| W1n-4 per-record crossing | **9.43** (95 % CI 9.37–9.51) | 8.93 | 8.04–9.82 | **yes** (+5.7 %) |
| **W1n-5 the ratio** | **3.297** | **3.304** | 2.974–3.635, > 2.5 | **yes** (−0.2 %) |
| **W1n-6 repeat**, ±5 % of W1j's 3.280 | **+0.53 %** | | 3.116–3.444 | **yes** |

**The points** (V/(1 − b), four windows each):
* AUTHBC A29–A32: 0.9649 / 0.9608 / 0.9516 / 0.9369;
* per-record P9–P9.75: 0.9640 / 0.9566 / 0.9477 / 0.9358.

Outputs: `results/raw/w1i_w1n_2026-11-08_s2_run.csv`,
`results/hw/channel24/w1n_2026-11-08_s2_run_windows.csv`.

**An independent script** (`crosscheck_w1g.py`, plain Python on the raw JSON) agrees exactly on
b, all eight points, both crossings, the ratio and the A31 spread, for sessions 1 and 2.

### Session 3 — ended in tuning, on check 7

* The preflight at 500 / auto / 1100 read 1.619× (pi-A 4.16, pi-B 5.93, the Pi 3 5.09, TP-Link
  6.74 %). The setting that tuned at 1.218× at 09:56 had drifted out by 10:36.
* Step 1 moved pi-A and the Pi 3 down 1 dB, to 400 / auto / 1000.
* **Step 2's balance was close, 1.299×. Check 7 failed:** two of the twelve alone-links fell
  below 97 %, both into node 4 (the TP-Link on Blue 2):
  * pi-A at 4 dBm → node 4: **95.18 %**;
  * the Pi 3 at 10 dBm → node 4: **76.72 %**.
* The other ten links were at 98.75–99.90 %.
* In every earlier W1n run (pi-A at 5–6 dBm, the Pi 3 at 11 dBm), node 4 received 98.46–100 % from
  both.
* By the registered rule, a NO-GO on any check but balance ends the series.

### Across the series (as registered)

* **Sessions run: two.** One valid (s2) and one void (s1, V5). A third (s3) ended in tuning,
  before its long run.
* **The valid ratios with W1j's and W1k's** (full precision, from the raw files):
  * W1j 3.2799, W1k 3.2716, W1n-s2 3.2973;
  * **mean 3.283, standard deviation 0.013, range 3.272–3.297** (0.026 wide);
  * the mean is 0.64 % below the model's 3.304.
* **Inside W1n-6:** 3 of 3.

### Against the expectations

* "The first preflight GO, or a balance NO-GO that tunes in one or two steps": **held** (s1 GO;
  s2 tuned in two). Session 3 did not tune; it ended on check 7.
* "V5 holds": **missed once** (s1, 1.643×). It held in s2, by 0.005×.
* "The ratio within 3.15–3.40": **held** (3.297).

### What it means

* **The hardware ratio repeats a third time, on a re-set layout and at a re-tuned power: 3.297,
  within 0.2 % of the model's 3.304.** The three valid sessions agree to within 0.026.
* **The balance does not hold still.** The same setting read 1.22× and then 1.62×, 40 minutes
  apart. A session can pass its gate and fail V5 (s1), or pass V5 by 0.005× (s2).
* **The ratio moved much less than the balance.** The void s1's reported ratio (3.286) and the
  valid ones (3.272–3.297) lie within 0.026 of each other, while V5 ran from 1.15× to 1.64×. That
  is an observation from four sessions, not a scored claim.
* **Lowering power has a floor set by the weakest link, not only by the grid.** In one reading,
  the TP-Link's corner lost 23 % of the Pi 3's frames at 10 dBm, against at most 1.54 % at 11 dBm.
