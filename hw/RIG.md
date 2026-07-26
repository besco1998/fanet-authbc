# P7b measurement rig — **Path A** (the one and only measurement path)

**Decision: Path A is what the thesis uses.** Two INA219s are read by an **Arduino meter-host**; the
benchmarked Pi spends **zero CPU** on logging, and both link nodes are instrumented simultaneously on
one timebase. `hw/INA219_wiring.md` describes the older Pi-reads-its-own-sensor wiring (**Path B**) —
kept only as a bring-up fallback if the Arduino path stalls. The INA219's SDA/SCL go to the Arduino
**or** the Pi, never both.

**The three programs:**

| where it runs | program | job |
|---|---|---|
| **Arduino** | `hw/arduino/ina219_logger/ina219_logger.ino` | sample both sensors at 50 Hz, tag each sample with the sync line, stream CSV over USB |
| **DUT Pi** | `hw/energy_loop.py` | run each op in a timed window and **drive the sync line in-process** (no separate command), emit a manifest JSON |
| **This WSL2 box** | `hw/ina219_capture.py` | capture the Arduino stream to a samples CSV; `--reduce` merges manifest+samples into energy/op |

---
## 1. Why this topology (the decisions)

| decision | choice | why |
|---|---|---|
| **Meter-host** | **Arduino** (not a Pi, not the DUT) | no OS ⇒ deterministic sampling; **zero CPU contamination**; the 2-node link test needs *both* Pis, so neither can be the logger |
| **Sensor count** | **one INA219 per Pi** (2 total) | TX-node and RX-node power **in the same run, on one timebase** |
| **Bus addressing** | **0x40 and 0x41** (bridge `A0` on board #2) | two devices cannot share an address |
| **Window sync** | **GPIO17 → Arduino D2, driven in-process** by `energy_loop.py` | the Arduino knows exactly which samples are in-window; no wall-clock alignment, no separate `gpioset` |
| **Redundancy** | manifest also carries **UTC + duration per window** | if GPIO ever fails, windows are still recoverable from timestamps |
| **DUT roles** | Pi-A = DUT/TX, Pi-B = link partner/RX | one wiring serves both the CPU-energy and radio-energy measurements |

---
## 2. Topology

```
            ┌──────── 5.2 V bench PSU (3 A) ────────┐
            │                                       │
   (+)──► [INA219 #1 @0x40] ──► RPi4-A (5V pin 2)   │   DUT / TX
   (+)──► [INA219 #2 @0x41] ──► RPi4-B (5V pin 2)   │   link partner / RX
   (−)──────── common GND ────► both Pis (pin 6) ───┘

   Both INA219  SDA/SCL/VCC/GND ──► ARDUINO (I²C bus, 5 V logic)
   RPi4-A GPIO17 (pin 11) ─────────► ARDUINO D2   ── plus a 10 kΩ pulldown D2→GND  (REQUIRED)
   RPi4-A GND (pin 39) ────────────► ARDUINO GND  (shared reference — REQUIRED)
   ARDUINO USB ────────────────────► this WSL2 machine (CSV over serial @115200)
```

**⚠️ The 10 kΩ pulldown on D2 is not optional.** Arduino has no `INPUT_PULLDOWN`, so if the sync wire
comes loose the pin **floats** and produces random window tags — corrupt data that still *looks*
plausible. The pulldown makes a broken wire read a steady 0 (no windows at all), which the reducer
detects immediately as a window/segment mismatch. Fail-obvious beats fail-silent.

**Grounding rule:** PSU(−), both Pi grounds, both INA219 grounds and the Arduino ground must meet at
one point (star ground). Two separate PSUs ⇒ **bond their grounds**, or the I²C has no common
reference and readings are junk.

**Direction rule:** the sync line is **Pi → Arduino only**. Pi GPIO is 3.3 V (an Uno reads that as
HIGH). **Never** drive a 5 V Arduino output into a Pi GPIO pin.

---
## 3. Set the second sensor's address
| A1 | A0 | address |
|----|----|---------|
| GND | GND | **0x40** (default — leave board #1 alone) |
| GND | VCC | **0x41** ← bridge `A0` on board #2 |
| VCC | GND | 0x44 |
| VCC | VCC | 0x45 |

Both must appear in the Arduino's I²C scan (or `i2cdetect -y 1` if you temporarily wire to a Pi).

---
## 4. Arduino logic level
**Uno / Nano / Mega** are 5 V logic — power the INA219 breakouts from Arduino **5 V** (the INA219's
supply range is 3.0–5.5 V, so this is in spec and the bus pull-ups then reference 5 V). On a
**3.3 V board (ESP32 / Due / Zero) power them from 3.3 V instead** — always match the breakout's VCC
to the MCU's logic level.

---
## 5. Flash the sketch
Install **Adafruit INA219** via Library Manager, open `hw/arduino/ina219_logger/ina219_logger.ino`,
flash it. Output CSV at 115200 baud:

```
ms,window,wtrans,V1,I1_mA,P1_W,V2,I2_mA,P2_W
```
`ms` = drift-free 50 Hz schedule · `window` = 1 while Pi-A holds the sync line · `wtrans` = count of
window transitions (lets the host spot a stuck or floating line). A missing sensor **halts** with a
`# FATAL:` line rather than streaming zeros that would look like real data.

---
## 6. ⚠️ WSL2: make the Arduino visible to this machine
WSL2 does not see USB devices by default. On **Windows PowerShell (Administrator)**:
```powershell
winget install usbipd
usbipd list                      # find the Arduino's BUSID, e.g. 2-3
usbipd bind   --busid 2-3        # once per device
usbipd attach --wsl --busid 2-3  # after every replug / WSL restart
```
Then in WSL:
```bash
ls -l /dev/ttyACM0               # or /dev/ttyUSB0 for CH340-based clones
sudo usermod -aG dialout $USER   # then log out/in, so you don't need sudo
```
If `/dev/ttyACM*` never appears, either re-run `usbipd attach`, or fall back to capturing on Windows
and copying the CSV into the repo (keep the repo on the Linux FS — never run it from `/mnt/c`).

---
## 7. The measurement run (order matters)
```bash
# 1) HERE (WSL2) — start capturing FIRST, and leave it running for the whole campaign:
./hw/ina219_capture.py --port /dev/ttyACM0
#    -> results/hw/energy/samples-<UTC>.csv

# 2) ON THE DUT PI — validate the rig, then run the campaign:
./hw/energy_loop.py --quick          # 5 s windows x2 reps: proves sync + sensors
./hw/energy_loop.py                  # full: 60 s windows x5 reps per op
#    -> results/hw/energy/manifest-<host>-<UTC>.json

# 3) HERE — stop the capture (Ctrl-C), then reduce:
./hw/ina219_capture.py --reduce results/hw/energy/manifest-*.json \
                                results/hw/energy/samples-*.csv
#    -> energy-<host>-<UTC>.csv  +  -summary.csv  (median + bootstrap CI per op)
```
`energy_loop.py` drives GPIO17 itself around every window — there is no separate command to run and
nothing to time by hand. The line is released by a `finally` block, an `atexit` hook **and**
SIGINT/SIGTERM handlers, so an aborted run cannot leave it stuck high.

**The reducer refuses to guess.** If the number of captured window segments ≠ the number of manifest
windows it **stops** with an explanatory error (capture started late, or a floating D2). Windows the
Pi flagged as **throttled are excluded and reported**, never averaged in.

---
## 8. Bring-up order (do not skip)
1. **Sensors alone** — Arduino + both INA219s, no Pis: the scanner sees 0x40 **and** 0x41; both
   channels read ≈ 0 A.
2. **Calibrate** each sensor against a known resistive load (10 Ω / ≥5 W at 5 V ⇒ 0.5 A / 2.5 W).
   Record `offset%` per sensor; **>2 % ⇒ stop and fix** before measuring.
3. **One Pi** on INA219 #1: idle ≈ 2.5–3.5 W and `vcgencmd get_throttled` = `0x0`.
4. **Load test** — `stress-ng --cpu 4 --timeout 70s`: power rises to ~6–7 W and returns.
5. **Add Pi-B** on INA219 #2; repeat 3–4.
6. **Sync line** — run `./hw/energy_loop.py --quick` and confirm the `window` column flips to 1 and
   `wtrans` increments; then reduce the quick run end-to-end.
7. Only then run the full protocol (`hw/energy_protocol.md`).

---
## 9. Safety recap
Feeding 5 V into the GPIO pin bypasses the Pi's input protection: **no reverse-polarity, no fuse**.
Triple-check polarity, **never** also plug in USB-C while GPIO-powered, set the supply to
**5.15–5.2 V** (to offset the ~0.15 V burden of a 0.1 Ω shunt at ~1.5 A), and wire everything with the
supply **off**. Confirm `get_throttled=0x0` after every boot — anything else invalidates the run.
