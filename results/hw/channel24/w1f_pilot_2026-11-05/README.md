# W1f pilot: two windows through node 4's new script and the full launch chain. 2026-11-05 21:39, disclosed, not scored

Run after the registration (`prereg-W1f`, `cd85eeb`) and before the session, as W1f's disclosure
says.
* **Boards.** All four in the W1f placement (side by side, 10–15 cm), Blue 2 on its 5 V adapter
  and freshly rebooted (boot `9f10fcb1`).
* **Plan** (`node1/plan_w1f_pilot.txt`): `R4 600 145 4`, `B4 50 145 4`. Header `# nodes: 1,2,3`.
* **Kits.** The Pis ran `hw/channel/run_window_plan.sh`; node 4 ran
  `hw/channel/run_window_plan_tplink.sh`. Every hash matched the repo.

**What it showed**
* **The cell formed.** The Pis' peer checks found one another. Node 4 joined the Pis' cell
  (BSSID `16:8b:a4:5a:6e:94`, not the driver's own `02:11:87:…`) and reached all three Pis.
* **The rate stayed fixed.** `rate_ctl` read `FIXED CCK_1M 0x00 0` at join, in both windows' `ctr`
  files and at the end. The boot ID was unchanged; `tx_dropped` was 0.
* **The reducer took all four boards' files** (`analysis/dsss_w1f.py`, `window_rows` and
  `apply_node4_rules`): both windows complete, `node4_ok`.
  * R4: the TP-Link's cycle was **1 962.3 µs**; loss 0.26 % at the three Pis.
  * B4: loss 0.15 %.
* **Every board reverted.** The Pis returned to the LAN at 21:40:30, Blue 2 at 21:40:43, with no
  reset.

The kit and the analysis chain work end to end. Nothing here is scored.
