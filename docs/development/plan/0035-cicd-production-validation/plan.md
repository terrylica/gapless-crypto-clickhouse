# Plan: CI/CD Production Validation Policy Implementation

**ADR ID**: 0035
**Status**: In Progress
**Start Date**: 2025-01-22
**Owner**: Engineering Team

---

## (a) Plan

### Phase 1: Remove Unit Tests/Linting from CI/CD

**Objective**: Align with local-first development policy by removing code quality checks from GitHub Actions.

**Tasks**:
1. Delete `.github/workflows/ci.yml` (test-fast, test-e2e, benchmark jobs)
2. Verify `.github/workflows/release.yml` remains unchanged (semantic-release only)

**Deliverables**:
- [ ] `.github/workflows/ci.yml` deleted
- [ ] No unit tests, linting, or formatting checks in GitHub Actions

**Success Criteria**: GitHub Actions only runs semantic-release workflow on main branch pushes.

---

### Phase 2: Create Production Validation Workflow

**Objective**: Add scheduled monitoring for ClickHouse Cloud AWS and Binance CDN infrastructure.

**Tasks**:
1. Create `.github/workflows/production-validation.yml` with 3 jobs:
   - `clickhouse-cloud-validation`: Schema + write/read round-trip
   - `binance-cdn-availability`: HTTP HEAD request to CloudFront
   - `simplified-e2e-validation`: 3-layer checks (environment → data flow → query)
2. Configure Doppler credentials access via GitHub Actions secrets
3. Set cron trigger: `0 */6 * * *` (every 6 hours)

**Deliverables**:
- [ ] `.github/workflows/production-validation.yml` created
- [ ] Doppler token configured in GitHub Actions secrets
- [ ] Workflow triggered manually to verify functionality

**Success Criteria**: Workflow runs successfully every 6 hours, validates ClickHouse Cloud connectivity and schema correctness.

---

### Phase 3: Create Validation Scripts

**Objective**: Implement production validation logic as PEP 723 self-contained scripts.

**Tasks**:
1. Create `scripts/validate_clickhouse_cloud.py`:
   - Schema validation via `deploy-clickhouse-schema.py --dry-run`
   - ORDER BY verification: `(symbol, timeframe, toStartOfHour(timestamp), timestamp)`
   - Write/read round-trip: Insert 100 BTCUSDT 1h bars → query with FINAL → verify deduplication
   - Cleanup test data after validation
2. Create `scripts/validate_binance_cdn.py`:
   - HTTP HEAD request to Binance Public Data Repository
   - 5s timeout, exit code 0/1 for success/failure

**Deliverables**:
- [ ] `scripts/validate_clickhouse_cloud.py` created and tested locally
- [ ] `scripts/validate_binance_cdn.py` created and tested locally
- [ ] Both scripts executable via `uv run scripts/<script>.py`

**Success Criteria**: Scripts run successfully locally and in CI/CD, exit with correct status codes.

---

### Phase 4: Update Documentation

**Objective**: Document policy exception and developer workflow changes.

**Tasks**:
1. Update project `CLAUDE.md`:
   - Add "CI/CD Production Validation" section
   - Document scheduled monitoring (every 6 hours)
   - List validation checks (ClickHouse Cloud, Binance CDN)
2. Update global `~/.claude/CLAUDE.md`:
   - Add "Production Validation Exception" to GitHub Actions policy
   - Document rationale (production credentials unavailable locally)
3. Update `docs/development/COMMANDS.md`:
   - Add local validation workflow (before commit/push)
   - Document manual production validation commands

**Deliverables**:
- [ ] `CLAUDE.md` updated with CI/CD section
- [ ] `~/.claude/CLAUDE.md` updated with policy exception
- [ ] `docs/development/COMMANDS.md` updated with validation workflow

**Success Criteria**: Documentation clearly explains policy exception and developer responsibilities.

---

### Phase 5: Commit and Release

**Objective**: Create semantic-release commit with BREAKING CHANGE marker (CI/CD workflow deletion).

**Tasks**:
1. Stage all changes (ADR, plan, workflows, scripts, docs)
2. Create commit with conventional commit format:
   ```
   feat!: implement CI/CD production validation policy

   BREAKING CHANGE: Removed unit tests/linting from GitHub Actions

   - Delete .github/workflows/ci.yml (unit tests, linting, E2E)
   - Create .github/workflows/production-validation.yml (scheduled monitoring)
   - Add scripts/validate_clickhouse_cloud.py (schema + round-trip)
   - Add scripts/validate_binance_cdn.py (CDN availability)
   - Update CLAUDE.md with policy exception

   Developers must now run tests locally before commit:
   - uv run ruff check .
   - uv run pytest -v --cov=src

   Production validation runs every 6 hours (ClickHouse Cloud + Binance CDN).

   References: ADR-0035
   ```
3. Push to main branch to trigger semantic-release

**Deliverables**:
- [ ] Commit created with BREAKING CHANGE marker
- [ ] Pushed to main branch
- [ ] semantic-release creates v10.0.0 (major version bump)

**Success Criteria**: GitHub Actions creates release tag, updates CHANGELOG.md, no errors.

---

## (b) Context

### Problem Statement

The workspace enforces local-first development (no unit tests/linting in CI/CD), but production infrastructure validation requires:

1. **ClickHouse Cloud AWS**: Production credentials (Doppler `aws-credentials/prd`) unavailable locally
2. **Schema deployment**: Must verify ORDER BY optimization from ADR-0034 in production
3. **Binance CDN**: External service health monitoring (22x performance advantage)
4. **Scheduled monitoring**: Independent of code changes, detects infrastructure degradation

### Architecture Context

**Current State**:
- `.github/workflows/ci.yml`: Runs pytest, ruff, E2E tests (VIOLATES workspace policy)
- `.github/workflows/release.yml`: Semantic-release only (COMPLIANT)
- ClickHouse Cloud: Manual deployment via `scripts/deploy-clickhouse-schema.py`
- No scheduled monitoring for external services

**Target State**:
- `.github/workflows/ci.yml`: DELETED
- `.github/workflows/production-validation.yml`: Scheduled every 6 hours
- `.github/workflows/release.yml`: UNCHANGED
- Developers: Run tests locally before commit (5-30s feedback)
- CI/CD: Production validation only (ClickHouse Cloud + Binance CDN)

### Policy Evolution

**Workspace Policy (Global `~/.claude/CLAUDE.md`)**:
- Original: "NO testing in GitHub Actions" (strict local-only)
- Updated: "NO development testing in GitHub Actions, production validation allowed"

**Rationale**:
- Development testing (unit, linting): Fast local feedback (5-30s vs 2-5min CI/CD)
- Production validation: Requires credentials/infrastructure unavailable locally
- Scheduled monitoring: Independent of code changes, detects external degradation

### Research Findings

**Multi-Agent Investigation** (2025-01-22):
- 4 parallel agents analyzed CI/CD, validation coverage, requirements, gaps
- Discovered: `.github/workflows/ci.yml` violates workspace policy (5 violations)
- Discovered: No automated ClickHouse Cloud validation exists
- Discovered: Multi-agent E2E validation workflows are manual-only
- Discovered: Performance benchmarks are informational (don't fail CI)

### Trade-offs Analysis

| Aspect | Local-Only (Option 1) | Full CI/CD (Option 2) | Hybrid (SELECTED) |
|--------|----------------------|----------------------|-------------------|
| **Development Speed** | ✅ Fast (5-30s) | ❌ Slow (2-5min) | ✅ Fast (5-30s) |
| **Production Monitoring** | ❌ Manual | ✅ Automated | ✅ Automated |
| **Developer Discipline** | ❌ High (manual checks) | ✅ Low (CI enforces) | ⚠️ Medium (local checks) |
| **Policy Consistency** | ✅ Strict adherence | ❌ Violates policy | ⚠️ Exception documented |
| **CI/CD Costs** | ✅ Minimal (release only) | ❌ High (every commit) | ⚠️ Medium (scheduled) |

---

## (c) Task List

### Phase 1: Remove Unit Tests/Linting from CI/CD
- [x] Read `.github/workflows/ci.yml` to understand current implementation
- [x] Verify `.github/workflows/release.yml` is compliant (semantic-release only)
- [ ] Delete `.github/workflows/ci.yml`
- [ ] Verify no other workflows run unit tests/linting

### Phase 2: Create Production Validation Workflow
- [ ] Create `.github/workflows/production-validation.yml` skeleton
- [ ] Implement `clickhouse-cloud-validation` job
  - [ ] Configure Doppler token access
  - [ ] Call `scripts/validate_clickhouse_cloud.py`
  - [ ] Handle failure notifications
- [ ] Implement `binance-cdn-availability` job
  - [ ] Call `scripts/validate_binance_cdn.py`
  - [ ] Handle failure notifications
- [ ] Implement `simplified-e2e-validation` job
  - [ ] Environment check (ClickHouse Cloud connection)
  - [ ] Data flow check (write test data)
  - [ ] Query check (read with FINAL)
- [ ] Configure cron trigger: `0 */6 * * *`
- [ ] Add Doppler token to GitHub Actions secrets
- [ ] Test workflow manually via workflow_dispatch

### Phase 3: Create Validation Scripts
- [ ] Create `scripts/validate_clickhouse_cloud.py`
  - [ ] Add PEP 723 inline dependencies
  - [ ] Implement schema validation (dry-run mode)
  - [ ] Implement ORDER BY verification
  - [ ] Implement write/read round-trip (100 BTCUSDT 1h bars)
  - [ ] Implement FINAL deduplication check
  - [ ] Implement cleanup logic
  - [ ] Add exit code handling (0 success, 1 failure)
  - [ ] Test locally with Doppler credentials
- [ ] Create `scripts/validate_binance_cdn.py`
  - [ ] Add PEP 723 inline dependencies
  - [ ] Implement HTTP HEAD request
  - [ ] Add 5s timeout
  - [ ] Add exit code handling
  - [ ] Test locally

### Phase 4: Update Documentation
- [ ] Update `CLAUDE.md`
  - [ ] Add "CI/CD Production Validation" section
  - [ ] Document scheduled monitoring frequency
  - [ ] List validation checks performed
  - [ ] Add workflow reference
- [ ] Update `~/.claude/CLAUDE.md`
  - [ ] Add "Production Validation Exception" section
  - [ ] Document rationale
  - [ ] Update policy constraints
- [ ] Update `docs/development/COMMANDS.md`
  - [ ] Add local validation workflow
  - [ ] Document before-commit checks
  - [ ] Document manual production validation

### Phase 5: Commit and Release
- [ ] Stage all changes
- [ ] Create commit with BREAKING CHANGE marker
- [ ] Push to main branch
- [ ] Monitor semantic-release workflow
- [ ] Verify v10.0.0 release created
- [ ] Verify CHANGELOG.md updated

---

## Progress Log

### 2025-01-22 [Initial Planning]
- Created ADR-0035 (CI/CD Production Validation Policy)
- Created implementation plan (Google Design Doc format)
- Multi-agent investigation completed (4 parallel agents)
- Policy clarifications obtained via iterative Q&A
- Decision: Hybrid approach (local-first development + production validation)

---

## Open Issues

None currently.

---

## Dependencies

- Doppler token access in GitHub Actions (requires repository secret configuration)
- ClickHouse Cloud credentials (Doppler `aws-credentials/prd`)
- Binance Public Data Repository URL (CloudFront CDN endpoint)

---

## References

- ADR-0035: CI/CD Production Validation Policy
- ADR-0027: Local-Only PyPI Publishing (workspace policy foundation)
- ADR-0034: Schema Optimization for Prop Trading (ORDER BY validation requirement)
- Global `~/.claude/CLAUDE.md`: GitHub Actions policy
- Multi-agent investigation reports (2025-01-22)
