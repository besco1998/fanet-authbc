# Contention on real radios — prediction, written and committed BEFORE any measurement

*Written 2026-10-09. No board has been switched on for this experiment. Open item G4.*

## Why this exists

Every 802.11 capacity in the paper and the thesis is simulated. The hardware measurement of
August 2026 had one transmitter, so it measured airtime and link loss and **no contention at
all**. A supervisor's first question about the capacity result is whether a radio behaves as
the simulator does. This is the experiment that can begin to answer it with the boards on
hand.

It does not measure a capacity: reaching the 95 % crossing takes dozens of nodes. It measures
the thing the capacities are *made of* — the fraction of frames lost when several stations
contend at a known offered load — and compares it with the access-rule model of `docs/02` §6g,
which reproduces every simulated capacity within 1.2 % and has never been tested outside a
simulator.

## What is run

N boards in one ad-hoc cell on 5 GHz (channel 36, broadcast at 6 Mb/s, as in August). **Every
board sends and receives.** Each sends one 1400 B broadcast frame per period, at an instant
drawn uniformly within the period (`hw/channel/bcast_tx.py --redraw`), and counts the frames it
receives from each other board by sequence number (`bcast_rx.py`).
`hw/channel/run_adhoc_contention.sh` is the session; it is `run_adhoc_sweep.sh` with those two
changes and nothing else.

*Why redrawn instants.* Two boards' clocks differ by a few parts per million. Strictly periodic
senders would keep nearly the same relative phase for a whole window, and a window would sample
one phase configuration — the artifact of finding F51. Redrawing is the traffic source the
simulated capacities use.

| | |
|---|---|
| boards | 2 and 3 with what is on hand (two Pi 4, one Pi 3B+); 4 and 5 if more are found |
| loads | three per N: the cell's frames fill 0.50, 0.70 and 0.85 of the medium |
| windows | four of 25 s per load (22 s of sending); twelve windows, about six minutes per N |
| quantity | frames received over frames sent, summed over every ordered pair of boards |

A window is **usable** only if no frame was dropped before the air (`tx_dropped = 0`), every
board achieved at least 98 % of its nominal rate, and under 1 % of its frames were sent a whole
period late. These three conditions are fixed now.

## The prediction

`results/raw/contention_hw_predictions.csv` (`python analysis/contention_hw.py --predict`):
the event model, thirty seeds of 20 s, with the measured link loss of 2.3 × 10⁻⁴ added.

| boards | frames/s per board | occupancy | predicted loss | band |
|---|---|---|---|---|
| 2 | 124 | 0.50 | **0.29 %** | 0.18–0.40 % |
| 2 | 174 | 0.70 | **0.64 %** | 0.39–0.89 % |
| 2 | 211 | 0.85 | **1.40 %** | 0.85–1.95 % |
| 3 | 83 | 0.50 | **0.66 %** | 0.21–0.92 % |
| 3 | 116 | 0.70 | **1.52 %** | 0.47–2.12 % |
| 3 | 141 | 0.85 | **3.00 %** | 0.92–4.20 % |
| 4 | 62 | 0.50 | **1.02 %** | 0.32–1.41 % |
| 4 | 87 | 0.70 | **2.15 %** | 0.66–3.00 % |
| 4 | 106 | 0.85 | **4.23 %** | 1.28–5.91 % |
| 5 | 50 | 0.50 | **1.22 %** | 0.38–1.70 % |
| 5 | 70 | 0.70 | **2.89 %** | 0.88–4.04 % |
| 5 | 85 | 0.85 | **5.27 %** | 1.60–7.37 % |

**The load-bearing prediction is the two-board one: measured loss within 0.6–1.4 times the
model's.** With two boards the only receiver of a frame is the other transmitter. If the two
transmit together, each misses the other's frame because it is itself sending; no third radio
exists to *capture* one of the two. So the two-board case tests the access rule — ties between
backoff counters and the window in which a transmission cannot yet be sensed — with nothing
else in the way.

**With three or more boards: 0.3–1.4 times the model's.** A third board that hears two
colliding frames at different strengths may decode the stronger. Capture can only reduce loss,
and the model has none, so the band is open downward. A result well below the model there is
capture, not a failure of the access rule.

**Also predicted:** loss rises with load at every N; and at equal occupancy it rises with N.

*Power.* At the weakest point (two boards, 124 frames/s) four windows carry about 21,800
frames and the model expects about 63 lost: a relative standard error near 13 %, against a
band of ±40 %. Every other point has more.

## Is the prediction one simulator's, or two?

The model had been compared with ns-3 only at 28 nodes and above. Before registering, the
twelve points were run in ns-3 as well (`--ns3-check`, thirty seeds,
`results/raw/contention_hw_ns3_check.csv`). These are two simulations of one standard, not
evidence about a radio:

| boards | ns-3 loss over the model's |
|---|---|
| 2 | 0.82, 0.84, 0.91 |
| 3 | 1.05, 1.02, 0.96 |
| 4 | 1.00, 1.04, 1.00 |
| 5 | 1.05, 1.01, 0.98 |

At three to five nodes they agree within 5 %. **At two nodes the model is 9–18 % above ns-3**,
more than the standard error (3–8 %): a small bias of the model at the smallest network,
not seen before because nothing so small had been simulated. The registered band contains both.
If the boards land nearer ns-3 than the model at two nodes, that is this bias and will be
reported as such.

## What each outcome means

| outcome | reading |
|---|---|
| two boards inside 0.6–1.4× | the access rule and a detection window of a few microseconds describe a real radio at this load; the simulated capacities rest on a mechanism that has now been seen on hardware, at small N |
| two boards **above** 1.4× | a real radio loses more than the rule says: a longer detection window, or losses the rule does not have. The simulated capacities are then optimistic, and the paper must say by how much |
| two boards **below** 0.6× | fewer collisions than the rule allows — most likely the boards do not send when asked (check the usable-window conditions first), or their backoff differs from the standard's |
| three boards below 0.3× | capture. The bench geometry decides it; repeat with the boards equidistant before concluding anything |
| loss does not rise with load | the measurement is not measuring contention; stop and find out why |

## What this cannot show

* **Not a capacity.** Nothing here reaches 5 % loss at the operating frame rate. The capacities
  stay simulated; what changes is whether their mechanism has been observed.
* **One chip family, one band, one room.** Broadcom radios at a few metres.
* **The boards' medium access is in firmware.** Whether it uses the timing of the 802.11a DCF
  or of EDCA's best-effort class (an inter-frame space one slot longer) is not visible from the
  host. The difference is 9 µs in a frame of 2 ms.
* **A Python sender.** Its send instants are as exact as the operating system's timer. The
  usable-window conditions bound that; they do not remove it.

## Disclosure

The bands were chosen before any run and with no hardware data. They are wide. A first
measurement of a mechanism on real radios does not justify ±5 %, and a band that could only be
met by luck would teach nothing by being missed.

The session script could not be tested: no board was reachable when it was written. It differs
from the proven sweep script in the ways listed above, the two Python programs were exercised
on the loopback interface, and the script has a probe mode — one short window — to be run
first.
