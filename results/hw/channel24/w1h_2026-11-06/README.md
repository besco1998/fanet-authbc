# W1h attempts, 2026-11-06 (registered at `prereg-W1h`, `0bdb157`)

Each attempt has its own folder:
* `launch.log`;
* `session/` with every board's files, `gate.csv`, and the `--gate` output in `collect_gate.log`.

As registered, an attempt whose gate says ABORT is discarded: its capacity windows are neither
scored nor analysed.

| attempt | time | Blue 2 boot | gate | why |
|---|---|---|---|---|
| a1 | 13:31–13:58 | `2f39ecd8` | **ABORT** | Pi 3 rate check before 2 613.4 µs (band ≤ 2 600); G31 spread 5.23× (TP-Link 1.17 %, the Pis 2.95–6.12 %) |
| a2, preflight 1 | 14:12–14:16 | `eeb200cc` | **NO-GO** (attempt 2 not started) | balance 5.35× (TP-Link 1.20 %, the Pis 2.88–6.42 %); all else held, the Pi 3 at 2 192.5 µs after its reboot |

A first launch of a1 stopped on my side, before touching any board (a launcher without its execute
bit). It is not counted as an attempt.

The first collection of a1 ran a few seconds before the boards finished reverting, because WSL's
clock stepped during the 28-minute wait. All 52 windows' files were already present. It was
collected again complete, with every revert and pi-B's return to auto, and the gate is unchanged.
The tools now time START from a Pi's clock and wait for every board's own revert line.

| attempt | time | Blue 2 boot | preflight | why |
|---|---|---|---|---|
| a2, placement 120 cm, try 1 | 14:24 | `9968b40c` | not a reading | node 4's start command lost on Blue 2's weak router link (−91/−92 dBm); the Pis ran alone (launcher fixed: node 4 first, verified) |
| a2, placement 120 cm, try 2 | 14:45–14:49 | `4c1f728f` | **NO-GO** | balance 1.97×: pi-A 3.21 %, pi-B 4.99 %, Pi 3 6.34 %, TP-Link 6.30 %; all else held |
| a2, 120 cm, pi-A + pi-B at 8 dBm | 15:18–15:22 | `a3088f70` | **GO** (1.499×) | all six checks held |
| **a2, the session** | 15:26:48–15:52:48 | `ca461667` | gate **GO** (1.433×) | **VOID** on V5: A31 spread 1.549×. Everything else held. Reported, not scored: 30.99 / 9.33, ratio 3.32. Files in `a2/w1h_2026-11-06_a2/` |

