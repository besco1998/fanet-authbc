# P6 — NS-3 VALIDATION + E5  (COPY-PASTE WHOLE FILE)  — LANE 3 (build early; validate at SYNC-3)
Needs P0 (P6a); p5a-done + p3-done (P6b) · ends: tags p6a-done, p6-done · Eight Laws · PLAN MODE.

IF PARALLEL: Lane-3 worktree if 3-lane chosen; else the integrator runs it after P4/P5. You OWN
ONLY: ns3/**, results/raw/ns3*, analysis/figures_ns3.py. Re-read the repo CLAUDE.md.
⚠️ Read docs/06 §2 IN FULL before touching NS-3 — the broadcast/ACK subtlety below is a
scientific-integrity trap.

CONTEXT BUDGET — read exactly: docs/06 §2 (NS-3 build + no-ACK broadcast issue) · docs/04 §3
(scenario + campaign) · docs/02 §6 (the Bianchi variant to compare against) · docs/01 §1
(traffic). Nothing else.

OBJECTIVE: validate the Bianchi airtime/throughput model against NS-3, and run the end-to-end
E5 comparison of optimizer configs vs baselines.

KEY FACTS INLINED:
- NS-3 version 3.41, built from source (⚠️ D4 if it must change). Build:
  `sudo apt install g++ cmake ninja-build python3 libgsl-dev`; download ns-allinone-3.41;
  `./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja`; `./ns3 build`
  (15–40 min first time); GATE on `./ns3 run hello-simulator` before proceeding.
- THE TRAP: 802.11 BROADCAST has NO ACKs, NO retransmission, NO RTS/CTS. Classic Bianchi
  saturation throughput ASSUMES unicast with ACKs. So you MUST run BOTH: (a) saturated
  UNICAST matched to classic Bianchi (with ACK/SIFS in T_s), and (b) BROADCAST with the no-ACK
  Bianchi variant (T_air = T_phy+8(L+34)/R+DIFS+δ, no ACK, no retries). Compare each NS-3 mode
  to its MATCHING analytic variant. Mixing a broadcast NS-3 run against ACK-Bianchi is the #1
  way to fabricate a fake "model gap" — forbidden.
- Legit Bianchi-vs-NS-3 gap sources to enumerate & QUANTIFY (never silently correct): EIFS
  after errored frames, capture effect, retry/CW-reset details, propagation-delay defaults.
- Campaign: N∈{5,10,20,35,50} × 10 seeds × both modes; 30 s runs. Frame sizes come from
  results/raw/framesizes.csv (real framer output from P3, imported at SYNC-3); until then use
  spec-level sizes. Runtime budget: full matrix < 2 h on WSL.

P6a STEPS (environment — mostly unattended; do EARLY, right after P0 if possible):
1. Build NS-3 3.41 per the inlined steps; gate on hello-simulator; record build flags/version
   in docs/status.
2. ns3/authbc-sat.cc skeleton: 802.11a ad-hoc, ConstantRateWifiManager OfdmRate6Mbps, RTS/CTS
   off, N senders, frame sizes read from a CSV PARAMETER; implement BOTH modes (a) and (b).
3. Wire `make sim-ns3`; a 2-node smoke run parses to CSV via a COMMITTED parse script (never
   hand-copy numbers). Tag `p6a-done`; push.

P6b STEPS (at SYNC-3):
4. Rebase to obtain results/raw/framesizes.csv; feed real sizes in.
5. Run the matrix (both modes); parse FlowMonitor (unicast) / PHY-RX-OK traces (broadcast)→CSV.
6. RESULTS VALIDATION (Law 6, §Validate-Results) — do this BEFORE writing any "gap" narrative:
   state the EXPECTED relationship (NS-3 unicast throughput should track ACK-Bianchi within a
   modest, EXPLAINABLE gap; broadcast should track the no-ACK variant); check saturation was
   actually reached (offered load ≫ capacity); throughput ≤ 6 Mb/s PHY ceiling; each NS-3 mode
   compared ONLY to its matching analytic variant. If the gap is large or wrong-signed:
   reproduce minimally, list candidate causes from the inlined set, quantify each — do NOT add
   a silent correction factor and do NOT widen a tolerance. If still ambiguous, raise to
   Mohamed. Write into audits/p6.md.
7. Comparison figure + written gap analysis (quantified causes, no hidden corrections). Export
   NS-3-informed contention (effective airtime share vs N) for the integrator's E5.
8. AUDIT P6b (§Audit): saturation reached? correct Bianchi variant per mode? seed handling in
   NS-3? runtime < 2 h? Fix → `make all` → tag `p6-done` → push → §Handoff.

ACCEPTANCE: NS-3 builds reproducibly via `make sim-ns3` · BOTH modes run · matrix < 2 h · gap
analysis with quantified causes and NO hidden corrections · results-validation in audits/p6.md ·
E5 contention export committed · tags pushed.
