"""
Single-axis Cubli plant: the cube balanced on its edge is an inverted pendulum that
carries one reaction wheel. Two coupled bodies, one control input.

State   x = [theta, theta_dot, omega_w]
  theta     : body tilt from upright (rad)              <- Madgwick estimates this on HW
  theta_dot : body tilt rate (rad/s)                    <- gyro reads this
  omega_w   : wheel speed RELATIVE to the body (rad/s)  <- d/dt of the AS5600 angle
Input   tau : motor torque applied to the wheel (N.m)

Equations of motion (derived previously; gravity enters as a NEGATIVE spring):
  (A)  I_b' * theta_ddot + I_w * alpha_ddot = m*g*l*sin(theta) - b_th*theta_dot
  (B)  I_w * (theta_ddot + alpha_ddot)      = tau - b_w*omega_w
Eliminate alpha_ddot, define I_bar = I_b' - I_w (body inertia minus the wheel's spin
inertia, which is exactly PLANT.I_bar), and you get the form we integrate:

  theta_ddot  = ( m*g*l*sin(theta) - tau - b_th*theta_dot + b_w*omega_w ) / I_bar
  omega_w_dot = ( tau - b_w*omega_w ) / I_w  -  theta_ddot

Sign check: at theta > 0 the m*g*l*sin term is positive -> theta_ddot positive -> the cube
tips FURTHER over. Gravity destabilizes. A positive tau subtracts from theta_ddot -> it
restores. That is the entire control problem in one line.
"""

import numpy as np
from params import PLANT, G


def deriv(x, tau, P=PLANT):
    """Continuous-time state derivative xdot = f(x, tau)."""
    theta, theta_dot, omega_w = x
    theta_ddot = (P.m * G * P.l * np.sin(theta)
                  - tau - P.b_th * theta_dot + P.b_w * omega_w) / P.I_bar
    omega_w_dot = (tau - P.b_w * omega_w) / P.I_w - theta_ddot
    return np.array([theta_dot, theta_ddot, omega_w_dot])


def rk4_step(x, tau, dt, P=PLANT):
    """One fixed-step RK4 integration. tau is held constant across the step (zero-order
    hold) -- this mirrors how the real controller updates torque once per loop tick."""
    k1 = deriv(x, tau, P)
    k2 = deriv(x + 0.5 * dt * k1, tau, P)
    k3 = deriv(x + 0.5 * dt * k2, tau, P)
    k4 = deriv(x + dt * k3, tau, P)
    return x + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


if __name__ == "__main__":
    # ---- OPEN-LOOP VALIDATION -------------------------------------------------
    # No control (tau = 0). Release from a small tilt. A correct inverted-pendulum
    # plant MUST fall away from upright. If this curve stayed near zero, the model
    # would be wrong and every controller built on it would be fiction.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dt = 1.0 / 2000          # 2 kHz physics step
    T = 1.2                  # seconds
    n = int(T / dt)

    x = np.array([np.deg2rad(4.0), 0.0, 0.0])   # 4 deg tilt, everything at rest
    FACE = np.deg2rad(45.0)                      # the cube slaps down on a face here
    t_hist, th_hist = [], []
    for i in range(n):
        x = rk4_step(x, 0.0, dt)
        t_hist.append(i * dt)
        th_hist.append(np.rad2deg(x[0]))
        if abs(x[0]) >= FACE:                    # physical stop: it has fallen onto a face
            break
    t_hist, th_hist = np.array(t_hist), np.array(th_hist)

    mgl = PLANT.m * G * PLANT.l
    growth = np.sqrt(mgl / PLANT.I_bar)          # natural divergence rate, rad/s
    print(f"tilt at t=0:        4.0 deg")
    print(f"hit a face (45 deg) at t = {t_hist[-1]*1000:.0f} ms")
    print(f"open-loop growth rate sqrt(mgl/I_bar) = {growth:.1f} rad/s "
          f"-> fall time constant ~{1/growth*1000:.0f} ms")

    plt.figure(figsize=(7, 4))
    plt.plot(t_hist, th_hist, lw=2, color="#d4623a")
    plt.axhline(0, color="k", lw=0.6)
    plt.axhline(45, color="0.6", lw=0.8, ls="--")
    plt.text(0.01, 41, "lands on a face (~45 deg)", color="0.4", fontsize=9)
    plt.xlabel("time (s)")
    plt.ylabel("tilt  theta  (deg)")
    plt.title("Open-loop plant: uncontrolled fall from 4 deg  (gravity wins)")
    plt.tight_layout()
    plt.savefig("openloop_fall.png", dpi=120)
    print("saved openloop_fall.png")
