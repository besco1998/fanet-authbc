#!/bin/sh
# Blue 2: let a freeze recover by itself (Mohamed, 2026-11-05: "Watchdog on, diagnose").
# After probe 3 the board froze and stayed frozen until its power was cut: watchdog0 was inactive,
# systemd's RuntimeWatchdogSec off, kernel.panic 0. The frozen boot never flushed probe.log's last
# 177 bytes in 80 minutes, so writeback itself had stopped: a kernel lockup, not one stuck process.
# * systemd pets the hardware watchdog (omap_wdt) every 15 s with a 30 s timeout: a hard freeze
#   resets the board.
# * kernel.panic=10 reboots 10 s after a panic; softlockup_panic=1 makes a CPU stuck in the kernel
#   a panic.
# Undo: delete the two files, `systemctl daemon-reexec`, `sysctl kernel.panic=0
# kernel.softlockup_panic=0`. Run as root.
set -eu
mkdir -p /etc/systemd/system.conf.d
printf '%s\n' '[Manager]' 'RuntimeWatchdogSec=30s' >/etc/systemd/system.conf.d/authbc-watchdog.conf
printf '%s\n' 'kernel.panic = 10' 'kernel.softlockup_panic = 1' >/etc/sysctl.d/90-authbc-panic.conf
systemctl daemon-reexec
sysctl -q -p /etc/sysctl.d/90-authbc-panic.conf
sleep 2
echo "--- files"; cat /etc/systemd/system.conf.d/authbc-watchdog.conf /etc/sysctl.d/90-authbc-panic.conf
echo "--- in force"
systemctl show -p RuntimeWatchdogUSec
echo "kernel.panic=$(cat /proc/sys/kernel/panic) softlockup_panic=$(cat /proc/sys/kernel/softlockup_panic)"
echo "watchdog0: state=$(cat /sys/class/watchdog/watchdog0/state) timeout=$(cat /sys/class/watchdog/watchdog0/timeout) identity=$(cat /sys/class/watchdog/watchdog0/identity)"
