"""`analysis/geometry.py`: the template is incomplete by construction; a filled record is complete;
a choice left as the template's alternatives counts as missing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "analysis"))

import geometry  # noqa: E402

TEMPLATE = REPO / "experiments" / "channel24" / "geometry_template.json"


def _filled() -> dict:
    g = json.loads(TEMPLATE.read_text())
    g.update(session="s0_x", layout="gate", time="2026-11-24T20:00", room="lab",
             nearby_metal="none within 1 m")
    for b in g["boards"].values():
        b.update(height_cm=75, antenna_faces="north")
    g["distances_cm"] = {"1-2": 100, "1-3": 100, "2-3": 100}
    g["sniffer"].update(near_node=3, offset_cm=8, height_cm=75, antenna_faces="up")
    g["photos"] = {k: f"{k}.jpg" for k in g["photos"]}
    return g


def test_the_template_is_not_a_record() -> None:
    gaps = geometry.missing(json.loads(TEMPLATE.read_text()))
    assert "layout" in gaps and "distances_cm.1-2" in gaps and "sniffer.offset_cm" in gaps


def test_a_filled_record_is_complete() -> None:
    assert geometry.missing(_filled()) == []


def test_one_empty_height_is_named() -> None:
    g = _filled()
    g["boards"]["2"]["height_cm"] = None
    assert geometry.missing(g) == ["boards.2.height_cm"]
