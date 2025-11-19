"""Test output_dir bug fix and DataFrame return functionality."""

import tempfile
from pathlib import Path

import pandas as pd

from gapless_crypto_clickhouse import BinancePublicDataCollector


def test_output_dir_bug_fix():
    """Test that output_dir parameter is now respected and files are saved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "test_output"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        collector = BinancePublicDataCollector(
            symbol="BTCUSDT",
            start_date="2024-01-01",
            end_date="2024-01-01",
            output_dir=str(test_output_dir),
        )

        # Verify collector has correct output_dir
        assert collector.output_dir == test_output_dir

        # Before collection - no files
        files_before = list(test_output_dir.glob("*"))
        assert len(files_before) == 0

        # Collect data
        collector.collect_timeframe_data("1h")

        # After collection - files should exist
        files_after = list(test_output_dir.glob("*.csv"))
        assert len(files_after) == 1, f"Expected 1 CSV file, found {len(files_after)}"

        # Metadata file should also exist
        metadata_files = list(test_output_dir.glob("*.json"))
        assert len(metadata_files) == 1, f"Expected 1 metadata file, found {len(metadata_files)}"

        print("✅ Output_dir bug fix confirmed!")


def test_dataframe_return_functionality():
    """Test that collect_timeframe_data returns proper DataFrame and metadata."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "df_test"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        collector = BinancePublicDataCollector(
            symbol="BTCUSDT",
            start_date="2024-01-01",
            end_date="2024-01-01",
            output_dir=str(test_output_dir),
        )

        result = collector.collect_timeframe_data("1h")

        # Check return format
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "dataframe" in result, "Missing 'dataframe' key"
        assert "filepath" in result, "Missing 'filepath' key"
        assert "stats" in result, "Missing 'stats' key"

        # Check DataFrame
        df = result["dataframe"]
        assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"
        assert not df.empty, "DataFrame should not be empty"

        # Check columns
        expected_columns = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
        ]
        assert list(df.columns) == expected_columns, f"Unexpected columns: {list(df.columns)}"

        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df["date"]), "date column should be datetime"
        assert pd.api.types.is_datetime64_any_dtype(df["close_time"]), (
            "close_time column should be datetime"
        )
        assert pd.api.types.is_numeric_dtype(df["open"]), "open column should be numeric"
        assert pd.api.types.is_numeric_dtype(df["volume"]), "volume column should be numeric"

        # Check filepath
        filepath = result["filepath"]
        assert filepath is not None, "filepath should not be None"
        assert isinstance(filepath, Path), f"Expected Path, got {type(filepath)}"
        assert filepath.exists(), "CSV file should exist"

        # Check stats
        stats = result["stats"]
        assert isinstance(stats, dict), f"Expected dict, got {type(stats)}"
        assert "method" in stats, "Missing 'method' in stats"
        assert "total_bars" in stats, "Missing 'total_bars' in stats"
        assert stats["method"] == "direct_download", (
            f"Expected 'direct_download', got {stats['method']}"
        )
        assert stats["total_bars"] > 0, f"Expected positive bars, got {stats['total_bars']}"

        print("✅ DataFrame return functionality confirmed!")


def test_backwards_compatibility():
    """Test that the new return format doesn't break existing workflows."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_output_dir = Path(temp_dir) / "compat_test"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        collector = BinancePublicDataCollector(
            symbol="BTCUSDT",
            start_date="2024-01-01",
            end_date="2024-01-01",
            output_dir=str(test_output_dir),
        )

        result = collector.collect_timeframe_data("1h")

        # Users can access DataFrame directly
        df = result["dataframe"]
        assert isinstance(df, pd.DataFrame)

        # Users can access filepath for file operations
        filepath = result["filepath"]
        assert filepath.exists()

        # Users can read the CSV file independently
        df_from_file = pd.read_csv(filepath, comment="#")
        assert len(df_from_file) == len(df), "DataFrame and file should have same length"

        print("✅ Backwards compatibility confirmed!")


if __name__ == "__main__":
    test_output_dir_bug_fix()
    test_dataframe_return_functionality()
    test_backwards_compatibility()
    print("🎉 All tests passed!")
