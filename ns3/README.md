# ns3 — NS-3 3.41 validation (P6)

Validates the Bianchi airtime/throughput model against NS-3 (docs/04 §3, docs/06 §2). The
NS-3 tree is built locally and **git-ignored** (`ns3/ns-allinone-*`); only the scenario, parser,
and this README are committed. NS-3 is machine-dependent and NOT run in CI.

## ⚠️ D4 — NS-3 pinned at **3.48** (migrated from 3.41 on 2026-07-29)

Both trees may coexist; `ns3/ns3_paths.py` selects one and every driver imports it:

```bash
python ns3/run_matrix.py                                          # the pinned tree (3.48)
AUTHBC_NS3=ns3/ns-allinone-3.41/ns-3.41 python ns3/run_matrix.py  # the old tree, for comparison
```

The 3.41 tree is **kept until the migration comparison passes** — you cannot show results did not
move by deleting the simulator that produced them (`ns3/compare_versions.py`).

## ⚠️ MEMORY: build with `-j 3`, not the default

This machine is **WSL2 with ~7.8 GB RAM and 16 cores**, so ninja defaults to `-j 15`. NS-3
translation units need roughly 1–2 GB each, so the default parallelism exhausts the VM, the OOM
killer fires, and **WSL itself drops** — losing the SSH/IDE session mid-build. Symptom: the build
appears to "break" and the IDE must be restarted.

```bash
cd ns3/ns-3.48
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
nohup ./ns3 build -j 3 > /tmp/ns348_build.log 2>&1 &   # detached: survives an IDE restart
tail -f /tmp/ns348_build.log
```

Run it under `nohup` (or `tmux`): a build attached to the IDE's shell dies with the IDE.

## Build ns-3.48 (one-time, ~40–90 min at `-j 3`)
```bash
sudo apt install -y g++ cmake ninja-build python3 libgsl-dev
cd ns3 && wget https://www.nsnam.org/releases/ns-3.48.tar.bz2 && tar xf ns-3.48.tar.bz2
# LoRaWAN arm (item D2) — the module pins ns-3.48 exactly (its NS3-VERSION file):
git clone --depth 1 https://github.com/signetlabdei/lorawan.git ns-3.48/contrib/lorawan
python ../ns3/patch_lorawan.py        # REQUIRED: see below
cd ns-3.48
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja
nohup ./ns3 build -j 3 > /tmp/ns348_build.log 2>&1 &
```

### Why `patch_lorawan.py` is required
57 of the module's sources use `NS_LOG_*` and none include `ns3/log.h`; they rely on a transitive
include that our `optimized` profile (`NS3_ASSERT=OFF`, `NS3_LOG=OFF`) does not provide. Without the
patch the module fails with *"'NS_LOG_FUNCTION' was not declared in this scope"*. The script is
idempotent; re-run it after any `git pull` inside the module. We patch rather than switch profile
because the frozen 802.11 results were produced under `optimized`, and changing the profile would
confound a version migration with a build-profile change.

## Legacy: the 3.41 tree
```bash
cd ns3 && wget https://www.nsnam.org/releases/ns-allinone-3.41.tar.bz2
tar xf ns-allinone-3.41.tar.bz2 && cd ns-allinone-3.41/ns-3.41
./ns3 configure --build-profile=optimized --enable-examples -- -G Ninja && ./ns3 build -j 3
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
