#!/bin/bash
# W1g (predictions/W1g.md): hold a Pi's transmit power at a fixed value through a session's windows,
# then return it to automatic. run_window_plan.sh is unchanged; this runs beside it on the same Pi.
#
# Set 50 s before the first window: run_window_plan.sh has joined the cell by then (it joins at
# launch, about 110 s before), and brcmfmac applies set_tx_power only to an interface that is up
# (brcmf_cfg80211_set_tx_power -> check_vif_up; it writes the firmware's qtxpower with the override
# flag). Returned to auto 5 s after the last window ends. Each step is logged with the read-back.
#
#   set_txpower_window.sh <start-epoch> <plan-file> <mBm> <log-file>
set -u
START="$1"
PLAN="$2"
MBM="$3"
LOG="$4"
IW=/usr/sbin/iw
SLOT=30
W=$(grep -cvE '^\s*(#|$)' "$PLAN")
log() { echo "$(date -Is) $*" >>"$LOG"; }
power() { $IW dev wlan0 info 2>/dev/null | grep txpower | tr -s ' \t' ' ' | sed 's/^ //'; }

s=$((START - 50 - $(date +%s)))
[ $s -gt 0 ] && sleep $s
sudo -n $IW dev wlan0 set txpower fixed "$MBM"
log "set $MBM: $(power)"
s=$((START + W * SLOT + 5 - $(date +%s)))
[ $s -gt 0 ] && sleep $s
sudo -n $IW dev wlan0 set txpower auto
log "auto: $(power)"
