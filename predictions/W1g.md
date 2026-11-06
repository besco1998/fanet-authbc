# W1g — four radios balanced, the grid moved to bracket both crossings: the AUTHBC / per-record ratio on real radios, capture included

*Registered 2026-11-06, before the session. Main open item W1 (`docs/OPEN_ITEMS.md` §2a). It follows
W1f (F127).
* **Mohamed chose it:** "Re-scoped W1g (Recommended)", 2026-11-06, after the calibration showed
  that the rule in `results/hw/channel24/w1g_cal_2026-11-06/PROTOCOL.md` was the wrong proxy.
  **This is a deviation from that protocol, approved by him.**

Code, plan and predictions at this commit:
* `analysis/dsss_w1g.py`, which imports `analysis/dsss_w1f.py` unchanged (`prereg-W1f`);
* `experiments/channel24/plan_w1g.txt`;
* `results/raw/w1g_predictions.csv` (a second run is byte-identical);
* the kit:
  * the Pis: `hw/channel/run_window_plan.sh`, unchanged since W1d;
  * node 4: `hw/channel/run_window_plan_tplink.sh`, unchanged since `prereg-W1f`;
  * pi-B's power: `hw/channel/set_txpower_window.sh`, new.*

## Why

* **W1f measured AUTHBC's four-board crossing** (31.57 against the model's 29.50) **but not the
  ratio.** The per-record curve stayed above 0.95 at its grid's last point (0.9527 at N_eq 9.5).
* **The cause was capture:** loss depended on the sender, and every point lay above the model.
* **Equal senders cannot remove capture with these radios.**
  * Three calibration runs reached the pre-set balance rule: per-sender spread 1.30× at run 3,
    with the TP-Link at 90 cm and pi-B at 8 dBm.
  * But total loss at that load stayed 0.59–0.65× of the model.
  * Each receiver still has its own strongest sender. Capture-free would need equal strength at
    every receiver: twelve links, four knobs.
* **What remains measurable** is the ratio on real radios with capture present, balanced and
  stated.
  * In W1f both designs crossed 0.95 at nearly the same offered load (AUTHBC at 0.957,
    per-record still above at 0.962).
  * So a grid that brackets the per-record crossing below overload measures the ratio.

## Setup

* **Stations as W1f:** 1 pi-A, 2 pi-B (BCM4345/6), 3 Pi 3 (BCM43430/1), 4 the TP-Link on Blue 2
  (RTL8188EUS, community driver, `rate_ctl` 1 Mb/s). Channel 11, 802.11b at 1 Mb/s, cell
  `authbc-mesh`.
* **The balanced setup, as calibration run 3:**
  * the Pis side by side, 10–15 cm apart, as in W1f;
  * **Blue 2 with its TP-Link at 90 cm** from the group of Pis, same height, on its 5 V adapter;
  * **pi-B held at 8 dBm** through the windows (`set_txpower_window.sh`: set 50 s before the first
    window, after pi-B has joined, read back, returned to `auto` after the last);
  * the other Pis at their default power.
* **Blue 2 is freshly rebooted**, so node 4 joins the Pis' cell. Node 4 joins 40 s before the first
  window, and the plan's header names only the Pis (as W1f).

## The session (`plan_w1g.txt`): 48 windows, about 24 minutes

1. **R1–R4:** each board alone at 600/s, 145 B (the bracket, before).
2. **The capacity points.** All four at f_b = (N_eq − 1)·f₀/3. The designs alternate, each in
   ascending load: A29, P9, A30, P9.25, A31, P9.5, A32, P9.75.
   * A = AUTHBC (145 B, f₀ = 12.5); P = per-record (118 B, f₀ = 50).
   * Four windows each, then a control (one sender at 50/s, rotating over nodes 1–4).
   * Offered load 0.893–0.990, all below overload.
3. **R1–R4 again** (the bracket, after).

Everything else is W1f's: the windows, the shared clock, the frame timing.

## Predictions

**Scored: W1f's registered values, unchanged** (`w1f_predictions.csv`, copied into
`w1g_predictions.csv`):

| | model, four boards | band |
|---|---|---|
| AUTHBC crossing | 29.50 | 26.55–32.45 |
| per-record crossing | 8.93 | 8.04–9.82 |
| **ratio** | **3.304** | **2.974–3.635, and above 2.5** |

**Reported, not scored: the model at this grid** (the same event model, 30 seeds; identical to
W1f's values at the points they share):

| A29 | A30 | A31 | A32 | P9 | P9.25 | P9.5 | P9.75 |
|---|---|---|---|---|---|---|---|
| 0.9569 | 0.9431 | 0.9230 | 0.8964 | 0.9474 | 0.9331 | 0.9126 | 0.8877 |

The model crosses below this grid's per-record points: W1g measures the hardware curves, which
W1f showed lie above the model.

## Definitions

As W1f:
* the delivered fraction;
* the usable-window rule, including node 4's rules (files present, first boot, not its own cell,
  rate fixed);
* at least three usable windows per point;
* b from the control windows, V/(1 − b);
* the crossing interpolated at 0.95 over the scored points (`interpolated_crossing`), and **not
  determined** if the curve does not cross inside the grid, never extrapolated.

Note that the per-record band reaches 9.82, beyond the grid's last point (9.75).

## Validity: the session is void if any of these fails

* **V1–V4, as W1f:**
  * all eight rate checks in 1.9–2.6 ms, with no Pi under-voltage;
  * b ≤ 1 %;
  * node 4 joined the Pis' cell (not `02:11:87:…`) and reached all three Pis;
  * `rate_ctl` `FIXED CCK_1M` at join.
* **V5, balanced senders.** At the A31 windows (the calibration's rate), every sender's mean loss
  is within 1.5× of every other's: the rule of `PROTOCOL.md`, kept as a check of the setup.
* **V6, pi-B at 8 dBm.** Its log shows `set 800: txpower 8.00 dBm` before the windows and `auto`
  after.

## Scored as

* **W1g-1:** the bracket (V1).
* **W1g-2:** the background (V2).
* **W1g-3:** AUTHBC's crossing within 26.55–32.45.
* **W1g-4:** per-record's crossing within 8.04–9.82.
* **W1g-5 — the claim:** the ratio within 2.974–3.635, and above 2.5.

## My expectations `[agent]`

* **V1, V2, V3, V4 and V6 hold**, as in W1f and the calibration.
* **V5 probably holds** (1.30× in calibration). It is one 4-window run, though, and a spread above
  1.5× in this session's A31 windows would void it. That possibility is stated now.
* **AUTHBC's crossing near 31.** W1f gave 31.57. Balancing raised the loss at A31 a little (5.0 %
  in calibration against about 4.3 % in W1f), which moves the crossing left.
* **Per-record's crossing between 9.25 and 9.75.** If it falls between 9.75 and overload, it is not
  determined again; that is also stated now.
* **The ratio near 3.2–3.3, inside its band.** Both designs cross at nearly the same offered load,
  and the model's ratio rests on the same arithmetic.

## What each outcome means

| outcome | meaning |
|---|---|
| valid, W1g-5 holds | **the AUTHBC / per-record ratio measured on four real radios**, with capture present and balanced, inside ±10 % of the model's: the paper's claim holds on hardware even though the radios depart from the model's no-capture rule |
| valid, W1g-5 fails | the ratio on real radios differs from the model's: reported plainly, and the claim is limited to simulation |
| a crossing not determined | the curve stays on one side of 0.95 inside the grid; the ratio stays unmeasured |
| void | a setup or bracket condition failed; nothing is scored, and a re-run needs a new registration |

## What it cannot show

* **The model's own conditions.** Capture is present (F127). The hardware ratio is a ratio of
  real radios, not a check that the model's no-capture rule holds.
* **The paper's PHY** (this is 802.11b at 1 Mb/s), **many nodes** (four boards through A12's
  mapping), and **repeatability** (one session).
* **Equal strength at every receiver.** The senders are balanced only in their mean loss.

## Disclosure

* **This grid was chosen after W1f's results.** Its points bracket W1f's measured AUTHBC crossing
  (31.57) and the region above 9.5 where W1f left the per-record crossing. The bands are W1f's,
  fixed before W1f ran.
* **The calibration runs 1–3** ran on these boards at the A31 rate
  (`results/hw/channel24/w1g_cal_2026-11-06/`), with their loss and spreads known.
* **`PROTOCOL.md` said W1g would keep W1f's plan.** Its balance rule proved to be the wrong proxy
  for capture, and the plan is changed with Mohamed's approval.
* **Already run on these boards:** W1f, its pilot, and probes 1–3 with the diagnostics (F124–F127).
* **The power script was tested on pi-B** on its home Wi-Fi link before this registration (set,
  read back, returned to `auto`); its inline form ran in calibration runs 2–3.
* **No window of this plan has been run.**

---

## Outcome — added 2026-11-06, after the session; nothing above this line was changed

**How it ran.**
* Registered at `26f3ba8` (tag `prereg-W1g`) before any window. The session ran 03:48–04:12 on
  channel 11, scored by `analysis/dsss_w1g.py --score`, unchanged. Outputs:
  `results/raw/w1g_w1g_2026-11-06.csv`, windows `results/hw/channel24/w1g_2026-11-06_windows.csv`,
  files `results/hw/channel24/w1g_2026-11-06/`.
* All four boards ran all 48 windows and reverted.
* Node 4 joined the Pis' cell (`aa:69:5b:4c:da:61`) at `FIXED CCK_1M` and stayed on one boot
  (no reset).
* pi-B was held at 8.00 dBm (03:47:47) and returned to `auto` (04:12:42).
* An independent script recomputed b, every point, the A31 spread and the crossings from the raw
  files; it agrees exactly.

**The session is VOID, by two registered conditions.**
* **V5, balance: failed.** The A31 spread was **5.08×** (rule ≤ 1.5×).
  * The TP-Link's frames were lost at 1.17 %, the Pis' at 4.70–5.92 %.
  * The TP-Link dominated at every point (0.8–1.2 % against the Pis' 3.0–7.1 %).
* **V1, bracket: failed.** The Pi 3's rate check after the session was **2 779.6 µs**, above the
  band's top (2 600 µs). The other seven held (1 940.5–2 508.7 µs).
* V2 (b = 0.083 %), V3, V4 and V6 held.

**Nothing is scored.**

**Reported, not scored.**
* **Neither curve crossed 0.95 inside the grid** (A32 0.9518, P9.75 0.9509). So even a valid
  session would not have measured the ratio: on these radios, with the TP-Link dominant, both
  crossings lie within about 1 % of overload.
* **The TP-Link's transmit strength changed between boots.**
  * In calibration run 3, with the same setup 25 minutes earlier and a fresh boot, its frames were
    lost at 4.46 % and the spread was 1.30×.
  * At the TP-Link as a receiver, the Pis' frames were lost about as in calibration 3: pi-A 7.1 %
    (8.0 %), Pi 3 2.9 % (2.3 %).
  * Radio links are reciprocal: had Blue 2 moved or turned, both directions would have changed.
    Only its sending changed. The cause is unknown.
* **The Pi 3 slows across the day:** before / after 2 293 / 2 358 µs in W1e (13:34), 2 357 /
  2 470 µs in W1f (21:46), 2 509 / 2 780 µs here (03:48). It was at 46 °C, not throttled, after
  15 hours up. The cause is unknown; a reboot may reset it, untested.

**My expectations.**
* "V5 probably holds" was **wrong**, as stated possible: the balance did not survive a reboot of
  Blue 2.
* "V1 holds" was **wrong** for the Pi 3.
* "Per-record's crossing between 9.25 and 9.75" was wrong: it lies above 9.75.

**What it means.** A re-run needs a new registration (registered rule). The calibration and this
session together show that this kit cannot hold a balanced four-station setup across boots, and
that the Pi 3 drifts out of its rate band over hours. F128.
