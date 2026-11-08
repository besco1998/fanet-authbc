# The square layout, 2026-11-06 evening. Diagnostic, disclosed, not scored

Mohamed placed all four boards on the corners of a 1 m square, at the same height. All the boards
had been power-cycled. Blue 2's router signal at its corner was −67 dBm, the best today. Every Pi
was at its default power (no held power).

**`pf1/`, 17:43–17:47: the Pis at 6 Mb/s** (first ad-hoc session after their boot, F129). Each
rate check was sender-limited (1 666 µs). The checker said NO-GO rather than RETRY: check 7 failed
at 6 Mb/s (the Pi 3's OFDM frames reached one receiver at 96.9 %). Fixed since in
`hw_preflight.py`: at 6 Mb/s, checks 6 and 7 do not block a retry.

**`pf2/`, 17:52–17:56: the Pis at 1 Mb/s.**

| sender | rate check | G31 loss | lost at pi-A / pi-B / Pi 3 / TP-Link |
|---|---|---|---|
| pi-A | 1 944.1 µs | 4.59 % | – / 3.64 / 6.67 / 3.47 % |
| pi-B | 1 952.2 µs | 4.65 % | 4.67 / – / 3.29 / 6.00 % |
| **Pi 3** | **3 244.5 µs (out of band)** | **7.30 %** | 7.73 / 6.80 / – / 7.36 % |
| TP-Link | 1 961.6 µs | 5.56 % | 4.75 / 5.95 / 5.98 / – % |

**What it shows:**
* In the square, pi-A, pi-B and the TP-Link sit within 1.2× of each other at default power.
  Before, pi-A dominated even at 4 dBm.
* The Pi 3 is the weakest sender (spread 1.59×). Its rate check (308 frames/s alone) is out of
  band, as at one spot on 2026-11-05 (F121/F122, where the cause lay outside the board).
* Next: swap the Pi 3's corner with another board's, to tell the place from the board.

**`swap_pi3_piB/`, 18:32–18:36:** the Pi 3 and pi-B swapped corners, all antennas toward the centre,
the Pi 3 and pi-B power-cycled.
* The Pis ran at 1 Mb/s although two were fresh: warm pi-A created the cell (F129 addendum, a
  second case).
* **The Pi 3's rate check was 3 485.2 µs at pi-B's old corner, and pi-B's 2 008.0 µs at the Pi 3's
  old corner: the slowness follows the board.**
* Alone, the Pi 3 got 293 frames/s out (6 481 sent, none dropped). Its load was 0.02, 42 °C, no
  throttling or under-voltage.
* Balance 2.17×: pi-A 3.39 %, pi-B 5.36 %, Pi 3 7.35 %, TP-Link 6.04 %.

**`swap_bt_off/`, 18:42–18:46:** as above, with Bluetooth soft-blocked on all three Pis.
* The Pi 3 read 3 398.7 µs, so Bluetooth is not the cause. It was unblocked again after.
* Balance 2.39×: pi-A 3.15 %, pi-B 5.42 %, Pi 3 7.52 %, TP-Link 6.28 %.

**The Pi 3's rate check across layouts:**

| layout | rate check |
|---|---|
| away from the Pi 4s (W1d S0, 2026-11-05) | 4.7–5.0 ms |
| beside them (F122) | 2.45–2.51 ms |
| the cluster today | 2.19–2.59 ms |
| the 1 m square | 3.24–3.49 ms |

It is slow whenever it is far from the Pi 4s. The cause is not known.
