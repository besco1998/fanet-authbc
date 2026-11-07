#!/bin/bash
# Probe (disclosed, not scored): can a TP-Link TL-WN722N v2/v3 (RTL8188EUS) on a BeagleBone Blue,
# driven by the kernel's staging driver r8188eu through wireless extensions, join the Pis' ad-hoc
# cell on channel 11 as node 4, and at what pace does it send? The Blue's own TI radio is taken
# off the air for the probe; a deadman returns everything to the home Wi-Fi.
#
# Run as root:  systemd-run --collect --unit=authbc-probe4 <this> <start-epoch> <plan-file>
#               <this> revert          (what the deadman calls)
# Plan lines as run_window_plan.sh's: <label> <rate_fps> <bytes> <senders>; node 4 is this Blue.
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/probe.log"
IWC=/sbin/iwconfig
log() { echo "[$(date -Is)] $*" >>"$L"; }

revert() {
    pkill -f "bcast_(tx|rx).py" 2>/dev/null
    ip addr flush dev wlan1 2>/dev/null
    $IWC wlan1 essid off 2>/dev/null
    $IWC wlan1 mode managed 2>/dev/null
    ip link set wlan1 down 2>/dev/null
    ip link set wlan0 up 2>/dev/null
    systemctl start iwd
    sleep 25
    if ip -4 addr show 2>/dev/null | grep -q '192\.168\.1\.'; then
        systemctl stop authbc-probe-revert.timer 2>/dev/null
        log "reverted OK: back on the home Wi-Fi, deadman disarmed"
    else
        log "revert: LAN address not back yet — deadman left armed"
    fi
}
if [ "${1:-}" = revert ]; then revert; exit 0; fi

START="$1"
PLAN="$2"
WINDOWS=$(grep -cvE '^\s*(#|$)' "$PLAN")
SESSION_S=$(( WINDOWS * 30 + 120 ))
systemctl stop authbc-probe-revert.timer 2>/dev/null
systemd-run --on-active=$((SESSION_S + 300)) --unit=authbc-probe-revert "$0" revert >/dev/null 2>&1
log "deadman armed: revert in $((SESSION_S + 300)) s | start=$START windows=$WINDOWS plan sha=$(sha256sum "$PLAN" | cut -c1-12)"

# Join 40 s before the first window: the Pis' cell exists by then, so this station joins it.
wait_s=$((START - 40 - $(date +%s)))
[ $wait_s -gt 0 ] && sleep $wait_s
systemctl stop iwd
ip link set wlan0 down
ip link set wlan1 up
sleep 2
$IWC wlan1 mode ad-hoc >>"$L" 2>&1
$IWC wlan1 channel 11 >>"$L" 2>&1
$IWC wlan1 essid authbc-mesh >>"$L" 2>&1
ip addr add 10.0.0.4/24 dev wlan1 >>"$L" 2>&1
sleep 10
log "after join: $($IWC wlan1 2>&1 | tr -s ' ' | tr '\n' ' ')"
for k in 1 2; do
    if ping -c 3 -W 2 "10.0.0.$k" >/dev/null 2>&1; then log "peer 10.0.0.$k reachable"
    else log "peer 10.0.0.$k UNREACHABLE"; fi
done

k=0
while read -r label rate bytes senders; do
    open=$((START + k * 30))
    wait_s=$((open - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s
    tag=$(printf "%02d_%s_%sfps" "$k" "$label" "$rate")
    tp0=$(cat /sys/class/net/wlan1/statistics/tx_packets)
    python3 "$O/bcast_rx.py" --seconds 25 --self 10.0.0.4 --out "$O/rx_node4_$tag.json" >>"$L" 2>&1 &
    rx_pid=$!
    sleep 1
    if [[ ",$senders," == *",4,"* ]]; then
        python3 "$O/bcast_tx.py" --rate "$rate" --bytes "$bytes" --redraw --seed "$((4000 + k))" \
            --seconds 22 --out "$O/tx_node4_$tag.json" >>"$L" 2>&1
    fi
    wait "$rx_pid"
    echo "{\"tag\":\"$tag\",\"node\":4,\"senders\":\"$senders\",\"tx_packets\":$(( $(cat /sys/class/net/wlan1/statistics/tx_packets) - tp0 ))}" \
        >"$O/ctr_node4_$tag.json"
    log "window $tag done"
    k=$((k + 1))
done < <(grep -vE '^\s*(#|$)' "$PLAN")

log "after windows: $($IWC wlan1 2>&1 | tr -s ' ' | tr '\n' ' ')"
revert
