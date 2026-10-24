# Mobility survey — what FANET / UAV-swarm papers actually configure

*Phase M1 of `docs/MOBILITY_PLAN.md`. Mohamed's direction (2026-07-30) was that mobility must be
preceded by a survey of published practice, "so that our configuration is anchored to published
practice and our results are comparable to theirs, rather than to parameters we chose ourselves."*

**Status: PILOT, not the full survey.** Five sources are read below, all of them already held in
`docs/literature/`. That is enough to fix the *model* choice and to bracket speed, and it is **not**
enough to claim a representative picture of the field. Treated the same way the Direction C survey
is treated: a pilot is reported as a pilot.

---

## 1. What the sources actually say

Every row is quoted from the PDF held in `docs/literature/`, not from an abstract or a search
snippet — the F18 rule (*"quoting the PDF is not enough: quote the FIGURE"*) applies here too.

| source | role | mobility model | scenario parameters as stated |
|---|---|---|---|
| **Paredes et al. 2023**, *Sensors* 23:2403 — LoRa-FANET survey | the field's own summary | §3.2.2 surveys **four**: "Random Way Point, Gauss-Markov, Semi-random Circular Movement, and Mission Plan Based"; others add "Pheromone-Based, Paparazzi, and Particle Swarm" | gives a **five-category taxonomy** (random-, time-, path-, group-, topology-based). Notes **RPGM** used for evaluation "through simulations in Network Simulator (NS)-3" |
| **arXiv 2510.10236** (2025) — UAV-swarm hybrid MAC | current practice, NS-3 | **Random Waypoint** | **20–100 nodes**; area **400 m × 400 m × 1000 m**; Nakagami-m; IEEE 802.11ah; 100 J/node; run "until more than half the drones were dead" |
| **Davoli et al. 2021** — hybrid LoRa + 802.11s UAV mesh | the speed anchor | — | UAVs "typically flying in a speed range between **20 km/h and 70 km/h**"; studies "a UAV linear speed between **20 km/h and 50 km/h**"; reports degradation "at speeds higher than **40 km/h**" |
| **Chen et al. 2020** — UAV swarm communication architectures | corroborates G-M | notes GPMOR "uses the *Gaussian-Markov mobility model* to predict the movement of the UAVs" | — |
| **Zirak et al. 2021** — air-to-air LoRa field test | ⚠️ **not extractable** | — | The held PDF is **image-only**; text extraction returns 5 characters. Its PDR-vs-range table was transcribed by hand earlier (F23) and is unaffected, but it contributes nothing to this survey |

### Speeds, converted once so the paper can quote one unit

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

## 2. Two findings that change what we should do

### 2a. Random Waypoint is the *dominant practice*, and `MOBILITY_PLAN.md` argues against it

The plan says RWP "would be wrong here: UAV swarms fly formations and coordinated search patterns,
not memoryless random destinations." That reasoning stands. But the survey shows RWP is what a
**2025** NS-3 UAV-swarm paper uses, and the survey lists it first among the four.

This **strengthens** our position rather than weakening it, but it changes the framing:

> Choosing Gauss-Markov is a **deviation from common practice**, and must be defended as such — not
> presented as the obvious choice. A reviewer who works in this field uses RWP.

The defence is already written (RWP's speed decay and non-uniform density artifacts, and its
memorylessness being wrong for a formation). It needs to be *stated* in the paper, with the
observation that we ran the comparison rather than assumed it.

### 2b. Reporting is as thin as Direction C found for replication counts

The 2025 paper specifies node count, area, path loss, PHY, MAC and initial energy — and **never
states the RWP speed range or pause time**, the two parameters that determine what its mobility
model actually did. Its stopping rule ("until more than half the drones were dead") is
energy-defined, so the simulated duration is not stated either.

⚠️ This is the *same* class of gap Direction C documents for seed counts. Whether it generalises is
**unknown from one paper** — n=1 is an observation, not a finding. It is recorded here as a
hypothesis to test if the full survey happens, and **must not be quoted as a result**.

---

## 3. What this fixes for our configuration

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

## 4. ANSWERED — the sweep was run, and mobility makes no difference (F37)

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

## 5. What the full survey still needs

1. **Sample size.** Five sources, three of which say something about mobility. The plan's wording
   ("deep literature survey") means tens of papers, and specifically ones that state speeds.
2. **The parameters nobody reports.** Speed, pause time, and duration are the values we most need
   and are the ones most often missing. Worth recording the *absence* systematically.
3. **Fixed-wing vs rotary.** Davoli's 20–70 km/h does not say which, and a fixed-wing UAV has a
   **stall speed** — a non-zero minimum — while a quadrotor can hover. Our {0, 5, 20} grid assumes
   hovering is physical, which is true only for rotary craft. **Unresolved; state it as an
   assumption until a source settles it.**

---

## 6. 2026-10-21 — the 802.11 spatial arm: relative motion (decision H8)

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
