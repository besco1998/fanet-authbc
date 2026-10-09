# Two saturated senders — the textbook case, written BEFORE its runs

*Written 2026-10-09, after runs R1 and R2 of `docs/CONTENTION_HW_FRAMEBURST_EXPECTATIONS.md`
and while R3 was on air. No run with two saturated senders exists. Open item G4.*

## Why one more experiment

Two predictions have failed today, in the same direction:

* **Two boards at occupancy 0.85** lose 0.64 % with the chip's frame-burst mode on and 0.84 %
  with it off. The standard's access rule gives 1.40 % (the model) or 1.27 % (ns-3). Off is
  just outside the registered band (0.848–1.947 %); on is far outside.
* **One saturated sender** puts a frame on air every 2.019 ms with frame burst on and every
  2.050 ms with it off. The standard's rule gives 2.078 ms. Prediction P1 of the follow-up
  (2.070–2.095 ms with frame burst off) failed.

So frame burst accounts for part of the gap and not all of it, and this radio's own spacing is
not the standard's in either state. What is not known is **where** the difference is. Two
places are possible, and they predict different things for a case not yet measured:

* **in the contention itself** — how two radios that both want the medium draw and count their
  backoff. Then two saturated senders collide less often than the standard says.
* **in how one radio's queued frames follow one another** — which matters only when a queue
  holds two frames or more, and never changes what happens when two radios contend frame by
  frame. Then two saturated senders collide as the standard says.

Two saturated senders is also the case every textbook treatment of the access rule starts
from, and it needs nothing from the traffic generator: no send instants, no periods, no
queueing model.

## The runs

`run_adhoc_contention.sh` unchanged, with each board **offered 400 frames/s** — 800 in total
where the medium carries about 490. Four windows of 25 s per run.

| run | frame burst |
|---|---|
| S1 | off |
| S2 | on (the driver's setting) |

What is counted is read at the receiver, because a saturated sender's own count includes
frames still queued when it stops: for each sender, the sequence numbers the other board spans
from the first frame it heard to the last are the **frames on air**; the share of them that did
not arrive is the **loss**; frames on air over that time is the **rate on air**
(`analysis/contention_hw.py --saturated`). The window conditions of the first registration do
not apply — a saturated sender is late by construction.

## The predictions

**S-P1 — what the standard's rule gives, frame burst off (S1).** Two stations, a contention
window of 16 that never doubles: each attempts in a slot with probability 2/17, so
**11.8 % of the frames on air are lost** (the event model of `docs/02` §6g: 11.9 %), each
sender puts **260 frames/s** on air, and 459 frames/s are delivered in total. Band, as in the
first registration: 0.6–1.4 times — **7.1–16.5 %**.

**What today's data lead me to expect instead,** stated so that it can be held against the
result: at occupancy 0.85 the boards lost 0.60 times the model's figure with frame burst off.
If that ratio belongs to the contention, S1 shows about **7 %**, at the lower edge of the band
or under it. I think this the likelier outcome. If S1 shows about 12 %, the difference is in
how queued frames follow one another, and the contention is the standard's.

**S-P2.** With frame burst on (S2) the loss is lower than with it off.

**S-P3.** The two senders' rates on air differ by less than 10 % in each run. The standard's
rule is symmetric; a large difference would mean one board holds the medium.

## What each outcome means

| S1, frame burst off | reading |
|---|---|
| 7.1–16.5 %, near 11.8 % | In contention this radio follows the standard. The shortfall at occupancy 0.85 comes from how a radio sends its own queued frames; the simulated capacities, which are reached with every station's queue nearly empty, are not touched by it |
| below 7.1 % | The contention itself is not the standard's on this chip. A simulated capacity is then the capacity of the standard's rule and of radios that keep to it, and the paper says so |
| above 16.5 % | A radio loses more than the rule says when pressed; the simulated capacities are optimistic for it |

## What this cannot show

It is one chip, two boards, one room. Two saturated stations are the opposite of the operating
point of the paper, where 124 stations each send 12.5 frames/s; the experiment locates a
difference and does not measure a capacity.

## Disclosure

Written after R1 and R2 were reduced. The band is the first registration's. The reducer for
saturated sessions was written today and tested on made-up files. The receiver program gained
bookkeeping fields that change nothing that is counted: the first sequence number heard (before
R2), and the time each sender was first and last heard (after R3 was started).

---

## Outcome — added 2026-10-09, after the runs; nothing above this line was changed

Finding F76. `results/hw/channel/saturated_2nodes_fb_{off,on}.csv`, eight values each.

| | predicted | frame burst off (S1) | frame burst on (S2) | |
|---|---|---|---|---|
| S-P1: frames on air lost | 11.8 %, band 7.1–16.5 % | **12.40 %** (sd 0.70) | 12.14 % (sd 0.42) | **held** |
| frames/s on air per sender | 260 | 262.7 | 264.8 | — |
| S-P2: on loses less than off | — | — | lower by 0.26 points, inside the scatter | held in sign; no effect shown |
| S-P3: the two senders within 10 % | — | 2.4 % | 5.4 % | **held** |

**My stated expectation — about 7 % — was wrong.** By the table above: in contention this
radio follows the standard, and the shortfall at occupancy 0.85 comes from how a radio sends
its own queued frames.

⚠️ One sentence of this file, written before R3 was reduced, did not survive it: "frame burst
accounts for part of the gap and not all of it". R3 showed no part.
