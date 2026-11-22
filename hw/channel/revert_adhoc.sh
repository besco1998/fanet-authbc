#!/bin/bash
# Return wlan0 from a raw-`iw` ad-hoc cell to NetworkManager control and the LAN.
#
# Runs as root. Called from three places: the end of a normal session, the 600 s deadman, and
# by hand for recovery. It is therefore written to be **idempotent** — every step tolerates
# already being in the target state, because the deadman routinely fires on a session that has
# already reverted itself.
set -u
OUT="$(dirname "$(readlink -f "$0")")"   # the folder this script was deployed to (any login)
LOG="$OUT/session.log"
log() { echo "[$(date -Is)] revert: $*" >>"$LOG"; }
# Each step's exit code, duration and messages go to the session log, and the kernel log is kept
# beside it on the SD card: on 2026-11-22 pi-B's revert took 159 s twice, ended with no LAN
# address, and its volatile journal kept nothing of which step hung or what the driver said.
step() {
    local name=$1 t0 rc
    shift
    t0=$(date +%s%N)
    "$@" >>"$LOG" 2>&1
    rc=$?
    log "step $name rc=$rc $(( ($(date +%s%N) - t0) / 1000000 )) ms"
    return $rc
}
KLOG="$OUT/revert_kernel_$(date +%Y%m%dT%H%M%S)_$$.log"
kernel_log() { { echo "== $1 $(date -Is)"; dmesg | tail -n 80; } >>"$KLOG" 2>&1; }

log "starting"
kernel_log "at start"

# A session may have switched the chip's frame-burst mode off (frameburst.sh). Put it back to
# what the driver sets, here, so that every way out of a session — normal end, early revert,
# deadman — leaves the board as it was found.
[ -x "$OUT/frameburst.sh" ] && step frameburst_on "$OUT/frameburst.sh" set 1

# Leave the cell before changing type: `iw set type` fails while the interface is joined.
step ibss_leave /usr/sbin/iw dev wlan0 ibss leave
step addr_flush ip addr flush dev wlan0
step link_down ip link set wlan0 down
step type_managed /usr/sbin/iw dev wlan0 set type managed
step link_up ip link set wlan0 up

# wpa_supplicant must be back before NM can associate. The session stops it so that it cannot
# re-associate to the AP and fight the IBSS join — restarting it here is what makes the AP
# path work again, and skipping it leaves a managed interface that never associates.
step wpa_start systemctl start wpa_supplicant
step nm_managed nmcli dev set wlan0 managed yes
sleep 3
# The profile is called `preconfigured` on an image written by Raspberry Pi Imager for Debian 12
# and `netplan-wlan0-<SSID>` on Debian 13. Where the first name does not exist, ask for whichever
# profile the interface has; on a board where it does exist nothing changes.
step con_up nmcli con up preconfigured || step dev_connect nmcli dev connect wlan0
sleep 5

kernel_log "at end"
log "finished, wlan0 = $(ip -4 -o addr show wlan0 | grep -oE 'inet [0-9.]+' || echo NONE)"
sync   # the logs must survive the power cut that recovers a locked chip
