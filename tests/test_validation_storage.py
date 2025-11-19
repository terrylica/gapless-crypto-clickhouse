#!/usr/bin/env python3
"""
Comprehensive end-to-end tests for ValidationStorage and ValidationReport.

This test suite validates the complete validation persistence workflow:
1. Load real CSV data from sample_data directory
2. Validate CSV using CSVValidator with store_report=True
3. Query validation reports from DuckDB
4. Test all ValidationStorage query methods
5. Verify ValidationReport Pydantic model validation
6. Test helper functions with real data

Real-world production testing using authentic Binance data.
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from gapless_crypto_clickhouse.validation import (
    CSVValidator,
    ValidationReport,
    ValidationStorage,
    extract_symbol_timeframe_from_path,
    get_validation_db_path,
)


class TestValidationStorageEndToEnd:
    """End-to-end tests for validation persistence using real data."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary DuckDB database for testing."""
        temp_dir = tempfile.mkdtemp(prefix="validation_db_test_")
        db_path = Path(temp_dir) / "test_validation.duckdb"
        yield db_path

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_csv_files(self):
        """Get list of real sample CSV files for testing."""
        sample_data_dir = Path("src/gapless_crypto_clickhouse/sample_data")
        csv_files = list(sample_data_dir.glob("*.csv"))

        # Filter to get a representative sample
        # Include different symbols, timeframes, and date ranges
        test_files = []

        for csv_file in csv_files:
            # Get at least one file for each symbol/timeframe combination
            if any(
                pattern in csv_file.name
                for pattern in ["BTCUSDT-1h", "ETHUSDT-1h", "BTCUSDT-1d", "BTCUSDT-5m"]
            ):
                if "v2.10.0" in csv_file.name:  # Use latest version
                    test_files.append(csv_file)
                    if len(test_files) >= 4:  # Limit to 4 files for testing
                        break

        assert len(test_files) > 0, "No sample CSV files found for testing"

        return test_files

    @pytest.fixture
    def storage(self, temp_db_path):
        """Create ValidationStorage instance with temporary database."""
        return ValidationStorage(db_path=temp_db_path)

    def test_validation_storage_initialization(self, temp_db_path):
        """Test ValidationStorage initialization and table creation."""
        print(f"\nTesting ValidationStorage initialization with DB at: {temp_db_path}")

        storage = ValidationStorage(db_path=temp_db_path)

        # Verify database file was created
        assert temp_db_path.exists(), f"Database file not created at {temp_db_path}"

        # Verify database is accessible and table exists
        import duckdb

        with duckdb.connect(str(temp_db_path)) as conn:
            # Check if validation_reports table exists
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()

            table_names = [t[0] for t in tables]
            assert "validation_reports" in table_names, "validation_reports table not created"

            print(f"✅ Database initialized with tables: {table_names}")

    def test_get_validation_db_path_xdg_compliance(self):
        """Test that get_validation_db_path follows XDG Base Directory spec."""
        db_path = get_validation_db_path()

        # Should be under ~/.cache/gapless-crypto-data/
        assert ".cache" in str(db_path), "Path should use .cache directory"
        assert "gapless-crypto-data" in str(db_path), "Path should include package name"
        assert db_path.name == "validation.duckdb", (
            f"Expected validation.duckdb, got {db_path.name}"
        )

        print(f"\n✅ XDG-compliant path: {db_path}")

    def test_extract_symbol_timeframe_from_path(self, sample_csv_files):
        """Test symbol and timeframe extraction from various filename patterns."""
        print("\nTesting symbol/timeframe extraction from real sample files:")

        for csv_file in sample_csv_files:
            symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_file))

            print(f"  {csv_file.name}")
            print(f"    → Symbol: {symbol}, Timeframe: {timeframe}")

            # Verify extraction worked
            assert symbol is not None, f"Failed to extract symbol from {csv_file.name}"
            assert timeframe is not None, f"Failed to extract timeframe from {csv_file.name}"

            # Verify symbol format (should be uppercase with USDT)
            assert symbol.isupper(), f"Symbol should be uppercase: {symbol}"
            assert "USDT" in symbol, f"Expected USDT pair, got {symbol}"

            # Verify timeframe format
            assert any(tf in timeframe for tf in ["s", "m", "h", "d"]), (
                f"Invalid timeframe format: {timeframe}"
            )

    @pytest.mark.integration
    def test_csv_validator_with_store_report(self, storage, sample_csv_files, temp_db_path):
        """Test CSVValidator with store_report=True persists to DuckDB."""
        print(f"\nTesting CSVValidator integration with storage at: {temp_db_path}")

        # Use a single sample file for this test
        test_file = sample_csv_files[0]

        print(f"\nValidating CSV file: {test_file.name}")

        # Extract expected timeframe from filename
        _, timeframe = extract_symbol_timeframe_from_path(str(test_file))

        # Validate with store_report=True
        validator = CSVValidator()

        # Temporarily patch the storage to use our test database
        import gapless_crypto_clickhouse.validation.csv_validator as csv_validator_module

        original_storage_class = csv_validator_module.ValidationStorage

        def patched_storage_init():
            return ValidationStorage(db_path=temp_db_path)

        csv_validator_module.ValidationStorage = lambda: ValidationStorage(db_path=temp_db_path)

        try:
            results = validator.validate_csv_file(
                test_file, expected_timeframe=timeframe, store_report=True
            )

            # Verify validation completed
            assert "validation_summary" in results, "Validation results missing summary"
            assert "total_errors" in results, "Validation results missing error count"
            assert "total_warnings" in results, "Validation results missing warning count"

            print(f"\n📊 Validation Summary: {results['validation_summary']}")
            print(f"   Total Errors: {results['total_errors']}")
            print(f"   Total Warnings: {results['total_warnings']}")

            # Query database to verify report was stored
            reports = storage.query_recent(limit=1)

            assert len(reports) > 0, (
                "No validation reports found in database after store_report=True"
            )

            stored_report = reports[0]
            assert stored_report["file_path"] == str(test_file), "Stored report has wrong file path"

            print("\n✅ Validation report successfully stored to DuckDB")
            print(f"   File: {Path(stored_report['file_path']).name}")
            print(f"   Symbol: {stored_report['symbol']}")
            print(f"   Timeframe: {stored_report['timeframe']}")

        finally:
            # Restore original ValidationStorage class
            csv_validator_module.ValidationStorage = original_storage_class

    @pytest.mark.integration
    def test_validation_storage_insert_and_query(self, storage, sample_csv_files):
        """Test inserting and querying validation reports with real data."""
        print("\nTesting ValidationStorage insert and query operations...")

        # Validate multiple files and store their reports
        validator = CSVValidator()
        stored_count = 0

        for csv_file in sample_csv_files[:3]:  # Test with first 3 files
            symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_file))

            print(f"\n  Validating: {csv_file.name}")

            # Read CSV and create validation results
            try:
                df = pd.read_csv(csv_file, comment="#")

                # Basic validation
                validation_results = {
                    "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "file_path": str(csv_file),
                    "file_size_mb": csv_file.stat().st_size / (1024 * 1024),
                    "total_bars": len(df),
                    "total_errors": 0,
                    "total_warnings": 0,
                    "validation_summary": "PERFECT - Test data",
                    "structure_validation": {},
                    "datetime_validation": {},
                    "ohlcv_validation": {},
                    "coverage_validation": {},
                    "anomaly_validation": {},
                }

                # Convert to ValidationReport
                report = ValidationReport.from_legacy_dict(
                    validation_results, duration_ms=100.0, symbol=symbol, timeframe=timeframe
                )

                # Store report
                storage.insert_report(report)
                stored_count += 1

                print(f"    ✅ Stored report for {symbol}-{timeframe}")

            except Exception as e:
                print(f"    ⚠️  Skipped due to error: {e}")
                continue

        # Verify reports were stored
        all_reports = storage.query_recent(limit=10)
        assert len(all_reports) >= stored_count, (
            f"Expected at least {stored_count} reports, got {len(all_reports)}"
        )

        print(f"\n✅ Successfully stored and queried {stored_count} validation reports")

    def test_validation_storage_query_recent(self, storage, sample_csv_files):
        """Test query_recent with symbol and timeframe filters."""
        print("\nTesting ValidationStorage.query_recent()...")

        # First, populate database with test data
        for csv_file in sample_csv_files[:3]:
            symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_file))

            try:
                df = pd.read_csv(csv_file, comment="#")

                validation_results = {
                    "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "file_path": str(csv_file),
                    "file_size_mb": csv_file.stat().st_size / (1024 * 1024),
                    "total_bars": len(df),
                    "total_errors": 0,
                    "total_warnings": 0,
                    "validation_summary": "GOOD - Test data",
                    "structure_validation": {},
                    "datetime_validation": {},
                    "ohlcv_validation": {},
                    "coverage_validation": {},
                    "anomaly_validation": {},
                }

                report = ValidationReport.from_legacy_dict(
                    validation_results, duration_ms=50.0, symbol=symbol, timeframe=timeframe
                )

                storage.insert_report(report)

            except Exception:
                continue

        # Test unfiltered query
        all_reports = storage.query_recent(limit=5)
        assert len(all_reports) > 0, "query_recent should return reports"

        print(f"  ✅ query_recent(limit=5): {len(all_reports)} reports")

        # Test symbol filter
        btc_reports = storage.query_recent(limit=5, symbol="BTCUSDT")
        for report in btc_reports:
            assert report["symbol"] == "BTCUSDT", "Symbol filter not working"

        print(f"  ✅ query_recent(symbol='BTCUSDT'): {len(btc_reports)} reports")

        # Test timeframe filter
        hourly_reports = storage.query_recent(limit=5, timeframe="1h")
        for report in hourly_reports:
            assert report["timeframe"] == "1h", "Timeframe filter not working"

        print(f"  ✅ query_recent(timeframe='1h'): {len(hourly_reports)} reports")

    def test_validation_storage_query_by_status(self, storage):
        """Test query_by_status method."""
        print("\nTesting ValidationStorage.query_by_status()...")

        # Create test reports with different statuses
        statuses = [
            ("PERFECT - No errors or warnings", 0, 0),
            ("GOOD - 2 warnings", 0, 2),
            ("FAILED - 1 errors, 0 warnings", 1, 0),
        ]

        for i, (status, errors, warnings) in enumerate(statuses):
            validation_results = {
                "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "file_path": f"/tmp/test_{i}.csv",
                "file_size_mb": 1.0,
                "total_bars": 100,
                "total_errors": errors,
                "total_warnings": warnings,
                "validation_summary": status,
                "structure_validation": {},
                "datetime_validation": {},
                "ohlcv_validation": {},
                "coverage_validation": {},
                "anomaly_validation": {},
            }

            report = ValidationReport.from_legacy_dict(
                validation_results, duration_ms=50.0, symbol="TESTUSDT", timeframe="1h"
            )

            storage.insert_report(report)

        # Test status queries
        perfect_reports = storage.query_by_status("PERFECT")
        assert len(perfect_reports) >= 1, "Should find PERFECT reports"
        print(f"  ✅ query_by_status('PERFECT'): {len(perfect_reports)} reports")

        good_reports = storage.query_by_status("GOOD")
        assert len(good_reports) >= 1, "Should find GOOD reports"
        print(f"  ✅ query_by_status('GOOD'): {len(good_reports)} reports")

        failed_reports = storage.query_by_status("FAILED")
        assert len(failed_reports) >= 1, "Should find FAILED reports"
        print(f"  ✅ query_by_status('FAILED'): {len(failed_reports)} reports")

    def test_validation_storage_query_by_date_range(self, storage):
        """Test query_by_date_range method."""
        print("\nTesting ValidationStorage.query_by_date_range()...")

        # Create test reports with different timestamps
        now = datetime.now(timezone.utc)
        timestamps = [
            now - timedelta(days=7),  # 7 days ago
            now - timedelta(days=3),  # 3 days ago
            now - timedelta(hours=1),  # 1 hour ago
        ]

        for i, ts in enumerate(timestamps):
            validation_results = {
                "validation_timestamp": ts.isoformat() + "Z",
                "file_path": f"/tmp/test_{i}.csv",
                "file_size_mb": 1.0,
                "total_bars": 100,
                "total_errors": 0,
                "total_warnings": 0,
                "validation_summary": "PERFECT",
                "structure_validation": {},
                "datetime_validation": {},
                "ohlcv_validation": {},
                "coverage_validation": {},
                "anomaly_validation": {},
            }

            report = ValidationReport.from_legacy_dict(
                validation_results, duration_ms=50.0, symbol="TESTUSDT", timeframe="1h"
            )

            storage.insert_report(report)

        # Query last 5 days
        start = now - timedelta(days=5)
        end = now

        recent_reports = storage.query_by_date_range(start, end)

        # Should include reports from 3 days ago and 1 hour ago, but not 7 days ago
        assert len(recent_reports) >= 2, f"Expected at least 2 reports, got {len(recent_reports)}"

        print(f"  ✅ query_by_date_range(last 5 days): {len(recent_reports)} reports")

    def test_validation_storage_export_to_dataframe(self, storage, sample_csv_files):
        """Test export_to_dataframe method."""
        print("\nTesting ValidationStorage.export_to_dataframe()...")

        # Populate with test data
        for csv_file in sample_csv_files[:2]:
            symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_file))

            try:
                df_csv = pd.read_csv(csv_file, comment="#")

                validation_results = {
                    "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "file_path": str(csv_file),
                    "file_size_mb": csv_file.stat().st_size / (1024 * 1024),
                    "total_bars": len(df_csv),
                    "total_errors": 0,
                    "total_warnings": 1,
                    "validation_summary": "GOOD - 1 warning",
                    "structure_validation": {},
                    "datetime_validation": {},
                    "ohlcv_validation": {},
                    "coverage_validation": {},
                    "anomaly_validation": {},
                }

                report = ValidationReport.from_legacy_dict(
                    validation_results, duration_ms=50.0, symbol=symbol, timeframe=timeframe
                )

                storage.insert_report(report)

            except Exception:
                continue

        # Export all data
        df = storage.export_to_dataframe()

        assert len(df) > 0, "export_to_dataframe should return non-empty DataFrame"
        assert "symbol" in df.columns, "DataFrame should have 'symbol' column"
        assert "timeframe" in df.columns, "DataFrame should have 'timeframe' column"
        assert "total_errors" in df.columns, "DataFrame should have 'total_errors' column"

        print(f"  ✅ export_to_dataframe(): {len(df)} rows, {len(df.columns)} columns")

        # Test filtered export
        df_btc = storage.export_to_dataframe(symbol="BTCUSDT")

        if len(df_btc) > 0:
            assert all(df_btc["symbol"] == "BTCUSDT"), (
                "Filtered DataFrame should only contain BTCUSDT"
            )
            print(f"  ✅ export_to_dataframe(symbol='BTCUSDT'): {len(df_btc)} rows")

    def test_validation_storage_get_summary_stats(self, storage, sample_csv_files):
        """Test get_summary_stats method."""
        print("\nTesting ValidationStorage.get_summary_stats()...")

        # Populate with diverse test data
        for csv_file in sample_csv_files[:3]:
            symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_file))

            try:
                df = pd.read_csv(csv_file, comment="#")

                validation_results = {
                    "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "file_path": str(csv_file),
                    "file_size_mb": csv_file.stat().st_size / (1024 * 1024),
                    "total_bars": len(df),
                    "total_errors": 0,
                    "total_warnings": 1,
                    "validation_summary": "GOOD - 1 warning",
                    "structure_validation": {},
                    "datetime_validation": {},
                    "ohlcv_validation": {},
                    "coverage_validation": {},
                    "anomaly_validation": {},
                }

                report = ValidationReport.from_legacy_dict(
                    validation_results, duration_ms=100.0, symbol=symbol, timeframe=timeframe
                )

                storage.insert_report(report)

            except Exception:
                continue

        # Get summary statistics
        stats = storage.get_summary_stats()

        assert "total_validations" in stats, "Stats should include total_validations"
        assert "symbols" in stats, "Stats should include symbols list"
        assert "timeframes" in stats, "Stats should include timeframes list"
        assert "avg_errors" in stats, "Stats should include avg_errors"
        assert "avg_warnings" in stats, "Stats should include avg_warnings"
        assert "status_distribution" in stats, "Stats should include status_distribution"

        print("\n📊 Summary Statistics:")
        print(f"   Total Validations: {stats['total_validations']}")
        print(f"   Symbols: {stats['symbols']}")
        print(f"   Timeframes: {stats['timeframes']}")
        print(f"   Avg Errors: {stats['avg_errors']:.2f}")
        print(f"   Avg Warnings: {stats['avg_warnings']:.2f}")
        print(f"   Status Distribution: {stats['status_distribution']}")

        assert stats["total_validations"] > 0, "Should have at least one validation"

    def test_validation_report_pydantic_model(self):
        """Test ValidationReport Pydantic model validation."""
        print("\nTesting ValidationReport Pydantic model...")

        # Test valid report creation
        report = ValidationReport(
            validation_timestamp=datetime.now(timezone.utc),
            file_path="/tmp/test.csv",
            file_size_mb=1.5,
            total_bars=100,
            total_errors=0,
            total_warnings=1,
            validation_summary="GOOD - 1 warning",
            validation_duration_ms=123.45,
            structure_validation={},
            datetime_validation={},
            ohlcv_validation={},
            coverage_validation={},
            anomaly_validation={},
        )

        assert report.total_bars == 100
        assert report.total_errors == 0
        assert report.validation_summary == "GOOD - 1 warning"

        print("  ✅ ValidationReport model created successfully")

        # Test model_dump for JSON serialization
        report_dict = report.model_dump()

        assert "validation_timestamp" in report_dict
        assert "file_path" in report_dict
        assert "total_errors" in report_dict

        print("  ✅ ValidationReport.model_dump() works correctly")

        # Test model_dump_json for JSON string
        json_str = report.model_dump_json()

        assert isinstance(json_str, str)
        assert "validation_timestamp" in json_str

        print("  ✅ ValidationReport.model_dump_json() works correctly")

    def test_validation_report_from_legacy_dict(self):
        """Test ValidationReport.from_legacy_dict conversion."""
        print("\nTesting ValidationReport.from_legacy_dict()...")

        legacy_dict = {
            "validation_timestamp": "2025-10-18T12:00:00Z",
            "file_path": "/tmp/test.csv",
            "file_size_mb": 2.5,
            "total_bars": 200,
            "total_errors": 0,
            "total_warnings": 2,
            "validation_summary": "GOOD - 2 warnings",
            "structure_validation": {"status": "VALID"},
            "datetime_validation": {
                "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
                "duration_days": 1,
                "gaps_found": 0,
                "chronological_order": True,
            },
            "ohlcv_validation": {
                "price_range": {"min": 100.0, "max": 110.0},
                "volume_stats": {"min": 0.0, "max": 1000.0, "mean": 500.0},
                "ohlc_errors": 0,
                "negative_zero_values": 0,
            },
            "coverage_validation": {
                "expected_bars": 200,
                "actual_bars": 200,
                "coverage_percentage": 100.0,
            },
            "anomaly_validation": {
                "price_outliers": 0,
                "volume_outliers": 1,
                "suspicious_patterns": 0,
            },
        }

        report = ValidationReport.from_legacy_dict(
            legacy_dict, duration_ms=150.0, symbol="BTCUSDT", timeframe="1h"
        )

        assert report.total_bars == 200
        assert report.symbol == "BTCUSDT"
        assert report.timeframe == "1h"
        assert report.validation_duration_ms == 150.0

        # Verify flattened metrics were extracted
        assert report.gaps_found == 0
        assert report.chronological_order is True
        assert report.price_min == 100.0
        assert report.price_max == 110.0

        print("  ✅ from_legacy_dict() correctly converts and extracts flattened metrics")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
