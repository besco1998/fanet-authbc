#!/usr/bin/env python3
"""One lean frame, byte by byte, as a table for the thesis (thesis ch. 5; docs/01 §4b).

The frame is built, encoded, decoded and verified by the library — `placement/wire_v2.py` — and
this script only cuts the emitted bytes into the fields that module defines and writes them
beside their meaning:

    python analysis/worked_frame.py        # writes thesis/tab_worked_frame.tex

The second and third records of generator seed 1, an hour into a flight, from sender 40 000: a
keyframe and one delta, under one Ed25519 signature made with a fixed test key. (Not the first
two: the first record of a chain has no predecessor, and its link is thirty-two zero bytes.)
Nothing here is typed: `tests/test_thesis_matches_artifacts.py` regenerates the table and
compares it with the committed file.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import cbor2  # noqa: E402

from authbc.bench import leanframes  # noqa: E402
from authbc.crypto.ed25519 import Ed25519Scheme  # noqa: E402
from authbc.encodings.base import svarint_decode, uvarint_decode  # noqa: E402
from authbc.placement import wire_v2  # noqa: E402

OUT = REPO / "thesis" / "tab_worked_frame.tex"
SEED, RECORDS = 1, 2
KEY_SEED = bytes(range(32))
FIELD_MEANING = {
    wire_v2.F_V: ("v", "format version"),
    wire_v2.F_T: ("t", "frame type: one signature over the frame, decodes alone"),
    wire_v2.F_SRC: ("src", "sender identifier"),
    wire_v2.F_BASE_SEQ: ("base\\_seq", "sequence number of the first record"),
    wire_v2.F_N: ("n", "records in the frame"),
}
UNITS = {"ts": "ms", "lat": "$10^{-7}$ deg", "lon": "$10^{-7}$ deg", "alt": "cm",
         "vel_x": "cm/s", "vel_y": "cm/s", "vel_z": "cm/s", "battery": "\\%", "mode": ""}


def build() -> tuple[bytes, wire_v2.FrameV2]:
    """The frame as emitted, and as decoded again and verified."""
    sk, pk = Ed25519Scheme().keygen(seed=KEY_SEED)
    recs = leanframes.chained_records(SEED, RECORDS + 1)[1:]
    data = wire_v2.encode_frame_v2(wire_v2.build_B_v2(recs, sk))
    frame = wire_v2.decode_frame_v2(data)
    if not wire_v2.verify_v2(frame, pk) or list(frame.recs) != recs:
        raise SystemExit("the worked frame does not decode to its records and verify")
    return data, frame


def _hex(raw: bytes, keep: int = 0) -> str:
    """Hex of `raw`; with `keep`, only the first `keep` and the last two bytes."""
    if keep and len(raw) > keep + 2:
        return f"{raw[:keep].hex(' ')} \\ldots{{}} {raw[-2:].hex(' ')}"
    return raw.hex(" ")


def _stream_rows(stream: bytes, frame: wire_v2.FrameV2) -> list[tuple[bytes, str, str]]:
    """One row per varint of the record stream: its bytes, the field, the value it carries."""
    rows, pos = [], 0
    for i, rec in enumerate(frame.recs):
        kind = "keyframe" if i == 0 else "delta"
        prev = wire_v2._values(frame.recs[i - 1]) if i else None
        for j, name in enumerate(wire_v2.STREAM_FIELDS):
            unsigned = i == 0 and name in wire_v2._UNSIGNED
            value, end = (uvarint_decode if unsigned else svarint_decode)(stream, pos)
            absolute = wire_v2._values(rec)[j]
            if value != (absolute if prev is None else absolute - prev[j]):
                raise SystemExit(f"record {i}, field {name}: the stream does not hold the record")
            label = name.replace("_", "\\_")
            unit = f" {UNITS[name]}" if UNITS[name] else ""
            what = (f"${absolute}${unit}" if prev is None
                    else f"${value:+d}${unit} (now ${absolute}$)")
            rows.append((stream[pos:end], f"{kind}: {label}", what))
            pos = end
    if pos != len(stream):
        raise SystemExit("bytes left over in the record stream")
    return rows


def rows() -> tuple[list[tuple[str, str, str, int]], int]:
    """(hex, field, meaning, bytes) for every part of the frame, and the frame's length."""
    data, frame = build()
    out: list[tuple[str, str, str, int]] = []
    cut = [data[:1]]
    out.append((_hex(data[:1]), "(map)", "a CBOR map of eight pairs", 1))
    fields = {wire_v2.F_V: wire_v2.WIRE_VERSION_2, wire_v2.F_T: int(frame.t),
              wire_v2.F_SRC: frame.src, wire_v2.F_BASE_SEQ: frame.base_seq, wire_v2.F_N: frame.n}
    for key, value in fields.items():
        raw = cbor2.dumps(key) + cbor2.dumps(value)
        name, meaning = FIELD_MEANING[key]
        out.append((_hex(raw), name, f"{meaning}: {value}", len(raw)))
        cut.append(raw)
    stream = wire_v2.record_stream(frame.recs, None)
    for key, name, body, meaning in (
            (wire_v2.F_LINK, "link", frame.link, "hash of the record before the first one"),
            (wire_v2.F_RECS, "recs", stream, None),
            (wire_v2.F_AUTH, "auth", frame.auth, "Ed25519 signature over the canonical records")):
        head = cbor2.dumps(key) + cbor2.dumps(body)[:-len(body)]
        out.append((_hex(head), name, f"key, and a byte string of {len(body)}", len(head)))
        cut.append(head)
        if meaning is None:
            for raw, field, what in _stream_rows(stream, frame):
                out.append((_hex(raw), field, what, len(raw)))
        else:
            out.append((_hex(body, keep=6), "", meaning, len(body)))
        cut.append(body)
    if b"".join(cut) != data:
        raise SystemExit("the rows do not add up to the emitted frame")
    return out, len(data)


def render() -> str:
    table, total = rows()
    lines = ["% Generated by analysis/worked_frame.py from an emitted frame — do not edit.",
             "{\\small", "\\begin{longtable}{@{}p{5.1cm} p{2.6cm} p{5.2cm} r@{}}", "\\toprule",
             "bytes on the wire (hex) & field & content & B \\\\", "\\midrule", "\\endhead",
             "\\bottomrule", "\\endfoot"]
    for hexed, field, meaning, n in table:
        lines.append(f"\\texttt{{{hexed}}} & {field} & {meaning} & {n} \\\\")
    lines += ["\\midrule", f"\\multicolumn{{3}}{{@{{}}l}}{{the frame}} & {total} \\\\",
              "\\end{longtable}", "}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.write_text(render())
    print(f"wrote {OUT.relative_to(REPO)}: {rows()[1]} bytes in {len(rows()[0])} rows")


if __name__ == "__main__":
    main()
