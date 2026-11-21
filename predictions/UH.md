# U-H — the hardware-matched configurations (D4 → work package H), registered before any run

*Registered 2026-11-20; the time is the commit's. Mohamed's decisions of 2026-11-19 (D4, "no
guessed values") and 2026-11-20 (C: no closed form at N = 2, so the 5 GHz anchor is compared with
ns-3 and the event simulation only).*

**This is a comparison, not a scored prediction.** Each table puts the hardware, ns-3 at each
candidate setting, the event simulation (rule A, which tracks ns-3 at small N, F137) and the
closed forms side by side. Where hardware and ns-3 disagree, the parameter that accounts for it is
named with evidence. Nothing is tuned.

## (a) The 5 GHz anchor: the frame-burst-off sessions of 2026-10-09 (`results/hw/channel/`)

* **The setting:**
  * N = 2, two Pi 4 (BCM4345/6), channel 36, 802.11a 6 Mb/s;
  * the 1 400 B UDP frame: a 1 464 B MPDU, 1 976 µs on air; ns-3 frameSize 1 428;
  * the per-period redrawn source, as the hardware sent;
  * 124, 174 and 211 frames/s per board, as in R1 (`contention_2nodes_fb_off.csv`).
* **Two window candidates,** the standard slot (9 µs) and DIFS (34 µs) in both:
  * **W = 10**, from the burst-off one-sender cycle of 2 050 µs: mean backoff 40 µs;
  * **W = 16**, the standard's. It also fits the saturated pair (S1, 12.4 % lost) through
    2/(W + 1) = 11.8 %, model-dependent. S1 is not reproduced here, so Mohamed's rule allows it.
  * These are F115's open conflict, carried as a spread.
* **Capture:** none possible. Each board is the other's only receiver, and both capture ends are
  the same configuration.
* **ns-3:** the audit twin, `--cwMin = W − 1`, 30 seeds × 100 s per rate and W. Also at each W:
  * the saturated pair (both boards at 400 frames/s offered) against S1's 12.4 % lost and 263
    frames/s on air;
  * one saturated board against the 2 050 µs cycle.
* **The closed forms** (`python analysis/uh.py`), reported only:

| frames/s | hardware loss (burst off) | W | (G5) | (G25), outside its range | finite-station, not accepted at N = 2 |
|---|---|---|---|---|---|
| 124 | 0.00321 | 10 | 0.00919 | 0.00591 | 0.00123 |
| 124 | 0.00321 | 16 | 0.00632 | 0.00420 | 0.00123 |
| 174 | 0.00516 | 10 | 0.01940 | 0.01151 | 0.00187 |
| 174 | 0.00516 | 16 | 0.01323 | 0.00804 | 0.00187 |
| 211 | 0.00837 | 10 | 0.03053 | 0.01706 | 0.00239 |
| 211 | 0.00837 | 16 | 0.02086 | 0.01184 | 0.00239 |

## (b) The 2.4 GHz sessions W1e–W1n, at the driver default (frame burst on, F75)

* **The rule, from offered rate and frame airtime** (Mohamed, 2026-11-19):
  * a window is reproduced only if no station could hold two frames;
  * with the redrawn source, a board's next frame arrives within the shortest service time
    S = T_f + DIFS + 1.5σ (the fastest board alone) with probability S²f²/2;
  * **under 1 %, reproduced; otherwise flagged** as affected by frame burst.
* **Applied before any run:** only **W1f's four-board windows at 65 frames/s** pass (0.80 %).
  Every other contention window of W1e, W1f, W1j, W1k and W1n s2 lies at 1.4–9.3 % and is
  flagged. Those wait for the frame-burst-off session (`docs/revision/2026-11-20_session_plans.md`,
  session 2).
* **W1f at 65 frames/s:**
  * N = 4: pi-A, pi-B, the Pi 3 and the TP-Link (RTL8188EUS);
  * the 145 B UDP frame, 1 864 µs on air, ns-3 frameSize 173; u = 0.485;
  * 802.11b 1 Mb/s, the redrawn source.
* **The window per board,** from W1f's own measured one-sender cycles (1 941.4, 1 945.3, 2 413.4
  and 1 962.6 µs; cycle = T_f + DIFS + σ(W − 1)/2), under the two slot/DIFS families that fit the
  Pi 4's cycle (Mohamed, 2026-11-19):
  * **σ 20 µs, DIFS 50 µs:** W = 4, 4, 51, 6;
  * **σ 9 µs, DIFS 28 µs:** W = 12, 13, 117, 17.
  * They need two new twin options, default-off and gated: `--cwMinList` and `--slotUs`. Under
    the 9 µs slot, ns-3's DIFS = SIFS (10) + 2 × 9 = 28 µs.
* **Two capture ends:**
  * equal power (no capture);
  * the assumed channel of Mohamed's decision: equal mean power, Nakagami m = 1 per frame,
    ns-3's frame-capture model on.
* **ns-3:** 30 seeds × 100 s at each family × capture end.
* **The closed forms** (the standard's W = 32), reported only:

| W1f, 4 boards at 65 frames/s (u = 0.485) | (G5) 0.00961 | (G25) 0.00737 | finite-station 0.00613 | the standard's W = 32 in all three |

* **The hardware value:** W1f's windows at 65 frames/s: the measured loss less the session's
  background b, as W1f scored it.

## Expectations `[agent]`

* **(a):** ns-3 at W = 16 lies near the hardware at 124 frames/s, and above it at 211, as F73
  found at 5 GHz with frame burst on (0.56× at high load).
  * W = 10 raises ns-3's loss further: the spread of the two candidates is wider than the
    hardware's own interval.
  * No closed form is claimed at N = 2.
* **(b):** the Pi 3's large window (51 or 117) makes it nearly never collide. ns-3's loss lies
  below the standard-W closed forms.
  * The capture end lowers it further, as G1 found capture on these boards: a lower bound of
    0.28 % side by side.

## Disclosure

* **Known before this registration:**
  * the hardware results (published or on file);
  * F73–F76, F115, F116, F121–F133;
  * G1;
  * the flags above, computed from rates and airtimes alone.
* **No ns-3 run at any H configuration has been made.**

---

## Outcome, group (a) — added 2026-11-21, after the runs; nothing above this line was changed

**The runs:** ns-3 30 × 100 s per rate and W (`results/raw/uh_ha<f>w<W>{,_runs}.csv`); rule A
30 × 100 s (`results/raw/uh_anchor_rule_a.csv`). The saturated pair was counted again on air from
`--traceMac`, 10 × 20 s (`results/raw/uh_satpair_onair.csv`). The driver's own figure at
400 frames/s offered counts frames the MAC queue discarded, which S1 never counted.

| frames/s | hardware (burst off) | ns-3, W = 10 | ns-3, W = 16 | rule A, W = 10 / 16 | hardware ÷ ns-3, W = 10 / 16 |
|---|---|---|---|---|---|
| 124 | 0.00321 (0.00257–0.00422) | 0.00302 | 0.00228 | 0.00375 / 0.00279 | 1.06 / 1.41 |
| 174 | 0.00516 (0.00353–0.00666) | 0.00768 | 0.00557 | 0.01018 / 0.00708 | 0.67 / 0.93 |
| 211 | 0.00837 (0.00668–0.00970) | 0.01785 | 0.01269 | 0.02286 / 0.01638 | 0.47 / 0.66 |

| the saturated pair (S1) | lost on air | frames/s on air per board |
|---|---|---|
| hardware, burst off | 12.4 % (11.4–13.1) | 259–266 |
| ns-3, W = 10 | 20.1 % | 277.2 |
| ns-3, W = 16 | **13.8 %** | **265.9** |

**What it shows:**
* **The two window candidates conflict, now inside ns-3 itself.**
  * The one-sender cycle (2 050 µs) gives W ≈ 10.
  * The saturated pair is matched only by W = 16: 13.8 % lost and 265.9 frames/s, against 12.4 %
    and 259–266. At W = 10 ns-3 gives 20.1 % and 277 frames/s.
  * This is F115's open conflict, now shown without a formula.
* **The hardware departs from ns-3 in one direction with load, at either W:**
  * more loss than ns-3 at 124 frames/s (1.06–1.41);
  * less at 211 (0.47–0.66).
  * A smaller window moves the high-load gap further away, so **W within its measured candidates
    does not account for it.**
  * The low-load excess matches the one-sender loss that "nothing explains" (0.5–0.9 % lost by
    one saturated sender alone, `results/hw/channel/CONTENTION_RESULTS.md`). The high-load
    deficit matches F115: no tested rule for the radio's own queued frames fits.
  * With frame burst off, these departures cannot be blamed on frame burst.
* **No closed form is claimed at N = 2** (Mohamed, 2026-11-20). Rule A lies 1.24–1.29 times
  above ns-3 here, inside F137's range.

---

## Outcome, group (b) — added 2026-11-21, after the runs; nothing above this line was changed

**The rule, applied before any run** (`analysis/uh.py --flags` → `results/raw/uh_flags.csv`,
committed in `a5fce140` before the runs), 212 windows:

| session | N | windows | S²f²/2 | reproduced |
|---|---|---|---|---|
| W1e | 2, 3 | 48 | 1.43–9.31 % | 0 windows |
| W1f | 4 | 56 | 0.80–3.15 % | 4 windows (65 frames/s) |
| W1j | 4 | 36 | 2.57–3.18 % | 0 windows |
| W1k | 4 | 36 | 2.57–3.18 % | 0 windows |
| W1n s2 | 4 | 36 | 2.57–3.18 % | 0 windows |

**The runs:**
* the audit twin with `--cwMinList` and `--slotUs`, built once with nothing running, then gated:
  * 9/9 identical to the original scenario and the frozen runs;
  * the option checks 16 of 16, including the per-node window (`cwMinList 3,63`) and the slot
    timing: the minimum gap equal to DIFS, and every gap on DIFS + k·σ (1 201 gaps at 20 µs;
    1 267 at 9 µs, DIFS 28 µs);
* 30 seeds × 100 s per family × capture end, N = 4, 65 frames/s, frameSize 173, the redrawn
  source (`results/raw/uh_hb{,_runs}.csv`);
* the four means recomputed from the raw runs without the project's code: all four agree.

**Generated by `python analysis/uh.py --hb`:**

| family (per-board W) | capture end | ns-3 loss (± 1.96 SE) | ns-3 over seeds | hardware ÷ ns-3 |
|---|---|---|---|---|
| σ 20 µs, DIFS 50 µs (W = 4, 4, 51, 6) | equal power | 0.01400 (± 0.00038) | 0.0121–0.0162 | 0.41 |
| σ 20 µs, DIFS 50 µs | assumed channel: Rayleigh, capture model | 0.01160 (± 0.00035) | 0.0096–0.0132 | 0.49 |
| σ 9 µs, DIFS 28 µs (W = 12, 13, 117, 17) | equal power | 0.00620 (± 0.00026) | 0.0043–0.0074 | 0.93 |
| σ 9 µs, DIFS 28 µs | assumed channel: Rayleigh, capture model | 0.00513 (± 0.00018) | 0.0037–0.0058 | 1.12 |

* **The hardware:** W1f's four windows at 65 frames/s, less the session's background
  b = 0.000996, as W1f scored them: **0.00573** (windows 0.00506–0.00675).
* **The closed forms at the standard's W = 32,** as registered: (G5) 0.00961, (G25) 0.00737,
  finite-station 0.00613. The finite-station form is inside the range Mohamed accepted (N = 4,
  u = 0.485 ≤ 0.5).

**What it shows:**
* **The two window families put ns-3 2.3 times apart** (0.0140 against 0.0062 at equal power).
  * The hardware lies between the 9 µs family's two capture ends.
  * It lies below every run of the 20 µs family: that family's lowest seed, 0.0096, is above the
    hardware's highest window, 0.00675.
* **This is not used to choose the family** (Mohamed, 2026-11-19: W is not inferred from a
  session H reproduces). It is consistent with W = 12–17 under a 9 µs slot and a 28 µs DIFS,
  and not with W = 4–6 under the standard slot. Session 3's gap distribution is the separating
  measurement.
* **The expectations `[agent]`:**
  * *ns-3 below the standard-W closed forms:* true for the 9 µs family (0.0051–0.0062, at or
    below the finite-station 0.0061); **not for the 20 µs family** (0.0116–0.0140, above all
    three). With two of four boards at W = 4, same-slot ties are frequent, and the Pi 3's wide
    window does not offset them.
  * *the capture end lowers it:* true for both, by 17 % (0.0140 → 0.0116; 0.0062 → 0.0051).
* **The scope:** one session's four windows of 25 s at one rate. Every other 2.4 GHz window waits
  for the frame-burst-off session (session 2 of `docs/revision/2026-11-20_session_plans.md`).
