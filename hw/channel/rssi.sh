#!/bin/bash
# Read the Broadcom firmware's RSSI on wlan0, for one peer by its address or with the zero address.
# Runs as root.
#
# Why this exists. Every session plan logs each sender's signal strength (Mohamed, 2026-11-19).
# In ad-hoc (IBSS) mode, brcmfmac cannot give it through nl80211:
#   * a station query for any address returns one firmware RSSI, read with a zeroed address
#     (brcmf_cfg80211_get_station_ibss, cfg80211.c:3085–3112 and 3155–3156, rpi-6.12.y);
#   * the station dump reads the association list, which is empty in IBSS (RESULTS.md §3).
#
# How. The firmware command GET_RSSI (127, fwil.h) takes struct brcmf_scb_val_le
# {__le32 val; u8 ea[6]} (fwil_types.h:648; 12 bytes with its padding). brcmfmac's vendor command
# (OUI 0x001018, subcommand 1, as frameburst.sh) copies the caller's buffer to the firmware on a
# get as well as a set (vendor.c, the dcmd handler; bcdc.c, brcmf_proto_bcdc_msg), so the peer's
# address reaches the firmware. Whether the firmware answers per peer in IBSS mode is a property
# of the firmware, not of the driver: it is checked at the boards before any window is scored
# (predictions/W1p.md, the kit check), with the zero-address reading in single-sender windows as
# the registered fallback.
#
#   rssi.sh aa:bb:cc:dd:ee:ff    prints the firmware's RSSI for that address, in dBm
#   rssi.sh any                  the same with the zero address (what the driver reports)
# A reply without a data attribute prints "error: ..." and exits non-zero, never a number.
set -u
IW="${IW:-/usr/sbin/iw}"       # overridable so the reply parser can be tested off a board
OUI=0x001018
SUBCMD=0x1

mac_bytes() {   # aa:bb:cc:dd:ee:ff -> "0xaa 0xbb 0xcc 0xdd 0xee 0xff"
    local m="$1" out="" b
    [[ "$m" =~ ^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$ ]] || return 1
    for b in ${m//:/ }; do out+="0x$b "; done
    echo "${out% }"
}

case "${1:-}" in
any) ea="0x00 0x00 0x00 0x00 0x00 0x00" ;;
"") echo "usage: $0 aa:bb:cc:dd:ee:ff | any" >&2; exit 2 ;;
*) ea=$(mac_bytes "$1") || { echo "usage: $0 aa:bb:cc:dd:ee:ff | any" >&2; exit 2; } ;;
esac

# struct brcmf_vndr_dcmd_hdr: cmd 127, len 12, offset 20, set 0, magic 0; then val 0, ea, pad 2.
# shellcheck disable=SC2086
out=$("$IW" dev wlan0 vendor recv "$OUI" "$SUBCMD" \
    0x7f 0x00 0x00 0x00  0x0c 0x00 0x00 0x00  0x14 0x00 0x00 0x00  0x00 0x00 0x00 0x00 \
    0x00 0x00 0x00 0x00  0x00 0x00 0x00 0x00  $ea  0x00 0x00 2>&1) \
    || { echo "error: $out"; exit 1; }

# The reply is a list of netlink attributes (length, type, value, padded to four bytes);
# attribute 2 carries the 12-byte struct, whose first four bytes are val, little-endian, signed.
read -r -a bytes <<<"$(echo "$out" | sed -n 's/^vendor response: //p')"
i=0
while [ $((i + 4)) -le "${#bytes[@]}" ]; do
    len=$((0x${bytes[i]} + 256 * 0x${bytes[i + 1]}))
    type=$((0x${bytes[i + 2]} + 256 * 0x${bytes[i + 3]}))
    [ "$len" -lt 4 ] && break
    if [ "$type" = 2 ] && [ "$len" -ge 8 ] && [ $((i + 8)) -le "${#bytes[@]}" ]; then
        v=$((0x${bytes[i + 4]} + 256 * 0x${bytes[i + 5]} + 65536 * 0x${bytes[i + 6]} \
             + 16777216 * 0x${bytes[i + 7]}))
        [ "$v" -ge 2147483648 ] && v=$((v - 4294967296))
        echo "$v"
        exit 0
    fi
    i=$((i + (len + 3) / 4 * 4))
done
echo "error: no data attribute"
exit 1
