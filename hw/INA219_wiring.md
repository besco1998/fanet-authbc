# INA219 ↔ Raspberry Pi 4 Model B — wiring & bring-up (P7b energy rig)

Step-by-step to connect your INA219 breakout, read whole-board RPi4 power over I²C, calibrate it, and
validate the rig before any real measurement. Companion to `hw/energy_protocol.md` (the protocol) and
`hw/ina219_smoke.py` (the bring-up reader). Read the safety box first.

> ## ⚠️ SAFETY — read before wiring
> - **Polarity is unforgiving.** You will feed 5 V into the RPi4's **GPIO 5 V pin**, which is *after*
>   the board's USB-C input protection — so there is **no reverse-polarity or over-current protection**
>   on that path. A swapped +/− will destroy the Pi. Triple-check before powering.
> - **Never power the Pi from two sources at once.** While measuring via the GPIO 5 V feed, **do NOT
>   plug in the USB-C** supply (back-feeding damages regulators). One power path only.
> - **Use a current-limited supply** set to **5.15–5.2 V, limit ≈ 3 A**. Never exceed 5.5 V (INA219
>   Vin is fine to 26 V, but the Pi's 5 V rail is not).
> - Wire everything **with all supplies OFF**; power up last.

---
## 1. Identify your board (pins vs terminals) and the shunt
Every INA219 breakout has **two electrically separate sides**:

| side | typical labels | carries | connects to |
|---|---|---|---|
| **Power / shunt** (usually a 2-pos **screw terminal** or thick pads) | **Vin+** and **Vin−** (or `+`/`−`) | the **full board current** through the on-board shunt | inline with the Pi's 5 V feed |
| **Logic / I²C** (0.1″ **pin header**) | **VCC**, **GND**, **SCL**, **SDA** (± `A0/A1` address jumpers, `ALERT`) | a few mA of I²C signalling | the RPi4 GPIO header |

**Find the shunt value** (it sets range, resolution, and burden): read the silkscreen on the shunt
resistor — **`R100` = 0.1 Ω** (the common value; assumed below), `R010` = 0.01 Ω, `R050` = 0.05 Ω. If
unlabeled, measure it (or check the product page). If it is **not** 0.1 Ω, change `SHUNT_OHMS` in
`hw/ina219_smoke.py` accordingly.

**Default I²C address = `0x40`** (no A0/A1 jumper bridged).

---
## 2. Measurement concept
High-side sensing: the shunt sits in the **5 V supply line into the Pi**, so the INA219 reports the
**whole-board** bus voltage (the 5 V rail) and current (SoC + RAM + USB + Ethernet + regulators). Power
`P = V_bus × I` is exactly what the energy model needs: `energy/op = (P_loop − P_idle)·t_loop/n_ops`.

---
## 3. Wiring (single-board bring-up)
Power the RPi4 **through** the INA219 shunt via the GPIO 5 V pin; read the INA219 from the same Pi's I²C.

```
   5.15 V PSU (+) ───────────────► [ Vin+ ]  INA219  [ Vin− ] ───────► RPi4 pin 2  (5V in)
   5.15 V PSU (−, GND) ──────────────────────── common GND ──────────► RPi4 pin 6  (GND)

   INA219 VCC ──────────────────────────────────────────────────────► RPi4 pin 1  (3.3V, logic)
   INA219 GND ──────────────────────────────────────────────────────► RPi4 pin 9  (GND)
   INA219 SDA ──────────────────────────────────────────────────────► RPi4 pin 3  (GPIO2 / SDA1)
   INA219 SCL ──────────────────────────────────────────────────────► RPi4 pin 5  (GPIO3 / SCL1)
```

| INA219 | RPi4 physical pin | note |
|---|---|---|
| **Vin+** | — (to PSU **+**) | supply side of the shunt |
| **Vin−** | **pin 2** (5 V) | load side → powers the Pi |
| **VCC** | **pin 1** (3.3 V) | INA219 logic power (I²C at 3.3 V, matches the Pi) |
| **GND** | **pin 9** (GND) | logic ground (common) |
| **SDA** | **pin 3** (GPIO2/SDA1) | I²C data |
| **SCL** | **pin 5** (GPIO3/SCL1) | I²C clock |
| PSU **+** | — (to Vin+) | 5.15–5.2 V |
| PSU **GND** | **pin 6** (GND) | board return current path |

Notes:
- **Current direction:** PSU **+** → Vin+ → Vin− → Pi. If readings come out negative, your Vin+/Vin−
  are swapped — flip them (or the code will just report a negative sign).
- The board-return current goes PSU-GND → pin 6, **not** through the shunt. The shunt only carries the
  +5 V leg (that is correct high-side sensing).
- The INA219's own ~1 mA logic draw is inside the measured current but appears in *both* the idle and
  load windows, so it cancels in `P_loop − P_idle`.

---
## 4. Supply and burden voltage
0.1 Ω shunt drops `0.1 Ω × I`: ≈ 0.15 V at 1.5 A (typical RPi4 load), ≈ 0.2 V at a 2 A boot spike. Set
the PSU to **5.15–5.2 V** so the Pi still sees ≥ 5.0 V. A bench supply (5.2 V, 3 A limit) is ideal; a
clean 5.1 V/3 A USB brick tapped to bare +5 V/GND wires also works. After boot, **`vcgencmd
get_throttled` must read `0x0`** — anything else means under-voltage/throttle → raise the PSU voltage or
check the shunt/cabling.

---
## 5. Enable I²C and detect the sensor
```bash
sudo raspi-config nonint do_i2c 0          # enable I2C (or: dtparam=i2c_arm=on in /boot/firmware/config.txt)
sudo apt-get install -y i2c-tools python3-pip
sudo reboot
# after reboot:
i2cdetect -y 1                             # expect a device at 0x40
```
If `i2cdetect` shows nothing: check VCC/GND present, SDA/SCL not swapped, I²C enabled, and the ribbon
seated. `UU` at 0x40 means a driver already claimed it (fine).

---
## 6. Install the driver + smoke test
```bash
sudo apt-get install -y i2c-tools python3-smbus   # system I2C tooling
.venv/bin/pip install pi-ina219                   # INTO THE REPO VENV -- see the PEP 668 note below
.venv/bin/python hw/ina219_smoke.py --once        # one V / I / P reading
.venv/bin/python hw/ina219_smoke.py --watch       # live stream (Ctrl-C to stop)
```

> **⚠️ PEP 668 (Bookworm and Trixie both):** a bare `pip install` into the system Python fails with
> `error: externally-managed-environment`. Install into the repo venv as above. If the driver cannot
> reach the kernel I²C bindings from inside the venv, recreate it with
> `python -m venv --system-site-packages .venv` (so it can see `python3-smbus`), or as a last resort
> use `pip install --break-system-packages pi-ina219` — acceptable on a dedicated measurement box.
> Your user must be in the `i2c` group (`sudo usermod -aG i2c $USER`, then log out/in) to open
> `/dev/i2c-1` without sudo.
Expected at idle (headless, no peripherals): **V ≈ 5.0–5.1 V, I ≈ 0.5–0.7 A, P ≈ 2.5–3.5 W.**

---
## 7. Calibrate against a known load (do this once)
Before trusting Pi numbers, verify the INA219 on a **known resistive load**:
1. With supplies off, put a **10 Ω, ≥ 5 W** resistor as the "load" (Vin− → resistor → GND) instead of
   the Pi. Power on at 5.0 V.
2. Expected: `I = 5/10 = 0.5 A`, `P = 2.5 W`. Read with `--once`.
3. `offset% = 100·(reading − expected)/expected`. **If |offset%| > 2 %**, re-seat/re-cable (or your
   shunt value is wrong) before proceeding. Record the offset in every run header.
4. Cross-check `V_bus` against a multimeter on the rail — they should agree within ~1 %.

---
## 8. Validate the rig (idle vs. load)
```bash
# 60 s idle baseline:
python3 hw/ina219_smoke.py --window 60
# in another shell, stress all 4 cores, then re-measure the window:
sudo apt-get install -y stress-ng
stress-ng --cpu 4 --timeout 70s &
python3 hw/ina219_smoke.py --window 60
```
You should see mean power rise from ~3 W (idle) to ~6–7 W (4 cores busy). A clear, repeatable
idle→load delta means the rig is trustworthy. Confirm `vcgencmd get_throttled` = `0x0` throughout.

---
## 9. Clean measurement: keep the logger off the benchmarked cores
Reading the INA219 on the **same** Pi adds a little CPU to the load window. Two ways to keep it honest:
- **Core-pin (single board):** run the benchmark on cores 1–3 and the sampler on core 0 —
  `taskset -c 1-3 <bench>` and `taskset -c 0 python3 hw/ina219_smoke.py --window 60`. The tiny sampler
  load is on a core the benchmark never uses, and it is present in both idle and load windows anyway.
- **Two-board (cleanest):** wire the INA219 **shunt inline with DUT-A's 5 V**, but run its **I²C to
  your second RPi4** (SDA→pin 3, SCL→pin 5, VCC→3.3 V, GND→a common ground with DUT-A's supply). Now
  DUT-A does *only* the benchmark and RPi4-B logs power. Use this for the final numbers.

---
## 10. Troubleshooting
| symptom | cause / fix |
|---|---|
| `i2cdetect` empty | I²C not enabled / SDA-SCL swapped / no VCC / bad ribbon |
| negative current | Vin+/Vin− swapped — flip the shunt terminals |
| `DeviceRangeError` in code | shunt voltage exceeded the gain range — set `max_expected_amps=3.2`, gain 320 mV |
| under-voltage (`get_throttled ≠ 0x0`) | raise PSU to 5.2 V; shunt burden too high; bad cable |
| power reads ~0 / equals bus only | current path not through the shunt (load return going straight to PSU-GND *and* bypassing Vin−) — recheck §3 |

---
## 11. Next
Once §8 validates and §7 calibrates, run the full protocol in `hw/energy_protocol.md` (idle 60 s → op
loop 60 s → `energy/op`, ≥ 5 reps, median + CI, thermal guard) to produce `p_cpu_w` / `p_radio_w` and
the per-op energy tables — the inputs that replace E5's nominal 3.0 / 0.7 W at the model re-run.
