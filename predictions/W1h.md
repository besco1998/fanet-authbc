# W1h — W1g's session, scored only on an attempt whose own gate windows show balanced senders

*Registered 2026-11-06, before any attempt. Main open item W1 (`docs/OPEN_ITEMS.md` §2a). It
follows W1g (F128 and its addendum) and the W1h pilot (F129).
* **Mohamed asked for it:** "i have restarted the pi3, try again", 2026-11-06. He approved the plan
  that morning.
* **After the pilot he chose "Revised W1h":**
  * the gate is read after each attempt;
  * the Pis are not rebooted before attempts.

Code, plan and kit at this commit:
* `analysis/dsss_w1h.py`, which imports `analysis/dsss_w1g.py` unchanged (`prereg-W1g`) and,
  through it, `dsss_w1f.py` (`prereg-W1f`);
* `experiments/channel24/plan_w1h.txt`;
* the kit, all unchanged since W1g:
  * the Pis: `hw/channel/run_window_plan.sh`;
  * node 4: `hw/channel/run_window_plan_tplink.sh`;
  * pi-B's power: `hw/channel/set_txpower_window.sh`.

No new predictions: the score reads W1g's file (`results/raw/w1g_predictions.csv`), whose scored
rows are W1f's, unchanged.*

## Why

* **W1g was void** on two of its conditions: the senders were not balanced (V5, spread 5.08×), and
  the Pi 3 was out of its rate band after the session (V1, 2 780 µs).
* **The cause of the imbalance is undetermined** (F128 addendum).
  * At about 08:25 Mohamed found Blue 2 and its dongle displaced closer to the Pis, and restored
    them to 90 cm; when they moved is unknown.
  * The other explanation, the TP-Link differing between boots, is not established either.
* **So W1h measures the balance on each attempt's own Blue 2 boot and placement**, in four windows
  before the capacity block. It scores only an attempt whose gate passes. That covers both
  explanations.

## Setup

W1g's, unchanged:
* Stations: 1 pi-A, 2 pi-B (BCM4345/6), 3 Pi 3 (BCM43430/1), 4 the TP-Link on Blue 2 (RTL8188EUS,
  community driver, `rate_ctl` 1 Mb/s). Channel 11, 802.11b at 1 Mb/s, cell `authbc-mesh`.
* The Pis side by side, 10–15 cm apart.
* **Blue 2 with its TP-Link at 90 cm** from the Pis, on its 5 V adapter (placement restored by
  Mohamed at about 08:25).
* **pi-B held at 8 dBm** through the windows; the other Pis at default power.
* **Blue 2 freshly rebooted for each attempt**, so node 4 joins the Pis' cell.

**The Pis are not rebooted before an attempt** (F129: their first ad-hoc session after a boot
broadcasts at 6 Mb/s).
* They were last booted at 09:26 and have run two ad-hoc sessions since, both at 1 Mb/s.
* **If a Pi boots for any reason, one ad-hoc session runs on it before the next attempt**,
  disclosed and not scored.
* V1's rate checks catch a session at the wrong rate in any case.

## One attempt (`plan_w1h.txt`): 52 windows, about 26 minutes

1. **R1–R4:** each board alone at 600/s, 145 B (the bracket, before).
2. **G31 ×4 — the gate.** All four boards at W1g's A31 line (125 frames/s each, 145 B), relabelled.
   Not scored.
3. **W1g's capacity block, verbatim:** A29, P9, A30, P9.25, A31, P9.5, A32, P9.75. Four windows
   each, then a control (B1–B4 rotating).
4. **R1–R4 again** (the bracket, after).

## The gate

**Read after the attempt.** No board can be reached during a session (F129). The attempt's files
are collected, then `dsss_w1h.py --gate` is run on them. It reads only R1–R4 before and the G31
windows.

**GO needs all of these:**
* the four rate checks before in band (1.9–2.6 ms, no Pi under-voltage);
* node 4 joined the Pis' cell, reached all three Pis, at `FIXED CCK_1M` (W1f's join checks);
* all four G31 windows complete and usable;
* **the G31 senders within 1.5× of each other** (V5's own rule, on the gate's windows).

**What follows:**
* **GO:** the attempt is the session, scored with `dsss_w1h.py --score`. No attempt follows a GO.
* **ABORT:** the attempt is discarded. Its capacity windows are neither scored nor analysed; only
  its gate readings are reported. Blue 2 is rebooted and a new attempt starts.
* **At most three attempts.** If three gates fail at the restored placement, stop and ask
  Mohamed.

## Predictions

**Scored: W1f's registered values, unchanged**, read from `w1g_predictions.csv`:

| | model, four boards | band |
|---|---|---|
| AUTHBC crossing | 29.50 | 26.55–32.45 |
| per-record crossing | 8.93 | 8.04–9.82 |
| **ratio** | **3.304** | **2.974–3.635, and above 2.5** |

**Reported, not scored:** the model at this grid, as W1g registered it:

| A29 | A30 | A31 | A32 | P9 | P9.25 | P9.5 | P9.75 |
|---|---|---|---|---|---|---|---|
| 0.9569 | 0.9431 | 0.9230 | 0.8964 | 0.9474 | 0.9331 | 0.9126 | 0.8877 |

## Definitions

As W1g:
* the delivered fraction;
* the usable-window rule with node 4's rules;
* at least three usable windows per point;
* b from the control windows (B only; G31 is excluded), V/(1 − b);
* the crossing interpolated at 0.95 over the scored points, and **not determined** if the curve
  does not cross inside the grid, never extrapolated.

## Validity: the session is void if any of these fails

**W1g's V1–V6, unchanged**, computed by `w1g.score` on the session's own windows:
* V1: all eight rate checks in band;
* V2: b ≤ 1 %;
* V3: node 4 in the Pis' cell, all Pis reached;
* V4: `rate_ctl` fixed;
* **V5: the session's own A31 windows within 1.5×**, not the gate's;
* V6: pi-B at 8 dBm, then back to auto.

## Scored as

* **W1h-1:** the bracket (V1).
* **W1h-2:** the background (V2).
* **W1h-3:** AUTHBC's crossing within 26.55–32.45.
* **W1h-4:** per-record's crossing within 8.04–9.82.
* **W1h-5 — the claim:** the ratio within 2.974–3.635, and above 2.5.

## My expectations `[agent]`

* **The Pis at 1 Mb/s** (their third ad-hoc session on this boot), so V1 holds before.
* **The Pi 3's rate check in band.** It was booted at 09:26. In W1e, W1f and W1g its first rate
  check read 2 293–2 509 µs at 600/s. Its drift within a session (+65 to +271 µs) could still
  carry the check after the session past 2 600 µs; that is stated now.
* **The first gate probably passes.** Calibration run 3, with this placement and pi-B at 8 dBm,
  gave 1.30×. But the placement was restored by hand, and the cause of W1g's imbalance is unknown.
  A failed gate is possible.
* **AUTHBC's crossing near 31,** if the session is balanced. Calibration run 3 lost 5.0 % at A31,
  so V ≈ 0.95 there.
* **Per-record's crossing between 9.25 and 9.75.** If it lies above 9.75 it is not determined, as in
  W1g; that is stated now.
* **The ratio near 3.2–3.4, inside its band.**

## What each outcome means

| outcome | meaning |
|---|---|
| valid, W1h-5 holds | **the AUTHBC / per-record ratio measured on four real radios**, balanced and with capture present, within ±10 % of the model's |
| valid, W1h-5 fails | the ratio on real radios differs from the model's: reported plainly, and the claim stays limited to simulation |
| a crossing not determined | the curve stays on one side of 0.95 inside the grid; the ratio stays unmeasured |
| void | a validity condition failed; nothing is scored |
| three gates fail | no session; the three gates' readings are reported |

## What it cannot show

* **The model's own conditions.** Capture is present (F127). Balance makes the senders' mean losses
  equal; it does not make every link equal.
* **A random sample of setups.** The gate keeps only balanced boots and placements, by design. It
  selects on its own windows, never on the scored ones.
* **The paper's PHY** (this is 802.11b at 1 Mb/s), **many nodes** (four boards through A12's
  mapping), and **repeatability** (one session).

## Disclosure

**Known before this registration:**
* W1g's data (void) and its correction;
* calibration runs 1–3;
* W1f, its pilot, and probes 1–3 with the diagnostics (F124–F128).

**The grid and the bands are W1g's and W1f's**, fixed before those sessions.

**Run before this registration, on these boards** (F129):
* **The W1h pilot** (`results/hw/channel24/w1h_pilot_2026-11-06/`): the first 12 windows of the
  draft plan, after the Pis were rebooted.
  * The Pis were at 6 Mb/s.
  * Its gate read a spread of 2.64× (Pis about 1.2 %, TP-Link 0.54 % at G31). That says nothing
    about the 1 Mb/s setup.
* **Three rate diagnostics** (`results/hw/channel24/diag_rate_2026-11-06/`): the Pis alone, no
  capacity or gate windows.

**The launch and collect tools hold credentials** and are not in the repo. They do only what this
file states:
* a hash-checked deploy of the kit above;
* Blue 2's reboot;
* one START;
* pi-B's power script;
* collection after the attempt;
* the registered `--gate` and `--score`.

**No window of a W1h attempt has been run.**

---

## Attempts — added as they run, 2026-11-06; nothing above the first `---` line was changed

**Erratum in the registration above.** "Setup" says the Pis "have run two ad-hoc sessions since,
both at 1 Mb/s". In fact the first (diagnostic t1) ran at 6 Mb/s, which was its finding, and the
second (t2) at 1 Mb/s. The design is unaffected: attempt 1 was their third session.

**Attempt 1 — 13:31–13:58, gate ABORT, discarded unscored.**
* All four boards ran all 52 windows and reverted.
* Node 4 joined the Pis' cell (`22:37:7b:21:13:7b`) at `FIXED CCK_1M`, reached all three Pis, and
  stayed on one boot (`2f39ecd8`).
* pi-B was held at 8.00 dBm (13:30:50), then returned to auto (13:57:45).
* Folder: `results/hw/channel24/w1h_2026-11-06/a1/`.

The gate (`dsss_w1h.py --gate`, unchanged):

| check | reading | held |
|---|---|---|
| node 4 joined, rate fixed | `22:37:7b:21:13:7b`, `FIXED CCK_1M` | yes |
| rate check before, pi-A / pi-B / TP-Link | 1 942.3 / 1 947.7 / 1 962.8 µs | yes |
| **rate check before, Pi 3** | **2 613.4 µs** (band ≤ 2 600) | **no** |
| G31 windows usable | 4/4 | yes |
| **G31 sender spread** | **5.23×**: pi-A 2.95 %, pi-B 5.50 %, Pi 3 6.12 %, TP-Link 1.17 % | **no** |

* The Pis were at 1 Mb/s. The Pi 3 was already above its band at the start, after 4½ hours up.
* The TP-Link dominated as in W1g (1.17 % there too), at the placement Mohamed restored.
* As registered, its capacity windows are neither scored nor analysed.

**Procedure addendum — 2026-11-06, ~13:45, before attempt 2 (Mohamed's instruction).**
* **A 3-minute preflight precedes every further attempt:** `analysis/hw_preflight.py`, procedure in
  `hw/channel/README.md`, committed at `474b1f5` and amended in this commit. It has six checks:
  * the Pis at 1 Mb/s;
  * the TP-Link's rate;
  * pi-B's power;
  * node 4's join;
  * the supply;
  * a G31 spread ≤ 1.5×.
* **What the verdicts do:**
  * GO starts the attempt at once;
  * RETRY (only Pis too fast, after a boot) runs one more preflight;
  * NO-GO starts nothing and is reported.
* It is procedural and never scored. The registered gate still decides each attempt.
* **The Pi 3 is rebooted before attempt 2**, its rate check being out of band. The preflight is its
  ad-hoc session after the boot, as the setup above requires.
