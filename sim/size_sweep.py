import numpy as np
from scipy.integrate import solve_ivp

M_MOTOR=0.052; M_DRIVER=0.003; M_TEENSY=0.018; M_IMU=0.002; M_BATTERY=0.169; M_WIRING=0.015
KT=0.0434; I_MAX=2.0; TAU_MAX=KT*I_MAX
KV=220.0; VLIM=12.0; OMEGA_W_MAX=KV*VLIM*2*np.pi/60; ROTOR_I=3.7e-6
RHO=8500.0; g=9.81

def params(L, r_w, t_w, d):
    frame = 0.250*(L/0.15)**2          # frame scales ~ area
    comp = frame+3*M_MOTOR+3*M_DRIVER+M_TEENSY+M_IMU+M_BATTERY+M_WIRING
    m_w = RHO*np.pi*r_w**2*t_w
    I_w = 0.5*m_w*r_w**2+ROTOR_I
    m_total = comp+3*m_w
    I_c = (1/6)*m_total*L**2 + m_total*d**2
    return dict(d=d,m_w=m_w,m_total=m_total,I_c=I_c,I_w=I_w,frame=frame)

def mtorque(tc,ww):
    t=np.clip(tc,-TAU_MAX,TAU_MAX)
    if t*ww>0:
        md=TAU_MAX*max(0.0,1-abs(ww)/OMEGA_W_MAX); t=np.sign(t)*min(abs(t),md)
    return t
def gains(p,r=3.0,z=0.7):
    wo=np.sqrt(p['m_total']*g*p['d']/p['I_c']); wc=r*wo
    return p['I_c']*wc**2+p['m_total']*g*p['d'], 2*z*wc*p['I_c']
def dyn(t,x,p,Kp,Kd):
    th,thd,ww=x; tau=mtorque(Kp*th+Kd*thd,ww)
    thdd=(p['m_total']*g*p['d']*np.sin(th)-tau)/p['I_c']
    return [thd,thdd,tau/p['I_w']-thdd]
def rec(p,th0):
    Kp,Kd=gains(p)
    s=solve_ivp(dyn,[0,1.5],[np.deg2rad(th0),0,0],args=(p,Kp,Kd),max_step=3e-3,rtol=1e-4,atol=1e-6)
    return s.success and abs(s.y[0,-1])<np.deg2rad(2) and np.max(np.abs(s.y[2]))<0.98*OMEGA_W_MAX
def env(p,lo=1.0,hi=40.0,tol=0.5):
    if not rec(p,lo): return 0.0
    if rec(p,hi): return hi
    while hi-lo>tol:
        m=0.5*(lo+hi)
        if rec(p,m): lo=m
        else: hi=m
    return lo

print(f"{'L':>5} {'frame':>6} {'OD':>5} {'m_tot':>6} {'env_corner':>10} {'env_edge':>9}")
print(f"{'mm':>5} {'g':>6} {'mm':>5} {'kg':>6} {'deg':>10} {'deg':>9}")
for L in [0.080,0.090,0.100,0.110,0.120,0.130,0.140,0.150]:
    r_w=(L-0.040)/2; t_w=0.004              # OD = L-40mm, 4mm brass
    pc=params(L,r_w,t_w,L*np.sqrt(3)/2)
    pe=params(L,r_w,t_w,L*np.sqrt(2)/2)
    print(f"{L*1000:5.0f} {pc['frame']*1000:6.0f} {r_w*2*1000:5.0f} {pc['m_total']:6.3f} "
          f"{env(pc):10.1f} {env(pe):9.1f}")
