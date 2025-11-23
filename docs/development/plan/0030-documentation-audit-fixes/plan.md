# Implementation Plan: Documentation Audit Immediate Fixes

**ADR**: [0030-documentation-cleanup-deferred](../../../architecture/decisions/0030-documentation-cleanup-deferred.md)
**Created**: 2025-11-22
**Status**: In Progress

## Objective

Fix critical documentation issues discovered in comprehensive audit while deferring comprehensive package name cleanup to next sprint.

## Background

Multi-agent documentation audit (6 parallel agents, DCTL methodology) across 129 files revealed:

- **Docstrings**: 9.5/10 (2 minor issues)
- **Technical accuracy**: 7/10 (3 inconsistencies)
- **Package identity in code**: 9.5/10 (1 config issue - mypy)
- **Package identity in docs**: 7.5/10 (15 instances - DEFERRED to ADR-0030 Phase 2)

**User Decisions** (from clarification loop):

1. Timeframe count: Update to 16 everywhere
2. Package names: Create ADR-0030, defer to next sprint
3. CLI docs: Remove entirely (package never had CLI)
4. Broken links: Extract and reorganize content
5. Symbol count: Keep '400+' as approximate
6. Hardcoded versions: probe.py import **version**, models.py keep independent + document

## Plan

### Phase 1: Immediate Critical Fixes

**Scope**: Fix incorrect information causing user errors

1. **Update Timeframe Count** (13→16)
   - Files: CLAUDE.md, README.md, **init**.py, DATA_FORMAT.md
   - Change: "13 timeframes" → "16 timeframes (13 standard: 1s-1d + 3 exotic: 3d, 1w, 1mo)"
   - Rationale: Implementation has 16, docs claim 13 (discovered by Technical Accuracy agent)

2. **Fix probe.py Hardcoded Version**
   - File: src/gapless_crypto_clickhouse/probe.py:51
   - Change: `"version": "6.0.0"` → `"version": __version__`
   - Add import: `from . import __version__`
   - Rationale: Version drift (package is v8.0.0, probe claims v6.0.0)

3. **Document models.py Validator Version**
   - File: src/gapless_crypto_clickhouse/validation/models.py:58
   - Add comprehensive docstring explaining independent versioning
   - Rationale: Database schema version, not package version (keep independent per deep dive analysis)

4. **Remove CLI Documentation**
   - File: docs/guides/DATA_COLLECTION.md
   - Remove: Lines 63-132 (entire CLI usage section)
   - Rationale: Package never had CLI (confirmed in README.md:139, **probe**.py fixed in ADR-0029)

5. **Create Missing Documentation Files**
   - CORE_COMPONENTS.md: Extract from docs/architecture/OVERVIEW.md
   - network.md: Extract from CLAUDE.md network architecture section
   - GAP_FILLING.md: Create stub with TODO

### Phase 2: Deferred to Next Sprint (ADR-0030)

**Scope**: Comprehensive package name cleanup (15 instances)

- CONTRIBUTING.md (4 instances)
- docs/README.md (2 instances)
- docs/CLICKHOUSE_MIGRATION.md (1 instance)
- docs/guides/python-api.md (4 instances)
- AGENTS.md (2 instances)
- Automated validation suite

**Target**: Next planning cycle (est. 2025-12-01)

## Context

### Files Changed (Phase 1 Only)

**Documentation** (7 files):

- CLAUDE.md (timeframe count)
- README.md (timeframe count)
- docs/architecture/DATA_FORMAT.md (timeframe count)
- docs/guides/DATA_COLLECTION.md (remove CLI section)
- docs/architecture/CORE_COMPONENTS.md (new file - extracted)
- docs/architecture/network.md (new file - extracted)
- docs/guides/GAP_FILLING.md (new file - stub)

**Source Code** (2 files):

- src/gapless_crypto_clickhouse/**init**.py (timeframe count)
- src/gapless_crypto_clickhouse/probe.py (fix hardcoded version)
- src/gapless_crypto_clickhouse/validation/models.py (add documentation)

**Total**: 9 files modified + 3 files created

### Audit Summary by Agent

1. **Docstring Standards Auditor**: Excellent quality (9.5/10), found 2 hardcoded versions
2. **Technical Accuracy Verifier**: Found timeframe count mismatch (13 vs 16)
3. **Cross-Reference Checker**: Found 3 broken links (missing docs files)
4. **Example Code Validator**: Created validation script (not executed per user preference)
5. **Package Identity Auditor**: Found mypy config issue + 15 markdown instances (deferred)
6. **Markdown Documentation Auditor**: Confirmed CLI docs incorrect + broken links

### Decision Rationale

**Fix Now** (Phase 1):

- Incorrect technical claims (timeframes)
- Version drift (probe.py)
- Non-existent CLI documentation
- Broken navigation links

**Defer** (Phase 2 - ADR-0030):

- Package name inconsistencies where code is correct
- Comprehensive validation suite
- Quality improvements (timestamps, TOC, formatting)

**Key Principle**: Fix errors, defer cleanup

### SLOs

- **Correctness**: 100% technical accuracy in user-facing docs
- **Availability**: No broken internal links
- **Maintainability**: Clear version management documentation
- **Observability**: Audit findings documented, next steps clear

## Task List

**Status**: 0/11 tasks complete (0%)

### Implementation Tasks

- [ ] **Task 1**: Update CLAUDE.md timeframe count (line 9)
- [ ] **Task 2**: Update README.md timeframe count (line 41)
- [ ] **Task 3**: Update **init**.py timeframe count (line 16)
- [ ] **Task 4**: Update DATA_FORMAT.md timeframe count (lines 57-72)
- [ ] **Task 5**: Fix probe.py hardcoded version (import **version**)
- [ ] **Task 6**: Document models.py validator_version independence
- [ ] **Task 7**: Remove DATA_COLLECTION.md CLI section (lines 63-132)
- [ ] **Task 8**: Create CORE_COMPONENTS.md (extract from OVERVIEW.md)
- [ ] **Task 9**: Create network.md (extract from CLAUDE.md)
- [ ] **Task 10**: Create GAP_FILLING.md stub
- [ ] **Task 11**: Run validation (grep checks, build test)

### Release Tasks

- [ ] **Task 12**: Commit with conventional commit (docs: or fix:)
- [ ] **Task 13**: Push and trigger semantic-release (should NOT bump major - docs only)
- [ ] **Task 14**: Verify release notes mention audit completion

## Progress Log

**2025-11-22 [TIME]** - Created ADR-0030 and implementation plan
**2025-11-22 [TIME]** - Starting Phase 1 immediate fixes

## Risks and Mitigations

**Risk**: Deferred cleanup forgotten
**Mitigation**: ADR-0030 documents commitment, GitHub issue to track

**Risk**: More documentation issues discovered during Phase 1
**Mitigation**: Audit covered 129 files comprehensively, findings documented

**Risk**: Tests fail due to documentation changes
**Mitigation**: Changes are docs-only, no code logic changes

## Success Criteria

- [ ] Timeframe count accurate everywhere (16, not 13)
- [ ] probe.py reports correct package version (**version**)
- [ ] models.py validator_version clearly documented as independent
- [ ] DATA_COLLECTION.md has zero CLI references
- [ ] All internal doc links valid (no 404s)
- [ ] ADR-0030 Phase 2 scheduled for next sprint

## Validation Checks

```bash
# Timeframe count updated
grep -r "13 timeframes" docs/ CLAUDE.md README.md src/  # Should return 0

# probe.py uses __version__
grep '"version":' src/gapless_crypto_clickhouse/probe.py  # Should show __version__, not "6.0.0"

# CLI references removed
grep -i "uv run gapless-crypto" docs/guides/DATA_COLLECTION.md  # Should return 0

# Links valid
ls docs/architecture/CORE_COMPONENTS.md  # Should exist
ls docs/architecture/network.md  # Should exist
ls docs/guides/GAP_FILLING.md  # Should exist
```
