# W1c — five radios at 2.4 GHz: the hardware campaign's predictions, before any board session

*Registered 2026-11-05. Phase 0 of the 2.4 GHz campaign; main open item W1
(`docs/OPEN_ITEMS.md` §2a). **No board has been switched on for it.** Code and predictions at this
commit: `analysis/dsss_hardware.py`, `results/raw/w1c_predictions.csv`. It rests on W1b (F119): at
802.11b the model predicted ns-3's crossings within 1 %, and five stations stood for many up to
the crossing.*

## Why

The paper's capacities are simulated; on hardware only two radios have contended (F73–F76). The
radios at hand beyond the two Pi 4 are 2.4 GHz only. Five boards at 2.4 GHz give:
* **the contention model against N = 2, 3, 4, 5 real radios**, of three chipsets;
* **the crossing of each design, and so the ratio, measured on hardware.** Five boards stand for
  many nodes up to the crossing, the equivalence W1b checked.

All of it is at **802.11b, 1 Mb/s**, the only broadcast rate a Raspberry Pi can use there (F35).
It is a second PHY, not the paper's. The paper would say so.

## The kit and the room

| node | board | chipset |
|---|---|---|
| 1 | pi-A, Raspberry Pi 4 (re-flashed to Raspberry Pi OS Lite 64-bit Bookworm, as pi-B) | Broadcom BCM4345/6 |
| 2 | pi-B, Raspberry Pi 4 | Broadcom BCM4345/6 |
| 3 | Raspberry Pi 3 Model B (Raspberry Pi OS Lite 64-bit Bookworm) | Broadcom BCM43438 |
| 4, 5 | BeagleBone Blue (Debian 12 IoT, AM335x) | TI WiLink 8 (WL18xx) |

* **Placement.** One ad-hoc cell, the boards on a circle of about 2 m diameter, at the same height,
  antennas unobstructed: equal received power, as the model assumes.
* **Mohamed's home router is off during sessions.** The boards leave the home network for the
  ad-hoc cell in any case (`hw/channel/run_adhoc_contention.sh`), and the router is on 2.4 GHz.
* **Phase 1 adapts the kit before any session**, and none of the changes alters what a window
  counts:
  * a payload option in the session script;
  * per-node rates for the capacity-equivalent windows;
  * the Blues' network setup;
  * the Blues' multicast rate set to 1 Mb/s where their driver allows it.
* **A one-window probe with all five boards** comes first, as for F73.

## The sessions, in order

* **S0 — pilot.**
  * **(a) Rate check.** Each board alone is offered 600 frames/s of 145 B (the AUTHBC frame on air)
    for one 22 s window. Its cycle on air is read at a receiver, from the sequence numbers spanned
    over its own clock (`analysis/frame_spacing_hw.py`'s method).
  * **(b) Background survey** on channels 1, 6 and 11. One board sends 50 frames/s for 22 s and
    one receives; the Pi 3 counts foreign frames if monitor mode works on it. **The channel with
    the lowest loss is used.**
* **S1 — contention.** For N = 2, 3, 4, 5 boards, at occupancy 0.50, 0.70 and 0.85 (F70's
  definition, at 802.11b): 145 B, each frame at an instant drawn anew in its period, four 22 s
  windows per point. A **control window** (one sender alone at 50 /s) after every four windows.
* **S2 — capacity-equivalent.** Five boards at the per-board rate f_b = (N_eq − 1)·f₀/4:
  * AUTHBC frames (145 B UDP, f₀ = 12.5) at N_eq = 22, 26, 30, 34;
  * per-record frames (118 B UDP, f₀ = 50) at N_eq = 6, 7, 8, 9, 10;
  * four windows each, with control windows as in S1.
  * Every point is below overload: the highest offered load is 0.987.

## Definitions

* **Delivered fraction of a window:** frames received over frames sent × (N − 1), summed over every
  ordered pair of boards (the ns-3 definition; `contention_hw.windows`).
* **A window is usable** if no frame was dropped before the air, every sender reached 98 % of its
  rate, and at most 1 % of frames were late (`contention_hw.usable`). Unusable windows are excluded
  and reported, never replaced.
* **A point is scored** only with at least three usable windows.
* **Background b:** the mean loss of the session's control windows. Hardware loss is compared with
  the model after subtracting b (F70 added its measured link loss the same way).

## Predictions (`analysis/dsss_hardware.py`; event model at 802.11b, 30 seeds × 20 s)

**Rate check.** The cycle of one saturated sender under the standard's rule:

| rate | cycle |
|---|---|
| **1 Mb/s** | **2 224 µs** |
| 2 Mb/s | 1 388 µs |
| 5.5 Mb/s | 856 µs |
| 11 Mb/s | 704 µs |

**Contention (loss, model):**

| N \ occupancy | 0.50 | 0.70 | 0.85 |
|---|---|---|---|
| 2 (131 / 183 / 222 frames/s each) | 0.22 % | 0.55 % | 1.43 % |
| 3 (87 / 122 / 148) | 0.45 % | 1.06 % | 2.40 % |
| 4 (65 / 91 / 111) | 0.67 % | 1.51 % | 3.18 % |
| 5 (52 / 73 / 89) | 0.83 % | 1.77 % | 3.79 % |

**Capacity-equivalent (delivered fraction, model, five boards):**

| AUTHBC N_eq | 22 | 26 | 30 | 34 |
|---|---|---|---|---|
| V | 0.9867 | 0.9783 | 0.9594 | 0.8938 |

| per-record N_eq | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|
| V | 0.9900 | 0.9846 | 0.9766 | 0.9594 | 0.9141 |

**Crossings of V = 0.95: AUTHBC 30.57, per-record 9.21; ratio 3.32.** These are five-station
crossings, slightly below the many-station ones (31.05 and 9.72 in ns-3, W1b), as W1b showed.

## Scored as

* **W1c-1 — rate check.** Every board's cycle lies within 1.9–2.6 ms, i.e. at 1 Mb/s.
  **Stop rule:** a board outside it ends the campaign until a new registration.
* **W1c-2 — contention.** At each (N, occupancy), the mean loss of the usable windows minus b lies
  in the model's band: 0.6–1.4× for N = 2, 0.3–1.4× for N ≥ 3 (F70's bands; capture can only
  lower loss with three or more radios).
* **W1c-3 — crossings.** Each design's hardware crossing, interpolated from V/(1 − b) over its
  N_eq grid, lies within ±10 % of the model's: AUTHBC 27.51–33.63, per-record 8.29–10.13.
* **W1c-4 — the claim.** The hardware ratio lies within 2.99–3.65 (±10 % of 3.32), and in every
  case above 2.5.

**Stop rule on background:** b above 1 % on all three channels ends the campaign and is reported;
contention at 1–4 % cannot be read against it.

**Why ±10 %.** At 5 GHz the two radios lost 0.79–1.13 times the model at moderate load (F73).
Where V falls through 0.95, that moves a crossing by a few per cent. ±10 % allows that and
interference. The ratio is held to the same band, because both designs run on the same boards in
the same room.

## My expectations `[agent]`

* **W1c-1** holds for the three Pis (F35). For the Blues it depends on whether their driver honours
  a multicast rate of 1 Mb/s; I expect it to.
* **W1c-2** may fail at N = 2 and occupancy 0.85, below the band. The two Pi 4 hold queues of their
  own there, as at 5 GHz (F73: 0.56×). With three to five boards, each sends less often and the
  bands are wide; I expect those to hold.
* **W1c-3 and W1c-4** hold. The ratio is near 3.3.

## What each outcome means

| outcome | meaning |
|---|---|
| W1c-3 and W1c-4 hold | **the AUTHBC / per-record ratio measured on five real radios** (at 802.11b), matching the model; with W1a/W1b, the ratio is shown robust to the radio, the PHY and the hardware |
| W1c-4 holds, W1c-3 misses | the absolute crossings depart from the model on these radios, while the ratio, the paper's claim, does not |
| W1c-4 fails | the ratio on real radios differs from the model's: reported plainly, and the paper's claim is limited to simulation |
| W1c-2 fails at N ≥ 3 | the access rule on mixed real radios departs from the model; the capacity-equivalent part is then read with that stated |

## What it cannot show

* **802.11b at 1 Mb/s is not the paper's PHY (802.11a, 6 Mb/s).** The capacities measured are
  about a quarter of the paper's.
* **Five boards stand for many through an equivalence checked in ns-3** (W1b), not on hardware:
  the hardware measures the five-station curve.
* Three chipsets, with closed firmware on the Pis. A radio's own-queue handling at about 100
  frames/s per board is not the operating point's (G27).
* **Capture** at 2.4 GHz with five radios, limited only by placement. **Interference**, limited
  only by the survey, the router being off and the control windows.

## Disclosure

* The model predictions were run for this registration.
* W1b's results were known: its crossings, its ratio, and the overload limit that set these grids.
* The 2.4 GHz run of August (F35) used 1400 B frames and measured saturation. Nothing at 2.4 GHz
  has been run since.

---

## Outcome — added 2026-11-05: not run; superseded by W1d. Nothing above this line was changed

**Its premise of five ad-hoc radios is false.** The two BeagleBone Blues were checked on
2026-11-05, before any session:
* their TI WL18xx radios list no IBSS mode (`iw list`);
* the kernel refuses to create an ad-hoc interface on both (`iw phy phy0 interface add ibss0 type
  ibss` → "Operation not supported (-95)");
* mainline `wlcore` has not announced ADHOC since commit 7845af35e0de (2015-07-30), F120.

**Only three ad-hoc radios are available:** pi-A, pi-B and the Raspberry Pi 3 Model B.

**A consequence found while replanning.** A12's mapping holds the contending load fixed, so the
total offered load at the capacity crossing grows as N/(N − 1): 0.88 with five stations, 0.94
with four, **1.06 / 1.05 with three, which is overload.** Three radios cannot measure the capacity
ratio; that waits for a fourth station.

**What survives.** The contention predictions above for N = 2 and N = 3 were registered before
any board session. They are reused unchanged by `predictions/W1d.md`, which runs the 3-radio
campaign.
