# `p_cpu_w` — measured on COMPOSED pipelines (item D6, 2026-07-29)

## Why this supersedes the P7b value
P7b measured `p_cpu_w = 0.634 W` as the **median incremental power over eight isolated primitives**
(sign, verify, aggregate, encode, …), each run in a tight loop on its own. The energy model then
applies that constant to a *composed* pipeline — encode → chain-hash → sign → assemble — which has a
different instruction mix (bytes/list churn between crypto calls, more memory traffic).

D1 measured the composed pipeline directly and found it draws materially more. So the question D6
asked — *"is `p_cpu_w` configuration-dependent?"* — has a clear answer: **no.** The four E5
configurations agree to **3.8 %**. What was wrong is the *isolated-primitive* methodology, not the
use of a single constant.

## The measurement
INA219 channel 1 (pi-A), 5 idle/load window pairs per configuration, 60 s windows, GPIO-marked,
throttle-checked. Full protocol: `hw/energy_protocol.md`; harness: `hw/validate_energy_e2e.py`.

| configuration | b | ΔP (W) | µJ/frame | µJ/record |
|---|---|---|---|---|
| optimized delta / placement B | 4 | **0.732** | 233.53 | 58.38 |
| D-over-agg cbor / placement D | 40 | **0.744** | 1880.77 | 47.02 |
| A+CBOR baseline (Pillar-1) | 1 | **0.755** | 118.82 | 118.82 |
| A+JSON naive | 1 | **0.760** | 121.77 | 121.77 |

* **median = 0.749 W** — adopted.
* **spread = 3.8 %** (0.732 … 0.760) — the residual, and small enough that one constant stays
  defensible. Keeping a single `p_cpu_w` keeps the model *predictive*: a per-configuration power
  would mean you must build and meter a configuration before you can model it, which defeats the
  purpose.
* **vs the isolated-primitive median: +18.2 %** (0.634 → 0.749 W).

## What remains uncharged, and why
With `t_hash` added (D7) and this power adopted, the model's residual against measurement is the
**frame-assembly time** — list building, byte concatenation, slicing between crypto calls:

| configuration | measured µs/rec | model µs/rec | residual |
|---|---|---|---|
| optimized delta/B, b=4 | 79.93 | 72.53 | +10.19 % |
| A+CBOR, b=1 | 157.60 | 141.27 | +11.56 % |
| A+JSON, b=1 | 160.62 | 142.24 | +12.93 % |
| D-over-agg, b=40 | 63.17 | 55.36 | +14.12 % |

**This is deliberately not charged.** It is CPython interpreter overhead in a *prototype*; a C or
Rust implementation would carry a small fraction of it. Charging it would make the model describe
*this Python code* rather than the design the thesis is about. It is reported here, and every energy
figure should be read as a **lower bound of roughly 10–14 %** on that account.
