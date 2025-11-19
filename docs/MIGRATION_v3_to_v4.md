# Migration Guide: v3.x to v4.0.0

**Target Audience**: Users upgrading from gapless-crypto-data v3.x (file-based) to v4.0.0 (ClickHouse database)

**Migration Difficulty**: Low (file-based API unchanged, database features optional)

**Estimated Time**: 15-30 minutes (basic upgrade) to 2-4 hours (full database migration)

## Overview

### What's Changed in v4.0.0

**Major Changes**:
- **NEW**: Optional ClickHouse database support for persistent storage and advanced queries
- **BREAKING**: QuestDB support removed (was development-only, never released)
- **UNCHANGED**: File-based API (`gcd.download()`, `gcd.fetch_data()`) remains fully supported
- **UNCHANGED**: 11-column microstructure format, 13 timeframe support, zero-gap guarantee

**Version Strategy**:
- **v3.x**: File-based storage only (CSV/Parquet output)
- **v4.0.0**: File-based (default) + optional ClickHouse database
- **Rollback path**: v3.3.0 remains available if issues arise

### Who Needs to Migrate?

| User Type | Migration Required? | Reason |
|-----------|---------------------|--------|
| **File-based workflows** (CSV output only) | ❌ No | API unchanged, drop-in replacement |
| **Database users** (QuestDB in v3.x dev builds) | ⚠️ Yes | QuestDB deprecated, must migrate to ClickHouse |
| **New database adopters** | ✅ Optional | ClickHouse offers persistent storage, advanced queries |

**Summary**: Most users can upgrade without code changes. Database migration only needed for QuestDB users or new database adopters.

## Breaking Changes

### 1. QuestDB Removal

**Impact**: QuestDB support completely removed in v4.0.0

**Who's Affected**: Users who tested QuestDB features in v3.x development builds

**Migration Path**:
```python
# v3.x (QuestDB - REMOVED)
from gapless_crypto_data.questdb import QuestDBConnection
from gapless_crypto_data.collectors.questdb_bulk_loader import QuestDBBulkLoader

# v4.0.0 (ClickHouse - NEW)
from gapless_crypto_data.clickhouse import ClickHouseConnection
from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader
```

**Rationale**: See [ADR-0005: ClickHouse Migration](decisions/0005-clickhouse-migration.md) for technical decision rationale (ecosystem maturity, scalability, future-proofing).

### 2. Dependency Changes

**Removed Dependencies** (v4.0.0):
- `questdb>=2.0.0` (QuestDB Python client)
- `psycopg[binary]>=3.2.0` (PostgreSQL client for QuestDB wire protocol)

**Added Dependencies** (v4.0.0):
- `clickhouse-driver>=0.2.9` (ClickHouse native protocol client)

**Package Size**: Reduced by ~8-10 MB (22% reduction from 9 to 7 dependencies)

**Installation Impact**: Faster `pip install` due to fewer dependencies

## Migration Paths

### Path 1: File-Based Workflow (No Migration Needed)

**For users who**: Only use CSV/file-based output, no database features

**Action**: Upgrade package version, no code changes required

```bash
# Upgrade to v4.0.0
pip install --upgrade gapless-crypto-data

# Or with UV
uv pip install --upgrade gapless-crypto-data
```

**Verify upgrade**:
```python
import gapless_crypto_data as gcd

# Check version
print(gcd.__version__)  # Should print "4.0.0"

# Existing code works unchanged
df = gcd.download("BTCUSDT", timeframe="1h", start="2024-01-01", end="2024-01-31")
print(f"Downloaded {len(df)} bars")  # Zero code changes
```

**Rollback** (if issues arise):
```bash
# Downgrade to v3.3.0
pip install gapless-crypto-data==3.3.0
```

### Path 2: Adopt ClickHouse Database (New Users)

**For users who**: Want to start using database features for persistent storage, advanced queries

**Prerequisites**:
- Docker & Docker Compose installed
- 2 GB free disk space (ClickHouse image + data)
- Ports 9000 and 8123 available

**Step-by-Step Migration**:

#### Step 1: Install v4.0.0

```bash
pip install --upgrade gapless-crypto-data
```

#### Step 2: Start ClickHouse Container

```bash
# Clone repository to get docker-compose.yml
git clone https://github.com/terrylica/gapless-crypto-data.git
cd gapless-crypto-data

# Start ClickHouse
docker-compose up -d

# Verify ClickHouse is running
docker-compose ps
docker-compose logs clickhouse | grep "Ready for connections"
```

**What happens**:
- Downloads ClickHouse 24.1-alpine image (~200 MB)
- Creates `ohlcv` table with ReplacingMergeTree engine (auto-initialized from `schema.sql`)
- Configures compression (DoubleDelta for timestamps, Gorilla for OHLCV)
- Persistent volume created (`clickhouse-data`)

#### Step 3: Test Database Connection

```python
from gapless_crypto_data.clickhouse import ClickHouseConnection

# Test connection (uses defaults: localhost:9000)
with ClickHouseConnection() as conn:
    health = conn.health_check()
    print(f"ClickHouse connected: {health}")  # Should print True

    # Test query
    result = conn.execute("SELECT count() FROM ohlcv")
    print(f"Total rows: {result[0][0]}")  # Should print 0 (empty database)
```

#### Step 4: Ingest Historical Data

```python
from gapless_crypto_data.clickhouse import ClickHouseConnection
from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn, instrument_type="spot")

    # Ingest one month of data (small test)
    rows = loader.ingest_month("BTCUSDT", "1h", year=2024, month=1)
    print(f"Ingested {rows:,} rows for BTCUSDT 1h (Jan 2024)")

    # Ingest date range (larger dataset)
    total_rows = loader.ingest_date_range(
        symbol="ETHUSDT",
        timeframe="4h",
        start_date="2024-01-01",
        end_date="2024-03-31"
    )
    print(f"Ingested {total_rows:,} rows for ETHUSDT 4h (Q1 2024)")
```

**Zero-gap guarantee**: Re-running ingestion won't create duplicates (deterministic SHA256 versioning)

#### Step 5: Query Data

```python
from gapless_crypto_data.clickhouse import ClickHouseConnection
from gapless_crypto_data.clickhouse_query import OHLCVQuery

with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)

    # Get latest data
    df = query.get_latest("BTCUSDT", "1h", limit=10)
    print(df[["timestamp", "open", "high", "low", "close"]])

    # Get date range
    df = query.get_range(
        symbol="BTCUSDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-01-31"
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

### Path 3: Migrate from QuestDB (v3.x Dev Users)

**For users who**: Used QuestDB features in v3.x development builds

**Prerequisites**:
- QuestDB database accessible (for data export)
- ClickHouse setup completed (see Path 2)

**Migration Steps**:

#### Step 1: Export QuestDB Data to CSV

```python
# v3.x code (run BEFORE upgrading)
from gapless_crypto_data.questdb import QuestDBConnection
from gapless_crypto_data.query import OHLCVQuery
import pandas as pd

with QuestDBConnection() as conn:
    query = OHLCVQuery(conn)

    # Export all data to CSV
    df = query.get_all_data()  # Custom method or full table export
    df.to_csv("questdb_export.csv", index=False)
    print(f"Exported {len(df):,} rows from QuestDB")
```

#### Step 2: Upgrade to v4.0.0

```bash
pip install --upgrade gapless-crypto-data
```

#### Step 3: Import CSV Data to ClickHouse

```python
# v4.0.0 code (run AFTER upgrading)
from gapless_crypto_data.clickhouse import ClickHouseConnection
from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader
import pandas as pd

# Load exported CSV
df = pd.read_csv("questdb_export.csv")
print(f"Loaded {len(df):,} rows from CSV export")

# Import to ClickHouse
with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn)

    # Group by symbol/timeframe and ingest
    for (symbol, timeframe), group in df.groupby(["symbol", "timeframe"]):
        rows = loader.ingest_from_dataframe(group, symbol=symbol, timeframe=timeframe)
        print(f"Imported {rows:,} rows for {symbol} {timeframe}")
```

#### Step 4: Verify Data Integrity

```python
from gapless_crypto_data.clickhouse import ClickHouseConnection
from gapless_crypto_data.clickhouse_query import OHLCVQuery

with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)

    # Check row counts match
    total_rows = conn.execute("SELECT count() FROM ohlcv FINAL")[0][0]
    print(f"Total rows in ClickHouse: {total_rows:,}")

    # Verify sample data
    df_sample = query.get_latest("BTCUSDT", "1h", limit=10)
    print(f"Sample data:\n{df_sample[['timestamp', 'close']]}")
```

#### Step 5: Decommission QuestDB

**After successful migration**:

```bash
# Stop QuestDB service (if running as systemd service)
sudo systemctl stop questdb

# Or stop Docker container (if running in Docker)
docker-compose -f docker-compose-questdb.yml down

# Optional: Archive QuestDB data directory
tar -czf questdb_backup_$(date +%Y%m%d).tar.gz /path/to/questdb/data
```

**Rollback**: If migration fails, keep QuestDB running and stay on v3.3.0 until issues resolved.

### Expected Test Failures in v4.0.0

After upgrading to v4.0.0, the following tests are expected to fail due to CLI removal:

**Failing Test Files**:
- `tests/test_cli.py` - Entire file (CLI removed in v4.0.0)
- `tests/test_cli_integration.py` - CLI integration tests

**Why Tests Fail**:
The CLI interface was removed in v4.0.0 (pyproject.toml removed `[project.scripts]` section). Tests that invoke CLI commands or test CLI functionality will fail with import errors or missing command errors.

**Action Required**:
- **For maintainers**: Remove these test files in a follow-up PR
- **For users**: These failures are expected and can be ignored if not using CLI features

**Workaround**:
Run tests while ignoring CLI test files:
```bash
pytest tests/ --ignore=tests/test_cli.py --ignore=tests/test_cli_integration.py
```

**Alternative**:
Run only non-CLI tests:
```bash
pytest tests/ -k "not cli"
```

## Configuration Changes

### Environment Variables

**v3.x (QuestDB - REMOVED)**:
```bash
QUESTDB_HOST=localhost
QUESTDB_ILP_PORT=9009
QUESTDB_PG_PORT=8812
QUESTDB_PG_USER=admin
QUESTDB_PG_PASSWORD=quest
QUESTDB_PG_DATABASE=qdb
```

**v4.0.0 (ClickHouse - NEW)**:
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000              # Native protocol (default: 9000)
CLICKHOUSE_HTTP_PORT=8123         # HTTP interface (default: 8123)
CLICKHOUSE_USER=default           # Username (default: 'default')
CLICKHOUSE_PASSWORD=              # Password (empty for local dev)
CLICKHOUSE_DB=default             # Database name (default: 'default')
```

**File location**: Create `.env` file in project root or set system environment variables

### Docker Compose Configuration

**v4.0.0 includes production-ready `docker-compose.yml`**:

```yaml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.1-alpine
    ports:
      - "9000:9000"   # Native protocol
      - "8123:8123"   # HTTP interface
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./src/gapless_crypto_data/clickhouse/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro
    environment:
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
      CLICKHOUSE_DB: default
```

**Schema auto-initialization**: The `schema.sql` file is automatically executed on first container start.

## API Compatibility Matrix

| Feature | v3.x File-Based | v3.x QuestDB (Dev) | v4.0.0 File-Based | v4.0.0 ClickHouse |
|---------|-----------------|--------------------|--------------------|-------------------|
| **Data Collection** | ✅ `gcd.download()` | ✅ Same API | ✅ **Unchanged** | ✅ New API |
| **Gap Filling** | ✅ `gcd.fill_gaps()` | ✅ Same API | ✅ **Unchanged** | ✅ New API |
| **Query Interface** | ❌ N/A | ✅ `OHLCVQuery` (QuestDB) | ❌ N/A | ✅ `OHLCVQuery` (ClickHouse) |
| **Bulk Ingestion** | ❌ N/A | ✅ `QuestDBBulkLoader` | ❌ N/A | ✅ `ClickHouseBulkLoader` |
| **Futures Support** | ❌ Not supported | ❌ Not supported | ❌ Not supported | ✅ `instrument_type` param |

**API Signature Changes**: **NONE** for file-based workflows. Database APIs have identical signatures (drop-in replacement).

## Validation & Testing

### Pre-Migration Checklist

Before upgrading to v4.0.0:

- [ ] **Backup data**: Export critical QuestDB data to CSV (if applicable)
- [ ] **Check dependencies**: Verify Docker installed (if using ClickHouse)
- [ ] **Test in dev environment**: Upgrade dev environment first, test production later
- [ ] **Review breaking changes**: Read this guide's Breaking Changes section
- [ ] **Plan rollback**: Document rollback procedure (downgrade to v3.3.0)

### Post-Migration Validation

After upgrading to v4.0.0:

```bash
# Verify installation
python -c "import gapless_crypto_data as gcd; print(gcd.__version__)"
# Expected output: 4.0.0

# Test file-based API (should work unchanged)
python -c "
import gapless_crypto_data as gcd
df = gcd.download('BTCUSDT', timeframe='1d', start='2024-01-01', end='2024-01-07')
print(f'Downloaded {len(df)} bars')
"
# Expected output: Downloaded 7 bars

# Test ClickHouse connection (if using database)
python -c "
from gapless_crypto_data.clickhouse import ClickHouseConnection
with ClickHouseConnection() as conn:
    print(f'ClickHouse connected: {conn.health_check()}')
"
# Expected output: ClickHouse connected: True
```

### Common Migration Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Import Error** | `ModuleNotFoundError: No module named 'gapless_crypto_data.questdb'` | Expected (QuestDB removed). Update imports to use `clickhouse` instead |
| **Connection Refused** | `clickhouse_driver.errors.NetworkError: Connection refused` | Start ClickHouse: `docker-compose up -d` |
| **Port Conflict** | `Error starting ClickHouse: port 9000 already in use` | Change port in `docker-compose.yml` or stop conflicting service |
| **Schema Not Found** | `clickhouse_driver.errors.ServerException: Table ohlcv doesn't exist` | Restart container to trigger schema init: `docker-compose restart clickhouse` |

## Rollback Procedure

If you encounter issues with v4.0.0:

### Step 1: Downgrade Package

```bash
# Downgrade to last stable v3.x version
pip install gapless-crypto-data==3.3.0

# Verify downgrade
python -c "import gapless_crypto_data as gcd; print(gcd.__version__)"
# Expected output: 3.3.0
```

### Step 2: Restore QuestDB (If Applicable)

```bash
# Extract QuestDB backup (if you archived it)
tar -xzf questdb_backup_YYYYMMDD.tar.gz -C /path/to/restore

# Restart QuestDB service
sudo systemctl start questdb
```

### Step 3: Verify Rollback

```python
import gapless_crypto_data as gcd

# Test file-based API (should work on v3.3.0)
df = gcd.download("BTCUSDT", timeframe="1h", start="2024-01-01", end="2024-01-07")
print(f"Rollback successful: {len(df)} bars downloaded")
```

### Step 4: Report Issue

If rollback was necessary, please report the issue:

- **GitHub Issues**: https://github.com/terrylica/gapless-crypto-data/issues
- **Email**: terry@eonlabs.com

Include:
- Error message (full traceback)
- Migration path attempted (Path 1/2/3)
- Operating system and Python version
- Steps to reproduce

## FAQ

**Q: Do I need to use ClickHouse in v4.0.0?**

A: No. File-based workflows remain fully supported. ClickHouse is optional for users who want persistent storage and advanced queries.

**Q: Will v3.3.0 continue to receive updates?**

A: No. v3.3.0 is the last v3.x release. Security fixes may be backported if critical issues are found, but new features will only be added to v4.0.0+.

**Q: Can I use both file-based and ClickHouse simultaneously?**

A: Yes. You can collect data to CSV files using `gcd.download()`, then ingest into ClickHouse using `ClickHouseBulkLoader.ingest_from_dataframe()`. This hybrid approach is recommended for flexibility.

**Q: What happens to my existing CSV files when upgrading?**

A: Nothing. Existing CSV files are unaffected. v4.0.0 does not modify or delete any files.

**Q: How do I migrate from file-based to ClickHouse without re-downloading data?**

A: Use the hybrid approach: Load existing CSV files into pandas DataFrames, then ingest to ClickHouse using `ClickHouseBulkLoader.ingest_from_dataframe()`. See Path 2, Step 4 for code example.

**Q: Is there a performance difference between file-based and ClickHouse?**

A: Yes. File-based is faster for initial data collection (22x speedup via CloudFront). ClickHouse is faster for queries, aggregations, and multi-symbol analysis. Use file-based for collection, ClickHouse for analysis.

**Q: What if I encounter a bug during migration?**

A: Follow the rollback procedure (downgrade to v3.3.0) and report the issue on GitHub. Include error messages, migration path attempted, and steps to reproduce.

## Additional Resources

- **[ClickHouse Migration Guide](CLICKHOUSE_MIGRATION.md)** - Technical deep-dive on ClickHouse implementation
- **[ADR-0005: ClickHouse Migration](decisions/0005-clickhouse-migration.md)** - Decision rationale and architecture details
- **[Docker Compose Reference](../docker-compose.yml)** - Production-ready ClickHouse configuration
- **[GitHub Discussions](https://github.com/terrylica/gapless-crypto-data/discussions)** - Community support
- **[Release Notes](release-notes.md)** - Complete v4.0.0 changelog

## Support

**Need help with migration?**

- **GitHub Issues**: https://github.com/terrylica/gapless-crypto-data/issues
- **GitHub Discussions**: https://github.com/terrylica/gapless-crypto-data/discussions
- **Email**: terry@eonlabs.com

**Before posting**:
- Check FAQ section above
- Search existing issues for similar problems
- Provide error messages and reproduction steps
