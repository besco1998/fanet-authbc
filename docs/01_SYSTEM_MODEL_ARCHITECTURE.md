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

**Traffic.** Records are generated at rate Λ_i per UAV (default 20 rec/s, payload =
telemetry tuple: position, velocity, battery, mode). Aggregate neighborhood arrival Λ.

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
  48 B signature. Required only when forwarding others' records or combining attestations.
- **D. Block-level aggregate:** one signature over b records spanning n>1 frames.
  All-or-nothing under loss (T3 shows when it's dominated).

**Signature schemes σ:** ECDSA-P256 (64 B, legacy baseline), Ed25519 (64 B, fast),
BLS12-381 min-sig (48 B, aggregatable; AugScheme for distinct messages — doc 06 §5).

**Encodings e:** JSON (stdlib, Pillar-1 baseline), CBOR canonical (RFC 8949 §4.2),
MessagePack, delta-CBOR (canonical delta vs previous record with periodic keyframes;
keyframe interval fixed K=16 in this arm — optimizing K is the doc-30/LoRa question).

## 2. Notation (single source of truth — use everywhere, incl. code comments)
| Symbol | Meaning | Default |
|---|---|---|
| s | encoded record payload bytes | measured (E1) |
| g | signature bytes (scheme σ) | 64 / 64 / 48 |
| H_f | ledger frame header bytes | 40 |
| M | application MTU budget | 1500 |
| b | records per frame (batch) | decision var |
| p | frame loss probability | {.02,.05,.10} |
| Λ | record arrival rate (rec/s) | 20·N_local |
| R | PHY data rate | 6 Mb/s |
| T_fx | fixed MAC/PHY airtime per frame | ≈123 µs (doc 02 §6) |
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
├── ns3/                       # authbc-sat.cc scenario, run_matrix.sh, parse_flowmon.py
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
