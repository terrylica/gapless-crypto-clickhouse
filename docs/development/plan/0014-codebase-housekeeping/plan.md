# Implementation Plan: Codebase Housekeeping

**adr-id**: 0014
**Status**: In Progress
**Created**: 2025-11-19
**Updated**: 2025-11-19

## Objective

Restore documentation accuracy and clean temporary artifacts following ClickHouse migration (v1.0.0 → v2.1.2) and E2E validation framework implementation (ADR-0013).

**SLOs**:

- **Correctness**: 100% of documentation matches codebase reality
- **Observability**: Historical artifacts preserved in archive with context
- **Maintainability**: tmp/ directory reduced to active files only
- **Availability**: Users receive accurate setup/usage instructions

## Background

4-agent parallel investigation (DCTL methodology) revealed:

- **Critical P0**: v4.0.0 references (version never existed)
- **Critical P0**: CLI "removed" claims (CLI never existed in this fork)
- **Critical P0**: Database positioned as "optional" (core required feature)
- **High P1**: pytest-playwright package name (should be pytest-playwright-asyncio)
- **Medium P1**: Missing session-scoped event loop documentation
- **Low P2**: 25 temporary files obsolete (366KB+)
- **Low P2**: 12 historical docs need archival

## Overview

Execute 4-phase housekeeping with conservative approach:

**Phase 1 (P0)**: Fix critical user-facing errors in README.md, pyproject.toml
**Phase 2 (P1)**: Update documentation accuracy (pytest-playwright-asyncio, markers)
**Phase 3 (P2)**: Prune temporary files, archive historical documentation
**Phase 4 (P3)**: Minor improvements (CLAUDE.md, docker-compose.yml, ADR-0013)

## Detailed Design

### Phase 1: Critical Fixes (P0)

#### 1.1 Remove v4.0.0 Fiction (README.md)

**Intent**: Eliminate non-existent version references causing user confusion

**Current State**:

- Line 125-154: "CLI Removed in v4.0.0" section
- Line 210: "v4.0.0+ ClickHouse database support"
- Reality: v4.0.0 never existed (latest: v2.1.2)

**Changes**:

`````markdown
# Remove entire section (lines 125-154)

### CLI Removed in v4.0.0

> **Breaking Change**: The CLI interface was removed in v4.0.0.
> ...

# Update version reference (line 210)

- **v4.0.0+**: ClickHouse database support...

* **v1.0.0+**: ClickHouse database support...

# Add clarification note

- **Note**: This package never included a CLI (unlike parent package `gapless-crypto-data`). It provides a Python API only.

`````text

**Validation**: Search README.md for "v4.0" → 0 results

#### 1.2 Fix Database Positioning (README.md)

**Intent**: Correct core value proposition (database-first, not optional)

**Current State**:

- Line 64: "optionally set up ClickHouse"
- Line 208: "Database Integration (**Optional**)"
- Reality: `clickhouse-driver` is required dependency

**Changes**:

```markdown
# Line 64

- For persistent storage and advanced query capabilities, you can **optionally** set up ClickHouse

* For persistent storage and advanced query capabilities, set up ClickHouse

# Line 208

- ## 🗄️ Database Integration (**Optional**)

* ## 🗄️ Database Integration

# Add emphasis

- ClickHouse is a **required component** for this package. The database-first architecture enables advanced query capabilities and persistent storage.
```bash

**Validation**: README.md no longer claims ClickHouse is optional

#### 1.3 Update pyproject.toml Metadata

**Intent**: Sync version with git tags, remove v4.0.0 comment

**Investigation Needed**:

- pyproject.toml shows `version = "1.0.0"`
- Git tags show v2.1.2 as latest
- Semantic-release not updating pyproject.toml (root cause unknown)

**Changes**:

```toml
# Line 3 - INVESTIGATE FIRST, then update if needed
version = "1.0.0"  # May need manual sync with git tags

# Line 53 - Remove v4.0.0 fiction
- # [project.scripts] section removed in v4.0.0
+ # No CLI - machine interface only (use Python API for programmatic access)
```bash

**Validation**:

1. Check semantic-release configuration for pyproject.toml update behavior
2. Verify version matches latest git tag OR document intentional pinning
3. Confirm no v4.0.0 references remain

### Phase 2: Documentation Accuracy (P1)

#### 2.1 Fix Package Name (5 files)

**Intent**: Update pytest-playwright → pytest-playwright-asyncio throughout docs

**Files**:

1. `docs/validation/E2E_TESTING_GUIDE.md:264`
2. `docs/architecture/decisions/0013-autonomous-validation-framework.md:74,110`
3. `docs/development/plan/0013-autonomous-validation-framework/plan.md:79,121`
4. `scripts/run_validation.py:6`

**Changes** (abstraction over implementation):

```markdown
# E2E_TESTING_GUIDE.md line 264

- pytest-playwright handles it

* pytest-playwright-asyncio handles it

# ADR-0013 line 74

- Native Python integration (pytest-playwright)

* Native Python integration (pytest-playwright-asyncio)

# ADR-0013 line 110

- Auto-installs: playwright, pytest, pytest-playwright, pytest-cov

* Auto-installs: playwright, pytest, pytest-playwright-asyncio, pytest-asyncio>=0.26.0, pytest-cov
```text

```python
# scripts/run_validation.py line 6
- "pytest-playwright>=0.6.0",
+ "pytest-playwright-asyncio>=0.7.1",
```bash

**Validation**: `grep -r "pytest-playwright[^-]" docs/ scripts/` → 0 results

#### 2.2 Fix E2E Test Marker Examples

**Intent**: Show correct session-scoped async marker syntax

**Files**: `docs/validation/E2E_TESTING_GUIDE.md`

**Changes**:

````markdown
# Line 97 - Update example

@pytest.mark.e2e

- @pytest.mark.asyncio

* @pytest.mark.asyncio(loop_scope="session")
  async def test_example(page: Page, screenshot_dir: Path):

# Line 82 - Update marker table

| Marker | Description                                  |
| ------ | -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| -      | `@pytest.mark.asyncio`                       | Async test execution (required for Playwright)                                               |
| +      | `@pytest.mark.asyncio(loop_scope="session")` | Async test execution with session-scoped event loop (required for pytest-playwright-asyncio) |

# Add new section after line 100

- ### pytest-asyncio Configuration
-
- pytest-playwright-asyncio requires session-scoped event loop configuration:
-
- ```ini
`````
`````

- # pytest.ini
- asyncio_mode = auto
- asyncio_default_fixture_loop_scope = session
- ```

  ```

-
- All E2E tests must use `@pytest.mark.asyncio(loop_scope="session")` to ensure compatibility with Playwright's async fixtures.

`````

**Validation**: All E2E test examples show loop_scope parameter

#### 2.3 Document CH-UI CI Skip Decision

**Intent**: Clarify CI runs ClickHouse Play only, CH-UI tests are local-only

**File**: `docs/validation/E2E_TESTING_GUIDE.md:273-288`

**Changes**:

````markdown
# After line 288, add new section

### CI Test Execution

**CI Scope** (GitHub Actions):

- Runs: `tests/e2e/test_clickhouse_play.py` (6 tests)
- Skips: `tests/e2e/test_ch_ui_dashboard.py` (6 tests)

**Rationale**: CH-UI requires interactive web configuration (not CI-friendly). ClickHouse Play provides sufficient E2E framework validation.

**Local Testing** (full 12-test suite):

```bash
docker-compose up -d
uv run pytest tests/e2e/ -v
```text
`````

See `.github/workflows/ci.yml` lines 131-132 for CI configuration.

````

**Validation**: E2E guide explains CI vs local testing distinction

#### 2.4 Add E2E Commands to COMMANDS.md

**Intent**: Document E2E test execution commands

**File**: `docs/development/COMMANDS.md`

**Changes**:
```markdown
# Add after line 60 (after integration test section)
## E2E Testing

### Run E2E Tests
```bash
# Full E2E suite (requires Docker services)
docker-compose up -d
uv run pytest tests/e2e/ -v

# E2E validation script (PEP 723 bootstrap)
uv run scripts/run_validation.py --e2e-only

# Specific E2E marker
uv run pytest -m e2e -v

# ClickHouse Play only (CI subset)
uv run pytest tests/e2e/test_clickhouse_play.py -v

# With screenshots and tracing
uv run pytest tests/e2e/ -v --screenshot=only-on-failure --tracing=retain-on-failure
````

**Markers**: `@pytest.mark.e2e` - End-to-end tests requiring Playwright and running services

**Services Required**:

- ClickHouse: localhost:8123 (HTTP), localhost:9000 (native)
- CH-UI: localhost:5521 (web interface, local testing only)

````

**Validation**: COMMANDS.md has E2E section with executable examples

### Phase 3: File Cleanup (P2)

#### 3.1 Delete Temporary Files (25 files)

**Intent**: Remove obsolete validation artifacts superseded by production infrastructure

**Directory**: `tmp/`

**DELETE List**:
```bash
# Validation scripts (superseded by scripts/run_validation.py)
tmp/clickhouse_validation.py
tmp/clickhouse_quick_validation.py
tmp/clickhouse_futures_validation.py
tmp/comprehensive_validation.py

# Validation results (one-time outputs)
tmp/clickhouse_validation_results.txt
tmp/clickhouse_futures_validation_results.txt
tmp/comprehensive_validation_report.txt

# Snapshot artifacts (superseded by CI)
tmp/full-validation/test-coverage/coverage.json (121KB)
tmp/full-validation/test-coverage/pytest-output.txt (67KB)
tmp/full-validation/test-coverage/test-inventory.txt
tmp/full-validation/test-coverage/failure-analysis.txt
tmp/full-validation/test-coverage/SUMMARY.txt

# Build metadata (one-time verification)
tmp/full-validation/build-distribution/METADATA.txt (39KB)
tmp/full-validation/build-distribution/wheel-contents.txt
tmp/full-validation/build-distribution/dependencies-check.txt

# Git history snapshots
tmp/full-validation/git-history/commit-details.txt (11KB)
tmp/full-validation/git-history/commit-subjects.txt
tmp/full-validation/git-history/semantic-release-analysis.txt
tmp/full-validation/git-history/conventional-commits-analysis.txt
tmp/full-validation/git-history/adr-plan-sync-analysis.txt

# Code quality snapshots
tmp/full-validation/code-quality/ruff-check.txt
tmp/full-validation/code-quality/ruff-format.txt
tmp/full-validation/code-quality/mypy-check.txt (21KB)
tmp/full-validation/code-quality/pre-commit.txt
````

**Execution**:

````bash
rm tmp/clickhouse_*.py tmp/clickhouse_*_results.txt tmp/comprehensive_*.txt
rm -rf tmp/full-validation/test-coverage/*.{json,txt}
rm -rf tmp/full-validation/build-distribution/*.txt
rm -rf tmp/full-validation/git-history/*.txt
rm -rf tmp/full-validation/code-quality/*.txt
```text

**Validation**: 25 files deleted, ~366KB freed

#### 3.2 Archive Historical Documentation (12 files)

**Intent**: Preserve investigation artifacts with context

**CREATE Archive**:

```bash
mkdir -p tmp/archive/2025-11-clickhouse-migration
```text

**MOVE to Archive**:

```bash
# E2E resolution documentation (CHANGELOG references)
mv tmp/e2e-implementation-status.md tmp/archive/2025-11-clickhouse-migration/
mv tmp/e2e-resolution-complete.md tmp/archive/2025-11-clickhouse-migration/

# ADR-0005 synchronization audit
mv tmp/adr-plan-code-sync-verification.md tmp/archive/2025-11-clickhouse-migration/

# Multi-agent validation reports
mv tmp/full-validation/documentation/validation-report.md tmp/archive/2025-11-clickhouse-migration/documentation-validation.md
mv tmp/full-validation/build-distribution/VALIDATION_REPORT.md tmp/archive/2025-11-clickhouse-migration/build-validation.md
mv tmp/full-validation/code-quality/REPORT.md tmp/archive/2025-11-clickhouse-migration/code-quality-validation.md
mv tmp/full-validation/code-quality/mypy-analysis.md tmp/archive/2025-11-clickhouse-migration/type-checking-analysis.md
mv tmp/full-validation/test-coverage/VALIDATION_REPORT.md tmp/archive/2025-11-clickhouse-migration/test-coverage-validation.md
mv tmp/full-validation/git-history/GIT_HISTORY_VALIDATION_REPORT.md tmp/archive/2025-11-clickhouse-migration/git-history-audit.md

# Research reports (IDE integrations, PyPI packaging)
mv tmp/clickhouse-local-viz-research/ide-integrations/IDE_INTEGRATIONS_REPORT.md tmp/archive/2025-11-clickhouse-migration/ide-integrations-research.md
mv tmp/pypi-package-split/agent1-publishing/INVESTIGATION_REPORT.md tmp/archive/2025-11-clickhouse-migration/pypi-packaging-investigation.md
```text

**CREATE Archive README**:

```markdown
# ClickHouse Migration Archive (2025-11)

Historical documentation from v1.0.0 → v2.1.2 transition period.

## E2E Validation Framework Implementation (ADR-0013)

- `e2e-implementation-status.md`: Problem analysis (7 iteration debugging)
- `e2e-resolution-complete.md`: Resolution documentation (pytest-playwright-asyncio migration)

## ClickHouse Database Migration (ADR-0005)

- `adr-plan-code-sync-verification.md`: Comprehensive synchronization audit

## Multi-Agent Validation Workflow

5-agent parallel validation (Nov 17-19, 2025):

- documentation-validation.md
- build-validation.md
- code-quality-validation.md
- type-checking-analysis.md
- test-coverage-validation.md
- git-history-audit.md

## Research Reports

- ide-integrations-research.md: IDE integration investigation (25KB)
- pypi-packaging-investigation.md: PyPI package split analysis (ADR-0011 "Proposed")

## Context

These artifacts document the ClickHouse fork creation, database-first architecture adoption, and E2E validation framework implementation. Preserved for historical reference and future troubleshooting.
```text

**Validation**: Archive contains 12 files with README context

### Phase 4: Minor Improvements (P3)

#### 4.1 Clarify CLAUDE.md CLI Migration Guide Title

**Intent**: Accurately describe cross-package migration, not version upgrade

**File**: `CLAUDE.md:35`

**Changes**:

```markdown
- - [CLI Migration Guide](docs/development/CLI_MIGRATION_GUIDE.md) - v3.x to v4.0.0 migration (CLI removed)

* - [CLI Migration Guide](docs/development/CLI_MIGRATION_GUIDE.md) - Migrating from gapless-crypto-data (different package)
```text

**Validation**: CLAUDE.md accurately describes CLI_MIGRATION_GUIDE.md purpose

#### 4.2 Update docker-compose.yml ClickHouse Version

**Intent**: Use current stable ClickHouse release (10 months newer)

**File**: `docker-compose.yml:5`

**Changes**:

```yaml
- image: clickhouse/clickhouse-server:24.1-alpine
+ image: clickhouse/clickhouse-server:24.11-alpine
```text

**Rationale**: 24.11 released 2024-11, provides 10 months of improvements over 24.1

**Validation**: docker-compose.yml references current stable ClickHouse

#### 4.3 Add Missing pytest-asyncio to ADR-0013

**Intent**: Complete dependency list in auto-install documentation

**File**: `docs/architecture/decisions/0013-autonomous-validation-framework.md:110`

**Changes**:

```markdown
- Auto-installs: playwright, pytest, pytest-playwright, pytest-cov

* Auto-installs: playwright, pytest, pytest-playwright-asyncio, pytest-asyncio>=0.26.0, pytest-cov
```text

**Validation**: ADR-0013 lists all E2E dependencies

## Implementation Strategy

### Execution Order

1. **Phase 1 (P0)**: Critical fixes first to unblock users immediately
2. **Phase 2 (P1)**: Documentation accuracy ensures correct implementation guidance
3. **Phase 3 (P2)**: File cleanup after docs updated (avoid referencing deleted files)
4. **Phase 4 (P3)**: Minor improvements last (lowest impact)

### Validation Steps

**Automated**:

```bash
# 1. Verify v4.0.0 removed
grep -r "v4\.0\.0" docs/ README.md || echo "✅ v4.0.0 references removed"

# 2. Verify pytest-playwright-asyncio updated
grep -r "pytest-playwright[^-]" docs/ scripts/ && echo "❌ pytest-playwright found" || echo "✅ Package name updated"

# 3. Verify file cleanup
test $(find tmp/ -type f | wc -l) -lt 10 && echo "✅ Temporary files pruned"

# 4. Verify archive created
test -d tmp/archive/2025-11-clickhouse-migration && echo "✅ Archive created"

# 5. Verify archive contents
test $(find tmp/archive/2025-11-clickhouse-migration -type f | wc -l) -eq 13 && echo "✅ Archive has 12 files + README"
````

**Manual Review**:

1. README.md: No v4.0.0, ClickHouse not optional, CLI never existed note added
2. pyproject.toml: Version synced with git tags OR rationale documented
3. E2E_TESTING_GUIDE.md: loop_scope examples, pytest.ini config documented
4. COMMANDS.md: E2E section added with executable examples
5. Archive README: Context explains historical artifacts

### Rollback Plan

**If Issues Found**:

1. Revert commits (git revert)
2. Restore tmp/ files from archive if needed
3. Document issues in ADR-0014 (lessons learned)

**Low Risk**: All changes are documentation + cleanup (no code logic changes)

## Alternatives Considered

### Alternative 1: Documentation-Only Fix

**Rejected**: Leaves tmp/ cluttered with 366KB+ obsolete files

### Alternative 2: Aggressive Cleanup (Delete All tmp/)

**Rejected**: Loses historical E2E investigation records (7-iteration debugging process)

### Alternative 3: Test File Renames

**Deferred**: Current names functional, renames provide marginal benefit (marked LOW priority)

## Risks and Mitigations

| Risk                             | Impact | Likelihood | Mitigation                                      |
| -------------------------------- | ------ | ---------- | ----------------------------------------------- |
| Break documentation links        | Medium | Low        | Validate all internal links after changes       |
| Delete valuable artifacts        | High   | Very Low   | Archive before delete, comprehensive review     |
| pyproject.toml version confusion | Medium | Medium     | Investigate semantic-release, document findings |
| README.md clarity reduced        | Low    | Very Low   | Multiple reviews, focus on accuracy over style  |

## Success Metrics

**Correctness**:

- ✅ 0 v4.0.0 references remain
- ✅ 0 "CLI removed" false claims
- ✅ 0 "ClickHouse optional" incorrect positioning
- ✅ All package names accurate (pytest-playwright-asyncio)

**Observability**:

- ✅ Archive preserves 12 historical docs
- ✅ Archive README provides context

**Maintainability**:

- ✅ tmp/ reduced to active files only (<10 files)
- ✅ 366KB+ freed

**Availability**:

- ✅ Users get accurate setup instructions
- ✅ E2E testing commands documented

## Timeline

**Phase 1 (P0)**: 30 minutes (3 files)
**Phase 2 (P1)**: 45 minutes (5 files + new sections)
**Phase 3 (P2)**: 20 minutes (delete 25, archive 12)
**Phase 4 (P3)**: 15 minutes (3 minor updates)
**Validation**: 15 minutes (automated + manual review)

**Total**: ~2 hours

## References

- ADR-0013: Autonomous Validation Framework (E2E implementation)
- ADR-0005: ClickHouse Database Architecture
- tmp/e2e-implementation-status.md: 7-iteration debugging process
- Investigation reports: 4 parallel sub-agents (DCTL methodology)
