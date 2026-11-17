# U-C2 — capacity at 16, 32 and 64 records per frame: does the gain bend away from b?

*Registered 2026-11-17, before any U-C2 run; the time is the commit's. Task of 2026-11-17, work
package C, item C2. The model is in `docs/revision/2026-11-17_unified_model_spec.md`
(`src/authbc/models/unified_capacity.py`). C2 is one of the two items that can falsify it.*

## What is run

* **The cells.** The lean format, ℓ(b) = 137 + 9b bytes, 50 records/s, so f = 50/b frames/s;
  802.11a at 6 Mb/s, W = 16, ε = 5 %:

| cell | b | frame | f (frames/s) | T_f |
|---|---|---|---|---|
| UB16 | 16 | 281 B | 3.125 | 448 µs |
| UB32 | 32 | 425 B | 1.5625 | 640 µs |
| UB64 | 64 | 713 B | 0.78125 | 1 024 µs |

* **Method.** As the frozen campaign runs, through the audit twin (`ns3/run_unified.py`):
  * a pilot of 5 seeds on seven node counts at ±5 % steps around the root;
  * then 30 seeds on seven node counts around the pilot's crossing;
  * 20 simulated seconds, the designated source;
  * the crossing of 95 % mean delivery by straight-line interpolation, with its bootstrap
    interval over seeds.

## Predictions

| cell | law (G9) | root of (G5) | design law (G10–G13) |
|---|---|---|---|
| UB16 | **359.53** | **356.31** | 360.63 |
| UB32 | **531.13** | **528.72** | 532.34 |
| UB64 | **697.93** | **696.65** | 698.97 |

* **The design law:** N_inf = 1 016.9 and β = 29.24, from Φ_T and Ψ_T without symbol rounding.
  The author's values (about 360 / 531 / 698) agree.
* **Every frame has T_f ≥ 2τ0** (τ0 = 98.04 µs), so the law is inside its stated range.

**Tolerance:** each crossing holds if the law, and separately the root, is within **±5 %** of
ns-3's. A crossing outside fails. The tolerance is not widened after the runs.

**Reported, not scored:**
* **the gain** Γ(b) = (N(b) − 1)/(N(1) − 1), against b(1 + β)/(b + β). N(1) and b ≤ 8 come from the
  stored crossings (C 35.26; B2 66.73; B3 96.51; D 124.55; B8 222.33).
* **The question:** does ns-3's gain bend away from b, as the law says (Γ < min(b, 1 + β))?

## Expectations `[agent]`

* **All six within ±5 %, the law slightly below ns-3.** Of the 40 stored crossings at 6 Mb/s,
  W = 16, ε = 5 % with the designated source, the law lies −4.55 % … −0.01 % from ns-3, never
  above it. The exception is the one-record Falcon frame, at −7.8 %
  (`results/raw/unified_model_vs_ns3.csv`). These swarms are large (N ≈ 360–700), far from the
  Poisson limit.
* **Memory.** A run's memory at N ≈ 700 is not yet measured. The pilot's peak is read first, and
  the measurement's workers are set from it.
* **No U-C2 run has been made.**
