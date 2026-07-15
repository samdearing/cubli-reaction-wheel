/* ============================================================================
 *  analogWrite SPINNER — no SimpleFOC at all.
 *
 *  Since raw analogWrite works on pins 4/5/6, this drives the motor open-loop
 *  with a hand-rolled 3-phase sine, bypassing SimpleFOC entirely. If the motor
 *  spins with this, EVERY piece of hardware is proven good and the ONLY problem
 *  is SimpleFOC's Teensy-4 PWM config. Same pins, no rewiring.
 *
 *  SAFETY: amplitude is capped at 2.0 V phase (= 0.78 A into 2.55 ohm), well
 *  under the motor's 2 A max. Electrical frequency is a slow 2 Hz so you can
 *  watch it turn. It spins on boot. Pull the loop key to stop.
 *
 *  If it turns: hardware is 100% good — the fight is only with SimpleFOC.
 *  If it doesn't: something mechanical/phase is still off (but the raw PWM
 *                 test passing makes that unlikely).
 * ========================================================================= */

const int   EN = 3, PA = 4, PB = 5, PC = 6;
const float V_SUPPLY   = 14.8f;    // 4S nominal
const float PHASE_AMP  = 2.0f;     // volts peak per phase -> 0.78 A. Keep <= 3.
const float ELEC_HZ    = 2.0f;     // electrical Hz. mech spin = ELEC_HZ / 7 pole pairs
const float TWO_PI_3   = 2.0943951f;

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("analogWrite spinner: 3-phase sine on 4/5/6, EN(3) high.");
  Serial.printf("  amplitude %.1f V (~%.2f A), %.1f Hz elec = %.2f rad/s mech\n",
                PHASE_AMP, PHASE_AMP / 2.55f, ELEC_HZ, 2 * PI * ELEC_HZ / 7.0f);

  pinMode(EN, OUTPUT);
  digitalWrite(EN, HIGH);            // enable the DRV8313

  analogWriteResolution(8);          // 0..255
  analogWriteFrequency(PA, 25000);   // all three share FlexPWM2
  analogWriteFrequency(PB, 25000);
  analogWriteFrequency(PC, 25000);
}

void loop() {
  float th = TWO_PI * ELEC_HZ * (millis() / 1000.0f);
  float m  = PHASE_AMP / V_SUPPLY;                 // modulation fraction (~0.135)

  int da = 128 + (int)(128.0f * m * sinf(th));
  int db = 128 + (int)(128.0f * m * sinf(th - TWO_PI_3));
  int dc = 128 + (int)(128.0f * m * sinf(th + TWO_PI_3));

  analogWrite(PA, da);
  analogWrite(PB, db);
  analogWrite(PC, dc);
}
