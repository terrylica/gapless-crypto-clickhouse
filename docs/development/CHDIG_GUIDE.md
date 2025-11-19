# chdig TUI Performance Monitoring Guide

## Overview

`chdig` is a Rust-based terminal user interface (TUI) for ClickHouse performance monitoring and profiling. It provides top-like interactive views, flamegraph visualization, and real-time query metrics.

**Version**: 25.11.1+ (actively maintained)
**Language**: Rust (98.2%)
**License**: MIT
**Status**: Pre-alpha (interface may change)

**⚠️ Important**: chdig is monitoring-only (no data manipulation). For queries, use [clickhouse-client](./CLICKHOUSE_CLIENT_GUIDE.md) or [CH-UI](../CHUI_GUIDE.md).

## Installation

### Homebrew (macOS)
```bash
brew install chdig
```

### Scoop (Windows)
```bash
scoop bucket add extras
scoop install extras/chdig
```

### AUR (Arch Linux)
```bash
yay -S chdig-latest-bin
```

### Cargo (All Platforms)
```bash
cargo install chdig
```

### Verify Installation
```bash
which chdig
# Output: /opt/homebrew/bin/chdig (or similar)

chdig --version
# Output: chdig 25.11.1 (or later)
```

## Quick Start

### Basic Usage
```bash
# Monitor local ClickHouse instance
chdig --host localhost --port 9000

# With credentials
chdig --host localhost --port 9000 --user default --password ''

# Monitor cluster
chdig --cluster my_cluster
```

### Connection via Docker
```bash
# Monitor Docker ClickHouse
chdig --host localhost --port 9000
```

## Features

### Interactive Views

Press keys to switch views:

- **`q`** - Slow queries (queries taking longer than threshold)
- **`r`** - Recent queries (last executed queries)
- **`p`** - Query processors (execution pipeline stages)
- **`b`** - Backups status
- **`n`** - Replicas status
- **`s`** - Servers list (cluster view)
- **`f`** - Flamegraph visualization (CPU, memory)
- **`h`** - Help (show keyboard shortcuts)
- **`q`** - Quit (exit chdig)

### Flamegraph Visualization

**What it shows**: CPU/memory usage broken down by query stages

**How to use**:
1. Press `f` to open flamegraph view
2. Navigate with arrow keys
3. Press `Enter` to zoom into section
4. Press `Esc` to zoom out
5. Press `q` to exit flamegraph

**Use cases**:
- Identify slow query stages (JOINs, aggregations, filters)
- Spot memory-hungry operations
- Optimize query performance

### Query Monitoring

#### Slow Queries View (`q`)
Shows queries exceeding configured threshold.

**Columns**:
- Query ID
- User
- Elapsed time
- Read rows
- Read bytes
- Memory usage
- Query text (truncated)

**Sort**: By elapsed time (descending)

**Action**: Identify and optimize slow queries

#### Recent Queries View (`r`)
Shows last N executed queries.

**Columns**:
- Timestamp
- Query ID
- Elapsed time
- Status (running/completed/failed)
- Query text

**Use case**: Real-time monitoring during development

### Cluster Monitoring (`s`)

**Shows**:
- Server hostname
- Status (healthy/degraded)
- CPU usage
- Memory usage
- Disk usage
- Active queries

**Use case**: Multi-node cluster health checks

## Configuration

### Connection Options
```bash
# Host and port
chdig --host clickhouse.example.com --port 9000

# Authentication
chdig --host localhost --user admin --password 'secret'

# Database
chdig --host localhost --database production

# SSL/TLS
chdig --host secure-ch.example.com --secure
```

### Monitoring Options
```bash
# Slow query threshold (seconds)
chdig --slow-query-threshold 5.0

# Refresh interval (seconds)
chdig --refresh-interval 2.0

# Historical analysis (rotated system logs)
chdig --history --from '2024-01-01' --to '2024-01-31'
```

### Cluster Mode
```bash
# Monitor entire cluster
chdig --cluster production_cluster

# Specific shard
chdig --cluster production_cluster --shard 1

# Specific replica
chdig --cluster production_cluster --shard 1 --replica 2
```

## Use Cases

### Development

#### Monitor Ingestion Performance
```bash
# Terminal 1: Run chdig
chdig --host localhost --port 9000

# Terminal 2: Start ingestion
python -m gapless_crypto_data.collectors.clickhouse_bulk_loader

# In chdig:
# - Press 'r' for recent queries
# - Watch INSERT performance (rows/sec, memory usage)
# - Press 'f' for flamegraph if slow
```

#### Optimize Queries
```bash
# Run chdig
chdig --host localhost --port 9000

# Execute query in another terminal
docker exec gapless-clickhouse clickhouse-client --query "
  SELECT
    symbol,
    avg(close)
  FROM ohlcv FINAL
  WHERE timestamp >= now() - INTERVAL 30 DAY
  GROUP BY symbol
"

# In chdig:
# - Press 'q' for slow queries
# - Check execution time, memory usage
# - Press 'f' for flamegraph to identify bottlenecks
```

### Debugging

#### Identify Memory Leaks
1. Start chdig: `chdig --host localhost --port 9000`
2. Press `p` for query processors view
3. Watch memory column during query execution
4. Press `f` for memory flamegraph
5. Identify stages consuming excessive memory

#### Find Long-Running Queries
1. Start chdig
2. Press `r` for recent queries
3. Look for queries with high elapsed time
4. Press `f` to see where time is spent (flamegraph)
5. Optimize identified bottlenecks

### Production Monitoring (Future)

**⚠️ Pre-alpha Status**: Interface may change, test thoroughly before production use

```bash
# Run chdig in tmux/screen for persistent monitoring
tmux new -s clickhouse-monitor
chdig --host prod-clickhouse --port 9000 --secure --user monitor --password $MONITOR_PASS

# Detach: Ctrl+b, then d
# Reattach: tmux attach -t clickhouse-monitor
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Slow queries view |
| `r` | Recent queries view |
| `p` | Query processors view |
| `b` | Backups status |
| `n` | Replicas status |
| `s` | Servers list (cluster) |
| `f` | Flamegraph visualization |
| `h` | Help (shortcuts) |
| `↑`/`↓` | Navigate list |
| `Enter` | Zoom in (flamegraph) |
| `Esc` | Zoom out (flamegraph) |
| `Ctrl+C` or `q` | Quit |

## Flamegraph Interpretation

### CPU Flamegraph
- **Wide boxes**: Operations consuming most CPU time
- **Deep stacks**: Complex nested operations
- **Hot paths**: Wide boxes at top of stack (optimization targets)

**Example**:
```
┌────────────────────────────────────────────┐
│          Aggregation (50%)                 │  <- Optimize this
├───────────┬────────────────────────────────┤
│  Filter   │        JOIN                    │
│   (10%)   │        (40%)                   │
└───────────┴────────────────────────────────┘
```
**Interpretation**: JOIN consumes 40% of CPU, aggregation 50% → Optimize JOIN first, then aggregation

### Memory Flamegraph
- **Wide boxes**: Operations allocating most memory
- **Persistent boxes**: Memory not freed (potential leak)

**Example**:
```
┌────────────────────────────────────────────┐
│      HashTable (80%)                       │  <- High memory usage
├────────────────────────────────────────────┤
│      GROUP BY                              │
└────────────────────────────────────────────┘
```
**Interpretation**: GROUP BY hash table consuming 80% memory → Consider using LIMIT or pre-aggregation

## Troubleshooting

### Connection Failed
```bash
# Check ClickHouse running
docker ps | grep clickhouse

# Test connection
docker exec gapless-clickhouse clickhouse-client --query "SELECT 1"

# Verify port (native protocol, not HTTP)
chdig --host localhost --port 9000  # ✅ Correct
chdig --host localhost --port 8123  # ❌ Wrong (HTTP port)
```

### No Data Displayed
**Cause**: ClickHouse 21.2+ required

**Solution**:
```bash
# Check ClickHouse version
docker exec gapless-clickhouse clickhouse-client --query "SELECT version()"

# Upgrade if needed (edit docker-compose.yml)
image: clickhouse/clickhouse-server:24.1-alpine  # ✅ Supported
```

### Flamegraph Empty
**Cause**: No queries running or system.query_log disabled

**Solution**:
1. Run a query in another terminal
2. Immediately switch to chdig and press `f`
3. Ensure `system.query_log` enabled (default in Docker)

### Pre-Alpha Warnings
**Issue**: Interface may change in future versions

**Mitigation**:
- Pin version in Homebrew: `brew pin chdig`
- Test updates in non-production first
- Monitor changelog: https://github.com/azat/chdig/releases

## Comparison with Other Tools

| Feature | chdig | CH-UI | clickhouse-client |
|---------|-------|-------|-------------------|
| Interface | TUI | Web | CLI |
| Flamegraph | ✅ Yes | ❌ No | ❌ No |
| Real-time Metrics | ✅ Yes | ✅ Yes | ❌ No |
| Query Execution | ❌ No | ✅ Yes | ✅ Yes |
| Cluster View | ✅ Yes | ⚠️ Limited | ❌ No |
| Best For | Monitoring | Exploration | Automation |

## Integration with Other Tools

### chdig + clickhouse-client Workflow
```bash
# Terminal 1: Monitor performance
chdig --host localhost --port 9000

# Terminal 2: Execute queries
docker exec -it gapless-clickhouse clickhouse-client
> SELECT ... (query here)

# Watch in chdig:
# - Recent queries view ('r')
# - Slow queries if needed ('q')
# - Flamegraph for optimization ('f')
```

### chdig + CH-UI Workflow
```bash
# Start chdig
chdig --host localhost --port 9000

# Open CH-UI in browser
open http://localhost:5521

# Execute query in CH-UI
# Watch performance in chdig (recent queries, flamegraph)
```

## Best Practices

### Development
- ✅ Run chdig during ingestion testing
- ✅ Use flamegraph to identify slow stages
- ✅ Monitor memory usage for large queries
- ❌ Don't rely on chdig for query execution (use clickhouse-client)

### Performance Tuning
- ✅ Identify slow queries first (`q` view)
- ✅ Use flamegraph to pinpoint bottlenecks
- ✅ Test optimization impact (before/after flamegraphs)
- ❌ Don't optimize queries without profiling first

### Production (Future)
- ⚠️ Test interface stability before deploying
- ✅ Use tmux/screen for persistent monitoring
- ✅ Set up alerts based on slow query threshold
- ❌ Don't use for query execution (monitoring only)

## Next Steps

- **For query execution**: Use [clickhouse-client](./CLICKHOUSE_CLIENT_GUIDE.md)
- **For web interface**: Use [CH-UI](../CHUI_GUIDE.md)
- **For file analysis**: Use [clickhouse-local](./CLICKHOUSE_LOCAL_GUIDE.md)

## References

- GitHub: https://github.com/azat/chdig
- Latest release: https://github.com/azat/chdig/releases
- Flamegraph theory: http://www.brendangregg.com/flamegraphs.html
- ADR-0008: ClickHouse Local Visualization Toolchain
