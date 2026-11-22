# W1r — W1e's contention windows again, frame burst off, three Pis side by side (session 2)

*Registered 2026-11-21, before the session. Plan: session 2 of
`docs/revision/2026-11-20_session_plans.md`, approved by Mohamed on 2026-11-21 with his changes
(`docs/DECISIONS.md`): the side-by-side layout; each window sized so that each sender's expected
lost frames are at least 25, the count stated here; windows lengthened or repeated as needed.
Code: `analysis/w1r.py`. Kit: `hw/channel/run_window_plan2.sh`, `rssi.sh`, tested off the boards.*

## Why

* **W1e, the original session (2026-11-05):** valid, 11 of 12 points held. It ran at the driver's
  default, with frame burst on (F75).
* **ns-3 has no frame burst for broadcast,** so U-H could reproduce none of W1e's windows. The
  chance that a board held two frames was 1.4–9.3 % (`uh.flags`, `predictions/UH.md` (b)).
* **This session repeats them with frame burst off,** so that ns-3 and the hardware can be compared
  window by window.

## The session (`experiments/channel24/plan_w1r.txt`, 66 windows, 69 minutes of windows)

* **The layout:** W1e's, the three Pis side by side 10–15 cm apart, with positions taped and
  photographed.
* **The radio:** channel 11, 802.11b 1 Mb/s, the 145 B frame, the redrawn sender, frame burst off
  on all three, read back before and after.
* **The windows:** W1e's, in its order (`dsss_three.plan_s1`):
  * the groups AB, AC, BC and ABC at occupancy 0.50, 0.70 and 0.85 (131, 183 and 222 frames/s
    per board for a pair; 87, 122 and 148 for the trio);
  * four windows each, a 50 frames/s control window after every four;
  * a rate check per board before and after.
* **Each contention window's length** (Mohamed, 2026-11-21): every sender's expected lost frames
  are at least 25, under the lowest prediction of any candidate below. A sender sends for
  seconds − 3, so seconds = max(25, 3 + 25/(f·p_min)), rounded up to 5 s (`seconds_for`).
  * The longest windows, 150–155 s, are the groups with the Pi 3 at occupancy 0.5. Its window
    (51 or 117 slots) makes it lose least.

## The loss, as W1d defined it (`dsss_three.window_rows`, registered at `prereg-W1d`)

* **The loss:** a group's frames received by the group's other members, over frames sent × (n − 1).
  The silent board is not a receiver of a pair, so at N = 2 capture cannot occur. Only the trio
  has two capture ends.
* **The usable-window rule and the background b** (the mean loss of the control windows) are
  W1d's. The hardware value of a point is the mean over its usable windows of the loss less b,
  as W1e scored it.

## Predictions (`python analysis/w1r.py --predict`, `results/raw/w1r_predictions.csv`)

* **ns-3:**
  * the audit twin, N = 2 or 3, frameSize 173, 802.11b 1 Mb/s, the designated periodic source;
  * 30 seeds × 100 s;
  * each board's window from its one-sender cycle under each family (`uh.board_windows`:
    pi-A, pi-B and the Pi 3 at W = 4, 4, 51, or W = 12, 13, 117 with `--slotUs=9`);
  * equal power, and for the trio also the assumed channel of Mohamed's 2026-11-19 decision
    (Nakagami m = 1 per frame, ns-3's capture model at 5 dB).
* **The closed forms,** reported only, at the standard's W = 32 as U-H reported them:
  * (G5) and (G25), the latter outside its stated range here (N − 1 ≥ 8);
  * the finite-station form where Mohamed accepted it (N = 3, u ≤ 0.5: the trio at 0.50).

| group | u | frames/s per board | ns-3, σ 20/DIFS 50: equal power | with capture | ns-3, σ 9/DIFS 28: equal power | with capture | (G5), W = 32 | (G25), W = 32 | finite-station, W = 32 | window (s) | expected lost frames, least sender |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AB | 0.5 | 131 | 0.00605 | — | 0.00254 | — | 0.00409 | 0.00295 | — | 80 | 25.6 |
| AC | 0.5 | 131 | 0.00156 | — | 0.00129 | — | 0.00409 | 0.00295 | — | 155 | 25.7 |
| BC | 0.5 | 131 | 0.00156 | — | 0.00131 | — | 0.00409 | 0.00295 | — | 150 | 25.3 |
| ABC | 0.5 | 87 | 0.00923 | 0.00753 | 0.00421 | 0.00349 | 0.00743 | 0.00552 | 0.00397 | 150 | 25.6 |
| AB | 0.7 | 183 | 0.01730 | — | 0.00668 | — | 0.00831 | 0.00543 | — | 25 | 26.9 |
| AC | 0.7 | 183 | 0.00341 | — | 0.00250 | — | 0.00831 | 0.00543 | — | 60 | 26.0 |
| BC | 0.7 | 183 | 0.00341 | — | 0.00244 | — | 0.00831 | 0.00543 | — | 60 | 25.4 |
| ABC | 0.7 | 122 | 0.02053 | 0.01742 | 0.00845 | 0.00728 | 0.01661 | 0.01104 | — | 60 | 27.0 |
| AB | 0.85 | 222 | 0.04071 | — | 0.01436 | — | 0.01309 | 0.00792 | — | 25 | 70.1 |
| AC | 0.85 | 222 | 0.00874 | — | 0.00530 | — | 0.01309 | 0.00792 | — | 25 | 25.8 |
| BC | 0.85 | 222 | 0.00874 | — | 0.00532 | — | 0.01309 | 0.00792 | — | 25 | 26.0 |
| ABC | 0.85 | 148 | 0.03882 | 0.03344 | 0.01566 | 0.01326 | 0.02822 | 0.01691 | — | 30 | 28.9 |

## Scored as

* **The family:** the one W1p's registered rule selects. If W1p selects none, or both, every point
  is reported against both families, and nothing below is scored.
* **Per point (12):** ns-3 is **consistent** if its value lies inside the hardware's 95 % interval
  over the point's usable windows, by Student t with n − 1 degrees of freedom:
  * for a pair, the equal-power value;
  * for the trio, any value between its two capture ends.
  * The count consistent of 12 is reported, with each point's hardware ÷ ns-3 ratio.
* **Validity, fixed now:**
  * the six rate checks inside W1d's band (1.9–2.6 ms);
  * frame burst reading 0 on every board before and after;
  * at least three usable windows per point.
  * Otherwise the session is void, or the point is not scored.
* **Checked after the session and reported:** each sender's actual lost frames per window.

## My expectations `[agent]`

* With frame burst off, the hardware's high-load deficit against ns-3 (W1e's pattern, F115) should
  shrink.
* The low-load excess, the one-sender loss that nothing explains (`CONTENTION_RESULTS.md`), should
  remain, so the hardware lies above ns-3 at occupancy 0.50 and nearer it at 0.85.
* AB separates the families by itself (0.00605 against 0.00254 at 0.50).

## Disclosure

* **Known before this registration:**
  * W1e's results;
  * U-H (a) and (b);
  * W1p's predictions;
  * every 2.4 GHz finding (F115–F134).
* **No frame-burst-off session at 2.4 GHz has been run.**


## Outcome — added 2026-11-22, after the session; nothing above this line was changed

* **The session:** `results/hw/channel24/w1r_2026-11-22`, windows 22:09:47–23:19:07. All 66
  windows ran on every board, and every board reverted. Scored with
  `python analysis/w1r.py --score results/hw/channel24/w1r_2026-11-22 --family none`, which
  writes `results/raw/w1r_w1r_2026-11-22.csv`.
* **The preflight:** `w1r_2026-11-22_pre` came back GO at 22:07, with cycles of 2 022.5, 2 158.6
  and 2 572.0 µs.
* **The layout deviated from this registration, as decided before the run.** The boards were
  side by side **20 cm** apart, not 10–15 cm. Mohamed chose to keep 20 cm and record it
  (`LAYOUT.md`; `docs/DECISIONS.md`, "W1r's spacing"). No prediction was changed.
* **The family:** W1p's rule selected neither family (`predictions/W1p.md`, Outcome). So, as
  registered, every point is reported against both families and **nothing is scored.**

### Validity — held

* **Frame burst** read 0 before and after on all three boards.
* **The six rate checks** were all in band:
  * pi-A 2 196.0 and 2 046.2 µs;
  * pi-B 2 144.2 and 2 121.9 µs;
  * the Pi 3 2 344.5 and 2 360.2 µs.
* **The background b** was 0.000909, from 12 controls, against a limit of 0.01.
* **All 48 contention windows were usable,** 4 of 4 per point.

### The points (reported against both families; not scored)

| point | hardware, loss − b (95 % CI) | ns-3 σ 20/DIFS 50 (trio: equal–capture) | ratio | inside? | ns-3 σ 9/DIFS 28 | ratio | inside? | fewest lost frames, any sender, any window |
|---|---|---|---|---|---|---|---|---|
| AB at 131/s, u = 0.5 | 0.00369 (0.00328–0.00410) | 0.00605 | 0.61 | no | 0.00254 | 1.45 | no | 40 |
| AC at 131/s, u = 0.5 | 0.00408 (0.00349–0.00467) | 0.00156 | 2.62 | no | 0.00129 | 3.16 | no | 81 |
| BC at 131/s, u = 0.5 | 0.00495 (0.00456–0.00534) | 0.00156 | 3.18 | no | 0.00131 | 3.77 | no | 98 |
| ABC at 87/s, u = 0.5 | 0.00662 (0.00562–0.00761) | 0.00923–0.00753 | 0.72 / 0.88 | **yes** | 0.00421–0.00349 | 1.57 / 1.89 | no | 66 |
| AB at 183/s, u = 0.7 | 0.00813 (0.00728–0.00897) | 0.01730 | 0.47 | no | 0.00668 | 1.22 | no | 26 |
| AC at 183/s, u = 0.7 | 0.00821 (0.00687–0.00955) | 0.00341 | 2.41 | no | 0.00250 | 3.28 | no | 82 |
| BC at 183/s, u = 0.7 | 0.00941 (0.00817–0.01064) | 0.00341 | 2.76 | no | 0.00244 | 3.86 | no | 89 |
| ABC at 122/s, u = 0.7 | 0.01242 (0.01010–0.01474) | 0.02053–0.01742 | 0.61 / 0.71 | no | 0.00845–0.00728 | 1.47 / 1.71 | no | 60 |
| AB at 222/s, u = 0.85 | 0.01619 (0.00951–0.02286) | 0.04071 | 0.40 | no | 0.01436 | 1.13 | **yes** | 53 |
| AC at 222/s, u = 0.85 | 0.02215 (0.01465–0.02965) | 0.00874 | 2.53 | no | 0.00530 | 4.18 | no | 90 |
| BC at 222/s, u = 0.85 | 0.02640 (0.02443–0.02837) | 0.00874 | 3.02 | no | 0.00532 | 4.96 | no | 114 |
| ABC at 148/s, u = 0.85 | 0.02951 (0.02448–0.03453) | 0.03882–0.03344 | 0.76 / 0.88 | **yes** | 0.01566–0.01326 | 1.88 / 2.23 | no | 76 |

* **Inside the hardware's 95 % interval:**
  * σ 20/DIFS 50 at 2 of 12 points, the trio at 0.50 and at 0.85;
  * σ 9/DIFS 28 at 1 of 12, AB at 0.85. That interval is the widest of the twelve (±41 % of its
    mean, from 4 windows).
* **Every sender lost at least 25 frames in every window,** as the sizing intended. The fewest
  was 26 (AB at 0.70, where 26.9 was expected).
* **The independent check:** a separate script recomputed every point and gave the same values.
  It imports no project code and counts the receivers' sequence lists. One interval edge differs
  in the fifth decimal, from rounding. In all 48 windows, the receivers' JSON counts equal their
  per-frame timestamp files exactly. The same script reproduces W1e's scored values from W1e's
  files.

### My expectations, against the outcome

* **"With frame burst off, the high-load deficit against ns-3 should shrink": it held in
  direction, but the cause is not identified.**
  * At 0.85, against the same ns-3 values, the ratio rose toward 1 where the hardware lay below
    a family. AB went from 0.28 to 0.40 (σ 20) and from 0.80 to 1.13 (σ 9). The trio went from
    0.65 to 0.76 (σ 20, equal power).
  * Two things changed since W1e, frame burst and the spacing, so the change is not attributed
    to frame burst (see below).
* **"The low-load excess should remain: above ns-3 at 0.50 and nearer it at 0.85": half
  wrong.**
  * At 0.50 the hardware lies above σ 9 at all four points (1.45–3.77). It lies above σ 20 only
    in the two pairs with the Pi 3 (2.62, 3.18).
  * "Nearer at 0.85" held only for AB (1.45 to 1.13 against σ 9). AC, BC and the trio moved
    further away (3.16 to 4.18, 3.77 to 4.96, and 1.57–1.89 to 1.88–2.23).
* **"AB separates the families by itself": partly.**
  * AB excluded σ 20 at every occupancy (0.40–0.61 of it).
  * It excluded σ 9 at 0.50 and 0.70 (1.45 and 1.22 of it), but not at 0.85.
  * The hardware lies between the two families, as W1p found.

### Seen after scoring — not a result

* **The pairs with the Pi 3 lose as much as AB, or more; ns-3 puts them far below it.**
  * Against AB at the same rate, AC and BC lose 1.01–1.63× AB on the hardware. ns-3 gives
    0.20–0.26× (σ 20) and 0.37–0.52× (σ 9).
  * ns-3's low value comes from the Pi 3's window, inferred from its longer one-sender cycle
    (W = 51 or 117, `uh.board_windows`). With a window that large, the Pi 3 rarely collides.
  * **Hypothesis, not tested:** the Pi 3's extra time per frame is not spent in a wider random
    backoff. It may be a per-frame gap outside contention. Testing it needs a registered check.
* **Both directions of every pair lose about equally.** The difference is at most 0.19
  percentage points, and the Pi 3's frames lose the larger share in all six of its pairs:

| pair | rate | first → second: lost / sent | second → first: lost / sent |
|---|---|---|---|
| AB | 131/s | 1→2: 181/40348 = 0.45 % | 2→1: 190/40348 = 0.47 % |
| AC | 131/s | 1→3: 362/79648 = 0.45 % | 3→1: 433/79648 = 0.54 % |
| BC | 131/s | 2→3: 409/77028 = 0.53 % | 3→2: 494/77028 = 0.64 % |
| AB | 183/s | 1→2: 146/16104 = 0.91 % | 2→1: 145/16104 = 0.90 % |
| AC | 183/s | 1→3: 359/41724 = 0.86 % | 3→1: 402/41724 = 0.96 % |
| BC | 183/s | 2→3: 401/41724 = 0.96 % | 3→2: 460/41724 = 1.10 % |
| AB | 222/s | 1→2: 317/19536 = 1.62 % | 2→1: 351/19536 = 1.80 % |
| AC | 222/s | 1→3: 433/19536 = 2.22 % | 3→1: 468/19536 = 2.40 % |
| BC | 222/s | 2→3: 515/19536 = 2.64 % | 3→2: 552/19536 = 2.83 % |

  So the excess is not one receiver failing to hear. Equal power with collisions that destroy
  both frames would give equal losses; nothing more is inferred from it.
* **Against W1e:** W1r's loss is higher at 11 of 12 points, 1.15–1.99× W1e's, and lower at one
  (the trio at 0.70, 0.93×). The largest increases are in the pairs with the Pi 3 (1.33–1.99×). Frame burst (on in W1e, off here), the
  spacing (10–15 cm, now 20 cm) and the day all differ, so **the increase is not attributed to
  any one of them.**
