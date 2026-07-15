/* ============================================================================
 *  Cubli — M1 Bench Bring-Up  (Teensy 4.1 + SimpleFOC Mini + AS5600)
 *  Rev C pin map. One flash covers the whole bench session — no re-flashing.
 *
 *  WHAT THIS DOES
 *    1. Scans all three I2C buses and reports what enumerates.
 *    2. Streams the M1 AS5600 angle so you can confirm the encoder sees rotation.
 *    3. Runs M1 OPEN-LOOP velocity at a hard-capped voltage.
 *    4. Keeps M2 and M3 hardware-disabled at the driver the entire time.
 *
 *  WHY THE VOLTAGE CAP EXISTS  ** READ THIS **
 *    In open loop there is no back-EMF at low speed and the Mini has no current
 *    shunts. The winding current is just Ohm's law:
 *
 *        I = U / Rs = U / 2.55 ohm
 *
 *    The motor's hard max is 2.0 A  ->  U_max = 2.0 * 2.55 = 5.1 V.
 *    Your Phase-1 voltage_limit of 14.5 V is a CLOSED-LOOP number. Applying it
 *    open-loop would draw 14.5 / 2.55 = 5.7 A and cook the winding.
 *    This sketch clamps to 3.0 V (= 1.18 A). Do not raise the cap.
 *
 *  SAFETY MODEL
 *    - Boots DISABLED. Nothing moves until you type 'e'.
 *    - M2/M3 EN pins are driven LOW in setup() and never touched again.
 *    - Auto-disable after SPIN_TIMEOUT_MS of continuous spinning.
 *    - 'x' = kill everything, any time.
 *
 *  SERIAL COMMANDS (115200 baud, newline-terminated)
 *    ?          help
 *    s          re-scan all three I2C buses
 *    a          toggle AS5600 angle stream (turn the rotor BY HAND to test)
 *    b          read VBAT through the divider on pin 41
 *    e          ENABLE M1
 *    d          DISABLE M1
 *    u <volts>  set open-loop voltage (0 .. 3.0)
 *    v <rad/s>  set open-loop target velocity (signed)
 *    x          EMERGENCY STOP
 * ========================================================================= */

// NOTE: SIMPLEFOC_TEENSY4_FORCE_CENTER_ALIGNED_3PWM is set in build_opt.h, NOT here.
// A #define in this file would not reach SimpleFOC's own .cpp files — Arduino compiles
// libraries as separate translation units. It must be a compiler flag.
// (Not needed for this open-loop test anyway; required before closing the loop.)
#include <SimpleFOC.h>
#include <Wire.h>

// ---------------------------------------------------------------- pin map (Rev C)
// M1 -> FlexPWM2 (sm0A/sm1A/sm2A).  M2 -> FlexPWM4.  M3 -> FlexPWM1.
constexpr int M1_IN1 = 4,  M1_IN2 = 5,  M1_IN3 = 6,  M1_EN = 3;
constexpr int M2_EN  = 21;      // held LOW — hardware isolation
constexpr int M3_EN  = 9;       // held LOW — hardware isolation
constexpr int PIN_VBAT = 41;    // A17, behind the 68k:10k divider

// ---------------------------------------------------------------- motor constants
constexpr int   POLE_PAIRS   = 7;        // 12N14P
constexpr float PHASE_RES    = 2.55f;    // ohm   (HARDWARE.md §2)
constexpr float PHASE_IND    = 0.00086f; // H
constexpr float KV_RATING    = 220.0f;   // RPM/V
constexpr float I_MAX        = 2.0f;     // A, absolute
constexpr float V_SUPPLY_NOM = 14.8f;    // 4S nominal

// HARD CAP. 3.0 V / 2.55 ohm = 1.18 A. Never raise this for open loop.
constexpr float OPENLOOP_V_CAP = 3.0f;

constexpr uint32_t SPIN_TIMEOUT_MS = 20000;  // auto-disable after 20 s of spin
constexpr float    VBAT_DIV_INV    = 7.8f;   // (68k + 10k) / 10k

// ---------------------------------------------------------------- objects
BLDCMotor      motor  = BLDCMotor(POLE_PAIRS);
BLDCDriver3PWM driver = BLDCDriver3PWM(M1_IN1, M1_IN2, M1_IN3, M1_EN);
MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);   // 0x36 on Wire (18/19)

// ---------------------------------------------------------------- state
bool     motorEnabled = false;
bool     streamAngle  = false;
float    targetVel    = 0.0f;      // rad/s, electrical-frame-agnostic (shaft)
uint32_t spinStartMs  = 0;
uint32_t lastPrintMs  = 0;

// =========================================================================
//  I2C scan — the 60 seconds that protects everything downstream
// =========================================================================
void scanBus(TwoWire &bus, const char *name, const char *pins) {
  Serial.printf("  %-6s (%s): ", name, pins);
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    bus.beginTransmission(addr);
    if (bus.endTransmission() == 0) {
      Serial.printf("0x%02X ", addr);
      found++;
    }
  }
  if (!found) Serial.print("-- NOTHING --");
  Serial.println();
}

void scanAll() {
  Serial.println("\n--- I2C SCAN ---");
  scanBus(Wire,  "Wire",  "SDA 18 / SCL 19");
  scanBus(Wire1, "Wire1", "SDA 17 / SCL 16");
  scanBus(Wire2, "Wire2", "SDA 25 / SCL 24");
  Serial.println("EXPECT: Wire -> 0x36 (AS5600 #1) AND 0x6B (IMU)");
  Serial.println("        Wire1 -> 0x36   |   Wire2 -> 0x36");
  Serial.println("If an encoder is missing: check 3V3, GND, and that SDA/SCL");
  Serial.println("are not swapped on the connector you just re-mated.\n");
}

float readVbat() {
  // 12-bit, 3.3 V reference. V_bus = V_pin * (68k + 10k) / 10k
  int raw = analogRead(PIN_VBAT);
  return (raw / 4095.0f) * 3.3f * VBAT_DIV_INV;
}

void killAll() {
  targetVel = 0.0f;
  motor.move(0);
  motor.disable();         // motor.disable(), not driver.disable() — see setup()
  motorEnabled = false;
  digitalWriteFast(M2_EN, LOW);
  digitalWriteFast(M3_EN, LOW);
  Serial.println("!! ALL MOTORS DISABLED !!");
}

void help() {
  Serial.println("\n=== COMMANDS ===");
  Serial.println("  ?          this help");
  Serial.println("  s          re-scan I2C buses");
  Serial.println("  a          toggle AS5600 angle stream (turn rotor by hand)");
  Serial.println("  b          read VBAT (pin 41)");
  Serial.println("  e / d      enable / disable M1");
  Serial.printf ("  u <volts>  open-loop voltage  (0 .. %.1f V hard cap)\n", OPENLOOP_V_CAP);
  Serial.println("  v <rad/s>  open-loop target velocity (signed)");
  Serial.println("  x          EMERGENCY STOP\n");
}

// =========================================================================
void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { }

  // ---- FIRST: hardware-isolate M2 and M3. Before anything else can go wrong.
  pinMode(M2_EN, OUTPUT); digitalWriteFast(M2_EN, LOW);
  pinMode(M3_EN, OUTPUT); digitalWriteFast(M3_EN, LOW);

  analogReadResolution(12);

  Serial.println("\n============================================");
  Serial.println(" Cubli M1 bench bring-up — Rev C pin map");
  Serial.println(" M2/M3 held DISABLED at the driver.");
  Serial.printf ( " Open-loop voltage cap: %.1f V  (= %.2f A into %.2f ohm)\n",
                  OPENLOOP_V_CAP, OPENLOOP_V_CAP / PHASE_RES, PHASE_RES);
  Serial.println("============================================");

  Wire.begin();  Wire.setClock(400000);
  Wire1.begin(); Wire1.setClock(400000);
  Wire2.begin(); Wire2.setClock(400000);
  delay(50);

  scanAll();

  // ---- encoder (M1, on Wire). Used only as an INDEPENDENT measurement here —
  //      open-loop control does not close on it. That is the whole point: if the
  //      commanded velocity and the measured velocity disagree, you learn something.
  sensor.init(&Wire);
  Serial.printf("AS5600 #1 initial angle: %.3f rad\n", sensor.getAngle());

  // ---- driver
  driver.voltage_power_supply = V_SUPPLY_NOM;
  driver.voltage_limit        = OPENLOOP_V_CAP;   // clamp at the driver too
  driver.pwm_frequency        = 25000;            // 25 kHz — above audible, << L/R = 337 us
  if (!driver.init()) {
    Serial.println("FATAL: driver.init() failed. Check EN/IN wiring. Halting.");
    while (1) { }
  }
  motor.linkDriver(&driver);

  // ---- motor, OPEN LOOP
  motor.phase_resistance  = PHASE_RES;
  motor.phase_inductance  = PHASE_IND;
  motor.KV_rating         = KV_RATING;
  motor.voltage_limit     = OPENLOOP_V_CAP;       // <-- the number that matters today
  motor.current_limit     = I_MAX;
  motor.velocity_limit    = 40.0f;                // rad/s, gentle for a bench spin
  motor.controller        = MotionControlType::velocity_openloop;

  motor.useMonitoring(Serial);
  motor.init();
  motor.disable();         // boot disabled. nothing spins until you say so.
                           // NOTE: motor.disable(), not driver.disable() — the
                           // motor keeps its OWN enabled flag, and BLDCMotor::move()
                           // early-returns if it's false. Driving EN high alone is
                           // not enough; the library must also know it's enabled.

  Serial.println("\nReady. Motor is DISABLED.");
  Serial.println("Suggested order:  s  ->  a (spin rotor by hand)  ->  b  ->  u 2.0  ->  e  ->  v 5");
  help();
}

// =========================================================================
void loop() {
  // ---- serial command parser
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length()) {
      char c = line.charAt(0);
      float arg = (line.length() > 1) ? line.substring(1).toFloat() : 0.0f;

      switch (c) {
        case '?': help(); break;
        case 's': scanAll(); break;

        case 'a':
          streamAngle = !streamAngle;
          Serial.printf("angle stream %s\n", streamAngle ? "ON — turn the rotor by hand"
                                                         : "OFF");
          break;

        case 'b': {
          float vb = readVbat();
          Serial.printf("VBAT = %.2f V  (pin 41 raw -> x%.1f)\n", vb, VBAT_DIV_INV);
          if (vb < 1.0f) Serial.println("  ~0 V: divider not fitted, or loop key is OUT. Both are fine on USB-only.");
          else if (vb < 12.0f) Serial.println("  *** BELOW 12 V CUTOFF — charge the pack. ***");
          break;
        }

        case 'e':
          motor.enable();          // sets driver EN high AND the motor's enabled flag
          motorEnabled = true;
          spinStartMs  = millis();
          Serial.printf("M1 ENABLED. voltage_limit = %.2f V (~%.2f A). "
                        "Auto-disable in %lu s.\n",
                        motor.voltage_limit, motor.voltage_limit / PHASE_RES,
                        SPIN_TIMEOUT_MS / 1000UL);
          break;

        case 'd':
          targetVel = 0.0f;
          motor.disable();         // zeroes the phases AND clears the enabled flag
          motorEnabled = false;
          Serial.println("M1 disabled.");
          break;

        case 'u': {
          float v = constrain(arg, 0.0f, OPENLOOP_V_CAP);
          if (arg > OPENLOOP_V_CAP)
            Serial.printf("REFUSED %.2f V — open-loop cap is %.1f V (%.1f A limit / %.2f ohm). "
                          "Clamped.\n", arg, OPENLOOP_V_CAP, I_MAX, PHASE_RES);
          motor.voltage_limit  = v;
          driver.voltage_limit = v;
          Serial.printf("voltage_limit = %.2f V  ->  est. %.2f A at standstill\n",
                        v, v / PHASE_RES);
          break;
        }

        case 'v':
          targetVel = arg;
          spinStartMs = millis();      // restart the spin timer on a new command
          Serial.printf("target velocity = %.2f rad/s\n", targetVel);
          break;

        case 'x': killAll(); break;

        default: Serial.println("? for help"); break;
      }
    }
  }

  // ---- auto-disable: don't cook a stalled winding while you stare at the serial monitor
  if (motorEnabled && fabsf(targetVel) > 0.01f &&
      (millis() - spinStartMs) > SPIN_TIMEOUT_MS) {
    Serial.println("\n*** SPIN TIMEOUT — auto-disabling. 'e' then 'v' to resume. ***");
    killAll();
  }

  // ---- open-loop move (must be called as fast as possible)
  if (motorEnabled) motor.move(targetVel);

  // ---- telemetry, 10 Hz
  if (millis() - lastPrintMs > 100) {
    lastPrintMs = millis();
    sensor.update();                              // independent measurement

    if (streamAngle) {
      Serial.printf("angle %8.3f rad   vel %8.3f rad/s\n",
                    sensor.getAngle(), sensor.getVelocity());
    } else if (motorEnabled) {
      float vMeas = sensor.getVelocity();
      Serial.printf("cmd %6.2f | meas %6.2f rad/s | err %6.2f | U %.2f V | ~%.2f A | VBAT %.1f V\n",
                    targetVel, vMeas, targetVel - vMeas,
                    motor.voltage_limit, motor.voltage_limit / PHASE_RES, readVbat());
    }
  }
}

/* ============================================================================
 *  WHAT "WORKING" LOOKS LIKE
 *
 *  I2C scan .... 0x36 + 0x6B on Wire; 0x36 on Wire1; 0x36 on Wire2.
 *                A missing 0x36 is almost always a swapped SDA/SCL on a
 *                connector you just re-mated, or a dead 3V3 leg.
 *
 *  'a' + hand ... angle sweeps 0 -> 6.283 rad and wraps cleanly. Dropouts or
 *                a frozen value mean the magnet gap is wrong or the bus is noisy.
 *
 *  'e' + 'v 5' .. rotor turns smoothly, quietly, in one direction. 'meas'
 *                converges toward 'cmd'. Motor stays cool to the touch.
 *
 *  FAILURE SIGNATURES
 *    Cogs / stutters / screeches ....... phase order or a bad phase connection.
 *                                        Kill it. Re-check A/B/C continuity.
 *    Turns but 'meas' stays ~0 ......... encoder is alive but not reading the
 *                                        rotor magnet. Mechanical, not electrical.
 *    'meas' has the wrong sign ......... expected. Phase order sets rotation
 *                                        sense; initFOC() will resolve it later.
 *    Motor gets warm fast .............. STOP. You are over-current. Check that
 *                                        voltage_limit really is <= 3 V.
 *    Nothing at all .................... EN wiring (M1 EN is pin 3 now, not 30),
 *                                        or VM/GND at the Mini, or common ground
 *                                        not tied to the star node.
 *
 *  ONLY after all of the above is clean do you move to initFOC() and closed loop,
 *  where voltage_limit goes back up to 14.5 V.
 * ========================================================================= */
