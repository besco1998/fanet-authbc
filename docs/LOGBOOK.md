# Logbook — what was done, what was tried, what was found, in order

*Purpose: the one place that records **method and trial**, not just outcome. The findings register
(`audits/model_provenance.md`) says what is true; the decision log (`DECISIONS.md`) says what was
chosen; this says **how we got there, including the paths that failed**. A wrong turn that is not
written down gets taken twice.*

**How to use it.** Newest first. Each entry: what we were doing → what we tried → what happened →
where the durable record lives. If you want the conclusion only, follow the pointer.

**Index of every document** → [`docs/README.md`](README.md).

---

# 2026-07-30 (cont.) — the audit session: four wrong numbers, two retractions, one external baseline

The longest correction run in the project. Everything below was found by attacking our own work.

## What moved

**Four headline numbers were wrong, and every one was sampling — not modelling.** LoRa `N_max`
5→3; the delay crossing U 2.797→2.435; a broadcast band endpoint −1.44→−0.51 %; capacity at V≥0.95
233/116→213/100. The models were right the whole time. Drivers now default to 30 seeds and emit
min/max/σ so the next instance is visible in the artifact.

**Two of my own claims were retracted.** F18 (I said we were the *more optimistic* model vs Bor —
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

**The trap.** A search summary attributed *"32 % loss at 1000 nodes"* to Bor et al. 2017. Reading
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

**(a) "Bor said 90 % is pure ALOHA and 32 % is LoRaWAN."** Correct. I had quoted their Fig. 14
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
closed form. Now implemented (`lora.bor2017_loss_pct`), validated against their own four prose
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
