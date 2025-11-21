"""ClickHouse Schema Validator for v6.0.0.

Validates runtime schema matches expected schema.sql definition.
Raises SchemaValidationError on mismatch (no fallback, no retry).

**SLO Focus**: Correctness (prevents 1000x data loss from DateTime64(3) vs DateTime64(6) mismatch)

**ADR**: ADR-0024 (Comprehensive Validation Canonicity)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExpectedSchema:
    """Expected ohlcv table schema (v4.0.0+ with DateTime64(6) microsecond precision).

    Reference: src/gapless_crypto_clickhouse/clickhouse/schema.sql
    """

    columns: Dict[str, str] = field(
        default_factory=lambda: {
            # Metadata columns
            "symbol": "LowCardinality(String)",
            "timeframe": "LowCardinality(String)",
            "instrument_type": "LowCardinality(String)",
            "data_source": "LowCardinality(String)",
            "timestamp": "DateTime64(6)",  # Microsecond precision (ADR-0021)
            # OHLCV columns
            "open": "Float64",
            "high": "Float64",
            "low": "Float64",
            "close": "Float64",
            "volume": "Float64",
            # Microstructure columns
            "close_time": "DateTime64(6)",  # Microsecond precision (ADR-0021)
            "quote_asset_volume": "Float64",
            "number_of_trades": "Int64",
            "taker_buy_base_asset_volume": "Float64",
            "taker_buy_quote_asset_volume": "Float64",
            # Futures-specific column
            "funding_rate": "Nullable(Float64)",
            # Internal deduplication columns
            "_version": "UInt64",
            "_sign": "Int8",
        }
    )

    engine: str = "ReplacingMergeTree"
    partition_key: str = "toYYYYMMDD(timestamp)"
    sorting_key: Tuple[str, ...] = ("timestamp", "symbol", "timeframe", "instrument_type")

    # Expected compression codecs (optional validation)
    expected_codecs: Dict[str, str] = field(
        default_factory=lambda: {
            "timestamp": "DoubleDelta",
            "close_time": "DoubleDelta",
            "open": "Gorilla",
            "high": "Gorilla",
            "low": "Gorilla",
            "close": "Gorilla",
            "volume": "Gorilla",
            "quote_asset_volume": "Gorilla",
            "taker_buy_base_asset_volume": "Gorilla",
            "taker_buy_quote_asset_volume": "Gorilla",
            "funding_rate": "Gorilla",
        }
    )


class SchemaValidationError(Exception):
    """Raised when schema validation fails.

    **Behavior**: STRICT - No fallback, no retry, no silent failures.
    Propagate to caller (SLO requirement).
    """

    pass


class SchemaValidator:
    """Validates ClickHouse schema at runtime against expected schema.sql definition.

    **Usage**:
    ```python
    with ClickHouseConnection() as conn:
        validator = SchemaValidator(conn)
        validator.validate_schema()  # Raises SchemaValidationError on mismatch
    ```

    **Validation Scope**:
    - Column types (DateTime64(6) vs DateTime64(3) detection)
    - Engine configuration (ReplacingMergeTree with _version)
    - Partition key (daily partitions for pruning)
    - Sorting key (query optimization)
    - Compression codecs (storage efficiency, optional)
    """

    def __init__(self, connection):
        """Initialize validator with ClickHouse connection.

        Args:
            connection: ClickHouseConnection instance (must be opened)
        """
        self.connection = connection
        self.expected = ExpectedSchema()

    def validate_schema(self) -> Dict[str, any]:
        """Validate ohlcv table schema matches expectations.

        Returns:
            Validation report: {"status": "valid", "errors": []}

        Raises:
            SchemaValidationError: If critical mismatch detected (STRICT mode)
        """
        errors = []

        # 1. Validate column types
        try:
            column_errors = self._validate_column_types()
            errors.extend(column_errors)
        except Exception as e:
            errors.append(f"Column type validation failed: {e}")

        # 2. Validate engine configuration
        try:
            engine_errors = self._validate_engine()
            errors.extend(engine_errors)
        except Exception as e:
            errors.append(f"Engine validation failed: {e}")

        # 3. Validate partitioning
        try:
            partition_errors = self._validate_partitioning()
            errors.extend(partition_errors)
        except Exception as e:
            errors.append(f"Partition validation failed: {e}")

        # 4. Validate sorting key
        try:
            sorting_errors = self._validate_sorting_key()
            errors.extend(sorting_errors)
        except Exception as e:
            errors.append(f"Sorting key validation failed: {e}")

        if errors:
            raise SchemaValidationError(
                f"Schema validation failed ({len(errors)} errors):\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        logger.info("Schema validation passed: ohlcv table matches expected schema")
        return {"status": "valid", "errors": []}

    def _validate_column_types(self) -> List[str]:
        """Validate column types match expected schema.

        **Critical Check**: DateTime64(6) vs DateTime64(3) mismatch
        (prevents 1000x data loss)
        """
        query = """
            SELECT name, type
            FROM system.columns
            WHERE database = 'default' AND table = 'ohlcv'
            ORDER BY name
        """
        result = self.connection.execute(query)
        actual_columns = {row[0]: row[1] for row in result}

        errors = []

        # Check for missing columns
        for col, expected_type in self.expected.columns.items():
            if col not in actual_columns:
                errors.append(f"Missing column: {col} (expected type: {expected_type})")

        # Check for type mismatches
        for col, expected_type in self.expected.columns.items():
            if col in actual_columns:
                actual_type = actual_columns[col]
                if actual_type != expected_type:
                    errors.append(
                        f"Type mismatch: {col} (expected {expected_type}, got {actual_type})"
                    )

                    # Special warning for DateTime64 precision mismatch
                    if "DateTime64" in expected_type and "DateTime64" in actual_type:
                        if "DateTime64(6)" in expected_type and "DateTime64(3)" in actual_type:
                            errors.append(
                                f"  ⚠️  CRITICAL: {col} has millisecond precision (3) "
                                f"but microsecond precision (6) required. "
                                f"This causes 1000x data loss! See ADR-0021."
                            )

        # Check for unexpected columns (informational, not error)
        extra_columns = set(actual_columns.keys()) - set(self.expected.columns.keys())
        if extra_columns:
            logger.warning(f"Unexpected columns in ohlcv table: {extra_columns}")

        return errors

    def _validate_engine(self) -> List[str]:
        """Validate table engine is ReplacingMergeTree with _version column."""
        query = """
            SELECT engine, engine_full
            FROM system.tables
            WHERE database = 'default' AND name = 'ohlcv'
        """
        result = self.connection.execute(query)

        if not result:
            return ["Table 'ohlcv' not found in database 'default'"]

        engine, engine_full = result[0]
        errors = []

        if engine != self.expected.engine:
            errors.append(
                f"Wrong engine: expected {self.expected.engine}, got {engine}. "
                f"ReplacingMergeTree required for zero-gap guarantee."
            )

        # Verify _version column is used for deduplication
        if "_version" not in engine_full:
            errors.append(
                f"ReplacingMergeTree version column missing. "
                f"Expected '_version' in engine definition, got: {engine_full}"
            )

        return errors

    def _validate_partitioning(self) -> List[str]:
        """Validate partition key for daily partitions (performance optimization)."""
        query = """
            SELECT partition_key
            FROM system.tables
            WHERE database = 'default' AND name = 'ohlcv'
        """
        result = self.connection.execute(query)

        if not result:
            return ["Cannot retrieve partition_key for ohlcv table"]

        actual_partition_key = result[0][0]

        if actual_partition_key != self.expected.partition_key:
            return [
                f"Partition key mismatch: "
                f"expected '{self.expected.partition_key}', got '{actual_partition_key}'. "
                f"Daily partitioning required for query performance."
            ]

        return []

    def _validate_sorting_key(self) -> List[str]:
        """Validate sorting key (ORDER BY) for query optimization."""
        query = """
            SELECT sorting_key
            FROM system.tables
            WHERE database = 'default' AND name = 'ohlcv'
        """
        result = self.connection.execute(query)

        if not result:
            return ["Cannot retrieve sorting_key for ohlcv table"]

        actual_sorting_key = result[0][0]
        expected_sorting_key = ", ".join(self.expected.sorting_key)

        if actual_sorting_key != expected_sorting_key:
            return [
                f"Sorting key mismatch: "
                f"expected ({expected_sorting_key}), got ({actual_sorting_key}). "
                f"Correct sorting key required for query performance."
            ]

        return []

    def _validate_compression(self) -> List[str]:
        """Validate compression codecs (optional, informational warnings only).

        Note: Missing compression doesn't prevent correctness, only increases storage.
        """
        query = """
            SELECT name, compression_codec
            FROM system.columns
            WHERE database = 'default' AND table = 'ohlcv'
        """
        result = self.connection.execute(query)
        actual_codecs = {row[0]: row[1] for row in result}

        warnings = []

        for col, expected_codec in self.expected.expected_codecs.items():
            if col in actual_codecs:
                actual_codec = actual_codecs[col]
                if expected_codec not in actual_codec:
                    warnings.append(
                        f"Suboptimal compression for {col}: "
                        f"expected {expected_codec}, got {actual_codec}"
                    )

        if warnings:
            logger.warning(f"Compression codec warnings: {warnings}")

        # Return empty list (warnings don't fail validation)
        return []
