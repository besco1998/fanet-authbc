# W1d — three ad-hoc radios at 2.4 GHz: the contention model on hardware, two chips, channel 11

*Registered 2026-11-05, before any measured session; the one-window probe below is disclosed. Main
open item W1 (`docs/OPEN_ITEMS.md` §2a). It supersedes W1c, whose premise of five ad-hoc radios
proved false (F120; W1c's outcome addendum). Code, plans and predictions at this commit:
`analysis/dsss_three.py`, `hw/channel/run_window_plan.sh`, `hw/channel/run_sniffer.sh`,
`experiments/channel24/plan_s{0,1}.txt`, `results/raw/w1d_predictions.csv`.*

## Why, and what changed from W1c

On 2026-11-05 the BeagleBone Blues were found to have no ad-hoc (IBSS) mode:
* the kernel's answer is −95 on both boards;
* mainline `wlcore` has not announced ADHOC since commit 7845af35e0de (2015).

The radios that can join an ad-hoc cell are three:

| node | board | chip | firmware |
|---|---|---|---|
| 1 | pi-A, Raspberry Pi 4 | BCM4345/6 | 7.45.265 |
| 2 | pi-B, Raspberry Pi 4 | BCM4345/6 | 7.45.265 |
| 3 | Raspberry Pi 3 Model B | BCM43430/1 | 7.45.98 |

All three run Raspberry Pi OS Bookworm; pi-A is on an official supply that passed a stress check.

**Three radios cannot measure the capacity ratio.** A12's mapping keeps the contending load
fixed, so the total offered load at the crossing grows as N/(N − 1): with three stations it is
1.06 (AUTHBC) and 1.05 (per-record), overload, where W1b showed that a queue's discard policy and
not the access rule decides delivery. **This registration tests the contention model.** The ratio
waits for a fourth station: a Blue that injects ad-hoc-format frames (an engineering probe, not
this registration) or a purchase.

## The room, the channel, the kit

* **Channel 11 (2462 MHz).** Mohamed: *"use a channel that does not overlap my home Wi-Fi after
  surveying"*. The survey of 2026-11-05 (pi-A, `iw scan`) heard one network, his router, on
  channel 1 (−69 dBm). Channel 11 does not overlap it.
* **802.11b at 1 Mb/s:** the only broadcast rate a Raspberry Pi can use at 2.4 GHz (F35).
* **Placement:** the three boards on a circle of about 2 m, at the same height, antennas
  unobstructed; Mohamed places them.
* **The Blues are sniffers only**, in monitor mode on channel 11 (`run_sniffer.sh`). What they
  count is reported, not scored.
* **The kit (`run_window_plan.sh`)** follows the path F73–F76 ran on (deadmen, raw `iw`,
  receivers bound before senders, self-revert). In addition:
  * every window names its senders and payload;
  * `vcgencmd get_throttled` is recorded before and after every window;
  * the governor is set to `performance`;
  * the deadmen are sized to the plan.
  * It is deployed to `~/authbc_w1d/` on each board; pi-B's October kit is left untouched.

## The sessions

* **S0 — pilot** (`plan_s0.txt`, nine windows).
  * Each board alone, offered 600 frames/s of 145 B (the AUTHBC frame on air), twice: the rate
    check, read at the receivers from the sequence numbers spanned (F74's method).
  * Then one control window per board, alone at 50 frames/s.
* **S1 — contention** (`plan_s1.txt`, sixty windows).
  * For each occupancy (0.50, 0.70, 0.85) and each group: the pairs A–B, A–C, B–C, and the trio.
  * Four windows per group, then a control window; 145 B, each frame at an instant drawn anew in
    its period.
* Windows of 25 s, senders sending 22 s, starts 30 s apart, on one shared clock.

## Definitions

* **The delivered fraction of a window:** frames received over frames sent × (n − 1), summed over
  ordered pairs **of that window's senders**. In a pair window the third board only listens and
  is not counted.
* **A window is usable** if no frame was dropped before the air, every sender reached 98 % of its
  rate, at most 1 % of frames were late (F73's rule), **and no board lost voltage during it**
  (`get_throttled` bit 0 set at the end, or bit 16 newly set).
* **Background b:** the mean loss of the session's usable control windows.
* **A point is scored** only with at least three usable windows.

## Predictions (`analysis/dsss_three.py --predict`)

**The contention predictions are W1c's registered rows, unchanged.** They come from the event
model at 802.11b that W1b tested against ns-3 (F119) and were registered before any board session.
The model does not know which chip a station has, so a mixed pair carries the Pi 4 pair's
prediction.

| group (frames/s per board at occupancy 0.50 / 0.70 / 0.85) | model loss | band |
|---|---|---|
| a pair: A–B, A–C or B–C (131 / 183 / 222) | 0.217 / 0.552 / 1.426 % | 0.6–1.4× |
| the trio A–B–C (87 / 122 / 148) | 0.446 / 1.059 / 2.395 % | 0.3–1.4× |

These are F70's bands. Capture can only lower loss where a third radio listens, hence the wider
band for the trio.

**Rate check.** One saturated sender's cycle under the standard's rule at 1 Mb/s is **2 224 µs**.
At 2 Mb/s it would be 1 388 µs, and less at higher rates.

## Scored as

* **W1d-1 — rate check.** Each board's cycle lies within 1.9–2.6 ms, i.e. at 1 Mb/s. **Stop rule:**
  a board outside it ends the campaign until a new registration.
* **W1d-2 — background.** b ≤ 1 %. **Stop rule:** above it, S1 is not run on this channel.
* **W1d-3 — contention.** At each group and occupancy, the mean loss of the usable windows minus b
  lies in its band (12 points).
* **W1d-4 — spacing, the BCM4345.** Each Pi 4's cycle in the rate check is shorter than the
  standard's 2 224 µs. At 5 GHz F74 found this chip short of the standard; here the same is
  registered at 2.4 GHz and 1 Mb/s. For the Pi 3's BCM43430 no direction is registered: it is
  reported.
* **Reported, not scored:**
  * the loss of each chip in the mixed pairs;
  * what the third board hears in pair windows;
  * the Blues' counts of frames on air per source, foreign frames on channel 11, and frames that
    failed their check sequence (`analysis/sniffer_hw.py`, written after the first capture;
    nothing scored depends on it).

## My expectations `[agent]`

* **W1d-1 and W1d-2** hold; the probe below already ran cleanly on channel 11.
* **W1d-3** fails low for the Pi 4 pair (A–B) at occupancy 0.85, below the band. There the two
  Pi 4s hold queues of their own, as at 5 GHz (F73: 0.56×, and F115). The other points hold,
  the trio's band being wide.
* **W1d-4** holds. I have no expectation for the Pi 3.

## What each outcome means

| outcome | meaning |
|---|---|
| W1d-3 holds at most points | **the contention model, which every capacity rests on, predicts loss on real radios of two chip families with two and three stations**, at a second PHY, with nothing fitted |
| W1d-3 fails at high load for the Pi 4 pair only | the own-queue departure of F73 recurs at 2.4 GHz; it belongs to that chip, and the mixed pairs say whether the Pi 3 shares it |
| W1d-3 fails broadly | the model does not describe these radios at 802.11b; reported plainly, and the hardware support for the capacities is weaker than the paper states |

## What it cannot show

* **The capacity ratio**: three stations reach the crossing only in overload.
* **The paper's PHY.** This is 802.11b at 1 Mb/s, not 802.11a at 6 Mb/s.
* **Capture** at 2.4 GHz is limited only by the placement. **Interference** is limited only by
  the channel choice and the control windows.

## Disclosure

* **The probe.** One window of the trio at 87 frames/s on channel 11 was run on 2026-11-05 to
  check the kit (`results/hw/channel24/probe_2026-11-05/`). Every board joined the cell, reached
  the others, sent at its rate, lost no power, and returned to the home Wi-Fi. Its loss was
  0.25 %, inside the band, one window. **It is not scored and not pooled with S1.**
* W1c's predictions, its 802.11b model (F119) and the overload arithmetic were all known.
* Nothing else has been run at 2.4 GHz since F35 (August).

---

## Outcome — added 2026-11-05, after S0; nothing above this line was changed

Registered at `914b7ec` (tag `prereg-W1d`). S0 ran on 2026-11-05, 03:52–04:00, on channel 11.
`analysis/dsss_three.py --score` (unchanged since) → `results/raw/w1d_s0_2026-11-05.csv`; windows
`results/hw/channel24/s0_2026-11-05_windows.csv`; the boards' files `results/hw/channel24/s0_2026-11-05/`.
All nine windows were usable: no frame dropped before the air, no board lost voltage.

| | registered | measured | |
|---|---|---|---|
| **W1d-1** rate check, pi-A | 1.9–2.6 ms | 1 946.6 µs (windows 1 950.2, 1 943.0) | held |
| **W1d-1** rate check, pi-B | 1.9–2.6 ms | 1 945.6 µs (1 945.0, 1 946.2) | held |
| **W1d-1** rate check, Pi 3 | 1.9–2.6 ms | **4 878.5 µs (4 714.3, 5 042.6)** | **failed** |
| **W1d-2** background | b ≤ 1 % | 0.091 % (three control windows: 0.05, 0.18, 0.05 %) | held |
| **W1d-4** the BCM4345 shorter than 2 224 µs | | 1 946.6 and 1 945.6 µs | held |
| **W1d-3** contention | 12 points | **not run** | — |

**The stop rule ends the campaign.** A board outside the rate band "ends the campaign until a new
registration". S1 was not run and will not be run under this registration. My expectation (W1d-1
holds) was wrong.

**Cross-check.** In every rate window the two receivers give the same cycle to 0.1 µs. For window
04 the Pi 3's own count gives 4 592 µs (4 792 frames in 22.0 s) and the receivers 4 714 µs. The
receivers' span runs 0.58 s past the sender's end: frames still queued in the radio, which is
why F74 reads the cycle at the receivers.

**What the Pi 3's failure is.** Three diagnostics ran after S0, disclosed and outside this
registration (`results/hw/channel24/diag_2026-11-05/pi3/`). In each the Pi 3 was alone in the cell
on channel 11, offered 600 frames/s of 145 B.
* **Not the host.** The CPU was 99 % idle and the sender blocked in its socket, waiting for the
  radio. Every frame sent reached the radio's counter (3 819 of 3 819).
* **Not power save or Bluetooth.** The chip shares its antenna with Bluetooth. Four runs:
  power save on (254 frames/s), off (219), off with Bluetooth blocked (209), on again (202). The
  last run had the first one's settings and was the slowest.
* **A limit in the radio that tightens with sending and relaxes with rest.** After nine minutes
  idle, eight runs of 10 s back to back gave 266, 232, 216, 208, 197, 193, 190 and 183 frames/s
  (a cycle of 3.76 rising to 5.46 ms). The SoC was never throttled (`get_throttled` 0x0) and
  warmed only from 43.5 to 47.2 °C. From outside the closed firmware one cannot tell whether the
  radio throttles on its own temperature or on a budget of transmit time.
* **Not a slower rate.** 802.11b has no rate below 1 Mb/s, at which this frame takes 1 864 µs.
  The receivers counted no duplicates.

Even rested, the BCM43430 sends a frame every 3.76 ms where the standard's rule takes 2.22 ms. It
is not a station of the model. Its limit changes with time and would act at the contention rates
too, in a way that no frame-level record here could show (next paragraph).

**The sniffers recorded nothing.** Both Blues ran `run_sniffer.sh` through S0 and captured 0
frames on channel 11, while the Pis sent 58 668. Two checks followed on Blue 1, each
10 s on channel 1, where the router beacons at −69 dBm (`results/hw/channel24/diag_2026-11-05/blue1/`):
* `wlan0` itself set to monitor: 0 frames;
* a monitor interface beside a connected `wlan0`: 0 frames.

The TI driver lets a monitor interface be created, but on this kernel and firmware it delivers
no frame. The Pi 4's stock driver offers no monitor mode at all, so no board in the kit can see
single frames. The sniffer was reported, not scored; nothing scored changes.

**What holds, and is new.**
* **Channel 11 is quiet:** 0.09 % background.
* **The Pi 4's spacing is short of the standard again, now at 2.4 GHz and 1 Mb/s.** The gap
  between frames is 82 µs (1 946 − 1 864), against a mean of 360 µs under the standard (DIFS
  50 µs plus 15.5 slots of 20 µs). This is a second band for G27.
* **Reported, not scored:** saturated alone, each Pi 4 lost 0.70–0.81 % of its frames at the
  other two boards. At 50 frames/s the loss was 0.05–0.18 %. W2 lists the same symptom at 5 GHz
  ("one sender losing 0.5–0.9 % alone").

**What it changes.** Three ad-hoc radios became two of one chip. The contention model can still
be tested at 802.11b with the Pi 4 pair (N = 2, W1c's registered rows), but only under a new
registration. What to run next is Mohamed's decision (`docs/OPEN_ITEMS.md`, Q15). F121.

---

## Addendum — added 2026-11-05, 13:10: the Pi 3 reading above is WITHDRAWN. Nothing above this line was changed

Mohamed moved the Pi 3 beside the two Pi 4s, moved Blue 1 farther from them, unplugged Blue 2, and
asked for the tests again. They were repeated unchanged, with the same kit (hashes checked against the repo), plan and channel. This is a
disclosed repeat, not a scored session: the stop rule triggered in S0 stands and S1 was not run.
Data: `results/hw/channel24/s0r_2026-11-05/`, scored by the unchanged script into
`results/raw/w1d_s0r_2026-11-05.csv`.

*Expected, stated before the run:* if the Blue had nothing to do with it, the Pi 3 at 4.7–5.0 ms
again, decaying from about 266 to 183 frames/s.

| | S0, 03:53, the boards as first placed, both Blues present | repeat, 12:53, the Pi 3 beside the Pi 4s, Blue 2 unplugged |
|---|---|---|
| Pi 3 cycle in the rate check | 4 714 / 5 043 µs | **2 507 / 2 452 µs** (inside 1.9–2.6 ms) |
| Pi 3 frames sent in 22 s | 4 792 / 4 519 | **8 912 / 9 096** |
| pi-A / pi-B | 1 946.6 / 1 945.6 µs | 1 944.0 / 1 945.8 µs |
| background | 0.091 % | 0.091 % |

**The decay test, repeated identically** (nine idle minutes, then eight 10 s runs, the Pi 3 alone
in the cell):

| run | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 04:21, frames/s | 266 | 232 | 216 | 208 | 197 | 193 | 190 | 183 |
| 13:06, frames/s | 435 | 422 | 429 | 428 | 434 | 442 | 447 | 454 |

The Pi 3 warmed more this time (45.1 → 50.5 °C, against 43.5 → 47.2 °C), yet its rate did not
fall. **"A limit in the radio that tightens with sending and relaxes with rest" is therefore
wrong.** What held the Pi 3 back was outside it. Two things changed together: the Pi 3's place
(now beside the Pi 4s, with Blue 1 farther away) and Blue 2 (unplugged). Which one mattered was not
tested, and will not be: Mohamed will not use Blue 2, which does the same as Blue 1. Rested and alone, the BCM43430 sends a
frame every 2.20–2.37 ms, close to the standard's 2.22 ms.

**What still stands.**
* S0's failure is a fact, and so is the stop rule. Any further session needs a new registration.
* The Blues' empty captures and the Pi 4's results stand.
* The rate check did its job. A disturbance that made one station defer left the background
  untouched: 0.09 % in both sessions, because a deferring sender loses nothing; it only sends
  less. Only the single-sender rate check could see it.

F122.
