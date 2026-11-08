# Thesis status — what is written, what was checked, what is still missing

*Created 2026-08-30; rewritten 2026-10-08 after the whole built PDF was audited, and updated
three times on 2026-10-09 (findings F63–F83 in `docs/audits/model_provenance.md`), and on 2026-10-24
for the experiments of October (below), and on 2026-10-28 for the review of 2026-10-27. `main.pdf`
builds to 153 pages with no errors, no undefined
references and no overfull boxes. **Read this before showing the PDF to anyone.***

## In one paragraph

Every chapter is written and was read end to end in the built PDF on 2026-10-08. The red
"STATUS" boxes are gone because what they listed is done. **Two red markers remain, and both
are yours:** the declaration and the acknowledgements — with the degree and the department on the
title page. The statement on generative AI was removed on your decision of 2026-10-24.

⚠️ **On 2026-11-08 the derivation of the two capacity models was restated as mathematics, and
you have not read it.** You asked for the assumptions to be defined and for a proof in place of a
table, in the deck, the paper and the thesis ("Deck, paper and thesis").
* **Paper, Appendix "Why capacity is where it is":** rewritten as:
  * Assumptions A1–A7;
  * Lemma 1 (Tie), Lemma 2 (Waiting Together, Eq. B1), Lemma 3 (Detection Window);
  * Proposition 1 (Loss, Eq. B2, the closed form);
  * Corollary 1 (the airtime capacity law as its tangent, a = ρ/(W(1−ρ)), c = 2δ);
  * the contention model as the same rules without the first-order steps.
  * New citation: Sepulcre *et al.*, IEEE TVT 2022 (the CBR, concurrent transmissions, the
    same assumptions in published models).
  * §3.5 gains one sentence pointing to the appendix.
  * **The paper is 43 pp (was 42).**
* **Thesis ch. 8 §"Why the crossing is where it is":** a paragraph "Assumptions" (A1–A7); the
  two mechanisms are labelled Lemma 1 and Lemma 3, the closed form Lemma 2 and Proposition 1,
  and the slope Corollary 1.
* **Thesis ch. 2:** one sentence on Sepulcre *et al.*, and the sentence on who checks against
  what made exact.
* **Thesis:** 160 pp.

⚠️ **Later on 2026-11-07 ("Continue") a second source was credited: Kumar, Choi & Kim, EURASIP
JWCN 2019.** Their four-device 802.11p testbed let each transmitter send for a hundred vehicles,
which is the device by which our four boards stand for many drones. The paper and the thesis
described that device without the citation; the literature register had said to credit it.
* **Paper §3.5, "Capacity on Four Radios":** one sentence after "…interpolated from the
  measured curve.": their transmitters could not sense each other; ours contend for the channel.
* **Thesis ch. 9 (the paragraph "Each board stands for a share of a larger swarm"):** two
  sentences on the same.
* Pages: the paper is still 42; the thesis went from 158 to 159.

⚠️ **On the evening of 2026-11-07 one source was credited, and you have not read the
sentences.** You asked, reviewing the seminar deck, for prior work or an official law behind the
airtime capacity law and the contention model. Bazzi *et al.*, IEEE PIMRC 2016, already asked the
law's question for vehicle beacons (the highest beacon rate at a loss target, found numerically)
and counted our first loss mechanism (busy, then the same slot). Not crediting it would be the
F9/F65 defect a third time. Pages unchanged: thesis 158, paper 42.
* **Paper §3.5, "The Airtime Capacity Law":** one new sentence after "We call Eq. (7) the airtime
  capacity law …" (the question is theirs; the closed form in airtime is ours). In "The Contention
  Model", `bazzi2016beaconing` was added to the citation of the first mechanism.
* **Thesis ch. 2 (non-saturated broadcast):** one sentence on Bazzi *et al.*; "Both check" became
  "All three check", and "which neither has" became "which none has".
* **Thesis ch. 8 §"What is known, and what is added":** two sentences on Bazzi *et al.*; "Neither
  analysis" became "None of the three"; "Their fixed point" became "The fixed point of Cao *et al.*".
* The official counterparts (the IEEE 802.11 airtime link metric; ETSI TS 102 687's channel busy
  ratio) are on the seminar slides only, not in the paper or thesis. The register entry,
  `docs/literature/README.md` "Added 2026-11-07 (evening)", says why.

⚠️ **On 2026-11-07 W3a and the novelty framing were written in, and you have not read them.**
You asked: "Do it", read ePrint 2022/133, "take care of the novelty framing … honestly and
scientifically", and strengthen the paper's framing. The thesis builds to 158 pages, the paper to
**42 (from 40; you chose to keep it until the journal is chosen)**. In reading order:
* **Thesis:**
  * **ch. 1, Contributions:** a new opening paragraph on what is known and what is added. The
    larger step of the capacity gain, sharing the frame, is the established one. The validation
    bullet gains the loss on air.
  * **ch. 2:**
    * Rotta & Mykytyn's relays aggregate messages into one 802.11 frame, each keeping its tag
      (row 6 of the ladder);
    * a new paragraph on message chaining (Cominetti et al.: the verifier's work falls and the
      bytes rise);
    * *Where this thesis sits* opens with the three costs and a new **Table `tab:position`**.
  * **ch. 7:** a new subsection, *Loss measured on air* (W3a), with the loss table, the three
    claims, the length penalty, the bursts, a footnote correcting two reported figures, and what
    it cannot show.
  * **ch. 8, E17:** a paragraph on why chaining and relay aggregation are not in the stream table.
  * **ch. 9, *What the hardware supports*:** a bullet on the loss on air.
  * **ch. 12:**
    * finding 6 gains the 2.2× / 1.6× split;
    * a new finding 12 (loss on air);
    * *Modelling scope*: "no loss was measured on air" is replaced by its scope;
    * *Closing*: one sentence on the established mechanism.
  * **App. B:** row 13 (W3a); ch. 6 counts thirteen.
* **Paper:**
  * **§1, paragraph 2, rewritten on three costs:** the signer's work, the verifier's work and the
    bytes. None reduces frames; sharing a frame is established (802.11n, not for broadcast;
    Rotta's relays). Gündoğan is credited. The gap sentence is narrowed to "the accounting that
    decides between these options for authenticated telemetry".
  * **Contributions:**
    * 1, *Where the gain comes from*: 2.2× is the established step, 1.6× the signature's, a 13 B
      tag reaches 42.1;
    * 2 gains the four-radio ratio;
    * 3 gains Λ·D_max > 2 and the loss on air.
  * **§1.1:** a new **Table 1 `tab:position`**; a sentence after it; Rotta's relays; Cominetti's
    chaining.
  * **§3.2:** item 3 gains one sentence; a new run-in, **Loss on Air**.
  * **§3.4:** Rotta joins the 802.11n aggregation sentence.
  * **§4.2, *What generalizes*:** 802.11n is credited for the frame's fixed cost; the
    authentication consequence is ours; the V2X sentence cites Cominetti.
  * **Table 18, footnote 1:** "only the ratio was measured".
  * **Limitations, *Loss Models*:** rewritten to the link measured.
  * **Conclusion:** one sentence on the three costs, one on the loss on air.
  * The abstract and the title are unchanged.
* ⚠️ **The paper is 42 pages.** Its content is about 41.4: page 42 holds the last references. My
  own added text was tightened once. It grew by the table, the loss paragraph and the framing.
  **Decided 2026-11-07: keep 42 pp until the journal is chosen (I1).**

⚠️ **On 2026-11-06 the hardware campaign and the desk work of November were written in, and you
have not read them.** You asked for it ("finish the paper and thesis") and chose to apply Q8, Q9
and Q11–Q14 as drafted. The PDF builds to 156 pages. In reading order:
* **ch. 1:** the validation contribution names the ratio measured on four radios.
* **ch. 3:** canonical encoding is injective, proven and tested; it is no longer "assumed" (Q14).
* **ch. 7:** a new paragraph, *At the largest records the schema allows* (W4a: AUTHBC keeps
  2.75× at the schema bound).
* **ch. 8:** the remark *What this does not show* gains two sentences: the four-radio ratio, and
  the contention windows of commercial cards (W1a: the ratio 3.48–3.52 against 3.53).
* **ch. 9, §Hardware: three new subsections.**
  * *Three and four radios at 2.4 GHz* (W1b–W1f);
  * *Balancing four radios* (W1g–W1i, the square layout, the preflight);
  * *The ratio on four radios* (W1j, W1k, with Table 9.x).

  *What the hardware supports* is rewritten, with Q8's sentence; "No capacity was measured" is
  gone.
* **ch. 12:** a new finding (the hardware ratio). *Validation scope* is rewritten. *Security
  scope* gains the GNSS holdover and the injective encoding (Q14).
* **App. B:** a third table, *The registrations of November 2026*, with twelve rows (Q11). ch. 6
  counts them.

The paper changed in the same places: abstract, methods, §Results *Contention Model on Radios*
with a new *Capacity on Four Radios* and Table *tab:hw*, the limitations (Q12, Q13, Q14) and the
conclusion. Q9 is a footnote. It is still 40 pages.

⚠️ **On 2026-10-27 and 28, after the review of the paper** (`docs/review 27-10-2026/CHANGE_LOG.md`),
three things changed here as well, and you have not read them:
* **ch. 8:** a paragraph on the capacity at 97 % delivery (S-01: 27.6 and 97.3 nodes, both
  predicted), and the receiver table's nodes per core by Eq. (4) (290 and 629, were 289 and 628).
* **App. B:** the S-01 registration is the eighteenth row of the October table; ch. 6 counts it.
* **Figures:** all redrawn at 4.5 in in one serif font; Fig. 3.1 is TikZ.

⚠️ **On 2026-10-25 the names changed throughout** (your decision): record-linked and
frame-linked format (were first and lean), key record (was keyframe), contention model,
group MAC, deferred batch verification. Figures are redrawn at print size. Nothing else in the
chapters changed that day.

⚠️ **On 2026-10-24 the experiments of October 2026 were written into the chapters they belong to,
and you have not read them.** Each result sits where its subject is:

* **ch. 1:** three contributions.
* **ch. 2:** mobility, FMAC, hidden terminals and Tamarin.
* **ch. 3:** your block diagram as Fig. 3.1, redrawn in TikZ on 2026-10-27 with the agreed names
  (the paper's own file, `fig_overview_tikz.tex`; each constraint box points to its section here); two rows of the claims table; *Formal analysis, and
  the evidence for each property* with its table; two items of "what is not claimed" rewritten.
* **ch. 4:** peak age under loss, the window on GNSS time, the loss margin, the design map.
* **ch. 5:** admission (group tag, cheap checks, rate cap) and the compiled codec.
* **ch. 6:** intervals that cover, registrations, the new scenarios, the compiled sender and the
  floods.
* **ch. 7:** traced loss and the margin figure; richer records and airframes with their table.
* **ch. 8:** compiled receiver table, stream schemes run in time, a spread and moving swarm, a
  batch chosen at run time, other PHYs and Falcon-512, flooding, the design map, compiled energy
  rows.
* **ch. 9:** the access rule away from its operating point.
* **ch. 10:** other broadcast links with their table.
* **ch. 12:** three findings; limitations and future work rewritten. Nothing on hardware still to
  be bought is stated (your decision).
* **App. B:** a second table, the eighteen registrations of October with commit and outcome.

⚠️ **Chapter 9's hardware section was rewritten on the night of 2026-10-09 and has not been read
by you.** It now reports contention measured between two radios — one registered prediction
that held, one that failed at one load of three, a follow-up in which all four failed —
and withdraws a figure ("airtime within 0.36 %") that earlier versions and the paper carried.
Read the section *Hardware* of chapter 9 before the supervisor does.

⚠️ **On the afternoon of 2026-10-09 a review of the paper changed seven places of the thesis,
and you have not read them either** (F80–F83). In reading order: ch. 2 — three new passages
(erasure-coded stream authentication, ADS-B, a subsection on frame aggregation); ch. 3 — the
remark *What the receiver keeps, and what it did not*; ch. 4 — the last paragraph of the
freshness remark (the bound is a peak age); ch. 8 — a second certificate column with its
remark, the receiver's time after it keeps frames, and the table of three other batch sizes;
ch. 10 — a fifth scope condition; ch. 12 — the limitations; Appendix B — two more
registrations.

⚠️ **And that evening, for four weak points of the same review** (F84, F85): ch. 8 — the
paragraph *The board's four cores, measured* (124 nodes need three cores, not 2.2; two
registered ranges failed), the figure of capacity against deadline, and the section on nodes
spread out with capture; ch. 12 and Appendix B follow them.

## Per chapter

| ch | title | state | what remains |
|---|---|---|---|
| — | front matter | written | ⚠️ **degree, department, declaration, AI statement, acknowledgements — only Mohamed** |
| 1 | Introduction | audited | — |
| 2 | Background and Related Work | **three passages added 2026-10-09 (F83)**: erasure-coded stream authentication, ADS-B, frame aggregation — each source read first; audited before that; a general survey and the Remote ID standard added; all four aggregate-signature schemes and the 2009 analysis of non-saturated broadcast obtained and read (F68, F72) | two older analyses of non-saturated broadcast are closed access and not held (`OPEN_ITEMS` G23) |
| 3 | System Model and Threat Model | audited; **remark added 2026-10-09 (F80, F81): the receiver did not keep what it verified, and now does** | — |
| 4 | Theoretical Framework | audited; the freshness bound named a peak age (F83); two figures and one theorem statement corrected (F64); worked examples for T2 and T4 | — |
| 5 | Implementation | **expanded**: package figure, one frame byte by byte, receiver outcomes, test layers | — |
| 6 | Experimental Methodology | **expanded**: generator, how a capacity is read, timings, energy rig, uncertainty; says since 2026-10-09 that the energy table tests times and not power, describes the rig check, and reports the second-sensor control and the re-metered JSON row | the energy sensor's calibration (G22) |
| 7 | Results I | audited | — |
| 8 | Results II | audited; RQ3 now has its numbers; prior work for the derivation credited (F65); **the lean codec timed and metered on the board, Ed25519 batch verification measured (F77, F79)** — the prototype's receiver serves 57 nodes per core; the lean sender costs 2.7 times the first format's energy | — |
| 9 | Model validation and hardware | **hardware section rewritten 2026-10-09**: link loss; a withdrawn airtime figure (F74); one radio's frame spacing; two radios at a set load (F73, F75); two saturated radios (F76) | three to five radios (G4); the cause of the shortfall below saturation (G27) |
| 10 | Low-rate regime | audited; **mobility subsection added**; **a fifth scope condition (F80, F81): three of the eight exclusions are this format's** | — |
| 11 | Reproducibility | **expanded**: how citations are checked, where the chapter sits; Kurkowski et al. 2005 now held and cited directly | — |
| 12 | Conclusions | audited; **research questions answered one by one**; four stale items corrected | — |
| A | Reproducing the results | new | — |
| B | Predictions registered before their data | twenty, by commit; seven failed in whole or in part; one run with two boards of the five it covers | ⚠️ **merge pull requests with a merge commit** — squashing would erase the commits this table cites |
| C | Results that were corrected | new 2026-10-09: the three superseded figures and the old envelope table, moved out of the results chapters | — |

## What a supervisor may still say, and why it is not fixed

* **"The capacities are simulated."** True, and stated first among the limitations. No capacity
  was measured: two radios cannot reach one.
* **"Has the capacity mechanism been seen on a radio?"** Between two saturated radios, yes,
  within 6 % of the standard's rule, from a prediction registered first. Below saturation the
  registered prediction failed at the highest load, and the thesis says so and says what is
  not explained (ch. 9).
* **"Your own hardware check of August was wrong."** Yes. It is withdrawn in a remark in ch. 9
  that says how two errors cancelled; `results/hw/channel/RESULTS.md` keeps the old text under
  a correction.
* **"Your prototype cannot keep up with 124 nodes on one core."** True: 57. Ch. 8 gives the
  number and says the ceilings are for a compiled receiver.
* **"Is your energy table of the design you report?"** Since 2026-10-09, yes: the lean sender
  is metered (155.4 µJ per record) on a second board and sensor, with a control that ties that
  rig to July's within 2.2 %. It costs 2.7 times the first format's energy per record, and
  ch. 8 says so in bold.
* **"Was the meter calibrated?"** No. Two sensors agree with each other within 2.2 %; neither
  has been checked against a known load (G22). Ch. 6 says so.
* **"Is your meter-against-model comparison circular?"** In its power, yes, and ch. 6 says so:
  the model's power is the median of the metered runs. What the table tests is the times.
* **"Sixty-five references is few."** Every one was read at source. Raising the number means
  reading more, not listing more (G23).
* **"Chapter 11 is unusual."** It is deliberate. It now says where it sits in the literature.
* **"Can your board serve 124 nodes at all?"** With three of its four cores, measured: two serve
  106, three 150, four 187. The cores scale at 1.90, 2.70 and 3.36 times one — the last two
  below what was written down beforehand, and ch. 8 says so.
* **"Most of your capacity gain is frame aggregation."** About three fifths, yes. Ch. 2 and
  ch. 8 say so, cite the 802.11n mechanism, and say why a broadcast sender cannot use it.
* **"Your exclusion count depends on your own header."** For three of the eight, yes; five
  hold in any format. Ch. 10 has it as a fifth condition and the abstract gives the split.
* **"You only simulated one batch size."** One and four for every result; two, three and eight
  for the capacity rule, predicted before they were run, all six predictions held (ch. 8).
* **"Does a receiver keep anything a third party could check?"** Since 2026-10-09, the frames.
  Before that, no — and the thesis says so in ch. 3.

## Rules that keep it true

* **No typed results.** Numbers are macros from `numbers.tex`, which `make thesis` copies from
  `paper/numbers.tex`, which `analysis/paper_numbers.py` writes from `results/`. What *is*
  typed is held to its artifact by `tests/test_thesis_matches_artifacts.py`.
* **After changing a results chapter, re-read chapters 1, 11 and 12.** Four statements there had
  gone stale because a correction stopped at the chapter it was made in (F64).
* **`thesis/tab_worked_frame.tex` is generated** (`analysis/worked_frame.py`); a test compares.
* **Before any submission, `grep -c '\\needswork{' thesis/*.tex` must total 0.**

## Build

```bash
make thesis        # → thesis/main.pdf
```
