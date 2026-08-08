# Direction C — what is still missing

*Updated 2026-08-08. Most of the earlier worklist was retrieved after all: **Unpaywall**,
**Semantic Scholar** and the **Europe PMC REST API** return legal open-access copies that the
publishers' own web front-ends refuse to serve to a script. Seven of the thirteen were obtained
that way, six of them qualified, and the corpus is now **20**.*

## Still needed — 5 papers

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

## Two rules that still apply

⚠️ **Do not select on whether a paper looks like it reports seeds.** That is selecting on the
dependent variable and would invalidate the sweep (protocol §2).

⚠️ **PDFs only — never a summary, abstract or saved HTML page.** The sweep is a mechanical scan
over full text; a summary would manufacture "no replication reported" verdicts, which §3 names as
the likeliest way this survey produces a false result.

## Where the corpus stands

| | |
|---|---|
| corpus, fully adjudicated | **20** |
| no replication reported | 17 |
| reports it | 3 |
| REPORTS share | **15.0 %** vs a pre-registered 25 % falsification threshold |
| protocol target | 56 |

Adding all five above would take it to **25**.
