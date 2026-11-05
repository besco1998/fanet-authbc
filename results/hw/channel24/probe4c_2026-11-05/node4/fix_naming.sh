#!/bin/sh
# Blue 2: name the TP-Link "tplink0" when its driver creates it, instead of renaming it later.
# The udev rename (10-authbc-tplink.link) lost a boot race: iwd had the link up at 53 s and udev
# reached it at 59 s, and an interface that is up cannot be renamed. The driver's own `ifname`
# option (os_intfs.c l.3061 -> dev_alloc_name) names it at registration, so nothing can race it.
# systemd-networkd is kept off it, so no DHCP and no IPv4 link-local probes in the ad-hoc cell.
# Run as root.
set -eu
printf '%s\n' 'blacklist r8188eu' 'blacklist rtl8xxxu' 'options 8188eu ifname=tplink0' \
    >/etc/modprobe.d/authbc-realtek.conf
printf '%s\n' '[Match]' 'Name=tplink0' '' '[Link]' 'Unmanaged=yes' \
    >/etc/systemd/network/04-authbc-tplink.network
rm -f /etc/systemd/network/10-authbc-tplink.link
echo "--- /etc/modprobe.d/authbc-realtek.conf"; cat /etc/modprobe.d/authbc-realtek.conf
echo "--- /etc/systemd/network/04-authbc-tplink.network"; cat /etc/systemd/network/04-authbc-tplink.network
echo "--- /etc/systemd/network/"; ls /etc/systemd/network/
