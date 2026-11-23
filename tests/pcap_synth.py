"""Synthetic monitor-mode captures for the frame-level campaign's tests: the radiotap layout
the sniffer's driver writes (rtl8188eus `fill_radiotap_hdr()`), an IBSS data frame carrying
`bcast_tx.py`'s payload, and the pcap container."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import pcap_frames as pf  # noqa: E402

SRC = bytes.fromhex("d83add16a733")


def radiotap_realtek(tsft: int | None, signal: int, flags: int = pf.F_FCS,
                     rate_500k: int = 2) -> bytes:
    """As fill_radiotap_hdr() builds it: TSFT (if tsfl ≠ 0), flags, rate, a pad, channel,
    dBm signal, antenna, RX flags."""
    present = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 5) | (1 << 11) | (1 << 14)
    body = b""
    if tsft is not None:
        present |= 1
        body += struct.pack("<Q", tsft)
    body += bytes([flags, rate_500k])
    body += struct.pack("<HH", 2462, 0x00A0)
    body += struct.pack("b", signal) + b"\x00" + b"\x00\x00"
    return struct.pack("<BBHI", 0, 0, 8 + len(body), present) + body


def data_frame(seq: int, src_ip: str = "10.0.0.1", qos: bool = False, payload: int = 145,
               port: int = 9999) -> bytes:
    fc = bytes([0x88 if qos else 0x08, 0x00])
    hdr = fc + b"\x00\x00" + b"\xff" * 6 + SRC + bytes.fromhex("021187aabbcc") + b"\x10\x00"
    if qos:
        hdr += b"\x00\x00"
    udp_payload = f"{seq:<10}".encode() + b"x" * (payload - 10)
    udp = struct.pack(">HHHH", 40000, port, 8 + len(udp_payload), 0) + udp_payload
    ip = bytes([0x45, 0]) + struct.pack(">H", 20 + len(udp)) + b"\x00" * 4 + bytes([64, 17]) \
        + b"\x00\x00" + bytes(int(x) for x in src_ip.split(".")) + bytes([10, 0, 0, 255])
    return hdr + b"\xaa\xaa\x03\x00\x00\x00\x08\x00" + ip + udp


def pcap(records: list[tuple[int, bytes]], magic: bytes = b"\xd4\xc3\xb2\xa1",
         end: str = "<") -> bytes:
    out = magic + struct.pack(end + "HHiIII", 2, 4, 0, 0, 65535, pf.LINKTYPE_RADIOTAP)
    ns = magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
    for t_ns, frame in records:
        sec, rem = divmod(t_ns, 1_000_000_000)
        frac = rem if ns else rem // 1000
        out += struct.pack(end + "IIII", sec, frac, len(frame), len(frame)) + frame
    return out
