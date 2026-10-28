#!/bin/bash
# Read or set the Broadcom firmware's frame-burst mode on wlan0. Runs as root.
#
# Why this exists. The Linux driver switches frame burst ON whenever it configures the chip
# (`brcmf_config_dongle`: BRCMF_C_SET_FAKEFRAG = 1, "enable frameburst mode in default firmware
# setting", kernel commit of 2018-12-13). With it on, a radio that holds several frames sends
# them one behind the other without contending again. IEEE 802.11's access rule — and ns-3, and
# the model of docs/02 §6g — draw a new backoff counter before every frame. The two-board
# contention measurement of 2026-10-09 could not be read without separating the two
# (docs/CONTENTION_HW_FRAMEBURST_EXPECTATIONS.md).
#
# How. brcmfmac passes a firmware command through one nl80211 vendor command (vendor.c: OUI
# 0x001018, subcommand 1). Its payload is `struct brcmf_vndr_dcmd_hdr` — cmd, len, offset, set,
# magic, each 32 bits little-endian — followed by the data. Commands 218 and 219 are the
# firmware's GET_ and SET_FAKEFRAG.
#
#   frameburst.sh get        prints 0 or 1
#   frameburst.sh set 0|1    sets it, then prints what the firmware reports
set -u
IW="${IW:-/usr/sbin/iw}"       # overridable so the reply parser can be tested off a board
OUI=0x001018
SUBCMD=0x1

header() {   # $1 = firmware command (< 256), $2 = 1 to set, 0 to get
    printf '0x%02x 0x00 0x00 0x00  0x04 0x00 0x00 0x00  0x14 0x00 0x00 0x00  0x%02x 0x00 0x00 0x00  0x00 0x00 0x00 0x00' \
        "$1" "$2"
}

get() {
    local out bytes i len type
    # shellcheck disable=SC2046
    out=$("$IW" dev wlan0 vendor recv "$OUI" "$SUBCMD" $(header 218 0) 0x00 0x00 0x00 0x00 2>&1) \
        || { echo "error: $out"; return 1; }
    # The reply is a list of netlink attributes (length, type, value, padded to four bytes);
    # attribute 2 carries the data. Parsed in the shell: the boards' awk has no hex conversion.
    read -r -a bytes <<<"$(echo "$out" | sed -n 's/^vendor response: //p')"
    i=0
    while [ $((i + 4)) -le "${#bytes[@]}" ]; do
        len=$((0x${bytes[i]} + 256 * 0x${bytes[i + 1]}))
        type=$((0x${bytes[i + 2]} + 256 * 0x${bytes[i + 3]}))
        [ "$len" -lt 4 ] && break
        if [ "$type" = 2 ] && [ "$len" -ge 5 ]; then
            echo $((0x${bytes[i + 4]}))
            return 0
        fi
        i=$((i + (len + 3) / 4 * 4))
    done
    echo "error: no data attribute"
    return 1
}

case "${1:-}" in
get)
    get
    ;;
set)
    case "${2:-}" in 0 | 1) ;; *) echo "usage: $0 get | set 0|1" >&2; exit 2 ;; esac
    # shellcheck disable=SC2046
    "$IW" dev wlan0 vendor send "$OUI" "$SUBCMD" $(header 219 1) "0x0$2" 0x00 0x00 0x00 \
        >/dev/null 2>&1 || { echo "error: set failed"; exit 1; }
    get
    ;;
*)
    echo "usage: $0 get | set 0|1" >&2
    exit 2
    ;;
esac
