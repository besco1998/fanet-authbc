#!/bin/bash
# Diagnostic: does wlan0 itself, set to monitor type, receive on the wl18xx? 10 s on channel 1.
O=/home/bbb1/authbc_sniff
systemctl stop iwd; sleep 1
ip link set wlan0 down
/usr/sbin/iw dev wlan0 set type monitor > $O/montest.log 2>&1
/usr/sbin/iw dev wlan0 set monitor fcsfail control otherbss >> $O/montest.log 2>&1
ip link set wlan0 up >> $O/montest.log 2>&1
/usr/sbin/iw dev wlan0 set channel 1 >> $O/montest.log 2>&1
/usr/sbin/iw dev wlan0 info >> $O/montest.log 2>&1
timeout 10 tcpdump -i wlan0 -s 160 -w $O/montest.pcap >> $O/montest.log 2>&1
ip link set wlan0 down; /usr/sbin/iw dev wlan0 set type managed; ip link set wlan0 up
systemctl start iwd
tcpdump -r $O/montest.pcap -tt -e -n 2>/dev/null | head -5 >> $O/montest.log
echo "frames: $(tcpdump -r $O/montest.pcap 2>/dev/null | wc -l)" >> $O/montest.log
