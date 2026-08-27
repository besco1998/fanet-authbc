# Literature register — what we read, what it does for us, what it cost us

*Every source consulted for AUTHBC, with **why it matters to this thesis** stated explicitly. A
citation with no stated role is a citation nobody will check. PDFs are stored beside this file where
licensing allows. **50 PDFs; every source cited in the paper is held and has been read.** ⚠️ The count read *49* until 2026-08-27 while the Mehta et al. 2020 entry below already claimed “PDF here” — the file had never been committed, so the promise in this sentence was false for anyone cloning. It is committed now. ⚠️ The header said *20* until 2026-08-07 while 25 sat on disk, and **five held PDFs had no register entry at all** despite the promise above — they are added at the end of this file. A register that silently omits a fifth of its corpus is not a register. The one
exception is Gündoğan et al. (ACM DL only) — its DOI is recorded instead. See
[`A3_CITATION_VERIFICATION.md`](A3_CITATION_VERIFICATION.md) for how each citation was checked.*

**Status key:** `USED` — cited in the paper · `VALIDATES` — an independent check on one of our
results · `PRIOR ART` — establishes something we must *not* claim · `POSITIONING` — related work,
not a comparator · `TO READ` — identified but not yet studied in full.

---

## 1. Channel modelling — the 802.11 arm

| source | status | role |
|---|---|---|
| **Bianchi, *Performance analysis of the IEEE 802.11 DCF*, IEEE JSAC 18(3), 2000** | `USED` | The unicast saturation model our airtime layer implements. Validated against NS-3 3.48 to **+1.29/−0.40 %** (mean, 30 seeds) |
| **Ma & Chen, *Saturation Performance of IEEE 802.11 Broadcast Networks*, IEEE Comm. Lett. 11(8), 2007** — PDF here | `USED` `PRIOR ART` | **Cost us a novelty claim (F9).** We independently rediscovered the backoff-counter freeze that makes broadcast differ from unicast; they published it in 2007. Their abstract explicitly warns unicast models "cannot simply be reduced" to broadcast — which is exactly what we had done, wrong by 17.3× at N=50. Now implemented and cited; no novelty claimed |
| **Ma & Chen, *Performance Analysis of IEEE 802.11 Broadcast Scheme in Ad Hoc Wireless LANs*, IEEE TVT 57(6), 2008** — PDF here | `USED` | The journal version. **Use its eq. (8), not the letter's eq. (6)**, which misprints p_ss |
| **Tinnirello, Bianchi & Xiao, *Refinements on IEEE 802.11 DCF Modeling Approaches*, IEEE TVT 59(3), 2010** — PDF here | `VALIDATES` | "Anomalous slots": the post-success slot is available only to the station that just transmitted. Our unicast traces confirm it independently (94 µs floor seen 220×) |

## 2. The payload-exclusion bound — prior art we found before claiming

| source | status | role |
|---|---|---|
| **Gündoğan, Amsüss, Schmidt & Wählisch, *Reliable Firmware Updates for the Information-Centric IoT*, ACM ICN 2021** | `PRIOR ART` `POSITIONING` | **This is why T6 is not a theorem (F16).** They compute `MTU − headers − signature` for 802.15.4/NDN: 55 B of headers leave 73 B, and a 64 B Ed25519 signature leaves **9 B** for data. Same arithmetic as ours on a different link. **Net positive for us** — see §5 below |
| Post-quantum / 5G SIB1 incompatibility (arXiv 2510.23457) | `PRIOR ART` | NIST signatures exceed SIB1's 372 B limit — independent instance of our "tier 1", the signature alone overflowing the frame |
| 6LoWPAN fragment security (arXiv 2506.01767) | `PRIOR ART` | "The loss of a single fragment renders the entire packet invalid" — the `(1−p)^n` fact our no-fragmentation step rests on. Also documents *sliced signatures* as the standard workaround, which is what our ε ≤ p condition forecloses |

## 3. UAV / vehicular broadcast authentication — the comparator class

| source | status | role |
|---|---|---|
| **Veara, Jain, Moy & Ranganathan, *TBRD: TESLA Authenticated UAS Broadcast Remote ID*, arXiv 2510.11343, 2025** | `POSITIONING` **not a baseline** | Closest published UAV work: TESLA + TEE for Remote ID, 50 % less authentication overhead than signatures. **Cannot be a baseline for us** — TESLA is symmetric with public key disclosure, so it provides **no non-repudiation**, which a provenance ledger requires. Belongs in related work as a different point in the design space |
| **Perrig, Canetti, Tygar & Song, *The TESLA Broadcast Authentication Protocol*, RSA CryptoBytes 5(2), 2002** | `POSITIONING` | The underlying protocol. Establishes the alternative currency: TESLA delays *verification*, batching delays *transmission* |
| **Certificateless aggregate signature (CLAS) schemes for VANET** — e.g. LB-CLAS, *Vehicular Communications*, 2024 | `POSITIONING` `TO READ` | **The nearest methodological relatives.** They aggregate n signatures into one for vehicular safety beacons — the same problem shape. **Different contribution axis:** they build *new cryptographic constructions*; we ask which combination of *existing standardised* primitives and system parameters is feasible on a given link. Worth reading in full before the thesis defence |

## 4. LoRa — the low-rate arm

| source | status | role |
|---|---|---|
| **Semtech SX1276/77/78/79 datasheet, Rev. 7, 2020** | `USED` | §4.1.1.5 symbol rate, §4.1.1.7 time-on-air. Every LoRa timing constant transcribed from here |
| **LoRa Alliance RP002-1.0.3 Regional Parameters, 2021** | `USED` | EU868 Table 8 (data rates), **Table 13** (max payload, non-repeater), duty cycle < 1 %. ⚠️ The NS-3 module enforces **Table 12** (repeater-compatible, 222 B) instead — a defensible alternative reading, recorded in TRADEOFFS |
| **Bor, Roedig, Voigt & Alonso, *LoRa Scalability: A Simulation Model Based on Interference Measurements*, Sensors 17(6), 2017** — PDF here | `USED` `VALIDATES` | **Not just quoted — IMPLEMENTED.** Their Eq. (8) is now `lora.bor2017_loss_pct()`, validated against the four loss figures their own text states, and run at our operating point via `make exp-lora-external` (F20). **It gives N_max = 4 against our corrected 3** — the LoRa arm's external baseline. ⚠️ Always note which FIGURE a number comes from: collapsing Fig. 6/14/15 produced the retracted F18 |
| **Magrin et al., signetlabdei/lorawan ns-3 module** | `USED` | The simulator behind our capacity result. Requires our `patch_lorawan.py`. ⚠️ **Its `ALOHA` region preset = 1 channel + 1 demodulation path**; the `EU` preset = 3 channels + 8 paths. We used `ALOHA`. The preset choice dominates the capacity number — see §5 |

## 4a. Sources added by the A3 citation pass (see `A3_CITATION_VERIFICATION.md`)

| source | status | role |
|---|---|---|
| **Zhang, Lu, Lin, Ho & Shen, *An Efficient Identity-Based Batch Verification Scheme for Vehicular Sensor Networks*, IEEE INFOCOM 2008** — PDF here | `USED` `POSITIONING` | Related work (b). **Quoted from the PDF:** an RSU can *"verify multiple received signatures at the same time"*. The useful contrast: their deadline is DSRC's **300 ms** and their batching is **receiver-side** (V2I); ours is **sender-side** and buys airtime. Complementary, not competing |
| **Mehta, Gupta & Tanwar, *Blockchain Envisioned UAV Networks*, Computer Communications 151, 2020** — PDF here | `USED` | Related work (c): a survey pointer to the UAV-blockchain subfield. Nothing load-bearing rests on it |
| **Pelkonen et al., *Gorilla: A Fast, Scalable, In-Memory Time Series Database*, PVLDB 8(12), 2015** — PDF here | `USED` `PRIOR ART` | Related work (d): delta coding of telemetry. **Quoted from the PDF:** *"delta-of-delta timestamps and XOR'd floating point values … 10x"*. Prior art for delta coding, **not** for our keyframe scheme — Gorilla is a database and never loses a record, so it needs no re-anchoring |

## 4b. LoRa topology — is our gateway framing honest? (F22)

*Added because Mohamed asked for the "LoRaWAN has no peer-to-peer mode" claim to be verified against
literature before it was built on. It holds; these are the sources.*

| source | status | role |
|---|---|---|
| **Paredes, Kaushal, Vakilinia & Prodanoff, *LoRa Technology in Flying Ad Hoc Networks: A Survey of Challenges and Open Issues*, Sensors 23(5):2403, 2023** — PDF here | `USED` `VALIDATES` | **Confirms the claim in almost our words:** LoRaWAN "presents some limitations regarding its **star topology**, its **MAC layer** and its **lack of routing procedures**" for MANETs/FANETs. Also confirms **Class A = "half-duplex transceivers that implement pure ALOHA"** — so both our ALOHA uplink and E10's half-duplex caveat are *specification properties*, not modelling choices. And it states the gap: "**not much research work has been conducted on using LoRa as a mesh backhaul for air-to-air links**" |
| **Berto, Napoletano & Savi, *A LoRa-Based Mesh Network for Peer-to-Peer Long-Range Communication*, Sensors 21(13):4314, 2021** — PDF here | `USED` `VALIDATES` | Peer-to-peer LoRa **exists**, and is built by discarding LoRaWAN: "A LoRaWAN network **assumes a star topology**"; their mesh is "**not relying on LoRaWAN … without the use of gateways**". Also: "the employed controller **only permits half-duplex communication**", so implementers engineer around it |
| **Davoli, Pagliari & Ferrari, *Hybrid LoRa-IEEE 802.11s Opportunistic Mesh Networking for Flexible UAV Swarming*, Drones 5(2):26, 2021** — PDF here | `POSITIONING` | A hybrid LoRa + 802.11s UAV swarm — the architecture our two arms bracket from either side. Not yet read in full |
| **Zirak, Shashev & Shidlovskiy, *Swarm of Drones Using LoRa Flying Ad-Hoc Network*, ICIT 2021, pp. 400–405** — PDF here (supplied by Mohamed) | `USED` `VALIDATES` ⚠️ | **The most useful single source for the LoRa arm.** (1) Confirms the topology claim outright: *"the MAC level protocol **LoRaWAN only supports star topology**"*. (2) Their built system converges on a **single channel** — independently reaching `TRADEOFFS.md` §1a. (3) **Dedicated TX/RX radios** to beat half-duplex — confirms E10 and gives the engineering fix. (4) ⚠️ They use **LBT, not pure ALOHA**, so a real LoRa FANET collides *less* than we model — one more way `N_max=5` is conservative. (5) ⚠️ **Their Table I is the only HARDWARE air-to-air PDR-vs-range data we have, and it range-limits our result — see F23.** *Scanned PDF, no text layer: read by page rendering* |

**Conclusion for the thesis:** a LoRa UAV-to-UAV ledger is possible, but it is a *different system* —
raw LoRa plus a custom MAC and routing — not a configuration of what we simulated. Our low-rate arm
is therefore honestly the **infrastructure-collected variant**, and the paper now says so with these
citations rather than on our own reading of the spec.

⚠️ **And Zirak et al. Table I did more than corroborate: it range-limited a headline number.** Their
hardware measures air-to-air PDR of **0.9045 at 1000 m** — the exact radius our scenario configures
with an idealised channel that models **zero** link loss. Since delivery is
`P_link(range) × P_no_collision(N)`, **`N_max` is now 3 (F28), and composing it with measured link loss leaves V≥0.95 admitting no multi-node network at all — 1 node at ≤500 m. Relaxing to V≥0.90 restores 3.**
See F23 and `OPEN_ITEMS` E12. This is why "obtain before the defence" was the wrong deadline — a
source that can move a number should be read before the number is published.

## 4c. Related-work sweep around Zirak et al. (2026-07-30)

*Built from the OpenAlex citation graph for `10.1109/ICIT52682.2021.9491655` — 28 related/referenced
works plus 9 citing works, with open-access status resolved per record. Sci-Hub was **not** used;
open-access copies were fetched from the publishers, and the rest are listed below for Mohamed to
pull through institutional access.*

| source | status | role |
|---|---|---|
| **Chen, Tang & Lao, *Review of UAV Swarm Communication Architectures and Routing Protocols*, Appl. Sci. 10(10):3661, 2020** — PDF here | `POSITIONING` | 192 citations; the standard reference for swarm comms topologies. Context for why decentralised is the harder case |
| **Branch et al., *A Multi-Hop LoRa Linear Sensor Network … Medieval Aqueducts in Siena*, Sensors 19(2):402, 2019** — PDF here | `POSITIONING` `VALIDATES` | Their measurement campaign found LoRa range *"limited to a maximum of 200 m, thus making the adoption of a classical star topology impossible"*. Underground, so **not** comparable to air-to-air — but a second independent instance of **range constraining topology**, and it brackets Zirak's air-to-air 1000 m from the harsh side (F23) |
| **Jiang et al., *Hybrid Low-Power Wide-Area Mesh Network for IoT Applications*, IEEE IoT-J, 2020** — PDF here | `POSITIONING` | Sub-GHz long-range + 2.4 GHz short-range hybrid — the architecture our two arms bracket. ⚠️ Contains a **second-hand** figure (Varsier & Schwoerer: PDR falls to 25 % under high node density) that would corroborate our capacity collapse. **Not cited: it is a citation-of-a-citation, and F18 was exactly that mistake.** Read the primary first |

### ⚠️ Wanted, not open access — for Mohamed to fetch

Ranked by what they would actually change:

| # | source | why it matters | risk if we skip it |
|---|---|---|---|
| **1** | **LoRa vs. WiFi Ad Hoc: A Performance Analysis and Comparison** (2020, 30 cites) | **This is our two-arm structure as somebody else's whole paper.** Direct external comparison for the 802.11-vs-LoRa framing | High — a reviewer who knows it will ask why we did not cite it. ⚠️ **STILL WANTED:** the file supplied on 2026-07-30 (`klimiashvili2020.pdf`) turned out to be a different paper entirely (a solar-cell physics article); see F24 |
| 3 | A broadcast sub-GHz framework for UAV clock synchronization (2023) | Sub-GHz **broadcast** among UAVs — the closest thing to our ad hoc LoRa case | Medium |
| 4 | Strategies to Improve LoRaWAN Performance … Listen Before Talk (2024) | Would quantify how much LBT beats pure ALOHA, i.e. **how conservative `N_max = 5` is** | Low — improves a caveat, does not change a number |
| 5 | Varsier & Schwoerer (PDR → 25 % at high density) | Primary source for the second-hand figure above | Low |

| **Centelles, Freitag, Meseguer & Navarro, *Beyond the Star of Stars: An Introduction to Multihop and Mesh for LoRa and LoRaWAN*, IEEE Pervasive Computing 20(2):63–72, 2021** — PDF here | `USED` `VALIDATES` | **The strongest single confirmation of F21/F22, and it goes further.** LoRaWAN "defines a **star of stars** topology"; decentralized LoRa is framed as an *open research direction*, not a capability. Crucially for us: even mesh proposals retain "a **predominant nodes → gateway/sink data flow**", with "**fewer proposals**" targeting truly decentralized architectures — so **our gateway topology is representative of the multi-hop literature, not just of LoRaWAN**. It also lists "**network scalability with hundreds, or even thousands, of nodes**" as an *open challenge*, which is the right context for our N_max result. Independently repeats Branch et al.'s 200 m finding |

## 5. Cryptography

| source | status | role |
|---|---|---|
| **draft-irtf-cfrg-bls-signature-05** (Boneh, Gorbunov, Wahby, Wee, Wood, Zhang), 2022 | `USED` `PRIOR ART` | **Corrected us:** BLS12-381 targets **126-bit** security, not 128. minimal-signature-size = 48 B G1; minimal-pubkey-size = 96 B G2, which is what blspy implements and therefore what we measure |
| RFC 8032 (Ed25519), RFC 8949 §4.2 (canonical CBOR) | `USED` | Signature and encoding specifications |

## 6. Standards

| source | status | role |
|---|---|---|
| **3GPP TS 22.125 V17.6.0 (ETSI TS 122 125)** | `USED` | ⚠️ **The most consequential citation in the thesis.** §5.2.2 specifies *direct UAV-to-UAV local broadcast* — precisely our system. R-5.2.2-010 ≥10 msg/s · **R-5.2.2-011 ≤100 ms** · R-5.2.2-008 payload "50–1500 B, **not including security-related message component(s)**" — the standard itself separates auth bytes from payload, which is our φ metric. **Our D_max = 250 ms exceeds its latency bound**; the deviation is declared |
| **PX4 `mavlink_main.cpp`**, **ArduPilot `GCS_MAVLink_Parameters.cpp`** | `USED` | Telemetry rates read at source. Corrected our claim that ArduPilot defaults to 1 Hz — it is vehicle-specific, and **Copter defaults to 0 Hz** |
| IEEE 802.11-2020 | `USED` | DCF timing; broadcast frames carry no ACK — the mechanism behind our loss model |

---

## Two readings that need stating carefully

### Gündoğan et al. is *good* for us, not bad
It cost a novelty claim on an inequality we had held for one day. In exchange it gives three things
worth more:

1. **Independent corroboration.** A different group, a different link layer (802.15.4), a different
   application (firmware chunks over NDN) hit the *same wall*. That makes the phenomenon general
   rather than an artifact of our modelling.
2. **A related-work anchor.** It establishes that the problem is real and recognised, which is
   exactly what a thesis needs before claiming to bound it.
3. **A sharper contrast.** They hit the wall and *worked around it* (per-chunk signatures, accepting
   the overhead). We ask the different question — *when is the wall insurmountable?* — and answer it
   for a link where the standard workaround (fragmentation) is closed off by loss.

**What it changes:** T6 is presented as an applied bound with attribution, not a theorem. The LoRa
exclusion result is untouched and remains ours.

### Our LoRa `N_max = 5` versus the published numbers — corrected

⚠️ **This section previously said the opposite. It was wrong (F18, retracted). Read the correction,
not the memory of it.**

**What Bor et al. actually report**, by figure — the distinction that I collapsed and must not be
collapsed again:

| figure | configuration | access scheme | loss at 1000 nodes |
|---|---|---|---|
| Fig. 6 (§6.1) | **1 channel, 1 SF**, 20 B | **LoRa** | ~90 % collide |
| Fig. 15 (§6.3) | 3 ch × 6 SF = **18 logical channels** | **LoRa** | **~32 %** |
| Fig. 14 (§6.2) | 18 logical channels | **pure ALOHA** | ~90 % |
| Fig. 11 (§6.2) | 1 channel, 1 SF | **pure ALOHA** | total loss by **200 nodes** |

The abstract states it plainly: *"the losses will be up to 32 %. In such a case, pure Aloha will have
around 90 % losses."* **32 % is LoRa; 90 % is pure ALOHA.** The sentence about "90 % collide … 20
frames per hour" belongs to Figure 14 — their *pure ALOHA* model.

**What our simulation actually is.** `authbc-lora-capacity.cc` sets `LorawanMacHelper::ALOHA`, which
provisions the gateway with **1 logical channel (868.1 MHz) and 1 demodulation path**. We therefore
simulate **LoRaWAN's PHY** — real LoRa modulation with the module's interference and capture model —
on the module's **harshest** MAC preset. It is *not* a pure-ALOHA model, and it is *not* an
RP002-provisioned gateway (`EU` region: 3 channels, 8 demodulation paths).

**The like-for-like comparison, and it does not flatter us.** Both studies transmit at the 1 %
duty-cycle ceiling, so per-node channel occupancy is 1 % in both and offered load scales identically
as `G = N × 0.01`. Bor's own curve fit, `f_MCH_MSF(x) = f_SCH_SSF(x/18)`, maps their multi-channel
1000-node point onto **56 nodes on one channel with one SF, at ~32 % loss**. We measure **74.7 % loss
at N = 50** in that configuration.

> **We are roughly 2.3× more pessimistic than their measurement-based LoRa model, not more
> optimistic.** The most likely cause is the single demodulation path: a second concurrent arrival is
> rejected outright ("no more demodulators"), so it never gets the capture chance that their SX1301
> measurements grant it.

**What this means for the claim.** `N_max = 5` stands as a **worst-case** bound —
one channel, one demodulator, one spreading factor — and it must be labelled that way, not as
"LoRaWAN capacity". Two limitations now compound, and both are stated:

1. **Single SF** — the data rate is a design variable, so each run fixes one, forfeiting SF
   quasi-orthogonality (`OPEN_ITEMS` E8).
2. **Single channel and single demodulation path** — the `ALOHA` preset, harsher than any real
   EU868 gateway (`OPEN_ITEMS` E9).

A `gwRegion` flag has been added to the scenario so the `EU` preset (3 channels, 8 paths) can be run
as a sensitivity and the result reported as a **bracket** rather than a point. Until that runs, the
honest statement is the worst-case one.

**The pure-ALOHA cross-check still holds and is still useful:** measured 0.866 vs `e^(−2G)` = 0.852
at N = 8, and 0.253 vs 0.368 at N = 50. Above the curve at low load (capture works), below it at high
load (the single demodulator). That is a coherent signature of exactly the configuration described
above.



---

## Added 2026-08-07 — five sources that were held but unregistered

⚠️ These PDFs were in `docs/literature/` with **no entry here**, contradicting this file's opening
promise. Recorded now with their role, and with what we can and cannot claim from each.

### Durand & Booysen 2025 — *Performance Evaluation of a Mesh-Topology LoRa Network*
`durand2025_loramesh_ns3.pdf` · Sensors 25(5):1602 · **USED**
Was filed as `..._TOREAD.pdf` and **read on 2026-08-07**. An ns-3 LoRaMesh model; PDR for distant
nodes rises 40.2 % → 73.78 %, first hop 96.9 %. Cited in the LoRa topology caveat for its plain
statement that *"there is currently no standardised and commercialised multi-hop LoRa-based
network"*, which supports our single-hop scope.
⚠️ **It is also a Direction C data point.** A keyword sweep for seed / repetition / run count /
confidence interval / standard deviation over the whole paper returns **zero hits**: a 2025 ns-3
LoRa simulation study reporting no replication at all. That is the sixth paper checked and it fits
the pattern F32/F33 describe.

### Chen (Abel C. H.) 2023 — *Evaluation and Analysis of Standard Security Technology in V2X Communication: Exploring ECQV Implicit Certificate Cracking*
`arxiv2309.15340_ecqv_implicit_cert_v2x.pdf` · arXiv:2309.15340 · **NOT CITED — cannot be read**
⚠️ **The full text is in Chinese.** The filename is accurate (verified against the arXiv record);
what is missing is our ability to read it, so it is **not cited** — the standard in this register is
that a cited source has been read, and an English abstract is not the paper.
**It nonetheless marks a real gap.** Its abstract says it *"analyzes the length of uncompressed
elliptic curve points, compressed elliptic curve points, explicit certificates, and implicit
certificates"* — and our F34 certificate accounting charges an **explicit** 162 B ECDSA certificate
every fifth frame. **Implicit (ECQV) certificates are the smaller alternative we never priced.**
Recorded as open item S10.

### Sobati-Moghadam 2025 — *Predictive-CSM: Lightweight Fragment Security for 6LoWPAN IoT Networks*
`arxiv2506.01767_6lowpan_fragment_security.pdf` · arXiv:2506.01767 · **USED / POSITIONING**
Cited in the PQ projection: once a signature no longer fits one frame, fragmentation becomes a
security surface in its own right, not merely a byte-accounting change.

### Bhatt, Penumatsa & Kumar 2025 — *Hybrid MAC Protocol with Integrated Multi-Layered Security for Resource-Constrained UAV Swarm Communications*
`arxiv2510.10236_uav_swarm_hybrid_mac.pdf` · arXiv:2510.10236 · **USED / POSITIONING**
Current NS-3 UAV-swarm practice: 20–100 nodes, 400 × 400 × 1000 m, Random Waypoint, Nakagami,
802.11ah. Also the anchor in `MOBILITY_SURVEY.md` for RWP being standard practice.
⚠️ It states node count, area, path loss, PHY, MAC and energy — and **never states the RWP speed
range or pause time**, the two parameters that define what its mobility model did.

### Abrardo & Pozzebon 2019 — *A Multi-Hop LoRa Linear Sensor Network … Medieval Aqueducts in Siena*
`branch2019_multihop_lora_linear.pdf` · Sensors 19(2):402 · **USED / POSITIONING**
⚠️ **The filename is wrong** — it says `branch2019` but the authors are Abrardo & Pozzebon. The
bib key is `abrardo2019multihoplora`; the file is left under its original name so existing links do
not break, and the mismatch is recorded here rather than hidden.
Cited beside Jiang et al. as a concrete multi-hop LoRa deployment that still keeps a sink-directed
data flow.


---

## Added 2026-08-07 — ns-3 LoRa simulation studies, and the Direction C replication sweep

Sourced, downloaded and read as one pass serving two purposes: they are legitimate citations, and
each was swept for **replication reporting**, which is Direction C's central claim.

### Van den Abeele, Haxhibeqiri, Moerman & Hoebeke 2017 — *Scalability Analysis of Large-Scale LoRaWAN Networks in ns-3*
`vandenabeele2017_lorawan_ns3_scalability.pdf` · IEEE IoT Journal 4(6):2186--2198 · **USED / PRIOR ART**
The foundational ns-3 LoRaWAN scalability study. Cited as the precedent for simulating LoRaWAN node
counts in ns-3.
⚠️ **Direction C: reports NO replication.** Searched widely, not just for "seed": every occurrence of
*average* refers to the **traffic model** (Poisson rate, downstream rate, SF distribution), and
*"each simulation is run for a simulation time equal to hundred times the upstream period"* is
**duration, not repetitions**. No seed count, no confidence interval, no error bars — in the most
cited scalability analysis in this space.

### To & Duda 2018 — *Simulation of LoRa in NS-3: Improving LoRa Performance with CSMA*
`to2018_lora_ns3_csma.pdf` · IEEE ICC · **USED / POSITIONING**
Cited beside the above as a proposal to replace LoRaWAN's ALOHA MAC with carrier sense.
⚠️ **Direction C: reports no replication.** Its figures compare measurements against *a* single ns-3
simulation.

### Traspadini, Zorzi & Giordani 2025 — *Performance Evaluation of LoRa for IoT Applications in Non-Terrestrial Networks via ns-3*
`traspadini2025_lora_ntn_ns3.pdf` · arXiv:2509.02811 · **USED / POSITIONING**
Current ns-3 LoRa practice, extended to satellite links.
⚠️ **Direction C: reports no replication.** The one keyword hit was a false positive — "Hybrid
Automatic Repeat reQuest" matching *repeat*.

---

### Rotta & Mykytyn 2024 — *Secure Multi-hop Telemetry Broadcasts for UAV Swarm Communication*
`2024_secure_multihop_telemetry_broadcast.pdf` · arXiv:2401.11915 · **USED / PRIOR ART**
⚠️ **The most directly comparable outside work we have found.** An independent UAV-swarm design that
attaches *"a HMAC-256 signature with a timestamp"* to **each** broadcast telemetry message — i.e.
exactly the per-record placement our paper calls the naive baseline — and states that *"telemetry
messages in the MAVLink protocol are much smaller than 256 bytes"*. It corroborates both our premise
and our baseline from outside this project, which matters because a baseline one invents oneself is
open to the charge of being a straw man.
⚠️ **It is not a competitor.** HMAC-256 is a symmetric MAC under a group key: integrity and group
authenticity, but **no non-repudiation**, so it cannot underwrite a ledger attributable to a
specific UAV. Different trust model, not a cheaper answer to the same question — the same
distinction that moved TBRD/TESLA to Related Work.

### Al majmaie, Ghajari, Bhatta & Amsaad 2026 — *Blockchain-Driven AI-Enhanced Post-Quantum Multivariate IBS and Privacy-Preserving Data Aggregation for Fog-enabled FANETs*
`2026_pq_fanet_aggregation.pdf` · arXiv:2604.18819 · **USED / POSITIONING**
Blockchain + FANET + post-quantum + aggregation in one design. Cited beside the PQ projection.
⚠️ Its overhead metrics are **signing and verification time**, not wire bytes, so it is
complementary to — not a comparator for — the airtime constraint that binds here.

## Direction C survey tally — SUPERSEDED by the pre-registered protocol

⚠️ **The "9 of 9" tally previously recorded here was inflated** and is retracted. It counted papers
that do not meet the inclusion criteria later fixed in
`docs/DIRECTION_C_SURVEY_PROTOCOL.md` §2 — Bor et al. used **LoRaSim, not ns-3** (its lone ns-3
mention is future work); Mehta et al. is a **survey**; Bhatt et al. is ns-3 but **802.11ah, not
LoRa**. Applying the criteria strictly leaves **4** qualifying papers, all `NONE`.

The live tally now lives in `results/raw/direction_c_survey.csv`, generated by
`analysis/direction_c_survey.py` against a manifest, with every hit adjudicated in writing. See
**F42** for both corrections and for the prior art on the phenomenon itself.

---

## Added 2026-08-07 — the LoRa-vs-WiFi head-to-head (supplied by Mohamed)

| source | status | role |
|---|---|---|
| **Klimiashvili, Tapparello & Heinzelman, *LoRa vs. WiFi Ad Hoc: A Performance Analysis and Comparison*, IEEE ICNC 2020, pp. 654–660** — PDF here, DOI `10.1109/ICNC47757.2020.9049724` (Crossref-verified) | `USED` `VALIDATES` `PRIOR ART` | Does **three** jobs, and one of them cost us a claim. **(1) Corroborates the two-regime framing** — an independent ns-3 study finds neither technology uniformly better (WiFi ad hoc wins delay while single-hop; LoRa wins energy only once WiFi degrades to multi-hop) and recommends *selecting between* them, which is our §VI conclusion reached from the other side. ⚠️ **Qualitative only**: their "almost 5000×" is a PHY bit-rate ratio against DR6's 11 kb/s with no duty cycle, framing or authentication; our ≈4200× is an application-level aggregate. Close in magnitude, **not the same quantity** — recorded so nobody later presents one as confirming the other. **(2) A counter-example to Direction C's H1** — the first paper in the corpus that *does* report replication ("the average of 50 independent runs"), taking the sweep to 4/5 NONE, REPORTS 20 % against a pre-registered 25 % falsification threshold. **(3) Forced us to say which payload column we read** — their Table I lists DR3 at 123 B where we use 115 B. Both are RP002-1.0.3: 123 is *M* (MACPayload), 115 is *N* (application payload), differing by the 8 B FHDR+FPort. ⚠️ **The distinction decides the DR3 verdict** — at 123 B the residual is 15 B and DR3 would be *feasible*. Now argued explicitly in §VI-A. |
