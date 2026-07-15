/* ============================================================================
 *  Cubli — MINIMAL open-loop isolation test
 *
 *  Purpose: prove SimpleFOC can generate PWM and turn M1 on pins 4/5/6/3,
 *  with NOTHING else in the way. No encoder, no serial parser, no M2/M3 pins,
 *  no VBAT, no build_opt.h flag. If this spins and the full sketch doesn't,
 *  the problem is in the full sketch. If THIS doesn't spin, the problem is
 *  the library / wiring / driver itself.
 *
 *  Open-loop, voltage-limited to 3.0 V (= 1.18 A into 2.55 ohm) — safe.
 *  It spins the instant it boots. Pull USB or the loop key to stop it.
 * ========================================================================= */

#include <SimpleFOC.h>

BLDCMotor      motor  = BLDCMotor(7);                 // 7 pole pairs
BLDCDriver3PWM driver = BLDCDriver3PWM(4, 5, 6, 3);   // IN1,IN2,IN3,EN

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("MINIMAL open-loop test — motor should spin on boot.");

  driver.voltage_power_supply = 14.8;
  driver.voltage_limit        = 3.0;
  if (!driver.init()) {
    Serial.println("driver.init() FAILED");
    while (1) {}
  }
  Serial.println("driver.init() ok");

  motor.linkDriver(&driver);
  motor.voltage_limit  = 3.0;      // open-loop safe cap
  motor.velocity_limit = 20.0;
  motor.controller     = MotionControlType::velocity_openloop;

  motor.init();
  motor.enable();                  // driver EN high + motor enabled flag
  Serial.println("enabled — commanding 5 rad/s");
}

void loop() {
  motor.move(5.0);                 // constant 5 rad/s, open loop
}
