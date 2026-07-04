#!/usr/bin/env bash
# provision.sh — one-shot RPi4 provisioning for the P7 hardware campaign (docs/04 §4, docs/06 §1).
# Pins the performance governor, installs the deps to build Python 3.12 (Bookworm ships 3.11 but
# the repo pins requires-python>=3.12), disables wifi power-save (skews 802.11 airtime), enables
# NTP, and snapshots device metadata to results/hw/meta/. Idempotent; refuses to run off a Pi so
# an accidental x86/WSL invocation can't misconfigure this dev box. Needs sudo for apt + governor.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
META="$REPO/results/hw/meta"

# --- guard: RPi4 only ------------------------------------------------------------------------
MODEL_FILE=/proc/device-tree/model
MODEL="$( [ -r "$MODEL_FILE" ] && tr -d '\0' <"$MODEL_FILE" || echo unknown )"
if ! printf '%s' "$MODEL" | grep -qi "raspberry pi"; then
  echo "ERROR: this is a Raspberry Pi provisioning script but this host is not a Pi" >&2
  echo "       (/proc/device-tree/model = '$MODEL')." >&2
  echo "       Run it on the RPi4 target, not on the x86/WSL dev box. Aborting." >&2
  exit 1
fi
echo "== provisioning: $MODEL =="

# --- apt deps (build-essential + pyenv build deps so we can build CPython 3.12) ---------------
echo "-- installing apt dependencies (sudo) --"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  build-essential git cpufrequtils python3-venv \
  libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev liblzma-dev

# --- CPU governor -> performance (docs/06 §1: RPi4 runs pin performance) ----------------------
echo "-- setting CPU governor to performance --"
if command -v cpufreq-set >/dev/null 2>&1; then
  for c in $(seq 0 "$(( $(nproc) - 1 ))"); do sudo cpufreq-set -c "$c" -g performance; done
else
  for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance | sudo tee "$g" >/dev/null
  done
fi
# verify it actually took (abort if not — a silently-ignored governor invalidates every timing)
GOV="$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unknown)"
if [ "$GOV" != "performance" ]; then
  echo "ERROR: governor is '$GOV', expected 'performance' — refusing to proceed." >&2
  exit 1
fi
echo "   governor = $GOV (verified on all cores)"

# --- radio + headless hygiene -----------------------------------------------------------------
# wifi power-save duty-cycles the NIC and skews the P7b 802.11 airtime measurement — turn it off.
if command -v iw >/dev/null 2>&1 && [ -d /sys/class/net/wlan0 ]; then
  sudo iw dev wlan0 set power_save off || echo "   (warn: could not disable wlan0 power_save)"
  echo "   wlan0 power_save: $(iw dev wlan0 get power_save 2>/dev/null || echo unknown)"
fi
# headless: boot to console, no desktop (raspi-config nonint B1 = console autologin off).
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_boot_behaviour B1 || echo "   (warn: raspi-config headless step skipped)"
fi

# --- clock: NTP on (perf_counter_ns is monotonic; NTP only matters for cross-node log correlation)
echo "-- enabling NTP time sync --"
sudo timedatectl set-ntp true || echo "   (warn: timedatectl set-ntp failed)"
timedatectl show -p NTP -p NTPSynchronized 2>/dev/null || true

# --- Python 3.12 note (repo pins requires-python>=3.12; Bookworm ships 3.11) -------------------
PYV="$(python3 --version 2>&1 | awk '{print $2}')"
echo "-- system python3 = $PYV --"
case "$PYV" in
  3.12.*|3.13.*) echo "   OK: python3 >= 3.12; run 'make setup' directly." ;;
  *) cat <<'EOF'
   NOTE: system python3 < 3.12. Install 3.12 with pyenv, then point make at it:
     curl -fsSL https://pyenv.run | bash    # then add pyenv to your shell rc
     pyenv install 3.12 && pyenv local 3.12
     make setup PYTHON="$(pyenv which python)"
   (build deps above are already installed.)
EOF
  ;;
esac

# --- snapshot baseline device metadata --------------------------------------------------------
mkdir -p "$META"
{
  echo "model=$MODEL"
  echo "governor=$GOV"
  echo "python3=$PYV"
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "temp=$(vcgencmd measure_temp 2>/dev/null || echo NA)"
  echo "throttled=$(vcgencmd get_throttled 2>/dev/null || echo NA)"
} >"$META/provision.env"
lscpu >"$META/lscpu.txt" 2>/dev/null || true
cp /etc/os-release "$META/os-release.txt" 2>/dev/null || true

echo "== provisioned. metadata -> $META ; next: hw/run_micro.sh =="
