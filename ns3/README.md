# ns3 — NS-3 3.41 validation (P6)

Validates the Bianchi airtime/throughput model against NS-3 (docs/04 §3, docs/06 §2). The
NS-3 tree is built locally and **git-ignored** (`ns3/ns-allinone-*`); only the scenario, parser,
and this README are committed. NS-3 is machine-dependent and NOT run in CI.

## ⚠️ D4 — NS-3 version pinned at **3.41** (from source, optimized).

## Build (one-time, ~15–40 min)
```bash
sudo apt install -y g++ cmake ninja-build python3 libgsl-dev      # deps
cd ns3 && wget https://www.nsnam.org/releases/ns-allinone-3.41.tar.bz2
tar xf ns-allinone-3.41.tar.bz2 && cd ns-allinone-3.41/ns-3.41
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
./ns3 build
./ns3 run hello-simulator        # GATE: runs (exit 0)
```
**Gate note**: `hello-simulator` prints via `NS_LOG_UNCOND`, which the **optimized** profile
(`NS3_LOG=OFF`) compiles out — so it runs silently (exit 0 = gate passed). The scenario below
uses `std::ofstream`/FlowMonitor (not NS_LOG), so its output is unaffected by the profile.

**P6a smoke (2 nodes, frameSize=200, 5 s, seed=1)** — `results/raw/ns3_smoke.csv`:
unicast goodput 3.27 Mb/s (FlowMonitor 3.39), broadcast 3.71 Mb/s. Both ≤ 6 Mb/s PHY ceiling
and > 0 (saturation reached); broadcast > unicast (no ACK/SIFS) — consistent with the P3 airtime.
Recorded build: NS-3 **3.41**, profile **optimized** (release, native opt on, asserts/log off),
generator **Ninja**, g++ 13.3, cmake 3.28, ninja 1.11, libgsl 2.7.

## Scenario `authbc-sat.cc`
802.11a ad-hoc · `ConstantRateWifiManager` @ `OfdmRate6Mbps` · RTS/CTS off · N saturated senders
(OnOff at an offered load ≫ capacity). Params: `--mode={unicast,broadcast}`, `--nNodes`,
`--frameSize` (app payload; real sizes from `results/raw/framesizes.csv` at P6b), `--simTime`,
`--seed`, `--outPrefix`.

### THE ACK TRAP (docs/06 §2 — do NOT mix)
802.11 **broadcast has no ACK/SIFS/retry/RTS-CTS**; classic Bianchi assumes **unicast with ACKs**.
So each NS-3 mode is compared ONLY to its matching analytic variant (`authbc.channel.airtime`):
- `--mode=unicast` ↔ ACK-Bianchi (`airtime_unicast`, T_s with ACK/SIFS);
- `--mode=broadcast` ↔ no-ACK variant (`airtime_broadcast`).
Legit gap sources to enumerate + quantify at P6b (never silently correct): EIFS, capture effect,
retry/CW-reset, propagation-delay defaults.

## Run
`make sim-ns3` → builds the scenario + runs a 2-node both-modes smoke → `ns3/parse_ns3.py`
(FlowMonitor XML for unicast, PacketSink goodput for both) → `results/raw/ns3_smoke.csv`. The
full N∈{5,10,20,35,50} × 10-seed × both-modes matrix + Bianchi gap analysis + E5 export is **P6b**
(blocked on the P5a `bianchi.py` merge).
