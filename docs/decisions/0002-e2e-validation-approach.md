# ADR-0002: E2E Validation Approach for QuestDB Refactor

## Status

Accepted

## Context

ADR-0001 implemented QuestDB as single source of truth (Phases 1-3 complete). Before merging to main and triggering v4.0.0 release via semantic-release, we need comprehensive end-to-end validation to ensure:

- Breaking changes work as intended (CLI removal, Python 3.12+ requirement)
- QuestDB integration functions correctly (schema, ingestion, queries)
- Zero-gap guarantee maintained
- Error handling complies with raise-and-propagate policy
- SLO targets met (availability, correctness, observability, maintainability)

**User Requirements** (2025-11-15):
- E2E validation in branch before PR
- Comprehensive testing (edge cases + error scenarios)
- Real Binance CloudFront data (small dataset)
- macOS Colima deployment (current environment)
- Reuse existing test artifacts to reduce context-token usage

**Constraints**:
- Phase 4 (Migration Tooling) skipped - deferred to post-v4.0.0
- Phase 5 (Testing & Validation) skipped - this e2e validation fills gap
- Phase 6 (Documentation) skipped - deployment guides already complete
- No integration tests exist for v4.0.0 QuestDB modules

## Decision

Implement **comprehensive e2e validation using parallel specialized agents** with dynamic writeTodo creation, validating all v4.0.0 modules against real QuestDB instance and authentic Binance data.

### Validation Architecture

**Parallel Agent Strategy**:
1. **Environment Setup Agent**: Colima + QuestDB + schema + .env
2. **Bulk Loader Agent**: CloudFront → QuestDB ingestion validation
3. **Query Interface Agent**: All query methods + edge cases
4. **Gap Filler Agent**: Detection + filling + deduplication
5. **Error Handling Agent**: Raise-and-propagate compliance
6. **Performance/Observability Agent**: SLO validation + logging
7. **Integration Agent**: Full pipeline end-to-end

**Dynamic writeTodo Flow**:
- Each agent starts with ONE initial writeTodo
- Complete → Analyze findings → CREATE next writeTodo(s)
- Mark completed → Execute next → Repeat until validated
- Non-pre-defined tiers - writeTodos emerge from discoveries

**Reusable Artifacts** (reduce context-token usage):
- `tests/conftest.py` - Real Binance data download fixture (`real_btcusdt_1h_sample`)
- `tests/test_error_handling.py` - Error propagation testing patterns
- `tests/test_gap_filler.py` - Gap detection logic (adapt for QuestDB)
- CloudFront download patterns from existing collectors

### Validation Scope

**In Scope**:
- ✅ QuestDB deployment (docker-compose.macos.yml via Colima)
- ✅ Schema application and validation (schema.sql)
- ✅ Bulk loader (CloudFront → QuestDB, 1-2 months BTCUSDT 1m data)
- ✅ Query interface (get_latest, get_range, get_multi_symbol, execute_sql, detect_gaps)
- ✅ Gap filler (SQL detection + REST API filling + UPSERT deduplication)
- ✅ Error handling (all errors raise and propagate, no silent failures)
- ✅ Performance SLOs (>100K rows/sec ingestion, <1s query latency)
- ✅ Observability (INFO/DEBUG logging, Prometheus metrics)
- ✅ Full pipeline integration (realistic scenario)

**Out of Scope**:
- ❌ Linux native deployment (validated via documentation review only)
- ❌ Linux Docker deployment (validated via documentation review only)
- ❌ Migration tooling (Phase 4 deferred)
- ❌ Multi-platform testing (macOS only)
- ❌ Load testing at scale (manual QA acceptable per plan)

### Test Data Strategy

**Real Binance Data** (not synthetic):
- Download from CloudFront: BTCUSDT 1m, Jan-Feb 2024 (~2 months)
- Rationale: Tests real-world data format, parsing, CloudFront reliability
- Size: ~5-10MB download (acceptable for comprehensive validation)
- Reuse pattern from `conftest.py` fixture

**Additional Symbols** (for multi-symbol testing):
- ETHUSDT 1m, Jan 2024 (1 month)
- Verify no cross-contamination between symbols

### Error Handling Validation

**Compliance with ADR-0001 Policy**:
- ✅ Connection failures → ConnectionError (propagate to caller)
- ✅ Invalid inputs → ValueError (propagate with context)
- ✅ API failures → httpx.HTTPStatusError (propagate with status code)
- ✅ Query failures → psycopg.Error (propagate with SQL context)
- ❌ No fallback mechanisms (explicitly test absence)
- ❌ No retry logic (explicitly test absence)
- ❌ No silent failures (explicitly test absence)

**Test Patterns** (reuse from `test_error_handling.py`):
- Stop QuestDB → attempt query → assert ConnectionError
- Invalid symbol (special chars) → assert ValueError
- Non-existent CloudFront month → assert HTTPError 404
- Corrupted ZIP → assert BadZipFile
- Verify temp file cleanup on all error paths

## Consequences

### Positive

- **Pre-PR confidence**: Comprehensive validation before v4.0.0 release
- **Real-world testing**: Authentic Binance data + actual QuestDB deployment
- **Error compliance**: Validates raise-and-propagate policy enforcement
- **SLO validation**: Confirms availability, correctness, observability, maintainability
- **Artifact reuse**: Leverages existing test patterns (reduced context-token usage)
- **Documentation**: Validation report serves as v4.0.0 smoke test guide

### Negative

- **Time investment**: Comprehensive validation takes ~30 minutes
- **Environment dependency**: Requires Colima running (macOS only)
- **Network dependency**: Requires CloudFront access (real data download)
- **No CI/CD integration**: Manual execution only (automated testing deferred to post-v4.0.0)

### Neutral

- **Phase 5 skip justified**: This e2e validation fulfills Phase 5 deliverables informally
- **No regression tests**: v3.x tests incompatible with v4.0.0 (file-based vs database)
- **Manual QA acceptable**: Per ADR-0001 plan, comprehensive automated testing deferred

## Compliance

### SLOs

**Availability**:
- QuestDB deployment health checks validated (systemd/Docker)
- Connection failure handling validated (raise ConnectionError)
- No silent fallbacks (explicitly tested)

**Correctness**:
- Zero-gap guarantee validated via SQL gap detection
- Deduplication validated via UPSERT semantics
- Data authenticity validated (CloudFront source tracking)
- 11-column microstructure format validated

**Observability**:
- INFO/DEBUG logging validated (connection lifecycle, ingestion metrics)
- Prometheus metrics endpoint validated (/metrics on port 9003)
- Data lineage tracking validated (data_source column)

**Maintainability**:
- Standard PostgreSQL protocol validated (psycopg3 queries)
- pandas DataFrame return type validated (backward compatibility)
- Documentation accuracy validated (deployment guides)

### Error Handling

**Policy Compliance** (raise-and-propagate):
- ✅ All connection failures raise ConnectionError
- ✅ All validation failures raise ValueError
- ✅ All API failures raise httpx.HTTPStatusError
- ✅ All query failures raise psycopg.Error
- ❌ No automatic retries (explicitly validated)
- ❌ No fallback defaults (explicitly validated)
- ❌ No silent failures (explicitly validated)

### OSS Libraries

All validation uses OSS tools:
- **pytest**: Test framework (existing in dev dependencies)
- **psycopg**: PostgreSQL client (already in dependencies)
- **pandas**: DataFrame validation (already in dependencies)
- **httpx**: REST API testing (already in dependencies)
- **docker-compose**: QuestDB deployment (Colima runtime)

### Auto-Validation

**Validation Artifacts**:
- Validation report: `tmp/e2e-validation/VALIDATION_REPORT.md`
- Agent logs: `tmp/e2e-validation/agent-N-*.log`
- QuestDB logs: Docker container logs
- Performance metrics: Ingestion rate, query latency measurements

**Success Criteria** (auto-validated):
- All agents report success (no failures)
- Ingestion rate >100K rows/sec
- Query latency <1s for typical OHLCV ranges
- Zero gaps detected after full pipeline
- All errors raised and propagated (no silent failures)

## Alternatives Considered

### Option 1: Unit Tests Only (Rejected)

**Pros**: Fast, no environment dependency
**Cons**: Doesn't validate QuestDB integration, misses deployment issues
**Verdict**: Insufficient for BREAKING CHANGE validation

### Option 2: Manual QA Checklist (Rejected)

**Pros**: Simple, no automation needed
**Cons**: Error-prone, not reproducible, no artifact trail
**Verdict**: Acceptable per plan but less rigorous than automated

### Option 3: Full CI/CD Integration (Rejected)

**Pros**: Automated on every commit, regression protection
**Cons**: Complex setup, deferred to post-v4.0.0 per plan
**Verdict**: Out of scope for pre-PR validation

### Option 4: Synthetic Data Only (Rejected)

**Pros**: No network dependency, faster
**Cons**: Doesn't test real CloudFront behavior, misses data quirks
**Verdict**: User requirement is "real Binance CloudFront data"

## Implementation Plan

See `docs/plan/0002-e2e-validation/plan.yaml` for detailed execution plan.

**Phases**:
1. Environment Setup (Agent 1)
2. Parallel Validation (Agents 2-6)
3. Integration Testing (Agent 7)
4. Validation Report Generation

**Timeline**: ~30 minutes (comprehensive testing)

## References

- [ADR-0001: QuestDB as Single Source of Truth](0001-questdb-single-source-truth.md)
- [Implementation Plan Phase 1-3](../plan/0001-questdb-refactor/plan.yaml)
- [Deployment Guide: macOS Colima](../deployment/macos-colima-setup.md)
- [Test Fixtures](../../tests/conftest.py)

## Metadata

- **ADR ID**: 0002
- **Date**: 2025-11-15
- **Authors**: gapless-crypto-data team
- **Status**: Accepted
- **Related Plans**: docs/plan/0002-e2e-validation/plan.yaml
- **Depends On**: ADR-0001
