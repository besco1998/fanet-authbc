"""Direction C step 1 — variance and location tests, chosen for bimodal data.

Levene (variance, robust to non-normality) and Mann-Whitney U (location, non-parametric) because
the delivered-fraction distribution under the frozen-phase traffic model is **bimodal**, which rules
out the usual F-test/t-test pair.

⚠️ This script previously read a HARDCODED path into an agent session scratchpad
(`/tmp/claude-.../c1_raw.csv`), so it was unrunnable by anyone else and its input was not the
committed artifact (audit S6). It now defaults to the committed CSV and takes `--csv` to override.

Usage:  python3 analysis/analyse_phase_artifact.py
        python3 analysis/analyse_phase_artifact.py --csv <per-seed artifact>
"""
import argparse
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

from scipy.stats import levene, mannwhitneyu

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO / "results" / "raw" / "lora_phase_artifact_30seed.csv"

ap = argparse.ArgumentParser(description=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                help="per-seed artifact to analyse (default: the committed ALOHA 30-seed run)")
args = ap.parse_args()

# Strip the `# key=value` provenance header before parsing.
_lines = [ln for ln in args.csv.read_text().splitlines() if not ln.startswith("#")]
rows = list(csv.DictReader(_lines))
print(f"# source: {args.csv.relative_to(REPO)}  ({len(rows)} runs)\n")
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
