# The unified closed-form capacity model — specification under test

*Received from Mohamed on 2026-11-17, with the task "validate the unified closed-form capacity
model in ns-3, audit the ns-3 arm, and add an 802.11b arm" (plan: approved the same day). This file
keeps Section 4 of that task word for word, so that code and tests can cite it. The reference
implementation is Mohamed's `analysis/closed_form_model.py`; the repository's implementation is
`src/authbc/models/unified_capacity.py`. Nothing in either is fitted to ns-3.*

## 4. The model under test

One collision domain, N stations, each offering f = Λ/b frames per second (Λ records per second,
b records per frame). Broadcast: no acknowledgement, no retransmission, constant window W.
ν = (N − 1)·f is the rate at which the other stations start frames. T_f is the frame's time on
air **without** DIFS. δ is the time during which a start cannot be sensed (ns-3: 4 µs).
σ is the slot. ε is the loss target; κ = 1 − ε/2.

**Loss (G4, G5).** With a = ν(T_f − δ)(1 − p/2), γ = ν·DIFS, η = ν·σ·(W − 1)/2:

    K = a(1 + γ + 2η) / (1 − γ − a)
    p = a·K/(W + K)  +  γ(2a/W + γ)  +  2δν(1 + a)
        [same-slot tie]  [zero-backoff start after a busy period]  [detection window]

p appears on both sides through a; solve by fixed-point iteration, or set p = ε inside a when
solving for capacity.

**Two-constant law (G6–G9).** With D0 = W − (W − 1)ρ* and s = σ(W − 1)/2:

    ρ*    = [ −ε(W − 1) + sqrt( ε²(W − 1)² + 4εW ) ] / 2
    p0'   = [ 2ρ*·D0 + (W − 1)ρ*² ] / D0²
    c_eff = ρ*²·W·[ (DIFS + 2s)(1 − ρ*) + DIFS ] / D0²  +  2ρ*·DIFS/W  +  2δ(1 + ρ*)
    τ0    = c_eff / p0'
    N_max = 1 + ρ* / ( f · [ κ(T_f − δ) + τ0 ] )

**Design law (G10–G13).** Frame airtime is affine in the batch, T_f(b) = Φ_T + Ψ_T·b. With
Β = ρ*/κ and τ̂ = τ0/κ − δ:

    N_max(b) − 1 = Β·b / ( Λ·(Φ_T + τ̂ + Ψ_T·b) ) = N_inf · b/(b + β)
    N_inf = Β/(Λ·Ψ_T),   β = (Φ_T + τ̂)/Ψ_T,   gain Γ(b) = b(1 + β)/(b + β) < min(b, 1 + β)

**Design rules to test.**
- Key record once in r frames: the per-frame loss target tightens to ε_r, the root of
  (1 − p)(1 − (1 − p)^r)/(r·p) = 1 − ε. Capacity at 95 % verified records is then N_max(ε_r)
  with the mean airtime of the key and dependent frames.
- A signed unit split over n frames: ε_n = 1 − (1 − ε)^(1/n), frame rate n·f.
- Duty-cycled ALOHA (LoRa) at the duty-cycle limit: N_max = 1 + floor( C·ln(1/(1 − ε)) / (2d) )
  for C channels and duty cycle d, independent of frame length, batch and data rate.

**Access rule the loss expression was derived for ("rule A").** A frame that finds the medium
idle for DIFS is sent at once; one that arrives in the DIFS after a busy period is sent at its
end with no backoff; one that arrives to a busy medium draws a uniform backoff in 0 … W − 1.
ns-3.48 does something slightly different (Section 6, item 1). Rule A and that rule gave the
same capacity within 1 % in an independent event simulation; confirm or refute this in ns-3.

**Known limits, stated by the model's author.** Poisson starts are assumed, so capacity is
underestimated by 7–9 % for swarms of about 8–14 stations. The two-constant law is first order
in τ0/T_f and overestimates when T_f is below about 2τ0 (802.11a at 24 Mb/s); the root of the
loss expression should be used there.

**Test vectors** (IEEE 802.11a: σ = 9 µs, DIFS = 34 µs, W = 16, δ = 4 µs). Your implementation
must reproduce these to the digits shown before anything else is run.

| Quantity | Value |
| --- | --- |
| ρ*, τ0 at ε = 0.02 | 0.43523, 143.27 µs |
| ρ*, τ0 at ε = 0.05 | 0.59486, 98.04 µs |
| ρ*, τ0 at ε = 0.10 | 0.72054, 73.89 µs |
| p at ν = 1425 /s, T_f = 304 µs | 0.04497 |
| p at ν = 1700 /s, T_f = 268 µs | 0.05439 |
| N_max, f = 12.5, T_f = 304 µs, ε = 0.05: law / root of p = ε | 122.85 / 120.64 |
| N_max, f = 50, T_f = 268 µs, ε = 0.05: law / root | 34.47 / 33.71 |

IEEE 802.11b (σ = 20 µs, DIFS = 50 µs, W = 32, δ = 4 µs; T_f = 192 µs + 8(ℓ + 36)/R, long preamble):

| Quantity | Value |
| --- | --- |
| ρ*, τ0 at ε = 0.02 / 0.05 / 0.10 | 0.54796, 254.94 µs / 0.70845, 186.04 µs / 0.81696, 140.79 µs |
| N_max, 146 B at 50 frames/s, 1 Mb/s (T_f = 1648 µs): law / root | 8.92 / 8.95 |
| N_max, 173 B at 12.5 frames/s, 1 Mb/s (T_f = 1864 µs): law / root | 29.34 / 29.43 |

Frame airtimes in this repository carry 36 B of lower-layer overhead (LLC 8, MAC header 24,
FCS 4): the scenario uses a packet socket, not UDP/IP. Verify this rather than trust it.
