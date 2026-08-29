# The AUTHBC story — a plain-language account

*Written 2026-08-30 at Mohamed's request: "a document that describes what we did in detail with
simple language and terms for me to understand." Readable rendering published as an artifact; **this
file is canonical**. Every number here comes from a committed artifact and is guarded by a test that
fails if it drifts.*

---

## 1. The problem, in one sentence

**The signature is bigger than the thing it signs.**

That is the whole thesis. Everything else is working out what follows.

The setup: a swarm of drones, each broadcasting what it is doing — position, speed, battery, mode —
perhaps fifty times a second. That stream must be *tamper-evident*: nobody should be able to forge,
replay or quietly alter a message undetected.

The standard tool is a digital signature: sign with your private key, anyone verifies with your
public key. At normal security strength that signature is **64 bytes**. A drone telemetry message,
written naively as JSON, is about 191 bytes. Compressed properly it is about **45 bytes**.

> A 64-byte signature on a 45-byte message. **59 % of what goes on the air is cryptography, not
> data.**

## 2. Why "compress harder" makes it worse

Earlier work compressed the payload — that is where 191 → 45 came from. The natural next thought is
to keep going. But watch the proportion:

| encoding | message | signature | share that is crypto |
|---|---|---|---|
| JSON (naive) | 191 B | 64 B | 25 % |
| CBOR (compressed) | 66 B | 64 B | 49 % |
| delta-CBOR (best) | 45 B | 64 B | **59 %** |

Every byte shaved off the message makes cryptography a *larger* share. The signature cannot shrink
— its size is fixed by the security level.

> **Compression does not solve the problem. Compression is what creates it.**

## 3. The four things we can change

Not the signature size — that would weaken security. So:

1. **Encoding** — how the message is written down. Already optimised by prior work.
2. **Placement** — *where* the signature sits. You need not sign each message separately: put four
   in one radio frame and sign the frame **once**.
3. **Scheme** — which algorithm, hence which size and speed.
4. **Batch size** — how many messages share one signature.

## 4. The two walls

Batching is the big lever. Sign 100 messages at once and the signature costs 0.64 B each. Two walls
stop you, and **which one you hit first matters enormously**.

- **Frame size.** A Wi-Fi frame holds ~1500 B; at 45 B per message that is ~30 messages.
- **Freshness.** Waiting to fill a batch makes the first message stale. 3GPP TS 22.125 requires
  drone-to-drone messages within **100 ms**. At 50 msg/s that allows only **5**.

**On Wi-Fi the freshness wall always binds first.** This kills an appealing argument: that on a
small-frame link every payload byte saved saves *more* than one byte on air, because it fits another
message in the frame. That multiplier is real — *but only where frame size is the binding wall*. On
Wi-Fi compression pays exactly **1×**.

On long-range LoRa, where a frame holds ~242 B, the frame-size wall *does* bind and the multiplier
is real. **The two link types are not fast and slow versions of each other. They are different
problems.**

## 5. What we built

No new cryptography — deliberately. We built a way to *measure* the design space honestly: all four
encodings, three schemes, four placements; a model of Wi-Fi under contention; a simulator to check
that model; two Raspberry Pis with real radios to check the simulator; an exhaustive search over all
1,536 combinations; and **an automated gate** that recomputes every published number from raw data
on every run and fails the build if any has drifted.

That last item is why the rest of this document can be honest about mistakes — we could find them.

## 6. The results

**Fewer bytes.** Best configuration: delta encoding, Ed25519, self-batching, 4 per frame — **72 B
per record** against 174 (compression-only) and 299 (naive). A **58.7 % reduction**.

⚠️ The tempting number is different: *"75 % fewer authentication bytes."* True, and we banned
ourselves from saying it. That 75 % is exactly `1 − 1/b` for batch size `b`. At b=4 it is 75 %,
independent of encoding, scheme, header — everything we designed. **It is the definition of
batching, not a finding.**

**More drones.** Joining the byte model to the channel model:

| configuration | max drones (conservative) | max drones (realistic) |
|---|---|---|
| compression-only baseline | 18 | 31 |
| **our co-design** | **35** | **100** |

Roughly **1.9×–3.2×** the swarm on the same channel. We report the range, never a single number.

**The result that cannot be argued with.** On long-range LoRa the slowest settings allow a
**51-byte** payload:

```
signature = 64 bytes
payload   = 51 bytes
--------------------------
64 > 51  →  it does not fit
```

Not inefficient — **impossible**. No encoding, no batch size, no header design. Even with a
zero-byte header and a one-byte message.

> Every performance number can drift, and four of ours did. **Arithmetic does not.** That is why the
> thesis was reorganised around this.

## 7. How we thought — the reframe

The project began as an *optimisation*: tune four axes together, beat tuning them separately.
Partway through we ran a **factorial ablation** — turning each axis on and off to test whether they
genuinely interact.

Mostly they do not. Placement and batching interact exactly, by a one-line formula. **Encoding is
perfectly separable** — every interaction term is exactly zero. The scheme axis is byte-neutral.

We had claimed "a smaller payload increases the value of batching." That was a **ratio illusion**:
the percentage grows because the denominator shrinks, but the absolute saving is 81 B for every
encoding.

**So we reframed the thesis around our own negative result.** As an optimisation paper this work is
mid-tier. As a *feasibility boundary* the same evidence is stronger, because a boundary cannot be
beaten by a better scheme next year.

## 8. The mistakes, and why they are in the thesis

Ten results moved after first being recorded. The *pattern* is more useful than any single number.

- **Four numbers wrong from too few samples.** Three runs averaged near a threshold can land on the
  wrong side by luck. One capacity figure was 5; at 30 runs it is **3**.
- **A theorem withdrawn the day it was written.** We claimed the channel excludes configurations
  past a load. The test — which we ran *after* publishing the claim into our own documentation —
  showed 98.8 % of messages still arriving there.
- **A perfectly repeatable, completely wrong measurement.** A hardware test gave a clean 97.45 %,
  consistent across runs. We were measuring the radio *saturating*, not the channel losing packets.
  Caught only because we wrote down our expectation first.
  ⚠️ **Repeatability did not protect us.** A precisely reproducible measurement of the wrong thing
  looks exactly like a good measurement.
- **A test that asserted a bug.** A function returned zero where it should not, and a unit test
  asserted it should. **A green suite means the code does what the tests say, not that the tests say
  the right thing.**

## 9. The uncomfortable one — four became three

We said **four** of seven LoRa settings cannot carry authenticated telemetry. Three fail on the
signature alone. The fourth, DR3, has 115 B of payload and missed by **six bytes**.

Then: *six bytes short of what, exactly?*

```
115 (payload) − 44 (our header) − 64 (signature) = 7 B left
smallest message we can make                     = 13 B
→ excluded, by six bytes
```

That 44-byte header is **ours** — and we had written down months earlier that it was inefficient:
**29 of the 44 bytes are field *names* spelled out as text** (`"src"`, `"base_seq"`, `"recs"`,
`"auth"`). Replacing text names with small numbers — completely standard — takes the header to
**22 bytes**.

```
115 − 22 − 64 = 29 B left    vs 13 needed
→ DR3 fits. It was excluded by our file format, not by physics.
```

⚠️ **Two facts, each recorded, never composed.** The system-model document said the header was
inefficient. The theory document said the boundary depends on the header. Nobody read them in the
same sitting. **This is the third time in the project a wrong claim survived that way.**

**Why this made the work better.** It is honest — the four-rate claim was one reviewer's question
away from being wrong. What remains is bulletproof. And the boundary became **constructive**: it now
says not just "you cannot do this here" but "*here is exactly what would have to change*" — and for
DR3 the answer is a better header, not better cryptography.

## 10. Decisions, and why

| decision | why | what it cost |
|---|---|---|
| Report total bytes, never the 75 % | 75 % is `1−1/b`, an identity | the most quotable number |
| Adopt 50 Hz / 100 ms | a real autopilot mode *and* standards-compliant | ~2× swarm size, zero bytes |
| Report both capacity thresholds | they answer different questions | two numbers to explain |
| Keep the frozen file format | every result rests on it | we report a boundary we could move ourselves |
| Keep header at 44 B in the model | realistic steady-state value | it is also the value most favourable to our claim — stated openly |
| Stop at 46 references | 46 is every source actually **read** | below the usual count |
| Pessimistic freshness formula | a latency bound should be an upper bound | we under-report our own saving by ~3 points |

## 11. If you remember five things

1. After compression the signature is bigger than the message — authentication, not data, is the
   cost.
2. Batching fixes most of it: 58.7 % fewer bytes, 1.9–3.2× more drones.
3. On long-range LoRa three settings cannot carry authenticated telemetry at all. Arithmetic.
4. A fourth *looked* excluded but was blocked by our own file format. We found it and said so.
5. We invented no cryptography. The contribution is knowing exactly where the existing tools work,
   where they do not, and how confident to be about each.

---

*Companions: `docs/HONEST_ASSESSMENT.md` (what the work is really worth) · `thesis/` (formal
treatment; see `thesis/STATUS.md`) · `docs/audits/model_provenance.md` (findings F1–F44).*
