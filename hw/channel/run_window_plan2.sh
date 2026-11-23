#!/bin/bash
# One ad-hoc cell, a plan of windows, for the sessions of 2026-11-21 (predictions/W1p.md, W1q.md,
# W1r.md; plans in docs/revision/2026-11-20_session_plans.md, approved by Mohamed 2026-11-21).
#
# Derived from run_window_plan.sh, which is kept as it was: it is the record of how W1d–W1n ran.
# What differs:
#   * frame burst is set OFF on this board after joining, and its value is logged before the first
#     window and after the last (frameburst.sh). A board that does not read 0 voids the session;
#   * each window may have its own length (the fifth plan column, seconds; default 25) and its own
#     transmit-power settings (the sixth: node:mBm or node:auto, comma-separated; each node applies
#     only its own, which then holds until changed);
#   * signal strength: halfway through and after every window, the firmware's RSSI for every peer
#     address and for the zero address (rssi.sh), one JSON line per reading;
#   * every received frame's kernel receive time (bcast_rx.py --timestamps);
#   * before each window, chip_check.sh: a board no longer in the cell, or a sender whose
#     previous window sent nothing, stops its own windows and reverts (2026-11-23);
#   * a per-frame sent log per window (bcast_tx.py --sendlog), and the board's kernel, driver
#     and firmware at the start (the frame-level campaign, 2026-11-23).
#
# ⚠️ SSH arrives over wlan0. Joining the cell drops it; run unattended under nohup/systemd-run.
#
#   run_window_plan2.sh <node> <start-epoch> <plan-file> [freq]
#     plan-file   "# nodes: 1,2,3" then one window per line:
#                 <label> <rate_fps> <bytes> <senders> [<seconds> [<node>:<mBm|auto>,...]]
#                 e.g.  "P6 600 145 1,2 25 1:1000"  — node 1 at 10 dBm, then nodes 1, 2 send
#     freq        2462 by default (2.4 GHz channel 11)
#   DRY=1 run_window_plan2.sh …   prints the schedule (one line per window) and changes nothing
set -u
NODE="$1"
START_EPOCH="$2"
PLAN="$3"
FREQ="${4:-2462}"

OUT="$(dirname "$(readlink -f "$0")")"
SSID=authbc-mesh
IP="10.0.0.$NODE"
GAP=5               # seconds between one window's end and the next one's start
log() { echo "[$(date -Is)] $*" >>"$OUT/session.log"; }
ctr() { cat "/sys/class/net/wlan0/statistics/$1" 2>/dev/null || echo 0; }
thr() { vcgencmd get_throttled 2>/dev/null | cut -d= -f2; }

NODES=$(grep -m1 '^# nodes:' "$PLAN" | cut -d: -f2 | tr -d ' ')
mapfile -t WINDOWS < <(grep -vE '^\s*(#|$)' "$PLAN")

# The schedule: window k opens at START + the sum of (seconds + GAP) over the windows before it.
OPENS=(); SECS=(); POWERS=()
t=0
for spec in "${WINDOWS[@]}"; do
    read -r _label _rate _bytes _senders sec power <<<"$spec"
    sec="${sec:-25}"
    [[ "$sec" =~ ^[0-9]+$ ]] && [ "$sec" -ge 10 ] || { echo "bad seconds '$sec' in: $spec" >&2; exit 2; }
    OPENS+=("$((START_EPOCH + t))"); SECS+=("$sec"); POWERS+=("${power:-}")
    t=$((t + sec + GAP))
done
SESSION_S=$((t + 120))

my_power() {   # the setting this node takes before a window, or nothing
    local entry
    for entry in ${1//,/ }; do
        [ "${entry%%:*}" = "$NODE" ] && { echo "${entry#*:}"; return; }
    done
}

if [ "${DRY:-0}" = 1 ]; then
    for k in "${!WINDOWS[@]}"; do
        read -r label rate bytes senders _ <<<"${WINDOWS[$k]}"
        p=$(my_power "${POWERS[$k]}")
        echo "window $k $label open ${OPENS[$k]} seconds ${SECS[$k]} rate $rate bytes $bytes" \
             "senders $senders power ${p:--}"
    done
    echo "session_s $SESSION_S"
    exit 0
fi

# ---- 1. Deadmen first, sized to the plan ---------------------------------------------------
sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
sudo -n systemd-run --on-active=$((SESSION_S + 300)) --unit=authbc-revert \
    "$OUT/revert_adhoc.sh" >>"$OUT/session.log" 2>&1
sudo -n systemd-run --on-active=$((SESSION_S + 600)) --unit=authbc-reboot \
    /sbin/reboot >>"$OUT/session.log" 2>&1
log "deadmen armed: revert $((SESSION_S + 300)) s, reboot $((SESSION_S + 600)) s | node=$NODE nodes=$NODES freq=$FREQ windows=${#WINDOWS[@]} plan=$(basename "$PLAN") sha=$(sha256sum "$PLAN" | cut -c1-12)"
log "env: kernel $(uname -r) | brcmfmac $(modinfo -F version brcmfmac 2>/dev/null) | firmware $(sudo -n dmesg 2>/dev/null | grep -m1 -oE 'brcmf_c_preinit_dcmds: Firmware: .*' | cut -c1-120)"

# ---- 2. Governor, then join the cell (as run_window_plan.sh) -------------------------------
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
PEER_IPS=(); PEER_MACS=()
for k in ${NODES//,/ }; do
    [ "$k" = "$NODE" ] && continue
    if ping -c 3 -W 2 "10.0.0.$k" >/dev/null 2>&1; then
        mac=$(ip neigh show "10.0.0.$k" dev wlan0 2>/dev/null | grep -oE 'lladdr [0-9a-f:]{17}' | cut -d' ' -f2)
        log "peer 10.0.0.$k reachable, mac ${mac:-unknown}"
        PEER_IPS+=("10.0.0.$k"); PEER_MACS+=("${mac:-}")
    else log "peer 10.0.0.$k UNREACHABLE"; missing=1; fi
done

# Frame burst OFF (frameburst.sh says what it is and why it matters). Read back and logged.
sudo -n "$OUT/frameburst.sh" set 0 >/dev/null 2>&1
log "frameburst before the windows: $(sudo -n "$OUT/frameburst.sh" get 2>&1) (asked: 0)"

restore() {
    sudo -n /usr/sbin/iw dev wlan0 set txpower auto >/dev/null 2>&1
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

rssi_line() {   # $1 tag, $2 when: one JSON line with the zero-address and every peer's reading
    local peers="" i v
    for i in "${!PEER_IPS[@]}"; do
        v=$( [ -n "${PEER_MACS[$i]}" ] && sudo -n "$OUT/rssi.sh" "${PEER_MACS[$i]}" 2>&1 || echo "error: no mac")
        peers+="\"${PEER_IPS[$i]}\":{\"mac\":\"${PEER_MACS[$i]}\",\"rssi\":\"$v\"},"
    done
    echo "{\"tag\":\"$1\",\"when\":\"$2\",\"t\":\"$(date +%s.%N)\",\"node\":$NODE," \
         "\"any\":\"$(sudo -n "$OUT/rssi.sh" any 2>&1)\",\"peers\":{${peers%,}}}" \
         >>"$OUT/rssi_node${NODE}.jsonl"
}

# ---- 3. The windows, on the shared clock: every node receives, the named nodes send --------
# Before each window chip_check.sh asks whether this board is still in the cell and, if it sent in
# the previous window, whether frames left it. If not, this board runs no more windows and goes
# straight to the revert (Mohamed, 2026-11-23); the other boards carry on.
PREV_SENT=-
for k in "${!WINDOWS[@]}"; do
    read -r label rate bytes senders _ <<<"${WINDOWS[$k]}"
    sec="${SECS[$k]}"
    if ! why=$("$OUT/chip_check.sh" "$FREQ" "$PREV_SENT"); then
        log "chip down before window $k: $why; this board runs no more windows"
        break
    fi
    want=$(my_power "${POWERS[$k]}")
    if [ -n "$want" ]; then
        if [ "$want" = auto ]; then sudo -n /usr/sbin/iw dev wlan0 set txpower auto
        else sudo -n /usr/sbin/iw dev wlan0 set txpower fixed "$want"; fi
        log "txpower asked $want: $(/usr/sbin/iw dev wlan0 info 2>/dev/null | grep txpower | tr -s ' \t' ' ')"
    fi
    wait_s=$((OPENS[k] - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s
    tag=$(printf "%02d_%s_%sfps" "$k" "$label" "$rate")
    tp0=$(ctr tx_packets); td0=$(ctr tx_dropped); rp0=$(ctr rx_packets); th0=$(thr)
    python3 "$OUT/bcast_rx.py" --seconds "$sec" --self "$IP" \
        --out "$OUT/rx_node${NODE}_$tag.json" \
        --timestamps "$OUT/rxts_node${NODE}_$tag.csv" >>"$OUT/session.log" 2>&1 &
    rx_pid=$!
    ( sleep $((sec / 2)); rssi_line "$tag" mid ) &
    mid_pid=$!
    sleep 1         # every receiver is bound before any sender starts
    if [[ ",$senders," == *",$NODE,"* ]]; then
        python3 "$OUT/bcast_tx.py" --rate "$rate" --bytes "$bytes" --redraw \
            --seed "$((NODE * 1000 + k))" --seconds "$((sec - 3))" \
            --out "$OUT/tx_node${NODE}_$tag.json" \
            --sendlog "$OUT/txlog_node${NODE}_$tag.csv" >>"$OUT/session.log" 2>&1
    fi
    wait "$rx_pid"
    wait "$mid_pid"
    rssi_line "$tag" after
    echo "{\"tag\":\"$tag\",\"node\":$NODE,\"senders\":\"$senders\",\"bytes\":$bytes,\"seconds\":$sec," \
         "\"tx_packets\":$(( $(ctr tx_packets) - tp0 )),\"tx_dropped\":$(( $(ctr tx_dropped) - td0 ))," \
         "\"rx_packets\":$(( $(ctr rx_packets) - rp0 )),\"throttled_before\":\"$th0\"," \
         "\"throttled_after\":\"$(thr)\"}" >"$OUT/ctr_node${NODE}_$tag.json"
    log "window $tag done (senders $senders, $sec s)"
    if [[ ",$senders," == *",$NODE,"* ]]; then PREV_SENT=$(( $(ctr tx_packets) - tp0 )); else PREV_SENT=-; fi
done

log "frameburst after the windows: $(sudo -n "$OUT/frameburst.sh" get 2>&1)"

# ---- 4. Revert ------------------------------------------------------------------------------
restore
