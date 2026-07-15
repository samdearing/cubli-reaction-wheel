# Cubli — Rolling To-Do

*Working backlog. Check items off, add as they surface. Newest priorities at the top of each
section. The "Standing reminders" at the bottom are permanent — they don't get checked off.*

Last touched: 2026-07-14

---

## 🔥 Now — close the loop on M1 (Phase 1 firmware)

- [ ] `initFOC()` sensor alignment on M1 — resolves the open-loop sign flip (encoder read −5 for cmd +5)
- [ ] After alignment succeeds, return `voltage_limit` 3 V → **14.5 V** (closed loop only)
- [ ] Closed-loop torque test on M1 — command a torque, confirm the wheel holds/accelerates as expected
- [ ] IMU first light — raw accel + gyro clean over serial (start from `firmware/Madgwick_test`)
- [ ] Madgwick filter → valid, stable quaternion at rest and under hand rotation
- [ ] Quaternion → edge-tilt (`theta`) extraction about the active axis
- [ ] 1 kHz control-loop scheduler + telemetry skeleton
- [ ] AS5600 wheel-speed estimator — **filter it** (raw diff at 1 kHz = ±1.5 rad/s quantization; see reminders)
- [ ] Port PD + desaturation controller from `sim/controller.py` to C++ (Kp 1.40, Kd 0.080, Kw **+**1e-4)
- [ ] Safety layer: tilt cutoff, overspeed cutoff, watchdog
- [ ] PC-side log decoder + plot script mirroring `sim/run.py`
- [ ] Tune on the edge → **🎯 Phase 1 deliverable: video of the cube balancing on an edge**

## 🔧 Build — mechanical + electrical

- [ ] Build the VBAT sense divider (68k:10k + 100 nF → pin 41) — currently **not built**, pin floats
- [ ] Star-ground distribution board — 470 µF bulk, home-run each driver GND (no daisy-chain)
- [ ] Final frame tensioning — pre-stretch the cable stays, re-tension after settle, verify hub centered
- [ ] Confirm cube edge `E` in CAD (inter-wheel clearance ≥ ~2 mm) → locks tube cut lengths
- [ ] Machine the brass CM ballast (~45–50 g) from wheel offcuts; finalize mass + position
- [ ] Full-assembly mass tensor in SolidWorks (battery + ballast in final slots) → feed `sim/params.py`

## 📈 Sim — remaining

- [ ] Re-run `params.py` with the measured mass tensor once SolidWorks gives it
- [ ] Sensor realism in `run.py` — add quantization, noise, bias, I2C latency
- [ ] Robustness sweep: vary m, l, I_bar ±30–50 % and confirm the gains still hold
- [ ] IMU accel/gyro full-scale range selection (and widen the gyro for the Phase-3 hop)

## 📂 Repo / portfolio

- [ ] Add GitHub topics (gear by "About"): reaction-wheel, control-systems, sensor-fusion, teensy, bldc, foc, imu, adcs, aerospace, inverted-pendulum
- [ ] Export a few STEP or rendered PNGs of key parts (hub, wheel) into `cad/` — browser-viewable
- [ ] Embed the Phase-1 balancing video in the README when it exists
- [ ] Optional: contact / LinkedIn line under your name in the README

## 🔭 Later — Phase 2 (3-axis corner balance)

- [ ] Wire encoders #2/#3 to `Wire1` (17/16) and `Wire2` (25/24)
- [ ] Activate M2 + M3 (drivers, phases, EN 21 / 9)
- [ ] Extend the sim to a 3-DOF rigid body
- [ ] LQR design on the linearized plant — choose Q, R
- [ ] Corner balance (hand-placed start) → **🎯 deliverable: video w/ disturbance rejection**

## 🔭 Later — Phase 3 (hop-up)

- [ ] Brake chopper (power resistor + MOSFET on bus overvoltage) — required before ANY hop
- [ ] Multi-swing pump-up trajectory on the same ~8e-5 wheel
- [ ] Catch with the Phase-2 corner controller → **🎯 deliverable: video of the hop**

---

## 📌 Standing reminders (do not delete — these already bit once)

- **SimpleFOC library = 2.3.5.** NOT 2.4.0 (its Teensy-4 driver outputs zero PWM silently). `HARDWARE.md` §11.4.
- **Open-loop `voltage_limit` = 2–3 V, never 14.5 V.** No back-EMF at standstill → `I = U/Rs`; 14.5 V = 5.7 A into a 2 A motor.
- **Wheel-speed quantization:** raw AS5600 diff at 1 kHz = ±1.5 rad/s of noise (12-bit / 1 ms). Filter or lengthen the diff window before feeding the `Kw` desaturation term.
- **`Kw` sign is +.** Negative places a right-half-plane pole → wheel runs away. `sim/controller.py` proves it.
- **Don't cut the VUSB↔VIN pad** until the BEC is physically ready — and that's post-Phase-1, not now.
- **Bench boundary = the loop key.** Everything before it (logic, I2C, encoders) is free; a wiring error after it is a dead board or a LiPo event. Continuity-check grounds on every re-mate.
- **Git rhythm:** `git pull` when you sit down, `git add -A && git commit && git push` when you stop. Pull before, push after.
- **`initFOC()` resolves the M1 sign flip** — don't "fix" it by rewiring phases.
