# A1, step 1 — the neighbour distance d_ref. Written before the measurement (2026-10-19)

**What.** The plan (A1, Metrics) defines a receiver's neighbours as the nodes within d_ref, the
distance at which an isolated two-node link delivers at least 99 %, and says to measure it
first. This is a calibration of the scenario, not a capacity; it is written down first anyway.

**Run.** `ns3/authbc-spatial.cc --layout pair`: one sender, one receiver, 100 m altitude,
distance 150–400 m in 5 m steps; the three frames of A1 at their own rates (146 B at 50 /s,
372 B and 173 B at 12.5 /s); 30 seeds of 20 s. Plan: `experiments/spatial/plan_dref.txt`.
Channel exactly as A1's: log-distance exponent 2, 46.7 dB at 1 m, Nakagami m = 3, 20 dBm,
capture margin 4 dB, ns-3.48 defaults otherwise (preamble detection: 4 dB SNR and −82 dBm).

**Rule.** d_ref is the largest distance on the grid at which the 30-seed mean delivery is at
least 0.99 for **all three** frames, and at every shorter distance. One d_ref for all
configurations, so that baseline and design are scored over the same neighbour sets.

**Expectation, by hand.** The −82 dBm preamble threshold binds before the error-rate model at
6 Mb/s (noise ≈ −94 dBm, so −82 dBm is 12 dB of SNR). With Nakagami m = 3 the power gain is
Gamma(3, 1/3); its 1 % quantile is 0.145 (−8.4 dB). Delivery is 99 % where the mean received
power is −82 + 8.4 = −73.6 dBm: 20 − 46.7 − 20 log10 d = −73.6 gives **d ≈ 221 m**. The three
frames should agree within one grid step, since the threshold, not the frame length, binds.
**Expected d_ref: 215–225 m.** The median preamble range (mean power −82 dBm) is ≈ 582 m.

**Disclosure.** One 5-second pair run at 200 m (173 B, seed 1) was made to check the new
layout: 61 of 61 frames delivered.
