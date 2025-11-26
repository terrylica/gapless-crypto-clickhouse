# ADR-0012: Documentation Accuracy Remediation Post-Fork

## Status

Accepted (2025-11-19)

## Context

### Problem Statement

Comprehensive 5-agent documentation audit (2025-11-19) revealed **systematic accuracy failures** across all documentation categories due to incomplete fork transition from `gapless-crypto-data` to `gapless-crypto-clickhouse`:

**Critical Findings**:

- **100% of Python examples broken** (75/75 examples fail with `ModuleNotFoundError`)
- **121 files** contain incorrect `gapless-crypto-data` references
- **All file paths** in architecture docs point to non-existent locations
- **Version confusion**: Docs reference v3.0.0/v4.0.0 but package is v1.0.0
- **Missing ClickHouse architecture documentation** (primary feature undocumented)

**Agent Investigation Results**:

| Agent               | Focus                       | Critical Issues                           | Accuracy |
| ------------------- | --------------------------- | ----------------------------------------- | -------- |
| Python API Examples | Code-doc alignment          | Package name mismatch in all imports      | 0%       |
| Architecture Claims | Implementation verification | Wrong paths, missing ClickHouse docs      | 60%      |
| CLI Documentation   | Migration guide accuracy    | Obsolete v3→v4 timeline, wrong imports    | 0%       |
| Data Format Spec    | 11-column format validation | Column name discrepancy, timeframe count  | 92%      |
| Validation System   | API/schema verification     | Wrong paths, but API/schema 100% accurate | 67%      |

**Root Cause**: Documentation inherited from parent package (`gapless-crypto-data`) without systematic find-and-replace during ADR-0011 fork implementation.

### Constraints

1. **Correctness SLO**: Documentation must match actual implementation (zero tolerance for broken examples)
2. **Maintainability**: Establish validation to prevent future drift
3. **No backward compatibility**: This is v1.0.0, no legacy migration guides needed
4. **Intent over implementation**: Document abstractions, not code details
5. **Auto-validation**: All fixes must be empirically validated before commit

## Decision

**Implement systematic documentation remediation** with 5-phase execution plan, empirical validation, and automated drift prevention.

### Key Decisions

1. **Global Package Name Correction**: Find-and-replace `gapless_crypto_clickhouse` → `gapless_crypto_clickhouse` across all docs
   - Rationale: Restores 75 broken examples immediately
   - Exception: Cache directory `~/.cache/gapless-crypto-data/` unchanged (intentional)

2. **Architecture Documentation Rewrite**: Add ClickHouse-first architecture section to OVERVIEW.md
   - Rationale: Primary feature (ClickHouse integration) completely undocumented
   - Scope: Document ClickHouseConnection, ClickHouseBulkLoader, schema.sql

3. **CLI Documentation Cleanup**: Delete/rewrite obsolete CLI migration guide
   - Rationale: This fork never had a CLI (inherited docs from parent's v4.0.0 removal)
   - Action: Retitle as "Migrating from gapless-crypto-data to gapless-crypto-clickhouse"

4. **Data Format Clarification**: Document dual column naming (CSV vs database)
   - Rationale: CSV uses `date`, database uses `timestamp` - undocumented conversion
   - Action: Add table showing CSV→DB column mapping

5. **Empirical Validation**: Extract and test 10 representative examples in `/tmp/doc-audit/`
   - Rationale: Ensure fixes work end-to-end before committing
   - Method: `uv run` execution with actual package installation

## Implementation

### Phase 1: Critical Package Name Fixes

**Objective**: Restore 75 broken Python examples

**Scope**:

```bash
# Find-and-replace in documentation
find docs/ examples/ -name "*.md" -o -name "*.py" | \
  xargs sed -i '' 's/gapless_crypto_clickhouse/gapless_crypto_clickhouse/g'

find docs/ -name "*.md" | \
  xargs sed -i '' 's|/gapless-crypto-clickhouse/|/gapless-crypto-clickhouse/|g'
```text

**Files Affected** (15 high-priority):

- `docs/guides/python-api.md` (15 examples)
- `docs/guides/DATA_COLLECTION.md` (9 examples)
- `docs/api/quick-start.md` (6 examples)
- `docs/validation/QUERY_PATTERNS.md` (25 examples)
- `docs/guides/pypi-documentation.md` (20 examples)
- `docs/architecture/OVERVIEW.md` (all paths)
- `docs/validation/OVERVIEW.md` (21 path refs)
- `docs/validation/STORAGE.md` (4 path refs)

**Exception**: Preserve `~/.cache/gapless-crypto-data/` (cache dir intentional)

**Validation**:

```bash
# Zero matches expected (except cache dir and historical ADRs)
grep -r "gapless_crypto_clickhouse" docs/ examples/ | \
  grep -v ".cache/gapless-crypto-data" | \
  grep -v "docs/decisions" | \
  grep -v "CHANGELOG"
```text

### Phase 2: Architecture Documentation Updates

**2.1 Fix Version References**

- `docs/CURRENT_ARCHITECTURE_STATUS.yaml`: v3.0.0 → v1.0.0
- Remove v3.x → v4.0.0 timeline references

**2.2 Add ClickHouse Architecture Section** to `docs/architecture/OVERVIEW.md`:

```markdown
## ClickHouse Integration (Primary Mode)

### Components

- **ClickHouseConnection** (`clickhouse/connection.py`)
- **ClickHouseConfig** (`clickhouse/config.py`)
- **ClickHouseBulkLoader** (`collectors/clickhouse_bulk_loader.py`)

### Schema

- Engine: ReplacingMergeTree with deterministic versioning
- Deduplication: `(_version, _sign)` for idempotent ingestion
- Schema: `clickhouse/schema.sql` (17 columns)
```python

**2.3 Update Network Architecture** in `CLAUDE.md`:

- Document actual httpx+pooling implementation (not just urllib claims)
- Clarify dual download strategy: urllib (monthly/daily) + httpx (concurrent)

**2.4 Remove Obsolete Features** from `CLAUDE.md`:

- Delete joblib, polars, pyod references (removed 2025-01-19)

### Phase 3: CLI Documentation Cleanup

**3.1 Delete Obsolete File**:

- `examples/cli_usage_examples.sh` (135 lines of invalid commands)

**3.2 Rewrite Migration Guide** (`docs/development/CLI_MIGRATION_GUIDE.md`):

- Retitle: "Migrating from gapless-crypto-data to gapless-crypto-clickhouse"
- Fix all imports: `gapless_crypto_clickhouse` → `gapless_crypto_clickhouse`
- Clarify: For **parent package users** migrating to ClickHouse fork
- Remove: v3.x → v4.0.0 timeline (doesn't apply to this fork)

**3.3 Update Source Docstring** (`src/gapless_crypto_clickhouse/__init__.py`):

- Remove v4.0.0 references (this package never had that version)
- Clarify CLI never existed in this fork

### Phase 4: Data Format Clarifications

**4.1 Add Column Name Mapping** to `docs/architecture/DATA_FORMAT.md`:

```markdown
### Column Naming (CSV vs Database)

| CSV Column | Database Column | Type          | Notes                      |
| ---------- | --------------- | ------------- | -------------------------- |
| `date`     | `timestamp`     | DateTime64(6) | Converted during ingestion |
| `open`     | `open`          | Float64       | Direct mapping             |

...
```text

**4.2 Resolve Timeframe Discrepancy**:

**Option A** (Recommended): Update `utils/timeframe_constants.py`:

```python
TIMEFRAME_TO_MINUTES: Dict[str, float] = {
    # ... existing 13 ...
    "3d": 4320,   # 3 days
    "1w": 10080,  # 7 days
    "1mo": 43200, # 30 days (approximation)
}
```text

**Option B**: Document that bulk loader supports 16 timeframes (not 13)

### Phase 5: Empirical Validation

**Objective**: Validate fixes work end-to-end

**Test Suite** (`/tmp/doc-audit/validation/`):

```bash
# Extract 10 representative examples
for doc in python-api.md DATA_COLLECTION.md QUERY_PATTERNS.md; do
  extract_code_blocks "docs/guides/$doc" > "/tmp/doc-audit/test_${doc%.md}.py"
done

# Run with actual package
cd /tmp/doc-audit/
for test in test_*.py; do
  uv run "$test" || echo "FAILED: $test"
done
```bash

**Validation Metrics**:

- ✅ All imports resolve
- ✅ Syntax is valid
- ✅ Basic execution succeeds (or fails gracefully with clear errors)

## Validation

### Automated Checks

**Package Name Validation**:

```bash
# Zero old references (except cache dir, ADRs, CHANGELOG)
grep -r "gapless_crypto_clickhouse" docs/ examples/ | \
  grep -v -E "(\.cache|decisions|CHANGELOG)" | \
  wc -l
# Expected: 0
```python

**Import Validation**:

````bash
# Extract all Python code blocks from docs
find docs/ -name "*.md" -exec \
  grep -Pzo '```python\n\K.*?(?=\n```)' {} \; | \
  python -m py_compile -
# Expected: No SyntaxError
````

**Test Suite**:

```bash
uv run pytest tests/ -v
# Expected: All tests pass
```python

### Manual Checklist

- [ ] All 75 Python examples execute without `ModuleNotFoundError`
- [ ] Architecture docs include ClickHouse section
- [ ] CLI migration guide retitled and imports fixed
- [ ] Data format docs clarify CSV vs DB column naming
- [ ] Version references consistent (v1.0.0)
- [ ] No stale parent package references (except historical)

## Consequences

### Positive

- **Restored Usability**: All 75 Python examples work immediately
- **Complete Documentation**: ClickHouse integration (primary feature) now documented
- **Accuracy**: Code-doc alignment restored to >95% (from 0-92%)
- **Maintainability**: Empirical validation prevents future drift
- **Clarity**: Users understand this is a ClickHouse-first package (not file-based)

### Negative

- **Effort**: ~15 files modified, ~200-300 lines changed
- **Validation Time**: Empirical testing adds ~30 minutes to workflow
- **Breaking for Preview Users**: Anyone following old docs must update imports

### Neutral

- **Cache Directory**: Intentionally keeps `~/.cache/gapless-crypto-data/` name (backward compat)
- **Historical References**: ADRs and CHANGELOGs preserve parent package history

## Alternatives Considered

### Alternative 1: Partial Fix (Examples Only)

**Implementation**: Fix only Python examples, leave architecture docs as-is

**Pros**: Faster (30 min vs 2 hours)

**Cons**: Leaves ClickHouse undocumented, version confusion persists

**Verdict**: Rejected - fails correctness SLO

### Alternative 2: Regenerate All Docs from Scratch

**Implementation**: Delete all docs, regenerate from codebase

**Pros**: Guaranteed accuracy

**Cons**: Loses valuable context/explanations, massive effort (~10 hours)

**Verdict**: Rejected - violates "copy/move instead of regenerate" principle

### Alternative 3: Add Compatibility Layer

**Implementation**: Keep old docs, add `gapless_crypto_clickhouse` → `gapless_crypto_clickhouse` import alias

**Pros**: No doc changes needed

**Cons**: Confusing for new users, violates "no backward compatibility" constraint

**Verdict**: Rejected - this is v1.0.0, no legacy needed

## Compliance

### Error Handling

**Policy**: Raise and propagate (no silent failures)

- **Broken examples**: Fail validation, block commit
- **Import errors**: Explicit `ModuleNotFoundError` (no fallback imports)
- **Path errors**: Grep validation catches incorrect paths

### SLOs

- **Availability**: N/A (documentation, not runtime)
- **Correctness**: 100% of examples must execute without errors
- **Observability**: Empirical validation provides feedback before commit
- **Maintainability**: Automated grep/import checks prevent regression

### OSS Preference

- **Validation**: Use `uv run` (not custom test harness)
- **Syntax Check**: Use `python -m py_compile` (not custom parser)
- **Find-Replace**: Use `sed` (not custom scripts)

### Auto-Validation

**CI/CD Integration** (future enhancement):

```yaml
# .github/workflows/docs-validation.yml
- name: Validate documentation examples
  run: |
    find docs/ -name "*.md" | xargs extract_code_blocks | \
      xargs -I {} uv run {}
```text

### Semantic Release

**Commit Message**:

```
docs: fix systematic package name inconsistencies across all documentation

BREAKING CHANGE: Documentation examples now use correct gapless_crypto_clickhouse imports.

Fixes 75 broken Python examples across 5 documentation categories.
Adds missing ClickHouse architecture documentation.
Removes obsolete CLI migration guide references.

Agent investigation findings: tmp/doc-audit/ (5 parallel agents)
```

**Expected Release**: Patch version (v1.0.1) - documentation-only changes

## References

- **Agent Reports**: `tmp/doc-audit/` (5-agent parallel investigation, 2025-11-19)
- **Plan**: `docs/development/plan/0012-documentation-accuracy-remediation/plan.md`
- **ADR-0011**: PyPI Package Fork (context for fork creation)
- **ADR-0005**: ClickHouse Migration (ClickHouse architecture background)

## Decision Makers

- Terry Li (2025-11-19)

## Approval Date

2025-11-19 (implementing immediately)
