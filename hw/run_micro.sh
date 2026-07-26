#!/usr/bin/env bash
# run_micro.sh — rerun the P1 microbenchmark suite on the RPi4 and harvest the CSVs to
# results/hw/ with the REAL device governor/temp/throttle folded into the header (the shared
# provenance.env_block hard-codes "WSL, governor uncontrolled", so we augment it here).
# Reuses the exact P1 harness (authbc.bench.micro) — only the platform changes (docs/04 §1,4).
#
# Usage:  hw/run_micro.sh [--seed N] [--n N]     run the suite, write results/hw/p1_*.<host>.csv
#         hw/run_micro.sh --check                x86 self-test: imports + paths resolve, no run
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$REPO/.venv/bin/python}"
RAW="$REPO/results/raw"
HWDIR="$REPO/results/hw"
SEED=1
N=10000
CHECK=0
while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1; shift ;;
    --seed) SEED="$2"; shift 2 ;;
    --n) N="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# --- self-test (runs anywhere incl. x86; touches nothing) -------------------------------------
if [ "$CHECK" -eq 1 ]; then
  [ -x "$PY" ] || { echo "FAIL: python not found/executable at $PY (run 'make setup')" >&2; exit 1; }
  "$PY" -c "import authbc.bench.micro" || { echo "FAIL: cannot import authbc.bench.micro" >&2; exit 1; }
  [ -d "$RAW" ] && [ -d "$HWDIR" ] || { echo "FAIL: results/raw or results/hw missing" >&2; exit 1; }
  echo "OK: run_micro.sh --check passed ($("$PY" --version 2>&1); micro suite importable)"
  exit 0
fi

# --- device metadata (real values; NA off a Pi) -----------------------------------------------
HOST="$(hostname -s)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
METADIR="$HWDIR/meta/$HOST-$TS"
mkdir -p "$METADIR"
gov() { cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown; }
temp() { vcgencmd measure_temp 2>/dev/null || echo NA; }
throt() { vcgencmd get_throttled 2>/dev/null | cut -d= -f2 || echo NA; }
MODEL="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo unknown)"
GOV="$(gov)"
T_BEFORE="$(temp)"; THR_BEFORE="$(throt)"

# thermal guard: warn on non-performance governor before we waste a 10k-iter run on bad data
if [ "$GOV" != "performance" ]; then
  echo "WARNING: governor='$GOV' (expected 'performance') — run hw/provision.sh first." >&2
fi

lscpu >"$METADIR/lscpu.txt" 2>/dev/null || true
cp /etc/os-release "$METADIR/os-release.txt" 2>/dev/null || true

# --- back up any existing x86 p1_*.csv so we never clobber the frozen dev-box data -------------
BK="$(mktemp -d)"
trap 'rm -rf "$BK"' EXIT
for f in p1_sizes.csv p1_crypto.csv; do
  [ -f "$RAW/$f" ] && cp "$RAW/$f" "$BK/$f"
done

echo "== running P1 micro suite on $MODEL (seed=$SEED n=$N) =="
"$PY" -m authbc.bench.micro --seed "$SEED" --n "$N"

T_AFTER="$(temp)"; THR_AFTER="$(throt)"
# THERMAL GUARD. get_throttled is a bitmask with TWO halves (raspberrypi.com docs):
#   bits 0-3  = state NOW      : 0x1 under-volt, 0x2 freq-capped, 0x4 throttled, 0x8 soft-temp-limit
#   bits 16-19 = HAS OCCURRED since boot (STICKY — only cleared by a reboot)
# The old "!= 0x0" test conflated the two, so once a board had ever throttled EVERY later run was
# flagged until reboot. The precise question is whether throttling happened during THIS run:
#   invalid  <=> any NOW bit set at either sample, OR the sticky half CHANGED across the run.
# A sticky bit that was already set before the run and did not change is history, not this run —
# it still earns a loud warning (the board demonstrably throttles under load) but not an invalid tag.
bits()   { [ "$1" = "NA" ] && echo 0 || echo $(( $1 )); }
now_b=$(( $(bits "$THR_BEFORE") & 0xF ));     now_a=$(( $(bits "$THR_AFTER") & 0xF ))
stk_b=$(( ($(bits "$THR_BEFORE") >> 16) & 0xF )); stk_a=$(( ($(bits "$THR_AFTER") >> 16) & 0xF ))
FLAG=""
if [ "$now_b" -ne 0 ] || [ "$now_a" -ne 0 ] || [ "$stk_a" -ne "$stk_b" ]; then
  FLAG=".THROTTLED"
  echo "!! THROTTLED DURING THIS RUN: before=$THR_BEFORE after=$THR_AFTER ($T_BEFORE -> $T_AFTER)" >&2
  [ $(( (stk_a | now_a) & 0x1 )) -ne 0 ] \
    && echo "!!   UNDER-VOLTAGE -> power problem: use 5.15-5.2 V, check the shunt/cable." >&2
  [ $(( (stk_a | now_a) & 0xE )) -ne 0 ] \
    && echo "!!   THERMAL -> cooling problem: fit a heatsink + fan and re-run." >&2
  echo "!! this run is FLAGGED (filename tagged $FLAG) — do NOT use for the paper tables." >&2
elif [ "$stk_b" -ne 0 ]; then
  echo "WARNING: sticky throttle bits were ALREADY set before this run (before=$THR_BEFORE)." >&2
  echo "         No NEW throttling was recorded during the run, so the data is usable — but the" >&2
  echo "         board throttles under load. REBOOT to clear the sticky bits and re-run for a" >&2
  echo "         pristine baseline before recording paper numbers." >&2
fi

# --- harvest fresh CSVs to results/hw/ with real device-meta prepended, then restore x86 data --
prepend_meta() {  # $1=src csv  $2=dest csv
  { echo "# device_model=$MODEL"
    echo "# device_host=$HOST"
    echo "# device_governor=$GOV"
    echo "# device_temp_before=$T_BEFORE"
    echo "# device_temp_after=$T_AFTER"
    echo "# device_throttled_before=$THR_BEFORE"
    echo "# device_throttled_after=$THR_AFTER"
    echo "# run_utc=$TS"
    cat "$1"
  } >"$2"
}
prepend_meta "$RAW/p1_sizes.csv"  "$HWDIR/p1_sizes.$HOST$FLAG.csv"
prepend_meta "$RAW/p1_crypto.csv" "$HWDIR/p1_crypto.$HOST$FLAG.csv"

for f in p1_sizes.csv p1_crypto.csv; do
  if [ -f "$BK/$f" ]; then cp "$BK/$f" "$RAW/$f"; else rm -f "$RAW/$f"; fi
done

echo "== wrote results/hw/p1_{sizes,crypto}.$HOST$FLAG.csv ; meta -> $METADIR =="
echo "   x86 results/raw/p1_*.csv restored untouched."
