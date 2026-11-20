# U-C7 — duty-cycled ALOHA over C channels, in ns-3's LoRaWAN module

*Registered 2026-11-20, before any U-C7 run; the time is the commit's. Work package E of
`docs/prompts/NEXT_PHASE_PROMPT.md` (Mohamed, 2026-11-19: "C7: run it").*

## The prediction under test

    N_max = 1 + floor( C·ln(1/(1 − ε)) / (2d) )

* C channels, each node at its duty-cycle limit d, ε = 0.05.
* **Claimed independent of frame length, batch and data rate.**
* Its continuous form, N* = 1 + C·ln(1/(1 − ε))/(2d), is where the per-frame loss of unslotted
  ALOHA, 1 − exp(−2(N − 1)d/C), reaches ε (`unified_capacity.n_aloha_duty`).

## How it is run (`ns3/authbc-lora-dc.cc --channels=C`, driver `ns3/run_c7.py`)

**The scenario:** `authbc-lora-capacity.cc`'s, through its twin.
* The twin's default path is identical to the original (`ns3/verify_lora_twin.py`: 8 of 8).
* **With `--channels=C`:**
  * each frame's channel is drawn at random from C channels (868.1 + 0.2k MHz);
  * one sub-band of duty 1, so the MAC enforces no duty: the duty is set by the period, as E11
    states for the original;
  * one gateway listening on all C with 8 reception paths;
  * the `aloha` collision matrix (any same-SF, same-channel overlap destroys both frames:
    `lora-interference-helper.cc:113–120`, `:277`);
  * SF7 on every device, the ideal channel (no link loss), the scenario's 1 000 m disc.

**What the module has that the formula omits, and what is done about each:**
* **Capture:** the module allows it to be switched off, and it is (`aloha`, not `goursaud`).
* **SF orthogonality:** one SF only.
* **Downlinks:** with a network server, every device sets ADRACKReq after 64 uplinks without a
  downlink, ADR or not (`end-device-lorawan-mac.cc:585`).
  * The server answers it (`network-controller-components.cc:97–106`), and its ADR component
    masks devices back to channels 0–2 (`adr-component.cc:133–143`).
  * The half-duplex gateway hears nothing while it sends.
  * **The `--channels` path therefore builds no network server and no forwarder.** The gateway
    still receives, and counts, every uplink.
  * Checked at a setting that is not registered (d = 5 %, 50 B, N = 10): no gateway transmission,
    loss falling as 1/C.
* **Gateway reception paths:** 8, never the limit at these loads.

**"Every node at its duty-cycle limit":**
* the period is P = ToA/d, the shortest interval the limit allows;
* a one-sided jitter U(0, 2·ToA) is added to each interval, so that the phases do not freeze
  (bimodal delivery, F26);
* the duty cycle is therefore **d_eff = ToA/(P + ToA) = d/(1 + d)**, and the prediction uses it;
* ToA is the module's own at SF7 (its `durations.txt`): 66.816 ms for a 20 B payload, 333.056 ms
  for 200 B.

**The grid:**
* d ∈ {0.1, 1, 10} % × C ∈ {1, 3, 8} × two payloads (20 B, 200 B) = **18 cells**;
* each run lasts 60 mean intervals per node.

**The method:**
* **N* ≥ 5:** a pilot of 5 seeds on seven node counts at ±5 % steps around N*, then **30 seeds** on
  seven node counts by U-C2's rule (centre round(pilot crossing), step max(1, round(2 %)));
* **2 ≤ N* < 5:** N = 2 … 7, 30 seeds;
* **N* < 2:** N = 2, 3, 4, 30 seeds;
* the delivered fraction is received over sent at the gateway, averaged over seeds;
* **scoring:** `analysis/uc7.py --score` → `results/raw/uc7_scored.csv`.

## Predictions (`python analysis/uc7.py --markdown`, generated)

| cell | d | C | payload | ToA (ms) | period (s) | d_eff | **N_max** | N* | loss at N = 2 | scored by |
|---|---|---|---|---|---|---|---|---|---|---|
| D0.1C1L20 | 0.001 | 1 | 20 B | 66.816 | 66.8160 | 0.000999 | **26** | 26.67 | 0.0020 | crossing ±5 % (N_max reported) |
| D0.1C1L200 | 0.001 | 1 | 200 B | 333.056 | 333.0560 | 0.000999 | **26** | 26.67 | 0.0020 | crossing ±5 % (N_max reported) |
| D0.1C3L20 | 0.001 | 3 | 20 B | 66.816 | 66.8160 | 0.000999 | **78** | 78.02 | 0.0007 | crossing ±5 % (N_max reported) |
| D0.1C3L200 | 0.001 | 3 | 200 B | 333.056 | 333.0560 | 0.000999 | **78** | 78.02 | 0.0007 | crossing ±5 % (N_max reported) |
| D0.1C8L20 | 0.001 | 8 | 20 B | 66.816 | 66.8160 | 0.000999 | **206** | 206.38 | 0.0002 | crossing ±5 % (N_max reported) |
| D0.1C8L200 | 0.001 | 8 | 200 B | 333.056 | 333.0560 | 0.000999 | **206** | 206.38 | 0.0002 | crossing ±5 % (N_max reported) |
| D1C1L20 | 0.01 | 1 | 20 B | 66.816 | 6.6816 | 0.009901 | **3** | 3.59 | 0.0196 | N_max exact |
| D1C1L200 | 0.01 | 1 | 200 B | 333.056 | 33.3056 | 0.009901 | **3** | 3.59 | 0.0196 | N_max exact |
| D1C3L20 | 0.01 | 3 | 20 B | 66.816 | 6.6816 | 0.009901 | **8** | 8.77 | 0.0066 | crossing ±5 % (N_max reported) |
| D1C3L200 | 0.01 | 3 | 200 B | 333.056 | 33.3056 | 0.009901 | **8** | 8.77 | 0.0066 | crossing ±5 % (N_max reported) |
| D1C8L20 | 0.01 | 8 | 20 B | 66.816 | 6.6816 | 0.009901 | **21** | 21.72 | 0.0025 | crossing ±5 % (N_max reported) |
| D1C8L200 | 0.01 | 8 | 200 B | 333.056 | 33.3056 | 0.009901 | **21** | 21.72 | 0.0025 | crossing ±5 % (N_max reported) |
| D10C1L20 | 0.1 | 1 | 20 B | 66.816 | 0.6682 | 0.090909 | **1** | 1.28 | 0.1662 | loss at N = 2 above eps |
| D10C1L200 | 0.1 | 1 | 200 B | 333.056 | 3.3306 | 0.090909 | **1** | 1.28 | 0.1662 | loss at N = 2 above eps |
| D10C3L20 | 0.1 | 3 | 20 B | 66.816 | 0.6682 | 0.090909 | **1** | 1.85 | 0.0588 | loss at N = 2 above eps |
| D10C3L200 | 0.1 | 3 | 200 B | 333.056 | 3.3306 | 0.090909 | **1** | 1.85 | 0.0588 | loss at N = 2 above eps |
| D10C8L20 | 0.1 | 8 | 20 B | 66.816 | 0.6682 | 0.090909 | **3** | 3.26 | 0.0225 | N_max exact |
| D10C8L200 | 0.1 | 8 | 200 B | 333.056 | 3.3306 | 0.090909 | **3** | 3.26 | 0.0225 | N_max exact |

**Scored, fixed now and not widened:**
* **N* ≥ 5 (10 cells): the continuous crossing ±5 %.** The integer N_max is reported, not scored.
  At several cells N* sits a few hundredths above an integer (78.02, 206.38): the loss at N_max is
  0.04997 at D0.1C3, which seed noise cannot resolve.
* **2 ≤ N* < 5 (4 cells): N_max exact.** The 30-seed mean delivery is at least 0.95 at N_max and
  below it at N_max + 1.
* **N* < 2 (4 cells): the loss at N = 2 above ε.**
* **Independence of length** is scored by the same rule at both payloads. Each cell is scored on
  its own.

**A failure** is reported with its side:
* *optimistic:* the model admits more nodes than ns-3;
* *conservative:* fewer.

It is explained with evidence, or raised with Mohamed.

## Expectations `[agent]`

* **Most cells hold.** The module with `aloha` is close to the formula's pure ALOHA. At the
  unregistered check point (d = 5 %, C = 1, 3, 8; two seeds) the loss was 0.540–0.568,
  0.220–0.252 and 0.079–0.098, against 0.576, 0.249 and 0.102.
* **The likeliest misses are at small N.**
  * There the exponential and the exact random-phase form 1 − (1 − 2d/C)^(N−1) differ: 0.166
    against 0.182 at N = 2, d = 10 %, C = 1.
  * Partly frozen phases also widen the spread over seeds.
  * Neither moves an integer N_max here.
* **Length should not matter,** within the seeds' spread.

## Disclosure

* **Known before this registration:**
  * the formula;
  * the frozen LoRa arm's results (N_max = 3 at 1 %, one channel, F19–F38);
  * the twin's checks at d = 5 %, 50 B, N = 10, which is not a registered cell.
* **No run has been made** at any registered cell.
