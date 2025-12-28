"""Test version consistency across all sources.

ADR: 2025-12-27-importlib-metadata-version-management

Validates that __version__ (read via importlib.metadata) matches the versions
defined in pyproject.toml and package.json.
"""

import json
import tomllib
from pathlib import Path

import gapless_crypto_clickhouse


def test_version_matches_pyproject():
    """Ensure __version__ matches pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    pyproject_version = pyproject["project"]["version"]
    package_version = gapless_crypto_clickhouse.__version__

    # Skip check for development installs
    if package_version == "0.0.0+dev":
        return

    assert package_version == pyproject_version, (
        f"__version__ ({package_version}) != pyproject.toml ({pyproject_version})"
    )


def test_version_matches_package_json():
    """Ensure __version__ matches package.json."""
    package_json_path = Path(__file__).parent.parent / "package.json"
    with open(package_json_path) as f:
        package_json = json.load(f)

    package_json_version = package_json["version"]
    package_version = gapless_crypto_clickhouse.__version__

    # Skip check for development installs
    if package_version == "0.0.0+dev":
        return

    assert package_version == package_json_version, (
        f"__version__ ({package_version}) != package.json ({package_json_version})"
    )
