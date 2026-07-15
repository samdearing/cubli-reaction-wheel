# Cubli build — design considerations

*The frame is a controls component, not a chassis. Every line below exists to protect the
plant your PID/LQR will later run on.*

---

## ★ The three non-negotiables
If you read nothing else tonight — everything else serves these:

1. **CM at the geometric centre.** The battery **+ brass ballast** are the lever that gets you there.
2. **The three wheel faces truly perpendicular (square).** Keeps the torque-allocation map 1:1.
3. **A rigid frame.** Flex is unmodeled dynamics; the controller assumes a rigid body.

---

## 1. Mass & balance — the controls part
- CM → geometric centre. The three motors bias it toward their shared corner (~4,810 g·mm
  per axis as-modeled); counter with the **4S 650 battery (~75 g) placed toward the
  *opposite* corner** plus **~45–50 g of brass ballast packed deeper into that corner** —
  the 650 pack alone covers only ~59 % of the countermoment. Working numbers in
  `HARDWARE.md` §10; finalize against the full assembly and the weighed pack.
- Products of inertia (Ixy, Ixz, Iyz): the motors on face-centres give you **zero** for free;
  off-centre battery/ballast reintroduce them. Keep both near the [1,1,1] diagonal, then
  **measure the real tensor in SolidWorks and feed it to the controller** — the LQR needs a
  *known* tensor, not necessarily a diagonal one.
- **Total mass is the enemy.** Every gram shrinks the torque-limited recovery envelope
  (~224 g of electronics roughly *halves* it). Don't over-build the frame. (This is exactly
  why 650 mAh + brass beats a 1500+ mAh pack: same CM fix, ~30 g lighter.)
- Assign **real material densities** in SolidWorks (PETG ≈ 1270, brass ≈ 8500, steel ≈ 7700
  kg/m³) or every mass-property number is fiction.

## 2. Geometry & fit
- ~100 mm PETG cube; three motors on three mutually perpendicular faces meeting at one corner;
  spin axes = body axes x / y / z.
- **87 mm wheels** (CAD-confirmed): inter-wheel clearance near the shared corner is the binding
  packing constraint — holds ~2 mm gap at the shared vertex. Wheels must not protrude past the
  cube silhouette or into the ground-contact corner/edges.
- Motor hub must match the **bell bolt pattern** (hole count + bolt-circle diameter).
- Don't obstruct the hollow shaft or the pre-mounted AS5600 magnet ring — leave room and the
  correct **air-gap** for each encoder behind its motor.
- Define the **contact geometry**: the three edges it balances on (**Phase 1**) and the corner
  (**Phase 2–3**). A small, repeatable, slightly rounded contact point beats a sharp printed
  corner that chips and changes your pivot.
- Route channels for phase leads (MX1.25), the Qwiic/I2C runs, and the battery leads.

## 3. Flywheels
- **8.00e-5 kg·m² reflected** (disk 7.63e-5 + rotor 3.7e-6). **CNC-machined C360 brass, spoked,
  87 mm OD, 5.9 mm rim, 1/8″ plate, 65 g** — hit dead-on in CAD, **one-and-done, no trim screws**
  (the tight build can't take rim protrusions, so the inertia is dialed in the model instead).
  (Was printed PETG / 5.0e-5; metal let the OD grow, which lifted the optimum, and 8e-5 = the
  multi-swing-pump-up floor so one wheel covers all phases.)
- **Minimize mass in-plane, never by thinning.** Out-of-plane stiffness goes as **thickness³** —
  keep rim, spokes, and hub at full 1/8″ and remove mass with **through-pockets** between
  **3–4 narrow (~4 mm) full-depth spokes**. Strength is free here (0.087 N·m peak → trivial
  stress); the constraint is **trueness/stiffness**, not strength.
- Read inertia as **Izz about the spin axis**, wheel centred on the shaft axis.
- Keep CM on the spin axis and products zero → no vibration. (A shaky wheel at speed corrupts
  the IMU reading too — balance helps *sensing*, not just dynamics.) **Hold hub-bore-to-rim
  concentricity** in machining — runout = wobble = imbalance.
- **Mount on a center pilot, not the bolts.** A short spigot (~4–5 mm) slip-fits (~0.03 mm) into
  the bell's rotating bore and *centers* the wheel; the M2.5 bolts (2.8–2.9 mm clearance) only
  clamp. Keep the pilot short so the wheel seats on the bell **face**, not bottomed in the bore,
  and well clear of the encoder magnet at the bottom. Brass is non-magnetic, so it won't disturb
  the AS5600 field even near it.
- Mass at the rim is most efficient (inertia ∝ r²); the bigger OD hits the target at lower mass.
- **Tooling (C360):** 2-flute, uncoated, low/neutral-rake (avoid for-aluminium high-helix mills —
  they grab in brass). A 1/4″ mill cuts the whole part if inside fillets are ≥1/8″ R.
- **Keep the blank offcuts** — they're the CM ballast stock (§1).
- **Phase 3 is a multi-swing pump-up on this same wheel** — no heavier wheel needed. But still
  design the hub **modular** to accept a dedicated single-dump hop rim (~16e-5) as a fallback.

## 4. Structure & stiffness
- The three **motor mounts carry the reaction torque** — make them the stiffest parts.
  Rib/triangulate them; print solid or high-infill with layers across the load.
- Frame flex shifts resonances into your control bandwidth and makes the IMU read frame
  *ringing* instead of body attitude.
- Design for **repeated assembly/disassembly** — you'll be in and out of this many times.
  Heat-set inserts / captive nuts beat printed threads; keep fastener access clear.

## 5. Electronics, wiring & power
- Teensy on **USB** (logic); 4S LiPo → SimpleFOC **VM only**; **common ground mandatory**
  (tie battery GND to Teensy GND or the drivers can't read the PWM).
- **Torque control is voltage-mode with *estimated* current** — the SimpleFOC Mini has no
  current sensing, so `current_limit = 2.0 A` is an estimate riding on Rs, not a measurement.
  Set `phase_resistance` and `KV_rating` so the library can estimate well (see `HARDWARE.md` §3).
- Three I2C buses: encoder #1 + IMU on `Wire`; encoders #2/#3 on `Wire1`/`Wire2`. Wire only #1
  for Phase 1, but **route all three now** so Phase 2 isn't a teardown.
- IMU: mount rigidly to a stiff member, ideally near the CM, axes aligned to the body frame —
  and **write down the sensor→body rotation.** You'll need it, and it must transfer verbatim
  to the rocket.
- Keep driver-to-motor leads short; 680 µF/25 V across VM near the drivers; inline fuse and
  correct cap polarity **before** motor power.
- `voltage_limit = 14.5 V`, `current_limit = 2.0 A`. Battery **and ballast** sit in their final
  slots even in Phase 1, so the CM you tune against is the real one.
- Phase 3 only: regen brake chopper (~1.9 J/wheel from the 217 rad/s knee — sized in
  `HARDWARE.md` §9) — not now, just leave bus headroom in mind.

## 6. Build sequence (Phase 1)
- Build the **complete** mechanical cube + all electronics in final position → Phase 1 becomes a
  true *subset* of the final config, so your tuning transfers instead of being throwaway.
- Power **one** motor only (its driver + AS5600 on `Wire`, IMU on `Wire`). The other two are
  installed **dead mass**.
- Balance on the edge whose pivot runs **parallel** to the active wheel's spin axis.
- Idle wheels: leave unpowered — cogging holds them, and their axes don't couple into your tip axis.

---

## Before you cut or print — the CAD loop
Model every part with real densities → drop in McMaster bolt CAD → pull **Mass Properties** on
the *full assembly* (battery + ballast in their slots) → check CM at centre and products near
zero → nudge battery/ballast placement → only then commit. Log the final mass tensor in the
repo — it's both portfolio gold and the controller's input.
