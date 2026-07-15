"""Cubli design optimizer with per-cube-size analysis."""
import numpy as np
from scipy.integrate import solve_ivp
from itertools import product
import time

TAU_MAX     = 0.09
OMEGA_W_MAX = 300.0
g           = 9.81
DENSITIES = {'brass_360': 8500, 'steel_1018': 7850}

def estimate_cube_mass(L):
    return 0.250 * (L / 0.100) ** 2

def compute_params(L, r_w, t_w, material):
    rho = DENSITIES[material]
    m_w = rho * np.pi * r_w**2 * t_w
    I_w = 0.5 * m_w * r_w**2
    m_cube = estimate_cube_mass(L)
    m_total = m_cube + m_w
    d = L * np.sqrt(2) / 2
    I_cube_cm = (1/6) * m_cube * L**2
    I_cube_pivot = I_cube_cm + m_cube * d**2
    I_c = I_cube_pivot + m_w * d**2
    return dict(L=L, r_w=r_w, t_w=t_w, material=material,
                m_cube=m_cube, m_w=m_w, m_total=m_total,
                d=d, I_c=I_c, I_w=I_w)

def is_feasible(p):
    max_r = (p['L'] - 0.010) / 2
    if p['r_w'] > max_r: return False
    if p['m_total'] > 1.2: return False
    arg = TAU_MAX / (p['m_total'] * g * p['d'])
    if arg >= 1.0: return True
    if np.rad2deg(np.arcsin(arg)) < 3: return False
    return True

def static_bound_deg(p):
    arg = TAU_MAX / (p['m_total'] * g * p['d'])
    return np.rad2deg(np.arcsin(min(1.0, arg)))

def momentum_bound_deg(p):
    omega_n = np.sqrt(p['m_total'] * g * p['d'] / p['I_c'])
    bound = p['I_w'] * OMEGA_W_MAX * omega_n / (p['m_total'] * g * p['d'])
    return np.rad2deg(min(np.pi/2, bound))

def analytical_envelope_deg(p):
    return 0.7 * min(static_bound_deg(p), momentum_bound_deg(p))

def motor_torque(tau_cmd, omega_w):
    tau = np.clip(tau_cmd, -TAU_MAX, TAU_MAX)
    if tau * omega_w > 0:
        max_drive = TAU_MAX * max(0.0, 1.0 - abs(omega_w) / OMEGA_W_MAX)
        tau = np.sign(tau) * min(abs(tau), max_drive)
    return tau

def dynamics(t, x, p, Kp, Kd):
    theta, theta_dot, omega_w = x
    tau_cmd = Kp * theta + Kd * theta_dot
    tau = motor_torque(tau_cmd, omega_w)
    theta_ddot = (p['m_total'] * g * p['d'] * np.sin(theta) - tau) / p['I_c']
    omega_w_dot = tau / p['I_w'] - theta_ddot
    return [theta_dot, theta_ddot, omega_w_dot]

def gains_for(p, omega_ratio=3.0, zeta=0.7):
    omega_n_open = np.sqrt(p['m_total'] * g * p['d'] / p['I_c'])
    omega_n_closed = omega_ratio * omega_n_open
    Kp = p['I_c'] * omega_n_closed**2 + p['m_total'] * g * p['d']
    Kd = 2 * zeta * omega_n_closed * p['I_c']
    return Kp, Kd

def test_recovery(p, theta0_deg, t_end=1.5):
    Kp, Kd = gains_for(p)
    theta0 = np.deg2rad(theta0_deg)
    try:
        sol = solve_ivp(dynamics, [0, t_end], [theta0, 0.0, 0.0],
                        args=(p, Kp, Kd), max_step=3e-3, rtol=1e-4, atol=1e-6)
    except Exception:
        return False
    if not sol.success: return False
    final_theta = abs(sol.y[0, -1])
    peak_omega_w = np.max(np.abs(sol.y[2]))
    return final_theta < np.deg2rad(2.0) and peak_omega_w < OMEGA_W_MAX * 0.98

def find_envelope_sim(p, theta_min=1.0, theta_max=28.0, tol=0.5):
    if not test_recovery(p, theta_min): return 0.0
    if test_recovery(p, theta_max): return theta_max
    lo, hi = theta_min, theta_max
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if test_recovery(p, mid): lo = mid
        else: hi = mid
    return lo

def sweep_all_configs():
    L_vals = np.arange(0.080, 0.151, 0.010)
    r_frac = np.arange(0.55, 0.91, 0.05)
    t_w_vals = np.array([0.003, 0.004, 0.005, 0.006, 0.008])
    materials = ['brass_360', 'steel_1018']

    candidates = []
    for L, frac, t_w, mat in product(L_vals, r_frac, t_w_vals, materials):
        r_w = frac * L / 2
        p = compute_params(L, r_w, t_w, mat)
        if not is_feasible(p): continue
        p['analytical_envelope'] = analytical_envelope_deg(p)
        candidates.append(p)
    return candidates

def find_best_per_cube_size(candidates):
    """For each cube size, find the best simulated envelope."""
    L_groups = {}
    for c in candidates:
        L_key = round(c['L'] * 1000)  # mm
        L_groups.setdefault(L_key, []).append(c)

    # For each cube size, sim the top 4 analytical candidates and take best
    best_per_L = {}
    for L_key, group in sorted(L_groups.items()):
        group.sort(key=lambda x: -x['analytical_envelope'])
        top4 = group[:4]
        for p in top4:
            p['envelope_deg'] = find_envelope_sim(p)
        top4.sort(key=lambda x: -x['envelope_deg'])
        best_per_L[L_key] = top4[0]
    return best_per_L

def find_global_top(candidates, n=10):
    candidates.sort(key=lambda x: -x['analytical_envelope'])
    sim_set = candidates[:30]
    for p in sim_set:
        if 'envelope_deg' not in p:
            p['envelope_deg'] = find_envelope_sim(p)
    sim_set.sort(key=lambda x: -x['envelope_deg'])
    return sim_set[:n]

def print_config(r, idx=None):
    label = f"#{idx}  " if idx else ""
    print(f"{label}envelope = {r['envelope_deg']:.1f} deg "
          f"(analytical: {r['analytical_envelope']:.1f})")
    print(f"     Cube:      {r['L']*1000:.0f} mm side, body est {r['m_cube']*1000:.0f} g")
    print(f"     Flywheel:  {r['r_w']*2*1000:.0f} mm OD x {r['t_w']*1000:.1f} mm "
          f"{r['material']}, {r['m_w']*1000:.0f} g")
    print(f"     System:    m_total {r['m_total']*1000:.0f} g, "
          f"I_w {r['I_w']:.2e}, I_c {r['I_c']:.2e}")

if __name__ == "__main__":
    print("Sweeping design space...")
    t0 = time.time()
    candidates = sweep_all_configs()
    print(f"  {len(candidates)} feasible configurations  ({time.time()-t0:.1f}s)")

    print("\nSimulating best candidates at each cube size...")
    t0 = time.time()
    best_per_L = find_best_per_cube_size(candidates)
    print(f"  Done  ({time.time()-t0:.1f}s)")

    print("\n" + "=" * 78)
    print("BEST DESIGN AT EACH CUBE SIZE  (the Pareto curve)")
    print("=" * 78)
    for L_key in sorted(best_per_L.keys()):
        r = best_per_L[L_key]
        print()
        print(f"--- {L_key} mm cube ---")
        print_config(r)

    print("\n" + "=" * 78)
    print("TOP 5 GLOBAL")
    print("=" * 78)
    top5 = find_global_top(candidates, n=5)
    for i, r in enumerate(top5):
        print()
        print_config(r, idx=i+1)
