# Logbook — what was done, what was tried, what was found, in order

*Purpose: the one place that records **method and trial**, not just outcome. The findings register
(`audits/model_provenance.md`) says what is true; the decision log (`DECISIONS.md`) says what was
chosen; this says **how we got there, including the paths that failed**. A wrong turn that is not
written down gets taken twice.*

**How to use it.** Newest first. Each entry: what we were doing → what we tried → what happened →
where the durable record lives. If you want the conclusion only, follow the pointer.

**Index of every document** → [`docs/README.md`](README.md).

---

# 2026-10-09 — "solve all the issues": what could be closed from here, and what could not

*Mohamed, after the audit: "solve all the issues and contradictions except the front matter".
The audit had left five: contention never measured; three older papers not obtained; few
references and two gaps of reading; superseded figures among the results; the sensor never
calibrated. Durable records: F68–F71; registration `456a4e7`.*

## What was reachable

Nothing physical. No board answered and no meter was attached, so every hardware item was
reduced to its last step and left there, said plainly. Papers were sought through open indexes
(OpenAlex, Crossref, Semantic Scholar, CORE, arXiv) with no identifier of the user in any
request.

## Reading

Two sources were obtained and read: a general survey of UAV networks (Gupta et al.) and one of
the four aggregate-signature schemes the thesis knew only through another paper's table (Wang
et al.). **The second corrected a claim (F68).** Both documents said the cost of n messages is n
times the cost of one. That is what each signer sends; what the *aggregator* forwards is one
compact aggregate. The claim had been written from a table that counts the first link. It is
the supervisor's kind of comment — an assertion one size too wide — found by doing the reading
the thesis had said it lacked.

**Tried and not obtained.** Three CC BY papers are served only behind a script challenge, by
their publishers and by the public aggregator alike. I did not work round it. Three more are
closed access. They are listed by DOI for a browser (G23, G24, G8).

**A source read in part is now recorded as read in part.** The thesis said every source was
read in full. For a 32-page survey and a 60-page standard that was not true of every section.
The sentence now says what is true, and the register says which parts.

## Contention

A real experiment was designed for the boards on hand, and registered before any board was
switched on. The useful idea came from asking what two radios can show that three cannot:
with two, the only receiver is the other transmitter, so capture — the thing that would blur
a comparison with a model that has none — cannot happen.

**Checked before registering, and it found something.** The model had only ever been compared
with ns-3 at 28 nodes and more. Run at two to five, ns-3 agrees within 5 % from three nodes up
and is 9–18 % below the model at two. A prediction registered without that check would have
carried an unknown bias into the one case meant to be sharp.

**The check itself first crashed.** ns-3 aborted at 116 frames per second: the driver's "one
period" of jitter exceeded the scenario's guard by one unit in the last place (F69). Diagnosed
by running the binary by hand; fixed in the driver with a test over a sweep of rates.

## Tried and wrong

* **Splitting the work into two commits.** The registration had to be a commit of its own. I
  staged it, stashed the rest, found that the test counts differ in that tree (two fewer
  bibliography entries mean fewer parametrised tests), corrected three count lines — and the
  stash then conflicted on those lines when restored. Resolved by hand and verified identical
  to what had been set aside, file by file, before the stash was dropped. Do the count before
  the stash.
* **A test that needed a PDF library nobody had declared.** Written, then caught by the guard
  added yesterday before it was ever committed. The guard earned its place in a day.
* **Two locally held PDFs appeared as "in the repository"** while their manifest lines were
  stashed. An artifact of the split, not of the repository; they were moved aside for the check.

## Layout

The three superseded figures and the old envelope table moved to an appendix of their own.
The history is as visible as before; the results chapters now show only what is current.

---

# 2026-10-08, later — the paper and the thesis read whole, as built

*Mohamed: "audit the paper and the thesis and make sure they are strong and complete and will
not have any future comments from any supervisor". Nobody can promise the last part. What could
be done was to read both documents as an examiner would and remove everything that reading
found. Durable records: F63–F67; open items G22–G25.*

## Method

1. **The deliverable, not its source.** Both PDFs were converted to text and read end to end —
   10 pages and 100 — beside a list of the *kinds* of comment the supervisor's review had made
   (a headline that does not match its table; a count that moves; a claim wider than its
   evidence; a missing comparison; a name never defined).
2. **Mechanical checks first**: LaTeX and BibTeX logs, placeholders, references that print
   without an identifier, phrases the review had objected to.
3. **Every suspicion checked at the source before a word was changed** — a number against its
   CSV, a formula against the code, a sentence against the chapter it summarises.
4. **Everything typed in the fix is pinned by a test.**

## What it found

The paper: no result moved; twelve defects of presentation (F63). The thesis: six statements
that were wrong and seven that had gone stale, a test cited in the conclusions and reported
nowhere, seventeen places where a table ran off the page (F64, F67). And one thing that matters
more than the rest:

**The derivation written this morning had prior work, and no search had been made (F65).** One
query found a 2021 analysis of periodic 802.11p broadcast with the same first mechanism. It is
now credited, and what this work adds to it is stated. That is F9 a second time: in July the
project rediscovered a published broadcast model and lost a novelty claim, and wrote down
"search before deriving". The rule did not survive one busy day.

## Tried and wrong

* **A false alarm of my own.** Checking that the generator's default stream was unchanged, I
  compared lists of records from two copies of the module and got "different" — the two copies
  define two classes, and a dataclass is equal only to its own class. Compared field by field
  they are identical. A check has to be checked.
* **A guard I nearly widened.** The registry lists RFC 9575's editor apart from its authors, so
  my entry failed the citation check. The quick fix was the override that exists for registry
  abbreviations; a test allows that override for exactly one entry and requires a held file.
  The entry now cites the RFC as the registry does, with the editor in a note.
* **Three sources I could not get.** The open-access paper by the authors of the broadcast model
  is behind a cookie redirect that refuses scripts. I did not work around it; it is G23.
* **The module figure** first drew an arrow through two boxes, and the byte table wrapped its
  hex column. Both were seen only by rendering the page and looking.

## What was not done, on purpose

Superseded figures stay where they are (a choice of style, for Mohamed). No new experiment was
run. Nothing was added to the reference list that was not read.

---

# 2026-10-08 — eighteen decisions taken, and the work they asked for

*Mohamed answered every open point with an option, and: "handle all in parallel but in the
correct logical order to save time and credit". The decisions are in `DECISIONS.md`. This entry
is what was done under them, in the order it was done, and why that order.*

## The order, and why

Long unattended jobs first, each after its prediction was committed; writing while they ran.

1. The decisions recorded, the pull request to `main` opened (not merged — his to merge), and a
   new branch cut so the request he reads stays fixed.
2. PX4 download and build started; the fresh-seed campaign (F4) registered, committed, launched.
3. While both ran: the derivation, the bench-session kit, one paper read, thesis chapter 2.
4. The simulated flight, registered before it was flown.
5. The derivation's predictions (F5), registered before their runs; queued behind F4 because the
   doubled contention window needs a rebuilt binary, and a campaign's binary is not replaced
   while it runs.

## The derivation (decision 14-c) — F58

The airtime line had a fitted slope "near 1/W₀" that nobody had explained. Writing down how a
frame can be lost here gave two mechanisms — a tie between backoff counters, and the 4 µs in
which a transmission cannot yet be sensed — and a closed form with no free constant that put
the eighteen crossings within 5.5 %. An event simulator of the access rule, 150 lines sharing
nothing with ns-3, then reproduced all eighteen within 1.2 %.

**Tried and wrong the first time.**
* The simulator's first version delivered 0.005 too much everywhere. It handled a frame arriving
  within 4 µs *after* a counter runs out and not one arriving just *before*: half the window.
  Found by comparing with one ns-3 cell — which is why the agreement with the eighteen is
  recorded as a comparison and not as a prediction.
* Its first loop never ended when the detection window was set to zero (a unit test found it).
* I wrote that the fit "had found the slope to three figures". It had not: the tie term's slope
  equals the fitted 0.071 at the *mean* occupancy of the crossings and varies by ±25 % cell by
  cell. Corrected, with a dated note in the registration, before any F5 run.

**Then it was asked for something it had not seen (F5 → F62).** Six crossings were registered
before any of their runs, with a ±3 % band: the contention window doubled, and loss levels of
2 % and 10 %, each for the baseline and the design. The doubled window needed a new option in
the ns-3 scenario; the rebuilt binary first reproduced nine stored runs bit for bit, and the
option at its default value gave the default's output. 1,080 runs later:

| case | registered | ns-3 | error |
|---|---|---|---|
| baseline, window doubled | 39.09 | 39.18 | +0.23 % |
| design, window doubled | 139.03 | 139.61 | +0.42 % |
| baseline, 10 % loss | 46.77 | 47.36 | +1.26 % |
| design, 10 % loss | 165.30 | 166.79 | +0.90 % |
| baseline, 2 % loss | 22.49 | 22.40 | −0.39 % |
| design, 2 % loss | 79.65 | 78.27 | −1.73 % |

All six inside the band, recounted from the run files by a second route. Two simpler readings
were written down beside the first case before its runs and both missed: scaling the fitted
line by 1/W gives 53.4, the closed form 42.6; ns-3 gave 39.2. Doubling the window buys 11–12 %
more neighbours, not twice as many — stations that count down for longer wait together more
often, so the tie probability does not halve.

## The simulated flight (decision 13-a) — F60

PX4 v1.17.0 needed no system packages, but its recursive download stalled for twenty minutes on
simulator models the build does not use; killing it left four small libraries cloned and empty,
and the build failed twice until each was checked out by hand.

The sizes came out as predicted and slightly better than the generator's. Two predictions did
not hold as written: the 0.2 s comparison missed its range by 0.04 B (the flight is more dynamic
than the real logs), and the timing statistic could not be scored because **the measuring host's
wall clock was stepped back eight times during the flight**. The stream's regularity was
recovered from an interquantile spread and a second capture on a monotonic clock: 20.0 ms,
±0.37 ms.

**Tried and wrong the first time.**
* The first flight hung at 28 m waiting to reach 29: the vehicle settles under the commanded
  height. The climb is now over when the altitude stops changing.
* ⚠️ `pkill -f` killed its own shell **twice more** today. The bracket trick protects against the
  pattern matching *itself*; it does nothing when the same string appears elsewhere in the
  command line (here, a file name passed to the next command). Kill in a command of its own.

## The traffic-source question (decision 14-b) — F61

Fresh seeds, registered first: the +0.0031 between the two sources **did not replicate**
(+0.0004 ± 0.0009 on 1,260 runs). Closed.

**And an explanation of mine did not survive its own check.** I had written into the same
registration that the crossing rule reads low on noisy means, to account for all six crossings
being lower under periodic senders. Resampling showed the rule is unbiased; the six were one
fluctuation of one set of thirty seeds. The paper's sentence quoting "1–9 % lower" is withdrawn.
Designing the test also changed it for the better: the periodic source carries nearly all the
noise, so it got sixty fresh seeds and the redrawn source thirty — the same machine time bought
a standard error of 0.0009 instead of 0.0014.

## A caveat found by preparing a measurement — F59

Timing the lean receiver for the bench kit showed that the prototype spends several times more
on decoding than on verifying. The paper's receiver-CPU ceiling charges cryptography only, so
"the channel binds first" is true of a compiled receiver and not of the prototype. The paper and
thesis now say so; the bench session will put a number on it.

## A failure: the frozen gate was green here and red on a clean install

Worked through in the structure of `docs/06` §7.

* **WHAT.** After the push of `1a5baf7`, CI's `make verify-frozen` failed, 1 of 38:
  `tests/test_px4_sitl.py::TestTheFlightThatWasRegistered::test_the_artifacts_are_the_analysis_of_the_raw_files`
  — `ModuleNotFoundError: No module named 'pyulog'` at `analysis/px4_log_sizes.py:160`.
  Lint, types and the 1951 fast tests had passed there. `make all` had exited 0 on this machine
  minutes before.
* **CONTEXT.** Branch `p10-followups`. The test was added with the simulated flight (`989fac9`);
  it re-derives `px4_sitl_sizes.csv` and `px4_sitl_stream_timing.csv` from the committed
  `flight.ulg`. No earlier CI run had seen it: the branch was pushed for the first time today.
* **REPRO.** `sys.modules["pyulog"] = None`, then that one test: the same error, here.
* **HYPOTHESES.** H1, the package is missing from CI's environment — supported at once by the
  message, and by `pyproject.toml`, which does not name it. H2, a platform difference in the
  log parser — killed: the import fails before any parsing.
* **ROOT CAUSE.** `pyulog` was installed by hand in August for the public-log measurement,
  which is outside the gate because it needs the network, and was deliberately left out of the
  dependencies. I then wrote a **gate** test on top of it without declaring it. From inside an
  environment that has the package, nothing can show this: the local check answers "does it
  pass here", and the question was "does it pass from the declarations".
* **FIX.** `pyulog==1.2.4` is a pinned development dependency (`pyproject.toml`, `docs/03` §2).
  The test was not skipped, guarded or moved out of the gate: the raw log is in the repository,
  so the gate should be able to read it everywhere. Six places that said the package was not a
  dependency now say what is true.
* **REGRESSION GUARD.** `tests/test_declared_dependencies.py` reads every import statement in
  `src/`, `analysis/`, `tests/` and the `ns3/` drivers and requires each third-party package to
  be declared. Before the fix it failed naming exactly `pyulog`. Two packages stay outside on
  purpose (`pymavlink`, `pypdf`), each tied to the one file that may import it, and only inside
  a function.
* **VERIFICATION.** A new virtual environment built from `pip install -e '.[dev]'` alone
  (`make all VENV=<that environment>`): `ruff` clean, `mypy` 0 / 57 files, **1955 fast tests
  and all 38 gate tests passed**. Then CI on the fixed commit.

**Found by the verification itself.** Running the gate in that second environment left one
committed figure modified, `results/figures/e4_crossover.png` — same size, **zero pixels
different**. `figures_e4.py` was the only one of seven generators that saved without
`metadata={"Software": None}`, so its file named the matplotlib release that drew it (3.11.0
here, 3.11.2 there), against the reproduction guide's statement that the figures are
byte-stable. Fixed in the generator; the regenerated file is byte-identical under both
releases and pixel-identical to the one it replaces. Guard:
`test_no_figure_embeds_the_plotting_library_version` reads the text chunks of every figure.
The same lesson twice in one hour: an environment-dependent output is invisible until a second
environment runs it.

**And then I broke the build with the fix.** CI on `445731f` failed in the fast suite:
`thesis/e4_crossover.png is stale`. The thesis keeps byte copies of the figures (`make thesis`
makes them, a test compares them); I regenerated the figure and did not refresh its copy.
*Root cause:* before that push I ran the tests I judged to be affected — four files — and not
the suite. The one that failed was not among them, and no amount of care in choosing would
have been as good as running everything. *Fix:* `make thesis`; the copy matches, 100 pages.
*Guard:* the test that caught it already exists; what was missing was running it. The status
board now says: **the whole of `make all`, in the clean environment, before every push** — a
subset is for iterating, never for deciding to push.

**What it teaches.** "Green on my machine" was the claim I had just made about a gate whose
purpose is that anyone can re-derive the results. A check run inside the author's environment
tests the author's environment. The guard reads declarations because that is the only place
this defect is visible.

## Also

* **Bench session** (decision 11-a): `hw/BENCH_SESSION.md`, five steps, with the expected ranges
  written first. Ed25519 batch verification, dry-run on x86: 0.49× per signature at a batch of 64.
* **SSDBFAN** (decision 17-a): read, not cited — it aggregates *data* at cluster heads and gives
  no per-message byte budget.
* **Thesis chapter 2** (decision 18-a): drafted from the sources held; two gaps of reading are
  marked in the chapter instead of being written round.
* **Implicit certificates** (decision 16-a): one sentence; the certificate column is an upper
  bound.

**Durable records:** F58–F62 in `audits/model_provenance.md`; follow-ups F4 and F5 in
`NMAX_DIRECT_EXPECTATIONS.md`; the flight in `PX4_LOGS_EXPECTATIONS.md`; `docs/02` §6g.

---

# 2026-10-07 — the second pass: auditing the revision, not the description of it

*Mohamed: "think deeply of the current state and the remaining open and decision points and give
me options for each, then edit the paper and thesis and re-audit them against the latest reviewer
comment".*

## Method

The review was read again in full, from the PDF. Each request was then looked up **in the built
paper**, not in the response that had been written about it, and not from memory of the edit.
The thesis was read against the same list, because a claim the paper had lost could still be
standing in a chapter.

## What it found

Eleven places in the paper where the response said "done" and the text did not yet do it (F55).
The three that matter:

* **The LoRa paragraph had re-created the mismatch the review listed** — the batch and rate of a
  242 B frame beside the capacity of a simulation run at 222 B.
* **"All lean sizes are emitted frames" was false for one row** of the ladder, in the paper, the
  thesis and the checklist; and every first-format row is a sum of parts too. This is the review's
  root concern in miniature, written by the revision that answered it.
* **The curve the review asked for did not exist.** Drawing it gave the cleanest statement yet of
  what the lean format buys: 24 of the 31.7 B per record between the two designs are *where the
  chain link sits*, and a link in every record costs more at twelve records per frame than one
  link per frame costs at four.

And in the thesis, which the first pass had corrected chapter by chapter but not re-read whole:

* **"No choice of existing cryptography helps"** — the review's own example of an over-claim —
  **was still in four places**: the abstract, research question 5, the positioning section and the
  closing paragraph. The paper had lost it; the thesis had not.
* The abstract still gave the payload as "45–190 B", sizes that include the record's own 32 B
  chain link. Chapters 1, 4 and 7 never said so. A remark now does: 13 B of telemetry, 32 B of
  link; signature and link are 88 % of what is sent, not the 58.7 % that φ gave.
* Ed25519 batch verification was mentioned in the paper and not in the thesis.

## Tried and did NOT work, or was wrong the first time

* **A response row written before measuring.** I wrote "related work is about half the length
  (about 540 words)" from the edit I intended; the count after the edit was 587. Corrected before
  anything was sent. Cutting further would have removed a prior-art citation, so the length stays
  and the response states the real figure.
* **The figure's first labels** overlapped the legend, and matplotlib printed 43.25 as "43.2"
  where the paper prints 43.3. Labels are now rounded half-up, as the generator rounds.
* **The project's red/green pair fails a colour-blindness check** (ΔE 2.5 under deuteranopia).
  The new figure uses a checked three-colour set with different markers. The older two-panel
  figure is not affected in practice — its series are in separate, titled panels.
* **Unpaywall was queried with the author's e-mail address in the URL** while looking for an
  open-access copy. That was a mistake: the address is for identification only. One request, to
  one service; reported to Mohamed.

## The baselines got the same instrument as the design (follow-up F3)

The stream-signing schemes had a saturation bound where the design had a simulated capacity. Five
more cells went through the direct search, their crossings predicted with the airtime line and
committed first (`f72db7f`). **All five held**, 3.5–4.2 % above the line — the offset written
down beforehand for cells at 50 frames per second. A 13 B tag in place of a 64 B signature takes
the neighbourhood from 35 to 42; four records in a frame take it to 124 (F56).

**And the scoring caught a defect in the readers.** Its first table had four rows. The summary
stores the send jitter to six significant figures and three readers looked it up by the exact
period — invisible while every period was a round number of milliseconds, fatal for EMSS's
1000/50.5. Fixed at the root with one function and three regression tests. It was caught only
because the scorer's output was compared with the list of cells it was supposed to contain.

## A source that "needed a browser" did not

Rajasekaran et al. 2022 had been on the checklist since August as a missing FANET comparator.
The publisher's article page refuses scripts; its static file server does not. Read in full,
checked against Crossref (five authors, not the four the checklist listed), cited in one
sentence. It supports the same point as the CLAS table: its communication cost for n
authentications is n times the cost of one (F57).

## The pattern

*A response to a review is one more document that can drift from the text it describes.* The
project already had the rule at two levels — check the figure, not the quotation; build the
object, not the sum. This is the third: **audit the deliverable, not the description of it.**

**Durable records:** F55–F57 in `audits/model_provenance.md`; open items G19–G21 in
`OPEN_ITEMS.md`; follow-up F3 in `NMAX_DIRECT_EXPECTATIONS.md`.

---

# 2026-10-06 — an outside reader: the design had never been built

*Mohamed's supervisor reviewed the paper. Mohamed: "understand and analyse it deeply … plan how to
fix these comments", then "re-read and re-audit the comments and don't skip any tiny detail",
then "think deeper while fixing, do the recommended decision, and double-check everything after
editing or running".*

## What the review found that two audits had not

Not a wrong number. **A missing object.** The configuration every result headlined — delta
records, one signature per four — was a *sum*: a record size from one module, a header measured
on frames of a different encoding, a signature length. No frame carrying delta records had ever
been encoded, sent or decoded, and the receiver that would decode one did not exist. Each part was
right, so re-deriving any number reproduced it — which is exactly what the August audits did.

Four errors followed from that one (F45–F48), and a fifth was unrelated (F49, a paper cited for
two months under another paper's authors).

## Method: build it, then recompute everything from the one definition

1. **A second frame format, `wire_v2` ("lean")**, with a sender and a receiver
   (`placement/session_v2.py`): integer keys, one chain link per frame, a keyframe then deltas.
   The first format is untouched and its artifacts are bit-identical (D6).
2. **One definition of a frame** (`models/frame.py`), whose arithmetic a test holds equal to the
   frames the code emits. Bytes, loss and exclusion are all computed from it.
3. **Nine experiments on that object** (E9–E17, `make exp-frames`), all in the frozen gate.
4. **No typed results.** `analysis/paper_numbers.py` writes every number the paper and the
   corrected thesis chapters print, from the artifacts, and refuses to run if an artifact stops
   supporting a sentence ("eight of twelve", "does not meet the target").
5. **The paper was rewritten** around the frame, not patched. Retraction history moved to the
   methods paper and thesis ch. 11 (decision R12); the low-rate section became the exclusion
   matrix and one paragraph, the rest moving to thesis ch. 10 (R11).

## What it cost

* **The design misses its own target as published.** One keyframe per four frames at p = 0.05
  verifies 0.881 of records, not 0.95 (T3′). Fixed by a keyframe in every frame: +3 B per record
  in the first format.
* **"Three of seven" excluded data rates is withdrawn** — and so is F44, the August finding that
  produced it. With the chain link and a record that decodes alone charged, over the twelve rates
  the standard defines, **eight** cannot carry one frame.
* **The LoRa batch was sized with a record measured at the wrong time scale** (50 ms spacing used
  at 5.5 s): five records per frame in the first format, not seven.
* **Every 802.11 capacity changed**, because the review asked for confidence intervals and
  producing them meant simulating each configuration (below).

## The capacity search — a prediction that failed, and what chasing it found

Pre-registered data-free (`6f82599`): direct simulation would agree with the single load ceiling
U = 2.435 within ±10 %. **It did not** (−23 % for the lean design, +8 % for the long-frame cell).
The ceiling was measured at one N with one frame and is not invariant (F50).

The per-run spread then looked wrong: at node counts well under the crossing, a few runs in
thirty fell below 0.95. Per-node output showed why — in the worst run four nodes delivered
nothing and 22 lost nothing. Strictly periodic senders keep their phases; the simulator raises
carrier sense only after a 4 µs preamble-detection period; a pair inside that window collides
every period (F51).

**Tried, each registered before it was run:**

| follow-up | prediction | outcome |
|---|---|---|
| F1 | the source moves the mean by under 0.005 | **held** — and later data put the difference at +0.003, of one sign in all six cells; see below |
| F1 | 1 ms of send jitter halves the per-run spread | **failed** |
| F1b | a ±5000 ppm rate offset brings the spread under 0.004 | **failed** |
| F1b | the offset source and the redraw-every-period source agree in the mean | **held** |

By the rule F1b registered, every reported capacity uses a send time redrawn within each period.

**A wrong explanation, written down and committed before it was checked.** When all six cells
had been run under both sources, every crossing was higher with redrawn phases. I explained the
common sign away: seed *s*, I wrote, draws the same start offsets in every cell, so the thirty
strictly periodic runs are one sample six times over. That came from reading the scenario. The
runs file was on disk; one correlation would have tested it. It was false — per-seed delivery is
uncorrelated between node counts, because ns-3 assigns random streams in creation order — and it
went into the pre-registration document, a commit message (`fad28e0`), the findings register and
the thesis within ten minutes. The correct reading is duller: fourteen nearly independent
differences averaging +0.003 ± 0.0014. Weak evidence of something real, with no mechanism.
**The lesson is the project's own, again: an explanation is a claim, and it gets checked like
one.**

**The one prediction that held.** Looking at the six crossings suggested a line in airtime,
0.05 = N·f·(a·T + c). It was found by looking, so it was tested as a hypothesis: seven
configurations it had not seen, its value for each written down with a ±6 % tolerance, committed,
then simulated (1470 runs). All seven fell within 3.4 %; the old ceiling misses them by up to
15 %. It replaces the ceiling as the closed form the paper states — with a domain, and with the
residual pattern (ordered by frame rate) written beside it (F54).

## Tried and did NOT work, or was wrong the first time

* **The driver printed the wrong estimate** — the median of the bootstrap replicates instead of
  the sample's own crossing. They differed in one cell (31 against 29). Caught before a number
  was quoted.
* **Three sentences in my own outcome text were wrong against the raw data** ("at least three of
  30" was two to five; "three of 60" was five; "−11 %" was −10.5 %). Found by re-reading each
  claim against the CSV, not by a test.
* **The keyframe-size prediction for real flight logs missed** by 0.02 B (F52). Recorded as a miss.
* **PX4 logs carry position at 5 Hz, not 50.** The prediction had to be amended to 0.2 s spacing
  — done, and committed, before any size was computed. The 20 ms delta stays untested.
* **Two approved items were found undelivered on a second pass** over the decision list: the
  analytic table of classical stream-signing schemes, and loss that grows with frame length.
  Both are now in (E17; the `ber` rows of E10). The second cost the design something: at equal
  bit error rate its longer frame is lost more often and V = 0.943 at the 5 % point.
* **A citation check found the methods paper misquoting a source that was never held** —
  survey years wrong, a figure attributed to the wrong paper, another unsupported. Corrected to
  what the held follow-up reports. This is the F49 class again, in the document written to
  describe it.
* **The first rewrite of the paper departed from the approved plan twice, silently.** It carried a
  new, design-first title, and it put the exclusion after the 802.11 results. The plan Mohamed
  approved said to drop one phrase from the title and to put the exclusion *first*. Found by
  re-reading the plan row by row against the paper, not by any test; both undone, and a test now
  holds the order. The same pass found the abstract did not state the condition under which the
  exclusion holds, the paper never said what a receiver does after a lost frame, and the
  receiver-CPU paragraph lacked the batch-verification sentence the plan promised.
* **Four hours lost to a wait that could not end.** The loop waiting for the held-out campaign
  grepped the process list for a string its own command line contained. The campaign finished at
  05:31; the loop was still "waiting" at 09:20.
* **`thirteen hundred tests`**: I "corrected" this to eleven hundred from a stale copy of the
  status board, checked the repository's own, and reverted. The copy of `CLAUDE.md` outside the
  repository is older than the one inside it.

## Before publication: eleven PDFs taken out of the branch (2026-10-07)

Asked before the first push, Mohamed chose not to publish the new PDFs. The unpublished commits
from the one that added them were rewritten with `git filter-branch`: the eleven files removed,
nothing else changed, dates kept. Because documents and commit messages cite commit hashes, the
same pass rewrote each cited hash to its new value as it went (filter-branch's `map`), so no
reference dangles. The four pre-registration commits that precede the PDFs kept their hashes.
Checked afterwards: no stripped file reachable from the branch; the old and new tips differ only
by those files and eight lines of hash references; committer dates identical.

What "held and read" means changed with it. It used to be checkable by cloning. Now a manifest
gives each withheld file's SHA-256 and where to obtain it, and the tests check the hash wherever
the file is present.

## The pattern

The August chapter ended: *a register that stores facts separately does not compose them; only
re-derivation does.* That was not enough — these errors were re-derived, repeatedly, and
reproduced, because each part was right. **What composes facts is building the thing they
describe and making it run.** A design that exists only as a sum has no receiver to refuse a
frame it cannot decode.

**Durable records:** findings F45–F54 in `audits/model_provenance.md`; pre-registrations
`NMAX_DIRECT_EXPECTATIONS.md`, `PX4_LOGS_EXPECTATIONS.md`; decisions R1–R16 in `DECISIONS.md`;
what is still open in `OPEN_ITEMS.md` §G.

---

# 2026-08-28 — the math audit: nothing was wrong, and the headline still moved

*Mohamed: "analyze then audit deeply each scientific claim, number, result, implementation,
literature comparison, value, methods and placement", then "audit all the math deeply and compare
it against the simulation", then "fix them with the correct simulation and verify with the correct
math".*

## Method, because it is the point

Re-derive each quantity from its equations, then check it against a simulation written for the
purpose — never re-read the project's own conclusion about it. That distinction is what made the
session productive: **every published number reproduced**, so nothing was found by recomputing
arithmetic. What was found was found by asking *what does this constant actually mean*.

## What it cost

**The headline.** "Four of seven EU868 rates excluded" is now **three** (F44). The frame header is
29 B of CBOR text key names; as integers they cost 7 B, so H_f halves to 22 B, DR3's budget goes
7 B → 29 B, and DR3 becomes feasible. `docs/01 §2a` had always said the header was untuned and
`docs/02` T6 had always depended on it. **Nobody composed the two facts.**

⚠️ Mohamed authorised the investigation *knowing* it might do this. It did, and the honest version
is stronger: the boundary is now constructive — it names what would have to change — and the half
that survives (DR0–DR2, where a 64 B signature will not fit a 51 B payload at a zero-byte header)
was always the durable half.

## The pattern, and why 30 seeds could not have caught any of it

Every finding is **class C2 — an unverified constant on the measurement path**. The 30-seed
discipline installed after F30 protects against C1, the failure that had already happened. It gives
no protection at all against a constant that is precisely reproducible and means something other
than its label:

* `D(b)` **names** the oldest record's age and **computes** the batch window. Simulation confirms
  both forms exactly. `b/Λ` survives as the worst case (it is `(b−1)/Λ` plus one sampling quantum)
  — but the "knife-edge" argument in §7a was an artifact of the convention, not a fact about the
  design space.
* `H_f` is a **range**, 38–44 B, and 44 is the end most favourable to the exclusion.
* `s` depends on how long the generator runs; two committed artifacts disagree by 3.7 B and both
  are right for their own protocol; the quoted CI is ~150× narrower than the systematic term.
* The pre-registered ≥40 % criterion reduces to **1 − 1/b** — met by any b ≥ 2. The *ordering* is
  genuine and verifiable in git; the *risk* was not.

## What was tried and did NOT find anything

Recorded because a clean result is only useful if you can see what was tested. Ma & Chen's closed
form against `sim.dcf_ladder` — an independent slot-exact Monte Carlo written *before* the paper
was found — agrees to **≤0.08 %** at N=5–50, and to ≤0.51 % against NS-3. Disabling the CFP head
start collapses the simulator onto the discarded naive reduction with a **16.9× gap at N=50**,
reproducing F9's mechanism attribution exactly. Bianchi's unicast band re-measured at
−0.40…+1.29 %, matching the status board. Fixed-point residuals ≤7×10⁻¹³. The `N_max` first-failure
search checked exhaustively against a full scan over 7 configurations × 4 ceilings: identical
everywhere.

⚠️ One clean result is clean **by accident**: Ma & Chen's S(n) is non-monotone in N — all three
implementations agree, so it is real physics of the CFP series — and the search is safe only
because U(n)'s explicit factor n outruns the recovery. Nothing had tested that. Now guarded.

## M4, and a flaw in my own pre-registration

The U ceiling was measured at a second frame size (174 B, the A+CBOR baseline frame): crossing
**2.367** against 288 B's **2.435**, a **0.45 σ** difference. Indistinguishable across a 1.66×
change, so the universal ceiling is justified and no published number moves.

⚠️ But the pre-registration also predicted a *direction* — that the crossing would drift higher —
with a mechanism. It drifted lower, and the experiment has **no power to resolve the sign**. Had
the noise fallen the other way I would have recorded a confirmation I had not earned. Kept visible:
**a directional prediction needs a power estimate or must be stated as a band.** The load-bearing
prediction did carry one (±15 %) and is the only reason the run answers its question.

## The lesson worth carrying

Three times now a claim has survived because two facts were each recorded and never put side by
side — F18 (quoting the PDF instead of the figure), docs/02 §9c (asserting `N_max = 3` one line
above a table of 3-seed data saying otherwise), and now F44. **A register that stores facts
separately does not compose them. Only re-derivation does.**

# 2026-08-05 … 08-08 — ⚠️ BACKFILL, written 2026-08-28

> ⚠️ **This entry is retrospective and says so.** The logbook's whole value is that it is
> contemporaneous, and between 2026-07-30 and 2026-08-28 it was not written at all — a three-week
> hole covering the project's most productive stretch. Reconstructed from
> `docs/audits/model_provenance.md` (F35–F42), `docs/audits/scientific_implementation_audit.md`
> and the git history, all of which *were* written at the time. **Treat those as the record and
> this as an index to them.** Method and trial that were never written down are simply lost;
> nothing here is reconstructed from memory.

## What happened, in order

**2026-08-05 — hardware, and mobility answered.** The 802.11 arm stopped being simulation-only
(**F35**): two Raspberry Pis, ad-hoc IBSS at 5 GHz, broadcast link loss **p = 2.3 × 10⁻⁴** and
airtime **1.995 ms/frame against 1.99 predicted**. ⚠️ A first 2.4 GHz sweep gave a tidy 97.45 % that
was **saturation at the 802.11b 1 Mb/s broadcast basic rate**, not channel loss — caught by a
pre-stated prediction plus a load sweep, and kept labelled rather than deleted. Mobility (**F36**,
**F37**) came back **null**: 30 seeds of Gauss-Markov 5/20 m/s and RWP 20 m/s all within 0.06 σ of
static. ⚠️ The confound that nearly produced a false 5-point penalty was ns-3 assigning RNG streams
by object-creation order, so installing a mobility model shifted every sender's stream.

**2026-08-05/06 — the scientific-implementation audit.** The question was narrower and harder than
formula conformance: *does each number measure what it is claimed to measure?* It produced the
five-class defect taxonomy (C1–C5) the project now checks against, and **S3**: `N_max` applied
V ≥ 0.95 to a **mean across seeds**, while nine of thirty runs at the certified N=3 fail the very
criterion. **S3b** found the same defect in the 802.11 arm's U crossing. ⚠️ **S7** — `make
sim-ns3-delay` did not reproduce its own artifact. **O5** — `channel_utilisation` returned 0.0 at
N=1, **and a unit test asserted the defect**.

**2026-08-06 — the purge, the ablation, and a withdrawal.** **F38** re-ran the last six 3-seed
artifacts at 30 seeds; A2's capture table was corrected. **F39**'s factorial ablation **narrowed our
own claim**: placement×batching couple exactly by `g_a(1−1/b)`, encoding is perfectly separable, and
the apparent encoding coupling was a **ratio-scale artifact**. **F40** withdrew a pre-registration
claim rather than reconstruct it — writing the expectations file after the results were known would
have manufactured evidence.

**2026-08-07 — the framing audit, and the reframe.** The first pass to question the premise rather
than the numbers. The paper disagreed with itself about its own best contribution (**I1**); the
conclusion used the phrasing the project forbids (**I2**); the abstract was **693 words** and
defensive (**I3**) — and ⚠️ the rewrite that fixed it **deleted an honesty disclosure**, caught only
by checking. Mohamed reframed the paper from co-design optimization to **feasibility boundary**,
because an impossibility cannot drift and four performance numbers here had. **F41**: reading the
one unread source produced a finding, not a citation. **F42**: Direction C's phenomenon has **prior
art**, and its "9 of 9" was inflated — only 4 papers qualify.

**2026-08-08 — a claim withdrawn, and the submission package.** The Direction C literature claim was
**retracted**: the pre-registered threshold was 25 %, the estimate walked to 21.7 % [7.5, 43.7], and
**the interval contains the threshold**, so the test cannot answer its own question. ⚠️ Two
temptations recorded because both were real — the point estimate sits on the favourable side, and
the non-arXiv subset reads 28.6 %. Then the venue-agnostic submission package.

## The lesson this hole itself teaches

The logbook is the one document with no automated guard, because "was method recorded?" is not
checkable by a test. Every other staleness class in this project has been closed by a gate; this
one was closed by nobody, and three weeks vanished. ⚠️ **A discipline that depends on remembering
to write is the one that fails first when the work gets interesting.**

# 2026-07-30 (cont.) — the audit session: four wrong numbers, two retractions, one external baseline

The longest correction run in the project. Everything below was found by attacking our own work.

## What moved

**Four headline numbers were wrong, and every one was sampling — not modelling.** LoRa `N_max`
5→3; the delay crossing U 2.797→2.435; a broadcast band endpoint −1.44→−0.51 %; capacity at V≥0.95
233/116→213/100. The models were right the whole time. Drivers now default to 30 seeds and emit
min/max/σ so the next instance is visible in the artifact.

**Two of my own claims were retracted.** F18 (I said we were the *more optimistic* model vs Haxhibeqiri et al. —
I had quoted their pure-ALOHA figure as their LoRa one) and the "no capture" correction, where I had
attributed our low-N margin to capture that our interference matrix does not implement.

**The external baseline finally exists** (F34), and the interesting part is that it is not a score:
CLAS overheads are linear in message count because aggregation compresses verification, not
airtime. Different axis, not a competitor.

**The hardware stage was audited and largely vindicated.** I wrongly reported the Pi-B sync wire as
undocumented — `hw/RIG.md:40-42` states it explicitly, and my three failed reduction attempts simply
re-derived the design note's own rationale ("no wall-clock alignment"). Two real defects were fixed:
Pi-B's venv lacked `gpiod`, and the capture recorded no per-sample host time.

## What was decided and deferred

Mobility (separate new scenario files, literature survey first) and Direction C — the LoRaWAN
frozen-phase artifact, a possible second short paper. Both have written plans; neither is started.

## The lesson worth carrying

Three times this session a number changed after re-sampling, and once a claim inverted after reading
which *figure* a quotation came from. Quoting the PDF is not enough — quote the figure. And a mean
of a few samples near a threshold is where sampling error turns into a wrong categorical answer.

# 2026-07-30 — Literature sweep, licensing, and a type gate that found real defects

Pre-commit hardening. Nothing was committed on this day either; the working tree is still
uncommitted pending Mohamed's green light.

## 1. Licensing settled (Mohamed's decision)

**All rights reserved.** `LICENSE` rewritten from a permissive placeholder to an explicit
all-rights-reserved grant, © 2026 Mohamed A. Farouk, with a third-party section recording that the
vendored NS-3 and `signetlabdei/lorawan` remain GPLv2 and are **not redistributed** by this repo
(they are fetched by the setup scripts and git-ignored). `CITATION.cff` updated to point at it.

*Why it needed saying:* a private thesis repo with an unclear licence is a problem the moment it is
shared with an examiner or a collaborator, and the GPLv2 dependencies make "all rights reserved"
alone an incomplete statement.

## 2. Deep literature sweep — the part Mohamed asked to be done "like we did" for F9

Four questions were put to the literature, and each got a different answer:

**(a) Does T2a have prior art?** Yes, and it is not close. Batching amortizing per-transmission
overhead with diminishing returns, and the resulting latency trade-off, are thoroughly established
(packet aggregation, the alpha-beta cost model). **T2a is analysis, not a novel theorem** — the same
disposition as T6 (F16). It remains a correct and useful statement of *which ceiling binds*, and it
is presented that way. `OPEN_ITEMS` A6 **closed**.

**(b) Is there a true external baseline?** The nearest comparators are **certificateless aggregate
signature (CLAS) schemes for VANET** — they aggregate n signatures for vehicular safety beacons,
which is the same problem shape. But the contribution axis differs: they build *new cryptographic
constructions*; we ask which combination of *existing, standardised* primitives and system
parameters is feasible on a given link. That contrast is now the closing sentence of §Related Work.

**(c) Is TBRD a baseline?** **No — and Mohamed was right to ask.** TESLA is symmetric with delayed
key disclosure, so it provides **no non-repudiation**, which a provenance ledger requires. The two
are not substitutes and a byte-for-byte comparison would mislead. **The TBRD subsection was moved
out of §Results into §Related Work (f)**, keeping the comparison table but reframing it as a
design-space contrast — both buy authentication bytes with latency, but spend it at opposite ends of
the link. `OPEN_ITEMS` A7 reframed from "missing baseline" to an accepted, argued limitation.

**(d) Does the LoRa capacity result survive contact with the literature?** This one nearly went
wrong. See §3.

## 3. `N_max = 5` checked against published measurements — and a secondary source caught lying

**The trap.** A search summary attributed *"32 % loss at 1000 nodes"* to Haxhibeqiri et al. 2017. Reading
the PDF: **"For 1000 nodes per gateway, around 90 % of packets collide."** Using the snippet would
have manufactured a disagreement with our own result that does not exist. **This is the third time
the rule has paid: quote the PDF, never the summary** (cf. F9, F16).

**The reconciliation, computed with our own `frame_time_on_air_s`.** Their 1000 nodes at 20 B every
180 s = 0.040 % channel occupancy each; ours at 218 B every 36.4 s = 1.000 % — **25× per node**. So
their 1000-node point is ≈40 AUTHBC-equivalent nodes, where they report ~90 % collisions and we
measure 59–75 %. **We are the more optimistic of the two**, which is the useful direction: `N_max=5`
is not a simulator artifact.

**Second check** against pure ALOHA `e^(−2G)`: we sit *above* it at low load (capture) and *below*
it at high load (finite gateway demodulation paths) — both physically expected. A model that matched
pure ALOHA exactly would have meant the simulator was ignoring LoRa physics.

**What it cost us:** a limitation we had not stated. Because the data rate is a design variable,
each run fixes one DR and therefore forfeits SF quasi-orthogonality. `N_max = 5` is a
**within-one-SF bound at maximum legal rate, not a LoRaWAN network capacity.** Now in the paper, in
`OPEN_ITEMS` E8, and in F18.

## 4. `docs/literature/` built out

Mohamed asked that every source found be kept for reuse. The directory now holds **8 PDFs** plus
`README.md`, a register that states for each source **what role it plays** — `USED`, `VALIDATES`,
`PRIOR ART`, `POSITIONING` — because a citation with no stated role is one nobody will check. Two
sources could not be redistributed automatically (Gündoğan et al. is ACM-DL only; the DOI is
recorded instead). Existing PDFs were renamed to a sortable `author-year-topic` convention and the
WSL `Zone.Identifier` turds removed.

## 5. `mypy` added — expected to find nothing, found three real defects

**Stated expectation before running: 0 substantive findings, some annotation noise.** Wrong. 18
errors, of which three were genuine (**F17**):

1. **An LSP violation across the entire `Framer` hierarchy** — subclasses had silently diverging
   `pack`/`unpack` signatures, so polymorphic use could `TypeError`. The tests never caught it
   because every call site instantiates a concrete placement. The root cause turned out to be a
   *modelling* fact worth documenting: placement C is genuinely different (it aggregates other
   senders' signatures, and carries its own public keys), and the hierarchy had encoded that
   asymmetry by diverging instead of stating it.
2. **`aggregate`/`aggregate_verify` called through `SignatureScheme`**, which does not declare them
   — the docstring was ahead of the types. Now an `AggregateScheme` protocol.
3. **Three dead `# type: ignore`s**, found only because `warn_unused_ignores` was switched on.

**Every one fixed at the design level; none suppressed.** `make typecheck` is now in `make all` and
pre-commit. *Lesson worth keeping: 1077 tests are why the numbers are trustworthy, but tests
exercise the paths that get called, and this defect lived in the path nobody calls.*

## 6. Mohamed's three corrections, and what each cost

**(a) "Haxhibeqiri et al. said 90 % is pure ALOHA and 32 % is LoRaWAN."** Correct. I had quoted their Fig. 14
(pure ALOHA) as their LoRa result — after "correcting" a search snippet that had it right. F18
retracted, F19 written, and the wrong wording chased out of four other files with a grep on the
*wording*, not the name (the F9 rule).

**(b) "What is our actual model — pure ALOHA or LoRaWAN?"** Neither label was in our docs, which is
itself the finding. Reading `lorawan-mac-helper.cc`: `LorawanMacHelper::ALOHA` provisions **1 channel
and 1 demodulation path**; `EU` provisions **3 and 8**. We simulate the **LoRaWAN PHY on the harshest
MAC preset**. `N_max = 5` is a worst case, relabelled everywhere. A `--gwRegion` flag now exists to
bracket it (E9, needs an NS-3 rebuild, not yet run).

**(c) "Why didn't we implement their model and run it with our optimizer?"** No good reason — I read
the paper after the result existed and treated it as a yardstick rather than a model. It is stated in
closed form. Now implemented (`lora.haxhibeqiri2017_loss_pct`), validated against their own four prose
figures, and run at our operating point: **their N_max = 4, ours = 5.** That closed A7 for the LoRa
arm and is a far stronger statement than the one F18 claimed. Implementing it also surfaced two
defects in *their* published fit — a 1.78 % intercept at N=0 and a non-monotone stretch at
x ≈ 723–923 — both asserted in tests so nobody later mistakes them for our bugs.

**(d) B3 resolved:** report the region, adopt the compliant point. Primary is now **50 Hz / 100 ms**
(PX4 `MAVLINK_MODE_ONBOARD`, TS 22.125 compliant). Bytes identical (b ≤ Λ·D_max ⇒ b=4 either way);
compliance costs ~2× swarm. **New finding: the region has a floor** — b≥4 under 100 ms needs
Λ ≥ 40 Hz, below which the saving collapses to 12.2 %.

**(e) Abstract corrected.** It claimed "≈3×, a ratio that holds" across thresholds; measured, the
four combinations give **1.94× / 2.24× / 3.22× / 3.31×**. Now stated as a range.
> ⚠️ **Superseded 2026-08-07.** Two of those four were themselves stale: recomputed from
> `capacity_envelope.csv` the set is **1.94× / 3.23× / 3.22× / 2.42×**, so the range is
> **1.9–3.2×**, not 1.9–3.3×. The status board carried the wrong pair for weeks while a later
> line in the same file carried the right one — CLAUDE.md contradicted itself. Guarded now by
> `TestAbstractRatioRange`. Kept above as written, because the entry records what was believed. It also said
compliance costs "a factor of two" — true at V≥0.95 (2.01×), but 2.94× at saturation. Both fixed.

---

# 2026-07-29 — Audit, hardware, NS-3 migration, paper restructure

The longest working day in the project. Ordered by when each thing was done.

## 1. Pre-P8 full audit (morning)

**Method.** Systematic scan rather than recall: inventory every doc and artifact, grep for
unverified markers, cross-check every documented number against the frozen CSVs, then adversarial
review ("what would an examiner attack?").

**What it found — the big one, [F13](audits/model_provenance.md).** The headline auth-byte cut is
**algebraically `1 − 1/b`**. Both baseline and optimized carry the same `H_f + g_a`; one divides by
1, the other by b, so every symbol cancels. Verified by substitution over H_f ∈ {20,40,80,200} ×
g_a ∈ {48,64,96} — **all twelve give 75.0000 %** — and cross-checked against frozen E2 by an
independent route (`bytes_per_rec − s`): auth overhead is identical to three decimals across all
four encodings. **The encoding and scheme axes contribute nothing to that number**, and b=4 is
itself ⌊Λ·D_max⌋ minus an airtime correction, i.e. fixed by two inputs.

*Consequence:* the four-axis framing was retired. Headline became **total bytes −58.68 %** reported
as a decomposition, with the **feasibility envelope** as the load-bearing claim.

**Documentation inconsistencies found and fixed** (each was a real contradiction, not a typo):

| what | reality |
|---|---|
| narrative's E5 table said ECDSA / b=28 / 3.71 B | F10 updated the prose beneath it but not the table |
| docs/01 said BLS = 48 B in three places | code and DECISIONS say 96 B |
| docs/01 listed `T_fx ≈ 123 µs` | D9 deleted it; a test asserts it is absent |
| paper §Results said "nominal power" | paper §Limitations, same document, said "measured" |
| charter said "no LoRa in this arm" | contradicted Mohamed's decision |
| charter said "4× Raspberry Pi 4" | real inventory is 2× (hw/SETUP.md already knew) |
| docs/04 named only E1–E5 | three runnable experiments had no entry |
| `H_f = 40 B` | a bare table default feeding every formula, never derived |

**Also found:** `lora_eu868.csv`, `lora_codesign.csv`, `capacity_envelope.csv` were **outside the
frozen gate** — the F1-class hole the gate exists to close, and one I had created myself by adding
experiments without extending it.

## 2. Closing the audit's open items

### B1 — H_f measured, not assumed
**Method.** Encode real frames with `placement/wire.py`, subtract record and auth bytes.
**Result: 44 B**, not 40. Placement-dependent in reality (A 45→51 with b, D 81); the flat 44 B
understates A by 1 B and D by 37 B, **both conservative**. Predicted the full ripple *before*
re-running and it matched exactly: headline unmoved (H_f cancels — the first real test of F13),
b_max 31→30, total cut 58.30→58.68 %.

### A4 — autopilot rates, read at source
Opened the actual files rather than trusting the earlier search. PX4 confirmed
(NORMAL 5, OSD/CONFIG 10, **ONBOARD 50** Hz). **ArduPilot corrected**: the default is
*vehicle-specific* — Plane/Rover 1 Hz, Sub 3 Hz, **Copter 0 Hz** (GCS requests on demand) — not the
universal 1 Hz our table claimed, and Copter is exactly the FANET vehicle class.

### The 3GPP anchor (found while doing A4)
**TS 22.125 §5.2.2** specifies *direct UAV-to-UAV local broadcast* — precisely this system.
R-5.2.2-010 ≥10 msg/s · R-5.2.2-011 **≤100 ms** · R-5.2.2-008 payload "50–1500 B, **not including
security-related message component(s)**" — the standard itself separates auth bytes from payload,
which is the φ metric this thesis optimises.

⚠️ **Our D_max = 250 ms exceeds the standard.** Recoverable because only the *product* Λ·D_max
matters: (50 Hz, 100 ms) is compliant, PX4-real, and gives the identical b=4. **Still Mohamed's
decision** (item B3).

### B3 reframed as optimization (Mohamed's instruction)
> *"it's an optimization problem … state everything, choose what to stick with, but state all the
> trade-offs for all decisions."*

That changed the task: Λ and D_max are **decision variables**, not constants to defend. Built
`operating_region.csv` (70 points) with compliance flags. The answer is a **bound, not a choice** —
under full compliance at N=50 the best achievable auth cut is 50 %, not 75 %. Reference point kept
**with its cost stated**. Produced [`TRADEOFFS.md`](TRADEOFFS.md).

### A5, B2, B4
A5: 48 B floor cited to draft-irtf-cfrg-bls-signature-05 — which **corrected us**: BLS12-381 targets
**126**-bit security, not 128. B2: N_local reported as a *curve* (N_max 25/32/103). B4: loss grid
justified by *mechanism* (802.11 broadcast has no ACK, so the receiver sees raw channel error).

## 3. Hardware: D1, D6, D7

**D1 — the model's output had never been measured.** Powers and timings were measured; the composed
µJ/record never was.

**Two defects in my own harness, found by running it:** the prediction included `t_verify` while the
pipeline never verifies (inflating it ~1.9×), and the manifest schema didn't match the reducer.
Both fixed at source.

**Measured (INA219, 5 reps/config):** model under-predicts sender-side CPU energy by **~32 %**.
Root-caused to two equal halves — **D7** (no chain-hash term; SHA-256 measured **2745.5 ns** on ARM,
now charged 2×/record) and **D6** (`p_cpu_w` from *isolated primitives* understates a *composed*
pipeline: 0.634 → **0.749 W**). After both fixes the residual is **+7.5…+14.3 %**, all uncharged
CPython framing, deliberately not charged. **Energy figures are lower bounds by ~10–14 %.**

⚠️ **A claim of mine was retracted here.** I had inferred from x86 timings that the model
"overstates the optimized config's energy advantage by ~4 points". The measurement says the
opposite — 2.035× measured vs 1.985× predicted. **D6's premise was also wrong**: `p_cpu_w` is *not*
configuration-dependent (four configs spread only 3.8 %); the isolated-primitive *methodology* was
the error.

## 4. D3 — the delay validation, and the theorem it killed

**Method.** The saturated scenario cannot measure delay (a backlogged queue diverges by
construction), so a **new non-saturated scenario** was written, timestamping each frame on entering
the MAC queue.

**Result: C1 is closed and the answer is "negligible"** — the omitted DCF access delay is
**+0.033 ms** at the reference point against a 250 ms budget. The structural reason matters more
than the number: **802.11 broadcast has no ARQ and cannot queue**, so overload degrades *delivery*,
never latency (mean delay <2.7 ms across a 60× load range).

### ⚠️ RETRACTION 1 — theorem T7, withdrawn hours after being written
I had promoted a finding to a named theorem: *capacity excludes what frame size permits, at U ≥ 1*.
Its own validation experiment — **already scheduled as D3** — refuted it: NS-3 delivers **98.8 % at
U = 1.00**, and the V=0.95 crossing is at **U ≈ 2.80**. Saturation throughput understates usable
capacity ~2.8×.

**Consequences:** the 3GPP-compliant point *is* feasible, so the 75 % cut **is** achievable at the
standard's deadline; the "50 % compliant ceiling" was an artifact of the wrong threshold; every
N_max computed at U<1 is a **conservative lower bound**. T7 is struck through, not deleted.

**Lesson recorded:** the claim was published into docs *and the paper* before running the experiment
already queued to test it.

## 5. NS-3 3.41 → 3.48 migration (Mohamed's direction)

Motivation: the LoRaWAN module pins ns-3.48 exactly, and the LoRa arm needs a capacity envelope no
analytical model can supply.

**Method — both trees kept.** You cannot show results didn't move by deleting the simulator that
produced them. Built `ns3_paths.py` (the path was hardcoded in **five** drivers, making a two-version
comparison impossible) and `compare_versions.py` with **tolerance stated before looking**.

**Trials and obstacles, in order:**

| what happened | resolution |
|---|---|
| `ns-allinone-3.48` 404s | not released yet; used the plain tarball |
| build kept killing WSL | **7.8 GB RAM, 16 cores → ninja defaults `-j 15`**; NS-3 TUs need 1–2 GB each. OOM killer takes WSL down, which reads as "the build broke". Fixed: `-j 3` under `nohup` |
| ruff reported **1172 errors** | it was linting NS-3's own source; the old tree escaped only by its `ns-allinone-*` name |
| lorawan wouldn't compile | 57 sources use `NS_LOG_*`, none include `ns3/log.h`; our optimized profile breaks the transitive include. Wrote idempotent `patch_lorawan.py` rather than change profile (which would confound version with profile) |
| `WifiPhy::GetAckTxTime()` removed | now `GetEstimatedAckTxTime(txVector)`; OFDM/BPSK yields the same 44 µs, and the scenario now **asserts** that equivalence |

**Gate result — PASSED.** matrix 2.56 % · DCF trace 2.62 % · smoke 2.44 % · delay crossing
**identical (U=2.80)**. Agreement bands re-measured and **both directions reported**: unicast↔Bianchi
+0.6/−2.9 % → **+1.28/−0.49 %** (improved); broadcast↔Ma&Chen ≤0.75 % → **≤2.49 %** (widened).

⚠️ **Sensitivity moved a lot at marginal SNR:** `realistic_500m` **−26.5 %**, `nakagami1` **−18.2 %**,
near-field all <2 %. Coherent with 3.48's `InterferenceHelper`/`WifiPhy` fixes. **Paper limitations
updated**: idealised model is **39 % optimistic at 500 m** (was 15.7 %), Rayleigh fading costs **27
points** (was 9).

### ⚠️ RETRACTION 2 — audit F15, withdrawn the same day
I claimed the "≤0.36 % on every quantity" validation was one comparison restated three times.
**Both arguments were wrong.** (i) `ns3_dcf_residual.csv` holds **both unicast and broadcast rows**
and I aggregated across both; filtering correctly reproduces the audit's table **to the digit**.
(ii) I argued that p_s and throughput ratios tracking to 2×10⁻⁴ proved back-derivation — but they
come from the same trace and S is a monotone function of the success rate, so they **must** track.
I treated an expected correlation as evidence of fabrication.

**What survived:** "≤0.36 % on every quantity" was always slightly optimistic (the idle column
reaches **0.75 %** at N=10, visible in the audit's own table), and on 3.48 the bound is **≤2.49 %**.

**How it was caught:** `test_broadcast_residual.py` expected p_s ≈ 0.214 where my analysis produced
0.506. **The tests refuted me** — after I had already propagated the wrong finding to five
documents.

## 6. D2 — the LoRa arm, closed by simulation

**Debugging trail, recorded because it cost hours:**

1. Wrote a scenario from scratch. Every component reported correct — 10 apps, DR=5, live PHY — and
   **it transmitted nothing**.
2. Concluded the module was broken because the stock example "printed 0 0". **That was my
   misreading**: `tail -5` shows the SF8–SF12 rows, which are zero by construction. The **first**
   row had the real numbers. The module was fine all along.
3. Bisected parameters, regions (EU vs ALOHA), TX power, the network server — none of it.
4. Stopped guessing and **re-derived the scenario from the module's working example**, changing only
   what the study needs. That worked immediately.
5. Then bisected payload: **the module caps DR5 at exactly 222 B** — RP002 **Table 12**
   (repeater-compatible) — while our model uses **Table 13**'s 242 B. An independent implementation
   reads the standard the other way. At DR5 that caps b at 6, not 7.

**A guard earned its place:** the scenario aborts if zero packets were sent, so a broken run cannot
be written out as `delivered_frac = 0` and read as a capacity result.

**Result: N_max = 5** at DR5 (V≥0.95) — a sharp ALOHA cliff (1.000 at N=5 → 0.866 at N=8), because
there is no carrier sense and no backoff to absorb contention. **The two penalties compound:**
121× slower per node **and** 21× smaller per domain = **≈2500× less aggregate capacity** than the
802.11 arm.

## 7. F1 — the paper restructure

Three stale claims fixed en route: T5 still said "largest MTU-feasible batch" (pre-F10), the energy
model had no chain-hash term (D7 never reached the paper), and E4 led with the x86 verify ratio while
κ* beside it was already ARM.

⚠️ **And one repeat offence caught before shipping:** the feasibility paragraph claimed the baselines
are "unrunnable at N=50" — **the exact error retracted with T7**. Rewritten to report both thresholds
and make the ~3× *ratio* the claim, since that survives either reading.

## 8. Consolidation and tidy-up (this entry)

**A pattern worth naming.** The withdrawn-T7 error — treating `U ≥ 1` as infeasible when it is only
"above saturation throughput" — turned up in **four** separate places: the theorem itself, the
paper's feasibility paragraph, docs/02 §7a's trade-off table, and docs/04's E8 row. Each was written
at a different time from the same wrong mental model. Fixing the theorem did not fix the phrase,
because the phrase had already been copied. **When a claim is retracted, grep for its wording, not
just its name.**

**Found: I had committed the entire ns-3.48 source tree — 5,439 files — plus two tarballs (84 MB).**
`.gitignore` covered `ns-3.41` and `ns-allinone-*`; the new tree matched neither. `.git` is now
183 MB. Pattern generalised to `ns3/ns-3.*/` and `ns3/*.tar.bz2`; the tree is untracked (files stay
on disk). **The history still contains it** — see the open question in the handover.

## 9. Code documentation and the reproduction guide (2026-07-30)

**Audit first.** Checked module-docstring coverage across our own code (the vendored NS-3 trees
skew any naive `find`): **112 of 115 Python files** already carried one, all nine packages had a
package-level docstring, and all four C++ scenarios had header comments. The three gaps were empty
`__init__.py` files, now filled — including `experiments/e4/__init__.py`, which explains *why* E4 is
a standalone script rather than a registry runner.

**So the gap was not docstrings — it was the map and the on-ramp.** Written as
[`05_REPRODUCTION_GUIDE.md`](05_REPRODUCTION_GUIDE.md) (slot 05 was free in the numbering):

* **Four paths by cost** — analytical (~10 min, reproduces the headline), 802.11 simulation, LoRa
  simulation, hardware — because most readers need only the first.
* **What every source file does**, package by package, with the non-obvious properties stated
  (delta encoders are stateful; `wire.py` owns the signature boundary; `dcf_ladder` is deliberately
  independent of the model it checks).
* **The artifact dependency graph** — measured vs derived, and which is re-checked by the gate.
* **Verification spot-checks** with expected values, including the one that must *not* move: the
  auth cut stays 75.00 % under any H_f or g_a, because it is 1 − 1/b.
* **Troubleshooting from the traps we actually hit** — the OOM that reads as a broken build, the
  LoRaWAN `log.h` patch, ruff linting the vendored tree, the "prints 0 0" misread, and
  `bench-micro` silently swapping ARM timings for x86 ones.

**Verified rather than assumed.** Every `make` target the guide names was checked to exist — which
caught `exp-operating-region` **missing from the Makefile** (the runner was registered during the B3
work but no target was added). Every file path checked; every quoted number re-derived from the
frozen CSVs; and grepped for machine-specific paths — none, so the guide is genuinely portable.

## 10. Pre-commit review: prior art, external baseline, repo hygiene (2026-07-30)

Mohamed asked what we still lacked scientifically, developmentally and professionally, before
committing. The review found four things worth acting on and two worth flagging.

### The one that mattered — T6 is not novel (F16)
A deep prior-art search, run the way the A4/B3 citation work was run. **Gündoğan et al. (ACM ICN
2021) compute exactly `M − H_f − g_a = s_max`** for 802.15.4/NDN: 55 B of headers leave 73 B, and a
64 B Ed25519 signature reduces application data to 9 B. The post-quantum literature independently
reports NIST signatures as incompatible with 5G SIB1's 372 B limit — our tier 1. And `(1−p)^n`
fragmented delivery is standard 6LoWPAN material, with "sliced signatures" an actively proposed
workaround.

**T6 was demoted from theorem to applied bound**, in docs/02, the paper (now "five theorems… and we
apply a known payload-exclusion bound") and the abstract. What survives is narrow and stated as
such: the *composition* (the sliced-signature escape is foreclosed when ε ≤ p) and the EU868
partition.

**This is the F9 lesson applied in time.** F9 cost a retraction because a claim went out before the
literature was read; here we searched first and downgraded a claim we liked. **T2a has NOT had the
equivalent check** — logged as A6, and no novelty may be implied for it until it does.

### External baseline
Searched for a published comparator and found **TBRD (2025)**, a TESLA-based authenticator for UAS
Remote ID reporting a 50 % overhead reduction versus digital signatures. Added as a structural
comparison, and it turns out to be the *interesting* kind: both approaches buy authentication bytes
with latency, but TESLA delays **verification** while batching delays **transmission**. For a
tamper-evident ledger that difference decides it — a record that cannot yet be verified cannot yet
be committed — and TESLA additionally forfeits non-repudiation. **We claim no superiority**; the
comparison is qualitative, which is logged as A7.

### Repo hygiene
`LICENSE` (MIT, with an explicit note that the vendored ns-3 and LoRaWAN module remain GPLv2) and
`CITATION.cff` were both absent — real gaps for a repo meant to accompany a thesis. Added.
`docs/failures/` documented a per-failure report process that had **never been used** while the
failures went into audits and the LOGBOOK; rather than leave the repo describing a process it does
not follow, it now redirects here. Dead `lane2` worktree and branch removed after confirming they
held no unique commits.

### mypy
Ran it for the first time: 18 errors, of which **two were real annotation errors and are fixed** —
`block_agg._buf` was typed `dict[int, …]` while the code correctly uses a `(src, block_id)` tuple
key (the comment even said so), and a `bytes` value in `json_enc` was never narrowed. The remaining
16 are design smells (LSP violations in the `Framer` hierarchy; BLS-only methods missing from the
`SignatureScheme` protocol), not bugs. Logged as E7 rather than half-fixed before a commit.

---

# Earlier phases (pointers)

P0–P7 are recorded in `audits/p0.md` … `audits/p7.md`, with the cross-cutting findings in
`audits/model_provenance.md`. Highlights worth knowing without reading them:

- **F9** — the broadcast residual. Our in-house reduction τ=2/(W+1) was wrong by 16× at N=50; the
  mechanism is *published* (Ma & Chen's backoff-counter Consecutive Freeze Process). **No novelty is
  claimed**; two earlier explanations ("18× capture", "we discovered the head start") were retracted.
- **F10** — freshness was specified as a hard constraint and had been softened to an annotation, so
  b=31 was reported as optimal while sitting **6.2× over** the latency bound. Headline moved
  96.77 % → 75.00 %.
- **F8** — NS-3 sinks outlived the sources, inflating every goodput ~4.8 %.
- **D9** — airtime is an OFDM-symbol *step* function; `T_fx` deleted, a test asserts its absence.
- **F4** — one 30-seed sizing protocol; single-seed sampling had drifted 4.1 %.
- **F1** — a decision (BLS 96 B) landed but a frozen artifact kept the old value. **This is why the
  staleness gate exists.**
