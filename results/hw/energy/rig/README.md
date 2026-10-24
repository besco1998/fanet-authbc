# Rig checks — what the meter was, the day it was checked

`hw/rig_check.py` judges a capture of the meter on the sequence `hw/rig_selftest.py` runs
(`hw/RIG.md` §8). No energy figure is taken on a rig that has not passed. Finding F78.

## 2026-10-09 — pi-B (`authbc-pi4b`) on channel 1: FAILED, for two different reasons in one morning

| file | what it shows |
|---|---|
| `fault-ground-20261009-load-and-line.csv` | before the check existed: the voltage reading at 4.82 V idle, 4.39 V with four cores busy, and **4.59 V with the sync line high and nothing else changed** |
| `fault-ground-20261009-line-toggles.csv` | the sync line toggled five times with no load: 4.582 V high, 4.874 V low, every cycle; then an unconnected pin toggled as a control, with no effect. **The board's ground was not tied to the meter's** |
| `rigcheck-samples-20261009T045024Z.csv`, `selftest-…045024Z.json`, `rigcheck-20261009T045024Z.json` | ground re-seated: the line no longer moves the voltage (+5 mV). **With every core busy the board draws 1.17 A, the supply falls to 4.73 V and the board throttles within 40 ms**; the kernel logs the under-voltage |
| `…045618Z.*` | the same, six minutes later: it reproduces, and the idle voltage afterwards is 42 mV off because the board is still throttled |
| `…050437Z.*` | a third time, after the leads were looked at again: every meter-side line passes; the board still logs an under-voltage with every core busy (1.14–1.17 A, 4.73 V) |
| `reference-other-branch-pi-a-four-cores-20261009.csv` | **the other branch, for comparison:** pi-A, fed through sensor 2, with four cores busy for six seconds — 5.01 V at 1.07 A, no under-voltage. **0.19 Ω against 0.47 Ω.** The weakness is in the sensor-1 branch, not in the board on it; July's captures, made on that branch, show the same 0.45–0.49 Ω |

The first two captures were made by hand, with the sync pin driven from the shell, and are not
in the sequence the check expects; the check was written between them and the third.

**Not measured on that rig:** anything.

## 2026-10-09, later — pi-B moved to the other branch, channel 2: PASSED

Mohamed swapped the two boards' supplies and sensors. `…20261009T051248Z.*`: every line passes. The
voltage moves by 1 mV with the sync line; with every core busy the board draws its full power
(+3.49 W) at 5.07 V; it has logged no under-voltage since it booted; it sees 0.18 Ω; and one
busy core adds 0.757 W, where July's constant from the other board and the other sensor is
0.749 W. Judged as channel 1, the same capture fails the line "this channel is the board under
test", as it should. The energy runs of that day were made on this rig.

## What a pass looks like

July's captures (`../e2e/`, `../full_samples.csv`) were made before this check existed. Their
meter-side quantities are held by `tests/test_energy_reduction.py`: voltage independent of the
sync line within 4 mV, windows of sixty seconds by both clocks within 0.1 %, the chip's power
register equal to voltage × current within a milliwatt, no throttling in any reported window.
