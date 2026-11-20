"""Check p_loss = p_c(1 - q) and the capacity law with eps -> eps/(1 - q) when a receiver
decodes the strongest of k overlapping frames (Rayleigh fading, equal mean power, threshold theta):
a given colliding frame survives at a given receiver with probability (1+theta)^-(k-1)/k * k ...
exactly: P(tagged is decoded) = P(S_t > theta * sum of others) = (1+theta)^-(k-1)."""
import random, math, sys
sys.path.insert(0,'/home/claude/out')
from closed_form_model import n_law, n_root, SLOT, DIFS, W0, DELTA
def sim(N,f,Tf,theta,dur=20.0,seed=0,W=W0,delta=DELTA,slot=SLOT,difs=DIFS):
    rnd=random.Random(seed); per=1/f; arr=[]
    for _ in range(N):
        k=0
        while k*per<dur: arr.append(k*per+rnd.random()*per); k+=1
    arr.sort(); na=len(arr); ia=0; t_idle=-1.0; bl=[]; sent=0; lost=0.0; ties=0; tiesk2=0
    while ia<na or bl:
        t0=t_idle+difs; tb=t0+min(bl)*slot if bl else float('inf'); ta=arr[ia] if ia<na else float('inf')
        if ta<tb and ta<t0: bl.append(0); ia+=1; continue
        ts=min(ta,tb); n=int(math.floor((ts-t0)/slot+1e-9)) if ts>=t0 else 0
        tx=0; rest=[]
        for c in bl:
            if t0+c*slot<=ts+delta+1e-12: tx+=1
            else: rest.append(c-n)
        while ia<na and arr[ia]<=ts+delta: tx+=1; ia+=1
        sent+=tx
        if tx>1:
            q=(1+theta)**(-(tx-1))          # per frame, per receiver, expected
            lost+=tx*(1-q); ties+=tx; tiesk2+=tx*(tx==2)
        end=(ts+delta if tx>1 else ts)+Tf
        while ia<na and arr[ia]<end: rest.append(rnd.randrange(W)); ia+=1
        bl=rest; t_idle=end
    return lost/sent, ties/sent, tiesk2/max(ties,1)
def cap(f,Tf,theta,eps,guess):
    Ns=[int(round(guess*k)) for k in (0.85,0.95,1.05,1.15,1.25,1.35)]
    ps=[sum(sim(N,f,Tf,theta,seed=s)[0] for s in range(4))/4 for N in Ns]
    for i in range(5):
        if ps[i]<=eps<=ps[i+1]: return Ns[i]+(eps-ps[i])/(ps[i+1]-ps[i])*(Ns[i+1]-Ns[i])
    return float('nan'), ps
for thdb in (4.0,10.0):
    th=10**(thdb/10); q=1/(1+th)
    for Tf,f in ((304e-6,12.5),(268e-6,50.0)):
        e=0.05; ee=e/(1-q)
        law=n_law(f,Tf,ee); root=n_root(f,Tf,ee); s=cap(f,Tf,th,e,root)
        pc,share,k2=sim(int(round(root)),f,Tf,th,seed=9)[0],*sim(int(round(root)),f,Tf,th,seed=9)[1:]
        print("theta=%4.1f dB q=%.3f Tf=%.0f f=%.1f | sim N_max %.1f | law %.1f (%+.1f%%) root %.1f (%+.1f%%) | no-capture law %.1f | 2-frame share of collided %.3f"%(thdb,q,Tf*1e6,f,s,law,100*(law-s)/s,root,100*(root-s)/s,n_law(f,Tf,e),k2))
