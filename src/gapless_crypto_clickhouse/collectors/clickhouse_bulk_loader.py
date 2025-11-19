"""
ClickHouse Bulk Loader for gapless-crypto-data v4.0.0.

Ultra-fast historical data ingestion from Binance Public Data Repository to ClickHouse.
Preserves 22x speedup advantage of CloudFront CDN + zero-gap guarantee via deterministic versioning.

Architecture:
    CloudFront ZIP → Extract (temp) → Parse (pandas) → Add _version → ClickHouse → Delete temp

Performance:
    - Download: 22x faster than REST API (CloudFront CDN, unchanged from QuestDB)
    - Ingestion: >100K rows/sec via clickhouse-driver bulk insert
    - Storage: No persistent intermediate files (transient extraction only)

Zero-Gap Guarantee:
    - Deterministic _version hash ensures identical writes → identical versions
    - ReplacingMergeTree merges duplicate rows with same _version
    - Query with FINAL keyword returns deduplicated results

Error Handling:
    - Raise and propagate download failures (no retry)
    - Raise and propagate extraction failures (no fallback)
    - Raise and propagate ingestion failures (no silent drops)
    - Temporary files cleaned up even on errors

SLOs:
    - Availability: CloudFront 99.99% SLA, connection failures propagate
    - Correctness: Zero-gap guarantee via deterministic versioning
    - Observability: Ingestion metrics logged at INFO level
    - Maintainability: Standard clickhouse-driver, no custom protocols

Usage:
    from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    with ClickHouseConnection() as conn:
        loader = ClickHouseBulkLoader(conn, instrument_type="spot")
        loader.ingest_month(symbol="BTCUSDT", timeframe="1h", year=2024, month=1)
"""

import hashlib
import logging
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from ..clickhouse.connection import ClickHouseConnection

logger = logging.getLogger(__name__)


class ClickHouseBulkLoader:
    """
    Bulk data loader from Binance Public Data Repository to ClickHouse.

    Downloads monthly ZIP archives from CloudFront CDN, extracts to temporary location,
    parses CSV, adds deterministic _version for deduplication, and ingests to ClickHouse.

    Attributes:
        connection: ClickHouse connection for bulk inserts
        instrument_type: 'spot' or 'futures' (ADR-0004)
        base_url: Binance Public Data Repository base URL

    Error Handling:
        - Download failures raise urllib.error.HTTPError
        - Extraction failures raise zipfile.BadZipFile
        - Ingestion failures raise ClickHouseError
        - Temporary files cleaned up in all cases

    Performance:
        - CloudFront CDN: 22x faster than REST API
        - ClickHouse bulk insert: 100-500K rows/sec
        - Memory efficient: Streaming CSV→DataFrame→ClickHouse

    Examples:
        # Single month ingestion (spot)
        with ClickHouseConnection() as conn:
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            loader.ingest_month(symbol="BTCUSDT", timeframe="1h", year=2024, month=1)

        # Single month ingestion (futures)
        with ClickHouseConnection() as conn:
            loader = ClickHouseBulkLoader(conn, instrument_type="futures")
            loader.ingest_month(symbol="BTCUSDT", timeframe="1h", year=2024, month=1)
    """

    # Binance Public Data Repository base URLs
    SPOT_BASE_URL = "https://data.binance.vision/data/spot"
    FUTURES_BASE_URL = "https://data.binance.vision/data/futures/um"  # USDT-margined

    # Supported timeframes (all 16 Binance timeframes, empirically validated ADR-0003)
    SUPPORTED_TIMEFRAMES = [
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
        "3d",  # Three-day (exotic timeframe)
        "1w",  # Weekly (exotic timeframe)
        "1mo",  # Monthly (exotic timeframe) - Binance uses "1mo" not "1M"
    ]

    def __init__(self, connection: ClickHouseConnection, instrument_type: str = "spot") -> None:
        """
        Initialize ClickHouse bulk loader.

        Args:
            connection: Active ClickHouse connection
            instrument_type: Instrument type ("spot" or "futures"), defaults to "spot"

        Raises:
            ValueError: If connection or instrument_type is invalid
        """
        if not isinstance(connection, ClickHouseConnection):
            raise ValueError(f"Expected ClickHouseConnection, got {type(connection).__name__}")

        if instrument_type not in ("spot", "futures"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. Must be 'spot' or 'futures'"
            )

        self.connection = connection
        self.instrument_type = instrument_type

        # Set base_url based on instrument_type
        self.base_url = self.SPOT_BASE_URL if instrument_type == "spot" else self.FUTURES_BASE_URL

        logger.info(
            f"ClickHouse bulk loader initialized (instrument_type={instrument_type}, base_url={self.base_url})"
        )

    def ingest_month(self, symbol: str, timeframe: str, year: int, month: int) -> int:
        """
        Ingest one month of OHLCV data from Binance Public Data Repository.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "1h")
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Number of rows ingested

        Raises:
            ValueError: If parameters are invalid
            urllib.error.HTTPError: If download fails (404, 403, etc.)
            zipfile.BadZipFile: If ZIP extraction fails
            ClickHouseError: If ingestion fails

        Example:
            rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
            print(f"Ingested {rows} rows")
        """
        # Validate inputs
        symbol = symbol.upper()
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe: {timeframe}. Must be one of {self.SUPPORTED_TIMEFRAMES}"
            )
        if not (1 <= month <= 12):
            raise ValueError(f"Month must be 1-12, got {month}")

        # Construct URL
        url = (
            f"{self.base_url}/monthly/klines/"
            f"{symbol}/{timeframe}/{symbol}-{timeframe}-{year}-{month:02d}.zip"
        )

        # Use temporary directory for transient files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download ZIP
            zip_path = temp_path / f"{symbol}-{timeframe}-{year}-{month:02d}.zip"
            self._download_cloudfront(url, zip_path)

            # Extract CSV
            csv_path = self._extract_zip(zip_path, temp_path)

            # Parse CSV
            df = self._parse_csv(csv_path, symbol, timeframe)

            # Ingest to ClickHouse
            rows_ingested = self._ingest_dataframe(df)

            logger.info(
                f"Completed ingestion: {symbol} {timeframe} {year}-{month:02d} ({rows_ingested} rows)"
            )
            return rows_ingested

    def _download_cloudfront(self, url: str, dest_path: Path) -> None:
        """
        Download file from CloudFront CDN.

        Reused from QuestDBBulkLoader (CloudFront logic unchanged).
        """
        logger.info(f"Downloading from CloudFront: {url}")

        try:
            urllib.request.urlretrieve(url, dest_path)
            logger.info(f"Download complete: {dest_path.stat().st_size} bytes")
        except urllib.error.HTTPError as e:
            raise urllib.error.HTTPError(
                url=url,
                code=e.code,
                msg=f"CloudFront download failed: {e.reason}",
                hdrs=e.headers,
                fp=None,
            ) from e
        except urllib.error.URLError as e:
            raise urllib.error.URLError(
                f"Network error downloading from CloudFront: {e.reason}"
            ) from e

    def _extract_zip(self, zip_path: Path, extract_dir: Path) -> Path:
        """
        Extract ZIP archive to temporary directory.

        Reused from QuestDBBulkLoader (extraction logic unchanged).
        """
        logger.info(f"Extracting ZIP: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find CSV file
            csv_files = list(extract_dir.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError(f"No CSV file found in ZIP archive: {zip_path}")

            if len(csv_files) > 1:
                logger.warning(f"Multiple CSV files found in ZIP, using first: {csv_files[0]}")

            csv_path = csv_files[0]
            logger.info(f"Extracted CSV: {csv_path} ({csv_path.stat().st_size} bytes)")
            return csv_path

        except zipfile.BadZipFile as e:
            raise zipfile.BadZipFile(f"Corrupted ZIP file: {zip_path}") from e

    def _parse_csv(self, csv_path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Parse Binance CSV file to DataFrame.

        Reused from QuestDBBulkLoader with ADR-0004 futures support.
        Handles both spot (11-column, no header) and futures (12-column, with header).
        """
        logger.info(f"Parsing CSV: {csv_path} (instrument_type={self.instrument_type})")

        try:
            # Auto-detect CSV format by checking first line
            with open(csv_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()

            has_header = first_line.startswith("open_time")  # Futures CSV has header

            if has_header:
                # Futures format: 12 columns with header
                df = pd.read_csv(csv_path, header=0, index_col=False)

                # Validate column count (expect 12 columns)
                if len(df.columns) != 12:
                    raise ValueError(
                        f"Expected 12 columns for futures format, got {len(df.columns)}. "
                        f"Columns: {df.columns.tolist()}"
                    )

                # Drop the "ignore" column (always empty in futures CSV)
                df = df.drop(columns=["ignore"])

                # Rename futures column names to match spot format for consistency
                df = df.rename(
                    columns={
                        "count": "number_of_trades",
                        "quote_volume": "quote_asset_volume",
                        "taker_buy_volume": "taker_buy_base_asset_volume",
                        "taker_buy_quote_volume": "taker_buy_quote_asset_volume",
                    }
                )

            else:
                # Spot format: 11 columns, no header
                df = pd.read_csv(
                    csv_path,
                    header=None,
                    index_col=False,
                    names=[
                        "open_time",
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

                # Validate column count
                if len(df.columns) != 11:
                    raise ValueError(
                        f"Expected 11 columns for spot format, got {len(df.columns)}. "
                        f"Columns: {df.columns.tolist()}"
                    )

            # Convert timestamps (ms → datetime)
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
            df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

            # Drop open_time (redundant with timestamp)
            df = df.drop(columns=["open_time"])

            # Add metadata columns
            df["symbol"] = symbol
            df["timeframe"] = timeframe
            df["data_source"] = "cloudfront"
            df["instrument_type"] = self.instrument_type

            logger.info(
                f"Parsed {len(df)} rows from CSV (format={'futures' if has_header else 'spot'})"
            )
            return df

        except pd.errors.ParserError as e:
            raise pd.errors.ParserError(f"Failed to parse CSV {csv_path}: {e}") from e

    def _compute_version_hash(self, row: pd.Series) -> int:
        """
        Compute deterministic _version hash for ReplacingMergeTree deduplication.

        Creates hash from (timestamp, OHLCV, symbol, timeframe, instrument_type).
        Ensures identical writes → identical _version → consistent merge outcome.

        Args:
            row: pandas Series with OHLCV data

        Returns:
            UInt64 hash value (0 to 2^64-1)

        Example:
            row = pd.Series({'timestamp': ..., 'open': 50000, ...})
            version = self._compute_version_hash(row)  # e.g., 1234567890
        """
        # Create deterministic string from row content
        version_input = (
            f"{row['timestamp']}"
            f"{row['open']}{row['high']}{row['low']}{row['close']}{row['volume']}"
            f"{row['symbol']}{row['timeframe']}{row['instrument_type']}"
        )

        # Use SHA256 for cryptographic hash (deterministic, collision-resistant)
        hash_bytes = hashlib.sha256(version_input.encode("utf-8")).digest()

        # Convert first 8 bytes to UInt64
        version = int.from_bytes(hash_bytes[:8], byteorder="big", signed=False)

        return version

    def _ingest_dataframe(self, df: pd.DataFrame) -> int:
        """
        Ingest DataFrame to ClickHouse with deterministic versioning.

        Adds _version (deterministic hash) and _sign (1 for active rows) columns
        for ReplacingMergeTree deduplication.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Number of rows ingested

        Raises:
            ClickHouseError: If ingestion fails
        """
        if df.empty:
            logger.warning("Empty DataFrame, skipping ingestion")
            return 0

        logger.info(f"Ingesting {len(df)} rows to ClickHouse")

        try:
            # Prepare DataFrame for bulk ingestion
            df_ingest = df.copy()

            # Add deterministic _version hash (row-by-row)
            logger.debug("Computing deterministic _version hashes...")
            df_ingest["_version"] = df_ingest.apply(self._compute_version_hash, axis=1)

            # Add _sign column (1 for all active rows)
            df_ingest["_sign"] = 1

            # Convert number_of_trades to integer (schema requires Int64)
            df_ingest["number_of_trades"] = df_ingest["number_of_trades"].astype("int64")

            # Reorder columns to match ClickHouse schema
            column_order = [
                "timestamp",
                "symbol",
                "timeframe",
                "instrument_type",
                "data_source",
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
                "_version",
                "_sign",
            ]
            df_ingest = df_ingest[column_order]

            # Bulk insert to ClickHouse
            rows_inserted = self.connection.insert_dataframe(df_ingest, table="ohlcv")

            logger.info(f"Successfully ingested {rows_inserted} rows")
            return rows_inserted

        except Exception as e:
            raise RuntimeError(f"Ingestion failed for {len(df)} rows: {e}") from e
