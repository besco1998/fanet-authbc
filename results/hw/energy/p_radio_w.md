# p_radio_w — measured (P7b, 2026-07-28)

2-node 802.11 IBSS ad-hoc link (channel 1, 2412 MHz) between authbc-pi4a (TX) and authbc-pi4b (RX).
pi-A drove the GPIO sync line and blasted 1400 B UDP datagrams at 10.9.9.2 for 30 s per window,
alternating with 30 s idle windows, 2 reps. pi-B's **receive** power is INA219 channel 2.

| window | pi-A (TX side) | pi-B (RX side) |
|---|---|---|
| rep1 idle | 1.924 W | 2.217 W |
| rep1 TX | 3.305 W | 2.449 W |
| rep2 idle | 1.919 W | 2.240 W |
| rep2 TX | 3.336 W | 2.445 W |

- **`p_radio_w` (receive path, what the model uses) = 0.218 W** — reps 0.231 / 0.205.
- TX-side delta 1.399 W, but that **includes the sender's CPU** in the blast loop, so it is not a
  clean radio figure and is reported for context only.
- Offered load 55–61 Mb/s at the socket (far above what the link carries), so the radio was saturated.
- **Nominal was 0.700 W ⇒ measured is 0.31× the assumption.**

Both `p_cpu_w` (0.634 W vs 3.0 nominal) and `p_radio_w` (0.218 vs 0.700) are far below the nominal
values E5 used, so the E5 energy column must be re-derived. κ = p_radio/p_cpu = **0.34**, which
*does* sit inside E4's assumed "plausible ≲ 0.5" band — that assumption survives measurement.
