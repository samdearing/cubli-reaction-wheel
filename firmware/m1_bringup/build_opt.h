// No build flags needed.
//
// REQUIRED: SimpleFOC library version 2.3.5. Version 2.4.0's Teensy-4 driver is
// broken (init succeeds, zero PWM output). See docs/HARDWARE.md §11.4.
//
// Center-aligned 3PWM is NOT used — it's only for low-side current sensing, which
// the SimpleFOC Mini doesn't have. Plain fast-pwm (the 2.3.5 default) is correct
// for voltage-mode torque control. This file is intentionally empty of flags.
