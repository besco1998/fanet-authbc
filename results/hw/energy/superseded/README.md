# SUPERSEDED — biased by warmup-inside-window (do not use)

These files come from the first completed campaign. `run_window()` performed its 1000 warmup
iterations *inside* the GPIO sync window, so `duration_s` covered warmup + timed loop while `n_ops`
counted only the timed loop. energy/op = ΔP·duration_s/n_ops was therefore inflated by
warmup_time / window_time:

| op | predicted bias | observed cross-check gap |
|---|---|---|
| bls:verify | 14.35 % | 14.4 % |
| bls:sign | 4.55 % | 4.4 % |
| cheaper ops | <1 % | within noise |

Detected by the Law-6 cross-check against ΔP × t_op from the independent micro suite. Fixed by
moving `warmup()` outside the window; the campaign was **re-measured**, not corrected by a factor
(Law 7 forbids hidden correction factors). Retained only as evidence of the defect.
