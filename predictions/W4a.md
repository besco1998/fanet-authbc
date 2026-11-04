# W4a — a record size no telemetry of the schema can exceed, and AUTHBC's capacity there

*Registered 2026-11-05, before any capacity was computed for the frames below. Main open item W4
(`docs/OPEN_ITEMS.md` §2a), option (a), on Mohamed's word "for now do the desk work". Code at this
commit: `analysis/worst_case_records.py`.*

## Why

AUTHBC's records are delta-coded. Their size depends on how much the telemetry changes from one
record to the next, and that has been measured on synthetic telemetry and on twelve real logs at
5 Hz ("Telemetry Is Synthetic", paper §4.4). Collecting more flights would narrow the doubt.
**Bounding the size removes it:** if AUTHBC still carries more nodes when every record is as large
as the schema allows, no telemetry inside the schema can reverse the result.

## The bounds (definitions; the frame lengths follow from them)

Every frame is built from chained records, encoded by `wire_v2`, decoded and verified (the F45
rule: a size is the length of an emitted byte string). The header is also at its largest
(`src` = 65 535, `base_seq` near 2³²).

* **Schema bound.** Two records A and B sit at opposite extremes of every field's range in
  `bench/telemgen.py` and alternate, so every delta is the full span of its field:
  * ts 0 ↔ 2³²−1;
  * lat ±90°; lon ±180°; alt −500 m ↔ 50 km;
  * each velocity ±30 m/s;
  * battery 0 ↔ 100 %; mode 0 ↔ 7.
* **Physical bound, at 50 Hz (20 ms per record).** The key record is at the schema's extremes. The
  deltas follow from the schema's speed limit of ±30 m/s, i.e. 60 cm per record:
  * lat 54 units; lon 3 089 units (at 89° latitude); alt 60 cm;
  * the whole velocity range in one record (bounding, not physical);
  * battery ±1 %; mode ±7; ts +63 ms.
* **Per-record signing (cell C), for comparison:**
  * at the schema bound (its one key record at A);
  * at its smallest (every value 0, `src` = `base_seq` = 0);
  * at its published mean.

| frame | bytes | key record | delta record |
|---|---|---|---|
| AUTHBC (b = 4), schema bound | **233** | 27 | **28** |
| AUTHBC, physical bound | 188 | 27 | 13 |
| AUTHBC, published mean | 173.0 | — | — |
| per-record, schema bound | 150 | 27 | — |
| per-record, published mean | 146.76 | — | — |
| per-record, smallest | **125** | 9 | — |

Cross-check by hand. The key record is 5+5+5+4+2+2+2+1+1 = 27 B (ts, lat, lon, alt, three
velocities, battery, mode). The schema delta is 5+5+5+4+2+2+2+2+1 = 28 B (the battery's ±100 takes
two bytes zig-zagged). The physical delta is 1+1+2+1+2+2+2+1+1 = 13 B.

## What is computed

* For each frame, the crossing of V = 0.95 at its frame rate (AUTHBC 12.5 /s, per-record
  50 /s):
  * by the closed form of docs/02 §6g;
  * by the event model (`dcf_own_queue`, the standard rule, 30 seeds × 20 s).
* The ratio AUTHBC / per-record for each pairing of the three AUTHBC frames with the three
  per-record frames.
* **Break-even.** The AUTHBC frame size at which its crossing equals per-record signing's at its
  *smallest*, which is the most favourable case for per-record signing. It is converted to a
  delta-record size: δ* = 28 + (F* − 233)/3, by the closed form.

Model only. The claim is an ordering, and the model's agreement with ns-3 on capacity against
frame size is already registered: F2, 7 of 7 within 3.4 %; F5, 6 of 6 within 1.73 %.

## My expectations `[agent]`

* **W4a-1.** AUTHBC at the physical bound against per-record at its published mean: ratio ≥ 3.3.
* **W4a-2.** AUTHBC at the schema bound against per-record at its published mean: ratio ≥ 2.5.
* **W4a-3.** AUTHBC at the schema bound against per-record at its smallest, the most conservative
  pairing: ratio ≥ 2.0.
* **W4a-4.** Break-even δ* > 28 B: no telemetry of the schema reverses the ordering.
* **W4a-5.** The closed form and the event model agree within 3 % at every frame.

## What it cannot show

* **The physical bound rests on the schema's speed limit (±30 m/s).** A faster aircraft has
  larger position deltas. The schema bound covers it, up to the schema's ranges.
* **The wire format does not enforce the schema.** `Record` admits any integer, so a sender
  outside the schema can make records larger still. Break-even says how much larger they would
  have to be.
* The capacities are the model's (see above). Burst and capture effects are outside them, as for
  the published capacities.

## Disclosure

* The frame lengths in the table were computed before this was written. They follow from the
  definitions, and building them checked that every frame decodes and verifies.
* **No crossing, ratio or break-even had been computed** for these frames.
* The closed form for the published frames is known (C 35.8, D 126.7: W1a's planning). These
  expectations are mine, made with that in mind.
