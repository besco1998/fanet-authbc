# Hardware session plans for Mohamed's approval (work packages G and H)

*2026-11-20. Three sessions, each run only after Mohamed approves its plan and is at the boards
(prompt §1). Standing rule (Mohamed, 2026-11-19): **every session logs per-sender signal
strength.** Nothing here has been run.*

**The kit today, and what each plan adds:**
* **What exists:**
  * `bcast_rx.py` keeps every received sequence number per source (`seqs`, since W3a), but no
    timestamps and no RSSI;
  * `run_window_plan.sh` (the 2.4 GHz runner) logs neither frame burst nor signal strength;
  * `run_adhoc_contention.sh` (the 5 GHz runner) sets and logs frame burst;
  * `set_txpower_window.sh` sets a Pi's fixed power through brcmfmac's qtxpower override.
* **Each kit change below** is tested on made-up data and committed before its session, as
  before.

**Boards:**
* the three Pis: pi-A and pi-B (BCM4345/6), and the Pi 3 (BCM43430);
* channel 11, 802.11b at 1 Mb/s, 145 B frames, the jittered sender, unless stated;
* Blue 2, with the TP-Link, has been offline since the 2026-11-08 power cut, and none of these
  plans needs it.

## Kit changes, common to all three sessions

1. **Signal strength per sender:** `run_window_plan.sh` writes `iw dev wlan0 station dump` at each
   node after every window: the signal and its average for each peer MAC. The per-window file
   joins the session's raw data.
2. **Frame burst:** the runner sets frame burst off on every Broadcom board before the windows
   (`frameburst.sh set 0`) and logs its value before and after, as `run_adhoc_contention.sh`
   does for 5 GHz. A board whose value cannot be read or set is listed as such, and a session
   with any board not off is void.
3. **Arrival timestamps:** `bcast_rx.py` gains an option to keep each frame's kernel receive
   time (`SO_TIMESTAMPNS`), off by default. Session 3 needs it.

## Session 1 — G2: capture against power difference (two senders saturated, one receiver)

**Purpose:** q, the share of a collided frame that is still received, against the senders' power
difference. It is measured where the model needs it: the 4 dB threshold of ns-3's rule (D).

**Layout:**
* pi-A and pi-B as senders, the Pi 3 as the receiver, on a line or triangle with taped
  positions;
* each distance measured and recorded before the first window. No board moves during the
  session (photographed at the start and the end).

**Steps:**
1. **Preflight (W1k's):**
   * each board alone at 600 frames/s, its cycle in band (F122's rule: a sender that defers
     cannot be seen any other way);
   * a 50 frames/s background.
2. **Power steps:** pi-A fixed at P0 (its default), then P0 − 3, − 6, − 10, − 15 dB
   (`set_txpower_window.sh`). pi-B stays at its default throughout.
3. **At each step:**
   * **(a) Signal alone:** pi-A alone at 50 frames/s for 25 s, then pi-B alone, each with the
     Pi 3's station dump. This checks that the chip honours the fixed power: pi-A's signal at
     the Pi 3 must fall by the step ± 1.5 dB. Otherwise the step is void and reported.
   * **(b) Capture windows:** both senders saturated (600 frames/s offered), three windows of
     25 s.
4. **Backgrounds,** a 50 frames/s single sender, between steps.

**The measured quantity, with its model stated** (the logs give counts per sender, not
collisions):
* with two saturated senders, each collision involves both, so p_c is shared:
  loss_A = p_c(1 − q_A) + ℓ_A and loss_B = p_c(1 − q_B) + ℓ_B, with ℓ from the backgrounds;
* at a power difference large enough that the stronger frame always wins (q_strong + q_weak = 1),
  p_c = (loss_A − ℓ_A) + (loss_B − ℓ_B), and q of each sender follows;
* at small differences only q_A + q_B ≤ 1 is identified, and the bound is reported;
* the saturated-pair loss also gives F75's p_c at equal power, for comparison.

**Predictions** (registered before the session, from U-CAP's curve for 802.11b):
* q_weak = 0 at every step;
* q_strong = 0 below about 4 dB of SINR, and 1 from 5 dB.

Stated in advance: real chips are not ns-3. A gradual curve, or capture of a later, stronger
frame (message-in-message), is a finding.

**About 75 minutes of board time.**

## Session 2 — H: the 2.4 GHz contention sessions again, frame burst logged off

**Purpose:** H can reproduce in ns-3 only the 2.4 GHz sessions where no station's queue builds up,
because frame burst was never logged at 2.4 GHz (Mohamed, 2026-11-19). This session repeats the
others with frame burst off.

**What runs:**
* W1e's plan (`plan_w1h.txt` family) on the three Pis: groups of 2 and 3 at occupancy 0.50, 0.70
  and 0.85;
* the preflight, rate checks and backgrounds as in W1e;
* the 1 m square's layout (W1j's, re-measured with a tape) or W1e's side-by-side layout, as
  Mohamed chooses. One layout per session.

**Logged:**
* frame burst before and after (off on all three);
* the station dump per window;
* sequence numbers (existing).

**Predictions:** registered before the session, at each window's own N, frame and rate:
* ns-3 at each candidate window setting (session 3 narrows them);
* the Poisson and (G25) losses;
* the finite-station form where Mohamed accepted it (N = 3, u ≤ 0.5).

**About 40 minutes of board time.**

## Session 3 — separating the contention window from slot and DIFS (Mohamed, 2026-11-19)

**Why:**
* the one-sender cycle (1 944–1 946 µs against 1 864 µs on air) fits W ≈ 4 with the standard
  20 µs slot and 50 µs DIFS, and also W = 16 with a 9 µs slot and a 28 µs DIFS;
* a mean cannot separate them, but the gap distribution can:
  * W = 4, σ = 20, DIFS 50 gives gaps after the frame on {50, 70, 90, 110} µs: mean 80,
    standard deviation 22 µs;
  * W = 16, σ = 9, DIFS 28 gives {28, 37, …, 163} µs: mean 95.5, standard deviation 41.5 µs.

**Steps:**
1. **One saturated sender** at a time (pi-A, pi-B, the Pi 3), 25 s each, frame burst off. The
   receiver keeps arrival timestamps (kit change 3).
   * **The gap distribution:** the minimum gap gives T_f + DIFS, the lattice spacing gives σ,
     and the range gives W.
   * Software timestamps jitter by microseconds to tens of microseconds; the variance survives
     that where the lattice may not.
   * Reported per board.
2. **A saturated pair** (pi-A with pi-B), three windows of 25 s, each the other's only receiver,
   so capture is impossible:
   * the collision loss, about 2/(W + 1) for saturated broadcast at N = 2, is marked as
     model-dependent;
   * by Mohamed's rule it is used for W only because **no session H reproduces** is used for
     this.

**About 20 minutes of board time.**

## Order, and what waits on what

* **Order:** session 3 first (it narrows H's window settings), then session 1 (capture), then
  session 2. All three fit one evening of about 2.5 hours with breaks.
* **H's first group** (the 5 GHz frame-burst-off anchor, and the 2.4 GHz sessions with no queue)
  needs no new session and goes ahead.
* **H's capture end** is the assumed channel Mohamed set: equal mean power, Nakagami m = 1, ns-3's
  capture model. Session 1 would later let it be replaced by measured powers, if he chooses.
