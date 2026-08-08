# Direction C — papers to download manually

*For Mohamed, 2026-08-08. These are the ns-3 LoRa simulation studies I identified but could not
retrieve: MDPI, PMC, IEEE and ACM all refuse scripted download from this environment and return a
challenge page. arXiv works, so everything reachable there is **already in the corpus**.*

## What to do

1. Download the PDFs below.
2. Save each with **exactly the filename in the last column** into `docs/literature/`.
3. Tell me they are there. I run `make survey-direction-c`, hand-adjudicate every keyword hit in
   context, and update the paper and the register.

⚠️ **Do not skip a paper because it looks like it does or does not report seeds.** The corpus must
be assembled on topic alone — selecting on the thing being measured is exactly the bias the
pre-registered protocol forbids (§2). If it is an ns-3 LoRa simulation study, it goes in.

⚠️ **Do not send me a summary, an abstract, or an HTML page in place of the PDF.** The sweep is a
mechanical keyword scan over full text; running it on a summary would manufacture "no replication
reported" verdicts, which protocol §3 names as the single most likely way this survey produces a
false result. A missing paper is fine. A summarised one is not.

---

## Priority 1 — near-certain to qualify (ns-3 LoRa simulation studies)

| # | paper | venue / year | DOI or link | save as |
|---|---|---|---|---|
| 1 | Magrin, Capuzzo & Zanella, *A Thorough Study of LoRaWAN Performance Under Different Parameter Settings* | IEEE Internet of Things Journal, 2020 | `10.1109/JIOT.2019.2946487` | `magrin2020_lorawan_parameter_settings_ns3.pdf` |
| 2 | Reynders, Wang & Pollin, *A LoRaWAN module for ns-3: implementation and evaluation* | ACM WNS3 '18, 2018 | `10.1145/3199902.3199913` | `reynders2018_lorawan_module_wns3.pdf` |
| 3 | Finnegan, Brown & Farrell, *Evaluating the Scalability of LoRaWAN Gateways for Class B Communication in ns-3* | IEEE CSCN, 2018 | `10.1109/CSCN.2018.8581759` | `finnegan2018_classb_gateway_scalability_ns3.pdf` |
| 4 | Abakar, Bennis & Abouaissa, *A Multi-Gateway Behaviour Study for Traffic-Oriented LoRaWAN Deployment* | Future Internet 14(11):312, 2022 | `10.3390/fi14110312` · [mdpi.com/1999-5903/14/11/312](https://www.mdpi.com/1999-5903/14/11/312) | `abakar2022_multigateway_lorawan_ns3.pdf` |
| 5 | Saraereh, Alsaraira & Khan, *Performance Evaluation of UAV-Enabled LoRa Networks for Disaster Management Applications* | Sensors 20(8):2396, 2020 | `10.3390/s20082396` · [mdpi.com/1424-8220/20/8/2396](https://www.mdpi.com/1424-8220/20/8/2396) | `saraereh2020_uav_lora_disaster_ns3.pdf` |
| 6 | Kufakunesu, Hancke & Abu-Mahfouz, *Collision Avoidance Adaptive Data Rate Algorithm for LoRaWAN* | Future Internet 16(10):380, 2024 | `10.3390/fi16100380` · [mdpi.com/1999-5903/16/10/380](https://www.mdpi.com/1999-5903/16/10/380) | `kufakunesu2024_collision_avoidance_adr_ns3.pdf` |
| 7 | Kufakunesu, Hancke & Abu-Mahfouz, *A Fuzzy-Logic Based Adaptive Data Rate Scheme for Energy-Efficient LoRaWAN Communication* | J. Sensor & Actuator Networks 11(4):65, 2022 | `10.3390/jsan11040065` · [mdpi.com/2224-2708/11/4/65](https://www.mdpi.com/2224-2708/11/4/65) | `kufakunesu2022_fuzzy_adr_lorawan_ns3.pdf` |
| 8 | Anwar, Rahman & Zeb, *RM-ADR: Resource Management Adaptive Data Rate for Mobile Application in LoRaWAN* | Sensors 21(23):7980, 2021 | `10.3390/s21237980` · [mdpi.com/1424-8220/21/23/7980](https://www.mdpi.com/1424-8220/21/23/7980) | `anwar2021_rmadr_mobile_lorawan_ns3.pdf` |
| 9 | Teymuri, Serati & Anagnostopoulos, *LP-MAB: Improving the Energy Efficiency of LoRaWAN Using a Reinforcement-Learning-Based Adaptive Configuration Algorithm* | Sensors 23(4):2363, 2023 | `10.3390/s23042363` · [mdpi.com/1424-8220/23/4/2363](https://www.mdpi.com/1424-8220/23/4/2363) | `teymuri2023_lpmab_lorawan_ns3.pdf` |
| 10 | Tito-Lara *et al.*, *Inter-Protocol Interference Impact of LoRaWAN on IEEE 802.11ah in a Simulation Environment* | Sensors 25(22):6924, 2025 | `10.3390/s25226924` · [mdpi.com/1424-8220/25/22/6924](https://www.mdpi.com/1424-8220/25/22/6924) | `titolara2025_lorawan_80211ah_interference_ns3.pdf` |

**Note on 10** — it is also the closest published thing to our two-arm framing (LoRa and 802.11
sharing an environment), so it is worth reading beyond the survey regardless of its verdict.

## Priority 2 — arXiv preprints whose PDFs will not serve to me

Both are LoRaWAN multi-hop ns-3 work. The abstract pages load; the PDF endpoint returns HTML on
every attempt and both mirrors. They may render for you in a browser.

| # | paper | link | save as |
|---|---|---|---|
| 11 | *Optimizing Multi-hop Mechanism for the Long Range Wide Area Network* | [arxiv.org/abs/1811.05386](https://arxiv.org/abs/1811.05386) | `multihop_optimization_lorawan_ns3_2018.pdf` |
| 12 | *Trilateration-based Multi-hop for the Long Range Wide Area Network* | [arxiv.org/abs/1811.06345](https://arxiv.org/abs/1811.06345) | `trilateration_multihop_lorawan_ns3_2018.pdf` |
| 13 | *Long Range Wide Area Network: A Simulation Module for ns-3* | [arxiv.org/abs/1811.05829](https://arxiv.org/abs/1811.05829) | `lorawan_simulation_module_ns3_2018.pdf` |

## Priority 3 — grab if convenient, likely to be EXCLUDED

| paper | why it may not qualify |
|---|---|
| *Survey and Comparative Study of LoRa-Enabled Simulators for IoT and WSN*, Sensors 22(15):5546, `10.3390/s22155546` | A **survey**. Fails criterion 1 (must present its own simulation results). Useful to us as a source of further candidates, not as a corpus entry. |

---

## If you want to push toward the protocol's target of 56

The bottleneck is retrieval, not identification. A search that keeps the corpus unbiased:

* **Google Scholar / IEEE Xplore / Scopus**, query on the **topic only**:
  `LoRa ns-3 simulation`, `LoRaWAN ns-3 scalability`, `LoRa "network simulator 3"`,
  `LoRaWAN simulation spreading factor gateway`.
* ⚠️ **Never** put `seed`, `confidence interval`, `Monte Carlo`, `runs` or `replication` in a query.
  That selects on the dependent variable and would invalidate the sweep.
* Include anything that (a) presents its own LoRa/LoRaWAN **simulation results** and (b) says the
  simulator is **ns-3**. Exclude surveys and papers whose simulator is FLoRa, LoRaSim, OMNeT++ or
  their own framework.
* The forward-citation lists of Magrin's ns-3 module paper (#1, #2 above) and Van den Abeele's
  scalability paper are the densest source of qualifying work.

## Where this stands now

| | |
|---|---|
| corpus, fully adjudicated | **14** |
| no replication reported | 12 |
| reports replication | 2 (Klimiashvili 2020; Khan, Jurdak & Portmann 2019) |
| REPORTS share | **14.3 %**, against a pre-registered 25 % falsification threshold |
| protocol target | 56 |

Adding all of Priority 1 and 2 would take the corpus to roughly **27**. That does not reach 56, but
it roughly doubles the base and — more importantly — it would fix the current sampling bias, which
is that everything in the corpus today came from arXiv.
