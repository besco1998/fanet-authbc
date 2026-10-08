"""Every third-party package the code imports is declared in `pyproject.toml` (docs/03 §2).

⚠️ Added 2026-10-08, after the frozen gate passed on the author's machine and failed on a clean
install. A gate test re-derived an artifact from a committed flight log with `pyulog`, which had
been installed by hand for an earlier measurement and never declared. `make all` cannot see that
kind of defect from inside the environment that has it, so this test reads the declarations and
the import statements instead of trying an import.

What is scanned: `src/`, `analysis/`, `tests/` and the drivers directly under `ns3/`. What is not:
`hw/`, whose scripts run on the boards with the packages `hw/SETUP.md` installs there, and the
vendored ns-3 trees.
"""
from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCANNED = ("src", "analysis", "tests")
# A distribution whose import name is not its own name.
IMPORT_NAME = {"pyyaml": "yaml"}
# Imported by one tool that the test suite never runs, inside the function that needs it. Each
# entry names the only file allowed to import it, and why it is not a dependency.
OUTSIDE = {
    "pymavlink": ("analysis/px4_sitl_flight.py",
                  "flies the simulated mission; run with PX4's own Python environment"),
    "pypdf": ("analysis/direction_c_survey.py",
              "a one-off literature sweep over PDFs that are not in the repository"),
}


def _declared() -> set[str]:
    project = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]
    requirements = project["dependencies"] + project["optional-dependencies"]["dev"]
    names = {re.split(r"[<>=!~ \[;]", r, maxsplit=1)[0].strip().lower() for r in requirements}
    return {IMPORT_NAME.get(n, n).replace("-", "_") for n in names}


def _files() -> list[Path]:
    out = [p for d in SCANNED for p in (REPO / d).rglob("*.py")]
    return out + sorted((REPO / "ns3").glob("*.py"))


def _local() -> set[str]:
    """Names that resolve inside the repository: the package and every script and test module."""
    return {"authbc", "tests"} | {p.stem for p in _files()} | {p.parent.name for p in _files()}


def _imports(path: Path) -> list[tuple[str, bool]]:
    """(top-level package, imported at module level?) for every absolute import in `path`."""
    tree = ast.parse(path.read_text())
    at_module_level = {id(n) for n in tree.body}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        out += [(n.split(".")[0], id(node) in at_module_level) for n in names]
    return out


def _third_party() -> dict[str, list[tuple[str, bool]]]:
    """package -> [(file, at module level?)], standard library and local modules left out."""
    local, found = _local(), {}
    for path in _files():
        for name, top in _imports(path):
            if name not in sys.stdlib_module_names and name not in local:
                found.setdefault(name, []).append((str(path.relative_to(REPO)), top))
    return found


def test_every_imported_package_is_declared() -> None:
    undeclared = {name: sorted({f for f, _ in uses})
                  for name, uses in _third_party().items()
                  if name not in _declared() and name not in OUTSIDE}
    assert not undeclared, (
        "imported but not in pyproject.toml — a clean install (and CI) will not have it: "
        f"{undeclared}")


def test_the_flight_log_reader_is_pinned() -> None:
    """The frozen gate re-derives `px4_sitl_*.csv` from `flight.ulg`; that needs this reader."""
    dev = tomllib.loads((REPO / "pyproject.toml").read_text())["project"][
        "optional-dependencies"]["dev"]
    assert [r for r in dev if r.startswith("pyulog==")], "pyulog must be pinned exactly"


def test_a_package_kept_outside_is_used_only_where_stated_and_only_on_demand() -> None:
    found = _third_party()
    for name, (only_file, _why) in OUTSIDE.items():
        uses = found.get(name, [])
        assert uses, f"{name} is no longer imported anywhere: remove it from OUTSIDE"
        assert {f for f, _ in uses} == {only_file}, (name, uses)
        assert not any(top for _, top in uses), (
            f"{name} is imported at module level in {only_file}: importing that file would "
            "then need a package that is not installed")


def test_nothing_is_both_declared_and_kept_outside() -> None:
    assert not _declared() & set(OUTSIDE)
