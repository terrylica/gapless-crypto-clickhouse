# Implementation Plan: Docstring and Package Version Alignment

**ADR**: [0029-docstring-package-version-alignment](../../../architecture/decisions/0029-docstring-package-version-alignment.md)
**Created**: 2025-01-21
**Status**: In Progress

## Objective

Correct 29 instances of outdated package references and version strings across the codebase to ensure accurate documentation and clear package identity.

## Background

Schema audit revealed systematic staleness in docstrings and package references:

- **13 instances**: Wrong package name (gapless-crypto-data → gapless-crypto-clickhouse)
- **6 instances**: Outdated version strings (v3.2.0, v4.0.0, v6.0.0)
- **6 instances**: Invalid CLI references in **probe**.py (package is API-only)
- **4 instances**: Inconsistent cache directory paths

**Root Cause**: Fork from gapless-crypto-data without systematic reference updates

**Impact**:

- Correctness: Misleading user-facing documentation
- Maintainability: Version staleness and technical debt
- Observability: Unclear package boundaries

## Plan

### Phase 1: Schema and ClickHouse Modules (5 files)

**Files**:

1. `clickhouse/schema.sql` - Fix header comment
2. `clickhouse/config.py` - Fix module docstring
3. `clickhouse/__init__.py` - Fix module docstring
4. `clickhouse/connection.py` - Fix module docstring
5. `clickhouse_query.py` - Fix module docstring

**Changes**:

- Replace: `gapless-crypto-data` → `gapless-crypto-clickhouse`
- Remove: Explicit version strings (v4.0.0, v6.0.0)
- Preserve: ADR references with historical context (e.g., "ADR-0021, v3.2.0+")

### Phase 2: Core Modules (5 files)

**Files**:

1. `api.py` - Fix docstring + get_info() return value
2. `exceptions.py` - Fix module docstring
3. `resume/__init__.py` - Fix module docstring
4. `utils/__init__.py` - Fix module docstring
5. `utils/error_handling.py` - Fix module docstring

**Changes**:

- Replace: `gapless-crypto-data` → `gapless-crypto-clickhouse`
- Fix: `api.py:955` name field in get_info() function

### Phase 3: Probe Metadata Cleanup (1 file)

**File**: `__probe__.py`

**Changes**:

- Remove: Lines 281-286 (invalid CLI references)
- Update: Line 50 package name
- Replace: CLI examples with API usage patterns

**Rationale**: This package never had a CLI (machine interface only)

### Phase 4: Cache Directory Migration (2 files)

**Files**:

1. `utils/etag_cache.py` - Lines 14, 68
2. `validation/storage.py` - Lines 12, 65, 67

**Changes**:

- Replace: `~/.cache/gapless-crypto-data/` → `~/.cache/gapless-crypto-clickhouse/`

**Breaking Change**: Users must clear or migrate cache manually

### Phase 5: Validation

**Automated Checks**:

```bash
# No stray package name references (except migration docs)
grep -r "gapless-crypto-data" src/ | grep -v "__init__.py" | grep -v "migration"

# No stale version strings
grep -r "v[0-9]\.[0-9]" src/ | grep -v "__version__" | grep -v "ADR-"

# Cache paths updated
grep -r "\.cache/gapless-crypto-data" src/
```

**Tests**:

```bash
uv run pytest -xvs  # All tests must pass
```

### Phase 6: Documentation

Update CHANGELOG.md with breaking change note:

```markdown
## [8.0.0] - YYYY-MM-DD

### BREAKING CHANGES

- **Cache Directory**: Moved from `~/.cache/gapless-crypto-data/` to `~/.cache/gapless-crypto-clickhouse/`
  - Users must clear old cache: `rm -rf ~/.cache/gapless-crypto-data/`
  - Or migrate manually: `mv ~/.cache/gapless-crypto-data/ ~/.cache/gapless-crypto-clickhouse/`
```

## Context

### Files Changed (Total: 13)

**Schema/ClickHouse** (5):

- clickhouse/schema.sql
- clickhouse/config.py
- clickhouse/**init**.py
- clickhouse/connection.py
- clickhouse_query.py

**Core Modules** (5):

- api.py
- exceptions.py
- resume/**init**.py
- utils/**init**.py
- utils/error_handling.py

**Metadata/Cache** (3):

- **probe**.py
- utils/etag_cache.py
- validation/storage.py

### Decision Rationale

**Remove Version Strings**: Version numbers in docstrings violate DRY and become stale. Single source of truth: `__version__` in `__init__.py`.

**Update Cache Paths**: Prevents conflicts if both gapless-crypto-data and gapless-crypto-clickhouse installed. Cache is ephemeral and can be regenerated.

**Fix Probe Metadata**: This package never had a CLI (unlike parent gapless-crypto-data). Probe should reflect API-only interface.

### SLOs

- **Correctness**: 100% accurate package references
- **Maintainability**: Zero version staleness (no hardcoded versions)
- **Observability**: Clear package boundaries via correct naming
- **Availability**: No functional regression (tests pass)

## Task List

**Status**: 0/11 tasks complete (0%)

### Implementation Tasks

- [ ] **Task 1**: Fix schema.sql header (package name, remove version)
- [ ] **Task 2**: Fix clickhouse/config.py docstring
- [ ] **Task 3**: Fix clickhouse/**init**.py docstring
- [ ] **Task 4**: Fix clickhouse/connection.py docstring
- [ ] **Task 5**: Fix clickhouse_query.py docstring
- [ ] **Task 6**: Fix api.py docstring + get_info() name field
- [ ] **Task 7**: Fix exceptions.py, resume/**init**.py, utils/**init**.py, utils/error_handling.py
- [ ] **Task 8**: Fix **probe**.py CLI references
- [ ] **Task 9**: Update cache directory paths (etag_cache.py, storage.py)
- [ ] **Task 10**: Run validation checks (grep + tests)
- [ ] **Task 11**: Update CHANGELOG.md with breaking change note

### Release Tasks

- [ ] **Task 12**: Commit with conventional commit (fix!: or feat!: for breaking change)
- [ ] **Task 13**: Push and trigger semantic-release (bump to v8.0.0)
- [ ] **Task 14**: Publish to PyPI using pypi-doppler skill

## Progress Log

**2025-01-21 18:29:56** - Created ADR-0029 and implementation plan
**2025-01-21 18:30:xx** - Starting Phase 1 (Schema and ClickHouse modules)

## Risks and Mitigations

**Risk**: Cache migration breaks existing workflows
**Mitigation**: Document clearly in CHANGELOG, cache is regenerable

**Risk**: Tests fail due to cache path changes
**Mitigation**: Run full test suite, update fixtures if needed

**Risk**: Users confused by version bump (v7.1.0 → v8.0.0)
**Mitigation**: Clear CHANGELOG entry explaining breaking change scope

## Success Criteria

- [ ] Zero grep matches for "gapless-crypto-data" (except **init**.py migration notes)
- [ ] Zero grep matches for stale version strings (v3.x, v4.x, v6.x)
- [ ] All tests pass (uv run pytest)
- [ ] CHANGELOG.md documents breaking change
- [ ] Released as v8.0.0 (major bump for cache path change)
