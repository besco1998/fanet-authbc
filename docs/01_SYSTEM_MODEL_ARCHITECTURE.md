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

**Λ_i = 20 rec/s — sourced, not assumed (2026-07-28).** An AUTHBC record maps onto MAVLink
`GLOBAL_POSITION_INT` plus part of `SYS_STATUS`. Autopilot stream rates for exactly that content:

| link class | position stream | source |
|---|---|---|
| ArduPilot default, 57k SiK radio | 1 Hz | `GCS_MAVLink_Parameters.cpp` |
| PX4 `MAVLINK_MODE_NORMAL` (telemetry radio) | 5 Hz | `mavlink_main.cpp` |
| PX4 `MAVLINK_MODE_OSD` / `CONFIG` (USB) | 10 Hz | ″ |
| **PX4 `MAVLINK_MODE_ONBOARD`** (companion computer) | **50 Hz** | ″ |

802.11 is a **companion-computer-class link**, so 20 Hz sits between the OSD and ONBOARD rates —
not an inflated figure. It is *also* the ≤50 % channel-utilisation limit at N_local=50
(`results/raw/capacity_envelope.csv`), so the pair **(N_local=50, Λ_i=20)** is the stated
operating point rather than two independent defaults.

**Structural coupling:** any batching at all needs `b/Λ_i ≤ D_max` with b ≥ 1, hence
**Λ_i ≥ 1/D_max**. At D_max = 250 ms that means Λ_i ≥ 4 rec/s — the co-design result depends on
being on a fast link, and at a 1 Hz SiK rate no batching is possible at all.

**Security model.** Adversary may inject, replay, modify, or forge frames but does not
hold any honest UAV's private key (key compromise out of scope, per charter). Required:
existential unforgeability (EUF-CMA schemes at 128-bit level), replay rejection (src,seq
monotonic per chain), integrity (hash chain). Availability under loss is a *robustness*
metric, not a security claim.

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

## 2a. ⚠️ H_f = 40 B is a modelling assumption (added 2026-07-28, pre-P8 audit)
`H_f` appears in T2, T2a, T6, `b_max`, every byte-accounting formula and the channel-utilisation
constraint, but **it was never derived and is not measured**. It is an indicative budget for a
ledger frame header — version + flags, source node id, frame sequence, timestamp, batch count,
payload length, and the first chain link's context — and no wire-format implementation pins it.

**Stated plainly:** it is an assumption, and the thesis must say so rather than let a bare table
default read as a measurement. Two things bound the damage:

* **The auth-byte headline is invariant to it.** The cut is 1 − 1/b (audit F13); H_f cancels
  identically. Substituting H_f ∈ {20, 40, 80, 200} B changes the headline by **0.0000 %**.
* **It does bias:** T6's exclusion tiers (a leaner header moves DR3 from excluded to feasible),
  `b_max` under an MTU, total bytes/record, and therefore channel utilisation and energy.

**Open action for P8:** either derive H_f from an implemented wire format (`placement/wire.py`
already serialises frames — measure it) or report T6 and the byte tables against a *range* of H_f.
Tracked in the open-items list.

## 2. Notation (single source of truth — use everywhere, incl. code comments)
| Symbol | Meaning | Default |
|---|---|---|
| s | encoded record payload bytes | measured (E1) |
| g | signature bytes (scheme σ) | 64 / 64 / **96** (BLS: blspy AugScheme G2 — DECISIONS) |
| H_f | ledger frame header bytes | 40 — ⚠️ **modelling assumption, not measured** (see §2a) |
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
