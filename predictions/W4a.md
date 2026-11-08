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

---

## Outcome — added 2026-11-05, after the run; nothing above this line was changed

Registered at `1dc2301` (tag `prereg-W4a`). `analysis/worst_case_records.py` (unchanged since) →
`results/raw/w4a_worst_case.csv`; event model 30 seeds × 20 s.

| frame | bytes | crossing, model | closed form |
|---|---|---|---|
| AUTHBC, published mean | 173.0 | 124.15 | 126.70 |
| AUTHBC, physical bound | 188 | 118.50 | 120.33 |
| AUTHBC, **schema bound** | 233 | **103.78** | 104.56 |
| per-record, published mean | 146.76 | 34.99 | 35.75 |
| per-record, schema bound | 150 | 34.68 | 35.35 |
| per-record, **smallest** | 125 | **37.73** | 38.86 |

**Ratio AUTHBC / per-record (model):**

| AUTHBC frame ↓ / per-record frame → | published mean | schema bound | smallest |
|---|---|---|---|
| published mean | 3.55 | 3.58 | 3.29 |
| physical bound | **3.39** | 3.42 | 3.14 |
| schema bound | **2.97** | 2.99 | **2.75** |

**Break-even** (closed form): AUTHBC would have to send frames of **819 B** to fall to
per-record signing's capacity at its smallest frame. That is delta records of **223 B**, eight
times the 28 B the schema allows.

| | expected | outcome |
|---|---|---|
| W4a-1 | physical bound vs published per-record ≥ 3.3 | **held**: 3.39 |
| W4a-2 | schema bound vs published per-record ≥ 2.5 | **held**: 2.97 |
| W4a-3 | schema bound vs per-record at its smallest ≥ 2.0 | **held**: 2.75 |
| W4a-4 | break-even δ* > 28 B | **held**: 223 B |
| W4a-5 | closed form and model within 3 % at every frame | **held at the edge**: 0.75–2.99 %; the closed form is always above the model, most for the shortest frame |

**What it means.** No telemetry inside the schema can reverse the ordering. At the largest record
the schema allows, set against per-record signing at its smallest possible frame, AUTHBC still
carries **2.75 times** as many nodes. With realistic dynamics (the physical bound) it carries
3.39 times, against 3.55 at the published mean. The synthetic telemetry decides the *size* of the
advantage, between 2.75 and 3.55, never its *sign*. To lose it, a sender would have to put 223 B
into each delta record, which is outside the schema and eight times its largest.

**Checks (Law 6).**
* Every bound frame decoded to its records and verified before any capacity was computed.
* Its lengths equal the hand arithmetic.
* The published means reproduce the model crossings of `dcf_model_vs_ns3.csv` (C 34.99 exactly;
  D 124.15 against 123.70, as in W1a).
* W4a-5 held by 0.01 percentage points (2.99 % against 3 %), and is reported as that. It is not a
  defect: the closed form's tie term is first order, and it errs in one direction.
