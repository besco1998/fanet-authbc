# Two radios contending — the sessions of 2026-10-09

*Findings F73–F76 in `docs/audits/model_provenance.md`. Three registrations, each committed
before the runs it predicts: `456a4e7`, `06f1bfa`, `9a85afa`
(`docs/CONTENTION_HW_*_EXPECTATIONS.md`). This file is the record of what was run; the
findings say what it means.*

## The boards

| | node | address in the cell | what it is |
|---|---|---|---|
| pi-A | 1 | 10.0.0.1 | Raspberry Pi 4 B rev 1.5, **re-installed since August**: Debian 13, kernel 6.18, Python 3.13 |
| pi-B | 2 | 10.0.0.2 | Raspberry Pi 4 B rev 1.4, as in August: Debian 12, kernel 6.12, Python 3.11 (system) |

Both radios: BCM4345/6, firmware 7.45.265 of 2023-08-29. Ad-hoc cell on channel 36 (5180 MHz),
20 MHz, broadcast at 6 Mb/s, 1400 B of UDP payload. No other 5 GHz network was visible in a
scan before the first session; the house access point is on 2.4 GHz. CPU governor
`performance` on both for the sessions; receive buffers of 8 MB or more granted on both; the
kernel's UDP error counters did not move on either board in any session
(`sessions_2026-10-09/`).

## The sessions, in the order they ran (times UTC)

| start | what | frame burst | raw files | reduced |
|---|---|---|---|---|
| 00:36 | probe: one window at 124 frames/s | on, not logged | `contention_2/probe/` | — (7 lost of 2976) |
| 00:39 | **the registered session**: 124, 174, 211 frames/s, four windows each | on, not logged | `contention_2/node{1,2}/` | `contention_2nodes.csv` |
| 00:51 | control: August's one-sender session | on, not logged | `one_sender_fb_on_2026-10-09_pi-{a,b}/` | `one_sender_fb_on_2026-10-09.csv` |
| 01:05 | R1: the registered session | **off**, logged | `contention_2_fb_off/` | `contention_2nodes_fb_off.csv` |
| 01:13 | R2: the one-sender session | **off**, logged | `one_sender_fb_off_2026-10-09_pi-{a,b}/` | `one_sender_fb_off_2026-10-09.csv` |
| 01:21 | R3: the registered session, repeated | on, logged | `contention_2_fb_on_repeat/` | `contention_2nodes_fb_on_repeat.csv` |
| 01:30 | S1: both offered 400 frames/s | **off**, logged | `saturated_2_fb_off/` | `saturated_2nodes_fb_off.csv` |
| 01:35 | S2: both offered 400 frames/s | on, logged | `saturated_2_fb_on/` | `saturated_2nodes_fb_on.csv` |

`frame_spacing.csv` holds the one-sender spacing of August and of both one-sender sessions
above. Each `*_windows.csv` holds every window; nothing is averaged before it is written.

## How a session was started

```bash
START=$(( $(date +%s) + 60 ))
# pi-B, as analysis/contention_hw.py --commands prints it
ssh pi@<pi-b> "nohup setsid /home/pi/authbc_channel/run_adhoc_contention.sh 2 2 $START 124,174,211 5180 full [keep|0] >/dev/null 2>&1 </dev/null &"
# pi-A: sudo asks for a password there, so the same script was started as root
ssh pi@<pi-a> "sudo systemd-run --unit=authbc-session-$START --collect /home/pi/authbc_channel/run_adhoc_contention.sh 1 2 $START 124,174,211 5180 full [keep|0]"
```

The one-sender sessions use `run_adhoc_sweep.sh tx|rx $START 5180 full [keep|0]` the same way.
Every session reverted by itself and disarmed its two safety timers; no timer fired.

## What changed in the kit during the night

Each change is in the registration that followed it. None alters what a window counts.

* `revert_adhoc.sh` — asks for whichever network profile the interface has where
  `preconfigured` does not exist (Debian 13 names it differently); restores frame burst.
* `frameburst.sh` — new: reads and sets the chip's frame-burst mode.
* both session scripts — an optional last argument for frame burst; the firmware's value is
  logged before and after the windows.
* `bcast_rx.py` — also records the first sequence number heard (from R2 on) and when each
  sender was first and last heard (from S1 on).
* `analysis/contention_hw.py` — the launch line no longer keeps the terminal waiting;
  `--tag` names a second session's files; `--saturated` reduces S1 and S2.

## Reading the numbers

| | measured | the standard's rule |
|---|---|---|
| one sender, link loss at 100 frames/s | 0 of 17 600 (August: 4 of 17 600) | — |
| one saturated sender, per frame | 2.019 ms on, 2.050 ms off | 2.078 ms |
| two boards at occupancy 0.50 / 0.70 / 0.85, 36 windows | 0.33 / 0.50 / 0.78 % | model 0.29 / 0.64 / 1.40 %; ns-3 0.25 / 0.54 / 1.27 % |
| two saturated senders, frames on air lost | 12.4 % off, 12.1 % on | 11.8 % |
| two saturated senders, frames/s on air each | 263 off, 265 on | 260 |

⚠️ One sender alone already loses 0.5–0.9 % of the frames its receiver spans once it is
saturated, and 0.1–0.3 % at 300–400 frames/s, with nobody to collide with. Nothing here
explains that, and nothing was registered about it.
