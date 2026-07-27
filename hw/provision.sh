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

# --- guard: 64-bit (arm64) USERLAND, not just a 64-bit kernel ---------------------------------
# The 32-bit image reports uname -m = aarch64 (64-bit kernel) but dpkg arch = armhf, and its wheel
# platform tag is armv8l. PyPI publishes NO armhf/armv8l wheels for scipy (and several others), so
# `make setup` dies with "metadata-generation-failed x scipy" ~30 min in. Catch it here instead.
# It also matters scientifically: both nodes must be the SAME architecture or the cross-node and
# x86-vs-ARM comparisons are confounded.
DEB_ARCH="$(dpkg --print-architecture 2>/dev/null || echo unknown)"
if [ "$DEB_ARCH" != "arm64" ]; then
  echo "ERROR: 32-bit userland detected — dpkg architecture is '$DEB_ARCH', expected 'arm64'." >&2
  echo "       ($(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME"); kernel $(uname -m).)" >&2
  echo "       'Raspbian GNU/Linux' = the 32-bit image; the 64-bit one reports 'Debian GNU/Linux'." >&2
  echo "" >&2
  echo "       FIX: reflash with Raspberry Pi Imager ->" >&2
  echo "            Raspberry Pi OS (other) -> 'Raspberry Pi OS Lite (64-bit)'" >&2
  echo "            (NOT the 32-bit or 'Legacy, 32-bit' entries)." >&2
  echo "       Verify after boot:  dpkg --print-architecture   # must print arm64" >&2
  echo "       Aborting: scipy/numpy have no 32-bit ARM wheels and would fail to build." >&2
  exit 1
fi
echo "   userland arch = $DEB_ARCH (64-bit) OK"

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

# PERSIST it. `cpufreq-set` is RUNTIME-ONLY: after a reboot the governor silently reverts to
# ondemand, and any measurement taken then is invalid (this cost us a full energy campaign — the
# board rebooted mid-run and every later window was measured at the wrong clock policy). Install a
# systemd unit so the setting survives reboots, and also write the cpufrequtils default.
echo 'GOVERNOR="performance"' > /etc/default/cpufrequtils 2>/dev/null || true
cat >/etc/systemd/system/authbc-governor.service <<'UNIT'
[Unit]
Description=AUTHBC: pin CPU governor to performance (measurement validity)
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done'

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload >/dev/null 2>&1 || true
systemctl enable --now authbc-governor.service >/dev/null 2>&1 \
  && echo "   governor PERSISTED across reboots (authbc-governor.service)" \
  || echo "   (warn: could not enable authbc-governor.service — governor will revert on reboot)"

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
# This script runs under sudo (apt + governor), so anything it creates in the repo would be
# root-owned and the normal user could no longer write there — which breaks hw/run_micro.sh with
# "Permission denied" on results/hw/meta. Create as root, then hand ownership back.
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

# hand the repo back to the invoking user (see the note above)
if [ -n "${SUDO_USER:-}" ]; then
  chown -R "$SUDO_USER":"$(id -gn "$SUDO_USER")" "$REPO/results" 2>/dev/null || true
  echo "   repo results/ ownership returned to $SUDO_USER"
fi

echo "== provisioned. metadata -> $META ; next: hw/run_micro.sh =="
