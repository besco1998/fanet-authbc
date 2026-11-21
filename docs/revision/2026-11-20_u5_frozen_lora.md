# U5 — two module behaviours in the frozen LoRa arm, measured: a decision request

*2026-11-20. Mohamed (2026-11-20): "in a twin, measure how much (a) the ADRACKReq downlinks and (b)
the missing 4 B MIC each move every published LoRa number. Separate the analytic payload-exclusion
results, which neither touches, from the simulated ones. Write a decision request only if a number
moves beyond its stated precision." **Several printed numbers move beyond their precision, so this is
a decision request.** Nothing in the paper or thesis has been changed.*

## The two behaviours

* **(a) ADRACKReq downlinks.**
  * The frozen scenario `authbc-lora-capacity.cc` builds a network server.
  * In ns-3's LoRaWAN module, each device sets ADRACKReq once it has sent 64 uplinks without a
    downlink, whatever ADR is (`end-device-lorawan-mac.cc:585`). The server answers with a
    downlink (`network-controller-components.cc:97–106`).
  * While it sends, the half-duplex gateway hears nothing. The published runs (about 98 uplinks
    per device in 3 600 s) all contain such replies.
* **(b) The missing 4 B MIC.**
  * The period was set from `authbc.models.lora.frame_time_on_air_s`, which counts LoRaWAN's
    4 B MIC: 363.78 ms for the 218 B frame at SF7, so a 36.378 s period at 1 %.
  * The module sends no MIC: 358.656 ms on air. So the simulated duty was about 1.4 % below
    1 %.
* **The analytic payload-exclusion results** (`lora_budget.csv`: batches, frame sizes, rates per
  data rate) count the MIC, as a real LoRaWAN frame carries it. Neither behaviour touches them.

## How it was measured (`ns3/run_u5_lora.py` → `results/raw/u5_lora{,_runs}.csv`)

* **The configurations:** each published simulated LoRa configuration, rerun through the twin
  `authbc-lora-dc.cc` (its default path is byte-identical to the frozen scenario, 8 of 8). The
  same node counts, seeds 1–30, 3 600 s, a 1 s one-sided jitter.
* **Three variants:**
  * **as published;**
  * **(a)** with no network server (`--noServer`), so no downlinks;
  * **(b)** with the period from the module's own time on air, 35.8656 s.
* **Paired:** each variant uses the same seeds, so its difference from "as published" is the
  effect alone.
* **The mobility study** comes from the other frozen scenario (`authbc-lora-capacity-mobile.cc`),
  which has no twin here. It is not measured.

## N_max, its 95 % interval and the strict reading

| configuration | as published (today) | (a) no downlinks | (b) true 1 % duty |
|---|---|---|---|
| headline | 3, [2,3], strict 0 | 3, [2,3], strict 0 | 3, [2,3], strict 0 |
| eu | 8, [5,8], strict 1 | 8, [5,10], strict 1 | 8, [5,8], strict 1 |
| goursaud | 3, [2,5], strict 1 | 3, [2,5], strict 1 | 3, [2,5], strict 1 |
| shadow500 | 3, [2,3], strict 1 | 3, [2,3], strict 1 | 3, [2,3], strict 1 |
| shadow1000 | 3, [2,3], strict 1 | 3, [2,3], strict 1 | 3, [2,3], strict 1 |

**No N_max moves in any configuration.** The EU gateway preset's interval goes from [5, 8] to
[5, 10] under (a). The headline's interval [2, 3] does not move.

*"Strict 0" for the headline: its rerun starts at N = 2, as the stored `lora_capacity.csv` does.
The published strict reading of 1 comes from the companion run that included N = 1
(`lora_capacity_ci.csv`).*

## Every delivered fraction, to the four decimals the text prints

"≠" marks a change in the fourth decimal against the stored value. "Printed" marks a value that
appears in the paper or thesis text. A "1.0000" match may be coincidental.

| configuration | N | stored | today, as published | (a) no downlinks | (b) true 1 % duty | printed in the text? |
|---|---|---|---|---|---|---|
| headline | 2 | 0.9717 | 0.9717 | 0.9717 | 0.9712 **≠** |  |
| headline | 3 | 0.9598 | 0.9598 | 0.9601 **≠** | 0.9595 **≠** |  |
| headline | 5 | 0.9167 | 0.9167 | 0.9168 **≠** | 0.9161 **≠** |  |
| headline | 8 | 0.8710 | 0.8710 | 0.8716 **≠** | 0.8695 **≠** |  |
| headline | 10 | 0.8292 | 0.8292 | 0.8303 **≠** | 0.8277 **≠** |  |
| headline | 15 | 0.7498 | 0.7498 | 0.7510 **≠** | 0.7460 **≠** |  |
| headline | 20 | 0.6913 | 0.6912 **≠** | 0.6923 **≠** | 0.6871 **≠** |  |
| headline | 30 | 0.5703 | 0.5703 | 0.5720 **≠** | 0.5637 **≠** |  |
| headline | 50 | 0.3755 | 0.3755 | 0.3776 **≠** | 0.3713 **≠** | yes |
| eu | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | yes |
| eu | 2 | 0.9880 | 0.9881 **≠** | 0.9881 **≠** | 0.9877 **≠** |  |
| eu | 3 | 0.9877 | 0.9877 | 0.9882 **≠** | 0.9875 **≠** |  |
| eu | 5 | 0.9690 | 0.9690 | 0.9701 **≠** | 0.9688 **≠** |  |
| eu | 8 | 0.9526 | 0.9526 | 0.9549 **≠** | 0.9522 **≠** | yes |
| eu | 10 | 0.9398 | 0.9398 | 0.9425 **≠** | 0.9387 **≠** | yes |
| eu | 15 | 0.9025 | 0.9025 | 0.9061 **≠** | 0.9014 **≠** | yes |
| eu | 20 | 0.8826 | 0.8826 | 0.8878 **≠** | 0.8812 **≠** |  |
| eu | 30 | 0.8253 | 0.8253 | 0.8333 **≠** | 0.8224 **≠** |  |
| eu | 50 | 0.7134 | 0.7134 | 0.7240 **≠** | 0.7099 **≠** | yes |
| eu | 100 | 0.5071 | 0.5071 | 0.5205 **≠** | 0.5018 **≠** | yes |
| goursaud | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | yes |
| goursaud | 2 | 0.9794 | 0.9793 **≠** | 0.9790 **≠** | 0.9791 **≠** |  |
| goursaud | 3 | 0.9677 | 0.9677 | 0.9679 **≠** | 0.9676 **≠** |  |
| goursaud | 5 | 0.9326 | 0.9326 | 0.9329 **≠** | 0.9322 **≠** |  |
| goursaud | 8 | 0.8976 | 0.8976 | 0.8977 **≠** | 0.8967 **≠** |  |
| goursaud | 10 | 0.8623 | 0.8623 | 0.8625 **≠** | 0.8603 **≠** |  |
| goursaud | 15 | 0.8008 | 0.8008 | 0.8017 **≠** | 0.7988 **≠** |  |
| goursaud | 20 | 0.7533 | 0.7533 | 0.7543 **≠** | 0.7493 **≠** |  |
| goursaud | 30 | 0.6526 | 0.6527 **≠** | 0.6532 **≠** | 0.6483 **≠** |  |
| goursaud | 50 | 0.4856 | 0.4856 | 0.4863 **≠** | 0.4816 **≠** |  |
| shadow500 | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | yes |
| shadow500 | 2 | 0.9717 | 0.9717 | 0.9717 | 0.9712 **≠** |  |
| shadow500 | 3 | 0.9598 | 0.9598 | 0.9601 **≠** | 0.9595 **≠** |  |
| shadow500 | 5 | 0.9167 | 0.9167 | 0.9168 **≠** | 0.9161 **≠** |  |
| shadow500 | 8 | 0.8710 | 0.8710 | 0.8716 **≠** | 0.8695 **≠** |  |
| shadow500 | 10 | 0.8292 | 0.8292 | 0.8303 **≠** | 0.8277 **≠** |  |
| shadow500 | 15 | 0.7498 | 0.7498 | 0.7510 **≠** | 0.7460 **≠** |  |
| shadow500 | 20 | 0.6913 | 0.6912 **≠** | 0.6923 **≠** | 0.6871 **≠** |  |
| shadow500 | 30 | 0.5703 | 0.5703 | 0.5720 **≠** | 0.5637 **≠** |  |
| shadow500 | 50 | 0.3755 | 0.3755 | 0.3776 **≠** | 0.3713 **≠** | yes |
| shadow1000 | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | yes |
| shadow1000 | 2 | 0.9713 | 0.9713 | 0.9717 **≠** | 0.9712 **≠** |  |
| shadow1000 | 3 | 0.9599 | 0.9599 | 0.9601 **≠** | 0.9595 **≠** |  |
| shadow1000 | 5 | 0.9167 | 0.9167 | 0.9168 **≠** | 0.9159 **≠** |  |
| shadow1000 | 8 | 0.8709 | 0.8709 | 0.8716 **≠** | 0.8694 **≠** |  |
| shadow1000 | 10 | 0.8291 | 0.8291 | 0.8303 **≠** | 0.8276 **≠** |  |
| shadow1000 | 15 | 0.7497 | 0.7497 | 0.7510 **≠** | 0.7459 **≠** |  |
| shadow1000 | 20 | 0.6908 | 0.6907 **≠** | 0.6923 **≠** | 0.6868 **≠** |  |
| shadow1000 | 30 | 0.5699 | 0.5700 **≠** | 0.5720 **≠** | 0.5633 **≠** |  |
| shadow1000 | 50 | 0.3753 | 0.3753 | 0.3776 **≠** | 0.3711 **≠** |  |

## What moves beyond its stated precision

* **(a), removing the downlinks:**
  * the EU preset's printed delivery rises by +0.0023 (N = 8: 0.9526 → 0.9549), +0.0027
    (N = 10), +0.0036 (N = 15), +0.0106 (N = 50: 0.7134 → 0.7240) and +0.0134 (N = 100:
    0.5071 → 0.5205);
  * its 95 % interval becomes [5, 10];
  * the headline's printed N = 50 value rises by +0.0021 (0.3755 → 0.3776).
* **(b), the true 1 % duty:** the same printed values fall by 0.0004–0.0053 (EU N = 100:
  0.5071 → 0.5018; headline N = 50: 0.3755 → 0.3713).
* **No N_max, and no headline interval, moves.** The paper's LoRa capacity statement (N_max = 3,
  interval [2, 3]) stands under both.

## Also found: today's build reproduces the stored runs, but not bit for bit at N ≥ 20

* As published, today's build gives every stored mean at N ≤ 15 exactly. At N ≥ 20 it differs
  by at most 6 × 10⁻⁵, from one or two runs per node count (for example a run maximum of 0.42591
  against the stored 0.4255 at N = 50). Sent counts are identical.
* The module, the scenario and the driver have the same source as when the stored files were
  written (2026-07-29 to 08-06). The original and the twin agree today, deterministically.
* The cause is not established: something in the build differs from July's.
* Every printed value reproduces at four decimals, so no printed number is affected.

## Decisions for Mohamed

1. **Whether the printed LoRa values, in thesis ch. 10, are rerun and reprinted.** The choices are
   without the downlinks, at the true 1 % duty, or both; or the values are kept, with the two
   behaviours stated as properties of the simulated configuration. N_max and the headline's
   interval do not change in any case.
2. **Whether the N ≥ 20 reproduction drift needs more than this record,** for example a rebuild
   from a clean tree to see whether it disappears.

## Decided 2026-11-21, and the drift closed

**Mohamed's decisions** (`docs/DECISIONS.md`, 2026-11-21):
* **The printed values in ch. 10 are kept,** with a stated note: the measured shifts of both
  behaviours, no N_max moving, the headline interval unchanged, and the EU interval [5, 8]
  becoming [5, 10] under (a). The wording goes to Mohamed before it goes in.
* **The ADRACKReq reply is realistic behaviour; the missing MIC is the module's omission.** A
  later rerun, if asked for, keeps the server and adds 4 B of payload in place of the MIC.
* **The drift:** one rebuild from a clean tree, recorded, then closed.

**The rebuild** (`ns3/u5_clean_rebuild_check.py`, `results/raw/u5_clean_rebuild_check.csv`):
* a fresh copy of `ns3/ns-3.48`: sources, the lorawan module with its patch, the scratch
  programs, and no `build/` or `cmake-cache/`;
* configured as the original (optimized, examples on, tests off, native optimisations on) and
  compiled with ccache disabled, so every object is new;
* the frozen `authbc-lora-capacity` rerun from it at every published configuration and N ≥ 20,
  seeds 1–30: 480 runs.

**The result:**
* **all 480 runs are identical to today's main build,** in frames sent and received;
* against the stored July files the means still differ, at the fifth decimal, at 12 of 16 node
  counts (by at most 6 × 10⁻⁵, as found on 2026-11-20).
* **So the build tree is not the cause.** A clean build of the same sources gives today's numbers.

**What did change since July** (the package log, `/var/log/dpkg.log*`):
* the compiler did not (gcc 13.3.0-6ubuntu2~24.04.1 since 2026-04-02);
* the C library, which carries `libm`, did: 2.39-0ubuntu8.8 when the July runs were made, then
  8.9 (2026-10-06) and 8.12 (2026-11-18). ns-3's libraries link it dynamically.
* A last-bit change in a `libm` function can move a rare frame across a reception threshold,
  which fits "one or two runs per node count, at N ≥ 20".
* **It is not tested,** because July's library cannot be restored here.

**Closed.** Every printed value reproduces at four decimals, no N_max or interval moves, and the
stored files remain the record.
