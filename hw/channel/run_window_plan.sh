#!/bin/bash
# One ad-hoc cell, a plan of windows: each window names its rate, payload and sending nodes.
#
# predictions/W1d.md (the 3-radio campaign at 2.4 GHz). Derived from run_adhoc_contention.sh, the
# path F73-F76 ran on (deadmen, raw `iw`, receivers bound before senders, self-revert); that
# script is kept as it was, because it is the record of how those sessions ran. What differs:
#   * the windows come from a plan file shared by every node: a window may have one sender (rate
#     check, control) or a subset of the cell (a pair inside a cell of three);
#   * the payload is per window (the 145 B AUTHBC frame of W1c/W1d, not F73's 1400 B);
#   * `vcgencmd get_throttled` is recorded before and after every window: a window in which a
#     board lost voltage is not usable (pi-A browned out on 2026-11-05 before its new supply);
#   * the CPU governor is `performance` for the session and restored after;
#   * the deadmen are sized to the plan, and paths follow wherever the kit was deployed.
#
# ⚠️ SSH arrives over wlan0. Joining the cell drops it; run unattended under nohup/systemd-run.
#
#   run_window_plan.sh <node> <start-epoch> <plan-file> [freq]
#     plan-file   "# nodes: 1,2,3" then one window per line: <label> <rate_fps> <bytes> <senders>
#                 e.g.  "C 131 145 1,2" — nodes 1 and 2 send 145 B at 131 frames/s each
#     freq        2462 by default (2.4 GHz channel 11)
set -u
NODE="$1"
START_EPOCH="$2"
PLAN="$3"
FREQ="${4:-2462}"

OUT="$(dirname "$(readlink -f "$0")")"
SSID=authbc-mesh
IP="10.0.0.$NODE"
MEASURE=25          # seconds a receiver listens in a window
SLOT=30             # seconds between window starts; senders send for MEASURE - 3
log() { echo "[$(date -Is)] $*" >>"$OUT/session.log"; }
ctr() { cat "/sys/class/net/wlan0/statistics/$1" 2>/dev/null || echo 0; }
thr() { vcgencmd get_throttled 2>/dev/null | cut -d= -f2; }

NODES=$(grep -m1 '^# nodes:' "$PLAN" | cut -d: -f2 | tr -d ' ')
mapfile -t WINDOWS < <(grep -vE '^\s*(#|$)' "$PLAN")
SESSION_S=$(( ${#WINDOWS[@]} * SLOT + 120 ))

# ---- 1. Deadmen first, sized to the plan ---------------------------------------------------
sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
sudo -n systemd-run --on-active=$((SESSION_S + 300)) --unit=authbc-revert \
    "$OUT/revert_adhoc.sh" >>"$OUT/session.log" 2>&1
sudo -n systemd-run --on-active=$((SESSION_S + 600)) --unit=authbc-reboot \
    /sbin/reboot >>"$OUT/session.log" 2>&1
log "deadmen armed: revert $((SESSION_S + 300)) s, reboot $((SESSION_S + 600)) s | node=$NODE nodes=$NODES freq=$FREQ windows=${#WINDOWS[@]} plan=$(basename "$PLAN") sha=$(sha256sum "$PLAN" | cut -c1-12)"

# ---- 2. Governor, then join the cell (as run_adhoc_contention.sh) --------------------------
GOV0=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)
echo performance | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
log "governor: $GOV0 -> $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor); throttled $(thr)"
sudo -n nmcli dev set wlan0 managed no >>"$OUT/session.log" 2>&1
sudo -n systemctl stop wpa_supplicant  >>"$OUT/session.log" 2>&1
sleep 2
sudo -n ip link set wlan0 down
sudo -n /usr/sbin/iw dev wlan0 set type ibss >>"$OUT/session.log" 2>&1
sudo -n ip link set wlan0 up
sleep 2
sudo -n /usr/sbin/iw dev wlan0 ibss join "$SSID" "$FREQ" fixed-freq >>"$OUT/session.log" 2>&1
sudo -n ip addr flush dev wlan0
sudo -n ip addr add "$IP/24" dev wlan0 >>"$OUT/session.log" 2>&1
sleep 12
log "type:  $(/usr/sbin/iw dev wlan0 info 2>/dev/null | grep -E 'type|channel' | tr '\n' ' ')"
missing=0
for k in ${NODES//,/ }; do
    [ "$k" = "$NODE" ] && continue
    if ping -c 3 -W 2 "10.0.0.$k" >/dev/null 2>&1; then log "peer 10.0.0.$k reachable"
    else log "peer 10.0.0.$k UNREACHABLE"; missing=1; fi
done

restore() {
    echo "$GOV0" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
    sudo -n "$OUT/revert_adhoc.sh"
    sleep 5
    if ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.'; then
        sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
        log "reverted OK, both deadmen disarmed"
    else
        log "revert did NOT restore the LAN address — leaving both deadmen armed"
    fi
}
if [ "$missing" = 1 ]; then
    log "the cell did not form with every node at $FREQ MHz; reverting early"
    restore
    exit 1
fi

# ---- 3. The windows, on the shared clock: every node receives, the named nodes send --------
k=0
for spec in "${WINDOWS[@]}"; do
    read -r label rate bytes senders <<<"$spec"
    open=$((START_EPOCH + k * SLOT))
    wait_s=$((open - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s
    tag=$(printf "%02d_%s_%sfps" "$k" "$label" "$rate")
    tp0=$(ctr tx_packets); td0=$(ctr tx_dropped); rp0=$(ctr rx_packets); th0=$(thr)
    python3 "$OUT/bcast_rx.py" --seconds "$MEASURE" --self "$IP" \
        --out "$OUT/rx_node${NODE}_$tag.json" >>"$OUT/session.log" 2>&1 &
    rx_pid=$!
    sleep 1         # every receiver is bound before any sender starts
    if [[ ",$senders," == *",$NODE,"* ]]; then
        python3 "$OUT/bcast_tx.py" --rate "$rate" --bytes "$bytes" --redraw \
            --seed "$((NODE * 1000 + k))" --seconds "$((MEASURE - 3))" \
            --out "$OUT/tx_node${NODE}_$tag.json" >>"$OUT/session.log" 2>&1
    fi
    wait "$rx_pid"
    echo "{\"tag\":\"$tag\",\"node\":$NODE,\"senders\":\"$senders\",\"bytes\":$bytes," \
         "\"tx_packets\":$(( $(ctr tx_packets) - tp0 )),\"tx_dropped\":$(( $(ctr tx_dropped) - td0 ))," \
         "\"rx_packets\":$(( $(ctr rx_packets) - rp0 )),\"throttled_before\":\"$th0\"," \
         "\"throttled_after\":\"$(thr)\"}" >"$OUT/ctr_node${NODE}_$tag.json"
    log "window $tag done (senders $senders)"
    k=$((k + 1))
done

# ---- 4. Revert ------------------------------------------------------------------------------
restore
