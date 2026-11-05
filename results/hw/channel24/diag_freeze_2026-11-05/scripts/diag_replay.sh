#!/bin/bash
# Diagnosis (not a measurement): probe 3 replayed to find what froze Blue 2 (F125). Identical to
# probe 3's script (results/hw/channel24/probe4c_2026-11-05/node4/blue_probe_iw.sh) up to the end of
# the windows. Then probe 3's revert runs one step at a time, each start and end written and synced
# to the SD card, 3 s apart, while the kernel log streams to the card with a sync every second. A
# freeze leaves the step and any kernel message before it on disk; the watchdog resets the board.
#
# Run as root:  systemd-run --collect --unit=authbc-diag-replay <this> <start-epoch> <plan-file>
#               <this> revert
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/replay.log"
IW=/usr/sbin/iw
TPLINK_MAC=d0:37:45:2b:23:b0
log() { echo "[$(date -Is)] $*" >>"$L"; }
tplink() {   # the TP-Link's interface name, found by its hardware address
    for i in /sys/class/net/*; do
        [ "$(cat "$i/address" 2>/dev/null)" = "$TPLINK_MAC" ] && { basename "$i"; return; }
    done
}

revert() {
    pkill -f "bcast_(tx|rx).py" 2>/dev/null
    local t; t=$(tplink)
    if [ -n "$t" ]; then
        echo "0xff" >"/proc/net/8188eu/$t/rate_ctl" 2>/dev/null
        $IW dev "$t" ibss leave 2>/dev/null
        ip addr flush dev "$t" 2>/dev/null
        ip link set "$t" down 2>/dev/null
        $IW dev "$t" set type managed 2>/dev/null
    fi
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
dmesg -w --time-format iso >>"$O/kern.log" 2>&1 &
KLOG_PID=$!
( while true; do sync; sleep 1; done ) &
SYNC_PID=$!
T=$(tplink)
log "deadman armed: revert in $((SESSION_S + 300)) s | start=$START windows=$WINDOWS plan sha=$(sha256sum "$PLAN" | cut -c1-12) | tplink=$T driver=$(basename "$(readlink -f /sys/class/net/$T/device/driver)")"
[ -n "$T" ] || { log "TP-Link not found"; revert; exit 1; }

# Join 40 s before the first window: the Pis' cell exists by then, so this station joins it.
wait_s=$((START - 40 - $(date +%s)))
[ $wait_s -gt 0 ] && sleep $wait_s
systemctl stop iwd
for i in /sys/class/net/wlan*; do [ "$(basename "$i")" != "$T" ] && ip link set "$(basename "$i")" down; done
ip link set "$T" down
$IW dev "$T" set type ibss >>"$L" 2>&1
ip link set "$T" up
sleep 2
$IW dev "$T" ibss join authbc-mesh 2462 fixed-freq >>"$L" 2>&1
echo "0x00 0" >"/proc/net/8188eu/$T/rate_ctl" 2>>"$L"
log "rate_ctl now: $(cat "/proc/net/8188eu/$T/rate_ctl" 2>&1 | tr '\n' ' ')"
ip addr add 10.0.0.4/24 dev "$T" >>"$L" 2>&1
sleep 10
log "after join: $($IW dev "$T" info 2>&1 | grep -E 'type|channel' | tr '\n' ' ') | $($IW dev "$T" link 2>&1 | tr '\n' ' ')"
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
    tp0=$(cat "/sys/class/net/$T/statistics/tx_packets")
    td0=$(cat "/sys/class/net/$T/statistics/tx_dropped")
    python3 "$O/bcast_rx.py" --seconds 25 --self 10.0.0.4 --out "$O/rx_node4_$tag.json" >>"$L" 2>&1 &
    rx_pid=$!
    sleep 1
    if [[ ",$senders," == *",4,"* ]]; then
        python3 "$O/bcast_tx.py" --rate "$rate" --bytes "$bytes" --redraw --seed "$((4000 + k))" \
            --seconds 22 --out "$O/tx_node4_$tag.json" >>"$L" 2>&1
    fi
    wait "$rx_pid"
    echo "{\"tag\":\"$tag\",\"node\":4,\"senders\":\"$senders\",\"tx_packets\":$(( $(cat "/sys/class/net/$T/statistics/tx_packets") - tp0 )),\"tx_dropped\":$(( $(cat "/sys/class/net/$T/statistics/tx_dropped") - td0 ))}" \
        >"$O/ctr_node4_$tag.json"
    log "window $tag done"
    k=$((k + 1))
done < <(grep -vE '^\s*(#|$)' "$PLAN")

log "rate_ctl at end: $(cat "/proc/net/8188eu/$T/rate_ctl" 2>&1 | tr '\n' ' ')"
sync
# probe 3's revert, one step at a time
step() { echo "[$(date +%T.%3N)] $*" >>"$L"; sync; }
run() { step "BEGIN $*"; "$@" >>"$L" 2>&1; local rc=$?; step "END rc=$rc $*"; sleep 3; }
step "BEGIN pkill"; pkill -f "bcast_(tx|rx).py" 2>/dev/null; step "END pkill"; sleep 3
step "BEGIN rate_ctl 0xff"; echo "0xff" >"/proc/net/8188eu/$T/rate_ctl"; step "END rate_ctl now: $(tr '\n' ' ' <"/proc/net/8188eu/$T/rate_ctl")"; sleep 3
step "cell before leave: $($IW dev "$T" link 2>&1 | head -1) | stations: $($IW dev "$T" station dump 2>/dev/null | grep -c '^Station')"
run $IW dev "$T" ibss leave
run ip addr flush dev "$T"
run ip link set "$T" down
run $IW dev "$T" set type managed
run ip link set wlan0 up
run systemctl start iwd
sleep 25
if ip -4 addr show 2>/dev/null | grep -q '192\.168\.1\.'; then
    systemctl stop authbc-probe-revert.timer 2>/dev/null
    step "=== reverted OK: back on the home Wi-Fi, deadman disarmed"
else
    step "=== revert: LAN address not back yet, deadman left armed"
fi
kill "$KLOG_PID" "$SYNC_PID" 2>/dev/null
