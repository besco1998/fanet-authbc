#!/bin/bash
# Multi-window ad-hoc measurement: a delivery DISTRIBUTION plus an offered-load sweep.
#
# Why not repeated single runs: each mode switch costs ~40 s and one lockout window. Staying in
# the cell and measuring N times inside it gives the same statistics for one switch.
#
# Why a distribution at all: a single delivery number compared against a threshold is exactly
# the failure mode that moved four headline numbers in this project (see the audit pattern in
# CLAUDE.md). Windows are reported individually; nothing here averages them away.
#
# ⚠️ Why 5 GHz by default. The first sweep ran on 2.4 GHz and every offered rate from 100 to
# 1600 fps produced the SAME ~85 fps / 0.96 Mb/s on air — the signature of the 802.11b 1 Mb/s
# basic rate (1400 B = 11.2 ms). Broadcast always uses the lowest basic rate, and on 2.4 GHz
# that is 1 Mb/s. The delivery figures from that run are therefore SATURATION loss, not channel
# loss. On 5 GHz the lowest basic rate is 6 Mb/s, which is also what the NS-3 802.11a model
# assumes — so this is the band that makes hardware and simulation comparable, not a workaround.
#
# ⚠️ Why the interface counters. `sendto` returning success does NOT mean the frame reached the
# air: a full qdisc drops it locally and silently. The first sweep counted those as "sent" and
# so reported local queue overflow as channel loss. tx_packets/tx_dropped are read around every
# window to separate the two.
set -u
ROLE="$1"          # tx | rx
START_EPOCH="$2"   # absolute unix time at which window 0 opens
FREQ="${3:-5180}"  # 5180 = ch 36 (802.11a, non-DFS, no NO-IR under reg domain EG)
MODE="${4:-full}"  # probe = one short window (feasibility) | full = distribution + sweep

OUT=/home/pi/authbc_channel
SSID=authbc-mesh
IP=$([ "$ROLE" = tx ] && echo 10.0.0.1 || echo 10.0.0.2)
PEER=$([ "$ROLE" = tx ] && echo 10.0.0.2 || echo 10.0.0.1)
SIZE=1400          # matches FRAME_BYTES in the model and the NS-3 matrix
log() { echo "[$(date -Is)] $*" >>"$OUT/session.log"; }
ctr() { cat "/sys/class/net/wlan0/statistics/$1" 2>/dev/null || echo 0; }

# window spec: "<rate_fps>:<measure_s>:<slot_s>:<phase>"
if [ "$MODE" = probe ]; then
    WINDOWS=("100:15:20:P")
else
    # phase A -- 8 repeats at the operating point, for the distribution
    # phase B -- offered-load sweep. At 6 Mb/s a 1400 B frame is ~2.1 ms including overhead,
    #            so the knee is predicted near 475 fps; the sweep brackets that.
    WINDOWS=(
      "100:25:30:A" "100:25:30:A" "100:25:30:A" "100:25:30:A"
      "100:25:30:A" "100:25:30:A" "100:25:30:A" "100:25:30:A"
      "50:15:20:B" "100:15:20:B" "200:15:20:B" "300:15:20:B"
      "400:15:20:B" "600:15:20:B" "900:15:20:B"
    )
fi

# ---- 1. Deadmen first ----------------------------------------------------------------------
sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
sudo -n systemd-run --on-active=800 --unit=authbc-revert \
    "$OUT/revert_adhoc.sh" >>"$OUT/session.log" 2>&1
sudo -n systemd-run --on-active=1100 --unit=authbc-reboot \
    /sbin/reboot >>"$OUT/session.log" 2>&1
log "deadmen armed: revert 800 s, reboot 1100 s | role=$ROLE freq=$FREQ mode=$MODE"

# ---- 2. Join the cell ----------------------------------------------------------------------
sudo -n nmcli dev set wlan0 managed no >>"$OUT/session.log" 2>&1
sudo -n systemctl stop wpa_supplicant  >>"$OUT/session.log" 2>&1
sleep 2
sudo -n ip link set wlan0 down
sudo -n /usr/sbin/iw dev wlan0 set type ibss >>"$OUT/session.log" 2>&1
sudo -n ip link set wlan0 up
sleep 2
sudo -n /usr/sbin/iw dev wlan0 ibss join "$SSID" "$FREQ" fixed-freq >>"$OUT/session.log" 2>&1
# ⚠️ No HT20 argument. brcmfmac rejects it with "Invalid argument (-22)" on BOTH bands — a
# single-node probe tried 2412/5180/5200 with and without it and only the HT20 variants failed.
# Dropping it is what makes 5 GHz work; the band was never the limitation.
# ⚠️ A fixed BSSID argument is accepted but IGNORED by brcmfmac: the 2.4 GHz session asked for
# 02:12:34:56:78:9a and the two nodes reported different self-generated BSSIDs -- yet still
# exchanged traffic in both directions. It is omitted rather than left in as a no-op control.
sudo -n ip addr flush dev wlan0
sudo -n ip addr add "$IP/24" dev wlan0 >>"$OUT/session.log" 2>&1
sleep 12

log "type:  $(/usr/sbin/iw dev wlan0 info 2>/dev/null | grep -E 'type|channel' | tr '\n' ' ')"
log "link:  $(/usr/sbin/iw dev wlan0 link 2>/dev/null | head -2 | tr '\n' ' ')"
log "addr:  $(ip -4 -o addr show wlan0 2>/dev/null | grep -oE 'inet [0-9.]+' | tr '\n' ' ')"
if ping -c 3 -W 2 "$PEER" >/dev/null 2>&1; then
    log "PEER $PEER REACHABLE — link formed at $FREQ MHz"
else
    log "PEER $PEER UNREACHABLE at $FREQ MHz — link did NOT form; reverting early"
    sudo -n "$OUT/revert_adhoc.sh"
    sleep 5
    ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.' && \
        sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
    log "early revert complete"
    exit 1
fi

# ---- 3. Run the windows on the shared clock ------------------------------------------------
k=0; offset=0
for spec in "${WINDOWS[@]}"; do
    IFS=: read -r rate measure slot phase <<<"$spec"
    open=$((START_EPOCH + offset))
    wait_s=$((open - $(date +%s)))
    [ $wait_s -gt 0 ] && sleep $wait_s

    tag=$(printf "%02d_%s_%sfps" "$k" "$phase" "$rate")
    tp0=$(ctr tx_packets); td0=$(ctr tx_dropped); rp0=$(ctr rx_packets)
    if [ "$ROLE" = rx ]; then
        python3 "$OUT/bcast_rx.py" --seconds "$measure" --out "$OUT/rx_$tag.json" \
            >>"$OUT/session.log" 2>&1
    else
        sleep 1     # let the receiver bind first
        python3 "$OUT/bcast_tx.py" --rate "$rate" --bytes "$SIZE" \
            --seconds "$((measure - 3))" --out "$OUT/tx_$tag.json" >>"$OUT/session.log" 2>&1
    fi
    echo "{\"tag\":\"$tag\",\"tx_packets\":$(( $(ctr tx_packets) - tp0 ))," \
         "\"tx_dropped\":$(( $(ctr tx_dropped) - td0 ))," \
         "\"rx_packets\":$(( $(ctr rx_packets) - rp0 ))}" >"$OUT/ctr_${ROLE}_$tag.json"
    log "window $tag done"
    k=$((k + 1)); offset=$((offset + slot))
done

/usr/sbin/iw dev wlan0 station dump >"$OUT/station_dump.txt" 2>&1
/usr/sbin/iw dev wlan0 link        >"$OUT/link_final.txt"   2>&1

# ---- 4. Revert -----------------------------------------------------------------------------
sudo -n "$OUT/revert_adhoc.sh"
sleep 5
if ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.'; then
    sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
    log "reverted OK, both deadmen disarmed"
else
    log "revert did NOT restore the LAN address — leaving both deadmen armed"
fi
