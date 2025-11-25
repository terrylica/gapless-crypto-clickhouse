# ADR-0036: CI/CD Workflow DRY Refactoring

**Status**: Accepted
**Date**: 2025-01-24
**Deciders**: Engineering Team
**Related**: ADR-0035 (CI/CD Production Validation Policy), ADR-0027 (Local-Only PyPI Publishing)

## Context and Problem Statement

Following ADR-0035 implementation, the CI/CD infrastructure has accumulated significant duplication across 3 workflows:

1. **E2E Validation Workflow**: Broken (100% failure rate), unmaintained, redundant with Production Validation
2. **Setup Step Duplication**: Python + UV setup repeated 4 times (56 lines), Doppler setup repeated 2 times (4 lines)
3. **Validation Script Duplication**: 90-120 lines of shared logic across `validate_e2e_simple.py`, `validate_clickhouse_cloud.py`, `run_validation.py`

**Investigation Evidence** (2025-01-24):

- 3-agent parallel analysis identified redundancy across workflows and scripts
- `e2e-validation.yml` has 100% failure rate since 2025-11-20
- Scheduled trigger disabled (commented out), suggesting intentional abandonment
- Violates ADR-0035 policy (runs ruff/mypy in CI/CD)

**Core Tension**: DRY principle vs workflow independence and script portability (PEP 723).

## Decision Drivers

1. **Maintainability**: Duplication increases bug surface area (fixes must be replicated 3x)
2. **Policy Compliance**: `e2e-validation.yml` violates ADR-0035 (runs linting in CI/CD)
3. **Reliability**: 100% failure rate for broken workflow signals abandonment
4. **Simplicity**: 2-workflow architecture aligns with ADR-0035 (Release + Production Validation)
5. **Code Reuse**: Shared validation logic enables consistent testing patterns

## Considered Options

### Option 1: Status Quo (Keep All Duplication)

**Pros**:

- No changes required
- Each workflow/script fully self-contained
- PEP 723 inline dependencies preserved

**Cons**:

- 56 lines of workflow duplication (28% of total)
- 90-120 lines of script duplication
- Bug fixes require 3x replication
- Broken workflow continues consuming CI/CD minutes on manual triggers

**Decision**: ❌ Rejected - Violates DRY principle, broken workflow provides no value

---

### Option 2: Reusable Workflows + Script Templates

**Pros**:

- Maximum DRY compliance
- Single source of truth

**Cons**:

- High complexity (reusable workflow limitations)
- Template generation adds build step
- Harder debugging (indirection)
- Overkill for current scale (3 workflows, 3 scripts)

**Decision**: ❌ Rejected - Too complex for marginal benefit

---

### Option 3: Composite Actions + Shared Module (CHOSEN)

**Approach**:

1. **Delete** `e2e-validation.yml` (broken, redundant)
2. **Create composite actions** for setup steps (`.github/actions/setup-python-uv/`, `.github/actions/setup-doppler/`)
3. **Extract shared validation logic** to `src/gapless_crypto_clickhouse/validation/e2e_core.py`
4. **Refactor scripts** to import e2e_core functions

**Pros**:

- Incremental refactoring (low risk)
- Immediate duplication reduction (56 workflow lines, 90-120 script lines)
- Preserves workflow independence (separate jobs, triggers, schedules)
- Creates testable validation primitives
- Composite actions are GitHub-native (no custom tooling)

**Cons**:

- Scripts lose PEP 723 full self-containment (acceptable trade-off)
- Composite actions add one level of indirection

**Decision**: ✅ Accepted - Best balance of DRY compliance and maintainability

---

## Decision Outcome

**Chosen**: Option 3 (Composite Actions + Shared Module)

### Implementation Strategy

**Phase 1: Delete Redundant Workflow**

- Remove `.github/workflows/e2e-validation.yml`
- Rationale: 100% failure rate, violates ADR-0035, redundant with `simplified-e2e-validation` job

**Phase 2: Composite Actions (Workflow DRY)**

- Create `.github/actions/setup-python-uv/action.yml` (eliminates 52 lines)
- Create `.github/actions/setup-doppler/action.yml` (eliminates 4 lines)
- Update `production-validation.yml` (3 jobs)
- Update `release.yml`

**Phase 3: Shared Validation Module (Script DRY)**

- Create `src/gapless_crypto_clickhouse/validation/e2e_core.py`
- Functions: `create_clickhouse_client()`, `validate_table_exists()`, `insert_test_data()`, `query_with_final()`, `cleanup_test_data()`, `log_with_timestamp()`
- Refactor `validate_e2e_simple.py` and `validate_clickhouse_cloud.py`

**Phase 4: Documentation**

- Update CLAUDE.md (2-workflow architecture)
- Remove e2e-validation.yml references

### Target Architecture

**Workflows** (2 total):

1. **Release** (`release.yml`): Semantic versioning, changelog, GitHub releases
2. **Production Validation** (`production-validation.yml`): Scheduled infrastructure monitoring (3 jobs: ClickHouse Cloud, Binance CDN, Simplified E2E)

**Composite Actions** (2 total):

1. `.github/actions/setup-python-uv/`: Python 3.12 + UV with caching
2. `.github/actions/setup-doppler/`: Doppler CLI installation

**Validation Module** (1 new):

- `src/gapless_crypto_clickhouse/validation/e2e_core.py`: Reusable validation primitives

### Impact Metrics

**Before**:

- Workflows: 3 (1 broken)
- Workflow duplication: 56 lines (28%)
- Script duplication: 90-120 lines
- Total lines: ~200 workflow + ~500-520 script = 700-720 lines

**After**:

- Workflows: 2 (both working)
- Workflow duplication: 0 lines (0%)
- Script duplication: 0 lines (0%)
- Total lines: ~150 workflow + ~400 script = 550 lines

**Net Reduction**: 146-176 lines eliminated (20-25% reduction)

## Consequences

### Positive

1. **Maintainability**: Bug fixes propagate automatically via shared module
2. **Reliability**: Remove broken workflow that consumes CI/CD resources
3. **Policy Compliance**: Eliminate ADR-0035 violation (linting in CI/CD)
4. **Simplicity**: 2-workflow architecture is easier to reason about
5. **Testability**: Shared module enables unit testing of validation primitives

### Negative

1. **Import Dependencies**: Validation scripts lose PEP 723 full self-containment
2. **Module Stability**: Must maintain backward compatibility in e2e_core API
3. **Indirection**: Composite actions add one level of abstraction

### Neutral

1. **Workflow Behavior**: No changes to triggers, schedules, or job logic
2. **Validation Coverage**: Same E2E validation coverage (via simplified-e2e-validation job)

## Validation Criteria

**Acceptance Criteria**:

- [ ] `e2e-validation.yml` deleted
- [ ] Composite actions created and working
- [ ] `production-validation.yml` uses composite actions (all 3 jobs pass)
- [ ] `release.yml` uses composite actions
- [ ] `e2e_core.py` module created with 6+ functions
- [ ] `validate_e2e_simple.py` refactored (imports e2e_core)
- [ ] `validate_clickhouse_cloud.py` refactored (imports e2e_core)
- [ ] Documentation updated (CLAUDE.md)
- [ ] Manual workflow test passes (production-validation.yml)

**Rollback Criteria**:

- If composite actions cause workflow failures (>10% failure rate), revert to inline steps
- If shared module import failures, revert to duplicated script logic

## Constraints

1. **No Behavior Changes**: Workflows must produce identical results before/after refactoring
2. **ADR-0035 Compliance**: Maintain local-first development, production validation exception
3. **Zero Downtime**: Scheduled production validation continues during refactoring

## References

- ADR-0035: CI/CD Production Validation Policy (foundational policy)
- ADR-0027: Local-Only PyPI Publishing (workflow policy precedent)
- GitHub Actions Composite Actions: https://docs.github.com/en/actions/creating-actions/creating-a-composite-action
- DRY Investigation: 3-agent parallel analysis (2025-01-24)
