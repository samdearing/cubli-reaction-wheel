"""Single-axis Cubli plant simulation.
Open-loop: no controller, just gravity + an optional motor torque profile.
Starts the cube at a small tilt and watches it fall.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

from params import I_c, I_w, m_total, g, d, TAU_MAX, OMEGA_W_MAX
import numpy as np


def motor_torque(tau_command, omega_w):
    """Apply motor saturation: torque limit + speed-torque curve."""
    tau = np.clip(tau_command, -TAU_MAX, TAU_MAX)
    
    # If we're trying to drive the wheel faster (same sign as omega_w),
    # available torque drops linearly with speed
    if tau * omega_w > 0:
        max_drive = TAU_MAX * max(0.0, 1.0 - abs(omega_w) / OMEGA_W_MAX)
        tau = np.sign(tau) * min(abs(tau), max_drive)
    # Braking direction (opposite sign) is unrestricted — regen
    return tau


def dynamics(t, x, tau_motor_fn):
    theta, theta_dot, omega_w = x
    tau = motor_torque(tau_motor_fn(t, x), omega_w)
    
    theta_ddot = (m_total * g * d * np.sin(theta) - tau) / I_c
    omega_w_dot = tau / I_w - theta_ddot
    return [theta_dot, theta_ddot, omega_w_dot]


def zero_torque(t, x):
    """No control input — just watch it fall."""
    return 0.0


def pd_controller(Kp, Kd, theta_ref=0.0):
    """Return a controller function tau(t, x) implementing PD on theta error."""
    def tau(t, x):
        theta, theta_dot, _ = x
        return Kp * (theta - theta_ref) + Kd * theta_dot
    return tau


def run_sim(tau_motor_fn=zero_torque, theta0=np.deg2rad(2), t_end=0.5):
    """Integrate the plant and return time + state arrays."""
    x0 = [theta0, 0.0, 0.0]   # small initial tilt, at rest, wheel stopped
    sol = solve_ivp(
        dynamics, [0, t_end], x0,
        args=(tau_motor_fn,),
        max_step=1e-3,
        dense_output=True,
    )
    return sol


def plot_run(sol, title="Open-loop fall"):
    t = sol.t
    theta_deg = np.rad2deg(sol.y[0])
    theta_dot = sol.y[1]
    omega_w   = sol.y[2]
    
    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True)
    axes[0].plot(t, theta_deg);     axes[0].set_ylabel("θ [deg]")
    axes[1].plot(t, theta_dot);     axes[1].set_ylabel("θ̇ [rad/s]")
    axes[2].plot(t, omega_w);       axes[2].set_ylabel("ω_w [rad/s]"); axes[2].set_xlabel("time [s]")
    for ax in axes: ax.grid(alpha=0.3)
    fig.suptitle(title)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    # Open-loop reference
    sol_open = run_sim(zero_torque, theta0=np.deg2rad(2), t_end=0.5)
    plot_run(sol_open, title="Open-loop fall")

    # PD-controlled
    Kp, Kd = 20, 0.7
    controller = pd_controller(Kp, Kd)
    sol_pd = run_sim(controller, theta0=np.deg2rad(11), t_end=2.0)
    plot_run(sol_pd, title=f"PD balance (Kp={Kp}, Kd={Kd})")