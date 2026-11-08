#!/bin/bash
# Blue 2, diagnosis (not a measurement): which step of leaving ad-hoc mode froze the board after
# probe 3 (F125)? Puts the TP-Link into an ad-hoc cell as probe 3 did (rate fixed at 1 Mb/s), holds
# it 20 s, then replays probe 3's revert one step at a time. Every step's start and end is written
# and synced to the SD card, 3 s apart, so a freeze leaves the step that caused it as the last line.
# The hardware watchdog (30 s) resets the board if it freezes.
#   mode lan:   the Blue's own radio stays on the home Wi-Fi (iwd ignores tplink0).
#   mode probe: as probe 3 — iwd stopped and the TI radio down; a deadman restores both in 300 s.
# Run as root:  systemd-run --collect --unit=authbc-diag-exit <this> <lan|probe>
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/diag_exit.log"
IW=/usr/sbin/iw
T=tplink0
P=/proc/net/8188eu/$T/rate_ctl
MODE="$1"
step() { echo "[$(date +%T.%3N)] $*" >>"$L"; sync; }
run() { step "BEGIN $*"; "$@" >>"$L" 2>&1; local rc=$?; step "END rc=$rc $*"; sleep 3; }

step "=== start mode=$MODE boot=$(cat /proc/sys/kernel/random/boot_id | cut -c1-8) up=$(cut -d' ' -f1 /proc/uptime)s"
if [ "$MODE" = probe ]; then
    systemd-run --on-active=300 --unit=authbc-diag-restore /bin/sh -c 'ip link set wlan0 up; systemctl start iwd' >/dev/null 2>&1
    run systemctl stop iwd
    run ip link set wlan0 down
fi
run ip link set "$T" down
run "$IW" dev "$T" set type ibss
run ip link set "$T" up
run "$IW" dev "$T" ibss join authbc-mesh 2462 fixed-freq
step "BEGIN rate_ctl 0x00 0"; echo "0x00 0" >"$P"; step "END rate_ctl now: $(tr '\n' ' ' <"$P")"
run ip addr add 10.0.0.4/24 dev "$T"
sleep 20
step "in the cell: $("$IW" dev "$T" info | grep -E 'type|channel' | tr -s '\t\n' '  ') | $("$IW" dev "$T" link | head -1)"

# probe 3's revert, in its order
step "BEGIN rate_ctl 0xff"; echo "0xff" >"$P"; step "END rate_ctl now: $(tr '\n' ' ' <"$P")"; sleep 3
run "$IW" dev "$T" ibss leave
run ip addr flush dev "$T"
run ip link set "$T" down
run "$IW" dev "$T" set type managed
if [ "$MODE" = probe ]; then
    run ip link set wlan0 up
    run systemctl start iwd
    systemctl stop authbc-diag-restore.timer 2>/dev/null
fi
step "=== done: $(ip -br link show "$T" | tr -s ' ')"
