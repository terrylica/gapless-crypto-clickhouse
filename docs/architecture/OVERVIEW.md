---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Architecture Overview

Gapless Crypto Data is a cryptocurrency data collection tool providing authentic Binance data with zero-gap guarantee. The architecture follows a modular design with separation of concerns.

## Purpose

Collect complete historical cryptocurrency market data from Binance with:

- **Zero-gap guarantee**: No missing timestamps in collected datasets
- **Authentic data only**: Direct from Binance public repository and API (no synthetic data)
- **11-column microstructure format**: OHLCV + order flow metrics
- **22x performance advantage**: Public repository downloads vs direct API calls

## Core Components

The system consists of six primary components:

### BinancePublicDataCollector

- **Purpose**: Data collection from Binance's public data repository
- **Performance**: 22x faster than API calls (CloudFront CDN vs REST API)
- **Operations**: Monthly/daily ZIP download, extraction, processing
- **Output**: 11-column microstructure format CSV files
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py`

### UniversalGapFiller

- **Purpose**: Gap detection and filling with authentic Binance API data
- **Algorithm**: Timestamp sequence analysis with timeframe-aware gap detection
- **Data source**: Binance REST API (authenticated or public endpoints)
- **Guarantee**: Only authentic market data, never synthetic interpolation
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/gap_filling/universal_gap_filler.py`

### CSVValidator

- **Purpose**: 5-layer validation engine for data quality assurance
- **Persistence**: DuckDB-based storage for validation reports
- **AI Integration**: SQL query interface for AI coding agents
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/validation/csv_validator.py`
- **Details**: See [Validation Overview](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/OVERVIEW.md)

### ValidationStorage

- **Purpose**: DuckDB persistent storage for validation reports
- **Schema**: 30+ columns with flattened metrics for SQL queries
- **Storage**: `~/.cache/gapless-crypto-data/validation.duckdb` (XDG-compliant)
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/validation/storage.py`
- **Details**: See [Validation Storage Specification](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/STORAGE.md)

### AtomicCSVOperations

- **Purpose**: Corruption-proof file operations with atomic guarantees
- **Mechanism**: Temp file + validation + atomic rename
- **Guarantee**: All-or-nothing writes (no partial file corruption)
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/gap_filling/safe_file_operations.py`

### SafeCSVMerger

- **Purpose**: Safe merging of multiple CSV files with validation
- **Operations**: Gap data integration, duplicate removal, chronological sorting
- **Validation**: Automatic data integrity checks
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/gap_filling/safe_file_operations.py`

## ClickHouse Integration (Primary Storage Mode)

### Overview

ClickHouse serves as the primary storage backend for `gapless-crypto-clickhouse`, providing persistent OHLCV data storage with production-grade capabilities:

- **Persistent storage**: Data survives across sessions
- **Multi-symbol querying**: Millisecond latency for time-range queries
- **Automatic deduplication**: ReplacingMergeTree engine with deterministic versioning
- **Production-ready**: Validated at 100M+ rows with 1.1M rows/sec ingestion throughput

### ClickHouse Components

#### ClickHouseConnection

- **Purpose**: Manages ClickHouse database connections with automatic reconnection
- **Features**: Connection pooling, config validation, graceful shutdown
- **Key Methods**:
  - `connect()`: Establish connection with environment-based configuration
  - `execute()`: Run queries with error handling and retry logic
  - `close()`: Clean connection shutdown
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/clickhouse/connection.py`

#### ClickHouseConfig

- **Purpose**: Configuration management from environment variables and `.env` files
- **Environment Variables**:
  - `CLICKHOUSE_HOST`: Database host (default: localhost)
  - `CLICKHOUSE_PORT`: Native protocol port (default: 9000)
  - `CLICKHOUSE_DATABASE`: Database name (default: crypto_data)
  - `CLICKHOUSE_USER`: Authentication username
  - `CLICKHOUSE_PASSWORD`: Authentication password
- **Features**: Automatic `.env` file loading, validation, secure credential handling
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/clickhouse/config.py`

#### ClickHouseBulkLoader

- **Purpose**: High-performance bulk data ingestion from CSV to ClickHouse
- **Features**:
  - Batch processing (configurable batch size, default 100K rows)
  - Idempotent inserts via ReplacingMergeTree with deterministic versioning
  - Automatic deduplication (handles reprocessing without duplicates)
  - 16 timeframe support (1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo)
  - Column type validation and transformation
- **Performance**: 1.1M rows/sec validated in production testing
- **Location**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/collectors/clickhouse_bulk_loader.py`

### Database Schema

**Engine**: ReplacingMergeTree (automatic deduplication on merge)

**Schema Definition**: `/Users/terryli/eon/gapless-crypto-clickhouse/src/gapless_crypto_clickhouse/clickhouse/schema.sql`

**Columns** (17 total):

**Metadata** (5 columns):

- `symbol` (String): Trading pair (e.g., "BTCUSDT")
- `timeframe` (String): Candle interval (e.g., "1m", "1h")
- `instrument_type` (String): Market type ("spot" or "um" for USDT-margined futures)
- `data_source` (String): Source identifier ("binance_public_data")
- `timestamp` (DateTime64(6)): Candle open time in UTC with microsecond precision

**OHLCV** (5 columns):

- `open` (Float64): Opening price
- `high` (Float64): Highest price in period
- `low` (Float64): Lowest price in period
- `close` (Float64): Closing price
- `volume` (Float64): Base asset volume

**Microstructure** (5 columns):

- `close_time` (DateTime64(6)): Candle close time in UTC with microsecond precision
- `quote_asset_volume` (Float64): Quote asset volume
- `number_of_trades` (Int64): Trade count in period
- `taker_buy_base_asset_volume` (Float64): Taker buy base volume
- `taker_buy_quote_asset_volume` (Float64): Taker buy quote volume

**Deduplication** (2 columns):

- `_version` (UInt64): Deterministic version for ReplacingMergeTree (SHA-256 hash of row data)
- `_sign` (Int8): Row operation indicator (1=insert, -1=delete for manual cleanup)

**Primary Key**: `(symbol, timeframe, timestamp)` - Optimized for time-series queries

**Ordering**: `timestamp DESC` - Most recent data first

**Indexes**: Automatic primary key index for efficient symbol+timeframe+time queries

### Data Ingestion Flow (ClickHouse Mode)

```
Binance Public Repository (monthly/daily ZIPs)
           ↓
   BinancePublicDataCollector
      - Download ZIP files
      - Extract CSV data
           ↓
   Polars DataFrame Processing
      - Schema validation
      - Type conversion
      - Column mapping (date → timestamp)
           ↓
   ClickHouseBulkLoader
      - Batch processing (100K rows/batch)
      - Add metadata (symbol, timeframe, instrument_type)
      - Calculate deterministic version (_version)
      - Insert to ClickHouse
           ↓
   ClickHouse ReplacingMergeTree
      - Automatic deduplication on background merges
      - Compressed storage (DoubleDelta + LZ4)
           ↓
   Query API (ClickHouseQuery)
      - Time-range queries
      - Multi-symbol aggregation
      - Export to DataFrame/CSV
```

### ClickHouse vs File-Based Workflows

| Aspect             | ClickHouse Mode                  | File-Based Mode               |
| ------------------ | -------------------------------- | ----------------------------- |
| **Storage**        | Database (persistent)            | CSV files (stateless)         |
| **Querying**       | SQL, millisecond latency         | Pandas/Polars file reads      |
| **Multi-symbol**   | Single query across symbols      | Load multiple CSV files       |
| **Deduplication**  | Automatic (ReplacingMergeTree)   | Manual merge logic            |
| **Production Use** | Database administration required | Simple file management        |
| **Best For**       | Production pipelines, analytics  | Exploratory analysis, backups |

## Data Flow Architecture

```
Binance Public Repository (monthly/daily ZIPs)
           ↓
   BinancePublicDataCollector
      - Download ZIP files
      - Extract CSV data
      - Process to 11-column format
           ↓
   11-column CSV files (output_dir/)
           ↓
   Gap Detection (UniversalGapFiller)
      - Analyze timestamp sequences
      - Identify gaps
           ↓
   Gap Filling (if gaps found)
      - Fetch from Binance API
      - Merge with existing data
           ↓
   AtomicCSVOperations
      - Atomic file writes
      - Corruption prevention
           ↓
   Final validated CSV files (gapless datasets)
           ↓
   CSVValidator (optional)
      - 5-layer validation
      - Store reports in DuckDB
           ↓
   ValidationStorage
      - Persistent validation history
      - SQL query interface for analysis
```

## Data Format Specifications

Output format: **11-column microstructure CSV**

Columns:

1. `date` (TIMESTAMP) - Open time in UTC
2. `open` (DOUBLE) - Opening price
3. `high` (DOUBLE) - Highest price in period
4. `low` (DOUBLE) - Lowest price in period
5. `close` (DOUBLE) - Closing price
6. `volume` (DOUBLE) - Base asset volume
7. `close_time` (TIMESTAMP) - Close time in UTC
8. `quote_asset_volume` (DOUBLE) - Quote asset volume
9. `number_of_trades` (INTEGER) - Trade count in period
10. `taker_buy_base_asset_volume` (DOUBLE) - Taker buy base volume
11. `taker_buy_quote_asset_volume` (DOUBLE) - Taker buy quote volume

This format provides complete microstructure data for:

- Price action analysis (OHLC)
- Volume profiling
- Order flow metrics (taker buy volumes)
- Trade frequency analysis (number of trades)

See [Data Format Specification](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/DATA_FORMAT.md) for detailed definitions.

## System Boundaries

**In Scope**:

- Binance Spot market data collection
- Historical data (1-second to 1-day timeframes)
- Zero-gap guarantee for continuous datasets
- Data validation and quality assurance

**Out of Scope**:

- Futures/derivatives market data
- Real-time streaming (use Binance WebSocket API)
- Data analysis or trading strategies
- Database storage (output is CSV/Parquet files)

## SLOs (Service Level Objectives)

### Availability

- **Data Source**: Binance public repository (99.99% SLA via CloudFront)
- **Dependencies**: Network connectivity, disk space

### Correctness

- **Zero-gap guarantee**: All timestamps present within collection range
- **Authentic data only**: Direct from Binance, no synthetic values
- **Validation**: 5-layer validation engine with persistent reporting

### Observability

- **Progress reporting**: Real-time collection status
- **Validation reports**: DuckDB-based persistent history
- **Error logging**: Complete exception trace with context

### Maintainability

- **Single responsibility**: Each component has one primary purpose
- **Separation of concerns**: Collection → Gap filling → Validation
- **Test coverage**: 30+ comprehensive tests
- **Documentation**: OpenAPI 3.1.1 specs + markdown guides

## Architecture References

- **Canonical Status**: [CURRENT_ARCHITECTURE_STATUS.yaml](/Users/terryli/eon/gapless-crypto-clickhouse/docs/CURRENT_ARCHITECTURE_STATUS.yaml)
- **Core Components**: [CORE_COMPONENTS.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/CORE_COMPONENTS.md)
- **Network Architecture**: [network.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/network.md)
- **Data Flow Diagrams**: [docs/diagrams/](/Users/terryli/eon/gapless-crypto-clickhouse/docs/diagrams/)

## Related Documentation

- **Data Collection Guide**: [docs/guides/DATA_COLLECTION.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/guides/DATA_COLLECTION.md)
- **Gap Filling Operations**: [docs/guides/GAP_FILLING.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/guides/GAP_FILLING.md)
- **Validation System**: [docs/validation/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/OVERVIEW.md)
- **Python API Reference**: [docs/api/quick-start.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/api/quick-start.md)
