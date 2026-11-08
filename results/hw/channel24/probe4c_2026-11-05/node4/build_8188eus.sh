#!/bin/bash
# Build the community RTL8188EUS driver (aircrack-ng/rtl8188eus, pinned commit) on a BeagleBone
# Blue, so the TP-Link TL-WN722N v2/v3 is driven through cfg80211 (`iw`) with ad-hoc mode. The
# kernel's own staging driver (r8188eu) speaks only wireless extensions. Run as root, detached:
#   systemd-run --unit=authbc-build8188 /home/<user>/authbc_tplink/build_8188eus.sh
# Nothing here transmits; the module is built and installed, not loaded.
set -u
O="$(dirname "$(readlink -f "$0")")"
L="$O/build.log"
COMMIT=af3bf004458f76b7aec33e9ba552cd382ed1f5c3
exec >>"$L" 2>&1
step() { echo "[$(date -Is)] $*"; }
fail() { step "FAILED: $*"; echo "$*" >"$O/build_failed"; exit 1; }
rm -f "$O/build_done" "$O/build_failed"
step "start: kernel $(uname -r), commit $COMMIT"

apt-get update -q || fail "apt-get update"
apt-get install -y -q "linux-headers-$(uname -r)" || fail "kernel headers"
[ -d "/lib/modules/$(uname -r)/build" ] || fail "no /lib/modules/$(uname -r)/build after install"
step "headers installed"

cd "$O" && rm -rf rtl8188eus
git clone -q https://github.com/aircrack-ng/rtl8188eus || fail "clone"
cd rtl8188eus && git checkout -q "$COMMIT" || fail "checkout $COMMIT"
step "source: $(git log -1 --format='%H %cd %s')"

# Generic little-endian ARM with cfg80211, as the driver's own README prescribes for ARM boards.
sed -i 's/^CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/; s/^CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/' Makefile
grep -E '^CONFIG_PLATFORM_(I386_PC|ARM_RPI) =' Makefile

make -j1 || fail "make"
[ -f 8188eu.ko ] || fail "no 8188eu.ko"
step "built: $(sha256sum 8188eu.ko)"

make install || fail "make install"
printf 'blacklist r8188eu\nblacklist rtl8xxxu\n' >/etc/modprobe.d/authbc-realtek.conf
depmod -a
step "installed; r8188eu and rtl8xxxu blacklisted (/etc/modprobe.d/authbc-realtek.conf)"
touch "$O/build_done"
