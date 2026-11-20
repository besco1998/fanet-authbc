# U-CAP2 — the corrected capture-window reading, checked afresh before any use

*Registered 2026-11-20, before any U-CAP2 run; the time is the commit's.*

*Mohamed (2026-11-20): "D stays recorded as failed as registered. The corrected reading
(simple-frame-capture-model.cc 71–72) may be used for F and H after one fresh registered check:
offsets of 12, 15, 16, 17, 20 and 30 µs around the 16 µs edge, one frame size not used before, at
802.11a 6 Mb/s and 802.11b 1 Mb/s. If any point disagrees, stop."*

## The reading under test

U-CAP's rule (`predictions/UCAP.md`) with one correction, read from the source after U-CAP failed.
* A later frame X takes over from a frame Y already detected only if both conditions hold:
  * the PHY's: Y's detection time + 16 µs ≥ now (`phy-entity.cc:439–442`, `:472–475`);
  * **and the model's own: Y's *start* time + 16 µs ≥ now**
    (`simple-frame-capture-model.cc:71–72`). This is the binding one;
* and X is stronger than Y by more than the 5 dB margin.
* **So capture is possible only for X arriving at most 16 µs after Y starts.** At exactly 16 µs,
  the test `start + 16 µs ≥ now` holds with equality, so capture is predicted there too.

Everything else is as U-CAP held it at 430 of its points:
* within 4 µs, the stronger frame wins at SINR ≥ 4 dB;
* a detected frame is decoded at its SINR by ns-3's error models.

## What is run (`ns3/authbc-capture.cc`, as for U-CAP)

* **New points:**
  * Δ = 12, 15, 16, 17, 20 and 30 µs (X after Y);
  * SIR −2 … 20 dB;
  * capture model on and off;
  * 802.11a 6 Mb/s and 802.11b 1 Mb/s, long preamble;
  * **a 97 B payload** (133 B MPDU), never sent by this program (U-CAP used 173 B);
  * **seed 2**, also new; 2 000 trials a point; P_Y = −60 dBm.
* 552 points, **every one scored.**

## Predictions (`python analysis/ucap.py --predict-check` → `results/raw/ucap2_predictions.csv`)

| Δ | capture model | X received | Y received |
|---|---|---|---|
| 12, 15, 16 µs | off | never | decoded at SINR −SIR from Δ on (802.11b to about SIR = 3–5; 802.11a to SIR ≈ 0–1) |
| 12, 15, 16 µs | on | **SIR ≥ 6 dB** (above the 5 dB margin), then decoded | as off up to SIR = 5, then 0 (aborted) |
| 17, 20, 30 µs | either | **never** | decoded at SINR −SIR from Δ on |

The intermediate values come from ns-3's own error models:
* DSSS: (1 − ½e^(−22·SINR))^bits over 144 µs … 192 + 8·133 µs;
* OFDM: the 6 Mb/s table through `ns3/authbc-per.cc` for 97 B, over 20 … 204 µs.

**Scored as U-CAP was:**
* a point predicted 0 or 1 holds only if all 2 000 trials agree;
* a point between holds within 0.05 (the neglected partial SIG chunk at 802.11a, and binomial
  noise).
* **The reading holds only if all 552 points hold. Any point that disagrees is a stop**, and the
  corrected reading is not used for F or H.

## Expectations `[agent]`

* All 552 hold: the reading is one source line, and U-CAP's post-hoc check agreed at 552 points
  of other offsets.
* **The point most at risk is Δ = 16 µs, the window's edge.** X arrives exactly at Y's start
  + 16 µs, and propagation delay is zero, so `start + 16 µs ≥ now` is an equality in integer
  nanoseconds.

## Disclosure

* **Known before this registration:** U-CAP's outcome and its post-hoc corrected check
  (`results/raw/ucap_posthoc_corrected.csv`), at offsets 0, 2, 19, 20, 21 and 200 µs, 173 B,
  seed 1.
* **No run at any U-CAP2 offset, at 97 B, or with seed 2.**
