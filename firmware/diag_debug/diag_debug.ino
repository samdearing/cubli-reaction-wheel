/* ============================================================================
 *  DIAGNOSTIC — SimpleFOC with internal debug output enabled.
 *
 *  Same pins as before (4/5/6/3), no rewiring. This turns on SimpleFOC's own
 *  debug channel so the library prints exactly what it does while configuring
 *  the Teensy timers. driver.init()'s return value is printed explicitly.
 *
 *  >>> COPY THE ENTIRE SERIAL OUTPUT and send it back. <<<
 *  That text is the smoking gun for why no PWM comes out.
 *
 *  Safe: open-loop, 3 V cap. It will try to spin at the end.
 * ========================================================================= */

#include <SimpleFOC.h>

BLDCMotor      motor  = BLDCMotor(7);
BLDCDriver3PWM driver = BLDCDriver3PWM(4, 5, 6, 3);

void setup() {
  Serial.begin(115200);
  delay(1500);                       // give the USB serial time to attach

  SimpleFOCDebug::enable(&Serial);   // <-- library now narrates its init
  Serial.println("=== SimpleFOC debug enabled ===");

  driver.voltage_power_supply = 14.8;
  driver.voltage_limit        = 3.0;
  driver.pwm_frequency        = 25000;

  Serial.print("calling driver.init() ... returned: ");
  int ok = driver.init();
  Serial.println(ok);                // 1 = success, 0 = fail

  motor.linkDriver(&driver);
  motor.voltage_limit  = 3.0;
  motor.velocity_limit = 20.0;
  motor.controller     = MotionControlType::velocity_openloop;

  Serial.println("calling motor.init() ...");
  motor.init();

  motor.enable();
  Serial.println("=== setup done. commanding 5 rad/s ===");
}

void loop() {
  motor.move(5.0);
}
