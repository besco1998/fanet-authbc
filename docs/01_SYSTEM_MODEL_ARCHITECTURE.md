# 01 — SYSTEM MODEL AND ARCHITECTURE

## 1. System model

**Network.** N UAVs share an 802.11 broadcast channel (OFDM, base rate R = 6 Mb/s for
robustness; MTU application budget M = 1500 B). Frames are lost i.i.d. with probability p
(channel abstraction of fading/collisions/mobility; p ∈ {0.02, 0.05, 0.10} in experiments).
Contention is modeled by Bianchi DCF (doc 02 §6) and validated in NS-3 (E5). No GCS.

**Ledger.** Each UAV i maintains an append-only hash chain of its own telemetry records
and stores verified records overheard from others. A record is
`rec = {src, seq, ts, prev_hash, payload}`; `prev_hash = SHA-256(prev record bytes)`.
Only the owner appends to chain i (owned-object model); tampering or equivocation on
(src,seq) is detectable by chain verification. Finality/witnessing semantics are OUT of
scope for this arm (no consensus); the deliverable is authenticated dissemination.

**Traffic.** Records are generated at rate **Λ_i per UAV** (payload = telemetry tuple: position,
velocity, battery, mode). **Aggregate neighbourhood arrival Λ = Λ_i·N_local** — the rate a
*receiver* must verify. ⚠️ These are different quantities and must not be interchanged: a node
batches its OWN records (freshness uses Λ_i) but verifies EVERYONE's (verify-throughput uses Λ).
Conflating them was audit finding **F12**.

**Λ_i = 50 rec/s and D_max = 100 ms — ADOPTED 2026-07-30 (B3 resolved by Mohamed: report the
region, adopt the compliant point). Sources VERIFIED at source (2026-07-29, item A4).**
An AUTHBC record maps onto MAVLink `GLOBAL_POSITION_INT` plus part of `SYS_STATUS`. The rates below
were read from the autopilot source, not from secondary summaries:

| link class | position stream | source |
|---|---|---|
| ArduPilot **Copter/Heli/Blimp** default | **0 Hz** — GCS requests on demand | `GCS_MAVLink_Parameters.cpp`, `default_rates[]` |
| ArduPilot Plane / Rover default | 1 Hz | ″ |
| ArduPilot Sub default | 3 Hz | ″ |
| PX4 `MAVLINK_MODE_NORMAL` (telemetry radio) | 5 Hz | `mavlink_main.cpp`, `configure_streams_to_default` |
| PX4 `MAVLINK_MODE_OSD` / `CONFIG` | 10 Hz | ″ |
| **PX4 `MAVLINK_MODE_ONBOARD`** (companion computer) | **50 Hz** | ″ |
| PX4 `LOW_BANDWIDTH` | 2 Hz | ″ |

⚠️ **Correction to the previous version of this table.** It listed "ArduPilot default 1 Hz" without
qualification. ArduPilot's default is **vehicle-specific**, and for multirotors — the typical FANET
node — the default is **0 Hz**: streams are requested by the GCS rather than pushed. The 1 Hz figure
is the Plane/Rover default only.

**The independent standards anchor.** 3GPP TS 22.125 §5.2.2 specifies the *direct UAV-to-UAV local
broadcast* service — which is precisely this system, not a cellular uplink:

* **R-5.2.2-010:** "at least **10 messages per second**"
* **R-5.2.2-011:** "end-to-end latency of at most **100 ms**"
* **R-5.2.2-008:** "variable message payloads of **50–1500 bytes, not including security-related
  message component(s)**" ← the standard itself accounts for authentication bytes *separately from*
  payload, which is exactly the φ metric this thesis optimises.
* R-5.2.2-009: range up to 600 m; R-5.2.2-007: relative speeds to 320 km/h.

**B3 RESOLVED (2026-07-30).** The adopted point is **Λ_i = 50 rec/s, D_max = 100 ms** — PX4's
`MAVLINK_MODE_ONBOARD` companion rate, and **fully compliant** with TS 22.125 (≥10 msg/s and
≤100 ms). The previous (20 Hz, 250 ms) point is retained as a reported alternative, not as the
headline.

**Why the switch is free in bytes.** Batching obeys **b ≤ Λ_i·D_max**, so only the *product*
matters. Both points give Λ·D = 5 ⇒ **b = 4 ⇒ 72.0 B/record ⇒ −58.68 %**. Identical.

**What it costs, stated because this is an optimization problem:**

| | Λ | D_max | b | B/rec | N_max (U<1) | N_max (V≥0.95) | compliant |
|---|---|---|---|---|---|---|---|
| **ADOPTED** | 50 | 100 ms | 4 | **72.0** | 35 | **100** | ✅ |
| alternative | 20 | 250 ms | 4 | **72.0** | 103 | 213 | ❌ exceeds 100 ms |
| — | 20 | 100 ms | 1 | 153.0 | 34 | — | ✅ but no batching |
| — | 10 | 100 ms | 1 | 153.0 | 78 | — | ✅ but no batching |

Compliance costs **~2× swarm size** (213 → 100 at the V≥0.95 boundary; 103 → 35 at saturation) and
**nothing in bytes**.

> ⚠️ *Corrected 2026-08-27.* This table read 233/116 until today — the pre-F30 crossing. The paper was
> corrected on 2026-08-07; this document was not, because every staleness guard parses `paper/main.tex`
> only. Current values are `results/raw/capacity_envelope.csv`, columns `n_max_v95_mean`.

⚠️ **The region has a floor, and it is a real constraint on the application.** Holding b ≥ 4 under a
100 ms deadline needs **Λ ≥ 40 Hz**. At 20 or 10 Hz the same deadline forces b = 1 and the saving
collapses from 58.7 % to **12.2 %**. So the batching benefit is *not* available at every compliant
operating point — it requires a telemetry rate fast enough to fill a batch inside the deadline.
See docs/02 §6b, `TRADEOFFS.md` §1 and `results/raw/operating_region.csv` for the full surface.

**Structural coupling:** any batching at all needs `b/Λ_i ≤ D_max` with b ≥ 1, hence
**Λ_i ≥ 1/D_max**. At D_max = 250 ms that means Λ_i ≥ 4 rec/s; at the 3GPP 100 ms bound it means
Λ_i ≥ 10 rec/s — exactly the standard's own minimum message rate. **At an ArduPilot Copter default
of 0 Hz or a 1 Hz SiK link, no batching is possible at all** and this thesis's mechanism does not
apply.

**N_local = 50 neighbours (item B2).** Not an assumption to be justified in isolation — it is
*reported as a curve*. The largest single collision domain each configuration can carry at
Λ_i = 20 rec/s, D_max = 250 ms (802.11a, 6 Mb/s, U < 1) is **N ≤ 25** for A+JSON, **N ≤ 32** for the
A+CBOR Pillar-1 baseline and **N ≤ 103** for the co-designed configuration. N = 50 is quoted because
it lies *between* those: a swarm the baselines cannot serve and the co-design can. See docs/02 §6b.

**Security model.** Adversary may inject, replay, modify, or forge frames but does not
hold any honest UAV's private key (key compromise out of scope, per charter). Required:
existential unforgeability (EUF-CMA schemes at 128-bit level), replay rejection (src,seq
monotonic per chain), integrity (hash chain). Availability under loss is a *robustness*
metric, not a security claim.

**Threat model, stated in full (2026-10-06; the paragraph above is the summary it expands).**
*What is claimed, and where each property is enforced* (`ledger/store.py`, `placement/session_v2.py`):

| property | meaning | mechanism | where it is checked |
|---|---|---|---|
| origin authentication | a stored record was produced by the UAV named in `src` | public-key signature over the canonical records | `verify_v2`, before anything is stored |
| integrity | no field of a stored record was altered in transit | the same signature (every one of 1328 single-bit flips of a frame fails it) | ″ |
| replay rejection | a frame delivered twice is stored once | `seq` strictly increasing per sender | `Store.ingest` → `REPLAY` |
| equivocation evidence | two validly signed records for one `(src, seq)` are kept as a pair | both carry the sender's signature, so the pair is transferable proof | `Store.ingest` → `EQUIVOCATION` |
| continuity | omission or re-ordering inside what is held is detectable | each record's `prev_hash`; one link per frame commits to the record before it | `Store.ingest` → `TAMPERED` when the predecessor is held |
| non-repudiation | a sender cannot later deny a record | follows from a public-key signature; a symmetric tag would not give it | — |

*The adversary* controls the radio: it can read, inject, replay, modify, delay and drop frames,
and may run any number of its own radios. It holds no honest UAV's private key.

*What is NOT claimed* — each of these is outside the design, not an oversight in it:

* **Confidentiality.** Telemetry is broadcast in clear.
* **Availability.** Jamming removes frames; nothing here recovers them (no retransmission, no
  coding across frames). Loss is the *robustness* metric V, not a security property. A flood of
  forged frames costs a receiver one verification each — bounded by the CPU budget of docs/02
  §6c, not prevented.
* **Timeliness against a delaying attacker.** Replay is rejected by sequence number, not by
  time. An attacker who keeps a frame from a receiver and delivers it later gets it accepted, as
  authentic and in order, however stale. Rejecting that needs a clock shared with the sender,
  which is not assumed. The record's signed `ts` lets an application apply its own bound.
* **Truthfulness.** A UAV holding a valid key can sign false telemetry. Only *inconsistent*
  falsehood — two records for one sequence number — is detectable.
* **Key distribution, revocation and admission.** Receivers are assumed to hold each sender's
  public key. The on-air cost of delivering certificates is charged separately (docs/02 §6d);
  who may join, and how a key is withdrawn, is out of scope, and so is Sybil resistance.
* **Privacy.** Senders are identified by a stable `src`. Pseudonymous schemes (the certificateless
  aggregate signatures of the vehicular literature) buy conditional privacy that this design
  does not offer.

*Behaviour under loss, which the properties above depend on.* Every frame of the design decodes
alone (docs/02 T3′), so a lost frame costs its own records and nothing else. The receiver then
holds a chain with a gap: the next frame's link commits to a record it does not have, which it
records and cannot check. Continuity across the gap is therefore *provable later*, if the missing
records are ever obtained, and *unknown until then* — not violated, and not verified.

*What one link per frame gives up.* In the first format every record carries its own
`prev_hash`; in the lean format (§4b) only the first record of a frame does, and the rest are
derived by the receiver. Within a frame, order and content then rest on the frame signature
alone rather than on a signature and an independent hash. A frame is signed as a unit and is
accepted or refused as a unit, so nothing is lost in strength — but there is one mechanism where
there were two (docs/02 §9b).

**Authentication placements (the decision space)** — audit-corrected:
- **A. Inline per-record:** every record carries its own signature g. Baseline.
- **B. Self-batch (one signer):** a UAV packs b of its OWN records in one frame and signs
  the frame once (any scheme; Ed25519 default). Per-record auth bytes = (g+H_f)/b.
  Self-contained ⇒ loss-local.
- **C. Cross-signer aggregate (relay/attestation):** a frame carries b records from
  DIFFERENT originators, each originally signed; BLS aggregates the b signatures into one
  96 B signature (see below). Required only when forwarding others' records or combining attestations.
- **D. Block-level aggregate:** one signature over b records spanning n>1 frames.
  All-or-nothing under loss (T3 shows when it's dominated).

**Signature schemes σ:** ECDSA-P256 (64 B, legacy baseline), Ed25519 (64 B, fast),
BLS12-381 (aggregatable; AugScheme for distinct messages — doc 06 §5). ⚠️ **96 B, not the 48 B
min-sig this doc originally specified**: blspy ships only the min-pubkey Chia scheme (pk 48 B in G1,
sig 96 B in G2). Accepted and applied everywhere — see DECISIONS.md.

**Encodings e:** JSON (stdlib, Pillar-1 baseline), CBOR canonical (RFC 8949 §4.2),
MessagePack, delta-CBOR (canonical delta vs previous record with periodic keyframes;
keyframe interval fixed K=16 in this arm — optimizing K is the doc-30/LoRa question).

## 2a. H_f = 44 B — MEASURED from the implemented wire format (B1, 2026-07-29)
`H_f` feeds T2, T2a, T6, `b_max`, the channel-utilisation constraint and the energy model. It was
previously an **undocumented assumption of 40 B**. It is now measured directly from
`placement/wire.py` — the canonical-CBOR frame that this project actually serialises — by encoding
real frames and subtracting the record and authentication bytes:

        H_f = len(encode_frame(F)) − Σ len(record canonical bytes) − len(auth)

**Result: H_f = 44 B** for placement B at every batch 1 ≤ b ≤ 23, stepping to 46 B at b ≥ 24 where
the CBOR array-length and byte-string-length prefixes widen.

> ⚠️ **H_f is a RANGE, 38–44 B — added 2026-08-28.** It is constant in b (below 24). It is **not**
> constant in the magnitudes of `src` and `base_seq`, because canonical CBOR encodes an integer
> 0–23 in one byte and one ≥ 65536 in five. Measured with `framer.measure_frame_header_bytes`:
>
> | src | base_seq | H_f | state |
> |---|---|---|---|
> | 0 | 0 | **38 B** | first 24 records of a flight, low node id |
> | 24 | 24 | 39 B | — |
> | 256 | 256 | 40 B | — |
> | 40 000 | 180 000 | **44 B** | 1 h into flight at 50 Hz — the value above |
>
> ⚠️ **And the direction of bias is opposite for T6.** The table below analyses H_f's bias for the
> *byte comparison*, where 44 B is conservative. T6's bound is `s_max = M − H_f − g_a`, so a
> **larger H_f makes exclusion MORE likely** — 44 B is the top of the range and therefore the value
> most favourable to the paper's most durable claim. DR3 is excluded for H_f ≥ 39 and **feasible at
> H_f ≤ 38**, at which point the headline is *three* of seven EU868 rates, not four. DR0–DR2 are
> unconditional at any header size (64 B will not fit 51 B). See docs/02 T6 and
> `tests/test_math_audit.py::TestFrameHeaderIsARange`. The empty frame skeleton alone is
43 B; most of it is CBOR *text* keys (`v`, `t`, `src`, `base_seq`, `n`, `recs`, `auth`), which an
integer-keyed profile would shrink substantially — that is a wire-format optimisation this thesis
does not claim.

**The model uses a single H_f, but the real value is placement-dependent.** Measured:

| placement | H_f measured | note |
|---|---|---|
| **B** (self-batch — *the optimized configuration*) | **44 B** (46 at b ≥ 24) | the adopted model constant |
| A (inline) | 45 B at b=1, 51 B at b=4 | grows ≈2 B per record: each of the b signatures carries its own CBOR byte-string header |
| D (block) | 81 B | the auth block adds `block_id` / `frag_idx` / `frag_total` keys and names |

**Direction of the remaining bias, stated rather than hidden.** Using 44 B everywhere
(i) matches the optimized configuration exactly; (ii) understates the A baseline by 1 B at b=1
(45 measured), which makes the reported improvement *slightly conservative*; and (iii) understates
placement D by 37 B, which is **conservative in the direction that matters** — D is already
rejected on verifiability (T3), and a truer D would look worse still, not better.

**What changed when 40 → 44 was adopted** (no verdict moved):

| quantity | at H_f=40 | at H_f=44 |
|---|---|---|
| auth-byte cut | 75.00 % | **75.00 %** — invariant, H_f cancels (F13) |
| T6 exclusion tiers | DR0–2 signature, DR3 encoding | **identical**; DR3's headroom tightens 11 B → 7 B |
| T2a binding ceiling | freshness binds | **freshness binds** |
| `b_max` at MTU 1500 (delta) | 31 | 30 |
| total bytes/record cut | 58.30 % | **58.68 %** |

*Closes open item B1.*

## 2. Notation (single source of truth — use everywhere, incl. code comments)
| Symbol | Meaning | Default |
|---|---|---|
| s | encoded record payload bytes | measured (E1) |
| g | signature bytes (scheme σ) | 64 / 64 / **96** (BLS: blspy AugScheme G2 — DECISIONS) |
| H_f | ledger frame header bytes | **44 — measured** from `wire.py` (§2a) |
| M | application MTU budget | 1500 |
| b | records per frame (batch) | decision var |
| p | frame loss probability | {.02,.05,.10} |
| Λ_i | per-UAV record rate (rec/s) | 20 (PX4 companion-class, docs/01 §1) |
| Λ | **aggregate** arrival a receiver verifies (rec/s) | Λ_i·N_local = 20·50 |
| N_local | neighbours in the collision domain | 50 |
| U | channel utilisation, offered/deliverable frames | ≤1 required |
| R | PHY data rate | 6 Mb/s |
| ~~T_fx~~ | ~~fixed MAC/PHY airtime per frame~~ | **REMOVED by D9** — airtime is an OFDM-symbol *step* function, not affine; use `bianchi.ofdm_ppdu` (docs/02 §6) |
| t_enc,t_dec | encode/decode time per record | measured |
| t_sg,t_vf | sign / verify time | measured |
| t_ag,t_av(b) | aggregate / aggregate-verify time | measured |
| P_c,P_r | CPU / radio active power (W) | measured (P7) |
| V | P(record verifiable at receiver) | constraint ≥1−ε |

## 3. Software architecture (repo `fanet-authbc`)
```
fanet-authbc/
├── CLAUDE.md                  # agent policy (from this package)
├── Makefile                   # setup|lint|test|bench-micro|bench-macro|exp-*|sim-ns3|figures
├── pyproject.toml             # pinned deps (doc 03 §2)
├── src/authbc/
│   ├── encodings/             # json_enc.py cbor_enc.py msgpack_enc.py delta_enc.py (common ABC)
│   ├── crypto/                # ecdsa_p256.py ed25519.py bls.py  (sign/verify/agg APIs + KATs)
│   ├── ledger/                # record.py chain.py store.py verify.py (replay+equivocation checks)
│   ├── placement/             # inline.py self_batch.py relay_agg.py block_agg.py (Framer ABC)
│   ├── channel/               # emulator.py airtime.py  (broadcast, MTU, Bernoulli loss, 802.11 timing)
│   ├── models/                # bianchi.py energy.py optimizer.py  (doc 02 formulas)
│   └── bench/                 # timers.py micro.py macro.py stats.py (bootstrap CIs)
├── experiments/               # e1..e5/config.yaml + runner.py  → results/raw/*.csv (committed)
├── analysis/                  # figures.py tables.py (reads only results/raw)
├── ns3/                       # authbc-sat.cc + authbc-dcf-trace.cc, run_matrix.py, parse_ns3.py
├── tests/                     # unit/ property/ integration/ (mirrors src layout)
├── results/{raw,figures}/     # raw CSVs committed; figures regenerable via make figures
└── paper/                     # IEEEtran skeleton (P8)
```
**Data flow:** generator → encoding → placement framer → channel emulator (airtime+loss)
→ deframer → crypto verify → ledger store → metrics collector → CSV. Every experiment is
a YAML config + seed; every CSV row carries the full config hash for provenance.

## 4. Wire format (canonical CBOR; freeze in P2, version field mandatory)
```
Frame  := {v:1, t:PLACEMENT_ID, src:u16, base_seq:u32, n:u8,
           recs:[RecordBody×n], auth:AuthBlock}
Record := {src:u16, seq:u32, ts:u32(ms), ph:bytes32, pl:map}   # pl = telemetry map
AuthBlock:
  A: per-record sigs [bytes×n]      B: one sig bytes over canonical(recs)
  C: agg_sig bytes48 + signer list   D: sig + block_id/frag_idx/frag_total
```
Canonicalization rule: CBOR canonical form; signature input = canonical bytes of the
covered region; test vectors frozen in `tests/vectors/` at P2 (⚠️ D6 applies after).

## 4b. Wire format v2 — the lean frame (2026-10-06, audit F45)

*Implemented: `placement/wire_v2.py` (format), `placement/session_v2.py` (sender, receiver).
Additive: §4 above is frozen and untouched, and every artifact derived from it is bit-identical.*

Until this format existed, the design the results headline was a sum of sizes measured in
three places; no frame carrying delta records had been encoded or decoded (F45). v2 is that
design as one object, and every size reported for it is the length of an emitted frame.

```
Frame := canonical CBOR map, INTEGER keys (the COSE / SenML convention)
  0 v         2
  1 t         0 inline (one signature per record) · 1 self-batch, decodes alone ·
              2 self-batch, first record coded against the previous frame's last
  2 src       u16
  3 base_seq  u32 — sequence number of the first record
  4 n         1..255 records
  5 link      bytes(32) — prev_hash of the first record: the ONE chain link a frame carries
  6 recs      bytes — the record stream
  7 auth      self-batch: bytes(64) · inline: array of n × bytes(64)

Record stream := nine LEB128 varints per record: ts, lat, lon, alt, vel_x, vel_y, vel_z,
  battery, mode. A KEY record carries absolute values; a DELTA record, zig-zag differences
  from the record before it. `src` and `seq` are not repeated: seq_i = base_seq + i.
```

**What is signed is unchanged from §4:** the canonical CBOR of the ledger records, each with its
own `prev_hash` (`prev_hash_0 = link`, `prev_hash_i = SHA-256(canonical(rec_{i−1}))`). A receiver
must therefore *rebuild* the records before it can verify them — which is the point: a frame it
cannot decode is a frame it cannot verify, and docs/02 T3′ counts that.

Bytes, field by field, at the documented flight point (sender 40 000, one hour at 50 Hz;
`results/raw/frame_components.csv`, rows `header_field`):

| field | first format (§4) | lean (§4b) | why it differs |
|---|---|---|---|
| map header | 1 | 1 | |
| `v` | 3 | 2 | key name: 1 B of text against a 1 B integer |
| `t` | 3 | 2 | ″ |
| `src` | 7 | 4 | `"src"` is 4 B as a key |
| `base_seq` | 14 | 6 | `"base_seq"` is 9 B as a key |
| `n` | 3 | 2 | |
| `recs` | 6 | 3 | key name; an array header against a byte-string prefix |
| `auth` | 7 | 3 | key name |
| **H_f** | **44** (38–44) | **23** (17–23) | key names are 29 B of the first header and 7 B of the lean one |
| chain link | 32 **per record**, inside it | 35 **per frame** (32 + key + prefix) | §9b of docs/02 |
| record that decodes alone | 59.85 (56–61), link included | 24.0 (21–25) | no key names, no `src`/`seq`, varints |
| record coded against its predecessor, 50 ms apart | 44.0, link included | 9.0 | ″ |

**Decision recorded (D2 of the 2026-10 revision, `DECISIONS.md`).** The lean format carries one
chain link per frame on **both** arms. That extends to 802.11 what the decision of 2026-07-28
scoped to LoRa only — *for the lean format*; the first format keeps a link in every record. The
cost is stated under "What one link per frame gives up" in §1.

## 5. Measured-parameters table (what/where/how — methodology in doc 04 §1)
| Param | Platform(s) | Method |
|---|---|---|
| s per encoding (incl. delta mean/max) | x86 | encode 10k telemetry samples, report mean±CI, max |
| t_enc,t_dec | x86 → RPi4 | perf_counter_ns, ≥10k iters, GC off, warmup 1k |
| t_sg,t_vf,t_ag,t_av(b) per σ | x86 → RPi4 | same harness; b∈{2,4,8,16,32}; KATs must pass first |
| T_fx and airtime(s) | analytic + NS-3 | constants doc 02 §6; validated E5 |
| V(placement,b,p), goodput | emulator | ≥30 seeded runs/config, bootstrap 95% CI |
| Saturation throughput vs N | Bianchi + NS-3 | N∈{5,10,20,35,50}; E5 |
| P_c,P_r, energy/record | RPi4 (P7) | external meter protocol, doc 04 §4 |
