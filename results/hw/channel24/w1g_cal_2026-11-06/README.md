# W1g calibration: three runs toward equal senders. 2026-11-06, 03:07–03:25, disclosed, not scored

The rule was fixed beforehand in `PROTOCOL.md` (committed at `fde2ca8` before the first run).

**Each run**
* Blue 2 freshly rebooted; node 4 joined the Pis' cell every time (BSSID not `02:11:87:…`), at
  `FIXED CCK_1M`, with no reset.
* Four windows, all four boards sending 145 B at 125 frames/s each (W1f's A31 rate, offered load
  0.957; plan `plan_cal.txt`).
* Every board ran all four windows and reverted.
* Per-sender loss comes from `results/hw/channel24/w1f_2026-11-05/analysis/sender_receiver.py`
  (`calN/sender_receiver.txt`).
* The Pis stayed as in W1f (side by side, 10–15 cm).

| run | setup | pi-A | pi-B | Pi 3 | TP-Link | spread (rule ≤ 1.5×) | total loss |
|---|---|---|---|---|---|---|---|
| `cal1_90cm` | Blue 2 + TP-Link moved to **90 cm** from the Pis (Mohamed placed it at 90, not the 50 asked) | 5.91 % | 3.09 % | 6.13 % | 3.19 % | 1.98× | 4.58 % |
| `cal2_90cm_piB1500` | as cal 1, **pi-B at 15 dBm** (`iw … set txpower fixed 1500`; read back 15.00 dBm) | 6.22 % | 3.26 % | 5.91 % | 3.47 % | 1.91× | 4.72 % |
| `cal3_90cm_piB800` | as cal 1, **pi-B at 8 dBm** (read back 8.00 dBm) | 5.82 % | 4.68 % | 5.03 % | 4.46 % | **1.30× ✓** | 5.00 % |

**What it shows**
* **Moving the TP-Link to 90 cm ended its dominance.** In W1f it lost 1.5 % against the Pi 4s'
  8 %. Underneath it, pi-B was the strongest Pi.
* **Software control of a Pi's power works.** At 8 dBm, pi-B's frames are lost 7.2 % at the
  distant TP-Link, against 2.6 % at its default. 15 dBm changed almost nothing, so its real
  default is likely near or below 15 dBm.
* **The rule was met at run 3**, with a spread of 1.30×.

**What it also shows: the rule was the wrong proxy, and that is my error in `PROTOCOL.md`.**
* At this rate the model predicts a total loss of 7.70 %. The three runs gave 4.58–5.00 %,
  0.59–0.65× of the model, about the same gap as W1f.
* Equal per-sender *means* do not remove capture. Each receiver still has its own strongest
  sender: in cal 3, pi-A's frames are lost 3.4 % at pi-B and 8.0 % at the TP-Link.
* Capture-free would need every sender received equally strongly *at every receiver*: twelve
  links against four knobs, not reachable with these radios and antennas.
* So W1g, as `PROTOCOL.md` words it (W1f's plan unchanged), would not test the capture reading.
  Mohamed chose instead the re-scoped W1g: the balanced setup kept, the grid moved to bracket both
  crossings (`predictions/W1g.md`).
