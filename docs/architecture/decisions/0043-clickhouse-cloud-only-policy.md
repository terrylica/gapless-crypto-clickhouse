# ADR-0043: ClickHouse Cloud-Only Architecture Policy

## Status

Accepted

## Date

2025-11-25

## Context

The gapless-crypto-clickhouse package previously supported two ClickHouse deployment options:

1. **Local development**: Docker Compose with ClickHouse container, CH-UI, ClickHouse Play
2. **Production**: ClickHouse Cloud (AWS) via Doppler credentials

This dual approach created maintenance burden:

- `docker-compose.yml` and local tooling guides required ongoing maintenance
- E2E tests for local web interfaces (CH-UI, ClickHouse Play) added complexity
- Documentation confusion between local and Cloud setups
- Homebrew ClickHouse deprecated (macOS Gatekeeper issues, disabled 2026-09-01)

## Decision

Establish **ClickHouse Cloud as the single source of truth** for all ClickHouse operations.

### What This Means

1. **Removed local development artifacts**:
   - `docker-compose.yml`
   - `docs/development/CHDIG_GUIDE.md`
   - `docs/development/CLICKHOUSE_CLIENT_GUIDE.md`
   - `docs/development/CLICKHOUSE_LOCAL_GUIDE.md`
   - `docs/development/CLICKHOUSE_PLAY_GUIDE.md`
   - `tests/e2e/test_ch_ui_dashboard.py`
   - `tests/e2e/test_clickhouse_play.py`
   - Legacy QuestDB deployment docs

2. **Credential management**: All credentials via Doppler (`aws-credentials/prd`)

3. **Schema deployment**: Via `scripts/deploy-clickhouse-schema.py` (not Docker initdb)

4. **Production validation**: GitHub Actions workflow (every 6 hours)

### Strict Enforcement

**CLICKHOUSE_HOST environment variable is REQUIRED** - no localhost fallback.

The `ClickHouseConfig.from_env()` method raises `ClickHouseCloudRequiredError` if `CLICKHOUSE_HOST` is not set. This ensures all ClickHouse operations target Cloud infrastructure.

**Code defaults** (when environment variables not set):

- `port`: 9440 (Cloud secure native)
- `http_port`: 8443 (Cloud HTTPS)
- `secure`: True (TLS/SSL enabled)

**Error message** guides users to configure Doppler or environment variables:

```
ClickHouseCloudRequiredError: CLICKHOUSE_HOST environment variable is REQUIRED.
ClickHouse Cloud is the single source of truth (ADR-0043).

Configure via Doppler (recommended):
  doppler run --project aws-credentials --config prd -- python script.py

Or via environment variables:
  export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
  export CLICKHOUSE_PASSWORD=your-password
```

## Consequences

### Positive

- **Simplified maintenance**: Single deployment target
- **Reduced documentation**: No local vs Cloud confusion
- **Consistent environment**: Development matches production
- **Security**: Credentials centralized in Doppler, not in docker-compose files

### Negative

- **Requires network**: Cannot develop offline with ClickHouse features
- **Cost**: ClickHouse Cloud has associated costs (mitigated by free tier)
- **Onboarding**: New developers need Doppler access

### Supersedes

- ADR-0008: ClickHouse Local Visualization Toolchain (superseded - local tools removed)
- ADR-0009: Port Reconfiguration for CH-UI Enablement (superseded - CH-UI removed)
- ADR-0010: Optional Development Tooling (chdig) (superseded - chdig guide removed)
- ADR-0013: Autonomous Validation Framework (partially superseded - local E2E tests removed)

## References

- ADR-0026: ClickHouse Cloud Data Pipeline
- ADR-0034: Schema Optimization for Prop Trading
- ADR-0035: CI/CD Production Validation
