# P7b hardware setup & configuration — start-to-finish runbook

Follow this top-to-bottom to take a bare board to "ready to run the P7b campaign" (micro timings +
INA219 energy + 2-node 802.11 link), then feed the measured numbers back into the E4/E5 model.
Companion to `hw/provision.sh`, `hw/run_micro.sh`, `hw/energy_protocol.md`, and docs/DECISIONS.md
(⚠️ D5 = the meter). Nothing here runs until you have the boards + meter in hand.

---
## 0. Plan: which board does what
Your inventory ≠ the docs' "4× RPi4" assumption, so the campaign is tiered (docs/DECISIONS.md, D5):

| tier | boards | role | notes |
|---|---|---|---|
| **Primary (headline)** | 2× **RPi4 B** | micro timing + energy tables; 2-node Wi-Fi link | matches the thesis "RPi4"; do these first |
| **Secondary (bonus)** | 2× **RPi3 B / B+** | cross-platform timing/energy points | A53 64-bit; weaker cooling; B is 2.4 GHz-only |
| **Stretch (optional)** | 2× **BeagleBone Black** | single-core Cortex-A8 timing points | 32-bit, no Wi-Fi, **BLS may not build** — see §9 |

**Minimum to complete P7b:** the 2× RPi4 (one is the DUT for timing/energy, both form the link).
RPi3/BBB only add generalization breadth.

### Shopping / bench checklist
- Per board: a **quality 5.1 V supply** (RPi4: official 5.1 V/3 A USB-C; RPi3: 5.1 V/2.5 A micro-USB).
  A weak supply causes under-voltage throttling that silently corrupts timing **and** energy.
- **Cooling** for RPi4 & RPi3: heatsink **+ fan** (Argon case / official fan). A 60 s crypto loop
  heats the SoC; throttling invalidates the run.
- microSD ≥ 16 GB (A1/A2) per Pi; an SD card reader.
- **INA219 breakout** (your SparkFun one) + Dupont jumpers. **Check its shunt resistor** — the value
  printed on the board (`R100` = 0.1 Ω, `R010` = 0.01 Ω) sets range/resolution/burden (§6).
- A **known resistive load** for meter calibration (a USB constant-current dummy load, or a measured
  ~10 Ω / ≥5 W power resistor).
- The **meter-host**: a 2nd Pi or a laptop that reads the INA219 over I²C (keeps logging off the DUT).
- (Optional, BBB link) a USB Wi-Fi dongle.

---
## 1. Flash the OS
### RPi4 & RPi3 → Raspberry Pi OS **Bookworm 64-bit *Lite***
Lite = no desktop (a desktop adds idle-power noise and background CPU). 64-bit: RPi4 and RPi3 B/B+
are all ARMv8.

#### ⚠️ Imager shows "Trixie" (newest) and "Bookworm (legacy)" — use **Bookworm**
"Legacy" in Imager means *previous stable*, **not** unsupported: Bookworm is Debian 12, security-
supported well past this thesis's timeline. Choose it because:
1. **Interpreter must stay constant.** The x86 baseline was measured on **Python 3.12.3** (see the
   `# python=` header in every frozen CSV). Trixie (Debian 13) ships a newer Python. If the Pi runs a
   different interpreter, the x86↔ARM timing ratio confounds *platform* with *Python version* — and
   the P7 protocol is explicit that "only the platform changes". We therefore pin **Python 3.12 via
   pyenv on either OS** (§4); Bookworm simply makes that the obvious path.
2. **Toolchain risk.** `blspy` is the fragile dependency (no guaranteed wheels for the newest CPython;
   source builds need cmake+gmp). Building it for 3.12 is the known-good path; a newer interpreter
   invites a packaging fight instead of measurements.
3. **These scripts are written and reasoned against Bookworm** (`provision.sh`, package names,
   `/boot/firmware` paths).

*If you prefer Trixie anyway:* it will most likely work, but still install **pyenv 3.12** (do **not**
use the system Python), and re-verify `provision.sh`'s governor/`raspi-config` steps — they are
untested there. Whichever you pick, **record it** in `results/hw/meta/` (provision.sh does this
automatically) so the thesis states the exact platform.

1. Install **Raspberry Pi Imager** on your laptop.
2. Choose device → OS: *Raspberry Pi OS (other)* → **Raspberry Pi OS Lite (64-bit)**.
3. **⚙ / Ctrl-Shift-X (advanced options)** before writing — set:
   - hostname: `authbc-pi4a`, `authbc-pi4b`, `authbc-pi3a`, `authbc-pi3b` (one per board);
   - **enable SSH** (password or, better, your public key);
   - username + password;
   - **Wi-Fi** SSID + password + **country code** (needed to unlock the radio);
   - locale / timezone.
4. Write to the microSD. Repeat per board with its own hostname.

### BeagleBone Black → see §9 (different toolchain; do it last, if at all).

---
## 2. First boot + headless SSH
1. Insert the SD, connect the **official/quality supply**, power on. First boot resizes the FS + reboots (~2 min).
2. From your laptop: `ssh <user>@authbc-pi4a.local` (mDNS). If `.local` fails, find the IP on your
   router or `ping authbc-pi4a.local`.
3. Update once: `sudo apt-get update && sudo apt-get -y full-upgrade && sudo reboot`.

---
## 3. Provision (governor, deps, radio hygiene, cooling)
```bash
ssh <user>@authbc-pi4a.local
git clone <your-repo-url> ~/fanet-authbc && cd ~/fanet-authbc
sudo ./hw/provision.sh
```
`hw/provision.sh` (idempotent; refuses to run on a non-Pi so it can't touch your dev box) does:
- installs build deps (build-essential, cpufrequtils, and the libs to compile CPython 3.12);
- sets the CPU governor to **performance** and **verifies** it (aborts if it didn't take — a
  silently-ignored governor invalidates every timing);
- disables **Wi-Fi power-save** on `wlan0` (power-save duty-cycles the NIC and skews airtime);
- sets **headless** boot (console, no desktop) and enables **NTP**;
- snapshots `lscpu` / temp / `get_throttled` / governor to `results/hw/meta/`.

**Cooling check now:** attach the heatsink + fan before any timed run. Confirm idle temp is sane:
`vcgencmd measure_temp` (aim < 55 °C idle) and `vcgencmd get_throttled` → `throttled=0x0`.

---
## 4. Python 3.12 + repo environment
Bookworm ships Python 3.11; the repo pins ≥ 3.12, so build 3.12 with pyenv (provision.sh already
installed the build deps):
```bash
curl -fsSL https://pyenv.run | bash
# add the 3 lines pyenv prints to ~/.bashrc, then: exec $SHELL
pyenv install 3.12          # ~15-20 min on RPi4, ~30-40 min on RPi3 (single-threaded compile)
pyenv local 3.12            # pins 3.12 for this repo dir
make setup PYTHON="$(pyenv which python)"   # venv + pinned deps (cryptography, blspy, cbor2, msgpack…)
```
If `blspy` has no aarch64 wheel and builds from source, it needs cmake + gmp (already pulled by the
build deps); the build is slow but works on 64-bit Pi. Verify the env:
```bash
make test        # fast suite should pass on-device (proves crypto/encoders/KATs work here)
```

---
## 5. Micro timing run (P1 suite on hardware)
```bash
./hw/run_micro.sh --check      # sanity: venv python + micro suite import + paths
./hw/run_micro.sh              # the real run
```
This reruns the exact P1 micro suite and writes `results/hw/p1_{sizes,crypto}.<host>.csv` with the
**real** governor/temp/`get_throttled` folded into the header; it backs up + restores the committed
x86 CSVs (never clobbers them) and **flags** any throttled run with a `.THROTTLED` filename.

**Sanity gates (docs/04 §1, expect RPi4 ≈ 5–15× the x86 numbers):**
- Ed25519 sign ≈ 0.1–0.9 ms, verify ≈ 0.3–1.4 ms; BLS verify ≈ 5–45 ms.
- `verify ≥ sign` per scheme; BLS-verify ≫ Ed25519-verify still holds on ARM.
- **Watch F6:** on ARM, Ed25519 may now beat ECDSA (the x86 OpenSSL-asm edge is gone) — if so, the
  E5 scheme pick flips ECDSA→Ed25519 (both 64 B, identical % cut). That is a *finding*, record it.
- If any op is far outside the band, STOP and check the governor / throttling before recording.

Repeat §3–§5 on the second RPi4 and (bonus) the RPi3s.

---
## 6. INA219 energy rig (⚠️ D5)
Goal: measure whole-board power so `energy/op = (P_loop − P_idle)·t_loop/n_ops` (hw/energy_protocol.md).

### 6.1 ✅ DECIDED: Path A — Arduino meter-host
**`hw/RIG.md` is the authoritative rig document.** Two INA219s (0x40 / 0x41) are read by an
**Arduino**, so the benchmarked Pi spends **zero CPU** on logging and both link nodes are measured on
one timebase. Three programs:

| where | program | job |
|---|---|---|
| Arduino | `hw/arduino/ina219_logger/` | sample both sensors at 50 Hz, tag each with the sync line, stream CSV |
| DUT Pi | `hw/energy_loop.py` | run each op in a timed window, **drive GPIO17 in-process**, emit a manifest |
| this WSL2 box | `hw/ina219_capture.py` | capture the stream; `--reduce` → energy/op + CI |

The INA219's SDA/SCL go to the **Arduino**, so nothing is installed on the Pi for sensing (only
`gpiod` for the sync line). `hw/INA219_wiring.md` documents the older **Path B** (Pi reads its own
sensor via `hw/ina219_smoke.py`) — kept **only** as a bring-up fallback; the two are alternative
wirings, never both at once.

**Feed the DUT through the shunt** (identical in both paths), one of two ways:
- *cut USB cable:* open a USB-A→C (RPi4) / →micro (RPi3) cable, route the **red 5 V** wire through the
  INA219 shunt (PSU side → Vin+, Pi side → Vin−); leave GND/data intact. Keeps the Pi's input fuse.
- *GPIO 5 V feed:* bench supply into **GPIO pin 2 (5 V)** and **pin 6 (GND)** via the shunt. Bypasses
  the Pi's input protection — use a clean current-limited supply and double-check polarity.

### 6.2 ⚠️ Three caveats (from the D5 assessment)
1. **Shunt burden voltage.** 0.1 Ω × 1.4 A ≈ 0.14 V drop (≈ 0.2 V at 2 A peaks). RPi4 throttles if
   its rail sags below ~4.7 V. **Mitigate:** feed **5.15–5.2 V**, keep peripherals off the DUT, and
   **watch `get_throttled`** every run — non-zero invalidates it. (Lower-shunt boards trade burden
   for resolution; an INA260 with a 2 mΩ integrated shunt removes this entirely if you hit trouble.)
2. **Don't let the logger load the DUT** — Path A removes this by construction; Path B minimizes it
   with `taskset` core-pinning.
3. **Calibrate first** (§6.4).

### 6.3 Host software
**Path A (Arduino):** install the *Adafruit INA219* library via Library Manager, flash
`hw/arduino/ina219_logger/ina219_logger.ino`, read the serial port at 115200 baud. Nothing is
installed on the Pi for sensing; the Pi only needs `gpiod` for the sync line (`sudo apt-get install -y
gpiod`). See `hw/RIG.md` §5–§6.

**Path B (Pi) only:**
```bash
sudo raspi-config nonint do_i2c 0        # enable I2C (or dtparam=i2c_arm=on in /boot/firmware/config.txt)
sudo apt-get install -y i2c-tools python3-smbus
i2cdetect -y 1                            # expect a device at 0x40 (and 0x41 with 2 sensors)
.venv/bin/pip install pi-ina219           # into the repo venv: PEP 668 blocks system pip on
                                          # Bookworm AND Trixie (see hw/INA219_wiring.md §6)
```

### 6.4 Calibrate against a known load (before touching the Pi)
1. Put the INA219 inline with your **known resistive load** (not the DUT).
2. Read V and I; compute expected `P = V²/R`. `offset% = 100·(P_meter − P_expected)/P_expected`.
3. **If |offset%| > 2 %, stop** and re-seat/re-cable before measuring. Record the offset in the run header.
4. Set the INA219 calibration for your actual shunt + expected max current:
   `Current_LSB = Max_Expected_A / 2^15`, `Cal = trunc(0.04096 / (Current_LSB × R_shunt))`.

### 6.5 Run the energy protocol
`hw/energy_loop.py` implements the protocol and is **already written** — it runs each op for a
wall-clock window under the **P1 timing rules** (perf_counter_ns, GC off, ≥1000 warmup, checksum,
fixed 200 B seeded input) and **drives GPIO17 itself** around every window, so there is nothing to
time by hand. Per op it alternates a 60 s **idle** and a 60 s **load** window, ≥5 reps, and records
temp/`get_throttled` before and after each window.

```bash
# 1) HERE (WSL2) — start the capture FIRST and leave it running (see hw/RIG.md §6 for usbipd):
./hw/ina219_capture.py --port /dev/ttyACM0

# 2) ON THE DUT PI:
sudo apt-get install -y gpiod        # sync-line access (nothing else is needed for sensing)
./hw/energy_loop.py --quick          # 5 s x2 reps: proves sync + sensors end-to-end
./hw/energy_loop.py                  # full campaign

# 3) HERE — Ctrl-C the capture, then reduce:
./hw/ina219_capture.py --reduce results/hw/energy/manifest-*.json \
                                results/hw/energy/samples-*.csv
```
Reduction yields `energy/op = (P_loop − P_idle)·t_loop/n_ops`, median + bootstrap CI over reps, and
`ΔP` → `p_cpu_w`. Get `p_radio_w` from the saturated receive loop of §7 (channel 2 = the RX Pi:
`--channel 2`). Op set: sign/verify per scheme; BLS aggregate/agg_verify(b∈{2,4,8,16,32}); encode per
encoding (delta uses one **stateful** encoder — the keyframe pitfall). **Throttled windows are
excluded and reported**, never averaged in; a window/segment mismatch **stops** the reduction rather
than guessing an alignment.

**Cross-check (Law 6):** `energy/op ≈ p_cpu_w · t_op` (t_op from §5). A > 10 % gap = STOP, reconcile.

---
## 7. Two-node 802.11 broadcast link (both RPi4)
Qualitative sanity of the golden scenario with **measured** (not injected) loss + the `p_radio_w`
receive-power measurement. State small-N (2-node) honesty explicitly.

On **both** RPi4 (IBSS / ad-hoc, same cell + frequency):
```bash
sudo ip link set wlan0 down
sudo iw dev wlan0 set type ibss
sudo ip link set wlan0 up
sudo iw dev wlan0 ibss join authbc-mesh 2412 fixed-freq   # same SSID+freq on both; 2412=ch1
sudo ip addr add 10.0.0.1/24 dev wlan0                     # .2 on the other node
```
Then broadcast UDP telemetry frames from one, count received on the other → **measured** frame loss.
While saturating the link, log the receiver's INA219 → `p_radio_w`. (brcmfmac IBSS can be finicky;
if it won't hold the cell, fall back to a monitor-mode + `packet` inject/capture, and note it.)
Confirm with `iw dev wlan0 link` / `iw dev wlan0 station dump`.

---
## 8. Feed measured numbers back into the model + re-freeze safely
1. Put the measured RPi4 `t_enc / t_sign / t_verify / t_agg*` and `p_cpu_w / p_radio_w` into the E5
   config (replacing the nominal `p_cpu_w=3.0`, `p_radio_w=0.7`) and reconcile the energy fixed part
   to the **broadcast** airtime (audit F2).
2. Re-run E4/E5: `make exp-e4 exp-e5 figures`.
3. **The reproduction gate will now fail** (`make verify-frozen`) because the derived numbers changed
   — that is expected and correct. Review the diff, then **commit the new frozen CSVs** as a
   deliberate re-freeze (docs/DECISIONS.md); the gate goes green on the new baseline.
4. Write `docs/audits/p7.md` with the Law-6 validation (expected ranges, thermal-clean runs, meter
   calibration, x86↔ARM ratios). Tag `p7-done`.

---
## 9. Per-platform gotchas
**RPi3 B / B+:** same Bookworm 64-bit Lite; pyenv 3.12 build is slower (~30–40 min); weaker cooling
(heatsink + fan matters more); micro-USB power path is more under-voltage-prone (use 5.1 V/2.5 A);
RPi3 **B** Wi-Fi is 2.4 GHz-only. Expect ~1.5–2× slower than RPi4.

**BeagleBone Black (stretch, expect friction):**
- **32-bit** (ARMv7) → *cannot* run 64-bit Bookworm. Flash the **BeagleBoard.org Debian 12** armhf image.
- **BLS may not build:** `blspy` has no armhf wheel and building it (cmake + gmp + relic) on a
  single-core A8 / 512 MB RAM is slow-to-infeasible. Plan for **Ed25519 + ECDSA + encoders only** on
  BBB; skip BLS there (note it in the writeup).
- **No `vcgencmd`** → no `get_throttled`/`measure_temp`. But the A8 @ 1 GHz draws ~1–2 W and runs
  cool, so throttling is a non-issue; read temp (if exposed) via `/sys/class/thermal/thermal_zone*`.
- **No built-in Wi-Fi** → skip the 2-node link on BBB (or add a USB dongle). Use BBB only for
  CPU-timing (and, if wired, energy) points on a single-core in-order core.

---
## 10. Pre-flight checklist (per board, before recording anything)
- [ ] Quality 5.1 V+ supply; `vcgencmd get_throttled` = `0x0` at idle and after a warmup loop.
- [ ] Heatsink + fan on; idle temp < 55 °C.
- [ ] `hw/provision.sh` run → governor = **performance** (verified), Wi-Fi power-save off, NTP on.
- [ ] Python 3.12 via pyenv; `make setup`; `make test` green on-device.
- [ ] `hw/run_micro.sh --check` OK; timings inside the 5–15× band; no `.THROTTLED` file.
- [ ] INA219 calibrated (|offset| < 2 %); logged from the **meter-host**, not the DUT.
- [ ] Device metadata (`lscpu`, temp, governor) captured to `results/hw/meta/`.
- [ ] Every energy CSV carries meter model + calibration offset + temp min/max + throttle flags.
