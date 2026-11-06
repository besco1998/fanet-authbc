# W1h attempts, 2026-11-06 (registered at `prereg-W1h`, `0bdb157`)

Each attempt has its own folder:
* `launch.log`;
* `session/` with every board's files, `gate.csv`, and the `--gate` output in `collect_gate.log`.

As registered, an attempt whose gate says ABORT is discarded: its capacity windows are neither
scored nor analysed.

| attempt | time | Blue 2 boot | gate | why |
|---|---|---|---|---|
| a1 | 13:31–13:58 | `2f39ecd8` | **ABORT** | Pi 3 rate check before 2 613.4 µs (band ≤ 2 600); G31 spread 5.23× (TP-Link 1.17 %, the Pis 2.95–6.12 %) |

A first launch of a1 stopped on my side, before touching any board (a launcher without its execute
bit). It is not counted as an attempt.

The first collection of a1 ran a few seconds before the boards finished reverting, because WSL's
clock stepped during the 28-minute wait. All 52 windows' files were already present. It was
collected again complete, with every revert and pi-B's return to auto, and the gate is unchanged.
The tools now time START from a Pi's clock and wait for every board's own revert line.
