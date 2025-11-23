# ADR-0031: Comprehensive Validation from Clean Slate

**Status**: Accepted

**Date**: 2025-01-22

**Deciders**: Development Team

**Context**: Follow-up to ADR-0030 and ADR-0029

## Context and Problem Statement

After completing ADR-0029 (package name alignment) and ADR-0030 (documentation cleanup), we need to validate from clean slate that all systems are working correctly. The 6-agent parallel audit identified critical discrepancies between documentation and implementation that require systematic verification and fixes.

## Decision Drivers

- **Correctness**: Documentation must accurately reflect implementation
- **Observability**: Users must see correct version numbers and feature counts
- **Maintainability**: Type checking and validation tools must work
- **User Trust**: Examples and API documentation must be executable

## Considered Options

1. **Manual spot checks** - Quick but incomplete
2. **Automated validation only** - Fast but misses semantic issues
3. **Hybrid approach with fixes** - Thorough validation followed by immediate remediation (CHOSEN)

## Decision Outcome

Chosen option: **Hybrid approach with immediate fixes**

Execute comprehensive validation covering:

1. Code compilation and imports
2. Test suite execution
3. Documentation accuracy (versions, counts, API surface)
4. Example code functionality

Then immediately fix all CRITICAL and HIGH priority issues found.

### Positive Consequences

- **Single source of truth verified**: All version numbers, counts, and claims validated against implementation
- **Type checking works**: Mypy configuration corrected
- **User confidence**: Examples and docs proven to work
- **Baseline established**: Future changes validated against this baseline

### Negative Consequences

- **Time investment**: ~60 minutes for full validation + fixes
- **Potential test failures**: May expose integration test issues (ClickHouse availability, Python 3.14 compatibility)

## Validation Strategy

### Phase 1: Automated Foundation (10 min)

- Environment health check
- Static analysis (ruff, mypy)
- Package import validation
- Validation scripts (validate_examples.py, verify_cross_references.py)

### Phase 2: Test Suite (15 min)

- Unit tests (fast, isolated)
- Integration tests (requires ClickHouse)
- Full suite with coverage
- Example script compilation

### Phase 3: Ground Truth Verification (20 min)

- Version consistency across all files
- Timeframe count (documentation vs implementation)
- Symbol count (documentation vs implementation)
- Package name consistency (mypy config)
- API surface discovery

### Phase 4: Fixes (15 min)

Apply fixes for:

- **CRITICAL #1**: Version mismatch (**init**.py 1.0.0 → 8.0.0)
- **CRITICAL #2**: Timeframe constants (add 3d, 1w, 1mo OR update docs to 13)
- **CRITICAL #3**: Mypy config (gapless_crypto_data → gapless_crypto_clickhouse)
- **HIGH #4**: Symbol count (400+ → 713 in docs)

## Implementation

See: `docs/development/plan/0031-comprehensive-validation/plan.md`

## Links

- Supersedes: ADR-0030 (documentation cleanup deferred)
- Related: ADR-0029 (package name alignment)
- Implementation Plan: `docs/development/plan/0031-comprehensive-validation/plan.md`
- Validation Scripts: `validate_examples.py`, `verify_cross_references.py`
