"""
Phase-1 closed-loop simulation: plant.py + motor.py + controller.py, run together.

This is the artifact the whole sims-first workflow exists to produce. The controller in
here is the logic you transcribe to the Teensy; params.py is the file you edit when
SolidWorks hands you the real mass tensor. Nothing else should need to change to go to
hardware.

Loop structure mirrors the firmware:
  - physics integrates at 2 kHz (fine truth model)
  - the controller updates at C.loop_rate (default 1 kHz) and HOLDS its torque between
    ticks (zero-order hold) -- exactly what the real control loop does.

Scenario: released from a small tilt, then shoved at t=1.5 s to show the wheel absorb the
disturbance momentum and then desaturate (bleed back toward zero) under the +Kw term.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from params import PLANT, MOTOR, G
from plant import rk4_step
from motor import torque_ceiling
from controller import Controller


def simulate(C, theta0_deg=3.0, T=4.0, shove_time=1.5, shove_rate=1.0,
             phys_dt=1.0 / 2000, P=PLANT):
    """Run the closed loop. Returns a dict of time histories.
    shove_rate is an instantaneous step in theta_dot (rad/s) applied once at shove_time --
    a model of a physical poke."""
    ctrl_dt = 1.0 / C.loop_rate
    n = int(T / phys_dt)

    x = np.array([np.deg2rad(theta0_deg), 0.0, 0.0])   # [theta, theta_dot, omega_w]
    tau_held, t_since_ctrl = 0.0, 0.0
    shoved = False

    hist = {k: np.empty(n) for k in
            ("t", "theta", "theta_dot", "omega_w", "tau", "tau_ceil")}

    for i in range(n):
        t = i * phys_dt

        # one-shot disturbance
        if (not shoved) and t >= shove_time:
            x[1] += shove_rate
            shoved = True

        # controller runs at its own rate, torque held in between (ZOH)
        t_since_ctrl += phys_dt
        if t_since_ctrl >= ctrl_dt - 1e-12:
            tau_held, _ = C.torque(x)
            t_since_ctrl = 0.0

        hist["t"][i] = t
        hist["theta"][i] = x[0]
        hist["theta_dot"][i] = x[1]
        hist["omega_w"][i] = x[2]
        hist["tau"][i] = tau_held
        hist["tau_ceil"][i] = torque_ceiling(tau_held, x[2])

        x = rk4_step(x, tau_held, phys_dt, P)

    return hist


def report(hist, settle_deg=1.0):
    """Print a pass/fail summary of the run."""
    th_deg = np.rad2deg(hist["theta"])
    final_tilt = abs(th_deg[-1])
    peak_tilt = np.max(np.abs(th_deg))
    peak_wheel = np.max(np.abs(hist["omega_w"]))
    final_wheel = abs(hist["omega_w"][-1])
    fell = peak_tilt > 30.0
    w_flat, w_zero = MOTOR.omega_flat_end, MOTOR.omega_zero_torque

    print(f"peak tilt        = {peak_tilt:6.2f} deg")
    print(f"final tilt       = {final_tilt:6.2f} deg   (balanced if < {settle_deg})")
    print(f"peak wheel speed = {peak_wheel:6.1f} rad/s  "
          f"({peak_wheel/w_flat*100:.0f}% of the {w_flat:.0f} rad/s flat-torque region, "
          f"{peak_wheel/w_zero*100:.0f}% of the {w_zero:.0f} rad/s asymptote)")
    print(f"final wheel speed= {final_wheel:6.1f} rad/s  (desaturated if -> 0)")
    print(f"VERDICT: {'FELL OVER' if fell else ('BALANCED' if final_tilt < settle_deg else 'STILL SETTLING')}")
    return not fell and final_tilt < settle_deg


def plot(hist, path="closed_loop.png"):
    t = hist["t"]
    fig, ax = plt.subplots(2, 2, figsize=(11, 6.5))

    # tilt
    ax[0, 0].plot(t, np.rad2deg(hist["theta"]), color="#34a853", lw=1.6)
    ax[0, 0].axhline(0, color="0.7", lw=0.6)
    ax[0, 0].set_title("tilt  theta  (deg)")
    ax[0, 0].set_xlabel("time (s)")

    # wheel speed with the two physical references: flat-torque knee + zero-torque asymptote
    ax[0, 1].plot(t, hist["omega_w"], color="#2a7de1", lw=1.6)
    for s in (+MOTOR.omega_flat_end, -MOTOR.omega_flat_end):
        ax[0, 1].axhline(s, color="#d4623a", lw=1.0, ls=":")
    for s in (+MOTOR.omega_zero_torque, -MOTOR.omega_zero_torque):
        ax[0, 1].axhline(s, color="#d4623a", lw=1.0, ls="--")
    ax[0, 1].axhline(0, color="0.7", lw=0.6)
    ax[0, 1].set_title(f"wheel speed  omega_w  (rad/s)   "
                       f"[knee {MOTOR.omega_flat_end:.0f}, zero-torque {MOTOR.omega_zero_torque:.0f}]")
    ax[0, 1].set_xlabel("time (s)")

    # torque vs live envelope
    ax[1, 0].plot(t, hist["tau"] * 1000, color="#ffb454", lw=1.6, label="applied")
    ax[1, 0].plot(t, hist["tau_ceil"] * 1000, color="#d4623a", lw=1.0, ls="--", label="ceiling")
    ax[1, 0].plot(t, -hist["tau_ceil"] * 1000, color="#d4623a", lw=1.0, ls="--")
    ax[1, 0].set_title("motor torque  (mN.m)")
    ax[1, 0].set_xlabel("time (s)")
    ax[1, 0].legend(fontsize=8, loc="upper right")

    # phase portrait
    ax[1, 1].plot(np.rad2deg(hist["theta"]), np.rad2deg(hist["theta_dot"]),
                  color="#34e6c0", lw=1.0)
    ax[1, 1].plot(0, 0, "o", color="#d4623a", ms=5)
    ax[1, 1].set_title("phase portrait  (theta vs theta_dot, deg)")
    ax[1, 1].set_xlabel("theta (deg)")
    ax[1, 1].set_ylabel("theta_dot (deg/s)")

    fig.suptitle("Cubli Phase-1 closed loop: release from 3 deg, shove at 1.5 s, recover + desaturate")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"saved {path}")


if __name__ == "__main__":
    C = Controller()   # defaults: Kp 1.40, Kd 0.080, Kw +1e-4, 1 kHz
    print(f"gains: Kp={C.Kp}  Kd={C.Kd}  Kw={C.Kw:+}  loop_rate={C.loop_rate:.0f} Hz\n")
    hist = simulate(C)
    ok = report(hist)
    plot(hist)
    print("\nclosed-loop balance:", "CONFIRMED" if ok else "FAILED -- do not port")
