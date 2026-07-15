"""
Cubli flywheel sizing — corrected for the as-built cube.
Fixed 150 mm frame, measured component masses, corner-balance geometry,
real QiuLovesYT 2804 motor constants, all 3 brass flywheels present,
motor rotor inertia included.
"""
import numpy as np
from scipy.integrate import solve_ivp

# ---- Fixed cube (Sam's build) ----
L = 0.150                              # m, frame side

# ---- Component mass budget (kg) ----
M_FRAME   = 0.250                      # PETG estimate (sturdy, hop-rated)
M_MOTOR   = 0.052
M_DRIVER  = 0.003
M_TEENSY  = 0.018
M_IMU     = 0.002
M_BATTERY = 0.169
M_WIRING  = 0.015
M_COMPONENTS = (M_FRAME + 3*M_MOTOR + 3*M_DRIVER + M_TEENSY
                + M_IMU + M_BATTERY + M_WIRING)

# ---- Real 2804 motor ----
KT          = 0.0434                   # N.m/A
I_MAX       = 2.0                      # A hard limit
TAU_MAX     = KT * I_MAX               # 0.0868 N.m peak
KV          = 220.0                    # RPM/V
VOLTAGE_LIM = 12.0                     # conservative SimpleFOC voltage_limit
OMEGA_W_MAX = KV * VOLTAGE_LIM * 2*np.pi/60   # no-load wheel speed (rad/s)
ROTOR_I     = 3.7e-6                   # kg.m^2, add to flywheel inertia

RHO_BRASS = 8500.0
g = 9.81

d_corner = L*np.sqrt(3)/2              # CM-to-corner (worst case)
d_edge   = L*np.sqrt(2)/2              # for reference

def make_params(r_w, t_w, d):
    m_w = RHO_BRASS * np.pi * r_w**2 * t_w
    I_w = 0.5*m_w*r_w**2 + ROTOR_I
    m_total = M_COMPONENTS + 3*m_w           # all three wheels present
    I_cm = (1/6)*m_total*L**2
    I_c  = I_cm + m_total*d**2
    return dict(r_w=r_w, t_w=t_w, d=d, m_w=m_w, m_total=m_total, I_c=I_c, I_w=I_w)

def static_bound_deg(p):
    arg = TAU_MAX/(p['m_total']*g*p['d'])
    return np.rad2deg(np.arcsin(min(1.0, arg)))

def momentum_bound_deg(p):
    omega_n = np.sqrt(p['m_total']*g*p['d']/p['I_c'])
    b = p['I_w']*OMEGA_W_MAX*omega_n/(p['m_total']*g*p['d'])
    return np.rad2deg(min(np.pi/2, b))

def motor_torque(tau_cmd, omega_w):
    tau = np.clip(tau_cmd, -TAU_MAX, TAU_MAX)
    if tau*omega_w > 0:
        max_drive = TAU_MAX*max(0.0, 1.0 - abs(omega_w)/OMEGA_W_MAX)
        tau = np.sign(tau)*min(abs(tau), max_drive)
    return tau

def gains_for(p, omega_ratio=3.0, zeta=0.7):
    wn_open  = np.sqrt(p['m_total']*g*p['d']/p['I_c'])
    wn_close = omega_ratio*wn_open
    Kp = p['I_c']*wn_close**2 + p['m_total']*g*p['d']
    Kd = 2*zeta*wn_close*p['I_c']
    return Kp, Kd

def dynamics(t, x, p, Kp, Kd):
    th, thd, ww = x
    tau = motor_torque(Kp*th + Kd*thd, ww)
    thdd = (p['m_total']*g*p['d']*np.sin(th) - tau)/p['I_c']
    wwd  = tau/p['I_w'] - thdd
    return [thd, thdd, wwd]

def recovers(p, theta0_deg, t_end=1.5):
    Kp, Kd = gains_for(p)
    try:
        sol = solve_ivp(dynamics, [0, t_end], [np.deg2rad(theta0_deg), 0, 0],
                        args=(p, Kp, Kd), max_step=3e-3, rtol=1e-4, atol=1e-6)
    except Exception:
        return False
    if not sol.success: return False
    return abs(sol.y[0,-1]) < np.deg2rad(2.0) and np.max(np.abs(sol.y[2])) < 0.98*OMEGA_W_MAX

def sim_envelope(p, lo=1.0, hi=35.0, tol=0.5):
    if not recovers(p, lo): return 0.0
    if recovers(p, hi): return hi
    while hi-lo > tol:
        mid = 0.5*(lo+hi)
        if recovers(p, mid): lo = mid
        else: hi = mid
    return lo

print(f"Components (no flywheels): {M_COMPONENTS*1000:.0f} g")
print(f"TAU_MAX = {TAU_MAX:.4f} N.m   OMEGA_W_MAX = {OMEGA_W_MAX:.0f} rad/s "
      f"({OMEGA_W_MAX*60/2/np.pi:.0f} RPM)")
print(f"d_corner = {d_corner*1000:.1f} mm   d_edge = {d_edge*1000:.1f} mm")
print("="*92)
print(f"{'OD':>5} {'thk':>5} {'m_w':>7} {'3wheel':>7} {'m_tot':>7} {'I_w':>10} "
      f"{'static':>7} {'mom':>7} {'env(corner)':>11} {'env(edge)':>10}")
print(f"{'mm':>5} {'mm':>5} {'g':>7} {'g':>7} {'kg':>7} {'kg.m^2':>10} "
      f"{'deg':>7} {'deg':>7} {'deg':>11} {'deg':>10}")
print("-"*92)

best = []
for r_w in np.arange(0.025, 0.066, 0.005):       # 50..130 mm OD
    if r_w > (L-0.020)/2: continue
    for t_w in [0.003,0.004,0.005,0.006,0.008,0.010]:
        pc = make_params(r_w, t_w, d_corner)
        pe = make_params(r_w, t_w, d_edge)
        env_c = sim_envelope(pc); env_e = sim_envelope(pe)
        print(f"{r_w*2*1000:5.0f} {t_w*1000:5.1f} {pc['m_w']*1000:7.0f} "
              f"{3*pc['m_w']*1000:7.0f} {pc['m_total']:7.3f} {pc['I_w']:10.2e} "
              f"{static_bound_deg(pc):7.1f} {momentum_bound_deg(pc):7.1f} "
              f"{env_c:11.1f} {env_e:10.1f}")
        best.append((env_c, r_w, t_w, pc))

print("="*92)
best.sort(key=lambda x: -x[0])
print("Top 5 by corner envelope:")
for env, r_w, t_w, p in best[:5]:
    print(f"  OD {r_w*2*1000:.0f} mm x {t_w*1000:.1f} mm brass: "
          f"each {p['m_w']*1000:.0f} g, I_w {p['I_w']:.2e}, "
          f"corner envelope {env:.1f} deg, cube total {p['m_total']*1000:.0f} g")
