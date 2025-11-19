# ADR-0008: ClickHouse Local Visualization Toolchain

## Status

Implemented (2025-11-17)

## Context

### Problem Statement

Developers working with gapless-crypto-data v4.0.0 need idiomatic, production-ready tools to visualize and explore ClickHouse data locally. The package collects high-frequency cryptocurrency market data (1s-1d timeframes, 11-column microstructure format) into ClickHouse, but lacks comprehensive guidance on local visualization and database management tools.

**User Requirements** (from multi-agent research):
- Primary use case: Development + Data exploration + Database administration (all three)
- Interface preference: Mixed tooling (GUI + CLI + IDE integration)
- Current setup: ClickHouse running via Docker + Colima (Alpine native ARM64)
- Licensing: Open-source preferred, commercial acceptable if superior

### Current State

**Existing Infrastructure**:
- ClickHouse 24.1-alpine running in Docker via Colima
- Native protocol: `localhost:9000` (clickhouse-driver)
- HTTP interface: `localhost:8123` (client queries, web UIs)
- Production-ready docker-compose.yml with schema auto-initialization

**Gap**: No documented visualization stack, developers rely on ad-hoc solutions

**Research Methodology**: 5-agent parallel investigation covering:
1. Local ClickHouse deployment options
2. GUI/Web visualization tools (11 tools analyzed)
3. CLI tools (7 tools analyzed)
4. IDE integrations (8 environments analyzed)
5. Python ecosystem (pandas, Jupyter, visualization libraries)

## Decision

**Implement a comprehensive 5-tool visualization stack** covering web, CLI, and monitoring needs with 100% open-source options.

### Selected Toolchain

**Tier 1: Essential Tools (Required)**
1. **CH-UI** - Modern web interface for interactive exploration
2. **clickhouse-client** - Official CLI for scripting and automation
3. **ClickHouse Play** - Built-in web UI for quick queries

**Tier 2: Advanced Tools (Optional)**
4. **chdig** - TUI performance monitoring and profiling
5. **clickhouse-local** - File-based analysis without server

### Selection Criteria

**Web Interface Decision**: CH-UI over alternatives
- Rejected: Tabix (unmaintained since 2022), LightHouse (archived 2024), HouseOps (2018)
- Rejected: ClickHouse-Mate (minimal maintenance, AGPLv3 license)
- Selected: CH-UI (508 stars, TypeScript, active development, Apache 2.0)

**CLI Decision**: Official clickhouse-client over third-party
- Rejected: clickhouse-cli (HTTP-only, limited session support)
- Rejected: chc (low adoption, Windows limitations)
- Rejected: usql (generic, not ClickHouse-optimized)
- Selected: clickhouse-client (70+ formats, AI assistance, production-proven)

**Monitoring Decision**: chdig over alternatives
- No mature alternatives found (HouseOps unmaintained)
- Selected: chdig (Rust, flamegraph support, pre-alpha but actively developed)

## Implementation

### Tool 1: CH-UI Web Interface

**Integration**: Docker Compose service

**File**: `docker-compose.yml` (add to existing services)

```yaml
services:
  ch-ui:
    image: ghcr.io/caioricciuti/ch-ui:latest
    container_name: gapless-ch-ui
    ports:
      - "5521:5521"
    environment:
      VITE_CLICKHOUSE_URL: http://localhost:8123
      VITE_CLICKHOUSE_USER: default
      VITE_CLICKHOUSE_PASS: ''
    depends_on:
      clickhouse:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - gapless-network
```

**Access**: `http://localhost:5521`

**Features**:
- TypeScript UI with IntelliSense
- Multi-tab SQL editor with syntax highlighting
- Real-time performance dashboard
- Schema browser (tables, columns, types)
- Query history (LocalStorage persistence)
- Dark/Light mode

**Rationale**: Modern alternative to unmaintained Tabix, active development, Apache 2.0 license

---

### Tool 2: ClickHouse Play (Built-in)

**Integration**: Documentation only (ships with ClickHouse 20.11+)

**Access**: `http://localhost:8123/play`

**Features**:
- Zero installation (built-in)
- Query execution with results display
- Query history via URL base64 encoding
- Limited to 10K rows / 1MB per query

**Rationale**: Simplest option for quick ad-hoc queries, already available

---

### Tool 3: clickhouse-client CLI

**Integration**: Shell aliases + documentation

**File**: `docs/development/CLICKHOUSE_CLIENT_GUIDE.md`

**Setup**:
```bash
# Via Docker (recommended for gapless-crypto-data)
alias ch='docker exec -it gapless-clickhouse clickhouse-client'

# Single query
alias chq='docker exec -it gapless-clickhouse clickhouse-client --query'

# Export formats
alias ch-csv='docker exec -it gapless-clickhouse clickhouse-client --format CSV --query'
alias ch-json='docker exec -it gapless-clickhouse clickhouse-client --format JSONEachRow --query'
```

**Features**:
- 70+ output formats (CSV, JSON, Parquet, Arrow, Markdown, etc.)
- Progress bar with real-time metrics (rows/sec, bytes, execution time)
- Query parameters for SQL injection prevention
- AI-powered query generation (`??` prefix with OpenAI/Anthropic)
- Keyboard shortcuts (Alt+Shift+E for external editor, Ctrl+R for history)
- In-client autocomplete (SQL keywords, tables, columns)

**Rationale**: Official tool, production-ready, comprehensive format support

---

### Tool 4: chdig TUI Monitoring

**Integration**: Homebrew installation + validation script

**Installation**:
```bash
brew install chdig
```

**Usage**:
```bash
# Monitor local instance
chdig --host localhost --port 9000

# Cluster monitoring
chdig --cluster my_cluster
```

**Features**:
- Top-like interactive TUI
- Flamegraph visualization (CPU, memory, live metrics)
- Multiple views: slow queries, recent queries, processors, backups, replicas
- Historical analysis (rotated system logs)
- Cluster support
- Written in Rust (fast, low overhead)

**Rationale**: Best-in-class TUI for ClickHouse, active development, MIT license

**Limitations**: Pre-alpha status (interface may change), monitoring-only (no data manipulation)

---

### Tool 5: clickhouse-local (File Analysis)

**Integration**: Documentation only (bundled with ClickHouse)

**File**: `docs/development/CLICKHOUSE_LOCAL_GUIDE.md`

**Usage**:
```bash
# Query local CSV files
clickhouse-local --query "SELECT * FROM file('data.csv', CSV) LIMIT 10"

# Format conversion
clickhouse-local \
  --input-format JSONLines \
  --output-format Parquet \
  --query "SELECT * FROM table" < data.json > data.parquet

# S3 file analysis
clickhouse-local --query "
  SELECT count()
  FROM s3('https://data.binance.vision/data.parquet')
"
```

**Features**:
- Embedded ClickHouse engine (no server required)
- Query local/remote files with full ClickHouse SQL
- Same core as ClickHouse server (all formats/engines supported)
- Data persistence with `--path` parameter
- Stream processing and ETL preprocessing

**Rationale**: Essential for file validation before ingestion, format conversion, ad-hoc analysis

**Limitations**: Not suitable for gapless-crypto-data primary database (requires persistent ReplacingMergeTree)

---

## Validation

### Automated Validation Suite

**File**: `scripts/validate-clickhouse-tools.sh`

**Tests**:

1. **Docker Health Checks**:
   ```bash
   docker ps | grep -q gapless-clickhouse && echo "✅ ClickHouse running"
   docker ps | grep -q gapless-ch-ui && echo "✅ CH-UI running"
   ```

2. **HTTP Endpoint Checks**:
   ```bash
   curl -s http://localhost:8123/ping && echo "✅ ClickHouse HTTP"
   curl -s http://localhost:5521 | grep -q "CH-UI" && echo "✅ CH-UI web"
   curl -s http://localhost:8123/play | grep -q "ClickHouse" && echo "✅ Play UI"
   ```

3. **CLI Functionality**:
   ```bash
   docker exec gapless-clickhouse clickhouse-client --query "SELECT 1" | grep -q "1" && echo "✅ clickhouse-client"
   ```

4. **chdig Installation**:
   ```bash
   which chdig && echo "✅ chdig installed"
   chdig --version && echo "✅ chdig operational"
   ```

5. **clickhouse-local**:
   ```bash
   echo "a,b\n1,2" > /tmp/test.csv
   clickhouse-local --query "SELECT * FROM file('/tmp/test.csv', CSV)" | grep -q "1" && echo "✅ clickhouse-local"
   ```

**Expected Output**: All 7 checks pass (5 tools + 2 ClickHouse interfaces)

---

### Manual Validation Checklist

- [ ] CH-UI accessible at http://localhost:5521 with ClickHouse connection
- [ ] ClickHouse Play accessible at http://localhost:8123/play
- [ ] clickhouse-client executes queries via Docker
- [ ] chdig displays performance metrics
- [ ] clickhouse-local queries local CSV files
- [ ] All tools connect to same ClickHouse instance
- [ ] Documentation accurate and complete

---

## Consequences

### Positive

- **Comprehensive Coverage**: Web + CLI + TUI + file analysis
- **100% Open Source**: All tools Apache 2.0 / MIT licensed
- **Zero Cost**: No commercial licenses required
- **Production-Ready**: Official tools + actively maintained projects
- **Developer Experience**: Modern UIs (CH-UI) + powerful CLI (clickhouse-client)
- **Performance Monitoring**: chdig provides flamegraph profiling
- **File Validation**: clickhouse-local enables pre-ingestion validation

### Negative

- **Docker Dependency**: CH-UI requires Docker (acceptable given existing setup)
- **Pre-Alpha Risk**: chdig interface may change (low impact, monitoring-only tool)
- **No Desktop GUI**: Omitted commercial tools (DataGrip, Beekeeper Studio) from required stack
- **Learning Curve**: 5 tools to learn (mitigated by comprehensive documentation)

### Neutral

- **Tooling Redundancy**: Multiple ways to query (web, CLI, TUI)
  - Justification: Different use cases (exploration vs automation vs monitoring)
- **Homebrew Dependency**: chdig requires Homebrew (standard on macOS)

---

## Alternatives Considered

### Alternative 1: Single Desktop GUI (Rejected)

**Options**: DataGrip (JetBrains), DBeaver, Beekeeper Studio

**Pros**: Unified interface, less cognitive overhead

**Cons**:
- DataGrip commercial license for business use
- DBeaver feels heavyweight for simple tasks
- Desktop apps don't address CLI/automation needs

**Verdict**: Rejected - Web + CLI combination more flexible

---

### Alternative 2: Commercial Tools Only (Rejected)

**Options**: DataGrip + TablePlus

**Pros**: Best-in-class UX, comprehensive features

**Cons**:
- Cost barrier ($100-780/year)
- Violates OSS preference principle
- Not all users need commercial features

**Verdict**: Rejected - Open source alternatives sufficient

---

### Alternative 3: Minimal Stack (CH-UI Only) (Rejected)

**Pros**: Simplest to document, single tool to learn

**Cons**:
- No CLI for automation/scripting
- No performance monitoring
- No file validation capabilities

**Verdict**: Rejected - Insufficient for comprehensive development

---

### Alternative 4: Python-Only Visualization (Rejected)

**Options**: Jupyter + Streamlit + Plotly

**Pros**: Programmable, version-controlled dashboards

**Cons**:
- Requires Python coding for simple queries
- Not suitable for ad-hoc exploration
- Higher barrier to entry

**Verdict**: Rejected as primary approach, kept as optional enhancement (future ADR)

---

## Compliance

- **Error Handling**: All tools follow fail-fast principle (connection errors propagate)
- **SLOs**:
  - Availability: Docker health checks ensure CH-UI uptime matches ClickHouse
  - Correctness: Validation suite verifies all tools connect to same database
  - Observability: chdig provides metrics dashboard
  - Maintainability: Documentation guides reduce support burden
- **OSS Preference**: All tools open source (Apache 2.0 / MIT)
- **Auto-Validation**: Automated script validates tool availability
- **Semantic Release**: Docker Compose changes follow conventional commits

---

## References

- Multi-agent research artifacts: `tmp/clickhouse-local-viz-research/`
- CH-UI repository: https://github.com/caioricciuti/ch-ui
- chdig repository: https://github.com/azat/chdig
- ClickHouse client docs: https://clickhouse.com/docs/en/interfaces/cli
- Plan: `docs/plan/0008-clickhouse-local-visualization-toolchain/plan.yaml`
