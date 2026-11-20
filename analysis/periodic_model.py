"""Periodic-source correction (G25) to the unified loss expression (G5).
R_bb: Brownian-bridge mean-backlog ratio of n periodic random-phase streams to Poisson.
loss(N, f, Tf, ...): loss with periodic=True (G25) or False (Poisson, as G5).
nmax(f, Tf, eps, periodic, ...): capacity (real-valued N) at loss target eps.
Valid for about 8 or more other stations; not for 1-4 (see doc Section 10.1)."""
import math, sys
sys.path.insert(0,'/home/claude/out')
def R_bb(n, rho):
    """Mean-backlog ratio of n periodic streams (random phase) to Poisson at load rho, from the
    Brownian-bridge tail P(Q>x) ~ exp(-2x(x/n + 1 - rho)) (N*D/D/1). Closed form via erfc."""
    if rho>=1: return 1.0
    c=(1-rho)*math.sqrt(n/2)
    if c>25: ex=1/(c*math.sqrt(math.pi))*(1-1/(2*c*c)+3/(4*c**4))
    else: ex=math.exp(c*c)*math.erfc(c)
    return math.sqrt(math.pi*n/8)*ex*2*(1-rho)
def loss(N,f,Tf,W=16,delta=4e-6,slot=9e-6,difs=34e-6,periodic=True,p_fix=None):
    nu=(N-1)*f; p=0.0 if p_fix is None else p_fix
    for _ in range(300):
        a=nu*(Tf-delta)*(1-p/2); gam=nu*difs; eta=nu*slot*(W-1)/2
        if 1-gam-a<=0: return 1.0
        K=a*(1+gam+2*eta)/(1-gam-a)
        if periodic: K*=R_bb(N-1,a+gam)
        pn=min(1.0,a*K/(W+K)+gam*(2*a/W+gam)+2*delta*nu*(1+a))
        if p_fix is not None: return pn
        if abs(pn-p)<1e-10: break
        p=0.5*(p+pn)
    return p
def nmax(f,Tf,eps=0.05,periodic=True,**kw):
    lo,hi=2,int(1/(f*Tf))+2
    g=lambda N: loss(N,f,Tf,periodic=periodic,p_fix=eps,**kw)-eps
    # continuous N: bisection on real N
    lo,hi=2.0,float(hi)
    for _ in range(80):
        m=(lo+hi)/2
        lo,hi=(m,hi) if g(m)<0 else (lo,m)
    return lo
