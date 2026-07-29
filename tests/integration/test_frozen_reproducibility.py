"""Frozen-data staleness gate (the fix for the freezing shortage — docs/DECISIONS.md).

Freezing measured/derived CSVs buys reproducibility but risks SILENT STALENESS: an upstream
decision or code change can move a derived number while the committed frozen artifact keeps the old
one (exactly what produced audit finding F1 — E4 kept BLS=48 B after the 96 B decision). This gate
re-derives every DETERMINISTIC frozen artifact from the CURRENT code + configs + frozen measured
inputs and asserts it is byte-identical (data rows) to the committed CSV. Any drift ⇒ a loud CI
failure that forces a deliberate re-freeze — staleness can no longer be committed unnoticed.

Only the deterministic *derived* layer is checked. The genuinely MEASURED inputs — `p1_crypto`
(timings) and `ns3_matrix` (simulation) — are non-deterministic fixtures and are compared here only
as the frozen inputs the derived layer reads, never re-measured. Provenance headers (`# key=value`,
machine-specific) are ignored; only the scientific data rows are compared.
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from authbc.bench import framesizes, micro
from authbc.bench.experiments import (
    load_config,
    run_capacity,
    run_e1,
    run_e2,
    run_e3,
    run_e5,
    run_lora,
    run_lora_codesign,
    run_operating_region,
)

# Slow (re-runs the encode-heavy generators): deselected from the fast local `make test`, run in
# CI + `make all` via `make verify-frozen` (-m frozen). This is the frozen-staleness gate.
pytestmark = pytest.mark.frozen

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "results" / "raw"


def _load_script(rel: str) -> ModuleType:
    """Import a repo script that is not an installed package (experiments/, analysis/)."""
    path = REPO / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_run_e4 = _load_script("experiments/e4/run_e4.py")


def _frozen_body(name: str) -> tuple[list[str], list[dict[str, str]]]:
    """Committed CSV data rows (drop the `# key=value` provenance header)."""
    text = [ln for ln in (RAW / name).read_text().splitlines() if not ln.startswith("#")]
    reader = csv.DictReader(text)
    return list(reader.fieldnames or []), list(reader)


def _render(rows: list[dict], fieldnames: list[str]) -> list[dict[str, str]]:
    """Render fresh runner rows to the exact string form DictWriter(restval='') would emit."""
    return [{f: str(r.get(f, "")) for f in fieldnames} for r in rows]


def _assert_reproduces(name: str, fresh_rows: list[dict]) -> None:
    fieldnames, frozen = _frozen_body(name)
    rendered = _render(fresh_rows, fieldnames)
    assert len(rendered) == len(frozen), (
        f"{name}: row count drift — fresh {len(rendered)} vs frozen {len(frozen)}. "
        f"Re-run its generator and re-freeze (docs/DECISIONS.md)."
    )
    for i, (a, b) in enumerate(zip(rendered, frozen, strict=True)):
        assert a == b, (
            f"{name}: row {i} drifted from the frozen CSV — a decision/code/config change moved a "
            f"derived number without a re-freeze (staleness, F1-class).\n  fresh : {a}\n"
            f"  frozen: {b}\nIf intended, re-run `make exp-*` / figures and re-freeze."
        )


# --- deterministic derived artifacts (pure runners over frozen inputs) --------------------
_CASES = {
    "e1_dominance.csv": lambda: run_e1(load_config("e1")),
    "e2_batching.csv": lambda: run_e2(load_config("e2")),
    "e3_loss.csv": lambda: run_e3(load_config("e3")),
    "e5_codesign.csv": lambda: run_e5(load_config("e5")),
    "framesizes.csv": lambda: framesizes.build_rows(framesizes.measured_sizes()),
    "p1_sizes.csv": lambda: micro.measure_sizes(1, 10000),
    # must read the SAME source main() does (D8: ARM timings), or the gate reports false drift
    "e4_crossover.csv": lambda: _run_e4.crossover_rows(
        _run_e4.load_crypto(_run_e4.CRYPTO_CSV if _run_e4.CRYPTO_CSV.exists()
                            else RAW / "p1_crypto.csv")),
    "e4_bytes.csv": lambda: _run_e4.bytes_rows(_run_e4.load_sizes(RAW / "p1_sizes.csv")),
    # Added 2026-07-28 (pre-P8 audit): these three were UNGATED, which is precisely the F1 hole
    # the gate exists to close — three runnable experiments producing frozen artifacts that
    # nothing re-derived. The LoRa pair in particular moved on the F5 decision the same day.
    "lora_eu868.csv": lambda: run_lora(load_config("lora")),
    "lora_codesign.csv": lambda: run_lora_codesign(load_config("lora")),
    "capacity_envelope.csv": lambda: run_capacity(load_config("capacity")),
    "operating_region.csv": lambda: run_operating_region(load_config("operating-region")),
}


@pytest.mark.parametrize("name", sorted(_CASES))
def test_frozen_artifact_reproduces(name: str) -> None:
    """Re-deriving the artifact from current code must byte-match the committed data rows."""
    _assert_reproduces(name, _CASES[name]())


# --- NS-3-derived contention (from the frozen simulation matrix) --------------------------
def test_ns3_contention_reproduces(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ns3_contention.csv must re-derive from the frozen ns3_matrix via the real analytic path."""
    fns = _load_script("analysis/figures_ns3.py")
    rows, _ = fns.load_matrix()                 # reads the frozen matrix from the real RAW
    summary = fns.summarize(rows)
    monkeypatch.setattr(fns, "RAW", tmp_path)   # redirect the write so nothing frozen is clobbered
    fns.write_contention(summary)
    assert (tmp_path / "ns3_contention.csv").read_text() == (RAW / "ns3_contention.csv").read_text()


# --- measured inputs exist and are well-formed (frozen fixtures, never re-measured) -------
def test_measured_inputs_present_and_shaped() -> None:
    """p1_crypto / ns3_matrix are immutable measured fixtures the derived layer depends on."""
    _, crypto = _frozen_body("p1_crypto.csv")
    schemes = {r["scheme"] for r in crypto}
    assert {"ed25519", "ecdsa_p256", "bls"} <= schemes
    assert any(r["op"] == "verify" for r in crypto)
    matrix = [ln for ln in (RAW / "ns3_matrix.csv").read_text().splitlines()
              if not ln.startswith("#")]
    assert len(matrix) > 1 and matrix[0].startswith("N,mode")
    # ns3_delay is the same class of artifact: a simulation measurement, not a derived table, so
    # it is shape-checked here rather than re-derived above (D3, docs/02).
    delay = [ln for ln in (RAW / "ns3_delay.csv").read_text().splitlines()
             if not ln.startswith("#")]
    assert len(delay) > 1 and delay[0].startswith("n_nodes,frames_per_s")
