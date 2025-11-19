# Linux Docker Deployment (Production Alternative)

Docker-based QuestDB deployment for Linux production. Alternative to native deployment.

## Architecture

**Hybrid approach**:
- QuestDB: Docker container (easier deployment and updates)
- Python: Native uv-managed (systemd service, no container overhead)
- Performance: ~10% disk I/O overhead vs native (acceptable trade-off)
- Management: Docker + systemd

## When to Use Docker

**Advantages**:
- Easier deployment (no manual binary installation)
- Consistent environment across systems
- Simpler updates (pull new image)
- Better isolation

**Disadvantages**:
- ~2.67% CPU overhead
- ~10% disk I/O overhead
- Additional layer complexity

**Recommendation**: Use Docker if:
- Containerized infrastructure is standard
- Ease of deployment > maximum performance
- Running multiple services in containers

Otherwise, use native deployment (see `linux-native-setup.md`).

## Prerequisites

**System Requirements**:
- Linux kernel 5.10+ (Ubuntu 22.04 LTS, Debian 12, or equivalent)
- 16GB+ RAM (64GB+ recommended for production)
- 500GB+ SSD/NVMe storage
- Docker Engine 24.0+
- Docker Compose v2.20+

**Network Requirements**:
- Outbound HTTPS (443) for Docker Hub, Binance API, CloudFront
- Inbound ports (if remote access needed):
  - 9000: QuestDB Web Console
  - 8812: PostgreSQL wire protocol
  - 9009: InfluxDB Line Protocol (ILP)

## Installation

### Install Docker Engine

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Update package index
sudo apt update

# Install dependencies
sudo apt install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release

# Add Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### Configure Docker

```bash
# Add current user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Log out and back in for group membership to take effect
# Or run: newgrp docker

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Verify Docker is running
docker ps
```

### Install Python and uv

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify
uv --version
```

## Deployment

### Deploy gapless-crypto-data

```bash
# Create deployment user
sudo useradd -r -s /bin/bash -d /opt/gapless-crypto-data gapless
sudo mkdir -p /opt/gapless-crypto-data
sudo chown gapless:gapless /opt/gapless-crypto-data

# Clone repository
sudo -u gapless git clone https://github.com/terrylica/gapless-crypto-data.git \
  /opt/gapless-crypto-data

# Install dependencies
cd /opt/gapless-crypto-data
sudo -u gapless uv sync --frozen --no-dev
```

### Create Docker Compose Configuration

```bash
# Copy macOS config as template (modify for Linux)
sudo -u gapless cp deployment/docker-compose.macos.yml \
  deployment/docker-compose.linux.yml

# Edit for Linux optimizations
sudo -u gapless nano deployment/docker-compose.linux.yml
```

**Optimized `docker-compose.linux.yml`**:
```yaml
version: '3.8'

services:
  questdb:
    image: questdb/questdb:9.2.0
    container_name: gapless-questdb

    ports:
      - "9000:9000"   # HTTP REST API & Web Console
      - "8812:8812"   # PostgreSQL wire protocol
      - "9009:9009"   # InfluxDB Line Protocol
      - "9003:9003"   # Prometheus metrics

    # Named volume (optimal for Linux)
    volumes:
      - questdb_data:/var/lib/questdb

    environment:
      # Production memory settings (adjust based on available RAM)
      - JAVA_OPTS=-Xms24g -Xmx48g -XX:+UseG1GC -XX:MaxGCPauseMillis=200

      # WAL mode for concurrent writes
      - QDB_CAIRO_WAL_ENABLED_DEFAULT=true

      # Metrics
      - QDB_METRICS_ENABLED=true

      # Timezone
      - TZ=UTC

    # Health check
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # Restart policy
    restart: unless-stopped

    # Resource limits (adjust based on hardware)
    deploy:
      resources:
        limits:
          cpus: '8.0'
          memory: 64G
        reservations:
          cpus: '4.0'
          memory: 32G

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

volumes:
  questdb_data:
    driver: local

networks:
  default:
    name: gapless-network
    driver: bridge
```

### Start QuestDB Container

```bash
cd /opt/gapless-crypto-data

# Start QuestDB
docker compose -f deployment/docker-compose.linux.yml up -d

# Verify container is running
docker ps

# Check logs
docker compose -f deployment/docker-compose.linux.yml logs -f questdb
```

Wait for: `Server is ready to accept connections`

## Database Initialization

### Apply Schema

```bash
# Apply schema using psql
psql -h localhost -p 8812 -U admin -d qdb \
  -f /opt/gapless-crypto-data/src/gapless_crypto_data/questdb/schema.sql

# Verify table creation
psql -h localhost -p 8812 -U admin -d qdb \
  -c "\d ohlcv"
```

### Test QuestDB

```bash
# HTTP endpoint
curl http://localhost:9000/

# PostgreSQL connection
psql -h localhost -p 8812 -U admin -d qdb -c "SELECT 1;"

# Web Console
# Open browser to http://localhost:9000
```

## Configure Python Collector

### Create systemd Service

```bash
# Copy service file
sudo cp /opt/gapless-crypto-data/deployment/systemd/gapless-crypto-collector.service \
  /etc/systemd/system/gapless-crypto-collector.service

# Note: QuestDB is in Docker, not systemd
# Edit service to remove Requires=questdb.service dependency
sudo nano /etc/systemd/system/gapless-crypto-collector.service
```

**Modified service** (remove `Requires=questdb.service`):
```ini
[Unit]
Description=Gapless Crypto Data Collector
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
# ... rest of configuration unchanged
```

### Configure Environment

```bash
# Create .env file
sudo -u gapless cp /opt/gapless-crypto-data/.env.example \
  /opt/gapless-crypto-data/.env

# Edit configuration
sudo -u gapless nano /opt/gapless-crypto-data/.env
```

**Environment configuration**:
```bash
# QuestDB connection (Docker container)
QUESTDB_HOST=localhost
QUESTDB_ILP_PORT=9009
QUESTDB_PG_PORT=8812
QUESTDB_PG_USER=admin
QUESTDB_PG_PASSWORD=quest
QUESTDB_PG_DATABASE=qdb

# Data collection
BINANCE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT
BINANCE_TIMEFRAMES=1m,5m,15m,1h,4h,1d
COLLECTION_MODE=hybrid
CLOUDFRONT_ENABLED=true
GAP_FILL_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Start Collector

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable collector
sudo systemctl enable gapless-crypto-collector

# Start collector
sudo systemctl start gapless-crypto-collector

# Check status
sudo systemctl status gapless-crypto-collector

# View logs
sudo journalctl -u gapless-crypto-collector -f
```

## Monitoring

### Container Status

```bash
# QuestDB container status
docker ps | grep questdb

# Container stats
docker stats gapless-questdb

# Container logs
docker logs -f gapless-questdb
```

### Service Status

```bash
# Collector status
sudo systemctl status gapless-crypto-collector

# Collector logs
sudo journalctl -u gapless-crypto-collector -f
```

### Data Verification

```bash
# Row count
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT COUNT(*) FROM ohlcv;"

# Latest data
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT * FROM ohlcv ORDER BY timestamp DESC LIMIT 10;"

# Data sources
psql -h localhost -p 8812 -U admin -d qdb \
  -c "SELECT data_source, COUNT(*) FROM ohlcv GROUP BY data_source;"
```

### Prometheus Metrics

```bash
# Fetch QuestDB metrics
curl http://localhost:9003/metrics

# Key metrics:
# - questdb_memory_heap_used_bytes
# - questdb_disk_size_bytes
# - questdb_writer_rows_total
```

## Maintenance

### Update QuestDB

```bash
# Pull new image
docker pull questdb/questdb:latest

# Stop and remove old container
docker compose -f deployment/docker-compose.linux.yml down

# Update image tag in docker-compose.linux.yml
nano deployment/docker-compose.linux.yml
# Change: image: questdb/questdb:9.2.0
# To: image: questdb/questdb:latest

# Start new container
docker compose -f deployment/docker-compose.linux.yml up -d
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
# Create backup directory
sudo mkdir -p /backup

# Export data volume
docker run --rm \
  -v gapless-crypto-data_questdb_data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/questdb-$(date +%Y%m%d).tar.gz -C /data .

# Verify backup
ls -lh /backup/
```

### Restore QuestDB Data

```bash
# Stop QuestDB container
docker compose -f deployment/docker-compose.linux.yml down

# Remove old volume
docker volume rm gapless-crypto-data_questdb_data

# Create new volume
docker volume create gapless-crypto-data_questdb_data

# Restore data
docker run --rm \
  -v gapless-crypto-data_questdb_data:/data \
  -v /backup:/backup \
  alpine tar xzf /backup/questdb-20250115.tar.gz -C /data

# Start QuestDB
docker compose -f deployment/docker-compose.linux.yml up -d
```

## Troubleshooting

### Container Fails to Start

**Check logs**:
```bash
docker logs gapless-questdb
```

**Common issues**:
- Port already in use: `sudo lsof -i :9000`
- Insufficient memory: Reduce Xmx in docker-compose.linux.yml
- Volume permission errors: Check volume ownership

### Collector Cannot Connect to QuestDB

**Diagnosis**:
```bash
# Check if QuestDB is reachable
telnet localhost 9009

# Check Docker network
docker network inspect gapless-network
```

**Solution**:
- Ensure QuestDB container is running: `docker ps`
- Verify ports are exposed: `docker port gapless-questdb`
- Check firewall rules: `sudo ufw status`

### Slow Performance

**Diagnosis**:
```bash
# Check Docker stats
docker stats gapless-questdb

# Check disk I/O
iostat -x 1

# Check volume driver
docker volume inspect gapless-crypto-data_questdb_data
```

**Solutions**:
- Use overlay2 storage driver (default)
- Mount volume on fast SSD/NVMe
- Consider native deployment for maximum performance

## Performance Comparison

| Metric | Docker (Linux) | Native (Linux) | Difference |
|--------|---------------|----------------|------------|
| CPU overhead | 2.67% | 0% | +2.67% |
| Disk I/O | 90% | 100% | -10% |
| Ingestion rate | 90-180K rows/sec | 100-200K rows/sec | -10% |
| Query latency | <1.1s | <1s | +10% |

**Verdict**: Docker overhead is acceptable for most workloads. Use native if maximum performance is critical.

## Security

### Container Security

```bash
# Run as non-root user (add to docker-compose.linux.yml)
user: "1000:1000"

# Read-only root filesystem
read_only: true
tmpfs:
  - /tmp

# Drop capabilities
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

### Firewall

```bash
# Install ufw
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow QuestDB (from specific subnet)
sudo ufw allow from 192.168.1.0/24 to any port 9000
sudo ufw allow from 192.168.1.0/24 to any port 8812

# Enable firewall
sudo ufw enable
```

## Auto-Start on Boot

```bash
# QuestDB container (Docker Compose)
# Add to docker-compose.linux.yml:
# restart: unless-stopped

# Collector (systemd)
sudo systemctl enable gapless-crypto-collector

# Verify
sudo systemctl is-enabled gapless-crypto-collector
# Expected: enabled
```

## Resource Requirements

**Production workload (400 symbols × 13 timeframes × 1 year)**:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 8 cores | 16+ cores   |
| RAM      | 32GB    | 64GB+       |
| Storage  | 500GB   | 1TB SSD     |

## Next Steps

1. **Configure monitoring**: Prometheus + Grafana for metrics visualization
2. **Set up alerts**: Container failures, disk space, ingestion errors
3. **Plan backups**: Automated daily backups to S3/GCS
4. **Load testing**: Validate performance under production load
5. **Consider native**: If performance is critical, migrate to native deployment
