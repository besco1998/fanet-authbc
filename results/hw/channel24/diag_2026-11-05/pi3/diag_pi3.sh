#!/bin/bash
# Diagnostic (disclosed, outside W1d): is the Pi 3's ~212 frames/s ceiling the host or the radio?
O="$(dirname "$(readlink -f "$0")")"
sudo -n systemd-run --on-active=180 --unit=authbc-diag-revert "$O/revert_adhoc.sh" >/dev/null 2>&1
sudo -n nmcli dev set wlan0 managed no; sleep 1
sudo -n ip link set wlan0 down; sudo -n /usr/sbin/iw dev wlan0 set type ibss; sudo -n ip link set wlan0 up; sleep 2
sudo -n /usr/sbin/iw dev wlan0 ibss join authbc-mesh 2462 fixed-freq
sudo -n ip addr flush dev wlan0; sudo -n ip addr add 10.0.0.3/24 dev wlan0; sleep 8
GOV0=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
echo performance | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
tp0=$(cat /sys/class/net/wlan0/statistics/tx_packets)
vmstat 1 16 > "$O/diag_vmstat.txt" &
python3 "$O/bcast_tx.py" --rate 600 --bytes 145 --redraw --seconds 15 --out "$O/diag_tx.json" & PID=$!
sleep 7; top -b -n1 -p $PID > "$O/diag_top.txt"
wait $PID; wait
echo "nic tx_packets: $(( $(cat /sys/class/net/wlan0/statistics/tx_packets) - tp0 ))" > "$O/diag_nic.txt"
echo "$GOV0" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
sudo -n "$O/revert_adhoc.sh"; sleep 5
ip -4 addr show wlan0 | grep -q '192\.168\.1\.' && sudo -n systemctl stop authbc-diag-revert.timer
echo done > "$O/diag_done"
