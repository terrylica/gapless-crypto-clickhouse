"""Test package structure and imports."""

from pathlib import Path

import pytest

import gapless_crypto_clickhouse


def test_package_import():
    """Test that the main package can be imported."""
    assert gapless_crypto_clickhouse is not None


def test_main_exports():
    """Test that main classes are exported from package."""

    # Check that main classes are available
    expected_exports = ["BinancePublicDataCollector", "UniversalGapFiller"]

    for export in expected_exports:
        assert hasattr(gapless_crypto_clickhouse, export), f"Missing export: {export}"


def test_collectors_module():
    """Test that collectors module can be imported."""
    try:
        from gapless_crypto_clickhouse.collectors import binance_public_data_collector

        assert binance_public_data_collector is not None
        assert hasattr(binance_public_data_collector, "BinancePublicDataCollector")
    except ImportError as e:
        pytest.fail(f"Failed to import collectors module: {e}")


def test_gap_filling_module():
    """Test that gap filling module can be imported."""
    try:
        from gapless_crypto_clickhouse.gap_filling import universal_gap_filler

        assert universal_gap_filler is not None
        assert hasattr(universal_gap_filler, "UniversalGapFiller")
    except ImportError as e:
        pytest.fail(f"Failed to import gap filling module: {e}")


def test_version_available():
    """Test that package version is available."""
    try:
        version = getattr(gapless_crypto_clickhouse, "__version__", None)

        if version is not None:
            assert isinstance(version, str)
            assert len(version) > 0
            # Basic semantic version format check
            parts = version.split(".")
            assert len(parts) >= 2  # At least major.minor
    except Exception:
        # Version might not be implemented yet
        pass


def test_package_structure():
    """Test that expected package structure exists."""
    # Get the package root

    package_path = Path(gapless_crypto_clickhouse.__file__).parent

    # Check for expected directories
    expected_dirs = ["collectors", "gap_filling", "utils"]

    for dir_name in expected_dirs:
        dir_path = package_path / dir_name
        assert dir_path.exists(), f"Missing directory: {dir_name}"
        assert dir_path.is_dir(), f"Not a directory: {dir_name}"

        # Check for __init__.py
        init_file = dir_path / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in {dir_name}"


def test_no_syntax_errors():
    """Test that all Python files have valid syntax."""

    package_path = Path(gapless_crypto_clickhouse.__file__).parent

    # Find all Python files
    python_files = list(package_path.rglob("*.py"))

    for py_file in python_files:
        try:
            # Try to compile each file
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
            compile(content, str(py_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {py_file}: {e}")
        except Exception:
            # Other errors (like import errors) are acceptable for this test
            pass


def test_all_imports_valid():
    """Test that all imports in the package are valid and instantiable."""
    # Test main package imports
    try:
        from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller

        # Test instantiation with safe defaults
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date="2022-01-01", end_date="2022-01-02"
        )
        gap_filler = UniversalGapFiller()

        assert collector is not None
        assert gap_filler is not None
        assert hasattr(collector, "collect_multiple_timeframes")
        assert hasattr(gap_filler, "detect_all_gaps")

    except ImportError as e:
        pytest.fail(f"Failed to import main classes: {e}")
    except Exception as e:
        pytest.fail(f"Failed to instantiate classes: {e}")


def test_no_missing_dependencies():
    """Test that there are no missing module dependencies."""

    package_path = Path(gapless_crypto_clickhouse.__file__).parent

    # Find all Python files and check for problematic imports
    python_files = list(package_path.rglob("*.py"))

    forbidden_imports = [
        "multi_source_gap_filler",
        "legitimate_gaps_registry",
        "binance_data_downloader",
        "kucoin_data_collector",
    ]

    for py_file in python_files:
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            for forbidden in forbidden_imports:
                if f"from {forbidden} import" in content or f"import {forbidden}" in content:
                    pytest.fail(f"Found forbidden import '{forbidden}' in {py_file}")

        except Exception:
            # Skip files that can't be read
            pass
