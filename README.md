# Gapless Crypto ClickHouse

[![PyPI version](https://img.shields.io/pypi/v/gapless-crypto-clickhouse.svg)](https://pypi.org/project/gapless-crypto-clickhouse/)
[![GitHub release](https://img.shields.io/github/v/release/terrylica/gapless-crypto-clickhouse.svg)](https://github.com/terrylica/gapless-crypto-clickhouse/releases/latest)
[![Python Versions](https://img.shields.io/pypi/pyversions/gapless-crypto-clickhouse.svg)](https://pypi.org/project/gapless-crypto-clickhouse/)
[![Downloads](https://img.shields.io/pypi/dm/gapless-crypto-clickhouse.svg)](https://pypi.org/project/gapless-crypto-clickhouse/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UV Managed](https://img.shields.io/badge/uv-managed-blue.svg)](https://github.com/astral-sh/uv)
[![Release](https://github.com/terrylica/gapless-crypto-clickhouse/actions/workflows/release.yml/badge.svg)](https://github.com/terrylica/gapless-crypto-clickhouse/actions/workflows/release.yml)
[![AI Agent Ready](https://img.shields.io/badge/AI%20Agent-Ready-brightgreen.svg)](https://github.com/terrylica/gapless-crypto-clickhouse#ai-agent-integration)

ClickHouse-based cryptocurrency data collection with zero-gap guarantee. Optimized for bulk historical data via Binance public repository with persistent database storage and USDT-margined futures support.

## When to Use This Package

**Choose `gapless-crypto-clickhouse`** (this package) when you need:

- **Persistent database storage** for multi-symbol, multi-timeframe datasets
- **Advanced SQL queries** for time-series analysis, aggregations, and joins
- **USDT-margined futures** support (perpetual contracts)
- **Production data pipelines** with deterministic versioning and deduplication
- **Python 3.11+** modern runtime environment

**Choose [`gapless-crypto-data`](https://github.com/terrylica/gapless-crypto-data)** (file-based) when you need:

- **Simple file-based workflows** with CSV output
- **Single-symbol analysis** without database overhead
- **Python 3.9-3.13** broader compatibility
- **Lightweight dependency footprint** (no database required)

Both packages share the same performance optimization via Binance public repository and zero-gap guarantee.

## Features

- Bulk historical data via Binance public data repository (pre-generated ZIP files)
- Apache Arrow optimization for query performance
- Auto-ingestion: `query_ohlcv()` downloads missing data automatically
- ClickHouse ReplacingMergeTree for deterministic deduplication
- USDT-margined futures support (perpetual contracts via `instrument_type` column)
- Zero gaps guarantee through monthly-to-daily fallback
- All Binance-supported timeframes (1s through 1mo)
- Microstructure format with order flow metrics (see [Data Structure](#data-structure))
- Multi-symbol SQL queries, joins, and aggregations
- Compressed storage (DoubleDelta timestamps, Gorilla OHLCV)
- AI agent integration via probe hooks

## Quick Start

### Installation (UV)

```bash
# Install via UV
uv add gapless-crypto-clickhouse

# Or install globally
uv tool install gapless-crypto-clickhouse
```

### Installation (pip)

```bash
pip install gapless-crypto-clickhouse
```

### Database Setup (ClickHouse Cloud)

This package uses **ClickHouse Cloud** as the single source of truth for persistent storage. Configure credentials via environment variables or Doppler:

```bash
# Required environment variables
export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
export CLICKHOUSE_PORT=8443
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=your-password
```

See [Database Integration](#database-integration) for complete setup guide and usage examples.

### Python API (Recommended)

#### Function-based API

```python
import gapless_crypto_clickhouse as gcch

# Fetch recent data with date range (CCXT-compatible timeframe parameter)
df = gcch.download("BTCUSDT", timeframe="1h", start="2024-01-01", end="2024-06-30")

# Or with limit
df = gcch.fetch_data("ETHUSDT", timeframe="4h", limit=1000)

# Get available symbols and timeframes
symbols = gcch.get_supported_symbols()
timeframes = gcch.get_supported_timeframes()

# Fill gaps in existing data
results = gcch.fill_gaps("./data")

# Multi-symbol batch download (concurrent execution)
results = gcch.download_multiple(
    symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"],
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30",
    max_workers=5  # Configure concurrency
)
# Returns: dict[str, pd.DataFrame]
# Example: btc_df = results["BTCUSDT"]
```

#### Class-based API

```python
from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller

# Custom collection with full control
collector = BinancePublicDataCollector(
    symbol="SOLUSDT",
    start_date="2023-01-01",
    end_date="2023-12-31"
)

result = collector.collect_timeframe_data("1h")
df = result["dataframe"]

# Manual gap filling
gap_filler = UniversalGapFiller()
gaps = gap_filler.detect_all_gaps("BTCUSDT_1h_data.csv", "1h")
```

> **Note**: This package never included a CLI interface (unlike parent package `gapless-crypto-data`). It provides a Python API only for programmatic access. See examples above for usage patterns.

## Data Structure

All functions return pandas DataFrames with complete microstructure data. The schema includes OHLCV price data plus order flow metrics for professional analysis:

```python
import gapless_crypto_clickhouse as gcch

# Fetch data
df = gcch.download("BTCUSDT", timeframe="1h", start="2024-01-01", end="2024-06-30")

# DataFrame columns (microstructure format)
print(df.columns.tolist())
# ['timestamp', 'open', 'high', 'low', 'close', 'volume',
#  'close_time', 'quote_asset_volume', 'number_of_trades',
#  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']

# Professional microstructure analysis
buy_pressure = df['taker_buy_base_asset_volume'].sum() / df['volume'].sum()
avg_trade_size = df['volume'].sum() / df['number_of_trades'].sum()
market_impact = df['quote_asset_volume'].std() / df['quote_asset_volume'].mean()

print(f"Taker buy pressure: {buy_pressure:.1%}")
print(f"Average trade size: {avg_trade_size:.4f} BTC")
print(f"Market impact volatility: {market_impact:.3f}")
```

## Data Sources

The package supports two data collection methods:

- **Binance Public Repository**: Pre-generated monthly ZIP files for historical data
- **Binance API**: Real-time data for gap filling and recent data collection

## Architecture

### Core Components

- **BinancePublicDataCollector**: Data collection with microstructure format
- **UniversalGapFiller**: Intelligent gap detection and filling with authentic API-first validation
- **AtomicCSVOperations**: Corruption-proof file operations with atomic writes
- **SafeCSVMerger**: Safe merging of data files with integrity validation

### Data Flow

```
Binance Public Data Repository → BinancePublicDataCollector → Microstructure Format
                ↓
Gap Detection → UniversalGapFiller → Authentic API-First Validation
                ↓
AtomicCSVOperations → Final Gapless Dataset with Order Flow Metrics
```

## Database Integration

**ClickHouse Cloud** is the single source of truth for this package. While the package works without a database (file-based approach), ClickHouse Cloud enables persistent storage, advanced query capabilities, and multi-symbol analysis.

**When to use**:

- **File-based approach**: Simple workflows, single symbols, CSV output, no database setup required
- **Database approach** (recommended): Multi-symbol analysis, time-series queries, aggregations, production pipelines

### ClickHouse Cloud Setup

Configure ClickHouse Cloud credentials via environment variables or Doppler:

```bash
# Environment variables (or use Doppler for secret management)
export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
export CLICKHOUSE_PORT=8443
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=your-password

# Deploy schema (creates ohlcv table with ReplacingMergeTree)
doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py
```

**Schema deployment**: The `scripts/deploy-clickhouse-schema.py` script creates the `ohlcv` table with optimized ORDER BY for prop trading queries (ADR-0034).

### Unified Query API

The recommended way to query data is using `query_ohlcv()` with auto-ingestion:

```python
from gapless_crypto_clickhouse import query_ohlcv

# Query with auto-ingestion (downloads data if missing)
df = query_ohlcv(
    "BTCUSDT",
    "1h",
    "2024-01-01",
    "2024-01-31"
)
print(f"Retrieved {len(df)} rows")

# Multi-symbol query
df = query_ohlcv(
    ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "1h",
    "2024-01-01",
    "2024-01-31"
)

# Futures data
df = query_ohlcv(
    "BTCUSDT",
    "1h",
    "2024-01-01",
    "2024-01-31",
    instrument_type="futures-um"
)

# Query without auto-ingestion (faster, raises if data missing)
df = query_ohlcv(
    "BTCUSDT",
    "1h",
    "2024-01-01",
    "2024-01-31",
    auto_ingest=False
)
```

**When to use lower-level APIs**: Custom SQL, bulk loading, or connection management.

### Basic Usage Examples

#### Connection and Health Check

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

# Connect to ClickHouse (reads from .env or uses defaults)
with ClickHouseConnection() as conn:
    # Verify connection
    health = conn.health_check()
    print(f"ClickHouse connected: {health}")

    # Execute simple query
    result = conn.execute("SELECT count() FROM ohlcv")
    print(f"Total rows in database: {result[0][0]:,}")
```

#### Bulk Data Ingestion

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

# Ingest historical data from Binance public repository
with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn, instrument_type="spot")

    # Ingest single month (e.g., January 2024)
    rows_inserted = loader.ingest_month("BTCUSDT", "1h", year=2024, month=1)
    print(f"Inserted {rows_inserted:,} rows for BTCUSDT 1h (Jan 2024)")

    # Ingest date range (e.g., Q1 2024)
    total_rows = loader.ingest_date_range(
        symbol="ETHUSDT",
        timeframe="4h",
        start_date="2024-01-01",
        end_date="2024-03-31"
    )
    print(f"Inserted {total_rows:,} rows for ETHUSDT 4h (Q1 2024)")
```

**Zero-gap guarantee**: ClickHouse uses deterministic versioning (SHA256 hash) to handle duplicate ingestion safely. Re-running ingestion commands won't create duplicates.

#### Querying Data

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery

with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)

    # Get latest data (last 10 bars)
    df = query.get_latest("BTCUSDT", "1h", limit=10)
    print(f"Latest 10 bars:\n{df[['timestamp', 'close']]}")

    # Get specific date range
    df = query.get_range(
        symbol="BTCUSDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-01-31",
        instrument_type="spot"
    )
    print(f"January 2024: {len(df):,} bars")

    # Multi-symbol comparison
    df = query.get_multi_symbol(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        timeframe="1d",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"Multi-symbol dataset: {df.shape}")
```

**FINAL keyword**: All queries automatically use `FINAL` to ensure deduplicated results.

#### Futures Support (ADR-0004)

```python
# Ingest futures data (same format as spot)
with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn, instrument_type="futures-um")
    rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
    print(f"Futures data: {rows:,} rows")

    # Query futures data (isolated from spot)
    query = OHLCVQuery(conn)
    df_spot = query.get_latest("BTCUSDT", "1h", instrument_type="spot", limit=10)
    df_futures = query.get_latest("BTCUSDT", "1h", instrument_type="futures-um", limit=10)

    print(f"Spot data: {len(df_spot)} bars")
    print(f"Futures data: {len(df_futures)} bars")
```

**Spot/Futures isolation**: The `instrument_type` column ensures spot and futures data coexist without conflicts.

### Configuration

**Environment Variables** (Doppler recommended, or `.env` file):

```bash
CLICKHOUSE_HOST=your-instance.clickhouse.cloud  # ClickHouse Cloud hostname
CLICKHOUSE_PORT=8443                            # HTTPS port (ClickHouse Cloud)
CLICKHOUSE_USER=default                         # Username
CLICKHOUSE_PASSWORD=your-password               # Password (required for Cloud)
CLICKHOUSE_DB=default                           # Database name
```

**Doppler integration**: Credentials stored in `aws-credentials/prd` project. Use `doppler run` to inject secrets automatically.

### Migration Guide

**Migrating from `gapless-crypto-data` (file-based) to `gapless-crypto-clickhouse` (database-first)**:

See [`docs/CLICKHOUSE_MIGRATION.md`](https://github.com/terrylica/gapless-crypto-clickhouse/blob/main/docs/CLICKHOUSE_MIGRATION.md) for:

- Architecture changes (file-based → ClickHouse Cloud)
- Code migration examples (drop-in replacement)
- Deployment guide (ClickHouse Cloud)
- Performance characteristics (ingestion, query, deduplication)
- Troubleshooting common issues

**Key Changes**:

- Package name: `gapless-crypto-data` → `gapless-crypto-clickhouse`
- Import paths: `gapless_crypto_data` → `gapless_crypto_clickhouse`
- ClickHouse Cloud: Single source of truth (credentials via Doppler)
- Python version: 3.11+ (was 3.9-3.13)
- API signatures: **Unchanged** (backwards compatible)

**Rollback strategy**: Continue using `gapless-crypto-data` for file-based workflows. Both packages maintained independently.

### Production Deployment

**ClickHouse Cloud** (recommended):

1. **Credentials**: Store in Doppler (`aws-credentials/prd`) - never in source code
2. **TLS**: Enabled by default on port 8443
3. **Monitoring**: ClickHouse Cloud provides built-in observability
4. **Backups**: Automated by ClickHouse Cloud

**Scaling**: ClickHouse Cloud handles scaling automatically. See ClickHouse Cloud documentation for advanced configuration.

## Advanced Usage

### Batch Processing

#### Simple API (Recommended)

```python
import gapless_crypto_clickhouse as gcch

# Process multiple symbols with simple loops
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
timeframes = ["1h", "4h"]

for symbol in symbols:
    for timeframe in timeframes:
        df = gcch.fetch_data(symbol, timeframe, start="2023-01-01", end="2023-12-31")
        print(f"{symbol} {timeframe}: {len(df)} bars collected")
```

#### Advanced API (Complex Workflows)

```python
from gapless_crypto_clickhouse import BinancePublicDataCollector

# Initialize with custom settings
collector = BinancePublicDataCollector(
    start_date="2023-01-01",
    end_date="2023-12-31",
    output_dir="./crypto_data"
)

# Process multiple symbols with detailed control
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
for symbol in symbols:
    collector.symbol = symbol
    results = collector.collect_multiple_timeframes(["1m", "5m", "1h", "4h"])
    for timeframe, result in results.items():
        print(f"{symbol} {timeframe}: {result['stats']}")
```

### Gap Analysis

#### Simple API (Recommended)

```python
import gapless_crypto_clickhouse as gcch

# Quick gap filling for entire directory
results = gcch.fill_gaps("./data")
print(f"Processed {results['files_processed']} files")
print(f"Filled {results['gaps_filled']}/{results['gaps_detected']} gaps")
print(f"Success rate: {results['success_rate']:.1f}%")

# Gap filling for specific symbols only
results = gcch.fill_gaps("./data", symbols=["BTCUSDT", "ETHUSDT"])
```

#### Advanced API (Detailed Control)

```python
from gapless_crypto_clickhouse import UniversalGapFiller

gap_filler = UniversalGapFiller()

# Manual gap detection and analysis
gaps = gap_filler.detect_all_gaps("BTCUSDT_1h.csv", "1h")
print(f"Found {len(gaps)} gaps")

for gap in gaps:
    duration_hours = gap['duration'].total_seconds() / 3600
    print(f"Gap: {gap['start_time']} → {gap['end_time']} ({duration_hours:.1f}h)")

# Fill specific gaps
result = gap_filler.process_file("BTCUSDT_1h.csv", "1h")
```

### Database Query Examples

For users leveraging ClickHouse database integration:

#### Bulk Ingestion Pipeline

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

# Multi-symbol bulk ingestion for backtesting datasets
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
timeframes = ["1h", "4h", "1d"]

with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn, instrument_type="spot")

    for symbol in symbols:
        for timeframe in timeframes:
            # Ingest Q1 2024 data
            rows = loader.ingest_date_range(
                symbol=symbol,
                timeframe=timeframe,
                start_date="2024-01-01",
                end_date="2024-03-31"
            )
            print(f"{symbol} {timeframe}: {rows:,} rows ingested")

# Zero-gap guarantee: Re-running this script won't create duplicates
```

#### Multi-Symbol Analysis

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery

with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)

    # Get synchronized data for all symbols (same time range)
    df = query.get_multi_symbol(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    # Analyze cross-asset correlations
    pivot = df.pivot_table(index="timestamp", columns="symbol", values="close")
    correlation = pivot.corr()
    print(f"Correlation matrix:\n{correlation}")

    # Relative strength analysis
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        symbol_data = df[df["symbol"] == symbol]
        returns = symbol_data["close"].pct_change().sum()
        print(f"{symbol} total return: {returns:.2%}")
```

#### Advanced Time-Series Queries

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

with ClickHouseConnection() as conn:
    # Custom SQL for advanced analytics (ClickHouse functions)
    query = """
    SELECT
        symbol,
        timeframe,
        toStartOfDay(timestamp) AS day,
        avg(close) AS avg_price,
        stddevPop(close) AS volatility,
        sum(volume) AS total_volume,
        count() AS bar_count
    FROM ohlcv FINAL
    WHERE symbol IN ('BTCUSDT', 'ETHUSDT')
      AND timeframe = '1h'
      AND timestamp >= '2024-01-01'
      AND timestamp < '2024-02-01'
    GROUP BY symbol, timeframe, day
    ORDER BY day ASC, symbol ASC
    """

    result = conn.execute(query)

    # Process results
    for row in result:
        symbol, timeframe, day, avg_price, volatility, volume, bars = row
        print(f"{day} {symbol}: avg=${avg_price:.2f}, vol={volatility:.2f}, volume={volume:,.0f}")
```

#### Hybrid Approach (File + Database)

Combine file-based collection with database querying:

```python
import gapless_crypto_clickhouse as gcch
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery
from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

# Step 1: Collect to CSV files
df = gcch.download("BTCUSDT", timeframe="1h", start="2024-01-01", end="2024-03-31")
print(f"Downloaded {len(df):,} bars to CSV")

# Step 2: Ingest CSV to ClickHouse for analysis
with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn)
    loader.ingest_from_dataframe(df, symbol="BTCUSDT", timeframe="1h")

    # Step 3: Run advanced queries
    query = OHLCVQuery(conn)
    gaps = query.detect_gaps("BTCUSDT", "1h", "2024-01-01", "2024-03-31")
    print(f"Gap detection: {len(gaps)} gaps found")
```

**When to use hybrid approach**:

- Initial data collection: Use file-based (faster, no database required)
- Post-processing: Load into ClickHouse for aggregations, joins, time-series analytics
- Archival: Keep CSV files for portability, use database for active analysis

## AI Agent Integration

This package includes probe hooks (`gapless_crypto_clickhouse.__probe__`) that enable AI coding agents to discover functionality programmatically.

### For AI Coding Agent Users

To have your AI coding agent analyze this package, use this prompt:

```
Analyze gapless-crypto-clickhouse using: import gapless_crypto_clickhouse; probe = gapless_crypto_clickhouse.__probe__

Execute: probe.discover_api(), probe.get_capabilities(), probe.get_task_graph()

Provide insights about cryptocurrency data collection capabilities and usage patterns.
```

## Development

### Prerequisites

- **UV Package Manager** - [Install UV](https://docs.astral.sh/uv/getting-started/installation/)
- **Python 3.11+** - UV will manage Python versions automatically
- **Git** - For repository cloning and version control
- **Doppler CLI** (Optional) - For ClickHouse Cloud credential management

### Development Installation Workflow

**IMPORTANT**: This project uses **mandatory pre-commit hooks** to prevent broken code from being committed. All commits are automatically validated for formatting, linting, and basic quality checks.

#### Step 1: Clone Repository

```bash
git clone https://github.com/terrylica/gapless-crypto-clickhouse.git
cd gapless-crypto-clickhouse
```

#### Step 2: Development Environment Setup

```bash
# Create isolated virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install all dependencies (production + development)
uv sync --dev
```

#### Step 3: Verify Installation

```bash
# Run test suite
uv run pytest
```

#### Step 3a: Database Setup (Optional - ClickHouse Cloud)

If you want to develop with ClickHouse database features, configure credentials via Doppler or environment variables:

```bash
# Option 1: Doppler (recommended)
doppler setup  # Select aws-credentials/prd

# Option 2: Environment variables
export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
export CLICKHOUSE_PORT=8443
export CLICKHOUSE_PASSWORD=your-password
```

**Test database connection**:

```python
# Create a test script: test_clickhouse.py
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

with ClickHouseConnection() as conn:
    # Health check
    print(f"ClickHouse connected: {conn.health_check()}")

    # Test ingestion (small dataset)
    loader = ClickHouseBulkLoader(conn, instrument_type="spot")
    rows = loader.ingest_month("BTCUSDT", "1d", year=2024, month=1)
    print(f"Test ingestion: {rows} rows")

# Run test with Doppler
# doppler run -- uv run python test_clickhouse.py
```

#### Step 4: Set Up Pre-Commit Hooks (Mandatory)

```bash
# Install pre-commit hooks (prevents broken code from being committed)
uv run pre-commit install

# Test pre-commit hooks
uv run pre-commit run --all-files
```

#### Step 5: Development Tools

```bash
# Code formatting
uv run ruff format .

# Linting and auto-fixes
uv run ruff check --fix .

# Type checking
uv run mypy src/

# Run specific tests
uv run pytest tests/test_binance_collector.py -v

# Manual pre-commit validation
uv run pre-commit run --all-files
```

### Development Commands Reference

| Task                   | Command                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Install dependencies   | `uv sync --dev`                                                                       |
| Setup pre-commit hooks | `uv run pre-commit install`                                                           |
| Add new dependency     | `uv add package-name`                                                                 |
| Add dev dependency     | `uv add --dev package-name`                                                           |
| Run Python API         | `uv run python -c "import gapless_crypto_clickhouse as gcch; print(gcch.get_info())"` |
| Run tests              | `uv run pytest`                                                                       |
| Format code            | `uv run ruff format .`                                                                |
| Lint code              | `uv run ruff check --fix .`                                                           |
| Type check             | `uv run mypy src/`                                                                    |
| Validate pre-commit    | `uv run pre-commit run --all-files`                                                   |
| Build package          | `uv build`                                                                            |

### Production Validation

Automated validation of ClickHouse Cloud connectivity and data integrity runs via GitHub Actions (every 6 hours).

**Manual validation**:

```bash
# Validate ClickHouse Cloud connection
doppler run --project aws-credentials --config prd -- uv run scripts/validate_clickhouse_cloud.py

# Validate Binance CDN availability
uv run scripts/validate_binance_cdn.py
```

**CI/CD validation**: See `.github/workflows/production-validation.yml` for scheduled production health checks.

### Project Structure for Development

```
gapless-crypto-clickhouse/
├── src/gapless_crypto_clickhouse/        # Main package
│   ├── __init__.py                 # Package exports
│   ├── collectors/                 # Data collection modules
│   └── gap_filling/                # Gap detection/filling
├── tests/                          # Test suite
├── docs/                           # Documentation
├── examples/                       # Usage examples
├── pyproject.toml                  # Project configuration
└── uv.lock                        # Dependency lock file
```

### Building and Publishing

```bash
# Build package
uv build

# Publish to PyPI (requires API token)
uv publish
```

## Supported Timeframes

All Binance-supported timeframes for complete market coverage (standard + exotic):

| Timeframe  | Code  | Description              | Use Case                     |
| ---------- | ----- | ------------------------ | ---------------------------- |
| 1 second   | `1s`  | Ultra-high frequency     | HFT, microstructure analysis |
| 1 minute   | `1m`  | High resolution          | Scalping, order flow         |
| 3 minutes  | `3m`  | Short-term analysis      | Quick trend detection        |
| 5 minutes  | `5m`  | Common trading timeframe | Day trading signals          |
| 15 minutes | `15m` | Medium-term signals      | Swing trading entry          |
| 30 minutes | `30m` | Longer-term patterns     | Position management          |
| 1 hour     | `1h`  | Popular for backtesting  | Strategy development         |
| 2 hours    | `2h`  | Extended analysis        | Multi-timeframe confluence   |
| 4 hours    | `4h`  | Daily cycle patterns     | Trend following              |
| 6 hours    | `6h`  | Quarter-day analysis     | Position sizing              |
| 8 hours    | `8h`  | Third-day cycles         | Risk management              |
| 12 hours   | `12h` | Half-day patterns        | Overnight positions          |
| 1 day      | `1d`  | Daily analysis           | Long-term trends             |
| 3 days     | `3d`  | Multi-day patterns       | Weekly trend detection       |
| 1 week     | `1w`  | Weekly analysis          | Swing trading, market cycles |
| 1 month    | `1mo` | Monthly patterns         | Long-term strategy, macro    |

## Requirements

- Python 3.11+
- pandas >= 2.0.0
- Stable internet connection for data downloads

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Install development dependencies (`uv sync --dev`)
4. Make your changes
5. Run tests (`uv run pytest`)
6. Format code (`uv run ruff format .`)
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## API Reference

### BinancePublicDataCollector

Cryptocurrency spot data collection from Binance's public data repository using pre-generated monthly ZIP files.

#### Key Methods

**`__init__(symbol, start_date, end_date, output_dir)`**

Initialize the collector with trading pair and date range.

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",           # USDT spot pair
    start_date="2023-01-01",    # Start date (YYYY-MM-DD)
    end_date="2023-12-31",      # End date (YYYY-MM-DD)
    output_dir="./crypto_data"  # Output directory (optional)
)
```

**`collect_timeframe_data(trading_timeframe) -> Dict[str, Any]`**

Collect complete historical data for a single timeframe with microstructure format.

```python
result = collector.collect_timeframe_data("1h")
df = result["dataframe"]              # pandas DataFrame with OHLCV + microstructure
filepath = result["filepath"]         # Path to saved CSV file
stats = result["stats"]               # Collection statistics

# Access microstructure data
total_trades = df["number_of_trades"].sum()
taker_buy_ratio = df["taker_buy_base_asset_volume"].sum() / df["volume"].sum()
```

**`collect_multiple_timeframes(timeframes) -> Dict[str, Dict[str, Any]]`**

Collect data for multiple timeframes with comprehensive progress tracking.

```python
results = collector.collect_multiple_timeframes(["1h", "4h"])
for timeframe, result in results.items():
    df = result["dataframe"]
    print(f"{timeframe}: {len(df):,} bars")
```

### UniversalGapFiller

Gap detection and filling for various timeframes using Binance API data.

#### Key Methods

**`detect_all_gaps(csv_path, timeframe) -> List[Dict]`**

Automatically detect timestamp gaps in CSV files.

```python
gap_filler = UniversalGapFiller()
gaps = gap_filler.detect_all_gaps("BTCUSDT_1h_data.csv", "1h")
print(f"Found {len(gaps)} gaps to fill")
```

**`fill_gap(gap_info, csv_path, timeframe) -> bool`**

Fill a specific gap with authentic Binance API data.

```python
# Fill first detected gap
success = gap_filler.fill_gap(gaps[0], "BTCUSDT_1h_data.csv", "1h")
print(f"Gap filled successfully: {success}")
```

**`process_file(csv_path, timeframe) -> Dict`**

Process a single CSV file for gap detection and filling.

```python
result = gap_filler.process_file("BTCUSDT_1h_data.csv", "1h")
print(f"Filled {result['gaps_filled']}/{result['gaps_detected']} gaps")
```

### AtomicCSVOperations

Safe atomic operations for CSV files with header preservation and corruption prevention. Uses temporary files and atomic rename operations to ensure data integrity.

#### Key Methods

**`create_backup() -> Path`**

Create timestamped backup of original file before modifications.

```python
from pathlib import Path
atomic_ops = AtomicCSVOperations(Path("data.csv"))
backup_path = atomic_ops.create_backup()
```

**`write_dataframe_atomic(df) -> bool`**

Atomically write DataFrame to CSV with integrity validation.

```python
success = atomic_ops.write_dataframe_atomic(df)
if not success:
    atomic_ops.rollback_from_backup()
```

### SafeCSVMerger

Safe CSV data merging with gap filling capabilities and data integrity validation. Handles temporal data insertion while maintaining chronological order.

#### Key Methods

**`merge_gap_data_safe(gap_data, gap_start, gap_end) -> bool`**

Safely merge gap data into existing CSV using atomic operations.

```python
from datetime import datetime
merger = SafeCSVMerger(Path("eth_data.csv"))
success = merger.merge_gap_data_safe(
    gap_data,                    # DataFrame with gap data
    datetime(2024, 1, 1, 12),   # Gap start time
    datetime(2024, 1, 1, 15)    # Gap end time
)
```

## Output Formats

### DataFrame Structure (Python API)

Returns pandas DataFrame with microstructure format (see [Data Structure](#data-structure)):

| Column                         | Type           | Description            | Example               |
| ------------------------------ | -------------- | ---------------------- | --------------------- |
| `date`                         | datetime64[ns] | Open timestamp         | `2024-01-01 12:00:00` |
| `open`                         | float64        | Opening price          | `42150.50`            |
| `high`                         | float64        | Highest price          | `42200.00`            |
| `low`                          | float64        | Lowest price           | `42100.25`            |
| `close`                        | float64        | Closing price          | `42175.75`            |
| `volume`                       | float64        | Base asset volume      | `15.250000`           |
| `close_time`                   | datetime64[ns] | Close timestamp        | `2024-01-01 12:59:59` |
| `quote_asset_volume`           | float64        | Quote asset volume     | `643238.125`          |
| `number_of_trades`             | int64          | Trade count            | `1547`                |
| `taker_buy_base_asset_volume`  | float64        | Taker buy base volume  | `7.825000`            |
| `taker_buy_quote_asset_volume` | float64        | Taker buy quote volume | `329891.750`          |

### CSV File Structure

CSV files include header comments with metadata followed by data:

```csv
# Binance Spot Market Data
# Generated: 2025-01-15T12:00:00.000000+00:00Z
# Source: Binance Public Data Repository
# Market: SPOT | Symbol: BTCUSDT | Timeframe: 1h
# Coverage: 48 bars
# Period: 2024-01-01 00:00:00 to 2024-01-02 23:00:00
# Collection: direct_download in 0.0s
# Data Hash: 5fba9d2e5d3db849...
# Compliance: Zero-Magic-Numbers, Temporal-Integrity, Official-Binance-Source
#
date,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume
2024-01-01 00:00:00,42283.58,42554.57,42261.02,42475.23,1271.68108,2024-01-01 00:59:59,53957248.973789,47134,682.57581,28957416.819645
```

### Metadata JSON Structure

Each CSV file includes comprehensive metadata in `.metadata.json`:

```json
{
  "version": "<package_version>",
  "generator": "BinancePublicDataCollector",
  "data_source": "Binance Public Data Repository",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "enhanced_microstructure_format": {
    "total_columns": "<schema_column_count>",
    "analysis_capabilities": [
      "order_flow_analysis",
      "liquidity_metrics",
      "market_microstructure",
      "trade_weighted_prices",
      "institutional_data_patterns"
    ]
  },
  "gap_analysis": {
    "total_gaps_detected": 0,
    "data_completeness_score": 1.0,
    "gap_filling_method": "authentic_binance_api"
  },
  "data_integrity": {
    "chronological_order": true,
    "corruption_detected": false
  }
}
```

### File Naming Convention

Output files follow consistent naming pattern:

```
binance_spot_{SYMBOL}-{TIMEFRAME}_{START_DATE}-{END_DATE}_v{VERSION}.csv
binance_spot_{SYMBOL}-{TIMEFRAME}_{START_DATE}-{END_DATE}_v{VERSION}.metadata.json
```

Examples:

- `binance_spot_BTCUSDT-1h_20240101-20240102.csv`
- `binance_spot_ETHUSDT-4h_20240101-20240201.csv`
- `binance_spot_SOLUSDT-1d_20240101-20241231.csv`

### Error Handling

All classes implement robust error handling with meaningful exceptions:

```python
try:
    collector = BinancePublicDataCollector(symbol="INVALIDPAIR")
    result = collector.collect_timeframe_data("1h")
except ValueError as e:
    print(f"Invalid symbol format: {e}")
except ConnectionError as e:
    print(f"Network error: {e}")
except FileNotFoundError as e:
    print(f"Output directory error: {e}")
```

### Type Hints

All public APIs include comprehensive type hints for better IDE support:

```python
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd

def collect_timeframe_data(self, trading_timeframe: str) -> Dict[str, Any]:
    # Returns dict with 'dataframe', 'filepath', and 'stats' keys
    pass

def collect_multiple_timeframes(
    self,
    timeframes: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    # Returns nested dict by timeframe
    pass
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/terrylica/gapless-crypto-clickhouse/blob/main/LICENSE) file for details.
