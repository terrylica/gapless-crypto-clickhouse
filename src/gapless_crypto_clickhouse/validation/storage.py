"""DuckDB-based persistent storage for validation reports.

This module provides efficient storage and querying of CSV validation reports
using DuckDB's single-file OLAP database. Designed for AI coding agents to
analyze validation history and trends.

Examples:
    >>> from gapless_crypto_clickhouse.validation.storage import ValidationStorage
    >>> from gapless_crypto_clickhouse.validation.models import ValidationReport
    >>> from datetime import datetime, timezone
    >>>
    >>> # Initialize storage (creates DB at ~/.cache/gapless-crypto-data/validation.duckdb)
    >>> storage = ValidationStorage()
    >>>
    >>> # Create a validation report
    >>> report = ValidationReport(
    ...     validation_timestamp=datetime.now(timezone.utc),
    ...     file_path="/data/BTCUSDT-1h.csv",
    ...     file_size_mb=15.3,
    ...     symbol="BTCUSDT",
    ...     timeframe="1h",
    ...     total_bars=8760,
    ...     total_errors=0,
    ...     total_warnings=2,
    ...     validation_summary="GOOD - 2 warnings",
    ...     validation_duration_ms=123.45,
    ...     structure_validation={},
    ...     datetime_validation={},
    ...     ohlcv_validation={},
    ...     coverage_validation={},
    ...     anomaly_validation={}
    ... )
    >>>
    >>> # Store report
    >>> storage.insert_report(report)
    >>>
    >>> # Query recent validations
    >>> recent = storage.query_recent(limit=10, symbol="BTCUSDT")
    >>>
    >>> # Export to pandas for analysis
    >>> df = storage.export_to_dataframe()
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd

from .models import ValidationReport


def get_validation_db_path() -> Path:
    """Get XDG-compliant path for validation database.

    Returns:
        Path to validation.duckdb in XDG cache directory

    Examples:
        >>> path = get_validation_db_path()
        >>> str(path)
        '/Users/username/.cache/gapless-crypto-data/validation.duckdb'
    """
    cache_dir = Path.home() / ".cache" / "gapless-crypto-data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "validation.duckdb"


def extract_symbol_timeframe_from_path(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract trading pair symbol and timeframe from CSV file path.

    Supports multiple filename patterns:
    - binance_spot_BTCUSDT-1h_20240101-20240102_v2.10.0.csv
    - BTCUSDT-1h.csv
    - BTCUSDT_1h_data.csv
    - /path/to/BTCUSDT-1h.csv

    Args:
        filepath: Path to CSV file (absolute or relative)

    Returns:
        Tuple of (symbol, timeframe) where each may be None if not found

    Examples:
        >>> extract_symbol_timeframe_from_path("binance_spot_BTCUSDT-1h_20240101-20240102_v2.10.0.csv")
        ('BTCUSDT', '1h')

        >>> extract_symbol_timeframe_from_path("/data/ETHUSDT-5m.csv")
        ('ETHUSDT', '5m')

        >>> extract_symbol_timeframe_from_path("random_file.csv")
        (None, None)
    """
    # Get filename without directory
    filename = Path(filepath).name

    # Pattern 1: binance_spot_SYMBOL-TIMEFRAME_DATES_VERSION.csv
    # Example: binance_spot_BTCUSDT-1h_20240101-20240102_v2.10.0.csv
    match = re.search(r"binance_spot_([A-Z]+USDT?)-(\d+[smhd])", filename)
    if match:
        return match.group(1), match.group(2)

    # Pattern 2: SYMBOL-TIMEFRAME (with optional extensions)
    # Example: BTCUSDT-1h.csv or BTCUSDT-1h_data.csv
    match = re.search(r"([A-Z]+USDT?)-(\d+[smhd])", filename)
    if match:
        return match.group(1), match.group(2)

    # Pattern 3: SYMBOL_TIMEFRAME (underscore separator)
    # Example: BTCUSDT_1h.csv
    match = re.search(r"([A-Z]+USDT?)_(\d+[smhd])", filename)
    if match:
        return match.group(1), match.group(2)

    # Could not extract symbol/timeframe
    return None, None


class ValidationStorage:
    """DuckDB-based storage for validation reports with SQL query interface.

    Provides persistent storage of CSV validation reports with efficient querying
    capabilities for AI coding agents. Uses DuckDB's columnar storage for fast
    analytical queries over large validation histories.

    Attributes:
        db_path: Path to DuckDB database file

    Examples:
        >>> storage = ValidationStorage()
        >>> storage.insert_report(report)
        >>> recent_btc = storage.query_recent(limit=5, symbol="BTCUSDT")
        >>> failed = storage.query_by_status("FAILED")
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize ValidationStorage with DuckDB connection.

        Args:
            db_path: Optional custom database path. Defaults to XDG cache location.

        Examples:
            >>> # Use default XDG location
            >>> storage = ValidationStorage()
            >>>
            >>> # Use custom location
            >>> storage = ValidationStorage(db_path=Path("/tmp/validation.duckdb"))
        """
        self.db_path = db_path or get_validation_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create table on first use
        self._create_table()

    def _create_table(self) -> None:
        """Create validation_reports table if it doesn't exist.

        Schema matches ValidationReport Pydantic model with 30+ columns for
        efficient SQL queries. JSON columns store nested layer results.
        """
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_reports (
                    -- Metadata
                    validation_timestamp TIMESTAMP NOT NULL,
                    file_path VARCHAR NOT NULL,
                    file_size_mb DOUBLE NOT NULL,
                    validator_version VARCHAR DEFAULT '3.3.0',
                    symbol VARCHAR,
                    timeframe VARCHAR,

                    -- Core Results
                    total_bars INTEGER NOT NULL,
                    total_errors INTEGER NOT NULL,
                    total_warnings INTEGER NOT NULL,
                    validation_summary VARCHAR NOT NULL,
                    validation_duration_ms DOUBLE NOT NULL,

                    -- Layer Results (JSON columns for nested data)
                    structure_validation JSON NOT NULL,
                    datetime_validation JSON NOT NULL,
                    ohlcv_validation JSON NOT NULL,
                    coverage_validation JSON NOT NULL,
                    anomaly_validation JSON NOT NULL,

                    -- Flattened metrics for efficient querying
                    date_range_start TIMESTAMP,
                    date_range_end TIMESTAMP,
                    duration_days DOUBLE,
                    gaps_found INTEGER,
                    chronological_order BOOLEAN,

                    price_min DOUBLE,
                    price_max DOUBLE,
                    volume_min DOUBLE,
                    volume_max DOUBLE,
                    volume_mean DOUBLE,
                    ohlc_errors INTEGER,
                    negative_zero_values INTEGER,

                    expected_bars INTEGER,
                    actual_bars INTEGER,
                    coverage_percentage DOUBLE,

                    price_outliers INTEGER,
                    volume_outliers INTEGER,
                    suspicious_patterns INTEGER,

                    -- Indexing for fast queries
                    PRIMARY KEY (validation_timestamp, file_path)
                );

                -- Indexes for common query patterns
                CREATE INDEX IF NOT EXISTS idx_symbol_timeframe
                    ON validation_reports(symbol, timeframe);
                CREATE INDEX IF NOT EXISTS idx_validation_timestamp
                    ON validation_reports(validation_timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_validation_summary
                    ON validation_reports(validation_summary);
            """)

    def _convert_to_json_safe(self, obj: Any) -> Any:
        """Convert numpy/pandas types to JSON-serializable Python types.

        Args:
            obj: Object to convert (can be dict, list, numpy/pandas type, or any)

        Returns:
            JSON-serializable version of the object
        """
        import numpy as np

        if isinstance(obj, dict):
            return {key: self._convert_to_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_safe(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.bool_)):
            return bool(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        else:
            return obj

    def insert_report(self, report: ValidationReport) -> None:
        """Insert validation report into DuckDB.

        Args:
            report: ValidationReport instance to store

        Examples:
            >>> storage = ValidationStorage()
            >>> storage.insert_report(report)
        """
        with duckdb.connect(str(self.db_path)) as conn:
            # Convert Pydantic model to dict for insertion
            data = report.model_dump()

            # Convert datetime objects to ISO strings for DuckDB
            if isinstance(data["validation_timestamp"], datetime):
                data["validation_timestamp"] = data["validation_timestamp"].isoformat()
            if data.get("date_range_start") and isinstance(data["date_range_start"], datetime):
                data["date_range_start"] = data["date_range_start"].isoformat()
            if data.get("date_range_end") and isinstance(data["date_range_end"], datetime):
                data["date_range_end"] = data["date_range_end"].isoformat()

            # Convert dicts to JSON strings (with numpy/pandas type conversion)
            data["structure_validation"] = json.dumps(
                self._convert_to_json_safe(data["structure_validation"])
            )
            data["datetime_validation"] = json.dumps(
                self._convert_to_json_safe(data["datetime_validation"])
            )
            data["ohlcv_validation"] = json.dumps(
                self._convert_to_json_safe(data["ohlcv_validation"])
            )
            data["coverage_validation"] = json.dumps(
                self._convert_to_json_safe(data["coverage_validation"])
            )
            data["anomaly_validation"] = json.dumps(
                self._convert_to_json_safe(data["anomaly_validation"])
            )

            # Build INSERT statement
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = list(data.values())

            conn.execute(
                f"INSERT INTO validation_reports ({columns}) VALUES ({placeholders})", values
            )

    def query_recent(
        self, limit: int = 10, symbol: Optional[str] = None, timeframe: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query most recent validation reports.

        Args:
            limit: Maximum number of reports to return
            symbol: Optional filter by trading pair symbol
            timeframe: Optional filter by timeframe

        Returns:
            List of validation report dicts ordered by timestamp (newest first)

        Examples:
            >>> # Get 10 most recent validations
            >>> storage.query_recent(limit=10)

            >>> # Get recent BTCUSDT validations
            >>> storage.query_recent(limit=5, symbol="BTCUSDT")

            >>> # Get recent 1h validations
            >>> storage.query_recent(limit=5, timeframe="1h")
        """
        with duckdb.connect(str(self.db_path)) as conn:
            query = "SELECT * FROM validation_reports WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY validation_timestamp DESC LIMIT ?"
            params.append(limit)

            result = conn.execute(query, params).fetchall()
            columns = [desc[0] for desc in conn.description]

            return [dict(zip(columns, row, strict=False)) for row in result]

    def query_by_date_range(
        self, start: datetime, end: datetime, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query validations within a date range.

        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            symbol: Optional filter by trading pair symbol

        Returns:
            List of validation report dicts within date range

        Examples:
            >>> from datetime import datetime
            >>> start = datetime(2025, 1, 1)
            >>> end = datetime(2025, 1, 31)
            >>> storage.query_by_date_range(start, end, symbol="BTCUSDT")
        """
        with duckdb.connect(str(self.db_path)) as conn:
            query = """
                SELECT * FROM validation_reports
                WHERE validation_timestamp >= ? AND validation_timestamp <= ?
            """
            params = [start.isoformat(), end.isoformat()]

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            query += " ORDER BY validation_timestamp DESC"

            result = conn.execute(query, params).fetchall()
            columns = [desc[0] for desc in conn.description]

            return [dict(zip(columns, row, strict=False)) for row in result]

    def query_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Query validations by summary status.

        Args:
            status: Validation status to filter by (PERFECT, GOOD, FAILED)

        Returns:
            List of validation report dicts matching status

        Examples:
            >>> # Find all failed validations
            >>> storage.query_by_status("FAILED")

            >>> # Find all perfect validations
            >>> storage.query_by_status("PERFECT")
        """
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute(
                "SELECT * FROM validation_reports WHERE validation_summary LIKE ? ORDER BY validation_timestamp DESC",
                [f"{status}%"],
            ).fetchall()
            columns = [desc[0] for desc in conn.description]

            return [dict(zip(columns, row, strict=False)) for row in result]

    def export_to_dataframe(
        self, symbol: Optional[str] = None, timeframe: Optional[str] = None
    ) -> pd.DataFrame:
        """Export validation reports to pandas DataFrame for analysis.

        Args:
            symbol: Optional filter by trading pair symbol
            timeframe: Optional filter by timeframe

        Returns:
            Pandas DataFrame with all validation reports

        Examples:
            >>> # Export all validations
            >>> df = storage.export_to_dataframe()
            >>>
            >>> # Export BTCUSDT validations
            >>> df = storage.export_to_dataframe(symbol="BTCUSDT")
            >>>
            >>> # Analyze validation trends
            >>> df.groupby("symbol")["total_errors"].mean()
        """
        with duckdb.connect(str(self.db_path)) as conn:
            query = "SELECT * FROM validation_reports WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY validation_timestamp DESC"

            return conn.execute(query, params).df()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about validation history.

        Returns:
            Dictionary with aggregate statistics:
            - total_validations: Total number of validations stored
            - symbols: List of unique symbols validated
            - timeframes: List of unique timeframes validated
            - avg_errors: Average errors per validation
            - avg_warnings: Average warnings per validation
            - status_distribution: Count by validation_summary

        Examples:
            >>> stats = storage.get_summary_stats()
            >>> stats["total_validations"]
            1247
            >>> stats["symbols"]
            ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        """
        with duckdb.connect(str(self.db_path)) as conn:
            # Get total count
            total = conn.execute("SELECT COUNT(*) FROM validation_reports").fetchone()[0]

            # Get unique symbols and timeframes
            symbols = conn.execute(
                "SELECT DISTINCT symbol FROM validation_reports WHERE symbol IS NOT NULL ORDER BY symbol"
            ).fetchall()
            symbols = [s[0] for s in symbols]

            timeframes = conn.execute(
                "SELECT DISTINCT timeframe FROM validation_reports WHERE timeframe IS NOT NULL ORDER BY timeframe"
            ).fetchall()
            timeframes = [t[0] for t in timeframes]

            # Get averages
            avg_stats = conn.execute("""
                SELECT
                    AVG(total_errors) as avg_errors,
                    AVG(total_warnings) as avg_warnings,
                    AVG(validation_duration_ms) as avg_duration_ms
                FROM validation_reports
            """).fetchone()

            # Get status distribution
            status_dist = conn.execute("""
                SELECT validation_summary, COUNT(*) as count
                FROM validation_reports
                GROUP BY validation_summary
                ORDER BY count DESC
            """).fetchall()
            status_distribution = dict(status_dist)

            return {
                "total_validations": total,
                "symbols": symbols,
                "timeframes": timeframes,
                "avg_errors": avg_stats[0] if avg_stats[0] is not None else 0.0,
                "avg_warnings": avg_stats[1] if avg_stats[1] is not None else 0.0,
                "avg_duration_ms": avg_stats[2] if avg_stats[2] is not None else 0.0,
                "status_distribution": status_distribution,
            }
