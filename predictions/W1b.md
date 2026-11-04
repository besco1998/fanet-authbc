# W1b — the contention model at 802.11b, 1 Mb/s, against ns-3 (Phase 0 of the 2.4 GHz campaign)

*Registered 2026-11-05, before any 802.11b run of ns-3 beyond the smoke run disclosed below.
Main open item W1 (`docs/OPEN_ITEMS.md` §2a). Mohamed's boards beyond the two Pi 4 are 2.4 GHz
only, and he asked for "phase 0 now". Code and predictions at this commit:
`analysis/dsss_campaign.py`, `src/authbc/models/phy.py` (`DSSS_1M`), `ns3/authbc-links.cc`
(`--standard 80211b`), `ns3/run_links.py`, `results/raw/w1b_predictions.csv`,
`experiments/dsss/plan.txt`.*

## Why

The capacity question (W1) can be taken further on hardware only with more than two radios. The
radios at hand beyond the two Pi 4 are 2.4 GHz only. At 2.4 GHz a Raspberry Pi broadcasts at
802.11b's 1 Mb/s and cannot be made to do otherwise (F35). Five boards there can do two things:
* test the contention model at N = 2–5;
* through A12's equivalence, measure where each design's capacity lies, and so the ratio.

Both rest on the model being right at 802.11b. **This registration tests that, in ns-3, before
any board is touched.** It does for 802.11b what F5 did for 802.11a.

## The model at 802.11b (nothing fitted)

The access rule of docs/02 §6g with 802.11b's constants, read from ns-3.48's source:
* slot 20 µs, SIFS 10 µs, so DIFS 50 µs (`WifiPhy::Configure80211b`);
* CWmin 31, a window of 32 (`wifi-mac.cc`);
* a frame lasts 192 µs of long preamble and header plus 8 µs a byte (`dsss-phy.cc`);
* preamble detection 4 µs, as for every PHY (`WifiPhy::GetPreambleDetectionDuration`).

The event model is `dcf_own_queue`, the corrected loop (F114); there are 30 seeds × 20 s per point.
The cells are the paper's frames: per-record signing at 146 B and 50 frames/s, AUTHBC at 173 B and
12.5 /s, each ns-3 frame being MAC payload.

## Predictions (`analysis/dsss_campaign.py --predict`)

| | model | closed form | band (±3 %) | ns-3 grid |
|---|---|---|---|---|
| per-record (C), crossing of V = 0.95 | **9.65** | 9.11 | 9.36–9.94 | 6–13 |
| AUTHBC (D) | **31.12** | 29.85 | 30.19–32.06 | 22–40, step 3 |
| ratio D/C | **3.225** | 3.275 | 2.925–3.525 | — |

At 1 Mb/s the ratio is lower than at 6 Mb/s (3.55), as A11's trend with rate leads one to expect.
The closed form is 5.6 % low for per-record signing: its tie term is first order, and at nine
nodes the first order is not enough.

**Five stations in place of many: A12's equivalence at 1 Mb/s.** Five stations each send at f_b,
which A12 maps to N_eq = 1 + 4·f_b/f₀ nodes at the paper's rate f₀:

| split (frame, f_b) | N_eq | five stations, model | many stations at N_eq, model | difference |
|---|---|---|---|---|
| 146 B, 62.5 /s | 6 | 0.99002 | 0.99011 | −0.0001 |
| 146 B, 87.5 /s | 8 | 0.97659 | 0.97540 | +0.0012 |
| 146 B, 112.5 /s | 10 | 0.91409 | 0.94318 | **−0.029** |
| 146 B, 137.5 /s | 12 | 0.78058 | 0.84200 | **−0.061** |
| 173 B, 65.625 /s | 22 | 0.98669 | 0.98346 | +0.0032 |
| 173 B, 90.625 /s | 30 | 0.95938 | 0.95626 | +0.0031 |
| 173 B, 115.625 /s | 38 | 0.78271 | 0.89291 | **−0.110** |

**The model predicts that the equivalence holds up to the capacity crossing and fails beyond
it.** Past the crossing, five stations lose more than many slower ones. A12 was registered and
held at the crossing at 6 Mb/s, and did not look beyond it. For the hardware this means the
crossing transfers from many stations to five, but the curve past it does not. The hardware will
therefore be scored against the model's five-station curve.

## The test

`ns3/run_links.py --plan experiments/dsss/plan.txt --stem w1b`: the links scenario with
`--standard 80211b --dataMode DsssRate1Mbps`, broadcast at that rate (`NonUnicastMode`), 30 seeds
× 20 s. That is the two grids above plus the seven splits at N = 5: 15 × 30 = 450 runs.

**Scored as:**
* **W1b-1.** Each ns-3 crossing within ±3 % of the model's (F5's tolerance).
* **W1b-2.** The ns-3 ratio within ±0.3 of the model's 3.225.
* **W1b-3.** Each ns-3 split within ±0.02 of the model's five-station value (the model's accuracy
  at five stations).
* **W1b-4 — the equivalence.** In ns-3, at the four splits at or below the crossing (N_eq 6, 8,
  22, 30), five stations within 0.02 of ns-3's own curve at N_eq; at the three beyond (10, 12,
  38), five stations below it by more than 0.02.

## My expectations `[agent]`

W1b-1 to W1b-4 hold. My least confidence is in W1b-3 at the three splits beyond the crossing:
the medium is near saturation there, where ns-3 and the model have been compared least.

## What each outcome means

| outcome | meaning for the hardware campaign (W1c) |
|---|---|
| all hold | the model is the hardware's prediction at 802.11b, the crossing transfers to five boards, and W1c is registered from these numbers |
| W1b-1 or W1b-2 fails | W1c takes ns-3's crossings, not the model's, and says so |
| W1b-4 fails at or below the crossing | five boards cannot stand for many: the capacity-equivalent part of W1c is dropped, and only N = 2–5 contention remains |

## What it cannot show

* That real radios at 2.4 GHz behave as either simulator does: that is W1c.
* Capture and hidden stations: one collision domain, equal power, as published.

## Disclosure

* The closed form at 1 Mb/s was computed while planning (2026-11-05). The event-model predictions
  above were run for this registration, before it was written. The first prediction file had a
  per-record grid that missed one split's N_eq (a test caught it); the grid was widened and the
  predictions re-run with the same seeds and identical values.
* **One smoke run** of the rebuilt scenario at 802.11b (one seed, N = 2, not a grid point) checked
  that the option works. Every published default was re-run to show it unchanged
  (`results/raw/links_identity.csv`).
* No other 802.11b run of ns-3 exists.
