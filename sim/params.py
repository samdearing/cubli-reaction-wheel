"""
Physical parameters for the Cubli single-axis (Phase 1) edge-balancing plant.

Two groups, with very different trust levels:
  MOTOR  - LOCKED to HARDWARE.md (QiuLovesYT 2804 + SimpleFOC Mini). Do not guess these;
           they are measured/spec'd and they set your real actuator ceilings.
  PLANT  - ESTIMATES for a ~100 mm PETG cube on edge. Replace m, l, I_bar with your
           SolidWorks Mass-Properties numbers the moment you have them. That swap is the
           "feed the real tensor to the controller" step from your build doc.

Frames (we state the convention every time):
  Inertial frame I : fixed to the bench. z_I points up (against gravity); x_I lies along
                     the pivot edge.
  Body frame     B : glued to the cube. x_B is shared with x_I -- that shared axis is the
                     whole reason this collapses to a SINGLE rotation.
  theta            : rotation of B relative to I about the shared x-axis, measured from
                     upright (CM stacked over the pivot). This is what Madgwick estimates.
  The reaction wheel spins about an axis parallel to x_B; alpha is the wheel angle RELATIVE
  to the body -- exactly the quantity the AS5600 reads.
"""

from dataclasses import dataclass

G = 9.81  # m/s^2, gravitational acceleration


@dataclass(frozen=True)
class Motor:
    """As-purchased 2804 / SimpleFOC Mini. Numbers are from HARDWARE.md.

    NOTE (hardware reality): the SimpleFOC Mini has NO current-sense shunts, so on the
    Teensy this is voltage-mode torque control with ESTIMATED current (SimpleFOC uses
    phase_resistance + KV to estimate and limit current). I_lim below is therefore
    enforced by estimate, not measurement -- copper Rs rises ~0.4%/degC, so a hot
    winding draws slightly more than the estimate believes. Low torque duty keeps this
    benign for balancing, but it is a real margin, not a measured limit."""
    Kt: float = 0.0434          # N.m/A   torque constant
    Ke: float = 0.0434          # V.s/rad back-EMF constant (= Kt, self-consistent w/ KV)
    Rs: float = 2.55            # ohm     phase resistance
    V_lim: float = 14.5         # V       SimpleFOC voltage_limit -> sets the speed ceiling
    I_lim: float = 2.0          # A       SimpleFOC current_limit -> the motor hard max
    rotor_inertia: float = 3.7e-6  # kg.m2  (already folded into PLANT.I_w below)

    @property
    def tau_stall(self) -> float:
        """Peak torque at zero wheel speed: Kt * I_lim ~= 0.087 N.m."""
        return self.Kt * self.I_lim

    @property
    def omega_flat_end(self) -> float:
        """End of the FLAT-torque region: below this speed the current limit binds and
        the full tau_stall is available; above it, back-EMF eats the voltage budget and
        torque tapers linearly to zero. (V_lim - I_lim*Rs)/Ke ~= 217 rad/s.
        THIS is the speed that matters for momentum budgets, not omega_zero_torque."""
        return (self.V_lim - self.I_lim * self.Rs) / self.Ke

    @property
    def omega_zero_torque(self) -> float:
        """Wheel speed where back-EMF consumes the whole voltage budget -> torque 0.
        ~334 rad/s. The wheel can coast here but cannot accelerate under load -- treat
        it as an asymptote, not an operating point."""
        return self.V_lim / self.Ke


@dataclass(frozen=True)
class Plant:
    """~100 mm PETG cube balancing on the edge parallel to the active wheel's spin axis.

    m, I_bar derivation (2026-06-09, all [ESTIMATE -> SolidWorks]):
      as-modeled assembly (SolidWorks, no battery/ballast) ........ 418 g
      battery: 4S 650 mAh LiPo (typ. 70-85 g; WEIGH THE REAL PACK)  ~75 g
      brass CM ballast at the far corner (see HARDWARE.md s.10) ...  ~47 g
      frame completion / wiring / fasteners margin ................ ~160 g
      total ~700 g. I_bar from the measured tensor (Ixx ~7.45e5 g.mm^2 about the
      geometric center) + battery/ballast/frame parallel-axis terms (~+8.1e5)
      -> ~1.56e-3 about the center axis, + m*l^2 (3.50e-3) about the pivot edge."""
    m: float = 0.70      # kg     total cube mass                          [ESTIMATE -> SolidWorks]
    l: float = 0.0707    # m      pivot edge -> CM distance; = (L/2)*sqrt(2) for a 100 mm cube
    I_bar: float = 5.0e-3  # kg.m2 body inertia about the pivot edge, NOT counting wheel spin  [ESTIMATE]
    I_w: float = 8.0e-5  # kg.m2  reflected wheel inertia, LOCKED: machined C360 brass spoked
                         #        disk 7.63e-5 (SolidWorks Lzz 76,304 g.mm^2) + rotor 3.7e-6.
                         #        Hit in CAD, no trim hardware. Re-verify vs the as-cut part.
    b_th: float = 3.0e-4  # N.m.s  tip-axis bearing/contact friction (small, stabilizing)
    b_w: float = 2.0e-6   # N.m.s  wheel bearing friction (small)


MOTOR = Motor()
PLANT = Plant()


if __name__ == "__main__":
    # Quick sanity print of the numbers that govern everything downstream.
    mgl = PLANT.m * G * PLANT.l
    print(f"mgl (gravity 'negative spring') = {mgl:.4f} N.m/rad")
    print(f"  -> you need Kp > {mgl:.4f} just to not fall")
    print(f"tau_stall        = {MOTOR.tau_stall:.4f} N.m")
    print(f"omega_flat_end   = {MOTOR.omega_flat_end:.1f} rad/s  (full torque available below this)")
    print(f"omega_zero_torque= {MOTOR.omega_zero_torque:.1f} rad/s  (asymptote -- torque is zero here)")
