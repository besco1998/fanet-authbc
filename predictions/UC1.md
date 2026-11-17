# U-C1 — the loss expression's three terms, one by one, in ns-3 (802.11a, 6 Mb/s)

*Registered 2026-11-17, before any U-C1 run; the time is the commit's. Task of 2026-11-17, work
package C, item C1. The model is in `docs/revision/2026-11-17_unified_model_spec.md` and
`src/authbc/models/unified_capacity.py`. C1 is one of the two items that can falsify it.*

## What is run

* **Cells.** C (146 B, 50 frames/s) and D (173 B, 12.5 frames/s): the lean format at one and
  four records per frame, 50 records/s.
* **Loads.** The node counts where the loss expression's root gives 1, 2, 5 and 10 % loss:

| | 1 % | 2 % | 5 % | 10 % |
|---|---|---|---|---|
| C | N = 14 | 21 | 34 | 45 |
| D | 51 | 77 | 121 | 161 |

* **The runs.** 10 seeds at each load, 20 simulated seconds, the designated source (a jitter of
  one period). They use the audit twin `authbc-links-audit.cc` with `--traceMac`:
  `ns3/run_unified.py --cells C --n … --seeds 10 --trace DIR --stem unified_c1`.
* **The classifier.** `analysis/unified_c1.py` classifies every frame, as fixed below.

## How a lost frame is classified (fixed now)

**Groups.** A *group* is a set of transmissions whose air intervals overlap. With equal power,
all of them are lost (audit item 8). Each lost frame takes its group's class:

1. **Detection window:** the group's starts are not all at one instant (spread > 0). The audit
   found every spread below 4 µs.
2. **Same-slot tie:** all starts at one instant, and every frame in the group *drew a backoff*:
   a backoff draw by its station falls between its enqueue and its start.
3. **Zero-backoff start after a busy period:** all starts at one instant, and at least one frame
   in the group drew no backoff. That is a frame that found the medium idle, or in the gap after
   a busy period, was pre-empted, and kept zero slots (audit item 1).

**Shares.** Each class's share is its lost frames divided by all frames sent, per seed, then the
mean over seeds with a bootstrap 95 % interval over seeds.

**Also measured:**
* **a:** the share of frames that arrive to a busy medium (busy from a start + 4 µs to its end).
* **K:** for each frame that arrived to a busy medium, the number of other stations holding a
  frame (enqueued, not yet sent) when that busy period ends, averaged over such frames.

## Predictions (the loss expression at its fixed point, `unified_capacity.loss_terms`)

| cell | N | tie | zero backoff after busy | detection window | p | a | K |
|---|---|---|---|---|---|---|---|
| C | 14 | 0.00247 | 0.00096 | 0.00609 | 0.00952 | 0.1708 | 0.2348 |
| C | 21 | 0.00690 | 0.00227 | 0.01009 | 0.01926 | 0.2615 | 0.4338 |
| C | 34 | 0.02603 | 0.00612 | 0.01880 | 0.05096 | 0.4245 | 1.0452 |
| C | 45 | 0.06203 | 0.01075 | 0.02731 | 0.10009 | 0.5517 | 2.0266 |
| D | 51 | 0.00299 | 0.00095 | 0.00593 | 0.00987 | 0.1866 | 0.2604 |
| D | 77 | 0.00818 | 0.00218 | 0.00974 | 0.02010 | 0.2821 | 0.4776 |
| D | 121 | 0.02768 | 0.00540 | 0.01726 | 0.05034 | 0.4387 | 1.0775 |
| D | 161 | 0.06623 | 0.00947 | 0.02512 | 0.10081 | 0.5698 | 2.1045 |

**Tolerance (the model author's).** A predicted quantity **holds** at a load if it lies within
±10 % of the measured mean, or inside the measured 95 % interval. Otherwise it **fails**. The
tolerance is not widened after the runs.

**Scored:** each of the three terms, p, a and K, at each of the eight loads (48 cases), reported
term by term.

## Expectations and disclosure `[agent]`

* **The middle term was derived for rule A, which ns-3 does not follow** (audit item 1). Under
  ns-3 its population is pre-empted zero-slot frames. If it fails, that is reported as the
  expression having the wrong form for ns-3's rule, not tuned.
* **Known before this registration:**
  * the audit's single trace at C, N = 35, seed 1 (not a registered load) had 879 collision
    groups, 304 of them with all starts at one instant, and 575 spread within 4 µs;
  * 15 357 of 34 953 frames arrived to a busy medium (0.44), against a = 0.42 predicted at N = 34.
  * **I therefore expect the detection-window share above its prediction, and a near it.**
* **The classifier was developed on that one audit trace,** never on a U-C1 run.
* **No U-C1 run has been made.**

---

## Outcome — added 2026-11-17, after the runs; nothing above this line was changed

**The runs.** 80, as registered: cells C and D at four loads, 10 seeds each, through the audit
twin with `--traceMac` (`ns3/run_unified.py`, `results/raw/unified_c1_runs.csv`). Every frame
was classified by `analysis/unified_c1.py` → `results/raw/unified_c1_scored.csv`.

**Scored: 17 of 48 cases held. The decomposition fails; the totals hold.**

| quantity | held | how the prediction compares with ns-3 |
|---|---|---|
| **a**, the share of frames arriving to a busy medium | **8 / 8** | within 0.7 % at every load |
| **p**, the total loss | **7 / 8** | +2.5 … +8.9 %; fails only at C, N = 45 (+13.2 %) |
| tie | 0 / 8 | +16 … +388 %: the expression's ties are 1.2–4.9 times ns-3's |
| zero-backoff start after a busy period | 1 / 8 | +9 … +337 % |
| detection window | 1 / 8 | +5 % at C, N = 14, then −15 … −67 %: ns-3's is up to three times the expression's |
| K | 0 / 8 | +13 … +71 % |

**What it means.**
* **The expression's total loss and its busy-arrival share are right.** How it splits the loss
  among the three mechanisms is not, under the classification registered.
* **Ties against the detection window, mainly.** At the higher loads most of ns-3's lost frames
  start a few µs apart, not at one instant.
* **The middle term is overpredicted at every load,** consistent with its derivation for rule A.
  Under ns-3's rule its population is the pre-empted zero-slot frames (audit item 1).
* **K is overpredicted throughout,** increasingly with load.

**Reported, not scored: why the tie/detection split fails** (`analysis/unified_c1.py --diagnose`
→ `results/raw/unified_c1_diagnostic.csv`; added after the scoring).
* **The mechanism.** ns-3 counts each station's slots from that station's own backoff start
  (`GetBackoffStartFor`, channel-access-manager.cc:789–798). A station that arrived to an idle
  medium starts at its arrival + DIFS, off the other stations' slot grid.
* **So two counters that expire "in the same slot" can start up to a slot apart.** If they are
  within 4 µs they collide, and the registered rule files them as "detection window". If they
  are further apart, the second senses the first and there is no collision at all.
* **The evidence.** Collisions in which every frame drew a backoff but the starts were not at one
  instant make up most of the detection-window class at the higher loads (0.0186 of 0.0384 at D,
  N = 121).
* **Counting every all-drew collision as a tie, at any spread,** the expression's tie term lies
  +3.3 … +17.8 % above ns-3's at all eight loads, against +16 … +388 % under the registered
  classification.

**The answer the task asks for.** The expression has the right total and the right busy share,
but its three terms do not map one to one onto ns-3's mechanisms:
* its "same-slot tie" assumes one slot grid for all stations, which ns-3 does not have;
* its middle term was derived for an access rule ns-3 does not follow;
* its K is too large.

Any revision of the loss expression is to be registered and tested on new runs.

**Expectations.** "Detection window above its prediction and a near it": both held.
