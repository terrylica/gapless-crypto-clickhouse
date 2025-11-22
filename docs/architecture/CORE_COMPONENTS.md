# Core Components

The `gapless-crypto-clickhouse` system consists of six primary components providing modular data collection, validation, and storage capabilities.

## BinancePublicDataCollector

**Purpose**: Data collection from Binance's public data repository

**Performance**: 22x faster than API calls (CloudFront CDN vs REST API)

**Operations**:
- Monthly/daily ZIP download
- Extraction and processing
- CSV format conversion

**Output**: 11-column microstructure format CSV files

**Location**: `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py`

**Key Features**:
- Automatic monthly-to-daily fallback
- Intelligent retry logic with exponential backoff
- CloudFront edge caching optimization
- Parallel download support

## UniversalGapFiller

**Purpose**: Gap detection and filling with authentic Binance API data

**Algorithm**: Timestamp sequence analysis with timeframe-aware gap detection

**Data Source**: Binance REST API (authenticated or public endpoints)

**Guarantee**: Only authentic market data, never synthetic interpolation

**Location**: `src/gapless_crypto_clickhouse/gap_filling/universal_gap_filler.py`

**Key Features**:
- Automatic gap boundary detection
- Batch API requests for efficiency
- Timeframe-aware validation (1s to 1d intervals)
- Safe file merging with atomic operations

## CSVValidator

**Purpose**: 5-layer validation engine for data quality assurance

**Validation Layers**:
1. Structure validation (11-column format)
2. DateTime validation (chronological order, gaps)
3. OHLCV validation (price logic, negative values)
4. Coverage validation (expected vs actual bars)
5. Anomaly validation (outliers, suspicious patterns)

**Persistence**: DuckDB-based storage for validation reports

**AI Integration**: SQL query interface for AI coding agents

**Location**: `src/gapless_crypto_clickhouse/validation/csv_validator.py`

**Documentation**: See [Validation Overview](../validation/OVERVIEW.md)

## ValidationStorage

**Purpose**: DuckDB persistent storage for validation reports

**Schema**: 30+ columns with flattened metrics for SQL queries

**Storage**: `~/.cache/gapless-crypto-clickhouse/validation.duckdb` (XDG-compliant)

**Location**: `src/gapless_crypto_clickhouse/validation/storage.py`

**Key Features**:
- SQL query interface for historical analysis
- Report versioning and comparison
- AI agent-friendly structured output
- Automatic schema migrations

**Documentation**: See [Validation Storage Specification](../validation/STORAGE.md)

## AtomicCSVOperations

**Purpose**: Corruption-proof file operations with atomic guarantees

**Mechanism**:
1. Write to temporary file
2. Validate content integrity
3. Atomic rename to target location

**Guarantee**: All-or-nothing writes (no partial file corruption)

**Location**: `src/gapless_crypto_clickhouse/gap_filling/safe_file_operations.py`

**Key Features**:
- POSIX atomic rename semantics
- Automatic rollback on errors
- Checksum validation
- Cross-platform compatibility

## SafeCSVMerger

**Purpose**: Safe merging of multiple CSV files with validation

**Operations**:
- Gap data integration
- Duplicate removal
- Chronological sorting

**Validation**: Automatic data integrity checks

**Location**: `src/gapless_crypto_clickhouse/gap_filling/safe_file_operations.py`

**Key Features**:
- Deterministic merge ordering
- Duplicate detection and removal
- Timestamp continuity validation
- Memory-efficient streaming for large files

## Component Relationships

```
BinancePublicDataCollector
    ↓ (generates)
CSV Files
    ↓ (analyzed by)
UniversalGapFiller
    ↓ (validates via)
CSVValidator
    ↓ (stores results in)
ValidationStorage (DuckDB)
    ↓ (uses for I/O)
AtomicCSVOperations & SafeCSVMerger
```

## References

- [Architecture Overview](OVERVIEW.md) - Complete architecture documentation
- [Data Format Specification](DATA_FORMAT.md) - 11-column format details
- [Validation System](../validation/OVERVIEW.md) - Complete validation pipeline
- [ClickHouse Integration](OVERVIEW.md#clickhouse-integration-primary-storage-mode) - Database storage mode
