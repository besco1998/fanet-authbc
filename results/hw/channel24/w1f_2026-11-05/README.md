# W1f session: four ad-hoc radios at 2.4 GHz, channel 11. 2026-11-05, 21:46–22:25 (registered at `prereg-W1f`, `cd85eeb`)

Nodes:
* `node1/` pi-A, `node2/` pi-B (Raspberry Pi 4, BCM4345/6);
* `node3/` Raspberry Pi 3 (BCM43430/1);
* `node4/` the TP-Link TL-WN722N (RTL8188EUS) on BeagleBone Blue 2, community driver, `rate_ctl`
  1 Mb/s.

Placement: side by side, 10–15 cm (Mohamed). Blue 2 on its 5 V adapter, freshly rebooted (boot
`b3f826e2`).

**How it ran**
* **The plan** is `experiments/channel24/plan_w1f.txt` (sha `19ae903ea17e`): 78 windows.
* **The kits** matched the repo by hash on all four boards: the Pis ran
  `hw/channel/run_window_plan.sh`, node 4 ran `hw/channel/run_window_plan_tplink.sh`. A two-window
  pilot came first (`../w1f_pilot_2026-11-05/`).
* **Node 4** joined the Pis' cell (`meta_node4_join.json`: BSSID `2a:59:a9:66:b4:cb`), reached
  all three Pis, and read `FIXED CCK_1M` at join, in every window and at the end. Its boot ID was
  the same in every window and after the session (`node4/boot_after_session.txt`), so there was
  no reset.
* **Every board ran all 78 windows and reverted to the LAN.**

**Scored by `analysis/dsss_w1f.py --score`, unchanged since registration**
* Outputs: `../w1f_2026-11-05_windows.csv` (per window) and `results/raw/w1f_w1f_2026-11-05.csv`
  (the score).
* All 78 windows are complete; all 56 multi-sender windows are usable. There were no late frames
  and no drops, every sender ran at ≥ 99.99 % of its rate, and there was no under-voltage.
* A re-score is byte-identical. b, A29, R1's cycle and the AUTHBC crossing were recomputed by an
  independent script from the raw files, and agree to the fourth decimal.

**Reported, not scored** (`analysis/sender_receiver.py`, output in `analysis/sender_receiver.txt`):
the loss of every ordered (sender, receiver) pair. **Loss depends on the sender, not the
receiver**, at every load:
* at A32: pi-A's frames are lost at 8.31 %, pi-B's at 7.74 %, the Pi 3's at 4.94 % and the
  TP-Link's at 1.48 %, nearly equally at each receiver;
* at 65/s the order is the same (1.01 % for pi-A against 0.36 % for the TP-Link).

This is what capture by the stronger sender produces; transmit power and antenna gain were not
measured (F127).
