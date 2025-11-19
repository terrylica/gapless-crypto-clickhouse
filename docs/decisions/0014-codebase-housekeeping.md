# Codebase Housekeeping: Documentation Accuracy and Artifact Cleanup

**Status**: Accepted
**Date**: 2025-11-19
**Decision Makers**: System Architecture Team
**Technical Story**: [Housekeeping investigation revealed critical documentation inaccuracies and 366KB+ temporary artifacts]

## Context and Problem Statement

Multi-agent investigation (4 parallel sub-agents using Dynamic Todo List Creation) identified critical issues across 4 dimensions:
1. **Documentation Accuracy**: 7 discrepancies (v4.0.0 fiction, package name errors)
2. **Temporary Files**: 38 files (25 DELETE, 12 ARCHIVE) from ClickHouse migration
3. **File Organization**: Test structure 85%+ quality (minor improvements)
4. **Root Documentation**: Critical version/CLI inconsistencies

**Core Problem**: Users expect v4.0.0 features (don't exist), believe CLI was removed (never existed), and think ClickHouse is optional (core feature).

## Decision Drivers

* **Correctness**: Documentation must match codebase reality
* **Observability**: Historical artifacts should be preserved, not deleted
* **Maintainability**: Remove obsolete temporary files blocking navigation
* **Availability**: Accurate instructions prevent user confusion

## Considered Options

### Option 1: Comprehensive Housekeeping (Conservative)
Delete obvious temporaries, archive historical docs, fix critical documentation errors

### Option 2: Documentation-Only Fix
Fix docs without file cleanup

### Option 3: Aggressive Cleanup
Delete all tmp/ files including historical records

## Decision Outcome

**Chosen**: Option 1 (Comprehensive Housekeeping - Conservative)

**Rationale**:
- Balances cleanup with historical preservation
- Fixes user-facing errors immediately (P0)
- Archives completed work products (E2E migration, validation reports)
- Maintains investigation artifacts for future reference

### Consequences

**Good**:
- Users get accurate documentation (no v4.0.0 confusion)
- tmp/ directory reduced by ~366KB (25 files deleted)
- Historical context preserved in tmp/archive/
- Test organization validated (85%+ quality, no changes needed)

**Bad**:
- Requires updates across 13 documentation files
- Manual version investigation needed (semantic-release not updating pyproject.toml)

**Neutral**:
- Test file renames marked optional (low priority)
- Archive creation adds directory structure

## Validation

**Automated Checks**:
1. Verify all v4.0.0 references removed
2. Confirm pytest-playwright → pytest-playwright-asyncio updates
3. Validate archive directory structure
4. Check file cleanup completed (25 files deleted)

**Manual Review**:
1. README.md accuracy (version claims, database positioning)
2. pyproject.toml version sync with git tags
3. Archive README completeness

## Pros and Cons of the Options

### Option 1: Comprehensive Housekeeping (Conservative)

* ✅ Fixes critical user-facing errors
* ✅ Preserves historical context
* ✅ Reduces tmp/ clutter significantly
* ❌ Requires 13 file updates
* ❌ Manual version investigation

### Option 2: Documentation-Only Fix

* ✅ Faster execution (fewer files)
* ✅ No risk of losing artifacts
* ❌ tmp/ remains cluttered
* ❌ Doesn't address file organization

### Option 3: Aggressive Cleanup

* ✅ Maximum cleanup (all tmp/ removed)
* ✅ Simplest execution
* ❌ Loses historical investigation records
* ❌ No audit trail for E2E migration debugging

## More Information

**Investigation Methodology**: Dynamic Todo List Creation (DCTL) with 4 parallel sub-agents
- Documentation Accuracy Investigator: 6 TLIs executed
- Temporary Files Auditor: 5 TLIs executed
- File Organization Analyst: 4 TLIs executed
- Root Documentation Validator: 5 TLIs executed

**Key Findings**:
- v4.0.0 never existed (latest: v2.1.2)
- CLI never existed in this package (fork started without CLI)
- ClickHouse is core feature, not optional
- E2E validation framework complete but under-documented

**References**:
- Investigation reports in tmp/ (to be archived)
- Git history shows v1.0.0 → v2.1.2 progression
- pyproject.toml version = "1.0.0" (requires sync)
