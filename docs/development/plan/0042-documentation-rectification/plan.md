# Plan 0042: Documentation Rectification

**ADR**: [ADR-0042](../../../architecture/decisions/0042-documentation-rectification.md)

**Status**: Complete

**Author**: Claude Code

**Last Updated**: 2025-11-25

---

## Overview

Systematic rectification of ~1,140 documentation issues identified by 9-agent parallel audit.

### Goals

1. Fix all critical architecture inaccuracies in OVERVIEW.md
2. Correct broken code examples that prevent execution
3. Update package name references (excluding ADRs for historical context)
4. Add language tags to all code blocks for syntax highlighting
5. Repair broken internal links

### Non-Goals

- Modifying ADR historical references (intentional preservation)
- Changing cache paths (`~/.cache/gapless-crypto-data/` per ADR-0012)
- Consolidating ADR-0037 duplicate directories (user decision: keep both)

---

## Context

### Problem

9-agent audit (2025-11-25) revealed documentation inherited from `gapless-crypto-data` fork (ADR-0011) was not systematically updated during package rename.

### Agent Findings Summary

| Agent | Focus            | Critical Issues                        |
| ----- | ---------------- | -------------------------------------- |
| #1    | Broken links     | 105 broken (26% failure rate)          |
| #2    | Outdated content | release-notes.md wrong package         |
| #3    | Code examples    | 3 broken examples in python-api.md     |
| #4    | API alignment    | Method name mismatch, missing sections |
| #5    | Architecture     | 7 critical OVERVIEW.md errors          |
| #6    | Terminology      | 283 package name violations            |
| #7    | Formatting       | 530+ code blocks without language tags |
| #8    | Completeness     | PASS - all ADRs/plans exist            |
| #9    | Cross-references | ADR-0037 duplicates (kept per user)    |

### User Decisions

| Decision            | Choice              |
| ------------------- | ------------------- |
| Package names (283) | Fix all except ADRs |
| Code blocks (530+)  | Fix all             |
| Architecture (7)    | Fix all now         |
| ADR-0037 duplicates | Keep both           |

---

## Task List

| #   | Task                         | Status | Notes                            |
| --- | ---------------------------- | ------ | -------------------------------- |
| 1   | Create ADR-0042              | Done   | MADR format                      |
| 2   | Create plan-0042             | Done   | This file                        |
| 3   | Fix OVERVIEW.md (7 errors)   | Done   | Column count, ORDER BY, scope    |
| 4   | Fix examples/README.md       | Done   | Package name, removed CLI refs   |
| 5   | Add code block language tags | Done   | 816 blocks in 88 files           |
| 6   | Run build validation         | Done   | Package imports OK               |
| 7   | Create commit                | Done   | `241b9f0` - 91 files, +1054/-854 |

---

## Implementation Details

### Phase 1: Critical Architecture Fixes

**File**: `docs/architecture/OVERVIEW.md`

| Line | Current                                    | Correct                                                           |
| ---- | ------------------------------------------ | ----------------------------------------------------------------- |
| ~124 | 17 columns                                 | 18 columns (+funding_rate)                                        |
| ~131 | data_source="binance_public_data"          | data_source="cloudfront"                                          |
| ~155 | PRIMARY KEY (symbol, timeframe, timestamp) | ORDER BY (symbol, timeframe, toStartOfHour(timestamp), timestamp) |
| ~157 | ORDER BY timestamp DESC                    | Ascending (per ADR-0034)                                          |
| ~275 | Futures: Out of Scope                      | Production-ready (713 symbols)                                    |
| ~278 | Database: Out of Scope                     | Primary storage backend                                           |

### Phase 2: Code Example Fixes

**File**: `docs/guides/python-api.md`

```python
# Current (broken):
atomic_ops.write_csv_atomic(Path("data.csv"), test_data, headers)

# Correct:
atomic_ops.write_dataframe_atomic(df, include_headers=True)
```

### Phase 3: Package Name Updates

**Pattern**: `gapless-crypto-data` → `gapless-crypto-clickhouse`

**Exclusions**:

- `docs/architecture/decisions/*.md` (historical context)
- `~/.cache/gapless-crypto-data/` paths (ADR-0012)

### Phase 4: Code Block Language Tags

**Target files** (highest counts):

1. deployment/\*.md (128 blocks)
2. development/COMMANDS.md (24 blocks)
3. development/CLI_MIGRATION_GUIDE.md (28 blocks)
4. validation/QUERY_PATTERNS.md (24 blocks)

---

## Risk Assessment

| Risk                      | Likelihood | Impact | Mitigation                 |
| ------------------------- | ---------- | ------ | -------------------------- |
| Incomplete find-replace   | Medium     | High   | Grep validation post-fix   |
| Breaking working examples | Low        | High   | Test each example manually |
| Large commit size         | High       | Low    | Split into logical commits |

---

## Success Criteria

- [ ] Zero `gapless-crypto-data` references outside ADRs and cache paths
- [ ] All code blocks have language tags
- [ ] OVERVIEW.md matches schema.sql and ADR-0034
- [ ] Code examples in python-api.md are executable
- [ ] Build passes without errors

---

## Log File

`logs/0042-documentation-rectification-20251125_HHMMSS.log`
