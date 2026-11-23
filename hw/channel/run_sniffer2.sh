#!/bin/bash
# The frame-level campaign's sniffer (docs/DECISIONS.md, 2026-11-23): the TP-Link TL-WN722N on
# Blue 2, driver rtl8188eus af3bf004 plus the approved TSF line, in monitor mode on the plan's
# channel. Derived from run_sniffer.sh (the WL18xx sniffer of W1d, kept as the record of F121).
# What differs:
#   * the interface is the USB adapter (default tplink0); the Blue's own TI radio stays on the home
#     LAN on channel 1, so the board stays reachable and its supply and boot can be watched;
#   * the capture runs from 60 s before the plan's start to 60 s after its end: those two minutes,
#     with the Pis in their cell but silent, are the session's channel-occupancy captures;
#   * frames are kept to 256 B, enough for the sender, its sequence number and the UDP length;
#   * a heartbeat every HEARTBEAT_S seconds logs the boot ID, the interface's type and channel and
#     the capture's size, so a reset (F126) is dated by the log, not guessed;
#   * the driver's identity (kernel, module srcversion, the .ko's SHA-256) is logged at the start.
#
# Run as root (the Blues have no passwordless sudo): sudo systemd-run --unit=authbc-sniff2 ...
#   run_sniffer2.sh <plan-start-epoch> <plan-seconds> [iface] [channel]
#   run_sniffer2.sh revert [iface]                 # what the deadman calls
set -u
OUT="$(dirname "$(readlink -f "$0")")"
IW="${IW:-/usr/sbin/iw}"
HEARTBEAT_S="${HEARTBEAT_S:-60}"
MARGIN_S="${MARGIN_S:-60}"
log() { echo "[$(date -Is)] $*" >>"$OUT/sniffer.log"; }
boot_id() { cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; }

revert() {
    local ifc="${1:-tplink0}"
    pkill -f "tcpdump -i $ifc" 2>/dev/null
    ip link set "$ifc" down 2>/dev/null
    $IW dev "$ifc" set type managed >>"$OUT/sniffer.log" 2>&1
    systemctl stop authbc-sniff2-revert.timer 2>/dev/null
    log "reverted: $ifc down and managed ($($IW dev "$ifc" info 2>/dev/null | grep -E 'type' | tr -s ' \t\n' ' ')); boot $(boot_id); deadman disarmed"
    sync
}
if [ "${1:-}" = revert ]; then revert "${2:-tplink0}"; exit 0; fi

START_EPOCH="$1"
PLAN_S="$2"
IFACE="${3:-tplink0}"
CHANNEL="${4:-11}"
BEGIN=$((START_EPOCH - MARGIN_S))
SPAN_S=$((PLAN_S + 2 * MARGIN_S))
HOST=$(hostname)

# ---- 1. The deadman first, sized to the capture ---------------------------------------------
systemctl stop authbc-sniff2-revert.timer 2>/dev/null
lead=$((BEGIN - $(date +%s))); [ $lead -lt 0 ] && lead=0
systemd-run --on-active=$((lead + SPAN_S + 300)) --unit=authbc-sniff2-revert \
    "$0" revert "$IFACE" >>"$OUT/sniffer.log" 2>&1
log "deadman armed | iface=$IFACE channel=$CHANNEL begin=$BEGIN span_s=$SPAN_S boot $(boot_id)"
log "env: kernel $(uname -r) | module $(modinfo -F srcversion 8188eu 2>/dev/null) | ko sha256 $(sha256sum "$(modinfo -n 8188eu 2>/dev/null)" 2>/dev/null | cut -c1-16)"

# ---- 2. Monitor mode, read back -------------------------------------------------------------
ip link set "$IFACE" down
$IW dev "$IFACE" set type monitor >>"$OUT/sniffer.log" 2>&1
$IW dev "$IFACE" set monitor fcsfail control otherbss >>"$OUT/sniffer.log" 2>&1
ip link set "$IFACE" up
$IW dev "$IFACE" set channel "$CHANNEL" >>"$OUT/sniffer.log" 2>&1
STATE=$($IW dev "$IFACE" info 2>/dev/null | grep -E 'type|channel' | tr -s ' \t\n' ' ')
log "monitor: $STATE"
if ! grep -q "type monitor" <<<"$STATE"; then
    log "the interface is not in monitor mode; no capture"
    revert "$IFACE"
    exit 1
fi

# ---- 3. The capture, from MARGIN_S before the plan to MARGIN_S after it ----------------------
wait_s=$((BEGIN - $(date +%s)))
[ $wait_s -gt 0 ] && sleep $wait_s
PCAP="$OUT/sniff_${HOST}_${START_EPOCH}.pcap"
timeout "$SPAN_S" tcpdump -i "$IFACE" -s 256 -U -w "$PCAP" >>"$OUT/sniffer.log" 2>&1 &
cap=$!
while kill -0 "$cap" 2>/dev/null; do
    sleep "$HEARTBEAT_S"
    log "heartbeat: boot $(boot_id) | $($IW dev "$IFACE" info 2>/dev/null | grep -E 'type|channel' | tr -s ' \t\n' ' ')| pcap $(stat -c %s "$PCAP" 2>/dev/null) B"
done
wait "$cap"
log "capture done: $(stat -c %s "$PCAP" 2>/dev/null) bytes; boot $(boot_id)"
revert "$IFACE"
