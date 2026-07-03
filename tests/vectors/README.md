# tests/vectors — vendored known-answer test (KAT) vectors

Cryptographic KATs are vendored here **with their source URLs** (docs/06 §4) so the crypto
suite is reproducible offline and its provenance is auditable. KATs are a release gate and
must pass before any timing exists (docs/03 §3).

These are **crypto** KATs added in P1. **Wire-format** vectors (canonical CBOR frames) are a
separate artifact frozen at **P2** under ⚠️ D6 — do not confuse the two.

| File | Source (URL) | Used by | Covers |
|---|---|---|---|
| `rfc8032.txt` | https://www.rfc-editor.org/rfc/rfc8032.txt | `test_ed25519.py` | RFC 8032 §7.1 Ed25519 — 5 deterministic **sign+verify** vectors (msg 0/1/2/1023/64 B) |
| `wycheproof_ed25519.json` | https://raw.githubusercontent.com/google/wycheproof/master/testvectors_v1/ed25519_test.json | `test_ed25519.py` | Ed25519 **verify** vectors incl. edge/negative cases |
| `wycheproof_ecdsa_secp256r1_sha256.json` | https://raw.githubusercontent.com/google/wycheproof/master/testvectors_v1/ecdsa_secp256r1_sha256_test.json | `test_ecdsa_p256.py` | ECDSA P-256/SHA-256 **SigVer** (484 cases: 174 valid, 310 invalid) |
| `chia_bls_test.cpp` | https://raw.githubusercontent.com/Chia-Network/bls-signatures/main/src/test.cpp | `test_bls.py` | BLS AugScheme "aggregate of aggregates" (known aggregate-sig hex) + IETF/Pyecc BasicScheme sign vector |

Retrieved 2026-07-03. To refresh, re-download from the URLs above and re-run `make test`;
any KAT change is a scientific event — investigate before accepting (Law 3/6).
