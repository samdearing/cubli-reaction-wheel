# Cubli — Firmware

Teensy 4.1 + SimpleFOC + AS5600. Arduino IDE 2.x.

## ⚠ REQUIRED: SimpleFOC library version 2.3.5

**Do not use SimpleFOC 2.4.0.** Its Teensy-4 driver is broken: `driver.init()` reports success
and configures the FlexPWM timers, but **no PWM ever reaches the pins** — 0 V output, motor dead,
no error. Diagnosed 2026-07-14 on this exact hardware by measuring: raw `analogWrite` on pins
4/5/6 worked perfectly, yet SimpleFOC 2.4.0 produced nothing. **2.3.5 fixes it instantly.**

Install: Arduino IDE → Library Manager → *Simple FOC* → version dropdown → **2.3.5**.

Center-aligned 3PWM is **not** used — it only matters for low-side current sensing, which the
SimpleFOC Mini doesn't have. Plain fast-pwm (the 2.3.5 default) is correct for voltage-mode
torque control. No `build_opt.h` flags, no library edits.

## Sketches

| Sketch | Purpose |
|---|---|
| **`m1_bringup/`** | The real bench tool. Serial-driven: I2C scan, encoder stream, open-loop M1 spin with encoder feedback, VBAT read, per-command enable/disable, safety timeouts. M2/M3 held disabled at the driver. **Start here.** |
| `m1_minimal/` | Barest SimpleFOC open-loop spin — no encoder, no serial. Used to isolate library vs sketch during debugging. |
| `diag_debug/` | SimpleFOC with `SimpleFOCDebug::enable()` — prints the library's PWM config decisions. The sketch that exposed the 2.4.0 bug. |
| `pwm_raw_test/` | Raw `analogWrite` on 4/5/6, no SimpleFOC. Proves the Teensy PWM hardware independent of the library. |
| `analogwrite_spin/` | Hand-rolled 3-phase sine open-loop spinner, no SimpleFOC. Proves the motor+driver turn independent of the library. |

The four small sketches are debugging artifacts kept deliberately — they're the isolation ladder
that located the 2.4.0 regression, and they'll re-diagnose any future "motor won't spin" problem.

## Pin map (Rev C — see `docs/HARDWARE.md` §11)

| Motor | IN1 | IN2 | IN3 | EN | Encoder bus |
|---|---|---|---|---|---|
| M1 | 4 | 5 | 6 | 3 | `Wire` (18/19) |
| M2 | 22 | 23 | 2 | 21 | `Wire1` (17/16) |
| M3 | 8 | 7 | 1 | 9 | `Wire2` (25/24) |

## Open-loop safety

`voltage_limit` is hard-capped at **3.0 V** in the bring-up sketch. Open loop has no back-EMF at
standstill and the Mini has no current shunts, so `I = U / Rs = U / 2.55 Ω`. The closed-loop
14.5 V would draw 5.7 A into a 2 A motor. Do not raise the open-loop cap. It returns to 14.5 V
only after `initFOC()` succeeds and the loop is closed.

## Status

- [x] I2C scan, encoder hand-turn, phase/continuity checks — all pass
- [x] M1 open-loop spin, encoder tracks commanded velocity (2026-07-14)
- [ ] `initFOC()` sensor alignment + closed-loop torque (resolves the open-loop sign flip)
- [ ] VBAT sense divider — **not yet built** (pin 41 currently floats; the ~6 V it reads is noise)
