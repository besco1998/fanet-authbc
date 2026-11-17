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

---

## Outcome — added 2026-11-17, after the runs; nothing above this line was changed

**The runs.** As registered, through the audit twin (`ns3/run_unified.py`, config hash
`26f97d469287c167`):
* pilots of 5 seeds (`results/raw/unified_c2_pilot{,32,64}{,_runs}.csv`), which put the
  crossings at 367.47 / 546.21 / 710.86;
* then 30 seeds at seven node counts around each pilot crossing, 210 runs per cell, 630 in all
  (`results/raw/unified_c2_b{16,32,64}{,_runs}.csv`).

Every unit ended `Result=success` under the 8 GB cap (6, 5 and 5 workers). Their memory peak was
not logged.

**Checked before scoring.** An independent script on the raw counts agrees with the driver to the
digits shown:
* every node count has seeds 1–30;
* each delivered fraction equals rx / (tx (N − 1));
* the mean curves fall monotonically, so each crossing is unique.

**Scored** by `analysis/unified_c2.py` → `results/raw/unified_c2_scored.csv`. Its model values are
the registered ones (`tests/test_unified_c2.py`).

**Scored: 6 of 6 held.**

| cell | b | ns-3 crossing (95 % CI) | law (G9) | error | root of (G5) | error | held |
|---|---|---|---|---|---|---|---|
| UB16 | 16 | **366.72** (364.99–368.57) | 359.53 | −1.96 % | 356.31 | −2.84 % | **yes, yes** |
| UB32 | 32 | **547.15** (543.19–549.63) | 531.13 | −2.93 % | 528.72 | −3.37 % | **yes, yes** |
| UB64 | 64 | **717.27** (708.41–726.85) | 697.93 | −2.70 % | 696.65 | −2.87 % | **yes, yes** |

**Reported, not scored: the gain.** Γ(b) = (N(b) − 1)/(N(1) − 1), with N(1) = 35.26 and
b ≤ 8 taken from the stored crossings, against the design law's b(1 + β)/(b + β), β = 29.24:

| b | 1 | 2 | 3 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|---|
| ns-3 | 1 | 1.919 | 2.788 | 3.606 | 6.460 | 10.675 | 15.941 | 20.907 |
| design law | 1 | 1.936 | 2.814 | 3.639 | 6.496 | 10.695 | 15.801 | 20.757 |
| law − ns-3 | 0 | +0.91 % | +0.94 % | +0.91 % | +0.56 % | +0.19 % | −0.88 % | −0.72 % |

**The question, answered.** Yes, ns-3's gain bends away from b, as the law says:
* at b = 64, 64 records to a frame buy 20.9 times the one-record capacity, a third of b;
* it stays below 1 + β = 30.24;
* the design law follows ns-3's gain within 0.95 % at every b from 2 to 64.

**What it means.** At 360–720 stations, the two-constant law and the full loss expression each
lie 2–3.4 % below ns-3. That is the same side and size as the 40 stored crossings at 6 Mb/s
(−4.55 … −0.01 %). The law does not drift as b grows from 16 to 64: its error at b = 64 lies
between its errors at b = 16 and b = 32. **C2 does not falsify the model.**

**Expectations.** "All six within ±5 %, the law slightly below ns-3": held, at all six.
