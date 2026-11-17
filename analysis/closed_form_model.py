"""Unified closed-form capacity model for batched, authenticated broadcast telemetry,
with an independent event simulation of broadcast DCF to check it.

Model (tab "Unified closed-form model" of the doc):
  loss(nu, Tf)        three-mechanism DCF loss, Eq. (G5)
  dcf_constants(eps)  rho*, tau_0 of the two-constant law, Eqs. (G6)-(G8)
  n_law(f, Tf, eps)   explicit capacity law, Eq. (G9)
  n_root(f, Tf, eps)  capacity from the full loss expression (bisection)
  n_master(...)       master formula, Eq. (G10)
Simulator:
  simulate(N, f, Tf)  one collision domain, no capture, rule set A (see doc)
Defaults are IEEE 802.11a OFDM values: slot 9 us, DIFS 34 us, W = 16, detection 4 us.
"""
import math, random

SLOT, DIFS, W0, DELTA = 9e-6, 34e-6, 16, 4e-6

def loss(nu, Tf, W=W0, delta=DELTA, slot=SLOT, difs=DIFS, p_fix=None):
    """Frame loss probability at start rate nu = (N-1) f, frame airtime Tf. Eq. (G5)."""
    p = 0.0 if p_fix is None else p_fix
    for _ in range(300):
        a = nu * (Tf - delta) * (1 - p / 2)
        gam, eta = nu * difs, nu * slot * (W - 1) / 2
        if 1 - gam - a <= 0:
            return 1.0
        K = a * (1 + gam + 2 * eta) / (1 - gam - a)                 # (G4)
        pn = min(1.0, a * K / (W + K) + gam * (2 * a / W + gam) + 2 * delta * nu * (1 + a))
        if p_fix is not None:
            return pn
        if abs(pn - p) < 1e-10:
            break
        p = 0.5 * (p + pn)
    return p

def dcf_constants(eps, W=W0, delta=DELTA, slot=SLOT, difs=DIFS):
    """Occupancy ceiling rho* and protocol time tau_0. Eqs. (G6)-(G8)."""
    rho = (-eps * (W - 1) + math.sqrt(eps ** 2 * (W - 1) ** 2 + 4 * eps * W)) / 2
    D0, s = W - (W - 1) * rho, slot * (W - 1) / 2
    dp0 = (2 * rho * D0 + (W - 1) * rho ** 2) / D0 ** 2
    c_eff = rho ** 2 * W * ((difs + 2 * s) * (1 - rho) + difs) / D0 ** 2 + 2 * rho * difs / W + 2 * delta * (1 + rho)
    return rho, c_eff / dp0

def n_law(f, Tf, eps, **kw):
    rho, tau0 = dcf_constants(eps, **kw)
    return 1 + rho / (f * ((1 - eps / 2) * (Tf - kw.get('delta', DELTA)) + tau0))      # (G9)

def n_root(f, Tf, eps, **kw):
    lo, hi = 0.0, 1.0 / Tf
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if loss(m, Tf, p_fix=eps, **kw) < eps else (lo, m)
    return 1 + lo / f

def n_master(Lam, b, Phi, Psi, Beta):
    """Eq. (G10): shared resource with per-frame cost Phi, per-record cost Psi, budget Beta."""
    return 1 + Beta * b / (Lam * (Phi + Psi * b))

def simulate(N, f, Tf, W=W0, delta=DELTA, slot=SLOT, difs=DIFS, dur=20.0, seed=0,
             poisson=False, gap_backoff=False, join=True):
    """Event simulation, rule set A: a frame that finds the medium idle for DIFS is sent at once;
    one that arrives in the DIFS after a busy period is sent at its end without backoff
    (gap_backoff=True: it draws a backoff instead); one that arrives to a busy medium draws a
    uniform backoff in 0..W-1. A start cannot be sensed for delta (join=False: backoff expiries
    are exempt). Overlapping frames are all lost. Returns the lost fraction of frames."""
    rnd, per, arr = random.Random(seed), 1.0 / f, []
    for _ in range(N):
        if poisson:
            t = rnd.expovariate(f)
            while t < dur:
                arr.append(t); t += rnd.expovariate(f)
        else:
            k = 0
            while k * per < dur:
                arr.append(k * per + rnd.random() * per); k += 1
    arr.sort(); na, ia = len(arr), 0
    t_idle, backlog, sent, lost = -1.0, [], 0, 0
    while ia < na or backlog:
        t0 = t_idle + difs
        tb = t0 + min(backlog) * slot if backlog else float('inf')
        ta = arr[ia] if ia < na else float('inf')
        if ta < tb and ta < t0:
            backlog.append(rnd.randrange(W) if gap_backoff else 0); ia += 1; continue
        ts = min(ta, tb)
        n = int(math.floor((ts - t0) / slot + 1e-9)) if ts >= t0 else 0
        lim, tx, rest = ts + (delta if join else 0) + 1e-12, 0, []
        for c in backlog:
            if t0 + c * slot <= lim: tx += 1
            else: rest.append(c - n)
        while ia < na and arr[ia] <= ts + delta:
            tx += 1; ia += 1
        sent += tx
        if tx > 1: lost += tx
        end = (ts + delta if tx > 1 else ts) + Tf
        while ia < na and arr[ia] < end:
            rest.append(rnd.randrange(W)); ia += 1
        backlog, t_idle = rest, end
    return lost / sent

def sim_capacity(f, Tf, eps=0.05, seeds=4, **kw):
    g = n_root(f, Tf, eps)
    Ns = [max(2, int(round(g * k))) for k in (0.85, 0.95, 1.05, 1.15, 1.25)]
    ps = [sum(simulate(N, f, Tf, seed=s, **kw) for s in range(seeds)) / seeds for N in Ns]
    for i in range(len(Ns) - 1):
        if ps[i] <= eps <= ps[i + 1]:
            return Ns[i] + (eps - ps[i]) / (ps[i + 1] - ps[i]) * (Ns[i + 1] - Ns[i])
    return float('nan')

if __name__ == "__main__":
    for eps in (0.02, 0.05, 0.10):
        r, t = dcf_constants(eps)
        print("eps=%.2f  rho*=%.3f  tau_0=%.1f us" % (eps, r, t * 1e6))
    for Tf, f in ((200e-6, 12.5), (340e-6, 12.5), (600e-6, 12.5)):
        s = sim_capacity(f, Tf)
        print("Tf=%3.0f us f=%.1f: simulated %.1f | full model %.1f | law %.1f"
              % (Tf * 1e6, f, s, n_root(f, Tf, 0.05), n_law(f, Tf, 0.05)))
