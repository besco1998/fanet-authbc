# Scientific-implementation audit

*Requested by Mohamed 2026-08-05: "fix all things with correct scientifically correct
implementation, then audit the whole project from the scientific implementation point of view."*

**Scope.** Not a code-quality review and not a re-check of the arithmetic — `docs/audits/model_provenance.md`
already carries F1–F37 for formula conformance. This asks a narrower and harder question:

> **Does each number in this project measure the thing it is claimed to measure?**

Every finding below is backed by a command that was run, not by inspection alone. Where a check
*passed*, the evidence is recorded too — a clean result is only useful if you can see what was tested.

---

## 1. Defect taxonomy — the classes this project actually produces

Five distinct ways a plausible number has turned out wrong here. The first two were already known;
**S3 is new in this pass** and is the most consequential.

| class | mechanism | instances |
|---|---|---|
| **C1 — small-sample mean vs a threshold** | too few seeds; the mean lands on the wrong side | four headline numbers (F26, F30); `N_max` 5→3; delay crossing 2.797→2.435 |
| **C2 — an unverified constant on the measurement path** | the rig did not do what the config said | 2.4 GHz broadcast basic rate (F35). ⚠️ σ was 0.196 pp over 8 windows — **repeatability did not protect against it** |
| **C3 — a threshold applied to a mean instead of to the distribution** | the criterion answers a different question from the one asked | **S3 below — `N_max`** |
| **C4 — a configuration change that perturbs the random realisation** | comparison arms differ in bookkeeping, not just physics | RNG stream displacement (F36/F37) |
| **C5 — a claim wider than the experiment supports** | the measurement is sound; the sentence around it is not | 2-node hardware ≠ Ma & Chen validation (F35); F18 retraction |

**More seeds only fixes C1.** C2–C5 are immune to sample size, which is why "we ran 30 seeds" is not
by itself a statement of correctness.

---

## 2. S3 (MAJOR, new) — `N_max` applies its acceptance test to a mean, and V is a reliability target

### The finding

`run_lora_capacity.py` accepted an N when the **mean delivered fraction across seeds** met V ≥ 0.95.
The published `N_max = 3` rests on this row of `lora_capacity.csv`:

```
n=2   delivered=0.97166   seeds_failing_v = 8/30    meets_v=1
n=3   delivered=0.95981   seeds_failing_v = 9/30    meets_v=1
```

**At N = 3, nine of thirty runs fail the very criterion being certified.** V is a *verifiability /
reliability* target. A network that delivers ≥95 % "on average" while 30 % of realisations fall below
it does not meet a 95 % reliability requirement in any operational sense — the mean is answering a
throughput question, not the reliability question the paper asks.

### Re-derived with both criteria and a bootstrap interval

```
N_max (mean V >= 0.95)             = 3
N_max 95 % bootstrap CI            = [2, 3]     <-- KNIFE EDGE, do not quote bare
bootstrap distribution             = {1: 0.013, 2: 0.188, 3: 0.796, 5: 0.003}
N_max (>= 95 % of individual runs) = 1          <-- DISAGREES with the mean criterion
```

Artifact: `results/raw/lora_capacity_ci.csv`.

**Two things follow, and both matter:**

1. **`N_max = 3` was never a point estimate the data supported.** Its 95 % CI spans [2, 3]; 18.8 % of
   bootstrap replicates return 2. It must be quoted as **3 (95 % CI [2, 3])**.
2. ⚠️ **Under a per-realisation reading, the LoRa arm admits ONE node.** The mean and reliability
   criteria differ by 3×.

This is **independent of**, and points the same way as, the already-recorded result that composing
with Zirak's measured link loss leaves V ≥ 0.95 admitting no multi-node network (`CLAUDE.md`). Two
unrelated routes reaching the same conclusion is a strong signal, not a coincidence.

### Fixed

`run_lora_capacity.py` now computes and prints **both** criteria plus the bootstrap CI, emits
`seed_pass_frac` and `meets_v_strict` per row, and records `n_max_ci95` / `n_max_is_knife_edge` /
`n_max_strict_criterion` in the provenance header. ⚠️ **Which criterion the paper quotes is
Mohamed's decision (Law 8)** — both are defensible, they answer different questions, and the honest
move is to report both and say which one the headline uses.

### New machinery, with tests

`authbc.bench.stats.threshold_crossing_ci` — a nonparametric bootstrap for "largest N whose mean
still meets a threshold". A crossing is discrete and non-linear in the sample, so unlike a mean it
does not get an interval for free. `tests/test_threshold_crossing_ci.py` (10 tests) pins the
behaviour, including the knife-edge and single-outlier cases that motivated it.

⚠️ **A criterion I got wrong first, kept visible.** `is_knife_edge` originally asked whether the
point estimate held a *majority* of replicates. That passed a **56/44** split as settled, which is
plainly not settled. The defensible criterion is whether the 95 % CI is degenerate: if it spans more
than one candidate, the data do not distinguish them and a bare number misleads.

---

## 3. S4 (MODERATE, new) — the delay driver reported 30-seed means with no dispersion at all

After F30 the project's standard became "drivers default to 30 seeds and emit min/max/σ".
`run_matrix.py` and `run_lora_capacity.py` were brought up to it; **`run_delay.py` was not.** It
emitted `delivered_frac` as a bare 30-seed mean — and the **U ≈ 2.435 crossing that produces the
swarm-size figures is a threshold applied to exactly that column**, i.e. class C3 again, with the
distribution not even visible to a reader.

**Fixed:** now emits `delivered_min`, `delivered_max`, `delivered_stdev`, `seeds_failing_v` and
`delay_mean_stdev_ms`, and prints the range and failure count per rate. Re-derived as
`results/raw/ns3_delay_ci.csv`.

---

## 4. S5 (checked, CLEAN) — are the project's other comparisons confounded by RNG displacement?

F37 found that installing a mobility model shifts every sender's RNG stream, because ns-3 allocates
stream indices by object-creation order. That defect class threatens **any** comparison whose arms
construct different objects. The published comparisons were therefore tested rather than assumed.

**The invariant used:** `sent` counts *transmissions*. None of these options can physically change
how many packets a device transmits — they act on propagation, gateway configuration, or collision
resolution, all of which affect *reception*. So for a fixed seed, `sent` must be identical.

| axis | published in | `sent` | verdict |
|---|---|---|---|
| `channelModel` ideal vs shadowing | F25 | 323 vs 323 (**and received 249 vs 249**) | **clean** |
| `gwRegion` aloha vs eu | E9 | 323 vs 323 | **clean** |
| `interferenceMatrix` aloha vs goursaud | A2 | 323 vs 323 | **clean** |
| `txJitter` 1.0 vs 0 | E13/F32/F33 | 323 vs 325 | **not comparable this way** — selects a different sender *class* (`JitteredSender` vs the module's `PeriodicSender`), so a different `sent` is expected. Handled distributionally over 30 seeds instead, which is the right treatment |

**So F25, E9 and A2 are not confounded.** The structural reason the mobility case differed:
`GaussMarkovMobilityModel` creates its random variables **at install time, before the senders are
constructed**, whereas the shadowing and gateway models do not.

**Made permanent:** `make verify-rng-isolation` (`ns3/verify_rng_isolation.py`) asserts the invariant
on every axis and fails loudly with the reason if it is ever violated.

---

## 4b. S7 (MAJOR, new) — `make sim-ns3-delay` does not reproduce its own artifact

The committed `results/raw/ns3_delay.csv` sweeps rates **1 2 3 5 7 9 12 15 20 30 40 60**, reaching
U = 6.69. The driver's default `--rates` were **1 2 3 5 7 8 9 10 12**, topping out at **U = 1.34**.

**So the documented entry point produced a different file from the committed artifact — and one
that cannot contain the headline crossing.** The paper quotes the V = 0.95 crossing at **U ≈ 2.44**;
a default run stops at 1.34, well short of it. Anyone reproducing from `docs/05` would get a CSV
that silently omits the region the claim lives in.

⚠️ **Related, and worth stating in the paper:** U ≈ 2.435 is an **interpolation** between two
measured rows — U = 2.2299 (delivered 0.96246) and U = 3.3448 (0.89479). Interpolating between
bracketing measurements is legitimate, unlike extrapolation, but it is not itself a measured point
and should be labelled as interpolated.

**Fixed:** the driver's defaults are now the rates that generated the artifact, with a comment
saying why they must not be narrowed again.

**Re-derived with dispersion** (`results/raw/ns3_delay_ci.csv`). The delay arm turns out to be
well behaved where the LoRa arm was not — through U = 1.338 the spread is tight and at most
**1 of 30** seeds falls below V, so unlike S3 this crossing is not a knife edge in the swept region.

---

## 4c. S3b (MAJOR, new) — the U crossing has the SAME defect as `N_max`, and it moves the headline

The full-range re-derivation (`results/raw/ns3_delay_ci.csv`, 12 rates x 30 seeds) makes the
dispersion visible for the first time:

| fps | U | mean delivered | min | max | seeds failing V |
|---|---|---|---|---|---|
| 12 | 1.338 | 0.98435 | 0.93925 | 0.99925 | **1 / 30** |
| 15 | 1.672 | 0.97814 | 0.94421 | 0.99639 | **1 / 30** |
| **20** | **2.230** | **0.96246** | 0.92842 | 0.99378 | ⚠️ **10 / 30** |
| 30 | 3.345 | 0.89479 | 0.82494 | 0.94367 | 30 / 30 |

**At U = 2.23 the mean (0.9625) clears V ≥ 0.95 while a third of the runs fail it.** This is exactly
S3 in the 802.11 arm: the crossing that yields the headline swarm capacities (**31→100** compliant,
**88→213** relaxed) is a threshold applied to a mean whose distribution straddles it.

* **Mean criterion:** crossing at U ≈ 2.435 (interpolated) — the published value.
* **Per-realisation criterion** (≤5 % of runs may fail): the crossing is bracketed by
  **U ∈ (1.672, 2.230]** — at U = 1.672 only 1/30 fails, at U = 2.230 ten do.

So the strict crossing is at most **~69 %** of the quoted one, and the V ≥ 0.95 capacity figures
would fall by roughly a third.

### ✅ The adopted operating point is NOT affected — and that is the important part

The 3GPP-compliant point sits at **U = 1.39** (B8). At U = 1.338 only **1 of 30** seeds falls below
V, and every rate up to U = 1.672 behaves the same. **The operating point the thesis actually adopts
is comfortably inside the safe region under either criterion.** What moves is the *maximum* capacity
claim, not the configuration being proposed.

The delay arm is also markedly better behaved than the LoRa arm: 0/30 failures up to U = 0.557 and
≤1/30 through U = 1.672, where LoRa was already failing 8/30 at N = 2.

---

## 5. S6 (MINOR) — three raw CSVs carry no provenance header

Law 7 requires raw CSVs to carry config-hash + environment headers. Missing on:

| file | assessment |
|---|---|
| `ns3_smoke.csv` | **real gap.** Generated by `ns3/sim_ns3.sh`, which writes no `#` header |
| `lora_phase_artifact_eu_30seed.csv` | **real gap.** Stores good per-seed rows, no header |
| `ns3_contention.csv` | ⚠️ **correctly headerless — do not "fix" it.** It is *derived* deterministically from `ns3_matrix.csv`, and its frozen test compares `read_text()` **exactly**. Adding an `env_block` header (which contains cpu and platform) would make that test **pass on this machine and fail on any other** — converting a reproducibility guarantee into a machine lock-in. If provenance is wanted here it must be the *source artifact's* hash only, with no machine-specific fields, and the test left comparing full text |

That last row is itself an audit finding: **provenance headers and exact-text reproducibility tests
are in tension**, and the resolution differs for raw vs derived artifacts. The other frozen CSVs are
safe because `_frozen_body()` strips `#` lines before comparing.

---

## 6. Verified good — practices worth not regressing

| practice | evidence |
|---|---|
| **Per-seed raw data retained, not just summaries** | `ns3_matrix.csv` stores 30 rows per (N, mode); `lora_phase_artifact_*.csv` likewise. This is the gold standard — it let the validation bands be re-derived at 30 seeds without re-simulating, and it is what makes any future re-analysis possible |
| **First-failure crossing rule** | A4's fix (`if ok and not failed_yet`) is present in `run_lora_capacity.py` and is now mirrored in `threshold_crossing_ci`, so the bootstrap cannot disagree with the driver |
| **Stated-in-advance predictions** | the practice that caught C2 on the hardware rig, and that the mobile scenario's two property checks now enforce mechanically rather than by discipline |
| **Retractions kept visible** | T7, F15, F18 remain in the register with the reasoning. This is rarer than it should be and is worth preserving |

---

## 7. Open, with precise next actions

| # | item | action |
|---|---|---|
| **O1** | ⚠️ Which `N_max` criterion the paper quotes (mean vs per-realisation) | **Mohamed's decision.** Both are computed and emitted; the paper must state which and why |
| **O2** | `p = 0.05` has no sensitivity analysis | The 802.11 envelope (`N_max` 100/213) is analytic in `p`, so it carries no seed uncertainty — but all of its uncertainty is inherited from `p`. Sweep it (Tier 2 #5). Hardware now bounds the optimistic end at 2.3 × 10⁻⁴ (F35) |
| **O3** | `ns3_smoke.csv`, `lora_phase_artifact_eu_30seed.csv` lack headers | Add `env_block` + `config_hash` to their generators and re-derive. Safe: neither is compared by exact text |
| **O4** | Unicast −1.4…−2.6 % small-frame bias | Still unexplained; anomalous-slot (Tinnirello) remains an untested hypothesis, and is labelled as such |
| **O5** | ✅ **FIXED** — `channel_utilisation` returned exactly 0.0 at N=1 | It conflated *contention* with *utilisation*: a lone sender does not collide but still occupies airtime, and U = 0 declared a single node able to carry unbounded traffic. Ma & Chen already handles n = 1 correctly (1793.72 frames/s at 288 B, matching the closed form `1/(t_broadcast + (W−1)/2·slot)` — an independent cross-check), so the special case was removed. ⚠️ A unit test **asserted the defect** (`"a lone sender never contends"`); it has been corrected with the reasoning kept visible. Latent until S3 began reporting N = 1 |

⚠️ **O5 is the kind of thing this audit exists to catch:** a defect that was harmless yesterday
became relevant the moment another number moved — and it was *protected by a passing test* that had
encoded the wrong behaviour as intended behaviour. A green suite is evidence that the code does what
the tests say, not that the tests say the right thing.

---

## 7b. Second pass (2026-08-06) — Mohamed: "report both, headline the mean" + execute all fixes

### A. The paper contradicted itself, and the V column was never generated

`tab:envelope`'s $V{\geq}0.95$ column was **hand-written in LaTeX**. When F30 corrected the crossing
2.797 → 2.435 the prose was updated to 213/100 but the table kept **233/116**, and two further rows
(A+CBOR@50/100, optimized@20/100) existed in the table with no generator at all.

**Fixed properly rather than patched:** every column is now derived by `_n_max_envelope` at four U
ceilings, and `tests/test_paper_matches_artifacts.py` **parses the LaTeX table and compares it to
the CSV**, so the two cannot diverge again.

**The load-bearing claim survives the criterion change** — which is what had to be checked before
adopting "report both":

| criterion | compliant | relaxed |
|---|---|---|
| U < 1 | 1.94× | 3.22× |
| V ≥ 0.95 (mean) | 3.23× | 2.42× |
| V ≥ 0.95 (per run) | 2.67–3.14× | 2.51–3.02× |

Every ratio lies between **1.94×** and **3.23×**, i.e. the quotable range is **1.9–3.2×**. ⚠️ Two published ratios were also stale (3.31→**3.23**,
2.24→**2.42**), so the four-number list in the status board needed correcting too.

### B. `p` sensitivity (O2) — the constant is not load-bearing, but it sits on a boundary

`analysis/sensitivity_p.py`, 16 points from the hardware measurement (2.3 × 10⁻⁴, F35) to 0.20:

* **The selection never changes.** `delta / ed25519 / B, b = 4, 71.998 B/rec` at **every** feasible
  p. One distinct selection across the whole grid, so the unsourced `p = 0.05` is *not*
  load-bearing.
* ⚠️ **Feasibility collapses at p > ε, identically.** At p = 0.051 *nothing* is feasible. This is an
  identity, not a finding: placement B attains V = 1 − p and D gives (1 − p)ⁿ ≤ 1 − p, so the best
  achievable V is 1 − p and `V ≥ 1 − ε ⟺ p ≤ ε`. With p = ε = 0.05 the adopted point has **zero
  margin in the model** — a property of the *requirement*, not a defect in the design, and the
  hardware measurement puts the real link ~200× inside it.

### C. Provenance (S6) — and two worse things found while fixing it

* `ns3_smoke.csv` had no header because `parse_ns3.py` wrote none. **Fixed at the generator.**
* ⚠️ **`analysis/analyse_phase_artifact.py` read a hardcoded path into an agent session scratchpad**
  (`/tmp/claude-.../c1_raw.csv`). It was unrunnable by anyone else and did not read the committed
  artifact. **Fixed**: defaults to the committed CSV, `--csv` to override. It now reproduces F32's
  2–8× variance inflation (2.91× / 2.82× / 7.88×) from data in the repo.
* ⚠️ **Neither `lora_phase_artifact_*.csv` has a committed generator** — 300 runs that are Direction
  C's entire evidence base cannot be re-derived. Recorded as open; a retrospective header was added
  to the EU file stating config and findings, with the **env block deliberately absent rather than
  guessed**, plus an explicit warning that no generator reproduces it.

### D. The unicast small-frame bias (O4) — hypothesis tested, and it holds

E21 recorded the anomalous-slot effect (Tinnirello, Bianchi & Xiao, TVT 2010) as a *plausible,
untested* cause. Bianchi omits the anomalous slot, so it under-counts the cycle by one idle slot σ
per success and over-predicts by σ/(T_s + σ) — a worst case that should **bound** the bias and,
crucially, **scale as 1/T_s**:

| L | predicted bound | measured deviation |
|---|---|---|
| 72 B | −3.32 % | −2.60 … −1.40 % |
| 288 B | −1.61 % | −1.07 … +0.33 % |
| **1400 B** | **−0.44 %** | **−0.40** … +1.29 % |

Correct sign, bounded at every size, and the predicted 7.5× collapse across a 20× frame-size range
is matched. At 1400 B the bound and the measured floor agree to **0.04 points**. ⚠️ This is a
consistency check against a bounding argument, not a fit of the full Tinnirello model — and
broadcast (which the headline runs on) holds to ±0.21 % at 72 B, so the explanation is asserted for
the unicast arm only. `tests/test_anomalous_slot_bias.py` pins all of it.

---

## 8. Summary — what changed in this pass

| # | severity | finding | state |
|---|---|---|---|
| **S3** | MAJOR | `N_max` applied V to a **mean**, not a distribution: 9/30 seeds fail at the certified N. `N_max = 3` has CI **[2, 3]**; the per-realisation criterion gives **1** | fixed (both criteria + bootstrap CI emitted); ⚠️ **which one the paper quotes is Mohamed's call** |
| **S7** | MAJOR | `make sim-ns3-delay` swept to U = 1.34 while the artifact and the headline crossing need U ≈ 2.44+ | fixed (defaults corrected, re-derived) |
| **S4** | MODERATE | delay driver emitted 30-seed means with **no dispersion**, against the project's own post-F30 standard | fixed |
| **O5** | MODERATE | `channel_utilisation` = 0 at N = 1, pinned by a test asserting the defect | fixed, test corrected |
| **S5** | — | are F25 / E9 / A2 confounded by RNG displacement? | **checked: clean**, and now guarded by `make verify-rng-isolation` |
| **S6** | MINOR | 3 raw CSVs lack provenance headers (one of them correctly so) | recorded with the precise fix |

**New machinery:** `threshold_crossing_ci` + 13 tests, `verify_rng_isolation.py`, and two make
targets. The through-line is that each replaces a discipline with a mechanical check — the project
has repeatedly found that "remember to look at the distribution" is not a control.

---

## 9. Idea and framing audit (2026-08-07) — the first pass that questioned the *premise*

*Requested: "audit the project, the idea and the process." Every earlier pass asked whether numbers
measure what they claim. This one asks whether the claims are worth making, and whether the paper
states them well. It found four framing defects and verified two integrity claims — one of which
survived and one of which did not.*

### I1 (MAJOR) — the paper did not agree with itself about its own best contribution

| where | valuation of the payload-exclusion result |
|---|---|
| Abstract | listed among "**applications of established results rather than new ones**" |
| Conclusion | "an exclusion result that we regard as **the more durable contribution**" |

Both readings are defensible — *durable* is not *novel* — but a paper that files its strongest
result under "not new" in the abstract and "most durable" in the conclusion has not decided what it
is arguing. **Resolved by promoting it to the first result in the abstract and the first
contribution bullet**, stated precisely: the bound is Gündoğan's, the *instantiation on EU868 with a
measured H_f*, and the fragmentation corollary, are ours.

⚠️ It also deserves the promotion on merit: it is arithmetic. 64 B does not fit in 51 B, so DR0--2
are excluded whatever the encoding, batch or scheme. **Unlike every performance number in this
project — four of which this audit had to move — an impossibility result cannot drift.**

### I2 (MAJOR) — the conclusion violated a rule the same paper states

* §Results: *"a single `≈3×` would be true of two of those four numbers and misleading about the
  other two."*
* §Conclusion: *"a `≈3×` ratio that is **stable under either feasibility threshold**."*

The artifact says **3.22× at saturation and 2.42× at the verifiability boundary**. The conclusion
was both wrong and self-contradicting, and it is the phrasing `CLAUDE.md` explicitly forbids.
**Fourth internal contradiction found by this audit, and the same mechanism every time: prose that
no test compares against anything.**

### I3 (MAJOR) — the abstract was 693 words and structurally defensive

IEEE Access expects ~250. More important than length was the *shape*: it spent more words
qualifying the result than stating it — three separate self-criticisms before the reader reached
the feasibility envelope, which is the contribution that actually requires the co-design.

⚠️ **Honesty and impact were not in tension here; the abstract was failing at both.** Burying a
sound result under hedges tells a reader "this work is weak", which is itself inaccurate. Rewritten
to **267 words**, ordered by durability (exclusion → feasibility → bytes), with the limitations
stated once and precisely instead of woven through every sentence.

⚠️ **The rewrite caused a regression, which is worth recording.** The disclosure that the
pre-registered criterion's verifiability half was *satisfied by construction* existed **only in the
abstract**. Shortening deleted it. It is now restored to §Results, expanded with the stronger
statement the `p` sweep later established (feasibility requires `p ≤ ε` identically). **Improving
impact silently removed a self-criticism — exactly the failure this audit exists to catch, produced
by the audit itself.**

### I4 — no contributions list

A reader could not extract what was new in ten seconds. Four bullets added, each naming what is
*not* ours alongside what is.

### P1 (CHECKED — the claim is TRUE and verifiable)

The abstract calls the ≥40 % criterion **pre-registered**. Given S9 — where an identical claim was
withdrawn because its evidence had vanished — this had to be checked rather than trusted.

```
docs/04_EVALUATION_PLAN.md   3354ec1  2026-07-03  "Success criterion for the thesis headline:
                                                   optimized config reduces on-air auth bytes >=40%
                                                   vs A+CBOR at V >= 0.95 under p=0.05"
results/raw/e5_codesign.csv  a51486a  2026-07-05
```

**The criterion was committed two days before the result existed, in the public history.** This is
the rare case where a pre-registration claim is checkable by a third party with nothing but the
repository, and the paper now says so with that ordering rather than asserting the word.

### P2 (MAJOR) — "all results are reproduced by an automated staleness gate" was an overstatement

The gate covered **16 of 41** artifacts. Most of the remainder genuinely require NS-3 or the Pi rig —
but **four did not**: `factorial_ablation`, `pqc_projection`, `sensitivity_p` and
`lora_external_check` are pure model computation and were ungated only because they were new. That
is the same F1 hole the gate exists to close.

**Fixed by closing the hole rather than softening the sentence.** All four are now gated (each
re-derives byte-identically; the frozen suite is 14 → 18 tests), every remaining ungated artifact
has a stated reason, and the paper now claims exactly "all 20 model-derived artifacts" instead of
"all results".

---

## 10. Full paper audit (2026-08-07) — read end to end, every table checked against its artifact

*Requested: "understand it deeply, rewrite every section to standard, audit for contradictions,
tone, clarity, claims, results and methodology, fix and re-audit; check formatting, graphs and
tables; think about what visualisations we lack."*

### ⚠️ The largest finding: a whole table was stale, and a shipped figure plotted superseded data

**`tab:ns3` disagreed with its artifact in every cell.** It carried pre-30-seed values:

| N | paper had | artifact |
|---|---|---|
| 5 | +0.6 / −0.3 | **+0.54 / −0.07** |
| 10 | +0.9 / −0.4 | **+1.33 / −0.12** |
| 20 | +0.6 / −0.7 | **+1.14 / +0.39** |
| 35 | −1.4 / +0.9 | **+0.24 / −0.56** |
| 50 | −2.9 / +1.1 | **−0.37 / −0.27** |

Regenerated from the frozen `ns3_contention.csv`, with the statistic now named (median over 30
seeds, exact OFDM airtimes).

⚠️ **`fig_e5_codesign.png` had been shipping since 28 July plotting $H_f{=}40$\,B**, three days
before B1 measured it at 44\,B. Its caption said "104\,B to 26.0\,B" while the table beside it said
108 to 27.0 — 104 = 40+64. Two further figures (`e4_crossover`, `fig_envelope`) were equally stale.

**Root cause, and it is structural:** `make figures` regenerated only `figures_e123`, so four of the
five generators were never run by any gate. The frozen gate covers CSVs; nothing covered figures.
Fixed — `make figures` now runs all five, and `tests/test_figures_are_current.py` asserts every
generator still runs and every cited figure exists.

### Contradictions found and fixed

| # | contradiction | resolution |
|---|---|---|
| 1 | §Theory said $H_f \approx 40$\,B (assumed) while the rest of the paper used 44\,B measured | 44\,B measured, everywhere; all 9 mentions now agree |
| 2 | Text said the optimizer "breaks a byte-tie toward **ECDSA**"; the artifact selects **Ed25519** | corrected to Ed25519, which is what E5 reports |
| 3 | `tab:envelope` caption said the crossing is $U{\approx}2.80$; the text said 2.44 | 2.44, labelled as interpolated between the measured $U{=}2.23$ and $3.34$ rows |
| 4 | Text said the advantage "needs … the scheme (auth bytes)" while `tab:decomp` reports the scheme axis as moving *neither* | scheme removed from the list; stated byte-neutral and decided on energy |
| 5 | Validation band quoted as $+1.28/-0.49\%$ — matching neither derivation | $+1.29/-0.40\%$ (mean, guarded by a test), with the median-based $+1.33/-0.37\%$ named as such |
| 6 | `fig:ns3` caption claimed agreement "within 1.44 %" — the superseded 10-seed figure | 0.51 % |
| 7 | "within 2.49 % on success probability, idle-slot occupancy **and throughput**" — throughput is 0.51 % | statistics separated, each with its own figure |
| 8 | Naive-reduction failure quoted as $16\times$; the regenerated table gives $+1631\%$ | $17.3\times$, consistent in all three places |

⚠️ **Two derivations of the same band existed** and neither was wrong: `figures_ns3.py` uses the
*median* with exact OFDM airtimes, `test_validation_bands.py` uses the *mean* with defaults. The
paper now names which statistic it is quoting instead of implying there is only one.

### Visualisations: the gap was not missing figures but unused ones

The paper cited 3 of 9 generated figures — and the two it omitted were **exactly boundaries 1 and 2
of the new framing**. `figures_envelope_lora.py`'s own docstring had already said the envelope
"deserves a figure more than the auth-byte ratio does", and the paper was doing the opposite.
Added `fig:t6` (the exclusion tiers) and `fig:envelope` (the capacity envelope); 5 figures now.

### Rewritten for standard

* **§Implementation** was a project changelog ("P0 locked the toolchain… P1b switched…") in internal
  phase numbering, with "an eight-law discipline" as jargon. Rewritten as
  **Implementation and Validation**: what was built and how each component was checked.
* **Abstract** now opens on the feasibility question, matching the title, before naming the knobs.
* **Tone:** "This is the disease; T2--T5 are the cure" removed; "AUTHBC is a **rigorous**…" removed
  (self-praise); "we **jointly optimize all four**" softened to "search all four jointly, and report
  which of them actually interact" — the previous wording contradicted the F39 ablation.
* **Consistency:** the intro called the four choices "coupled" two sentences before showing that
  only one pair is.

### Methodological inconsistency between the two arms, fixed

The 802.11 arm reported `N_max` under both the mean and per-realisation readings; **the LoRa arm
reported only the mean**, with the caveat buried in §Reproducibility. `N_max = 3` is now given at the
point of use with its 95 % interval $[2,3]$, the 9-of-30 failure count, and the per-run value of 1.

### ⚠️ Re-audit pass 2 — the worst finding came last: a table built on the PURGED 3-seed run

`tab:lora-external` (the Bor cross-check) still carried the superseded data. Its AUTHBC column
matched `lora_capacity_3seed_SUPERSEDED.csv` **to three decimals**:

| N | paper had | 3-seed (purged) | 30-seed (current) |
|---|---|---|---|
| 5 | 0.0 % | **0.000** | 8.33 % |
| 8 | 13.4 % | **13.443** | 12.90 % |
| 30 | 59.0 % | **59.030** | 42.97 % |
| 50 | 74.7 % | **74.683** | 62.45 % |

Six 3-seed artifacts were purged weeks earlier (F38) and **this table was never re-derived with
them**. So the defect class CLAUDE.md calls *"the pattern of the whole audit"* — small samples read
against a threshold — was still being printed, after the audit that named it.

Two claims rode on the stale column:

1. **`N_max` was quoted as 5.** The 30-seed run gives **3** (0.9508 at $N{=}3$, 0.8981 at $N{=}4$);
   Bor's closed form gives **4** (4.418 % at $N{=}4$, 5.065 % at $N{=}5$). CLAUDE.md had said "their
   N_max=4 vs our 3" all along — the status board was right and the paper was wrong.
2. ⚠️ **The row annotated "we are more optimistic" restated retracted finding F18** — while a bold
   sentence 100 lines earlier said the exact opposite. The crossover is at $N{\approx}3$, not
   $N{=}8$: beyond it we are the *more pessimistic* model (1.6× at $N{=}5$, 2.1× at $N{=}50$).

**Why it survived three passes:** the Bor column was correct throughout. Half the table agreed with
its source, so it read as verified. ⚠️ *A partially-correct table is harder to catch than a wholly
wrong one.*

It propagated: `tab:lowrate` used $N_{\max}{=}5$ to compute an aggregate of 0.82 rec/s and a
"$\approx$2500×" 802.11-vs-LoRa gap. Corrected: 0.495 rec/s and **≈4200×**, which *strengthens* the
section's argument that LoRa is a different regime rather than a slow 802.11. The prose figure
"we measure ≈75 % at $N{=}50$" (also 3-seed) is now 62 %, and "2.3× more pessimistic" is 2×.

**Guards added:** `TestLoraExternalTable` compares every cell to `lora_external_check.csv`, asserts
no row revives F18 (it checks the *artifact*, not the wording), pins both $N_{\max}$ values, and
recomputes `tab:lowrate`'s arithmetic from its own columns.
