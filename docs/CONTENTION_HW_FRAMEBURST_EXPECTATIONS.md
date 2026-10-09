# Frame burst — a follow-up to the two-board contention run, written BEFORE its runs

*Written 2026-10-09, after the registered two-board run and one control, and before any run
with frame burst switched off. Open item G4.*

## What the registered run found

`docs/CONTENTION_HW_EXPECTATIONS.md`, commit `456a4e7`. Two Raspberry Pi 4 in one ad-hoc cell,
channel 36, every board sending and receiving, twelve windows, all twelve usable (no frame
dropped before the air, every sender at its rate, none late, no receiver-buffer loss).

| frames/s per board | occupancy | measured loss | predicted | registered band | |
|---|---|---|---|---|---|
| 124 | 0.50 | 0.293 % | 0.293 % | 0.185–0.401 % | inside, 1.00× |
| 174 | 0.70 | 0.513 % | 0.641 % | 0.394–0.888 % | inside, 0.80× |
| 211 | 0.85 | 0.641 % | 1.397 % | 0.848–1.947 % | **outside, 0.46×** |

**The load-bearing prediction failed at the highest load.** Loss does rise with load, as
predicted. The two directions lose nearly the same number of frames in every window (30 and
34, 79 and 78, 112 and 126 over the three loads): frames are lost in pairs, which is what a
collision between two half-duplex radios does. The error cannot be a counting artifact in the
measurement's favour: a receiver cannot count a frame that did not arrive.

The registration's reading of this outcome was "the boards do not send when asked, or their
backoff differs from the standard's". The first is excluded by the window conditions.

## What was found on looking — after the data, and labelled so

1. **The spacing of one sender's frames is not the standard's, and August's own files show
   it.** With one saturated sender, the receiver's timestamps give the time from one frame to
   the next: the sequence numbers spanned, over the time from the first frame received to the
   last. August 2026: 2018.6 µs and 2019.1 µs (the 600 and 900 frames/s windows). The control
   run of today, same script, same boards: 2018.9 µs. The frame itself is 1976 µs on air, so
   **the gap between two frames is about 43 µs.** IEEE 802.11 requires DIFS (34 µs) and then
   a counter drawn from 0…15 slots of 9 µs — **101.5 µs on average**, a cycle of 2077.5 µs.
   This radio does not draw that counter between its own consecutive frames.
2. **The driver switches a vendor mode on.** `brcmf_config_dongle()` in the Linux driver sets
   the firmware's frame-burst mode to 1 whenever it configures the chip (kernel commit of
   2018-12-13, "brcmfmac: enable frameburst mode in default firmware setting"). Read from the
   firmware on both boards today: 1. In that mode a radio holding several frames sends them
   one behind another without contending again.
3. **This is known of commercial cards.** Bianchi, Di Stefano, Giaconia, Scalia, Terrazzino
   and Tinnirello (INFOCOM 2007) measured exactly this quantity — the time between a saturated
   card's consecutive frames — on six cards and found that none followed the standard's
   backoff.
4. **Today's link loss is not the cause.** The control (one sender, 100 frames/s, eight
   windows): 17 600 of 17 600 delivered; August had 17 596.

⚠️ **A correction this forces whatever the follow-up shows.** August's result "airtime 1.995 ms
against 1.99 ms predicted, 0.36 %" compared two wrong numbers that happened to agree. The
1.995 ms was the sender's own rate, which counts frames still queued when it stops; the air
carried one frame per 2.019 ms. The 1.99 ms left the frame's headers out and assumed the
standard's backoff. It is written up as a finding of its own.

## The hypothesis

With frame burst off, this radio follows the standard's access rule, and both measurements land
where the standard's rule puts them. With it on, a board that has two or more frames queued —
common at high load, rare at low load — sends them without a new contention, so fewer
contentions happen per frame and fewer frames collide. That is why the model was right at
occupancy 0.50 and twice too high at 0.85.

## The runs, in this order

Frame burst is switched with `hw/channel/frameburst.sh` after the cell has formed; the value
the firmware reports is logged before the first window and after the last.

| run | what | frame burst |
|---|---|---|
| R1 | the registered two-board session, unchanged: 124, 174, 211 frames/s, four windows each | **off** |
| R2 | August's one-sender session, unchanged (`run_adhoc_sweep.sh`) | **off** |
| R3 | the registered two-board session again | on (the driver's setting, logged) |

R3 comes last on purpose: if the room or the boards drifted during the session, the repeat
of the first run shows it.

## The predictions

**P1 — one sender, frame burst off (R2).** The time from one frame to the next in the two
saturated windows, from the receiver's timestamps, is **2.070–2.095 ms** (477–483 frames/s on
air). The standard's rule gives 2.0775 ms; with the inter-frame space of the best-effort
class, one slot longer, 2.0865 ms. With frame burst on it is 2.019 ms.

**P2 — two boards, frame burst off (R1).** The predictions and the bands registered in
`456a4e7`, unchanged:

| frames/s per board | predicted loss | band |
|---|---|---|
| 124 | 0.29 % | 0.185–0.401 % |
| 174 | 0.64 % | 0.394–0.888 % |
| 211 | 1.40 % | 0.848–1.947 % |

At two boards the model is 9–18 % above ns-3 (stated in the first registration); the values
are expected nearer ns-3's — 0.25 %, 0.54 %, 1.27 %.

**P3 — the repeat with frame burst on (R3)** agrees with the first run within twice the
standard error of a difference, taking frames as lost in pairs: 124: 0.15–0.44 %;
174: 0.35–0.68 %; 211: 0.47–0.81 %. In particular 211 frames/s stays below 0.848 %.

**P4 — the contrast.** At 211 frames/s, loss with frame burst off is at least 1.5 times the
loss with it on (expected: about 2).

Window conditions as registered: nothing dropped before the air, every board at 98 % of its
rate or more, under 1 % of frames a whole period late.

## What each outcome means

| outcome | reading |
|---|---|
| P1, P2 and P4 hold | With the vendor mode off the standard's rule describes this radio, at two boards. The first run's miss is the vendor mode. The simulated capacities remain those of the standard's rule; what a radio with frame burst does at capacity is **not** measured here and is said so |
| P1 holds, P2 fails at 211 | Frame burst changes one sender's spacing and is not why two boards collide less. The model is too high at two boards at high load for a reason not yet found; reported as that |
| P1 fails (spacing stays near 2.019 ms) | The switch does not act on broadcast frames, or the spacing has another cause. Nothing follows about the model; the first run's miss stays unexplained |
| P3 fails | Something changed between sessions. Every comparison made today is then suspect, and the day is repeated |

## What this cannot show

* The firmware is closed. What "frame burst" does inside it is inferred from a mean spacing;
  no single frame is timed.
* One chip (BCM4345/6, firmware 7.45.265), one band, one room, two boards.
* It says nothing of a capacity. With frame burst on, a radio behaves unlike the standard at
  high load; whether a cell of such radios has a higher or lower capacity than the simulated
  one is a different experiment, with many more boards.

## Disclosure

The hypothesis was formed **after** the first run's data were seen. Nothing in this file was
measured with frame burst off: no such run existed when it was committed. P2's bands are the
ones registered before any data; P1's and P3's were chosen today.

Changes to the kit since the first registration, none of which touches what a window measures:
`revert_adhoc.sh` asks for whichever network profile the interface has where `preconfigured`
does not exist (one board had been re-installed with a newer system) and restores frame burst;
the launch line no longer keeps the terminal waiting; both session scripts take the frame-burst
setting as an optional last argument and log the firmware's value. On the re-installed board
the session is started as root through `systemd-run`, because `sudo` there asks for a
password; the script is the same file.
