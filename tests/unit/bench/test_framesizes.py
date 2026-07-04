"""Frame-size model hand values + feasibility (docs/02 T2)."""

from __future__ import annotations

import pytest

from authbc.bench.framesizes import amplification, auth_bytes, build_rows, frame_bytes


def test_auth_bytes_per_placement() -> None:
    assert auth_bytes("A", 8) == 512   # 8 sigs × 64
    assert auth_bytes("B", 8) == 64    # one sig
    assert auth_bytes("C", 8) == 112   # 96 + 2·8
    assert auth_bytes("D", 8) == 70    # 64 + 6


def test_frame_bytes_hand_values() -> None:
    # B, s=100, b=8: 40 + 8·100 + 64 = 904 ; bytes/rec = 113
    assert frame_bytes("B", 100, 8) == pytest.approx(904)
    # A, s=100, b=8: 40 + 800 + 512 = 1352
    assert frame_bytes("A", 100, 8) == pytest.approx(1352)
    # amplification B, s=100, b=8 = (904/8)/100 = 1.13
    assert amplification("B", 100, 8) == pytest.approx(1.13)


def test_bytes_per_rec_decreases_with_b_for_single_auth() -> None:
    # B amortizes one signature over b records ⇒ bytes/rec strictly decreasing in b
    per = [frame_bytes("B", 69, b) / b for b in (1, 2, 4, 8, 16)]
    assert all(per[i] > per[i + 1] for i in range(len(per) - 1))


def test_build_rows_shape_and_feasibility() -> None:
    rows = build_rows({"json": 193.5, "cbor": 68.9, "msgpack": 68.8, "delta": 45.0})
    assert len(rows) == 4 * 4 * 6  # placements × encodings × b

    def find(placement, enc, b):
        return next(r for r in rows if r["placement"] == placement
                    and r["encoding"] == enc and r["b"] == b)

    assert find("B", "json", 32)["feasible"] == 0   # 40 + 32·193.5 + 64 ≫ 1500
    assert find("B", "delta", 8)["feasible"] == 1
