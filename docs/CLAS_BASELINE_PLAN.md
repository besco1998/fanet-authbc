# The external baseline: comparing against a VANET CLAS scheme

*The single largest gap identified by the adversarial review: every baseline in the paper is an
internal variant of our own design. This plans the fix.*

## The key structural insight — the comparison is cheaper than it looks

**Placement C already *is* the cross-signer aggregation slot**, currently filled by BLS12-381
(96 B aggregate, invariant in b). A certificateless aggregate-signature (CLAS) scheme is an
**alternative construction for that same slot**, not a different system.

So the comparison does **not** require implementing CLAS cryptography. It requires:

| need | why | source |
|---|---|---|
| CLAS aggregate signature size (B) at a stated security level | drives every byte and capacity number | primary paper, not a survey |
| whether certificates ride on the wire | ⚠️ **the real CLAS advantage** — see below | primary paper |
| CLAS verify cost on ARM | only for the energy column | primary paper, or measure |

With (1) and (2), the existing optimizer, channel model and capacity machinery evaluate it directly.

## ⚠️ The comparison our model currently cannot make fairly

CLAS's headline claim is **certificateless**: no certificate bytes on the wire. Our byte model
assumes PKI and **does not charge certificate transmission at all** — for any scheme. So a naive
comparison would understate CLAS's advantage.

**This must be fixed before the comparison is run**, or the result is rigged in our favour. Two
options:
* charge certificates to the PKI schemes explicitly (correct, and it changes our own numbers), or
* state the comparison as *signature bytes only* and say plainly that certificate distribution is
  excluded from both sides.

The first is more honest and more work. **Recommended: the first.** ⚠️ It may reduce our reported
advantage, which is precisely why it must be done before, not after, seeing the CLAS numbers.

## What the comparison should report

1. **Bytes/record vs b**, placement C, for BLS vs CLAS — the direct substitution.
2. **Capacity** at both thresholds, via the existing `channel_utilisation` path.
3. **Feasibility** — does the CLAS aggregate fit the LoRa 222 B payload where BLS does not?
4. **What we do NOT claim**: we are not proposing a better construction. The axis stays
   *configuration of standardised primitives* vs *new construction*, as §Related Work already states.

## Honest expected outcome

**[SPECULATION — flagged as such]** CLAS schemes are typically ECC-based with aggregate sizes in the
tens of bytes, i.e. plausibly *smaller* than BLS's 96 B. **The comparison may well show a CLAS
construction beating our placement-C configuration on bytes.** That is a publishable and honest
result: it would say the co-design framework correctly identifies *which axis* matters, while a
purpose-built construction wins on the crypto axis — which is exactly the division of labour the
paper already claims.

**Do not run this expecting to win.** Run it to find out.

## Effort

* obtaining and verifying two primary sources: ~1 day
* certificate-byte correction to the model: ~2 days, touches frozen artifacts
* evaluation and write-up: ~2 days

Roughly one week, not the 2–3 weeks estimated in the review, because no cryptographic implementation
is required.
