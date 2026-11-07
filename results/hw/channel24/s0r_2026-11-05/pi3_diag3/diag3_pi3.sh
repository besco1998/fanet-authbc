#!/bin/bash
# Diagnostic (disclosed, outside W1d): does the Pi 3's sending rate decay with continuous sending
# (thermal or duty-cycle limiter)? Started after >= 9 min idle. Pi 3 alone in the cell, ch 11,
# 600 /s offered, 145 B; eight runs of 10 s with 1 s between; SoC temperature logged per run.
O="$(dirname "$(readlink -f "$0")")"; IW=/usr/sbin/iw
sudo -n systemd-run --on-active=240 --unit=authbc-diag3-revert "$O/revert_adhoc.sh" >/dev/null 2>&1
L="$O/diag3.log"; : >"$L"
sudo -n nmcli dev set wlan0 managed no; sleep 1
sudo -n ip link set wlan0 down; sudo -n $IW dev wlan0 set type ibss; sudo -n ip link set wlan0 up; sleep 2
sudo -n $IW dev wlan0 ibss join authbc-mesh 2462 fixed-freq
sudo -n ip addr flush dev wlan0; sudo -n ip addr add 10.0.0.3/24 dev wlan0; sleep 8
GOV0=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
echo performance | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
echo "start $(date -Is) $(vcgencmd measure_temp) $(vcgencmd get_throttled)" >>"$L"
for k in 1 2 3 4 5 6 7 8; do
    python3 "$O/bcast_tx.py" --rate 600 --bytes 145 --redraw --seconds 10 --out "$O/diag3_$k.json"
    echo "run$k $(date +%T) $(vcgencmd measure_temp) $(cat "$O/diag3_$k.json")" >>"$L"
    sleep 1
done
echo "end $(vcgencmd get_throttled)" >>"$L"
echo "$GOV0" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
sudo -n "$O/revert_adhoc.sh"; sleep 5
ip -4 addr show wlan0 | grep -q '192\.168\.1\.' && sudo -n systemctl stop authbc-diag3-revert.timer
echo done >"$O/diag3_done"
