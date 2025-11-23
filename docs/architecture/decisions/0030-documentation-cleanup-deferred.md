# ADR-0030: Documentation Cleanup (Deferred to Next Sprint)

## Status

Accepted - Implementation Deferred

## Context

Comprehensive documentation audit (2025-11-22) revealed **15 instances** of outdated package name references in markdown files that were missed during ADR-0029 implementation:

**Files Affected**:

- `CONTRIBUTING.md` (4 instances): `gapless-crypto-data` → `gapless-crypto-clickhouse`
- `docs/README.md` (2 instances): Title and package description
- `docs/CLICKHOUSE_MIGRATION.md` (1 instance): Package name in header
- `docs/guides/python-api.md` (3 instances): Package references + 1 cache path
- `docs/guides/DATA_COLLECTION.md` (context-dependent): CLI references to non-existent CLI
- `AGENTS.md` (2 instances): Module paths `gapless_crypto_data` → `gapless_crypto_clickhouse`

**Root Cause**: ADR-0029 focused on Python source code cleanup. Markdown documentation files were not systematically updated.

**Current State**:

- ✅ Python code: 100% aligned with `gapless-crypto-clickhouse` identity
- ⚠️ Markdown docs: ~85% aligned (15 instances requiring fixes)
- ✅ Critical user docs: README.md, CLAUDE.md, CHANGELOG.md all correct

## Decision

**Defer comprehensive documentation cleanup to dedicated sprint work** rather than rush fixes immediately after v8.0.0 release.

### Rationale

**Why Defer**:

1. **Just shipped v8.0.0**: Package released 2025-11-22 with ADR-0029 breaking changes
2. **Code is correct**: All Python source properly references `gapless-crypto-clickhouse`
3. **Critical docs correct**: README.md (root), CLAUDE.md, CHANGELOG.md all accurate
4. **Proper planning**: Documentation sweep deserves ADR + plan + review cycle
5. **Avoid rush fixes**: Post-release fixes often introduce new errors

**Why Not Defer**:

- User-facing docs like CONTRIBUTING.md have wrong package name
- New contributors following CONTRIBUTING.md will clone wrong repository
- Developer tooling docs (AGENTS.md) reference wrong module paths

**Compromise**:

- Fix **critical user-facing** issues immediately (addressed in separate commits)
- Defer **comprehensive documentation sweep** to this ADR's implementation

## Implementation Plan

### Phase 1: Immediate Fixes (Not Deferred)

Handled separately from this ADR:

- ✅ Remove CLI documentation from DATA_COLLECTION.md (package never had CLI)
- ✅ Update timeframe count 13→16 across docs
- ✅ Fix probe.py hardcoded version (import **version**)
- ✅ Create missing documentation files (CORE_COMPONENTS.md, network.md, GAP_FILLING.md)

### Phase 2: Comprehensive Documentation Sweep (This ADR - Deferred)

**Target Sprint**: Next planning cycle (est. 2025-12-01)

**Scope**:

1. **Package Name Cleanup** (15 instances):
   - CONTRIBUTING.md: Replace git clone URL, package references
   - docs/README.md: Update title and intro
   - docs/CLICKHOUSE_MIGRATION.md: Update package name
   - docs/guides/python-api.md: Update package references and cache path
   - AGENTS.md: Update module paths for coverage and testing

2. **Validation**:
   - Run automated link checker on all markdown files
   - Verify all code examples are executable
   - Check all cross-references point to existing files
   - Validate external links (GitHub, PyPI, Binance)

3. **Quality Improvements**:
   - Add timestamps to frequently updated docs
   - Improve table of contents in longer docs
   - Standardize code block formatting
   - Add missing examples where identified

**Acceptance Criteria**:

- Zero grep matches for `gapless-crypto-data` in markdown (except migration notes)
- All internal links validated
- All code examples tested
- Documentation audit score: 10/10

## Consequences

### Positive

- **Quality over speed**: Proper planning prevents rushed errors
- **Focus**: Separates immediate fixes from comprehensive cleanup
- **Post-release stability**: Avoids documentation churn immediately after major release
- **Better scope**: Allows time to discover other documentation issues

### Negative

- **Temporary inconsistency**: Some docs reference wrong package name until Phase 2
- **New contributor confusion**: CONTRIBUTING.md has wrong clone URL temporarily
- **Manual workaround needed**: Users must mentally translate `gapless-crypto-data` → `gapless-crypto-clickhouse`

### Mitigation

**Immediate fixes** (not deferred):

1. Add banner to CONTRIBUTING.md: "⚠️ Documentation update in progress. Use `gapless-crypto-clickhouse` package name."
2. Ensure README.md (most visible) is 100% accurate (already done)
3. Fix DATA_COLLECTION.md CLI references (removes most confusing docs)

**Tracking**:

- Create GitHub issue linking to ADR-0030
- Add to next sprint planning
- Set reminder for 2025-12-01 review

## References

- **ADR-0029**: Docstring and Package Version Alignment (2025-11-22)
- **Audit Report**: `/Users/terryli/eon/gapless-crypto-clickhouse/CROSS_REFERENCE_REPORT.md`
- **Parent Issue**: Documentation consistency post-v8.0.0 release

## Timeline

- **Created**: 2025-11-22 (post-v8.0.0 release)
- **Target Implementation**: 2025-12-01 (next sprint)
- **Status**: Deferred (not blocked, just planned)

## Notes

This is a **process ADR** documenting a conscious decision to defer work, not reject it. The documentation cleanup is valuable and will be completed, but not rushed immediately after a major release.

**Immediate vs Deferred Criteria**:

- **Immediate**: Incorrect information causing user errors (CLI docs, timeframes)
- **Deferred**: Package name inconsistencies where code is correct and README is accurate
