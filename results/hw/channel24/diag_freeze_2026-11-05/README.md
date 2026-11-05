# Blue 2 after probe 3: the diagnosis. 2026-11-05, 19:05–20:30, disclosed, nothing measured (F126)

Mohamed: "intensively find why". He approved a hardware watchdog and reboot on panic for it
("Watchdog on, diagnose"). The question was why Blue 2 went off the LAN after probe 3
(`../probe4c_2026-11-05/`). **Answer: it did not freeze. Its revert succeeded, the board reset
seconds later, and the iwd start-up race (fixed in F125) kept it off the LAN for about
77 minutes.** Probe 3 ran on a **5 V micro-USB adapter** (Mohamed). The reset did not recur in
25 later exits, 11 of them on that adapter, so **its cause is undetermined** (F126, second
addendum).

## Evidence (`blue2/`)

* **`journal_probe3_end_boots_power.txt`**
  * The last 60 entries of probe 3's boot (`8fe1d97c`). The revert's radio reconnects, DHCP
    follows, and the time server is reached at **17:38:00.448**. Nothing after that: no
    shutdown, no kernel message.
  * Then the list of all boots. `bae4c597` follows probe 3's boot; its clock was restored to
    17:38:00.
* **`power_check.txt`**
  * USB power errors per boot: `VBUS_ERROR` in 2 of 18 boots, at 14:39:38 and 19:03:06.
  * The TPS65217 status, 0x84: USB input present, 12 V input absent (the board is now on the
    PC's USB).
  * ADC channels 5 and 6 (taken to be the battery and the jack; mapping not verified): 0.
* Boot `bae4c597`'s iwd lines, read on the board: "No default interface for wiphy 1" at 59.6 s,
  the radio's interface at 59.8 s. It was never connected; 730 entries, the last at 2 377 s.

## The tests, all on the PC's USB power, all exits clean (boot ID unchanged after each)

| test | what | file |
|---|---|---|
| 1 (19:47) | Blue alone, own radio on the LAN; creates a cell, rate fixed, exit with 3 s between steps | `blue2/diag_exit_t1_lan.log` |
| 2 (19:49) | as 1, with iwd stopped and the own radio down, as in probe 3 | `blue2/diag_exit_t2_probe.log` |
| replay 1 (19:58) | probe 3's plan with both Pis (`replay/`), who stay in the cell during the exit; 3 s between steps. **The TP-Link created its own cell (`02:11:87:…`); not faithful** | `blue2/replay.log`, `blue2/kern.log` |
| loop (20:03) | 10 cycles: Blue alone, saturated sending for 10 s, probe 3's exit back to back (1.9 s) | `blue2/loop.log`, `blue2/kern_loop.log` |
| **replay 2 (20:21)** | **faithful:** fresh boot, the TP-Link **joined** the Pis' cell (`be:6c:1c:…`); pace 516.9 frames/s (probe 3: 516.6); exit back to back in 2.3 s; the Pis in the cell | `blue2/replay2.log`, `blue2/kern2.log`, `replay2/` |

### Then on the 5 V adapter (Mohamed reset Blue 2 onto it, about 20:53)

| test | what | file |
|---|---|---|
| boot `8beb5ee8` | the TP-Link enumerated at 7.0 s, no VBUS error | `blue2/power_check_adapter.txt` |
| **replay 3 (20:56)** | as replay 2: joined the Pis' cell (`c2:1f:e7:…`), cycle 1 961.9–1 962.8 µs, exit back to back; no reset | `blue2/adapter_replay3*.log`, `adapter_replay3/` |
| loop (21:00) | 10 cycles as above; no reset, no VBUS error | `blue2/adapter_loop*.log` |

**Tally: one reset (probe 3) in 26 exits; 1 of 12 on the adapter, 0 of 14 on the PC's USB
(Fisher p = 0.46). The supply is not shown to be the cause; the cause is undetermined (F126,
second addendum).**

Scripts: `scripts/`. The launchers are not kept, because they hold the Blue's password. Each test
was started as a systemd unit on the Blue, and the Pis ran `hw/channel/run_window_plan.sh` with
`scripts/plan_replay_pis.txt` at one shared start time.

## Found on the way

* **Join or create** (`rtw_do_join`, `core/rtw_ioctl_set.c`, l. 99–151):
  * an empty scan list makes the driver scan, then join;
  * a stale list makes it create a cell without scanning.

  That is why replay 1 was not faithful. The driver ignores a BSSID passed to `iw ibss join`.
* **A creator-path defect.** The driver reports channel 0 on its first created cell after boot.
  It reads the channel (`ioctl_cfg80211.c`, l. 964) before filling it in (l. 979), and
  `cfg80211_ibss_joined` warns (`net/wireless/ibss.c`, l. 69). This was seen in test 1.
* **Alone in its own cell, the TP-Link accepted 1 000 frames/s with the rate fixed** (loop). So
  it was not sending at 1 Mb/s there, or not sending at all. With peers it always paced at 1 Mb/s.
* **Replay 1's TP-Link cycle was 2 006–2 011 µs**, against probe 3's 1 963–1 964. The likely
  cause is the instrumentation sharing the Blue's one core (kernel-log streaming, a sync every
  second). Replay 2, with the same instrumentation, paced as probe 3 did, so this is not settled.
  Diagnostic only.

## Settings left on Blue 2

* The hardware watchdog (30 s, `/etc/systemd/system.conf.d/authbc-watchdog.conf`).
* Reboot on panic and on soft lockup (`/etc/sysctl.d/90-authbc-panic.conf`).
* `i2c-tools` installed.

`scripts/fix_watchdog.sh` says how to undo them.
