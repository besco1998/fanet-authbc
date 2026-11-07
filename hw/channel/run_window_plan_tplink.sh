#!/bin/bash
# Node 4 of W1f (predictions/W1f.md): the TP-Link TL-WN722N (RTL8188EUS) on BeagleBone Blue 2, in
# the Pis' ad-hoc cell, on the same plan and the same shared clock as run_window_plan.sh.
#
# Probe 3's script (results/hw/channel24/probe4c_2026-11-05/node4/blue_probe_iw.sh), whose join,
# windows and revert are kept as they ran there (F125, F126), plus the safeguards W1f registers:
#   * every window's files are synced to the card before the next window, and before the exit
#     (probe 3 lost its last window's files to a reset after its revert, F126);
#   * every window's ctr file records the boot ID before and after, the BSSID and rate_ctl, so a
#     reset, a cell of its own or a rate that is no longer fixed makes that window unusable;
#   * at join: the BSSID (02:11:87:... is the driver's own cell, core/rtw_mlme.c l. 518), rate_ctl
#     and which of the Pis answered, in meta_node4_join.json.
# The driver: aircrack-ng/rtl8188eus af3bf004, adapter named tplink0 (F125). Start Blue 2 from a
# fresh boot so that the driver's scan list is empty and it JOINS the Pis' cell (rtw_do_join,
# core/rtw_ioctl_set.c l. 99-151), and join after the Pis have formed it: 40 s before the first
# window. The Blue's own radio is off the air during the session; a deadman brings it back.
#
# Run as root:  systemd-run --collect --unit=authbc-w1f <this> <start-epoch> <plan-file>
#               <this> revert          (what the deadman calls)
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/session.log"
IW=/usr/sbin/iw
NODE=4
IP="10.0.0.$NODE"
MEASURE=25
SLOT=30
TPLINK_MAC=d0:37:45:2b:23:b0
log() { echo "[$(date -Is)] $*" >>"$L"; }
tplink() {   # the TP-Link's interface, found by its hardware address
    for i in /sys/class/net/*; do
        [ "$(cat "$i/address" 2>/dev/null)" = "$TPLINK_MAC" ] && { basename "$i"; return; }
    done
}
boot_id() { cut -c1-8 /proc/sys/kernel/random/boot_id; }
bssid() { $IW dev "$1" link 2>/dev/null | awk '/Joined IBSS/ {print $3; exit}'; }
ratectl() { tr '\n' ' ' <"/proc/net/8188eu/$1/rate_ctl" 2>/dev/null | sed 's/ *$//'; }

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
        systemctl stop authbc-w1f-revert.timer 2>/dev/null
        log "reverted OK: back on the home Wi-Fi, deadman disarmed"
    else
        log "revert: LAN address not back yet, deadman left armed"
    fi
    sync
}
if [ "${1:-}" = revert ]; then revert; exit 0; fi

START="$1"
PLAN="$2"
PIS=$(grep -m1 '^# nodes:' "$PLAN" | cut -d: -f2 | tr -d ' ')
WINDOWS=$(grep -cvE '^\s*(#|$)' "$PLAN")
SESSION_S=$(( WINDOWS * SLOT + 120 ))
systemctl stop authbc-w1f-revert.timer 2>/dev/null
systemd-run --on-active=$((SESSION_S + 300)) --unit=authbc-w1f-revert "$0" revert >/dev/null 2>&1
T=$(tplink)
log "deadman armed: revert in $((SESSION_S + 300)) s | start=$START windows=$WINDOWS plan sha=$(sha256sum "$PLAN" | cut -c1-12) | tplink=$T driver=$(basename "$(readlink -f "/sys/class/net/$T/device/driver")") boot=$(boot_id) uptime=$(cut -d' ' -f1 /proc/uptime)s"
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
ip addr add "$IP/24" dev "$T" >>"$L" 2>&1
sleep 10
reached=()
for k in ${PIS//,/ }; do
    if ping -c 3 -W 2 "10.0.0.$k" >/dev/null 2>&1; then reached+=("$k"); log "peer 10.0.0.$k reachable"
    else log "peer 10.0.0.$k UNREACHABLE"; fi
done
B0=$(boot_id)
printf '{"bssid":"%s","rate_ctl":"%s","boot":"%s","peers_reachable":[%s]}\n' \
    "$(bssid "$T")" "$(ratectl "$T")" "$B0" "$(IFS=,; echo "${reached[*]}")" >"$O/meta_node4_join.json"
log "after join: $(cat "$O/meta_node4_join.json")"
sync

k=0
while read -r label rate bytes senders; do
    open=$((START + k * SLOT))
    wait_s=$((open - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s
    tag=$(printf "%02d_%s_%sfps" "$k" "$label" "$rate")
    tp0=$(cat "/sys/class/net/$T/statistics/tx_packets"); td0=$(cat "/sys/class/net/$T/statistics/tx_dropped")
    rp0=$(cat "/sys/class/net/$T/statistics/rx_packets"); b0=$(boot_id)
    python3 "$O/bcast_rx.py" --seconds "$MEASURE" --self "$IP" --out "$O/rx_node${NODE}_$tag.json" >>"$L" 2>&1 &
    rx_pid=$!
    sleep 1         # every receiver is bound before any sender starts
    if [[ ",$senders," == *",$NODE,"* ]]; then
        python3 "$O/bcast_tx.py" --rate "$rate" --bytes "$bytes" --redraw --seed "$((NODE * 1000 + k))" \
            --seconds "$((MEASURE - 3))" --out "$O/tx_node${NODE}_$tag.json" >>"$L" 2>&1
    fi
    wait "$rx_pid"
    printf '{"tag":"%s","node":%d,"senders":"%s","bytes":%s,"tx_packets":%d,"tx_dropped":%d,"rx_packets":%d,"boot_before":"%s","boot_after":"%s","bssid":"%s","rate_ctl":"%s"}\n' \
        "$tag" "$NODE" "$senders" "$bytes" \
        $(( $(cat "/sys/class/net/$T/statistics/tx_packets") - tp0 )) \
        $(( $(cat "/sys/class/net/$T/statistics/tx_dropped") - td0 )) \
        $(( $(cat "/sys/class/net/$T/statistics/rx_packets") - rp0 )) \
        "$b0" "$(boot_id)" "$(bssid "$T")" "$(ratectl "$T")" >"$O/ctr_node${NODE}_$tag.json"
    sync
    log "window $tag done (senders $senders)"
    k=$((k + 1))
done < <(grep -vE '^\s*(#|$)' "$PLAN")

log "at end: bssid=$(bssid "$T") rate_ctl=$(ratectl "$T") boot=$(boot_id)"
sync
revert
