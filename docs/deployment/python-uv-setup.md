# Python Deployment with uv (Non-Containerized)

Non-containerized Python deployment using uv package manager for gapless-crypto-data v4.0.0.

## Advantages Over Docker Python

**Performance**:
- 40% faster CI/CD pipelines vs Docker Python
- No 200-800MB Python base image overhead
- 10x faster dependency resolution vs pip
- Zero container layer overhead

**Simplicity**:
- Single `uv run` command execution
- No Dockerfile maintenance
- No image registry required
- Direct git pull + uv sync deployment

**Cost**:
- Lower storage costs (no images)
- Lower network costs (smaller dependencies)
- Faster deployments (no image pull)

## Prerequisites

**System Requirements**:
- Linux (Ubuntu 22.04 LTS, Debian 12, or equivalent)
- macOS 13+ (Ventura or later)
- Python 3.12+ (installed and available in PATH)

**Not Required**:
- Docker
- Python virtual environment managers (venv, virtualenv, conda)
- pip, setuptools, poetry (uv handles everything)

## Installation

### Install uv

**Linux/macOS (Recommended)**:
```bash
# Install uv using official installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (add to ~/.bashrc or ~/.zshrc for persistence)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
uv --version
```

**Alternative (Homebrew on macOS)**:
```bash
brew install uv
uv --version
```

**Alternative (pip)**:
```bash
# Not recommended, but works
pip install uv
uv --version
```

### Install Python 3.12+

**Linux (Ubuntu/Debian)**:
```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv

# Verify
python3.12 --version
```

**macOS**:
```bash
# Install via Homebrew
brew install python@3.12

# Verify
python3.12 --version
```

## Development Workflow

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/terrylica/gapless-crypto-data.git
cd gapless-crypto-data

# Install dependencies (creates .venv automatically)
uv sync

# Verify installation
uv run python -c "import gapless_crypto_data; print('OK')"
```

### Running Commands

**Execute Python scripts**:
```bash
# Run Python module
uv run python -m gapless_crypto_data.collectors.questdb_bulk_loader

# Run Python script
uv run python scripts/example.py

# Run Python REPL
uv run python
```

**Execute without installation (uvx)**:
```bash
# Run tool without installing
uvx pytest

# Run script with inline dependencies (PEP 723)
uvx --from requests python fetch_data.py
```

### Development Dependencies

```bash
# Install with dev dependencies
uv sync

# Install without dev dependencies (production)
uv sync --no-dev

# Install with frozen lockfile (CI/CD)
uv sync --frozen --no-dev
```

### Update Dependencies

```bash
# Update all dependencies to latest versions
uv sync --upgrade

# Update specific package
uv add questdb@latest

# Update lockfile
uv lock

# Commit updated lockfile
git add uv.lock
git commit -m "chore: update dependencies"
```

## Production Deployment

### Deployment Architecture

**Recommended setup**:
- Python code: Native (uv-managed, no container)
- QuestDB: Native systemd service OR Docker container
- Deployment: git pull + uv sync + systemctl restart

**Not using Docker for Python**:
- Faster deployment (no image build/push/pull)
- Lower resource usage (no container overhead)
- Simpler debugging (direct process access)

### Deployment Steps

**Initial deployment**:
```bash
# 1. Create deployment user
sudo useradd -r -s /bin/bash -d /opt/gapless-crypto-data gapless
sudo mkdir -p /opt/gapless-crypto-data
sudo chown gapless:gapless /opt/gapless-crypto-data

# 2. Clone repository
sudo -u gapless git clone https://github.com/terrylica/gapless-crypto-data.git \
  /opt/gapless-crypto-data

# 3. Install dependencies (production)
cd /opt/gapless-crypto-data
sudo -u gapless uv sync --frozen --no-dev

# 4. Configure environment
sudo -u gapless cp .env.example .env
sudo -u gapless nano .env

# 5. Set up systemd service (see systemd section)
sudo cp deployment/systemd/gapless-crypto-collector.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gapless-crypto-collector
sudo systemctl start gapless-crypto-collector
```

**Zero-downtime updates**:
```bash
# 1. Pull latest code
cd /opt/gapless-crypto-data
sudo -u gapless git pull origin main

# 2. Update dependencies (uses lockfile)
sudo -u gapless uv sync --frozen --no-dev

# 3. Restart service
sudo systemctl restart gapless-crypto-collector

# 4. Verify
sudo systemctl status gapless-crypto-collector
```

### systemd Integration

**Service file**: `deployment/systemd/gapless-crypto-collector.service`

```ini
[Unit]
Description=Gapless Crypto Data Collector
After=network-online.target questdb.service
Wants=network-online.target
Requires=questdb.service

[Service]
Type=simple
User=gapless
Group=gapless

# Working directory
WorkingDirectory=/opt/gapless-crypto-data

# Python execution via uv
ExecStart=/home/gapless/.local/bin/uv run --frozen python -m gapless_crypto_data.collectors.binance_public_data_collector

# Environment configuration
EnvironmentFile=/opt/gapless-crypto-data/.env

# Restart policy
Restart=on-failure
RestartSec=30s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=gapless-crypto-collector

[Install]
WantedBy=multi-user.target
```

**Commands**:
```bash
# Install service
sudo cp deployment/systemd/gapless-crypto-collector.service \
  /etc/systemd/system/
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable gapless-crypto-collector

# Start service
sudo systemctl start gapless-crypto-collector

# Check status
sudo systemctl status gapless-crypto-collector

# View logs
sudo journalctl -u gapless-crypto-collector -f
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Install uv
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      # Install dependencies (faster than pip)
      - name: Install dependencies
        run: uv sync --frozen

      # Run tests
      - name: Run tests
        run: uv run pytest

      # Run linting
      - name: Run linting
        run: uv run ruff check .
```

**Performance comparison** (typical Python project):
- **Docker Python**: 3-5 minutes (image build + dependency install)
- **uv**: 1-2 minutes (dependency install only)
- **Speedup**: 40-60% faster

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Setup**:
```bash
# Install pre-commit
uv add --dev pre-commit

# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## Dependency Management

### uv.lock File

**Purpose**:
- Reproducible builds across environments
- Pins exact versions and hashes
- Committed to git (unlike node_modules/)
- Cross-platform compatible

**Workflow**:
```bash
# Developer updates dependencies
uv add questdb@latest
uv lock  # Updates uv.lock

# CI/CD uses frozen lockfile
uv sync --frozen --no-dev  # No dependency resolution
```

**Benefits**:
- Deterministic builds
- Faster CI/CD (no dependency resolution)
- Audit trail (git blame on uv.lock)

### Adding Dependencies

```bash
# Add production dependency
uv add psycopg[binary]>=3.2.0

# Add dev dependency
uv add --dev pytest>=8.0.0

# Add optional dependency
uv add --optional ml numpy pandas

# Remove dependency
uv remove pandas
```

### Upgrading Dependencies

```bash
# Upgrade all dependencies
uv sync --upgrade

# Upgrade specific package
uv add questdb@latest

# Check outdated packages
uv pip list --outdated
```

## Environment Configuration

### .env File

```bash
# QuestDB connection
QUESTDB_HOST=localhost
QUESTDB_ILP_PORT=9009
QUESTDB_PG_PORT=8812
QUESTDB_PG_USER=admin
QUESTDB_PG_PASSWORD=quest
QUESTDB_PG_DATABASE=qdb

# Data collection
BINANCE_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
BINANCE_TIMEFRAMES=1m,5m,15m,1h,4h,1d
COLLECTION_MODE=hybrid
CLOUDFRONT_ENABLED=true
GAP_FILL_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Security**:
```bash
# Restrict .env permissions
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
```

## Performance Tuning

### Dependency Resolution

**Cache location**:
```bash
# Default cache: ~/.cache/uv/
# Configure:
export UV_CACHE_DIR=/path/to/cache
```

**Parallel downloads**:
```bash
# uv automatically uses parallel downloads (10x faster than pip)
# No configuration needed
```

### Virtual Environment

**Location**:
```bash
# Default: .venv in project root
# Configure:
export UV_VENV=/path/to/venv
```

**Python version**:
```bash
# Use specific Python version
uv venv --python 3.12

# Use system Python
uv venv --python python3.12
```

## Troubleshooting

### uv Command Not Found

**Solution**:
```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify
which uv
```

**Permanent fix**:
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Dependency Resolution Fails

**Diagnosis**:
```bash
# Verbose output
uv sync -v

# Check Python version
python3.12 --version

# Check lockfile
cat uv.lock
```

**Solutions**:
```bash
# Clear cache
rm -rf ~/.cache/uv

# Recreate lockfile
rm uv.lock
uv lock

# Use specific Python version
uv sync --python 3.12
```

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'gapless_crypto_data'`

**Solution**:
```bash
# Install dependencies
uv sync

# Verify installation
uv run python -c "import gapless_crypto_data; print(gapless_crypto_data.__version__)"

# Check virtual environment
uv venv --show
```

### Slow Dependency Install

**Diagnosis**:
```bash
# Check network
curl -I https://pypi.org

# Check cache
ls -lh ~/.cache/uv
```

**Solutions**:
```bash
# Use frozen lockfile (no resolution)
uv sync --frozen

# Increase timeout
UV_HTTP_TIMEOUT=60 uv sync

# Use different index
UV_INDEX_URL=https://pypi.org/simple uv sync
```

## Migration from pip/poetry

### From pip

```bash
# Old workflow (pip)
pip install -r requirements.txt

# New workflow (uv)
uv sync
```

**Benefits**:
- 10-100x faster
- Automatic virtual environment management
- Reproducible builds via lockfile

### From poetry

```bash
# Old workflow (poetry)
poetry install

# New workflow (uv)
uv sync
```

**Migration**:
```bash
# Convert pyproject.toml (manual)
# uv uses PEP 621 format, poetry uses custom format
# Update [tool.poetry] to [project] section
```

## Resource Requirements

### Development

- Disk: 500MB (dependencies + cache)
- RAM: 200MB (uv process)
- CPU: Minimal (dependency resolution is fast)

### Production

- Disk: 300MB (dependencies only, no cache)
- RAM: 100MB (uv overhead)
- CPU: Minimal (no continuous process)

## Next Steps

1. **Set up QuestDB**: See `docs/deployment/linux-native-setup.md` or `macos-colima-setup.md`
2. **Configure environment**: Edit `.env` file with connection details
3. **Test connection**: Run `uv run python -m gapless_crypto_data.query` to verify
4. **Deploy to production**: Follow systemd integration guide above
5. **Monitor**: Use `journalctl -u gapless-crypto-collector -f` for logs
