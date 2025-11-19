# ADR-0006: v4.0.0 Audit Remediation

## Status

Implemented (2025-11-17)

## Context

### Problem Statement

Comprehensive pre-release audit of main-clickhouse branch (v4.0.0) identified 6 issues blocking or affecting release quality:

**Critical (Release Blocking)**:
- Version inconsistency between pyproject.toml (4.0.0) and `__init__.py` (3.3.0)

**Medium Priority (Documentation)**:
- CLI deprecation notice uses future tense ("will be removed") but CLI already removed
- CLAUDE.md references outdated version (v2.5.0 instead of 4.0.0)
- README project structure diagrams reference removed cli.py file

**Low Priority (User Experience)**:
- Expected test failures (CLI tests) not documented in migration guide
- CLAUDE.md multi-agent methodology incorrectly references "QuestDB v4.0.0 migration"

### Current State

**Branch**: main-clickhouse (ClickHouse-only, QuestDB removed)

**Version**: 4.0.0 declared in pyproject.toml, but runtime `__version__` returns 3.3.0

**Impact**:
- PyPI package metadata will show 4.0.0, but programmatic version checks return 3.3.0
- Users checking version at runtime will see wrong version
- Semantic release automation may fail
- Documentation inconsistencies confuse users

**Audit Results** (10 dimensions):
```
✅ Code Quality & Correctness: PASS
⚠️ Documentation Completeness: PARTIAL (3 issues)
✅ Breaking Changes Documentation: PASS
✅ Dependencies & Configuration: PASS
✅ Git History & Commits: PASS
⚠️ ADR-Plan-Code Synchronization: PARTIAL (1 issue)
✅ Package Build & Distribution: PASS
✅ Migration Path Validation: PASS
⚠️ Test Coverage: WARNING (1 issue)
⚠️ Missing Pieces & Inconsistencies: CRITICAL (1 issue)
```

**Release Gate**: ❌ NO-GO due to critical version mismatch

## Decision

**Remediate all 6 audit findings with individual atomic commits** to ensure clean v4.0.0 release.

### Remediation Strategy

**Commit Strategy**: One commit per issue (6 commits total)
- Rationale: Granular git history, easier to review, simpler to revert individual fixes if needed

**Fix Priority**: Critical → Medium → Low (in sequence)
- Ensures release-blocking issue fixed first
- Documentation issues addressed before low-priority UX improvements

**Validation Suite**: Version check + Package rebuild + Ruff linting
- Ensures no regressions introduced by fixes
- Confirms runtime behavior matches package metadata

## Implementation

### Fix 1: Version Mismatch (CRITICAL)

**File**: `src/gapless_crypto_data/__init__.py:79`

**Change**:
```python
# Before
__version__ = "3.3.0"

# After
__version__ = "4.0.0"
```

**Rationale**: Runtime version attribute must match pyproject.toml version for:
- Semantic release automation compatibility
- User version checks via `gcd.__version__`
- PyPI package metadata consistency

**Validation**:
```python
import gapless_crypto_data as gcd
assert gcd.__version__ == "4.0.0"
```

### Fix 2: CLI Deprecation Notice (MEDIUM)

**File**: `README.md:91-94`

**Change**:
```markdown
# Before
### CLI Usage (⚠️ Deprecated - Will be removed in v4.0.0)
> **Deprecation Notice**: The CLI interface is deprecated and will be removed in v4.0.0.

# After
### CLI Removed in v4.0.0
> **Breaking Change**: The CLI interface was removed in v4.0.0.
```

**Rationale**: CLI already removed (pyproject.toml:53 removed `[project.scripts]`), but README used future tense implying it still exists.

### Fix 3: CLAUDE.md Version Update (MEDIUM)

**File**: `CLAUDE.md:77`

**Change**:
```markdown
# Before
**Version**: v2.5.0 (validation v3.3.0+ with DuckDB persistence)

# After
**Version**: v4.0.0 (ClickHouse database with optional file-based workflows)
```

**Rationale**: AI agents using CLAUDE.md need correct version context for accurate assistance.

### Fix 4: README Project Structure Cleanup (MEDIUM)

**Files**: `README.md:780,807`

**Change**: Remove 2 lines referencing cli.py:
- Line 780: `│   ├── cli.py                   # Command-line interface`
- Line 807: `├── cli.py                      # CLI interface`

**Rationale**: CLI file removed but still shown in project structure diagrams, causing confusion.

### Fix 5: Document Expected Test Failures (LOW)

**File**: `docs/MIGRATION_v3_to_v4.md` (add after line 303)

**Change**: Add new section:
```markdown
### Expected Test Failures in v4.0.0

After upgrading to v4.0.0, the following tests are expected to fail due to CLI removal:

**Failing Test Files**:
- `tests/test_cli.py` - Entire file (CLI removed in v4.0.0)
- `tests/test_cli_integration.py` - CLI integration tests

**Action Required**:
- For maintainers: Remove these test files in a follow-up PR
- For users: These failures are expected and can be ignored

**Workaround**: Run tests with: `pytest tests/ --ignore=tests/test_cli.py --ignore=tests/test_cli_integration.py`
```

**Rationale**: Prevents user confusion when CI/CD pipelines show expected CLI test failures.

### Fix 6: CLAUDE.md Multi-Agent Reference (LOW)

**File**: `CLAUDE.md:38`

**Change**:
```markdown
# Before
**Multi-Agent Methodologies** - Extracted from production use (QuestDB v4.0.0 migration):

# After
**Multi-Agent Methodologies** - Extracted from production use (ClickHouse v4.0.0 migration):
```

**Rationale**: Corrects database reference to match current v4.0.0 architecture (ClickHouse, not QuestDB).

## Validation

### Automated Validation Suite

**Version Verification**:
```bash
uv run python -c "import gapless_crypto_data as gcd; assert gcd.__version__ == '4.0.0'"
```
**Expected**: Exit code 0 (assertion passes)

**Package Build**:
```bash
uv build
```
**Expected**: Successfully built dist/gapless_crypto_data-4.0.0.tar.gz and .whl

**Linting**:
```bash
uv run ruff check src/
```
**Expected**: All checks passed (zero warnings)

**Pre-commit Hooks**:
```bash
git commit (auto-triggers hooks)
```
**Expected**: ruff, end-of-file-fixer, yaml-check, commitizen all pass

### Manual Review Checklist

- [ ] All 6 commits follow conventional commits format
- [ ] Breaking change properly marked in Fix 1 commit (version update)
- [ ] Documentation changes accurate and complete
- [ ] No regressions introduced (package still builds, imports work)
- [ ] Git history clean (no merge conflicts, logical commits)

## Consequences

### Positive

- **Release Unblocked**: Critical version mismatch resolved
- **Documentation Accuracy**: All outdated references corrected
- **User Experience**: Clear migration path with expected test failures documented
- **Clean Git History**: 6 atomic commits, easy to review and revert if needed
- **Validated Quality**: Automated checks confirm no regressions

### Negative

- **Commit Volume**: 6 commits for relatively minor fixes (could have been 1 atomic commit)
- **No Functional Changes**: All fixes are metadata/documentation-only (no new features)

### Neutral

- **Release Readiness**: After fixes, v4.0.0 ready for tag/release/publish
- **Test Suite**: CLI tests still fail (expected, documented in migration guide)

## Alternatives Considered

### Alternative 1: Single Atomic Commit (Rejected)

**Pros**: Simpler git history, one revert if needed

**Cons**: Harder to review, loses granularity for cherry-picking specific fixes

**Verdict**: Rejected per user preference for granular commit history

### Alternative 2: Fix Critical Only, Defer Others (Rejected)

**Pros**: Fastest path to release (5 minutes)

**Cons**: Documentation inconsistencies remain, user confusion likely

**Verdict**: Rejected per user preference to fix all issues

### Alternative 3: Batch by Priority (Critical, Medium, Low) (Rejected)

**Pros**: Balanced granularity vs simplicity (3 commits instead of 6)

**Cons**: Less granular than per-issue commits

**Verdict**: Rejected per user preference for maximum granularity

## Compliance

- **Error Handling**: All fixes are static file edits, no runtime error handling required
- **SLOs**:
  - Availability: No impact (documentation-only changes)
  - Correctness: ✅ Version attribute now correct
  - Observability: ✅ Users can accurately check version at runtime
  - Maintainability: ✅ Documentation accurate, easier to maintain
- **OSS Preference**: Uses uv (OSS) for validation, ruff (OSS) for linting
- **Auto-Validation**: Automated suite runs after all fixes (version, build, ruff)
- **Semantic Release**: Conventional commits enable automated changelog generation

## References

- Audit Report: Comprehensive 10-dimension analysis (internal)
- Previous ADRs: ADR-0005 (ClickHouse Migration)
- Plan: `docs/plan/0006-v4-audit-remediation/plan.yaml`
