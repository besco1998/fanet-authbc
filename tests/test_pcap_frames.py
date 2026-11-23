"""`analysis/pcap_frames.py` on hand-built captures whose every field is known: the radiotap layout
the sniffer's driver writes (rtl8188eus `fill_radiotap_hdr()`, with and without the TSF line), the
alignment rule, the appended FCS, and the sender's sequence number in the UDP payload."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import pcap_frames as pf  # noqa: E402

sys.path.insert(0, str(REPO / "tests"))
from pcap_synth import data_frame, pcap, radiotap_realtek  # noqa: E402


def _one(tmp_path: Path, frame: bytes, **kw: object) -> pf.Frame:
    p = tmp_path / "c.pcap"
    p.write_bytes(pcap([(1_795_400_000_123_456_000, frame)], **kw))  # type: ignore[arg-type]
    return next(pf.parse(p))


class TestTheSnifferLayout:
    def test_with_the_tsf_line_every_field_is_read(self, tmp_path: Path) -> None:
        f = _one(tmp_path, radiotap_realtek(4_000_123_456, -47) + data_frame(1234) + b"FCS!")
        assert f.tsft_us == 4_000_123_456 and f.signal_dbm == -47 and f.rate_mbps == 1.0
        assert f.freq_mhz == 2462 and f.short_preamble is False and f.bad_fcs is False
        assert (f.src, f.src_ip, f.seq) == ("d8:3a:dd:16:a7:33", "10.0.0.1", 1234)
        assert f.udp_len == 8 + 145

    def test_without_it_the_same_frame_has_no_tsft_and_the_rest_moves_up(self, tmp_path: Path
                                                                       ) -> None:
        f = _one(tmp_path, radiotap_realtek(None, -60) + data_frame(7) + b"FCS!")
        assert f.tsft_us is None and f.signal_dbm == -60 and f.seq == 7

    def test_the_appended_fcs_is_not_counted_in_the_length(self, tmp_path: Path) -> None:
        body = data_frame(1)
        f = _one(tmp_path, radiotap_realtek(1, -50) + body + b"FCS!")
        assert f.length == len(body)

    def test_a_bad_fcs_flag_is_kept(self, tmp_path: Path) -> None:
        f = _one(tmp_path, radiotap_realtek(1, -50, flags=pf.F_FCS | pf.F_BADFCS)
                 + data_frame(1) + b"FCS!")
        assert f.bad_fcs is True


class TestTheGeneralRules:
    def test_alignment_is_counted_from_the_header_start(self) -> None:
        # flags (bit 1) at 8, then TSFT is not present; channel (bit 3) after rate needs a
        # 2-byte boundary: rate at 9, so channel at 10, signal at 14.
        present = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 5)
        body = bytes([0, 2]) + struct.pack("<HH", 2412, 0) + struct.pack("b", -33)
        rt = struct.pack("<BBHI", 0, 0, 8 + len(body), present) + body
        fields, length = pf.radiotap(rt)
        assert struct.unpack("<H", fields[3][:2])[0] == 2412
        assert struct.unpack("b", fields[5])[0] == -33 and length == 15

    def test_an_extended_bitmap_shifts_the_fields(self) -> None:
        present0 = 1 | (1 << pf.EXT_BIT)
        # 12 bytes of header and bitmaps, so the u64 is padded to offset 16
        rt = struct.pack("<BBHII", 0, 0, 24, present0, 0) + b"\x00" * 4 + struct.pack("<Q", 99)
        fields, _ = pf.radiotap(rt)
        assert struct.unpack("<Q", fields[0])[0] == 99

    def test_a_vendor_namespace_stops_the_walk(self) -> None:
        present = (1 << 5) | (1 << 30)
        rt = struct.pack("<BBHI", 0, 0, 9, present) + struct.pack("b", -40)
        fields, _ = pf.radiotap(rt)
        assert list(fields) == [5]

    def test_a_qos_data_frame_is_read(self, tmp_path: Path) -> None:
        f = _one(tmp_path, radiotap_realtek(5, -50) + data_frame(42, qos=True) + b"FCS!")
        assert f.seq == 42

    def test_a_frame_that_is_not_ours_has_no_sequence(self, tmp_path: Path) -> None:
        f = _one(tmp_path, radiotap_realtek(5, -50) + data_frame(42, port=53) + b"FCS!")
        assert f.seq is None and f.src_ip == "10.0.0.1"

    def test_a_beacon_has_a_transmitter_only_if_data(self, tmp_path: Path) -> None:
        beacon = bytes([0x80, 0]) + b"\x00" * 22 + b"\x00" * 12
        f = _one(tmp_path, radiotap_realtek(5, -69) + beacon + b"FCS!")
        assert f.src is None and f.seq is None

    @pytest.mark.parametrize(("magic", "end"), [(b"\xa1\xb2\xc3\xd4", ">"),
                                                (b"\x4d\x3c\xb2\xa1", "<")])
    def test_host_time_from_each_pcap_variant(self, tmp_path: Path, magic: bytes, end: str
                                              ) -> None:
        f = _one(tmp_path, radiotap_realtek(5, -50) + data_frame(1), magic=magic, end=end)
        assert f.host_ns == 1_795_400_000_123_456_000

    def test_a_capture_that_is_not_radiotap_is_refused(self, tmp_path: Path) -> None:
        p = tmp_path / "e.pcap"
        p.write_bytes(b"\xd4\xc3\xb2\xa1" + struct.pack("<HHiIII", 2, 4, 0, 0, 65535, 1))
        with pytest.raises(ValueError, match="link type 1"):
            list(pf.parse(p))
