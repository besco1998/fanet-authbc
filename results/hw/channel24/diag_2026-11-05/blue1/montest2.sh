#!/bin/bash
# Diagnostic: does a monitor interface receive on the wl18xx while wlan0 stays connected (ch 1)?
O=/home/bbb1/authbc_sniff; L=$O/montest2.log; IW=/usr/sbin/iw
: >$L
$IW phy phy0 interface add mon0 type monitor >>$L 2>&1
$IW dev mon0 set monitor fcsfail control otherbss >>$L 2>&1
ip link set mon0 up >>$L 2>&1
$IW dev mon0 info >>$L 2>&1
timeout 10 tcpdump -i mon0 -s 160 -w $O/montest2.pcap >>$L 2>&1
ip link set mon0 down; $IW dev mon0 del >>$L 2>&1
tcpdump -r $O/montest2.pcap -tt -e -n 2>/dev/null | head -4 | cut -c1-200 >>$L
echo "frames: $(tcpdump -r $O/montest2.pcap 2>/dev/null | wc -l)" >>$L
echo "wlan0 after: $(ip -4 -br addr show wlan0)" >>$L
