"""P0 skeleton smoke test — every stub subpackage must import cleanly.

Guards the scaffold: if a package is missing, misnamed, or has an import-time error, CI
fails here rather than deep inside a later phase. Real per-module unit tests replace/augment
this from P1 onward (docs/03 §3–4).
"""

import importlib

import pytest

MODULES = [
    "authbc",
    "authbc.encodings",
    "authbc.crypto",
    "authbc.ledger",
    "authbc.placement",
    "authbc.channel",
    "authbc.models",
    "authbc.bench",
]


@pytest.mark.parametrize("name", MODULES)
def test_stub_module_imports(name: str) -> None:
    mod = importlib.import_module(name)
    assert mod is not None


def test_package_version_present() -> None:
    import authbc

    assert authbc.__version__ == "0.0.0"
