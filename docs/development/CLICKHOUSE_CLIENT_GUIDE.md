# clickhouse-client Comprehensive Guide

## Overview

`clickhouse-client` is the official CLI for ClickHouse, providing production-ready query execution, 70+ output formats, and advanced features like AI-assisted query generation.

**Version**: 24.1+ (ships with ClickHouse)
**Protocol**: Native TCP (port 9000) - faster than HTTP
**License**: Apache 2.0

## Quick Start

### Via Docker (Recommended)
```bash
# Interactive mode
docker exec -it gapless-clickhouse clickhouse-client

# Single query
docker exec -it gapless-clickhouse clickhouse-client --query "SELECT count() FROM ohlcv FINAL"

# Output to file
docker exec -it gapless-clickhouse clickhouse-client \
  --query "SELECT * FROM ohlcv FINAL LIMIT 1000 FORMAT CSV" > data.csv
```

### Shell Aliases (Recommended)
Add to your `.zshrc` or `.bashrc`:

```bash
# Interactive client
alias ch='docker exec -it gapless-clickhouse clickhouse-client'

# Quick query
alias chq='docker exec -it gapless-clickhouse clickhouse-client --query'

# Format-specific aliases
alias ch-csv='docker exec -it gapless-clickhouse clickhouse-client --format CSV --query'
alias ch-json='docker exec -it gapless-clickhouse clickhouse-client --format JSONEachRow --query'
alias ch-parquet='docker exec -it gapless-clickhouse clickhouse-client --format Parquet --query'
```

## Features

### Core Capabilities
- ✅ **70+ output formats** (CSV, JSON, Parquet, Arrow, ORC, Markdown, etc.)
- ✅ **Progress bar** with real-time metrics (rows/sec, bytes, execution time)
- ✅ **Query parameters** for SQL injection prevention
- ✅ **AI-powered query generation** (`??` prefix with OpenAI/Anthropic)
- ✅ **Keyboard shortcuts** (Alt+Shift+E for editor, Ctrl+R for history)
- ✅ **In-client autocomplete** (SQL keywords, tables, columns)
- ✅ **Multiquery support** (semicolon-separated queries)
- ✅ **Session management** (SET commands persist across queries)

### Interactive Mode vs Batch Mode

**Interactive Mode**:
- Default format: `PrettyCompact` (human-readable tables)
- Progress bar enabled
- Query history navigation (Ctrl+R)
- Tab completion

**Batch Mode** (non-TTY):
- Default format: `TabSeparated` (machine-parseable)
- No progress bar
- Optimized for piping/redirection

## Output Formats (70+ Options)

### Common Formats

#### CSV
```bash
# Export to CSV
chq "SELECT * FROM ohlcv FINAL LIMIT 1000 FORMAT CSV" > data.csv

# Import from CSV
ch-csv "INSERT INTO ohlcv FORMAT CSV" < data.csv
```

#### JSON
```bash
# JSONEachRow (one JSON object per line)
chq "SELECT * FROM ohlcv FINAL LIMIT 100 FORMAT JSONEachRow" > data.jsonl

# JSONCompact (compact arrays)
chq "SELECT * FROM ohlcv FINAL LIMIT 100 FORMAT JSONCompact" > data.json

# JSON (full metadata)
chq "SELECT * FROM ohlcv FINAL LIMIT 100 FORMAT JSON" > data.json
```

#### Parquet
```bash
# Export to Parquet (columnar, compressed)
chq "SELECT * FROM ohlcv FINAL FORMAT Parquet" > data.parquet

# Import from Parquet
chq "INSERT INTO ohlcv FORMAT Parquet" < data.parquet
```

#### Markdown
```bash
# Pretty tables for documentation
chq "SELECT symbol, count() as bars FROM ohlcv FINAL GROUP BY symbol FORMAT Markdown"
```

#### Arrow / ORC
```bash
# Apache Arrow (in-memory columnar)
chq "SELECT * FROM ohlcv FINAL FORMAT Arrow" > data.arrow

# Apache ORC (Hadoop ecosystem)
chq "SELECT * FROM ohlcv FINAL FORMAT ORC" > data.orc
```

### Specialized Formats

```bash
# Vertical (one row per line, key-value pairs)
ch --query "SELECT * FROM ohlcv FINAL LIMIT 1 FORMAT Vertical"

# Pretty (colored, formatted tables)
ch --query "SELECT * FROM ohlcv FINAL LIMIT 10 FORMAT Pretty"

# PrettyCompact (condensed tables, default interactive)
ch --query "SELECT * FROM ohlcv FINAL LIMIT 10 FORMAT PrettyCompact"

# PrettyNoEscapes (no ANSI color codes)
ch --query "SELECT * FROM ohlcv FINAL LIMIT 10 FORMAT PrettyNoEscapes"

# Values (INSERT-ready format)
ch --query "SELECT * FROM ohlcv FINAL LIMIT 10 FORMAT Values"

# Null (no output, count rows only)
ch --query "SELECT * FROM ohlcv FINAL FORMAT Null"
```

## Query Parameters (SQL Injection Prevention)

### Parameterized Queries
```bash
# Safe parameter substitution
chq --param_symbol="BTCUSDT" --param_start="2024-01-01" \
  "SELECT * FROM ohlcv FINAL
   WHERE symbol = {symbol:String}
     AND timestamp >= {start:Date}"

# Multiple parameters with types
chq \
  --param_symbols="['BTCUSDT', 'ETHUSDT', 'SOLUSDT']" \
  --param_min_volume=1000000 \
  "SELECT symbol, avg(volume) as avg_vol
   FROM ohlcv FINAL
   WHERE symbol IN {symbols:Array(String)}
     AND volume >= {min_volume:Float64}
   GROUP BY symbol"
```

### Parameter Types
- `{name:String}` - Text
- `{name:Int64}` - Integer
- `{name:Float64}` - Decimal
- `{name:Date}` - Date
- `{name:DateTime}` - Timestamp
- `{name:Array(String)}` - String array
- `{name:UUID}` - UUID

## AI-Powered Query Generation

### OpenAI Integration
```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Generate query with ?? prefix
ch
> ?? show me top 10 symbols by trading volume

# AI generates and executes:
# SELECT symbol, sum(volume) as total_volume
# FROM ohlcv FINAL
# GROUP BY symbol
# ORDER BY total_volume DESC
# LIMIT 10
```

### Anthropic Integration
```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Same ?? syntax
ch
> ?? find gaps in BTCUSDT 1h data for last 30 days
```

## Keyboard Shortcuts

### Interactive Mode
- **Alt+Shift+E**: Open query in external editor ($EDITOR or vim)
- **Ctrl+R**: Search query history
- **Ctrl+C**: Interrupt running query
- **Ctrl+D**: Exit client
- **Tab**: Autocomplete SQL keywords, tables, columns
- **Up/Down**: Navigate query history

### Editor Integration
```bash
# Set preferred editor
export EDITOR=code  # VSCode
export EDITOR=vim   # Vim
export EDITOR=nano  # Nano

# In client, press Alt+Shift+E to edit query in editor
```

## Configuration

### Config File
Create `~/.clickhouse-client/config.yaml`:

```yaml
# Connection defaults
host: localhost
port: 9000
user: default
password: ''
database: default

# Output settings
format: PrettyCompact
max_rows_to_read: 1000000
max_result_rows: 10000

# Behavior
multiquery: true
progress: true
highlight: true
```

### Connection Strings
```bash
# Name connections in config
# ~/.clickhouse-client/config.yaml
connections:
  dev:
    host: localhost
    port: 9000
    database: default

  prod:
    host: prod-clickhouse.example.com
    port: 9000
    database: production

# Use named connections
ch --connection dev
ch --connection prod
```

## Advanced Usage

### Multiquery Mode
```bash
# Run multiple queries (semicolon-separated)
ch --multiquery --query "
  SELECT 'Query 1', count() FROM ohlcv;
  SELECT 'Query 2', count(DISTINCT symbol) FROM ohlcv;
  SELECT 'Query 3', max(timestamp) FROM ohlcv;
"
```

### Progress Tracking
```bash
# Enable detailed progress (rows/sec, bytes, time)
ch --query "SELECT * FROM ohlcv FINAL" --progress

# Output example:
# Progress: 1.50 million rows, 150.00 MB (500.00 thousand rows/s., 50.00 MB/s.)
```

### External Tables (Join with Files)
```bash
# Join ClickHouse table with local CSV
ch --query "
  SELECT o.symbol, e.name
  FROM ohlcv o
  JOIN external_symbols e ON o.symbol = e.symbol
" --external --file=symbols.csv --name=external_symbols --structure='symbol String, name String' --format=CSV
```

### Streaming Large Results
```bash
# Stream to stdout (memory-efficient)
ch --query "SELECT * FROM ohlcv FINAL FORMAT JSONEachRow" | gzip > data.jsonl.gz

# Process line-by-line
ch --query "SELECT * FROM ohlcv FINAL FORMAT JSONEachRow" | while read line; do
  echo "$line" | jq '.close'
done
```

## Common Workflows

### Data Export
```bash
# Full table export
chq "SELECT * FROM ohlcv FINAL FORMAT Parquet" > ohlcv_backup.parquet

# Filtered export
chq "SELECT * FROM ohlcv FINAL
     WHERE symbol = 'BTCUSDT'
       AND timeframe = '1h'
       AND timestamp >= '2024-01-01'
     FORMAT CSV" > btcusdt_1h_2024.csv

# Compressed export
chq "SELECT * FROM ohlcv FINAL FORMAT JSONEachRow" | gzip > ohlcv.jsonl.gz
```

### Data Import
```bash
# CSV import
chq "INSERT INTO ohlcv FORMAT CSV" < data.csv

# JSON import (one object per line)
chq "INSERT INTO ohlcv FORMAT JSONEachRow" < data.jsonl

# Parquet import
chq "INSERT INTO ohlcv FORMAT Parquet" < data.parquet
```

### Schema Management
```bash
# Show all tables
chq "SHOW TABLES FROM default"

# Describe table structure
chq "DESCRIBE TABLE ohlcv"

# Show CREATE statement
chq "SHOW CREATE TABLE ohlcv"

# Table statistics
chq "SELECT
       table,
       formatReadableSize(total_bytes) as size,
       formatReadableQuantity(total_rows) as rows
     FROM system.tables
     WHERE database = 'default'"
```

### Performance Analysis
```bash
# EXPLAIN query plan
ch --query "EXPLAIN PLAN SELECT * FROM ohlcv WHERE symbol = 'BTCUSDT'" --format Pretty

# EXPLAIN with indexes
ch --query "EXPLAIN PLAN indexes = 1 SELECT * FROM ohlcv WHERE symbol = 'BTCUSDT'" --format Pretty

# EXPLAIN AST
ch --query "EXPLAIN AST SELECT * FROM ohlcv FINAL" --format Pretty
```

## Troubleshooting

### Connection Issues

**Problem**: `Connection refused`
```bash
# Check ClickHouse status
docker ps | grep clickhouse

# Start if not running
docker-compose up -d clickhouse

# Test native protocol
nc -zv localhost 9000
```

**Problem**: `Authentication failed`
```bash
# Verify credentials
ch --user default --password ''

# Check environment
docker exec gapless-clickhouse clickhouse-client --query "SELECT currentUser()"
```

### Query Issues

**Problem**: `Memory limit exceeded`
```bash
# Increase memory limit
ch --max_memory_usage 10000000000 --query "SELECT * FROM ohlcv"

# Or use streaming
ch --query "SELECT * FROM ohlcv FORMAT JSONEachRow" | head -n 1000
```

**Problem**: `Syntax error`
```bash
# Check query with EXPLAIN
ch --query "EXPLAIN AST SELECT ..." --format Pretty

# Test in interactive mode (better error messages)
ch
> SELECT ...
```

## Best Practices

### Performance
- ✅ Use `FORMAT Null` for row counts (no data transfer)
- ✅ Use `LIMIT` for exploration (faster results)
- ✅ Use Parquet/Arrow for large exports (compressed, columnar)
- ❌ Avoid `SELECT *` on large tables without LIMIT

### Security
- ✅ Use query parameters to prevent SQL injection
- ✅ Use named connections (credentials in config, not CLI)
- ❌ Never pass user input directly in `--query`

### Automation
- ✅ Use batch mode for scripts (`--query` flag)
- ✅ Set `--format` explicitly (don't rely on defaults)
- ✅ Check exit codes (`$?` in bash)
- ❌ Don't parse PrettyCompact format (use CSV/JSON/TSV)

## Comparison with Other Tools

| Feature | clickhouse-client | CH-UI | Play UI |
|---------|------------------|-------|---------|
| Output Formats | 70+ | Table only | Table only |
| Progress Bar | ✅ Yes | ✅ Yes | ❌ No |
| Scripting | ✅ Excellent | ❌ No | ❌ No |
| Query History | ✅ Persistent | ✅ LocalStorage | ⚠️ URL only |
| AI Assistance | ✅ Yes | ❌ No | ❌ No |
| Autocomplete | ✅ SQL + Tables | ✅ Full | ❌ No |
| Best For | Automation | Exploration | Quick checks |

## Next Steps

- **For web interface**: Use [CH-UI](../CHUI_GUIDE.md)
- **For performance monitoring**: Use [chdig](./CHDIG_GUIDE.md)
- **For file analysis**: Use [clickhouse-local](./CLICKHOUSE_LOCAL_GUIDE.md)

## References

- Official docs: https://clickhouse.com/docs/en/interfaces/cli
- Format reference: https://clickhouse.com/docs/en/interfaces/formats
- ADR-0008: ClickHouse Local Visualization Toolchain
