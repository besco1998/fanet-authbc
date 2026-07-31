# Adding mobility: what it costs, what it buys, and what I recommend

*Requested by Mohamed 2026-07-30, after audit F26 recorded that all four NS-3 scenarios use
`ConstantPositionMobilityModel` — a Flying Ad-hoc Network study in which nothing flies.*

> ## ⚠️ MOHAMED'S DIRECTION (2026-07-30) — DEFERRED, DO NOT START YET
>
> Mobility will be added as **separate, new scenario files**, not by modifying the existing ones.
> The frozen static scenarios stay exactly as they are, so the current results remain reproducible
> and the mobility work becomes an additive comparison rather than a migration.
>
> It is to be preceded by a **deep literature survey of what mobility scenarios and models FANET /
> UAV-swarm papers actually use** — speeds, models, node counts, areas, durations — so that our
> configuration is anchored to published practice and our results are comparable to theirs, rather
> than to parameters we chose ourselves. That survey is the reference we test against.
>
> **Scheduled after the current work. Keep in mind, do not begin.**

**Recommendation (unchanged, and consistent with the above): the LoRa arm is where mobility buys
something; the 802.11 saturation arm is where it cannot, because Bianchi and Ma & Chen contain no
position term.** Reasoning below.

---

## 1. First, what mobility physically changes

Two separate effects, often conflated. Numbers computed with our own models at the operating point.

### (a) Doppler / fast fading — *within* a frame

Coherence time `T_c ≈ 0.423 / f_D` (Clarke), against our frame durations:

| speed | 802.11a @5.8 GHz | vs frame (1.97 ms) | LoRa @868 MHz | vs ToA (364 ms) |
|---|---|---|---|---|
| 5 m/s | T_c = 4.38 ms | 2.2× longer — safe | T_c = 29.2 ms | **0.08× — 12 fades per frame** |
| 20 m/s | T_c = 1.09 ms | **0.55× — decorrelates mid-frame** | T_c = 7.3 ms | **0.02× — 50 fades per frame** |
| 30 m/s | T_c = 0.73 ms | **0.37×** | T_c = 4.9 ms | **0.01×** |

**This is the important finding.** At realistic UAV speeds the channel decorrelates *during* a
transmission on both arms — and catastrophically so on LoRa, whose 364 ms frame spans tens of
coherence intervals. LoRa's chirp spreading is robust to narrowband fades, which is part of why the
technology works at all, but our simulation models **no fading whatsoever** (F25: even enabling
correlated shadowing changes nothing at our ranges, because the link margin is 17–29 dB).

### (b) Topology change — *across* the run

| speed | distance per frame (802.11) | per LoRa frame | per 3600 s run |
|---|---|---|---|
| 5 m/s | 9.9 mm | 1.8 m | **18 km** |
| 20 m/s | 39 mm | 7.3 m | **72 km** |
| 30 m/s | 59 mm | 10.9 m | **108 km** |

Within a single frame the geometry is effectively frozen on both arms. Over a 3600 s run it is
meaningless: a node at 20 m/s covers 72 km, so a static 1000 m disc describes nothing real.

---

## 2. What it would cost

| cost | 802.11 arm | LoRa arm |
|---|---|---|
| **code** | small — swap the mobility model, ~20 lines | same |
| **runtime** | negligible | negligible |
| **frozen artifacts** | **every 802.11 CSV re-derived**, plus the validation bands re-established | LoRa CSVs re-derived |
| **statistical** | ⚠️ **large** — mobility adds a variance dimension on top of the seed variance F26 already showed to be under-sampled at 3 seeds | ⚠️ **larger** — compounds with the bimodality of E13 |
| **scientific** | ⚠️ **the real cost**: choosing a mobility model is a modelling *claim* requiring justification | same |

**The scientific cost is the one that matters.** Random Waypoint is the default in most NS-3 work and
would be wrong here: UAV swarms fly formations and coordinated search patterns, not memoryless random
destinations, and RWP has known artifacts (speed decay, non-uniform node density). Adopting it would
trade a *stated* limitation ("nodes are static") for a *hidden* one ("nodes move according to a model
nobody would defend for a swarm"). That is the same trap we declined in F25 when we chose not to
refit the LoRa path-loss exponent to nine hardware points.

---

## 3. What it would buy, per arm

### 802.11 saturation arm — **almost nothing, and I recommend against it**

The two models being validated, **Bianchi and Ma & Chen, contain no position term at all**. They are
MAC contention models parameterised by the number of *contending stations* and the frame duration.
Mobility cannot change their predictions, so it cannot improve the validation.

It could only matter by changing *which* nodes are in the collision domain — but our scenario places
nodes deliberately close (the cluster spans well under the reference distance) precisely so that
"single collision domain" is exact rather than approximate. Adding motion would either preserve that
(no effect) or break it (measuring a different, multi-domain problem that the models do not describe
and that we do not claim).

**Verdict: state the assumption, do not simulate it.** The honest sentence is that the 802.11 result
is a single-collision-domain MAC result, valid while nodes remain mutually in range, and that
mobility enters only through domain membership, which is out of scope.

### LoRa arm — **worth doing, but not first**

Here mobility genuinely couples to a result: F23 established that delivery is range-limited
(`N_max = 5` holds only within ≈500 m), so a moving node's delivery varies continuously in a way a
fixed disc cannot show. Mobility would let us report delivery over a realistic geometry.

**But it must not be done before E13.** The LoRa capacity result is currently bimodal and
under-sampled — 3 seeds against a distribution with σ ≈ 0.21. Layering a mobility model on top would
compound two sources of variance and make the outcome uninterpretable. Fix the sampling and the
frozen-phase artifact first; then mobility is a clean sensitivity axis.

---

## 4. If we do it — the plan

**Phase M0 — prerequisites (blocking).** Resolve E13: sender-side transmission randomisation and
≥30 seeds with a distributional report. Without this, no mobility result is interpretable.

**Phase M1 — pick a defensible model and say why.** Not Random Waypoint. Two candidates:
* **Gauss–Markov** (`ns3::GaussMarkovMobilityModel`) — temporally correlated velocity, no sudden
  turns, tunable memory α. The standard choice in FANET literature precisely because it avoids RWP's
  artifacts. Recommended default.
* **Formation / reference-point group mobility** — a swarm holding station relative to a leader.
  Closer to the actual application, and it keeps mutual distances bounded, which matters for the
  broadcast reachability argument in `TRADEOFFS.md §1a`.

Report both if cheap; they bracket "loose swarm" and "tight formation".

**Phase M2 — LoRa sensitivity sweep.** Speeds {0, 5, 20} m/s × the existing N sweep, ≥30 seeds,
reporting the **distribution** of `delivered_frac`, not a mean. Expected direction, stated in
advance: mobility should *reduce* the bimodality (nodes moving through each other's ranges break
frozen collision pairs) and *widen* the delivery distribution (link quality varies with distance).
If mobility instead leaves the result unchanged, suspect the link margin again — the F25 result says
our propagation has 17–29 dB of headroom, and mobility inside a 1000 m disc will not exhaust that.

**Phase M3 — report as a sensitivity, not a replacement.** The static result stays the headline with
its stated assumption; mobility becomes a row in the limitations table with a measured delta. This
mirrors how the 802.11 arm already reports `realistic_500m` and `nakagami1` sensitivity.

**Phase M4 — the honest caveat that will remain.** Even with mobility, we would still not model
Doppler-induced fast fading *within* a frame, which §1(a) shows is the dominant mobility effect at
these speeds on the LoRa arm. Moving nodes around a disc changes *distance*; it does not add the
per-frame fading that a 364 ms LoRa frame at 20 m/s would actually experience. Claiming "we modelled
mobility" while omitting that would be the misleading outcome, so the limitation must be stated
either way.

---

## 5. Summary

| | add mobility? | why |
|---|---|---|
| **802.11 saturation** | **No** | Bianchi and Ma & Chen have no position term; mobility cannot change them. State the single-collision-domain assumption instead |
| **802.11 delay/DCF** | No | same reason |
| **LoRa capacity** | **Yes, after E13** | range genuinely couples to delivery (F23); worth a sensitivity sweep with Gauss–Markov and a formation model |
| **fast fading (both)** | Separate item | the dominant mobility effect at 20 m/s, and adding position dynamics does *not* address it |

**Net:** mobility is a real limitation, but it is not the binding one. **E13 is** — it currently
breaks a headline number, while mobility would change a number we would still report with a caveat.
Fix the sampling first.

---

## 6. Execution shape, per Mohamed's direction

**New files, not edits.** `authbc-lora-capacity-mobile.cc` (and an 802.11 counterpart only if the
survey shows it is expected) sitting alongside the frozen scenarios. Benefits: the static results
stay byte-reproducible, the frozen gate keeps passing untouched, and the mobility result is a
*comparison against* the static baseline rather than a replacement for it.

**Survey first, parameters second.** Before any code, answer from the literature:

| question | why it decides something |
|---|---|
| which mobility models do FANET papers actually use? | avoids us defending Random Waypoint, which is wrong for swarms |
| what speeds? | §1 shows 5 vs 20 m/s is the difference between safe and mid-frame decorrelation |
| what node counts and areas? | our disc radius currently drives the F23 range result |
| what run durations? | at 20 m/s a 3600 s run covers 72 km — most papers use far shorter |
| do they model Doppler/fast fading, or only position? | tells us whether §4 Phase M4's caveat is standard or a gap |

The survey output is a table of published configurations, and our scenario is then set to sit inside
that envelope — the same discipline used for the LoRa arm's Bor and Zirak comparisons.
