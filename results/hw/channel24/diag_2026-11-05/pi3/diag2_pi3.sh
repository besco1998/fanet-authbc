#!/bin/bash
# Diagnostic (disclosed, outside W1d): what sets the Pi 3's ~4-5 ms cycle at 1 Mb/s?
# CPU is ruled out (diag 1: 99 % idle, sender blocked downstream of the socket). A/B on the Pi 3
# alone in the cell on channel 11, 600 /s offered, 145 B, 15 s per run:
#   A0 as S0 (power save as found, Bluetooth up) | P power save off | PB power save off + BT blocked
#   A1 as S0 again (drift check)
O="$(dirname "$(readlink -f "$0")")"
IW=/usr/sbin/iw; RF=/usr/sbin/rfkill
cat >"$O/diag2_revert.sh" <<EOF
#!/bin/bash
$RF unblock bluetooth
$O/revert_adhoc.sh
EOF
chmod +x "$O/diag2_revert.sh"
sudo -n systemd-run --on-active=240 --unit=authbc-diag2-revert "$O/diag2_revert.sh" >/dev/null 2>&1
L="$O/diag2.log"; : >"$L"
sudo -n nmcli dev set wlan0 managed no; sleep 1
sudo -n ip link set wlan0 down; sudo -n $IW dev wlan0 set type ibss; sudo -n ip link set wlan0 up; sleep 2
sudo -n $IW dev wlan0 ibss join authbc-mesh 2462 fixed-freq
sudo -n ip addr flush dev wlan0; sudo -n ip addr add 10.0.0.3/24 dev wlan0; sleep 8
GOV0=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
echo performance | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
echo "in cell: $($IW dev wlan0 info | grep -E 'type|channel' | tr '\n' ' ') ps=$($IW dev wlan0 get power_save)" >>"$L"
run() {  # $1 label
    tp0=$(cat /sys/class/net/wlan0/statistics/tx_packets)
    python3 "$O/bcast_tx.py" --rate 600 --bytes 145 --redraw --seconds 15 --out "$O/diag2_$1.json"
    echo "$1 ps=$($IW dev wlan0 get power_save | cut -d: -f2) bt=$($RF list bluetooth | grep -c 'Soft blocked: yes') nic=$(( $(cat /sys/class/net/wlan0/statistics/tx_packets) - tp0 )) $(cat "$O/diag2_$1.json")" >>"$L"
    sleep 2
}
run A0
sudo -n $IW dev wlan0 set power_save off; sleep 1; run P
sudo -n $RF block bluetooth; sleep 2; run PB
sudo -n $RF unblock bluetooth; sudo -n $IW dev wlan0 set power_save on; sleep 3; run A1
echo "$GOV0" | sudo -n tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null
sudo -n "$O/revert_adhoc.sh"; sleep 5
ip -4 addr show wlan0 | grep -q '192\.168\.1\.' && sudo -n systemctl stop authbc-diag2-revert.timer
echo "bt after: $($RF list bluetooth | grep 'Soft blocked')" >>"$L"
echo done >"$O/diag2_done"
