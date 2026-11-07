# W1i — an adaptive preflight tunes the Pis' powers to within 1.25×, then one long run at those powers, fixed

*Registered 2026-11-06, before any tuning run. Main open item W1 (`docs/OPEN_ITEMS.md` §2a). It
follows W1h (F130: void by a hair).
* **Mohamed:** "i go 1 but can we make this adaptive in the preflight and the long run ?!"
* **Then:** "make what is more scientifically right and honest and achieve the fastest development
  and result … without too much loading to the current machine make tests to the setup". He
  approved the plan.

Code, plan and kit at this commit:
* `analysis/dsss_w1i.py`, which imports these unchanged:
  * `dsss_w1h.py` (`prereg-W1h`), and through it `dsss_w1g.py` and `dsss_w1f.py`;
  * `analysis/hw_preflight.py` as at this commit;
* the plan: **`experiments/channel24/plan_w1h.txt`, unchanged** (52 windows);
* the kit, all unchanged since W1g:
  * `run_window_plan.sh`, `run_window_plan_tplink.sh`;
  * `set_txpower_window.sh`, now run on every Pi whose power is held.

No new predictions: the score reads W1g's file, whose scored rows are W1f's, unchanged.*

## Why

* **W1h was void by a hair (F130).** Its gate read 1.433× and the session's own A31 1.549×,
  against a rule of ≤ 1.5×. The balance drifted about 0.12× in 12 minutes, with no margin left.
* **W1i adds margin, and keeps the rule.** The Pis' powers are tuned until a preflight reads
  ≤ 1.25×, by a rule fixed here.
* **The long run holds those powers, fixed**, for all eight capacity points. It does not adapt
  during the run, for three reasons:
  * no board can be reached mid-session (F129);
  * a Pi cannot see its own frames' loss;
  * re-tuning between blocks would measure points at different powers, so the crossings would
    interpolate across configurations.

## Setup

* **W1h's, as it ended:**
  * the Pis side by side, 10–15 cm apart;
  * **Blue 2 with its TP-Link at about 120 cm** (W1h deviation 1), on its 5 V adapter, rebooted
    for every session;
  * channel 11, 802.11b at 1 Mb/s; node 4 at `FIXED CCK_1M`.
* **The Pis are not rebooted** (F129: a cell created by a freshly booted Pi runs at 6 Mb/s). If a
  Pi boots, the preflight's RETRY covers it.
* **The knobs:** each Pi's power on the ladder `auto` → 1000 → 800 → 600 → 400 mBm (the floor,
  4 dBm). The TP-Link has no knob.
  * **Start:** pi-A 800, pi-B 800, Pi 3 `auto`, where W1h ended.
  * A Pi below `auto` is held through its windows by `set_txpower_window.sh`, read back, and
    returned to `auto` after.

## The adaptive preflight (`dsss_w1i.py --step`; the checks in `hw_preflight.py`)

**One tuning preflight** is the 6-window preflight (R1–R4, G31 ×2, about 8 minutes with the
launch), at the current powers, checked with:
* checks 1–5 as `hw/channel/README.md`:
  * the Pis at 1 Mb/s;
  * the TP-Link's rate;
  * **every held Pi's power read back, then auto**;
  * node 4 joined, one boot, every window complete;
  * no under-voltage;
* **check 6 at the tuning target: the G31 senders within 1.25×**;
* **check 7 (new):** alone in its rate check, each sender reaches every receiver with ≥ 97 % of its
  frames. This guards against a power tuned too low.

**Verdicts:**
* **TUNED:** every check holds. The long run starts at once, at these powers.
* **RETRY:** only Pis too fast after a boot. Same powers again.
* **NO-GO:** any check other than 6 failed. Stop.
* **ADJUST:** only check 6 failed. The rule (`next_powers`) gives the next powers:
  1. every Pi too strong (loss below L_max / 1.25) goes down one rung, if above the floor;
  2. if the TP-Link is too strong, every held Pi that is not goes up one rung;
  3. the weakest sender, if a held Pi below `auto`, goes up one rung.
* **STOP:** the rule can move no knob.

**At most five tuning preflights.**

## The long run

`plan_w1h.txt` (R1–R4, G31 ×4, W1g's capacity block, R1–R4; about 26 minutes) at the tuned powers,
on a fresh Blue 2 boot.
* **The gate is W1h's, unchanged** (`dsss_w1h.gate`, read after the run): the G31 senders within
  1.5×, the rate checks before in band, node 4 joined.
  * GO makes the run the session, scored once, whatever its outcome.
  * ABORT discards it unscored (its capacity windows are not analysed). Then up to three more
    tuning preflights, and **one more long run at most**.

## Predictions

**Scored: W1f's registered values, unchanged:**

| | model, four boards | band |
|---|---|---|
| AUTHBC crossing | 29.50 | 26.55–32.45 |
| per-record crossing | 8.93 | 8.04–9.82 |
| **ratio** | **3.304** | **2.974–3.635, and above 2.5** |

Reported, not scored: the model at the grid, as W1g registered it (A29–A32: 0.9569 / 0.9431 /
0.9230 / 0.8964; P9–P9.75: 0.9474 / 0.9331 / 0.9126 / 0.8877).

## Validity: the session is void if any of these fails

Computed by `dsss_w1i.score` on the session's own windows. It is W1g's score with V6 generalised:
* V1: all eight rate checks in 1.9–2.6 ms, with no Pi under-voltage;
* V2: b ≤ 1 % (control windows B only);
* V3: node 4 in the Pis' cell, all Pis reached;
* V4: `rate_ctl` fixed;
* **V5: the session's own A31 windows within 1.5×**, unchanged and **not widened**;
* **V6: every held Pi's log shows its tuned setting read back** (`set <mBm>: txpower <dBm>`), then
  `auto`.

## Scored as

* **W1i-1:** the bracket (V1).
* **W1i-2:** the background (V2).
* **W1i-3:** AUTHBC's crossing within 26.55–32.45.
* **W1i-4:** per-record's crossing within 8.04–9.82.
* **W1i-5 — the claim:** the ratio within 2.974–3.635, and above 2.5.

## My expectations `[agent]`

* **Tuning in one or two preflights.** On the real 120 cm preflight at (800, 800, auto), the rule
  says: pi-A down to 600. pi-B (5.06 %) sits just above the boundary L_max / 1.25. A toy plant
  fitted to W1h's two 120 cm preflights balances in one step. That is a sanity check, not a
  prediction.
* **V1–V4 and V6 hold.** The Pi 3 has been up since 14:07; its rate check read 2 190–2 592 µs
  today, near the band's top at times, which is stated now.
* **V5 holds with the margin.** Tuned to ≤ 1.25× at the preflight, with drift of about 0.12× seen
  in W1h. It is not certain.
* **AUTHBC's crossing near 31, per-record's near 9.3, the ratio near 3.3, inside its band.**

## What each outcome means

| outcome | meaning |
|---|---|
| valid, W1i-5 holds | **the AUTHBC / per-record ratio measured on four real radios**, balanced and with capture present, within ±10 % of the model's |
| valid, W1i-5 fails | the ratio on real radios differs from the model's: reported plainly |
| a crossing not determined | the ratio stays unmeasured |
| void | a validity condition failed; nothing scored |
| STOP, NO-GO, or not tuned in five | no session; the tuning readings are reported |

## What it cannot show

* **The model's own conditions.** Capture is present (F127). Balance equalises the senders' mean
  losses, not every link.
* **A random sample of setups.** The tuning selects powers, by design, from preflight windows, never
  from scored ones.
* **The paper's PHY** (802.11b at 1 Mb/s), **many nodes** (four boards through A12's mapping), and
  **repeatability** (one session).

## Disclosure

* **Known before this registration:**
  * **W1h's void session read crossings 30.99 / 9.33 and a ratio of 3.32**;
  * W1h's gate and preflight readings, and its two deviations (F130);
  * W1g, the calibration, W1f, and the probes (F124–F129).
* **The rule's single real-data check, run before registration:** the 120 cm preflight at
  (800, 800, auto) gives ADJUST: pi-A to 600.
* **The grid and bands are W1g's and W1f's**, fixed before those sessions.
* **The launch and tuning tools hold credentials** and are not in the repo. They do only what this
  file states:
  * Blue 2's reboot;
  * a hash-checked deploy;
  * one START from a Pi's clock;
  * node 4 started first and verified;
  * the held powers;
  * collection after each board's revert;
  * the registered `--step`, `--gate` and `--score`.
* **No tuning preflight or long run of W1i has been run.**

---

## Runs — added as they happen, 2026-11-06; nothing above the first `---` line was changed

**Tuning preflight 1 — 16:38–16:42, at (800, 800, auto): NO-GO, so tuning stopped as registered.**
Folder: `results/hw/channel24/w1i_2026-11-06/tune1/`.
* **Check 4 failed: node 4's ping at join reached only pi-A** (`peers_reachable [1]`; pi-B and the
  Pi 3 "UNREACHABLE" at 16:38:08–11).
* **The window data show the four boards in one cell throughout.** From the first window
  (16:38:29) every board received every other's frames in every window. In the G31 windows each
  pair exchanged 2 539–2 664 frames.
* The ping is an instant check at join; it missed for the first time in about ten node-4 joins
  today.
* Every other check held:
  * the rate checks: 1 945.7 / 1 965.3 / 2 196.2 / 1 967.1 µs, all channel-limited;
  * `FIXED CCK_1M`;
  * pi-A and pi-B at 8.00 dBm, then auto;
  * one Blue 2 boot (`730fad64`), 6/6 windows;
  * no under-voltage;
  * links alone ≥ 98.7 %.
* **The balance at G31 read 1.442×:** pi-A 5.77 %, pi-B 4.53 %, Pi 3 6.53 %, TP-Link 6.08 %.
  It was not used, the preflight being NO-GO.
* Reported to Mohamed. Continuing needs his decision.

**Deviation — 2026-11-06, ~16:50, approved by Mohamed ("Retry once, rule unchanged").**
* **One retry** of the tuning after a NO-GO caused by node 4's join ping alone.
* **The join check (check 4) and V3 stay exactly as registered.** If the join check fails again,
  W1i stops for good.
* The retry counts toward the five tuning preflights, so preflights 2–5 remain.

**Tuning preflights 2–5 — 16:49–17:22.** Folders `…/w1i_2026-11-06/tune2`–`tune5`.

| # | powers pi-A / pi-B / Pi 3 (mBm) | G31 loss pi-A / pi-B / Pi 3 / TP-Link | spread | verdict |
|---|---|---|---|---|
| 2 | 800 / 800 / auto | 4.22 / 5.13 / 5.39 / 5.57 % | 1.320× | ADJUST: pi-A to 600 |
| 3 | 600 / 800 / auto | 4.24 / 5.04 / 5.98 / 5.72 % | 1.411× | ADJUST: pi-A to 400 |
| 4 | 400 / 800 / auto | 4.62 / 4.52 / 6.73 / 5.73 % | 1.488× | ADJUST: pi-B to 600 |
| 5 | 400 / 600 / auto | 5.00 / 5.24 / 5.98 / 6.19 % | **1.239×** | **NO-GO on check 7** |

* In every one, checks 1–5 held: all four radios at 1 Mb/s, each held power read back then auto,
  node 4 joined with all Pis reached, one boot, no under-voltage.
* **Preflight 5 met the tuning target (1.239×) and failed check 7.** Alone in its rate check, the
  Pi 3's frames reached node 4 at 92.75 %. In preflights 2–4 that figure was 99.98 %; at pi-A and
  pi-B it was 99.75 / 99.80 %.
  * It is a receive-side loss at node 4, in one window. The Pi 3 was at `auto`, never lowered.

---

## Outcome — added 2026-11-06, 17:25; nothing above the first `---` line was changed

**W1i ends with no session, as registered.** Its fifth and last tuning preflight was NO-GO (check
7), and a NO-GO stops the tuning. No long run was started, and nothing is scored.

**What the five preflights show:**
* **The spread at one setting varies more than one step of the rule moves it.**
  * At (800, 800, auto) it read 1.442× and 1.320×, 16 minutes apart. W1h's readings at the same
    setting were 1.43–1.55×.
  * pi-A's loss at 800 mBm ranged over 4.1–5.8 % across today's runs.
  * Taking pi-A from `auto` to 4 dBm (about −15 dB) moved its loss only from about 3.2 % to about
    5.0 %.
* **The Pi 3 was the weakest sender at every setting** (5.4–6.7 %), already at full power.
* **The 1.25× target was reached once** (1.239×), when that preflight failed on another check.
* These boards, 10–15 cm apart, sit within about one wavelength of each other at 2.4 GHz
  (12.5 cm). That could explain why power steps act weakly and the balance wanders, but it is
  not tested here. F131.

**My expectations:**
* "Tuning in one or two preflights" was wrong. Five ran, and none was TUNED.
* The toy plant converged; the radios moved less, and less steadily.
