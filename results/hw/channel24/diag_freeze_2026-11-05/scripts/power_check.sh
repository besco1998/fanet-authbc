#!/bin/sh
# Blue 2 (read-only): USB power errors in every readable boot, and the TPS65217 PMIC's view of its
# power inputs. Run as root.
for b in $(journalctl --list-boots --no-pager -q 2>/dev/null | awk '{print $2}'); do
    first=$(journalctl -b "$b" --no-pager -q -o short 2>/dev/null | grep -m1 'Nov 05' | cut -c1-15)
    n=$(journalctl -b "$b" -k --no-pager -q 2>/dev/null | grep -ciE 'VBUS_ERROR|over-?current|usb 1-1: USB disconnect|Babble')
    echo "boot $(echo "$b" | cut -c1-8) (first dated line: ${first:-none}): $n"
    journalctl -b "$b" -k --no-pager -q -o short-precise 2>/dev/null | grep -iE 'VBUS_ERROR|over-?current|usb 1-1: USB disconnect|Babble' | cut -c1-160
done
command -v i2cget >/dev/null || apt-get install -y -q i2c-tools >/dev/null 2>&1
echo "i2cget: $(command -v i2cget)"
s=$(i2cget -f -y 0 0x24 0x0a 2>&1); echo "STATUS 0x0A raw=$s"
case "$s" in 0x*) v=$((s)); echo "  ACPWR(bit3)=$(( (v>>3)&1 )) USBPWR(bit2)=$(( (v>>2)&1 ))";; esac
p=$(i2cget -f -y 0 0x24 0x01 2>&1); echo "PPATH 0x01 raw=$p"
case "$p" in 0x*) v=$((p)); echo "  AC_EN=$(( (v>>5)&1 )) USB_EN=$(( (v>>4)&1 )) IAC=$(( (v>>2)&3 )) IUSB=$(( v&3 ))";; esac
echo "ADC raw: ch5=$(cat /sys/bus/iio/devices/iio:device0/in_voltage5_raw) ch6=$(cat /sys/bus/iio/devices/iio:device0/in_voltage6_raw)"
