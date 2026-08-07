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

---

# OUTCOME (appended after the attempt; the prediction above is unchanged)

## ⚠️ The run is not possible in this simulator, and that is the finding

`authbc-lora-capacity` aborted on its own guard, `dataRate > 5`. Investigating it produced two
results, one of them a defect in our own code.

**1. Our guard's stated reason was wrong.** It read *"DR must be 0..5 (LoRa modulation only)"*.
DR6 **is** LoRa modulation — SF7 at 250 kHz; FSK begins at DR7, exactly as `lora.py` already
documents. The bound was right, the justification was false.

**2. The real reason is a module limitation that would have produced an optimistic number.**
`EndDeviceLoraPhy::SENSITIVITY[6] = {-124,-127,-130,-133,-135,-137}` and
`GatewayLoraPhy::SENSITIVITY[6]` are indexed by **spreading factor alone — there is no bandwidth
dimension**, and `LoraInterferenceHelper` carries no bandwidth term either. The scenario also
selects a DR by writing `drDistribution.at(5 - dataRate)`, a six-slot SF12..SF7 vector that cannot
express 250 kHz at all.

Forcing SF7 onto a 250 kHz channel would therefore have produced DR6's **doubled bit rate while
silently retaining DR5's noise floor** — DR6's entire cost, the 3 dB sensitivity penalty, would have
been invisible. ⚠️ **This is precisely the C2 failure mode** (an unverified constant on the
measurement path): the run would have completed, looked clean, and been repeatable across all 30
seeds. No amount of seeding detects it.

## What replaces the run: a closed form, validated against the DR5 simulation

At a fixed duty cycle $d$, the transmissions falling in one $2T_{\text{air}}$ vulnerability window
number $N \cdot 2T_{\text{air}}/T_{\text{period}} = 2Nd$ — **the airtime cancels**. So
$P(\text{deliver}) = e^{-2(N-1)d}$ is *rate-independent*, and DR6 must have the same $N_{\max}$.

Checked against the measured DR5 run ($d = 0.9864\%$ after jitter):

| $N$ | closed form | DR5 measured | diff |
|---|---|---|---|
| 2 | 0.9805 | 0.97166 | +0.0088 |
| 3 | 0.9613 | 0.95981 | +0.0015 |
| 5 | 0.9241 | 0.91670 | +0.0074 |
| 8 | 0.8710 | 0.87103 | −0.0000 |
| 10 | 0.8373 | 0.82919 | +0.0081 |

Max deviation 0.9 pp, and the closed form returns $N_{\max}=3$, matching the simulation.

## Verdict against the prediction

| predicted | outcome |
|---|---|
| $b=6$, ToA ≈0.50×, period ≈18.1 s | **Confirmed** by the driver's own computation before the abort: `b=6, ToA=181.9 ms, duty interval=18.2 s` |
| per-node ≈0.33 rec/s, aggregate ≈0.99 rec/s | **Derived**, not simulated |
| $N_{\max}$ unchanged at 3 | **Derived and supported** by a closed form validated against DR5 — but ⚠️ **not verified by simulation**, and the paper says so |
| range 1.41× shorter | Unchanged: analytical throughout, as the prediction already stated |

⚠️ **The prediction is not claimed as confirmed.** It is claimed as derived from a model checked
against the neighbouring data rate. That is weaker than a measurement and is labelled as such.
