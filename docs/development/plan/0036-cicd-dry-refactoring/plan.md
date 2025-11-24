# Plan: CI/CD Workflow DRY Refactoring Implementation

**ADR ID**: 0036
**Status**: In Progress
**Start Date**: 2025-01-24
**Updated**: 2025-01-24 (Initial planning)
**Owner**: Engineering Team

---

## (a) Plan

### Phase 1: Delete Redundant E2E Workflow

**Objective**: Remove broken and redundant `e2e-validation.yml` workflow.

**Tasks**:

1. Delete `.github/workflows/e2e-validation.yml`
2. Verify no documentation references exist
3. Test that production-validation.yml still provides E2E coverage via simplified-e2e-validation job

**Deliverables**:

- [ ] `e2e-validation.yml` deleted
- [ ] Documentation checked (CLAUDE.md, validation docs)

**Success Criteria**: Workflow count reduced from 3 to 2, no broken workflow consuming CI/CD resources.

---

### Phase 2: Create Composite Actions (Workflow DRY)

**Objective**: Eliminate 56 lines of duplicated setup steps across workflows.

**Tasks**:

1. Create `.github/actions/setup-python-uv/action.yml`:
   - Python 3.12 setup
   - UV installation with caching
   - Cache key: `uv.lock`
2. Create `.github/actions/setup-doppler/action.yml`:
   - Doppler CLI installation via `dopplerhq/cli-action@v3`
3. Update `production-validation.yml` (3 jobs):
   - Replace Python + UV setup in `clickhouse-cloud-validation`
   - Replace Python + UV setup in `binance-cdn-availability`
   - Replace Python + UV + Doppler setup in `simplified-e2e-validation`
4. Update `release.yml`:
   - Replace UV setup with composite action

**Deliverables**:

- [ ] `.github/actions/setup-python-uv/action.yml` created
- [ ] `.github/actions/setup-doppler/action.yml` created
- [ ] `production-validation.yml` refactored (all 3 jobs)
- [ ] `release.yml` refactored

**Success Criteria**: 56 lines eliminated, workflows pass manual trigger test.

---

### Phase 3: Create Shared Validation Module (Script DRY)

**Objective**: Extract 90-120 lines of duplicated validation logic to reusable module.

**Tasks**:

1. Create `src/gapless_crypto_clickhouse/validation/__init__.py` (package marker)
2. Create `src/gapless_crypto_clickhouse/validation/e2e_core.py`:
   - `create_clickhouse_client(host, port, username, password, secure=True)` → clickhouse_connect.get_client wrapper
   - `validate_table_exists(client, table_name)` → SHOW TABLES verification
   - `insert_test_data(client, table_name, test_df)` → client.insert_df wrapper with error handling
   - `query_with_final(client, table_name, test_symbol)` → SELECT with FINAL query
   - `cleanup_test_data(client, table_name, test_symbol)` → DELETE cleanup
   - `log_with_timestamp(message)` → UTC timestamp logging
3. Add type hints and docstrings to all functions
4. Add `py.typed` marker if not already present

**Deliverables**:

- [ ] `src/gapless_crypto_clickhouse/validation/__init__.py` created
- [ ] `src/gapless_crypto_clickhouse/validation/e2e_core.py` created (6 functions)
- [ ] Type hints added
- [ ] Docstrings added

**Success Criteria**: Module importable, functions callable, type-safe.

---

### Phase 4: Refactor Validation Scripts

**Objective**: Update validation scripts to use shared module, eliminating duplication.

**Tasks**:

1. Refactor `scripts/validate_e2e_simple.py`:
   - Import functions from `gapless_crypto_clickhouse.validation.e2e_core`
   - Replace duplicated ClickHouse client creation
   - Replace duplicated insert/query/cleanup logic
   - Keep script-specific orchestration (3-layer validation structure)
2. Refactor `scripts/validate_clickhouse_cloud.py`:
   - Import functions from `gapless_crypto_clickhouse.validation.e2e_core`
   - Replace duplicated ClickHouse client creation
   - Replace duplicated insert/query/cleanup logic
   - Keep production-specific validation (schema checks, ORDER BY verification, deduplication tests)

**Deliverables**:

- [ ] `validate_e2e_simple.py` refactored
- [ ] `validate_clickhouse_cloud.py` refactored
- [ ] PEP 723 dependencies updated (add `gapless-crypto-clickhouse` if needed)

**Success Criteria**: Scripts run successfully locally with Doppler credentials, 90-120 lines eliminated.

---

### Phase 5: Update Documentation

**Objective**: Update documentation to reflect 2-workflow architecture and composite actions.

**Tasks**:

1. Update `CLAUDE.md`:
   - Remove `e2e-validation.yml` references
   - Document 2-workflow architecture (Release + Production Validation)
   - Add note about composite actions
2. Check `docs/validation/` for e2e-validation.yml references
3. Update README if needed

**Deliverables**:

- [ ] `CLAUDE.md` updated
- [ ] Validation docs checked
- [ ] README checked

**Success Criteria**: No broken documentation links, accurate workflow count.

---

### Phase 6: Testing & Validation

**Objective**: Verify all changes work correctly before committing.

**Tasks**:

1. Test composite actions:
   - Trigger `production-validation.yml` manually via workflow_dispatch
   - Verify all 3 jobs pass (ClickHouse Cloud, Binance CDN, Simplified E2E)
   - Check job logs for composite action execution
2. Test refactored scripts locally:
   - Run `doppler run --project aws-credentials --config prd -- uv run scripts/validate_e2e_simple.py`
   - Run `doppler run --project aws-credentials --config prd -- uv run scripts/validate_clickhouse_cloud.py`
   - Verify no import errors, validation passes
3. Test release workflow (dry-run if possible)

**Deliverables**:

- [ ] Production validation workflow passes (manual trigger)
- [ ] Refactored scripts pass local execution
- [ ] No import errors or type errors

**Success Criteria**: All workflows pass, all scripts execute successfully, no errors.

---

### Phase 7: Commit & Release

**Objective**: Commit changes with conventional commit format, trigger semantic-release.

**Tasks**:

1. Stage changes in logical groups:
   - Group 1: ADR + plan documents
   - Group 2: Composite actions + workflow updates
   - Group 3: Validation module + script refactoring
   - Group 4: Delete e2e-validation.yml + documentation
2. Create commits:
   - `docs(adr-0036): create CI/CD DRY refactoring decision + plan`
   - `refactor(ci): create composite actions for setup steps`
   - `refactor(validation): extract shared logic to e2e_core module`
   - `refactor(ci): delete redundant e2e-validation.yml workflow`
3. Push to main → trigger semantic-release (minor version bump)

**Deliverables**:

- [ ] Commits created with conventional format
- [ ] Pushed to main branch
- [ ] Semantic-release triggered

**Success Criteria**: CHANGELOG.md updated, version tagged, GitHub release created.

---

## (b) Context

### Problem Statement

Post-ADR-0035 implementation, CI/CD infrastructure accumulated duplication:

1. **Broken Workflow**: `e2e-validation.yml` has 100% failure rate (2025-11-20 onwards)
2. **Setup Duplication**: Python + UV setup repeated 4×, Doppler setup repeated 2×
3. **Script Duplication**: 90-120 lines of shared ClickHouse validation logic

**Investigation Evidence**:
- 3-agent parallel analysis (2025-01-24) identified redundancy across workflows and scripts
- `e2e-validation.yml` scheduled trigger disabled (commented out), suggesting abandonment
- Workflow violates ADR-0035 policy (runs ruff/mypy static analysis)
- Redundant with `simplified-e2e-validation` job in `production-validation.yml`

### Architecture Context

**Current State**:

- **Workflows**: 3 total
  1. `release.yml`: Semantic versioning (working)
  2. `production-validation.yml`: Infrastructure monitoring (working after ADR-0035 fixes)
  3. `e2e-validation.yml`: Comprehensive Playwright validation (broken, unmaintained)
- **Duplication**: 56 workflow lines, 90-120 script lines
- **Policy Violation**: `e2e-validation.yml` runs static analysis in CI/CD

**Target State**:

- **Workflows**: 2 total
  1. `release.yml`: Semantic versioning (refactored with composite actions)
  2. `production-validation.yml`: Infrastructure monitoring (refactored with composite actions)
- **Composite Actions**: 2 new (setup-python-uv, setup-doppler)
- **Validation Module**: 1 new (`e2e_core.py` with 6 reusable functions)
- **Duplication**: 0 workflow lines, 0 script lines

### Research Findings

**Multi-Agent Investigation** (2025-01-24):

**Agent 1: E2E Workflow Analysis**
- Found: `e2e-validation.yml` has 100% failure rate (5 consecutive runs failed)
- Found: Workflow redundant with `simplified-e2e-validation` job
- Found: Violates ADR-0035 (runs `scripts/run_validation.py --e2e-only` which includes ruff/mypy)
- Recommendation: DELETE

**Agent 2: Workflow Inventory**
- Found: Exactly 3 workflows (Release, Production Validation, E2E Validation)
- Found: All workflows aligned with ADR-0035 except `e2e-validation.yml`
- Found: `production-validation.yml` already provides E2E validation via simplified approach

**Agent 3: DRY Analysis**
- Found: 56 lines of workflow duplication (Python + UV setup × 4, Doppler setup × 2)
- Found: 90-120 lines of script duplication (ClickHouse client creation, insert/query/cleanup)
- Recommendation: Composite actions + shared module

### Trade-offs Analysis

| Aspect                    | Status Quo            | Reusable Workflows    | Composite Actions + Module (SELECTED) |
| ------------------------- | --------------------- | --------------------- | ------------------------------------- |
| **DRY Compliance**        | ❌ 28% duplication    | ✅ 0% duplication     | ✅ 0% duplication                     |
| **Complexity**            | ✅ Simple             | ❌ High (limitations) | ⚠️ Medium (one level indirection)     |
| **Debuggability**         | ✅ Direct             | ❌ Indirect           | ⚠️ Slightly indirect                  |
| **Maintainability**       | ❌ 3× bug replication | ✅ Single fix         | ✅ Single fix                         |
| **PEP 723 Self-Contain**  | ✅ Full               | ✅ Full               | ⚠️ Module import required             |
| **Implementation Effort** | ✅ None               | ❌ High (8-10 hours)  | ⚠️ Medium (3-4 hours)                 |

---

## (c) Task List

### Phase 1: Delete Redundant E2E Workflow

- [ ] Delete `.github/workflows/e2e-validation.yml`
- [ ] Grep for references in documentation
- [ ] Update CLAUDE.md if referenced

### Phase 2: Create Composite Actions

- [ ] Create `.github/actions/setup-python-uv/action.yml`
  - [ ] Add Python 3.12 setup step
  - [ ] Add UV installation with caching
  - [ ] Add metadata (name, description, branding)
- [ ] Create `.github/actions/setup-doppler/action.yml`
  - [ ] Add Doppler CLI installation step
  - [ ] Add metadata
- [ ] Update `production-validation.yml`
  - [ ] Refactor `clickhouse-cloud-validation` job (remove lines 27-36)
  - [ ] Refactor `binance-cdn-availability` job (remove lines 58-67)
  - [ ] Refactor `simplified-e2e-validation` job (remove lines 84-95)
- [ ] Update `release.yml`
  - [ ] Refactor UV setup (lines 30-33)

### Phase 3: Create Validation Module

- [ ] Create `src/gapless_crypto_clickhouse/validation/__init__.py`
- [ ] Create `src/gapless_crypto_clickhouse/validation/e2e_core.py`
  - [ ] Add `create_clickhouse_client()` function
  - [ ] Add `validate_table_exists()` function
  - [ ] Add `insert_test_data()` function
  - [ ] Add `query_with_final()` function
  - [ ] Add `cleanup_test_data()` function
  - [ ] Add `log_with_timestamp()` function
  - [ ] Add type hints to all functions
  - [ ] Add docstrings to all functions

### Phase 4: Refactor Scripts

- [ ] Refactor `scripts/validate_e2e_simple.py`
  - [ ] Add import from e2e_core
  - [ ] Replace ClickHouse client creation
  - [ ] Replace insert logic
  - [ ] Replace query logic
  - [ ] Replace cleanup logic
  - [ ] Update PEP 723 dependencies
- [ ] Refactor `scripts/validate_clickhouse_cloud.py`
  - [ ] Add import from e2e_core
  - [ ] Replace ClickHouse client creation
  - [ ] Replace insert logic (2 locations: initial + duplicate)
  - [ ] Replace query logic
  - [ ] Replace cleanup logic
  - [ ] Update PEP 723 dependencies

### Phase 5: Update Documentation

- [ ] Update `CLAUDE.md`
  - [ ] Remove e2e-validation.yml references
  - [ ] Document 2-workflow architecture
  - [ ] Add composite actions note
- [ ] Check `docs/validation/` for references
- [ ] Check README for references

### Phase 6: Testing

- [ ] Test production-validation.yml manually
  - [ ] Trigger via workflow_dispatch
  - [ ] Verify all 3 jobs pass
  - [ ] Check logs for composite action execution
- [ ] Test validate_e2e_simple.py locally
  - [ ] Run with Doppler credentials
  - [ ] Verify no import errors
  - [ ] Verify validation passes
- [ ] Test validate_clickhouse_cloud.py locally
  - [ ] Run with Doppler credentials
  - [ ] Verify no import errors
  - [ ] Verify validation passes

### Phase 7: Commit & Release

- [ ] Stage ADR + plan
- [ ] Commit: `docs(adr-0036): create CI/CD DRY refactoring decision + plan`
- [ ] Stage composite actions + workflow updates
- [ ] Commit: `refactor(ci): create composite actions for setup steps`
- [ ] Stage validation module + script refactoring
- [ ] Commit: `refactor(validation): extract shared logic to e2e_core module`
- [ ] Stage e2e-validation.yml deletion + documentation
- [ ] Commit: `refactor(ci): delete redundant e2e-validation.yml workflow`
- [ ] Push to main
- [ ] Monitor semantic-release

---

## Progress Log

### 2025-01-24 [Initial Planning]

- Created ADR-0036 (CI/CD Workflow DRY Refactoring)
- Created implementation plan (Google Design Doc format)
- 3-agent investigation completed (E2E workflow analysis, inventory, DRY analysis)
- Decision: Composite actions + shared module approach
- Target: 2-workflow architecture, 146-176 lines eliminated

---

## Open Issues

None currently.

---

## Dependencies

- Doppler credentials (for local script testing)
- ClickHouse Cloud availability (for validation testing)
- GitHub Actions secrets (DOPPLER_TOKEN already configured)

---

## References

- ADR-0036: CI/CD Workflow DRY Refactoring
- ADR-0035: CI/CD Production Validation Policy (foundational policy)
- ADR-0027: Local-Only PyPI Publishing (workflow policy precedent)
- GitHub Actions Composite Actions: https://docs.github.com/en/actions/creating-actions/creating-a-composite-action
- 3-agent investigation reports (2025-01-24)
