#!/bin/bash
# Self-contained 802.11 ad-hoc measurement session, driven by raw `iw`.
#
# ⚠️ SSH arrives over wlan0 and eth0 has no carrier, so switching to ad-hoc DROPS the only
# control path. Everything here runs unattended under nohup, reverts itself, and sits behind
# two independent deadmen.
#
# **Why raw `iw` and not nmcli.** NetworkManager insists on attaching a security layer to an
# ad-hoc cell, and both earlier attempts died on it:
#   attempt 1 — no security specified  -> "802.1X supplicant took too long to authenticate"
#   attempt 2 — `key-mgmt none` added  -> "Secrets were required, but not provided"
# because in NM `key-mgmt none` means *static WEP*, not "open". Taking wlan0 out of NM's hands
# removes the entire class rather than guessing at another property.
set -u
ROLE="$1"                       # tx | rx
SECONDS_RUN="${2:-60}"
RATE="${3:-100}"
SIZE="${4:-1400}"

OUT=/home/pi/authbc_channel
SSID=authbc-mesh
FREQ=2412                       # channel 1; verified not NO-IR under reg domain EG
BSSID=02:12:34:56:78:9a         # locally-administered (bit 1 of the first octet)
IP=$([ "$ROLE" = tx ] && echo 10.0.0.1 || echo 10.0.0.2)
PEER=$([ "$ROLE" = tx ] && echo 10.0.0.2 || echo 10.0.0.1)
log() { echo "[$(date -Is)] $*" >>"$OUT/session.log"; }

# ⚠️ The fixed BSSID is not cosmetic. Two nodes that each generate a random BSSID form two
# separate cells on the same SSID and never see one another — a classic silent IBSS failure
# that looks exactly like "the radio doesn't work".

# ---- 1. Two deadmen, armed BEFORE anything touches the radio -------------------------------
# 600 s: full revert. 900 s: reboot — the guaranteed path, because NetworkManager is enabled at
# boot and `preconfigured` has autoconnect=yes (both verified before this was first run).
sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
sudo -n systemd-run --on-active=600 --unit=authbc-revert \
    "$OUT/revert_adhoc.sh" >>"$OUT/session.log" 2>&1
sudo -n systemd-run --on-active=900 --unit=authbc-reboot \
    /sbin/reboot >>"$OUT/session.log" 2>&1
log "deadmen armed: revert 600 s, reboot 900 s | role=$ROLE ip=$IP"

# ---- 2. Take wlan0 away from NM and wpa_supplicant, then join the cell by hand --------------
sudo -n nmcli dev set wlan0 managed no >>"$OUT/session.log" 2>&1
sudo -n systemctl stop wpa_supplicant  >>"$OUT/session.log" 2>&1
sleep 2
sudo -n ip link set wlan0 down
sudo -n /usr/sbin/iw dev wlan0 set type ibss >>"$OUT/session.log" 2>&1
sudo -n ip link set wlan0 up
sleep 2
sudo -n /usr/sbin/iw dev wlan0 ibss join "$SSID" "$FREQ" fixed-freq "$BSSID" \
    >>"$OUT/session.log" 2>&1
sudo -n ip addr add "$IP/24" dev wlan0 >>"$OUT/session.log" 2>&1

# Pin the broadcast PHY rate. 802.11 sends broadcast at a *basic rate* chosen by the driver;
# left unset, the airtime per frame is unknown and the offered load is uninterpretable — at a
# 1 Mb/s basic rate a 1400 B frame occupies 11.2 ms, so 100 fps would saturate the medium and
# the resulting loss would be over-subscription masquerading as channel loss. 6 Mb/s is also
# exactly what the NS-3 802.11a model uses, so the measurement stays comparable to the sim.
if sudo -n /usr/sbin/iw dev wlan0 set mcast_rate 6 >>"$OUT/session.log" 2>&1; then
    log "mcast_rate = 6 Mb/s (airtime ~2.1 ms/frame at 1400 B)"
else
    log "⚠️ mcast_rate NOT set — airtime per frame is driver-chosen, load is uninterpretable"
fi
sleep 12

# ---- 3. Prove the link BEFORE measuring ----------------------------------------------------
# A delivery number taken from a link that never formed is worse than no number: the first two
# attempts produced exactly that (rx.json said 0 received, which reads like 100 % loss).
log "type:  $(/usr/sbin/iw dev wlan0 info 2>/dev/null | grep -E 'type|channel' | tr '\n' ' ')"
log "link:  $(/usr/sbin/iw dev wlan0 link 2>/dev/null | head -2 | tr '\n' ' ')"
log "addr:  $(ip -4 -o addr show wlan0 2>/dev/null | grep -oE 'inet [0-9.]+')"
log "peers: $(/usr/sbin/iw dev wlan0 station dump 2>/dev/null | grep -c Station)"
if ping -c 3 -W 2 "$PEER" >/dev/null 2>&1; then
    log "PEER $PEER REACHABLE — link formed"
else
    log "PEER $PEER UNREACHABLE — link did NOT form (measurement below is not valid)"
fi

# ---- 4. Measure ----------------------------------------------------------------------------
if [ "$ROLE" = rx ]; then
    python3 "$OUT/bcast_rx.py" --seconds "$SECONDS_RUN" --out "$OUT/rx.json" \
        >>"$OUT/session.log" 2>&1
else
    sleep 5     # let the receiver bind first
    python3 "$OUT/bcast_tx.py" --rate "$RATE" --bytes "$SIZE" \
        --seconds "$((SECONDS_RUN - 10))" --out "$OUT/tx.json" >>"$OUT/session.log" 2>&1
fi
log "measurement done"

# Station dump AFTER the traffic: signal strength and the peer's counters only populate once
# frames have actually been exchanged.
/usr/sbin/iw dev wlan0 station dump >"$OUT/station_dump.txt" 2>&1

# ---- 5. Revert, and disarm only after the LAN address is confirmed back --------------------
sudo -n "$OUT/revert_adhoc.sh"
sleep 5
if ip -4 addr show wlan0 2>/dev/null | grep -q '192\.168\.1\.'; then
    sudo -n systemctl stop authbc-revert.timer authbc-reboot.timer 2>/dev/null
    log "reverted OK, both deadmen disarmed"
else
    log "revert did NOT restore the LAN address — leaving both deadmen armed"
fi
