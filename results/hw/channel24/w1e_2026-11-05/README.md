# W1e session, 2026-11-05 13:34–14:07 — registered at `prereg-W1e` (`2409d36`)

Three Raspberry Pis side by side, 10–15 cm apart, on channel 11: pi-A (node 1), pi-B (node 2), Pi 3
(node 3). Both BeagleBone Blues were unplugged at the start. Kit and plan are identical to the repo
(SHA-256 checked on each board before launch): `hw/channel/run_window_plan.sh`,
`experiments/channel24/plan_w1e.txt`.

* `node1..3/` — each board's `session.log`, and per window `tx_*` (sender), `rx_*` (receiver,
  per source) and `ctr_*` (NIC counters, voltage flags).
* Scored by `analysis/dsss_w1e.py --score` → `../w1e_2026-11-05_windows.csv`,
  `results/raw/w1e_w1e_2026-11-05.csv`.

**Events during the session** (disclosed in `predictions/W1e.md`, outcome). Window k starts at
13:34:04 + 30·k s.
* About 13:48–13:57 (windows 28–46): a TP-Link TL-WN722N USB Wi-Fi adapter was plugged into the
  PC, disconnected under Windows.
* About 14:02–14:06:29 (windows 55–65): BeagleBone Blue 2 was powered from the PC's USB with that
  adapter. Its radios were taken down at 14:06:29.
