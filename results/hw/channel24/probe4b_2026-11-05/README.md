# Probe 2 of the TP-Link as node 4 — see `../probe4_2026-11-05/README.md`

`node4/blue_probe.sh` is probe 1's script with one addition: a window labelled `F…` fixes the rate at
1 Mb/s first (`iwconfig wlan1 rate 1M fixed`), and the revert sets it back to `auto`.
Plan `node4/plan_probe4b.txt`: `X4 2000 145 4` (its own rate), `F4 1000 145 4` (after the fix).
