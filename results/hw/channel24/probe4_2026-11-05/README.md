# TP-Link TL-WN722N (RTL8188EUS) on BeagleBone Blue 2 as node 4 — engineering probes, 2026-11-05, disclosed, not scored

The adapter is driven by the Blue's kernel staging driver `r8188eu` (5.10.168-ti-r84) through
wireless extensions (`/sbin/iwconfig`); no out-of-tree code. The Blue's own TI radio was taken off
the air for each probe, and a deadman returned it. pi-A (node 1) and pi-B (node 2) formed the cell
on channel 11 with the standard kit (`hw/channel/run_window_plan.sh`).

* **Probe 1** (this folder, 14:46–14:49; `node4/blue_probe.sh`, `node4/plan_probe4.txt`):
  * the TP-Link joined the cell (2.462 GHz, pings both ways);
  * it delivered its offered 600 frames/s with no backlog: cycle 1 666.3 µs = 1/600 s; received
    13 175 / 13 177 of 13 200;
  * at 50 frames/s it lost 0.27–0.45 %;
  * it received 11 263 of pi-A's 11 325 saturated frames (pi-B: 11 188).
* **Probe 2** (`../probe4b_2026-11-05/`, 14:51–14:54):
  * offered 2 000 frames/s, it delivered 2 000 (cycle 499.9 µs, 99.7 % received);
  * after `iwconfig wlan1 rate 1M fixed` (accepted, exit 0), offered 1 000 frames/s, it delivered
    1 000 (cycle 999.7 µs).

  At 1 Mb/s this frame takes 1 864 µs on air. **The adapter broadcasts at least 3.9× faster per
  frame than the Pis**, at an unknown rate (OFDM likely). The kernel driver's rate setting does
  not reach broadcast frames.
