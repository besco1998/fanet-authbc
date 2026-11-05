# W1f — four ad-hoc radios at 2.4 GHz: the capacity ratio of AUTHBC and per-record signing, measured on hardware

*Registered 2026-11-05, before the session. Main open item W1 (`docs/OPEN_ITEMS.md` §2a). Mohamed
chose this ("do 1 plan for it correctly then excecute the plan", 2026-11-05) after F126; the plan
was approved in plan mode. Code, plan and predictions at this commit:
* `analysis/dsss_w1f.py`, which imports, unchanged:
  * `analysis/dsss_hardware.py` (W1c's model and designs, `prereg-W1c`);
  * `analysis/dsss_three.py` (W1d's reducer and rules, `prereg-W1d`);
* `experiments/channel24/plan_w1f.txt`;
* `results/raw/w1f_predictions.csv` (config hash `b1494d53bcbbc733`; a second run is
  byte-identical);
* the kit:
  * `hw/channel/run_window_plan.sh` for the Pis, unchanged since W1d;
  * `hw/channel/run_window_plan_tplink.sh` for node 4, new.*

## Why

* **The paper's capacities are simulated.** W1c designed the hardware measurement of the
  AUTHBC / per-record ratio with five boards.
* **That route closed twice.**
  * The Blues have no ad-hoc mode (F120).
  * With three radios the crossing lies in overload, so W1e tested only the contention model
    (11 of 12 points, F123).
* **The fourth station now exists.** It is the TP-Link TL-WN722N on Blue 2, under the community
  driver with `rate_ctl` fixed at 1 Mb/s.
  * It saturates at 1 963–1 964 µs, against the Pi 4s' 1 945 µs, and waits rather than drops
    (F125).
  * It reproduced within 2 µs in replay 3 (F126).
* **With four boards, both crossings lie at an offered load near 0.90, below overload.** The
  ratio can be measured.

## Stations, room, supply

| node | board | radio |
|---|---|---|
| 1 | pi-A, Raspberry Pi 4 | BCM4345/6, brcmfmac |
| 2 | pi-B, Raspberry Pi 4 | BCM4345/6, brcmfmac |
| 3 | Raspberry Pi 3 Model B | BCM43430/1, brcmfmac |
| 4 | BeagleBone Blue 2 + TP-Link TL-WN722N | RTL8188EUS, aircrack-ng/rtl8188eus `af3bf004`, `rate_ctl` `0x00 0` (1 Mb/s, no fallback) |

* **The cell.** Channel 11 (2 462 MHz, clear of the home router on channel 1), 802.11b at 1 Mb/s,
  ad-hoc cell `authbc-mesh`.
* **Placement as W1e.** Side by side, 10–15 cm apart, same height, antennas unobstructed. Blue 2
  and its adapter are placed beside the Pis by Mohamed before the session.
* **Supply.** Blue 2 runs on its 5 V micro-USB adapter, the one probe 3 ran on. It has a hardware
  watchdog (30 s) and reboot on panic (F126).
* **Node 4 joins, never founds.** Its driver joins or creates by its stale scan list
  (`rtw_do_join`, F126), so Blue 2 is rebooted just before the session. Node 4 joins 40 s before
  the first window, after the Pis have formed the cell.
* **The Pis' early peer check names only nodes 1–3** (the plan's header). Their script would
  abort on a peer that joins later; node 4's own pings are checked instead (V3).

## The session (`plan_w1f.txt`): 78 windows, about 40 minutes, in this order

1. **R1–R4.** Each board alone, offered 600 frames/s of 145 B: the bracket, before.
2. **N = 4 contention.** All four at W1c's registered rates, 65 / 91 / 111 frames/s each (occupancy
   0.50 / 0.70 / 0.85), 145 B. Four windows each, then a control.
3. **Capacity-equivalent.** All four at f_b = (N_eq − 1)·f₀/3, which is A12's mapping inverted for
   four boards (each board contends with the load of N_eq − 1 nodes).
   * The two designs alternate, each in ascending load, so that a drift in the room falls on both:
     A24, P7, A27, P8, A29, P8.5, A30, P9, A31, P9.5, A32.
   * A = AUTHBC: 145 B UDP, f₀ = 12.5. P = per-record: 118 B UDP, f₀ = 50.
   * Four windows each, then a control.
4. **R1–R4 again:** the bracket, after.

* **Controls:** one sender at 50 frames/s, rotating over nodes 1–4.
* **Everything else is W1e's:** windows of 25 s, senders sending 22 s, starts 30 s apart on one
  shared clock; each frame at an instant drawn anew in its period; receivers bound before senders
  start.

## Predictions (`analysis/dsss_w1f.py --predict`)

**N = 4 contention: W1c's registered rows, unchanged (band 0.3–1.4×):**

| frames/s per board | 65 | 91 | 111 |
|---|---|---|---|
| model loss | 0.665 % | 1.506 % | 3.184 % |

**Capacity-equivalent, four boards** (event model as W1c: `dcf_own_queue` with W1b's rule,
802.11b, 30 seeds × 20 s). Delivered fraction V at each point:

| AUTHBC N_eq | 24 | 27 | 29 | 30 | 31 | 32 |
|---|---|---|---|---|---|---|
| f_b (frames/s) | 95.8 | 108.3 | 116.7 | 120.8 | 125.0 | 129.2 |
| offered load | 0.734 | 0.829 | 0.893 | 0.925 | 0.957 | 0.989 |
| V | 0.9828 | 0.9722 | 0.9569 | 0.9431 | 0.9230 | 0.8964 |

| per-record N_eq | 7 | 8 | 8.5 | 9 | 9.5 |
|---|---|---|---|---|---|
| f_b (frames/s) | 100.0 | 116.7 | 125.0 | 133.3 | 141.7 |
| offered load | 0.679 | 0.792 | 0.849 | 0.906 | 0.962 |
| V | 0.9856 | 0.9760 | 0.9658 | 0.9474 | 0.9126 |

**Crossings of V = 0.95 and the ratio:**

| | model, four boards | band |
|---|---|---|
| AUTHBC | **29.50** | 26.55–32.45 |
| per-record | **8.93** | 8.04–9.82 |
| **ratio** | **3.304** | **2.974–3.635, and above 2.5** |

**Reported, not scored.** The same model with N_eq real nodes, each at the design's own rate,
crosses at 31.12 (AUTHBC) and 9.65 (per-record). W1b's ns-3 gave 31.05 and 9.72. Four boards
stand 5–7 % below many nodes on each design, and the ratio moves less (3.30 against 3.23).

## Definitions (W1c's, with two rules for node 4)

* **Delivered fraction of a window:** frames received over frames sent × (N − 1), summed over
  every ordered pair of the window's senders.
* **A window is usable** if:
  * no frame was dropped before the air;
  * every sender reached 98 % of its rate, and at most 1 % of its frames were late;
  * no Pi lost voltage;
  * **every node's files are present;**
  * **node 4 was on the session's first boot before and after the window** (its boot ID), in a
    cell not its own (BSSID not `02:11:87:…`, the driver's own-cell signature, `core/rtw_mlme.c`
    l. 518), with `rate_ctl` reading `FIXED CCK_1M`.
  * A reset of Blue 2 therefore makes that window and every later one unusable.
* **Points.** A point is scored only with at least three usable windows. Unusable windows are
  reported, never replaced.
* **Background b** is the mean loss of the usable control windows. Contention loss is compared
  after subtracting b, and V after dividing by 1 − b (W1c-3).
* **The hardware crossing** is interpolated at V/(1 − b) = 0.95 over the scored points
  (`interpolated_crossing`, as W1c). If the measured curve does not cross 0.95 inside the grid,
  the crossing is **not determined**; it is reported, never extrapolated. A bootstrap interval is
  reported, not scored. Note that AUTHBC's band reaches 32.45, beyond the grid's last point (32).

## Validity: the session is void if any of these fails

Its points are then reported and not scored.

* **V1, the bracket.** All eight rate checks are present, each cycle within 1.9–2.6 ms, and no Pi
  lost voltage.
* **V2, the background.** b ≤ 1 %.
* **V3, node 4 in the Pis' cell.** At join its BSSID is not `02:11:87:…`, and it reached nodes
  1, 2 and 3 by ping.
* **V4, 1 Mb/s.** `rate_ctl` read `FIXED CCK_1M` at join. Every window then checks it again.

## Scored as

* **W1f-1:** the bracket (V1).
* **W1f-2:** the background (V2).
* **W1f-3:** N = 4 contention. At each of the three rates, the mean loss of the usable windows
  minus b lies in its band.
* **W1f-4:** each design's hardware crossing lies within ±10 % of the model's four-board crossing.
* **W1f-5 — the claim:** the hardware ratio lies within 2.974–3.635 (±10 % of 3.304), and above
  2.5.

## My expectations `[agent]`

* **W1f-1 holds:** the Pi 4s run near 1 945 µs and the TP-Link near 1 963 µs. The Pi 3 is the
  nearest to the band's top (2.29–2.36 ms in W1e), so a void session is possible, and I state it
  now.
* **W1f-2 holds** (0.17 % in W1e).
* **W1f-3:** at 0.50, W1e's excess at low load (1.16–1.44× in every group) may put the point above
  1.4×. At 0.70 and 0.85 I expect it to hold.
* **W1f-4 holds for both designs.** Near the crossings the load is about 0.9, where W1e ran
  0.81–1.06× of the model.
* **W1f-5 holds.** Both designs run on the same boards in the same room, interleaved. A common
  departure moves both crossings.
* **A Blue 2 reset** (one in 26 exits so far, cause undetermined) has struck only after the
  windows. If one comes mid-session, the boot rule removes the windows from then on.

## What each outcome means

| outcome | meaning |
|---|---|
| valid, W1f-4 and W1f-5 hold | **the AUTHBC / per-record capacity ratio measured on four real radios of three chip families**, at 802.11b, matching the model with nothing fitted; with W1a/W1b, the ratio is robust to the radio and the PHY |
| W1f-5 holds, W1f-4 misses | the absolute crossings on these radios depart from the model, but the ratio (the paper's claim) does not |
| W1f-5 fails | the ratio on real radios differs from the model's: reported plainly, and the paper's claim is limited to simulation |
| a crossing not determined | the measured curve stays on one side of 0.95 inside the grid; the ratio is not measured by this session |
| void | a bracket, background or node-4 condition failed; nothing is scored, and a re-run needs a new registration |

## What it cannot show

* **The paper's PHY.** This is 802.11b at 1 Mb/s, not 802.11a at 6 Mb/s.
* **Many nodes.** Four boards stand for many through A12's mapping. In the model, four-board
  crossings lie 5–7 % below many-node ones (above). Five boards were checked in ns-3 (W1b); four
  were not. The hardware measures the four-board curve.
* **Equal received power.** Three chip families and two drivers are mixed, and capture is limited
  only by the placement.
* **Repeatability.** It is one session.

## Disclosure

* **Already run on these boards today:**
  * probes 1–3 of the TP-Link (F124, F125);
  * the diagnostic runs after probe 3: tests 1–2, replays 1–3, two 10-cycle loops (F126). In them
    the TP-Link's saturated cycle was seen at 1 962–1 964 µs, and at 2 006–2 011 µs when it had
    founded its own cell;
  * W1d and W1e, whose results are known.
* **Known before registering:** Blue 2 reset once in 26 exits from ad-hoc mode, cause undetermined
  (F126).
* **How the grid was chosen:** a coarse run of this model (5 seeds) located the four-board
  crossings and the overload limit, and the grid was set to bracket them below overload.
* **To run after this registration**, disclosed and not scored: a two-window pilot (R4, B4) through
  the new node-4 script and the full launch chain.
* **No capacity-equivalent window and no N = 4 contention window has ever been run on these
  boards.**
