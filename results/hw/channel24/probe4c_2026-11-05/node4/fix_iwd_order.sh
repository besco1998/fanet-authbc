#!/bin/sh
# Blue 2: start iwd only once the TI radio's interface (wlan0) exists.
# iwd uses only a radio's default interface (wl18xx sets that flag). When the radio was registered
# before its interface, iwd logged "No default interface for wiphy 1" and never connected it, so the
# Blue stayed off the LAN after every reboot since 17:38 (boots of 18:54, 18:58 and 19:04).
# Restarting iwd with both present connected it at once. Wants= rather than Requires=: if wlan0
# never appears, iwd still starts after the device timeout (90 s).
# Run as root.
set -eu
D=/etc/systemd/system/iwd.service.d
printf '%s\n' '[Unit]' 'Wants=sys-subsystem-net-devices-wlan0.device' \
    'After=sys-subsystem-net-devices-wlan0.device' >"$D/authbc-wait-ti-radio.conf"
systemctl daemon-reload
for f in "$D"/*.conf; do echo "--- $f"; cat "$f"; done
systemctl show iwd -p After -p Wants | tr ' ' '\n' | grep -E 'wlan0|^(After|Wants)='
