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

## 4. What the full survey still needs

1. **Sample size.** Five sources, three of which say something about mobility. The plan's wording
   ("deep literature survey") means tens of papers, and specifically ones that state speeds.
2. **The parameters nobody reports.** Speed, pause time, and duration are the values we most need
   and are the ones most often missing. Worth recording the *absence* systematically.
3. **Fixed-wing vs rotary.** Davoli's 20–70 km/h does not say which, and a fixed-wing UAV has a
   **stall speed** — a non-zero minimum — while a quadrotor can hover. Our {0, 5, 20} grid assumes
   hovering is physical, which is true only for rotary craft. **Unresolved; state it as an
   assumption until a source settles it.**
