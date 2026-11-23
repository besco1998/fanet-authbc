#!/usr/bin/env python3
"""Read a monitor-mode capture into one row per frame, with the standard library only: the pcap
container, the radiotap header and the 802.11 data frame down to the sender's sequence number.

The frame-level campaign (docs/DECISIONS.md, 2026-11-23; plan: the gate S0, then C1–C3, V1–V4).
The sniffer is the TP-Link on Blue 2 in monitor mode (rtl8188eus `af3bf004` plus the approved TSF
line); what its radiotap header carries was read in the driver source before any data
(DECISIONS, "The sniffer's driver"): TSFT (with the TSF line), flags, rate, channel, dBm signal,
antenna, RX flags; the FCS is appended to every frame.

**Radiotap** (radiotap.org): fields follow the presence bitmaps in bit order, each aligned to its
own natural size counted from the start of the radiotap header. Only the fields up to bit 22 are
known here; a frame whose bitmap names a later field, or a vendor or radiotap namespace, stops the
walk, and the fields after it are left out rather than guessed.

**The payload** (`hw/channel/bcast_tx.py`): UDP to port 9999, the first ten bytes the sender's
sequence number in ASCII, left-justified.

    python analysis/pcap_frames.py CAPTURE.pcap   -> one CSV row per frame on stdout
"""
from __future__ import annotations

import csv
import struct
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

LINKTYPE_RADIOTAP = 127
PAYLOAD_PORT = 9999
SEQ_BYTES = 10

# radiotap field: bit -> (alignment, size); radiotap.org, "Defined fields"
_FIELDS: dict[int, tuple[int, int]] = {
    0: (8, 8),    # TSFT, u64 µs
    1: (1, 1),    # flags
    2: (1, 1),    # rate, 500 kb/s units
    3: (2, 4),    # channel: u16 MHz, u16 flags
    4: (1, 2),    # FHSS
    5: (1, 1),    # dBm antenna signal, s8
    6: (1, 1),    # dBm antenna noise, s8
    7: (2, 2),    # lock quality
    8: (2, 2),    # TX attenuation
    9: (2, 2),    # dB TX attenuation
    10: (1, 1),   # dBm TX power
    11: (1, 1),   # antenna
    12: (1, 1),   # dB antenna signal
    13: (1, 1),   # dB antenna noise
    14: (2, 2),   # RX flags
    15: (2, 2),   # TX flags
    16: (1, 1),   # RTS retries
    17: (1, 1),   # data retries
    18: (4, 8),   # XChannel
    19: (1, 3),   # MCS
    20: (4, 8),   # A-MPDU status
    21: (2, 12),  # VHT
    22: (8, 12),  # timestamp
}
F_SHORTPRE, F_FCS, F_BADFCS = 0x02, 0x10, 0x40
EXT_BIT, NAMESPACE_BITS = 31, (29, 30)


@dataclass
class Frame:
    """One captured frame. `seq` is the sender's own number (None if the frame is not ours)."""
    index: int
    host_ns: int
    tsft_us: int | None
    rate_mbps: float | None
    short_preamble: bool | None
    bad_fcs: bool
    signal_dbm: int | None
    freq_mhz: int | None
    length: int                  # 802.11 frame length without the FCS
    src: str | None              # transmitter address, aa:bb:…
    src_ip: str | None
    seq: int | None
    udp_len: int | None


def records(path: Path) -> Iterator[tuple[int, bytes]]:
    """(host time in ns, frame bytes) for each record of a pcap file."""
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError(f"{path}: shorter than a pcap header")
    magic = data[:4]
    table = {b"\xd4\xc3\xb2\xa1": ("<", 1000), b"\xa1\xb2\xc3\xd4": (">", 1000),
             b"\x4d\x3c\xb2\xa1": ("<", 1), b"\xa1\xb2\x3c\x4d": (">", 1)}
    if magic not in table:
        raise ValueError(f"{path}: not a pcap file (magic {magic.hex()})")
    end, frac_ns = table[magic]
    linktype = struct.unpack(end + "I", data[20:24])[0]
    if linktype != LINKTYPE_RADIOTAP:
        raise ValueError(f"{path}: link type {linktype}, not radiotap ({LINKTYPE_RADIOTAP})")
    off = 24
    while off + 16 <= len(data):
        sec, frac, incl, _orig = struct.unpack(end + "IIII", data[off:off + 16])
        off += 16
        yield sec * 1_000_000_000 + frac * frac_ns, data[off:off + incl]
        off += incl


def radiotap(buf: bytes) -> tuple[dict[int, bytes], int]:
    """The radiotap fields present ({bit: raw bytes}) and the header's length."""
    if len(buf) < 8 or buf[0] != 0:
        raise ValueError("not a radiotap version 0 header")
    length = struct.unpack("<H", buf[2:4])[0]
    words, pos = [], 4
    while True:
        w = struct.unpack("<I", buf[pos:pos + 4])[0]
        words.append(w)
        pos += 4
        if not w & (1 << EXT_BIT):
            break
    fields: dict[int, bytes] = {}
    present = words[0]
    for bit in range(EXT_BIT):
        if not present & (1 << bit):
            continue
        if bit in NAMESPACE_BITS or bit not in _FIELDS:
            break                                  # unknown layout from here on: stop
        align, size = _FIELDS[bit]
        pos += (-pos) % align
        fields[bit] = buf[pos:pos + size]
        pos += size
    if pos > length:
        raise ValueError(f"radiotap fields run past its length ({pos} > {length})")
    return fields, length


def _mac(b: bytes) -> str:
    return ":".join(f"{x:02x}" for x in b)


def _payload(body: bytes) -> tuple[str | None, int | None, int | None]:
    """(source IP, sequence number, UDP length) from an LLC/SNAP + IPv4 + UDP body, if ours."""
    if len(body) < 8 or body[:6] != b"\xaa\xaa\x03\x00\x00\x00" or body[6:8] != b"\x08\x00":
        return None, None, None
    ip = body[8:]
    if len(ip) < 20 or ip[0] >> 4 != 4 or ip[9] != 17:
        return None, None, None
    ihl = (ip[0] & 0x0F) * 4
    src_ip = ".".join(str(x) for x in ip[12:16])
    udp = ip[ihl:]
    if len(udp) < 8:
        return src_ip, None, None
    dport, ulen = struct.unpack(">H", udp[2:4])[0], struct.unpack(">H", udp[4:6])[0]
    if dport != PAYLOAD_PORT or len(udp) < 8 + SEQ_BYTES:
        return src_ip, None, ulen
    text = udp[8:8 + SEQ_BYTES].decode("ascii", "replace").strip()
    return src_ip, (int(text) if text.isdigit() else None), ulen


def parse(path: Path) -> Iterator[Frame]:
    for k, (host_ns, buf) in enumerate(records(path)):
        fields, rt_len = radiotap(buf)
        flags = fields[1][0] if 1 in fields else 0
        mpdu = buf[rt_len:]
        if flags & F_FCS:
            mpdu = mpdu[:-4]
        src = src_ip = seq = ulen = None
        if len(mpdu) >= 24 and (mpdu[0] >> 2) & 0x3 == 2:          # a data frame
            src = _mac(mpdu[10:16])
            hdr = 24 + (2 if (mpdu[0] >> 4) & 0x8 else 0)           # QoS data: +2
            src_ip, seq, ulen = _payload(mpdu[hdr:])
        yield Frame(
            index=k, host_ns=host_ns,
            tsft_us=struct.unpack("<Q", fields[0])[0] if 0 in fields else None,
            rate_mbps=fields[2][0] / 2 if 2 in fields else None,
            short_preamble=bool(flags & F_SHORTPRE) if 1 in fields else None,
            bad_fcs=bool(flags & F_BADFCS),
            signal_dbm=struct.unpack("b", fields[5])[0] if 5 in fields else None,
            freq_mhz=struct.unpack("<H", fields[3][:2])[0] if 3 in fields else None,
            length=len(mpdu), src=src, src_ip=src_ip, seq=seq, udp_len=ulen)


def main() -> None:
    w = csv.DictWriter(sys.stdout, fieldnames=list(Frame.__dataclass_fields__),
                       lineterminator="\n")
    w.writeheader()
    for f in parse(Path(sys.argv[1])):
        w.writerow(asdict(f))


if __name__ == "__main__":
    main()
