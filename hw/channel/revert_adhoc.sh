#!/bin/bash
# Return wlan0 from a raw-`iw` ad-hoc cell to NetworkManager control and the LAN.
#
# Runs as root. Called from three places: the end of a normal session, the 600 s deadman, and
# by hand for recovery. It is therefore written to be **idempotent** — every step tolerates
# already being in the target state, because the deadman routinely fires on a session that has
# already reverted itself.
set -u
OUT=/home/pi/authbc_channel
LOG="$OUT/session.log"
log() { echo "[$(date -Is)] revert: $*" >>"$LOG"; }

log "starting"

# Leave the cell before changing type: `iw set type` fails while the interface is joined.
/usr/sbin/iw dev wlan0 ibss leave 2>/dev/null
ip addr flush dev wlan0 2>/dev/null
ip link set wlan0 down 2>/dev/null
/usr/sbin/iw dev wlan0 set type managed 2>/dev/null
ip link set wlan0 up 2>/dev/null

# wpa_supplicant must be back before NM can associate. The session stops it so that it cannot
# re-associate to the AP and fight the IBSS join — restarting it here is what makes the AP
# path work again, and skipping it leaves a managed interface that never associates.
systemctl start wpa_supplicant 2>/dev/null
nmcli dev set wlan0 managed yes 2>/dev/null
sleep 3
nmcli con up preconfigured 2>/dev/null
sleep 5

log "finished, wlan0 = $(ip -4 -o addr show wlan0 | grep -oE 'inet [0-9.]+' || echo NONE)"
