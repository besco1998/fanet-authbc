# Deferred plans — work Mohamed has deferred, written down so it can be started later

*Merged on 2026-11-01 from three files, copied verbatim. **Do not start any of this unprompted**
(`CLAUDE.md`, "Deferred by Mohamed"): the mobility study for the LoRa arm, with its literature
survey, and Direction C (the LoRaWAN frozen-phase artifact as a second short paper). The survey
protocol of Direction C is a registration and lives in
[`../predictions/DIRECTION_C_SURVEY_PROTOCOL.md`](../predictions/DIRECTION_C_SURVEY_PROTOCOL.md).*

## Contents

1. [Adding mobility: what it costs, what it buys, and what I recommend](#s1) — formerly `docs/MOBILITY_PLAN.md`
2. [Mobility survey — what FANET / UAV-swarm papers actually configure](#s2) — formerly `docs/MOBILITY_SURVEY.md`
3. [Direction C — what is still missing](#s3) — formerly `docs/DIRECTION_C_DOWNLOAD_LIST.md`

---

<a id="s1"></a>

## 1. Adding mobility: what it costs, what it buys, and what I recommend

*Formerly `docs/MOBILITY_PLAN.md`, last changed 2026-10-06. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

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

### 1. First, what mobility physically changes

Two separate effects, often conflated. Numbers computed with our own models at the operating point.

#### (a) Doppler / fast fading — *within* a frame

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

#### (b) Topology change — *across* the run

| speed | distance per frame (802.11) | per LoRa frame | per 3600 s run |
|---|---|---|---|
| 5 m/s | 9.9 mm | 1.8 m | **18 km** |
| 20 m/s | 39 mm | 7.3 m | **72 km** |
| 30 m/s | 59 mm | 10.9 m | **108 km** |

Within a single frame the geometry is effectively frozen on both arms. Over a 3600 s run it is
meaningless: a node at 20 m/s covers 72 km, so a static 1000 m disc describes nothing real.

---

### 2. What it would cost

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

### 3. What it would buy, per arm

#### 802.11 saturation arm — **almost nothing, and I recommend against it**

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

#### LoRa arm — **worth doing, but not first**

Here mobility genuinely couples to a result: F23 established that delivery is range-limited
(`N_max = 3` holds only within ≈500 m), so a moving node's delivery varies continuously in a way a
fixed disc cannot show. Mobility would let us report delivery over a realistic geometry.

**But it must not be done before E13.** The LoRa capacity result is currently bimodal and
under-sampled — 3 seeds against a distribution with σ ≈ 0.21. Layering a mobility model on top would
compound two sources of variance and make the outcome uninterpretable. Fix the sampling and the
frozen-phase artifact first; then mobility is a clean sensitivity axis.

---

### 4. If we do it — the plan

**Phase M0 — prerequisites (blocking).** Resolve E13: sender-side transmission randomisation and
≥30 seeds with a distributional report. Without this, no mobility result is interpretable.

**Phase M1 — pick a defensible model and say why.** Not Random Waypoint. Two candidates:
* **Gauss–Markov** (`ns3::GaussMarkovMobilityModel`) — temporally correlated velocity, no sudden
  turns, tunable memory α. The standard choice in FANET literature precisely because it avoids RWP's
  artifacts. Recommended default.
* **Formation / reference-point group mobility** — a swarm holding station relative to a leader.
  Closer to the actual application, and it keeps mutual distances bounded, which matters for the
  broadcast reachability argument in `TRADEOFFS.md §1a` (now the trade-off register in
  `docs/DECISIONS.md`).

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

### 5. Summary

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

### 6. Execution shape, per Mohamed's direction

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
that envelope — the same discipline used for the LoRa arm's Haxhibeqiri et al. and Zirak comparisons.


---

<a id="s2"></a>

## 2. Mobility survey — what FANET / UAV-swarm papers actually configure

*Formerly `docs/MOBILITY_SURVEY.md`, last changed 2026-10-21. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*Phase M1 of `docs/DEFERRED_PLANS.md`. Mohamed's direction (2026-07-30) was that mobility must be
preceded by a survey of published practice, "so that our configuration is anchored to published
practice and our results are comparable to theirs, rather than to parameters we chose ourselves."*

**Status: PILOT, not the full survey.** Five sources are read below, all of them already held in
`docs/literature/`. That is enough to fix the *model* choice and to bracket speed, and it is **not**
enough to claim a representative picture of the field. Treated the same way the Direction C survey
is treated: a pilot is reported as a pilot.

---

### 1. What the sources actually say

Every row is quoted from the PDF held in `docs/literature/`, not from an abstract or a search
snippet — the F18 rule (*"quoting the PDF is not enough: quote the FIGURE"*) applies here too.

| source | role | mobility model | scenario parameters as stated |
|---|---|---|---|
| **Paredes et al. 2023**, *Sensors* 23:2403 — LoRa-FANET survey | the field's own summary | §3.2.2 surveys **four**: "Random Way Point, Gauss-Markov, Semi-random Circular Movement, and Mission Plan Based"; others add "Pheromone-Based, Paparazzi, and Particle Swarm" | gives a **five-category taxonomy** (random-, time-, path-, group-, topology-based). Notes **RPGM** used for evaluation "through simulations in Network Simulator (NS)-3" |
| **arXiv 2510.10236** (2025) — UAV-swarm hybrid MAC | current practice, NS-3 | **Random Waypoint** | **20–100 nodes**; area **400 m × 400 m × 1000 m**; Nakagami-m; IEEE 802.11ah; 100 J/node; run "until more than half the drones were dead" |
| **Davoli et al. 2021** — hybrid LoRa + 802.11s UAV mesh | the speed anchor | — | UAVs "typically flying in a speed range between **20 km/h and 70 km/h**"; studies "a UAV linear speed between **20 km/h and 50 km/h**"; reports degradation "at speeds higher than **40 km/h**" |
| **Chen et al. 2020** — UAV swarm communication architectures | corroborates G-M | notes GPMOR "uses the *Gaussian-Markov mobility model* to predict the movement of the UAVs" | — |
| **Zirak et al. 2021** — air-to-air LoRa field test | ⚠️ **not extractable** | — | The held PDF is **image-only**; text extraction returns 5 characters. Its PDR-vs-range table was transcribed by hand earlier (F23) and is unaffected, but it contributes nothing to this survey |

#### Speeds, converted once so the paper can quote one unit

| source figure | m/s |
|---|---|
| 20 km/h | 5.6 |
| 40 km/h (Davoli's degradation onset) | 11.1 |
| 50 km/h | 13.9 |
| 70 km/h | 19.4 |

**Published practice brackets 5.6–19.4 m/s.** That contains the {0, 5, 20} m/s grid already proposed
in `MOBILITY_PLAN.md` §M2 — 20 m/s sits just above Davoli's upper figure, which makes it a defensible
stress point rather than an invented one.

---

### 2. Two findings that change what we should do

#### 2a. Random Waypoint is the *dominant practice*, and `MOBILITY_PLAN.md` argues against it

The plan says RWP "would be wrong here: UAV swarms fly formations and coordinated search patterns,
not memoryless random destinations." That reasoning stands. But the survey shows RWP is what a
**2025** NS-3 UAV-swarm paper uses, and the survey lists it first among the four.

This **strengthens** our position rather than weakening it, but it changes the framing:

> Choosing Gauss-Markov is a **deviation from common practice**, and must be defended as such — not
> presented as the obvious choice. A reviewer who works in this field uses RWP.

The defence is already written (RWP's speed decay and non-uniform density artifacts, and its
memorylessness being wrong for a formation). It needs to be *stated* in the paper, with the
observation that we ran the comparison rather than assumed it.

#### 2b. Reporting is as thin as Direction C found for replication counts

The 2025 paper specifies node count, area, path loss, PHY, MAC and initial energy — and **never
states the RWP speed range or pause time**, the two parameters that determine what its mobility
model actually did. Its stopping rule ("until more than half the drones were dead") is
energy-defined, so the simulated duration is not stated either.

⚠️ This is the *same* class of gap Direction C documents for seed counts. Whether it generalises is
**unknown from one paper** — n=1 is an observation, not a finding. It is recorded here as a
hypothesis to test if the full survey happens, and **must not be quoted as a result**.

---

### 3. What this fixes for our configuration

| decision | value | anchored to |
|---|---|---|
| Primary model | **Gauss–Markov** (`ns3::GaussMarkovMobilityModel`) | surveyed as one of the four standard FANET models; used by GPMOR (Chen 2020) |
| Second model | **RPGM / formation**, via `HierarchicalMobilityModel` | Paredes §3.2.2 records RPGM used for FANET evaluation in NS-3. Verified present in our restored 3.48 tree |
| Speed grid | **{0, 5, 20} m/s** | brackets the 5.6–19.4 m/s published range; 0 is the frozen static control |
| Baseline to also run | **RWP** | it is what the field does; running it makes our G-M choice a *measured* comparison |
| Node counts | our existing N sweep | already inside the 20–100 of arXiv 2510.10236 |
| Area | our existing 1000 m disc | comparable to 400×400×1000 m |

**One change to the plan follows from the survey:** `MOBILITY_PLAN.md` §M1 says "Not Random
Waypoint." The survey says run it anyway — **as a baseline, not as our model** — because it converts
"we rejected RWP on theoretical grounds" into "we measured RWP and G-M and report both." That costs
one extra arm and removes the most obvious reviewer objection to the choice.

⚠️ This is a deviation from a written plan, so it is Mohamed's call (Law 8). It does not block M2:
the G-M arm can be built while the question is open.

---

### 4. ANSWERED — the sweep was run, and mobility makes no difference (F37)

`ns3/authbc-lora-capacity-mobile.cc` was built and swept at 30 seeds. **Every arm lands within
0.06 σ of the static control** (Gauss-Markov 5 m/s −0.24 pp, G-M 20 m/s −0.03 pp, RWP 20 m/s
+0.36 pp; |t| ≤ 0.22) at 816–967 m mean displacement, under the **goursaud** capture matrix. Under
**aloha** all four arms are byte-identical, because without capture position cannot enter the
calculation at all. **Same conclusion under both collision models.**

⚠️ **This retires §2a's open question.** The survey argued RWP should be run as a baseline against
`MOBILITY_PLAN.md` §M1's "not Random Waypoint". Both were run and they are **statistically
indistinguishable**, so the model choice carries no weight in this result and neither position needs
defending. The speed grid in §3 is validated as adequate rather than merely plausible.

Per-frame Doppler remains unmodelled — see F37's closing caveat before quoting this anywhere.

### 5. What the full survey still needs

1. **Sample size.** Five sources, three of which say something about mobility. The plan's wording
   ("deep literature survey") means tens of papers, and specifically ones that state speeds.
2. **The parameters nobody reports.** Speed, pause time, and duration are the values we most need
   and are the ones most often missing. Worth recording the *absence* systematically.
3. **Fixed-wing vs rotary.** Davoli's 20–70 km/h does not say which, and a fixed-wing UAV has a
   **stall speed** — a non-zero minimum — while a quadrotor can hover. Our {0, 5, 20} grid assumes
   hovering is physical, which is true only for rotary craft. **Unresolved; state it as an
   assumption until a source settles it.**

---

### 6. 2026-10-21 — the 802.11 spatial arm: relative motion (decision H8)

*Why the 802.11 arm now, against `MOBILITY_PLAN.md`'s "No" for it:* that verdict was for the
single-collision-domain scenarios, where position cannot enter (Bianchi, Ma & Chen). Revision A1
added layouts that span several domains, where motion changes who is a neighbour and who
contends. A1's group layout tested only a rigid translation (F88); Mohamed chose to test relative
motion (H8). This section adds six sources to §1's five, read for that choice. Every value was
read in the PDF; files in `docs/literature/` (`README.md`, 2026-10-21 section).

| source | kind | models it uses or recommends | speeds | nodes, area, duration |
|---|---|---|---|---|
| Bujari, Calafate, Cano, Manzoni, Palazzi & Ronzani, IJDSN 13(10), 2017 (CC BY) | survey | Random Walk / Waypoint / Direction are **excluded from every FANET application** (its Table 3); Gauss–Markov (GM), Smooth Turn, group (column, nomadic, pursue) and path-planned models per application. GM: smooth acceleration, no smooth curves (Table 1). ns-3 implements GM and reference-point group mobility (Table 2) | GM example: mean 10 m/s, speed σ 1 m/s, heading σ 45°, α = 0.8, step 1 s (Fig. 6); Smooth Turn 15 m/s, turn radius 10–100 m (Fig. 7); Random Walk example 10–30 m/s | — |
| Guillen-Perez & Cano, Sensors 18:3571, 2018 (CC BY) | survey + case study | rotary-wing: Random Waypoint in the works it cites; fixed-wing: Paparazzi or Smooth Turn (Table 2) | rotary-wing ~50 km/h (14 m/s), fixed-wing ~100 km/h (28 m/s) (Table 2) | — |
| Wheeb, Nordin, Samah, Alsharif & Khan, Drones 6:9, 2022 (CC BY) | survey | 14 models compared (Table 2); Enhanced GM as the FANET-specific GM | EGM "typically … 30–60 m/s … suitable for quadcopter UAVs" (§2.3.4) — high for small quadcopters; quoted as written | — |
| Huang et al. (FMAC), IEEE IoT J 8(1), 2021 (held locally) | primary, flocking | flocking control through obstacles | virtual leader 6 m/s | 150 UAVs, 10 Hz, 100 s |
| Kumar, Choi & Kim, EURASIP JWCN 2019 (CC BY) | primary, VANET | constant speed per lane | 40–140 km/h (11–39 m/s) | ns-3, 10 km highway, 50 s |
| Yang, Zhao, Wang, Dong & Ju, arXiv:2503.16834, 2025 (held locally) | primary, formation | GM group (leaders GM, followers around them), α = 0.5 | leaders 200 m/s (a marching formation) | ns-3, 36–144 nodes, 100 s |

**The envelope with §1:** small rotary-wing UAVs 5.6–19.4 m/s (§1) and 6–15 m/s here;
fixed-wing ~28 m/s; one survey's 30–60 m/s and one formation study's 200 m/s are outliers for
small swarms. GM is the standard time-correlated choice; Random Waypoint is common practice but
excluded by Bujari et al. for every FANET application, and on the LoRa arm it made no difference
(§4).

**Our configuration** (`ns3/authbc-spatial-mobile.cc`, layout `gm`; `predictions/A1-motion.md`):

| | value | anchored to |
|---|---|---|
| model | **GM per node** — each node independent, so relative motion | §1 and Bujari et al.; the group case is A1's S3 (F88) |
| α, step | **0.85, 0.5 s** | 0.5–0.85 published; A1's S3 used 0.85 / 0.5 s |
| speed | **0 (control), 5, 15 m/s** | inside 5.6–19.4 (§1); 15 is the plan's "up to 15 m/s" (H8) |
| speed / heading noise | **σ = 0.1 × mean; 45°** | Bujari et al.'s GM example |
| nodes | **60–70 (base), 199–234 (design)** | A1's stage-2 grids at R = 1 km; 36–150 published |
| area | a square of the area of A1's 1 km disc (side 1 772 m), altitude 50–150 m | A1 S1 |
| duration | **20 s**, as every A1 run; 300 m of travel at 15 m/s | 50–100 s published; ours is shorter, stated |

⚠️ **Hovering is assumed** for the speed-0 control and for 5 m/s: physical for rotary-wing
craft, not for fixed-wing ones with a stall speed (§5.3, still open). ⚠️ **No Doppler, no
time-correlated fading** — ns-3 draws Nakagami fading per frame, right for moving nodes at frame
spacings of 20–80 ms, pessimistic for still ones; motion acts only through geometry.


---

<a id="s3"></a>

## 3. Direction C — what is still missing

*Formerly `docs/DIRECTION_C_DOWNLOAD_LIST.md`, last changed 2026-08-08. Copied verbatim on 2026-11-01; headings moved down one level and relative links re-pointed.*

*Updated 2026-08-08. Most of the earlier worklist was retrieved after all: **Unpaywall**,
**Semantic Scholar** and the **Europe PMC REST API** return legal open-access copies that the
publishers' own web front-ends refuse to serve to a script. Seven of the thirteen were obtained
that way, six of them qualified, and the corpus is now **20**.*

### Still needed — 5 papers

| # | paper | where | save as |
|---|---|---|---|
| 1 | Abakar, Bennis & Abouaissa, *A Multi-Gateway Behaviour Study for Traffic-Oriented LoRaWAN Deployment*, Future Internet 14(11):312, 2022 | [mdpi.com/1999-5903/14/11/312](https://www.mdpi.com/1999-5903/14/11/312) · `10.3390/fi14110312` | `abakar2022_multigateway_lorawan_ns3.pdf` |
| 2 | Kufakunesu, Hancke & Abu-Mahfouz, *Collision Avoidance Adaptive Data Rate Algorithm for LoRaWAN*, Future Internet 16(10):380, 2024 | [mdpi.com/1999-5903/16/10/380](https://www.mdpi.com/1999-5903/16/10/380) · `10.3390/fi16100380` | `kufakunesu2024_collision_avoidance_adr_ns3.pdf` |
| 3 | Kufakunesu, Hancke & Abu-Mahfouz, *A Fuzzy-Logic Based Adaptive Data Rate Scheme*, JSAN 11(4):65, 2022 | [mdpi.com/2224-2708/11/4/65](https://www.mdpi.com/2224-2708/11/4/65) · `10.3390/jsan11040065` | `kufakunesu2022_fuzzy_adr_lorawan_ns3.pdf` |
| 4 | *Optimizing Multi-hop Mechanism for the Long Range Wide Area Network* | [arxiv.org/abs/1811.05386](https://arxiv.org/abs/1811.05386) | `multihop_optimization_lorawan_ns3_2018.pdf` |
| 5 | *Trilateration-based Multi-hop for the Long Range Wide Area Network* | [arxiv.org/abs/1811.06345](https://arxiv.org/abs/1811.06345) | `trilateration_multihop_lorawan_ns3_2018.pdf` |

**1--3** are open access and free; MDPI simply returns a challenge page to any script. They are
one click each in a browser. **4--5** are arXiv entries whose PDF endpoint returns HTML on every
mirror I tried; they may render for you.

Dropped: *Long Range Wide Area Network: A Simulation Module for ns-3* (arXiv 1811.05829) — same PDF
problem, and it is superseded for our purposes by Reynders et al. WNS3 2018 and Magrin
et al. IoT-J 2020, both now held.

### Two rules that still apply

⚠️ **Do not select on whether a paper looks like it reports seeds.** That is selecting on the
dependent variable and would invalidate the sweep (protocol §2).

⚠️ **PDFs only — never a summary, abstract or saved HTML page.** The sweep is a mechanical scan
over full text; a summary would manufacture "no replication reported" verdicts, which §3 names as
the likeliest way this survey produces a false result.

### Where the corpus stands

| | |
|---|---|
| corpus, fully adjudicated | **20** |
| no replication reported | 17 |
| reports it | 3 |
| REPORTS share | **15.0 %** vs a pre-registered 25 % falsification threshold |
| protocol target | 56 |

Adding all five above would take it to **25**.
