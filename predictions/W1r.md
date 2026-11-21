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
