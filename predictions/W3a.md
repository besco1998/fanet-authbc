# W3a — frame loss measured on air at 802.11b 1 Mb/s, traced frame by frame, replayed through the real decoder

*Registered 2026-11-06, before any session. Main open item W3 ("no loss measured on air").
* **Mohamed:** "do the packet-loss measurement"; then pi-A in another room, 1 Mb/s only.
* He approved the plan the same evening.

Code, plan and kit at this commit:
* `analysis/w3a_loss.py`, which reuses unchanged `verifiability_margin` (A3's trace replay through
  `LeanReceiver`), `frame_model` and `hw_preflight.power_check_at`;
* `experiments/channel24/plan_w3a.txt`;
* the kit: `hw/channel/bcast_rx.py`, which since `43a2f1a4` keeps every received sequence number,
  and otherwise the kit of W1k.*

## Why

The paper's loss processes are generated (independent, Gilbert, length-dependent) or simulated
(ns-3 collision traces), and it states "no loss was measured on air". It also states that under
length-dependent loss AUTHBC is below its target where one-record frames lose 5 %: the design's
one known weak spot. This measures real loss traces and asks three of the paper's questions of
them.

## Setup

* **pi-A, the only sender, in another room, three walls from the square** (Mohamed, 23:37). Its
  power is held by `set_txpower_window.sh` and read back.
* **pi-B, the Pi 3 and the TP-Link record every frame**, where they stood for W1j and W1k.
* Channel 11, 802.11b at 1 Mb/s.
  * **pi-B creates the cell** (launched first; a cell created by a freshly booted Pi runs at
    6 Mb/s, F129). pi-A had just been power-cycled.
  * Blue 2 is rebooted for each session; the Pis are not.

## The sessions

**Three, in this order:** pi-A at **1000, 400 and 100 mBm**.

Each is `plan_w3a.txt`:
* R1 (pi-A alone at 600/s, the 1 Mb/s guard);
* then S A L four times;
* then R1 again.

That is 14 windows, about 7 minutes. pi-A sends alone at 50 frames/s, for 22 s a window:
* **S**, 119 B: the frame-linked one-record frame, 147 B on the IP layer;
* **A**, 145 B: AUTHBC's four-record frame, as in W1;
* **L**, 1 000 B.

## Definitions

Per session, receiver and size:
* **the trace:** the lost-frame mask over 0…sent−1, one per window;
* **p̂:** frames lost over frames sent;
* **the mean burst:** lost frames over runs of loss, against the independent 1/(1 − p̂);
* **V:** AUTHBC's four-record frames (b = 4) replayed through `LeanReceiver`, with one key record
  per frame (r = 1, as built) and per four (r = 4, dependent);
* **the independent values:** `frame_model.verifiability(p̂, r)`;
* **the bit-error model:** `frame_model.length_scaled_loss`, reference the S frame.

**Valid session:**
* both R1 windows in 1.9–2.6 ms;
* pi-A's log shows its setting read back, then `auto`;
* every receiver's file present for every window.

The claims read the valid sessions, over the traces with p̂ ≥ 1 %.

## Scored as

* **W3a-1, real loss hurts dependent frames no more than independent loss does.** Pooled over the A
  traces, V(r = 4) is not below its independent value by more than the one-sided 95 % margin. The
  binomial variance is inflated by r for the shared groups. The paper uses independent loss as
  the dependent design's worst case.
* **W3a-2, AUTHBC as built loses only its own frames.** On every A trace, V(r = 1) equals 1 − p̂
  exactly.
* **W3a-3, length dependence no stronger than the bit-error model.** Pooled over the links with
  p̂(S) ≥ 1 %, the 95 % lower bound of p̂(L)/p̂(S) does not exceed the model's ratio at that p̂(S).

**Reported, not scored:**
* each trace's mean burst against independent;
* p̂(A)/p̂(S), AUTHBC's real length penalty, against the model's;
* at the A trace nearest 5 %, whether V(r = 1) ≥ 0.95;
* whether each receiver's loss rises as pi-A's power falls. The TP-Link's did not in the
  one-wall tuning runs: a loss that does not follow the sender's power is more likely the
  receiver's than the channel's.

## My expectations `[agent]`

* **Loss levels:**
  * pi-B about 1 %, 4 % and 8 % at the three settings;
  * the TP-Link 3–7 %, following power weakly or not at all;
  * the Pi 3 under 1 % except perhaps at 100 mBm.
* **W3a-2 holds.** Each four-record frame carries its key record, so a lost frame takes only its
  own records.
* **W3a-1 holds,** with the loss close to independent: mean bursts 1.0–1.1 in tuning, and V(r = 4)
  within 0.003 of independent on the tuning traces.
* **W3a-3 holds:** in tuning, L lost about as often as S, not the several times the bit-error model
  gives.
* **AUTHBC's length penalty p̂(A)/p̂(S) near 1,** that is, below the model's.

## What each outcome means

| outcome | meaning |
|---|---|
| all three hold | real loss at 1 Mb/s is no harder on the design than the paper's generated processes; the paper's "no loss was measured on air" can narrow to the link and setting measured |
| W3a-1 fails | real loss hurts dependent frames more than independent loss: the paper's worst case is not the worst |
| W3a-2 fails | the decoder loses records beyond their own frames under real loss: a defect to find |
| W3a-3 fails | real loss grows with length at least as the bit-error model says: AUTHBC's known weak spot is real on air |

## What it cannot show

* **Flight.** One indoor link, static, at one PHY (802.11b at 1 Mb/s), through walls. Not
  air-to-air, not moving, not the 802.11a of the paper's capacities.
* **Collisions.** pi-A sends alone; collision loss was traced in ns-3 (F98).
* Three receivers and one sender, in one evening.

## Disclosure

* **Tuning runs before this registration** (`results/hw/channel24/w3a_tuning_2026-11-06/`). Each was
  R1 plus one window of each size, A loss shown:

  | placement and power | pi-B | Pi 3 | TP-Link |
  |---|---|---|---|
  | one wall, 10 dBm | 0.09 % | 0.09 % | 7.55 % |
  | one wall, 4 dBm | 0.18 % | 0.36 % | 6.91 % |
  | one wall, 1 dBm | 0.18 % | 1.18 % | 5.27 % |
  | **three walls, 4 dBm** | 3.64 % | 0.18 % | 4.45 % |

  Every rate check was at 1 Mb/s. The last run, minutes before the first session, is that
  session's preflight (Mohamed's rule).
* **On the three-wall A traces**, the decoder gave V(r = 1) = 1 − p̂ exactly, and V(r = 4) within
  0.003 of independent.
* **Two rules were revised before this registration** after reading the tuning data, so that
  agreement within noise cannot read as failure. W3a-1 was first "V(r = 4) ≥ independent on every
  trace"; W3a-3 was "p̂(L)/p̂(S) ≤ the model's ratio". Both are now one-sided interval tests.
* **No window of a W3a session has been run.**

---

## Outcome — added 2026-11-07, 00:45, after the three sessions; nothing above this line was changed

**How it ran.**
* Three sessions, 00:01–00:33, at pi-A 1000, 400 and 100 mBm.
* Every board ran all 14 windows and reverted.
* Node 4 was in the cell at `FIXED CCK_1M`, with every Pi reached.
* Each power setting was read back.
* **All three sessions valid:** rate checks 1 939.5–1 954.7 µs (1 Mb/s), no file missing.
* Scored by `analysis/w3a_loss.py --score`, unchanged since `prereg-W3a` (an empty diff) →
  `results/raw/w3a_w3a_2026-11-06.csv`. One link was recounted independently from the raw JSON
  (100 mBm, pi-B, A: 727/4 400 lost, mean burst 1.645), and agrees exactly.

**The losses** (4 400 frames per size per link):

| pi-A | pi-B S / A / L | TP-Link S / A / L | Pi 3 S / A / L |
|---|---|---|---|
| 10 dBm | 3.14 / 3.43 / 4.45 % | 3.66 / 3.75 / 3.98 % | 0.14 / 0.07 / 0.23 % |
| 4 dBm | 3.27 / 4.09 / 5.48 % | 4.77 / 6.73 / 4.89 % | 0.27 / 0.45 / 0.68 % |
| 1 dBm | 13.02 / 16.52 / 29.73 % | 10.89 / 12.77 / 23.45 % | 3.11 / 4.70 / 12.57 % |

**Scored: all three held.**
* **W3a-1, held.** Pooled over the seven A traces at p̂ ≥ 1 %, V(r = 4) = **0.8467** against
  **0.8326** independent (margin 0.0068). All seven were at or above their independent value.
* **W3a-2, held.** V(r = 1) = 1 − p̂ exactly on all nine A traces.
* **W3a-3, held.** p̂(L)/p̂(S) = **2.02** (95 % lower bound 1.91) against the bit-error model's
  **5.04**, at p̂(S) = 6.0 %, over seven links.

**Reported, not scored:**
* **Burstiness.** Near independent at 10 and 4 dBm (mean bursts 1.01–1.15 against 1.00–1.07).
  Bursty at 1 dBm: 1.12–1.76 against 1.03–1.42.
* **The loss swings strongly between 22-second windows.** At 1 dBm, pi-B's L windows read 22.5 /
  38.2 / 20.1 / 38.2 %, the Pi 3's 5.9 / 22.2 / 1.8 / 20.4 %. The channel is not stationary at
  that scale.
* **AUTHBC's length penalty, p̂(A)/p̂(S) = 1.24,** with a 95 % interval of 1.06–1.45 from a
  bootstrap over the 36 paired S/A cycles, against the model's 1.14. The excess over the model is
  not significant. A computed per frame, it would have looked significant: the window-to-window
  swings make the frames of one window far from independent.
* **The A trace nearest 5 %** (1 dBm, Pi 3): p̂ = 4.71 %, V(r = 1) = 0.953, meets 0.95.
* **Every receiver's loss rose as pi-A's power fell,** the TP-Link's included (A: 3.75 → 6.73 →
  12.77 %). So at three walls its loss is the channel's. The flat readings through one wall were
  not repeated here.

**My expectations:**
* **Right:** W3a-1, W3a-2, W3a-3; burstiness near independent at the higher powers.
* **Wrong:**
  * pi-B "about 1 %, 4 %, 8 %" read 3.4 / 4.1 / 16.5 %, a steeper fall between 4 and 1 dBm;
  * the TP-Link "following power weakly or not at all": it followed it;
  * "p̂(A)/p̂(S) near 1, below the model's": it is 1.24, its interval containing the model's 1.14.

**What it means. On this link, real loss is no harder on the design than the paper's generated
processes:**
* it is independent to mildly bursty, which helps dependent frames;
* AUTHBC as built loses only its own frames;
* loss grows with length far less than the bit-error model says for long frames, and about as it
  says at AUTHBC's own size.

The paper's known weak spot, that AUTHBC's longer frame loses more, is real on air at about the
size the model gives, not worse within the interval. F134.

**Limits:** one indoor link through walls, static, 802.11b at 1 Mb/s, one sender, one evening.
