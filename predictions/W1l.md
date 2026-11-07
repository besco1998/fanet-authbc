# W1l — repeated sessions of W1j, unchanged, until Mohamed says stop

*Registered 2026-11-08, before any session. Main open item W1. It repeats W1j (F132: valid, ratio
3.280) and W1k (F133: valid, ratio 3.272).
* **Mohamed (2026-11-08):** "i turned on the setup in the 1 m square with pi3 toward the middle for
  some distance as before. i want you to take as measurments as you can till i say stop".
* W1j and W1k gave two sessions. This series asks how the hardware ratio spreads over more of them.

Code, plan and kit at this commit, unchanged since `prereg-W1k` but for one addition. Since W3a
(`43a2f1a4`), `hw/channel/bcast_rx.py` also writes every received sequence number. Its counts, the
only thing scored, are unchanged. The rest:
* the plan `plan_w1h.txt`;
* the gate `dsss_w1h.py`;
* the score `dsss_w1i.py --score … --powers 1:600,2:auto,3:1100`;
* the preflight `hw_preflight.py`;
* the kit `hw/channel/`.

The predictions are W1f's, unchanged.*

## Setup

**W1j's layout, reassembled by Mohamed on 2026-11-08:**
* the 1 m square;
* the Pi 3 moved toward the centre, "for some distance as before" (W1j: 35 cm inward);
* pi-A held at 600 mBm, the Pi 3 at 1100 mBm, pi-B at default;
* channel 11, 802.11b at 1 Mb/s;
* Blue 2 rebooted by the launcher for each session; the Pis are never rebooted between a GO and its
  long run.

**Disclosed:**
* Unlike W1k, the setup was taken down and put up again. The distances are Mohamed's by eye, not
  measured.
* The boards were booted at about 01:05 today (uptimes 237–281 s at the check). The Pis' first
  ad-hoc session after a boot runs at 6 Mb/s (F129), so **the first preflight is expected to say
  RETRY.**

## The series

Each session k = 1, 2, … runs as W1k did:
1. **A preflight at these powers** (`hw_preflight.py --check --held 1:600,3:1100`, its default limit
   1.5×).
   * GO starts the long run.
   * RETRY runs one more preflight.
   * NO-GO ends the series with no session k, and the failing check is reported to Mohamed. **No
     re-tuning:** this is a repeat.
2. **One long run,** `plan_w1h.txt`, read by W1h's gate after it.
   * GO: the session, scored once.
   * ABORT: reported as void.

Sessions follow one another until Mohamed says stop. A session running when he says stop is let
finish (about 26 minutes), since stopping it mid-run leaves the boards to their deadmen.
**Every session is reported, valid or void, in the order it ran. None is dropped and none is
repeated in place.**

## Scored per session (W1j's, unchanged)

A session is void unless V1–V6 hold:
* V1: the eight rate checks in 1.9–2.6 ms;
* V2: b ≤ 1 %;
* V3, V4: node 4 joined at `FIXED CCK_1M`;
* V5: the session's A31 within 1.5×;
* V6: pi-A at 6 dBm and the Pi 3 at 11 dBm, read back.

Each valid session is scored against W1f's bands:
* **W1l-1:** the bracket.
* **W1l-2:** the background.
* **W1l-3:** AUTHBC's crossing within 26.55–32.45.
* **W1l-4:** per-record's crossing within 8.04–9.82.
* **W1l-5:** the ratio within 2.974–3.635, and above 2.5.
* **W1l-6, repeatability:** the ratio within ±5 % of W1j's 3.280, that is 3.116–3.444.

**Across the series (reported when it ends):**
* the number of sessions run, valid and void;
* the ratios of the valid ones, with W1j and W1k, their mean, spread and range;
* how many fall inside W1l-6.

## My expectations `[agent]`

* **The first preflight RETRY, the second GO.**
* **V5 the least sure.** The layout was rebuilt, so the balance may differ from W1j's. A NO-GO on
  balance is possible, and if it comes, the series stops.
* **Each valid ratio within 3.15–3.40,** inside W1l-6's band.

## Disclosure

* Known: W1j (3.280) and W1k (3.272), with everything before them (F124–F133).
* **No window of W1l has been run.**
