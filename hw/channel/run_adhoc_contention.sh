#!/bin/bash
# Contention on real radios: every node of an ad-hoc cell SENDS and RECEIVES in the same windows.
#
# Derived from run_adhoc_sweep.sh, which is the proven path (deadmen, raw `iw`, 5 GHz, interface
# counters) and whose comments explain each of those choices. What differs here, and only this:
#   * a node is a number, not a role: node k has address 10.0.0.k and does both jobs;
#   * the sender draws each send instant within its period (`bcast_tx.py --redraw`), because
#     strictly periodic senders on drifting clocks hold one phase configuration for a whole
#     window (docs/CONTENTION_HW_EXPECTATIONS.md);
#   * the receiver counts each sender separately and leaves its own broadcasts out.
#
# ⚠️ SSH arrives over wlan0. Joining the cell drops it; the script runs unattended under nohup,
# reverts itself, and sits behind the same two deadmen as the sweep.
#
#   run_adhoc_contention.sh <node> <nodes> <start-epoch> <rates> [freq] [mode]
#     node         1..nodes, this board
#     nodes        how many boards are in the cell
#     start-epoch  unix time at which window 0 opens, the same on every board
#     rates        frames per second per node, comma separated, e.g. 125,175,213
#     freq         5180 by default (channel 36)
#     mode         full (four windows per rate) | probe (one short window at the first rate)
set -u
NODE="$1"
NODES="$2"
START_EPOCH="$3"
RATES="$4"
FREQ="${5:-5180}"
MODE="${6:-full}"

OUT=/home/pi/authbc_channel
SSID=authbc-mesh
IP="10.0.0.$NODE"
SIZE=1400          # the frame of the two-radio airtime measurement
log() { echo "[$(date -Is)] $*" >>"$OUT/session.log"; }
ctr() { cat "/sys/class/net/wlan0/statistics/$1" 2>/dev/null || echo 0; }

# window spec: "<rate_fps>:<measure_s>:<slot_s>:<label>"
WINDOWS=()
IFS=, read -r -a RATE_LIST <<<"$RATES"
if [ "$MODE" = probe ]; then
    WINDOWS=("${RATE_LIST[0]}:15:20:P")
else
    for rate in "${RATE_LIST[@]}"; do
        for _ in 1 2 3 4; do WINDOWS+=("$rate:25:30:C"); done
    done
fi

# ---- 1. Deadmen first ----------------------------------------------------------------------
sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
sudo -n systemd-run --on-active=800 --unit=authbc-revert \
    "$OUT/revert_adhoc.sh" >>"$OUT/session.log" 2>&1
sudo -n systemd-run --on-active=1100 --unit=authbc-reboot \
    /sbin/reboot >>"$OUT/session.log" 2>&1
log "deadmen armed: revert 800 s, reboot 1100 s | node=$NODE/$NODES freq=$FREQ mode=$MODE rates=$RATES"

# ---- 2. Join the cell (as run_adhoc_sweep.sh) ----------------------------------------------
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
log "addr:  $(ip -4 -o addr show wlan0 2>/dev/null | grep -oE 'inet [0-9.]+' | tr '\n' ' ')"
missing=0
for k in $(seq 1 "$NODES"); do
    [ "$k" = "$NODE" ] && continue
    if ping -c 3 -W 2 "10.0.0.$k" >/dev/null 2>&1; then
        log "peer 10.0.0.$k reachable"
    else
        log "peer 10.0.0.$k UNREACHABLE"
        missing=1
    fi
done
if [ "$missing" = 1 ]; then
    log "the cell did not form with every node at $FREQ MHz; reverting early"
    sudo -n "$OUT/revert_adhoc.sh"
    sleep 5
    ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.' && \
        sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
    log "early revert complete"
    exit 1
fi

# ---- 3. Run the windows on the shared clock: receive throughout, send inside ---------------
k=0; offset=0
for spec in "${WINDOWS[@]}"; do
    IFS=: read -r rate measure slot label <<<"$spec"
    open=$((START_EPOCH + offset))
    wait_s=$((open - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s

    tag=$(printf "%02d_%s_%sfps" "$k" "$label" "$rate")
    tp0=$(ctr tx_packets); td0=$(ctr tx_dropped); rp0=$(ctr rx_packets)
    python3 "$OUT/bcast_rx.py" --seconds "$measure" --self "$IP" \
        --out "$OUT/rx_node${NODE}_$tag.json" >>"$OUT/session.log" 2>&1 &
    rx_pid=$!
    sleep 1         # every receiver is bound before any sender starts
    python3 "$OUT/bcast_tx.py" --rate "$rate" --bytes "$SIZE" --redraw \
        --seed "$((NODE * 1000 + k))" --seconds "$((measure - 3))" \
        --out "$OUT/tx_node${NODE}_$tag.json" >>"$OUT/session.log" 2>&1
    wait "$rx_pid"
    echo "{\"tag\":\"$tag\",\"node\":$NODE,\"tx_packets\":$(( $(ctr tx_packets) - tp0 ))," \
         "\"tx_dropped\":$(( $(ctr tx_dropped) - td0 ))," \
         "\"rx_packets\":$(( $(ctr rx_packets) - rp0 ))}" >"$OUT/ctr_node${NODE}_$tag.json"
    log "window $tag done"
    k=$((k + 1)); offset=$((offset + slot))
done

/usr/sbin/iw dev wlan0 station dump >"$OUT/station_dump_node$NODE.txt" 2>&1

# ---- 4. Revert -----------------------------------------------------------------------------
sudo -n "$OUT/revert_adhoc.sh"
sleep 5
if ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.'; then
    sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
    log "reverted OK, both deadmen disarmed"
else
    log "revert did NOT restore the LAN address — leaving both deadmen armed"
fi
