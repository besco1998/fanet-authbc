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
