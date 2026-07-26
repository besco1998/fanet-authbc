# P7b measurement rig — corrected architecture for 2× RPi4 + 2× INA219 + Arduino

Supersedes the single-sensor sketch in `hw/INA219_wiring.md` §9. With **two** INA219s and an Arduino
available, the right topology changes: the Arduino becomes a **dedicated meter-host** so neither Pi
spends CPU on logging, and both link nodes are instrumented **simultaneously**.

---
## 1. Why this topology (the decisions)

| decision | choice | why | what it fixes |
|---|---|---|---|
| **Meter-host** | **Arduino** (not a Pi, not the DUT) | no OS ⇒ deterministic sampling, no scheduler jitter; zero CPU contamination of the benchmarked Pi | the 2-node link test needs *both* Pis, so neither can be the logger |
| **Sensor count** | **one INA219 per Pi** (2 total) | measures TX-node and RX-node power **in the same run, on one timebase** | `p_radio_w` (receive) and TX power without two sequential runs |
| **Bus addressing** | **0x40 and 0x41** (bridge `A0` on the second board) | two devices cannot share an address | otherwise the second sensor is invisible |
| **Window sync** | **GPIO line Pi→Arduino** | the Arduino must know exactly when the 60 s idle/load window runs | removes wall-clock alignment guesswork |
| **DUT roles** | Pi-A = DUT/TX, Pi-B = link partner/RX | both instrumented; Pi-A also runs the crypto/encode loops | one wiring serves both the CPU-energy and radio-energy measurements |

**Fallback (simpler, already scripted):** if you'd rather not wire the Arduino yet, run
`hw/ina219_smoke.py` on the Pi itself with `taskset -c 0` (sampler) vs `taskset -c 1-3` (benchmark).
The sampler's small load appears in *both* the idle and load windows, so it largely cancels in
`P_loop − P_idle`. Use this for bring-up; use the Arduino for the numbers that go in the thesis.

---
## 2. Topology

```
            ┌──────── 5.2 V bench PSU (3 A) ────────┐
            │                                       │
   (+)──► [INA219 #1 @0x40] ──► RPi4-A (5V pin 2)   │   DUT / TX
   (+)──► [INA219 #2 @0x41] ──► RPi4-B (5V pin 2)   │   link partner / RX
   (−)──────── common GND ────► both Pis (pin 6) ───┘

   Both INA219  SDA/SCL/VCC/GND ──► ARDUINO (I²C bus, 5 V logic)
   RPi4-A GPIO17 (pin 11) ─────────► ARDUINO D2      (window sync, 3.3 V → 5 V input: OK)
   RPi4-A GND (pin 39) ────────────► ARDUINO GND     (shared reference — REQUIRED)
   ARDUINO USB ────────────────────► laptop (CSV over serial @115200)
```

**Grounding rule:** every ground must meet — PSU(−), both Pi grounds, both INA219 grounds, and the
Arduino ground. Tie them at one point (star ground). If you use two separate PSUs instead of one bench
supply, **bond their grounds together**, or the I²C has no common reference and readings will be junk.

**Direction rule:** the sync line runs **Pi → Arduino only**. Pi GPIO is 3.3 V; an Arduino Uno reads
3.3 V as HIGH (V_IH = 0.6·V_CC = 3.0 V). **Never** drive a 5 V Arduino output into a Pi GPIO pin —
that damages the Pi. If you need Arduino → Pi signalling, use a level shifter.

---
## 3. Set the second sensor's address
Two INA219s on one bus need different addresses. On the second board, **bridge the `A0` solder
jumper** (or tie the `A0` pin to VCC if it is broken out):

| A1 | A0 | address |
|----|----|---------|
| GND | GND | **0x40** (default — leave board #1 alone) |
| GND | VCC | **0x41** ← board #2 |
| VCC | GND | 0x44 |
| VCC | VCC | 0x45 |

Verify from the Arduino (I²C scanner) or a Pi: `i2cdetect -y 1` should list **both 0x40 and 0x41**.

---
## 4. Arduino logic level
Arduino **Uno / Nano / Mega** are 5 V logic — power the INA219 breakouts from Arduino **5 V** so the
board's I²C pull-ups reference 5 V and levels match. The INA219 chip's supply range is 3.0–5.5 V, so
5 V is in spec. **If you use an ESP32 / Due / Zero (3.3 V logic), power the breakouts from 3.3 V
instead** — always match the breakout's VCC to the MCU's logic level.

---
## 5. Arduino sketch (`hw/arduino/ina219_logger/ina219_logger.ino`)
Install **Adafruit INA219** via Library Manager, flash the sketch, then read the serial port at
115200 baud. Output is CSV: `millis,window,V1,I1,P1,V2,I2,P2` where `window` is 1 while Pi-A holds
GPIO17 high (the measurement window) and 0 otherwise.

Log it on the laptop with, e.g.:
```bash
python3 -c "import serial,sys; s=serial.Serial('/dev/ttyACM0',115200); [sys.stdout.write(s.readline().decode()) for _ in iter(int,1)]" | tee run.csv
```

---
## 6. Raising the sync line from the Pi
On Pi-A, around each measurement window (Bookworm ships `gpiod`):
```bash
sudo apt-get install -y gpiod
# window start: hold GPIO17 high for the duration of the command it wraps
gpioset --mode=wait gpiochip0 17=1 &      # release with: kill %1
# ... run the 60 s idle window / the 60 s op loop here ...
```
The Python driver (`hw/energy_loop.py`, written at P7b start) will raise/lower the same line around
each window so every sample is unambiguously tagged.

---
## 7. Bring-up order (do not skip)
1. **Sensors alone** — Arduino + both INA219s, no Pis. Confirm the scanner sees 0x40 **and** 0x41 and
   the sketch prints two channels of ~0 A.
2. **Calibrate** each sensor against a known resistive load (10 Ω / ≥5 W at 5 V ⇒ 0.5 A / 2.5 W).
   Record `offset%` per sensor; **>2 % ⇒ stop and fix** before measuring.
3. **One Pi, powered off the bench supply through INA219 #1.** Confirm idle ≈ 2.5–3.5 W and
   `vcgencmd get_throttled` = `0x0`.
4. **Load test** — `stress-ng --cpu 4 --timeout 70s`; power should rise to ~6–7 W and return.
5. **Add Pi-B on INA219 #2**, repeat 3–4 for it.
6. **Sync line** — raise GPIO17 on Pi-A, confirm the `window` column flips to 1.
7. Only then run the real protocol in `hw/energy_protocol.md`.

---
## 8. Safety recap (unchanged, still the way to kill a Pi)
Feeding 5 V into the GPIO pin bypasses the Pi's input protection: **no reverse-polarity, no fuse**.
Triple-check polarity, **never** also plug in USB-C while GPIO-powered, set the supply to
**5.15–5.2 V** (to offset the ~0.15 V burden of a 0.1 Ω shunt at ~1.5 A), and wire everything with the
supply **off**. Confirm `get_throttled=0x0` after every boot — anything else invalidates the run.
