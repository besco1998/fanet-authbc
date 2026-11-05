#!/bin/bash
# A BeagleBone Blue listens to a window plan's channel in monitor mode (predictions/W1d.md).
#
# The Blues' TI WL18xx radios cannot join an ad-hoc cell (no IBSS: F120), but they can listen to
# everything on a channel. During a session one runs this: it leaves the home Wi-Fi, opens a
# monitor interface on the plan's channel, records every frame from the plan's start for the
# plan's length, writes tcpdump's text decoding beside the capture, and returns to the home
# Wi-Fi. What it counts is reported, not scored: frames on air per source, foreign frames on the
# channel, frames that failed their check sequence.
#
# Run as root (the Blues have no passwordless sudo): sudo systemd-run --unit=authbc-sniff ...
#   run_sniffer.sh <start-epoch> <plan-file> [channel]     # default channel 11
#   run_sniffer.sh revert                                  # what the deadman calls
set -u
OUT="$(dirname "$(readlink -f "$0")")"
IW=/usr/sbin/iw
log() { echo "[$(date -Is)] $*" >>"$OUT/sniffer.log"; }

revert() {
    pkill -f "tcpdump -i mon0" 2>/dev/null
    $IW dev mon0 del 2>/dev/null
    ip link set wlan0 up 2>/dev/null
    systemctl start iwd 2>/dev/null
    sleep 15
    if ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.'; then
        systemctl stop authbc-sniff-revert.timer 2>/dev/null
        log "reverted OK: back on the home Wi-Fi, deadman disarmed"
    else
        log "revert did not restore the LAN address yet — deadman left armed"
    fi
}
if [ "${1:-}" = revert ]; then revert; exit 0; fi

START_EPOCH="$1"
PLAN="$2"
CHANNEL="${3:-11}"
WINDOWS=$(grep -cvE '^\s*(#|$)' "$PLAN")
SESSION_S=$(( WINDOWS * 30 + 120 ))
HOST=$(hostname)

systemctl stop authbc-sniff-revert.timer 2>/dev/null
systemd-run --on-active=$((SESSION_S + 300)) --unit=authbc-sniff-revert "$0" revert \
    >>"$OUT/sniffer.log" 2>&1
log "deadman armed: revert $((SESSION_S + 300)) s | channel=$CHANNEL windows=$WINDOWS plan=$(basename "$PLAN") sha=$(sha256sum "$PLAN" | cut -c1-12)"

systemctl stop iwd
ip link set wlan0 down
$IW phy phy0 interface add mon0 type monitor >>"$OUT/sniffer.log" 2>&1
$IW dev mon0 set monitor fcsfail control otherbss >>"$OUT/sniffer.log" 2>&1
ip link set mon0 up
$IW dev mon0 set channel "$CHANNEL" >>"$OUT/sniffer.log" 2>&1
log "monitor: $($IW dev mon0 info 2>/dev/null | grep -E 'type|channel' | tr '\n' ' ')"

wait_s=$((START_EPOCH - $(date +%s)))
[ $wait_s -gt 0 ] && sleep $wait_s
PCAP="$OUT/sniff_${HOST}_${START_EPOCH}.pcap"
timeout "$SESSION_S" tcpdump -i mon0 -s 160 -w "$PCAP" >>"$OUT/sniffer.log" 2>&1
log "capture done: $(stat -c %s "$PCAP" 2>/dev/null) bytes"
tcpdump -r "$PCAP" -tt -e -n >"${PCAP%.pcap}.txt" 2>>"$OUT/sniffer.log"
log "decoded: $(wc -l <"${PCAP%.pcap}.txt") lines"
revert
