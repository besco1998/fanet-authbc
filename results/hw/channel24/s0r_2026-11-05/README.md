# S0 repeated, 2026-11-05 12:50–12:57, the Pi 3 moved, Blue 2 unplugged — disclosed, not scored

Asked by Mohamed after he moved the Pi 3 beside the two Pi 4s, moved Blue 1 farther away and
unplugged Blue 2. The same kit (`hw/channel/run_window_plan.sh`, hashes
checked against the repo), the same `plan_s0.txt` and channel 11; Blue 1 stayed on the home Wi-Fi
(channel 1). W1d's stop rule from S0 stands: this repeat is reported, not scored (`predictions/W1d.md`,
second addendum; F122).

* `node1..3/` — each board's files. `aborted_launch_1.log` is a first launch at 12:48–12:49 that
  aborted before any window: my launch staggered the boards by 15 s, so each one's peer check found
  the others not yet in the cell. Every board reverted at once.
* `pi3_diag3/` — the decay test (`diag3_pi3.sh`, identical to `../diag_2026-11-05/pi3/`), run
  13:06 after nine idle minutes.
* Scored by the unchanged `analysis/dsss_three.py --score` → `../s0r_2026-11-05_windows.csv`,
  `results/raw/w1d_s0r_2026-11-05.csv`.
