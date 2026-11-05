#!/bin/bash
# Blue 2, diagnosis (not a measurement): does probe 3's exit from ad-hoc mode freeze the board when
# its steps run back to back, as they did at 17:38 (F125)? The replay with 3 s between steps did
# not freeze. N cycles of: probe 3's join (iwd stopped, every other radio down, ad-hoc on channel 11,
# 1 Mb/s fixed), 10 s of saturated broadcasts, then probe 3's revert exactly, its steps back to back.
# A marker is written and synced before each step (milliseconds), the kernel log streams to the card
# with a sync every second, and the watchdog resets the board if it freezes.
# Run as root:  systemd-run --collect --unit=authbc-diag-loop <this> <cycles>
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/loop.log"
IW=/usr/sbin/iw
T=tplink0
P=/proc/net/8188eu/$T/rate_ctl
N="$1"
mark() { echo "[$(date +%T.%3N)] $*" >>"$L"; sync; }

dmesg -w --time-format iso >>"$O/kern_loop.log" 2>&1 &
KLOG_PID=$!
( while true; do sync; sleep 1; done ) &
SYNC_PID=$!
systemd-run --on-active=$((N * 75 + 300)) --unit=authbc-diag-restore /bin/sh -c \
    "ip link set $T down; ip link set wlan0 up; systemctl start iwd" >/dev/null 2>&1
mark "=== start: $N cycles, boot=$(cut -c1-8 /proc/sys/kernel/random/boot_id)"

for c in $(seq 1 "$N"); do
    mark "cycle $c: join"
    systemctl stop iwd
    for i in /sys/class/net/wlan*; do ip link set "$(basename "$i")" down; done
    ip link set "$T" down
    $IW dev "$T" set type ibss >>"$L" 2>&1
    ip link set "$T" up
    sleep 2
    $IW dev "$T" ibss join authbc-mesh 2462 fixed-freq >>"$L" 2>&1
    echo "0x00 0" >"$P"
    ip addr add 10.0.0.4/24 dev "$T" >>"$L" 2>&1
    sleep 5
    mark "cycle $c: in cell [$($IW dev "$T" link 2>&1 | head -1)] rate [$(tr '\n' ' ' <"$P")]; sending"
    python3 "$O/bcast_tx.py" --rate 1000 --bytes 145 --redraw --seed $((7000 + c)) --seconds 10 \
        --out "$O/tx_loop_$c.json" >>"$L" 2>&1
    # probe 3's revert, back to back (blue_probe_iw.sh, revert())
    mark "c$c pkill";        pkill -f "bcast_(tx|rx).py" 2>/dev/null
    mark "c$c rate 0xff";    echo "0xff" >"$P" 2>/dev/null
    mark "c$c ibss leave";   $IW dev "$T" ibss leave 2>/dev/null
    mark "c$c addr flush";   ip addr flush dev "$T" 2>/dev/null
    mark "c$c link down";    ip link set "$T" down 2>/dev/null
    mark "c$c type managed"; $IW dev "$T" set type managed 2>/dev/null
    mark "c$c wlan0 up";     ip link set wlan0 up 2>/dev/null
    mark "c$c start iwd";    systemctl start iwd
    mark "c$c revert done"
    sleep 30
    mark "cycle $c: LAN $(ip -4 -br addr show wlan0 | awk '{print $3}')"
done
systemctl stop authbc-diag-restore.timer 2>/dev/null
mark "=== done: $N cycles"
kill "$KLOG_PID" "$SYNC_PID" 2>/dev/null
