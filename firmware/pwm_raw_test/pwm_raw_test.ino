/* ============================================================================
 *  RAW PWM TEST — no SimpleFOC at all.
 *
 *  Tests one thing: does the Teensy put PWM on pins 4, 5, 6?
 *  EN (pin 3) is held LOW, so the DRV8313 outputs stay high-Z and the motor
 *  is completely de-energized. We only care about the IN pins here.
 *
 *  Measure pins 4 / 5 / 6 (or the Mini's IN1/IN2/IN3 pads) to GND:
 *     ~1.6 V on each  -> the Teensy's PWM hardware works. Problem is SimpleFOC.
 *     still 0 V       -> the Teensy/core/pins are the problem, not SimpleFOC.
 *
 *  Safe to run with the battery connected: EN low = no motor drive.
 * ========================================================================= */

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("RAW PWM test: 50% duty on pins 4/5/6, EN(3) held LOW.");
  Serial.println("Measure IN pins to GND -> expect ~1.6 V each.");

  pinMode(3, OUTPUT);
  digitalWrite(3, LOW);            // driver disabled — motor stays dead

  analogWriteResolution(8);        // 0..255
  analogWriteFrequency(4, 25000);  // pins 4,5,6 are all on FlexPWM2
  analogWrite(4, 128);             // 50% duty -> ~1.65 V average
  analogWrite(5, 128);
  analogWrite(6, 128);
}

void loop() {}
