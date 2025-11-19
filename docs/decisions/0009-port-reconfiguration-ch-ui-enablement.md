# ADR-0009: Port Reconfiguration for CH-UI Enablement

## Status

Implemented (2025-11-18)

## Context

### Problem Statement

ADR-0008 validation (VALIDATION_REPORT.md) identified a port conflict preventing CH-UI web interface from starting:

**Current State**:
- ClickHouse container: `gapless-clickhouse` running on non-standard ports (9001 native, 8124 HTTP)
- QuestDB container: `gapless-questdb` occupying standard port 9000
- CH-UI container: `gapless-ch-ui` not started, expects ClickHouse at standard port 8123

**Impact**:
- CH-UI web interface unavailable (4/5 visualization tools operational, 1/5 blocked)
- ADR-0008 implementation incomplete (CH-UI documented but not functional)
- Non-standard ports require manual configuration for future tools
- Validation script needed port auto-detection workaround

**Root Cause**: QuestDB container from pre-v4.0.0 architecture still running, occupying port 9000.

### Current Architecture (v4.0.0)

**Branch**: main-clickhouse (ClickHouse-only, QuestDB removed in v4.0.0)

**Database Status**:
- ✅ ClickHouse: Primary database (v24.1-alpine), functional on ports 9001/8124
- ⚠️ QuestDB: Legacy container still running (v7.4.3), **no longer used** in v4.0.0
- ❌ CH-UI: Not started due to port configuration mismatch

**Container State**:
```bash
$ docker ps | grep -E "clickhouse|questdb|ch-ui"
gapless-clickhouse   Up 7 hours   0.0.0.0:9001->9000/tcp, 0.0.0.0:8124->8123/tcp
gapless-questdb      Up 33 hours  0.0.0.0:9000->9000/tcp
```

**Data Persistence**: All data in ClickHouse (QuestDB data not migrated, not needed for v4.0.0)

### Decision Drivers

1. **Completeness**: CH-UI is the only visualization tool not operational (4/5 working)
2. **Standard Ports**: Using standard ports (9000/8123) simplifies configuration and reduces friction
3. **v4.0.0 Architecture**: QuestDB removed in v4.0.0, no reason to keep legacy container running
4. **User Experience**: CH-UI provides modern web interface for ClickHouse exploration

## Decision

**Reconfigure ClickHouse to use standard ports (9000/8123) by stopping QuestDB container**, then start CH-UI web interface.

### Implementation Strategy

**Phase 1: Stop QuestDB** (no data loss, container preserved)
- Stop QuestDB container to free port 9000
- Container and volumes remain intact (can be restarted if needed)

**Phase 2: Reconfigure ClickHouse** (minimal downtime)
- Stop existing ClickHouse container (gapless-clickhouse)
- Remove container (volumes persist, no data loss)
- Start ClickHouse via docker-compose.yml (standard ports 9000/8123)

**Phase 3: Start CH-UI** (immediate benefit)
- Start CH-UI via docker-compose.yml
- Connects to ClickHouse at standard port 8123 (internal Docker network)

**Phase 4: Validation** (comprehensive checks)
- Run validation script (should pass without port auto-detection)
- Verify CH-UI accessible at http://localhost:5521
- Confirm all 5 visualization tools operational

## Implementation

### Phase 1: Stop QuestDB

```bash
# Stop QuestDB container (no data loss)
docker stop gapless-questdb

# Verify port 9000 freed
docker ps | grep 9000  # Should return nothing
```

**Rationale**: QuestDB data not needed in v4.0.0 (ClickHouse-only). Container preserved for potential rollback.

**Rollback**: `docker start gapless-questdb` (instant, no data loss)

### Phase 2: Reconfigure ClickHouse

```bash
# Stop and remove existing ClickHouse container (volumes persist)
docker stop gapless-clickhouse
docker rm gapless-clickhouse

# Start ClickHouse via docker-compose.yml (standard ports)
docker compose up -d clickhouse

# Verify standard ports active
docker ps | grep gapless-clickhouse
# Expected: 0.0.0.0:9000->9000/tcp, 0.0.0.0:8123->8123/tcp
```

**Rationale**: docker-compose.yml already configured for standard ports. Volumes persist (/var/lib/clickhouse), zero data loss.

**Data Safety**: ClickHouse data stored in Docker volumes, unaffected by container recreation.

### Phase 3: Start CH-UI

```bash
# Start CH-UI web interface
docker compose up -d ch-ui

# Verify container running
docker ps | grep gapless-ch-ui
# Expected: 0.0.0.0:5521->5521/tcp

# Test accessibility
curl -s http://localhost:5521 | grep -q "CH-UI"
```

**Rationale**: CH-UI is a frontend SPA running in the browser. Browsers cannot resolve Docker internal hostnames, requiring `http://localhost:8123` (exposed via port mapping) for connectivity.

### Phase 4: Validation

```bash
# Run comprehensive validation suite
bash scripts/validate-clickhouse-tools.sh

# Expected output:
# [1/7] ✅ PASS - ClickHouse container running (port 9000)
# [2/7] ✅ PASS - HTTP interface responding (port 8123)
# [3/7] ✅ PASS - ClickHouse Play UI accessible (http://localhost:8123/play)
# [4/7] ✅ PASS - CH-UI web interface accessible (http://localhost:5521)
# [5/7] ✅ PASS - clickhouse-client functional
# [6/7] ⚠️ WARN - chdig not installed (optional)
# [7/7] ✅ PASS - clickhouse-local functional
#
# Tests passed: 6/6 (all tools operational)
```

**Validation Criteria**:
- ✅ ClickHouse on standard ports (9000/8123)
- ✅ CH-UI accessible at http://localhost:5521
- ✅ All visualization tools pass validation (6/6 critical tests)
- ✅ No port auto-detection needed in validation script

## Validation

### Automated Validation Suite

**Port Verification**:
```bash
docker port gapless-clickhouse 9000 | grep -q "0.0.0.0:9000"
docker port gapless-clickhouse 8123 | grep -q "0.0.0.0:8123"
```
**Expected**: Both commands succeed (standard ports active)

**CH-UI Accessibility**:
```bash
curl -sf http://localhost:5521 | grep -q "CH-UI"
```
**Expected**: Exit code 0 (CH-UI responsive)

**Comprehensive Validation**:
```bash
bash scripts/validate-clickhouse-tools.sh
```
**Expected**: 6/6 critical tests passed (was 5/5 before, now includes CH-UI)

### Manual Review Checklist

- [ ] QuestDB container stopped (no longer needed in v4.0.0)
- [ ] ClickHouse on standard ports (9000/8123)
- [ ] ClickHouse data intact (no data loss during reconfiguration)
- [ ] CH-UI web interface accessible at http://localhost:5521
- [ ] All 5 visualization tools operational
- [ ] Validation script passes without port auto-detection workarounds

## Consequences

### Positive

- **Completeness**: All 5 visualization tools operational (was 4/5)
- **Standard Ports**: ClickHouse uses industry-standard ports (9000/8123)
- **Simplified Configuration**: Future tools work without port customization
- **Clean Architecture**: v4.0.0 architecture fully realized (ClickHouse-only)
- **Validation Simplicity**: No port auto-detection needed in scripts

### Negative

- **QuestDB Inaccessible**: QuestDB container stopped (not a concern, v4.0.0 is ClickHouse-only)
- **Brief Downtime**: ClickHouse restart required (~5 seconds, minimal impact)
- **Container Recreation**: New ClickHouse container (volumes persist, no data loss)

### Neutral

- **Docker Compose Dependency**: Reliance on docker-compose.yml for port configuration (already required for CH-UI)
- **QuestDB Rollback**: Container preserved, can be restarted if needed for pre-v4.0.0 testing

## Alternatives Considered

### Alternative 1: Keep Non-Standard Ports (Rejected)

**Implementation**: Manually configure CH-UI environment variables to use port 8124.

**Pros**:
- No ClickHouse downtime
- QuestDB remains accessible

**Cons**:
- Non-standard ports complicate future tool integration
- Manual configuration for every tool
- Validation scripts need permanent port auto-detection
- Inconsistent with v4.0.0 architecture (ClickHouse-only)

**Verdict**: Rejected - violates v4.0.0 architecture principle (ClickHouse-only)

### Alternative 2: Use Different Ports for CH-UI (Rejected)

**Implementation**: Map ClickHouse to different external ports (e.g., 9002/8125), update CH-UI config.

**Pros**:
- Both QuestDB and ClickHouse accessible simultaneously

**Cons**:
- Unnecessary complexity (QuestDB not used in v4.0.0)
- Non-standard ports persist
- Requires docker-compose.yml modification
- Breaks ADR-0008 validation assumptions

**Verdict**: Rejected - adds complexity without benefit (QuestDB not needed)

### Alternative 3: Update docker-compose.yml for Co-Existence (Rejected)

**Implementation**: Modify docker-compose.yml to use non-standard ports for ClickHouse.

**Pros**:
- QuestDB and ClickHouse coexist

**Cons**:
- Permanently commits to non-standard ports
- Requires documentation updates
- Complicates v4.0.0 release (should use standard ports)
- QuestDB provides no value in v4.0.0

**Verdict**: Rejected - QuestDB removed in v4.0.0, no reason to accommodate legacy container

## Compliance

- **Error Handling**: All commands fail-fast (docker stop, docker rm, docker compose up)
  - Port conflict detection: Script fails if port 9000 still occupied after QuestDB stop
  - Container start failures: docker compose up exits with error if ports unavailable
  - Validation failures: Validation script exits with non-zero code if CH-UI inaccessible
- **SLOs**:
  - Availability: ~5 second downtime during ClickHouse restart (acceptable for development)
  - Correctness: ✅ Data persists in volumes, zero data loss
  - Observability: ✅ Validation script confirms all tools operational
  - Maintainability: ✅ Standard ports reduce configuration burden
- **OSS Preference**: Uses Docker Compose (OSS) for orchestration, no custom port management code
- **Auto-Validation**: Automated validation suite confirms success (scripts/validate-clickhouse-tools.sh)
- **Semantic Release**: Conventional commit for configuration change (chore or docs type)

## References

- ADR-0008: ClickHouse Local Visualization Toolchain
- VALIDATION_REPORT.md: Port conflict documentation
- Plan: `docs/plan/0009-port-reconfiguration-ch-ui-enablement/plan.yaml`
