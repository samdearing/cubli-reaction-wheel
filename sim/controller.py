"""
Phase-1 controller: PD on tilt + reaction-wheel desaturation.

Control law (one scalar torque command, updated once per loop tick):

    tau_cmd = Kp*theta + Kd*theta_dot + Kw*omega_w

  Kp*theta      : the restoring spring. Must exceed mgl to overpower gravity's
                  negative spring (see plant.py). This is what holds you up.
  Kd*theta_dot  : damping. Bleeds the oscillation once Kp has made the stiffness positive.
  Kw*omega_w    : wheel-speed desaturation. The subtle one -- see the note below. Leans
                  the cube imperceptibly so gravity unloads the wheel back toward zero.

Sign convention check against plant.py:
    theta_ddot = (mgl*sin(theta) - tau - ...)/I_bar
  A POSITIVE tau SUBTRACTS from theta_ddot -> restoring. So at theta>0 (tipped),
  Kp>0 makes tau>0 -> pushes back upright. Correct.

-------------------------------------------------------------------------------
WHY +Kw IS THE CORRECT DESATURATION SIGN (and why we don't trust our gut on it)
-------------------------------------------------------------------------------
Instantaneously, +Kw*omega_w looks WRONG: if the wheel spins at +omega_w, the term
adds a +torque, which seems like it would spin the wheel up further. But desaturation
is not an instantaneous effect -- it's a closed-loop pole. The honest way to settle the
sign is to linearize the whole loop and look at the eigenvalue tied to wheel speed:

  With Kw = 0, the wheel-speed direction is a pure integrator -> one eigenvalue sits
  exactly at 0 (marginally stable). That is the wheel "parking at a nonzero speed
  forever" after a disturbance: nothing pulls it home.

  Turning Kw on perturbs that zero eigenvalue off the imaginary axis. The SIGN of Kw
  decides which way it moves:
     +Kw -> eigenvalue goes into the left half-plane  -> omega_w decays to 0 (unload)
     -Kw -> eigenvalue goes into the right half-plane  -> omega_w runs away (the bug)

The closed_loop_eigs() routine below computes exactly this, so the sign is earned from
the math instead of inherited. This is the same bug that cost us a stable-LOOKING but
falling controller in the sandbox: a feedback sign that reads fine on paper, caught only
by computing the closed loop. On the TVC rocket, that class of bug ends the flight.
"""

import numpy as np
from params import PLANT, MOTOR, G
from motor import saturate


class Controller:
    """Holds the gains and the ZOH state (torque held between loop ticks)."""

    def __init__(self, Kp=1.40, Kd=0.080, Kw=1.0e-4, loop_rate=1000.0):
        self.Kp = Kp
        self.Kd = Kd
        self.Kw = Kw                 # NOTE: positive. See module docstring / closed_loop_eigs.
        self.loop_rate = loop_rate   # Hz; must beat the ~11 rad/s open-loop divergence

    def command(self, state):
        """Raw (unsaturated) torque command from the current estimated state.
        state = [theta, theta_dot, omega_w]. On hardware these come from Madgwick (theta),
        the gyro (theta_dot), and the AS5600 difference (omega_w)."""
        theta, theta_dot, omega_w = state
        return self.Kp * theta + self.Kd * theta_dot + self.Kw * omega_w

    def torque(self, state):
        """Command, then clip to what the motor can deliver at this wheel speed.
        Returns (tau_applied, hit_ceiling)."""
        tau_cmd = self.command(state)
        return saturate(tau_cmd, state[2])


def closed_loop_A(C, P=PLANT):
    """Linearized closed-loop dynamics matrix A about upright (theta=0), state
    x=[theta, theta_dot, omega_w], with tau = Kp*theta + Kd*theta_dot + Kw*omega_w.
    Frictions dropped -- they are tiny and only help; we want the worst-case core.

    Open-loop (sin theta ~= theta):
        theta_ddot  = (mgl*theta - tau)/I_bar
        omega_w_dot = tau/I_w - theta_ddot
    Substitute tau and collect terms."""
    mgl = P.m * G * P.l
    Ib, Iw = P.I_bar, P.I_w
    Kp, Kd, Kw = C.Kp, C.Kd, C.Kw

    # theta_ddot = a*theta + b*theta_dot + c*omega_w
    a = (mgl - Kp) / Ib
    b = -Kd / Ib
    c = -Kw / Ib
    # omega_w_dot = tau/I_w - theta_ddot, with tau = Kp*th + Kd*thd + Kw*ww
    r0 = Kp / Iw - a
    r1 = Kd / Iw - b
    r2 = Kw / Iw - c
    return np.array([[0.0, 1.0, 0.0],
                     [a,   b,   c],
                     [r0,  r1,  r2]])


def closed_loop_eigs(C, P=PLANT):
    """Eigenvalues of the linearized closed loop. Stable iff all real parts < 0."""
    return np.linalg.eigvals(closed_loop_A(C, P))


if __name__ == "__main__":
    # ---- DERIVE THE Kw SIGN FROM THE EIGENVALUES -----------------------------
    mgl = PLANT.m * G * PLANT.l
    print(f"mgl = {mgl:.4f} N.m/rad  -> Kp must exceed this\n")

    base = dict(Kp=1.40, Kd=0.080, loop_rate=1000.0)

    for label, Kw in [("Kw = 0      (no desat: marginal, wheel parks)", 0.0),
                      ("Kw = +1e-4  (correct sign: wheel unloads)",     +1.0e-4),
                      ("Kw = -1e-4  (the bug: wheel runs away)",        -1.0e-4)]:
        eigs = closed_loop_eigs(Controller(Kw=Kw, **base))
        max_re = max(e.real for e in eigs)
        verdict = "STABLE" if max_re < -1e-9 else ("MARGINAL" if abs(max_re) <= 1e-9 else "UNSTABLE")
        eig_str = ", ".join(f"{e.real:+.3f}{e.imag:+.3f}j" for e in eigs)
        print(f"{label}")
        print(f"    eigenvalues: {eig_str}")
        print(f"    max real part = {max_re:+.4f}  -> {verdict}\n")

    # Also confirm the Kp>mgl floor: drop Kp below mgl and watch it go unstable.
    eigs = closed_loop_eigs(Controller(Kp=0.40, Kd=0.080, Kw=1.0e-4))
    print(f"Kp = 0.40 < mgl: max real part = {max(e.real for e in eigs):+.4f} (expect UNSTABLE)")
