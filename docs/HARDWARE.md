# Cubli — Hardware Specification (as purchased)

> **Source of truth.** This sheet reflects the parts actually bought and supersedes the
> hardware called out in the original project brief. Where it differs from the brief,
> *this document wins.* Substitutions vs. the brief are noted in the changelog at the bottom.
>
> **Rev C — 2026-07-14.** Electrical wiring, the Teensy pin map, VBAT sense, the BEC, and the
> connector ICD are now **locked in §11**. They previously lived only in conversation memory.

---

## 1. Microcontroller

| | |
|---|---|
| Board | **Teensy 4.1** |
| MCU | i.MX RT1062, 600 MHz Cortex-M7 + hardware FPU |
| Logic level | 3.3 V |
| I2C buses (exposed) | **3** — `Wire` (SDA 18 / SCL 19), `Wire1` (SDA 17 / SCL 16), `Wire2` (SDA 25 / SCL 24) |
| Power (bench) | **USB** (5 V → onboard 3.3 V regulator) |
| Power (untethered) | 3 A BEC → `VIN`, **after** the VUSB↔VIN pad cut — see §11.7 |

The three independent I2C buses are load-bearing for this design — see §6.

> `Wire2` (SDA 25 / SCL 24) has **no alternate pins** on this MCU. Those two pins are also
> FlexPWM1's sm2-X and sm3-X outputs, so committing to a third I2C bus removes them from the
> PWM pool. That is what forces the motor pin allocation in §11.3 — the constraint is real and
> traceable, not a layout accident.

---

## 2. Motors — QiuLovesYT 2804 BLDC (×3)

Gimbal-style outrunner, hollow shaft. *Replaces the GBM2804 / MN3110 in the brief.*

| Parameter | Value | Notes |
|---|---|---|
| KV | 220 RPM/V | True low-KV → high torque/amp, ideal for reaction-wheel torque control |
| Torque constant Kt | 0.0434 N·m/A | = Ke; self-consistent with KV (9.549 / 220) |
| Back-EMF constant Ke | 0.0434 V·s/rad | |
| Pole pairs | **7** (12N14P) | → `BLDCMotor(7)` in SimpleFOC |
| Phase resistance Rs | 2.55 Ω | line-to-line winding R = 5.1 Ω |
| Phase inductance Ls | 0.86 mH | electrical time constant τ = L/R ≈ **337 µs** — sets the PWM frequency floor (§11.4) |
| Rated current | 0.5 A | continuous |
| **Max current** | **2.0 A** | hard limit → `current_limit = 2.0` (enforced by *estimate* — see §3) |
| Continuous torque | ≈ 0.022 N·m | Kt × 0.5 A |
| **Peak torque** | ≈ 0.087 N·m | Kt × 2.0 A |
| Rotor inertia | 3.7e-6 kg·m² | add to flywheel inertia for the precise plant model |
| No-load speed | 2600 RPM @ 12 V | ≈ 272 rad/s @ 12 V. Operating envelope set by `voltage_limit` — see below |
| Magnetic flux | 0.0035 Wb | |
| Operating voltage | 7.4–16 V (rated 12 V) | **20 V absolute max** — see §7 |
| Phase connector | MX1.25, 3-pin | |
| Shaft | 8 mm OD, 6.5 mm bore, hollow 5.4–6.5 mm | pre-installed radial magnet ring for the encoder |
| Body size | 34.5 × 15 mm (19.5 mm tall w/ magnet ring) | |

**Speed/torque envelope at `voltage_limit = 14.5 V` (the numbers that matter):**

- **Flat-torque knee ≈ 217 rad/s** — `(V_lim − I_lim·Rs)/Ke`. Below this the *current* limit
  binds and the full 0.087 N·m is available. **This is the speed to use for momentum budgets.**
- **Zero-torque asymptote ≈ 334 rad/s** — `V_lim/Ke`. Between 217 and 334 the available motoring
  torque tapers linearly to zero; the wheel can coast near 334 but cannot accelerate there under
  load. Treat it as a wall, not an operating point. (Braking torque does *not* taper — see §9.)

**Thermal caveat:** peak (2 A) torque is *not* sustainable continuously — rated current is only
0.5 A. Balancing is low-duty on torque (wheel idles near zero with bursts), so RMS current stays
well under 2 A in practice.

> ### ⚠ OPEN-LOOP VOLTAGE LIMIT — the number that kills motors
> `voltage_limit = 14.5 V` is a **closed-loop** number. It is safe only because back-EMF opposes
> the applied voltage once the rotor is turning and the current *estimate* throttles the command.
>
> **In open loop there is no back-EMF at standstill and no current shunt to catch it.** The
> winding current is simply `I = U / Rs`:
>
> | Applied U | Current into 2.55 Ω | Verdict |
> |---|---|---|
> | 14.5 V | **5.7 A** | 2.85× the 2.0 A max — destroys the winding |
> | 5.1 V | 2.0 A | exactly at the hard limit |
> | **3.0 V** | **1.18 A** | **use this for any open-loop bring-up** |
>
> Invert it: `U_max = I_max · Rs = 2.0 × 2.55 = 5.1 V`. **Any open-loop test sets
> `motor.voltage_limit` to 2–3 V.** It returns to 14.5 only after `initFOC()` succeeds.

---

## 3. Motor drivers — SimpleFOC Mini (×3)

Bundled with the motor kit. DRV8313-based.

| Parameter | Value | Notes |
|---|---|---|
| Driver IC | DRV8313 (3 × half-bridge) | |
| Input voltage (VM) | 8–30 V | **8 V floor is the binding constraint** |
| Max current | 2.5 A / phase | motor's 2 A is the tighter limit |
| **Current sensing** | **NONE** | the board has no shunts — see note below ⚠ |
| Onboard 3.3 V LDO | 10 mA only | **cannot power the Teensy** — logic runs on USB / BEC |
| Control pins | IN1, IN2, IN3, EN (3.3 V logic) | + common GND (mandatory, see §7 and §11.1) |
| Size | ~26 × 21 mm | |

> ⚠ **No current sense → no closed current loop.** The "inner torque loop" on this board is
> SimpleFOC **voltage-mode torque control with *estimated* current**: the library uses
> `phase_resistance` + `KV_rating` to estimate the current and enforce `current_limit`.
> Consequences: (1) torque accuracy and the 2 A limit ride on the Rs estimate — copper rises
> ~0.4 %/°C, so a hot winding draws more than the estimate believes; (2) this is fine for our
> low-duty balancing bursts, but it is an *estimated* limit, not a measured one. Flight
> reaction-wheel electronics carry true current loops for exactly this reason — note the
> difference in the portfolio writeup. True FOC current control would require a driver with
> shunts (e.g. SimpleFOC Shield v2); not needed for this project.

---

## 4. Encoders — AS5600 magnetic (×3)

Bundled and pre-mounted on each motor's hollow-shaft magnet; reads to the Teensy over I2C.

| Parameter | Value | Notes |
|---|---|---|
| Type | 12-bit magnetic rotary encoder, I2C | absolute single-turn |
| **I2C address** | **0x36 — FIXED** | standard AS5600 has *no* address pins ⚠ |
| Supply | 3.3 V | onboard pull-ups present |

> ⚠ **The AS5600 address is hardwired to 0x36 and cannot be changed.** Three of them therefore
> **cannot share one I2C bus.** The solution is one encoder per Teensy bus (see §6). *(Only the
> AS5600**L** variant has a programmable address — confirm which you have.)*

> **Phase-2 timing note:** `Wire` reads are blocking; three sequential AS5600 angle reads at
> 400 kHz cost ~300 µs of the 1000 µs loop tick. Fine for one encoder (Phase 1); at three,
> stagger the reads, run encoders below the control rate, or go non-blocking.

---

## 5. IMU — SparkFun Qwiic ISM330DHCX (×1)

ST 6-axis (raw accel + gyro, no on-chip fusion). *Replaces the ICM-42688-P in the brief.*

| Parameter | Value | Notes |
|---|---|---|
| Interface | I2C / Qwiic | also 0.1" pins; 3.3 V (direct to Teensy, no level shift) |
| I2C address | ~0x6B | ADR jumper open; confirm with a bus scan |
| Accel full-scale | ±2 / ±4 / ±8 / ±16 g | likely **±4 g** (tilt resolution + impact margin) |
| Gyro full-scale | ±125 … ±4000 dps | **±500–1000 dps** for balance; widen for hop-up |
| Features | FIFO, interrupts, ML core/FSM | ML core unused — fusion is written from scratch |

---

## 6. I2C bus map

Because all three AS5600s answer to **0x36**, each gets its own bus. The IMU (0x6B) is free to
share, since its address differs.

| Bus | Pins (SDA/SCL) | Devices | Phase |
|---|---|---|---|
| `Wire`  | 18 / 19 | AS5600 #1 (0x36) **+** ISM330DHCX (0x6B) | Phase 1 + |
| `Wire1` | 17 / 16 | AS5600 #2 (0x36) | Phase 2 |
| `Wire2` | 25 / 24 | AS5600 #3 (0x36) | Phase 2 |

No I2C multiplexer needed — the Teensy's three native buses cover all three encoders. Internal
pull-ups on the T4.1 are weak, but every device board here ships its own pull-ups, so a single
device (or the IMU+encoder pair) per bus is fine.

> **The three-bus choice has a downstream cost.** `Wire2` claims pins 24/25, which are also
> FlexPWM1's sm2-X and sm3-X. That reduces FlexPWM1's usable PWM outputs to `{0, 1, 7, 8}` and
> forces one stray wire in the M3 harness bundle (§11.3). Traceable all the way back to the
> AS5600's fixed 0x36 address. Worth stating plainly in the portfolio writeup: *a sensor's I2C
> addressing scheme propagated into the motor wiring harness.*

---

## 7. Power architecture & SimpleFOC limits

```
  USB ──► Teensy 4.1 (+ IMU, + AS5600 logic via Teensy 3.3 V)
                │
                └── PWM ×3 + EN ──► SimpleFOC Mini ×3 ──► motor phases (UVW)
  4S LiPo ──────────────────────────► VM (motor supply only)
                                       │
        COMMON GROUND  ◄── battery GND ─┴─ Teensy GND  (MANDATORY)
```

Full distribution topology, connector ICD and pin map: **§11**.

- **4S LiPo** (650 mAh — locked, see §10): 14.8 V nom / 16.8 V full / ~12 V cutoff. Stays clear of
  the driver's 8 V floor across the whole discharge, and matches the TVC-rocket bus.
- **Voltage tension:** 4S full charge (16.8 V) sits just above the motor's 16 V rated operating
  ceiling (under the 20 V abs max). Resolved in software: under voltage-mode torque control the
  commanded phase voltage never exceeds `voltage_limit`, so the full bus is never applied to the
  windings. **Set `voltage_limit ≈ 14.5 V`** (below the 16.8 V full-charge bus; gives the 217 rad/s
  flat-torque region / 334 rad/s asymptote of §2) **and `current_limit = 2.0 A`** (estimated — §3).
  The envelope sags as the pack discharges, so run recovery/shove tests on a reasonably charged pack.
- **Common ground is mandatory** — logic (USB) and motor power (LiPo) are separate domains; the
  PWM/EN signals are ground-referenced, so the grounds must be tied, **at the star node** (§11.5).
- **Phase 3 watch item:** hard braking during the hop-up regenerates energy onto the bus and can
  push it toward the 20 V abs max — brake chopper before Phase 3 (see §9).

### SimpleFOC config (per motor — closed loop)

```cpp
BLDCMotor      motor  = BLDCMotor(7);          // 7 pole pairs
motor.phase_resistance = 2.55;                 // ohms  (Rs)   -> enables current ESTIMATION
motor.phase_inductance = 0.00086;              // henries (0.86 mH)
motor.KV_rating        = 220;                  // RPM/V        -> enables back-EMF estimation
motor.torque_controller = TorqueControlType::voltage;  // the only mode this driver supports
motor.voltage_limit    = 14.5;                 // V — CLOSED LOOP ONLY. Open loop: 2-3 V (§2)
motor.current_limit    = 2.0;                  // A — motor hard max (estimated, no shunts)
// AS5600 sensor on its own I2C bus (addr 0x36); MagneticSensorI2C per motor
```

---

## 8. Balance wheel — machined C360 brass, spoked (×3)

*Supersedes the earlier printed-PETG / 75 mm / 5.0e-5 plan. The wheel is now CNC-machined in
brass: the larger OD reachable in metal moved the recovery-envelope optimum up, and the target is
set at the multi-swing-pump-up floor so one wheel can serve Phase 1–3 (see §9).*

| | |
|---|---|
| Type | **CNC-machined C360 free-machining brass, spoked rim-loaded disc (×3)** |
| Material | **C360** (machinability 100). *Not C260* — that's a cold-forming alloy (machinability ~30, gummy); identical density (~8500 kg/m³) so it'd hit the inertia but machines poorly |
| Stock | **1/8″ (3.175 mm) C360 plate**, full thickness retained on rim / spokes / hub |
| OD | **87 mm** (CAD-confirmed: ~2 mm inter-wheel gap at the shared corner, clears the ground-contact corner/edges) |
| Geometry | **Spoked:** rim **5.9 mm** wide at full 1/8″; **4 narrow (~4 mm) full-depth spokes**; **through-pockets** between spokes; **4 mm fillets** at spoke↔rim and spoke↔hub junctions; hub Ø set by the 2804 bell bolt pattern |
| As-designed mass | **65.2 g each** (SolidWorks; from a ~160 g solid 1/8″ blank → ~95 g removed) |
| **Spin-axis inertia** | **disk 7.63e-5 kg·m² (Lzz 76,304 g·mm²) → 8.00e-5 kg·m² reflected** (incl. rotor 3.7e-6). Hit dead-on in CAD — no trim, one-and-done |
| Mount / register | **Center pilot** locates the wheel: ~4–5 mm spigot, ~0.03 mm slip-fit into the bell's 6.5 mm **rotating** bore (machine to fit), seats on the bell **face** (must not bottom). **3× M2.5** clearance holes at **2.8–2.9 mm** — bolts clamp, pilot centers; edge distance ≥1.5× hole Ø. **No trim screws** — the tight build can't take rim protrusions, so inertia is hit in CAD instead |
| Balance | **Confirmed in SolidWorks:** CM at X = Y = 0, all products of inertia zero, Z a clean principal axis. Cut the pilot and rim in one setup to hold concentricity (runout = wobble = imbalance) |

**Verified (2026-06-09, mass estimates m ≈ 0.70 kg / I_bar ≈ 5.0e-3):** sim-confirmed balanced at
8.0e-5 — `run.py` catches a 3° release + 1.0 rad/s shove down to 0.13° final tilt, peak wheel speed
121 rad/s = **56 % of the 217 rad/s flat-torque region**. Large saturation margin → the system is
torque-limited, not momentum-limited, as expected. Max recoverable shove ≈ **1.6 rad/s (~93 °/s)**;
balance holds with stock gains across m 0.6–0.9 kg, I_bar 4–6e-3.

**Why ~8e-5 (not the old 5.0e-5, not more):** at 87 mm OD the recovery-envelope optimum sits on a
broad plateau ~7.5e-5; the target is nudged to **8e-5 because that is also the floor for a
multi-swing pump-up hop**, so the *same* wheel covers Phase 1–3 with no swap. The balance cost of
8e-5 vs the pure 7.5e-5 optimum is ~1–1.5 % of envelope — inside the rotor-estimate and
mass-tensor uncertainty. Past ~8e-5, extra inertia is flat (you're already past the saturation
knee) while the added mass *shrinks* the torque-limited envelope — balancing is torque-bound, not
momentum-bound (τ ceiling 0.087 N·m is fixed by the motor, §2). Bigger OD is the efficient lever:
I ∝ m·r², so 87 mm hits 8e-5 at lower rim mass.

**Why spoked + full thickness (the machining principle):** out-of-plane stiffness scales as
**thickness³**, so *never* thin a feature to save mass — drop a spoke 1/8″→2 mm and you keep 63 %
of the mass but only 25 % of the stiffness. Minimize mass **in-plane** (through-pockets between
narrow, full-depth spokes), keep rim/spokes/hub at full 1/8″. Strength is a non-issue (0.087 N·m
peak → trivial stress); the real constraint is **trueness** — a flat, concentric wheel that doesn't
wobble (which also keeps the IMU clean) and whose first resonance sits well above the ~50 Hz top
spin rate.

**Tooling (C360):** 2-flute, **uncoated**, carbide (or HSS — C360 is soft), **low/neutral rake,
lower helix** — avoid "for-aluminium" high-helix/high-rake mills, which *grab* in brass. A 1/4″ mill
(leaves a 1/8″-radius inside corner) cuts the whole wheel if fillets are ≥1/8″ R and pockets stay
>~6.5 mm. Rough the pockets while the blank is rigid; profile the thin rim last; back
through-pockets with a sacrificial plate.

**Phase 3:** plan is a **multi-swing pump-up** using this same ~8e-5 wheel (no second wheel). The
pump-up momentum budget must use the *tapered* τ(ω) envelope of §2 — spin-up slows past 217 rad/s
and the last ~30 rad/s before 334 is effectively unreachable under load. A dedicated single-dump
hop wheel (~16e-5, brass) remains the fallback — the **hub is designed modular to accept a heavier
rim** either way.

---

## 9. Still open (not yet locked)

- ~~PWM pin map / star-ground topology~~ → **✅ LOCKED, §11.2 / §11.5**
- ~~VBAT sense divider~~ → **✅ LOCKED, §11.6**
- ~~BEC + VUSB↔VIN cut sequencing~~ → **✅ LOCKED (deferred to post-Phase-1), §11.7**
- ~~Battery capacity~~ → **✅ locked: 4S 650 mAh** (§10)
- ~~Wheel OD / inertia~~ → **✅ 87 mm, 8.00e-5 reflected, balance confirmed** (§8)
- ~~`voltage_limit`~~ → **✅ 14.5 V closed-loop; 2–3 V open-loop** (§2, §7)

**Genuinely still open:**

- **Ballast final mass & position** — ~45–50 g brass at the far corner closes the CM (working
  numbers in §10); finalize against the *full* SolidWorks assembly and the weighed pack.
- **Full-assembly mass tensor** — the 418 g / 4,810 g·mm CM figures in §10 predate the
  aluminum-frame lock. Re-run against the as-built space-frame, then feed `params.py`.
- **IMU accel/gyro full-scale** selection (balance range now; **widen the gyro for the Phase-3
  hop** — the pump-up still slews fast).
- **Phase 3 regen-overvoltage mitigation** — brake chopper (power resistor + MOSFET on bus
  overvoltage); required for *any* hop-up, pump-up included. **Energy sized:**
  E = ½·I_w·ω² ≈ **1.9 J per wheel** braking from the 217 rad/s knee (worst case ~4.2 J from a
  334 rad/s coast — don't plan to be there). Single-event energy is trivial for any chassis-mount
  power resistor; the design driver is the *dump rate* during a hard brake (sets resistor wattage +
  MOSFET trip point). Size when Phase 3 starts. Trip signal comes from the §11.6 VBAT sense.

---

## 10. Frame & battery

- **Frame:** pre-tensioned aluminum space-frame — a 12-tube 6063 cage + 8 machined corner blocks, a
  central machined-aluminum motor hub, suspended by **7 pre-tensioned 1/8″ stranded-cable stays**
  (no rigid strut; 7 = 6 to constrain + 1 to prestress). **Full spec lives in
  `FRAME_BUILD_GUIDE.md`** (the frame source of truth). Cube edge `E` is **open pending the CAD
  inter-wheel / stay-clearance check**. Supersedes the old 3D-printed PETG ~100 mm cube.
- **Battery: 4S LiPo 650 mAh — LOCKED.** Typical pack: ~60 × 31 × 21 mm, **70–85 g**
  (brand-dependent — **weigh the actual pack** and feed the number to the CM analysis and
  `params.py`). Peak draw 3 × 2 A = 6 A ≈ **9 C** — any ≥25 C pack loafs; capacity gives well over
  an hour of balancing per charge at typical duty.
- **Battery placement + brass ballast (the CM plan).** Placement is a controls decision, not
  packaging: as-modeled (no battery) the assembly is **418 g with the CM at (+11.5, +11.6, +11.5)
  mm** — ~20 mm up the body diagonal toward the three-wheel corner — so **4,810 g·mm of
  countermoment per axis** is needed. A 650 pack (~75 g) at a practical interior placement (~38 mm
  per axis toward the (−,−,−) corner) supplies only **~2,850 g·mm (≈ 59 %)**. Close the remainder
  with **~45–50 g of brass ballast** packed deeper into the far corner (~42 mm per axis) — the
  wheel-blank offcuts are free stock. Net: battery + ballast ≈ **122 g** does the job of the old
  150 g / 1500 mAh plan at *lower* total mass, and dense brass is more precisely placeable than a
  battery brick. Keep both near the [1,1,1] diagonal to preserve Ixx ≈ Iyy ≈ Izz and the diagonal
  principal axis. **The 418 g / 4,810 g·mm figures predate the aluminum-frame lock — re-run the
  full mass tensor against the as-built space-frame before committing ballast.**

---

## 11. Electrical wiring, pin map & harness ICD — **LOCKED (Rev C)**

The pin map below is a decision, not a proposal. It is a hard dependency for the firmware skeleton
and for the harness build. Drawing: `cubli_wiring_reference.html`.

### 11.1 SimpleFOC Mini — what every pin connects to

| Mini pin | Connects to | Domain |
|---|---|---|
| `VM`, `GND` (power header) | Distribution board → 4S bus | Motor power (14.8 V nom) |
| `A`, `B`, `C` | Motor phases U / V / W (MX1.25, 3-pin) | Motor power |
| `IN1`, `IN2`, `IN3` | Three Teensy FlexPWM pins (§11.2) | 3.3 V logic |
| `EN` | One Teensy digital pin, per motor | 3.3 V logic |
| `GND` (logic header) | Teensy GND — **routed inside the signal bundle** | Signal reference |
| `3V3` out | **Nothing. Leave floating.** | — |

**Two failure modes to design against.**

1. **The logic-side `GND` is not "just another ground."** It is the reference the DRV8313 compares
   the incoming PWM/EN levels against. It rides in the JST GH signal bundle with the four signals it
   references — *not* bundled with the motor return. A signal ground sharing an impedance path with
   6 A of switched phase current is the textbook common-impedance coupling failure, and it presents
   as I2C corruption and phantom controller instability, not as an obvious wiring fault.
2. **The Mini's `3V3` out is a 10 mA LDO** (§3). Tying it to the Teensy's 3.3 V rail parallels two
   regulators with no droop sharing. Leave the pin open.

**Phase order (`A`/`B`/`C` → U/V/W):** arbitrary at build time; the pairing sets the sign of
rotation, and `initFOC()` discovers the sensor direction and electrical zero at startup. What
matters is that the mapping is *recorded per axis* and identical across rebuilds (§11.8).

### 11.2 Teensy 4.1 pin map — LOCKED

| Motor | IN1 | IN2 | IN3 | EN | FlexPWM module · channel | Harness bundle | Encoder bus |
|---|---|---|---|---|---|---|---|
| **M1** (Phase 1) | **4** | **5** | **6** | **3** | PWM2 · sm0A / sm1A / sm2A | **pins 3–6, contiguous** | `Wire` (18/19) |
| **M2** | **22** | **23** | **2** | **21** | PWM4 · sm0A / sm1A / sm2A | 21–23 + one stray at 2 | `Wire1` (17/16) |
| **M3** | **8** | **7** | **1** | **9** | PWM1 · sm3A / sm3B / sm0X | 7–9 + one stray at 1 | `Wire2` (25/24) |

| Other signal | Pin | Notes |
|---|---|---|
| VBAT sense | **41** (`A17`) | 68 k : 10 k divider + 100 nF — §11.6 |

**Reserved, do not reallocate:** 16, 17, 18, 19, 24, 25 (the three I2C buses).
**Never use for a phase:** 10–15, 18, 19 — **QuadTimer**, not FlexPWM. SimpleFOC's Teensy-4 3PWM
wants FlexPWM pins; keep every phase on a FlexPWM channel (see §11.4).

### 11.3 Why these pins — the derivation

All three phases of one motor must sit on **one FlexPWM module** so they share a carrier. Phases on
different modules run on free-running, mutually unsynchronized counters; the inverter legs then
switch incoherently and the applied voltage vector is not what the modulator thinks it is.

**Accessible FlexPWM outputs on the Teensy 4.1** (pins 42–47, 51, 54 are SD-card / bottom pads and
are not usable):

| Module | sm0 | sm1 | sm2 | sm3 |
|---|---|---|---|---|
| **FlexPWM1** | X = 1 | X = 0 | X = 24 ❌ | A = 8, B = 7, X = 25 ❌ |
| **FlexPWM2** | A = 4, B = 33 | A = 5 | A = 6, B = 9 | A = 36, B = 37 |
| **FlexPWM3** | — | A = 29, B = 28 | — | — |
| **FlexPWM4** | A = 22 | A = 23 | A = 2, B = 3 | — |

❌ = consumed by `Wire2`, which has no alternate pins.

- **`Wire2` costs us FlexPWM1.** Its usable outputs collapse to `{0, 1, 7, 8}` — two adjacent pairs
  with a six-pin gap. **M3's stray wire is the price of the third I2C bus,** which is itself the
  price of the AS5600's fixed 0x36 address (§4).
- **FlexPWM3 cannot drive a motor.** Only submodule 1 is brought out (28/29). One submodule cannot
  host three independently-modulated phases.
- **FlexPWM4's third submodule surfaces only at pin 2 or 3**, on the opposite header row from
  22/23. M2's stray is therefore also forced.
- **No two motors may share a FlexPWM module.** FlexPWM2 has enough outputs for two motors, but only
  by sharing a submodule between two `BLDCDriver3PWM` instances — two driver objects writing the
  same submodule's counter registers. Untested and unnecessary.

**Therefore the allocation is forced:** PWM2 → M1, PWM4 → M2, PWM1 → M3. Two stray wires across the
whole harness is the floor, not a compromise.

**EN pins** need no timer, only a digital output, so each sits adjacent to its motor's phase group:
`3` for M1 (FlexPWM4 sm2-B, unused as a timer), `21` for M2 (plain GPIO), `9` for M3 (FlexPWM2 sm2-B,
unused as a timer). Driving a pin as GPIO re-muxes only that pin and does not disturb the submodule
counter its sibling channel uses.

**Why three separate EN lines** — a bring-up safety feature, not a convenience. It lets you
hardware-isolate two motors *at the driver* while characterizing the third. "Commanded to zero in
firmware" is not isolation; a bad `initFOC()` or a sign error still energizes the phases.

### 11.4 Firmware config

> ### ⚠ PIN THE LIBRARY: SimpleFOC **2.3.5**. Do NOT use 2.4.0.
> **SimpleFOC 2.4.0's Teensy-4 driver is broken:** `driver.init()` reports success and configures
> the FlexPWM (both fast-pwm and center-aligned), but **no PWM reaches the pins — 0 V output, motor
> dead.** Verified 2026-07-14 on this exact hardware: raw `analogWrite` on pins 4/5/6 worked, yet
> SimpleFOC 2.4.0 produced nothing. **Downgrading to 2.3.5 fixed it instantly** — the default
> fast-pwm 3PWM path spins the motor. This cost an afternoon; it is the first thing to check if the
> motor ever goes silent after a library update.
>
> Debugging lesson worth keeping: `driver.init()` returning `1` and printing a happy config line is
> **not** proof of output. Confirm PWM with a meter on the pins, or with `SimpleFOCDebug::enable()`.

**Center-aligned 3PWM is NOT needed for this project.** It only matters for low-side current
sensing, and the SimpleFOC Mini has no shunts (§3). Plain fast-pwm 3PWM (the 2.3.5 default) is
correct for voltage-mode torque control. No `build_opt.h`, no library edits, no compiler flags.

```cpp
#include <SimpleFOC.h>   // library version 2.3.5 (see warning above)

BLDCDriver3PWM driver1 = BLDCDriver3PWM(4, 5, 6, 3);    // M1 — FlexPWM2
BLDCDriver3PWM driver2 = BLDCDriver3PWM(22, 23, 2, 21); // M2 — FlexPWM4
BLDCDriver3PWM driver3 = BLDCDriver3PWM(8, 7, 1, 9);    // M3 — FlexPWM1

driver1.pwm_frequency        = 25000;   // set explicitly; do not rely on the default
driver1.voltage_power_supply = 14.8;    // corrected at runtime from VBAT sense (§11.6)
```

**On 25 kHz:** above audible, and short against the motor's electrical time constant
τ = L/R = 0.86 mH / 2.55 Ω ≈ **337 µs**. The current ripple over one 40 µs period is therefore small
and the voltage-mode current *estimate* (§3) stays meaningful. Justify any change against τ.

### 11.5 Power distribution & star ground

```
  USB 5 V ──► Teensy 4.1 ──► 3.3 V rail ──► IMU + 3× AS5600   (~40–60 mA of a 250 mA rail)
                  │
                  ├── 3× (IN1,IN2,IN3,EN,GND) ──► SimpleFOC Mini ×3   [JST GH 5-pin]
                  │
  4S LiPo ──► XT30 loop key ──► 7.5 A fuse ──► DISTRIBUTION BOARD
                                                 ├─ 470 µF bulk
                                                 ├─ VM fan-out ×3 ──► Mini VM   [JST XH 2-pin]
                                                 ├─ VBAT divider ──► pin 41
                                                 └─ ★ STAR GROUND NODE  ◄── Teensy GND
```

- **Common ground is tied at the star node**, not opportunistically at the nearest GND pin. Motor
  return current must never share an impedance path with a signal reference. *(Spacecraft EPS
  practice, and the reason a "works on the bench, fails assembled" bug is almost always grounding.)*
- **470 µF bulk at the distribution board**, plus local decoupling at each Mini's `VM`. The lead
  inductance between bulk cap and half-bridge is what turns a switching edge into ringing overshoot.
- **Peak draw** 3 × 2 A = 6 A ≈ 9 C. The 7.5 A fuse sits above the 6 A peak, below the harness limit.

### 11.6 VBAT sense divider

> **Status: designed, NOT YET BUILT (2026-07-14).** Pin 41 currently floats — the bring-up
> sketch's ~6 V reading is noise on an unconnected ADC input, not a battery reading. Build the
> divider before relying on any VBAT telemetry or the undervoltage cutoff.

68 kΩ from the 4S bus to a node; 10 kΩ from that node to star ground; node → **pin 41 (`A17`)**;
**100 nF across the 10 kΩ**.

| Quantity | Value |
|---|---|
| Divider ratio | 10 / (68 + 10) = **0.128** |
| Reading at 16.8 V (full pack) | **2.15 V** — inside the 0–3.3 V ADC window |
| Full-scale bus (3.3 V at the pin) | **≈ 25.7 V** |
| Thévenin source impedance | 68k ‖ 10k ≈ **8.7 kΩ** |
| Quiescent draw | 16.8 V / 78 kΩ ≈ **215 µA** (negligible vs 650 mAh) |

**The 100 nF is not optional:** 8.7 kΩ is at the edge of what the Teensy's SAR ADC wants to see. The
cap gives the sampling capacitor a local reservoir so the conversion doesn't droop.

**Three jobs — this is a telemetry channel, not a battery gauge:**

1. **Undervoltage cutoff.** Drop all three EN lines at ~12 V (3.0 V/cell).
2. **Correct `voltage_power_supply` at runtime.** Under voltage-mode torque control the commanded
   torque *is* a voltage. If the bus sags and firmware assumes 14.8 V, the applied torque quietly
   scales down and the tuning drifts with state of charge. Feed the measured bus back each loop.
3. **Phase-3 regen overvoltage detection.** Trips the brake chopper before the bus reaches the
   motor's 20 V absolute max (§9).

> **Transfers to TVC verbatim.** Bus telemetry + undervoltage lockout is the same channel a flight
> vehicle's EPS carries, for the same three reasons.

### 11.7 BEC — 3 A, untethered only. **NOT INSTALLED.**

A 3 A / 5 V step-down off the 4S bus, feeding Teensy `VIN`, so the board runs without USB. Against a
~150 mA logic load, 3 A is comfortable margin.

> ### ⚠ The VUSB↔VIN pad must be cut **before** the BEC is ever connected.
> With the pad intact, feeding 5 V into `VIN` shorts the BEC output to the PC's USB rail.
> The cut is **not practically reversible** and it changes bench behavior immediately — the Teensy
> will no longer run from USB alone.
>
> **Sequencing rule (extends §12):** the BEC is fitted and the pad is cut only *after* Phase-1
> balancing is achieved on USB. It is not part of any bench bring-up.

### 11.8 Connector ICD

| Interface | Connector | Signals | Notes |
|---|---|---|---|
| Motor phases | MX1.25, 3-pin | U / V / W | Staked with RTV at the motor junction |
| Driver VM power | JST XH, 2-pin | VM / GND | Twisted pair back to the star node |
| Driver control | JST GH, 5-pin (gold) | IN1 / IN2 / IN3 / EN / **GND** | GND travels with the signals it references |
| Encoder & IMU I2C | Qwiic / JST GH | 3V3 / GND / SDA / SCL | One bus per encoder; keep runs short |

**Color-band and label all three axis harnesses at both ends.** Three identical subsystems is a
cross-wiring trap: a swapped M2/M3 bundle presents as a controller *sign error*, which you will hunt
in software for a weekend. **M1 = red, M2 = green, M3 = blue**, banded at both connector ends.

**Mounting:** boards on short standoffs, short load path into a structural member; target first mode
≳ 100 Hz to stay above the 0–50 Hz wheel excitation band; strain-relieve at every board. The failure
mode is **connector fatigue, not structure** — the boards are too light to disturb the dynamics, but
an under-constrained mount gives intermittent I2C that looks exactly like a firmware bug.

### 11.9 Bench rules — breadboard limits

| Breadboard is fine | Point-to-point wire only |
|---|---|
| Teensy, IMU, AS5600s, all I2C | **Motor phases (U/V/W)** |
| PWM / EN signal lines | **VM rail and its return** |
| VBAT divider | Bulk + local decoupling caps |

Breadboard contacts are rated ~1 A against a 6 A peak, carry tens of milliohms of contact
resistance, and add loop inductance exactly where di/dt is highest. Everything up to a valid Madgwick
quaternion is breadboard-safe; nothing past the loop key is.

---

## 12. Bring-up order (standing procedure — not a status)

1. **Logic before motor power.** Teensy on USB only, no battery, loop key **out**. Scan all three
   I2C buses; confirm 0x36 on each and 0x6B on `Wire` before trusting any reading.
2. **Continuity check.** Every harness GND → star node (<1 Ω). Ohm out each phase bundle: no
   phase-to-phase and no phase-to-GND short. **Do this on every re-mate.** Re-seating a connector is
   exactly when a strand bridges.
3. **IMU first light.** Raw accel + gyro clean over serial; sanity-check axes, units, bias, noise.
4. **Madgwick.** Valid, stable quaternion at rest and under hand rotation.
5. **Sensor check.** AS5600 angle monotonic and wrapping cleanly when the rotor is turned by hand.
6. **Then motor power.** All EN lines LOW → insert loop key → verify VBAT sense reads within ~2 % of
   a meter on the pack.
7. **Open loop, M1 only, `voltage_limit = 2–3 V`** (§2 ⚠). M2/M3 held disabled at the driver.
8. **`initFOC()`** on M1 — sensor alignment. Only then does `voltage_limit` return to 14.5 V.

> **Step 6 is the boundary.** Everything before it is recoverable; a wiring error after it is a dead
> driver, a dead Teensy, or a LiPo event.

---

## Changelog vs. original brief

| Item | Brief said | Actually using | Why |
|---|---|---|---|
| IMU | ICM-42688-P | **SparkFun ISM330DHCX** | ICM-42688-P supply crunch; ISM is raw 6-axis (learning goal intact) |
| Motor | GBM2804 / MN3110, "low-KV 600–1200" | **QiuLovesYT 2804, 220 KV** | 220 KV is genuinely low-KV; the "600–1200" figure was backwards |
| Driver | SimpleFOC Mini (separate) | SimpleFOC Mini (**bundled** w/ motor kit) | same board, came in the kit |
| Driver torque mode | (implied closed current loop / "FOC") | **Voltage-mode torque w/ estimated current** | SimpleFOC Mini has **no current sensing**; `current_limit` is enforced by estimate (§3) |
| Encoder | (implied AS5600) | **AS5600 ×3, pre-mounted** | bundled; note the fixed-0x36 / 3-bus constraint |
| Frame | ~150 mm printed PETG cube | **Pre-tensioned aluminum space-frame** (`FRAME_BUILD_GUIDE.md`) | Machined frame for stiffness + a precision perpendicular hub (PETG drifts/creeps) |
| Flywheel | brass C360, ~80 mm × ~20 mm placeholder | **CNC C360 brass, spoked, 87 mm OD, 5.9 mm rim, 1/8″ stock, 65 g, center-pilot register** | Metal OD reachable (87 mm) moved the optimum up; one wheel now covers all phases (§8) |
| Wheel inertia | I_w 3.68e-5 / 4.05e-5 reflected | **8.00e-5 reflected** (hit dead-on in CAD, sim-confirmed) | Larger OD lifted the envelope plateau (~7.5e-5); 8e-5 = the pump-up-hop floor, so one wheel serves Phase 1–3 |
| `voltage_limit` | (open) | **14.5 V closed-loop; 2–3 V open-loop** | Closed loop: flat torque to ~217 rad/s, zero at ~334, below the 16.8 V full-charge bus. **Open loop has no back-EMF — 14.5 V would draw 5.7 A into a 2 A motor (§2 ⚠)** |
| Battery | 4S, capacity TBD (1500–2200) | **4S 650 mAh (~75 g) + ~45–50 g brass corner ballast** | CM closed at *lower* total mass than a big pack (122 g vs 150+ g); 9 C peak draw is trivial; brass is a more precise CM lever (§10) |
| M1 drive pins | (not specified) | **IN 4 / 5 / 6, EN 3** — FlexPWM2 | One FlexPWM module per motor; bundle fully contiguous |
| M2 drive pins | (not specified) | **IN 22 / 23 / 2, EN 21** — FlexPWM4 | FlexPWM4's third submodule surfaces only at pin 2/3 — the stray wire is forced |
| M3 drive pins | earlier draft: 8 / 7 / ~~29~~, EN 32 | **IN 8 / 7 / 1, EN 9** — FlexPWM1 | **Defect fix.** The draft straddled FlexPWM1 *and* FlexPWM3 — two unsynchronized carriers on one motor. `Wire2` blocks 24/25, leaving FlexPWM1 with only {0,1,7,8} |
| EN pins | earlier draft: 30 / 31 / 32 | **3 / 21 / 9** | Placed adjacent to each motor's phase group so the 5-wire bundle leaves the board from one place |
| PWM mode | (implied default) | **`SIMPLEFOC_TEENSY4_FORCE_CENTER_ALIGNED_3PWM`**, 25 kHz | SimpleFOC does not center-align or sync 3PWM on Teensy 4 by default; the flag requires FlexPWM-only pins |
| VBAT sense | (not specified) | **Pin 41 (`A17`), 68 k : 10 k + 100 nF**, ≈26 V FS | Undervoltage lockout, runtime `voltage_power_supply` correction, Phase-3 regen trip |
| BEC | "~45 A BEC planned" | **3 A, 5 V — deferred to post-Phase-1** | 45 A was a note error. The VUSB↔VIN cut is irreversible and changes bench behavior; sequenced after Phase 1 |
| Power topology | (not specified) | **XT30 loop key → 7.5 A fuse → star-ground distribution board, 470 µF bulk** | Star ground prevents common-impedance coupling between motor return and signal reference |
