# The Pis' broadcast rate, 2026-11-06 morning. Diagnostic, disclosed, not scored (F129)

Each Pi sends alone, saturated (3 000/s offered), with 145 B and then with 1 000 B of UDP payload
(`plan_diag.txt`). Only the Pis took part (Blue 2 idle). The rate comes from the difference in cycle
between the two sizes (`rate_from_sizes.py`).

| run | Pis' uptime | ad-hoc session on that boot | rate pi-A / pi-B / Pi 3 | cycle at 145 B (pi-A) |
|---|---|---|---|---|
| `t0_up15min_no_node4` | 15 min | 2nd (after the W1h pilot) | 0.98 / 0.97 / 1.01 Mb/s | 1 945.6 µs |
| `t1_fresh_boot_no_node4` | 1 min | 1st | **5.96 / 5.98 / 6.13 Mb/s** | 352.6 µs |
| `t2_second_session_same_boot` | 6 min | 2nd | 0.97 / 0.97 / 1.02 Mb/s | 1 946.3 µs |

**Reading:**
* The first ad-hoc session after a Pi boots broadcasts at 6 Mb/s (OFDM); later sessions use 1 Mb/s.
  A threshold in time since boot, between 2½ and 6 minutes, would also fit.
* Node 4 is not involved.

The Pi 3's 145 B cycle at 3 000/s offered (2 650 / 2 722 µs) is not comparable with the 600/s rate
check: its sender loop is busier.

Rerun: `python3 -I rate_from_sizes.py <run folder>`.
