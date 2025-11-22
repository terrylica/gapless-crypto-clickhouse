# ADR-0029: Docstring and Package Reference Alignment

## Status

Accepted

## Context

Schema audit revealed 29 instances of outdated or incorrect package references across the codebase:

1. **Wrong Package Name** (13 instances): Docstrings reference `gapless-crypto-data` instead of `gapless-crypto-clickhouse`
2. **Outdated Versions** (6 instances): Version strings reference v3.2.0, v4.0.0, v6.0.0 instead of current v7.1.0
3. **Invalid CLI References** (6 instances): `__probe__.py` references CLI entry points that never existed in this package
4. **Inconsistent Cache Paths** (4 instances): Cache directories use parent package name

### Root Cause

This package was forked from `gapless-crypto-data` and migrated to ClickHouse architecture. During migration:

- Module docstrings were copied without updating package references
- Version numbers became stale as features evolved
- CLI probe metadata was copied despite this package being API-only
- Cache directory paths retained parent package name

### Impact

**Correctness**: Misleading documentation confuses users about package identity and capabilities
**Observability**: Incorrect version numbers prevent accurate feature tracking
**Maintainability**: Stale references create technical debt and confusion

### Affected Files

**Schema and ClickHouse modules** (5 files):

- `clickhouse/schema.sql` - Header references gapless-crypto-data v4.0.0
- `clickhouse/config.py` - Docstring references gapless-crypto-data v4.0.0
- `clickhouse/__init__.py` - Docstring references gapless-crypto-data v4.0.0
- `clickhouse/connection.py` - References v6.0.0 (outdated)
- `clickhouse_query.py` - References gapless-crypto-data v4.0.0

**Core modules** (5 files):

- `api.py` - Docstring and get_info() name field
- `exceptions.py` - Docstring header
- `resume/__init__.py` - Docstring header
- `utils/__init__.py` - Docstring header
- `utils/error_handling.py` - Docstring header

**Probe metadata** (1 file):

- `__probe__.py` - Invalid CLI references (lines 50, 281-286)

**Cache paths** (2 files):

- `utils/etag_cache.py` - ~/.cache/gapless-crypto-data/
- `validation/storage.py` - ~/.cache/gapless-crypto-data/

## Decision

**Standardize all package references to `gapless-crypto-clickhouse` with current version v7.1.0.**

### Option 1: Global Find-Replace with Version Strings (REJECTED)

**Approach**: Replace all instances of gapless-crypto-data → gapless-crypto-clickhouse, update all version strings to v7.1.0

**Pros**: Fast, comprehensive
**Cons**:

- Version numbers become stale again immediately after next release
- Violates DRY principle (version in multiple places)
- High maintenance burden

### Option 2: Remove Version Strings, Keep Package Name (SELECTED)

**Approach**:

- Replace package name: gapless-crypto-data → gapless-crypto-clickhouse
- Remove explicit version strings from docstrings (use **version** dynamically where needed)
- Fix CLI references in **probe**.py (document API-only interface)
- Update cache directory paths to gapless-crypto-clickhouse (breaking change with migration)

**Pros**:

- Single source of truth for version (**version** in **init**.py)
- No future staleness issues
- Clear package identity
- Prevents copy-paste errors

**Cons**:

- Breaking change for cache directory migration
- Requires users to clear old cache or migrate manually

**Justification**:

- Docstrings should describe WHAT and WHY, not version history
- Version tracking belongs in CHANGELOG.md and git tags (semantic-release)
- Cache directory should match actual package name to avoid conflicts

### Option 3: Hybrid Approach (REJECTED)

**Approach**: Keep version strings but automate updates via semantic-release hooks

**Pros**: Explicit version visibility
**Cons**: Adds complexity, still violates DRY, requires custom tooling

## Implementation

### Phase 1: Package Name Corrections

Replace all `gapless-crypto-data` → `gapless-crypto-clickhouse` in:

- Module docstrings
- Schema comments
- Error messages
- Cache directory paths

### Phase 2: Version String Removal

Remove explicit version numbers from docstrings in:

- clickhouse/schema.sql (remove v4.0.0, keep ADR-0021 reference to v3.2.0+ for historical context)
- clickhouse/config.py
- clickhouse/**init**.py
- clickhouse/connection.py
- clickhouse_query.py

### Phase 3: CLI Reference Cleanup

Fix **probe**.py to document API-only interface:

- Remove invalid CLI entry_point references
- Remove CLI uv_usage examples
- Document correct Python API usage patterns

### Phase 4: Cache Directory Migration

**Breaking Change**: Update cache paths from `~/.cache/gapless-crypto-data/` to `~/.cache/gapless-crypto-clickhouse/`

**Migration Strategy**:

- Update code to use new path
- Document breaking change in CHANGELOG.md
- Provide migration note: users should clear old cache or copy manually
- Rationale: Prevents conflicts if both packages installed, aligns with actual package name

## Consequences

### Positive

- **Correctness**: Accurate package identity in all documentation
- **Maintainability**: No version staleness (single source of truth)
- **Observability**: Clear separation from parent package
- **DRY Compliance**: Version managed in one place (**version**)

### Negative

- **Breaking Change**: Cache directory path changes require user action
- **Migration Effort**: Users must clear/migrate cache manually
- **Documentation Debt**: Need clear migration notes in CHANGELOG

### Neutral

- Version information still available via `__version__` attribute
- Historical ADR references (e.g., "v3.2.0+" in context) preserved

## Validation

### Automated Checks

```bash
# Verify no gapless-crypto-data references (except intentional migration docs)
grep -r "gapless-crypto-data" src/gapless_crypto_clickhouse/ | grep -v "__init__.py" | grep -v "CHANGELOG"

# Verify no stale version strings in docstrings
grep -r "v[0-9]\.[0-9]\.[0-9]" src/gapless_crypto_clickhouse/ | grep -v "__version__" | grep -v "ADR-"

# Verify cache directory updated
grep -r "\.cache/gapless-crypto-data" src/gapless_crypto_clickhouse/
```

### Manual Review

- [ ] Schema docstring accurate
- [ ] **probe**.py reflects API-only interface
- [ ] Cache directory paths updated
- [ ] CHANGELOG.md documents breaking change
- [ ] Tests pass

## References

- Schema audit report (2025-01-21)
- ADR-0027: Local-Only PyPI Publishing
- ADR-0028: Skills and Documentation Alignment
- Parent package: https://github.com/terrylica/gapless-crypto-data

## Notes

**Cache Directory Breaking Change**: Users upgrading from v7.1.0 to v8.0.0 will need to:

```bash
# Option 1: Clear old cache
rm -rf ~/.cache/gapless-crypto-data/

# Option 2: Migrate cache manually
mv ~/.cache/gapless-crypto-data/ ~/.cache/gapless-crypto-clickhouse/
```

This is acceptable because:

1. Cache is ephemeral (can be regenerated)
2. Most users won't have existing cache
3. Prevents conflicts between packages
4. Aligns with actual package identity
