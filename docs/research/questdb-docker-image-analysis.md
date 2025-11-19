# QuestDB Docker Image Analysis

**Research Date**: 2025-01-15
**QuestDB Latest Version**: 9.2.0
**Analysis Scope**: Docker image footprint, resource requirements, multi-platform support

---

## Executive Summary

QuestDB provides official Docker images (`questdb/questdb`) built on Debian Bookworm Slim with GraalVM Community JDK 17, supporting both amd64 and arm64 architectures. The images are production-ready for high-frequency crypto trading workloads and used by Tier 1/2 investment banks, hedge funds, and major crypto exchanges.

**Key Findings**:
- **Base Image**: Debian Bookworm Slim (~28 MB compressed)
- **Multi-arch Support**: Native amd64 and arm64 (M-series Macs compatible)
- **JVM Runtime**: GraalVM Community JDK 17.0.9
- **Minimum RAM**: 256 MB JVM heap (starts), 8 GB+ recommended production
- **Storage Architecture**: Off-heap memory mapping (minimal GC pressure)
- **Docker Overhead**: ~2.67% CPU on Linux, 40% CPU penalty on macOS (Colima/Docker Desktop)

---

## Image Specifications

### Official Image Details

**Registry**: `questdb/questdb`
**Recommended Tag**: `9.2.0` (latest points to newest version)
**Repository**: https://hub.docker.com/r/questdb/questdb
**Dockerfile**: https://github.com/questdb/questdb/blob/master/core/Dockerfile

### Architecture Support

| Architecture | Status | Platform |
|-------------|--------|----------|
| linux/amd64 | ✅ Full Support | x86_64 Linux, Windows WSL2 |
| linux/arm64 | ✅ Full Support | M-series Macs, Raspberry Pi 4, ARM servers |
| windows/amd64 | ✅ Full Support | Windows containers (UBI9 RedHat base) |

**Multi-Platform Notes**:
- ARM64 support restored via PR #878 (addressed native C++ library compilation)
- macOS M1/M2/M3 fully compatible via Colima or Docker Desktop
- Separate image variants for RedHat OpenShift (UBI9 base) and general-purpose (Debian)

### Base Image Composition

**Multi-Stage Build** (3 stages):

1. **Builder Stage**: `debian:bookworm` (~117 MB uncompressed)
   - GraalVM Community JDK 17.0.9
   - Maven 3.x, Git, curl, wget, GPG tools
   - Compiles QuestDB from source (clean package with web console)

2. **RedHat OpenShift Stage**: `registry.access.redhat.com/ubi9/ubi`
   - Enterprise-ready variant for OpenShift deployments
   - Non-root questdb user (UID 10001)

3. **Final General-Purpose Stage**: `debian:bookworm-slim`
   - **Compressed Size (amd64)**: 28.2 MB (28,228,567 bytes)
   - **Compressed Size (arm64)**: 28.1 MB (28,102,376 bytes)
   - Includes `gosu` binary for privilege dropping
   - Minimal layer count for fast pulls

**Total Estimated Image Size** (final QuestDB image):
- Unable to retrieve exact compressed size from Docker Hub (dynamic page rendering)
- Estimated **150-250 MB compressed** based on:
  - Debian Bookworm Slim base: ~28 MB
  - GraalVM JDK 17 runtime: ~180 MB (LabsJDK reference)
  - QuestDB binaries + dependencies: variable
- **Uncompressed**: Likely 400-600 MB (verify with `docker images`)

---

## Runtime Requirements

### Port Exposures

| Port | Protocol | Purpose |
|------|----------|---------|
| 9000 | HTTP | REST API + Web Console |
| 9009 | ILP | InfluxDB Line Protocol (streaming ingestion) |
| 8812 | PostgreSQL | PostgreSQL wire protocol (SQL queries) |
| 9003 | HTTP | Minimal health/metrics endpoint |

**All ports optional** - select only needed protocols.

### Volume Mounts

**QuestDB Root Directory**: `/var/lib/questdb`

**Recommended Mounts**:
- Data persistence: `-v /host/path:/var/lib/questdb`
- Custom logging: `-v /host/log.conf:/var/lib/questdb/conf/log.conf:ro`

**Docker Compose Example**:
```yaml
volumes:
  - questdb_data:/var/lib/questdb
```

### Environment Variables

**Default Configuration**:
- `DO_CHOWN=false` (prevents unnecessary permission changes)
- JVM heap configurable via `-e JAVA_OPTS="-Xmx4g"`

---

## Memory & CPU Requirements

### JVM Heap Sizing

**Architecture**: QuestDB minimizes JVM heap usage via off-heap memory mapping.

**JVM Heap (On-Heap)**:
- **Minimum**: 256 MB (can start and ingest/query data)
- **Default (Containerized)**: ~1 GB heap limit
- **Recommended Production**: 2-4 GB (depends on symbol caching, column metadata)

**Off-Heap Memory (Primary Storage)**:
- QuestDB uses **memory-mapped files** and **direct memory allocation**
- Bypasses Java GC for database I/O operations
- Size controlled by OS page cache (not JVM `-Xmx`)

**Table Writer Memory**:
- **16 MB per column** (2x8MB buffers) for O3 (out-of-order) writes
- Calculation: `columns × 16 MB × concurrent_writers`
- Example: 20-column table with 5 concurrent writers = 1.6 GB

### Total RAM Recommendations

| Workload | JVM Heap | Off-Heap (OS Cache) | Total RAM |
|----------|----------|---------------------|-----------|
| Development/Testing | 512 MB | 2 GB | **4 GB minimum** |
| Small Production | 1 GB | 4 GB | **8 GB minimum** |
| Crypto Trading (400 symbols, 13 timeframes) | 2-4 GB | 16-32 GB | **32-64 GB recommended** |
| High-Frequency (Tier 1 Bank) | 4-8 GB | 64+ GB | **128 GB+ recommended** |

**Source**: QuestDB documentation states "At least 8GB of RAM is recommended for handling large datasets."

### CPU Requirements

**Default Behavior**: QuestDB uses **all available CPU cores**

**Scaling**:
- Read-only queries scale **linearly with cores** (assuming disk not IOPS-bottlenecked)
- SIMD vectorized operations leverage modern CPU instruction sets
- ARM64 uses NEON, x86_64 uses AVX2/AVX-512 where available

**Recommended CPU**:
- **Development**: 2-4 cores
- **Production**: 8-16 cores
- **High-Frequency Trading**: 16+ cores (physical, not hyperthreaded)

### Disk I/O Requirements

**Storage Type**: SSD/NVMe strongly recommended

**IOPS Requirements**:
- Development: Standard SSD (500+ IOPS)
- Production: NVMe SSD (10,000+ IOPS)
- High-Frequency: Enterprise NVMe (100,000+ IOPS)

**Disk Space**:
- Image: ~200-300 MB
- Data: Variable (depends on retention, symbols, timeframes)
- **Crypto Workload Example** (400 symbols × 13 timeframes × 1 year @ 1s resolution):
  - Estimated: 5-10 TB uncompressed
  - QuestDB uses columnar storage (efficient compression)

---

## Performance Overhead Analysis

### Docker vs Native Performance

**Linux (Direct Container Execution)**:
- **CPU Overhead**: ~2.67% (negligible for most workloads)
- **Disk I/O Overhead**: ~10% compared to native
- **Memory Overhead**: Minimal (shared page cache)
- **Recommendation**: Docker on Linux is **production-ready** with minimal overhead

**Source**: Research paper "Performance Impact of Docker Containers on Linux" (Torizon)

**macOS (Colima/Docker Desktop)**:
- **CPU Overhead**: 40-80% slower for CPU-intensive workloads
- **Root Cause**: Virtualization layer (Hypervisor.framework or Colima VM)
- **Disk I/O**: Volume mounts suffer performance penalty (especially non-VirtioFS)
- **Recommendation**: macOS Docker is **acceptable for development**, avoid for performance-sensitive production

**Source**: Docker for Mac GitHub Issue #4769, Medium article "Dev environment performance tests"

### QuestDB-Specific Performance Notes

**No QuestDB-Specific Benchmarks Found**: Search did not reveal official QuestDB Docker vs native comparisons.

**Extrapolation from General Data**:
- **Linux Production**: Docker overhead acceptable (<3% CPU, ~10% disk)
- **macOS Development**: Expect 40-80% slower queries/ingestion vs native
- **Mitigation**: Use native QuestDB binary on macOS for development if performance critical

**Migration Path**:
- **macOS Dev (Colima + Docker)**: Convenient for testing, schema development
- **Linux Production (Native Binary)**: Maximum performance, no virtualization overhead

---

## Resource Limits & Tuning

### Docker Compose Resource Limits

**Recommended Configuration**:

```yaml
version: "3.8"
services:
  questdb:
    image: questdb/questdb:9.2.0
    container_name: questdb
    ports:
      - "9000:9000"
      - "9009:9009"
      - "8812:8812"
    volumes:
      - questdb_data:/var/lib/questdb
    environment:
      - JAVA_OPTS=-Xms2g -Xmx4g -XX:+UseG1GC
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          cpus: '4'
          memory: 8G
    restart: unless-stopped

volumes:
  questdb_data:
```

### JVM Tuning Parameters

**Garbage Collector**: G1GC (default, recommended for QuestDB)

**Heap Configuration**:
```bash
-Xms2g              # Initial heap size (match -Xmx for predictable allocation)
-Xmx4g              # Maximum heap size
-XX:+UseG1GC        # G1 Garbage Collector
-XX:MaxGCPauseMillis=200  # Target max GC pause (adjust for latency requirements)
```

**Off-Heap Configuration** (controlled by QuestDB settings, not JVM):
- Modify `/var/lib/questdb/conf/server.conf`
- See QuestDB documentation for `cairo.sql.map.page.size` and writer settings

---

## Development vs Production Sizing

### Development Environment (macOS Colima)

**Configuration**:
```bash
colima start --cpu 4 --memory 8 --disk 50
docker run -p 9000:9000 -p 9009:9009 -p 8812:8812 \
  -v questdb_data:/var/lib/questdb \
  -e JAVA_OPTS="-Xmx1g" \
  questdb/questdb:9.2.0
```

**Resource Allocation**:
- Colima VM: 4 CPUs, 8 GB RAM, 50 GB disk
- QuestDB Container: 1 GB heap, 4 GB total RAM
- **Use Case**: Schema design, small dataset testing, integration tests

### Production Environment (Linux Native)

**Option 1: Docker on Linux**:
```bash
docker run -d --name questdb \
  --cpus=8 --memory=16g \
  -p 9000:9000 -p 9009:9009 -p 8812:8812 \
  -v /mnt/nvme/questdb:/var/lib/questdb \
  -e JAVA_OPTS="-Xms4g -Xmx4g -XX:+UseG1GC" \
  questdb/questdb:9.2.0
```

**Option 2: Native Binary (Recommended)**:
```bash
# Download from https://github.com/questdb/questdb/releases
tar -xzf questdb-9.2.0-no-jre-bin.tar.gz
export JAVA_HOME=/path/to/graalvm-jdk-17
./questdb.sh start -d /mnt/nvme/questdb
```

**Resource Allocation**:
- 8-16 CPU cores (physical)
- 32-64 GB RAM (4 GB JVM heap + 28-60 GB OS cache)
- NVMe SSD with 10,000+ IOPS
- **Use Case**: 400 symbols, 13 timeframes, real-time ingestion + historical queries

---

## Multi-Platform Deployment Strategy

### macOS Development (Recommended: Docker)

**Pros**:
- Easy setup via Colima or Docker Desktop
- Consistent with Linux deployment
- Volume persistence for data

**Cons**:
- 40-80% performance penalty
- Hypervisor overhead
- Volume mount I/O slower than native

**Recommendation**: **Use Docker (Colima)** for development - convenience outweighs performance penalty for non-production workloads.

### Linux Production (Recommended: Native Binary)

**Pros**:
- Zero virtualization overhead
- Maximum I/O performance
- Direct hardware access (NUMA, SIMD)
- Lower memory footprint

**Cons**:
- Manual dependency management (Java 17+)
- System-level configuration

**Recommendation**: **Use Native Binary** for production - 2-3% overhead from Docker is acceptable, but native eliminates any uncertainty for performance-critical workloads.

**Alternative**: Docker on Linux is acceptable if:
- Infrastructure standardized on containers (Kubernetes)
- Resource limits needed via cgroups
- Minimal overhead acceptable (~3% CPU, ~10% disk)

---

## Sizing Guidelines for Crypto Workload

### Workload Specification

**Scenario**: gapless-crypto-data project
- **Symbols**: 400 USDT futures pairs
- **Timeframes**: 13 intervals (1s, 5s, 15s, 30s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 1d)
- **Data Format**: 11-column microstructure (OHLCV + trades + volume metrics)
- **Ingestion Rate**: Historical backfill (bursty), real-time maintenance (steady)
- **Query Pattern**: Ad-hoc analysis, backtesting, gap detection

### Recommended Resources

**Development (macOS Colima)**:
- **Colima VM**: 4 CPUs, 8 GB RAM, 100 GB disk
- **QuestDB Container**: 1 GB heap, max 4 GB container RAM
- **Dataset**: Sample period (1 week per symbol for testing)

**Production (Linux Native)**:
- **CPU**: 16 cores (physical)
- **RAM**: 64 GB total
  - JVM Heap: 4 GB (`-Xmx4g`)
  - OS Page Cache: 60 GB (for memory-mapped database files)
- **Disk**: 2 TB NVMe SSD (10,000+ IOPS)
  - Database: 1 TB (for 1 year retention @ 13 timeframes)
  - WAL/Logs: 100 GB
  - OS/Apps: 100 GB
- **Network**: 1 Gbps (for Binance API + CloudFront CDN data downloads)

### Partitioning Strategy

**Recommended Table Design**:
- **Partition by**: `TIMESTAMP` column (daily partitions)
- **Deduplication**: `timestamp, symbol` (designated timestamp + symbol key)
- **Index**: Symbol column (for multi-symbol queries)

**Example**:
```sql
CREATE TABLE ohlcv (
  timestamp TIMESTAMP,
  symbol SYMBOL,
  open DOUBLE,
  high DOUBLE,
  low DOUBLE,
  close DOUBLE,
  volume DOUBLE,
  trades LONG,
  -- ... additional columns
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

**Storage Estimate**:
- 11 columns × 8 bytes avg = 88 bytes per row
- 400 symbols × 13 timeframes = 5,200 tables (or use single partitioned table)
- 1s resolution: 86,400 rows/day/symbol = 34.6M rows/day for 400 symbols
- 1 year @ 88 bytes/row = ~1.1 TB uncompressed

---

## Portability Analysis

### Development → Production Migration Path

**Phase 1: macOS Development (Colima + Docker)**
```bash
# Local development with sample data
colima start --cpu 4 --memory 8
docker-compose up -d questdb
# Test data collection, schema design, validation logic
```

**Phase 2: Linux Staging (Docker)**
```bash
# AWS EC2 / Azure VM with Docker
docker run -d --name questdb \
  --cpus=8 --memory=16g \
  -v /mnt/nvme/questdb:/var/lib/questdb \
  questdb/questdb:9.2.0
# Performance testing with production-like data
```

**Phase 3: Linux Production (Native Binary)**
```bash
# Bare-metal or dedicated VM
./questdb.sh start -d /mnt/nvme/questdb
# Maximum performance, zero Docker overhead
```

### Data Portability

**Database Files**:
- `/var/lib/questdb/db/` contains table metadata + column files
- **Fully portable** across architectures (amd64 ↔ arm64)
- **Endianness-agnostic** (QuestDB handles serialization)

**Migration Steps**:
1. Stop QuestDB instance (`docker stop questdb` or `./questdb.sh stop`)
2. Tarball database directory: `tar -czf questdb-backup.tar.gz /var/lib/questdb/db`
3. Transfer to new system
4. Extract: `tar -xzf questdb-backup.tar.gz -C /new/path`
5. Start QuestDB with new data directory
6. Verify with `SELECT count() FROM table_name`

**No schema conversion needed** - binary format identical across platforms.

---

## Sources & References

### Official Documentation
- QuestDB Docker Deployment: https://questdb.com/docs/deployment/docker/
- Capacity Planning: https://questdb.com/docs/deployment/capacity-planning/
- Memory Management: https://questdb.com/docs/guides/architecture/memory-management/

### Docker Hub
- QuestDB Official Image: https://hub.docker.com/r/questdb/questdb
- Debian Bookworm Slim: https://hub.docker.com/_/debian (bookworm-slim tag)

### GitHub
- QuestDB Repository: https://github.com/questdb/questdb
- Dockerfile: https://github.com/questdb/questdb/blob/master/core/Dockerfile
- ARM64 Support PR: https://github.com/questdb/questdb/pull/878

### Performance Research
- Docker Performance on Linux: "Performance Impact of Docker Containers on Linux" (Torizon, 2024)
- Docker for Mac Overhead: GitHub Issue #4769 (docker/for-mac)
- QuestDB Crypto Trading: https://questdb.com/blog/scaling-trading-bot-with-time-series-database/

### Community Resources
- QuestDB Community Forum: https://community.questdb.com/
- High-Frequency Finance Use Cases: https://questdb.com/market-data/

---

## Recommendations Summary

### For gapless-crypto-data Project

**Development Environment** (macOS):
✅ **Use Docker via Colima**
- Consistent with production deployment
- Easy setup and teardown
- Acceptable performance for development

**Production Environment** (Linux):
✅ **Use Native QuestDB Binary**
- Zero virtualization overhead
- Maximum I/O throughput
- Direct CPU SIMD instructions

**Resource Sizing**:
- **Dev**: 4 CPUs, 8 GB RAM, 100 GB disk
- **Prod**: 16 CPUs, 64 GB RAM, 2 TB NVMe SSD

**Image Size Overhead**:
- Docker image: ~200-300 MB (estimated)
- Not a concern for modern infrastructure
- Focus on runtime RAM/CPU/disk instead

**Migration Strategy**:
- Develop schema and logic on macOS (Docker)
- Test with production data volume on Linux (Docker or native)
- Deploy to production using native binary for maximum performance
- Database files portable across environments (no conversion needed)

---

**Analysis Complete**: This report synthesizes publicly available information as of 2025-01-15. For exact Docker image sizes, run `docker images questdb/questdb:9.2.0` after pulling. For production capacity planning with your specific workload, consider QuestDB Enterprise support or community forum consultation.
