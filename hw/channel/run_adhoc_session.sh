#!/bin/bash
# Self-contained ad-hoc measurement session (hardware channel validation).
#
# ⚠️ SSH arrives over wlan0 and there is no ethernet, so switching to ad-hoc DROPS the control
# link. Everything here therefore runs unattended under nohup and reverts itself. A systemd
# deadman is armed FIRST as a second line of defence: even if this script dies mid-way, the Pi
# returns to the AP on its own. The deadman mechanism was tested before being relied on
# (⚠️ note: it must not write to /tmp -- systemd PrivateTmp isolates it).
set -u
ROLE="$1"; SECONDS_RUN="${2:-60}"; RATE="${3:-100}"; SIZE="${4:-1400}"
OUT=/home/pi/authbc_channel; mkdir -p "$OUT"
IP=$([ "$ROLE" = tx ] && echo 10.0.0.1 || echo 10.0.0.2)
log(){ echo "[$(date -Is)] $*" >> "$OUT/session.log"; }

# 1. Deadman FIRST -- restores the AP link no matter what happens below.
sudo -n systemctl stop authbc-revert.timer 2>/dev/null
sudo -n systemd-run --on-active=600 --unit=authbc-revert \
     /bin/sh -c 'nmcli con down authbc-adhoc; nmcli con up preconfigured' >>"$OUT/session.log" 2>&1
log "deadman armed (600 s)"

# 2. Switch to ad-hoc.
sudo -n nmcli con delete authbc-adhoc 2>/dev/null
sudo -n nmcli con add type wifi ifname wlan0 con-name authbc-adhoc ssid authbc-mesh \
     mode adhoc ipv4.method manual ipv4.addresses "$IP/24" ipv6.method disabled \
     802-11-wireless.band bg 802-11-wireless.channel 1 \
     802-11-wireless-security.key-mgmt none >>"$OUT/session.log" 2>&1
# ⚠️ key-mgmt none is REQUIRED. Without it NetworkManager attempts 802.1X on what is an OPEN
# ad-hoc cell and the activation dies with "802.1X supplicant took too long to authenticate"
# (observed on the first run: link never formed, RX received 0 frames).
sudo -n nmcli con down preconfigured >>"$OUT/session.log" 2>&1
sudo -n nmcli con up authbc-adhoc >>"$OUT/session.log" 2>&1
sleep 15
log "adhoc up: $(ip -4 addr show wlan0 | grep -oE 'inet [0-9.]+')  peers: $(/usr/sbin/iw dev wlan0 station dump 2>/dev/null | grep -c Station)"

# 3. Measure.
cd /home/pi/fanet-authbc/hw/channel 2>/dev/null || cd "$OUT"
if [ "$ROLE" = rx ]; then
  python3 "$OUT/bcast_rx.py" --seconds "$SECONDS_RUN" --out "$OUT/rx.json" >>"$OUT/session.log" 2>&1
else
  sleep 5   # let the receiver bind first
  python3 "$OUT/bcast_tx.py" --rate "$RATE" --bytes "$SIZE" \
        --seconds "$((SECONDS_RUN-10))" --out "$OUT/tx.json" >>"$OUT/session.log" 2>&1
fi
log "measurement done"

# 4. Revert, and disarm the deadman only after the AP link is confirmed back.
sudo -n nmcli con down authbc-adhoc >>"$OUT/session.log" 2>&1
sudo -n nmcli con up preconfigured  >>"$OUT/session.log" 2>&1
sleep 10
if ip -4 addr show wlan0 | grep -q '192.168.1.'; then
  sudo -n systemctl stop authbc-revert.timer 2>/dev/null
  log "reverted OK, deadman disarmed"
else
  log "revert did NOT restore the LAN address -- leaving the deadman armed"
fi
