<!-- Snapshot, 2026-11-21, of the Claude doc 'Mathematical models for authenticated, batched UAV telemetry', tab 'Unified closed-form model' (rev 19). Place at docs/revision/unified_closed_form_model.md. The Claude doc is the source; replace this file when Mohamed sends a newer export. -->

# Unified closed-form model

## 1. The result

The whole system reduces to one expression. For every shared resource j (the channel, the receiver processor) a frame of b records costs a fixed amount Φ\_j plus Ψ\_j per record, against a budget Β\_j, and the largest swarm is

```latex
N_{\max} = 1 + \min_{j}\ \frac{\mathrm{B}_j\, b^{*}}{\Lambda\,\bigl(\Phi_j + \Psi_j\, b^{*}\bigr)}, \qquad
b^{*} = \min\Bigl\{\bigl\lfloor \Lambda\,(D_{\max}-S_q) \bigr\rfloor,\ b_M\Bigr\} \tag{G1}
```

It holds when b\* ≥ 1 and a self-verifying frame fits the link (ℓ\_min ≤ M); otherwise no configuration exists. Everything else in this tab is either the definition of Β, Φ, Ψ for a given link and design, or a consequence of (G1).

**Status, 19 November 2026.** The model has now been tested against ns-3 at 802.11a and 802.11b with predictions registered before every run. Capacity holds within ±5 % at 802.11a; at 802.11b it is 5–6 % low (the safe side) for 15–37 stations; frames of a split unit sent back to back break it (the unsafe side). Section 9 gives the full scorecard and what changed in the model.

What changed from the first tab:

- **One law for every access protocol.** ALOHA, CSMA, scheduled access and 802.11 DCF differ only in the three numbers (Β, Φ, Ψ).
- **The DCF constants are derived, not fitted,** from three loss mechanisms. The first tab's (M24) had two; the third (frames that arrive in the DIFS after a busy period) and a correction to each of the other two matter for frames shorter than about 400 µs.
- **The model is checked.** The explicit law (G9) reproduces 24 ns-3 capacities from the project repository within 4.4 % (mean 2.0 %). Against an event simulation I wrote from the access rules, the full loss expression gives capacity within 6.5 % for N ≥ 19 and within 9 % for the smallest swarms (N ≈ 8–14), on the conservative side in 44 of 45 cases (Section 6).
- **Design rules follow in closed form:** the gain of batching, the price of the authenticator, when a key record in every frame is optimal, what fragmentation costs, the best batch under bit errors, and the smallest deadline a duty-cycled link can meet (Section 5).

No value from the seminar or the journal draft enters the derivation. Symbols are those of the first tab; new ones are defined where they appear.

## 2. The principle: fixed cost per frame, proportional cost per record

Every resource the system consumes has the same shape. A frame of b records costs Φ + Ψb of it, so one record costs

```latex
C(b) = \frac{\Phi}{b} + \Psi \tag{G2}
```

| Resource | Per frame, Φ | Per record, Ψ | Budget Β | Kind |
| --- | --- | --- | --- | --- |
| Bytes on air, signature per frame | H + L + g + (s\_k − s\_δ)/r | s\_δ | – | accounting |
| Bytes on air, signature per record | H + L + (s\_k − s\_δ)/r | s\_δ + g | – | accounting |
| Airtime | Φ\_T = T\_pre + 8(ℓ\_o + Φ\_B)/R | Ψ\_T = 8Ψ\_B/R | – | accounting |
| Channel | Φ\_X = Φ\_T + τ̂ | Ψ\_X = Ψ\_T | set by the access protocol (Section 3) | shared: bounds N |
| Receiver processor | t\_dec,0 + t\_v | t\_dec,1 + t\_h | u\_max · cores | shared: bounds N |
| Duty cycle | Φ\_T | Ψ\_T | d per node | private: bounds b and Λ |
| Sender energy | P\_cpu(t\_enc,0 + t\_s) + P\_txΦ\_T | P\_cpu(t\_enc,1 + t\_h) + P\_txΨ\_T | – | private: cost |

The frame airtime is therefore affine in the batch, T\_f(b) = Φ\_T + Ψ\_T b, and the frame rate is Λ/b.

The design variables do only one thing: they move an item between the Φ column and the Ψ column. One signature per frame moves g from Ψ to Φ. One chain link per frame moves L from Ψ to Φ. Delta coding moves s\_k − s\_δ from Ψ to Φ. The batch size then decides how much a Φ-item costs per record: 1/b of a Ψ-item.

## 3. The channel as a budget

Let ν = (N − 1)f be the rate at which the other stations start frames. A channel has capacity when its loss p(ν) reaches the target ε. For every access protocol below, that condition has the form

```latex
\nu^{*} = \frac{\mathrm{B}}{\Phi_X + \Psi_X\, b} \tag{G3}
```

| Access protocol | Loss model | Β | Φ\_X | Ψ\_X |
| --- | --- | --- | --- | --- |
| Pure ALOHA | 1 − exp(−2νT\_f) | ℓ\_ε/2 | Φ\_T | Ψ\_T |
| Slotted ALOHA | 1 − exp(−νT\_f) | ℓ\_ε | Φ\_T | Ψ\_T |
| Ideal CSMA, detection time δ | 1 − exp(−2δν) | ℓ\_ε | 2δ | 0 |
| Scheduled access, guard T\_g | 0 while ν(T\_f + T\_g) ≤ 1 | 1 | Φ\_T + T\_g | Ψ\_T |
| 802.11 broadcast DCF | (G5) | ρ\*/κ | Φ\_T + τ̂ | Ψ\_T |

Here ℓ\_ε = ln(1/(1 − ε)). The two extremes are instructive: under ALOHA only airtime matters, so a byte saved is as good as a frame saved; under ideal CSMA only the number of frames matters and bytes are free. DCF lies between, and τ̂ measures where.

### 3.1 Broadcast DCF: three loss mechanisms

Access rules assumed (rule set A): a frame that finds the medium idle for DIFS is sent at once; a frame that arrives in the DIFS after a busy period is sent at its end without backoff; a frame that arrives to a busy medium draws a backoff uniformly from 0 … W − 1; a start cannot be sensed during its first δ. One collision domain, no capture, Poisson starts. Define three dimensionless loads:

```latex
a = \nu\,(T_f-\delta)\Bigl(1-\frac{p}{2}\Bigr), \qquad \gamma = \nu\cdot\mathrm{DIFS}, \qquad \eta = \nu\,\sigma_s\,\frac{W-1}{2}
```

a is the probability that a frame arrives to a busy medium (collided frames share a busy period, hence the factor 1 − p/2); γ is the probability that it arrives in a DIFS gap; η is the mean number of frames sent by immediate access while a deferred frame counts down its own backoff.

```latex
\bar K = \frac{a\,(1+\gamma+2\eta)}{1-\gamma-a} \tag{G4}
```

```latex
p(\nu) = \underbrace{\frac{a\,\bar K}{W+\bar K}}_{\text{same-slot tie}}
\;+\; \underbrace{\gamma\Bigl(\frac{2a}{W}+\gamma\Bigr)}_{\text{DIFS-gap start}}
\;+\; \underbrace{2\,\delta\,\nu\,(1+a)}_{\text{detection window}} \tag{G5}
```

**Tie term.** A deferred frame ties with each frame it shares a contention round with, independently with probability 1/W (first tab, Lemma 1). K̄ is the mean number of such frames. *Derivation.* Let M be the number of busy periods between a deferred frame's arrival and its own transmission, counting the one it arrived in. Each brings a new deferred frames on average, and by symmetry the frame meets as many that arrived before it as after it, so K̄ = a(2E\[M\] − 1). The frame is delayed by immediate-access frames during its own countdown (η, exactly, since it must count its own slots whoever else is waiting), by gap frames (γ per busy period), and by half of the frames it meets (those with the smaller counter):

```latex
\mathbb{E}[M] = 1 + \eta + \gamma\,\mathbb{E}[M] + \tfrac{1}{2}\bar K
\quad\Longrightarrow\quad \mathbb{E}[M] = \frac{1+\eta-a/2}{1-\gamma-a}
```

which gives (G4). K is over-dispersed (geometric rather than Poisson), so the probability of at least one tie is K̄/(W + K̄) rather than 1 − exp(−K̄/W). With γ = η = 0 this is K̄ = a/(1 − a), the M/D/1 value of the first tab, now derived rather than assumed.

**Gap term.** A gap frame starts exactly at the end of the DIFS. It collides with a newly deferred frame that drew counter 0 (a/W) or with another gap frame (γ); the same pairs counted from the deferred frame's side give the factor 2.

**Window term.** Any start followed within δ by an arrival costs both frames (2δν). In addition, an immediate start that falls within δ before a backoff expiry is not sensed by the expiring station (2δν · a).

**What ns-3 showed about the three terms.** The total of (G5) and the busy share a hold at 802.11a, but the split does not describe ns-3's mechanisms: the tie term is predicted 1.2–4.9 times too large, the detection-window term up to 3 times too small (6 times at 802.11b), and K̄ 1.1–2.6 times too large. Most of the mismatch is a relabelling. ns-3 counts each station's backoff slots from that station's own backoff start, so two counters that expire in the same slot can start a few microseconds apart, and they are then lost as a detection-window collision rather than a tie. Counted together, ties are 3–18 % above ns-3 at 802.11a. (G5) is therefore validated as a total, not as a breakdown of causes; the derivation of K̄ above remains unconfirmed.

### 3.2 The two DCF constants

For frames long beside the protocol times, (G5) is p₀(a) plus a correction linear in ν, with p₀(a) = a²/(W − (W − 1)a). Setting p = ε and expanding to first order in the correction gives an explicit capacity with two constants, an occupancy ceiling ρ\* and a protocol time τ₀:

```latex
\rho^{*} = \frac{-\varepsilon\,(W-1) + \sqrt{\varepsilon^{2}(W-1)^{2} + 4\,\varepsilon\,W}}{2} \tag{G6}
```

```latex
c_{\mathrm{eff}} = \frac{\rho^{*2}\,W\,\bigl[(\mathrm{DIFS}+\sigma_s(W-1))(1-\rho^{*}) + \mathrm{DIFS}\bigr]}{\bigl(W-(W-1)\rho^{*}\bigr)^{2}} + \frac{2\rho^{*}\,\mathrm{DIFS}}{W} + 2\delta\,(1+\rho^{*}) \tag{G7}
```

```latex
\tau_0 = \frac{c_{\mathrm{eff}}}{p_0'(\rho^{*})}, \qquad
p_0'(\rho^{*}) = \frac{2\rho^{*}\bigl(W-(W-1)\rho^{*}\bigr) + (W-1)\rho^{*2}}{\bigl(W-(W-1)\rho^{*}\bigr)^{2}} \tag{G8}
```

```latex
N_{\max} - 1 = \frac{\rho^{*}}{f\,\bigl[\kappa\,(T_f-\delta) + \tau_0\bigr]}, \qquad \kappa = 1-\frac{\varepsilon}{2} \tag{G9}
```

In the notation of (G3): Β = ρ\*/κ and τ̂ = τ₀/κ − δ. (G9) has the form of an airtime law, capacity ∝ 1/(f(aT + c)), but both constants now come from W, the slot, DIFS, δ and ε. For the IEEE 802.11a OFDM values (slot 9 µs, DIFS 34 µs, W = 16, δ = 4 µs):

| Loss target ε | ρ\* | τ₀ (µs) | Β = ρ\*/κ | τ̂ (µs) |
| --- | --- | --- | --- | --- |
| 0.02 | 0.435 | 143 | 0.440 | 141 |
| 0.05 | 0.595 | 98 | 0.610 | 97 |
| 0.10 | 0.721 | 74 | 0.758 | 74 |

τ₀ is the time, in addition to its own airtime, that every frame effectively occupies. It is the quantitative form of the statement that the cost that binds is the frame: at ε = 0.05 a frame costs the channel about 97 µs before its first byte.

## 4. The capacity law

Substituting f = Λ/b in (G3) gives the capacity of one shared resource as a function of the batch:

```latex
N_{\max}(b) = 1 + \frac{\mathrm{B}\,b}{\Lambda\,(\Phi + \Psi\,b)} \tag{G10}
```

### 4.1 Saturation form and the gain of batching

(G10) is a saturating hyperbola with two parameters that have direct meanings:

```latex
N_{\max}(b) - 1 = N_{\infty}\,\frac{b}{b+\beta}, \qquad
N_{\infty} = \frac{\mathrm{B}}{\Lambda\,\Psi}, \qquad \beta = \frac{\Phi}{\Psi} \tag{G11}
```

N\_∞ is the capacity if only the per-record cost existed; it depends on nothing in the Φ column, so not on the header, the chain link or a per-frame signature. β is the batch at which half of N\_∞ is reached: the fixed cost of a frame measured in records. The gain over one record per frame is

```latex
\Gamma(b) = \frac{N_{\max}(b)-1}{N_{\max}(1)-1} = \frac{b\,(1+\beta)}{b+\beta}, \qquad 1 \le \Gamma(b) < \min\{b,\ 1+\beta\} \tag{G12}
```

This one number β answers the questions the first tab treated separately. The gain is always below b. It approaches b when β ≫ b (fixed cost dominates: fast PHY, small records, large τ̂). It depends on the signature size only through β, so a larger per-frame signature raises β and moves the gain closer to b. For the channel, β = (Φ\_T + τ̂)/Ψ\_T.

### 4.2 Deadline form and the two regimes

Freshness caps the batch at b = ΛD′, with D′ = D\_max − S\_q the deadline net of channel and verification delay. Inserting it (and ignoring the integer rounding) removes the batch from the expression:

```latex
N_{\max} - 1 = \frac{\mathrm{B}\,D'}{\Phi + \Psi\,\Lambda\,D'} \tag{G13}
```

Read it as a budget per deadline window: in one window each node must send one frame (Φ) carrying ΛD′ records (Ψ each), and the channel offers ΒD′. Two regimes follow, separated by ΛD′ = β:

| Regime | Condition | Capacity | Depends on | Does not depend on |
| --- | --- | --- | --- | --- |
| Frame-limited | ΛD′ ≪ β | ΒD′/Φ | deadline, header, link, signature, PHY overhead | record rate, record size |
| Record-limited | ΛD′ ≫ β | Β/(ΨΛ) | record rate, record size | deadline, authenticator |

In the frame-limited regime capacity is proportional to the deadline and the authenticator is paid in full; in the record-limited regime the authenticator is free. The inverse of (G13) gives the deadline a swarm of N needs, with a pole at N\_∞:

```latex
D' = \frac{\Phi\,(N-1)}{\mathrm{B} - \Psi\,\Lambda\,(N-1)} \tag{G14}
```

### 4.3 Feasibility

(G1) is defined on the set where a configuration exists. Its two edges are the two boundaries of the paper, now as conditions on the same quantities:

```latex
\Lambda\,D' \ge 1 \ \ (\text{a frame meets the deadline}), \quad \Lambda\,D' \ge 2 \ \ (\text{a batch does}), \qquad
M \ge \ell_{\min} = H_{\min}+L+g+s_{\min} \ \ (\text{a frame fits}) \tag{G15}
```

## 5. Design rules in closed form

Each rule is a consequence of (G10); none needs a simulation to state.

**R1. Placement.** Moving x bytes from per record to per frame lowers the cost per record by 8x(1 − 1/b)/R and raises N\_∞. Signing every record instead of every frame puts g in Ψ and divides N\_∞ by (s\_δ + g)/s\_δ.

**R2. Price of the authenticator.** Let Φ\_auth = 8(L + g)/R be the authenticator's share of Φ. Relative to the same frame without it, capacity falls by the fraction

```latex
\pi(b) = \frac{\Phi_{\mathrm{auth}}}{\Phi + \Psi\,b} \tag{G16}
```

which decreases with b. A shorter authenticator (a MAC tag, a truncated link) reduces Φ\_auth only; it cannot change τ̂ or the PHY overhead in Φ, which is why it gains less than a shared frame.

**R3. Key-record interval.** With one key record in r frames the loss target tightens to ε\_r ≈ 2ε/(r + 1) (exact values at ε = 0.05: 0.034, 0.020, 0.011 for r = 2, 4, 8) while Φ falls by 8(1 − 1/r)(s\_k − s\_δ)/R. So r > 1 raises capacity if and only if

```latex
\frac{\mathrm{B}(\varepsilon_r)}{\mathrm{B}(\varepsilon)} > \frac{\Phi_r + \Psi\,b}{\Phi + \Psi\,b} \tag{G17}
```

For ALOHA-type channels the left side is 2/(r + 1); for DCF at ε = 0.05 and r = 2 it is 0.525/0.595 = 0.88 before the increase of τ₀ is counted. A dependent frame therefore pays only if dropping the key record removes more than 12 % of the frame's whole channel cost, τ̂ and PHY overhead included. A key record in every frame is optimal otherwise, which is a general statement and not a property of one loss rate.

**R4. Fragmentation.** A signed unit split over n frames must have all n arrive, so the per-frame target becomes ε\_n = 1 − (1 − ε)^(1/n), and the per-transmission part of Φ (PHY and MAC overhead plus τ̂, call it Φ₀) is paid n times:

```latex
N_{\max} - 1 = \frac{\mathrm{B}(\varepsilon_n)\,b}{\Lambda\,\bigl(n\,\Phi_0 + (\Phi-\Phi_0) + \Psi\,b\bigr)}, \qquad \mathrm{B}(\varepsilon_n) = \frac{\mathrm{B}(\varepsilon)}{n} \ \text{exactly for ALOHA-type channels} \tag{G18}
```

This is the price of relaxing the exclusion bound by spreading a signature over small payloads: capacity falls faster than 1/n.

**How the fragments are sent decides whether R4 holds.** In ns-3 the unit rule itself holds exactly (verified units = (1 − p)^n on the measured frame loss). What breaks is the frame loss. Fragments handed to the MAC together lose 1.7–2.3 times what (G5) gives, because fragments 2 … n always contend behind their own station's previous frame; capacity is then 35–62 % below (G18). Fragments spread over the period match (G18) within 3 %, and each unit waits (n − 1)/n of a unit period longer to verify (measured 40.0 and 53.3 ms at 12.5 units per second for n = 2 and 3). A correction for bursts, tested on new cells, removed 63–75 % of the excess but not all of it. Design rule: spread fragments, and count the wait in the freshness budget.

**R5. Best batch under bit errors.** A longer frame is lost more often to bit errors, which shrinks the budget left for collisions. When that budget falls linearly, Β(b) = Β₀ − e₁b (exact for ALOHA-type channels, with e₁ proportional to 8Ψ\_B ln(1/(1 − ε\_b))), capacity (Β₀ − e₁b)b/(Λ(Φ + Ψb)) has an interior maximum at

```latex
b_{\mathrm{opt}} = \beta\left[\sqrt{1 + \frac{\mathrm{B}_0}{e_1\,\beta}}\; - 1\right] \tag{G19}
```

and the batch to use is min{b\_D, b\_M, b\_opt}. For DCF, use Β(ε\_c(b)) with ε\_c(b) = 1 − (1 − ε)/(1 − ε\_b)^(8ℓ(b)) and search over b.

R5 applies only where loss grows with frame length. In ns-3 at 802.11a 6 Mb/s that never happens, with constant power or with Rayleigh fading drawn once per frame: a frame is either received without error or not detected, at every length from 146 to 425 B. Fading that is constant over a frame cannot create a length dependence. On the hardware the loss does grow with length (W3a, 802.11b 1 Mb/s), so a best batch there must be predicted from the measured loss against length, not from ns-3.

**R6. Duty-cycled links.** A duty cycle d requires Λ(Φ\_T/b + Ψ\_T) ≤ d, which is a lower bound on the batch, while the deadline is an upper bound:

```latex
\frac{\Lambda\,\Phi_T}{d - \Lambda\,\Psi_T} \ \le\ b \ \le\ \Lambda\,D' \qquad\Longrightarrow\qquad
D' \ \ge\ D_{\min} = \frac{\Phi_T}{d - \Lambda\,\Psi_T}, \quad \Lambda < \frac{d}{\Psi_T} \tag{G20}
```

D\_min is the smallest deadline a duty-cycled link can honour at record rate Λ, and d/Ψ\_T is the largest record rate it can carry at any deadline. Together with (M32) of the first tab (the node count on such a link is fixed by d and ε alone) this is the complete closed form for LoRa-type links.

**R7. Which resource binds.** The channel binds before the receiver processor if and only if

```latex
\frac{\mathrm{B}_X}{\Phi_X + \Psi_X\,b} < \frac{\mathrm{B}_C}{\Phi_C + \Psi_C\,b} \tag{G21}
```

Both sides fall with b at different rates, so the binding resource can change with the batch; a slow verifier (large Φ\_C) binds at small b and is relieved by batching, a slow decoder (large Ψ\_C) is not.

**R8. Freshness and verifiability at capacity.** With a key record in every frame the loss at capacity is ε, so V = 1 − ε and, by (M14) of the first tab, a peak age above the deadline occurs with probability ε raised to ⌊(D\_max − S)Λ/b⌋.

## 6. Validation against an independent event simulation

I wrote an event simulation of rule set A (Section 3.1) and compared it with the formulas. It shares nothing with ns-3 and nothing with the draft's own contention model. Settings: IEEE 802.11a constants as in Section 3.2, periodic sources with a random instant in each period, 20 s per run, 4 to 6 seeds per point, capacity read as the interpolated crossing of the loss target. The script is attached to this conversation.

**Loss by mechanism.** At 35 load points (frame airtimes 80 µs to 1.5 ms, loads a = 0.15 to 0.75) the simulated loss was split into ties, gap starts and window collisions. Each term of (G5) tracks its own component, and the total is within 6 % on average wherever the loss is at most 16 %.

**Capacity.** Error of the predicted capacity over three frame rates (5, 12.5, 50 frames/s) and three loss targets (0.02, 0.05, 0.10), 45 cases:

| Frame airtime (µs) | Simulated capacities (nodes) | Full model, root of (G5) | Two-constant law (G9) |
| --- | --- | --- | --- |
| 100 | 32 – 854 | −4.4 % to −0.4 % | +1.2 % to +17.6 % |
| 200 | 26 – 563 | −4.5 % to −1.2 % | −2.9 % to +6.7 % |
| 340 | 20 – 376 | −5.2 % to +0.8 % | −4.4 % to +4.5 % |
| 600 | 13 – 234 | −6.5 % to −2.7 % | −6.3 % to −1.7 % |
| 1200 | 8 – 126 | −8.8 % to −3.3 % | −8.7 % to −3.1 % |

The full model is conservative by 2 to 5 % in most cases. The explicit law (G9) is as good for frames of 200 µs and longer; at 100 µs and a 2 % target it overestimates, because τ₀ is then larger than the frame. The first tab's (M25) on the same cases ranged from −12 % to +20 %.

**The saturation law.** An illustrative frame (120 B fixed, 10 B per record, 64 B lower-layer overhead, 6 Mb/s, 50 records/s, ε = 0.05) gives β = 27.4 and N\_∞ = 915 from (G11) and the constants of Section 3.2:

| Batch b | Frame airtime (µs) | Simulated N\_max | (G11) | Error | Simulated gain | Γ(b) from (G12) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 284 | 33.9 | 33.2 | −1.9 % | 1.00 | 1.00 |
| 2 | 296 | 64.0 | 63.2 | −1.2 % | 1.92 | 1.93 |
| 4 | 324 | 119.5 | 117.5 | −1.7 % | 3.61 | 3.62 |
| 8 | 376 | 208.5 | 207.7 | −0.4 % | 6.31 | 6.42 |
| 16 | 484 | 348.3 | 338.3 | −2.9 % | 10.57 | 10.47 |
| 32 | 696 | 504.3 | 493.9 | −2.1 % | 15.32 | 15.30 |

The two-parameter hyperbola reproduces the simulated capacity within 3 % and the gain within 2 % from one record per frame to thirty-two.

**Sensitivity to the access rules.** The same simulator with four other readings of the standard, at two test frames (340 µs at 12.5 frames/s; 304 µs at 50 frames/s; ε = 0.05):

| Rule variant | Capacity, 340 µs | Capacity, 304 µs | Ratio |
| --- | --- | --- | --- |
| A: as in Section 3.1 | 114.9 | 32.3 | 3.56 |
| B: a frame arriving in the DIFS gap draws a backoff | 114.3 | 32.2 | 3.55 |
| C: a backoff expiry is exempt from the detection window | 119.9 | 33.6 | 3.57 |
| D: B and C together | 117.7 | 33.7 | 3.49 |
| S: an idle-medium arrival waits DIFS from its own arrival | 114.3 | 32.0 | 3.57 |

Absolute capacity moves by up to 5 % with the rule; the ratio moves by 2 %.

**Against ns-3 (IEEE 802.11a, 6 Mb/s).** After the model was fixed, I compared it with the capacity crossings stored in the project repository (`results/raw/ns3_nmax_direct.csv`, 18 configurations, 5 % loss). No constant was changed for this comparison. Frame airtimes are those of the scenario: the frame rides directly on LLC and MAC, 36 B of lower-layer overhead, so the 173 B frame is on air for 304 µs and the 146 B frame for 268 µs.

| Configuration | Frame (B) | Batch | Frames/s | Airtime (µs) | ns-3 N\_max | Law (G9) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C: lean, one record per frame | 146 | 1 | 50 | 268 | 35.3 | 34.5 | −2.2 % |
| A: first format, one record | 174 | 1 | 50 | 304 | 32.3 | 31.5 | −2.6 % |
| D: lean, batch of 4 | 173 | 4 | 12.5 | 304 | 124.5 | 122.9 | −1.4 % |
| H: lean, batch, key records | 218 | 4 | 12.5 | 364 | 108.9 | 107.0 | −1.8 % |
| B: first format, batch of 4 | 300 | 4 | 12.5 | 472 | 88.8 | 86.8 | −2.3 % |
| E: signature per record, batch of 4 | 565 | 4 | 12.5 | 828 | 56.3 | 53.8 | −4.4 % |
| RD: lean, batch of 4, 20 records/s | 173 | 4 | 5 | 304 | 307.9 | 305.6 | −0.8 % |
| SM: MAVLink-2-sized frame | 94 | 1 | 50 | 200 | 42.1 | 42.1 | 0.0 % |

Over all 18 configurations the explicit law (G9) is within 4.4 % (mean 2.0 %) and the root of (G5) within 4.9 % (mean 3.6 %), both always on the conservative side. The dependence on the loss target and on the contention window also holds, from the repository's separate runs:

| Configuration | W | Loss target | ns-3 N\_max | Law (G9) | Error |
| --- | --- | --- | --- | --- | --- |
| C | 16 | 0.02 | 22.4 | 22.5 | +0.5 % |
| C | 16 | 0.10 | 47.4 | 45.4 | −4.2 % |
| C | 32 | 0.05 | 39.2 | 38.7 | −1.3 % |
| D | 16 | 0.02 | 78.3 | 80.1 | +2.3 % |
| D | 16 | 0.10 | 166.8 | 161.6 | −3.1 % |
| D | 32 | 0.05 | 139.6 | 138.8 | −0.6 % |

So two constants computed from W, the slot, DIFS, the detection time and ε reproduce 24 ns-3 capacities to within 4.4 %, with nothing fitted to ns-3 and no root to solve.

## 7. Limits, and what to check

- **The constants belong to a rule set.** ρ\* depends only on W and ε; τ₀ also depends on how the implementation treats the DIFS gap and the detection window (rule table in Section 6, up to 5 %). I read the ns-3.48 source (`channel-access-manager.cc`, `phy-entity.cc`): for a non-QoS station a frame queued to an idle medium is sent DIFS after its arrival, which is variant S, and CCA is raised only at the end of the 4 µs preamble-detection window. Variant S and rule set A give the same capacity within 1 %, which is why (G9) matches ns-3 as it stands. For a real radio the rules must be checked again.
- **A discrepancy, resolved.** An earlier version of this tab reported my simulator 8 % below the draft's ns-3 capacities. The error was mine: I had assumed UDP and IP headers (64 B of overhead), which made both test frames 36 µs too long. The scenario sends over LLC and MAC only (36 B). With the right airtimes the gap disappears (table in Section 6).
- **Small swarms.** The model assumes Poisson starts. With periodic sources it underestimates capacity by 5–11 % at 5–11 stations and, at 802.11b, by 5–6 % up to about 40 stations. Event simulations with ns-3's periodic sources match ns-3 within 0.4 %, which places the cause in this assumption. A finite-station, periodic-source loss expression is the planned fix.
- **Short frames.** (G9) is first order in τ₀/T\_f; use the root of (G5) when the frame airtime is below about twice τ₀.
- **High loss.** The gap and window terms of (G5) are first order and overestimate above about 15 % loss, outside any useful target.
- **Hidden stations.** A share h of the stations a receiver hears but the sender does not adds an ALOHA-type term 2hνT\_f to (G5). When it dominates, the channel budget tends to ℓ\_ε/(2h) and the channel becomes airtime-limited, so byte savings regain their value. This extension is stated, not simulated.
- **Not covered.** Multi-hop relaying and a consensus layer. Capture is treated in Section 8. The security model of the first tab is unchanged.

Checks to run, in order:

- [ ] Repeat the ns-3 comparison at the other PHY rates and for 802.11p (slot 13 µs, DIFS 58 µs, 8 µs symbols); only the constants of (G6)–(G8) change.
- [ ] Fit nothing, and plot N\_max against b for the thesis configurations on the hyperbola (G11); read β and N\_∞ off the frame format.
- [ ] Verify the two regimes of (G13) by sweeping the deadline at fixed record rate.
- [ ] Test (G20) against the LoRaWAN data rates: D\_min and the largest record rate per data rate.
- [ ] Decide whether the paper states the full model (G5) or the two-constant law (G9); the law is the simpler statement and is accurate where authenticated frames live (300 µs and longer at 6 Mb/s).

## 8. Extension: capture

When frames overlap, a receiver can still decode the strongest, and the four hardware radios show that it often does. Capture enters the model as one input, q: every law in this tab holds with the loss target ε replaced by ε/(1 − q). The capture-free model of Sections 3–5 is the case q = 0, a lower bound on capacity for every geometry.

### 8.1 Loss with capture

Let q\_ij be the probability that receiver i decodes sender j's frame given that the frame collided, and ℓ\_ij the loss on that link with no other sender (noise, fading). Then

```latex
p_{ij} = p_c(\nu)\,\bigl(1 - q_{ij}\bigr) + \ell_{ij} \tag{G22}
```

where p\_c(ν) is the collision probability (G5). In the event simulation about 95 % of collided frames at capacity are in two-frame collisions, so q is close to its two-frame value.

**Correction, 21 November 2026 (finding F138).** A station that is transmitting cannot receive. In a collision of k frames, the k − 1 other transmitters are among the tagged frame's N − 1 receivers and decode nothing, so the capture probability averaged over receivers is

```latex
\bar q_{\mathrm{eff}} = \bar q\,\frac{N-k}{N-1} \;\approx\; \bar q\,\frac{N-2}{N-1} \tag{G22a}
```

and q̄\_eff replaces q̄ in (G23) and (G24). The factor is 0.99 at 140 stations, 0.89 at 10, and 2/3 at 4, the size of the hardware swarm. The first version of this section and its check script both omitted it, so their agreement could not reveal the error; ns-3 did. The script is corrected, and the table in 8.4 is recomputed with it.

### 8.2 Closed forms for q

With capture threshold θ (the signal-to-interference ratio a receiver needs), path-loss exponent α, and receiver i at distance d\_ij from the sender and d\_im from an interferer m:

| Channel | q\_ij for one interferer | Notes |
| --- | --- | --- |
| Rayleigh fading, equal mean power | 1/(1 + θ); (1 + θ)^(−(k−1)) for k overlapping frames | 0.285 at θ = 4 dB, 0.091 at θ = 10 dB |
| Rayleigh fading with path loss | E\_m \[ 1/(1 + θ (d\_ij/d\_im)^α) \] | average over interferer positions |
| No fading (line of sight, large Rician K) | P( d\_im > θ^(1/α) d\_ij ) | a step in the distance ratio |
| Rician fading | between the two rows above; Marcum Q-function | air-to-air links sit here |

θ and the rule for which frame the receiver locks onto are properties of the receiver. A receiver that cannot re-synchronise decodes only a stronger frame that arrived first; one with frame capture can switch to a later, stronger frame. Both must be read from the implementation (ns-3) or measured (hardware), not assumed.

### 8.3 Capacity with capture

Two criteria give two closed forms. For the average over senders and receivers, with q̄ and ℓ̄ the averages:

```latex
p_c(\nu^{*}) = \varepsilon' , \qquad \varepsilon' = \frac{\varepsilon - \bar\ell}{1 - \bar q} \tag{G23}
```

and (G6)–(G9) apply with ε′ in place of ε. For a ledger the stricter criterion is that every sender's records meet the target. With q\_j and ℓ\_j the averages over the receivers of sender j:

```latex
\varepsilon_{w} = \min_{j}\ \frac{\varepsilon - \ell_j}{1 - q_j} \tag{G24}
```

and the laws apply with ε\_w. Capacity under (G24) lies between the capture-free value and the average value of (G23).

**Two different every-sender statistics.** (G24) is the worst sender's long-run loss: it depends on geometry only. A deployment, or one simulation run, observes each sender over a finite window of m = f·τ frames, and the worst observed sender is worse than (G24) by the noise of a maximum over N samples. Let sender j lose each frame with probability p\_j (its long-run loss from (G22)–(G24)), and send m\_j = f·τ frames in the window. Its observed loss is p̂\_j = L\_j/m\_j with L\_j \~ Binomial(m\_j, p\_j). The window statistic, and its closed-form approximation when the p\_j are close, are

```latex
p_{\mathrm{worst}}(\tau) = \mathbb{E}\Bigl[\max_{j}\ \hat p_j\Bigr] \;\approx\; \bar p + z_N \sqrt{\frac{\bar p\,(1-\bar p)}{f\,\tau}}, \qquad z_N = \mathbb{E}\bigl[\max \text{ of } N \text{ standard normals}\bigr] \tag{G24a}
```

The left side is the definition and is what a test registers: computed exactly from the predicted p\_j as the expectation of the maximum of N independent binomial proportions (a finite sum, or a Monte Carlo of the binomials with no channel model). The right side is a closed-form approximation for senders with similar p\_j (mean p̄) and enough lost frames per window for the normal approximation (m·p̄ of about 10 or more). z\_N is the expected maximum of N standard normal draws, not its large-N asymptote √(2 ln N), which overstates it by 60 % at N = 4:

| N | 2 | 3 | 4 | 5 | 10 | 20 | 50 | 100 | 200 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| z\_N | 0.564 | 0.846 | 1.029 | 1.163 | 1.539 | 1.867 | 2.249 | 2.508 | 2.746 |
| √(2 ln N) | 1.177 | 1.482 | 1.665 | 1.794 | 2.146 | 2.448 | 2.797 | 3.035 | 3.255 |

The senders' losses are treated as independent; in fact collisions are shared, which correlates them positively and makes the maximum somewhat smaller than this. A test should state that assumption with its prediction.

Both are meaningful. (G24) is the right statistic for a sender's true verifiability, measured on ns-3 by pooling each sender's frames over all seeds and the whole run. (G24a) is what a ledger sees within one verification window, and it shrinks only as the window grows. A test must say which of the two it scores.

### 8.4 Check against the event simulation

The simulator of Section 6 was extended so that a frame in a collision of k frames is decoded at a given receiver with probability (1 + θ)^(−(k−1)) (Rayleigh, equal mean power). Capacity at ε = 0.05:

| θ (dB) | q | Frame | Simulated N\_max | Law with ε′ | Error | Capture-free law |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | 0.285 | 304 µs, 12.5 frames/s | 142.5 | 141.0 | −1.1 % | 122.9 |
| 4 | 0.285 | 268 µs, 50 frames/s | 40.8 | 39.6 | −3.1 % | 34.5 |
| 10 | 0.091 | 304 µs, 12.5 frames/s | 129.6 | 127.9 | −1.3 % | 122.9 |
| 10 | 0.091 | 268 µs, 50 frames/s | 37.0 | 35.9 | −2.9 % | 34.5 |

With (G22a) in both simulator and law the values change by at most 0.2 stations (law 140.8, 39.4, 127.8, 35.8 against simulated 142.4, 40.7, 129.5, 36.9). The law with ε′ stays conservative and within 3.1 %. Capture at 4 dB raises both capacities by about 15 %, and the ratio between the two designs stays within 2 % of its capture-free value (3.49 against 3.56).

### 8.5 How unequal capture is

Per-sender capture probability for 60 nodes uniform in a disc, every node a receiver, θ = 4 dB, interferer uniform among the other nodes (one random placement):

| Path-loss exponent | Fading | Mean q | Worst sender | 10th percentile |
| --- | --- | --- | --- | --- |
| 2 | Rayleigh | 0.349 | 0.265 | 0.293 |
| 2 | none | 0.255 | 0.137 | 0.166 |
| 3 | Rayleigh | 0.369 | 0.232 | 0.245 |
| 3 | none | 0.321 | 0.187 | 0.211 |

In a compact formation the worst sender still gains, but about half as much as the average without fading. A node far outside the formation gains little, and its link loss ℓ\_j rises at the same time, so (G24) can fall back to the capture-free bound for it. The capacity claim should therefore be stated per criterion: average delivery under (G23), every sender under (G24).

### 8.6 What still has to be measured

- **q on the hardware radios,** per sender–receiver pair, together with the threshold and the lock-on rule.
- **q in ns-3:** its receiver rule (preamble detection threshold, frame-capture model) and capacities with geometry, registered from (G23) and (G24) before the runs.
- **Worst-sender verifiability** in both, as the stricter claim.

The agent prompt for this work is `CAPTURE_PROMPT.md`.

## 9. Validation against ns-3: the scorecard

Every prediction below was registered and tagged before its runs (branch `p12-unified-model`, report `docs/revision/2026-11-18_unified_model_validation.md`). Capacity is the node count at which 95 % of frames are delivered, 30 seeds per point, tolerance ±5 %.

### 9.1 What held

| Claim | Where | Result |
| --- | --- | --- |
| Capacity law (G9) and root of (G5) | 74 stored capacities and the new runs at 802.11a | within ±5 %, almost always on the safe side (below ns-3) |
| Gain from batching (G12) | 802.11a to 64 records, 802.11b to 32 | within 1 % and 2 % of ns-3's gain |
| Key record once in r frames (G17) | r = 2, 4 at 802.11a | 4 of 4; law +0.1 %, +2.8 % |
| Fragments spread over the period (G18) | n = 2, 3 at 802.11a, new seeds | root −2.8 % |
| Best batch under bit errors (G19 region) | 802.11a 48 Mb/s, fixed power | best batch 8 records as predicted; capacity 2.0 % above prediction |
| Share of frames arriving to a busy medium | 16 loads, both PHYs | 16 of 16 |
| ns-3's access rule against the model's | 18 capacities | within 0.40 % |
| Age-of-information tail (M14) | stored traces | 8 of 8 |
| Verifiability under bursty loss (M18) | 24 ns-3 and 81 on-air traces | 105 of 105 |

### 9.2 What failed, and what it means

| Claim | Result | Side | Cause | Consequence for the model |
| --- | --- | --- | --- | --- |
| Capacity at 802.11b, 15–37 stations | 5–6 % below ns-3 (17 of 18 outside ±5 %) | safe | Poisson starts assumed; ns-3's sources are periodic | Known limit, extends further than stated. Fix: finite-station, periodic-source loss expression (open) |
| The three loss terms one by one | 17 and 18 of 48 held | none for capacity | ns-3 counts backoff slots per station, moving ties into the detection window | (G5) is valid as a total, not as a breakdown of causes (Section 3.1) |
| Fragments sent back to back (G18) | root 35 % and 62 % above ns-3 | unsafe | each later fragment always contends behind its own station's frame | Design rule: spread fragments; burst correction recovers only 63–75 % |
| Mean access delay (M16), as registered | 2 of 9 | – | registration wrote T = T\_f; the model means T = T\_f + DIFS | With the intended reading 7 of 9, but not adopted after the fact |

### 9.3 What does not apply, and what is not tested

- **Best batch under bit errors at 6 Mb/s:** does not apply in ns-3, with fixed power or per-frame fading. A frame is either error-free or not detected (findings F135, F136). The length dependence measured on hardware must come from variation within a frame.
- **Hidden stations (Section 7) and the LoRa duty-cycle law (M32):** not yet tested.
- **Capture (Section 8):** not yet tested in ns-3 or on hardware.
- **Model against ns-3 against hardware, session by session:** waits for an ns-3 configuration matched to the hardware.

### 9.4 One-line summary

The capacity laws are confirmed at 802.11a and are conservative by about 5 % at 802.11b; the batching, key-record and spread-fragment rules are confirmed; the one result on the unsafe side is fragments sent back to back, which the design now forbids.

## 10. Generalisation: how the drones' sending pattern enters the model

Both failures of Section 9 have one cause. The loss expression (G5) assumes that frame starts from the other stations form a Poisson process, the textbook assumption of CSMA and DCF analysis. Real senders are not Poisson. A telemetry timer sends on a regular clock, which is less clustered than Poisson. A unit split into fragments sent back to back is more clustered. The more clustered the starts, the more frames wait together for the channel, and the more of them collide in the same backoff slot. That is why regular sending made the model pessimistic and burst sending made it optimistic.

The sending pattern is therefore now an explicit input of the model, not a hidden assumption.

| Sending pattern | Clustering against Poisson | Effect on capacity | Treatment in the model | Status |
| --- | --- | --- | --- | --- |
| Poisson (independent random starts) | equal | reference | (G4)–(G9) as stated | validated at 802.11a |
| Periodic with random phase (telemetry timers, ns-3's source) | less | higher than Poisson | (G25) below, for about 8 or more other stations | checked against stored ns-3 runs; to be registered |
| Periodic, very few stations (2–5 radios) | much less | much higher | finite-station form, to be derived | open |
| Fragments sent back to back | more | lower | batch-arrival form, to be derived | open; design rule: pace fragments |

### 10.1 Periodic sources: the correction (G25)

For n stations each sending once per period at a random phase, served at a constant rate, the number of waiting frames is the N·D/D/1 queue of the queueing literature. A Poisson model of it overestimates the queue, especially at high load (Roberts and Virtamo, 1991). Its Brownian-bridge approximation gives the queue tail P(Q > x) ≈ exp(−2x(x/n + 1 − ρ)), whose mean has a closed form. Dividing by its Poisson limit gives a ratio R, which scales the number of co-waiting frames K̄ in (G4):

```latex
R(n,\rho) = 2(1-\rho)\,\sqrt{\frac{\pi n}{8}}\; e^{c^{2}}\,\operatorname{erfc}(c), \qquad c = (1-\rho)\sqrt{\frac{n}{2}}, \qquad
\bar K_{\mathrm{per}} = R(N-1,\ a+\gamma)\cdot \bar K \tag{G25}
```

R tends to 1 for many stations (the Poisson model is recovered) and falls as stations become fewer or load rises. Everything else in (G5) is unchanged. The event simulation confirms that periodic sending changes mainly the tie term, through K̄, and leaves the other two terms nearly as they are.

**Check against stored ns-3 capacities.** These ns-3 values were known before (G25) was written, so this table is a consistency check, not a validation. The validation must be on new cells, registered first.

| Case | ns-3 | Poisson model | Periodic model (G25) |
| --- | --- | --- | --- |
| 802.11a, 146 B at 50 frames/s | 35.26 | −4.4 % | −2.6 % |
| 802.11a, 173 B at 12.5 frames/s | 124.55 | −3.1 % | −2.5 % |
| 802.11a, 146 B, window 8 | 30.35 | −4.8 % | −3.0 % |
| 802.11a, 64 records per frame | 717.27 | −2.9 % | −2.7 % |
| 802.11b, 146 B at 50 frames/s | 9.72 | −7.9 % | +1.7 % |
| 802.11b, 173 B at 12.5 frames/s | 31.03 | −5.2 % | −0.6 % |
| 802.11b, 173 B, 2 % target | 23.09 | −5.0 % | −1.3 % |
| 802.11b, 173 B, 10 % target | 37.32 | −5.3 % | +0.5 % |
| 802.11b, 146 B, window 8 | 7.31 | −9.4 % | −1.2 % |
| 802.11b, 32 records per frame | 599.31 | −4.4 % | −4.0 % |

**Where (G25) does not hold.** The Brownian bridge is a many-station approximation. Against a queue simulation it is good for 8 or more other stations (within about 0.07 in R) but wrong for 1–4 (R of 0.30–0.75 against simulated 0.07–0.62). The hardware sessions, with 2–5 radios, need an exact finite-station form. For so few stations it can be written as a finite sum over the number of other stations whose frame lands in the same busy period (a binomial count), which reduces to (G5) as the swarm grows. That derivation is the next step.

### 10.2 Fragments sent back to back

A unit split into n fragments sent together is a batch arrival: the first fragment contends like any frame, and the next n − 1 always find the medium busy with their own station's previous fragment. The first-order correction tested in ns-3 (fragments 2 … n always deferred) removed 63–75 % of the error. The remaining part is consistent with other stations' batches raising K̄, which a batch-arrival (M^X/D/1-type) version of (G25) would capture. It is not derived yet. Until it is, the model's validity condition is stated as a design rule: fragments of a unit are paced over the period, at a verification wait of (n − 1)/n of a unit period.

### 10.3 What the model now claims

- The capacity laws hold for the sending pattern stated as their input.
- For Poisson starts they are as validated in Section 9. For periodic sources they are a lower bound, because a regular clock is less clustered than Poisson.
- (G25) narrows that bound to within a few percent for swarms of about 8 or more stations, at the occupancies its registered tests covered. At occupancy 0.84–0.87 (802.11b, cell C, with capture raising the load) it was 3.6–5.5 % optimistic (finding F140), so its stated range ends below that until it is tested there.
- Swarms of 2–5 stations and burst sending are outside the closed form until their extensions are derived and tested.
