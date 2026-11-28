# V1a — the closed form as stated, tested on the radios: the trio at occupancy 0.3, 0.4 and 0.5

*Registered 2026-11-28, before the session; the time is the commit's. Decided by Mohamed on
2026-11-28 (`docs/DECISIONS.md`, "fixing the model report's three open issues", issue 1, path (a)).
Code: `analysis/v1.py` (`tests/test_v1.py`); plan `experiments/channel24/plan_v1a.txt`.*

## Why

**No hardware session has yet scored the closed form.**
* W1e, W1j and W1k were predicted by W1c's event simulation of the access rule, not by (G5) or
  (G9).
* W1r recorded the closed form's values beside ns-3 but scored neither.

**On three radios, the part of the closed form that applies is the finite-station form:**
* **(FS):** N = 3 to 5, occupancy at most 0.5, accepted by Mohamed on 2026-11-20 and held at 12 of
  12 cells against ns-3 (U-FS).
* **(G5) and (G25)** are outside their stated ranges here: (G25) needs 8 or more other stations.

V1a scores (FS) **as stated**:
* the standard's window W = 32 and rule set A;
* the airtime the model already uses;
* nothing measured on the radios.

The hardware-matched form, built from C1's measured backoff, is path (b). It gets its own
registration and a new session (V1b).

## The model under test

`authbc.models.finite_station.loss(3, f, T_f, W = 32)`, unchanged since U-FS, called through
`w1r._closed`, the function that produced W1r's recorded values. T_f is 1 864 µs: the 145 B UDP
frame, ns-3 frameSize 173, 802.11b at 1 Mb/s with the long preamble.

## The session (remote; Mohamed, 2026-11-28)

* **The radios:** pi-A, pi-B and the Pi 3, left as they stand in W1s's 1 m triangle (L2).
* **The settings:** 802.11b at 1 Mb/s on channel 11. Frame burst is off, and every power is 15 dBm
  from the first window; both are read back.
* **The traffic:**
  * broadcast UDP, 145 B of payload, each frame at an instant drawn anew in its period;
  * W1c's rates for occupancy 0.3, 0.4 and 0.5 among three boards: 52, 70 and 87 frames/s per
    board.
* **The plan** (`plan_v1a.txt`):
  * a rate check per board (600 frames/s offered);
  * then five rounds. Each round holds one trio window at every occupancy, in rotated order, then
    a control window (one board alone at 50 frames/s; boards 1, 2, 3, 1, 2);
  * then the rate checks again.
* **Each window's length:**
  * a point's five windows expect at least 400 lost receptions under the lowest of the candidate
    predictions below (three senders, two receivers each);
  * this gives a 95 % interval of about ±10 % on the point's loss.
* **Logged** (the standing rule of 2026-11-19):
  * per-sender RSSI at each receiver, halfway through and after each window;
  * the frame-burst state before and after;
  * every frame's sequence number and receive time.
* **The sniffer:** the TP-Link sniffer on Blue 2 records the session for timing. That record is
  not scored.
* **The safety kit:** preflight and chip check. A board that locks up stops its windows, and that
  is recorded.

## Predictions (`python analysis/v1.py --markdown`, generated from `results/raw/v1a_predictions.csv`)

| u | frames/s per board | **finite-station, W = 32** | (G5) | (G25) | ns-3, standard (± s.e.) | event simulation, standard (± s.e.) | window (s) | expected lost |
|---|---|---|---|---|---|---|---|---|
| 0.3 | 52 | **0.169 %** | 0.263 % | 0.216 % | 0.188 ± 0.010 % | 0.193 ± 0.015 % | 155 | 400 |
| 0.4 | 70 | **0.273 %** | 0.468 % | 0.366 % | 0.306 ± 0.010 % | 0.312 ± 0.019 % | 75 | 413 |
| 0.5 | 87 | **0.397 %** | 0.743 % | 0.552 % | 0.452 ± 0.008 % | 0.446 ± 0.026 % | 45 | 435 |

**Scored, at each of the three points:** the finite-station form holds if it lies within **±15 %**
of the measured loss (U-FS's tolerance): |FS − m| ≤ 0.15·m.
* **The measured loss m, as W1d defined it** (`dsss_three.window_rows`): the trio's frames
  received by the other two boards, over frames sent times two. It is averaged over the point's
  usable windows, less the background b from the control windows. Its 95 % interval comes from
  Student's t over windows, as in W1r.
* **A point needs three or more usable windows,** W1d's rule.
* The tolerance is fixed here and is not widened after the session.

**Reported, not scored:**
* (G5) and (G25) at W = 32, outside their stated ranges;
* ns-3 with the standard rule: W = 32 for every board, equal power, 30 seeds × 100 s;
* W1c's event simulation with the standard rule, 30 seeds.

**Validity, before anything is scored:**
* every rate check within 1 900–2 600 µs;
* frame burst 0 before and after on every board;
* no chip stop;
* background b ≤ 1 %;
* each board's link loss alone (its control windows) ≤ 1 %, the criterion of 2026-11-23.

A validity failure stops the scoring, and Mohamed is asked.

## Expectations `[agent]`

* **(FS) fails, on the optimistic side, at u = 0.5 at least.**
  * At that rate W1e measured 0.58 % and W1r 0.66 %, against FS's 0.40 %.
  * C1 then showed the likely cause, the radios' own access rule:
    * the Pi 4s send about 47 % of their frames at DIFS with no backoff, which the standard rule
      omits;
    * the Pi 3 waits a fixed 43 µs more than DIFS.
* **Probably at 0.3 and 0.4 as well,** by a similar factor of about 1.4–1.7.
* **ns-3 with the standard rule** lies near (FS), below the hardware.

## Disclosure

* **Seen before this registration:**
  * the trio at u = 0.5 in W1e (2026-11-05, frame burst on) and W1r (2026-11-22, frame burst off);
  * C1's timing (2026-11-27).
  * No session has run the trio at u = 0.3 or 0.4.
* **This test is run although its likely outcome is known.** The closed form's claim must be tested
  as stated before a matched version replaces it, and a failure here is reported as one.
* **None of V1a's windows has been run.**

## Outcome — added 2026-11-28, after the session; nothing above this line was changed

* **The session:** `results/hw/channel24/v1a_2026-11-28`, windows 20:49:29–21:19:09, run remotely at
  Mohamed's instruction (2026-11-28), boards as left in L2 (`geometry.json`, carried over from C1).
  * Preflight `v1a_2026-11-28_pre`: **GO** (cycles 2 029.5, 2 046.9, 2 392.5 µs; frame burst 0;
    every board reverted).
  * The plan deployed was the registered one (sha256 `f019e909e933…`, unchanged since
    `prereg-V1a`). All 26 windows ran on every board; every power read back 15.00 dBm; no chip
    stop; every board reverted.
  * The sniffer recorded throughout, 0 packets dropped by the kernel. Its capture is stored
    gzip-compressed (`sniffer/sniff_bbb2_1795891769.pcap.gz`, 10.4 MB; the raw 88.7 MB file's
    sha256 is `be3d925d…fc48498b`, checked after decompression). It is not scored.
* **Scored** with `python analysis/v1.py --score results/hw/channel24/v1a_2026-11-28`
  (`results/raw/v1a_v1a_2026-11-28.csv`).

### Validity — held

| condition | measured | held |
|---|---|---|
| frame burst off on every board, before and after | 0 / 0 | yes |
| rate checks, before / after (µs) | pi-A 2 025.9 / 2 026.0, pi-B 2 055.5 / 2 061.2, the Pi 3 2 453.3 / 2 417.9 | yes, all six |
| background b (5 control windows) | 0.109 % | yes |
| link loss alone, worst control window per board | pi-A 0.182 %, pi-B 0.136 %, the Pi 3 0.136 % | yes, all three |

### The closed form as stated: failed at all three points, on the optimistic side

| u | frames/s per board | measured loss, less b (95 % interval; 5 windows) | **finite-station, W = 32** | error | held |
|---|---|---|---|---|---|
| 0.3 | 52 | 0.294 % (0.198–0.391) | **0.169 %** | −42.7 % | **no** |
| 0.4 | 70 | 0.501 % (0.378–0.625) | **0.273 %** | −45.5 % | **no** |
| 0.5 | 87 | 0.697 % (0.597–0.798) | **0.397 %** | −43.0 % | **no** |

* **The radios lose 1.74–1.84 times what the form predicts.** The miss is not sampling: the
  form lies below the lower end of the 95 % interval at every point.
* **Reported beside it** (not scored):

| u | (G5), W = 32 | (G25), W = 32 | ns-3, standard rule | event simulation, standard rule |
|---|---|---|---|---|
| 0.3 | 0.263 % | 0.216 % | 0.188 % | 0.193 % |
| 0.4 | 0.468 % | 0.366 % | 0.306 % | 0.312 % |
| 0.5 | 0.743 % | 0.552 % | 0.452 % | 0.446 % |

  ns-3 and the event simulation, both with the standard rule, sit near the form, and the hardware
  loses 1.52–1.64 times what they predict: the **rule** is what misses, not the form's
  approximation of it.

### The independent check

A separate reader, sharing no project code, took the sent and received counts from every board's
raw JSON files. It gave the same background (0.001091) and the same three losses (0.002945,
0.005014, 0.006973), with all 15 trio windows usable.

### My expectations, against the outcome

* **"(FS) fails, on the optimistic side, at u = 0.5 at least":** right, and at 0.3 and 0.4 too.
* **"By a similar factor of about 1.4–1.7":** wrong in size. The factor is 1.74–1.84, above my
  range at every point.
* **"ns-3 with the standard rule lies near (FS), below the hardware":** right (1.11–1.14 × FS).

### Seen after scoring — not a result

* **(G5), outside its stated range, lands within −11 to +7 % of the hardware** (0.263 / 0.468 /
  0.743 against 0.294 / 0.501 / 0.697). This is not evidence for (G5) here. Two departures from
  the model would act in opposite directions: Poisson starts overstate the loss of three periodic
  stations (U-FS: 1.54–1.77 times ns-3's loss at N = 3), while the radios' own rule (C1) adds
  collisions the standard rule does not have. Their cancelling here is a coincidence to be shown,
  not assumed; the matched form (path b) separates them.
* **The Pi 3's frames are lost most** (raw, before b: 0.51–1.13 % from the Pi 3 against
  0.25–0.90 % between the others), which fits C1's fixed extra 43 µs on the Pi 3.
* **Each board's RSSI query gave one value for both peers** (pi-A −50/−50, pi-B −53/−53, the Pi 3
  −56/−56 dBm, medians), so it cannot show a change of geometry per link here.
