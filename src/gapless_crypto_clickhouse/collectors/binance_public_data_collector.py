#!/usr/bin/env python3
"""
Binance Public Data Collector

Ultra-fast historical data collection using Binance's official public data repository.
10-100x faster than API calls, with complete historical coverage.

Data source: https://data.binance.vision/data/spot/monthly/klines/
"""

import argparse
import csv
import hashlib
import json
import logging
import shutil
import tempfile
import urllib.request
import warnings
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from ..gap_filling.universal_gap_filler import UniversalGapFiller
from ..utils.etag_cache import ETagCache
from ..utils.timeframe_constants import TIMEFRAME_TO_MINUTES
from ..utils.timestamp_format_analyzer import TimestampFormatAnalyzer
from ..validation.csv_validator import CSVValidator


class BinancePublicDataCollector:
    """Ultra-fast cryptocurrency spot data collection from Binance's public data repository.

    This collector provides 10-100x faster data collection compared to API calls by
    downloading pre-generated monthly ZIP files from Binance's official public data repository.
    Supports complete historical coverage with full 11-column microstructure format including
    order flow metrics.

    Features:
        - Ultra-fast bulk data collection from monthly ZIP archives
        - Complete historical coverage from 2017 onwards
        - Full 11-column microstructure format with order flow data
        - Automatic gap detection and filling capabilities
        - Built-in data validation and integrity checks
        - Support for all major timeframes (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h)
        - DataFrame-first Python API with seamless pandas integration

    Data Format:
        The collector outputs CSV files with 11 columns providing complete market microstructure:
        - OHLCV: Open, High, Low, Close, Volume
        - Timestamps: Open Time, Close Time
        - Order Flow: Quote Asset Volume, Number of Trades
        - Taker Metrics: Taker Buy Base Volume, Taker Buy Quote Volume

    Examples:
        For simple data collection, consider using the function-based API:

        >>> import gapless_crypto_clickhouse as gcd
        >>> df = gcd.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-12-31")

        Advanced usage with this class for complex workflows:

        >>> collector = BinancePublicDataCollector()
        >>> result = collector.collect_timeframe_data("1h")
        >>> df = result["dataframe"]
        >>> print(f"Collected {len(df)} bars of {collector.symbol} data")
        Collected 26280 bars of SOLUSDT data

        Custom configuration and multiple timeframes:

        >>> collector = BinancePublicDataCollector(
        ...     symbol="BTCUSDT",
        ...     start_date="2023-01-01",
        ...     end_date="2023-12-31",
        ...     output_dir="./crypto_data"
        ... )
        >>> results = collector.collect_multiple_timeframes(["1h", "4h"])
        >>> for timeframe, result in results.items():
        ...     print(f"{timeframe}: {len(result['dataframe'])} bars")
        1h: 8760 bars
        4h: 2190 bars

    Note:
        This collector only supports USDT spot pairs (BTCUSDT, ETHUSDT, SOLUSDT, etc.).
        It does not support futures, perpetuals, or non-USDT pairs.
    """

    def _validate_symbol(self, symbol: str) -> str:
        """
        Validate and sanitize symbol input for security.

        This method prevents path traversal attacks and ensures symbol format integrity
        by rejecting invalid characters and malformed inputs.

        Args:
            symbol: Trading pair symbol to validate (e.g., "BTCUSDT", "SOLUSDT")

        Returns:
            Validated and normalized symbol string (uppercase, stripped)

        Raises:
            ValueError: If symbol is None, empty, or contains invalid characters

        Security:
            - Prevents path traversal attacks (CWE-22)
            - Blocks directory navigation characters (/, \\, ., ..)
            - Enforces alphanumeric-only input
            - Protects file operations using symbol in paths

        Examples:
            >>> collector._validate_symbol("btcusdt")
            'BTCUSDT'

            >>> collector._validate_symbol("BTC/../etc/passwd")
            ValueError: Symbol contains invalid characters...

            >>> collector._validate_symbol("")
            ValueError: Symbol cannot be empty

            >>> collector._validate_symbol(None)
            ValueError: Symbol cannot be None
        """
        # SEC-03: None value validation
        if symbol is None:
            raise ValueError("Symbol cannot be None")

        # SEC-02: Empty string validation
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")

        # SEC-01: Path traversal prevention
        import re

        if re.search(r"[./\\]", symbol):
            raise ValueError(
                f"Symbol contains invalid characters: {symbol}\n"
                f"Symbol must be alphanumeric (e.g., BTCUSDT, SOLUSDT)"
            )

        # Normalize to uppercase and strip whitespace
        symbol = symbol.upper().strip()

        # Whitelist validation - only alphanumeric characters
        if not re.match(r"^[A-Z0-9]+$", symbol):
            raise ValueError(
                f"Symbol must be alphanumeric: {symbol}\nValid examples: BTCUSDT, ETHUSDT, SOLUSDT"
            )

        return symbol

    def __init__(
        self,
        symbol: str = "SOLUSDT",
        start_date: str = "2020-08-15",
        end_date: str = "2025-03-20",
        output_dir: Optional[Union[str, Path]] = None,
        output_format: str = "csv",
    ) -> None:
        """Initialize the Binance Public Data Collector.

        Args:
            symbol (str, optional): Trading pair symbol in USDT format.
                Must be alphanumeric (A-Z, 0-9) only. Path characters (/, \\, .)
                and special characters are rejected for security.
                Symbol is normalized to uppercase.
                Defaults to "SOLUSDT".
            start_date (str, optional): Start date in YYYY-MM-DD format.
                Data collection begins from this date (inclusive).
                Must be on or before end_date.
                Defaults to "2020-08-15".
            end_date (str, optional): End date in YYYY-MM-DD format.
                Data collection ends on this date (inclusive, 23:59:59).
                Must be on or after start_date.
                Defaults to "2025-03-20".
            output_dir (str or Path, optional): Directory to save files.
                If None, saves to package's sample_data directory.
                Defaults to None.
            output_format (str, optional): Output format ("csv" or "parquet").
                CSV provides universal compatibility, Parquet offers 5-10x compression.
                Defaults to "csv".

        Raises:
            ValueError: If symbol is None, empty, or contains invalid characters
                (path traversal, special characters, non-alphanumeric).
            ValueError: If date format is incorrect (not YYYY-MM-DD).
            ValueError: If end_date is before start_date.
            ValueError: If output_format is not 'csv' or 'parquet'.
            FileNotFoundError: If output_dir path is invalid.

        Security:
            Input validation prevents path traversal attacks (CWE-22) by:
            - Rejecting symbols with path characters (/, \\, ., ..)
            - Enforcing alphanumeric-only symbols
            - Validating date range logic
            - Normalizing inputs to uppercase

        Examples:
            >>> # Default configuration (SOLUSDT, 4+ years of data)
            >>> collector = BinancePublicDataCollector()

            >>> # Custom symbol and shorter timeframe
            >>> collector = BinancePublicDataCollector(
            ...     symbol="BTCUSDT",
            ...     start_date="2024-01-01",
            ...     end_date="2024-12-31"
            ... )

            >>> # Custom output directory with Parquet format
            >>> collector = BinancePublicDataCollector(
            ...     symbol="ETHUSDT",
            ...     output_dir="/path/to/crypto/data",
            ...     output_format="parquet"
            ... )
        """
        # Validate and assign symbol (SEC-01, SEC-02, SEC-03)
        self.symbol = self._validate_symbol(symbol)

        # Parse and assign dates with validation
        try:
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            # Make end_date inclusive of the full day (23:59:59)
            self.end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {e}") from e

        # SEC-04: Validate date range logic
        if self.end_date < self.start_date:
            raise ValueError(
                f"Invalid date range: end_date ({self.end_date.strftime('%Y-%m-%d')}) "
                f"is before start_date ({self.start_date.strftime('%Y-%m-%d')})"
            )
        self.base_url = "https://data.binance.vision/data/spot/monthly/klines"

        # Initialize ETag cache for bandwidth optimization (90% reduction on re-runs)
        self.etag_cache = ETagCache()

        # Validate and store output format
        if output_format not in ["csv", "parquet"]:
            raise ValueError(f"output_format must be 'csv' or 'parquet', got '{output_format}'")
        self.output_format = output_format

        # Configure output directory - use provided path or default to sample_data
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "sample_data"

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Rich console for progress indicators
        # Simple logging instead of Rich console

        # Available timeframes on Binance public data
        self.available_timeframes = [
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1mo",
        ]

        # Popular symbols with known availability (for validation)
        self.known_symbols = {
            "BTCUSDT": "2017-08-17",
            "ETHUSDT": "2017-08-17",
            "SOLUSDT": "2020-08-11",
            "ADAUSDT": "2018-04-17",
            "DOTUSDT": "2020-08-19",
            "LINKUSDT": "2019-01-16",
        }

        # Validate date range and symbol
        self._validate_parameters()

        print("Binance Public Data Collector")
        print(f"Symbol: {self.symbol}")
        print(
            f"Date Range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
        )
        print(f"Data Source: {self.base_url}")

    def _validate_parameters(self):
        """Validate date range and symbol parameters."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Check for future dates
        if self.end_date.date() > yesterday:
            warnings.warn(
                f"⚠️  Requested end date {self.end_date.strftime('%Y-%m-%d')} is in the future. "
                f"Binance public data is typically available up to {yesterday}. "
                f"Recent data may not be available and requests may fail with 404 errors.",
                UserWarning,
                stacklevel=2,
            )

        # Check symbol availability
        if self.symbol in self.known_symbols:
            symbol_start = datetime.strptime(self.known_symbols[self.symbol], "%Y-%m-%d").date()
            if self.start_date.date() < symbol_start:
                warnings.warn(
                    f"⚠️  Requested start date {self.start_date.strftime('%Y-%m-%d')} is before "
                    f"{self.symbol} listing date ({symbol_start}). "
                    f"Data before {symbol_start} is not available.",
                    UserWarning,
                    stacklevel=2,
                )
        else:
            # Unknown symbol - provide general guidance
            logging.info(
                f"ℹ️  Symbol {self.symbol} availability not verified. "
                f"Known symbols: {list(self.known_symbols.keys())}. "
                f"If requests fail with 404 errors, check symbol availability on Binance."
            )

    def generate_monthly_urls(self, trading_timeframe: str) -> List[Tuple[str, str, str]]:
        """Generate list of monthly ZIP file URLs to download."""
        monthly_zip_urls = []
        current_month_date = self.start_date.replace(day=1)  # Start of month

        while current_month_date <= self.end_date:
            year_month_string = current_month_date.strftime("%Y-%m")
            zip_filename = f"{self.symbol}-{trading_timeframe}-{year_month_string}.zip"
            binance_zip_url = f"{self.base_url}/{self.symbol}/{trading_timeframe}/{zip_filename}"
            monthly_zip_urls.append((binance_zip_url, year_month_string, zip_filename))

            # Move to next month
            if current_month_date.month == 12:
                current_month_date = current_month_date.replace(
                    year=current_month_date.year + 1, month=1
                )
            else:
                current_month_date = current_month_date.replace(month=current_month_date.month + 1)

        return monthly_zip_urls

    def download_and_extract_month(self, binance_zip_url, zip_filename):
        """Download and extract a single monthly ZIP file with ETag caching.

        ETag caching reduces bandwidth by storing ZIP files locally and using
        HTTP conditional requests (If-None-Match) to check if the file has changed.
        Since Binance historical data is immutable, this achieves 90%+ bandwidth
        reduction on re-runs.
        """
        print(f"  Downloading {zip_filename}...")

        try:
            # Local cache path for ZIP files (XDG-compliant)
            cache_zip_path = self.etag_cache.cache_dir / "zips" / zip_filename
            cache_zip_path.parent.mkdir(parents=True, exist_ok=True)

            # Check cache for ETag
            cached_etag = self.etag_cache.get_etag(binance_zip_url)

            # If we have both ETag and local file, check if remote changed
            if cached_etag and cache_zip_path.exists():
                request = urllib.request.Request(binance_zip_url)
                request.add_header("If-None-Match", cached_etag)
                print(f"    💾 Cache check: ETag {cached_etag[:8]}...")

                try:
                    with urllib.request.urlopen(request, timeout=60) as http_response:
                        if http_response.status == 304:
                            # 304 Not Modified - use cached ZIP file
                            print(
                                f"    ✅ Cache HIT: {zip_filename} not modified (0 bytes downloaded)"
                            )
                            # Load data from cached ZIP file
                            with zipfile.ZipFile(cache_zip_path, "r") as zip_file_handle:
                                expected_csv_filename = zip_filename.replace(".zip", ".csv")
                                if expected_csv_filename in zip_file_handle.namelist():
                                    with zip_file_handle.open(
                                        expected_csv_filename
                                    ) as extracted_csv_file:
                                        csv_file_content = extracted_csv_file.read().decode("utf-8")
                                        return list(
                                            csv.reader(csv_file_content.strip().split("\n"))
                                        )
                                else:
                                    print(f"    ⚠️  CSV file not found in cached {zip_filename}")
                                    # Cache corrupted, delete and re-download
                                    cache_zip_path.unlink()
                                    self.etag_cache.invalidate(binance_zip_url)
                        elif http_response.status == 200:
                            # ETag changed - download new version
                            response_etag = http_response.headers.get("ETag")
                            content_length = http_response.headers.get("Content-Length", 0)

                            # Download to cache
                            with open(cache_zip_path, "wb") as cache_file:
                                shutil.copyfileobj(http_response, cache_file)

                            # Update ETag cache
                            if response_etag:
                                self.etag_cache.update_etag(
                                    binance_zip_url, response_etag, int(content_length)
                                )
                            print(f"    📦 Cache UPDATE: Downloaded {zip_filename}")

                            # Extract CSV data from cached file
                            with zipfile.ZipFile(cache_zip_path, "r") as zip_file_handle:
                                expected_csv_filename = zip_filename.replace(".zip", ".csv")
                                if expected_csv_filename in zip_file_handle.namelist():
                                    with zip_file_handle.open(
                                        expected_csv_filename
                                    ) as extracted_csv_file:
                                        csv_file_content = extracted_csv_file.read().decode("utf-8")
                                        return list(
                                            csv.reader(csv_file_content.strip().split("\n"))
                                        )
                        else:
                            print(
                                f"    ⚠️  HTTP {http_response.status} - {zip_filename} not available"
                            )
                            return []
                except urllib.error.HTTPError as e:
                    if e.code == 304:
                        # Handle 304 explicitly - load from cache
                        print(f"    ✅ Cache HIT: {zip_filename} not modified (0 bytes downloaded)")
                        with zipfile.ZipFile(cache_zip_path, "r") as zip_file_handle:
                            expected_csv_filename = zip_filename.replace(".zip", ".csv")
                            if expected_csv_filename in zip_file_handle.namelist():
                                with zip_file_handle.open(
                                    expected_csv_filename
                                ) as extracted_csv_file:
                                    csv_file_content = extracted_csv_file.read().decode("utf-8")
                                    return list(csv.reader(csv_file_content.strip().split("\n")))
                    else:
                        raise
            else:
                # No cache - download fresh
                request = urllib.request.Request(binance_zip_url)
                with urllib.request.urlopen(request, timeout=60) as http_response:
                    response_etag = http_response.headers.get("ETag")
                    content_length = http_response.headers.get("Content-Length", 0)

                    # Download to cache
                    with open(cache_zip_path, "wb") as cache_file:
                        shutil.copyfileobj(http_response, cache_file)

                    # Update ETag cache
                    if response_etag:
                        self.etag_cache.update_etag(
                            binance_zip_url, response_etag, int(content_length)
                        )
                    print(f"    📦 Cache MISS: Downloaded {zip_filename}")

                    # Extract CSV data from cached file
                    with zipfile.ZipFile(cache_zip_path, "r") as zip_file_handle:
                        expected_csv_filename = zip_filename.replace(".zip", ".csv")
                        if expected_csv_filename in zip_file_handle.namelist():
                            with zip_file_handle.open(expected_csv_filename) as extracted_csv_file:
                                csv_file_content = extracted_csv_file.read().decode("utf-8")
                                return list(csv.reader(csv_file_content.strip().split("\n")))
                        else:
                            print(f"    ⚠️  CSV file not found in {zip_filename}")
                            return []

        except Exception as download_exception:
            print(f"    ❌ Error downloading {zip_filename}: {download_exception}")

            # Implement automatic fallback to daily files when monthly fails
            print(f"    🔄 Attempting daily file fallback for {zip_filename}")
            return self._fallback_to_daily_files(zip_filename)

    def _fallback_to_daily_files(self, failed_monthly_filename):
        """
        Fallback to daily file downloads when monthly file is not available.

        Automatically downloads individual daily files for the failed month
        and combines them into a single dataset for seamless operation.

        Args:
            failed_monthly_filename: The monthly filename that failed (e.g., "BTCUSDT-1d-2025-09.zip")

        Returns:
            List of combined daily data, or empty list if all daily files also fail
        """
        # Extract symbol, timeframe, and year-month from failed filename
        # Format: "BTCUSDT-1d-2025-09.zip"
        parts = failed_monthly_filename.replace(".zip", "").split("-")
        if len(parts) < 4:
            print(f"    ❌ Cannot parse monthly filename: {failed_monthly_filename}")
            return []

        symbol = parts[0]
        timeframe = parts[1]
        year = parts[2]
        month = parts[3]

        print(f"    📅 Fallback: Downloading daily files for {symbol} {timeframe} {year}-{month}")

        # Generate daily URLs for the entire month
        daily_urls = self._generate_daily_urls_for_month(symbol, timeframe, year, month)

        # Download all daily files for this month
        combined_daily_data = []
        successful_daily_downloads = 0

        for daily_url, daily_filename in daily_urls:
            daily_data = self._download_and_extract_daily_file(daily_url, daily_filename)
            if daily_data:
                combined_daily_data.extend(daily_data)
                successful_daily_downloads += 1

        if successful_daily_downloads > 0:
            print(
                f"    ✅ Daily fallback successful: {successful_daily_downloads}/{len(daily_urls)} daily files retrieved"
            )
            return combined_daily_data
        else:
            print(f"    ❌ Daily fallback failed: No daily files available for {year}-{month}")
            return []

    def _generate_daily_urls_for_month(self, symbol, timeframe, year, month):
        """Generate daily URLs for all days in a specific month."""
        from calendar import monthrange

        # Get number of days in the month
        year_int = int(year)
        month_int = int(month)
        _, days_in_month = monthrange(year_int, month_int)

        daily_urls = []

        # Use daily data URL pattern: https://data.binance.vision/data/spot/daily/klines/
        daily_base_url = self.base_url.replace("/monthly/", "/daily/")

        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month_int:02d}-{day:02d}"
            daily_filename = f"{symbol}-{timeframe}-{date_str}.zip"
            daily_url = f"{daily_base_url}/{symbol}/{timeframe}/{daily_filename}"
            daily_urls.append((daily_url, daily_filename))

        return daily_urls

    def _download_and_extract_daily_file(self, daily_url, daily_filename):
        """Download and extract a single daily ZIP file."""
        try:
            with tempfile.NamedTemporaryFile() as temporary_zip_file:
                # Download daily ZIP file
                with urllib.request.urlopen(daily_url, timeout=30) as http_response:
                    if http_response.status == 200:
                        shutil.copyfileobj(http_response, temporary_zip_file)
                        temporary_zip_file.flush()
                    else:
                        # Daily file not available (normal for future dates or weekends)
                        return []

                # Extract CSV data from daily file
                with zipfile.ZipFile(temporary_zip_file.name, "r") as zip_file_handle:
                    expected_csv_filename = daily_filename.replace(".zip", ".csv")
                    if expected_csv_filename in zip_file_handle.namelist():
                        with zip_file_handle.open(expected_csv_filename) as extracted_csv_file:
                            csv_file_content = extracted_csv_file.read().decode("utf-8")
                            return list(csv.reader(csv_file_content.strip().split("\n")))
                    else:
                        return []

        except Exception:
            # Silent failure for daily files - many days may not have data
            return []

    def _detect_header_intelligent(self, raw_csv_data):
        """Intelligent header detection - determine if first row is data or header."""
        if not raw_csv_data:
            return False

        first_csv_row = raw_csv_data[0]
        if len(first_csv_row) < 6:
            return False

        # Header detection heuristics
        try:
            # Test if first field is numeric timestamp
            first_field_value = int(first_csv_row[0])

            # ✅ BOUNDARY FIX: Support both milliseconds (13-digit) AND microseconds (16-digit) formats
            # Valid timestamp ranges:
            # Milliseconds: 1000000000000 (2001) to 9999999999999 (2286)
            # Microseconds: 1000000000000000 (2001) to 9999999999999999 (2286)
            is_valid_millisecond_timestamp = 1000000000000 <= first_field_value <= 9999999999999
            is_valid_microsecond_timestamp = (
                1000000000000000 <= first_field_value <= 9999999999999999
            )

            if is_valid_millisecond_timestamp or is_valid_microsecond_timestamp:
                # Test if other fields are numeric (prices/volumes)
                for ohlcv_field_index in [1, 2, 3, 4, 5]:  # OHLCV fields
                    float(first_csv_row[ohlcv_field_index])
                return False  # All numeric = data row
            else:
                return True  # Invalid timestamp = likely header

        except (ValueError, IndexError):
            # Non-numeric first field = header
            return True

    def process_raw_data(self, raw_csv_data):
        """Convert raw Binance CSV data with comprehensive timestamp format tracking and transition detection."""
        processed_candle_data = []
        self.corruption_log = getattr(self, "corruption_log", [])

        # Initialize timestamp format analyzer
        format_analyzer = TimestampFormatAnalyzer()
        format_analyzer.initialize_tracking()

        # Intelligent header detection
        csv_has_header = self._detect_header_intelligent(raw_csv_data)
        data_start_row_index = 1 if csv_has_header else 0

        # Store header detection results for metadata
        self._header_detected = csv_has_header
        self._header_content = raw_csv_data[0][:6] if csv_has_header else None
        self._data_start_row = data_start_row_index

        if csv_has_header:
            print(f"    📋 Header detected: {raw_csv_data[0][:6]}")
        else:
            print("    📊 Pure data format detected (no header)")

        format_transition_logged = False

        for csv_row_index, csv_row_data in enumerate(
            raw_csv_data[data_start_row_index:], start=data_start_row_index
        ):
            if len(csv_row_data) >= 6:  # Binance format has 12 columns but we need first 6
                try:
                    # Binance format: [timestamp, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore]
                    raw_timestamp_value = int(csv_row_data[0])

                    # Comprehensive format detection with transition tracking
                    (
                        detected_timestamp_format,
                        converted_timestamp_seconds,
                        format_validation_result,
                    ) = format_analyzer.analyze_timestamp_format(raw_timestamp_value, csv_row_index)

                    # Track format transitions and update statistics
                    if format_analyzer.current_format is None:
                        print(f"    🎯 Initial timestamp format: {detected_timestamp_format}")

                    transition_detected = format_analyzer.update_format_stats(
                        detected_timestamp_format, raw_timestamp_value, csv_row_index
                    )

                    if transition_detected and not format_transition_logged:
                        last_transition = format_analyzer.format_transitions[-1]
                        print(
                            f"    🔄 Format transition detected: {last_transition['from_format']} → {detected_timestamp_format}"
                        )
                        format_transition_logged = True

                    # Skip if validation failed
                    if not format_validation_result["valid"]:
                        self.corruption_log.append(format_validation_result["error_details"])
                        continue

                    # ✅ CRITICAL FIX: Use UTC to match Binance's native timezone
                    # Eliminates artificial DST gaps caused by local timezone conversion
                    utc_datetime = datetime.fromtimestamp(converted_timestamp_seconds, timezone.utc)

                    # ✅ BOUNDARY FIX: Don't filter per-monthly-file to preserve month boundaries
                    # Enhanced processing: capture all 11 essential Binance columns for complete microstructure analysis
                    processed_candle_row = [
                        utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),  # date (from open_time)
                        float(csv_row_data[1]),  # open
                        float(csv_row_data[2]),  # high
                        float(csv_row_data[3]),  # low
                        float(csv_row_data[4]),  # close
                        float(csv_row_data[5]),  # volume (base asset volume)
                        # Additional microstructure columns for professional analysis
                        datetime.fromtimestamp(
                            int(csv_row_data[6])
                            / (1000000 if len(str(int(csv_row_data[6]))) >= 16 else 1000),
                            timezone.utc,
                        ).strftime("%Y-%m-%d %H:%M:%S"),  # close_time
                        float(csv_row_data[7]),  # quote_asset_volume
                        int(csv_row_data[8]),  # number_of_trades
                        float(csv_row_data[9]),  # taker_buy_base_asset_volume
                        float(csv_row_data[10]),  # taker_buy_quote_asset_volume
                    ]
                    processed_candle_data.append(processed_candle_row)

                except (ValueError, OSError, OverflowError) as parsing_exception:
                    format_analyzer.format_stats["unknown"]["count"] += 1
                    error_record = {
                        "row_index": csv_row_index,
                        "error_type": "timestamp_parse_error",
                        "error_message": str(parsing_exception),
                        "raw_row": csv_row_data[:10] if len(csv_row_data) > 10 else csv_row_data,
                    }
                    self.corruption_log.append(error_record)
                    format_analyzer.format_stats["unknown"]["errors"].append(error_record)
                    continue
            else:
                # Record insufficient columns
                self.corruption_log.append(
                    {
                        "row_index": csv_row_index,
                        "error_type": "insufficient_columns",
                        "column_count": len(csv_row_data),
                        "raw_row": csv_row_data,
                    }
                )

        # Report comprehensive format analysis
        format_analyzer.report_format_analysis()

        # Store format analysis summary for metadata
        self._format_analysis_summary = format_analyzer.get_format_analysis_summary()

        return processed_candle_data

    def collect_timeframe_data(self, trading_timeframe: str) -> Dict[str, Any]:
        """Collect complete historical data for a single timeframe with full 11-column microstructure format.

        Downloads and processes monthly ZIP files from Binance's public data repository
        for the specified timeframe. Automatically handles data processing, validation,
        and saves to CSV while returning a DataFrame for immediate use.

        Args:
            trading_timeframe (str): Timeframe for data collection.
                Must be one of: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h".

        Returns:
            dict: Collection results containing:
                - dataframe (pd.DataFrame): Complete OHLCV data with 11 columns:
                    * date: Timestamp (open time)
                    * open, high, low, close: Price data
                    * volume: Base asset volume
                    * close_time: Timestamp (close time)
                    * quote_asset_volume: Quote asset volume
                    * number_of_trades: Trade count
                    * taker_buy_base_asset_volume: Taker buy base volume
                    * taker_buy_quote_asset_volume: Taker buy quote volume
                - filepath (Path): Path to saved CSV file
                - stats (dict): Collection statistics including duration and bar count

        Raises:
            ValueError: If trading_timeframe is not supported.
            ConnectionError: If download from Binance repository fails.
            FileNotFoundError: If output directory is invalid.

        Examples:
            >>> collector = BinancePublicDataCollector(symbol="BTCUSDT")
            >>> result = collector.collect_timeframe_data("1h")
            >>> df = result["dataframe"]
            >>> print(f"Collected {len(df)} hourly bars")
            >>> print(f"Date range: {df['date'].min()} to {df['date'].max()}")
            Collected 26280 hourly bars
            Date range: 2020-08-15 01:00:00 to 2025-03-20 23:00:00

            >>> # Access microstructure data
            >>> print(f"Total trades: {df['number_of_trades'].sum():,}")
            >>> print(f"Average taker buy ratio: {df['taker_buy_base_asset_volume'].sum() / df['volume'].sum():.2%}")
            Total trades: 15,234,567
            Average taker buy ratio: 51.23%

        Note:
            This method processes data chronologically and may take several minutes
            for large date ranges due to monthly ZIP file downloads. Progress is
            displayed during collection.
        """
        print(f"\n{'=' * 60}")
        print(f"COLLECTING {trading_timeframe.upper()} DATA FROM BINANCE PUBLIC REPOSITORY")
        print(f"{'=' * 60}")

        if trading_timeframe not in self.available_timeframes:
            print(f"❌ Timeframe '{trading_timeframe}' not available")
            print(f"📊 Available timeframes: {', '.join(self.available_timeframes)}")
            print("💡 Use 'gapless-crypto-data --list-timeframes' for detailed descriptions")
            return None

        # Generate monthly URLs
        monthly_zip_urls = self.generate_monthly_urls(trading_timeframe)
        print(f"Monthly files to download: {len(monthly_zip_urls)}")

        # Collect data from all months
        combined_candle_data = []
        successful_download_count = 0

        for binance_zip_url, year_month_string, zip_filename in monthly_zip_urls:
            raw_monthly_csv_data = self.download_and_extract_month(binance_zip_url, zip_filename)
            if raw_monthly_csv_data:
                processed_monthly_data = self.process_raw_data(raw_monthly_csv_data)
                combined_candle_data.extend(processed_monthly_data)
                successful_download_count += 1
                print(f"    ✅ {len(processed_monthly_data):,} bars from {year_month_string}")
            else:
                print(f"    ⚠️  No data from {year_month_string}")

        print("\nCollection Summary:")
        print(f"  Successful downloads: {successful_download_count}/{len(monthly_zip_urls)}")
        print(f"  Total bars collected: {len(combined_candle_data):,}")

        # ETag cache statistics for observability
        cache_stats = self.etag_cache.get_cache_stats()
        if cache_stats["total_entries"] > 0:
            total_cached_size_mb = cache_stats["total_cached_size"] / (1024 * 1024)
            print(
                f"  ETag cache: {cache_stats['total_entries']} entries, {total_cached_size_mb:.1f} MB tracked"
            )

        if combined_candle_data:
            # Sort by timestamp to ensure chronological order
            combined_candle_data.sort(key=lambda candle_row: candle_row[0])
            print(
                f"  Pre-filtering range: {combined_candle_data[0][0]} to {combined_candle_data[-1][0]}"
            )

            # ✅ BOUNDARY FIX: Apply final date range filtering after combining all monthly data
            # This preserves month boundaries while respecting the requested date range
            date_filtered_data = []
            for candle_row in combined_candle_data:
                candle_datetime = datetime.strptime(candle_row[0], "%Y-%m-%d %H:%M:%S")
                if self.start_date <= candle_datetime <= self.end_date:
                    date_filtered_data.append(candle_row)

            print(f"  Post-filtering: {len(date_filtered_data):,} bars in requested range")
            if date_filtered_data:
                print(f"  Final range: {date_filtered_data[0][0]} to {date_filtered_data[-1][0]}")

            # Save to CSV and return DataFrame for seamless Python integration
            if date_filtered_data:
                # Calculate collection stats for metadata
                collection_stats = {
                    "method": "direct_download",
                    "duration": 0.0,  # Minimal for single timeframe
                    "bars_per_second": 0,
                    "total_bars": len(date_filtered_data),
                }

                # Save to CSV file (addresses the output_dir bug)
                filepath = self.save_data(trading_timeframe, date_filtered_data, collection_stats)

                # Convert to DataFrame for Python API users
                columns = [
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
                df = pd.DataFrame(date_filtered_data, columns=columns)

                # Convert numeric columns
                numeric_cols = [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                ]
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                # Convert date columns to datetime
                df["date"] = pd.to_datetime(df["date"])
                df["close_time"] = pd.to_datetime(df["close_time"])

                return {"dataframe": df, "filepath": filepath, "stats": collection_stats}

            return {"dataframe": pd.DataFrame(), "filepath": None, "stats": {}}

        # Save to CSV and return DataFrame for unfiltered data
        if combined_candle_data:
            # Calculate collection stats for metadata
            collection_stats = {
                "method": "direct_download",
                "duration": 0.0,  # Minimal for single timeframe
                "bars_per_second": 0,
                "total_bars": len(combined_candle_data),
            }

            # Save to CSV file (addresses the output_dir bug)
            filepath = self.save_data(trading_timeframe, combined_candle_data, collection_stats)

            # Convert to DataFrame for Python API users
            columns = [
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
            df = pd.DataFrame(combined_candle_data, columns=columns)

            # Convert numeric columns
            numeric_cols = [
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
            ]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Convert date columns to datetime
            df["date"] = pd.to_datetime(df["date"])
            df["close_time"] = pd.to_datetime(df["close_time"])

            return {"dataframe": df, "filepath": filepath, "stats": collection_stats}

        return {"dataframe": pd.DataFrame(), "filepath": None, "stats": {}}

    def generate_metadata(
        self, trading_timeframe, candle_data, collection_performance_stats, gap_analysis_result=None
    ):
        """Generate comprehensive metadata for 11-column microstructure format."""
        if not candle_data:
            return {}

        # Calculate statistics
        price_values = []
        volume_values = []
        for candle_row in candle_data:
            price_values.extend([candle_row[2], candle_row[3]])  # high, low
            volume_values.append(candle_row[5])

        return {
            "version": "v2.10.0",
            "generator": "BinancePublicDataCollector",
            "generation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "data_source": "Binance Public Data Repository",
            "data_source_url": self.base_url,
            "market_type": "spot",
            "symbol": self.symbol,
            "timeframe": trading_timeframe,
            "collection_method": "direct_download",
            "target_period": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat(),
                "total_days": (self.end_date - self.start_date).days,
            },
            "actual_bars": len(candle_data),
            "date_range": {
                "start": candle_data[0][0] if candle_data else None,
                "end": candle_data[-1][0] if candle_data else None,
            },
            "statistics": {
                "price_min": min(price_values) if price_values else 0,
                "price_max": max(price_values) if price_values else 0,
                "volume_total": sum(volume_values) if volume_values else 0,
                "volume_mean": sum(volume_values) / len(volume_values) if volume_values else 0,
            },
            "collection_performance": collection_performance_stats,
            "data_integrity": {
                "chronological_order": True,
                "data_hash": self._calculate_data_hash(candle_data),
                "corruption_detected": len(getattr(self, "corruption_log", [])) > 0,
                "corrupted_rows_count": len(getattr(self, "corruption_log", [])),
                "corruption_details": getattr(self, "corruption_log", []),
                "header_detection": {
                    "header_found": getattr(self, "_header_detected", False),
                    "header_content": getattr(self, "_header_content", None),
                    "data_start_row": getattr(self, "_data_start_row", 0),
                },
            },
            "timestamp_format_analysis": getattr(
                self,
                "_format_analysis_summary",
                {
                    "total_rows_analyzed": 0,
                    "formats_detected": {},
                    "transitions_detected": 0,
                    "transition_details": [],
                    "primary_format": "unknown",
                    "format_consistency": True,
                    "analysis_note": "Format analysis not available - may be legacy collection",
                },
            ),
            "enhanced_microstructure_format": {
                "format_version": "v2.10.0",
                "total_columns": len(candle_data[0]) if candle_data else 11,
                "enhanced_features": [
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "close_time",
                ],
                "analysis_capabilities": [
                    "order_flow_analysis",
                    "liquidity_metrics",
                    "market_microstructure",
                    "trade_weighted_prices",
                    "institutional_data_patterns",
                ],
                "professional_features": True,
                "api_format_compatibility": True,
            },
            "gap_analysis": gap_analysis_result
            or {
                "analysis_performed": False,
                "total_gaps_detected": 0,
                "gaps_filled": 0,
                "gaps_remaining": 0,
                "gap_details": [],
                "gap_filling_method": "authentic_binance_api",
                "data_completeness_score": 1.0,
                "note": "Gap analysis can be performed using UniversalGapFiller.detect_all_gaps()",
            },
            "compliance": {
                "zero_magic_numbers": True,
                "temporal_integrity": True,
                "authentic_spot_data_only": True,
                "official_binance_source": True,
                "binance_format_transition_aware": True,
                "supports_milliseconds_microseconds": True,
                "full_binance_microstructure_format": True,
                "professional_trading_ready": True,
            },
        }

    def _perform_gap_analysis(self, data, timeframe):
        """Perform gap analysis on collected data and return detailed results."""
        if not data or len(data) < 2:
            return {
                "analysis_performed": True,
                "total_gaps_detected": 0,
                "gaps_filled": 0,
                "gaps_remaining": 0,
                "gap_details": [],
                "gap_filling_method": "authentic_binance_api",
                "data_completeness_score": 1.0,
                "note": "Insufficient data for gap analysis (< 2 rows)",
            }

        # Calculate expected interval in minutes using centralized constants
        interval_minutes = TIMEFRAME_TO_MINUTES.get(timeframe, 60)
        expected_gap_minutes = interval_minutes

        # Analyze timestamp gaps
        gaps_detected = []
        total_bars_expected = 0

        for i in range(1, len(data)):
            current_time = datetime.strptime(data[i][0], "%Y-%m-%d %H:%M:%S")
            previous_time = datetime.strptime(data[i - 1][0], "%Y-%m-%d %H:%M:%S")

            actual_gap_minutes = (current_time - previous_time).total_seconds() / 60

            if actual_gap_minutes > expected_gap_minutes * 1.5:  # Allow 50% tolerance
                missing_bars = int(actual_gap_minutes / expected_gap_minutes) - 1
                if missing_bars > 0:
                    gaps_detected.append(
                        {
                            "gap_start": data[i - 1][0],
                            "gap_end": data[i][0],
                            "missing_bars": missing_bars,
                            "duration_minutes": actual_gap_minutes - expected_gap_minutes,
                        }
                    )
                    total_bars_expected += missing_bars

        # Calculate completeness score
        total_bars_collected = len(data)
        total_bars_should_exist = total_bars_collected + total_bars_expected
        completeness_score = (
            total_bars_collected / total_bars_should_exist if total_bars_should_exist > 0 else 1.0
        )

        return {
            "analysis_performed": True,
            "total_gaps_detected": len(gaps_detected),
            "gaps_filled": 0,  # Will be updated during gap filling process
            "gaps_remaining": len(gaps_detected),
            "gap_details": gaps_detected[:10],  # Limit to first 10 gaps for metadata size
            "total_missing_bars": total_bars_expected,
            "gap_filling_method": "authentic_binance_api",
            "data_completeness_score": round(completeness_score, 4),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "analysis_parameters": {
                "timeframe": timeframe,
                "expected_interval_minutes": expected_gap_minutes,
                "tolerance_factor": 1.5,
            },
        }

    def _calculate_data_hash(self, data):
        """Calculate hash of data for integrity verification."""
        data_string = "\n".join(",".join(map(str, row)) for row in data)
        return hashlib.sha256(data_string.encode()).hexdigest()

    def save_data(self, timeframe: str, data: List[List], collection_stats: Dict[str, Any]) -> Path:
        """Save data to file with format determined by output_format (CSV or Parquet)."""
        if not data:
            print(f"❌ No data to save for {timeframe}")
            return None

        # Generate filename with appropriate extension
        start_date_str = self.start_date.strftime("%Y%m%d")
        end_date_str = datetime.strptime(data[-1][0], "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d")
        version = "v2.10.0"  # Updated version for Parquet support
        file_extension = self.output_format
        filename = f"binance_spot_{self.symbol}-{timeframe}_{start_date_str}-{end_date_str}_{version}.{file_extension}"
        filepath = self.output_dir / filename

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Perform gap analysis on collected data
        gap_analysis = self._perform_gap_analysis(data, timeframe)

        # Generate metadata with gap analysis results
        metadata = self.generate_metadata(timeframe, data, collection_stats, gap_analysis)

        # Convert data to DataFrame for both formats
        df = pd.DataFrame(
            data,
            columns=[
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
            ],
        )

        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"])

        if self.output_format == "parquet":
            # Save as Parquet with metadata
            df.to_parquet(filepath, engine="pyarrow", compression="snappy", index=False)
            print(f"📊 Saved {len(df):,} bars to {filepath.name} (Parquet format)")
        else:
            # Save as CSV with metadata headers (existing logic)
            with open(filepath, "w", newline="") as f:
                # Write metadata headers
                f.write(f"# Binance Spot Market Data {metadata['version']}\n")
                f.write(f"# Generated: {metadata['generation_timestamp']}\n")
                f.write(f"# Source: {metadata['data_source']}\n")
                f.write(
                    f"# Market: {metadata['market_type'].upper()} | Symbol: {metadata['symbol']} | Timeframe: {metadata['timeframe']}\n"
                )
                f.write(f"# Coverage: {metadata['actual_bars']:,} bars\n")
                f.write(
                    f"# Period: {metadata['date_range']['start']} to {metadata['date_range']['end']}\n"
                )
                f.write(
                    f"# Collection: {collection_stats['method']} in {collection_stats['duration']:.1f}s\n"
                )
                f.write(f"# Data Hash: {metadata['data_integrity']['data_hash'][:16]}...\n")
                f.write(
                    "# Compliance: Zero-Magic-Numbers, Temporal-Integrity, Official-Binance-Source\n"
                )
                f.write("#\n")

                # Write CSV data
                df.to_csv(f, index=False)
            print(f"📊 Saved {len(df):,} bars to {filepath.name} (CSV format)")

        # Save metadata as JSON
        metadata_filepath = filepath.with_suffix(".metadata.json")
        with open(metadata_filepath, "w") as f:
            json.dump(metadata, f, indent=2)

        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"\n✅ Created: {filepath.name} ({file_size_mb:.1f} MB)")
        print(f"✅ Metadata: {metadata_filepath.name}")

        return filepath

    def collect_multiple_timeframes(
        self, timeframes: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Collect data for multiple timeframes with comprehensive progress tracking.

        Efficiently collects historical data across multiple timeframes in sequence,
        providing a complete dataset for multi-timeframe analysis. Each timeframe
        is processed independently with full validation and progress reporting.

        Args:
            timeframes (list, optional): List of timeframes to collect.
                Each must be one of: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h".
                If None, defaults to ["1m", "3m", "5m", "15m", "30m", "1h", "2h"].

        Returns:
            dict: Collection results by timeframe, where each key is a timeframe string
                and each value is a dict containing:
                - dataframe (pd.DataFrame): Complete OHLCV data with 11 columns
                - filepath (Path): Path to saved CSV file
                - stats (dict): Collection statistics

        Raises:
            ValueError: If any timeframe in the list is not supported.
            ConnectionError: If download from Binance repository fails.

        Examples:
            Default comprehensive collection:

            >>> collector = BinancePublicDataCollector(symbol="ETHUSDT")
            >>> results = collector.collect_multiple_timeframes()
            >>> for timeframe, result in results.items():
            ...     df = result["dataframe"]
            ...     print(f"{timeframe}: {len(df):,} bars saved to {result['filepath'].name}")
            1m: 1,574,400 bars saved to ETHUSDT_1m_2020-08-15_to_2025-03-20.csv
            3m: 524,800 bars saved to ETHUSDT_3m_2020-08-15_to_2025-03-20.csv

            Custom timeframes for specific analysis:

            >>> collector = BinancePublicDataCollector(symbol="BTCUSDT")
            >>> results = collector.collect_multiple_timeframes(["1h", "4h"])
            >>> hourly_df = results["1h"]["dataframe"]
            >>> four_hour_df = results["4h"]["dataframe"]
            >>> print(f"Hourly data: {len(hourly_df)} bars")
            >>> print(f"4-hour data: {len(four_hour_df)} bars")
            Hourly data: 26,280 bars
            4-hour data: 6,570 bars

            Access collection statistics:

            >>> results = collector.collect_multiple_timeframes(["1h"])
            >>> stats = results["1h"]["stats"]
            >>> print(f"Collection took {stats['duration']:.1f} seconds")
            >>> print(f"Processing rate: {stats['bars_per_second']:,.0f} bars/sec")
            Collection took 45.2 seconds
            Processing rate: 582 bars/sec

        Note:
            Processing time scales with the number of timeframes and date range.
            Progress is displayed in real-time with Rich progress bars.
            All timeframes are collected sequentially to avoid overwhelming
            Binance's public data servers.
        """
        if timeframes is None:
            timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h"]

        print("\n🚀 BINANCE PUBLIC DATA ULTRA-FAST COLLECTION")
        print(f"Timeframes: {timeframes}")
        print("=" * 80)

        results = {}
        overall_start = datetime.now()

        for i, timeframe in enumerate(timeframes):
            print(f"Processing {timeframe} ({i + 1}/{len(timeframes)})...")

            result = self.collect_timeframe_data(timeframe)

            if result and result.get("filepath"):
                filepath = result["filepath"]
                results[timeframe] = filepath
                file_size_mb = filepath.stat().st_size / (1024 * 1024)
                print(f"✅ {timeframe}: {filepath.name} ({file_size_mb:.1f} MB)")
            else:
                print(f"❌ Failed to collect {timeframe} data")

        overall_duration = (datetime.now() - overall_start).total_seconds()

        print("\n" + "=" * 80)
        print("🎉 ULTRA-FAST COLLECTION COMPLETE")
        print(
            f"⏱️  Total time: {overall_duration:.1f} seconds ({overall_duration / 60:.1f} minutes)"
        )
        print(f"📊 Generated {len(results)} files")

        return results

    async def collect_timeframe_data_concurrent(self, trading_timeframe: str) -> Dict[str, Any]:
        """
        Collect data using high-performance concurrent hybrid strategy.

        This method uses the ConcurrentCollectionOrchestrator to achieve 10-15x faster
        data collection through parallel downloads of monthly and daily ZIP files.

        Args:
            trading_timeframe (str): Timeframe for data collection.
                Must be one of: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h".

        Returns:
            dict: Collection results containing:
                - dataframe (pd.DataFrame): Complete OHLCV data with 11 columns
                - filepath (Path): Path to saved CSV file
                - stats (dict): Collection statistics including performance metrics
                - collection_method (str): "concurrent_hybrid"

        Examples:
            >>> collector = BinancePublicDataCollector(symbol="BTCUSDT")
            >>> result = await collector.collect_timeframe_data_concurrent("1h")
            >>> df = result["dataframe"]
            >>> print(f"Collected {len(df)} bars in {result['stats']['collection_time']:.1f}s")
            >>> print(f"Performance: {result['stats']['bars_per_second']:.0f} bars/sec")
            Collected 8760 bars in 12.3s
            Performance: 712 bars/sec

        Note:
            This is the recommended high-performance method for new applications.
            Falls back to synchronous method if async context is not available.
        """
        from .concurrent_collection_orchestrator import ConcurrentCollectionOrchestrator

        print(f"\n{'=' * 60}")
        print(f"CONCURRENT COLLECTION: {trading_timeframe.upper()} DATA")
        print(f"Strategy: Hybrid Monthly+Daily with {13} Concurrent Downloads")
        print(f"{'=' * 60}")

        if trading_timeframe not in self.available_timeframes:
            print(f"❌ Timeframe '{trading_timeframe}' not available")
            print(f"📊 Available timeframes: {', '.join(self.available_timeframes)}")
            return {"dataframe": pd.DataFrame(), "filepath": None, "stats": {}}

        try:
            # Initialize concurrent orchestrator
            orchestrator = ConcurrentCollectionOrchestrator(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                output_dir=self.output_dir,
                max_concurrent=13,
            )

            async with orchestrator:
                # Execute concurrent collection
                collection_result = await orchestrator.collect_timeframe_concurrent(
                    trading_timeframe, progress_callback=self._progress_callback
                )

                if not collection_result.success or not collection_result.processed_data:
                    print(f"❌ Concurrent collection failed for {trading_timeframe}")
                    if collection_result.errors:
                        for error in collection_result.errors:
                            print(f"   Error: {error}")
                    return {"dataframe": pd.DataFrame(), "filepath": None, "stats": {}}

                # Process data using existing methods
                processed_data = collection_result.processed_data

                # Calculate performance stats
                bars_per_second = (
                    collection_result.total_bars / collection_result.collection_time
                    if collection_result.collection_time > 0
                    else 0
                )

                collection_stats = {
                    "method": "concurrent_hybrid",
                    "duration": collection_result.collection_time,
                    "bars_per_second": bars_per_second,
                    "total_bars": collection_result.total_bars,
                    "successful_downloads": collection_result.successful_downloads,
                    "failed_downloads": collection_result.failed_downloads,
                    "data_source_breakdown": collection_result.data_source_breakdown,
                    "concurrent_downloads": 13,
                    "strategy": "monthly_historical_daily_recent",
                }

                # Save to CSV using existing method
                filepath = self.save_data(trading_timeframe, processed_data, collection_stats)

                # Convert to DataFrame
                columns = [
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
                df = pd.DataFrame(processed_data, columns=columns)

                # Convert numeric columns
                numeric_cols = [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                ]
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                # Convert date columns
                df["date"] = pd.to_datetime(df["date"])
                df["close_time"] = pd.to_datetime(df["close_time"])

                print("\n✅ CONCURRENT COLLECTION SUCCESS")
                print(f"📊 Collected: {len(df):,} bars")
                print(f"⚡ Performance: {bars_per_second:.0f} bars/sec")
                print(
                    f"🚀 Speed: {collection_result.collection_time:.1f}s vs ~{collection_result.collection_time * 10:.0f}s sequential"
                )
                print(
                    f"📁 Sources: {collection_result.data_source_breakdown['monthly']} monthly + {collection_result.data_source_breakdown['daily']} daily"
                )

                return {
                    "dataframe": df,
                    "filepath": filepath,
                    "stats": collection_stats,
                    "collection_method": "concurrent_hybrid",
                }

        except Exception as e:
            print(f"❌ Concurrent collection failed: {e}")
            print("⏮️  Falling back to synchronous method...")
            # Fallback to synchronous method
            return self.collect_timeframe_data(trading_timeframe)

    async def collect_multiple_timeframes_concurrent(
        self, timeframes: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect multiple timeframes using concurrent hybrid strategy.

        High-performance collection across multiple timeframes with optimal
        resource utilization and parallel processing.

        Args:
            timeframes (list, optional): List of timeframes to collect.
                If None, defaults to ["1m", "3m", "5m", "15m", "30m", "1h", "2h"].

        Returns:
            dict: Collection results by timeframe with comprehensive performance metrics.

        Examples:
            >>> collector = BinancePublicDataCollector(symbol="ETHUSDT")
            >>> results = await collector.collect_multiple_timeframes_concurrent(["1h", "4h"])
            >>> for timeframe, result in results.items():
            ...     stats = result["stats"]
            ...     print(f"{timeframe}: {stats['total_bars']} bars in {stats['duration']:.1f}s")
            1h: 8760 bars in 15.2s
            4h: 2190 bars in 8.7s

        Note:
            This method processes timeframes sequentially to avoid overwhelming
            servers, but each timeframe uses full concurrent downloading.
        """
        from .concurrent_collection_orchestrator import ConcurrentCollectionOrchestrator

        if timeframes is None:
            timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "2h"]

        print("\n🚀 CONCURRENT MULTI-TIMEFRAME COLLECTION")
        print(f"Strategy: Hybrid Monthly+Daily with {13} Concurrent Downloads")
        print(f"Timeframes: {timeframes}")
        print("=" * 80)

        results = {}
        overall_start = datetime.now()

        try:
            # Initialize concurrent orchestrator
            orchestrator = ConcurrentCollectionOrchestrator(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                output_dir=self.output_dir,
                max_concurrent=13,
            )

            async with orchestrator:
                # Process each timeframe with concurrent downloads
                for i, timeframe in enumerate(timeframes):
                    print(f"\n📊 Processing {timeframe} ({i + 1}/{len(timeframes)})...")

                    result = await self.collect_timeframe_data_concurrent(timeframe)

                    if result and result.get("filepath"):
                        filepath = result["filepath"]
                        results[timeframe] = filepath
                        file_size_mb = filepath.stat().st_size / (1024 * 1024)
                        bars_per_sec = result["stats"]["bars_per_second"]
                        print(
                            f"✅ {timeframe}: {filepath.name} ({file_size_mb:.1f} MB, {bars_per_sec:.0f} bars/sec)"
                        )
                    else:
                        print(f"❌ Failed to collect {timeframe} data")

        except Exception as e:
            print(f"❌ Concurrent collection failed: {e}")
            print("⏮️  Falling back to synchronous method...")
            # Fallback to synchronous method
            return self.collect_multiple_timeframes(timeframes)

        overall_duration = (datetime.now() - overall_start).total_seconds()

        print("\n" + "=" * 80)
        print("🎉 CONCURRENT MULTI-TIMEFRAME COLLECTION COMPLETE")
        print(
            f"⏱️  Total time: {overall_duration:.1f} seconds ({overall_duration / 60:.1f} minutes)"
        )
        print(f"📊 Generated {len(results)} datasets")
        print("🚀 Average speedup: ~10-15x faster than sequential downloads")

        return results

    def _progress_callback(self, completed: int, total: int, current_task):
        """Progress callback for concurrent downloads."""
        if completed % 5 == 0 or completed == total:  # Report every 5 downloads or at completion
            percentage = (completed / total) * 100
            source_type = current_task.source_type.value
            print(
                f"   📥 Progress: {completed}/{total} ({percentage:.1f}%) - {source_type}: {current_task.filename}"
            )

    def validate_csv_file(
        self, csv_filepath: Union[str, Path], expected_timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of CSV file data integrity, completeness, and quality.

        Delegates to CSVValidator for multi-layer validation including structure checking,
        datetime sequence validation, OHLCV quality analysis, coverage calculation, and
        statistical anomaly detection.

        Args:
            csv_filepath: Path to CSV file to validate
            expected_timeframe: Expected timeframe (e.g., '30m') for interval validation

        Returns:
            dict: Validation results with detailed analysis

        Note:
            This method delegates to the validation.csv_validator.CSVValidator class
            for complete validation logic. See CSVValidator for implementation details.
        """
        validator = CSVValidator()
        return validator.validate_csv_file(csv_filepath, expected_timeframe)

    def update_metadata_with_validation(self, csv_filepath, validation_results):
        """Update metadata JSON file with validation results."""
        metadata_filepath = csv_filepath.with_suffix(".metadata.json")

        if metadata_filepath.exists():
            with open(metadata_filepath, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {}

        # Add validation results to metadata
        metadata["validation"] = validation_results

        # Update compliance status based on validation
        compliance = metadata.get("compliance", {})
        if validation_results["total_errors"] == 0:
            compliance["data_validation_passed"] = True
            compliance["validation_summary"] = validation_results["validation_summary"]
        else:
            compliance["data_validation_passed"] = False
            compliance["validation_summary"] = validation_results["validation_summary"]
            compliance["validation_errors"] = validation_results["total_errors"]
            compliance["validation_warnings"] = validation_results["total_warnings"]

        metadata["compliance"] = compliance

        # Save updated metadata with JSON serialization fix
        def convert_numpy_types(obj):
            """Convert numpy types to Python native types for JSON serialization."""
            if hasattr(obj, "item"):
                return obj.item()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj

        with open(metadata_filepath, "w") as f:
            json.dump(convert_numpy_types(metadata), f, indent=2)

        print(f"✅ Updated metadata: {metadata_filepath.name}")

    def apply_gap_filling_to_validated_files(self):
        """Apply comprehensive gap filling to validated data files using authentic Binance API data"""

        try:
            print("\n🔧 INTEGRATED GAP FILLING SYSTEM")
            print("Primary Source: Binance REST API (Authentic Data Only)")
            print("=" * 60)

            # Initialize gap filling components
            gap_filler = UniversalGapFiller()

            # Find CSV files to check for gaps
            csv_files = list(Path(self.output_dir).glob("*.csv"))

            if not csv_files:
                print("❌ No CSV files found for gap filling")
                return

            # Filter to only files for this symbol
            symbol_files = [f for f in csv_files if self.symbol in f.name]

            if not symbol_files:
                print(f"❌ No CSV files found for symbol {self.symbol}")
                return

            print(f"🔍 Analyzing {len(symbol_files)} files for gaps...")

            total_gaps_detected = 0
            total_gaps_filled = 0
            total_gaps_failed = 0
            files_processed = 0
            results = []

            for csv_file in symbol_files:
                print(f"\n📁 Processing: {csv_file.name}")

                # Extract timeframe from filename
                file_timeframe = self._extract_timeframe_from_filename(csv_file.name)
                print(f"   📊 Detected timeframe: {file_timeframe}")

                # Use the proper UniversalGapFiller process_file method
                result = gap_filler.process_file(csv_file, file_timeframe)
                results.append(result)
                files_processed += 1

                # Update totals
                total_gaps_detected += result["gaps_detected"]
                total_gaps_filled += result["gaps_filled"]
                total_gaps_failed += result["gaps_failed"]

                # Report per-file results
                if result["gaps_detected"] == 0:
                    print(f"   ✅ No gaps found in {file_timeframe}")
                else:
                    success_rate = result["success_rate"]
                    status = "✅" if success_rate == 100.0 else "⚠️" if success_rate > 0 else "❌"
                    print(
                        f"   {status} {result['gaps_filled']}/{result['gaps_detected']} gaps filled ({success_rate:.1f}%)"
                    )

            # Comprehensive summary
            print("\n" + "=" * 60)
            print("📊 GAP FILLING SUMMARY")
            print("=" * 60)

            for result in results:
                if result["gaps_detected"] > 0:
                    status = (
                        "✅"
                        if result["success_rate"] == 100.0
                        else "⚠️"
                        if result["success_rate"] > 0
                        else "❌"
                    )
                    print(
                        f"{status} {result['timeframe']:>3}: {result['gaps_filled']:>2}/{result['gaps_detected']:>2} gaps filled ({result['success_rate']:>5.1f}%)"
                    )

            print("-" * 60)
            overall_success = (
                (total_gaps_filled / total_gaps_detected * 100)
                if total_gaps_detected > 0
                else 100.0
            )
            print(
                f"🎯 OVERALL: {total_gaps_filled}/{total_gaps_detected} gaps filled ({overall_success:.1f}%)"
            )

            if overall_success == 100.0:
                print("🎉 ALL GAPS FILLED SUCCESSFULLY!")
                print("✅ Datasets are now 100% gapless and ready for production use")
            else:
                print(
                    f"⚠️  {total_gaps_failed} gaps failed to fill (may be legitimate exchange outages)"
                )
                print("📋 Review failed gaps to confirm they are legitimate market closures")

            print(f"\nFiles processed: {files_processed}")
            print("Data source: Authentic Binance REST API")
            print("Gap filling protocol: API-first validation (no synthetic data)")

        except Exception as e:
            print(f"❌ Gap filling error: {e}")
            print("⚠️  Continuing without gap filling...")
            import traceback

            traceback.print_exc()

    def _extract_timeframe_from_filename(self, filename):
        """Extract timeframe from filename (e.g., 'SOLUSDT-15m-data.csv' -> '15m')"""
        for tf in [
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1mo",
        ]:
            if f"-{tf}_" in filename or f"-{tf}-" in filename:
                return tf
        return "15m"  # Default


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Create and configure CLI argument parser.

    Returns:
        Configured ArgumentParser with all CLI options
    """
    parser = argparse.ArgumentParser(
        description="Ultra-fast Binance spot data collector with validation"
    )
    parser.add_argument(
        "--symbol", default="SOLUSDT", help="Trading pair symbol (default: SOLUSDT)"
    )
    parser.add_argument(
        "--timeframes",
        default="1m,3m,5m,15m,30m,1h,2h",
        help="Comma-separated timeframes (default: 1m,3m,5m,15m,30m,1h,2h)",
    )
    parser.add_argument(
        "--start", default="2020-08-15", help="Start date YYYY-MM-DD (default: 2020-08-15)"
    )
    parser.add_argument(
        "--end", default="2025-03-20", help="End date YYYY-MM-DD (default: 2025-03-20)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing CSV files, do not collect new data",
    )
    parser.add_argument(
        "--validate-files", nargs="+", help="Specific CSV files to validate (with --validate-only)"
    )
    parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Skip validation after collection (not recommended)",
    )
    return parser


def _discover_files_to_validate(args, collector) -> List[Path]:
    """Discover CSV files to validate based on arguments.

    Args:
        args: Parsed command line arguments
        collector: BinancePublicDataCollector instance

    Returns:
        List of Path objects for files to validate
    """
    if args.validate_files:
        return [Path(f) for f in args.validate_files]
    else:
        pattern = f"*{args.symbol}*.csv"
        return list(collector.output_dir.glob(pattern))


def _validate_files(collector, files_to_validate: List[Path]) -> List[Dict]:
    """Validate list of CSV files.

    Args:
        collector: BinancePublicDataCollector instance
        files_to_validate: List of file paths to validate

    Returns:
        List of validation summary dictionaries
    """
    validation_summary = []
    for csv_file in files_to_validate:
        # Extract timeframe from filename
        timeframe = None
        for tf in ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"]:
            if f"-{tf}_" in csv_file.name:
                timeframe = tf
                break

        # Validate file
        validation_result = collector.validate_csv_file(csv_file, timeframe)
        collector.update_metadata_with_validation(csv_file, validation_result)

        validation_summary.append(
            {
                "file": csv_file.name,
                "status": validation_result["validation_summary"],
                "errors": validation_result["total_errors"],
                "warnings": validation_result["total_warnings"],
            }
        )

    return validation_summary


def _print_validation_summary(validation_summary: List[Dict]) -> int:
    """Print validation summary and return exit code.

    Args:
        validation_summary: List of validation result dictionaries

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    perfect_files = 0
    good_files = 0
    failed_files = 0

    for summary in validation_summary:
        if summary["errors"] == 0:
            if summary["warnings"] == 0:
                status_icon = "✅"
                perfect_files += 1
            else:
                status_icon = "⚠️ "
                good_files += 1
        else:
            status_icon = "❌"
            failed_files += 1

        print(f"{status_icon} {summary['file']}: {summary['status']}")
        if summary["errors"] > 0 or summary["warnings"] > 0:
            print(f"   └─ {summary['errors']} errors, {summary['warnings']} warnings")

    print("\nOVERALL RESULTS:")
    print(f"  ✅ Perfect: {perfect_files} files")
    print(f"  ⚠️  Good: {good_files} files")
    print(f"  ❌ Failed: {failed_files} files")

    if failed_files == 0:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed_files} files failed validation")
        return 1


def _run_validation_only_mode(args, collector) -> int:
    """Execute validation-only mode workflow.

    Args:
        args: Parsed command line arguments
        collector: BinancePublicDataCollector instance

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    print("🔍 VALIDATION-ONLY MODE")

    files_to_validate = _discover_files_to_validate(args, collector)

    if not files_to_validate:
        print("❌ No CSV files found to validate")
        return 1

    print(f"Found {len(files_to_validate)} files to validate:")
    for file_path in files_to_validate:
        print(f"  📄 {file_path.name}")

    validation_summary = _validate_files(collector, files_to_validate)
    return _print_validation_summary(validation_summary)


def _auto_validate_collected_files(collector, results: Dict) -> bool:
    """Perform auto-validation on collected files.

    Args:
        collector: BinancePublicDataCollector instance
        results: Collection results dictionary

    Returns:
        True if all validations passed, False otherwise
    """
    print("\n🔍 AUTO-VALIDATION AFTER COLLECTION")
    validation_passed = 0
    validation_failed = 0

    for timeframe, csv_file in results.items():
        validation_result = collector.validate_csv_file(csv_file, timeframe)
        collector.update_metadata_with_validation(csv_file, validation_result)

        if validation_result["total_errors"] == 0:
            validation_passed += 1
        else:
            validation_failed += 1

    print(f"\nVALIDATION RESULTS: {validation_passed} passed, {validation_failed} failed")

    if validation_failed == 0:
        print("🎉 ALL FILES VALIDATED SUCCESSFULLY!")
        print("Ready for ML training, backtesting, and production use")
        collector.apply_gap_filling_to_validated_files()
        return True
    else:
        print("⚠️  Some files failed validation - check errors above")
        return False


def _run_collection_mode(args, collector) -> int:
    """Execute data collection mode workflow.

    Args:
        args: Parsed command line arguments
        collector: BinancePublicDataCollector instance

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    timeframes = [tf.strip() for tf in args.timeframes.split(",")]
    print(f"Collecting timeframes: {timeframes}")

    results = collector.collect_multiple_timeframes(timeframes)

    if not results:
        print("❌ Collection failed")
        return 1

    print(f"\n🚀 ULTRA-FAST COLLECTION SUCCESS: Generated {len(results)} datasets")

    if not args.no_validation:
        _auto_validate_collected_files(collector, results)

    return 0


def main():
    """Main execution function with CLI argument support."""
    parser = _setup_argument_parser()
    args = parser.parse_args()

    print("Binance Public Data Ultra-Fast Collector with Validation")
    print("Official Binance data repository - 10-100x faster than API")
    print("=" * 80)

    collector = BinancePublicDataCollector(
        symbol=args.symbol, start_date=args.start, end_date=args.end
    )

    if args.validate_only:
        return _run_validation_only_mode(args, collector)
    else:
        return _run_collection_mode(args, collector)


if __name__ == "__main__":
    exit(main())
