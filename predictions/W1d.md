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
