// ina219_logger.ino — AUTHBC P7b meter-host (Path A; see hw/RIG.md)
//
// Reads TWO INA219 sensors (0x40 = Pi-A/DUT, 0x41 = Pi-B/link partner) and streams CSV over USB
// serial at 115200 baud. A sync line from Pi-A (GPIO17 -> D2, driven in-process by
// hw/energy_loop.py) tags samples that fall inside a measurement window, so the host computes
// P_idle / P_loop without any wall-clock alignment.
//
// Output CSV: ms,window,wtrans,V1,I1_mA,P1_W,V2,I2_mA,P2_W
//   ms      Arduino millis() at sample time (monotonic, drift-free schedule)
//   window  1 while Pi-A holds the sync line high, else 0
//   wtrans  count of window transitions so far — lets the host detect a stuck/floating line
//
// RELIABILITY NOTES
//  * Fixed-rate scheduler (no delay() drift). If a read overruns, the schedule catches up without
//    spiralling, and samples are never emitted faster than SAMPLE_MS.
//  * D2 needs a 10k pulldown to GND. Arduino has no INPUT_PULLDOWN, so a disconnected sync wire
//    would FLOAT and produce random window tags. The pulldown makes a broken wire read 0 (no
//    window) instead of noise — fail-obvious rather than fail-silent.
//  * Sensors are re-probed at boot; a missing sensor halts with a clear message rather than
//    streaming zeros that would look like real data.
//
// Requires: Adafruit INA219 library (Library Manager). Board: Uno/Nano/Mega (5 V logic) — power the
// breakouts from 5 V. On a 3.3 V board (ESP32/Due), power them from 3.3 V instead.
//
// SAFETY: the sync line is Pi -> Arduino ONLY. Never drive a 5 V output into a Pi GPIO pin.

#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina1(0x40);   // Pi-A  (DUT / TX)
Adafruit_INA219 ina2(0x41);   // Pi-B  (link partner / RX)  -- bridge A0 on this board

const uint8_t  SYNC_PIN    = 2;      // <- Pi-A GPIO17, with a 10k pulldown to GND
const uint16_t SAMPLE_MS   = 20;     // 50 Hz
const bool     TWO_SENSORS = true;   // set false to run with a single INA219 at 0x40

static unsigned long next_ms = 0;
static uint16_t      wtrans  = 0;
static int           w_prev  = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }                 // Leonardo/Micro: wait for the USB CDC port
  pinMode(SYNC_PIN, INPUT);             // external 10k pulldown required (see notes above)

  if (!ina1.begin()) {
    Serial.println(F("# FATAL: INA219 @0x40 not found - check wiring/address"));
    while (1) { delay(1000); }
  }
  if (TWO_SENSORS && !ina2.begin()) {
    Serial.println(F("# FATAL: INA219 @0x41 not found - bridge the A0 jumper on board #2"));
    while (1) { delay(1000); }
  }

  // 32V/2A calibration: with a 0.1 ohm shunt this covers the RPi4's ~0.5-2 A range.
  ina1.setCalibration_32V_2A();
  if (TWO_SENSORS) ina2.setCalibration_32V_2A();

  Serial.println(F("# AUTHBC INA219 logger v2 - Path A - hw/RIG.md"));
  Serial.print(F("# sample_ms=")); Serial.print(SAMPLE_MS);
  Serial.print(F(" two_sensors=")); Serial.println(TWO_SENSORS ? 1 : 0);
  Serial.println(F("ms,window,wtrans,V1,I1_mA,P1_W,V2,I2_mA,P2_W"));

  w_prev  = digitalRead(SYNC_PIN);
  next_ms = millis();
}

void loop() {
  // Drift-free fixed-rate schedule: wait until the next slot, then advance by exactly SAMPLE_MS.
  const unsigned long now = millis();
  if ((long)(now - next_ms) < 0) return;
  next_ms += SAMPLE_MS;
  if ((long)(millis() - next_ms) > 0) next_ms = millis();   // fell behind: resync, don't spiral

  const int window = digitalRead(SYNC_PIN);
  if (window != w_prev) { wtrans++; w_prev = window; }

  const float v1 = ina1.getBusVoltage_V();
  const float i1 = ina1.getCurrent_mA();
  const float p1 = ina1.getPower_mW() / 1000.0f;

  float v2 = 0.0f, i2 = 0.0f, p2 = 0.0f;
  if (TWO_SENSORS) {
    v2 = ina2.getBusVoltage_V();
    i2 = ina2.getCurrent_mA();
    p2 = ina2.getPower_mW() / 1000.0f;
  }

  Serial.print(now);      Serial.print(',');
  Serial.print(window);   Serial.print(',');
  Serial.print(wtrans);   Serial.print(',');
  Serial.print(v1, 3);    Serial.print(',');
  Serial.print(i1, 1);    Serial.print(',');
  Serial.print(p1, 4);    Serial.print(',');
  Serial.print(v2, 3);    Serial.print(',');
  Serial.print(i2, 1);    Serial.print(',');
  Serial.println(p2, 4);
}
