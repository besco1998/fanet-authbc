# Probe 3 of the TP-Link as node 4: community driver, rate fixed at 1 Mb/s. 2026-11-05, disclosed, not scored

Follows probes 1 and 2 (`../probe4_2026-11-05/README.md`, F124). There, the kernel's staging
driver joined the cell but broadcast at least 3.9× faster per frame than the Pis.

## The adapter, the driver and the board

* **Hardware.** TP-Link TL-WN722N (RTL8188EUS) on BeagleBone Blue 2.
* **Driver.** The community driver aircrack-ng/rtl8188eus at commit `af3bf004`, built on the Blue
  (`node4/build_8188eus.sh`, Mohamed's approval: "do it"). `r8188eu` and `rtl8xxxu` are
  blacklisted.
* **The 1 Mb/s setting.** Writing `0x00 0` to `/proc/net/8188eu/tplink0/rate_ctl` fixes every data
  frame, broadcasts included, at 1 Mb/s with no fallback. `CONFIG_PHDYM_FW_FIXRATE` is off, so the
  handler is the `sscanf("%hhx %hhu")` one in `core/rtw_debug.c`.
* **Naming.** The driver option `ifname=tplink0` (`node4/fix_naming.sh`) names the adapter. A udev
  rename lost a boot race: iwd had the link up at 53 s, and udev reached it at 59 s.
* **Who manages what.**
  * iwd runs with `-I tplink0`.
  * systemd-networkd leaves `tplink0` alone (`04-authbc-tplink.network`, `Unmanaged=yes`).
  * The TI radio is matched by MAC address for DHCP.
  * Checked after the reboot: `tplink0` (driver `8188eu`, IBSS and monitor modes), the TI radio
    as `wlan0` at its usual LAN address, `rate_ctl` reading `RA`.

## The session

* 17:36:00–17:37:56. Plan `node4/plan_probe4c.txt` (sha `379cde646ec1`): `F4 1000`, `F4 1000`,
  `B4 50`, `R1 600`, all at 145 B.
* pi-A (node 1) and pi-B (node 2) ran the standard kit. Blue 2 ran `node4/blue_probe_iw.sh`
  (sha `7263843019d3`).
* Expected, stated before the run: if the setting works, a cycle of 1.9–2.6 ms in the saturated
  windows; if not, about 1.0 ms (probe 2).

## What the Pis received from the TP-Link (`node1/`, `node2/`)

| window | receiver | received | sequence range | cycle (span / sequence range) | cycle (span / received) |
|---|---|---|---|---|---|
| 00 F4, 1 000/s offered | pi-A | 11 258 | 0–11 387 | 1 962.9 µs | 1 985.6 µs |
| | pi-B | 11 310 | 0–11 387 | 1 963.0 µs | 1 976.5 µs |
| 01 F4, 1 000/s offered | pi-A | 11 285 | 0–11 386 | 1 964.4 µs | 1 982.1 µs |
| | pi-B | 11 319 | 0–11 386 | 1 964.4 µs | 1 976.2 µs |
| 02 B4, 50/s | pi-A | 1 083 of 1 100 (1.55 % lost) | | | |
| | pi-B | 1 097 of 1 100 (0.27 % lost) | | | |
| 03 R1 (pi-A sending, 600/s offered) | pi-B | 11 192 | 0–11 319 | 1 979.1 µs | 2 001.8 µs |

* **The 1 Mb/s setting reaches the air.** The TP-Link's saturated cycle went from 999.7 µs
  (probe 2) to 1 963–1 964 µs. That lies inside the band and 1 % above the Pi 4s' 1 945 µs
  (W1e).
* **Why the two readings agree.** Offered 1 000 frames/s, the TP-Link numbered only about 11 390
  frames in 22 s. A full queue made the sender wait, as on the Pis, instead of dropping frames,
  so the sequence numbers follow the air's pace.
* **The arithmetic agrees with 1 Mb/s.**
  * At 1 Mb/s this frame takes 1 864 µs on air, and a cycle cannot be shorter than that plus DIFS
    (1 914 µs). The measured 1 963 µs leaves about 2.5 slots of backoff on average.
  * At 2 Mb/s (1 028 µs on air with the long preamble, 932 µs with the short) it would need
    44–49 slots of backoff on average, beyond the first attempt's maximum of 31.
* **What is reported here but not scored:**
  * pi-A lost 1.55 % of the 50/s window against pi-B's 0.27 %. Probe 1, with the kernel driver,
    lost 0.27–0.45 %. This is a single window, so it is noted, not explained.
  * pi-A's R1 cycle, read at pi-B alone, was 1 979 µs. In W1e, read at two receivers, it was
    1 945.8 µs.
* Both Pis: `throttled` 0x0 before and after every window.

## Blue 2's own files (`node4/from_blue/`, copied over the USB link at 19:15)

* **The setting took.** `probe.log` records `rate_ctl now: FIXED CCK_1M 0x00 0` after the join.
  The adapter joined `authbc-mesh` on 2462 MHz and reached both Pis.
* **Sending.**

  | window | sent | late | the driver's `tx_packets` | `tx_dropped` |
  |---|---|---|---|---|
  | 00 F4 1 000/s | 11 388 | 10 918 | 11 388 | 0 |
  | 01 F4 1 000/s | 11 387 | 10 904 | 11 388 (one system frame) | 0 |
  | 02 B4 50/s | 1 100 | 0 | 1 100 | 0 |

  Every frame sent went to the driver, and none was dropped. So the Pis' gaps are losses on the
  air.
* **Window 03, receiving pi-A: lost.** `rx_node4_03…` and `ctr_node4_03…` are 0 bytes, stamped
  17:37:57.

## Blue 2 froze after the windows, in its revert (F125)

* `probe.log` ends in **177 zero bytes**. That equals exactly the three lines written after
  window 03:
  * window 03's receive summary with a five-digit count (58 bytes);
  * `window 03_R1_600fps done` (53);
  * `rate_ctl at end: FIXED CCK_1M 0x00 0` (66).

  No other sequence fits: a four-digit count gives 176, and a reading of `RA` gives 160. The
  script therefore entered its revert, and the next line (after a 25 s pause) never came.
* The deadman logged nothing either.
* A scan from pi-A at 17:52 found no ad-hoc beacons on channel 11.
* **So the board froze while the adapter was being taken out of ad-hoc mode.** The step is
  unknown, because the journal of that boot was truncated by the unclean stop.
* Its hardware watchdog is inactive, and `kernel.panic` is 0, so it stayed frozen until restarted.

**Why it then stayed off the LAN (fixed).**
* The login records show four restarts after 17:31, none with a clean shutdown, and all with a
  2024 date because the clock never reached the network. The last three were at 18:54, 18:58 and
  19:04.
* On each, iwd met the TI radio before its interface existed ("No default interface for
  wiphy 1") and never connected it.
* Mohamed connected the Blue's USB at about 19:05, and its serial console and USB network gave
  access.
* Restarting iwd connected the radio at once.
* **Fix:** `node4/fix_iwd_order.sh` makes iwd start after the radio's interface exists.
* **Verified by a reboot:** back on the LAN by itself at 19:18:49, iwd connected 59 s after boot.

## My error: the Pis' revert script was not deployed

* I copied the kit into `authbc_probe4c/` without `revert_adhoc.sh`, which every earlier folder
  has.
* So `run_window_plan.sh` could arm no revert deadman ("Failed to find executable"), and its own
  revert left the Pis in the cell.
* The reboot deadman returned both Pis at 17:48 with no voltage flags. Nothing a window counted
  was affected.
* **Fix:** launches now deploy the kit by the list of files `run_window_plan.sh` calls, and check
  each exists before starting.
