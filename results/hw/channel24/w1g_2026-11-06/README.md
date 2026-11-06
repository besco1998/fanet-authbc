# W1g session: four radios, balanced setup, the grid moved. 2026-11-06, 03:48–04:12 (registered at `prereg-W1g`, `26f3ba8`). VOID

Setup:
* the Pis side by side, as in W1f;
* Blue 2 with its TP-Link at 90 cm from them, on its 5 V adapter, freshly rebooted (boot
  `17618a71`, unchanged after the session: `node4/boot_after_session.txt`);
* pi-B held at 8 dBm (`node2/txpower.log`).

Plan: `experiments/channel24/plan_w1g.txt` (sha `df6c363d362d`), 48 windows. All kits matched the
repo by hash.

**How it ran**
* Every board ran all 48 windows and reverted.
* Node 4 joined the Pis' cell (`aa:69:5b:4c:da:61`) at `FIXED CCK_1M`.
* Scored by `analysis/dsss_w1g.py`, unchanged: `../w1g_2026-11-06_windows.csv`,
  `results/raw/w1g_w1g_2026-11-06.csv`.
* An independent script recomputed the score from the raw files and agrees.

**VOID**
* **V5 (balance) failed: spread 5.08× at A31.** The TP-Link dominated at every point
  (`analysis/sender_receiver.txt`): its frames were lost at 0.8–1.2 %, the Pis' at 3.0–7.1 %.
  * Its reception of the Pis was as in calibration run 3; only its sending changed.
* **V1 (bracket) failed:** the Pi 3 after the session read 2 779.6 µs (band ≤ 2 600).

Neither curve crossed 0.95 inside the grid (A32 0.952, P9.75 0.951). F128.
