# Paper readability review — terminology and language, with options

> **Applied 2026-10-25** (Mohamed: "do all the recommendations … except L2 and L3"): T1–T6, L1, L4–L13
> and L15; L14 kept the title. Deviation: "analytical contention model" (T4) became **contention
> model**, because the model is an event simulation. ⚠️ T5 and L5 reverse decisions of 2026-10-08
> (the expansion; the exclusion first) and were put to Mohamed. The thesis carries the same names.

*2026-10-25, for Mohamed, after removing Appendix B and redrawing Fig. 4. Read on the built
paper (17 pages). Nothing below has been applied: each item gives options and a recommendation
(**R**). Answer by item number, e.g. "T1: B, T2: A, L3: A".*

Page numbers are those of the current PDF:

| section | page |
|---|---|
| I Introduction | 1 |
| II Background | 2 |
| III System and Threat Model | 3 |
| IV The AUTHBC Frame | 4 |
| V Constraints | 5 |
| VI Methodology | 6 |
| VII Low-Rate Links | 6 |
| VIII Results on 802.11 | 7–14 |
| IX Comparison | 14 |
| X Discussion | 14 |
| XI Limitations | 15 |
| XII Conclusion | 15 |

---

## Part 1 — Terminology (the names a reader meets first)

### T1. "first format" and "lean format" (Sec. IV, Tables II, V, VI, XI, everywhere)

What they are:

| | "first format" | "lean format" |
|---|---|---|
| map keys | text strings | small integers |
| chain link (32 B) | in every record | once per frame |
| sender id, sequence number | in every record | once per frame; derived for each record |
| header | 44 B | 23 B |

The defining difference — the one that moves the bytes most (Fig. 3) — is **where the chain link
travels**.

| option | names | for | against |
|---|---|---|---|
| **A** | **record-linked format** / **frame-linked format** | names the property that matters; Fig. 3 is already "by the position of the chain link" | does not mention the integer keys |
| B | self-describing format / compact format | plain; common in encoding papers | "compact" is vague; "self-describing" stresses keys, not the link |
| C | explicit-field format / derived-field format | exact: the second derives sender, sequence and links | unfamiliar |
| D | v1 format / v2 format | short; matches the code (`wire_v2`) | says nothing |

**R: A**, each defined once in Sec. IV with the table above, e.g. "the *frame-linked format*
carries one chain link per frame and derives each record's sender, sequence number and link".

### T2. "keyframe" and "delta" (Sec. IV onward)

"Frame" already means the radio frame here. "Keyframe" (from video coding) then reads as a kind
of radio frame, though it is a record.

| option | names |
|---|---|
| **A** | **key record** / **delta record** |
| B | absolute record / differential record |
| C | keep keyframe / delta |

**R: A.** The "reference interval r" (one frame in r starts with a keyframe) then becomes the
**key-record interval r**.

### T3. "the design" and "per-record signing / baseline"

The paper uses "the design", "the lean design", "AUTHBC design", "row 8" and "AUTHBC" for one
configuration: frame-linked, four records, one signature, delta records. It uses "baseline",
"per-record signing", "row 5" and "the lean baseline" for the comparison point.

| option | names |
|---|---|
| **A** | **AUTHBC** (b = 4) and **per-record signing**, defined once and used everywhere |
| B | batched signing / per-record signing |
| C | keep the current mix |

**R: A.**

### T4. Smaller terms, each with a recommended replacement

| current | where | recommended | alternative |
|---|---|---|---|
| self-verifying / self-contained / "verifies alone" (three names) | abstract, IV, V, VII | **self-verifying frame**, defined once | "independently verifiable frame" |
| design ladder, ladder, rung | VIII-A, Table V | **step-by-step (ablation) table** | "incremental comparison" |
| crossing, capacity crossing | VIII-C, D | **capacity** ($N_{\max}$), or "the 95 % delivery point" | keep with a definition |
| access rule, access-rule model | VIII-C onward | **analytical contention model** | "DCF access model" |
| capacity envelope, "the rule", airtime line | title, VIII-C | **airtime capacity law** | keep "envelope" (it is in the title) |
| spoilers (nodes able to spoil a frame) | VIII-C | **interferers** | — |
| per-run reading | VIII-C | **per-run capacity** | — |
| emitted frames | abstract, IV, VIII | **frames produced by the implementation** (on first use), then "measured lengths" | — |
| sums of measured parts (†) | Tables V, Fig. 3 | **estimated from measured components** | — |
| group tag | III, VIII | **8-byte group MAC** | "group authentication tag" |
| GNSS-time window Δ | III, VIII | **timestamp acceptance window Δ** | — |
| interpreted / compiled receiver | VIII, Tables VIII, XI | **Python / Rust implementation** | keep |
| lazy verification | VIII, Table VIII | **deferred batch verification** | — |
| neighborhood (of N nodes) | everywhere | keep, defined as "N nodes in one collision domain" | "network size N" |
| "Limited Prize" (run-in) | VIII-B | **"Limited Gain"** | — |
| "Mechanism of the Crossing" | VIII-C | **"Why Capacity Is Where It Is"** | "Loss Mechanism" |

### T5. The acronym AUTHBC

Now: "authenticated telemetry for a blockchain-style, hash-chained ledger"; the letters do not
map.

| option | expansion |
|---|---|
| A | **AUTHenticated telemetry for BlockChain-style ledgers** |
| B | keep as written |
| C | no expansion; AUTHBC as a name |

**R: A** (your decision of 2026-10-08 kept "blockchain-style"; A keeps it).

### T6. A notation table

The paper uses Λ, $D_{\max}$, b, r, p, ε, V, N, $N_{\max}$, $N_{\mathrm{sat}}$, f, T, a, c,
$H_f$, L, $g_a$, $s_k$, $s_\delta$, $t_v$, $T_{ch}$, Δ.

| option | |
|---|---|
| **A** | **a small notation table at the start of Sec. V** (about a third of a column) |
| B | none (as now) |

**R: A.**

---

## Part 2 — Language and ease of reading, by section

### L1. Abstract (p. 1)

The abstract uses "self-verifying frame", "the design" and "gain 3.46–3.63-fold" without saying
what they are, and its last sentence is two facts joined by a semicolon.

| option | |
|---|---|
| **A** | light edit: define the frame in four words, name the comparison ("per-record signing"), split the last sentence |
| B | rewrite as problem → method → three results → one limitation |
| C | keep |

**R: A.**

### L2. Introduction, paragraph 2 (p. 1)

One sentence carries four questions ("what we did not find is the accounting: …").

| option | |
|---|---|
| **A** | **turn the four questions into a short numbered list** |
| B | split into two sentences |
| C | keep |

**R: A.**

### L3. Contribution bullets (p. 2)

They are dense and lean on terms not yet defined ("capacity rule with its mechanism", "a
ladder", "a frame as one object", "the capacity envelope of the title").

| option | |
|---|---|
| **A** | **each bullet as "We …" + one plain claim + its section** (five bullets, about two lines each) |
| B | merge to four bullets: format, bounds, capacity, security |
| C | keep |

**R: A.**

### L4. "…, revealing three key findings:" (four times: VII, VIII-A, VIII-C, VIII-E)

The phrase is the form of your ICEENG paper, but four repeats read as a template.

| option | |
|---|---|
| **A** | **keep the numbered findings, drop the phrase** ("Table V shows three things:" once, then plain lead-ins) |
| B | keep as is |

**R: A.**

### L5. Section order (VII before VIII)

The LoRaWAN section (VII, p. 6) sits before the 802.11 results (VIII), which carry the
headline.

| option | |
|---|---|
| **A** | **move VII after VIII**, so the main result comes first |
| B | keep (the exclusion is the first boundary named in the title) |

**R: A**, unless you want the title's order kept.

### L6. Section VIII is eight pages of mixed topics (pp. 7–14)

It holds the ablation, loss, freshness, capacity, robustness (spread, moving, PHYs, Falcon),
receiver CPU, flooding, certificates, energy, telemetry and validation.

| option | |
|---|---|
| **A** | **split into VIII Results (bytes, loss, freshness, capacity, energy), IX Robustness (spread and moving swarm, batch controller, other PHYs, Falcon-512, telemetry), X Security Evaluation (time window, flooding, audit), then Validation** — same text, new headings |
| B | keep one section, add sub-subsection headings |
| C | keep |

**R: A.**

### L7. "The Capacity Envelope" and "Mechanism of the Crossing" (pp. 10–11)

These are the hardest paragraphs: a fit, its predictions, a derivation and an event simulation
in about 40 lines of prose.

| option | |
|---|---|
| **A** | **keep Eq. (6) and one paragraph of its result; move the derivation to the appendix** (after the frame layout) |
| B | keep in place, split into shorter paragraphs with one claim each |
| C | keep |

**R: A**: it shortens the main text and keeps the derivation for specialists.

### L8. "registered" now appears unexplained (VIII-C "As registered", VIII-H "a prediction registered before the run", twice more)

The appendix and the methods sentence that defined it are gone.

| option | |
|---|---|
| **A** | **one sentence in Sec. VI**: "Where an experiment tests a prediction, the prediction was fixed before the run, and misses are reported" |
| B | reword each use ("as first specified", "predicted beforehand") and drop the word |
| C | keep |

**R: A.**

### L9. Constraints, the freshness paragraph (p. 5)

The peak-age remark ("A record may describe a state up to one sampling interval old; and with
b/Λ the bound is on the peak age …") interrupts the derivation.

| option | |
|---|---|
| **A** | **move it to a footnote** |
| B | keep, reworded into two sentences |

**R: A.**

### L10. Sentence length (throughout)

Many sentences run past 35 words and chain clauses with ";" and "—".

| option | |
|---|---|
| **A** | **full copy-edit pass**: at most about 25 words a sentence, one claim each, numbers kept exactly; I list every change for you |
| B | targeted: only the ~20 longest sentences |
| C | keep |

**R: A.** The paper stays the same length or shortens slightly.

### L11. Limitations, "Capacities Are Simulated" (p. 15)

"Send instants are redrawn within each period. The own stream of PX4, in simulation, holds its
period to about ±0.4 ms, which is nearer to the strictly periodic source and its wider spread
between runs" is unclear.

| option | |
|---|---|
| **A** | rewrite: "Our traffic source randomises each node's send time within its period; a real autopilot is more regular (±0.4 ms), which in simulation gives the same mean capacity but a wider spread between runs" |
| B | delete the two sentences |

**R: A.**

### L12. Captions written as notes ("outlined: simulated in ns-3; hatched: none")

| option | |
|---|---|
| **A** | **full sentences**: "Cells outlined in black were simulated in ns-3; hatched cells admit no batch" (about six captions) |
| B | keep |

**R: A**, within the 27-word limit the tests hold.

### L13. Small text in the other new figures (Figs. 8, 9, 10; Fig. 5's cell labels)

They were drawn at 4.4 in and shrunk to the column, as Fig. 4 was.

| option | |
|---|---|
| **A** | **redraw all at column width with 8 pt text**, as done for Fig. 4 |
| B | only Fig. 9 (three panels, the smallest text) |
| C | keep |

**R: A.**

### L14. Title

"AUTHBC: Feasibility Boundaries for Authenticated UAV Telemetry — An Exclusion Bound and a
Capacity Envelope" is long, and "envelope" is a term the paper then calls "the rule" (T4).

| option | title |
|---|---|
| A | keep |
| B | "AUTHBC: Where Signed UAV Telemetry Fits — Exclusion Bounds and Capacity of Batched Authentication" |
| C | "Batched Authentication for UAV Telemetry Ledgers: Exclusion Bounds and Broadcast Capacity" |

**R: A or C.** Your decision of 2026-10-08 kept the current title; C is offered only because the
paper has grown since.

### L15. Keywords

| option | |
|---|---|
| **A** | **add "age of information", "formal verification", "frame aggregation"** (all now in the paper) |
| B | keep |

**R: A.**

---

## What is consistent already (no change proposed)

* US spelling throughout (neighbor, defense).
* Units: B, µs, ms, Mb/s, records/s.
* Every number is generated from its data.
* Every figure and table is cited in the text.
* Limitations are stated where results are.
