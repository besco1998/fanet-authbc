# DR6 capacity — prediction, written and committed BEFORE the run

*2026-08-07. Committed data-free, as its own commit, so the ordering is checkable in git history —
the same discipline used for the E5 success criterion (`3354ec1`) and the Direction C protocol
(`eb3eda5`). ⚠️ Finding F40 forced a pre-registration claim to be withdrawn once because the
expectations file had never been committed. This is that commit.*

## Why this run exists

Klimiashvili et al. (ICNC 2020) evaluate LoRa at **DR6**; we simulated only **DR5** and never said
why. Our own T6 table admits DR4, DR5 and DR6 equally (all N=242 B, residual 134 B), and DR6 carries
**2.01× the bit rate** (11 000 vs 5 470 bps). A reader holding their paper will ask why we chose the
slower setting. Mohamed's decision: measure it rather than argue it.

## The prediction

| quantity | DR5 (measured) | DR6 predicted | reasoning |
|---|---|---|---|
| batch $b$ | 6 | **6** | payload N=242 B is identical; $b$ is set by payload, not rate |
| time on air | — | **≈0.50×** | 250 kHz vs 125 kHz at the same SF7 |
| app period at 1 % duty | 36.378 s | **≈18.1 s** | duty cycle fixes occupancy, so the period scales with airtime |
| per-node rate | 0.165 rec/s | **≈0.33 rec/s** | $b$ / period |
| **$N_{\max}$ at $V\geq0.95$** | 3 | **3 (UNCHANGED)** | see below |
| aggregate | 0.495 rec/s | **≈0.99 rec/s** | from the rate alone, not from more nodes |
| range | reference | **1.41× shorter** | 3 dB sensitivity cost (−123 vs −120 dBm), $n=2$ |

### ⚠️ The load-bearing prediction: $N_{\max}$ does not move

At a **fixed 1 % duty cycle every node occupies 1 % of the channel regardless of data rate**, so the
offered load is $G = 0.01N$ in both cases. Pure ALOHA collision probability depends only on $G$.
Halving the airtime halves the vulnerability window *and* doubles the transmission frequency, and
these cancel **exactly**. So DR6 should buy throughput and buy **no extra nodes**.

**If $N_{\max}$ moves, the prediction is wrong and something in the model is load-bearing that I do
not currently understand.** In that case: do not average it away — reproduce, hypothesise, and
report the mechanism (Law 6). A change in $N_{\max}$ would specifically implicate the module's
interference/capture handling at 250 kHz, since the duty-cycle argument above is rate-independent.

### What this run cannot show

Nothing about range. The 3 dB sensitivity cost is a link-budget fact, not a capacity one, and the
simulation is run on the same ideal channel as DR5. The range claim stays analytical.
