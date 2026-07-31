"""Direction C step 1 — variance and location tests, chosen for bimodal data."""
import csv
import statistics as st
from collections import defaultdict

from scipy.stats import levene, mannwhitneyu

rows = list(csv.DictReader(open("/tmp/claude-1000/-home-besco1998-authbc-package/"
                                "498f150b-7bcc-4604-aa13-e2dce00bd774/scratchpad/c1_raw.csv")))
g = defaultdict(list)
for r in rows:
    g[(int(r["n_devices"]), float(r["tx_jitter_s"]))].append(float(r["delivered_frac"]))

print(f"{'N':>5} {'cfg':>10} {'n':>3} {'mean':>8} {'SD':>8} {'CV%':>7} {'min':>7} {'max':>7}")
for n in sorted({k[0] for k in g}):
    for j in (0.0, 1.0):
        v = g[(n, j)]
        if not v:
            continue
        cv = st.stdev(v) / st.mean(v) * 100 if len(v) > 1 else 0
        lbl = "frozen" if j == 0 else "jittered"
        print(f"{n:>5} {lbl:>10} {len(v):>3} {st.mean(v):>8.4f} {st.stdev(v):>8.4f} "
              f"{cv:>7.2f} {min(v):>7.4f} {max(v):>7.4f}")

print(f"\n{'N':>5} {'CV ratio':>9} {'Levene p':>12} {'MWU p':>12} {'mean shift %':>13}  verdict")
for n in sorted({k[0] for k in g}):
    a, b = g[(n, 0.0)], g[(n, 1.0)]
    if len(a) < 3 or len(b) < 3:
        continue
    cva = st.stdev(a) / st.mean(a)
    cvb = st.stdev(b) / st.mean(b)
    _, pv = levene(a, b)                       # variance, robust to non-normality
    _, pm = mannwhitneyu(a, b, alternative="two-sided")   # location, non-parametric
    shift = 100 * (st.mean(b) - st.mean(a)) / st.mean(a)
    v = ("variance inflated" if pv < 0.01 and cva > cvb else
         "no variance effect" if pv >= 0.05 else "weak")
    print(f"{n:>5} {cva/cvb:>8.2f}x {pv:>12.2e} {pm:>12.2e} {shift:>+12.2f}   {v}")
