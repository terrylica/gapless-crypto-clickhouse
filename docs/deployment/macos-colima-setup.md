# macOS Development Setup with Colima

Colima-optimized QuestDB deployment for macOS development environment.

## Prerequisites

**Required**:
- macOS 13+ (Ventura or later, for VirtioFS support)
- Homebrew package manager
- 8GB+ available RAM
- 20GB+ available disk space

**Not Required**:
- Docker Desktop (explicitly NOT used)

## Installation

### Install Colima and Docker CLI

```bash
# Install Colima VM runtime
brew install colima

# Install Docker CLI (without Docker Desktop)
brew install docker

# Install Docker Compose
brew install docker-compose
```

### Start Colima with VirtioFS

VirtioFS provides 2-3x faster I/O than gRPC-FUSE (default).

```bash
# Start Colima with optimized settings
colima start \
  --mount-type virtiofs \
  --cpu 4 \
  --memory 8 \
  --disk 50

# Verify Colima is running
colima status
```

**Expected output**:
```
INFO colima is running using QEMU
arch: aarch64
runtime: docker
mountType: virtiofs
socket: unix:///Users/username/.colima/default/docker.sock
```

### Verify Docker CLI

```bash
# Test Docker CLI connectivity
docker ps

# Expected: Empty list (no containers running yet)
```

## Deploy QuestDB

### Start QuestDB Container

```bash
# Navigate to project root
cd /path/to/gapless-crypto-data

# Start QuestDB using docker-compose
docker-compose -f deployment/docker-compose.macos.yml up -d

# Verify container is running
docker ps
```

**Expected output**:
```
CONTAINER ID   IMAGE                    STATUS         PORTS
abc123...      questdb/questdb:9.2.0    Up 10 seconds  0.0.0.0:9000->9000/tcp, ...
```

### Verify QuestDB Health

```bash
# Check container logs
docker-compose -f deployment/docker-compose.macos.yml logs questdb

# Wait for this message:
# "Server is ready to accept connections"

# Test HTTP endpoint
curl http://localhost:9000/

# Test PostgreSQL endpoint
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1;"
```

### Access Web Console

Open browser to http://localhost:9000

**Test query**:
```sql
SELECT * FROM ohlcv LIMIT 10;
```

## Initialize Database Schema

```bash
# Apply schema using psql
psql -h localhost -p 8812 -U admin -d qdb \
  -f src/gapless_crypto_data/questdb/schema.sql

# Verify table creation
psql -h localhost -p 8812 -U admin -d qdb \
  -c "\d ohlcv"
```

**Expected output**:
```
                   Table "ohlcv"
        Column              |  Type     | Nullable
----------------------------+-----------+----------
 timestamp                  | timestamp |
 symbol                     | symbol    |
 timeframe                  | symbol    |
 open                       | double    |
 ...
Designated timestamp: timestamp
```

## Python Development Setup

### Install uv

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Install Project Dependencies

```bash
# From project root
cd /path/to/gapless-crypto-data

# Install dependencies (creates virtual environment automatically)
uv sync

# Verify installation
uv run python -c "import gapless_crypto_data; print('OK')"
```

### Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings** (`.env`):
```bash
# QuestDB connection
QUESTDB_HOST=localhost
QUESTDB_ILP_PORT=9009
QUESTDB_PG_PORT=8812
QUESTDB_PG_USER=admin
QUESTDB_PG_PASSWORD=quest
QUESTDB_PG_DATABASE=qdb

# Data collection
BINANCE_SYMBOLS=BTCUSDT,ETHUSDT
BINANCE_TIMEFRAMES=1m,5m,1h
COLLECTION_MODE=bulk
CLOUDFRONT_ENABLED=true
```

## Test Data Collection

```bash
# Run bulk data collection (test mode)
uv run python -m gapless_crypto_data.collectors.binance_public_data_collector \
  --symbol BTCUSDT \
  --timeframe 1m \
  --start-date 2025-01-01 \
  --end-date 2025-01-02

# Verify data ingestion
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT COUNT(*) FROM ohlcv WHERE symbol = 'BTCUSDT' AND timeframe = '1m';"
```

## Performance Verification

### Measure I/O Performance

```bash
# Run I/O benchmark inside container
docker exec gapless-questdb fio \
  --name=randwrite \
  --ioengine=libaio \
  --iodepth=16 \
  --rw=randwrite \
  --bs=4k \
  --direct=1 \
  --size=1G \
  --numjobs=1 \
  --runtime=60 \
  --group_reporting \
  --filename=/var/lib/questdb/testfile

# Expected IOPS: ~2,786 (VirtioFS)
```

### Monitor Resource Usage

```bash
# Container stats
docker stats gapless-questdb

# Expected:
# CPU: 10-30%
# MEM: 2-4GB
# NET I/O: varies by workload
```

## Management

### Start/Stop QuestDB

```bash
# Stop QuestDB
docker-compose -f deployment/docker-compose.macos.yml stop

# Start QuestDB
docker-compose -f deployment/docker-compose.macos.yml start

# Restart QuestDB
docker-compose -f deployment/docker-compose.macos.yml restart
```

### View Logs

```bash
# Follow logs in real-time
docker-compose -f deployment/docker-compose.macos.yml logs -f questdb

# View last 100 lines
docker-compose -f deployment/docker-compose.macos.yml logs --tail 100 questdb
```

### Backup Data

```bash
# Export data volume
docker run --rm \
  -v gapless-questdb_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/questdb-backup-$(date +%Y%m%d).tar.gz -C /data .

# Verify backup
ls -lh backups/
```

### Clean Up

```bash
# Stop and remove containers (preserves data)
docker-compose -f deployment/docker-compose.macos.yml down

# Stop and remove containers + data (DESTRUCTIVE)
docker-compose -f deployment/docker-compose.macos.yml down -v

# Stop Colima
colima stop
```

## Troubleshooting

### Colima Not Starting

**Symptom**: `colima start` fails with QEMU errors

**Solution**:
```bash
# Delete existing VM
colima delete

# Restart with explicit architecture
colima start --arch aarch64 --vm-type=qemu --mount-type virtiofs
```

### Slow I/O Performance

**Symptom**: Ingestion rate <10K rows/sec

**Diagnosis**:
```bash
# Check mount type
colima status | grep mountType

# Should show: mountType: virtiofs
# If shows: mountType: sshfs or gRPC-FUSE, recreate VM
```

**Solution**:
```bash
colima delete
colima start --mount-type virtiofs
```

### Docker CLI Cannot Connect

**Symptom**: `docker ps` fails with "Cannot connect to Docker daemon"

**Solution**:
```bash
# Check DOCKER_HOST environment variable
echo $DOCKER_HOST

# Should show: unix:///Users/username/.colima/default/docker.sock

# If not set, add to ~/.zshrc or ~/.bashrc:
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock

# Reload shell
source ~/.zshrc
```

### QuestDB Container Fails Health Check

**Symptom**: Container status shows "unhealthy"

**Diagnosis**:
```bash
# Check container logs
docker logs gapless-questdb

# Look for:
# - Port binding errors
# - Java OutOfMemoryError
# - Disk space issues
```

**Solution**:
```bash
# Increase memory in docker-compose.macos.yml
# Change: JAVA_OPTS=-Xms1g -Xmx2g
# To: JAVA_OPTS=-Xms2g -Xmx4g

# Recreate container
docker-compose -f deployment/docker-compose.macos.yml up -d --force-recreate
```

### Port Already in Use

**Symptom**: `Bind for 0.0.0.0:9000 failed: port is already allocated`

**Solution**:
```bash
# Find process using port 9000
lsof -i :9000

# Kill process or change port in docker-compose.macos.yml
```

## Resource Requirements

### Minimum

- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB

### Recommended

- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB SSD

### Development Workload

- 100 symbols × 3 timeframes
- 1 year historical data
- Expected storage: ~5-10GB

## Performance Expectations

### I/O Benchmarks

| Configuration | IOPS | Latency |
|--------------|------|---------|
| VirtioFS (recommended) | 2,786 | 3.5ms |
| gRPC-FUSE (legacy) | 1,545 | 6.2ms |
| Docker Desktop | 1,000 | 9.5ms |

### Ingestion Performance

- CloudFront bulk: 50-100K rows/sec
- ILP ingestion: 100-200K rows/sec
- Query latency: <1s for 1M rows

## Next Steps

1. **Test Collection**: Run bulk historical data collection
2. **Verify Data**: Query QuestDB to confirm data integrity
3. **Configure Monitoring**: Set up Prometheus metrics scraping (optional)
4. **Production Readiness**: See `linux-native-setup.md` for production deployment
