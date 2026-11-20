# U-CAP — ns-3's receiver rule for two overlapping frames: the capture curve

*Registered 2026-11-20, before any run of `ns3/authbc-capture.cc`; the time is the commit's. Work
package D of `docs/prompts/NEXT_PHASE_PROMPT.md`, items 1–2. This is a check of my reading of
ns-3.48's source, not a model test: if ns-3 behaves otherwise, that is a stop (prompt §7).*

## The rule, as read in ns-3.48

1. **A frame arrives to an idle PHY.** It starts a preamble-detection period of 4 µs
   (`phy-entity.cc:1015–1030`; `WifiPhy::GetPreambleDetectionDuration`).
2. **A second frame arrives inside that period.** The PHY has no current event yet (state IDLE or
   CCA_BUSY without one), so the second frame starts its own detection period
   (`phy-entity.cc:470–494`). **No frame-capture model is consulted.**
3. **At the end of a detection period** (`phy-entity.cc:1033–1165`):
   * the strongest of the overlapping preambles is taken (`:1047–1056`); a weaker frame's own
     period ends with it dropped (`:1058–1073`);
   * the strongest is detected only if its SINR is at least **4 dB** and its RSSI at least
     −82 dBm (`threshold-preamble-detection-model.cc:31–40`);
   * the SINR's interference is the total power at the last change before that instant less the
     frame's own (`interference-helper.cc:433–463`), so **every frame that arrived inside the
     window counts**;
   * on a tie in power, the first event in the map, the lower packet UID, is the strongest (strict
     `>` at `:1050`).
4. **A frame arrives after the first was detected.**
   * With a frame-capture model, if it arrives within the capture window of the last detection
     and is stronger by the margin, the current reception is aborted and the new frame starts
     detection (`phy-entity.cc:439–446` in RX, `:470–480` in CCA_BUSY).
     `SimpleFrameCaptureModel`'s defaults are a 5 dB margin, strictly above
     (`simple-frame-capture-model.cc:34–41, 68–73`), and a 16 µs window
     (`frame-capture-model.cc:25–37`: detection time + 16 µs ≥ now).
   * Otherwise the new frame is dropped (RXING / BUSY_DECODING_PREAMBLE), and stays as
     interference to the frame being received.
5. **Decoding:** per chunk, at the chunk's SINR.
   * DSSS 1 Mb/s falls back to `DsssErrorRateModel`, with success (1 − ½·e^(−22·SINR))^bits
     (`table-based-error-rate-model.cc:139–160`; `dsss-error-rate-model.cc:43–49`).
   * OFDM 6 Mb/s uses `TableBasedErrorRateModel` (`yans-wifi-helper.cc:76`).

**What it implies,** stated before any run:
* **Within 4 µs, the stronger frame wins if its SINR is at least 4 dB, whichever arrives first,
  and the capture model changes nothing.** That is the prompt's "decodes whichever is stronger by
  θ" with **θ = 4 dB**.
* **ns-3's DCF collisions are same-slot ties**, all inside 4 µs (audit of 2026-11-17, item 3), so in
  the capacity scenarios **the capture model should never act.**
* **Once a frame is detected,** it survives a later interferer for as long as the error model
  passes at its SINR:
  * at 802.11b down to about −3.6 dB;
  * at 802.11a down to about 0 dB (the 6 Mb/s table gives success 0.79 at 0 dB and 0.99 at
    1 dB for a 209 B MPDU, `ns3/authbc-per.cc`).
* **At equal power** (SIR = 0) and Δ < 4 µs, neither frame is received (0 dB < 4 dB): **q = 0**,
  as the existing equal-power scenario assumes.

## What is run (`ns3/authbc-capture.cc`)

* **The set-up.** Three nodes on one YansWifiChannel:
  * received powers set exactly by a `MatrixPropagationLossModel`;
  * the two senders 300 dB apart, so neither defers;
  * frames handed straight to each sender's PHY (`WifiPhy::Send`), so the offsets are exact;
  * a 173 B payload (209 B MPDU).
* **The frames.** Frame Y is received at −60 dBm and sent first. Frame X is received at
  −60 + SIR dBm and sent Δ later.
* **The grid:**
  * SIR −2 … 20 dB in 1 dB steps;
  * Δ = 0, 2, 19, 20, 21, 200 µs (the prompt's 0, 2, 20, 200, with 19 and 21 added either side of
    the window's edge at 20);
  * with and without `SimpleFrameCaptureModel` at its defaults;
  * 802.11a at 6 Mb/s and 802.11b at 1 Mb/s, long preamble;
  * **2 000 trials per point, seed 1.**
* **Counted:** at the receiver, whether X and Y are each received (RxOk), plus every RxError
  and every PhyRxDrop reason.

## Predictions (`python analysis/ucap.py --predict` → `results/raw/ucap_predictions.csv`)

Every value comes from the rule above. The script holds the code path; values between 0 and 1 come
from ns-3's own error models. In summary, X is the later frame and Y the earlier, weaker-or-equal
one:

| Δ | capture model | X received | Y received |
|---|---|---|---|
| 0, 2 µs | either | **SIR ≥ 5 dB** (SINR ≥ 4 dB; at SIR = 4 the SINR is 3.998 dB) | **never** on the grid (needs SIR ≤ −4) |
| 19 µs | off | never | 802.11b: 1.00 to SIR = 2, then 0.99 / 0.87 / 0.44 / 0.03 at 3–6 dB. 802.11a: 1.00 / 0.99 / 0.79 / 0.09 at SIR −2 … 1, 0 from 2 |
| 19 µs | on | **SIR ≥ 6 dB** (strictly above the 5 dB margin) | as without the model up to SIR = 5, then 0 (aborted) |
| 21, 200 µs | either | never (after the window) | as at 19 µs, off; at 200 µs only the rest of Y is interfered (802.11a: 0.92 at SIR 0, 0.41 at 1) |
| 20 µs | either | **reported only:** the window's edge, where same-instant event order decides | |

**Scored** at Δ = 0, 2, 19, 21 and 200 µs (460 points):
* a point predicted 0 or 1 holds only if every one of its 2 000 trials agrees;
* a point between holds if within **0.05** of the prediction. That allowance covers the neglected
  partial SIG chunk at 802.11a, and binomial noise (σ ≤ 0.011).

**Scored as a whole:**
* **the rule holds if every scored point holds.** Any point that fails is a stop: ns-3 does
  otherwise than its source as I read it. The failure is reported, and the reading is corrected
  from the source before anything uses it;
* **q at equal power,** the SIR = 0 rows at Δ = 0 and 2 µs: X and Y both 0.

## Work package D, item 3 (after the curve)

* **The q closed forms rewritten for ns-3's rule:** a collided frame at receiver i is decoded if it
  is the strongest and its SINR is at least 4 dB, then it passes the error model at that SINR.
  * At 802.11b the decode is certain above 4 dB, so q is the prompt's closed form with
    **θ = 10^0.4**.
  * At 802.11a, q = E[1{SINR ≥ θ}·(1 − PER(SINR))], equal to that closed form wherever
    PER(4 dB) = 0, which the table gives at 6 Mb/s.
  * The rewrite goes into `src/authbc/models/capture.py` with tests.
* **q = 0 in the existing equal-power scenario,** confirmed by the curve and by the audit trace.
  If not, stop.

## Expectations `[agent]`

* **Every scored point holds:** the reading is line by line.
* **The likeliest surprise** is at 802.11a with Δ = 19 µs: there the SIG chunk is partly
  interfered, which my prediction ignores, and the allowance may be too small near SIR = 0–1.
* **The 20 µs points** will follow either the 19 µs rule or the 21 µs rule, not something else.

## Disclosure

* **Known before this registration:** ns-3.48's source as cited; the audit of 2026-11-17; F135's
  PER probe; the authbc-per values above, computed while writing this file.
* **No run of `authbc-capture` has been made.**

---

## Outcome — added 2026-11-20, after the runs; nothing above this line was changed

**The runs.** As registered: `ns3/authbc-capture.cc`, 24 processes, 2 000 trials a point, seed 1
(`results/raw/ucap_runs/`).
* The first launch aborted at once in `WifiTxVector::SetTxPowerLevel`: level 0 is below ns-3.48's
  `WIFI_MIN_TX_PWR_LEVEL = 1`. No result was written.
* The fix (`9dba23bb`, level 1), a 3-trial smoke test, then the runs.

**Scored** by `analysis/ucap.py --score` → `results/raw/ucap_scored.csv`.

**The rule as registered failed: 430 of 460 scored points held.**
* **All 30 failures are one case:** the capture model on, Δ = 19 µs, SIR ≥ 6 dB, at both PHYs.
  * Predicted: X takes over and is received.
  * Measured: X is never received (2 000 of 2 000 BUSY_DECODING_PREAMBLE), and Y is lost to its
    L-SIG or decoded at its SINR.
  * **No capture switch ever happened at 19 µs.**
* **Everything else held:**
  * **the 4 µs window** (Δ = 0, 2 µs, model on or off): X received from SIR = 5 dB and never below,
    Y never — 184 of 184;
  * **equal power** (SIR = 0, Δ < 4 µs): neither frame received, 8 of 8. **q = 0 in the
    equal-power scenario, as assumed;**
  * **a locked frame decoded at its SINR,** every intermediate point within about 0.01 of ns-3's
    own error models:

| frame Y decoded | SIR (dB) | measured | predicted |
|---|---|---|---|
| 802.11b, Δ = 19 µs, model off | 3 / 4 / 5 / 6 | 0.9905 / 0.8775 / 0.4355 / 0.0425 | 0.9861 / 0.8734 / 0.4406 / 0.0324 |
| 802.11a, Δ = 19 µs, model off | −2 / −1 / 0 / 1 | 0.9995 / 0.9885 / 0.8020 / 0.0875 | 0.9994 / 0.9901 / 0.7921 / 0.0860 |
| 802.11a, Δ = 200 µs, model off | −2 / −1 / 0 / 1 / 2 | 0.9995 / 0.9970 / 0.9275 / 0.3960 / 0.0080 | 0.9998 / 0.9963 / 0.9182 / 0.4072 / 0.0141 |

**The cause, shown in the source: my reading missed one of two window conditions.**
* Capture needs both:
  * `PhyEntity` checks the last detection + 16 µs ≥ now (`phy-entity.cc:439–442`, `:472–475`);
  * **`SimpleFrameCaptureModel::CaptureNewFrame` also checks the current frame's start + 16 µs ≥
    now** (`simple-frame-capture-model.cc:71–72`).
* The registration cites the second line but reads the window from detection alone.
* **The binding window ends 16 µs after the first frame starts, not 20 µs.** At Δ = 19 µs there is
  no capture.
* **ns-3 does what its source says. The error is mine.**

**The corrected reading, post hoc, not a score:** the same predictions with the window ending at
16 µs agree with **552 of 552 points**, the 20 µs edge included (`analysis/ucap.py --score` →
`results/raw/ucap_posthoc_corrected.csv`).

**What it means for the rest of the phase.**
* **ns-3's DCF collisions are same-slot ties inside 4 µs, where no capture model is consulted.**
  The narrower window (≤ 16 µs from the first start) strengthens the registered implication: in
  the capacity scenarios the capture model should never act.
* **The capture that ns-3 does have** is the preamble-window rule: the strongest frame wins if its
  SINR is at least 4 dB. With it, the q closed forms hold with θ = 4 dB.

**Expectations:**
* "every scored point holds": missed, by my misreading, at 30 points;
* "the likeliest surprise at 802.11a, 19 µs, near SIR 0–1": held there (within 0.01). The
  surprise was elsewhere;
* "the 20 µs points follow the 19 µs or the 21 µs rule": they follow both, which under the
  corrected reading are the same.

**Per the registration and the prompt §7 this is a stop.** The corrected reading is not used
until Mohamed decides.
