"""Architecture fitness tests for AD-023 (replaces a dependency-cruiser config,
since the prototype uses Python stdlib only).

Rules
  R1  dashboard/, reporting/, core/ do not import sqlite3 (no storage in domain).
  R2  dashboard/, reporting/, core/ do not import ad023.ingestion (direction:
      domain -> core <- ingestion; only app.py wires implementations).
  R3  Only ingestion/ mentions the sensor_readings table (data ownership).
  R4  core/ does not import dashboard/ or reporting/ (core stays innermost).

Set AD023_SRC=<path to src/backend/ad023> to check another checkout, e.g. the
baseline commit, and print its violations:
    AD023_SRC=/tmp/c1/src/backend/ad023 python -m tests.ad023.test_architecture
"""

import ast
import os
import sys
import unittest
from pathlib import Path

DEFAULT_SRC = Path(__file__).resolve().parents[2] / "src" / "backend" / "ad023"
DOMAIN = ("dashboard", "reporting", "core")


def _src():
    return Path(os.environ.get("AD023_SRC", DEFAULT_SRC))


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def violations(src=None):
    src = Path(src or _src())
    found = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src)
        package = rel.parts[0] if len(rel.parts) > 1 else ""
        text = path.read_text(encoding="utf-8")
        imports = set(_imports(ast.parse(text)))
        if package in DOMAIN:
            if "sqlite3" in imports:
                found.append(f"R1 {rel}: imports sqlite3")
            if any(m == "ad023.ingestion" or m.startswith("ad023.ingestion.") for m in imports):
                found.append(f"R2 {rel}: imports ad023.ingestion")
        if package != "ingestion" and "sensor_readings" in text:
            found.append(f"R3 {rel}: references sensor_readings")
        if package == "core" and any(m.startswith(("ad023.dashboard", "ad023.reporting"))
                                     for m in imports):
            found.append(f"R4 {rel}: core depends on an outer module")
    return found


class ArchitectureRules(unittest.TestCase):
    def test_source_tree_exists(self):
        self.assertTrue(_src().is_dir(), _src())

    def test_dependency_and_ownership_rules(self):
        self.assertEqual(violations(), [])


if __name__ == "__main__":
    result = violations()
    print(f"src: {_src()}")
    print("\n".join(result) if result else "no violations")
    sys.exit(1 if result else 0)
