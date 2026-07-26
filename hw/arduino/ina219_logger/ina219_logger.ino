// ina219_logger.ino — AUTHBC P7b meter-host (hw/RIG.md)
//
// Reads TWO INA219 sensors (0x40 = Pi-A/DUT, 0x41 = Pi-B/link partner) and streams CSV over USB
// serial at 115200 baud. A sync line from Pi-A (GPIO17 -> D2) tags samples that fall inside a
// measurement window, so the host can compute P_idle / P_loop without wall-clock alignment.
//
// Output: millis,window,V1,I1_mA,P1_W,V2,I2_mA,P2_W
//
// Requires: Adafruit INA219 library (Library Manager). Board: Uno/Nano/Mega (5 V logic) — power the
// breakouts from 5 V. On a 3.3 V board (ESP32/Due), power them from 3.3 V instead.
//
// SAFETY: the sync line is Pi -> Arduino ONLY. Never drive a 5 V output into a Pi GPIO pin.

#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina1(0x40);   // Pi-A  (DUT / TX)
Adafruit_INA219 ina2(0x41);   // Pi-B  (link partner / RX)  -- bridge A0 on this board

const uint8_t  SYNC_PIN    = 2;      // <- Pi-A GPIO17 (3.3 V reads HIGH on a 5 V Uno)
const uint16_t SAMPLE_MS   = 20;     // 50 Hz
const bool     TWO_SENSORS = true;   // set false to run with a single INA219 at 0x40

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }                 // Leonardo/Micro: wait for the USB CDC port
  pinMode(SYNC_PIN, INPUT);             // Pi drives it; no pull-up needed (Pi drives both ways)

  if (!ina1.begin()) {
    Serial.println(F("# ERROR: INA219 @0x40 not found - check wiring/address"));
    while (1) { delay(1000); }
  }
  if (TWO_SENSORS && !ina2.begin()) {
    Serial.println(F("# ERROR: INA219 @0x41 not found - bridge the A0 jumper on board #2"));
    while (1) { delay(1000); }
  }

  // 32V/2A calibration: with a 0.1 ohm shunt this covers the RPi4's ~0.5-2 A range.
  ina1.setCalibration_32V_2A();
  if (TWO_SENSORS) ina2.setCalibration_32V_2A();

  Serial.println(F("# AUTHBC INA219 logger - hw/RIG.md"));
  Serial.println(F("millis,window,V1,I1_mA,P1_W,V2,I2_mA,P2_W"));
}

void loop() {
  const unsigned long t = millis();
  const int window = digitalRead(SYNC_PIN);   // 1 = inside a measurement window

  const float v1 = ina1.getBusVoltage_V();
  const float i1 = ina1.getCurrent_mA();
  const float p1 = ina1.getPower_mW() / 1000.0f;

  float v2 = 0.0f, i2 = 0.0f, p2 = 0.0f;
  if (TWO_SENSORS) {
    v2 = ina2.getBusVoltage_V();
    i2 = ina2.getCurrent_mA();
    p2 = ina2.getPower_mW() / 1000.0f;
  }

  Serial.print(t);        Serial.print(',');
  Serial.print(window);   Serial.print(',');
  Serial.print(v1, 3);    Serial.print(',');
  Serial.print(i1, 1);    Serial.print(',');
  Serial.print(p1, 4);    Serial.print(',');
  Serial.print(v2, 3);    Serial.print(',');
  Serial.print(i2, 1);    Serial.print(',');
  Serial.println(p2, 4);

  delay(SAMPLE_MS);
}
