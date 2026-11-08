# W1o — W1n's series, with floors on the tuning: pi-A at least 5 dBm, the Pi 3 at least 11 dBm

*Registered 2026-11-08, before any W1o preflight; the time is the commit's. Main open item W1. It
follows W1n:
* session 2 VALID (the ratio 3.297);
* session 1 VOID on V5;
* session 3 ended in tuning on check 7.

In session 3 the tuning lowered pi-A to 4 dBm and the Pi 3 to 10 dBm. Node 4 then received 95.2 %
and 76.7 % of their frames alone. At pi-A 5–6 dBm and the Pi 3 11 dBm, it received 98.46–100 % in
every W1n run.

**Mohamed (2026-11-08):**
* chose "Series with power floors": W1n's rules unchanged, except that the tuning may not lower
  pi-A below 5 dBm or the Pi 3 below 11 dBm; sessions until he says stop;
* then chose that a STOP at the floors ends the series ("End the series (W1n's rule)").

Code, plan and kit at this commit. Unchanged since `prereg-W1n`:
* the plan `plan_w1h.txt`;
* the gate `dsss_w1h.py`;
* the score `dsss_w1i.py --score`;
* the preflight `hw_preflight.py`;
* the kit `hw/channel/`.

**New:** `analysis/dsss_w1o.py --step`. It is `dsss_w1m.next_powers`, word for word but for one
test: a Pi goes down only while above its own floor. `tests/test_dsss_w1o.py` (18 tests) checks
that it makes W1m's moves wherever no floor binds, and STOPs on W1n's session-3 reading.

The predictions are W1f's, unchanged.*

## Setup

W1n's, untouched by hand: W1j's layout, re-measured with a tape by Mohamed this morning.

**Disclosed:**
* **A power cut at about 13:39.** All three Pis rebooted then (uptime 2.96 h at 16:36). Mohamed:
  nothing in the square was moved.
* **Blue 2 did not come back onto the LAN.** It was down at 16:36, and Mohamed is restoring it.
  The launcher reboots it for every run in any case.
* **The Pis have run no ad-hoc session since the reboot,** so their first preflight runs at
  6 Mb/s (F129). **The first preflight is expected to RETRY.**

## The series — W1n's, word for word, but for the floors

**Powers P.** They start at W1j's: `1:600,2:auto,3:1100`.

Each session k = 1, 2, … runs as follows:
1. **W1k's preflight at P** (`hw_preflight.py --check --held P`, its limit 1.5×).
   * **GO:** the long run at P.
   * **RETRY:** one more preflight at P.
   * **NO-GO on check 6 alone** (balance): a tuning, below.
   * **NO-GO on any other check:** the series ends, and the failing check is reported.
2. **The tuning, only after a balance NO-GO.**
   * `dsss_w1o.py --step`: W1m's rule on the 1 dB grid, target 1.25×, **with each Pi's floor**:
     pi-A at least 500 mBm, the Pi 3 at least 1100 mBm, pi-B the grid's 400.
   * The NO-GO preflight is step 1; then tuning preflights.
   * **TUNED:** the long run starts at once, and the tuned powers become P.
   * **RETRY:** the same powers once more.
   * **STOP, NO-GO, or no TUNED within six steps:** the series ends. **The floors make a STOP
     likely:** when the strong senders are pi-A at 500 and the Pi 3 at 1100 (W1n's session 3), no
     knob can move. Mohamed chose that a STOP still ends the series, as in W1n.
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
* **W1o-1:** the bracket.
* **W1o-2:** the background.
* **W1o-3:** AUTHBC's crossing within 26.55–32.45.
* **W1o-4:** per-record's crossing within 8.04–9.82.
* **W1o-5:** the ratio within 2.974–3.635, and above 2.5.
* **W1o-6, repeatability:** the ratio within ±5 % of W1j's 3.280, that is 3.116–3.444.

**Across the series:** the sessions run, valid and void, with their powers; the valid ratios with
W1j's and W1k's, their mean, spread and range; how many fall inside W1o-6.

## My expectations `[agent]`

* **The first preflight RETRY (F129), the second GO or a balance NO-GO.**
* **A STOP is the likeliest end.** In W1n, the setting tuned at 1.22× read 1.62× forty minutes
  later, with pi-A strong at 5 dBm. With the floors, that reading would STOP.
* **I expect one or two sessions before a STOP, with perhaps one valid.**
* **If a session is valid, its ratio within 3.15–3.40**, inside W1o-6.

## Disclosure

* Known: W1j (3.280), W1k (3.272), W1n's sessions (3.297 valid; 3.286 void, reported), W1l and W1m
  (no session), and everything before them (F124–F134).
* The floors were chosen from W1n's alone-link readings (check 7, rate-check windows), never from
  a scored window.
* **The launch and tuning tools hold credentials** and are not in the repo. They do only what this
  file states.
* **No preflight or window of W1o has been run.**
