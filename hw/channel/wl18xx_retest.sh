#!/bin/bash
# The one WL18xx retest of the gate S0 (Mohamed, 2026-11-23; docs/DECISIONS.md): an AP role on the
# plan's channel with a monitor interface beside it, a set-up F121 did not try. wlcore's source
# says the firmware's receive filters follow its active roles (there is no API to set them), so
# the expected result is 0 frames from the Pis; the run is recorded and not repeated.
#
# Blue 1's only radio is the WL18xx, so the board leaves the home LAN for the run; a deadman
# brings iwd back if the script does not.
#
# Run as root: sudo systemd-run --unit=authbc-wl18xx ... wl18xx_retest.sh <open-epoch> <seconds> [channel]
#              wl18xx_retest.sh revert
set -u
OUT="$(dirname "$(readlink -f "$0")")"
IW="${IW:-/usr/sbin/iw}"
log() { echo "[$(date -Is)] $*" >>"$OUT/wl18xx.log"; }

revert() {
    pkill -f "tcpdump -i mon0" 2>/dev/null
    pkill -f "hostapd $OUT/wl18xx_ap.conf" 2>/dev/null
    $IW dev mon0 del 2>/dev/null
    ip link set wlan0 down 2>/dev/null
    $IW dev wlan0 set type managed >>"$OUT/wl18xx.log" 2>&1
    ip link set wlan0 up 2>/dev/null
    systemctl start iwd 2>/dev/null
    systemctl stop authbc-wl18xx-revert.timer 2>/dev/null
    log "reverted: hostapd and mon0 gone, wlan0 managed, iwd started; deadman disarmed"
    sync
}
if [ "${1:-}" = revert ]; then revert; exit 0; fi

OPEN="$1"
SECONDS_RUN="$2"
CHANNEL="${3:-11}"
lead=$((OPEN - $(date +%s))); [ $lead -lt 0 ] && lead=0
systemctl stop authbc-wl18xx-revert.timer 2>/dev/null
systemd-run --on-active=$((lead + SECONDS_RUN + 300)) --unit=authbc-wl18xx-revert "$0" revert \
    >>"$OUT/wl18xx.log" 2>&1
log "deadman armed | open=$OPEN seconds=$SECONDS_RUN channel=$CHANNEL | kernel $(uname -r)"

# The AP role (untried in F121), then the monitor interface beside it, both read back.
printf 'interface=wlan0\ndriver=nl80211\nssid=authbc-wl18xx-probe\nhw_mode=g\nchannel=%s\n' \
    "$CHANNEL" >"$OUT/wl18xx_ap.conf"
systemctl stop iwd
hostapd -B "$OUT/wl18xx_ap.conf" >>"$OUT/wl18xx.log" 2>&1
$IW phy phy0 interface add mon0 type monitor >>"$OUT/wl18xx.log" 2>&1
ip link set mon0 up
log "roles: $($IW dev 2>/dev/null | grep -E 'Interface|type|channel' | tr -s ' \t\n' ' ')"

wait_s=$((OPEN - $(date +%s)))
[ $wait_s -gt 0 ] && sleep $wait_s
PCAP="$OUT/wl18xx_$(hostname)_${OPEN}.pcap"
timeout "$SECONDS_RUN" tcpdump -i mon0 -s 256 -w "$PCAP" >>"$OUT/wl18xx.log" 2>&1
log "capture done: $(stat -c %s "$PCAP" 2>/dev/null) bytes"
revert
