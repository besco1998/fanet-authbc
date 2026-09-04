# Claim audit — every headline number, re-derived from first principles

*2026-08-28/30. Requested by Mohamed: "audit deeply each scientific claim, number, result,
implementation, literature comparison, value, methods and placement", then "audit all the math
deeply and compare it against the simulation". Readable rendering published as an artifact;
**this file is canonical**.*

**Method.** Re-derive each quantity from its equations, then check it against a discrete-event
simulation written for the purpose — never re-read the project's own conclusion about it. That
distinction is the whole point: every published number reproduced, so nothing here was found by
recomputing arithmetic. It was found by asking *what does this constant actually mean*.

Full evidence: **F43** and **F44** in [`audits/model_provenance.md`](audits/model_provenance.md).
Outstanding items: [`OPEN_ITEMS.md`](OPEN_ITEMS.md) §A9. Guards:
`tests/test_math_audit.py` (46 tests) and `tests/test_wire_profile.py` (30 tests).

---

## The verdict

**Nothing was a wrong number.** Every finding is a convention or a limit that decides a headline
and was never written down. All are defect class **C2 — an unverified constant on the measurement
path**, which is the one class the post-F30 30-seed discipline cannot touch.

⚠️ **In three of the five major findings, the unstated choice happens to favour our own claim** —
and in all three it does so *conservatively*, except one, which cost a headline.

---

## Major findings

### F44 — the exclusion bound rested on a header we declined to optimise

⚠️ **This one moved the headline: "four of seven EU868 rates" became THREE.**

Two facts the project had always known separately, and never composed:

1. `docs/01` §2a: the frame skeleton is mostly CBOR **text key names**, and "an integer-keyed
   profile would shrink substantially — a wire-format optimisation this thesis does not claim."
2. `docs/02` T6: the exclusion bound is `s_max = M − H_f − g_a`. **It depends on H_f.**

| profile | H_f | B/record | DR3 `s_max` | DR3 |
|---|---|---|---|---|
| current (text keys, `src`+`seq` per record) | **44 B** | 94.0 | 7 B | excluded |
| **integer keys only** | **22 B** | 76.5 | **29 B** | ⚠️ **FEASIBLE** |
| integer keys + `src`/`seq` elided | 22 B | 66.5 | 29 B | feasible |

Seven text keys cost **29 B**; the same seven as small integers cost **7 B** — the convention COSE
and SenML already use. That single change halves the header and takes DR3 from missing by six bytes
to clearing by sixteen. The record elision is not even needed.

**What survives, and it was always the strong half.** DR0–DR2 stay excluded at a **zero-byte header
and a one-byte record**, because `M = 51 B < g_a = 64 B`. The smallest standardised alternative
(48 B compressed BLS12-381 G1, 126-bit security) leaves three bytes for header and record together.
That is arithmetic and cannot move.

**And the boundary became constructive** — it now names what would have to change, and shows that
for DR3 the answer is a header redesign rather than new cryptography. T6's tier taxonomy always
named "encoding" as the tier compression can attack. This is that tier being attacked.

⚠️ **The wire format is NOT changed.** D6 freezes it; `placement/wire_profile.py` measures an
alternative and `TestTheFrozenFormatIsUntouched` fails if it leaks into the shipped format.

### F43c — the pre-registered success criterion could not have failed

The **ordering is genuine** and independently verified: the ≥40 % criterion is in `docs/04` at
`3354ec1` (2026-07-03 04:42); the E5 result at `a51486a` (2026-07-05 00:34).

But the quantity it tests reduces **exactly** to `1 − 1/b` — placement A carries `g_a + H_f` per
record, B carries `(g_a + H_f)/b`, and the ratio is the identity F13 already forbade quoting. So:

```
1 − 1/b ≥ 0.40   ⟺   b ≥ 1.667   ⟺   b ≥ 2
```

Independent of encoding, scheme, placement, H_f and g_a. The other half, V ≥ 0.95, E17 already
showed is satisfied by construction with zero margin. **Both halves are vacuous: no configuration
that batches at all could have failed.**

Keep the pre-registration and the date. What had to go is the implication that it was a live test.

### F43b — H_f is a range, 38–44 B, and 44 favours the exclusion

Canonical CBOR encodes integers 0–23 in one byte and those ≥65536 in five, so the measured header
moves with `src` and `base_seq`: **38 B** for a fresh low-id node, **44 B** an hour into flight at
50 Hz. The documented 44 B reproduces exactly at realistic magnitudes — the measurement was sound;
`docs/01` §2a simply called it constant when it is constant only in *b*.

⚠️ **The bias direction is opposite for T6.** docs/01 §2a analyses H_f's bias for the *byte
comparison*, where 44 B is conservative. T6's bound means a **larger H_f makes exclusion more
likely** — so 44 B is the end of the range most favourable to the paper's most durable claim.
`framer.measure_frame_header_bytes` makes the range measurable rather than assumed.

### F43a — `D(b)` names the oldest record's age and computes the batch window

With periodic arrivals: the **batch-window duration** is `b/Λ`; the **age of the oldest record** at
transmit is `(b−1)/Λ`. Both confirmed exactly by simulation, deterministic and Poisson (Erlang(b)
and Erlang(b−1)). `docs/02` §7 named the second and computed the first.

**`b/Λ` survives as the worst case** — it is exactly `(b−1)/Λ` plus one sampling quantum — and is
retained unchanged. ⚠️ Cost now stated: the tight reading admits **b=5** at both operating points
(66.6 B/rec, **−61.78 %**) where we publish b=4 (72.0 B, −58.68 %). **We under-report our own saving
by ~3 points.**

⚠️ One consequence was *not* conservative: `docs/02` §7a's "knife-edge" (100.37 ms, "b collapses to
1") is a property of the convention, not the design space — the oldest record in that frame is aged
**50.37 ms**. Corrected in place.

### F43d — `s` depends on the generator window; the CI is ~150× too narrow

`seq` and `ts` grow with the record index and variable-length encodings charge for the digits:

| | n=1000 | n=10 000 | `e1_dominance` (30×1000) | `p1_sizes` (seed 1, n=10 000) |
|---|---|---|---|---|
| json | 191.36 | 193.52 | 191.085 | 193.518 |
| cbor | 66.73 | 68.94 | 66.252 | 68.936 |
| msgpack | 66.29 | 68.84 | 65.160 | 68.836 |
| **delta** | 45.04 | 45.01 | 44.998 | 45.005 |

Delta is flat because it encodes differences. **Two committed artifacts disagree by up to 3.7 B on
the same named quantity and both are correct for their own protocol.** E1's bootstrap CI for cbor is
±0.02 B — *seed* variation — while the systematic window term is ~2.7 B, **≈150× wider**.

Direction is conservative: a longer flight inflates the CBOR *baseline* and leaves the delta
*optimum* alone. E1 samples the **first ~50 s of each flight**, now stated in `docs/04` §1.

### F43e — Bor's `N_max`=4 sits inside his own fit's unreliable region

`lora.py` already documents that Eq. (8) does not pass through the origin and predicts 1.783 % loss
at N=0, and that "below N ~ 5 the intercept dominates". Their N_max = 4 is decided at N=4 (4.418 %)
and N=5 (5.065 %) — **both inside that band**, with the non-physical intercept contributing **40 %
of the predicted loss at N=4**.

Direction is conservative: forcing the fit through the origin gives their N_max = **5**, *widening*
the gap against our 3. So quoting 4 is the safe choice — it simply needs saying.

⚠️ **"≈2× more pessimistic" hides a sign change.** The ratio runs **0.91× at N=2** (*we* are the more
optimistic model there), 1.07× at N=3, and 2.09–2.17× from N=10 up — and the crossover sits in
exactly the region where N_max is decided. F18 was retracted for a sign error on this same
comparison. `bor2017_pessimism_ratio` now refuses to be quoted as one number.

---

## M4 — closed by measurement

The U→V crossing was measured at a second frame size (**174 B**, the A+CBOR frame that produces the
baselines the capacity ratios divide by): **2.367** against 288 B's **2.435** — a **0.45 σ**
difference, **statistically indistinguishable** across a 1.66× change. The universal ceiling is
justified and no published number moves.

⚠️ **The pre-registration also made a DIRECTIONAL prediction the run had no power to test.** I
predicted the crossing would drift *higher*; it drifted lower, at 0.45 σ against a combined standard
error of ±0.151. **Had the noise fallen the other way I would have recorded a confirmation I had not
earned.** Kept visible as a flaw in my own pre-registration: *a directional prediction needs a power
estimate, or must be stated as a band.*

⚠️ **N-invariance remains untested** — both arms are N=50 while the envelope applies the ceiling from
N=2 to N=213.

---

## Checked and found CLEAN

*Recorded because a clean result is only useful if you can see what was tested.*

| check | method | result |
|---|---|---|
| OFDM PPDU airtime | hand-derived from 802.11a symbol timing | 1940 µs / 44 µs **exact** |
| Ma & Chen broadcast | vs `sim.dcf_ladder`, an independent slot-exact Monte Carlo | **≤0.08 %** at N=5–50 |
| … and vs NS-3 3.48 | 30 seeds | ≤0.51 % |
| the CFP mechanism | `head_start=False` removes only that asymmetry | collapses to the naive reduction; **16.9× at N=50**, reproducing F9 |
| Bianchi unicast | vs NS-3 | band **−0.40 … +1.29 %** |
| Bianchi fixed point | residual of both DCF equations, N=1…1000 | ≤ 7×10⁻¹³ |
| `N_max` first-failure search | exhaustive vs full scan, 7 configs × 4 ceilings | **identical everywhere** |
| −58.68 % and 213/100/88/31 | recomputed from artifacts | reproduce exactly |
| pre-registration ordering | git | genuine, ~1.8 days |

⚠️ **One clean result is clean by ACCIDENT.** Ma & Chen's S(n) is **non-monotone** in N — it dips near
N≈35 and recovers, and all three implementations agree, so it is real physics of the CFP series. The
`N_max` search breaks on the first violating N, which is valid only if U(n) is monotone. It is —
because U(n)'s explicit factor n outruns the recovery — but that is **safe by arithmetic, not by
construction**, and nothing tested it until now.

---

## Minor

* `bianchi.tau_of_pc(0.5)` raised on a **removable** singularity whose limit is `4/(2W+2+WM)`, and
  p_c crosses 0.5 for N ≳ 21. Never triggered; now returns the limit.
* Two dead constants removed (`LLC_SNAP_BYTES`, `MAC_HDR_FCS_BYTES`) — editing them changed no result
  while appearing to.
* The delivered fixed-point residual is `TOL/0.3`, not the documented `TOL`. Immaterial; documented.
* **Structural, not fixed:** 10 B/record of wire redundancy (`src` and `seq` duplicated against the
  frame header), ~14 % of the 72.0 B headline. D6 freezes the wire, so it is recorded as known
  headroom — which makes the reported cost an upper bound on an untuned design.

---

## The transferable lesson

Three times in this project a claim survived because two facts were each individually recorded and
never placed side by side — **F18** (quoting the PDF instead of the figure), **docs/02 §9c**
(asserting `N_max = 3` one line above a table of 3-seed data saying otherwise), and now **F44**.

> **A register that stores facts separately does not compose them. Only re-derivation does.**

---

*Companions: [`THE_STORY.md`](THE_STORY.md) (plain-language account) ·
[`HONEST_ASSESSMENT.md`](HONEST_ASSESSMENT.md) (what the work is worth) ·
[`../thesis/STATUS.md`](../thesis/STATUS.md) (thesis draft state).*
