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
