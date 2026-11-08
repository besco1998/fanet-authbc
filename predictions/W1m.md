# W1m — repeated sessions at W1j's registered powers; re-tuned on W1j's 1 dB grid only after a balance NO-GO

*Registered 2026-11-08, before any W1m preflight. Main open item W1. It follows W1l: no session;
its preflight NO-GO on balance alone, 1.769×, at W1j's powers, after the square was rebuilt.
* **Mohamed (2026-11-08):** asked to auto-tune the powers. Then: "Use the same power rules as
  session 1 and 2 registered". Sessions 1 and 2 are W1j and W1k.
* **What I take that to mean, stated here so it can be corrected:**
  * every session's powers are set, read back and returned to auto as in W1j and W1k;
  * the start is their powers, pi-A 600, pi-B auto, the Pi 3 1100 mBm;
  * the preflight is W1k's (1.5×);
  * the score is W1j's.
* **A re-tune happens only after a preflight fails on balance alone.** It is in 1 dB steps, the
  grid on which W1j chose its powers (the Pi 3 at 10, 11, 12 dBm). W1i's 2 dB ladder has no rung
  at 1100 mBm, so it cannot start from W1j's powers.

Code, plan and kit at this commit. Unchanged since `prereg-W1l`:
* the plan `plan_w1h.txt`;
* the gate `dsss_w1h.py`;
* the score `dsss_w1i.py --score`;
* the preflight `hw_preflight.py`;
* the kit `hw/channel/`.

**New:** `analysis/dsss_w1m.py --step`. It is W1i's tuning rule (`dsss_w1i.next_powers`), word for
word, on the 1 dB grid. `tests/test_dsss_w1m.py` checks:
* that it moves the same Pis the same way as W1i's on W1i's own cases;
* and what it does on W1l's reading.

The predictions are W1f's, unchanged.*

## Setup

W1l's, untouched since its preflights (checked at 02:11: nothing moved, no board rebooted):
* the 1 m square, rebuilt by Mohamed on 2026-11-08;
* the Pi 3 toward the centre, by eye;
* channel 11, 802.11b at 1 Mb/s;
* Blue 2 rebooted by the launcher for each run;
* the Pis never rebooted between a GO and its long run.

The boards were booted at about 01:05 and have run two preflights since. The Pis are past their
first ad-hoc session (F129), so a RETRY is not expected.

## The series

**Powers P.** They start at W1j's: `1:600,2:auto,3:1100`.

Each session k = 1, 2, … runs as follows:
1. **W1k's preflight at P** (`hw_preflight.py --check --held P`, its limit 1.5×).
   * **GO:** the long run at P.
   * **RETRY:** one more preflight at P.
   * **NO-GO on check 6 alone** (balance): a tuning, below.
   * **NO-GO on any other check:** the series ends, and the failing check is reported.
2. **The tuning, only after a balance NO-GO.**
   * The NO-GO preflight is the first tuning step: `dsss_w1m.py --step` on its own files gives the
     next powers.
   * Then tuning preflights at those powers, each read by `dsss_w1m.py --step` at **1.25×** (W1i's
     target, with margin under V5's 1.5×).
   * **TUNED:** the long run starts at once at the tuned powers, which become P for every later
     session.
   * **RETRY:** the same powers once more.
   * **STOP, NO-GO, or no TUNED within six tuning steps** (the NO-GO preflight counts as the
     first): the series ends, reported.
3. **One long run** (`plan_w1h.txt`, about 26 minutes) at P, read by W1h's gate after it.
   * **GO:** the session, scored once by `dsss_w1i.py --score … --powers P`.
   * **ABORT:** reported as void, and the series continues at P.

**The tuning rule** (`dsss_w1i.next_powers`, registered at `prereg-W1i`, on the 1 dB grid):
* every Pi too strong (its loss below L_max / 1.25) goes down 1 dB, if above 4 dBm;
* if the TP-Link is too strong, every held Pi that is not goes up 1 dB;
* the weakest sender, if a held Pi below auto, goes up 1 dB;
* the grid is auto, then 14 → 4 dBm.

**On W1l's reading** (pi-A 3.49, pi-B 6.18, the Pi 3 4.06, TP-Link 5.63 %), the rule gives
`1:500,2:auto,3:1000`. That is the first tuning preflight if the first W1m preflight reads the
same.

Sessions follow one another until Mohamed says stop. A session running when he says stop is let
finish (about 26 minutes): stopping mid-run leaves the boards to their deadmen. **Every session
and every tuning preflight is reported, in the order it ran. None is dropped and none is repeated
in place.**

## Scored per session (W1j's, unchanged)

A session is void unless V1–V6 hold:
* V1: the eight rate checks in 1.9–2.6 ms;
* V2: b ≤ 1 %;
* V3, V4: node 4 joined at `FIXED CCK_1M`;
* V5: the session's A31 within **1.5×**;
* V6: every held Pi read back at its setting in P, then auto.

Each valid session is scored against W1f's bands:
* **W1m-1:** the bracket.
* **W1m-2:** the background.
* **W1m-3:** AUTHBC's crossing within 26.55–32.45.
* **W1m-4:** per-record's crossing within 8.04–9.82.
* **W1m-5:** the ratio within 2.974–3.635, and above 2.5.
* **W1m-6, repeatability:** the ratio within ±5 % of W1j's 3.280, that is 3.116–3.444.

**Across the series** (reported when it ends):
* the sessions run, valid and void, with each one's powers;
* the ratios of the valid ones, with W1j and W1k: their mean, spread and range;
* how many fall inside W1m-6.

## My expectations `[agent]`

* **The first preflight NO-GO on balance again**, near W1l's 1.77×. It is the same setup 45 minutes
  later.
* **The tuning is the least sure part.**
  * W1i (F131) failed to tune in five preflights. Its balance wandered (1.44 → 1.32 at one
    setting, 16 minutes apart) by more than a 2 dB step moved it.
  * W1j, on the other hand, found its setting in 1 dB steps of the Pi 3.
  * I expect TUNED within the six steps, but not with confidence: perhaps two chances in three.
* **If a session runs: V5 holds and the ratio is within 3.15–3.40,** inside W1m-6. Re-tuned powers
  change the capture between senders. Per W1j, capture shifts both crossings up by similar
  fractions, so the ratio should move less than either crossing.

## Disclosure

* Known: W1j (3.280), W1k (3.272), W1l's two preflights (above), and everything before them
  (F124–F134).
* The powers W1j registered were themselves chosen by preflights on G31 windows only. W1m's
  tuning does the same by a fixed rule, never on scored windows.
* **The launch and tuning tools hold credentials** and are not in the repo. They do only what this
  file states.
* **No preflight or window of W1m has been run.**
