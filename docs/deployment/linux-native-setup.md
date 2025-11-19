# Linux Native Deployment (Production)

Native QuestDB and Python deployment for maximum performance. Recommended for production environments.

## Architecture

**Zero container overhead**:
- QuestDB: Native binary (systemd service)
- Python: uv-managed (systemd service)
- Performance: 2-5% faster than Docker
- Management: systemd (standard Linux service management)

## Prerequisites

**System Requirements**:
- Linux kernel 5.10+ (Ubuntu 22.04 LTS, Debian 12, or equivalent)
- 16GB+ RAM (64GB+ recommended for production)
- 500GB+ SSD/NVMe storage (XFS or ext4 filesystem)
- Java 17+ (OpenJDK or equivalent)

**Network Requirements**:
- Outbound HTTPS (443) for Binance API and CloudFront
- Inbound ports (if remote access needed):
  - 9000: QuestDB Web Console
  - 8812: PostgreSQL wire protocol
  - 9009: InfluxDB Line Protocol (ILP)

## Installation

### System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
  openjdk-17-jdk \
  postgresql-client \
  curl \
  wget \
  git \
  htop \
  iotop

# Verify Java installation
java -version
# Expected: openjdk version "17.0.x"
```

### Install QuestDB

```bash
# Download QuestDB binary (check https://questdb.io/download/ for latest version)
cd /opt
sudo wget https://github.com/questdb/questdb/releases/download/9.2.0/questdb-9.2.0-rt-linux-amd64.tar.gz

# Extract
sudo tar -xzf questdb-9.2.0-rt-linux-amd64.tar.gz
sudo mv questdb-9.2.0-rt-linux-amd64 questdb

# Create QuestDB user
sudo useradd -r -s /bin/false -d /var/lib/questdb questdb

# Create directories
sudo mkdir -p /var/lib/questdb/db
sudo mkdir -p /var/log/questdb

# Set ownership
sudo chown -R questdb:questdb /opt/questdb
sudo chown -R questdb:questdb /var/lib/questdb
sudo chown -R questdb:questdb /var/log/questdb

# Verify installation
/opt/questdb/bin/java -jar /opt/questdb/questdb.jar --version
```

### Install Python and uv

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
uv --version
```

### Deploy gapless-crypto-data

```bash
# Create deployment user
sudo useradd -r -s /bin/bash -d /opt/gapless-crypto-data gapless
sudo mkdir -p /opt/gapless-crypto-data
sudo chown gapless:gapless /opt/gapless-crypto-data

# Clone repository (as gapless user)
sudo -u gapless git clone https://github.com/terrylica/gapless-crypto-data.git /opt/gapless-crypto-data

# Install dependencies
cd /opt/gapless-crypto-data
sudo -u gapless uv sync --frozen --no-dev

# Verify installation
sudo -u gapless uv run python -c "import gapless_crypto_data; print('OK')"
```

## Configuration

### QuestDB systemd Service

```bash
# Copy systemd service file
sudo cp /opt/gapless-crypto-data/deployment/systemd/questdb.service \
  /etc/systemd/system/questdb.service

# Edit service file (adjust memory settings)
sudo nano /etc/systemd/system/questdb.service

# Reload systemd
sudo systemctl daemon-reload

# Enable QuestDB service
sudo systemctl enable questdb
```

**Memory configuration** (edit in `questdb.service`):

| System RAM | Xms (min heap) | Xmx (max heap) |
|-----------|----------------|----------------|
| 16GB      | 8g             | 12g            |
| 32GB      | 16g            | 24g            |
| 64GB      | 24g            | 48g            |
| 128GB     | 48g            | 96g            |

### gapless-crypto-data systemd Service

```bash
# Copy systemd service file
sudo cp /opt/gapless-crypto-data/deployment/systemd/gapless-crypto-collector.service \
  /etc/systemd/system/gapless-crypto-collector.service

# Create environment file
sudo -u gapless cp /opt/gapless-crypto-data/.env.example \
  /opt/gapless-crypto-data/.env

# Edit configuration
sudo -u gapless nano /opt/gapless-crypto-data/.env
```

**Environment configuration** (`.env`):
```bash
# QuestDB connection
QUESTDB_HOST=localhost
QUESTDB_ILP_PORT=9009
QUESTDB_PG_PORT=8812
QUESTDB_PG_USER=admin
QUESTDB_PG_PASSWORD=quest
QUESTDB_PG_DATABASE=qdb

# Data collection
BINANCE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT
BINANCE_TIMEFRAMES=1m,5m,15m,1h,4h,1d
COLLECTION_MODE=hybrid  # bulk + websocket
CLOUDFRONT_ENABLED=true
GAP_FILL_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable collector service
sudo systemctl enable gapless-crypto-collector
```

## Database Initialization

### Start QuestDB

```bash
# Start QuestDB service
sudo systemctl start questdb

# Check status
sudo systemctl status questdb

# View logs
sudo journalctl -u questdb -f
```

Wait for log message: `Server is ready to accept connections`

### Apply Schema

```bash
# Apply database schema
psql -h localhost -p 8812 -U admin -d qdb \
  -f /opt/gapless-crypto-data/src/gapless_crypto_data/questdb/schema.sql

# Verify table creation
psql -h localhost -p 8812 -U admin -d qdb \
  -c "\d ohlcv"
```

### Test QuestDB

```bash
# Test HTTP endpoint
curl http://localhost:9000/

# Test PostgreSQL connection
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1;"

# Test ILP endpoint (using telnet)
telnet localhost 9009
# Type: test,symbol=BTCUSDT value=1.0
# Ctrl+] then type 'quit'
```

## Start Data Collection

```bash
# Start collector service
sudo systemctl start gapless-crypto-collector

# Check status
sudo systemctl status gapless-crypto-collector

# View logs
sudo journalctl -u gapless-crypto-collector -f
```

### Verify Data Ingestion

```bash
# Check row count
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT COUNT(*) FROM ohlcv;"

# Check latest data
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT * FROM ohlcv ORDER BY timestamp DESC LIMIT 10;"

# Check data sources
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT data_source, COUNT(*) FROM ohlcv GROUP BY data_source;"
```

## Monitoring

### systemd Service Status

```bash
# QuestDB status
sudo systemctl status questdb

# Collector status
sudo systemctl status gapless-crypto-collector

# Check if services are running
systemctl is-active questdb
systemctl is-active gapless-crypto-collector
```

### View Logs

```bash
# QuestDB logs (live)
sudo journalctl -u questdb -f

# Collector logs (live)
sudo journalctl -u gapless-crypto-collector -f

# Recent errors
sudo journalctl -u questdb -p err --since today
sudo journalctl -u gapless-crypto-collector -p err --since today

# Logs from last hour
sudo journalctl -u questdb --since "1 hour ago"
```

### Resource Monitoring

```bash
# CPU and memory usage
htop

# Disk I/O
sudo iotop

# Disk space
df -h /var/lib/questdb

# QuestDB process details
ps aux | grep questdb
```

### Prometheus Metrics

QuestDB exposes metrics on port 9003:

```bash
# Fetch metrics
curl http://localhost:9003/metrics

# Key metrics:
# - questdb_memory_heap_used_bytes
# - questdb_disk_size_bytes
# - questdb_writer_rows_total
# - questdb_query_duration_seconds
```

**Prometheus scrape configuration** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'questdb'
    static_configs:
      - targets: ['localhost:9003']
```

## Maintenance

### Restart Services

```bash
# Restart QuestDB
sudo systemctl restart questdb

# Restart collector
sudo systemctl restart gapless-crypto-collector

# Restart both
sudo systemctl restart questdb gapless-crypto-collector
```

### Update gapless-crypto-data

```bash
# Stop collector
sudo systemctl stop gapless-crypto-collector

# Pull latest code
cd /opt/gapless-crypto-data
sudo -u gapless git pull origin main

# Update dependencies
sudo -u gapless uv sync --frozen --no-dev

# Restart collector
sudo systemctl start gapless-crypto-collector
```

### Backup QuestDB Data

```bash
# Stop QuestDB
sudo systemctl stop questdb

# Backup data directory
sudo tar -czf /backup/questdb-$(date +%Y%m%d).tar.gz \
  -C /var/lib/questdb db

# Restart QuestDB
sudo systemctl start questdb

# Verify backup
ls -lh /backup/
```

### Restore QuestDB Data

```bash
# Stop QuestDB
sudo systemctl stop questdb

# Restore data
sudo rm -rf /var/lib/questdb/db
sudo tar -xzf /backup/questdb-20250115.tar.gz \
  -C /var/lib/questdb

# Set ownership
sudo chown -R questdb:questdb /var/lib/questdb

# Restart QuestDB
sudo systemctl start questdb
```

## Performance Tuning

### Filesystem Optimization

```bash
# Use XFS for better write performance
sudo mkfs.xfs /dev/sdb1

# Mount with optimal options
sudo mount -o noatime,nodiratime /dev/sdb1 /var/lib/questdb

# Add to /etc/fstab for persistence
echo "/dev/sdb1 /var/lib/questdb xfs noatime,nodiratime 0 2" | \
  sudo tee -a /etc/fstab
```

### Kernel Tuning

Add to `/etc/sysctl.conf`:

```bash
# Increase file descriptor limit
fs.file-max = 2097152

# Network tuning
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.core.netdev_max_backlog = 5000

# Memory tuning
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
```

Apply settings:
```bash
sudo sysctl -p
```

### CPU Affinity (Optional)

Pin QuestDB to specific CPU cores:

```bash
# Edit questdb.service
sudo nano /etc/systemd/system/questdb.service

# Add under [Service]:
# CPUAffinity=0-7

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart questdb
```

## Troubleshooting

### QuestDB Fails to Start

**Check logs**:
```bash
sudo journalctl -u questdb -n 100
```

**Common issues**:
- Insufficient memory: Reduce Xmx in questdb.service
- Port already in use: Check with `sudo lsof -i :9000`
- Permission denied: Verify ownership of /var/lib/questdb

### Collector Fails to Start

**Check logs**:
```bash
sudo journalctl -u gapless-crypto-collector -n 100
```

**Common issues**:
- QuestDB not running: Start questdb service first
- Invalid .env file: Check syntax in /opt/gapless-crypto-data/.env
- Python dependencies: Run `sudo -u gapless uv sync --frozen`

### Slow Ingestion Performance

**Diagnosis**:
```bash
# Check disk I/O wait
iostat -x 1

# Check if WAL is enabled
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SHOW cairo.wal.enabled.default;"
```

**Solutions**:
- Enable WAL mode (see schema.sql)
- Use faster storage (NVMe SSD)
- Increase batch size in collector

### High Memory Usage

**Check memory**:
```bash
# QuestDB heap usage
curl http://localhost:9003/metrics | grep heap

# System memory
free -h
```

**Solutions**:
- Reduce Xmx in questdb.service
- Increase system RAM
- Enable disk-based caching

## Security

### Firewall Configuration

```bash
# Install ufw
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow QuestDB (adjust as needed)
sudo ufw allow from 192.168.1.0/24 to any port 9000
sudo ufw allow from 192.168.1.0/24 to any port 8812

# Enable firewall
sudo ufw enable
```

### Access Control

**QuestDB authentication** (edit `/var/lib/questdb/conf/server.conf`):

```properties
# Enable authentication
http.security.enabled=true
pg.security.enabled=true

# User database
acl.enabled=true
```

**Create users**:
```bash
# Access QuestDB Web Console
# Navigate to Settings > Users
# Add users with appropriate permissions
```

## Resource Requirements

### Production Workload

**400 symbols × 13 timeframes × 1 year**:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 8 cores | 16+ cores   |
| RAM      | 32GB    | 64GB+       |
| Storage  | 500GB   | 1TB SSD     |

### Expected Performance

- Ingestion: 100-200K rows/sec
- Query latency: <1s for 10M rows
- Storage efficiency: ~50% of Parquet

## Next Steps

1. **Set up monitoring**: Configure Prometheus + Grafana
2. **Configure alerts**: systemd failures, disk space, ingestion errors
3. **Plan backups**: Automated daily backups to S3/GCS
4. **Load testing**: Validate performance under production load
