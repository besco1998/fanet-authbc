# M4 — is the U→V crossing frame-size invariant? Prediction, written before the run

*2026-08-28. Committed **data-free**, as its own commit, so the ordering is checkable in git
history — the discipline of `docs/DR6_EXPECTATIONS.md` and `docs/DIRECTION_C_SURVEY_PROTOCOL.md`.
⚠️ Finding **F40** forced a pre-registration claim to be withdrawn once because the expectations
file had never been committed. This is that commit.*

## Why this run exists

Audit **F43** (2026-08-28) found that the capacity envelope applies **one measured ceiling to every
configuration**. `results/raw/ns3_delay_ci.csv` has `n_nodes = 50` and `frame_bytes = 288` in every
row — the crossing **U ≈ 2.435** was measured at exactly one point — and
`experiments/capacity/config.yaml` then uses it as `u_ceilings: v95_mean` for configurations whose
frames run from **153 B** (delta/B at b=1) to **299 B** (A+JSON).

Ma & Chen's capacity is recomputed at each frame size in the **denominator** of U, so U is already
normalised for frame size. What was never tested is whether the **mapping from U to delivered
fraction** is itself frame-size invariant. That assumption is load-bearing for the *absolute*
N_max figures — 213 / 100 / 88 / 31 — though not for the 1.9–3.2× ratios, which use the same
ceiling on both sides and are protected by construction.

## The prediction

Run: `authbc-delay`, N = 50, 30 seeds, **frame = 174 B** (the A+CBOR Pillar-1 baseline frame,
H_f 44 + g_a 64 + s_cbor 66 — the *other* end of the envelope's range, and the frame that produces
the 88 and 31 baselines the ratios divide by).

| quantity | at 288 B (measured) | at 174 B — predicted | reasoning |
|---|---|---|---|
| V ≥ 0.95 crossing | **U ≈ 2.435** | **2.1 – 2.8** | U already normalises for capacity, so the crossing should move little; the residual sensitivity is that a smaller frame spends proportionally more of its airtime on preamble + DIFS, so a collision costs relatively less channel time |
| direction of any shift | — | **slightly higher U** | shorter frames ⇒ shorter vulnerability window relative to the fixed 9 µs slot, so the channel should tolerate marginally more normalised load before V falls |
| delivered at U ≈ 1 | 0.98896 | **≥ 0.98** | the "98.9 % still at U=1" result should not be frame-size specific; it is what withdrew T7 |
| dispersion | 10/30 seeds fail V at U = 2.23 | **comparable straddling** | S3b's finding is about applying a threshold to a mean, which is a property of the criterion, not of the frame |

### ⚠️ The load-bearing prediction

**The crossing stays inside 2.1–2.8, i.e. within ±15 % of 2.435.**

* **If it does:** the universal ceiling is justified, M4 closes, and the absolute N_max figures keep
  the support they currently only assume.
* **If it does NOT:** the envelope must compute a **per-configuration crossing** rather than one
  ceiling, and the absolute N_max column changes. ⚠️ In that case **do not average it away** — the
  ratios would still hold, but `tab:envelope`'s absolute numbers would need re-deriving and the
  paper would need to say so (Law 6).

## What this run cannot show

Nothing about **N**. The crossing is measured at N = 50 in both arms, while the envelope applies it
from N = 2 to N = 213. Frame-size invariance is the cheaper half of the assumption and the half
that varies across the envelope's *rows*; N-invariance would need a second sweep and is left
stated rather than tested.

It also says nothing about the **per-realisation** criterion, which S3b already bracketed at
U ∈ (1.672, 2.230] and which the envelope reports separately as `v95_strict_lo/hi`.

---

# OUTCOME (appended after the run; the prediction above is unchanged)

*Artifact: `results/raw/ns3_delay_174B.csv`, 12 rates × 30 seeds, `authbc-delay` on ns-3.48.
Driver: `python ns3/run_delay.py --frame-bytes 174 --seeds 30 --out ns3_delay_174B.csv`.*

## Result

| | 288 B (published) | 174 B (this run) |
|---|---|---|
| V ≥ 0.95 crossing | **U = 2.435** | **U = 2.367** |
| interpolated between | U=2.230 (V=0.96246) and U=3.345 (V=0.89479) | U=2.321 (V=0.95293) and U=3.095 (V=0.90345) |
| shift | — | **−0.068 (−2.8 %)** |

## Verdict against the prediction

| predicted | outcome |
|---|---|
| **crossing inside 2.1–2.8** *(load-bearing)* | **2.367 — CONFIRMED** |
| V ≥ 0.98 at U ≈ 1 | 0.98832 at U = 0.928 — **confirmed** |
| comparable straddling of the threshold | U=2.321 has mean 0.9529 with **13/30 seeds failing** — **confirmed**, and it is S3b's defect reproducing at a second frame size |
| crossing drifts slightly **higher** at 174 B | ⚠️ **measured LOWER — but see below** |

## ⚠️ The directional prediction was untestable, and that is a flaw in the pre-registration

The shift is **−0.068** against a combined standard error of **±0.151** on the two interpolated
crossings — **0.45 σ**. Propagated from the bracketing rows' own dispersion
(σ = 0.018–0.032 over 30 seeds) through the local slope dV/dU ≈ −0.06:

```
crossing s.e.   288 B  ±0.109      174 B  ±0.104
observed shift  −0.068           combined s.e.  ±0.151       ->  0.45 sigma
```

So the experiment **cannot resolve the sign**. Writing "the crossing drifts slightly higher"
into the pre-registration committed me to a direction the design had no power to test, and had
the noise fallen the other way I would have recorded a confirmation I had not earned. **The
mechanism I gave — shorter vulnerability window against the fixed 9 µs slot — is neither
supported nor refuted here.** Recorded rather than quietly dropped, because a pre-registration
that claims more resolution than the run possesses is a defect of the same family as applying a
threshold to a mean (S3/S3b): the number looks like evidence and is not.

**A directional prediction should carry a power estimate, or be stated as a band.** The
load-bearing prediction did carry one (±15 %) and is the reason this run answers its question.

## What it settles

**The universal U ceiling is justified.** Across a **1.66×** change in frame size — 288 B, the
optimized delta/B frame, against 174 B, the A+CBOR Pillar-1 frame that produces the baselines the
capacity ratios divide by — the crossing is **statistically indistinguishable**. U already
normalises for capacity through Ma & Chen in its denominator, and what remains of the U→V mapping
carries no resolvable frame-size dependence over the envelope's range (153–299 B).

`tab:envelope`'s absolute N_max column — **213 / 100 / 88 / 31** — therefore keeps support it
previously only assumed. **No published number moves.** `docs/OPEN_ITEMS.md` M4 closes.

## What it still does not settle

**Nothing about N.** Both arms are at N = 50, while the envelope applies the ceiling from N = 2 to
N = 213. Frame-size invariance was the cheaper half of the assumption and the half that varies
across the envelope's *rows*; N-invariance remains stated rather than tested, and the paper says so.
