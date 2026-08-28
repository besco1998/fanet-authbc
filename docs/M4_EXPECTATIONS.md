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
