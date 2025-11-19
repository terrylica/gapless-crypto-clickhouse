"""Test Atomic File Operations functionality."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from gapless_crypto_clickhouse.gap_filling.safe_file_operations import (
    AtomicCSVOperations,
    SafeCSVMerger,
)


class TestAtomicCSVOperations:
    """Test suite for AtomicCSVOperations."""

    def test_init(self):
        """Test AtomicCSVOperations initialization."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
            csv_path = Path(temp_file.name)
            atomic_ops = AtomicCSVOperations(csv_path)

            assert atomic_ops.csv_path == csv_path
            assert atomic_ops.backup_path is None
            assert atomic_ops.temp_path is None

            # Cleanup
            csv_path.unlink()

    def test_create_backup_success(self):
        """Test successful backup creation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
            # Create a test CSV file
            temp_file.write("date,open,high,low,close,volume\n")
            temp_file.write("2024-01-01 00:00:00,100,105,95,102,1000\n")
            temp_file.flush()

            csv_path = Path(temp_file.name)
            atomic_ops = AtomicCSVOperations(csv_path)

            # Create backup
            backup_path = atomic_ops.create_backup()

            assert backup_path.exists()
            assert backup_path.name.startswith(csv_path.stem + ".backup_")
            assert backup_path.suffix == csv_path.suffix
            assert atomic_ops.backup_path == backup_path

            # Verify backup content matches original
            with open(csv_path, "r") as original, open(backup_path, "r") as backup:
                assert original.read() == backup.read()

            # Cleanup
            csv_path.unlink()
            backup_path.unlink()

    def test_create_backup_file_not_found(self):
        """Test backup creation with non-existent file."""
        non_existent_path = Path("/tmp/non_existent_file.csv")
        atomic_ops = AtomicCSVOperations(non_existent_path)

        with pytest.raises(FileNotFoundError):
            atomic_ops.create_backup()

    def test_read_header_comments_with_headers(self):
        """Test reading header comments from CSV with comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
            # Write CSV with header comments
            temp_file.write("# Binance Spot Market Data v1.0.0\n")
            temp_file.write("# Generated: 2025-01-01T00:00:00Z\n")
            temp_file.write("# Source: Binance Public Data Repository\n")
            temp_file.write("date,open,high,low,close,volume\n")
            temp_file.write("2024-01-01 00:00:00,100,105,95,102,1000\n")
            temp_file.flush()

            csv_path = Path(temp_file.name)
            atomic_ops = AtomicCSVOperations(csv_path)

            headers = atomic_ops.read_header_comments()

            assert len(headers) == 3
            assert headers[0] == "# Binance Spot Market Data v1.0.0"
            assert headers[1] == "# Generated: 2025-01-01T00:00:00Z"
            assert headers[2] == "# Source: Binance Public Data Repository"

            # Cleanup
            csv_path.unlink()

    def test_read_header_comments_no_headers(self):
        """Test reading header comments from CSV without comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
            # Write CSV without header comments
            temp_file.write("date,open,high,low,close,volume\n")
            temp_file.write("2024-01-01 00:00:00,100,105,95,102,1000\n")
            temp_file.flush()

            csv_path = Path(temp_file.name)
            atomic_ops = AtomicCSVOperations(csv_path)

            headers = atomic_ops.read_header_comments()

            assert len(headers) == 0

            # Cleanup
            csv_path.unlink()

    def test_read_header_comments_file_not_found(self):
        """Test reading header comments from non-existent file."""
        non_existent_path = Path("/tmp/non_existent_file.csv")
        atomic_ops = AtomicCSVOperations(non_existent_path)

        headers = atomic_ops.read_header_comments()

        assert headers == []

    def test_validate_dataframe_valid(self):
        """Test DataFrame validation with valid data."""
        valid_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="1h"),
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [95.0, 96.0, 97.0],
                "close": [102.0, 103.0, 104.0],
                "volume": [1000.0, 1100.0, 1200.0],
            }
        )

        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))
        is_valid, message = atomic_ops.validate_dataframe(valid_df)

        assert is_valid is True
        assert message == "Validation passed"

    def test_validate_dataframe_empty(self):
        """Test DataFrame validation with empty DataFrame."""
        empty_df = pd.DataFrame()

        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))
        is_valid, message = atomic_ops.validate_dataframe(empty_df)

        assert is_valid is False
        assert "empty" in message.lower()

    def test_validate_dataframe_missing_columns(self):
        """Test DataFrame validation with missing required columns."""
        incomplete_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="1h"),
                "price": [100.0, 101.0, 102.0],  # Missing OHLCV columns
            }
        )

        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))
        is_valid, message = atomic_ops.validate_dataframe(incomplete_df)

        assert is_valid is False
        assert "Missing required columns" in message

    def test_validate_dataframe_duplicate_timestamps(self):
        """Test DataFrame validation with duplicate timestamps."""
        duplicate_df = pd.DataFrame(
            {
                "date": ["2024-01-01 00:00:00", "2024-01-01 00:00:00", "2024-01-01 02:00:00"],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [95.0, 96.0, 97.0],
                "close": [102.0, 103.0, 104.0],
                "volume": [1000.0, 1100.0, 1200.0],
            }
        )

        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))
        is_valid, message = atomic_ops.validate_dataframe(duplicate_df)

        assert is_valid is False
        assert "duplicate timestamps" in message

    def test_validate_dataframe_non_numeric_columns(self):
        """Test DataFrame validation with non-numeric data in numeric columns."""
        invalid_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="1h"),
                "open": ["invalid", "data", "here"],  # Non-numeric
                "high": [105.0, 106.0, 107.0],
                "low": [95.0, 96.0, 97.0],
                "close": [102.0, 103.0, 104.0],
                "volume": [1000.0, 1100.0, 1200.0],
            }
        )

        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))
        is_valid, message = atomic_ops.validate_dataframe(invalid_df)

        assert is_valid is False
        assert "not numeric" in message

    def test_write_dataframe_atomic_success(self):
        """Test successful atomic DataFrame write."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            valid_df = pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=3, freq="1h"),
                    "open": [100.0, 101.0, 102.0],
                    "high": [105.0, 106.0, 107.0],
                    "low": [95.0, 96.0, 97.0],
                    "close": [102.0, 103.0, 104.0],
                    "volume": [1000.0, 1100.0, 1200.0],
                }
            )

            header_comments = ["# Test header", "# Generated by test"]

            atomic_ops = AtomicCSVOperations(csv_path)
            success = atomic_ops.write_dataframe_atomic(valid_df, header_comments)

            assert success is True
            assert csv_path.exists()

            # Verify file content
            with open(csv_path, "r") as f:
                content = f.read()
                assert "# Test header" in content
                assert "# Generated by test" in content

            # Verify data integrity
            df_read = pd.read_csv(csv_path, comment="#")
            assert len(df_read) == len(valid_df)
            assert list(df_read.columns) == list(valid_df.columns)

    def test_write_dataframe_atomic_validation_failure(self):
        """Test atomic write with invalid DataFrame."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            invalid_df = pd.DataFrame()  # Empty DataFrame

            atomic_ops = AtomicCSVOperations(csv_path)
            success = atomic_ops.write_dataframe_atomic(invalid_df)

            assert success is False
            assert not csv_path.exists()

    @patch("shutil.move")
    def test_write_dataframe_atomic_write_failure(self, mock_move):
        """Test atomic write with write operation failure."""
        mock_move.side_effect = OSError("Disk full")

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            valid_df = pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=3, freq="1h"),
                    "open": [100.0, 101.0, 102.0],
                    "high": [105.0, 106.0, 107.0],
                    "low": [95.0, 96.0, 97.0],
                    "close": [102.0, 103.0, 104.0],
                    "volume": [1000.0, 1100.0, 1200.0],
                }
            )

            atomic_ops = AtomicCSVOperations(csv_path)
            success = atomic_ops.write_dataframe_atomic(valid_df)

            assert success is False

    def test_rollback_from_backup_success(self):
        """Test successful rollback from backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"
            backup_path = Path(temp_dir) / "test.backup.csv"

            # Create original file
            original_content = (
                "date,open,high,low,close,volume\n2024-01-01 00:00:00,100,105,95,102,1000\n"
            )
            with open(csv_path, "w") as f:
                f.write(original_content)

            # Create backup
            with open(backup_path, "w") as f:
                f.write(original_content)

            # Corrupt original file
            with open(csv_path, "w") as f:
                f.write("corrupted data")

            atomic_ops = AtomicCSVOperations(csv_path)
            atomic_ops.backup_path = backup_path

            success = atomic_ops.rollback_from_backup()

            assert success is True

            # Verify restoration
            with open(csv_path, "r") as f:
                restored_content = f.read()
                assert restored_content == original_content

    def test_rollback_from_backup_no_backup(self):
        """Test rollback when no backup exists."""
        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))

        success = atomic_ops.rollback_from_backup()

        assert success is False

    def test_cleanup_backup_success(self):
        """Test successful backup cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "test.backup.csv"

            # Create backup file
            with open(backup_path, "w") as f:
                f.write("backup content")

            atomic_ops = AtomicCSVOperations(Path(temp_dir) / "test.csv")
            atomic_ops.backup_path = backup_path

            success = atomic_ops.cleanup_backup()

            assert success is True
            assert not backup_path.exists()

    def test_cleanup_backup_no_backup(self):
        """Test cleanup when no backup exists."""
        atomic_ops = AtomicCSVOperations(Path("/tmp/test.csv"))

        success = atomic_ops.cleanup_backup()

        assert success is True  # No backup to cleanup is considered success


class TestSafeCSVMerger:
    """Test suite for SafeCSVMerger."""

    def test_init(self):
        """Test SafeCSVMerger initialization."""
        csv_path = Path("/tmp/test.csv")
        merger = SafeCSVMerger(csv_path)

        assert merger.csv_path == csv_path
        assert isinstance(merger.atomic_ops, AtomicCSVOperations)

    def test_merge_gap_data_safe_success(self):
        """Test successful gap data merge."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            # Create original CSV with gaps
            original_df = pd.DataFrame(
                {
                    "date": [
                        "2024-01-01 00:00:00",
                        "2024-01-01 01:00:00",
                        # Gap: 02:00:00 and 03:00:00 missing
                        "2024-01-01 04:00:00",
                        "2024-01-01 05:00:00",
                    ],
                    "open": [100.0, 101.0, 104.0, 105.0],
                    "high": [105.0, 106.0, 109.0, 110.0],
                    "low": [95.0, 96.0, 99.0, 100.0],
                    "close": [102.0, 103.0, 106.0, 107.0],
                    "volume": [1000.0, 1100.0, 1400.0, 1500.0],
                }
            )

            # Add header comments
            with open(csv_path, "w") as f:
                f.write("# Test CSV\n")
                f.write("# With gaps\n")
                original_df.to_csv(f, index=False)

            # Create gap data
            gap_data = pd.DataFrame(
                {
                    "date": ["2024-01-01 02:00:00", "2024-01-01 03:00:00"],
                    "open": [102.5, 103.5],
                    "high": [107.0, 108.0],
                    "low": [97.0, 98.0],
                    "close": [104.0, 105.0],
                    "volume": [1200.0, 1300.0],
                }
            )

            gap_start = datetime.strptime("2024-01-01 02:00:00", "%Y-%m-%d %H:%M:%S")
            gap_end = datetime.strptime("2024-01-01 03:00:00", "%Y-%m-%d %H:%M:%S")

            merger = SafeCSVMerger(csv_path)
            success = merger.merge_gap_data_safe(gap_data, gap_start, gap_end)

            assert success is True

            # Verify merged data
            merged_df = pd.read_csv(csv_path, comment="#")
            assert len(merged_df) == 6  # Original 4 + Gap 2

            # Verify timestamps are sorted
            dates = pd.to_datetime(merged_df["date"])
            assert dates.is_monotonic_increasing

            # Verify gap data is present
            gap_mask = (dates >= gap_start) & (dates <= gap_end)
            assert gap_mask.sum() == 2

    def test_merge_gap_data_safe_overlapping_data(self):
        """Test gap merge with overlapping existing data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            # Create original CSV with data that overlaps gap range
            original_df = pd.DataFrame(
                {
                    "date": [
                        "2024-01-01 00:00:00",
                        "2024-01-01 01:00:00",
                        "2024-01-01 02:00:00",  # Will be replaced
                        "2024-01-01 04:00:00",
                    ],
                    "open": [100.0, 101.0, 102.0, 104.0],
                    "high": [105.0, 106.0, 107.0, 109.0],
                    "low": [95.0, 96.0, 97.0, 99.0],
                    "close": [102.0, 103.0, 104.0, 106.0],
                    "volume": [1000.0, 1100.0, 1200.0, 1400.0],
                }
            )

            original_df.to_csv(csv_path, index=False)

            # Create gap data that overlaps - must have all required columns
            gap_data = pd.DataFrame(
                {
                    "date": [
                        "2024-01-01 02:00:00",  # Replaces existing
                        "2024-01-01 03:00:00",  # New data
                    ],
                    "open": [102.5, 103.5],
                    "high": [107.5, 108.5],
                    "low": [97.5, 98.5],
                    "close": [104.5, 105.5],
                    "volume": [1250.0, 1350.0],
                    "close_time": ["2024-01-01 02:59:59", "2024-01-01 03:59:59"],
                    "quote_asset_volume": [12500.0, 13500.0],
                    "number_of_trades": [62, 67],
                    "taker_buy_base_asset_volume": [625.0, 675.0],
                    "taker_buy_quote_asset_volume": [6250.0, 6750.0],
                }
            )

            gap_start = datetime.strptime("2024-01-01 02:00:00", "%Y-%m-%d %H:%M:%S")
            gap_end = datetime.strptime("2024-01-01 03:00:00", "%Y-%m-%d %H:%M:%S")

            merger = SafeCSVMerger(csv_path)
            success = merger.merge_gap_data_safe(gap_data, gap_start, gap_end)

            assert success is True

            # Verify merged data
            merged_df = pd.read_csv(csv_path, comment="#")
            assert len(merged_df) == 5  # Original 4 - 1 replaced + 2 gap = 5

            # Verify the 02:00:00 data was replaced with gap data
            row_02 = merged_df[merged_df["date"] == "2024-01-01 02:00:00"].iloc[0]
            assert row_02["open"] == 102.5  # From gap data, not original 102.0

    def test_merge_gap_data_safe_validation_failure(self):
        """Test gap merge with validation failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            # Create original CSV
            original_df = pd.DataFrame(
                {
                    "date": ["2024-01-01 00:00:00", "2024-01-01 01:00:00"],
                    "open": [100.0, 101.0],
                    "high": [105.0, 106.0],
                    "low": [95.0, 96.0],
                    "close": [102.0, 103.0],
                    "volume": [1000.0, 1100.0],
                }
            )

            original_df.to_csv(csv_path, index=False)
            original_content = csv_path.read_text()

            # Create invalid gap data - use empty DataFrame to trigger validation failure
            gap_data = pd.DataFrame()

            gap_start = datetime.strptime("2024-01-01 02:00:00", "%Y-%m-%d %H:%M:%S")
            gap_end = datetime.strptime("2024-01-01 02:00:00", "%Y-%m-%d %H:%M:%S")

            merger = SafeCSVMerger(csv_path)
            success = merger.merge_gap_data_safe(gap_data, gap_start, gap_end)

            assert success is False

            # Verify original file is unchanged
            assert csv_path.read_text() == original_content

    @patch("pandas.concat")
    def test_merge_gap_data_safe_merge_failure(self, mock_concat):
        """Test gap merge with merge operation failure."""
        mock_concat.side_effect = Exception("Merge failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "test.csv"

            # Create original CSV
            original_df = pd.DataFrame(
                {
                    "date": ["2024-01-01 00:00:00"],
                    "open": [100.0],
                    "high": [105.0],
                    "low": [95.0],
                    "close": [102.0],
                    "volume": [1000.0],
                }
            )

            original_df.to_csv(csv_path, index=False)
            original_content = csv_path.read_text()

            gap_data = pd.DataFrame(
                {
                    "date": ["2024-01-01 01:00:00"],
                    "open": [101.0],
                    "high": [106.0],
                    "low": [96.0],
                    "close": [103.0],
                    "volume": [1100.0],
                }
            )

            gap_start = datetime.strptime("2024-01-01 01:00:00", "%Y-%m-%d %H:%M:%S")
            gap_end = datetime.strptime("2024-01-01 01:00:00", "%Y-%m-%d %H:%M:%S")

            merger = SafeCSVMerger(csv_path)
            success = merger.merge_gap_data_safe(gap_data, gap_start, gap_end)

            assert success is False

            # Verify original file is restored (rollback occurred)
            assert csv_path.read_text() == original_content
