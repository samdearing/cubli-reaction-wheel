"""
Motor torque ceiling for the 2804 / SimpleFOC Mini, as a function of wheel speed.

The controller can COMMAND any torque, but the hardware can only DELIVER what the
voltage/current budget allows at the current wheel speed. This module is the saturation
block that sits between controller.py and plant.py: command in, achievable torque out.

Electrical model (inductance dropped -- it governs current ripple, not the steady
envelope). For one phase circuit:

    V = I * Rs + Ke * omega          (applied volts = resistive drop + back-EMF)
    tau = Kt * I

MOTORING  (torque same sign as omega -> speeding the wheel up in its spin direction):
    back-EMF OPPOSES the supply, so the current you can push is
        I_avail = (V_lim - Ke*|omega|) / Rs
    and torque tapers from tau_stall (at omega=0, where the current limit binds) down to
    zero at omega = V_lim/Ke ~= 334 rad/s. Take the smaller of the current- and
    voltage-limited ceilings.

BRAKING   (torque opposite sign to omega -> slowing the wheel):
    back-EMF AIDS the supply (regenerative), full current available -> full tau_stall,
    no taper. This is the regen that threatens bus overvoltage in the Phase-3 hop-up.
"""

import numpy as np
from params import MOTOR


def torque_ceiling(tau_cmd, omega_w, M=MOTOR):
    """Largest |torque| the motor can deliver right now, given the commanded direction
    and current wheel speed. Returns a positive magnitude (N.m)."""
    # "motoring" = the commanded torque points the same way the wheel already spins.
    # At exactly omega=0 there is no spin direction to oppose, so treat as full torque.
    motoring = (omega_w != 0.0) and (np.sign(tau_cmd) == np.sign(omega_w))
    if not motoring:
        return M.tau_stall                      # braking / from rest: full current available
    # voltage budget left after back-EMF, converted to a current, clamped to >= 0
    i_avail = max(0.0, (M.V_lim - M.Ke * abs(omega_w)) / M.Rs)
    i_avail = min(M.I_lim, i_avail)             # current limit also applies
    return M.Kt * i_avail


def saturate(tau_cmd, omega_w, M=MOTOR):
    """Clip a commanded torque to what the motor can actually produce at this speed.
    Returns (tau_applied, hit_ceiling)."""
    ceil = torque_ceiling(tau_cmd, omega_w, M)
    tau = float(np.clip(tau_cmd, -ceil, ceil))
    return tau, abs(tau_cmd) > ceil + 1e-12


if __name__ == "__main__":
    # ---- VALIDATION: draw the torque-speed envelope --------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    w = np.linspace(0, 360, 400)
    # motoring ceiling: command a torque in the +spin direction at each +speed
    motor_ceil = np.array([torque_ceiling(+1.0, wi) for wi in w])
    brake_ceil = np.array([torque_ceiling(-1.0, wi) for wi in w])  # opposite to +spin

    w_zero = MOTOR.omega_zero_torque
    w_flat = MOTOR.omega_flat_end
    print(f"tau_stall (flat ceiling)      = {MOTOR.tau_stall*1000:.1f} mN.m")
    print(f"current limit binds until     ~{w_flat:.0f} rad/s  (omega_flat_end -- full torque below)")
    print(f"motoring torque -> 0 at omega  = {w_zero:.0f} rad/s  (asymptote, not an operating point)")
    print(f"available torque at omega_flat_end = {torque_ceiling(+1.0, w_flat)*1000:.1f} mN.m")

    plt.figure(figsize=(7.2, 4.2))
    plt.plot(w, motor_ceil * 1000, lw=2.2, color="#2a7de1", label="motoring (spin up)")
    plt.plot(w, brake_ceil * 1000, lw=2.2, color="#34a853", ls="--",
             label="braking (regen, full torque)")
    plt.axvline(w_flat, color="#d4623a", lw=1.2, ls=":",
                label=f"flat-torque knee ~{w_flat:.0f} rad/s")
    plt.axhline(MOTOR.tau_stall * 1000, color="0.6", lw=0.8)
    plt.text(8, MOTOR.tau_stall*1000 + 1.2, "tau_stall = Kt*I_lim", color="0.4", fontsize=9)
    plt.xlabel("wheel speed  |omega_w|  (rad/s)")
    plt.ylabel("available torque  (mN.m)")
    plt.title("Motor torque-speed envelope (2804, voltage_limit 14.5 V)")
    plt.legend(fontsize=9, loc="upper right")
    plt.ylim(0, MOTOR.tau_stall * 1000 * 1.15)
    plt.tight_layout()
    plt.savefig("torque_envelope.png", dpi=120)
    print("saved torque_envelope.png")
