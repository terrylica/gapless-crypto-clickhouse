"""Advanced tests for BinancePublicDataCollector - coverage boosters for 52%→70%.

Targets:
- ETag caching logic and bandwidth optimization
- Gap analysis and detection algorithms
- Data saving (CSV/Parquet format switching)
- Metadata generation and hash calculation
- File validation integration
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from gapless_crypto_clickhouse.collectors.binance_public_data_collector import (
    BinancePublicDataCollector,
)


class TestETagCaching:
    """Test ETag caching logic for bandwidth optimization."""

    def test_etag_cache_initialization(self):
        """Test that ETag cache is initialized on collector creation."""
        collector = BinancePublicDataCollector()
        assert hasattr(collector, "etag_cache")
        assert collector.etag_cache is not None

    def test_etag_cache_directory_creation(self):
        """Test that cache directory is created properly."""
        collector = BinancePublicDataCollector()
        # Cache should have a cache_dir attribute
        assert hasattr(collector.etag_cache, "cache_dir")
        assert isinstance(collector.etag_cache.cache_dir, Path)


class TestGapAnalysis:
    """Test gap detection and analysis functionality."""

    def test_perform_gap_analysis_no_data(self):
        """Test gap analysis with empty dataset."""
        collector = BinancePublicDataCollector()
        result = collector._perform_gap_analysis([], "1h")

        assert result["analysis_performed"] is True
        assert result["total_gaps_detected"] == 0
        assert result["data_completeness_score"] == 1.0
        assert "note" in result

    def test_perform_gap_analysis_single_row(self):
        """Test gap analysis with insufficient data (< 2 rows)."""
        collector = BinancePublicDataCollector()
        single_row_data = [["2024-01-01 00:00:00", 100, 105, 95, 102, 1000]]

        result = collector._perform_gap_analysis(single_row_data, "1h")

        assert result["analysis_performed"] is True
        assert result["total_gaps_detected"] == 0
        assert "Insufficient data" in result["note"]

    def test_perform_gap_analysis_continuous_data(self):
        """Test gap analysis with continuous data (no gaps)."""
        collector = BinancePublicDataCollector()

        # Create continuous hourly data
        continuous_data = [
            ["2024-01-01 00:00:00", 100, 105, 95, 102, 1000],
            ["2024-01-01 01:00:00", 102, 107, 97, 104, 1100],
            ["2024-01-01 02:00:00", 104, 109, 99, 106, 1200],
            ["2024-01-01 03:00:00", 106, 111, 101, 108, 1300],
        ]

        result = collector._perform_gap_analysis(continuous_data, "1h")

        assert result["analysis_performed"] is True
        assert result["total_gaps_detected"] == 0
        assert result["gaps_remaining"] == 0
        assert result["data_completeness_score"] == 1.0

    def test_perform_gap_analysis_with_gaps(self):
        """Test gap analysis with data containing gaps."""
        collector = BinancePublicDataCollector()

        # Create data with gaps (missing 2:00 and 3:00)
        gapped_data = [
            ["2024-01-01 00:00:00", 100, 105, 95, 102, 1000],
            ["2024-01-01 01:00:00", 102, 107, 97, 104, 1100],
            # Gap: 02:00:00 and 03:00:00 missing
            ["2024-01-01 04:00:00", 106, 111, 101, 108, 1300],
            ["2024-01-01 05:00:00", 108, 113, 103, 110, 1400],
        ]

        result = collector._perform_gap_analysis(gapped_data, "1h")

        assert result["analysis_performed"] is True
        assert result["total_gaps_detected"] > 0
        assert result["gaps_remaining"] > 0
        assert result["data_completeness_score"] < 1.0
        assert "gap_details" in result
        assert len(result["gap_details"]) > 0

        # Verify gap details structure
        gap_detail = result["gap_details"][0]
        assert "gap_start" in gap_detail
        assert "gap_end" in gap_detail
        assert "missing_bars" in gap_detail
        assert "duration_minutes" in gap_detail

    def test_perform_gap_analysis_different_timeframes(self):
        """Test gap analysis with different timeframes (5m, 15m, 4h)."""
        collector = BinancePublicDataCollector()

        # Test 5-minute timeframe
        five_min_data = [
            ["2024-01-01 00:00:00", 100, 105, 95, 102, 1000],
            ["2024-01-01 00:05:00", 102, 107, 97, 104, 1100],
            ["2024-01-01 00:10:00", 104, 109, 99, 106, 1200],
        ]

        result_5m = collector._perform_gap_analysis(five_min_data, "5m")
        assert result_5m["analysis_performed"] is True
        assert result_5m["analysis_parameters"]["timeframe"] == "5m"
        assert result_5m["analysis_parameters"]["expected_interval_minutes"] == 5

        # Test 4-hour timeframe
        four_hour_data = [
            ["2024-01-01 00:00:00", 100, 105, 95, 102, 1000],
            ["2024-01-01 04:00:00", 102, 107, 97, 104, 1100],
        ]

        result_4h = collector._perform_gap_analysis(four_hour_data, "4h")
        assert result_4h["analysis_performed"] is True
        assert result_4h["analysis_parameters"]["timeframe"] == "4h"
        assert result_4h["analysis_parameters"]["expected_interval_minutes"] == 240


class TestDataHashCalculation:
    """Test data integrity hash calculation."""

    def test_calculate_data_hash_consistent(self):
        """Test that hash calculation is consistent for same data."""
        collector = BinancePublicDataCollector()

        test_data = [
            ["2024-01-01 00:00:00", 100, 105, 95, 102, 1000],
            ["2024-01-01 01:00:00", 102, 107, 97, 104, 1100],
        ]

        hash1 = collector._calculate_data_hash(test_data)
        hash2 = collector._calculate_data_hash(test_data)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest is 64 characters

    def test_calculate_data_hash_different_data(self):
        """Test that different data produces different hashes."""
        collector = BinancePublicDataCollector()

        data1 = [["2024-01-01 00:00:00", 100, 105, 95, 102, 1000]]
        data2 = [["2024-01-01 00:00:00", 101, 105, 95, 102, 1000]]  # Different open price

        hash1 = collector._calculate_data_hash(data1)
        hash2 = collector._calculate_data_hash(data2)

        assert hash1 != hash2

    def test_calculate_data_hash_empty_data(self):
        """Test hash calculation with empty data."""
        collector = BinancePublicDataCollector()

        empty_hash = collector._calculate_data_hash([])

        assert isinstance(empty_hash, str)
        assert len(empty_hash) == 64


class TestMetadataGeneration:
    """Test comprehensive metadata generation."""

    def test_generate_metadata_structure(self):
        """Test that metadata has all required fields."""
        collector = BinancePublicDataCollector()

        test_data = [
            [
                "2024-01-01 00:00:00",
                100,
                105,
                95,
                102,
                1000,
                "2024-01-01 00:59:59",
                10000,
                50,
                500,
                5000,
            ],
            [
                "2024-01-01 01:00:00",
                102,
                107,
                97,
                104,
                1100,
                "2024-01-01 01:59:59",
                11000,
                55,
                550,
                5500,
            ],
        ]

        collection_stats = {
            "method": "direct_download",
            "duration": 10.5,
            "bars_per_second": 190,
            "total_bars": 2,
        }

        metadata = collector.generate_metadata("1h", test_data, collection_stats)

        # Verify required top-level keys
        assert "version" in metadata
        assert "generator" in metadata
        assert "generation_timestamp" in metadata
        assert "data_source" in metadata
        assert "market_type" in metadata
        assert "symbol" in metadata
        assert "timeframe" in metadata
        assert "collection_method" in metadata
        assert "target_period" in metadata
        assert "actual_bars" in metadata
        assert "date_range" in metadata
        assert "statistics" in metadata
        assert "collection_performance" in metadata
        assert "data_integrity" in metadata
        assert "gap_analysis" in metadata
        assert "compliance" in metadata

        # Verify metadata values
        assert metadata["version"] == "v2.10.0"
        assert metadata["generator"] == "BinancePublicDataCollector"
        assert metadata["market_type"] == "spot"
        assert metadata["symbol"] == "SOLUSDT"  # Default symbol
        assert metadata["timeframe"] == "1h"
        assert metadata["actual_bars"] == 2

    def test_generate_metadata_empty_data(self):
        """Test metadata generation with empty dataset."""
        collector = BinancePublicDataCollector()

        metadata = collector.generate_metadata("1h", [], {})

        assert metadata == {}

    def test_generate_metadata_statistics(self):
        """Test that statistics are calculated correctly."""
        collector = BinancePublicDataCollector()

        test_data = [
            [
                "2024-01-01 00:00:00",
                100,
                110,
                90,
                105,
                1000,
                "2024-01-01 00:59:59",
                10500,
                50,
                500,
                5000,
            ],
            [
                "2024-01-01 01:00:00",
                105,
                120,
                95,
                110,
                1100,
                "2024-01-01 01:59:59",
                12100,
                55,
                550,
                5500,
            ],
        ]

        metadata = collector.generate_metadata("1h", test_data, {})

        stats = metadata["statistics"]
        assert "price_min" in stats
        assert "price_max" in stats
        assert "volume_total" in stats
        assert "volume_mean" in stats

        # Verify calculated values
        assert stats["price_min"] == 90  # Min of all low prices
        assert stats["price_max"] == 120  # Max of all high prices
        assert stats["volume_total"] == 2100  # Sum of volumes
        assert stats["volume_mean"] == 1050  # Average volume

    def test_generate_metadata_data_integrity(self):
        """Test data integrity section in metadata."""
        collector = BinancePublicDataCollector()

        test_data = [
            [
                "2024-01-01 00:00:00",
                100,
                105,
                95,
                102,
                1000,
                "2024-01-01 00:59:59",
                10000,
                50,
                500,
                5000,
            ],
        ]

        metadata = collector.generate_metadata("1h", test_data, {})

        integrity = metadata["data_integrity"]
        assert "chronological_order" in integrity
        assert "data_hash" in integrity
        assert "corruption_detected" in integrity
        assert "corrupted_rows_count" in integrity

        assert integrity["chronological_order"] is True
        assert isinstance(integrity["data_hash"], str)
        assert len(integrity["data_hash"]) == 64  # SHA256


class TestDataSaving:
    """Test data saving with CSV and Parquet formats."""

    def test_save_data_csv_format(self):
        """Test saving data in CSV format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = BinancePublicDataCollector(output_dir=tmpdir, output_format="csv")

            test_data = [
                [
                    "2024-01-01 00:00:00",
                    100,
                    105,
                    95,
                    102,
                    1000,
                    "2024-01-01 00:59:59",
                    10000,
                    50,
                    500,
                    5000,
                ],
                [
                    "2024-01-01 01:00:00",
                    102,
                    107,
                    97,
                    104,
                    1100,
                    "2024-01-01 01:59:59",
                    11000,
                    55,
                    550,
                    5500,
                ],
            ]

            collection_stats = {
                "method": "direct_download",
                "duration": 5.0,
                "bars_per_second": 0,
                "total_bars": 2,
            }

            filepath = collector.save_data("1h", test_data, collection_stats)

            assert filepath is not None
            assert filepath.exists()
            assert filepath.suffix == ".csv"
            assert "SOLUSDT" in filepath.name
            assert "1h" in filepath.name

            # Verify metadata file was created
            metadata_file = filepath.with_suffix(".metadata.json")
            assert metadata_file.exists()

            # Verify CSV can be read back
            df = pd.read_csv(filepath, comment="#")
            assert len(df) == 2
            assert "date" in df.columns
            assert "open" in df.columns

    def test_save_data_parquet_format(self):
        """Test saving data in Parquet format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = BinancePublicDataCollector(output_dir=tmpdir, output_format="parquet")

            test_data = [
                [
                    "2024-01-01 00:00:00",
                    100,
                    105,
                    95,
                    102,
                    1000,
                    "2024-01-01 00:59:59",
                    10000,
                    50,
                    500,
                    5000,
                ],
                [
                    "2024-01-01 01:00:00",
                    102,
                    107,
                    97,
                    104,
                    1100,
                    "2024-01-01 01:59:59",
                    11000,
                    55,
                    550,
                    5500,
                ],
            ]

            collection_stats = {
                "method": "direct_download",
                "duration": 5.0,
                "bars_per_second": 0,
                "total_bars": 2,
            }

            filepath = collector.save_data("1h", test_data, collection_stats)

            assert filepath is not None
            assert filepath.exists()
            assert filepath.suffix == ".parquet"
            assert "SOLUSDT" in filepath.name
            assert "1h" in filepath.name

            # Verify metadata file was created
            metadata_file = filepath.with_suffix(".metadata.json")
            assert metadata_file.exists()

            # Verify Parquet can be read back
            df = pd.read_parquet(filepath)
            assert len(df) == 2
            assert "date" in df.columns
            assert "open" in df.columns

    def test_save_data_empty_dataset(self):
        """Test saving empty dataset returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = BinancePublicDataCollector(output_dir=tmpdir)

            filepath = collector.save_data("1h", [], {})

            assert filepath is None

    def test_save_data_creates_output_directory(self):
        """Test that save_data creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "output"
            collector = BinancePublicDataCollector(output_dir=str(output_path))

            test_data = [
                [
                    "2024-01-01 00:00:00",
                    100,
                    105,
                    95,
                    102,
                    1000,
                    "2024-01-01 00:59:59",
                    10000,
                    50,
                    500,
                    5000,
                ],
            ]

            collection_stats = {
                "method": "direct_download",
                "duration": 5.0,
                "bars_per_second": 0,
                "total_bars": 1,
            }

            filepath = collector.save_data("1h", test_data, collection_stats)

            assert output_path.exists()
            assert filepath.exists()


class TestTimeframeExtraction:
    """Test timeframe extraction from filenames."""

    def test_extract_timeframe_from_filename_valid(self):
        """Test extracting valid timeframes from filenames."""
        collector = BinancePublicDataCollector()

        test_cases = [
            ("BTCUSDT-1h_2024-01-01.csv", "1h"),
            ("ETHUSDT-5m_data.csv", "5m"),
            ("SOLUSDT-15m-20240101.csv", "15m"),
            ("binance_spot_ADAUSDT-30m_20240101-20240131_v2.10.0.csv", "30m"),
            ("DOTUSDT-1d_monthly.csv", "1d"),
            ("LINKUSDT-4h-historical.csv", "4h"),
        ]

        for filename, expected_timeframe in test_cases:
            result = collector._extract_timeframe_from_filename(filename)
            assert result == expected_timeframe, f"Failed for {filename}"

    def test_extract_timeframe_from_filename_default(self):
        """Test default timeframe when none found in filename."""
        collector = BinancePublicDataCollector()

        # Filename with no timeframe
        result = collector._extract_timeframe_from_filename("BTCUSDT_data.csv")

        assert result == "15m"  # Default timeframe


class TestOutputFormatValidation:
    """Test output format validation."""

    def test_invalid_output_format_rejected(self):
        """Test that invalid output formats are rejected."""
        with pytest.raises(ValueError, match="output_format must be"):
            BinancePublicDataCollector(output_format="json")

        with pytest.raises(ValueError, match="output_format must be"):
            BinancePublicDataCollector(output_format="xlsx")

    def test_valid_output_formats_accepted(self):
        """Test that valid output formats are accepted."""
        # CSV format
        collector_csv = BinancePublicDataCollector(output_format="csv")
        assert collector_csv.output_format == "csv"

        # Parquet format
        collector_parquet = BinancePublicDataCollector(output_format="parquet")
        assert collector_parquet.output_format == "parquet"


class TestMonthlyURLGeneration:
    """Test monthly URL generation for different date ranges."""

    def test_generate_monthly_urls_single_month(self):
        """Test URL generation for single month."""
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date="2024-01-01", end_date="2024-01-31"
        )

        urls = collector.generate_monthly_urls("1h")

        assert len(urls) == 1
        url, year_month, filename = urls[0]
        assert "BTCUSDT" in url
        assert "1h" in url
        assert "2024-01" in url
        assert year_month == "2024-01"
        assert filename == "BTCUSDT-1h-2024-01.zip"

    def test_generate_monthly_urls_multi_month(self):
        """Test URL generation spanning multiple months."""
        collector = BinancePublicDataCollector(
            symbol="ETHUSDT", start_date="2024-01-01", end_date="2024-03-31"
        )

        urls = collector.generate_monthly_urls("1h")

        assert len(urls) == 3  # January, February, March
        assert "2024-01" in urls[0][1]
        assert "2024-02" in urls[1][1]
        assert "2024-03" in urls[2][1]

    def test_generate_monthly_urls_year_boundary(self):
        """Test URL generation across year boundary."""
        collector = BinancePublicDataCollector(
            symbol="SOLUSDT", start_date="2023-11-01", end_date="2024-02-28"
        )

        urls = collector.generate_monthly_urls("1h")

        assert len(urls) == 4  # Nov 2023, Dec 2023, Jan 2024, Feb 2024
        assert "2023-11" in urls[0][1]
        assert "2023-12" in urls[1][1]
        assert "2024-01" in urls[2][1]
        assert "2024-02" in urls[3][1]


class TestHeaderDetection:
    """Test intelligent header detection in CSV data."""

    def test_detect_header_with_header_row(self):
        """Test detection when CSV has header row."""
        collector = BinancePublicDataCollector()

        # CSV with header row (non-numeric first field)
        csv_with_header = [
            ["open_time", "open", "high", "low", "close", "volume"],
            ["1704067200000", "42000.0", "42500.0", "41500.0", "42100.0", "1000.0"],
        ]

        has_header = collector._detect_header_intelligent(csv_with_header)

        assert has_header is True

    def test_detect_header_without_header_row(self):
        """Test detection when CSV has no header (pure data)."""
        collector = BinancePublicDataCollector()

        # CSV without header (numeric timestamp in first row)
        csv_no_header = [
            ["1704067200000", "42000.0", "42500.0", "41500.0", "42100.0", "1000.0"],
            ["1704070800000", "42100.0", "42600.0", "41600.0", "42200.0", "1100.0"],
        ]

        has_header = collector._detect_header_intelligent(csv_no_header)

        assert has_header is False

    def test_detect_header_empty_data(self):
        """Test header detection with empty data."""
        collector = BinancePublicDataCollector()

        has_header = collector._detect_header_intelligent([])

        assert has_header is False

    def test_detect_header_insufficient_columns(self):
        """Test header detection with insufficient columns."""
        collector = BinancePublicDataCollector()

        # Less than 6 columns
        insufficient_data = [["timestamp", "open", "high"]]

        has_header = collector._detect_header_intelligent(insufficient_data)

        assert has_header is False

    def test_detect_header_invalid_timestamp(self):
        """Test header detection with invalid timestamp (indicates header)."""
        collector = BinancePublicDataCollector()

        # First field is not a valid timestamp
        csv_with_text = [
            ["999", "42000.0", "42500.0", "41500.0", "42100.0", "1000.0"],  # Too short timestamp
        ]

        has_header = collector._detect_header_intelligent(csv_with_text)

        assert has_header is True  # Invalid timestamp suggests header row
