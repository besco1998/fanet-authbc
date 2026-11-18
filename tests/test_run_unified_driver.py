"""ns3/run_unified.py's process runner: a failed ns-3 process is reported with its exit code
and its stderr, never as a bare exit status (2026-11-18: one exit 127 at launch whose cause the
log could not show)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ns3"))
sys.path.insert(0, str(REPO / "src"))

import run_unified  # noqa: E402


def test_a_failure_carries_its_exit_code_and_stderr() -> None:
    with pytest.raises(RuntimeError, match=r"exit 127(.|\n)*cannot open shared object"):
        run_unified.run_checked(["sh", "-c", "echo 'cannot open shared object' >&2; exit 127"],
                                {})


def test_a_clean_run_raises_nothing() -> None:
    run_unified.run_checked(["sh", "-c", "exit 0"], {})
